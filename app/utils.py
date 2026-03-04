"""
utils.py — Shared utilities: memory monitoring, logging, token counting, file helpers.
"""

import os
import logging
import uuid
from datetime import datetime
from pathlib import Path

import psutil

from app.config import MEMORY_WARN_THRESHOLD_GB, MEMORY_CRITICAL_THRESHOLD_GB

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

logger = get_logger("utils")


# ── Memory ────────────────────────────────────────────────────────────────────
def get_memory_usage_gb() -> float:
    return round(psutil.virtual_memory().used / (1024 ** 3), 2)

def get_available_memory_gb() -> float:
    return round(psutil.virtual_memory().available / (1024 ** 3), 2)

def log_memory(tag: str = "") -> None:
    used = get_memory_usage_gb()
    available = get_available_memory_gb()
    prefix = f"[{tag}] " if tag else ""
    logger.info(f"{prefix}Memory — Used: {used}GB | Available: {available}GB")

def check_memory_safe() -> bool:
    used = get_memory_usage_gb()
    if used >= MEMORY_CRITICAL_THRESHOLD_GB:
        raise MemoryError(f"Memory usage {used}GB critically high. Aborting.")
    if used >= MEMORY_WARN_THRESHOLD_GB:
        logger.warning(f"Memory usage {used}GB approaching limit.")
    return True


# ── Token Counter ─────────────────────────────────────────────────────────────
def count_tokens(text: str) -> int:
    """Approximate token count. 1 token ≈ 0.75 words."""
    return int(len(text.split()) / 0.75)


# ── File Helpers ──────────────────────────────────────────────────────────────
def generate_id() -> str:
    return str(uuid.uuid4())

def get_file_size_mb(path: str | Path) -> float:
    return round(os.path.getsize(path) / (1024 ** 2), 2)

def sanitize_filename(filename: str) -> str:
    return "".join(c for c in filename if c.isalnum() or c in "._- ").strip()

def now_iso() -> str:
    return datetime.utcnow().isoformat()

def ensure_dirs(*paths) -> None:
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)
