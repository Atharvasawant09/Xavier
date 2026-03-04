"""
scripts/test_query.py — CLI to test the full RAG pipeline end to end.
Shows retrieval chunks AND the final LLM-generated answer.

Usage:
    python -m scripts.test_query --question "What ML models were used?"
    python -m scripts.test_query --question "What is section 8.2.5 about?" --doc_id <id>
    python -m scripts.test_query --question "..." --no-llm   # retrieval only, skip LLM
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import init_db, list_documents
from app.retrieval import retrieve
from app.llm import generate_answer
from app.utils import get_logger, log_memory

logger = get_logger("test_query")


def main():
    parser = argparse.ArgumentParser(description="Test full RAG pipeline")
    parser.add_argument("--question", required=True,  help="Question to ask")
    parser.add_argument("--doc_id",   default=None,   help="Scope to specific doc_id (optional)")
    parser.add_argument("--no-llm",   action="store_true", help="Skip LLM, show retrieval only")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Document Intelligence System — Full Pipeline Test")
    print(f"{'='*60}")
    print(f"  Question : {args.question}")
    print(f"  LLM      : {'SKIPPED' if args.no_llm else 'ENABLED'}")
    if args.doc_id:
        print(f"  Scope    : {args.doc_id}")
    print(f"{'='*60}\n")

    init_db()

    docs = list_documents()
    if not docs:
        print("❌ No documents ingested yet. Run ingest_pdf.py first.")
        sys.exit(1)

    print(f"  Indexed documents ({len(docs)}):")
    for d in docs:
        print(f"    • [{d['status']:8}] {d['filename']}  ({d['chunk_count']} chunks)")
    print()

    # ── Retrieval ─────────────────────────────────────────────────────────────
    doc_ids = [args.doc_id] if args.doc_id else None
    result = retrieve(question=args.question, doc_ids=doc_ids)

    if not result["passed_gate"]:
        print(f"{'='*60}")
        print(f"  ⚠️  NO RELEVANT CONTENT FOUND")
        print(f"  {result['no_answer_msg']}")
        print(f"{'='*60}")
        sys.exit(0)

    # ── Show retrieved chunks ─────────────────────────────────────────────────
    print(f"{'='*60}")
    print(f"  ✅ RETRIEVAL — {len(result['chunks'])} chunks")
    print(f"{'='*60}")
    for i, chunk in enumerate(result["chunks"]):
        print(f"\n  Chunk {i+1} | {chunk['filename']} | Page {chunk['page_number']} | Score {chunk['rerank_score']}")
        print(f"  {chunk['text'][:300]}...")
    print()

    if args.no_llm:
        print("  [LLM skipped via --no-llm flag]")
        sys.exit(0)

    # ── LLM Answer ────────────────────────────────────────────────────────────
    print(f"{'='*60}")
    print(f"  Generating answer via LLM...")
    print(f"{'='*60}\n")

    try:
        answer = generate_answer(
            question=result["question"],
            context=result["context"]
        )
    except Exception as e:
        print(f"  ❌ LLM generation failed: {e}")
        sys.exit(1)

    print(f"  ANSWER:")
    print(f"  {'-'*56}")
    # Pretty print answer with wrapping
    for line in answer.split('\n'):
        print(f"  {line}")
    print(f"  {'-'*56}")

    # ── Sources ───────────────────────────────────────────────────────────────
    print(f"\n  SOURCES:")
    for chunk in result["chunks"]:
        print(f"    • {chunk['filename']} — Page {chunk['page_number']} (score: {chunk['rerank_score']})")

    print(f"\n{'='*60}")
    log_memory("pipeline_complete")


if __name__ == "__main__":
    main()
