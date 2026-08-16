import os
import streamlit as st
from dotenv import load_dotenv

# Load local environment variables if available
load_dotenv()

def get_groq_api_key() -> str:
    """
    Safely retrieves the Groq API key from Streamlit Cloud Secrets
    or local .env without exposing values in error stack traces.
    """
    api_key = None
    
    # 1. Try Streamlit Cloud secrets
    try:
        if "GROQ_API_KEY" in st.secrets:
            api_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

    # 2. Fallback to local environment variable
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("System configuration error: API key is not configured.")

    return api_key.strip()
