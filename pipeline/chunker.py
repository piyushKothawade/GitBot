"""
pipeline/chunker.py
-------------------
Reads raw pages from data/raw/, splits them into overlapping chunks
suitable for embedding, and writes results to data/chunks/.

Chunking strategy:
  - Split on double-newlines (paragraph boundaries) first
  - If a paragraph exceeds MAX_TOKENS, split further on sentence boundaries
  - Sliding window overlap of OVERLAP_TOKENS between consecutive chunks
  - Each chunk carries metadata: url, title, source, headings, chunk_index

Run:
    python -m pipeline.chunker
"""

import json
import re
import logging
from pathlib import Path
from dataclasses import dataclass, asdict

# ── Config ────────────────────────────────────────────────────────────────────

RAW_DIR    = Path("data/raw")
CHUNK_DIR  = Path("data/chunks")

MAX_TOKENS   = 400    # Target max tokens per chunk
OVERLAP_TOKENS = 80   # Token overlap between consecutive chunks

# Rough approximation: 1 token ≈ 4 chars (good enough without a tokenizer)
AVG_CHARS_PER_TOKEN = 4

MAX_CHARS    = MAX_TOKENS * AVG_CHARS_PER_TOKEN       # 1600 chars
OVERLAP_CHARS = OVERLAP_TOKENS * AVG_CHARS_PER_TOKEN  # 320 chars

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    chunk_id: str        # "<url_hash>_<index>"
    url: str
    title: str
    source: str          # "handbook" | "direction"
    headings: list[str]
    text: str
    chunk_index: int
    total_chunks: int    # Filled in after all chunks are produced


# ── Splitting helpers ─────────────────────────────────────────────────────────

def split_sentences(text: str) -> list[str]:
    """Rough sentence splitter (no NLTK dependency)."""
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def split_into_chunks(text: str) -> list[str]:
    """
    Split text into overlapping chunks of ~MAX_CHARS.
    1. Split on paragraph boundaries (double newline).
    2. If a paragraph is still too long, split on sentence boundaries.
    3. Greedily accumulate into windows with OVERLAP_CHARS carried forward.
    """
    # Step 1: paragraph split
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]

    # Step 2: further split oversized paragraphs
    segments: list[str] = []
    for para in paragraphs:
        if len(para) <= MAX_CHARS:
            segments.append(para)
        else:
            sentences = split_sentences(para)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) + 1 <= MAX_CHARS:
                    current = (current + " " + sent).strip()
                else:
                    if current:
                        segments.append(current)
                    current = sent
            if current:
                segments.append(current)

    # Step 3: sliding window with overlap
    chunks: list[str] = []
    current_chunk = ""
    overlap_carry = ""

    for seg in segments:
        candidate = (overlap_carry + "\n\n" + seg).strip() if overlap_carry else seg

        if len(current_chunk) + len(candidate) + 2 <= MAX_CHARS:
            current_chunk = (current_chunk + "\n\n" + candidate).strip() if current_chunk else candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
                # Carry the tail as overlap
                overlap_carry = current_chunk[-OVERLAP_CHARS:].strip()
            current_chunk = (overlap_carry + "\n\n" + seg).strip() if overlap_carry else seg
            overlap_carry = ""

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# ── Main ──────────────────────────────────────────────────────────────────────

def chunk_all() -> None:
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    raw_files = list(RAW_DIR.glob("*.json"))
    log.info(f"Found {len(raw_files)} raw pages to chunk.")

    total_chunks = 0

    for raw_path in raw_files:
        with open(raw_path, encoding="utf-8") as f:
            page = json.load(f)

        url     = page["url"]
        title   = page["title"]
        source  = page["source"]
        headings = page.get("headings", [])
        content  = page["content"]

        if not content.strip():
            continue

        url_hash = raw_path.stem   # Already the md5 hash used as filename
        chunk_texts = split_into_chunks(content)

        chunks: list[Chunk] = []
        for i, text in enumerate(chunk_texts):
            chunk = Chunk(
                chunk_id=f"{url_hash}_{i}",
                url=url,
                title=title,
                source=source,
                headings=headings[:5],  # Top headings for context
                text=text,
                chunk_index=i,
                total_chunks=len(chunk_texts),
            )
            chunks.append(chunk)

        # Write all chunks for this page to one file
        out_path = CHUNK_DIR / f"{url_hash}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in chunks], f, ensure_ascii=False, indent=2)

        total_chunks += len(chunks)
        log.info(f"  {url_hash} → {len(chunks)} chunks  ({title[:60]})")

    log.info(f"\nDone. {total_chunks} chunks across {len(raw_files)} pages → {CHUNK_DIR}/")


if __name__ == "__main__":
    chunk_all()
