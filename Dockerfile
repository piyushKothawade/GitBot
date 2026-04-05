# ── Dockerfile ────────────────────────────────────────────────────────────────
# Deploys the FastAPI backend to Hugging Face Spaces (Docker SDK).
#
# HF Spaces Docker requirements:
#   - Must listen on port 7860
#   - Must have a CMD that starts the server
#   - Secrets (env vars) are injected via Space Settings → Secrets
#
# Build locally:
#   docker build -t gitlab-chatbot-backend .
#   docker run -p 7860:7860 \
#     -e GEMINI_API_KEY=... \
#     -e JINA_API_KEY=... \
#     -v $(pwd)/data:/app/data \
#     gitlab-chatbot-backend

FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY pipeline/ ./pipeline/
COPY scraper/  ./scraper/
COPY app.py    .

# Copy pre-built ChromaDB vector store
# ⚠ You must run `python -m pipeline.ingest` locally first,
#   then include data/chroma/ in your HF repo (via Git LFS).
COPY data/chroma/ ./data/chroma/

# HF Spaces requires port 7860
ENV PORT=7860

# Allow frontend origin (set to your Vercel URL after deployment)
ENV CORS_ORIGINS="http://localhost:3000,https://your-app.vercel.app"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
