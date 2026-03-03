"""
Local LLM Engine — Uses the GGUF model in the project root as a Gemini drop-in.
Activated when LLM_BACKEND=local in .env.

Model expected at: <project_root>/Qwen3-0.6B-f16%3AQ5_K_M.gguf
(or any *.gguf file in project root — first found is used)
"""
import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Locate the GGUF model in root
_ROOT = Path(__file__).parent.parent.parent
_GGUF_PATH: Optional[Path] = None
for _f in _ROOT.glob("*.gguf"):
    _GGUF_PATH = _f
    break

_llm = None   # lazy-loaded


def _load_llm():
    global _llm
    if _llm is not None:
        return _llm
    if _GGUF_PATH is None:
        raise FileNotFoundError("No *.gguf file found in project root.")
    try:
        from llama_cpp import Llama
        logger.info(f"Loading local LLM: {_GGUF_PATH.name} …")
        t0 = time.time()
        _llm = Llama(
            model_path=str(_GGUF_PATH),
            n_ctx=4096,
            n_threads=os.cpu_count() or 4,
            n_gpu_layers=0,          # CPU-only; set >0 if CUDA available
            verbose=False,
        )
        logger.info(f"✓ Local LLM loaded in {time.time()-t0:.1f}s")
        return _llm
    except ImportError:
        raise ImportError(
            "llama-cpp-python not installed. "
            "Run: pip install llama-cpp-python --prefer-binary"
        )


def _call_local(prompt: str, max_tokens: int = 1024, temperature: float = 0.1) -> str:
    llm = _load_llm()
    out = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=["```\n\n", "---END---"],
    )
    return out["choices"][0]["text"].strip()


class LocalLLMReasoningEngine:
    """
    Drop-in replacement for GeminiReasoningEngine using the local GGUF model.
    Shares the same DiseaseIndex, knowledge base, and anti-hallucination layers.
    """

    def __init__(self):
        # Import shared components from Gemini engine
        from src.reasoning.diagnostic_engine import (
            DiseaseIndex, DATA_DIR, PROCESSED_DIR
        )
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))

        kb_path = PROCESSED_DIR / "rare_diseases_knowledge_base.json"
        if not kb_path.exists():
            raise FileNotFoundError(f"Knowledge base not found: {kb_path}")

        with open(kb_path, encoding="utf-8") as f:
            self.knowledge_base: List[Dict] = json.load(f)

        self.disease_index = DiseaseIndex(self.knowledge_base)
        self.model_name = f"local/{_GGUF_PATH.name if _GGUF_PATH else 'unknown'}"
        logger.info(f"✓ LocalLLMReasoningEngine ready ({len(self.knowledge_base)} diseases)")

    # ---- reuse anti-hallucination helpers from Gemini engine ----------------
    def _verify_diagnoses(self, differential):
        from src.reasoning.diagnostic_engine import GeminiReasoningEngine as _G
        return _G._verify_diagnoses(self, differential)   # type: ignore

    def _check_rag_support(self, differential, rag_results):
        from src.reasoning.diagnostic_engine import GeminiReasoningEngine as _G
        return _G._check_rag_support(self, differential, rag_results)  # type: ignore

    def _add_disclaimer(self, diagnosis):
        from src.reasoning.diagnostic_engine import GeminiReasoningEngine as _G
        return _G._add_disclaimer(self, diagnosis)        # type: ignore

    # -------------------------------------------------------------------------
    def extract_features(self, clinical_note: str) -> Dict:
        prompt = (
            "Extract clinical features from this note as JSON.\n"
            "Return ONLY valid JSON with keys: symptoms (list), "
            "genes (list), age_years (number or null), sex (string or null), "
            "lab_values (dict), key_findings (list).\n\n"
            f"Note: {clinical_note}\n\nJSON:"
        )
        try:
            raw = _call_local(prompt, max_tokens=512, temperature=0.1)
            # Extract JSON block
            import re
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception as e:
            logger.warning(f"Local LLM feature extraction failed: {e}")
        # Fallback
        return {
            "symptoms": [],
            "genes": [],
            "age_years": None,
            "sex": None,
            "lab_values": {},
            "key_findings": [],
        }

    def match_diseases(self, features: Dict, top_k: int = 10) -> List[Dict]:
        symptoms = features.get("symptoms", [])
        genes = features.get("genes", [])
        age = features.get("age_years")
        return self.disease_index.match(symptoms, genes, top_k=top_k)

    def generate_diagnosis(self, features: Dict, matches: List[Dict], rag_results: List[Dict]) -> Dict:
        disease_list = "\n".join(
            f"- {m.get('name','?')} (Orpha:{m.get('orpha_id','?')}, score:{m.get('score',0):.1f})"
            for m in matches[:8]
        )
        rag_snip = "\n".join(r.get("content", "")[:200] for r in rag_results[:3])
        prompt = (
            "You are a rare disease specialist. Based on the features and candidate diseases, "
            "produce a differential diagnosis as JSON.\n"
            "Return ONLY valid JSON with key 'differential_diagnosis' (list of objects with: "
            "disease, orpha_id, confidence (0-100), reasoning, supporting_features (list), "
            "against_evidence (list), evidence_strength).\n"
            "Also include: recommended_tests (list), urgency (routine/urgent/emergency).\n\n"
            f"Patient features: {json.dumps(features)}\n\n"
            f"Candidate diseases:\n{disease_list}\n\n"
            f"Literature snippets:\n{rag_snip}\n\n"
            "JSON response:"
        )
        try:
            raw = _call_local(prompt, max_tokens=1500, temperature=0.1)
            import re
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                result = json.loads(m.group())
                result["patient_features"] = features
                return result
        except Exception as e:
            logger.warning(f"Local LLM diagnosis generation failed: {e}")
        return {
            "patient_features": features,
            "differential_diagnosis": [
                {
                    "disease": m.get("name", "Unknown"),
                    "orpha_id": m.get("orpha_id"),
                    "confidence": min(90, int(m.get("score", 10) * 5)),
                    "reasoning": "Matched via Orphanet inverted index.",
                    "supporting_features": features.get("symptoms", [])[:3],
                    "against_evidence": [],
                    "evidence_strength": "moderate",
                }
                for m in matches[:5]
            ],
            "recommended_tests": ["Genetic panel", "Enzyme assay", "MRI"],
            "urgency": "routine",
        }

    def diagnose(self, clinical_note: str, rag_system=None, top_k: int = 5) -> Dict:
        from concurrent.futures import ThreadPoolExecutor

        features = self.extract_features(clinical_note)

        def _db_task():
            return self.match_diseases(features, top_k=top_k * 2)

        def _rag_task():
            if rag_system is None:
                return []
            query = " ".join(features.get("symptoms", []) + features.get("genes", []))
            try:
                return rag_system.query(query, k=5) or []
            except Exception:
                return []

        with ThreadPoolExecutor(max_workers=2) as ex:
            db_fut = ex.submit(_db_task)
            rag_fut = ex.submit(_rag_task)
            matches = db_fut.result()
            rag_results = rag_fut.result()

        result = self.generate_diagnosis(features, matches, rag_results)

        diff = result.get("differential_diagnosis", [])
        diff = self._verify_diagnoses(diff)
        diff = self._check_rag_support(diff, rag_results)
        result["differential_diagnosis"] = diff

        result["literature_references"] = [
            {"content": r.get("content", "")[:300], "source": r.get("metadata", {}).get("source", "")}
            for r in rag_results[:3]
        ]

        return self._add_disclaimer(result)
