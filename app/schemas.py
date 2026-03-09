"""
schemas.py — Pydantic request/response models for DocInt API.
All endpoints use these models for validation and serialisation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Document Schemas ──────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    doc_id:       str
    filename:     str
    uploaded_by:  str
    visibility:   str
    page_count:   int
    chunk_count:  int
    file_size_mb: float
    has_tables:   bool
    status:       str
    created_at:   Optional[str] = None


class DocumentListResponse(BaseModel):
    total:     int
    documents: list[DocumentResponse]


class DocumentStatsResponse(BaseModel):
    total_documents:  int
    total_chunks:     int
    total_pages:      int
    total_size_mb:    float
    documents_ready:  int
    lancedb_vectors:  int


class ChunkResponse(BaseModel):
    chunk_id:    str
    chunk_index: int
    page_number: int
    token_count: int
    text:        str


class DocumentChunksResponse(BaseModel):
    doc_id:     str
    filename:   str
    total:      int
    chunks:     list[ChunkResponse]


# ── Upload / Delete Schemas ───────────────────────────────────────────────────

class UploadResponse(BaseModel):
    doc_id:      str
    filename:    str
    page_count:  int
    chunk_count: int
    has_tables:  bool
    status:      str
    message:     str


class DeleteResponse(BaseModel):
    doc_id:  str
    message: str


# ── Query Schemas ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question:   str  = Field(..., min_length=3, max_length=1000)
    user_id:    str  = Field(default="anonymous")
    top_k:      int  = Field(default=5, ge=1, le=20)
    visibility: str  = Field(default="shared")


class SourceChunk(BaseModel):
    filename:     str
    page_number:  int
    score:        float
    text_preview: str


class QueryResponse(BaseModel):
    query_id:    str
    question:    str
    answer:      str
    sources:     list[SourceChunk]
    passed_gate: bool
    top_score:   float
    latency_ms:  int


# ── Health Schema ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:        str
    version:       str
    total_docs:    int
    total_chunks:  int
    memory_used_gb: float
    memory_free_gb: float
    lancedb_ok:    bool
    duckdb_ok:     bool
