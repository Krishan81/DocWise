"""
Small helper to stop re-writing the same try/except/429-check block
every time we call the Gemini API from APP.py.
"""

QUOTA_EXCEEDED_MSG = (
    "Gemini API quota exceeded. Please wait a moment and try again."
)


def is_quota_error(error):
    return "429" in str(error)


def safe_call(fn, *args, error_prefix="Request failed", **kwargs):
    """
    Runs fn(*args, **kwargs) and returns a (result, error_message) tuple.

    - On success: (result, None)
    - On failure: (None, "<friendly error message>")

    Usage:
        answer, error = safe_call(generate_answer, client, question, context)
        if error:
            st.error(error)
        else:
            st.write(answer)
    """

    try:
        return fn(*args, **kwargs), None
    except Exception as e:
        if is_quota_error(e):
            return None, QUOTA_EXCEEDED_MSG
        return None, f"{error_prefix}: {e}"
