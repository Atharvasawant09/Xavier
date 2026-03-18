"""
embeddings.py — Embedding generation and LanceDB vector storage.
Uses BAAI/bge-small-en-v1.5. Stores vectors in LanceDB (SSD-native).
Model is loaded once and reused across calls.
"""
try:
    import torch
    import sklearn
    import scipy

except ImportError:
    pass


import numpy as np
from pathlib import Path

from app.config import (
    EMBEDDING_MODEL, EMBEDDING_DIM, EMBEDDING_BATCH, LANCEDB_DIR
)
from app.utils import get_logger, log_memory, ensure_dirs
from app.db import update_document_status, log_ingestion
from app.utils import generate_id


logger = get_logger("embeddings")

# ── Lazy model holder — loaded once on first call ─────────────────────────────
_embedding_model = None
_reranker_model  = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        log_memory("before_embedding_model_load")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        log_memory("after_embedding_model_load")
        logger.info("Embedding model loaded.")
    return _embedding_model


def get_reranker_model():
    global _reranker_model
    if _reranker_model is None:
        from sentence_transformers import CrossEncoder
        from app.config import RERANKER_MODEL
        logger.info(f"Loading reranker: {RERANKER_MODEL}")
        _reranker_model = CrossEncoder(RERANKER_MODEL)
        logger.info("Reranker loaded.")
    return _reranker_model


# ── LanceDB Table ─────────────────────────────────────────────────────────────

def get_lancedb_table():
    """
    Opens (or creates) the LanceDB vectors table.
    Schema: chunk_id, doc_id, page_number, text, vector
    """
    import lancedb
    import pyarrow as pa

    ensure_dirs(LANCEDB_DIR)
    db = lancedb.connect(str(LANCEDB_DIR))

    schema = pa.schema([
        pa.field("chunk_id",    pa.string()),
        pa.field("doc_id",      pa.string()),
        pa.field("page_number", pa.int32()),
        pa.field("text",        pa.string()),
        pa.field("vector",      pa.list_(pa.float32(), EMBEDDING_DIM)),
    ])

    if "chunks" not in db.table_names():
        table = db.create_table("chunks", schema=schema)
        logger.info("LanceDB table 'chunks' created.")
    else:
        table = db.open_table("chunks")

    return table


# ── Embed Chunks ──────────────────────────────────────────────────────────────

def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Generates embeddings for a list of chunk dicts.
    Adds 'vector' key to each chunk.
    Processes in batches to control memory.
    """
    model = get_embedding_model()
    texts = [c["text"] for c in chunks]

    logger.info(f"Embedding {len(texts)} chunks in batches of {EMBEDDING_BATCH}...")
    log_memory("before_embedding")

    all_vectors = []
    for i in range(0, len(texts), EMBEDDING_BATCH):
        batch = texts[i:i + EMBEDDING_BATCH]
        # BGE-small expects this prefix for retrieval tasks
        prefixed = [f"Represent this sentence for searching relevant passages: {t}" for t in batch]
        vectors = model.encode(prefixed, normalize_embeddings=True)
        all_vectors.extend(vectors.tolist())

    log_memory("after_embedding")

    for chunk, vector in zip(chunks, all_vectors):
        chunk["vector"] = vector

    return chunks


# ── Store in LanceDB ──────────────────────────────────────────────────────────

def store_in_lancedb(chunks: list[dict]) -> None:
    """
    Stores embedded chunks into LanceDB.
    Each record: chunk_id, doc_id, page_number, text, vector.
    """
    table = get_lancedb_table()

    records = [
        {
            "chunk_id":    c["chunk_id"],
            "doc_id":      c["doc_id"],
            "page_number": c.get("page_number", 0) or 0,
            "text":        c["text"],
            "vector":      c["vector"],
        }
        for c in chunks
        if "vector" in c
    ]

    if records:
        table.add(records)
        logger.info(f"Stored {len(records)} vectors in LanceDB.")
    else:
        logger.warning("No vectors to store — chunks missing embeddings.")


# ── Delete from LanceDB ───────────────────────────────────────────────────────

def delete_from_lancedb(doc_id: str) -> None:
    """Removes all vectors for a given doc_id from LanceDB."""
    try:
        table = get_lancedb_table()
        table.delete(f"doc_id = '{doc_id}'")
        logger.info(f"Deleted vectors for doc_id={doc_id} from LanceDB.")
    except Exception as e:
        logger.error(f"Failed to delete from LanceDB: {e}")


# ── Main Entry Point ──────────────────────────────────────────────────────────

def embed_and_store(doc: dict) -> None:
    """
    Takes a doc dict (output of ingest_pdf) containing 'chunks'.
    Embeds all chunks and stores in LanceDB.
    Updates document status to 'ready' in DuckDB on success.

    Args:
        doc: dict with keys doc_id, filename, chunks (list of chunk dicts)
    """
    doc_id   = doc["doc_id"]
    filename = doc["filename"]
    chunks   = doc.get("chunks", [])

    if not chunks:
        logger.error(f"No chunks found for doc_id={doc_id}")
        update_document_status(doc_id, "failed")
        return

    logger.info(f"Embedding {len(chunks)} chunks for {filename}")

    try:
        chunks_with_vectors = embed_chunks(chunks)
        store_in_lancedb(chunks_with_vectors)
        update_document_status(doc_id, "ready")
        log_ingestion(generate_id(), doc_id, "embedding", "ok",
                      f"Embedded and stored {len(chunks)} chunks")
        logger.info(f"Document {filename} is now READY for querying.")

    except Exception as e:
        update_document_status(doc_id, "failed")
        log_ingestion(generate_id(), doc_id, "embedding", "error", str(e))
        logger.error(f"Embedding failed for {filename}: {e}")
        raise


# ── Query Embedding (used by retrieval.py) ────────────────────────────────────

def embed_query(question: str) -> list[float]:
    """
    Embeds a user query for LanceDB semantic search.
    Uses same model and prefix as chunk embedding for consistency.
    """
    model = get_embedding_model()
    prefixed = f"Represent this sentence for searching relevant passages: {question}"
    vector = model.encode([prefixed], normalize_embeddings=True)
    return vector[0].tolist()


def delete_doc_vectors(doc_id: str):
    """
    Removes all vectors for a given doc_id from the LanceDB chunks table.
    Called when a document is deleted via the API.
    """
    try:
        db    = lancedb.connect(str(LANCEDB_DIR))
        table = db.open_table("chunks")
        table.delete(f"doc_id = '{doc_id}'")
        logger.info(f"Deleted vectors for doc_id={doc_id}")
    except Exception as e:
        logger.warning(f"Could not delete vectors for {doc_id}: {e}")
