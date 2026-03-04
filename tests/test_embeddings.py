"""Tests for embeddings module (Phase 1)."""
import pytest


def test_embed_chunks_raises_not_implemented():
    from app.embeddings import embed_chunks
    with pytest.raises(NotImplementedError):
        embed_chunks([{"text": "hello"}])


def test_store_embeddings_raises_not_implemented():
    from app.embeddings import store_embeddings
    with pytest.raises(NotImplementedError):
        store_embeddings("doc1", [], [])
