import os
import json

import streamlit as st
from dotenv import load_dotenv
from google import genai

from pdf_loader import extract_text
from chunker import create_chunks

from session import (
    init_session_state,
    reset_for_new_upload,
    store_processed_documents,
    get_processed_documents,
)

from ui_style import (
    apply_page_config,
    inject_css,
    render_header,
    render_document_card,
    render_source_expander,
)

from api_utils import safe_call
import prompts

from vector_store import (
    GENERATION_MODEL,
    create_embeddings,
    create_faiss_index,
    multi_query_search,
    create_context,
    create_chat_history,
    generate_answer,
    detect_document_type,
    detect_risks,
    compare_documents,
)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

apply_page_config()          # must be the first Streamlit call
init_session_state()
inject_css()
render_header()

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("Gemini API key not found. Check your .env file.")
    st.stop()

client = genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Cached pipeline steps
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def process_document(uploaded_file):
    pages = extract_text(uploaded_file)
    chunks = create_chunks(pages)
    return pages, chunks


@st.cache_data(show_spinner=False)
def create_document_embeddings(_client, chunks):
    return create_embeddings(_client, chunks)


@st.cache_resource(show_spinner=False)
def create_document_index(embeddings):
    return create_faiss_index(embeddings)


@st.cache_data(show_spinner=False)
def classify_document(document_text):
    return detect_document_type(client, document_text)


@st.cache_data(show_spinner=False)
def analyze_risks_cached(document_text):
    return detect_risks(client, document_text)


def full_text(pages):
    return "\n".join(page["text"] for page in pages)


def combine_document_texts(documents):
    combined = ""
    for document in documents:
        combined += f"\n\nDOCUMENT: {document['name']}\n"
        for page in document["pages"]:
            combined += f"\nPage {page['page']}:\n"
            combined += page["text"]
    return combined


def source_title(chunk):
    if chunk["start_page"] == chunk["end_page"]:
        return f"📄 {chunk['document_name']} — Page {chunk['start_page']}"
    return (
        f"📄 {chunk['document_name']} — "
        f"Pages {chunk['start_page']}-{chunk['end_page']}"
    )


# ---------------------------------------------------------------------------
# Upload + one-time ingestion
# ---------------------------------------------------------------------------

