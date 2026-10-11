import os
from dotenv import load_dotenv
load_dotenv()

try:
    import streamlit as st
    COHERE_API_KEY = st.secrets.get("COHERE_API_KEY", os.getenv("COHERE_API_KEY", ""))
except Exception:
    COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")

COHERE_MODEL    = "command-a-plus-05-2026"
CHUNK_SIZE      = 500
CHUNK_OVERLAP   = 50
TOP_K_CHUNKS    = 5
EMBED_MODEL     = "all-MiniLM-L6-v2"