"""
pipeline/ingest.py
------------------
Reads chunk files from data/chunks/, generates embeddings via the
Jina Embeddings API, and upserts them into a local ChromaDB vector store.

Why Jina embeddings?
  - Much higher rate limits than Gemini (no 'too many requests' errors)
  - jina-embeddings-v4: 3.8B param model, SOTA on retrieval benchmarks
  - Task-specific adapters: retrieval.passage for docs, retrieval.query for search
  - 2048-dim embeddings with Matryoshka support (truncatable to 128)
  - OpenAI-compatible API format — easy to swap later if needed

ChromaDB is stored locally under data/chroma/ — no external service needed.

Run:
    JINA_API_KEY=your_key python -m pipeline.ingest

Environment variables:
    JINA_API_KEY   Required. Get one free at jina.ai
    BATCH_SIZE     Optional. Chunks per embedding API call (default: 50)
"""

import json
import os
import time
import logging
from pathlib import Path

import chromadb
import requests

# ── Config ────────────────────────────────────────────────────────────────────

CHUNK_DIR   = Path("data/chunks")
CHROMA_DIR  = Path("data/chroma")
COLLECTION  = "gitlab_docs"

JINA_API_KEY  = os.environ.get("JINA_API_KEY", "")
EMBED_MODEL   = "jina-embeddings-v4"
EMBED_URL     = "https://api.jina.ai/v1/embeddings"
DIMENSIONS    = 1024   # Matryoshka: 128 | 256 | 512 | 1024 | 2048
                       # 1024 is a good balance of quality vs. storage

BATCH_SIZE    = int(os.environ.get("BATCH_SIZE", "50"))
REQUEST_DELAY = 2.0    # Seconds between API calls (2s = 30 req/min, well within Jina limits)
MAX_RETRIES   = 5
RETRY_BACKOFF = 2.0    # Exponential backoff multiplier for 429 errors

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Call Jina /v1/embeddings for a batch of document texts.
    Uses task='retrieval.passage' — optimised for indexing content.
    Returns a list of embedding vectors (one per text).
    Retries with exponential backoff on rate limit (429) errors.
    """
    if not JINA_API_KEY:
        raise ValueError(
            "JINA_API_KEY not set. Export it before running:\n"
            "  export JINA_API_KEY=your_key\n"
            "  Get a free key at: https://jina.ai"
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {JINA_API_KEY}",
    }
    payload = {
        "model": EMBED_MODEL,
        "task": "retrieval.passage",   # For document indexing
        "dimensions": DIMENSIONS,
        "input": [{"text": t} for t in texts],
    }

    retry_delay = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(EMBED_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                if attempt < MAX_RETRIES - 1:
                    log.warning(
                        f"  Rate limited (429). Retrying in {retry_delay:.1f}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= RETRY_BACKOFF
                    continue
            raise


# ── ChromaDB setup ────────────────────────────────────────────────────────────

def get_collection() -> chromadb.Collection:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


# ── Ingestion ─────────────────────────────────────────────────────────────────

def load_all_chunks() -> list[dict]:
    """Load every chunk from data/chunks/ into a flat list."""
    all_chunks = []
    for path in sorted(CHUNK_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            chunks = json.load(f)
        all_chunks.extend(chunks)
    return all_chunks


def ingest() -> None:
    chunks = load_all_chunks()
    log.info(f"Loaded {len(chunks)} chunks from {CHUNK_DIR}/")

    collection = get_collection()
    existing_ids = set(collection.get()["ids"])
    log.info(f"ChromaDB already has {len(existing_ids)} vectors.")

    # Filter to only new chunks
    new_chunks = [c for c in chunks if c["chunk_id"] not in existing_ids]
    log.info(f"{len(new_chunks)} new chunks to embed and ingest.")

    if not new_chunks:
        log.info("Nothing to do — collection is up to date.")
        return

    # Process in batches
    for batch_start in range(0, len(new_chunks), BATCH_SIZE):
        batch = new_chunks[batch_start : batch_start + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        log.info(
            f"  Embedding batch {batch_start // BATCH_SIZE + 1} "
            f"({len(batch)} chunks)..."
        )

        try:
            embeddings = embed_batch(texts)
        except Exception as e:
            log.error(f"  Embedding failed: {e}. Skipping batch.")
            continue

        # Prepare ChromaDB upsert
        ids       = [c["chunk_id"] for c in batch]
        metadatas = [
            {
                "url":          c["url"],
                "title":        c["title"][:200],
                "source":       c["source"],
                "chunk_index":  c["chunk_index"],
                "total_chunks": c["total_chunks"],
                # ChromaDB metadata values must be str/int/float/bool
                "headings": "; ".join(c.get("headings", [])[:3]),
            }
            for c in batch
        ]
        documents = texts

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        log.info(f"  ✓ Upserted {len(batch)} vectors.")
        time.sleep(REQUEST_DELAY)

    final_count = collection.count()
    log.info(f"\nDone. ChromaDB collection '{COLLECTION}' now has {final_count} vectors.")


if __name__ == "__main__":
    ingest()