# 📄 DocWise

DocWise is an AI-powered document assistant built with Streamlit and the
Gemini API. Upload one or more PDFs and:

- **Chat** with your documents using retrieval-augmented generation (RAG)
- **Analyze** documents into a structured summary (key points, dates,
  financial info, responsibilities, warnings, etc.)
- **Detect risks** — potentially important or unusual clauses, flagged by
  severity
- **Compare documents** side by side to surface meaningful differences

Answers are grounded only in the uploaded documents — DocWise is instructed
not to use outside knowledge and to say so when something isn't covered.

---

## How it works

1. **Extract** — PDF text is pulled page-by-page (`pdf_loader.py`, using
   PyMuPDF).
2. **Chunk** — page text is split into overlapping chunks with page-range
   metadata attached (`chunker.py`).
3. **Embed** — each chunk is embedded with `gemini-embedding-001` and
   indexed in a FAISS vector index using cosine similarity
   (`vector_store.py`).
4. **Retrieve** — a question is embedded and matched against the index;
   only chunks above a similarity threshold are kept.
5. **Generate** — matched chunks are passed as context to
   `gemini-3.6-flash`, which answers using only that context
   (`prompts.py` holds all prompt templates).

---

## Project structure

```
.
├── APP.py                       # Streamlit UI + orchestration (entry point)
├── vector_store.py               # Embeddings, FAISS index, retrieval, generation
├── chunker.py                    # Splits extracted page text into chunks
├── pdf_loader.py                 # PDF → per-page text extraction
├── session.py                    # st.session_state init/access, single source of truth
├── ui_style.py                   # Page config, CSS theme, header, card rendering
├── api_utils.py                  # Shared Gemini-call error handling (quota, etc.)
├── prompts.py                    # All LLM prompt templates
├── requirements.txt
├── .gitignore
└── .streamlit/
    └── secrets.toml.example      # Template only — real secrets.toml is git-ignored
```

---

## Setup (local)

**1. Clone and install dependencies**

```bash
git clone https://github.com/Krishan81/DocWise.git
cd DocWise
pip install -r requirements.txt
```

**2. Add your Gemini API key**

Create a `.env` file in the project root (this file is git-ignored, never
commit it):

```
GEMINI_API_KEY=your-real-key-here
```

Get a key from [Google AI Studio](https://aistudio.google.com/) if you
don't have one yet.

**3. Run the app**

```bash
streamlit run APP.py
```

The app opens at `http://localhost:8501`. Upload a PDF and start asking
questions.

---

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub (`.env` and `.streamlit/secrets.toml` stay out
   automatically, thanks to `.gitignore`).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with
   GitHub, and create a new app pointing at this repo with `APP.py` as the
   main file.
3. In the app's **Settings → Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your-real-key-here"
   ```
4. Deploy. `APP.py` reads the key via `os.getenv(...)` locally or
   `st.secrets.get(...)` on Streamlit Cloud automatically — no code changes
   needed between environments.

---

## Notes

- All document data lives in `st.session_state` for the duration of a
  browser session — nothing is persisted to disk or a database. Uploading
  a new/different set of files resets chat history and analysis results.
- Retrieval uses a `min_similarity` cosine threshold (default `0.55` in
  `vector_store.py`) to avoid pulling in irrelevant chunks — tune this if
  answers seem too sparse or too noisy for your documents.
- `multi_query_search(..., expand_query=True)` can be enabled for better
  retrieval on vaguely-worded questions, at the cost of one extra Gemini
  call per question.

## Disclaimer

DocWise explains document content in plain language but does not provide
legal, financial, or professional advice. Always consult a qualified
professional for decisions based on document terms.
