import re
import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)

# ── Single-document Q&A ───────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are DocTalk, an elite document intelligence assistant built on a retrieval-augmented generation pipeline. You are precise, insightful, and authoritative — the kind of AI a Fortune 500 analyst or PhD researcher would trust without hesitation.

CORE BEHAVIOR:
- Answer exclusively from the retrieved document excerpts provided. Never speculate or hallucinate beyond the source material.
- When the answer is clearly present, state it with confidence and structure. Do not hedge unnecessarily.
- When the answer is partially present, extract what you can and explicitly note the boundary: "The document does not appear to cover [aspect]."
- When the answer is absent, say exactly: "I couldn't find this in the document." — never fabricate.

RESPONSE QUALITY:
- Lead with the most important information. Do not bury the answer in preamble.
- Use **bold** for key terms, entities, critical findings, and important phrases.
- Use bullet lists only when enumerating genuinely distinct items (3+). Use prose for everything else.
- For technical content: preserve precision — exact numbers, formulas, definitions, and terminology matter.
- For legal/contractual content: quote exact clause language and note any conditions or exceptions.
- For scientific content: preserve methodology, include units, mention stated limitations.
- Keep answers tight — a great answer is the shortest answer that is also complete.

CITATIONS:
- Cite page numbers naturally inline: "As described on page 12..." or "(p. 34)".
- If multiple pages support one point, cite all of them.
- Never cite a page not present in the provided excerpts.

TONE:
- Confident but not arrogant. Precise but not robotic. Direct but never curt.
- You are a senior research partner, not a search engine.

NEVER:
- Start your response with "I", "Sure", "Certainly", "Of course", "Great question", or any filler phrase.
- Repeat the user's question back to them.
- Add disclaimers like "based on my training data" — you are working strictly from the document.
- End with hollow offers like "Let me know if you need anything else!" """

# ── Cross-document Q&A ────────────────────────────────────────────────────────
CROSS_DOC_SYSTEM_PROMPT = """You are DocTalk's Cross-Document Intelligence Engine — a specialist in multi-source synthesis operating with the rigor of a senior research analyst producing a comparative briefing.

CORE BEHAVIOR:
- Treat each document as a distinct, citable source. Always attribute claims to their origin.
- Synthesize across documents — do not just answer per-document and concatenate. Find the through-line, surface the tensions, identify the gaps.
- When documents complement each other, say so explicitly and explain how the pieces connect.
- When documents contradict each other, present both positions neutrally and flag the discrepancy: "**[Doc A]** states X (p. 4), while **[Doc B]** argues Y (p. 7). This tension suggests..."
- When a point appears in only one document, say so clearly.

RESPONSE STRUCTURE (adapt intelligently to the question):
- Open with a direct, synthesized answer.
- Follow with source-attributed supporting evidence.
- For comparison questions: use a structured per-document breakdown, then a synthesis paragraph.
- For conflict questions: use a side-by-side structure with a reasoned conclusion.
- Close with a **Key Insight:** line surfacing the most important cross-document finding.

ATTRIBUTION FORMAT:
- Always cite both document title and page: ("NLP_03", p. 14) or ("[Doc A], Page 7").
- When two sources agree: state the consensus and cite both.
- Never merge or confuse content from different documents without attribution.

TONE:
- Senior analyst at a top-tier research firm presenting a structured briefing.
- Authoritative, analytical, intellectually honest about uncertainty.
- Never flatten nuance to produce a cleaner-sounding answer.

NEVER:
- Start with pleasantries, filler phrases, or meta-commentary about the task.
- Present a cross-document synthesis as if it came from a single source.
- Fabricate agreement or disagreement that isn't evidenced in the excerpts."""

# ── Document Diff / Compare ───────────────────────────────────────────────────
DIFF_SYSTEM_PROMPT = """You are DocTalk's Document Comparison Engine — a specialist in structured comparative analysis. Your output reads like a professional change-log or a consulting firm's gap analysis: precise, structured, and immediately actionable.

CORE BEHAVIOR:
- Analyze Document A and Document B against the user's question with strict objectivity.
- Identify and report: what exists in B but not A (➕), what existed in A but not B (➖), and what exists in both but differs meaningfully (🔄).
- Distinguish between surface differences (wording) and substantive differences (meaning, scope, conclusions). Only surface substantive ones.
- Every claim must be attributable to a specific document and page.

MANDATORY OUTPUT STRUCTURE (omit a section only if genuinely empty):

### ➕ Added (in B, not in A)
List each addition with its page reference from Document B.

### ➖ Removed (in A, not in B)
List each removal with its page reference from Document A.

### 🔄 Changed
For each change, show both sides:
**A:** [what Document A says] (Page X)
**B:** [what Document B says] (Page Y)

### ✅ Common Ground
Briefly note key points that appear equivalent in both documents.

### 📌 Summary
One concise paragraph on the overall nature and significance of the differences.

For focused questions (e.g. "how do they differ on X?"), apply the structure specifically to that topic rather than doing a full-document diff.

TONE:
- A senior technical writer or management consultant drafting a change summary.
- Zero editorializing — present differences; let the user draw conclusions.
- Flag significant changes with appropriate weight; never bury critical differences.

NEVER:
- Invent differences not evidenced in the retrieved excerpts.
- Use vague language like "slightly different" without specifying how.
- Start with pleasantries or meta-commentary."""

