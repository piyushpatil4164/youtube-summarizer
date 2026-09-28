import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def get_secret(name: str, default: str = "") -> str:
    """Read a value from Streamlit Secrets first, then environment variables."""
    try:
        if name in st.secrets:
            value = st.secrets[name]
            if value is not None:
                return str(value).strip()
    except Exception:
        pass

    return os.getenv(name, default).strip()


def get_groq_api_key() -> str:
    key = get_secret("GROQ_API_KEY")
    if not key:
        raise ValueError("System configuration error: GROQ_API_KEY is not configured.")
    return key


def get_youtube_proxy_url() -> str:
    return get_secret("YOUTUBE_PROXY_URL") or get_secret("YOUTUBE_HTTP_PROXY")
