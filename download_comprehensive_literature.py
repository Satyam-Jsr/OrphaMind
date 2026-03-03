"""
Comprehensive Literature Downloader
Downloads thousands of papers across rare disease categories
"""

import requests
import time
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LITERATURE_DIR = Path("src/data/raw/literature")
LITERATURE_DIR.mkdir(parents=True, exist_ok=True)

# Comprehensive search queries covering major rare disease categories
SEARCH_QUERIES = [
    # General
    ("rare_disease_diagnosis", "rare disease diagnosis", 500),
    ("orphan_disease", "orphan disease", 300),
    ("diagnostic_delay", "rare disease diagnostic delay", 200),
    
    # Genetic/Metabolic
    ("genetic_disorders", "genetic disorders diagnosis", 500),
    ("metabolic_disorders", "inborn errors of metabolism", 400),
    ("lysosomal_storage", "lysosomal storage disease", 300),
    ("mitochondrial", "mitochondrial disease diagnosis", 300),
    
    # Neuromuscular
    ("muscular_dystrophy", "muscular dystrophy", 400),
    ("neuromuscular_disease", "neuromuscular disease", 400),
    ("neuropathy", "hereditary neuropathy", 300),
    
    # Connective Tissue
    ("ehlers_danlos", "Ehlers-Danlos syndrome", 200),
    ("marfan", "Marfan syndrome", 200),
    ("osteogenesis", "osteogenesis imperfecta", 200),
    
    # Immune/Inflammatory
    ("primary_immunodeficiency", "primary immunodeficiency", 300),
    ("autoinflammatory", "autoinflammatory disease", 200),
    
    # Hematologic
    ("hemophilia", "hemophilia diagnosis", 200),
    ("thalassemia", "thalassemia", 200),
    ("sickle_cell", "sickle cell disease", 200),
    
    # Endocrine
    ("adrenal_insufficiency", "adrenal insufficiency rare", 150),
    ("pituitary_disorders", "pituitary disorders rare", 150),
    
    # Other
    ("undiagnosed_diseases", "undiagnosed rare disease", 300),
    ("case_reports_rare", "rare disease case report", 500),
]


def download_pubmed_batch(filename: str, query: str, max_results: int = 500):
    """Download PubMed articles with rate limiting"""
    logger.info(f"Searching: {query} (max {max_results} results)")
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    try:
        # Search
        search_url = f"{base_url}esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }
        
        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        
        search_results = response.json()
        pmids = search_results.get("esearchresult", {}).get("idlist", [])
        
        logger.info(f"  Found {len(pmids)} articles")
        
        if not pmids:
            return 0
        
        # Fetch (in batches of 200 to avoid timeout)
        all_content = []
        for i in range(0, len(pmids), 200):
            batch_pmids = pmids[i:i+200]
            
            fetch_url = f"{base_url}efetch.fcgi"
            params = {
                "db": "pubmed",
                "id": ",".join(batch_pmids),
                "retmode": "xml"
            }
            
            response = requests.get(fetch_url, params=params, timeout=90)
            response.raise_for_status()
            all_content.append(response.content)
            
            # Rate limiting - NCBI requires max 3 requests/second
            time.sleep(0.4)
        
        # Combine and save
        output_path = LITERATURE_DIR / f"{filename}.xml"
        with open(output_path, "wb") as f:
            # Write combined XML
            f.write(b'<?xml version="1.0"?>\n<PubmedArticleSet>\n')
            for content in all_content:
                # Extract articles from each batch
                start = content.find(b'<PubmedArticle')
                end = content.rfind(b'</PubmedArticle>') + len(b'</PubmedArticle>')
                if start != -1 and end > start:
                    f.write(content[start:end])
                    f.write(b'\n')
            f.write(b'</PubmedArticleSet>')
        
        logger.info(f"  ✓ Saved {len(pmids)} articles to {output_path}")
        return len(pmids)
        
    except Exception as e:
        logger.error(f"  ✗ Failed: {e}")
        return 0


def main():
    """Download comprehensive literature"""
    logger.info("=== Comprehensive Literature Download ===")
    logger.info(f"Downloading {len(SEARCH_QUERIES)} categories")
    logger.info(f"Estimated time: 15-20 minutes")
    logger.info(f"Estimated total: ~6,000 articles\n")
    
    input("Press Enter to start download...")
    
    total_articles = 0
    start_time = time.time()
    
    for i, (filename, query, max_results) in enumerate(SEARCH_QUERIES, 1):
        logger.info(f"\n[{i}/{len(SEARCH_QUERIES)}] {filename}")
        count = download_pubmed_batch(filename, query, max_results)
        total_articles += count
        
        # Progress update
        elapsed = time.time() - start_time
        avg_time = elapsed / i
        remaining = avg_time * (len(SEARCH_QUERIES) - i)
        logger.info(f"  Progress: {i}/{len(SEARCH_QUERIES)} | Total articles: {total_articles} | ETA: {remaining/60:.1f} min")
    
    logger.info("\n=== Download Complete ===")
    logger.info(f"Total articles downloaded: {total_articles}")
    logger.info(f"Time taken: {(time.time() - start_time)/60:.1f} minutes")
    logger.info(f"Saved to: {LITERATURE_DIR}")
    logger.info("\nNext step: python src/data_processing/process_books.py")


if __name__ == "__main__":
    main()
