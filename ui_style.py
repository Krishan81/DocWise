"""
All UI/UX concerns for DocWise: page config, theme CSS, header, and the
small reusable render_* helpers used across APP.py.

Nothing in this file touches the RAG pipeline, session state, or the
Gemini API — it only draws things. That separation means you can restyle
the whole app (new theme, new layout) without touching APP.py's logic,
and vice versa.
"""

import streamlit as st

PAGE_CSS = """
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');


/* =========================
   GLOBAL
   ========================= */

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}


.stApp {
    background:
        radial-gradient(
            circle at 10% 10%,
            rgba(99, 102, 241, 0.16),
            transparent 30%
        ),
        radial-gradient(
            circle at 90% 20%,
            rgba(139, 92, 246, 0.14),
            transparent 30%
        ),
        radial-gradient(
            circle at 50% 100%,
            rgba(59, 130, 246, 0.10),
            transparent 35%
        ),
        linear-gradient(
            135deg,
            #0b1020 0%,
            #111827 50%,
            #0f172a 100%
        );

    color: #f8fafc;
}


.block-container {
    max-width: 1200px;
    padding-top: 3rem;
    padding-bottom: 4rem;
}


/* =========================
   DOCWISE LOGO
   ========================= */

.docwise-logo {
    text-align: center;
    margin-bottom: 2rem;
}


.docwise-logo h1 {
    font-size: 3.2rem;
    font-weight: 800;
    letter-spacing: -2px;
    margin-bottom: 0.2rem;

    color: #a78bfa;

    background: linear-gradient(
        90deg,
        #60a5fa,
        #8b5cf6
    );

    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;

    transition: all 0.3s ease;
}


.docwise-logo h1:hover {
    transform: scale(1.04);

    filter:
        drop-shadow(
            0 0 12px
            rgba(139, 92, 246, 0.55)
        );
}


.docwise-subtitle {
    font-size: 1.15rem;
    color: #94a3b8;
    margin-bottom: 2rem;
}


/* =========================
   HEADINGS
   ========================= */

h2 {
    font-weight: 700 !important;
    letter-spacing: -0.5px;
}


h3 {
    font-weight: 600 !important;
}


p {
    color: #cbd5e1;
}


/* =========================
   UPLOAD BOX
   ========================= */

[data-testid="stFileUploader"] {
    background: rgba(255, 255, 255, 0.045);

    border: 1px dashed
        rgba(148, 163, 184, 0.45);

    border-radius: 18px;

    padding: 1.5rem;

    transition: all 0.25s ease;
}


[data-testid="stFileUploader"]:hover {
    transform: translateY(-2px);

    border-color: #818cf8;

    background:
        rgba(129, 140, 248, 0.08);

    box-shadow:
        0 10px 30px
        rgba(139, 92, 246, 0.12);
}


/* =========================
   DOCUMENT CARDS
   ========================= */

.doc-card {
    background:
        rgba(255, 255, 255, 0.055);

    border: 1px solid
        rgba(255, 255, 255, 0.08);

    border-radius: 18px;

    padding: 1.2rem;

    margin: 0.7rem 0;

    backdrop-filter: blur(12px);

    box-shadow:
        0 10px 30px
        rgba(0, 0, 0, 0.18);

    transition: all 0.25s ease;

    cursor: pointer;
}


.doc-card:hover {
    transform: translateY(-4px);

    border-color:
        rgba(129, 140, 248, 0.6);

    box-shadow:
        0 14px 35px
        rgba(99, 102, 241, 0.2);
}


.doc-card-name {
    font-weight: 600;
}


.doc-card-meta {
    color: #94a3b8;
}


.doc-card-badge {
    display: inline-block;
    margin-top: 0.5rem;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #c4b5fd;
    background: rgba(139, 92, 246, 0.16);
    border: 1px solid rgba(139, 92, 246, 0.35);
}


/* =========================
   BUTTONS
   ========================= */

.stButton > button {
    border: none;

    border-radius: 12px;

    padding: 0.65rem 1.3rem;

    font-weight: 600;

    background:
        linear-gradient(
            135deg,
            #6366f1,
            #8b5cf6
        );

    color: white;

    box-shadow:
        0 8px 20px
        rgba(99, 102, 241, 0.25);

    transition: all 0.2s ease;
}


.stButton > button:hover {
    transform:
        translateY(-2px)
        scale(1.02);

    box-shadow:
        0 12px 28px
        rgba(99, 102, 241, 0.4);
}


/* =========================
   TEXT INPUT
   ========================= */

.stTextInput input {
    background:
        rgba(255, 255, 255, 0.06);

    color: white;

    border: 1px solid
        rgba(148, 163, 184, 0.3);

    border-radius: 12px;

    transition: all 0.25s ease;
}


.stTextInput input:hover {
    border-color:
        rgba(139, 92, 246, 0.7);
}


.stTextInput input:focus {
    transform: translateY(-1px);

    border-color: #818cf8;

    box-shadow:
        0 0 0 1px #818cf8;
}


/* =========================
   CHAT
   ========================= */

[data-testid="stChatMessage"] {
    background:
        rgba(255, 255, 255, 0.045);

    border: 1px solid
        rgba(255, 255, 255, 0.07);

    border-radius: 16px;

    padding: 0.8rem;

    margin-bottom: 0.7rem;

    transition: all 0.2s ease;
}


[data-testid="stChatMessage"]:hover {
    border-color:
        rgba(139, 92, 246, 0.35);

    box-shadow:
        0 6px 20px
        rgba(139, 92, 246, 0.08);
}


/* =========================
   EXPANDERS
   ========================= */

[data-testid="stExpander"] {
    background:
        rgba(255, 255, 255, 0.035);

    border: 1px solid
        rgba(255, 255, 255, 0.08);

    border-radius: 14px;

    transition: all 0.25s ease;
}


[data-testid="stExpander"]:hover {
    border-color:
        rgba(139, 92, 246, 0.5);

    box-shadow:
        0 6px 20px
        rgba(0, 0, 0, 0.15);
}


/* =========================
   METRICS
   ========================= */

[data-testid="stMetric"] {
    background:
        rgba(255, 255, 255, 0.045);

    border: 1px solid
        rgba(255, 255, 255, 0.08);

    padding: 1rem;

    border-radius: 16px;

    transition: all 0.25s ease;
}


[data-testid="stMetric"]:hover {
    transform: translateY(-3px);

    border-color:
        rgba(96, 165, 250, 0.5);

    box-shadow:
        0 8px 25px
        rgba(96, 165, 250, 0.12);
}


/* =========================
   DIVIDER
   ========================= */

hr {
    border-color:
        rgba(255, 255, 255, 0.08);
}


/* =========================
   ALERTS
   ========================= */

[data-testid="stAlert"] {
    border-radius: 12px;
}


/* =========================
   SIDEBAR
   ========================= */

section[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            #0b1020,
            #111827
        );

    border-right:
        1px solid
        rgba(255, 255, 255, 0.07);
}

</style>
"""

HEADER_HTML = """
<div class="docwise-logo">

<h1>📄 DocWise</h1>

<div class="docwise-subtitle">
Your AI-powered document assistant
</div>

</div>
"""


def apply_page_config():
    """Must be the first Streamlit call in the app."""
    st.set_page_config(
        page_title="DocWise",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_css():
    st.markdown(PAGE_CSS, unsafe_allow_html=True)


def render_header():
    st.markdown(HEADER_HTML, unsafe_allow_html=True)


def render_document_card(name, num_pages, doc_type=None):
    badge_html = (
        f'<div class="doc-card-badge">{doc_type}</div>'
        if doc_type else ""
    )

    st.markdown(
        f"""
        <div class="doc-card">
        <span class="doc-card-name">📄 {name}</span>
        <br>
        <span class="doc-card-meta">{num_pages} pages</span>
        {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source_expander(title, similarity, body_text):
    with st.expander(f"{title} · match {similarity:.0%}"):
        st.write(body_text)
