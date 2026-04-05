"""
backend/llm.py
--------------
Thin wrapper around the Gemini API (google-genai SDK).
Handles:
  - Standard (non-streaming) chat completions
  - Streaming completions (yields text chunks for SSE)
  - Guardrail pre-check (fast relevance classification)
  - Graceful error handling with typed exceptions

Why Gemini Flash?
  - Free tier: 1,500 requests/day, 1M tokens/min
  - Fast enough for interactive chat (low latency)
  - Strong instruction-following for structured RAG responses

Environment variables:
    GEMINI_API_KEY   Required.
"""

import json
import os
import logging
from typing import Generator

from google import genai
from google.genai import types

from backend.prompts import SYSTEM_PROMPT, build_rag_prompt, build_guardrail_prompt

log = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
CHAT_MODEL     = "gemini-2.5-flash"
GUARD_MODEL    = "gemini-2.5-flash"


class LLMError(Exception):
    """Raised when the Gemini API returns an error."""
    pass


class OffTopicError(Exception):
    """Raised when the guardrail classifier rejects the query."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _get_client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise LLMError(
            "GEMINI_API_KEY not set. Export it before running:\n"
            "  export GEMINI_API_KEY=your_key"
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def _build_contents(messages: list[dict]) -> list[types.Content]:
    """Convert our message dicts to google-genai Content objects."""
    contents = []
    for msg in messages:
        role = msg["role"]
        # Gemini uses "model" not "assistant"
        if role == "assistant":
            role = "model"
        parts = [types.Part(text=p["text"]) for p in msg["parts"]]
        contents.append(types.Content(role=role, parts=parts))
    return contents


# ── Guardrail ─────────────────────────────────────────────────────────────────

def check_relevance(query: str) -> None:
    """
    Run a fast relevance check on the user query.
    Raises OffTopicError if the query is clearly off-topic.
    Fails open — if classifier errors, the query is allowed through.
    """
    if not GEMINI_API_KEY:
        return  # Skip guardrail in dev mode

    try:
        client = _get_client()
        prompt = build_guardrail_prompt(query)

        response = client.models.generate_content(
            model=GUARD_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=64,
            ),
        )
        raw = response.text.strip()

        # Strip markdown fences if model wraps in ```json ... ```
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)

        if not result.get("relevant", True):
            reason = result.get(
                "reason",
                "Query is outside the scope of GitLab's Handbook and Direction pages."
            )
            raise OffTopicError(reason)

    except OffTopicError:
        raise
    except Exception as e:
        log.warning(f"Guardrail check failed (fail-open): {e}")


# ── Standard response ─────────────────────────────────────────────────────────

def chat(
    query: str,
    chunks: list[dict],
    history: list[dict],
) -> str:
    """
    Generate a full RAG response and return the complete text.

    Args:
        query:   Current user question
        chunks:  Retrieved context from Retriever
        history: Prior conversation turns

    Returns:
        Assistant response as a string
    """
    client = _get_client()
    messages = build_rag_prompt(query, chunks, history)
    contents = _build_contents(messages)

    try:
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                top_p=0.8,
                max_output_tokens=1024,
            ),
        )
        return response.text
    except Exception as e:
        log.error(f"Gemini chat error: {e}")
        raise LLMError(f"LLM generation failed: {e}") from e


# ── Streaming response ────────────────────────────────────────────────────────

def chat_stream(
    query: str,
    chunks: list[dict],
    history: list[dict],
) -> Generator[str, None, None]:
    """
    Stream the RAG response token-by-token.
    Yields text chunks as they arrive from Gemini.
    Consumed by the FastAPI SSE endpoint in main.py.

    Args:
        query:   Current user question
        chunks:  Retrieved context from Retriever
        history: Prior conversation turns

    Yields:
        String fragments of the assistant response
    """
    client = _get_client()
    messages = build_rag_prompt(query, chunks, history)
    contents = _build_contents(messages)

    try:
        for chunk in client.models.generate_content_stream(
            model=CHAT_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                top_p=0.8,
                max_output_tokens=1024,
            ),
        ):
            if chunk.text:
                yield chunk.text
    except Exception as e:
        log.error(f"Gemini stream error: {e}")
        raise LLMError(f"LLM streaming failed: {e}") from e
