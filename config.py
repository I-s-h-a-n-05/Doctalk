import os
from dotenv import load_dotenv
load_dotenv()

try:
    import streamlit as st
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
except Exception:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GROQ_MODEL      = "llama-3.3-70b-versatile"
CHUNK_SIZE      = 500
CHUNK_OVERLAP   = 50
TOP_K_CHUNKS    = 5
EMBED_MODEL     = "all-MiniLM-L6-v2"