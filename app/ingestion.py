"""
ingestion.py — PDF ingestion pipeline.
Flow: PDF file → extract text (pdfplumber) → table enrichment → OCR fallback
      → sentence-aware + heading-aware chunking → returns chunks for embedding.
"""

import re
import shutil
from pathlib import Path

import pdfplumber

from app.config import (
    CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS_PER_PDF, RAW_PDF_DIR
)
from app.utils import (
    get_logger, get_file_size_mb, sanitize_filename,
    generate_id, count_tokens, ensure_dirs
)
from app.db import (
    insert_document, insert_chunks, update_document_status,
    log_ingestion, document_exists
)

logger = get_logger("ingestion")

MIN_CHUNK_TOKENS = 20


# ── Text Extraction ───────────────────────────────────────────────────────────

def extract_text_pdfplumber(pdf_path: Path) -> list[dict]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append({
                    "page_number": i + 1,
                    "text": text.strip()
                })
            else:
                logger.warning(f"Page {i+1} has no extractable text — may need OCR.")
    return pages


def extract_text_ocr(pdf_path: Path) -> list[dict]:
    """OCR fallback via Tesseract. Called only when pdfplumber yields < 20% pages."""
    try:
        import pytesseract
        import cv2
        import numpy as np
        from pdf2image import convert_from_path

        pages = []
        images = convert_from_path(str(pdf_path), dpi=200)
        for i, img in enumerate(images):
            img_np = np.array(img)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            text = pytesseract.image_to_string(thresh)
            if text.strip():
                pages.append({"page_number": i + 1, "text": text.strip()})
        return pages

    except ImportError:
        logger.error("OCR dependencies missing. Install pdf2image, pytesseract, cv2.")
        return []
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return []


# ── Table Extraction ──────────────────────────────────────────────────────────

def extract_tables_as_text(pdf_path: Path) -> dict:
    """
    Extracts tables from PDF and converts each row to
    'Header: Value | Header: Value' format so embeddings
    carry full semantic context without relying on column position.
    Returns {page_number: table_text_block}.
    """
    table_texts = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if not tables:
                    continue

                page_table_blocks = []
                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    headers = [str(h).strip() if h else "" for h in table[0]]
                    rows_text = []

                    for row in table[1:]:
                        if not row:
                            continue
                        row_parts = []
                        for header, cell in zip(headers, row):
                            cell_val = str(cell).strip() if cell else ""
                            if cell_val:
                                row_parts.append(f"{header}: {cell_val}")
                        if row_parts:
                            rows_text.append(" | ".join(row_parts))

                    if rows_text:
                        block = f"[TABLE] {' || '.join(rows_text)}"
                        page_table_blocks.append(block)

                if page_table_blocks:
                    table_texts[i + 1] = "\n".join(page_table_blocks)

    except Exception as e:
        logger.warning(f"Table extraction failed for {pdf_path.name}: {e}")

    return table_texts


def extract_text(pdf_path: Path) -> tuple[list[dict], bool]:
    """
    Primary extraction via pdfplumber with table enrichment.
    Falls back to OCR if fewer than 20% of pages yield text.
    Returns (pages, used_ocr).
    """
    pages = extract_text_pdfplumber(pdf_path)
    total_pages = len(pages)
    good_pages = [p for p in pages if len(p["text"]) > 50]

    if total_pages == 0 or len(good_pages) / max(total_pages, 1) < 0.2:
        logger.info(f"Low text yield — attempting OCR for {pdf_path.name}")
        ocr_pages = extract_text_ocr(pdf_path)
        if ocr_pages:
            return ocr_pages, True

    # ── Enrich pages with table content ───────────────────────────────────────
    table_texts = extract_tables_as_text(pdf_path)
    for page in pages:
        pnum = page["page_number"]
        if pnum in table_texts:
            page["text"] = page["text"] + "\n" + table_texts[pnum]
            logger.info(f"Page {pnum}: enriched with table content")

    return pages, False


# ── Heading Detection ─────────────────────────────────────────────────────────

