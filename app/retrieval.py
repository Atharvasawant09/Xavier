"""
retrieval.py — Semantic retrieval pipeline.
Flow: question → embed → LanceDB Top-K search → metadata filter
      → reranker → confidence gate → return ranked chunks with sources.
"""

from app.config import (
    RETRIEVAL_TOP_K, RERANKER_TOP_K, RERANKER_MIN_SCORE
)
from app.utils import get_logger, log_memory
from app.embeddings import embed_query, get_reranker_model, get_lancedb_table

logger = get_logger("retrieval")


# ── LanceDB Search ────────────────────────────────────────────────────────────

def search_lancedb(query_vector: list[float], doc_ids: list[str] | None = None) -> list[dict]:
    """
    Searches LanceDB for Top-K nearest chunks.
    Optionally filters by a list of doc_ids (for scoped queries).

    Returns list of dicts: chunk_id, doc_id, page_number, text, _distance
    """
    table = get_lancedb_table()

    query = table.search(query_vector).limit(RETRIEVAL_TOP_K)

    if doc_ids:
        id_list = ", ".join(f"'{d}'" for d in doc_ids)
        query = query.where(f"doc_id IN ({id_list})", prefilter=True)

    results = query.to_list()
    logger.info(f"LanceDB returned {len(results)} candidates")
    return results


# ── Reranker ──────────────────────────────────────────────────────────────────

def rerank(question: str, candidates: list[dict]) -> list[dict]:
    """
    Reranks LanceDB candidates using MiniLM cross-encoder.
    Takes Top-K candidates, returns Top RERANKER_TOP_K with scores.
    Each result gets a 'rerank_score' key added.
    """
    if not candidates:
        return []

    reranker = get_reranker_model()
    pairs = [(question, c["text"]) for c in candidates]

    log_memory("before_rerank")
    scores = reranker.predict(pairs)
    log_memory("after_rerank")

    for candidate, score in zip(candidates, scores):
        candidate["rerank_score"] = float(score)

    ranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
    top = ranked[:RERANKER_TOP_K]

    logger.info(
        f"Reranker scores — top {RERANKER_TOP_K}: "
        + ", ".join(f"{r['rerank_score']:.3f}" for r in top)
    )
    return top


# ── Confidence Gate ───────────────────────────────────────────────────────────

def passes_confidence_gate(chunks: list[dict]) -> bool:
    """
    Returns False if the best reranked chunk score is below RERANKER_MIN_SCORE.
    Prevents the LLM from being called with irrelevant context.
    """
    if not chunks:
        return False
    best_score = chunks[0]["rerank_score"]
    if best_score < RERANKER_MIN_SCORE:
        logger.warning(
            f"Confidence gate FAILED — best score {best_score:.3f} "
            f"< threshold {RERANKER_MIN_SCORE}"
        )
        return False
    return True


# ── Source Attribution ────────────────────────────────────────────────────────

def build_sources(chunks: list[dict]) -> list[dict]:
    """
    Builds source attribution list from retrieved chunks.
    Fetches filename from DuckDB for each unique doc_id.
    """
    from app.db import get_document

    sources = []
    seen_docs = {}

    for c in chunks:
        doc_id = c["doc_id"]
        if doc_id not in seen_docs:
            doc = get_document(doc_id)
            seen_docs[doc_id] = doc["filename"] if doc else "Unknown"

        sources.append({
            "chunk_id":     c["chunk_id"],
            "doc_id":       doc_id,
            "filename":     seen_docs[doc_id],
            "page_number":  c.get("page_number", "?"),
            "rerank_score": round(c.get("rerank_score", 0.0), 4),
            "text":         c["text"],
        })

    return sources


# ── Main Retrieval Entry Point ────────────────────────────────────────────────

def retrieve(question: str, doc_ids: list[str] | None = None) -> dict:
    """
    Full retrieval pipeline for a user question.

    Args:
        question: the user's natural language question
        doc_ids:  optional list of doc_ids to scope the search to specific documents

    Returns:
        {
            "question":      str,
            "passed_gate":   bool,
            "chunks":        list of top chunks with source attribution,
            "context":       formatted string of chunks ready for LLM prompt,
            "no_answer_msg": str if gate failed, else None
        }
    """
    logger.info(f"Retrieving for: '{question}'")
    log_memory("retrieval_start")

    # Step 1 — Embed question
    query_vector = embed_query(question)

    # Step 2 — LanceDB semantic search
    candidates = search_lancedb(query_vector, doc_ids=doc_ids)

    if not candidates:
        return {
            "question":      question,
            "passed_gate":   False,
            "chunks":        [],
            "context":       "",
            "no_answer_msg": "No documents found in the knowledge base. Please upload relevant PDFs first.",
        }

    # Step 3 — Rerank
    top_chunks = rerank(question, candidates)

    # Step 4 — Confidence gate
    if not passes_confidence_gate(top_chunks):
        return {
            "question":      question,
            "passed_gate":   False,
            "chunks":        [],
            "context":       "",
            "no_answer_msg": "I could not find relevant information in the uploaded documents for this question.",
        }

    # Step 5 — Build sources
    sources = build_sources(top_chunks)

    # Step 6 — Build context string for LLM prompt
    context_parts = []
    for i, s in enumerate(sources):
        context_parts.append(
            f"[Source {i+1}: {s['filename']}, Page {s['page_number']}]\n{s['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    log_memory("retrieval_end")

    return {
        "question":      question,
        "passed_gate":   True,
        "chunks":        sources,
        "context":       context,
        "no_answer_msg": None,
    }
