# Quick Start Guide - Data Acquisition

## Step 1: Install Dependencies

```powershell
cd c:\Users\hp\OneDrive\Documents\OrphaMind
pip install -r requirements.txt
```

## Step 2: Download Structured Datasets (Recommended First)

```powershell
python src/data_processing/download_datasets.py
```

Choose option **4** to download all datasets:
- ✅ Orphanet (comprehensive rare disease database)
- ✅ HPO (Human Phenotype Ontology)
- ✅ PubMed articles on rare diseases

This takes ~5-10 minutes and downloads ~100MB of data.

## Step 3: Parse Orphanet Data

```powershell
python src/data_processing/parse_orphanet.py
```

This creates: `data/processed/rare_diseases_knowledge_base.json`

Contains structured info on 6000+ rare diseases:
- Disease names and synonyms
- Symptoms
- Age of onset
- Inheritance patterns
- Prevalence data

## Step 4: Add Medical Books (Optional but Recommended)

1. Download open-access medical books on rare diseases (PDF format)
2. Place in: `data/raw/literature/`

**Suggested sources:**
- PubMed Central Bookshelf: https://www.ncbi.nlm.nih.gov/books/
- Search for: "rare diseases", "orphan diseases", "clinical genetics"

Example books to look for:
- "Rare Diseases: Diagnosis and Therapeutics"
- "Clinical Features of Rare Diseases"
- Case report compilations

## Step 5: Process Books for RAG

```powershell
python src/data_processing/process_books.py
```

This creates: `data/processed/literature_documents.json`

Converts books into chunks ready for vector embedding.

## What You'll Have After This:

### Layer 1: Structured Knowledge Base ✅
- `rare_diseases_knowledge_base.json` - 6000+ diseases with symptoms, genetics

### Layer 2: RAG Literature ✅
- `literature_documents.json` - Medical books + PubMed articles chunked for retrieval

### Layer 3: Patient Data (Next Step)
- Mock patient cases with clinical notes
- Symptom extraction and matching engine

## Next Steps:

1. **Set up Gemini API key**
   ```powershell
   Copy-Item .env.example .env
   # Edit .env and add your Gemini API key
   ```

2. **Build the RAG system** with vector embeddings (ChromaDB + Gemini)

3. **Implement reasoning engine** for diagnostic inference

4. **Create patient input interface** for clinical notes

---

## Troubleshooting

**No internet/download fails?**
- Download datasets manually from links in `data/DATA_SOURCES.md`
- Place in `data/raw/datasets/`

**No books available?**
- System will still work with PubMed articles only
- Can add books later

**Want minimal setup?**
- Just run Orphanet download + parse
- That's 6000+ diseases - enough for demo