def is_heading(text: str) -> bool:
    text = text.strip()
    if not text or len(text) > 120:
        return False
    patterns = [
        r'^\d+(\.\d+)*\.?\s+\w',
        r'^(Chapter|Section|Part)\s+\d+',
        r'^[A-Z][A-Z\s]{4,50}$',
        r'^(Abstract|Introduction|Conclusion|References|Methodology|Summary)',
    ]
    return any(re.match(p, text, re.IGNORECASE) for p in patterns)


# ── Sentence-Aware + Heading-Aware Chunking ───────────────────────────────────

def split_into_sentences(text: str) -> list[str]:
    """
    Splits text into sentence units.
    Heading lines become __HEADING__ tokens — treated as hard chunk boundaries.
    """
    text = re.sub(r'\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e)\.\s', r'\1<PERIOD> ', text)
    lines = text.split('\n')
    units = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if is_heading(line):
            units.append(f"__HEADING__: {line}")
        else:
            sents = re.split(r'(?<=[.!?])\s+', line)
            units.extend([
                s.replace('<PERIOD>', '.').strip()
                for s in sents if s.strip()
            ])

    return units


def create_chunks(pages: list[dict], doc_id: str) -> list[dict]:
    """
    Produces overlapping, heading-prefixed chunks from page text.
    Discards micro-chunks below MIN_CHUNK_TOKENS to prevent garbage retrieval.
    """
    chunks = []
    chunk_index = 0
    sentence_buffer = []
    token_buffer = 0
    current_heading = ""

    all_units = []
    for page in pages:
        units = split_into_sentences(page["text"])
        for u in units:
            all_units.append((u, page["page_number"]))

    def flush_buffer(buffer, heading, index):
        if not buffer:
            return None
        chunk_text = " ".join(s for s, _ in buffer)
        if heading and not chunk_text.startswith(heading):
            chunk_text = f"{heading}: {chunk_text}"
        token_count = count_tokens(chunk_text)
        if token_count < MIN_CHUNK_TOKENS:
            logger.debug(f"Discarding micro-chunk ({token_count} tokens): {chunk_text[:60]}")
            return None
        return {
            "chunk_id":    generate_id(),
            "doc_id":      doc_id,
            "chunk_index": index,
            "page_number": buffer[0][1],
            "text":        chunk_text,
            "token_count": token_count,
        }

    i = 0
    while i < len(all_units) and chunk_index < MAX_CHUNKS_PER_PDF:
        unit, page_num = all_units[i]

        # ── Heading → flush and start fresh ───────────────────────────────────
        if unit.startswith("__HEADING__:"):
            heading_text = unit.replace("__HEADING__:", "").strip()
            if sentence_buffer:
                chunk = flush_buffer(sentence_buffer, current_heading, chunk_index)
                if chunk:
                    chunks.append(chunk)
                    chunk_index += 1
            current_heading = heading_text
            sentence_buffer = []
            token_buffer = 0
            i += 1
            continue

        sent_tokens = count_tokens(unit)

        if token_buffer + sent_tokens <= CHUNK_SIZE:
            sentence_buffer.append((unit, page_num))
            token_buffer += sent_tokens
            i += 1
        else:
            if sentence_buffer:
                chunk = flush_buffer(sentence_buffer, current_heading, chunk_index)
                if chunk:
                    chunks.append(chunk)
                    chunk_index += 1

                # Overlap: retain last CHUNK_OVERLAP tokens of sentences
                overlap_tokens = 0
                overlap_buffer = []
                for item in reversed(sentence_buffer):
                    t = count_tokens(item[0])
                    if overlap_tokens + t <= CHUNK_OVERLAP:
                        overlap_buffer.insert(0, item)
                        overlap_tokens += t
                    else:
                        break

                sentence_buffer = overlap_buffer
                token_buffer = overlap_tokens
            else:
                # Single oversized sentence — force include
                sentence_buffer.append((unit, page_num))
                chunk = flush_buffer(sentence_buffer, current_heading, chunk_index)
                if chunk:
                    chunks.append(chunk)
                    chunk_index += 1
                sentence_buffer = []
                token_buffer = 0
                i += 1

    # Flush remaining buffer
    if sentence_buffer and chunk_index < MAX_CHUNKS_PER_PDF:
        chunk = flush_buffer(sentence_buffer, current_heading, chunk_index)
        if chunk:
            chunks.append(chunk)

    logger.info(f"Created {len(chunks)} chunks from {len(pages)} pages (heading-aware)")
    return chunks


