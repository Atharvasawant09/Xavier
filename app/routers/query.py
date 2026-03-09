"""
routers/query.py — RAG query endpoint.
Accepts a question, runs embed → vector search → rerank → gate → LLM → return answer.
Logs every query to query_history for analytics and future export.
"""

import time
import json

from fastapi import APIRouter, HTTPException

from app.retrieval import retrieve
from app.llm import generate_answer
from app.db import log_query, get_conn
from app.schemas import QueryRequest, QueryResponse, SourceChunk
from app.utils import get_logger, generate_id

router = APIRouter(prefix="/query", tags=["Query"])
logger = get_logger("query")


@router.post("", response_model=QueryResponse)
def query_documents(request: QueryRequest):
    """
    Ask a question against ingested documents.
    Only searches documents the requesting user is allowed to see:
      - All shared documents
      - Private documents owned by the requesting user
    Returns a grounded answer with source citations and page references.
    All queries are logged to query_history regardless of outcome.
    """
    start_ms = time.time()
    query_id = generate_id()

    logger.info(f"[{query_id}] Question: {request.question!r} | User: {request.user_id}")

    # ── Resolve allowed doc_ids for this user ─────────────────────────────────
    try:
        conn        = get_conn()
        allowed_rows = conn.execute("""
            SELECT doc_id FROM documents
            WHERE visibility = 'shared'
               OR (visibility = 'private' AND uploaded_by = ?)
        """, [request.user_id or "anonymous"]).fetchall()
        allowed_ids = [r[0] for r in allowed_rows]
    except Exception as e:
        logger.error(f"[{query_id}] Access control resolution error: {e}")
        raise HTTPException(status_code=500, detail=f"Access control check failed: {e}")

    if not allowed_ids:
        return QueryResponse(
            query_id    = query_id,
            question    = request.question,
            answer      = "No documents are accessible for your user. Upload a document first.",
            sources     = [],
            passed_gate = False,
            top_score   = 0.0,
            latency_ms  = int((time.time() - start_ms) * 1000),
        )

    # ── Retrieval (scoped to allowed docs) ────────────────────────────────────
    try:
        result = retrieve(request.question, doc_ids=allowed_ids)
    except Exception as e:
        logger.error(f"[{query_id}] Retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")

    top_score  = result["chunks"][0]["rerank_score"] if result.get("chunks") else 0.0
    latency_ms = int((time.time() - start_ms) * 1000)

    # ── Gate failed ───────────────────────────────────────────────────────────
    if not result["passed_gate"]:
        logger.info(f"[{query_id}] Gate failed — top score: {top_score:.3f}")
        _log_query(query_id, request, result["no_answer_msg"], result,
                   top_score, latency_ms, allowed_ids)
        return QueryResponse(
            query_id    = query_id,
            question    = request.question,
            answer      = result["no_answer_msg"],
            sources     = [],
            passed_gate = False,
            top_score   = round(top_score, 4),
            latency_ms  = latency_ms,
        )

    # ── LLM Answer Generation ─────────────────────────────────────────────────
    try:
        answer = generate_answer(
            question = result["question"],
            context  = result["context"],
        )
    except Exception as e:
        logger.error(f"[{query_id}] LLM error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {e}")

    latency_ms = int((time.time() - start_ms) * 1000)

    # ── Build source list ─────────────────────────────────────────────────────
    sources = [
        SourceChunk(
            filename     = c["filename"],
            page_number  = c["page_number"],
            score        = round(c["rerank_score"], 4),
            text_preview = c["text"][:300],
        )
        for c in result["chunks"]
    ]

    _log_query(query_id, request, answer, result, top_score, latency_ms, allowed_ids)
    logger.info(f"[{query_id}] Answered in {latency_ms}ms | top score: {top_score:.3f}")

    return QueryResponse(
        query_id    = query_id,
        question    = request.question,
        answer      = answer,
        sources     = sources,
        passed_gate = True,
        top_score   = round(top_score, 4),
        latency_ms  = latency_ms,
    )


# ── Internal Helper ───────────────────────────────────────────────────────────

def _log_query(
    query_id:    str,
    request:     QueryRequest,
    answer:      str,
    result:      dict,
    top_score:   float,
    latency_ms:  int,
    allowed_ids: list,
):
    try:
        sources_json = json.dumps([
            {"filename": c["filename"], "page": c["page_number"], "score": c["rerank_score"]}
            for c in result.get("chunks", [])
        ])
        log_query({
            "query_id":    query_id,
            "user_id":     request.user_id or "anonymous",
            "doc_ids":     json.dumps(allowed_ids),
            "question":    request.question,
            "answer":      answer,
            "sources":     sources_json,
            "top_score":   top_score,
            "latency_ms":  latency_ms,
            "passed_gate": result.get("passed_gate", False),
        })
    except Exception as e:
        logger.warning(f"Failed to log query to history: {e}")
