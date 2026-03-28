from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)

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


def build_context(retrieved_chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block for the LLM."""
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        context_parts.append(
            f"[Excerpt {i} — Page {chunk['page_num']}]\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(context_parts)


def generate_answer(
    question: str,
    retrieved_chunks: list[dict],
    chat_history: list[dict] = None
) -> str:
    """
    Generate a grounded answer using Groq LLM.
    chat_history: list of {role, content} dicts for multi-turn context.
    """
    context = build_context(retrieved_chunks)

    user_message = (
        f"Document excerpts:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Provide a thorough, well-structured answer based strictly on the excerpts above. "
        "Cite page numbers for every substantive claim."
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if chat_history:
        for msg in chat_history[-6:]:  # keep last 6 turns for context window efficiency
            messages.append(msg)

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.15,   # low temperature for factual grounding
        max_tokens=1536,
    )

    return response.choices[0].message.content