# ── Table Detection Flag ──────────────────────────────────────────────────────

def detect_tables(pdf_path: Path) -> bool:
    """Quick boolean check — flags doc for SQL routing in Phase 6."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                if page.extract_tables():
                    return True
    except Exception:
        pass
    return False


# ── Main Ingestion Entry Point ────────────────────────────────────────────────

def ingest_pdf(file_path: Path, uploaded_by: str, visibility: str = "shared") -> dict:
    """
    Full ingestion pipeline for a single PDF.
    Saves → extracts text + tables → chunks → stores in DuckDB.
    Raises ValueError if the file was already ingested.
    Returns doc dict with doc_id, filename, chunk_count, status, chunks.
    """
    filename = sanitize_filename(file_path.name)

    # ── Deduplication check ───────────────────────────────────────────────────
    existing_id = document_exists(filename)
    if existing_id:
        logger.warning(f"'{filename}' already ingested as {existing_id}. Skipping.")
        raise ValueError(
            f"'{filename}' is already indexed (doc_id={existing_id}). "
            "Delete the existing document before re-ingesting."
        )

    doc_id   = generate_id()
    dest_path = RAW_PDF_DIR / f"{doc_id}_{filename}"
    ensure_dirs(RAW_PDF_DIR)

    logger.info(f"Ingesting: {filename} (doc_id={doc_id})")
    log_ingestion(generate_id(), doc_id, "start", "ok", f"File: {filename}")

    # ── Save to permanent location ─────────────────────────────────────────────
    shutil.copy2(str(file_path), str(dest_path))
    file_size_mb = get_file_size_mb(dest_path)
    logger.info(f"Saved to {dest_path} ({file_size_mb}MB)")

    # ── Page count + table flag ───────────────────────────────────────────────
    with pdfplumber.open(dest_path) as pdf:
        page_count = len(pdf.pages)
    has_tables = detect_tables(dest_path)

    # ── Insert document record (status=processing) ────────────────────────────
    doc = {
        "doc_id":       doc_id,
        "filename":     filename,
        "file_path":    str(dest_path),
        "uploaded_by":  uploaded_by,
        "visibility":   visibility,
        "page_count":   page_count,
        "chunk_count":  0,
        "file_size_mb": file_size_mb,
        "has_tables":   has_tables,
        "status":       "processing",
    }
    insert_document(doc)
    log_ingestion(generate_id(), doc_id, "db_insert", "ok")

    # ── Extract text + enrich with tables ─────────────────────────────────────
    try:
        pages, used_ocr = extract_text(dest_path)
        log_ingestion(generate_id(), doc_id, "extraction", "ok",
                      f"Pages: {len(pages)}, OCR: {used_ocr}")
    except Exception as e:
        update_document_status(doc_id, "failed")
        log_ingestion(generate_id(), doc_id, "extraction", "error", str(e))
        raise RuntimeError(f"Text extraction failed for {filename}: {e}")

    if not pages:
        update_document_status(doc_id, "failed")
        log_ingestion(generate_id(), doc_id, "extraction", "error", "No text extracted")
        raise RuntimeError(f"No text could be extracted from {filename}")

    # ── Chunk ─────────────────────────────────────────────────────────────────
    try:
        chunks = create_chunks(pages, doc_id)
        insert_chunks(chunks)
        log_ingestion(generate_id(), doc_id, "chunking", "ok", f"Chunks: {len(chunks)}")
    except Exception as e:
        update_document_status(doc_id, "failed")
        log_ingestion(generate_id(), doc_id, "chunking", "error", str(e))
        raise RuntimeError(f"Chunking failed: {e}")

    # ── Update chunk count ────────────────────────────────────────────────────
    from app.db import get_conn
    get_conn().execute(
        "UPDATE documents SET chunk_count = ?, status = 'chunked' WHERE doc_id = ?",
        [len(chunks), doc_id]
    )

    doc["chunk_count"] = len(chunks)
    doc["chunks"]      = chunks
    doc["status"]      = "chunked"

    logger.info(f"Ingestion complete: {filename} → {len(chunks)} chunks, {page_count} pages")
    return doc
