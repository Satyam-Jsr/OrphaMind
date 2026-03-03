"""
Book and Literature Processing for RAG
Converts PDF/text medical books into chunks for vector embedding
"""

import os
from pathlib import Path
from typing import List, Dict
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
LITERATURE_DIR = DATA_DIR / "raw" / "literature"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF file"""
    try:
        import PyPDF2
        
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = []
            
            for page in reader.pages:
                text.append(page.extract_text())
            
            return " ".join(text)
    
    except ImportError:
        logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
        return ""
    except Exception as e:
        logger.error(f"Error extracting PDF {pdf_path}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks for RAG"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind(".")
            if last_period > chunk_size * 0.5:  # Only if period is in last 50%
                end = start + last_period + 1
                chunk = text[start:end]
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return chunks


def process_books() -> List[Dict]:
    """Process all PDF books in literature directory"""
    logger.info("Processing medical books and GeneReviews chapters...")
    
    # Find PDFs in root directory
    pdf_files = list(LITERATURE_DIR.glob("*.pdf"))
    
    # Find PDFs in gene_NBK1116 subdirectory (GeneReviews chapters)
    gene_reviews_dir = LITERATURE_DIR / "gene_NBK1116"
    if gene_reviews_dir.exists():
        gene_pdfs = list(gene_reviews_dir.glob("*.pdf"))
        logger.info(f"Found {len(gene_pdfs)} GeneReviews chapters")
        pdf_files.extend(gene_pdfs)
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {LITERATURE_DIR}")
        logger.info("Please add medical books (PDF) to the literature directory")
        return []
    
    logger.info(f"Total PDFs to process: {len(pdf_files)}")
    all_documents = []
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        if idx % 50 == 0:
            logger.info(f"Progress: {idx}/{len(pdf_files)} PDFs processed...")
        
        text = extract_text_from_pdf(pdf_path)
        
        if not text or len(text) < 100:  # Skip very short/empty texts
            continue
        
        chunks = chunk_text(text)
        
        for i, chunk in enumerate(chunks):
            document = {
                "source": pdf_path.name,
                "chunk_id": i,
                "text": chunk,
                "type": "genereviews" if "gene_NBK1116" in str(pdf_path) else "book"
            }
            all_documents.append(document)
    
    logger.info(f"Total book/chapter chunks: {len(all_documents)}")
    return all_documents


def process_pubmed_xml(xml_path: Path) -> List[Dict]:
    """Process PubMed XML articles"""
    logger.info(f"Processing PubMed XML: {xml_path.name}")
    
    try:
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        documents = []
        
        for article in root.findall(".//PubmedArticle"):
            pmid_elem = article.find(".//PMID")
            title_elem = article.find(".//ArticleTitle")
            abstract_elem = article.find(".//AbstractText")
            
            pmid = pmid_elem.text if pmid_elem is not None else "unknown"
            title = title_elem.text if title_elem is not None else ""
            abstract = abstract_elem.text if abstract_elem is not None else ""
            
            if title or abstract:
                combined_text = f"{title}\n\n{abstract}"
                
                document = {
                    "source": f"PubMed:{pmid}",
                    "chunk_id": 0,
                    "text": combined_text,
                    "type": "article",
                    "pmid": pmid
                }
                documents.append(document)
        
        logger.info(f"  → Processed {len(documents)} articles")
        return documents
    
    except Exception as e:
        logger.error(f"Error processing PubMed XML: {e}")
        return []


def main():
    """Main book processing workflow"""
    logger.info("=== Medical Literature Processing ===")
    
    all_documents = []
    
    # Process PDF books and GeneReviews chapters
    book_docs = process_books()
    all_documents.extend(book_docs)
    
    # Process ALL PubMed XML files (not just pubmed_*.xml pattern)
    logger.info("\nProcessing research paper XMLs...")
    xml_files = list(LITERATURE_DIR.glob("*.xml"))
    logger.info(f"Found {len(xml_files)} XML files")
    
    for xml_file in xml_files:
        article_docs = process_pubmed_xml(xml_file)
        all_documents.extend(article_docs)
    
    if not all_documents:
        logger.warning("No documents processed!")
        logger.info("\nTo add data:")
        logger.info("1. Add PDF books to: src/data/raw/literature/")
        logger.info("2. Run download_comprehensive_literature.py to get research papers")
        return
    
    # Save processed documents
    output_path = PROCESSED_DIR / "literature_documents.json"
    logger.info(f"\nSaving {len(all_documents)} documents to JSON...")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_documents, f, indent=2, ensure_ascii=False)
    
    # Statistics
    book_count = sum(1 for d in all_documents if d['type'] == 'book')
    gene_count = sum(1 for d in all_documents if d['type'] == 'genereviews')
    article_count = sum(1 for d in all_documents if d['type'] == 'article')
    
    logger.info(f"\n✓ Saved {len(all_documents)} documents to {output_path}")
    logger.info(f"  Medical Books: {book_count}")
    logger.info(f"  GeneReviews Chapters: {gene_count}")
    logger.info(f"  Research Articles: {article_count}")
    logger.info(f"\nNext step: python src/rag/rag_system.py")


if __name__ == "__main__":
    main()
