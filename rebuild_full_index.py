"""
Rebuild ChromaDB with ALL 87,848 documents — supports resume after power loss.
Run: c:/python312/python.exe rebuild_full_index.py
"""
import shutil
import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

CHROMA_DIR = Path("src/data/embeddings/chroma")
PROGRESS_FILE = Path("src/data/embeddings/rebuild_progress.json")

import sys
sys.path.insert(0, "src")
from rag.rag_system import OrphaMindRAG

# Load all documents first
logger.info("Loading all 87,848 documents...")
rag = OrphaMindRAG()
documents = rag.load_priority_documents(max_chunks=87848)
total = len(documents)
logger.info(f"Loaded {total} documents")

# Check resume progress
start_batch = 0
if PROGRESS_FILE.exists():
    progress = json.loads(PROGRESS_FILE.read_text())
    saved_total = progress.get("total", 0)
    saved_batch = progress.get("last_completed_batch", -1)
    if saved_total == total and saved_batch >= 0:
        start_batch = saved_batch + 1
        already_done = start_batch * 500
        logger.info(f"Resuming from batch {start_batch} ({already_done}/{total} already indexed)")
    else:
        logger.info("Progress file mismatch — starting fresh")
        if CHROMA_DIR.exists():
            shutil.rmtree(CHROMA_DIR)
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        PROGRESS_FILE.unlink(missing_ok=True)
else:
    # Fresh start
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Starting fresh build")

# Re-init RAG after potential directory reset
rag = OrphaMindRAG()
rag._get_collection()

# Build in batches with progress checkpointing
import chromadb
batch_size = 500
total_batches = (total - 1) // batch_size + 1

for batch_idx in range(start_batch, total_batches):
    batch_start = batch_idx * batch_size
    batch = documents[batch_start: batch_start + batch_size]

    ids       = [f"doc_{batch_start + j}" for j in range(len(batch))]
    texts     = [d.get('text', '')[:1500] for d in batch]
    metadatas = [
        {
            'source':   str(d.get('source', 'unknown')),
            'doc_type': str(d.get('type',   'unknown')),
            'chunk_id': str(d.get('chunk_id', 0))
        }
        for d in batch
    ]

    rag.collection.add(ids=ids, documents=texts, metadatas=metadatas)

    # Save progress after every batch — safe to resume if power cuts
    PROGRESS_FILE.write_text(json.dumps({
        "total": total,
        "last_completed_batch": batch_idx,
        "docs_indexed": batch_start + len(batch)
    }))

    logger.info(f"  Batch {batch_idx + 1}/{total_batches} done ({batch_start + len(batch)}/{total})")

count = rag.collection.count()
logger.info(f"DONE — {count} documents in ChromaDB")
PROGRESS_FILE.unlink(missing_ok=True)  # Clean up progress file

# Quick test query
results = rag.query("muscle weakness elevated CK progressive childhood")
print("\n=== Sample query result ===")
for i, r in enumerate(results[:2], 1):
    print(f"{i}. [{r['type']}] {r['source']}")
    print(f"   {r['content'][:150]}...")
