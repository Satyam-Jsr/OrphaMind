"""
OrphaMind Data Downloader
Automated script to download rare disease datasets
"""

import os
import requests
import json
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create data directories
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DATASETS_DIR = DATA_DIR / "raw" / "datasets"
RAW_LITERATURE_DIR = DATA_DIR / "raw" / "literature"
PROCESSED_DIR = DATA_DIR / "processed"

for dir_path in [RAW_DATASETS_DIR, RAW_LITERATURE_DIR, PROCESSED_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


def download_orphanet():
    """Download Orphanet rare disease database"""
    logger.info("Downloading Orphanet database...")
    
    urls = {
        "diseases": "https://www.orphadata.com/data/xml/en_product1.xml",
        "prevalence": "https://www.orphadata.com/data/xml/en_product9_prev.xml",
        "clinical_signs": "https://www.orphadata.com/data/xml/en_product4.xml",
        "genes": "https://www.orphadata.com/data/xml/en_product6.xml"
    }
    
    for name, url in urls.items():
        try:
            output_path = RAW_DATASETS_DIR / f"orphanet_{name}.xml"
            logger.info(f"Downloading {name} from {url}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            logger.info(f"✓ Saved to {output_path}")
        except Exception as e:
            logger.error(f"✗ Failed to download {name}: {e}")


def download_hpo():
    """Download Human Phenotype Ontology data"""
    logger.info("Downloading HPO annotations...")
    
    urls = {
        "phenotype_to_genes": "http://purl.obolibrary.org/obo/hp/hpoa/phenotype_to_genes.txt",
        "genes_to_phenotype": "http://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt",
        "phenotype_annotations": "http://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa"
    }
    
    for name, url in urls.items():
        try:
            output_path = RAW_DATASETS_DIR / f"hpo_{name}.txt"
            logger.info(f"Downloading {name}...")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            logger.info(f"✓ Saved to {output_path}")
        except Exception as e:
            logger.error(f"✗ Failed to download {name}: {e}")


def download_pubmed_articles(query: str = "rare disease diagnosis", max_results: int = 100):
    """Download abstracts from PubMed"""
    logger.info(f"Searching PubMed for: {query}")
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    try:
        # Search for articles
        search_url = f"{base_url}esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json"
        }
        
        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        
        search_results = response.json()
        pmids = search_results.get("esearchresult", {}).get("idlist", [])
        
        logger.info(f"Found {len(pmids)} articles")
        
        if not pmids:
            return
        
        # Fetch article details
        fetch_url = f"{base_url}efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml"
        }
        
        response = requests.get(fetch_url, params=params, timeout=60)
        response.raise_for_status()
        
        output_path = RAW_LITERATURE_DIR / f"pubmed_{query.replace(' ', '_')}.xml"
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        logger.info(f"✓ Saved {len(pmids)} articles to {output_path}")
        
    except Exception as e:
        logger.error(f"✗ Failed to download PubMed articles: {e}")


def create_sample_books_structure():
    """Create placeholder structure for medical books"""
    logger.info("Creating books directory structure...")
    
    books_readme = RAW_LITERATURE_DIR / "BOOKS_README.md"
    content = """# Medical Books for RAG System

## Instructions for Adding Books

1. Place medical textbooks (PDF format) in this directory
2. Recommended books on rare diseases:
   - Rare Diseases: Diagnosis and Therapeutics
   - Orphan Diseases and Orphan Drugs
   - Clinical Features of Rare Diseases
   - Genetic Disorders and the Fetus

3. File naming convention:
   - Use descriptive names: `rare_disease_textbook_smith_2024.pdf`
   - Avoid spaces: use underscores instead

4. Sources for open-access medical books:
   - PubMed Central Bookshelf: https://www.ncbi.nlm.nih.gov/books/
   - Open Textbook Library: https://open.umn.edu/opentextbooks/
   - MedEdPORTAL: https://www.mededportal.org/

## Current Books
(Add your books here manually, then run the book processing script)
"""
    
    with open(books_readme, "w") as f:
        f.write(content)
    
    logger.info(f"✓ Created {books_readme}")


def main():
    """Main data download workflow"""
    logger.info("=== OrphaMind Data Downloader ===")
    
    print("\nWhat would you like to download?")
    print("1. Orphanet database (recommended, ~10MB)")
    print("2. HPO annotations (recommended, ~50MB)")
    print("3. PubMed articles (abstracts only)")
    print("4. All of the above")
    print("5. Setup books directory only")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        download_orphanet()
    elif choice == "2":
        download_hpo()
    elif choice == "3":
        query = input("Enter search query (default: 'rare disease diagnosis'): ").strip()
        query = query if query else "rare disease diagnosis"
        download_pubmed_articles(query)
    elif choice == "4":
        download_orphanet()
        download_hpo()
        download_pubmed_articles()
    elif choice == "5":
        create_sample_books_structure()
    else:
        logger.error("Invalid choice")
        return
    
    create_sample_books_structure()
    
    logger.info("\n=== Download Complete ===")
    logger.info(f"Raw datasets: {RAW_DATASETS_DIR}")
    logger.info(f"Literature: {RAW_LITERATURE_DIR}")


if __name__ == "__main__":
    main()
