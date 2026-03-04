"""
db.py — DuckDB connection, schema, and all database operations.
Single connection instance reused across the application lifecycle.
"""

import threading
from pathlib import Path
from datetime import datetime

import duckdb

from app.config import DUCKDB_PATH
from app.utils import get_logger

logger = get_logger("db")

_conn = None
_lock = threading.Lock()


# ── Connection ────────────────────────────────────────────────────────────────

def get_conn() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        with _lock:
            if _conn is None:
                DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
                _conn = duckdb.connect(str(DUCKDB_PATH))
                logger.info(f"DuckDB connected → {DUCKDB_PATH}")
    return _conn


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     VARCHAR PRIMARY KEY,
            username    VARCHAR NOT NULL UNIQUE,
            role        VARCHAR DEFAULT 'viewer',
            created_at  TIMESTAMP DEFAULT current_timestamp
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id        VARCHAR PRIMARY KEY,
            filename      VARCHAR NOT NULL,
            file_path     VARCHAR,
            uploaded_by   VARCHAR,
            visibility    VARCHAR DEFAULT 'shared',
            page_count    INTEGER DEFAULT 0,
            chunk_count   INTEGER DEFAULT 0,
            file_size_mb  FLOAT   DEFAULT 0.0,
            has_tables    BOOLEAN DEFAULT FALSE,
            status        VARCHAR DEFAULT 'processing',
            created_at    TIMESTAMP DEFAULT current_timestamp
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id     VARCHAR PRIMARY KEY,
            doc_id       VARCHAR NOT NULL,
            chunk_index  INTEGER,
            page_number  INTEGER,
            text         VARCHAR,
            token_count  INTEGER,
            created_at   TIMESTAMP DEFAULT current_timestamp
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            query_id      VARCHAR PRIMARY KEY,
            user_id       VARCHAR,
            doc_ids       VARCHAR,
            question      TEXT,
            answer        TEXT,
            sources       TEXT,
            top_score     FLOAT,
            latency_ms    INTEGER,
            passed_gate   BOOLEAN,
            created_at    TIMESTAMP DEFAULT current_timestamp
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_log (
            log_id      VARCHAR PRIMARY KEY,
            doc_id      VARCHAR,
            stage       VARCHAR,
            status      VARCHAR,
            message     VARCHAR,
            created_at  TIMESTAMP DEFAULT current_timestamp
        )
    """)

    logger.info("DuckDB schema ready.")


# ── Deduplication ─────────────────────────────────────────────────────────────

def document_exists(filename: str) -> str | None:
    """
    Returns doc_id if a document with the same filename already exists
    in ready, processing, or chunked state. Returns None if safe to ingest.
    """
    conn = get_conn()
    result = conn.execute(
        """
        SELECT doc_id FROM documents
        WHERE filename = ?
          AND status IN ('ready', 'processing', 'chunked')
        ORDER BY created_at DESC LIMIT 1
        """,
        [filename]
    ).fetchone()
    return result[0] if result else None


# ── Documents ─────────────────────────────────────────────────────────────────

def insert_document(doc: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO documents
            (doc_id, filename, file_path, uploaded_by, visibility,
             page_count, chunk_count, file_size_mb, has_tables, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        doc["doc_id"], doc["filename"], doc["file_path"],
        doc["uploaded_by"], doc["visibility"], doc["page_count"],
        doc["chunk_count"], doc["file_size_mb"], doc["has_tables"],
        doc["status"]
    ])


def update_document_status(doc_id: str, status: str):
    get_conn().execute(
        "UPDATE documents SET status = ? WHERE doc_id = ?",
        [status, doc_id]
    )


def get_document(doc_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM documents WHERE doc_id = ?", [doc_id]
    ).fetchone()
    if not row:
        return None
    cols = [d[0] for d in conn.description]
    return dict(zip(cols, row))


def list_documents(user_id: str = None) -> list[dict]:
    conn = get_conn()
    if user_id:
        rows = conn.execute(
            """
            SELECT * FROM documents
            WHERE (visibility = 'shared' OR uploaded_by = ?)
              AND status = 'ready'
            ORDER BY created_at DESC
            """, [user_id]
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM documents ORDER BY created_at DESC"
        ).fetchall()
    cols = [d[0] for d in conn.description]
    return [dict(zip(cols, row)) for row in rows]


def delete_document(doc_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM chunks   WHERE doc_id = ?", [doc_id])
    conn.execute("DELETE FROM documents WHERE doc_id = ?", [doc_id])
    logger.info(f"Deleted document and chunks for doc_id={doc_id}")


# ── Chunks ────────────────────────────────────────────────────────────────────

def insert_chunks(chunks: list[dict]):
    conn = get_conn()
    for chunk in chunks:
        conn.execute("""
            INSERT INTO chunks
                (chunk_id, doc_id, chunk_index, page_number, text, token_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            chunk["chunk_id"], chunk["doc_id"], chunk["chunk_index"],
            chunk["page_number"], chunk["text"], chunk["token_count"]
        ])


def get_chunks_by_doc(doc_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
        [doc_id]
    ).fetchall()
    cols = [d[0] for d in conn.description]
    return [dict(zip(cols, row)) for row in rows]


# ── Query History ─────────────────────────────────────────────────────────────

def log_query(record: dict):
    """Persists a completed query for analytics and export."""
    conn = get_conn()
    conn.execute("""
        INSERT INTO query_history
            (query_id, user_id, doc_ids, question, answer,
             sources, top_score, latency_ms, passed_gate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        record["query_id"],   record.get("user_id", "anonymous"),
        record.get("doc_ids", "all"), record["question"],
        record.get("answer", ""),     record.get("sources", ""),
        record.get("top_score", 0.0), record.get("latency_ms", 0),
        record.get("passed_gate", False)
    ])


def get_query_history(user_id: str = None, limit: int = 50) -> list[dict]:
    conn = get_conn()
    if user_id:
        rows = conn.execute(
            """
            SELECT * FROM query_history
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
            """, [user_id, limit]
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM query_history ORDER BY created_at DESC LIMIT ?",
            [limit]
        ).fetchall()
    cols = [d[0] for d in conn.description]
    return [dict(zip(cols, row)) for row in rows]


# ── Ingestion Logs ────────────────────────────────────────────────────────────

def log_ingestion(log_id: str, doc_id: str, stage: str, status: str, message: str = ""):
    get_conn().execute("""
        INSERT INTO ingestion_log (log_id, doc_id, stage, status, message)
        VALUES (?, ?, ?, ?, ?)
    """, [log_id, doc_id, stage, status, message])