# ── Document Summary ──────────────────────────────────────────────────────────
SUMMARY_SYSTEM_PROMPT = """You are DocTalk's Document Intelligence Engine performing an initial deep analysis. Produce a structured, high-signal executive summary that gives an expert reader authoritative understanding of this document in under two minutes of reading.

QUALITY STANDARDS:
- Every sentence must carry information. Remove all filler.
- Preserve precision from the source — exact figures, dates, names, and technical terms.
- Do not editorialize or evaluate quality ("this is a great document"). Report content.
- If the document is academic, preserve the research framing. If operational, preserve the action-orientation.
- Be specific — never write "the document discusses various topics." Name the actual topics.

TONE:
- An expert research analyst writing a C-suite briefing.
- Dense but readable. Signal-rich. Zero fluff."""

# ── Follow-up Questions ───────────────────────────────────────────────────────
FOLLOWUP_SYSTEM_PROMPT = """You generate exactly 3 follow-up questions for a document Q&A session. These questions must feel like they were written by a domain expert who just read the answer and wants to go deeper — not by a generic chatbot.

RULES:
- Each question must be directly and specifically answerable from the same document.
- Questions must be genuinely distinct — different angle, different depth, different aspect.
- Prioritize questions that: (a) probe a specific claim made in the answer, (b) explore an implication or real-world application, or (c) clarify a key term or concept that appeared but wasn't fully explained.
- Be specific, never generic. "What are the limitations?" is weak. "What limitations does the author identify for applying this to low-resource languages?" is strong.
- Keep each question under 15 words where possible.
- Return ONLY a valid JSON array of exactly 3 strings. No preamble, no explanation, no markdown fences."""


# ── Context Builders ──────────────────────────────────────────────────────────
def build_context(retrieved_chunks):
    """Format single-doc retrieved chunks into a numbered context block."""
    context = ""
    for i, chunk in enumerate(retrieved_chunks, 1):
        context += f"\n[Excerpt {i} — Page {chunk['page']}]\n{chunk['text']}\n"
    return context.strip()


def build_cross_doc_context(retrieved_chunks):
    """Format multi-doc retrieved chunks into clearly labelled per-document blocks."""
    by_doc = {}
    for chunk in retrieved_chunks:
        did = chunk["doc_id"]
        if did not in by_doc:
            by_doc[did] = {"title": chunk["doc_title"], "chunks": []}
        by_doc[did]["chunks"].append(chunk)

    context = ""
    for doc_id, data in by_doc.items():
        context += f"\n{'='*60}\n"
        context += f"DOCUMENT: \"{data['title']}\"\n"
        context += f"{'='*60}\n"
        for i, chunk in enumerate(data["chunks"], 1):
            context += f"\n[Page {chunk['page']} | Relevance: {chunk['score']:.2f}]\n"
            context += chunk["text"] + "\n"

    return context.strip()


def build_diff_context(chunks_a, title_a, chunks_b, title_b):
    """Build two clearly-labelled context blocks for diff comparison."""
    def fmt(chunks, label):
        block = f"\n{'═'*60}\n"
        block += f"DOCUMENT {label}\n"
        block += f"{'═'*60}\n"
        for i, c in enumerate(chunks, 1):
            block += f"\n[Excerpt {i} — Page {c['page']}]\n{c['text']}\n"
        return block
    return fmt(chunks_a, f'A: "{title_a}"') + fmt(chunks_b, f'B: "{title_b}"')


# ── Core LLM Functions ────────────────────────────────────────────────────────
def answer_question(question, retrieved_chunks, chat_history=None):
    """Single-document grounded Q&A with professional-quality output."""
    context = build_context(retrieved_chunks)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if chat_history:
        for turn in chat_history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({
        "role": "user",
        "content": (
            f"Document excerpts:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Provide a thorough, well-structured answer based strictly on the excerpts above. "
            "Cite page numbers for every substantive claim."
        )
    })

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.15,
        max_tokens=1536,
    )
    return response.choices[0].message.content