uploaded_files = st.file_uploader(
    "Upload PDF documents",
    type=["pdf"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Upload one or more PDF documents to get started.")
    st.stop()

current_files = [(f.name, f.size) for f in uploaded_files]

if current_files != st.session_state.uploaded_file_info:

    reset_for_new_upload()
    st.session_state.uploaded_file_info = current_files

    documents = []
    all_chunks = []

    for uploaded_file in uploaded_files:

        pages, chunks = process_document(uploaded_file)
        document_text = full_text(pages)

        with st.spinner(f"Identifying {uploaded_file.name}..."):
            document_type, error = safe_call(
                classify_document,
                document_text,
                error_prefix="Could not identify document type",
            )
            if error:
                document_type = "Unable to identify"

        documents.append({
            "name": uploaded_file.name,
            "pages": pages,
            "type": document_type,
        })

        for chunk in chunks:
            chunk["document_name"] = uploaded_file.name
            all_chunks.append(chunk)

    if not all_chunks:
        st.error("No text could be extracted from the uploaded documents.")
        st.stop()

    with st.spinner("Creating document embeddings..."):
        embeddings, error = safe_call(
            create_document_embeddings,
            client,
            all_chunks,
            error_prefix="Could not create embeddings",
        )

        if error:
            st.error(error)
            st.stop()

        index = create_document_index(embeddings)

    store_processed_documents(documents, all_chunks, index)

# Session state is the single source of truth from here on — we never
# recompute documents/chunks/index locally on later reruns.
documents, all_chunks, index = get_processed_documents()

st.success(
    f"{len(documents)} PDF(s) loaded — "
    f"{len(all_chunks)} chunks, {index.ntotal} vectors indexed."
)

st.subheader("📚 Uploaded Documents")

for document in documents:
    render_document_card(
        document["name"],
        len(document["pages"]),
        document.get("type"),
    )

st.divider()


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

st.subheader("💬 Chat with your documents")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask something about your documents...")

if question:

    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):

        with st.spinner("Searching documents..."):
            results, error = safe_call(
                multi_query_search,
                client, index, all_chunks, question,
                error_prefix="Search failed",
            )
            if error:
                st.error(error)
                results = []

        st.session_state.last_results = results or []

        if not results:
            answer = "This information is not mentioned in the uploaded documents."
            st.write(answer)

        else:
            context = create_context(results)
            chat_history = create_chat_history(st.session_state.messages)

            with st.spinner("Generating answer..."):
                answer, error = safe_call(
                    generate_answer,
                    client, question, context, chat_history,
                    error_prefix="Could not generate answer",
                )
                if error:
                    answer = error

            st.write(answer)

            st.subheader("📚 Sources")
            for result in results:
                chunk = result["chunk"]
                render_source_expander(
                    source_title(chunk),
                    result["similarity"],
                    chunk["text"],
                )

    st.session_state.messages.append({"role": "assistant", "content": answer})


st.divider()


# ---------------------------------------------------------------------------
# Document tools: analyze / compare / risks
# ---------------------------------------------------------------------------

st.subheader("🔍 Document Tools")

col1, col2, col3 = st.columns(3)

with col1:
    analyze_button = st.button("📋 Analyze Documents")

with col2:
    compare_button = st.button(
        "🔍 Compare Documents",
        disabled=len(documents) < 2,
    )

with col3:
    risk_button = st.button("⚠️ Find Important Clauses")


# --- Analyze -----------------------------------------------------------

if analyze_button:
    combined_text = combine_document_texts(documents)
    prompt = prompts.document_analysis_prompt(combined_text)

    with st.spinner("Analyzing documents..."):
        response, error = safe_call(
            client.models.generate_content,
            model=GENERATION_MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json"},
            error_prefix="Analysis failed",
        )

    if error:
        st.error(error)
    else:
        try:
            # This assignment was missing before — analysis was computed
            # but never saved, so the results never actually showed up.
            st.session_state.analysis = json.loads(response.text.strip())
        except json.JSONDecodeError:
            st.error("Gemini returned an invalid JSON response.")
            st.code(response.text)

if st.session_state.analysis:

    analysis = st.session_state.analysis

    st.subheader("📋 Document Analysis")

    st.markdown("### 📄 Documents")
    for document in analysis.get("documents", []):
        st.write(f"- {document}")

    st.markdown("### 📝 Overall Summary")
    st.write(analysis.get("overall_summary", ""))

    sections = [
        ("🔎 Key Points", "key_points"),
        ("💰 Financial Information", "financial_information"),
        ("📅 Important Dates", "important_dates"),
        ("👤 Responsibilities", "responsibilities"),
        ("📌 Important Clauses", "important_clauses"),
        ("⚠️ Warnings", "warnings"),
        ("❓ Questions You Should Consider", "questions_to_consider"),
    ]

    for title, key in sections:
        items = analysis.get(key, [])
        if items:
            st.markdown(f"### {title}")
            for item in items:
                st.write(f"- {item}")


# --- Risks ---------------------------------------------------------------

if risk_button:
    combined_text = combine_document_texts(documents)

    with st.spinner("Checking important clauses..."):
        risk_response, error = safe_call(
            analyze_risks_cached,
            combined_text,
            error_prefix="Risk analysis failed",
        )

    if error:
        st.error(error)
    else:
        try:
            st.session_state.risk_analysis = json.loads(risk_response)
        except json.JSONDecodeError:
            st.error("Could not process risk analysis.")

if st.session_state.risk_analysis:

    st.subheader("⚠️ Potentially Important Clauses")

    risks = st.session_state.risk_analysis.get("risks", [])

    if not risks:
        st.success("No potentially important clauses were detected.")
    else:
        for risk in risks:
            severity = risk.get("severity", "Low")
            title = risk.get("title", "Important Clause")
            explanation = risk.get("explanation", "")
            source = risk.get("source", "")

            st.markdown(f"### ⚠️ {severity} — {title}")
            st.write(explanation)

            if source:
                with st.expander("View relevant text"):
                    st.write(source)


# --- Compare ---------------------------------------------------------------

if compare_button:
    with st.spinner("Comparing documents..."):
        comparison_response, error = safe_call(
            compare_documents,
            client, documents,
            error_prefix="Comparison failed",
        )

    if error:
        st.error(error)
    else:
        try:
            st.session_state.comparison = json.loads(comparison_response)
        except json.JSONDecodeError:
            st.error("Gemini returned invalid comparison data.")

if st.session_state.comparison:

    comparison = st.session_state.comparison

    st.subheader("🔍 Document Comparison")

    st.markdown("### 📚 Documents Compared")
    for document in comparison.get("documents_compared", []):
        st.write(f"- {document}")

    st.markdown("### 📝 Summary")
    st.write(comparison.get("summary", ""))

    changes = comparison.get("changes", [])
    if changes:
        st.markdown("### 🔄 Changes")
        for change in changes:
            st.markdown(f"#### {change.get('category', 'Change')}")
            st.write(f"**Document 1:** {change.get('document_1', '')}")
            st.write(f"**Document 2:** {change.get('document_2', '')}")
            st.write(change.get("explanation", ""))

    important_changes = comparison.get("important_changes", [])
    if important_changes:
        st.markdown("### ⚠️ Important Changes")
        for item in important_changes:
            st.warning(item)

    warnings = comparison.get("warnings", [])
    if warnings:
        st.markdown("### 🚨 Warnings")
        for item in warnings:
            st.error(item)


st.divider()


# ---------------------------------------------------------------------------
# Debug / transparency panels
# ---------------------------------------------------------------------------

with st.expander("🔍 Retrieval Details"):
    if st.session_state.last_results:
        for i, result in enumerate(st.session_state.last_results):
            chunk = result["chunk"]
            st.write(f"Result {i + 1}")
            st.write(f"Document: {chunk['document_name']}")
            st.write(f"Pages: {chunk['start_page']}-{chunk['end_page']}")
            st.write(f"Similarity: {result['similarity']:.4f}")
    else:
        st.write("Ask a question to see retrieval details here.")

st.divider()

with st.expander("📖 View Document Chunks"):
    for i, chunk in enumerate(all_chunks):
        st.write(f"### Chunk {i + 1}")
        st.write(f"Document: {chunk['document_name']}")
        st.write(f"Pages: {chunk['start_page']} - {chunk['end_page']}")
        st.write(chunk["text"])

# streamlit run APP.py
