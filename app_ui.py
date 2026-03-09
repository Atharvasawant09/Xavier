"""
app_ui.py — Streamlit frontend for DocInt.
Run: streamlit run app_ui.py
"""

import streamlit as st
import requests

API = "http://localhost:8000"

st.set_page_config(
    page_title = "DocInt",
    page_icon  = "📄",
    layout     = "wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }

    .top-bar {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        padding: 1.2rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .top-bar h1 { color: #e2e8f0; font-size: 1.6rem; margin: 0; }
    .top-bar p  { color: #94a3b8; font-size: 0.85rem; margin: 0; }

    [data-testid="metric-container"] {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 1rem;
    }
    [data-testid="metric-container"] label {
        color: #94a3b8 !important;
        font-size: 0.75rem;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #e2e8f0 !important;
        font-size: 1.4rem !important;
        font-weight: 600;
    }

    .doc-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.5rem;
        transition: border-color 0.2s;
    }
    .doc-card:hover   { border-color: #6366f1; }
    .doc-card-private { border-left: 3px solid #f59e0b !important; }
    .doc-title { color: #e2e8f0; font-size: 1rem; font-weight: 600; margin: 0 0 0.3rem 0; }
    .doc-meta  { color: #64748b; font-size: 0.8rem; }

    .badge-private { color: #f59e0b; font-weight: 600; }
    .badge-shared  { color: #38bdf8; font-weight: 600; }

    .answer-box {
        background: #1e293b;
        border-left: 4px solid #6366f1;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        color: #e2e8f0;
        line-height: 1.7;
        margin: 1rem 0;
    }

    .access-info {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        color: #64748b;
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }

    .section-header {
        color: #94a3b8;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin: 1.5rem 0 0.75rem 0;
    }

    .stTextArea textarea, .stTextInput input, div[data-baseweb="select"] {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        color: #e2e8f0 !important;
        border-radius: 8px !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
    }

    .stButton > button[kind="primary"], .stFormSubmitButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
        transition: opacity 0.2s !important;
    }
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
        opacity: 0.85 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: #0f172a;
        border-radius: 10px;
        padding: 0.3rem;
        gap: 0.3rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #64748b;
        border-radius: 8px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: #1e293b !important;
        color: #e2e8f0 !important;
    }

    hr { border-color: #1e293b; }
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
                          files=files, data=data, timeout=120)
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def api_delete(path):
    try:
        r = requests.delete(f"{API}{path}", timeout=10)
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def status_badge(status):
    icons = {"ready": "🟢", "chunked": "🟡", "failed": "🔴", "pending": "🔵", "processing": "🟠"}
    return f"{icons.get(status, '⚪')} {status.upper()}"

def vis_badge(vis):
    if vis == "private":
        return '<span class="badge-private">🔒 PRIVATE</span>'
    return '<span class="badge-shared">🌐 SHARED</span>'


# ── Persistent user_id in session state ───────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state["user_id"] = "dev_user"


# ── Top Bar ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="top-bar">
    <div>
        <h1>📄 DocInt</h1>
        <p>Document Intelligence System — Semantic search and LLM-powered Q&A</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Global User ID (shared across tabs) ───────────────────────────────────────
with st.container():
    gcol1, gcol2 = st.columns([1, 4])
    with gcol1:
        uid_input = st.text_input(
            "🙍 Active User ID",
            value    = st.session_state["user_id"],
            help     = "This user ID controls which private documents you can see and query.",
            key      = "global_user_id_input",
        )
        if uid_input != st.session_state["user_id"]:
            st.session_state["user_id"] = uid_input
            st.rerun()

active_user = st.session_state["user_id"]


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_query, tab_docs, tab_system = st.tabs(["💬  Query", "📁  Documents", "⚙️  System"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — QUERY
# ══════════════════════════════════════════════════════════════════════════════

with tab_query:
    col_q, col_hint = st.columns([3, 1])

    with col_q:
        st.markdown('<p class="section-header">Ask a question</p>', unsafe_allow_html=True)

        # Show what this user can access
        st.markdown(f"""
        <div class="access-info">
            🙍 Querying as <strong style="color:#e2e8f0">{active_user}</strong> —
            searching <strong style="color:#38bdf8">all shared</strong> documents
            + <strong style="color:#f59e0b">private</strong> documents owned by you.
        </div>
        """, unsafe_allow_html=True)

        with st.form("query_form"):
            question  = st.text_area("", placeholder="e.g. What is Para-Virtualization?",
                                     height=90, label_visibility="collapsed")
            submitted = st.form_submit_button("🔍 Search", use_container_width=True)

    with col_hint:
        st.markdown('<p class="section-header">Tips</p>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#1e293b;border-radius:10px;padding:1rem;color:#94a3b8;
                    font-size:0.82rem;line-height:1.8">
            💡 Ask specific questions<br>
            📄 Reference section names<br>
            🔢 Ask about tables & data<br>
            ❓ Multi-part questions work<br>
            🔒 Private docs only visible to their owner
        </div>
        """, unsafe_allow_html=True)

    if submitted:
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Searching documents and generating answer..."):
                resp, status = api_post("/query", json_data={
                    "question": question,
                    "user_id":  active_user,
                })

            if status != 200:
                st.error(f"API Error {status}: {resp.get('detail', resp)}")

            elif not resp.get("passed_gate"):
                st.markdown("""
                <div style="background:#1e293b;border-left:4px solid #f59e0b;border-radius:8px;
                            padding:1rem 1.2rem;color:#fbbf24;margin:1rem 0">
                    ⚠️ No relevant content found in your accessible documents for this question.
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                c1.metric("Top Score", f"{resp.get('top_score', 0):.4f}")
                c2.metric("Latency",   f"{resp.get('latency_ms')}ms")

            else:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Top Score",  f"{resp['top_score']:.4f}")
                c2.metric("Latency",    f"{resp['latency_ms']}ms")
                c3.metric("Sources",    len(resp["sources"]))
                c4.metric("Gate",       "✅ Passed")

                st.markdown('<p class="section-header">Answer</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="answer-box">{resp["answer"]}</div>',
                            unsafe_allow_html=True)

                st.markdown('<p class="section-header">Sources</p>', unsafe_allow_html=True)
                for src in resp["sources"]:
                    with st.expander(
                        f"📎 {src['filename']}  ·  Page {src['page_number']}  ·  Score {src['score']:.4f}"
                    ):
                        st.code(src["text_preview"], language=None)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

with tab_docs:
    col_list, col_upload = st.columns([3, 2])

    with col_list:
        st.markdown('<p class="section-header">Indexed Documents</p>', unsafe_allow_html=True)

        # Controls row
        ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 2])
        with ctrl1:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        with ctrl2:
            vis_filter = st.selectbox(
                "", ["shared", "private", "all"],
                label_visibility = "collapsed",
                key              = "vis_filter",
                help             = "Filter documents by visibility",
            )

        # Info banner
        if vis_filter == "private":
            st.markdown(f"""
            <div class="access-info">
                🔒 Showing private documents. Only those uploaded by
                <strong style="color:#f59e0b">{active_user}</strong> are visible.
            </div>
            """, unsafe_allow_html=True)
        elif vis_filter == "all":
            st.markdown(f"""
            <div class="access-info">
                👁️ Showing all documents accessible to
                <strong style="color:#e2e8f0">{active_user}</strong>
                (shared + own private).
            </div>
            """, unsafe_allow_html=True)

        # Fetch docs
        if vis_filter == "all":
            shared_resp, _  = api_get("/documents", params={"visibility": "shared"})
            private_resp, _ = api_get("/documents", params={
                "visibility": "private",
                "uploaded_by": active_user,
            })
            all_docs = shared_resp.get("documents", []) + private_resp.get("documents", [])
            # deduplicate by doc_id
            seen     = set()
            all_docs = [d for d in all_docs if not (d["doc_id"] in seen or seen.add(d["doc_id"]))]
            docs_resp   = {"documents": all_docs, "total": len(all_docs)}
            docs_status = 200
        elif vis_filter == "private":
            docs_resp, docs_status = api_get("/documents", params={
                "visibility":  "private",
                "uploaded_by": active_user,
            })
        else:
            docs_resp, docs_status = api_get("/documents", params={"visibility": "shared"})

        if docs_status != 200:
            st.error(f"Could not fetch documents: {docs_resp}")
        elif docs_resp.get("total", 0) == 0:
            st.markdown("""
            <div style="background:#1e293b;border:2px dashed #334155;border-radius:10px;
                        padding:2rem;text-align:center;color:#475569;margin-top:1rem">
                📂 No documents found.<br>
                <span style="font-size:0.85rem">Try a different filter or upload a PDF.</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            for doc in docs_resp["documents"]:
                is_private = doc.get("visibility") == "private"
                card_class = "doc-card doc-card-private" if is_private else "doc-card"
                owner_note = f"&nbsp;·&nbsp;👤 {doc.get('uploaded_by', '?')}"

                st.markdown(f"""
                <div class="{card_class}">
                    <p class="doc-title">📄 {doc['filename']}</p>
                    <p class="doc-meta">
                        {status_badge(doc['status'])} &nbsp;·&nbsp;
                        {doc['page_count']} pages &nbsp;·&nbsp;
                        {doc['chunk_count']} chunks &nbsp;·&nbsp;
                        {doc['file_size_mb']:.2f} MB &nbsp;·&nbsp;
                        {'📊 Tables' if doc['has_tables'] else 'No tables'}
                        {owner_note}
                        &nbsp;·&nbsp; {vis_badge(doc.get('visibility', 'shared'))}
                    </p>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"🗑️ Delete", key=f"del_{doc['doc_id']}"):
                    del_resp, del_status = api_delete(f"/documents/{doc['doc_id']}")
                    if del_status == 200:
                        st.success(del_resp["message"])
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {del_resp}")

    with col_upload:
        st.markdown('<p class="section-header">Upload New PDF</p>', unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                    padding:1rem;color:#64748b;font-size:0.82rem;margin-bottom:1rem;line-height:1.8">
            📏 Max <strong style="color:#94a3b8">100 pages</strong> per document<br>
            📦 Max <strong style="color:#94a3b8">200MB</strong> file size<br>
            📄 <strong style="color:#94a3b8">PDF only</strong>
        </div>
        """, unsafe_allow_html=True)

        with st.form("upload_form"):
            uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"])
            uploader_name = st.text_input("Uploaded by", value=active_user)
            visibility    = st.selectbox("Visibility", ["shared", "private"])
            upload_btn    = st.form_submit_button("⬆️ Upload & Ingest", use_container_width=True)

        if upload_btn:
            if uploaded_file is None:
                st.warning("Please select a PDF file.")
            else:
                with st.spinner(f"Ingesting **{uploaded_file.name}**..."):
                    up_resp, up_status = api_post(
                        "/documents/upload",
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                        data  = {"uploaded_by": uploader_name, "visibility": visibility},
                    )
                if up_status == 200:
                    st.success(f"✅ {up_resp['message']}")
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
        st.markdown('<p class="section-header">Health Check</p>', unsafe_allow_html=True)
        health, h_status = api_get("/health")

        if h_status != 200:
            st.error(f"Health check failed: {health}")
        else:
            overall = "🟢 ONLINE" if health["duckdb_ok"] and health["lancedb_ok"] else "🔴 DEGRADED"
            st.markdown(f"""
            <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                        padding:1.2rem;margin-bottom:1rem">
                <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0">{overall}</div>
                <div style="color:#64748b;font-size:0.8rem">DocInt v{health['version']}</div>
            </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.metric("Memory Used", f"{health['memory_used_gb']} GB")
            c2.metric("Memory Free", f"{health['memory_free_gb']} GB")
            c3, c4 = st.columns(2)
            c3.metric("DuckDB",  "✅ OK" if health["duckdb_ok"]  else "❌ Down")
            c4.metric("LanceDB", "✅ OK" if health["lancedb_ok"] else "❌ Down")

    with col_stats:
        st.markdown('<p class="section-header">Ingestion Stats</p>', unsafe_allow_html=True)
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

    # ── Chunk Inspector ────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-header">Chunk Inspector — Debug Tool</p>',
                unsafe_allow_html=True)
    st.caption("Inspect extracted text chunks per document to debug retrieval quality.")

    # Load all docs accessible to this user for the inspector
    shared_r, _  = api_get("/documents", params={"visibility": "shared"})
    private_r, _ = api_get("/documents", params={
        "visibility": "private", "uploaded_by": active_user
    })
    all_inspect  = shared_r.get("documents", []) + private_r.get("documents", [])
    seen_ids     = set()
    all_inspect  = [d for d in all_inspect if not (d["doc_id"] in seen_ids or seen_ids.add(d["doc_id"]))]

    if not all_inspect:
        st.info("No documents to inspect.")
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
            load_btn = st.button("🔎 Load", use_container_width=True)

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
