import re
from typing import Any

from groq import Groq


PRIMARY_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]


def _model_candidates(client: Groq) -> list[str]:
    """Return usable text-generation models, preferring current production models."""
    available = []
    try:
        data = client.models.list()
        for model in getattr(data, "data", []) or []:
            model_id = getattr(model, "id", "") or ""
            lowered = model_id.lower()
            if not model_id:
                continue
            if any(x in lowered for x in ("whisper", "guard", "tts", "safeguard")):
                continue
            available.append(model_id)
    except Exception:
        # If model discovery is unavailable, use known current production IDs.
        pass

    ordered = []
    for model_id in PRIMARY_MODELS:
        if model_id in available or not available:
            if model_id not in ordered:
                ordered.append(model_id)

    # Only use dynamically discovered models after the known-good models.
    for model_id in available:
        if model_id not in ordered:
            ordered.append(model_id)

    return ordered


def call_groq_completion(
    client: Groq,
    messages: list[dict[str, str]],
    max_tokens: int = 1500,
    temperature: float = 0.3,
) -> str:
    """Call Groq with model fallback and clear error reporting."""
    last_error: Exception | None = None

    for model_name in _model_candidates(client):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )
            content = response.choices[0].message.content if response.choices else None
            if content and content.strip():
                return content.strip()
            raise RuntimeError("Groq returned an empty response.")
        except Exception as exc:
            last_error = exc
            continue

    detail = str(last_error) if last_error else "No compatible Groq model was available."
    raise RuntimeError(
        "Groq could not generate the requested output. "
        "Please check GROQ_API_KEY, model availability, and rate limits. "
        f"Details: {detail}"
    )


def chunk_text(text: str, max_chars: int = 18000) -> list[str]:
    """Split transcript on word boundaries without dropping any text."""
    text = (text or "").strip()
    if not text:
        return []

    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and current_length + extra > max_chars:
            chunks.append(" ".join(current))
            current = []
            current_length = 0
        current.append(word)
        current_length += extra

    if current:
        chunks.append(" ".join(current))

    return chunks


def _language_instruction(language: str) -> str:
    if language == "Hinglish":
        return (
            "Write the answer in natural Hinglish: Hindi written in the Latin alphabet, "
            "while keeping technical terms in English."
        )
    return f"Write the entire answer strictly in {language}."


def _mode_prompt(mode: str, detail_level: str, language: str) -> str:
    lang = _language_instruction(language)
    prompts = {
        "Detailed Study Notes": (
            "You are an expert academic professor. Create comprehensive, exam-ready study notes.\n"
            f"{lang}\nDetail Level: {detail_level}\n\n"
            "Use these sections:\n"
            "## 📌 Core Concept & Overview\n"
            "## 🔑 Key Topics & Technical Breakdown\n"
            "## 📐 Formulas, Definitions & Rules\n"
            "## 💡 Practical Examples & Applications\n"
            "## ❓ Potential Exam Questions & Answers"
        ),
        "Executive Summary": (
            "Create a concise but complete executive summary of the lecture.\n"
            f"{lang}\nDetail Level: {detail_level}\n\n"
            "Cover the core topic, major concepts, important examples, and final takeaways."
        ),
        "Actionable Bullet Points": (
            "Extract the most important concepts, facts, procedures, and steps from the lecture.\n"
            f"{lang}\nDetail Level: {detail_level}\n"
            "Use clear hierarchical bullet points and bold important terms."
        ),
        "Practice Quiz & Flashcards": (
            "Create a revision set from the lecture.\n"
            f"{lang}\n\n"
            "### 🧠 Multiple Choice Questions (5 Questions)\n"
            "Give 4 options, the correct answer, and a short explanation for each.\n\n"
            "### 🗂️ Flashcard Deck (5 Key Concepts)\n"
            "Format each as **Front** -> **Back**."
        ),
        "Formula & Keyword Cheat Sheet": (
            "Create a compact technical cheat sheet containing important terms, definitions, formulas, rules, and keywords.\n"
            f"{lang}\nDetail Level: {detail_level}"
        ),
    }
    return prompts.get(mode, prompts["Detailed Study Notes"])


