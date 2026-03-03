"""
OrphaMind RAG System
ChromaDB built-in embeddings (ONNX) + Gemini for reasoning
No torch/torchvision dependency — no API calls for embeddings
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CHROMA_DIR = DATA_DIR / "embeddings" / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

PRIORITY_DISEASES = [
    "duchenne", "huntington", "cystic fibrosis", "marfan", "wilson",
    "gaucher", "fabry", "pompe", "niemann", "tay-sachs", "phenylketonuria",
    "turner", "klinefelter", "fragile x", "prader-willi", "angelman",
    "tuberous sclerosis", "neurofibromatosis", "ehlers-danlos",
    "osteogenesis", "achondroplasia", "alport", "amyloidosis",
    "myasthenia gravis", "hemophilia", "von willebrand", "sickle cell",
    "thalassemia", "porphyria", "glycogen storage", "mucopolysaccharidosis",
    "mitochondrial", "lysosomal", "fatty acid oxidation", "spinal muscular",
    "friedreich ataxia", "charcot marie", "fanconi", "batten disease",
    "krabbe", "metachromatic", "canavan", "alexander disease"
]

class OrphaMindRAG:
    """RAG system using ChromaDB built-in ONNX embeddings (no torch required)"""

    def __init__(self):
        logger.info("Initializing OrphaMind RAG system...")

        # PersistentClient saves to disk automatically
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))

        # Built-in embedding function — uses ONNX runtime, zero extra dependencies
        self.ef = DefaultEmbeddingFunction()

        self.collection = None
        logger.info("✓ ChromaDB initialized (built-in ONNX embeddings — no torch needed)")

    def _get_collection(self):
        """Get or create the ChromaDB collection"""
        self.collection = self.client.get_or_create_collection(
            name="orphamind_literature",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )
        return self.collection

    def load_priority_documents(self, max_chunks: int = 5000) -> List[Dict]:
        """Load priority disease documents from processed literature"""
        literature_file = PROCESSED_DIR / "literature_documents.json"

        if not literature_file.exists():
            logger.error(f"❌ Not found: {literature_file}")
            logger.error("Run: python src/data_processing/process_books.py first")
            return []

        logger.info(f"Loading up to {max_chunks} priority documents...")

        with open(literature_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        priority_docs, other_docs = [], []

        for doc in data:
            text = doc.get('text', '').lower()
            source = doc.get('source', '').lower()
            is_priority = any(d in text or d in source for d in PRIORITY_DISEASES)
            (priority_docs if is_priority else other_docs).append(doc)

        selected = priority_docs[:max_chunks]
        remaining = max_chunks - len(selected)
        if remaining > 0:
            selected.extend(other_docs[:remaining])

        logger.info(
            f"✓ Selected {len(selected)} chunks "
            f"({min(len(priority_docs), max_chunks)} priority + "
            f"{max(0, len(selected) - min(len(priority_docs), max_chunks))} other)"
        )
        return selected

    def build_vector_store(self, documents: List[Dict]):
        """Build ChromaDB vector store in batches — entirely free, no API calls"""
        if not documents:
            logger.error("No documents provided!")
            return

        self._get_collection()
        total = len(documents)
        logger.info(f"Building vector store for {total} documents (ONNX embeddings, no API cost)...")

        batch_size = 500
        for batch_start in range(0, total, batch_size):
            batch = documents[batch_start: batch_start + batch_size]

            ids = [f"doc_{batch_start + j}" for j in range(len(batch))]
            texts = [d.get('text', '')[:1500] for d in batch]  # limit chunk size
            metadatas = [
                {
                    'source': str(d.get('source', 'unknown')),
                    'doc_type': str(d.get('type', 'unknown')),
                    'chunk_id': str(d.get('chunk_id', 0))
                }
                for d in batch
            ]

            self.collection.add(ids=ids, documents=texts, metadatas=metadatas)
            batch_num = batch_start // batch_size + 1
            total_batches = (total - 1) // batch_size + 1
            logger.info(f"  Batch {batch_num}/{total_batches} done ({batch_start + len(batch)}/{total})")

        count = self.collection.count()
        logger.info(f"✅ Vector store built! {count} documents indexed in ChromaDB")
        logger.info(f"   Saved to: {CHROMA_DIR}")

    def load_existing_vector_store(self) -> bool:
        """Load existing ChromaDB collection if it has data"""
        try:
            self._get_collection()
            count = self.collection.count()
            if count > 0:
                logger.info(f"✅ Loaded existing vector store: {count} documents")
                return True
            logger.info("Vector store exists but is empty — need to build it")
            return False
        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")
            return False

    def query(self, query_text: str, k: int = 5) -> List[Dict]:
        """Semantic search over the medical literature vector store"""
        if not self.collection:
            logger.error("Collection not loaded!")
            return []

        n = min(k, self.collection.count())
        if n == 0:
            return []

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n
        )

        output = []
        for i, doc_text in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            dist = results['distances'][0][i] if results.get('distances') else 0.0
            output.append({
                'content': doc_text,
                'source': meta.get('source', 'unknown'),
                'type': meta.get('doc_type', 'unknown'),
                'score': round(float(dist), 4)
            })
        return output

    # Backward compatibility alias
    def search(self, query: str, k: int = 5) -> List[Dict]:
        return self.query(query, k)


def main():
    rag = OrphaMindRAG()

    # If vector store already built, just run a test query
    if rag.load_existing_vector_store():
        logger.info("\nRunning test query...")
        results = rag.query("muscle weakness elevated CK early onset childhood")
        print("\n=== Test Results ===")
        for i, r in enumerate(results[:3], 1):
            print(f"\n{i}. [{r['type']}] {r['source']}")
            print(f"   {r['content'][:200]}...")
        print("\n✅ RAG is ready! Run: python src/api/main.py")
        return

    print("\n" + "=" * 50)
    print("  OrphaMind RAG Builder")
    print("=" * 50)
    print("\nHow many documents to embed? (All FREE — local ONNX embeddings)")
    print("  S —  1,000 docs  ~  <1 min  — quick smoke test")
    print("  M —  5,000 docs  ~  1-2 min — good for demo")
    print("  L — 10,000 docs  ~  3-4 min — comprehensive")
    print("  F — 87,848 docs  ~ 15-20 min — full coverage")
    print("\n  Recommendation: M")

    choice = input("\nEnter choice (S/M/L/F): ").strip().upper()
    chunk_map = {'S': 1000, 'M': 5000, 'L': 10000, 'F': 87848}
    max_chunks = chunk_map.get(choice, 5000)

    documents = rag.load_priority_documents(max_chunks=max_chunks)
    if not documents:
        logger.error("No documents loaded. Run process_books.py first!")
        return

    rag.build_vector_store(documents)

    # Test after build
    logger.info("\nTesting RAG system...")
    results = rag.query("duchenne muscular dystrophy symptoms treatment")
    print("\n=== Test Results ===")
    for i, r in enumerate(results[:3], 1):
        print(f"\n{i}. [{r['type']}] {r['source']}")
        print(f"   {r['content'][:200]}...")

    print("\n✅ RAG system ready! Run: python src/api/main.py")


if __name__ == "__main__":
    main()
