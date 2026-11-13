"""
AI Court of India — FastAPI Application Entry Point.
Provides REST and SSE endpoints for courtroom simulation, Case Packet upload,
and judicial decision generation.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure backend root and project root are in sys.path
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent
_repo_root = _backend_dir.parent

for d in [str(_backend_dir), str(_repo_root)]:
    if d not in sys.path:
        sys.path.insert(0, d)

from dotenv import load_dotenv

_env_path = _repo_root / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=False)
else:
    load_dotenv(override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.comparison_routes import router as comparison_router
from app.api.court_routes import router as court_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_court_app")

app = FastAPI(
    title="AI Court of India API",
    description="Autonomous Judicial Reasoning & Courtroom Simulation Engine",
    version="1.0.0",
)

# Configure CORS to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(court_router, prefix="/api/court", tags=["court"])
app.include_router(comparison_router, prefix="/api", tags=["comparison"])
app.include_router(comparison_router, prefix="/api/court", tags=["comparison"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint for container and client validation."""
    return {
        "status": "healthy",
        "service": "AI Court of India API",
        "version": "1.0.0",
    }


@app.get("/api/health/llm")
async def llm_health_check():
    """
    Diagnostic endpoint exposing the active LLM brain and its connectivity status.
    Guarantees zero API keys, secrets, or credential leakage.
    """
    from app.core.llm_provider import LLMConfig, LLMProvider

    health_data = LLMProvider.check_health()
    safe_data = {
        "provider": health_data.get("provider", LLMConfig.provider()),
        "model": health_data.get("model", ""),
        "available": health_data.get("available", False),
        "details": health_data.get("details", ""),
    }
    if "error" in health_data:
        safe_data["error"] = health_data["error"]
    if "model_found" in health_data:
        safe_data["model_found"] = health_data["model_found"]
    return safe_data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
