"""
pipeline/retriever.py
---------------------
Query-time retrieval. Given a user question:
  1. Embed the question using jina-embeddings-v4 with task='retrieval.query'
  2. Query ChromaDB for the top-k most similar chunks
  3. Optionally re-rank by source diversity (handbook vs direction)
  4. Return structured results ready for the LLM context window

IMPORTANT: task='retrieval.query' at query time vs task='retrieval.passage'
at ingest time — Jina's task-specific LoRA adapters optimise each direction
separately, which meaningfully improves retrieval quality.

This module is imported by the chatbot backend in Phase 2.

Usage:
    from pipeline.retriever import Retriever

    r = Retriever()
    results = r.search("What is GitLab's paid time off policy?", top_k=5)
    for chunk in results:
        print(chunk["title"], chunk["url"])
        print(chunk["text"][:200])
"""

import os
import logging
import requests
from pathlib import Path

import chromadb

# ── Config ────────────────────────────────────────────────────────────────────

CHROMA_DIR    = Path("data/chroma")
COLLECTION    = "gitlab_docs"
JINA_API_KEY  = os.environ.get("JINA_API_KEY", "")
EMBED_MODEL   = "jina-embeddings-v4"
EMBED_URL     = "https://api.jina.ai/v1/embeddings"
DIMENSIONS    = 1024   # Must match the dimension used during ingest

log = logging.getLogger(__name__)


# ── Retriever ─────────────────────────────────────────────────────────────────

class Retriever:
    def __init__(self):
        if not CHROMA_DIR.exists():
            raise FileNotFoundError(
                f"ChromaDB not found at {CHROMA_DIR}. "
                "Run `python -m pipeline.ingest` first."
            )
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = client.get_collection(COLLECTION)
        log.info(f"Retriever ready. Collection has {self.collection.count()} vectors.")

    # ── Embedding ──────────────────────────────────────────────────────────────

    def _embed_query(self, text: str) -> list[float]:
        """
        Embed a single query string using Jina.
        Uses task='retrieval.query' — different LoRA adapter from ingestion,
        optimised for short questions rather than long document passages.
        """
        if not JINA_API_KEY:
            raise ValueError(
                "JINA_API_KEY not set. Export it before running:\n"
                "  export JINA_API_KEY=your_key"
            )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {JINA_API_KEY}",
        }
        payload = {
            "model": EMBED_MODEL,
            "task": "retrieval.query",   # Different adapter from ingest!
            "dimensions": DIMENSIONS,    # Must match ingest dimension
            "input": [{"text": text}],
        }

        resp = requests.post(EMBED_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    # ── Search ─────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 6,
        source_filter: str | None = None,   # "handbook" | "direction" | None
    ) -> list[dict]:
        """
        Semantic search over the vector store.

        Returns a list of dicts:
            {
                "chunk_id":    str,
                "text":        str,
                "url":         str,
                "title":       str,
                "source":      str,
                "headings":    str,
                "score":       float,   # cosine similarity (higher = better)
            }
        """
        query_embedding = self._embed_query(query)

        where_filter = {"source": source_filter} if source_filter else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        ids       = results["ids"][0]
        docs      = results["documents"][0]
        metas     = results["metadatas"][0]
        distances = results["distances"][0]

        for chunk_id, text, meta, dist in zip(ids, docs, metas, distances):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity score in [0, 1]
            score = 1 - (dist / 2)
            output.append({
                "chunk_id": chunk_id,
                "text":     text,
                "url":      meta.get("url", ""),
                "title":    meta.get("title", ""),
                "source":   meta.get("source", ""),
                "headings": meta.get("headings", ""),
                "score":    round(score, 4),
            })

        return output

    def search_hybrid(
        self,
        query: str,
        top_k: int = 6,
        handbook_weight: float = 0.6,
    ) -> list[dict]:
        """
        Balanced retrieval across both sources.
        Fetches top_k from each source separately, then merges and
        re-ranks by score, returning the best top_k overall.
        Useful when a query might span both handbook policy and direction strategy.
        """
        n_each = max(top_k, 4)

        handbook_results  = self.search(query, top_k=n_each, source_filter="handbook")
        direction_results = self.search(query, top_k=n_each, source_filter="direction")

        # Apply source weights
        for r in handbook_results:
            r["score"] *= handbook_weight
        for r in direction_results:
            r["score"] *= (1 - handbook_weight)

        combined = handbook_results + direction_results
        combined.sort(key=lambda x: x["score"], reverse=True)

        # Deduplicate by chunk_id
        seen = set()
        unique = []
        for r in combined:
            if r["chunk_id"] not in seen:
                seen.add(r["chunk_id"])
                unique.append(r)

        return unique[:top_k]


# ── Quick CLI test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) or "What is GitLab's mission?"
    retriever = Retriever()
    results = retriever.search(query, top_k=3)
    print(f"\nTop results for: '{query}'\n{'─'*60}")
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r['title']} (score: {r['score']})")
        print(f"    URL: {r['url']}")
        print(f"    {r['text'][:300]}...")