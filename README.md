# 🧬 OrphaMind — AI-Powered Rare Disease Diagnostic Intelligence

> **Geminathon Submission** · Built with Google Gemini API

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue)](https://react.dev)
[![Gemini](https://img.shields.io/badge/Gemini-2.5‑Flash-orange)](https://ai.google.dev)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.6-purple)](https://www.trychroma.com)

---

## 🩺 Problem Statement

Rare diseases affect **1 in 17 people** worldwide, yet the average patient waits **4–7 years** to receive a correct diagnosis. Clinicians face an overwhelming knowledge gap: there are over **10,000 rare diseases**, many with overlapping presentations, sparse literature, and no single searchable knowledge source. A rare-disease-aware AI assistant that can synthesize structured disease databases, peer-reviewed literature, and clinical reasoning — in seconds — could dramatically shorten the diagnostic odyssey.

---

## 💡 Solution

**OrphaMind** is a full-stack clinical decision-support system that ingests a patient's **clinical note** (typed, dictated, or scanned via OCR) and returns a ranked differential diagnosis with confidence scores, supporting/against evidence, recommended workup, and direct literature citations — all powered by Google Gemini.

The system combines:
- **Structured knowledge** from Orphanet (11,456 rare diseases with symptoms, genes, prevalence)
- **Unstructured knowledge** from a 87,848-document RAG corpus (GeneReviews, OMIM, clinical textbooks)
- **Gemini 2.5 Flash** for multi-step diagnostic reasoning and hallucination guarding
- **4-layer validation** to prevent LLM hallucination of fictitious diseases

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React / Vite UI                      │
│  DiagnoseTab · HistoryTab · SearchTab · OCR Upload       │
└─────────────────────┬───────────────────────────────────┘
                      │ REST /diagnose /ocr /history
┌─────────────────────▼───────────────────────────────────┐
│               FastAPI Backend  (port 8000)               │
│  Input Validation → Lab Analyzer → RAG → Reasoning      │
└────┬──────────────────┬──────────────────────────────────┘
     │                  │
┌────▼────┐      ┌──────▼──────────────────────┐
│  SQLite │      │  ChromaDB Vector Store       │
│  Patient│      │  87,848 docs (ONNX embeds)   │
│  History│      └──────┬──────────────────────┘
└─────────┘             │ top-k semantic search
                 ┌──────▼──────────────────────┐
                 │    Gemini Reasoning Engine   │
                 │  gemini-2.5-flash (extract)  │
                 │  gemini-2.5-flash (diagnose) │
                 │  Orphanet inverted index     │
                 │  4-layer hallucination guard │
                 └─────────────────────────────┘
```

### Key Modules

| Module | File | Purpose |
|--------|------|---------|
| REST API | `src/api/main.py` | FastAPI routes, OCR, patient history endpoints |
| RAG System | `src/rag/rag_system.py` | ChromaDB vector store, semantic retrieval |
| Reasoning Engine | `src/reasoning/diagnostic_engine.py` | Gemini multi-step diagnosis, inverted disease index |
| Lab Analyzer | `src/utils/lab_analyzer.py` | Auto-parse lab values, flag criticals, fold-change |
| Input Validator | `src/utils/input_validator.py` | Reject gibberish / prompt-injection attempts |
| Patient History | `src/db/patient_history.py` | SQLite CRUD for case persistence |
| Data Processing | `src/data_processing/` | Orphanet XML parser, literature ingestion |

---

## ✨ Key Features

### Clinical Diagnosis
- **Differential diagnosis** — ranked list with confidence 0–100%, reasoning, supporting/against evidence
- **Orphanet verification** — every AI suggestion cross-checked against 11,456 known diseases; unverified entries flagged
- **Literature RAG** — 87,848 chunks from GeneReviews, OMIM, clinical references retrieved via semantic search
- **4-layer hallucination guard** — Orphanet DB check → symptom index match → literature grounding → confidence penalty

### Input Flexibility
- **Free-text clinical notes** — paste or type any structured/unstructured clinical narrative
- **OCR upload** — scan images or PDFs (typed and handwritten modes via Tesseract)
- **Symptom builder** — 55 pre-defined symptoms selectable as pills, auto-appended to note
- **Instant validation** — debounced 900 ms validity check while typing

### Lab Intelligence
- **Automatic lab parsing** — extracts test name, value, unit, reference range from the clinical note
- **Critical flagging** — CRITICAL HIGH/LOW, fold-change above upper limit of normal
- **Lab-augmented context** — parsed labs are injected into the RAG query for better retrieval

### Patient History
- **Case persistence** — every diagnosis saved to SQLite with timestamp and patient ID
- **History browser** — search by patient ID or browse all patients; click to reload any case
- **Tab persistence** — switching tabs never erases the current diagnosis (CSS display:none)

### Disease Search
- **Full-text + semantic search** across all 11,456 Orphanet diseases
- Detail modal with description, symptoms, inheritance, OMIM links

---

## 🛠️ Technologies Used

| Category | Technology |
|----------|-----------|
| **LLM** | Google Gemini 2.5 Flash (diagnosis) + 2.0 Flash (feature extraction) |
| **Vector DB** | ChromaDB 0.6 with ONNX DefaultEmbeddingFunction |
| **Backend** | FastAPI 0.115, Uvicorn, Pydantic v2 |
| **OCR** | Tesseract 5.5 via pytesseract |
| **Database** | SQLite (patient history) |
| **Frontend** | React 18, Vite 5, plain CSS design system |
| **Data Sources** | Orphanet XML, GeneReviews, OMIM, clinical textbooks |
| **Language** | Python 3.12, JavaScript (ES2022) |

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (Windows installer — install to default path)
- Google Gemini API key → [Get one free](https://aistudio.google.com/app/apikey)

### 1 · Clone & install Python deps

```bash
git clone https://github.com/Satyam-Jsr/OrphaMind.git
cd OrphaMind
pip install -r requirements.txt
```

### 2 · Configure environment

```bash
cp .env.example .env
# Edit .env and set:
#   GOOGLE_API_KEY=your_actual_key
```

### 3 · Build the knowledge base (one-time, ~10 min)

```bash
# Download and index all data
python src/data_processing/download_datasets.py   # downloads Orphanet XML + literature
python src/rag/rag_system.py                       # builds ChromaDB (87,848 docs)
```

> If you already have the data, just re-run `rag_system.py` to rebuild the index.

### 4 · Start the backend

```bash
python src/api/main.py
# → http://localhost:8000
# → API docs at http://localhost:8000/docs
```

### 5 · Start the frontend

```bash
cd ui
npm install
npm run dev
# → http://localhost:3002
```

---

## 📡 API Reference

### `POST /diagnose`

```json
{
  "clinical_note": "8-year-old male with progressive muscle weakness, CK 8500, calf pseudohypertrophy, positive Gowers sign",
  "patient_id": "P001",
  "top_k_diseases": 5,
  "include_literature": true,
  "save_to_history": true
}
```

**Response** includes: `differential_diagnosis[]`, `recommended_tests[]`, `urgency`, `urgency_reason`, `lab_analysis[]`, `literature_references[]`, `processing_time_ms`

### `POST /ocr`

Upload an image or PDF → returns extracted `text`, detected `lab_values`, `char_count`.

Query param: `note_type=typed|handwritten`

### Other endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System status, disease count |
| GET | `/diseases/search?query=...` | Search 11,456 diseases |
| GET | `/diseases/{orphanet_id}` | Disease detail |
| GET | `/history/{patient_id}` | Patient case history |
| GET | `/cases/{case_id}` | Single case detail |
| GET | `/patients` | All patients list |
| POST | `/validate` | Validate clinical note |

---

## 📂 Project Structure

```
OrphaMind/
├── src/
│   ├── api/
│   │   └── main.py                  # FastAPI application
│   ├── rag/
│   │   └── rag_system.py            # ChromaDB vector store + retrieval
│   ├── reasoning/
│   │   ├── diagnostic_engine.py     # Gemini reasoning + disease index
│   │   └── local_llm_engine.py      # Local LLM fallback (llama-cpp)
│   ├── utils/
│   │   ├── input_validator.py       # Input validation + injection guard
│   │   └── lab_analyzer.py          # Lab value extraction + flagging
│   ├── db/
│   │   └── patient_history.py       # SQLite patient history
│   └── data_processing/
│       ├── parse_orphanet.py        # Orphanet XML → JSON
│       ├── download_datasets.py     # Data downloader
│       └── process_books.py         # Literature chunker
├── ui/                              # React/Vite frontend
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── DiagnoseTab.jsx      # Main diagnosis interface
│           ├── HistoryTab.jsx       # Patient history browser
│           ├── SearchTab.jsx        # Disease search
│           ├── ResultsPanel.jsx     # Diagnostic report display
│           ├── LabPanel.jsx         # Lab results table
│           └── Header.jsx
├── data/                            # Knowledge base (not in repo — too large)
│   ├── raw/                         # Orphanet XML, literature downloads
│   └── processed/                   # Parsed JSON knowledge base
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🧠 How the Diagnosis Pipeline Works

```
Clinical Note (free text)
        │
        ▼
[1] Input Validation ─── reject gibberish / prompt injection
        │
        ▼
[2] Lab Extraction ────── parse lab values, flag criticals
        │
        ▼
[3] Feature Extraction ── Gemini 2.0 Flash: symptoms, genes, demographics (~1.5s)
        │
        ▼
[4] Candidate Retrieval ─ Orphanet inverted index: O(k) symptom lookup
        │
        ▼
[5] RAG Retrieval ──────── ChromaDB: semantic search over 87,848 literature chunks
        │
        ▼
[6] Diagnostic Reasoning ─ Gemini 2.5 Flash: differential + workup + urgency (~4-6s)
        │
        ▼
[7] Hallucination Guard ── 4-layer check: Orphanet DB, symptom index, lit search, confidence
        │
        ▼
Structured Diagnostic Report
```

---

## 🔒 Safety & Ethics

- **Research tool only** — every response includes a prominent disclaimer against clinical use
- **Input sanitization** — prompt-injection and gibberish detection with clear error messages  
- **Hallucination penalties** — unverifiable diseases receive −20% confidence and a warning badge
- **Transparent sourcing** — every literature reference shows source, type, and excerpt

---

## 🎯 Innovation Highlights

1. **Dual Gemini model strategy** — `gemini-2.5-flash` for both feature extraction and diagnostic reasoning, delivering high accuracy across the entire pipeline
2. **Inverted disease index** — O(k) symptom-to-disease matching over 11,456 diseases, no full scan
3. **4-layer hallucination guard** — builds trust by penalizing diseases not grounded in Orphanet + literature
4. **Lab-augmented RAG** — automatically parses numeric lab values and injects them as structured context into the retrieval query
5. **CSS display:none tab persistence** — all tabs permanently mounted in DOM so in-progress diagnoses survive navigation

---

##  Team

Mirage

## 👥 Team Members

- Satyam Agarwal
- Soumyajit Mukherjee

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
