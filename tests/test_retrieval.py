"""Tests for retrieval module (Phase 2)."""
import pytest


def test_retrieve_raises_not_implemented():
    from app.retrieval import retrieve
    with pytest.raises(NotImplementedError):
        retrieve("test query")
