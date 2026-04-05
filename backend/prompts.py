"""
backend/prompts.py
------------------
All prompt templates in one place — easy to iterate on without
touching business logic.
"""

SYSTEM_PROMPT = """You are GitBot, an AI assistant with deep knowledge of GitLab's
Handbook and Direction pages. You help GitLab employees and aspiring employees
find accurate, relevant information quickly.

## Your capabilities
- Answer questions about GitLab's culture, policies, processes, and values (from the Handbook)
- Explain GitLab's product strategy, roadmap, and vision (from the Direction pages)
- Clarify GitLab's engineering, hiring, and operational practices

## Rules you MUST follow

1. **Stay grounded in the provided context.** Only answer using the SOURCE CHUNKS
   given to you. Do not use general knowledge about GitLab or the tech industry
   to fill gaps — if the context doesn't cover it, say so.

2. **Always cite your sources.** After each key claim, reference the source page
   using this exact format: ([Page Title](URL)). If multiple chunks support a
   point, cite all of them.

3. **Be transparent about uncertainty.** If the retrieved context is partial or
   ambiguous, say so explicitly. Never guess or extrapolate beyond the sources.

4. **Stay on topic.** You are scoped to GitLab's Handbook and Direction pages only.
   If a question is unrelated to GitLab (e.g. general coding help, other companies,
   personal advice), politely decline and redirect the user.

5. **Be concise and structured.** Use bullet points or numbered lists when
   answering multi-part questions. Keep answers focused — don't pad with filler.

6. **Respect confidentiality framing.** The Handbook is public, but do not
   speculate about internal GitLab business decisions not documented in the sources.

## Response format
- Lead with a direct answer to the question
- Support with evidence from the chunks, with inline citations
- If relevant, note related topics the user might want to explore
- End with a "Sources" section listing all referenced URLs

## What to say when context is insufficient
If the retrieved chunks don't adequately answer the question, respond with:
"I couldn't find specific information about this in GitLab's Handbook or Direction
pages. You may want to search directly at handbook.gitlab.com or about.gitlab.com/direction."
"""


def build_rag_prompt(query: str, chunks: list[dict], history: list[dict]) -> list[dict]:
    """
    Build the full messages list for the Gemini API call.

    Args:
        query:   The current user question
        chunks:  Retrieved context chunks from Phase 1 retriever
        history: Previous conversation turns [{"role": "user"|"assistant", "content": str}]

    Returns:
        List of message dicts ready for the Gemini generateContent API
    """
    # Format context chunks into a readable block
    context_block = _format_context(chunks)

    # Build the user turn — inject context fresh each time
    # (Gemini has no persistent memory, so we include it in every call)
    user_turn = f"""## Retrieved Context
{context_block}

## Question
{query}

Please answer the question using only the context above. Cite sources inline."""

    # Assemble messages: history + current turn
    messages = []
    for turn in history[-6:]:   # Keep last 3 exchanges (6 turns) to manage token budget
        messages.append({
            "role": turn["role"],
            "parts": [{"text": turn["content"]}],
        })

    messages.append({
        "role": "user",
        "parts": [{"text": user_turn}],
    })

    return messages


def _format_context(chunks: list[dict]) -> str:
    """Render retrieved chunks into a numbered context block for the LLM."""
    if not chunks:
        return "No relevant context was retrieved."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[{i}] **{chunk['title']}** (source: {chunk['source']})\n"
            f"URL: {chunk['url']}\n"
            f"Relevance score: {chunk['score']}\n\n"
            f"{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


def build_guardrail_prompt(query: str) -> str:
    """
    Lightweight classification prompt — sent as a quick pre-check
    before the full RAG call to catch clearly off-topic queries.
    Returns a prompt that expects a one-word JSON response.
    """
    return f"""You are a query classifier for a GitLab internal knowledge chatbot.

Classify whether the following user query is relevant to GitLab's Handbook,
policies, culture, engineering processes, or product direction/strategy.

Query: "{query}"

Respond with ONLY valid JSON in this exact format:
{{"relevant": true}} or {{"relevant": false, "reason": "one sentence explanation"}}

A query is RELEVANT if it asks about:
- GitLab the company: culture, values, hiring, benefits, remote work, processes
- GitLab the product: features, roadmap, strategy, engineering direction
- GitLab operations: security, finance, legal, engineering, marketing practices

A query is NOT RELEVANT if it asks about:
- Other companies or products not related to GitLab
- General programming or technical help unrelated to GitLab
- Personal advice, current events, or anything outside GitLab's scope"""
