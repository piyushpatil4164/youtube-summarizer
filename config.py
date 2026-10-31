import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def get_secret(name: str, default: str = "") -> str:
    """Read a value from Streamlit Secrets first, then environment variables."""
    try:
        value = st.secrets.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass

    return os.getenv(name, default).strip()


def get_groq_api_key() -> str:
    key = get_secret("GROQ_API_KEY")
    if not key:
        raise ValueError(
            "GROQ_API_KEY is not configured. Add it in Streamlit Secrets."
        )
    return key


def get_youtube_proxy_url() -> str:
    """
    Optional HTTP/HTTPS proxy URL for YouTube requests.

    Example:
    YOUTUBE_PROXY_URL = "http://username:password@proxy-host:port"
    """
    return (
        get_secret("YOUTUBE_PROXY_URL")
        or get_secret("YOUTUBE_HTTP_PROXY")
    )
