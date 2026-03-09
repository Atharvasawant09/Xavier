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
    CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS_PER_PDF, RAW_PDF_DIR,
    MAX_PDF_PAGES, MIN_CHUNK_TOKENS
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

SECTION_MAP = {
    "8.1": "Functional Requirements",
    "8.2": "Non-Functional Requirements",
    "9.1": "System Architecture",
    "9.2": "Data Flow Diagram",
    "9.3": "Data Flow Diagram Level 1",
    "9.4": "Activity Diagram",
    "9.5": "ML Models Layer",
    "9.6": "RAG System Layer",
    "9.7": "Sprint Planning",
    "10.1": "Implementation Overview",
    "10.2": "Data Pre-processing",
    "10.3": "Feature Engineering",
    "10.4": "Data Training",
    "10.5": "Model Evaluation",
    "10.6": "Frontend Implementation",
    "10.7": "Backend Implementation",
    "11.1": "Deployment Architecture",
    "11.2": "Deployment Steps",
    "12.1": "Unit Testing",
    "12.2": "Integration Testing",
    "12.3": "Performance Testing",
    "1.1":  "Background",
    "1.2":  "Existing Tools",
    "1.3":  "Project Motivation",
    "1.4":  "Project Overview",
    "1.5":  "Project Goals",
    "1.6":  "Irrigation Methods",
    "2.1":  "Climate Change Overview",
    "2.2":  "Scientific Gaps",
    "2.3":  "Research Gap",
    "3.1":  "Primary Objectives",
    "3.2":  "Secondary Objectives",
}


# ── Text Extraction ───────────────────────────────────────────────────────────

def extract_text_pdfplumber(pdf_path: Path) -> list[dict]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append({"page_number": i + 1, "text": text.strip()})
            else:
                logger.warning(f"Page {i+1} has no extractable text — may need OCR.")
    return pages


def extract_text_ocr(pdf_path: Path) -> list[dict]:
    try:
        import pytesseract
        import cv2
        import numpy as np
        from pdf2image import convert_from_path

        pages  = []
        images = convert_from_path(str(pdf_path), dpi=200)
        for i, img in enumerate(images):
            img_np    = np.array(img)
            gray      = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            text      = pytesseract.image_to_string(thresh)
            if text.strip():
                pages.append({"page_number": i + 1, "text": text.strip()})
        return pages
    except ImportError:
        logger.error("OCR dependencies missing. Install pdf2image, pytesseract, cv2.")
        return []
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return []


def extract_tables_as_text(pdf_path: Path) -> dict:
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
                    headers   = [str(h).strip() if h else "" for h in table[0]]
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
                        page_table_blocks.append(f"[TABLE] {' || '.join(rows_text)}")
                if page_table_blocks:
                    table_texts[i + 1] = "\n".join(page_table_blocks)
    except Exception as e:
        logger.warning(f"Table extraction failed for {pdf_path.name}: {e}")
    return table_texts


def extract_text(pdf_path: Path) -> tuple[list[dict], bool]:
    pages       = extract_text_pdfplumber(pdf_path)
    total_pages = len(pages)
    good_pages  = [p for p in pages if len(p["text"]) > 50]

    if total_pages == 0 or len(good_pages) / max(total_pages, 1) < 0.2:
        logger.info(f"Low text yield — attempting OCR for {pdf_path.name}")
        ocr_pages = extract_text_ocr(pdf_path)
        if ocr_pages:
            return ocr_pages, True

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
        r'^(Abstract|Introduction|Conclusion|References|Methodology|Summary|Appendix)',
        r'^\d+(\.\d+)*\s+[A-Z][a-zA-Z\s\-&/()]+$',
    ]
    return any(re.match(p, text, re.IGNORECASE) for p in patterns)


def infer_parent_heading(text: str) -> str:
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', text.strip())
    if not match:
        return ""
    parent_key = f"{match.group(1)}.{match.group(2)}"
    return SECTION_MAP.get(parent_key, "")


# ── Chunking ──────────────────────────────────────────────────────────────────

def split_into_sentences(text: str) -> list[str]:
    text  = re.sub(r'\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e)\.\s', r'\1<PERIOD> ', text)
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
            units.extend([s.replace('<PERIOD>', '.').strip() for s in sents if s.strip()])
    return units


