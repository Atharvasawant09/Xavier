"""
documents.py — Document management endpoints.
Handles upload, listing, deletion, chunk inspection, and system stats.
"""

import tempfile
from pathlib import Path

import lancedb
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query

from app.config import RAW_PDF_DIR, LANCEDB_DIR
from app.db import get_conn, log_ingestion
from app.embeddings import embed_and_store
from app.ingestion import ingest_pdf
from app.schemas import (
    DocumentResponse, DocumentListResponse, DocumentStatsResponse,
    ChunkResponse, DocumentChunksResponse,
    UploadResponse, DeleteResponse
)
from app.utils import get_logger, ensure_dirs, generate_id

logger = get_logger("documents")
router = APIRouter(prefix="/documents", tags=["documents"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_doc(row: tuple) -> DocumentResponse:
    return DocumentResponse(
        doc_id       = row[0],
        filename     = row[1],
        uploaded_by  = row[2],
        visibility   = row[3],
        page_count   = row[4],
        chunk_count  = row[5],
        file_size_mb = row[6],
        has_tables   = bool(row[7]),
        status       = row[8],
        created_at   = str(row[9]) if row[9] else None,
    )


# ── GET /documents ────────────────────────────────────────────────────────────

@router.get("", response_model=DocumentListResponse)
def list_documents(
    visibility: str = Query(default="shared"),
    status:     str = Query(default=""),
    uploaded_by:  str = Query(default=""),
):
    conn   = get_conn()
    sql    = """
        SELECT doc_id, filename, uploaded_by, visibility,
               page_count, chunk_count, file_size_mb, has_tables,
               status, created_at
        FROM documents
        WHERE visibility = ?
    """
    params = [visibility]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if uploaded_by:
        sql += " AND uploaded_by = ?"
        params.append(uploaded_by)

    sql += " ORDER BY created_at DESC"

    rows = conn.execute(sql, params).fetchall()
    docs = [_row_to_doc(r) for r in rows]
    return DocumentListResponse(total=len(docs), documents=docs)


# ── GET /documents/stats ──────────────────────────────────────────────────────

@router.get("/stats", response_model=DocumentStatsResponse)
def get_stats():
    conn = get_conn()

    row = conn.execute("""
        SELECT
            COUNT(*)                       AS total_docs,
            COALESCE(SUM(chunk_count), 0)  AS total_chunks,
            COALESCE(SUM(page_count),  0)  AS total_pages,
            COALESCE(SUM(file_size_mb),0)  AS total_size_mb,
            COUNT(CASE WHEN status IN ('ready','chunked') THEN 1 END) AS docs_ready
        FROM documents
    """).fetchone()

    try:
        db           = lancedb.connect(str(LANCEDB_DIR))
        tbl          = db.open_table("chunks")
        vector_count = tbl.count_rows()
    except Exception:
        vector_count = 0

    return DocumentStatsResponse(
        total_documents = row[0],
        total_chunks    = row[1],
        total_pages     = row[2],
        total_size_mb   = round(row[3], 2),
        documents_ready = row[4],
        lancedb_vectors = vector_count,
    )


# ── GET /documents/{doc_id} ───────────────────────────────────────────────────

@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str):
    conn = get_conn()
    row  = conn.execute("""
        SELECT doc_id, filename, uploaded_by, visibility,
               page_count, chunk_count, file_size_mb, has_tables,
               status, created_at
        FROM documents WHERE doc_id = ?
    """, [doc_id]).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return _row_to_doc(row)


# ── GET /documents/{doc_id}/chunks ────────────────────────────────────────────

@router.get("/{doc_id}/chunks", response_model=DocumentChunksResponse)
def get_document_chunks(
    doc_id: str,
    page:   int = Query(default=1, ge=1),
    limit:  int = Query(default=20, ge=1, le=100),
):
    conn = get_conn()

    doc = conn.execute(
        "SELECT filename FROM documents WHERE doc_id = ?", [doc_id]
    ).fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    offset = (page - 1) * limit
    rows   = conn.execute("""
        SELECT chunk_id, chunk_index, page_number, token_count, text
        FROM chunks
        WHERE doc_id = ?
        ORDER BY chunk_index
        LIMIT ? OFFSET ?
    """, [doc_id, limit, offset]).fetchall()

    total = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE doc_id = ?", [doc_id]
    ).fetchone()[0]

    chunks = [
        ChunkResponse(
            chunk_id    = r[0],
            chunk_index = r[1],
            page_number = r[2],
            token_count = r[3],
            text        = r[4],
        ) for r in rows
    ]

    return DocumentChunksResponse(
        doc_id   = doc_id,
        filename = doc[0],
        total    = total,
        chunks   = chunks,
    )


# ── POST /documents/upload ────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file:        UploadFile = File(...),
    uploaded_by: str        = Form(default="anonymous"),
    visibility:  str        = Form(default="shared"),
):
    """
    Upload a PDF and run the full ingestion pipeline.
    Rejects non-PDFs, duplicates, and PDFs over MAX_PDF_PAGES.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    ensure_dirs(RAW_PDF_DIR)
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".pdf",
        dir=RAW_PDF_DIR, prefix="upload_"
    ) as tmp:
        content  = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    logger.info(f"Upload received: {file.filename} ({len(content)/1024/1024:.2f}MB)")

    try:
        doc = ingest_pdf(tmp_path, uploaded_by=uploaded_by, visibility=visibility,original_filename = file.filename)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    # embed_and_store handles status update + error logging internally
    try:
        embed_and_store(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    return UploadResponse(
        doc_id      = doc["doc_id"],
        filename    = doc["filename"],
        page_count  = doc["page_count"],
        chunk_count = doc["chunk_count"],
        has_tables  = doc["has_tables"],
        status      = "ready",
        message     = f"Successfully ingested {doc['chunk_count']} chunks from {doc['page_count']} pages.",
    )


# ── DELETE /documents/{doc_id} ────────────────────────────────────────────────

@router.delete("/{doc_id}", response_model=DeleteResponse)
def delete_document(doc_id: str):
    """
    Permanently delete a document — removes from DuckDB, LanceDB, and raw_pdfs.
    """
    conn = get_conn()
    row  = conn.execute(
        "SELECT filename, file_path FROM documents WHERE doc_id = ?", [doc_id]
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    filename, file_path = row

    # 1. DuckDB — chunks then document
    conn.execute("DELETE FROM chunks    WHERE doc_id = ?", [doc_id])
    conn.execute("DELETE FROM documents WHERE doc_id = ?", [doc_id])
    conn.commit()
    logger.info(f"DuckDB: deleted {filename} ({doc_id})")

    # 2. LanceDB — vectors
    try:
        db  = lancedb.connect(str(LANCEDB_DIR))
        tbl = db.open_table("chunks")
        tbl.delete(f"doc_id = '{doc_id}'")
        logger.info(f"LanceDB: deleted vectors for {doc_id}")
    except Exception as e:
        logger.warning(f"LanceDB delete partial: {e}")

    # 3. Raw PDF file
    try:
        pdf_path = Path(file_path)
        if pdf_path.exists():
            pdf_path.unlink()
            logger.info(f"Deleted raw PDF: {file_path}")
    except Exception as e:
        logger.warning(f"Raw PDF delete failed: {e}")

    log_ingestion(generate_id(), doc_id, "delete", "ok", f"Deleted: {filename}")

    return DeleteResponse(
        doc_id  = doc_id,
        message = f"'{filename}' permanently deleted.",
    )
