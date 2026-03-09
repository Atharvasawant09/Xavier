"""
main.py — FastAPI application entry point for DocInt.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routers import documents, query, health
from app.utils import get_logger, log_memory
from app.db import get_conn

logger = get_logger("main")

app = FastAPI(
    title       = "DocInt — Document Intelligence API",
    description = "PDF ingestion, semantic retrieval, and LLM-powered Q&A.",
    version     = "1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Global Error Handlers ─────────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code = 404,
        content     = {"error": "Not found", "path": str(request.url)},
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error(f"Unhandled error on {request.url}: {exc}")
    return JSONResponse(
        status_code = 500,
        content     = {"error": "Internal server error"},
    )

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(query.router)

# ── Startup / Shutdown ────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("DocInt API starting up...")
    get_conn()          # initialise DuckDB + schema
    log_memory("startup")
    logger.info("DocInt API ready.")

@app.on_event("shutdown")
async def shutdown():
    logger.info("DocInt API shutting down.")
