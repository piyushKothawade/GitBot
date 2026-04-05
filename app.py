"""
app.py
------
Hugging Face Spaces entrypoint.
HF Spaces runs this file directly — it must expose a FastAPI/Gradio
app at the module level. We simply re-export our existing FastAPI app.

The Space is configured as an SDK="docker" Space (see Dockerfile),
so uvicorn is launched from the Dockerfile CMD, not by HF's runner.
This file exists purely for completeness / local fallback.
"""

from backend.main import app  # noqa: F401 — re-exported for uvicorn
