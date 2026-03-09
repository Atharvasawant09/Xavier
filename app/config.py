"""
config.py — Central configuration for Document Intelligence System.
All tuneable constants live here. Never hardcode paths or values elsewhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Base Paths ─────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent.parent
DATA_DIR        = Path(os.getenv("DATA_DIR",        str(BASE_DIR / "data")))
RAW_PDF_DIR     = Path(os.getenv("RAW_PDF_DIR",     str(DATA_DIR / "raw_pdfs")))
LANCEDB_DIR     = Path(os.getenv("LANCEDB_DIR",     str(DATA_DIR / "lancedb")))
DUCKDB_PATH     = Path(os.getenv("DUCKDB_PATH",     str(DATA_DIR / "duckdb" / "docint.db")))
REPORTS_DIR     = Path(os.getenv("REPORTS_DIR",     str(DATA_DIR / "reports")))
TEMPLATES_DIR   = Path(os.getenv("TEMPLATES_DIR",   str(BASE_DIR / "templates")))
MODEL_PATH      = Path(os.getenv("MODEL_PATH",      "/mnt/ssd/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf"))

# ── Chunking ───────────────────────────────────────────────────────────────────
CHUNK_SIZE          = int(os.getenv("CHUNK_SIZE",           "300"))
CHUNK_OVERLAP       = int(os.getenv("CHUNK_OVERLAP",        "50"))
MAX_CHUNKS_PER_PDF  = int(os.getenv("MAX_CHUNKS_PER_PDF",   "2000"))

# ── Ingestion Limits ───────────────────────────────────────────────────────────
MAX_PDF_PAGES       = int(os.getenv("MAX_PDF_PAGES",     "100"))
MIN_CHUNK_TOKENS    = int(os.getenv("MIN_CHUNK_TOKENS",  "40"))


# ── Embeddings ─────────────────────────────────────────────────────────────────
EMBEDDING_MODEL     = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIM       = int(os.getenv("EMBEDDING_DIM",        "384"))
EMBEDDING_BATCH     = int(os.getenv("EMBEDDING_BATCH",      "32"))

# ── Retrieval ──────────────────────────────────────────────────────────────────
RETRIEVAL_TOP_K         = int(os.getenv("RETRIEVAL_TOP_K",      "20"))
RERANKER_TOP_K          = int(os.getenv("RERANKER_TOP_K",       "5"))
RERANKER_MODEL          = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANKER_MIN_SCORE      = float(os.getenv("RERANKER_MIN_SCORE", "-5.0"))

# ── LLM ────────────────────────────────────────────────────────────────────────
LLM_CONTEXT_WINDOW  = int(os.getenv("LLM_CONTEXT_WINDOW",  "4096"))
LLM_MAX_TOKENS      = int(os.getenv("LLM_MAX_TOKENS",      "512"))
LLM_TEMPERATURE     = float(os.getenv("LLM_TEMPERATURE",   "0.1"))
LLM_N_GPU_LAYERS    = int(os.getenv("LLM_N_GPU_LAYERS",    "20"))
LLM_N_THREADS       = int(os.getenv("LLM_N_THREADS",       "4"))

# ── LLM Stub — Groq API (dev only) ────────────────────────────────────────────
LLM_USE_STUB    = os.getenv("LLM_USE_STUB", "true").lower() == "true"
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL      = os.getenv("GROQ_MODEL",   "llama-3.1-8b-instant")
GROQ_BASE_URL   = "https://api.groq.com/openai/v1"

# ── Memory Safety ──────────────────────────────────────────────────────────────
MEMORY_WARN_THRESHOLD_GB        = float(os.getenv("MEMORY_WARN_THRESHOLD_GB",      "13.0"))
MEMORY_CRITICAL_THRESHOLD_GB    = float(os.getenv("MEMORY_CRITICAL_THRESHOLD_GB",  "14.5"))

# ── Users ──────────────────────────────────────────────────────────────────────
DEFAULT_VISIBILITY  = os.getenv("DEFAULT_VISIBILITY", "shared")
MAX_USERS           = int(os.getenv("MAX_USERS", "5"))

# ── API ────────────────────────────────────────────────────────────────────────
API_HOST    = os.getenv("API_HOST",     "0.0.0.0")
API_PORT    = int(os.getenv("API_PORT", "8000"))
API_RELOAD  = os.getenv("API_RELOAD",  "false").lower() == "true"

# ── Query Router Keywords ──────────────────────────────────────────────────────
SQL_TRIGGER_KEYWORDS = [
    "total", "sum", "average", "count", "how many", "list all",
    "compare", "maximum", "minimum", "across all", "aggregate"
]
