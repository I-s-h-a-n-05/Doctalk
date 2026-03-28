import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from config import EMBED_MODEL, TOP_K_CHUNKS

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model

def build_index(chunks):
    """
    Embed all chunks and build a FAISS index.
    Returns (index, embeddings, chunks).
    Handles empty chunk lists gracefully.
    """
    if not chunks:
        dim = 384  # all-MiniLM-L6-v2 dimension
        index = faiss.IndexFlatIP(dim)
        return index, np.zeros((0, dim), dtype="float32"), chunks

    model = get_model()
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")

    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index, embeddings, chunks

def retrieve(query, index, chunks, top_k=TOP_K_CHUNKS):
    """
    Retrieve top-k most relevant chunks for a single document.
    Returns list of {text, page, score} dicts.
    """
    if not chunks or index.ntotal == 0:
        return []

    model = get_model()
    q_emb = model.encode([query], normalize_embeddings=True)
    q_emb = np.array(q_emb, dtype="float32")

    actual_k = min(top_k, len(chunks))
    scores, indices = index.search(q_emb, actual_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if 0 <= idx < len(chunks):
            results.append({
                "text":  chunks[idx]["text"],
                "page":  chunks[idx]["page"],
                "score": float(score)
            })
    return results

def retrieve_multi(query, documents, top_k_per_doc=3, global_top_k=8):
    """
    Cross-document retrieval: query every loaded document's FAISS index,
    merge all results, sort by score globally, return top global_top_k chunks.

    Each result dict includes:
      {text, page, score, doc_id, doc_title}

    Parameters
    ----------
    query        : str   — the user's question
    documents    : dict  — st.session_state.documents
                   {doc_id: {index, chunks, meta, ...}, ...}
    top_k_per_doc: int   — how many chunks to pull from each document
    global_top_k : int   — how many to keep after global re-ranking

    Returns
    -------
    List of result dicts sorted by score descending.
    """
    if not documents:
        return []

    model = get_model()
    q_emb = model.encode([query], normalize_embeddings=True)
    q_emb = np.array(q_emb, dtype="float32")

    all_results = []

    for doc_id, doc in documents.items():
        index  = doc.get("index")
        chunks = doc.get("chunks", [])
        title  = doc.get("meta", {}).get("title", doc_id)

        if not chunks or index is None or index.ntotal == 0:
            continue

        k = min(top_k_per_doc, len(chunks))
        scores, indices = index.search(q_emb, k)

        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(chunks):
                all_results.append({
                    "text":      chunks[idx]["text"],
                    "page":      chunks[idx]["page"],
                    "score":     float(score),
                    "doc_id":    doc_id,
                    "doc_title": title,
                })

    # Global re-rank by cosine similarity score (descending)
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:global_top_k]


# ── Confidence scoring ────────────────────────────────────────────────────────
# Thresholds tuned for all-MiniLM-L6-v2 cosine similarity (normalized).
# Scores are in [0, 1] range after inner-product search on unit vectors.
CONF_HIGH   = 0.55   # strong semantic match
CONF_MEDIUM = 0.35   # partial / loose match


def score_confidence(retrieved_chunks):
    """
    Assess retrieval confidence from a list of scored chunks.

    Returns a dict:
      {
        "level":      "high" | "medium" | "low",
        "top_score":  float,     # best single chunk similarity
        "avg_score":  float,     # mean across returned chunks
        "label":      str,       # short display label
        "reason":     str,       # one-line explanation for the UI
      }

    Works for both single-doc (retrieve) and cross-doc (retrieve_multi) results.
    """
    if not retrieved_chunks:
        return {
            "level": "low", "top_score": 0.0, "avg_score": 0.0,
            "label": "No results",
            "reason": "No relevant passages were found in the document(s).",
        }

    scores    = [c["score"] for c in retrieved_chunks]
    top_score = max(scores)
    avg_score = sum(scores) / len(scores)

    if top_score >= CONF_HIGH:
        return {
            "level": "high", "top_score": top_score, "avg_score": avg_score,
            "label": "High confidence",
            "reason": f"Strong semantic match found (similarity {top_score:.2f}).",
        }
    elif top_score >= CONF_MEDIUM:
        return {
            "level": "medium", "top_score": top_score, "avg_score": avg_score,
            "label": "Medium confidence",
            "reason": (
                f"Partial match — the document may cover this topic indirectly "
                f"(similarity {top_score:.2f}). Verify key details against the source."
            ),
        }
    else:
        return {
            "level": "low", "top_score": top_score, "avg_score": avg_score,
            "label": "Low confidence",
            "reason": (
                f"Weak semantic match (similarity {top_score:.2f}). "
                "The document likely does not contain a direct answer. "
                "The response may be incomplete or imprecise."
            ),
        }