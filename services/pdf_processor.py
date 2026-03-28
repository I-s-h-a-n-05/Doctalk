import fitz
import re
from config import CHUNK_SIZE, CHUNK_OVERLAP

def extract_text_by_page(pdf_bytes):
    """Extract text from PDF, returns list of {page, text} dicts."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages

def chunk_pages(pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Split pages into overlapping chunks for embedding.
    Each chunk carries its source page number.
    """
    chunks = []
    for p in pages:
        text = p["text"]
        words = text.split()
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append({
                "text":    chunk_text,
                "page":    p["page"],
                "start_w": start,
                "end_w":   end
            })
            if end == len(words):
                break
            start += chunk_size - overlap
    return chunks

def get_pdf_metadata(pdf_bytes, filename):
    """Extract title, page count, word count from PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    meta = doc.metadata or {}
    page_count = len(doc)
    word_count = sum(len(p.get_text().split()) for p in doc)
    doc.close()
    return {
        "filename":   filename,
        "title":      meta.get("title") or filename.replace(".pdf", ""),
        "pages":      page_count,
        "words":      word_count,
        "author":     meta.get("author", "Unknown"),
    }

def highlight_passage(pdf_bytes, page_num, passage_text):
    """
    Return a specific page as an image with the passage highlighted.
    Returns PNG bytes of the rendered page.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num - 1]

    # Search for the passage
    search_text = passage_text[:80].strip()
    instances = page.search_for(search_text)
    for inst in instances:
        highlight = page.add_highlight_annot(inst)
        highlight.set_colors(stroke=[1, 0.9, 0])
        highlight.update()

    # Render page to image
    mat = fitz.Matrix(1.8, 1.8)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes