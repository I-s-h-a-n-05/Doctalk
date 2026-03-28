from fpdf import FPDF
import io
from datetime import datetime


def export_chat_as_text(doc_title, chat_history):
    """Export chat as a clean, readable plain text string."""
    lines = [
        "DocTalk — Conversation Export",
        f"Document : {doc_title}",
        f"Exported  : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Messages  : {len(chat_history)}",
        "=" * 64,
        "",
    ]
    for i, turn in enumerate(chat_history, 1):
        role = "You" if turn["role"] == "user" else "DocTalk"
        lines.append(f"[{i}] {role}")
        lines.append("-" * 40)
        lines.append(turn["content"])
        lines.append("")
    return "\n".join(lines)


def _clean(text):
    """Replace Unicode characters unsupported by Helvetica with ASCII equivalents."""
    replacements = {
        "\u2014": "-",   # em dash
        "\u2013": "-",   # en dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2022": "*",   # bullet
        "\u2026": "...", # ellipsis
        "\u00e9": "e", "\u00e8": "e", "\u00ea": "e",
        "\u00e0": "a", "\u00e2": "a",
        "\u00f4": "o", "\u00fb": "u", "\u00ee": "i",
        "\u00e7": "c", "\u00f1": "n",
        "\u2192": "->",  # right arrow
        "\u2190": "<-",  # left arrow
        "\u00b7": "*",   # middle dot
        "\u00d7": "x",   # multiplication sign
        "\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


def _strip_markdown(text):
    """Remove common markdown syntax for clean PDF rendering."""
    # Bold: **text** or __text__
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__",     r"\1", text)
    # Italic: *text* or _text_
    text = re.sub(r"\*(.*?)\*",     r"\1", text)
    text = re.sub(r"_(.*?)_",       r"\1", text)
    # Inline code: `text`
    text = re.sub(r"`(.*?)`",       r"\1", text)
    # Headers: ## or ### etc.
    text = re.sub(r"^#{1,6}\s+",    "",    text, flags=re.MULTILINE)
    return text


def export_chat_as_pdf(doc_title, chat_history):
    """Export chat history as a polished, readable PDF. Returns bytes."""
    import re  # local import to keep module-level clean if _strip_markdown is called

    # Patch _strip_markdown's re dependency
    def strip_md(text):
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"__(.*?)__",     r"\1", text)
        text = re.sub(r"\*(.*?)\*",     r"\1", text)
        text = re.sub(r"_(.*?)_",       r"\1", text)
        text = re.sub(r"`(.*?)`",       r"\1", text)
        text = re.sub(r"^#{1,6}\s+",    "",    text, flags=re.MULTILINE)
        return text

    pdf = FPDF()
    pdf.set_margins(left=18, top=18, right=18)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Cover header ─────────────────────────────────────────────────────────
    # Brand name
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(16, 185, 129)   # DocTalk green
    pdf.cell(0, 10, "DocTalk", ln=True)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, "Conversation Export", ln=True)
    pdf.ln(4)

    # Divider
    pdf.set_draw_color(230, 230, 230)
    pdf.set_line_width(0.4)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(5)

    # Metadata block
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(28, 5, "DOCUMENT", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 5, _clean(doc_title), ln=True)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(28, 5, "EXPORTED", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 5, datetime.now().strftime("%Y-%m-%d at %H:%M"), ln=True)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(28, 5, "MESSAGES", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 5, str(len(chat_history)), ln=True)

    pdf.ln(5)
    pdf.set_draw_color(230, 230, 230)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(8)

    # ── Conversation turns ────────────────────────────────────────────────────
    for i, turn in enumerate(chat_history, 1):
        is_user = turn["role"] == "user"
        content = _clean(strip_md(turn["content"]))

        if is_user:
            # User label
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(100, 100, 210)   # soft indigo
            pdf.cell(0, 5, f"YOU  [{i}]", ln=True)
            # User bubble — light indigo tint background
            pdf.set_fill_color(245, 245, 255)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, content, fill=True)
        else:
            # DocTalk label
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(16, 140, 90)     # DocTalk green
            pdf.cell(0, 5, f"DOCTALK  [{i}]", ln=True)
            # Assistant bubble — light green tint background
            pdf.set_fill_color(240, 255, 248)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, content, fill=True)

        pdf.ln(5)

        # Subtle separator between turns (not after last)
        if i < len(chat_history):
            pdf.set_draw_color(240, 240, 240)
            pdf.line(18, pdf.get_y(), 192, pdf.get_y())
            pdf.ln(5)

    # ── Footer on last page ───────────────────────────────────────────────────
    pdf.ln(4)
    pdf.set_draw_color(220, 220, 220)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(180, 180, 180)
    pdf.cell(0, 5, _clean("Generated by DocTalk - AI-powered document intelligence"), ln=True, align="C")

    return bytes(pdf.output())