"""
schemas.py — Pydantic models for all API request and response bodies.
Single source of truth for input validation and response serialisation.
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


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


class IngestResponse(BaseModel):
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
    question: str  = Field(..., min_length=3, max_length=1000,
                           description="The question to ask the document(s)")
    doc_ids:  Optional[list[str]] = Field(
        default=None,
        description="Scope query to specific doc_ids. Omit for all documents."
    )
    user_id:  Optional[str] = Field(default="anonymous")


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
    status:          str
    memory_used_gb:  float
    memory_avail_gb: float
    documents_count: int
    lancedb_status:  str
    duckdb_status:   str
