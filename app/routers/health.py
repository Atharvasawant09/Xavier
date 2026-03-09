"""
health.py — System health check endpoint.
"""

import psutil
import lancedb
from fastapi import APIRouter

from app.config import LANCEDB_DIR
from app.db import get_conn
from app.schemas import HealthResponse
from app.utils import get_logger

logger = get_logger("health")
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    vm          = psutil.virtual_memory()
    mem_used_gb = round((vm.total - vm.available) / 1024**3, 2)
    mem_free_gb = round(vm.available / 1024**3, 2)

    try:
        conn         = get_conn()
        total_docs   = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        duckdb_ok    = True
    except Exception as e:
        logger.warning(f"DuckDB health check failed: {e}")
        total_docs = total_chunks = 0
        duckdb_ok  = False

    try:
        db  = lancedb.connect(str(LANCEDB_DIR))
        tbl = db.open_table("chunks")
        tbl.count_rows()
        lancedb_ok = True
    except Exception as e:
        logger.warning(f"LanceDB health check failed: {e}")
        lancedb_ok = False

    return HealthResponse(
        status         = "ok",
        version        = "1.0.0",
        total_docs     = total_docs,
        total_chunks   = total_chunks,
        memory_used_gb = mem_used_gb,
        memory_free_gb = mem_free_gb,
        lancedb_ok     = lancedb_ok,
        duckdb_ok      = duckdb_ok,
    )
