"""
main.py — FastAPI entrypoint. Initialises DB, ensures directories, registers routes.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db import init_db
from app.utils import get_logger, log_memory, ensure_dirs
from app.config import RAW_PDF_DIR, LANCEDB_DIR, REPORTS_DIR, TEMPLATES_DIR, DUCKDB_PATH

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Document Intelligence System starting ===")
    ensure_dirs(RAW_PDF_DIR, LANCEDB_DIR, REPORTS_DIR, TEMPLATES_DIR, DUCKDB_PATH.parent)
    init_db()
    log_memory("startup")
    logger.info("=== Startup complete ===")
    yield
    logger.info("=== Shutting down ===")


app = FastAPI(
    title="Document Intelligence System",
    description="Private, local document assistant. Runs entirely on NVIDIA Jetson Xavier.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["System"])
async def health():
    """Basic health check — returns system status and current memory usage."""
    from app.utils import get_memory_usage_gb, get_available_memory_gb
    return {
        "status": "ok",
        "version": "0.1.0",
        "memory_used_gb": get_memory_usage_gb(),
        "memory_available_gb": get_available_memory_gb(),
    }
