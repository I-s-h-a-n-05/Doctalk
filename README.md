# DocTalk — AI Document Q&A with RAG

> Upload any PDF and ask questions in natural language. DocTalk retrieves the most relevant passages using vector search and generates grounded answers with exact page citations — no hallucinations.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red?style=flat-square)
![RAG](https://img.shields.io/badge/Architecture-RAG-purple?style=flat-square)
![LLM](https://img.shields.io/badge/LLM-Llama3--70B-orange?style=flat-square)

---

## Features

| Feature | Description |
|---|---|
| **RAG pipeline** | Chunks → FAISS vector index → semantic retrieval → grounded generation |
| **Auto-summary** | Document summarized instantly on upload with key topics and suggested questions |
| **Source citations** | Every answer includes exact page numbers used |
| **Passage highlighting** | Shows the exact excerpt the answer was drawn from |
| **Multi-document** | Upload up to 5 PDFs and switch between them |
| **Multi-turn chat** | Full conversation history maintained per document |
| **Voice input** | Ask questions by voice using browser Web Speech API |
| **Chat export** | Download full Q&A session as PDF or text file |

## Tech stack

```
UI              Streamlit (Notion-style light theme)
PDF parsing     PyMuPDF (fitz)
Embeddings      sentence-transformers (all-MiniLM-L6-v2)
Vector search   FAISS (IndexFlatIP — cosine similarity)
LLM             Llama3-70B via Groq API (free, fast)
Export          fpdf2
```

## Setup

```bash
git clone https://github.com/YOURUSERNAME/DocTalk.git
cd DocTalk
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "your_groq_key"
```

Run:
```bash
streamlit run app.py
```

## Architecture

```
PDF upload
    │
    ▼
PyMuPDF → extract text by page
    │
    ▼
Chunk into 500-token segments (50 token overlap)
    │
    ▼
sentence-transformers → embed all chunks
    │
    ▼
FAISS index (cosine similarity)
    │
    ▼
User question → embed → retrieve top-5 chunks
    │
    ▼
Groq LLM (Llama3-70B) → grounded answer with page citations
```

## License

MIT