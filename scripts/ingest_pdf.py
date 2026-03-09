"""
scripts/ingest_pdf.py — CLI entry point for PDF ingestion.
Handles the full pipeline: DB init → ingest → embed → mark ready.

Usage:
    python -m scripts.ingest_pdf --file path/to/doc.pdf --user dev_user
    python -m scripts.ingest_pdf --file path/to/doc.pdf --user dev_user --visibility private
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import init_db
from app.ingestion import ingest_pdf
from app.embeddings import embed_and_store
from app.utils import get_logger, log_memory

logger = get_logger("ingest_pdf")


def main():
    parser = argparse.ArgumentParser(description="Ingest a PDF into DocInt")
    parser.add_argument("--file",       required=True,  help="Path to the PDF file")
    parser.add_argument("--user",       required=True,  help="User ID of uploader")
    parser.add_argument("--visibility", default="shared",
                        choices=["shared", "private"], help="Document visibility")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"\n  ❌ File not found: {file_path}")
        sys.exit(1)
    if file_path.suffix.lower() != ".pdf":
        print(f"\n  ❌ Only PDF files are supported. Got: {file_path.suffix}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  Document Intelligence System — PDF Ingestor")
    print(f"{'='*50}")
    print(f"  File      : {file_path.name}")
    print(f"  User      : {args.user}")
    print(f"  Visibility: {args.visibility}")
    print(f"{'='*50}\n")

    # ── Step 1: Database ──────────────────────────────────────────────────────
    print("[ 1/3 ] Initialising database...")
    init_db()
    log_memory("init")
    print("        ✅ Database ready\n")

    # ── Step 2: Ingest ────────────────────────────────────────────────────────
    print("[ 2/3 ] Extracting text and chunking...")
    try:
        doc = ingest_pdf(
            file_path=file_path,
            uploaded_by=args.user,
            visibility=args.visibility
        )
    except ValueError as e:
        msg = str(e)
        if "already indexed" in msg:
            print(f"\n  ⚠️  SKIPPED — {msg}")
        else:
            print(f"\n  ❌  REJECTED — {msg}")
        print(f"  To re-ingest, first run:")
        print(f"    python -m scripts.delete_doc --doc_id <id>")
        print(f"\n  Or list all documents with:")
        print(f"    python -m scripts.list_docs")
        sys.exit(0)
    except RuntimeError as e:
        print(f"\n  ❌ INGESTION FAILED — {e}")
        sys.exit(1)

    print(f"        ✅ Extracted {doc['page_count']} pages")
    print(f"        ✅ Created   {doc['chunk_count']} chunks")
    print(f"        ✅ Doc ID    : {doc['doc_id']}")
    print(f"        ✅ Tables detected: {doc['has_tables']}\n")

    # ── Step 3: Embed ─────────────────────────────────────────────────────────
    print("[ 3/3 ] Generating embeddings and storing in LanceDB...")
    print("        (First run downloads BGE-small model ~90MB — may take a moment)")
    try:
        embed_and_store(doc)
    except Exception as e:
        print(f"\n  ❌ EMBEDDING FAILED — {e}")
        sys.exit(1)

    print("        ✅ All chunks embedded and stored\n")
    log_memory("complete")

    print(f"{'='*50}")
    print(f"  ✅ INGESTION COMPLETE")
    print(f"{'='*50}")
    print(f"  Document : {doc['filename']}")
    print(f"  Doc ID   : {doc['doc_id']}")
    print(f"  Pages    : {doc['page_count']}")
    print(f"  Chunks   : {doc['chunk_count']}")
    print(f"  Status   : {doc['status']}")
    print(f"{'='*50}")

    # ── Preview first 3 chunks ────────────────────────────────────────────────
    if doc.get("chunks"):
        print(f"\n  Preview — First 3 chunks:\n")
        for chunk in doc["chunks"][:3]:
            print(f"  Chunk {chunk['chunk_index']} | Page {chunk['page_number']} | {chunk['token_count']} tokens")
            print(f"  {chunk['text'][:160]}...\n")


if __name__ == "__main__":
    main()
