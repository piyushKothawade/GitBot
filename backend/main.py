"""
backend/main.py
---------------
FastAPI application — the bridge between the React frontend (Phase 3)
and the RAG pipeline + LLM (Phase 1 & 2).

Endpoints:
    POST /chat          Full response (non-streaming)
    POST /chat/stream   Server-Sent Events streaming response
    GET  /health        Health check

Run locally:
    uvicorn backend.main:app --reload --port 8000

Environment variables:
    GEMINI_API_KEY   Required for LLM
    JINA_API_KEY     Required for query-time embeddings
    CORS_ORIGINS     Comma-separated allowed origins (default: localhost:3000)
"""

import json
import logging
import os
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.llm import chat, chat_stream, check_relevance, LLMError, OffTopicError
from pipeline.retriever import Retriever

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="GitLab Chatbot API",
    description="RAG-powered chatbot over GitLab Handbook and Direction pages",
    version="1.0.0",
)

# CORS — allow the React frontend to call this API
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Retriever singleton ───────────────────────────────────────────────────────
# Initialised once at startup to avoid reloading ChromaDB on every request

retriever: Retriever | None = None

@app.on_event("startup")
async def startup():
    global retriever
    try:
        retriever = Retriever()
        log.info("Retriever initialised successfully.")
    except FileNotFoundError as e:
        log.error(f"Retriever init failed: {e}")
        log.error("Run `python -m pipeline.ingest` before starting the server.")


# ── Request / Response schemas ────────────────────────────────────────────────

class Turn(BaseModel):
    role: str           # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    history: list[Turn] = Field(default_factory=list)
    top_k: int = Field(default=6, ge=1, le=12)
    source_filter: str | None = Field(
        default=None,
        description="Filter results by source: 'handbook' | 'direction' | null"
    )
    use_hybrid: bool = Field(
        default=False,
        description="Use hybrid search across both sources (overrides source_filter)"
    )


class SourceChunk(BaseModel):
    title: str
    url: str
    source: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    query: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _retrieve(req: ChatRequest) -> list[dict]:
    """Run retrieval based on request parameters."""
    if retriever is None:
        raise HTTPException(
            status_code=503,
            detail="Retriever not initialised. Ensure ChromaDB is populated."
        )
    if req.use_hybrid:
        return retriever.search_hybrid(req.query, top_k=req.top_k)
    return retriever.search(req.query, top_k=req.top_k, source_filter=req.source_filter)


def _dedupe_sources(chunks: list[dict]) -> list[SourceChunk]:
    """Deduplicate sources by URL for the response metadata."""
    seen_urls = set()
    sources = []
    for chunk in chunks:
        if chunk["url"] not in seen_urls:
            seen_urls.add(chunk["url"])
            sources.append(SourceChunk(
                title=chunk["title"],
                url=chunk["url"],
                source=chunk["source"],
                score=chunk["score"],
            ))
    return sources


def _history_to_dicts(history: list[Turn]) -> list[dict]:
    return [{"role": t.role, "content": t.content} for t in history]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "retriever_ready": retriever is not None,
        "collection_size": retriever.collection.count() if retriever else 0,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Non-streaming chat endpoint.
    Returns the full answer + source metadata in one response.
    Used as fallback when SSE isn't available.
    """
    # Guardrail check
    try:
        check_relevance(req.query)
    except OffTopicError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "off_topic",
                "message": (
                    f"I can only answer questions about GitLab's Handbook and Direction pages. "
                    f"{e.reason}"
                )
            }
        )

    # Retrieve context
    chunks = _retrieve(req)

    # Generate response
    try:
        answer = chat(
            query=req.query,
            chunks=chunks,
            history=_history_to_dicts(req.history),
        )
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ChatResponse(
        answer=answer,
        sources=_dedupe_sources(chunks),
        query=req.query,
    )


@app.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    The frontend receives tokens as they arrive from Gemini.

    SSE event format:
        data: {"type": "token",   "content": "Hello"}
        data: {"type": "sources", "content": [...]}
        data: {"type": "done"}
        data: {"type": "error",   "content": "..."}
    """
    # Guardrail check
    try:
        check_relevance(req.query)
    except OffTopicError as e:
        # Return error as an SSE event so frontend handles it gracefully
        async def error_stream():
            payload = json.dumps({
                "type": "error",
                "content": (
                    f"I can only answer questions about GitLab's Handbook "
                    f"and Direction pages. {e.reason}"
                )
            })
            yield f"data: {payload}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # Retrieve context
    chunks = _retrieve(req)
    sources = _dedupe_sources(chunks)
    history = _history_to_dicts(req.history)

    async def generate() -> AsyncGenerator[str, None]:
        try:
            # Stream tokens
            for text_chunk in chat_stream(req.query, chunks, history):
                payload = json.dumps({"type": "token", "content": text_chunk})
                yield f"data: {payload}\n\n"

            # After streaming completes, send source metadata
            sources_payload = json.dumps({
                "type": "sources",
                "content": [s.model_dump() for s in sources],
            })
            yield f"data: {sources_payload}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except LLMError as e:
            payload = json.dumps({"type": "error", "content": str(e)})
            yield f"data: {payload}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
