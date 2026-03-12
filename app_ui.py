"""
app_ui.py — Streamlit frontend for DocInt.
Run: streamlit run app_ui.py
"""

import os
from pathlib import Path

import streamlit as st
import requests

API = "http://localhost:8000"

st.set_page_config(
    page_title = "DocInt — Document Intelligence",
    page_icon  = "assets/logo.png" if Path("assets/logo.png").exists() else None,
    layout     = "wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #f9fafb;
    }
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }

    /* Streamlit root background */
    .stApp { background-color: #f9fafb; }
    .block-container { padding-top: 1.5rem !important; }

    /* ── Header ── */
    .site-header {
        text-align: center;
        padding: 2rem 2rem 1.75rem;
        margin-bottom: 1.75rem;
        background: linear-gradient(135deg, #ecfdf5 0%, #f0f9ff 50%, #fff7ed 100%);
        border-radius: 16px;
        border: 1px solid #d1fae5;
        box-shadow: 0 2px 12px rgba(5,150,105,0.08);
    }
    .site-header img {
        height: 160px;
        margin-bottom: 0.9rem;
    }
    .site-header h1 {
        color: #134e4a;
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0 0 0.3rem 0;
    }
    .site-header p {
        color: #6b7280;
        font-size: 0.88rem;
        margin: 0;
        font-weight: 600;
    }

    /* ── Metrics ── */
    [data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-top: 3px solid #06b6d4;
        border-radius: 10px;
        padding: 0.9rem 1rem;
        box-shadow: 0 1px 4px rgba(6,182,212,0.07);
    }
    [data-testid="metric-container"] label {
        color: #9ca3af !important;
        font-size: 0.70rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #0e7490 !important;
        font-size: 1.4rem !important;
        font-weight: 700;
    }

    /* ── Document cards ── */
    .doc-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-left: 4px solid #06b6d4;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.55rem;
        transition: border-color 0.2s, box-shadow 0.2s, transform 0.15s;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .doc-card:hover {
        border-left-color: #f97316;
        box-shadow: 0 6px 18px rgba(249,115,22,0.1);
        transform: translateY(-1px);
    }
    .doc-card-private { border-left: 4px solid #f97316 !important; }
    .doc-title {
        color: #111827;
        font-size: 0.95rem;
        font-weight: 600;
        margin: 0 0 0.25rem 0;
    }
    .doc-meta  { color: #9ca3af; font-size: 0.78rem; }

    .badge-private {
        color: #c2410c; font-weight: 600; font-size: 0.73rem;
        background: #fff7ed; border: 1px solid #fed7aa;
        padding: 1px 8px; border-radius: 99px;
    }
    .badge-shared {
        color: #0369a1; font-weight: 600; font-size: 0.73rem;
        background: #e0f2fe; border: 1px solid #bae6fd;
        padding: 1px 8px; border-radius: 99px;
    }

    /* ── Answer box ── */
    .answer-box {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 4px solid #22c55e;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        color: #14532d;
        line-height: 1.8;
        margin: 0.75rem 0;
        font-size: 0.93rem;
        box-shadow: 0 2px 8px rgba(34,197,94,0.07);
    }

    /* ── Access / info banners ── */
    .access-info {
        background: #f0f9ff;
        border: 1px solid #bae6fd;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        color: #0369a1;
        font-size: 0.78rem;
        margin-bottom: 0.9rem;
    }

    /* ── Section labels ── */
    .section-label {
        color: #f97316;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 1.25rem 0 0.6rem 0;
    }

    /* ── Inputs ── */
    /* ── Inputs: text area / text input ── */
    .stTextArea textarea,
    .stTextInput input {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        color: #111827 !important;
        caret-color: #111827 !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextArea textarea:focus,
    .stTextInput input:focus {
        border-color: #06b6d4 !important;
        box-shadow: 0 0 0 3px rgba(6,182,212,0.12) !important;
    }

    /* ── Select dropdown: only target the trigger button, not every baseweb div ── */
    div[data-baseweb="select"] button,
    div[data-baseweb="select"] [class*="ValueContainer"],
    div[data-baseweb="select"] [class*="SingleValue"],
    div[data-baseweb="select"] [class*="Placeholder"] {
        background: #ffffff !important;
        color: #111827 !important;
    }
    /* The outer select container border */
    div[data-baseweb="select"] {
        border-radius: 8px !important;
    }
    div[data-baseweb="select"]:focus-within {
        outline: 2px solid #06b6d4 !important;
        outline-offset: 1px !important;
    }
    /* Dropdown option list */
    ul[role="listbox"] {
        background: #ffffff !important;
    }
    li[role="option"] {
        background: #ffffff !important;
        color: #111827 !important;
    }
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {
        background: #f0f9ff !important;
        color: #0891b2 !important;
    }

    /* ── Number input ── */
    [data-testid="stNumberInput"] input {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        color: #111827 !important;
        caret-color: #111827 !important;
    }
    [data-testid="stNumberInput"] button {
        background: #f9fafb !important;
        color: #374151 !important;
        border-color: #d1d5db !important;
    }

    /* ── Metric values: force dark text so nothing disappears ── */
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] label {
        color: #6b7280 !important;
    }
    [data-testid="stMetricValue"] {
        color: #0e7490 !important;
    }
    [data-testid="stMetricDelta"] {
        color: #374151 !important;
    }

    /* ── File uploader ── */
    [data-testid="stFileUploadDropzone"] {
        background: #f0f9ff !important;
        border: 1.5px dashed #06b6d4 !important;
        border-radius: 10px !important;
    }
    [data-testid="stFileUploadDropzone"] p,
    [data-testid="stFileUploadDropzone"] span,
    [data-testid="stFileUploadDropzone"] small {
        color: #0369a1 !important;
    }
    /* Filename shown after selecting a file */
    [data-testid="stFileUploaderFileName"] {
        color: #111827 !important;
    }
    [data-testid="stFileUploader"] > div > div > div small {
        color: #6b7280 !important;
    }


    /* ── Primary buttons ── */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #06b6d4, #0891b2) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.03em !important;
        padding: 0.55rem 1.5rem !important;
        transition: opacity 0.15s, box-shadow 0.15s !important;
        box-shadow: 0 2px 10px rgba(6,182,212,0.3) !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button:hover {
        opacity: 0.88 !important;
        box-shadow: 0 4px 16px rgba(6,182,212,0.4) !important;
    }

    /* ── Secondary buttons ── */
    .stButton > button[kind="secondary"] {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        color: #6b7280 !important;
        border-radius: 8px !important;
        font-size: 0.78rem !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #f97316 !important;
        color: #ea580c !important;
        background: #fff7ed !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: linear-gradient(90deg, #ecfdf5, #e0f2fe, #fff7ed);
        border-radius: 12px;
        padding: 0.7rem;
        gap: 0.7rem;
        border: 1px solid #d1fae5;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #6b7280;
        border-radius: 9px;
        font-weight: 500;
        font-size: 0.9rem;
        transition: color 0.15s;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #0891b2 !important;
    }
    .stTabs [aria-selected="true"] {
        # background: #ffffff !important;
        color: #0891b2 !important;
        font-weight: 600 !important;
        # box-shadow: 0 1px 6px rgba(6,182,212,0.15) !important;
    }

    /* ── Divider ── */
    hr { border-color: #e5e7eb; }

    /* ── Gate-fail banner ── */
    .gate-fail {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        border-left: 4px solid #f97316;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        color: #9a3412;
        margin: 0.75rem 0;
        font-size: 0.88rem;
    }

    /* ── Status badges ── */
    .status-ready      { color: #15803d; font-weight: 600; }
    .status-chunked    { color: #d97706; font-weight: 600; }
    .status-failed     { color: #dc2626; font-weight: 600; }
    .status-processing { color: #ea580c; font-weight: 600; }
    .status-pending    { color: #2563eb; font-weight: 600; }

    /* ── Expander ── */
    details {
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
    }
    summary { color: #374151 !important; font-size: 0.83rem !important; }

    /* ── Code blocks ── */
    .stCode, .stCodeBlock { border-radius: 6px !important; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #f3f4f6; }
    ::-webkit-scrollbar-thumb { background: #06b6d4; border-radius: 99px; }
    ::-webkit-scrollbar-thumb:hover { background: #0891b2; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def api_get(path, params=None):
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=10)
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def api_post(path, json_data=None, files=None, data=None):
    try:
        r = requests.post(f"{API}{path}", json=json_data,
                          files=files, data=data, timeout=300)
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def api_delete(path):
    try:
        r = requests.delete(f"{API}{path}", timeout=10)
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def status_badge(status: str) -> str:
    classes = {
        "ready":      "status-ready",
        "chunked":    "status-chunked",
        "failed":     "status-failed",
        "processing": "status-processing",
        "pending":    "status-pending",
    }
    cls = classes.get(status, "")
    return f'<span class="{cls}">{status.upper()}</span>'

def vis_badge(vis: str) -> str:
    if vis == "private":
        return '<span class="badge-private">PRIVATE</span>'
    return '<span class="badge-shared">SHARED</span>'


# ── Persistent user_id ──────────────────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state["user_id"] = "dev_user"


# ── Header ─────────────────────────────────────────────────────────────────────
logo_path = Path("assets/logo.png")
header_html = '<div class="site-header">'
if logo_path.exists():
    # Serve the logo inline via base64
    import base64
    with open(logo_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    header_html += f'<img src="data:image/png;base64,{b64}" alt="Logo" /><br/>'
header_html += """
    <h1>AI Assistant</h1>
    <p>Semantic search and grounded Q&amp;A over your document library</p>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)


# ── Global User ID ─────────────────────────────────────────────────────────────
with st.container():
    gcol1, gcol2 = st.columns([1, 5])
    with gcol1:
        uid_input = st.text_input(
            "Active User",
            value    = st.session_state["user_id"],
            help     = "Controls which private documents are visible to you.",
            key      = "global_user_id_input",
        )
        if uid_input != st.session_state["user_id"]:
            st.session_state["user_id"] = uid_input
            st.rerun()

active_user = st.session_state["user_id"]


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_query, tab_docs, tab_system = st.tabs(["   Query   ", "   Documents   ", "   System   "])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — QUERY
# ══════════════════════════════════════════════════════════════════════════════

with tab_query:
    st.markdown(f"""
    <div class="access-info">
        Querying as <strong style="color:#cbd5e1">{active_user}</strong> —
        all shared documents and private documents you own are included.
    </div>
    """, unsafe_allow_html=True)

    with st.form("query_form"):
        question  = st.text_area(
            "Question",
            placeholder = "e.g. What are the functional requirements in section 8.1?",
            height      = 60,
            label_visibility = "collapsed",
        )
        fc1, fc2 = st.columns([5, 1])
        with fc2:
            ans_style = st.selectbox(
                "Answer Style",
                options = ["Auto", "Brief", "Detailed"],
                index   = 0,
                label_visibility = "visible",
                key = "ans_style_select",
            )
        submitted = st.form_submit_button("Search", use_container_width=True)

    if submitted:
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            import threading, time as _time
            _QUERY_MESSAGES = [
                "Embedding your question...",
                "Searching across document vectors...",
                "Ranking the most relevant passages...",
                "Filtering by relevance score...",
                "Building context for the model...",
                "Generating a grounded answer...",
                "Verifying source citations...",
                "Almost there...",
            ]
            _style_suffix = {
                "Brief":    "\n\nPlease answer concisely in 2-3 sentences only.",
                "Detailed": "\n\nPlease provide a detailed, thorough explanation with all relevant details.",
                "Auto":     "",
            }.get(ans_style, "")
            _question_final = question.strip() + _style_suffix
            _qresult = {"resp": None, "status": None, "done": False}
            def _do_query():
                r, s = api_post("/query", json_data={
                    "question": _question_final,
                    "user_id":  active_user,
                })
                _qresult["resp"], _qresult["status"], _qresult["done"] = r, s, True
            _qt = threading.Thread(target=_do_query)
            _qt.start()
            _qph = st.empty()
            _qmi = 0
            while not _qresult["done"]:
                _qph.info(_QUERY_MESSAGES[_qmi % len(_QUERY_MESSAGES)])
                _qmi += 1
                _time.sleep(2.0)
            _qph.empty()
            _qt.join()
            resp, status = _qresult["resp"], _qresult["status"]

            if status != 200:
                st.error(f"API Error {status}: {resp.get('detail', resp)}")

            elif not resp.get("passed_gate"):
                st.markdown("""
                <div class="gate-fail">
                    No relevant content found in your accessible documents for this question.
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                c1.metric("Relevance Score", f"{resp.get('top_score', 0):.4f}")
                c2.metric("Latency",         f"{resp.get('latency_ms')}ms")

            else:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Relevance Score", f"{resp['top_score']:.4f}")
                c2.metric("Latency",         f"{resp['latency_ms']}ms")
                c3.metric("Sources",         len(resp["sources"]))
                c4.metric("Confidence",      "Passed")

                st.markdown('<p class="section-label">Answer</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="answer-box">{resp["answer"]}</div>',
                            unsafe_allow_html=True)

                st.markdown('<p class="section-label">Sources</p>', unsafe_allow_html=True)
                for src in resp["sources"]:
                    with st.expander(
                        f"{src['filename']}  ·  Page {src['page_number']}  ·  Score {src['score']:.4f}"
                    ):
                        st.code(src["text_preview"], language=None)



# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

with tab_docs:
    col_list, col_upload = st.columns([3, 2])

    with col_list:
        st.markdown('<p class="section-label">Indexed Documents</p>', unsafe_allow_html=True)

        ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 2])
        with ctrl1:
            if st.button("Refresh", use_container_width=True):
                st.rerun()
        with ctrl2:
            vis_filter = st.selectbox(
                "Visibility",
                ["shared", "private", "all"],
                label_visibility = "collapsed",
                key              = "vis_filter",
            )

        if vis_filter == "private":
            st.markdown(f"""
            <div class="access-info">
                Showing private documents uploaded by <strong style="color:#d97706">{active_user}</strong>.
            </div>
            """, unsafe_allow_html=True)
        elif vis_filter == "all":
            st.markdown(f"""
            <div class="access-info">
                Showing all documents accessible to <strong style="color:#1e293b">{active_user}</strong>
                (shared + your private documents).
            </div>
            """, unsafe_allow_html=True)

        # Fetch docs
        if vis_filter == "all":
            shared_resp, _  = api_get("/documents", params={"visibility": "shared"})
            private_resp, _ = api_get("/documents", params={
                "visibility": "private", "uploaded_by": active_user,
            })
            all_docs = shared_resp.get("documents", []) + private_resp.get("documents", [])
            seen     = set()
            all_docs = [d for d in all_docs if not (d["doc_id"] in seen or seen.add(d["doc_id"]))]
            docs_resp   = {"documents": all_docs, "total": len(all_docs)}
            docs_status = 200
        elif vis_filter == "private":
            docs_resp, docs_status = api_get("/documents", params={
                "visibility": "private", "uploaded_by": active_user,
            })
        else:
            docs_resp, docs_status = api_get("/documents", params={"visibility": "shared"})

        if docs_status != 200:
            st.error(f"Could not fetch documents: {docs_resp}")
        elif docs_resp.get("total", 0) == 0:
            st.markdown("""
            <div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;
                        padding:2.5rem;text-align:center;color:#94a3b8;margin-top:1rem">
                No documents found.<br>
                <span style="font-size:0.82rem">Try a different filter or upload a PDF.</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            for doc in docs_resp["documents"]:
                is_private = doc.get("visibility") == "private"
                card_class = "doc-card doc-card-private" if is_private else "doc-card"
                tables_txt = "Tables detected" if doc["has_tables"] else "No tables"

                st.markdown(f"""
                <div class="{card_class}">
                    <p class="doc-title">{doc['filename']}</p>
                    <p class="doc-meta">
                        {status_badge(doc['status'])} &nbsp;&middot;&nbsp;
                        {doc['page_count']} pages &nbsp;&middot;&nbsp;
                        {doc['chunk_count']} chunks &nbsp;&middot;&nbsp;
                        {doc['file_size_mb']:.2f} MB &nbsp;&middot;&nbsp;
                        {tables_txt} &nbsp;&middot;&nbsp;
                        {doc.get('uploaded_by', '?')}
                        &nbsp;&middot;&nbsp; {vis_badge(doc.get('visibility', 'shared'))}
                    </p>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Delete", key=f"del_{doc['doc_id']}"):
                    del_resp, del_status = api_delete(f"/documents/{doc['doc_id']}")
                    if del_status == 200:
                        st.success(del_resp["message"])
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {del_resp}")

    with col_upload:
        st.markdown('<p class="section-label">Upload PDF</p>', unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
                    padding:0.9rem;color:#64748b;font-size:0.8rem;margin-bottom:1rem;line-height:2.1">
            Max <strong style="color:#475569">100 pages</strong> per document<br>
            Max <strong style="color:#475569">200 MB</strong> file size<br>
            PDF format only
        </div>
        """, unsafe_allow_html=True)

        with st.form("upload_form"):
            uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"])
            uploader_name = st.text_input("Uploaded by", value=active_user)
            visibility    = st.selectbox("Visibility", ["shared", "private"])
            upload_btn    = st.form_submit_button("Upload and Ingest", use_container_width=True)

        if upload_btn:
            if uploaded_file is None:
                st.warning("Please select a PDF file.")
            else:
                import threading, time
                _INGEST_MESSAGES = [
                    f"Reading {uploaded_file.name}...",
                    "Extracting text from pages...",
                    "Detecting tables and document structure...",
                    "Splitting content into semantic chunks...",
                    "Loading embedding model...",
                    "Generating vector embeddings for chunks...",
                    "Writing vectors to LanceDB...",
                    "Indexing metadata in DuckDB...",
                    "Running quality checks on chunks...",
                    "Finalising document index...",
                    "Almost done...",
                ]
                _result = {"resp": None, "status": None, "done": False}
                def _do_upload():
                    r, s = api_post(
                        "/documents/upload",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                        data={"uploaded_by": uploader_name, "visibility": visibility},
                    )
                    _result["resp"], _result["status"], _result["done"] = r, s, True
                _t = threading.Thread(target=_do_upload)
                _t.start()
                _ph = st.empty()
                _mi = 0
                while not _result["done"]:
                    _ph.info(_INGEST_MESSAGES[_mi % len(_INGEST_MESSAGES)])
                    _mi += 1
                    time.sleep(2.5)
                _ph.empty()
                _t.join()
                up_resp, up_status = _result["resp"], _result["status"]
                if up_status == 200:
                    st.success(up_resp["message"])
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Pages",  up_resp["page_count"])
                    c2.metric("Chunks", up_resp["chunk_count"])
                    c3.metric("Tables", "Yes" if up_resp["has_tables"] else "No")
                    st.rerun()
                else:
                    st.error(f"Upload failed ({up_status}): {up_resp.get('detail', up_resp)}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

with tab_system:
    col_health, col_stats = st.columns(2)

    with col_health:
        st.markdown('<p class="section-label">System Health</p>', unsafe_allow_html=True)
        health, h_status = api_get("/health")

        if h_status != 200:
            st.error(f"Health check failed: {health}")
        else:
            overall_ok  = health["duckdb_ok"] and health["lancedb_ok"]
            status_text = "ONLINE" if overall_ok else "DEGRADED"
            status_color = "#22c55e" if overall_ok else "#ef4444"
            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;
                        padding:1.1rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.05)">
                <div style="font-size:1rem;font-weight:700;color:{status_color}">{status_text}</div>
                <div style="color:#94a3b8;font-size:0.78rem;margin-top:0.2rem">
                    DocInt v{health['version']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.metric("Memory Used", f"{health['memory_used_gb']} GB")
            c2.metric("Memory Free", f"{health['memory_free_gb']} GB")
            c3, c4 = st.columns(2)
            c3.metric("DuckDB",  "OK" if health["duckdb_ok"]  else "Down")
            c4.metric("LanceDB", "OK" if health["lancedb_ok"] else "Down")

    with col_stats:
        st.markdown('<p class="section-label">Ingestion Statistics</p>', unsafe_allow_html=True)
        stats, s_status = api_get("/documents/stats")

        if s_status != 200:
            st.error(f"Could not fetch stats: {stats}")
        else:
            c1, c2 = st.columns(2)
            c1.metric("Documents",    stats["total_documents"])
            c2.metric("Ready",        stats["documents_ready"])
            c3, c4 = st.columns(2)
            c3.metric("Total Chunks", stats["total_chunks"])
            c4.metric("Vectors",      stats["lancedb_vectors"])
            c5, c6 = st.columns(2)
            c5.metric("Pages",        stats["total_pages"])
            c6.metric("Storage",      f"{stats['total_size_mb']} MB")

    # ── Chunk Inspector ─────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-label">Chunk Inspector</p>', unsafe_allow_html=True)
    st.caption("Inspect extracted text chunks per document to debug retrieval quality.")

    shared_r, _  = api_get("/documents", params={"visibility": "shared"})
    private_r, _ = api_get("/documents", params={
        "visibility": "private", "uploaded_by": active_user
    })
    all_inspect = shared_r.get("documents", []) + private_r.get("documents", [])
    seen_ids    = set()
    all_inspect = [d for d in all_inspect if not (d["doc_id"] in seen_ids or seen_ids.add(d["doc_id"]))]

    if not all_inspect:
        st.info("No documents available to inspect.")
    else:
        doc_options = {d["filename"]: d["doc_id"] for d in all_inspect}
        ci1, ci2, ci3, ci4 = st.columns([3, 1, 1, 1])
        with ci1:
            selected_doc = st.selectbox("Document", list(doc_options.keys()),
                                        label_visibility="collapsed")
        with ci2:
            chunk_page  = st.number_input("Page", min_value=1, value=1,
                                          label_visibility="collapsed")
        with ci3:
            chunk_limit = st.select_slider("Per page", options=[5, 10, 20, 50], value=10,
                                           label_visibility="collapsed")
        with ci4:
            load_btn = st.button("Load", use_container_width=True)

        if load_btn:
            doc_id = doc_options[selected_doc]
            chunks_resp, c_status = api_get(
                f"/documents/{doc_id}/chunks",
                params={"page": chunk_page, "limit": chunk_limit}
            )
            if c_status != 200:
                st.error(f"Could not load chunks: {chunks_resp}")
            else:
                st.caption(f"Showing {len(chunks_resp['chunks'])} of {chunks_resp['total']} chunks")
                for ch in chunks_resp["chunks"]:
                    with st.expander(
                        f"Chunk {ch['chunk_index']:03d}  ·  Page {ch['page_number']}  ·  {ch['token_count']} tokens"
                    ):
                        st.code(ch["text"], language=None)
