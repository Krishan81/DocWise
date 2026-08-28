"""
Centralized Streamlit session-state management.

APP.py should only read/write session state through the functions in this
file. This keeps "what data exists and when it resets" in one place instead
of scattered across the UI script.
"""

import streamlit as st


def _defaults():
    # A fresh dict/list is created on every call, so different user
    # sessions never accidentally share the same list/dict object.
    return {
        "messages": [],
        "documents": [],
        "all_chunks": [],
        "index": None,
        "analysis": None,
        "comparison": None,
        "risk_analysis": None,
        "last_results": [],
        "uploaded_file_info": [],
    }


def init_session_state():
    """Call once near the top of APP.py, before anything else runs."""

    defaults = _defaults()

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_for_new_upload():
    """Call whenever the set of uploaded files changes."""

    st.session_state.messages = []
    st.session_state.analysis = None
    st.session_state.comparison = None
    st.session_state.risk_analysis = None
    st.session_state.last_results = []


def store_processed_documents(documents, all_chunks, index):
    st.session_state.documents = documents
    st.session_state.all_chunks = all_chunks
    st.session_state.index = index


def get_processed_documents():
    return (
        st.session_state.documents,
        st.session_state.all_chunks,
        st.session_state.index,
    )