def create_chunks(pages: list[dict], doc_id: str) -> list[dict]:
    chunks          = []
    chunk_index     = 0
    sentence_buffer = []
    token_buffer    = 0
    current_heading = ""

    all_units = []
    for page in pages:
        for u in split_into_sentences(page["text"]):
            all_units.append((u, page["page_number"]))

    def flush_buffer(buffer, heading, index):
        if not buffer:
            return None
        chunk_text     = " ".join(s for s, _ in buffer)
        first_sentence = buffer[0][0].strip()
        inferred       = infer_parent_heading(first_sentence)
        if inferred:
            heading = inferred
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

        if unit.startswith("__HEADING__:"):
            heading_text = unit.replace("__HEADING__:", "").strip()
            if sentence_buffer:
                chunk = flush_buffer(sentence_buffer, current_heading, chunk_index)
                if chunk:
                    chunks.append(chunk)
                    chunk_index += 1
            parent = infer_parent_heading(heading_text)
            current_heading = f"{parent}: {heading_text}" if parent else heading_text
            sentence_buffer = []
            token_buffer    = 0
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
                token_buffer    = overlap_tokens
            else:
                sentence_buffer.append((unit, page_num))
                chunk = flush_buffer(sentence_buffer, current_heading, chunk_index)
                if chunk:
                    chunks.append(chunk)
                    chunk_index += 1
                sentence_buffer = []
                token_buffer    = 0
                i += 1

    if sentence_buffer and chunk_index < MAX_CHUNKS_PER_PDF:
        chunk = flush_buffer(sentence_buffer, current_heading, chunk_index)
        if chunk:
            chunks.append(chunk)

    logger.info(f"Created {len(chunks)} chunks from {len(pages)} pages (heading-aware)")
    return chunks


# ── Table Detection ───────────────────────────────────────────────────────────

def detect_tables(pdf_path: Path) -> bool:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                if page.extract_tables():
                    return True
    except Exception:
        pass
    return False


# ── Main Entry Point ──────────────────────────────────────────────────────────

def ingest_pdf(
    file_path:         Path,
    uploaded_by:       str,
    visibility:        str = "shared",
    original_filename: str = None,        # ← fixed: added parameter
) -> dict:
    filename = sanitize_filename(original_filename if original_filename else file_path.name)

    existing_id = document_exists(filename)
    if existing_id:
        logger.warning(f"'{filename}' already ingested as {existing_id}. Skipping.")
        raise ValueError(
            f"'{filename}' is already indexed (doc_id={existing_id}). "
            "Delete the existing document before re-ingesting."
        )

    doc_id    = generate_id()
    dest_path = RAW_PDF_DIR / f"{doc_id}_{filename}"
    ensure_dirs(RAW_PDF_DIR)

    logger.info(f"Ingesting: {filename} (doc_id={doc_id})")
    log_ingestion(generate_id(), doc_id, "start", "ok", f"File: {filename}")

    shutil.copy2(str(file_path), str(dest_path))
    file_size_mb = get_file_size_mb(dest_path)
    logger.info(f"Saved to {dest_path} ({file_size_mb}MB)")

    with pdfplumber.open(dest_path) as pdf:
        page_count = len(pdf.pages)
    has_tables = detect_tables(dest_path)

    if page_count > MAX_PDF_PAGES:
        dest_path.unlink(missing_ok=True)
        update_document_status(doc_id, "failed")
        log_ingestion(generate_id(), doc_id, "page_limit", "error",
                      f"{page_count} pages exceeds limit of {MAX_PDF_PAGES}")
        raise ValueError(
            f"'{filename}' has {page_count} pages — limit is {MAX_PDF_PAGES}. "
            "Split the PDF and re-ingest each part."
        )

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

    try:
        chunks = create_chunks(pages, doc_id)
        insert_chunks(chunks)
        log_ingestion(generate_id(), doc_id, "chunking", "ok", f"Chunks: {len(chunks)}")
    except Exception as e:
        update_document_status(doc_id, "failed")
        log_ingestion(generate_id(), doc_id, "chunking", "error", str(e))
        raise RuntimeError(f"Chunking failed: {e}")

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