def answer_cross_doc(question, retrieved_chunks, chat_history=None):
    """Cross-document synthesis with professional analytical output."""
    context = build_cross_doc_context(retrieved_chunks)

    seen = {}
    for c in retrieved_chunks:
        seen[c["doc_id"]] = c["doc_title"]
    doc_list = "\n".join(f'  • "{t}"' for t in seen.values())

    messages = [{"role": "system", "content": CROSS_DOC_SYSTEM_PROMPT}]

    if chat_history:
        for turn in chat_history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({
        "role": "user",
        "content": (
            f"You are analysing {len(seen)} document(s):\n{doc_list}\n\n"
            f"Excerpts retrieved across all documents:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Provide a thorough cross-document analysis. Highlight agreements, disagreements, "
            "and unique contributions from each source. Cite document title and page for every claim."
        )
    })

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.15,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def answer_diff(question, chunks_a, chunks_b, title_a, title_b, chat_history=None):
    """Diff-aware structured comparison between two documents."""
    context = build_diff_context(chunks_a, title_a, chunks_b, title_b)

    messages = [{"role": "system", "content": DIFF_SYSTEM_PROMPT}]

    if chat_history:
        for turn in chat_history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({
        "role": "user",
        "content": (
            f"You are comparing two documents:\n"
            f"  • Document A: \"{title_a}\"\n"
            f"  • Document B: \"{title_b}\"\n\n"
            f"Excerpts from both documents:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Produce a precise structured diff analysis using the mandatory output structure. "
            "Cite document label and page number for every point."
        )
    })

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.15,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def summarize_document(pages, doc_title="document"):
    """Generate a professional executive-quality document summary."""
    full_text = " ".join(p["text"] for p in pages)
    excerpt = " ".join(full_text.split()[:3500])

    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Produce a professional executive summary of the document titled \"{doc_title}\".\n\n"
                "Use exactly this structure:\n\n"
                "## Overview\n"
                "2–3 sentences. What is this document, who is it for, and what is its core purpose? "
                "Be specific — name the actual subject matter.\n\n"
                "## Key Topics\n"
                "Bullet list of 4–7 major themes or concepts covered. Each bullet is a specific noun "
                "phrase using the document's actual terminology — not generic labels.\n\n"
                "## Critical Findings & Insights\n"
                "3–5 bullets of the most important conclusions, arguments, results, or requirements. "
                "These are what a decision-maker cannot afford to miss. Include specific numbers, "
                "names, and precise claims where present.\n\n"
                "## Technical Depth\n"
                "Note the level of complexity, prerequisite knowledge assumed, and any specialized "
                "terminology central to understanding this document. Omit if not applicable.\n\n"
                "## Limitations & Gaps\n"
                "1–3 bullets on what the document does NOT cover, notable caveats, or where the "
                "analysis is incomplete. Be honest — this is valuable signal.\n\n"
                "## Suggested Questions\n"
                "4–5 specific, insightful questions tailored to THIS document's actual content — "
                "not generic questions. These should make a reader immediately want to open the chat.\n\n"
                f"Document text:\n{excerpt}"
            )
        }
    ]

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=1400,
    )
    return response.choices[0].message.content


def suggest_followups(question, answer, retrieved_chunks):
    """
    Generate 3 specific, expert-level follow-up questions grounded in the retrieved passages.
    Returns a list of question strings (empty list on failure).
    """
    preview = ""
    for c in retrieved_chunks[:3]:
        preview += f"[Page {c['page']}]: {c['text'][:200]}\n\n"

    prompt = (
        f"Original question: {question}\n\n"
        f"Answer given: {answer[:600]}\n\n"
        f"Source passages used:\n{preview}"
        "---\n"
        "Generate exactly 3 expert follow-up questions a knowledgeable reader would naturally ask next.\n"
        "Rules:\n"
        "- Each question must be specifically answerable from the source passages above\n"
        "- Reference specific pages where relevant: 'What does page 4 say about...'\n"
        "- Explore aspects the original answer did not fully cover\n"
        "- Be specific and precise — never generic like 'Tell me more' or 'Can you elaborate'\n"
        "- Under 15 words each where possible\n"
        "Return ONLY a valid JSON array of exactly 3 strings. No explanation. No markdown fences.\n"
        'Example: ["How does the author define X on page 3?", "What evidence supports claim Y?", "What are the stated limitations of method Z?"]'
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": FOLLOWUP_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=320,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.IGNORECASE).replace("```", "").strip()
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(q).strip() for q in parsed[:3] if str(q).strip()]
    except Exception:
        pass
    return []