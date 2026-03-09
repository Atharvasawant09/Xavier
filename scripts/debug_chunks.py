"""
debug_chunks.py — Inspect chunks stored in DuckDB.
Usage: python -m scripts.debug_chunks
       python -m scripts.debug_chunks --doc blackbook
       python -m scripts.debug_chunks --range 88 96
"""

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.db import get_conn


def main():
    parser = argparse.ArgumentParser(description="Inspect DocInt chunks")
    parser.add_argument("--doc",   type=str, help="Filter by filename substring")
    parser.add_argument("--range", type=int, nargs=2, metavar=("FROM", "TO"),
                        help="Show chunk_index range e.g. --range 88 96")
    parser.add_argument("--limit", type=int, default=10,
                        help="Max chunks to show (default 10)")
    args = parser.parse_args()

    conn = get_conn()
    docs = conn.execute(
        "SELECT doc_id, filename, chunk_count, status FROM documents ORDER BY created_at DESC"
    ).fetchall()

    if not docs:
        print("No documents in DB.")
        return

    for doc_id, filename, chunk_count, status in docs:
        if args.doc and args.doc.lower() not in filename.lower():
            continue

        print(f"\n{'='*65}")
        print(f"Doc    : {filename}")
        print(f"ID     : {doc_id}")
        print(f"Chunks : {chunk_count} | Status: {status}")
        print(f"{'='*65}")

        if args.range:
            rows = conn.execute("""
                SELECT chunk_index, page_number, token_count, LEFT(text, 200)
                FROM chunks
                WHERE doc_id = ? AND chunk_index BETWEEN ? AND ?
                ORDER BY chunk_index
            """, [doc_id, args.range[0], args.range[1]]).fetchall()
        else:
            rows = conn.execute("""
                SELECT chunk_index, page_number, token_count, LEFT(text, 200)
                FROM chunks
                WHERE doc_id = ?
                ORDER BY chunk_index
                LIMIT ?
            """, [doc_id, args.limit]).fetchall()

        for r in rows:
            print(f"\nChunk {r[0]:03d} | Page {r[1]:02d} | {r[2]} tokens")
            print(r[3])
            print("─" * 65)


if __name__ == "__main__":
    main()
