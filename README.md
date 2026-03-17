# DocInt — Document Intelligence

DocInt is an AI Assistant designed for semantic search and grounded Question & Answering (Q&A) over your document library. It allows you to upload PDF documents, automatically processes and embeds them, and provides a conversational interface to query the information contained within these documents.

## Features

- **Semantic Search & Q&A:** Grounded answers generated using LLMs, with clear citations to source documents and pages.
- **Document Management:** Upload PDFs with visibility controls (shared or private to specific users).
- **PDF Processing & OCR:** Robust text extraction using `pdfplumber` and `pytesseract` for scanned documents.
- **Advanced Vector Storage:** Uses `LanceDB` for fast vector similarity search and `DuckDB` for structured metadata.
- **Streamlit User Interface:** Clean, responsive, and easy-to-use frontend for both querying and document management.
- **Chunk Inspector:** Built-in tool to inspect the semantic chunks extracted from your documents, useful for debugging retrieval quality.
- **System Health Monitoring:** Check database statuses, memory usage, and document ingestion statistics in real-time.

## Tech Stack

- **Backend:** FastAPI, Uvicorn
- **Frontend:** Streamlit
- **Embeddings:** `sentence-transformers`
- **Vector Database:** LanceDB
- **Structured Database:** DuckDB
- **LLM Integration:** 
  - Groq API (Development stub)
  - `llama-cpp-python` (Production on NVIDIA AGX Xavier)
- **PDF & Image Processing:** `pdfplumber`, `pdf2image`, OpenCV, Tesseract OCR

## Getting Started

DocInt consists of a FastAPI backend and a Streamlit frontend. For detailed setup instructions, refer to the guides provided:

- **Windows Setup:** See [`SETUP_GUIDE.md`](SETUP_GUIDE.md) for step-by-step instructions on setting up a local Windows environment and running the demo.
- **NVIDIA AGX Xavier Setup:** See [`XAVIER_SETUP_GUIDE.md`](XAVIER_SETUP_GUIDE.md) for production deployment instructions on the NVIDIA AGX Xavier platform, utilizing local LLM inference.

### Quick Start (Local Development)

1. **Install Dependencies:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   pip install streamlit watchdog
   ```

2. **Configure Environment Variables:**
   Create or edit the `.env` file with your Groq API key:
   ```env
   LLM_USE_STUB=true
   GROQ_API_KEY=your_actual_api_key_here
   ```

3. **Run the Backend System:**
   Run the provided `run.bat` script, or start uvicorn directly:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **Run the Frontend UI:**
   In a separate terminal (with the virtual environment activated), start the Streamlit UI:
   ```bash
   streamlit run app_ui.py
   ```
   The application will be accessible at `http://localhost:8501`.

## Project Structure

- `app/`: FastAPI backend implementation (routers, services, db connections).
- `app_ui.py`: Streamlit frontend UI.
- `scripts/`: Utility scripts (e.g., `ingest_pdf.py`).
- `data/`: Local database storage for LanceDB and DuckDB.
- `assets/`: Static assets like logos.
