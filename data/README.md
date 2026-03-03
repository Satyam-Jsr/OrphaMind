# OrphaMind - Rare Disease Diagnostic Intelligence System

A multi-modal diagnostic reasoning system powered by Gemini API for early detection of rare diseases.

## Architecture

### Layer 1: Structured Knowledge Base
- Orphanet rare disease database
- OMIM (Online Mendelian Inheritance in Man)
- NORD (National Organization for Rare Disorders)

### Layer 2: RAG Literature System
- Medical textbooks and case reports
- Research papers on rare diseases
- Clinical guidelines

### Layer 3: Patient Data Processing
- Clinical note analysis
- Lab value interpretation
- Symptom clustering and correlation

## Project Structure

```
OrphaMind/
├── data/
│   ├── raw/                    # Raw datasets and books
│   │   ├── datasets/          # Orphanet, OMIM, NORD
│   │   └── literature/        # Medical books and papers
│   ├── processed/             # Cleaned and structured data
│   └── embeddings/            # Vector embeddings for RAG
├── src/
│   ├── data_processing/       # Data ingestion and cleaning
│   ├── rag/                   # RAG implementation
│   ├── reasoning/             # Gemini reasoning engine
│   └── api/                   # Backend API
├── frontend/                  # Dashboard UI
└── docs/                      # Documentation
```

## Tech Stack

- **AI**: Google Gemini API (multimodal reasoning)
- **RAG**: LangChain + ChromaDB/Pinecone
- **Backend**: FastAPI/Flask
- **Frontend**: React/Next.js
- **Data**: Pandas, NumPy