def _summarize_chunk(client: Groq, chunk: str, part_number: int, language: str) -> str:
    prompt = (
        "Extract the important factual and technical information from this lecture section. "
        "Do not invent information. Preserve definitions, formulas, examples, algorithms, and relationships. "
        f"Write the result in {language}.\n\n"
        f"LECTURE SECTION {part_number}:\n{chunk}"
    )
    return call_groq_completion(
        client,
        [
            {"role": "system", "content": "You are a precise academic transcript analyst."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=900,
        temperature=0.2,
    )


def _reduce_summaries(client: Groq, summaries: list[str], language: str) -> str:
    """Reduce many intermediate summaries until they fit comfortably in a final prompt."""
    current = summaries[:]
    while len(current) > 8:
        reduced: list[str] = []
        for start in range(0, len(current), 6):
            group = current[start : start + 6]
            combined = "\n\n".join(
                f"SECTION SUMMARY {start + i + 1}:\n{item}" for i, item in enumerate(group)
            )
            reduced.append(
                call_groq_completion(
                    client,
                    [
                        {"role": "system", "content": "Combine academic summaries without losing important facts."},
                        {
                            "role": "user",
                            "content": (
                                f"Combine these summaries into a faithful condensed summary in {language}. "
                                "Do not add facts that are not present.\n\n{combined}"
                            ),
                        },
                    ],
                    max_tokens=1100,
                    temperature=0.2,
                )
            )
        current = reduced
    return "\n\n".join(current)


def generate_summary(
    text: str,
    mode: str,
    api_key: str,
    detail_level: str = "Standard",
    language: str = "English",
) -> str:
    text = (text or "").strip()
    if not text:
        raise ValueError("The transcript is empty, so there is nothing to summarize.")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key)
    chunks = chunk_text(text)
    selected_prompt = _mode_prompt(mode, detail_level, language)

    # Short transcripts can be processed in one request.
    if len(chunks) == 1:
        return call_groq_completion(
            client,
            [
                {
                    "role": "system",
                    "content": "You are an accurate academic AI assistant. Use only the supplied lecture transcript.",
                },
                {
                    "role": "user",
                    "content": f"{selected_prompt}\n\n--- TRANSCRIPT ---\n{chunks[0]}",
                },
            ],
            max_tokens=2400,
            temperature=0.25,
        )

    # Long transcripts: process EVERY chunk, then reduce and synthesize.
    summaries = []
    for index, chunk in enumerate(chunks, start=1):
        summaries.append(_summarize_chunk(client, chunk, index, language))

    combined = _reduce_summaries(client, summaries, language)
    final_prompt = (
        f"{selected_prompt}\n\n"
        "The following are faithful summaries of every section of the original lecture. "
        "Synthesize them into one coherent answer. Do not omit important concepts and do not invent facts.\n\n"
        f"--- SECTION SUMMARIES ---\n{combined}"
    )

    return call_groq_completion(
        client,
        [
            {"role": "system", "content": "You are an expert academic editor producing a faithful lecture digest."},
            {"role": "user", "content": final_prompt},
        ],
        max_tokens=3000,
        temperature=0.25,
    )


def _compact_transcript_for_chat(transcript_text: str, max_chars: int = 50000) -> str:
    text = (transcript_text or "").strip()
    if len(text) <= max_chars:
        return text
    # Keep beginning, middle, and end so chat is not biased to only the opening.
    part = max_chars // 3
    return (
        text[:part]
        + "\n\n[...middle of transcript condensed for context... ]\n\n"
        + text[len(text) // 2 - part // 2 : len(text) // 2 + part // 2]
        + "\n\n[...later transcript... ]\n\n"
        + text[-part:]
    )


def ask_video_question(
    transcript_text: str,
    question: str,
    chat_history: list[dict[str, str]],
    api_key: str,
) -> str:
    if not question.strip():
        raise ValueError("Please enter a question.")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key)
    safe_transcript = _compact_transcript_for_chat(transcript_text)

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are an academic tutor. Answer using ONLY the lecture transcript supplied below. "
                "If the answer is not supported by the transcript, say that it is not available in the transcript.\n\n"
                f"--- LECTURE TRANSCRIPT ---\n{safe_transcript}"
            ),
        }
    ]

    for item in (chat_history or [])[-6:]:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": question.strip()})
    return call_groq_completion(client, messages, max_tokens=1200, temperature=0.2)


def generate_mindmap_code(transcript_text: str, api_key: str) -> str:
    if not transcript_text.strip():
        raise ValueError("The transcript is empty, so a mind map cannot be generated.")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key)
    source = _compact_transcript_for_chat(transcript_text, max_chars=35000)

    system_prompt = (
        "Create a simple Mermaid flowchart from the lecture.\n"
        "RULES:\n"
        "1. Start with graph TD.\n"
        "2. Use simple alphanumeric node IDs only.\n"
        "3. Use labels in double quotes inside square brackets.\n"
        "4. Avoid parentheses, commas, colons, and special Mermaid syntax inside labels.\n"
        "5. Return ONLY Mermaid code, with no markdown fences.\n"
        "6. Use a small number of clear nodes so the diagram remains readable."
    )

    raw = call_groq_completion(
        client,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"LECTURE:\n{source}"},
        ],
        max_tokens=900,
        temperature=0.1,
    )

    clean = re.sub(r"```(?:mermaid)?", "", raw, flags=re.IGNORECASE).replace("```", "").strip()
    clean = re.sub(r"^\s*mermaid\s*\n", "", clean, flags=re.IGNORECASE).strip()
    if not clean.lower().startswith("graph td"):
        clean = "graph TD\n" + clean
    return clean
