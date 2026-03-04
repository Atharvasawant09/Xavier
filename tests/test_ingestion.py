"""Tests for ingestion module (Phase 1)."""
import pytest


def test_ingest_pdf_raises_not_implemented():
    from app.ingestion import ingest_pdf
    from pathlib import Path
    with pytest.raises(NotImplementedError):
        ingest_pdf(Path("dummy.pdf"))


def test_ingest_directory_raises_not_implemented():
    from app.ingestion import ingest_directory
    with pytest.raises(NotImplementedError):
        ingest_directory()
