# Data Sources for OrphaMind

## 📊 Structured Rare Disease Datasets

### 1. Orphanet
**Source**: https://www.orphadata.com/data/xml/en_product1.xml
- **What**: Comprehensive rare disease database
- **Format**: XML/JSON
- **Contains**: 
  - Disease names and classifications
  - Symptoms and clinical features
  - Prevalence data
  - Age of onset
  - Inheritance patterns
- **License**: Free for non-commercial use
- **Download**: `curl -O https://www.orphadata.com/data/xml/en_product1.xml`

### 2. OMIM (Online Mendelian Inheritance in Man)
**Source**: https://omim.org/downloads
- **What**: Genetic disease database
- **Format**: Text/JSON (requires API key)
- **Contains**:
  - Gene-disease relationships
  - Clinical synopses
  - Molecular genetics
  - Inheritance patterns
- **License**: Requires registration
- **API**: https://omim.org/api

### 3. Human Phenotype Ontology (HPO)
**Source**: https://hpo.jax.org/app/download/annotation
- **What**: Standardized vocabulary of phenotypic abnormalities
- **Format**: TSV/OBO
- **Contains**:
  - Disease-phenotype annotations
  - Symptom hierarchies
  - Frequency data
- **License**: Open access
- **Download**: https://hpo.jax.org/app/data/annotations

### 4. GARD (Genetic and Rare Diseases Information Center)
**Source**: https://rarediseases.info.nih.gov/
- **What**: NIH rare disease database
- **Format**: JSON (via API)
- **License**: Public domain

## 📚 Medical Literature Sources

### Books (PDF/ePub/Text)
1. **"Rare Diseases: Diagnosis and Therapeutics"** - Free medical texts
2. **"Orphan Diseases and Orphan Drugs"** - Open access books
3. **"Clinical Features of Rare Diseases"** - Medical reference texts
4. **PubMed Central Open Access**: https://www.ncbi.nlm.nih.gov/pmc/

### Research Papers
- **PubMed API**: https://www.ncbi.nlm.nih.gov/home/develop/api/
- **Europe PMC**: https://europepmc.org/RestfulWebService
- **arXiv Medical**: https://arxiv.org/list/q-bio/recent

### Case Reports
- **BMJ Case Reports**: https://casereports.bmj.com/
- **Journal of Medical Case Reports**: Free case studies
- **PubMed Case Reports**: Filtered search

## 📥 Quick Start Data Collection

### Priority 1: Essential Datasets (Free & Fast)
```bash
# Orphanet - Core rare disease data
curl -O https://www.orphadata.com/data/xml/en_product1.xml

# HPO - Phenotype annotations
wget http://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt
wget http://purl.obolibrary.org/obo/hp/hpoa/phenotype_to_genes.txt
```

### Priority 2: Medical Literature
- Start with open-access PubMed articles on rare diseases
- Use keywords: "rare disease", "orphan disease", "diagnostic delay"
- Focus on case reports with diagnostic reasoning

### Priority 3: Books (if available)
- Medical textbooks on rare diseases (PDF)
- Clinical guidelines
- Diagnostic manuals

## 🔧 Data Processing Pipeline

1. **Download**: Automated scripts to fetch datasets
2. **Parse**: Convert XML/TSV to JSON
3. **Normalize**: Standardize disease names, symptoms
4. **Enrich**: Combine data from multiple sources
5. **Embed**: Generate vectors for RAG system
6. **Index**: Store in vector database

## ⚠️ Legal & Ethical Considerations

- Always check license terms before using datasets
- OMIM requires registration and citation
- Books must be open access or properly licensed
- Patient data must be synthetic/anonymized for demo
- Cite all data sources in your presentation
