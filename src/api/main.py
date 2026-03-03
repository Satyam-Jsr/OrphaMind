"""
OrphaMind FastAPI Backend v2.0
Features: input validation, lab analysis, OCR, patient history, local LLM option
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import logging
import os
import time
from pathlib import Path
import sys

src_path = Path(__file__).parent.parent
sys.path.append(str(src_path))

from rag.rag_system import OrphaMindRAG
from reasoning.diagnostic_engine import GeminiReasoningEngine
from utils.input_validator import validate_clinical_note
from utils.lab_analyzer import analyze_labs, labs_to_clinical_context
from db.patient_history import save_case, get_patient_history, get_case_detail, get_all_patients, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LLM_BACKEND = os.getenv("LLM_BACKEND", "gemini").lower()

app = FastAPI(
    title="OrphaMind API",
    description="AI-Powered Rare Disease Diagnostic Intelligence v2.0",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_system: Optional[OrphaMindRAG] = None
reasoning_engine = None


class DiagnosticRequest(BaseModel):
    clinical_note: str = Field(..., description="Clinical note with patient history, symptoms, exam findings",
        example="8-year-old male with progressive muscle weakness, elevated CK, positive Gowers sign")
    patient_id: Optional[str] = Field(None, description="Optional patient identifier for history tracking")
    include_literature: bool = Field(True)
    top_k_diseases: int = Field(5, ge=1, le=20)
    save_to_history: bool = Field(True, description="Persist result in patient history")


class DiseaseMatch(BaseModel):
    model_config = {"extra": "ignore"}
    disease: str
    orpha_id: Optional[str] = None
    confidence: float = Field(..., ge=0, le=100)
    reasoning: str
    supporting_features: List[str] = []
    against_evidence: List[str] = []
    evidence_strength: str = "moderate"
    verified_in_orphanet: Optional[bool] = None
    literature_supported: Optional[bool] = None
    evidence_source: Optional[str] = None
    hallucination_warning: Optional[str] = None


class LabResult(BaseModel):
    name: str
    value: float
    unit: str
    normal_range: str
    status: str
    fold_change: Optional[float] = None
    flag: str


class DiagnosticResponse(BaseModel):
    success: bool
    patient_features: Dict
    differential_diagnosis: List[DiseaseMatch]
    recommended_tests: List[str]
    urgency: str
    literature_references: Optional[List[Dict]]
    processing_time_ms: float
    disclaimer: Optional[str] = None
    data_sources: Optional[Dict] = None
    lab_analysis: Optional[List[LabResult]] = None
    case_id: Optional[int] = None
    llm_backend: str = "gemini"


class HealthResponse(BaseModel):
    status: str
    rag_loaded: bool
    reasoning_loaded: bool
    diseases_loaded: int
    llm_backend: str


@app.on_event("startup")
async def startup_event():
    global rag_system, reasoning_engine
    init_db()
    logger.info(f"=== OrphaMind API v2.0 Startup [backend={LLM_BACKEND}] ===")
    try:
        rag_system = OrphaMindRAG()
        rag_system.load_existing_vector_store()
        logger.info("✓ RAG system loaded")
    except Exception as e:
        logger.warning(f"RAG not available: {e}")
        rag_system = None
    try:
        if LLM_BACKEND == "local":
            from reasoning.local_llm_engine import LocalLLMReasoningEngine
            reasoning_engine = LocalLLMReasoningEngine()
            logger.info("✓ Local LLM engine loaded")
        else:
            reasoning_engine = GeminiReasoningEngine()
            logger.info("✓ Gemini engine loaded")
    except Exception as e:
        logger.error(f"Failed to load reasoning engine: {e}")
        reasoning_engine = None
    logger.info("=== OrphaMind Ready ===")


@app.get("/", tags=["Root"])
async def root():
    return {"message": "OrphaMind API v2.0", "docs": "/docs", "health": "/health"}


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    diseases_count = len(reasoning_engine.knowledge_base) if reasoning_engine else 0
    return HealthResponse(
        status="healthy" if reasoning_engine else "degraded",
        rag_loaded=rag_system is not None,
        reasoning_loaded=reasoning_engine is not None,
        diseases_loaded=diseases_count,
        llm_backend=LLM_BACKEND,
    )


@app.post("/diagnose", response_model=DiagnosticResponse, tags=["Diagnosis"])
async def diagnose(request: DiagnosticRequest):
    start_time = time.time()
    if not reasoning_engine:
        raise HTTPException(status_code=503, detail="Reasoning engine not available.")

    valid, reason = validate_clinical_note(request.clinical_note)
    if not valid:
        raise HTTPException(status_code=422, detail=f"Invalid input: {reason}")

    labs = analyze_labs(request.clinical_note)
    lab_context = labs_to_clinical_context(labs)
    enriched_note = request.clinical_note
    if lab_context:
        enriched_note = request.clinical_note + "\n" + lab_context

    try:
        rag = rag_system if request.include_literature else None
        result = reasoning_engine.diagnose(enriched_note, rag_system=rag, top_k=request.top_k_diseases)
        processing_time = (time.time() - start_time) * 1000

        case_id = None
        if request.save_to_history:
            try:
                case_id = save_case(request.clinical_note, result, patient_id=request.patient_id or "anonymous")
            except Exception as e:
                logger.warning(f"Could not save to history: {e}")

        return DiagnosticResponse(
            success=True,
            patient_features=result.get("patient_features", {}),
            differential_diagnosis=[DiseaseMatch(**d) for d in result.get("differential_diagnosis", [])],
            recommended_tests=result.get("recommended_tests", []),
            urgency=result.get("urgency", "routine"),
            literature_references=result.get("literature_references") if request.include_literature else None,
            processing_time_ms=processing_time,
            disclaimer=result.get("disclaimer"),
            data_sources=result.get("data_sources"),
            lab_analysis=[LabResult(**l) for l in labs] if labs else None,
            case_id=case_id,
            llm_backend=LLM_BACKEND,
        )
    except Exception as e:
        logger.error(f"Diagnosis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-labs", tags=["Utilities"])
async def analyze_labs_endpoint(body: Dict):
    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=422, detail="Empty text.")
    labs = analyze_labs(text)
    return {"lab_count": len(labs), "labs": labs}


def _find_tesseract() -> str:
    """Locate tesseract.exe on Windows using common install paths."""
    import shutil
    candidates = [
        r"C:\Users\hp\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # Try PATH
    found = shutil.which("tesseract")
    if found:
        return found
    raise FileNotFoundError(
        "tesseract.exe not found. Install from: "
        "https://github.com/UB-Mannheim/tesseract/wiki"
    )


def _clean_ocr_text(raw: str) -> str:
    """
    Post-process raw Tesseract output for use as a clinical note:
    - Remove form-feed / vertical-tab control chars
    - Collapse runs of blank lines to a single newline
    - Fix common Tesseract substitutions in medical text:
        l→1, O→0, 'tbe'→'the', etc.
    - Strip lines that are purely scanner artefacts (single chars, dashes)
    """
    import re
    text = raw
    # Remove control characters except newline/tab
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    # Collapse 3+ consecutive blank lines → 1
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove lines that are just punctuation / scanner borders
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append('')
            continue
        # Skip lines that are all non-alphanumeric (ruler lines, box-drawing)
        if re.fullmatch(r'[^a-zA-Z0-9]+', stripped):
            continue
        # Skip single-character lines (stray marks)
        if len(stripped) == 1:
            continue
        lines.append(line)
    text = '\n'.join(lines).strip()
    # Common Tesseract medical OCR corrections
    corrections = [
        (r'\btbe\b', 'the'),
        (r'\bpatient s\b', "patient's"),
        (r'\bDr\.([A-Z])', r'Dr. \1'),   # space after Dr.
    ]
    for pattern, replacement in corrections:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


# ── Configure Tesseract once at module load ──────────────────────────────────
try:
    import pytesseract as _pytesseract
    _tess_exe = _find_tesseract()
    _pytesseract.pytesseract.tesseract_cmd = _tess_exe
    # Also inject the directory into PATH so pytesseract's subprocess check passes
    _tess_dir = str(Path(_tess_exe).parent)
    os.environ["PATH"] = _tess_dir + os.pathsep + os.environ.get("PATH", "")
    logger.info(f"Tesseract ready: {_tess_exe}")
except Exception as _tess_err:
    logger.warning(f"Tesseract not configured at startup: {_tess_err}")


@app.post("/ocr-note", tags=["Utilities"])
async def ocr_note(
    file: UploadFile = File(...),
    note_type: str = Query("typed", enum=["typed", "handwritten"])
):
    """
    Extract text from a medical document image or scanned doctor's note.

    **note_type**:
    - `typed` (default) — printed lab reports, typed referral letters.
      Uses PSM 6 → 4 → 3 for uniform text blocks.
    - `handwritten` — doctor's handwritten clinical notes.
      Uses PSM 11 (sparse text) + Tesseract LSTM engine, which tolerates
      irregular line spacing and cursive characters better.

    The extracted text is automatically cleaned (artefact lines removed,
    common OCR substitutions corrected) and can be dropped directly into
    the clinical note textarea for diagnosis.
    """
    try:
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter
        import io

        contents = await file.read()
        img = Image.open(io.BytesIO(contents))

        # ── Preprocessing pipeline ──────────────────────────────────────────
        # 1. Flatten transparency / convert to grayscale (keep as 8-bit L)
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background.convert("L")
        elif img.mode != "L":
            img = img.convert("RGB").convert("L")

        # 2. Upscale if too small — Tesseract degrades below ~200 DPI equivalent
        w, h = img.size
        if max(w, h) < 1600:
            scale = 1600 / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        # 3. Median filter to remove scan noise (salt-and-pepper)
        img = img.filter(ImageFilter.MedianFilter(size=3))

        # 4. Contrast enhancement (adaptive: only boost if image looks washed-out)
        import statistics
        pixels = list(img.getdata())
        pixel_std = statistics.stdev(pixels[:5000])   # sample first 5k pixels
        contrast_factor = 2.0 if pixel_std < 50 else 1.5   # boost more if low contrast
        img = ImageEnhance.Contrast(img).enhance(contrast_factor)

        # 5. Sharpen
        img = img.filter(ImageFilter.SHARPEN)

        # NOTE: Do NOT convert to binary ("1") — Tesseract applies Otsu internally
        # on 8-bit greyscale which is more accurate than a fixed threshold.

        # ── OCR — single best pass; only retry PSM if yield is poor ─────────
        primary_psm = 11 if note_type == "handwritten" else 6
        fallback_psms = (12, 6) if note_type == "handwritten" else (4, 3)

        raw_text = pytesseract.image_to_string(
            img, config=f"--psm {primary_psm} --oem 1"
        ).strip()

        # Only try fallback PSMs if the primary pass produced very little text
        if len(raw_text) < 50:
            for psm in fallback_psms:
                candidate = pytesseract.image_to_string(
                    img, config=f"--psm {psm} --oem 1"
                ).strip()
                if len(candidate) > len(raw_text):
                    raw_text = candidate
                if len(raw_text) >= 50:
                    break

        if not raw_text:
            raise HTTPException(status_code=422, detail="Could not extract text from image.")

        # Clean up OCR artefacts so text is ready to use as a clinical note
        text = _clean_ocr_text(raw_text)

        labs = analyze_labs(text)
        return {
            "text": text,           # cleaned — ready to append to clinical note
            "raw_text": raw_text,   # unmodified Tesseract output
            "char_count": len(text),
            "detected_labs": labs,
            "note_type": note_type,
            "preprocessing": "grayscale → upscale(1600px) → median-denoise → adaptive-contrast → sharpen → Tesseract Otsu"
        }
    except ImportError:
        raise HTTPException(status_code=501, detail="pytesseract not installed. Run: pip install pytesseract pillow")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")


@app.post("/validate-note", tags=["Utilities"])
async def validate_note(body: Dict):
    text = body.get("text", "")
    valid, reason = validate_clinical_note(text)
    return {"valid": valid, "reason": reason}


@app.get("/patients", tags=["History"])
async def list_patients():
    return {"patients": get_all_patients()}


@app.get("/patients/{patient_id}/history", tags=["History"])
async def patient_history(patient_id: str, limit: int = Query(20, ge=1, le=100)):
    history = get_patient_history(patient_id, limit=limit)
    return {"patient_id": patient_id, "count": len(history), "cases": history}


@app.get("/cases/{case_id}", tags=["History"])
async def get_case(case_id: int):
    detail = get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    return detail


_ACRONYM_STOP = {'to','of','a','an','the','and','or','in','for','with','due','by','at','as','on','from'}

def _disease_acronym(name: str) -> str:
    """Generate acronym from disease name, e.g. 'Congenital insensitivity to pain with anhidrosis' -> 'CIPA'"""
    return "".join(w[0].upper() for w in name.split() if w.lower() not in _ACRONYM_STOP and w.isalpha())

@app.get("/diseases/search", tags=["Knowledge Base"])
async def search_diseases(query: str, limit: int = 10):
    if not reasoning_engine:
        raise HTTPException(status_code=503, detail="Reasoning engine not available")
    q = query.strip()
    if not q:
        return {"query": query, "count": 0, "results": []}
    q_lower = q.lower()
    q_upper = q.upper()

    exact, starts, contains = [], [], []

    for disease in reasoning_engine.knowledge_base:
        name = disease.get("name", "")
        name_lower = name.lower()

        # 1. Name match
        if q_lower == name_lower:
            exact.append(disease); continue
        if name_lower.startswith(q_lower):
            starts.append(disease); continue
        if q_lower in name_lower:
            contains.append(disease); continue

        # 2. Synonym match
        matched = False
        for syn in disease.get("synonyms", []):
            syn_lower = syn.lower()
            if q_lower in syn_lower:
                contains.append(disease); matched = True; break
        if matched: continue

        # 3. Gene symbol / name match
        for gene in disease.get("genes", []):
            sym = gene.get("symbol", "").upper()
            gname = gene.get("name", "").lower()
            if q_upper == sym or q_lower in gname:
                contains.append(disease); matched = True; break
        if matched: continue

        # 4. Symptoms match
        for s in disease.get("symptoms", []):
            if q_lower in s.lower():
                contains.append(disease); matched = True; break
        if matched: continue

        # 5. Acronym match (e.g. "CIPA", "SMA", "HSAN")
        if len(q) >= 2 and q_upper == _disease_acronym(name):
            contains.append(disease)

    combined = exact + starts + contains
    # Deduplicate preserving order
    seen = set(); results = []
    for d in combined:
        oid = d.get("orpha_id")
        if oid not in seen:
            seen.add(oid); results.append(d)
        if len(results) >= limit:
            break

    return {"query": query, "count": len(results), "results": results}


@app.get("/diseases/{orpha_id}", tags=["Knowledge Base"])
async def get_disease(orpha_id: str):
    if not reasoning_engine:
        raise HTTPException(status_code=503, detail="Reasoning engine not available")
    for disease in reasoning_engine.knowledge_base:
        if disease.get("orpha_id") == orpha_id:
            return disease
    raise HTTPException(status_code=404, detail=f"Disease {orpha_id} not found")


@app.get("/stats", tags=["System"])
async def get_stats():
    return {
        "api_version": "2.0.0",
        "llm_backend": LLM_BACKEND,
        "systems": {
            "rag_available": rag_system is not None,
            "reasoning_available": reasoning_engine is not None,
        },
        "knowledge_base": {
            "total_diseases": len(reasoning_engine.knowledge_base) if reasoning_engine else 0,
            "sources": ["Orphanet", "HPO"],
        },
    }


if __name__ == "__main__":
    import uvicorn
    print(f"=== OrphaMind API v2.0 [{LLM_BACKEND.upper()}] ===")
    print("Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
