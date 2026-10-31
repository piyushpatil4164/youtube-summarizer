import re

from groq import Groq


# Models to try, in priority order.
# The code first checks which of these are available to your API key.
PREFERRED_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen/qwen3-32b",
]

FALLBACK_MODELS = [
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


def _model_candidates(client: Groq) -> list[str]:
    """Return supported preferred models available to this API key."""
    try:
        response = client.models.list()
        available_ids = {
            model.id
            for model in getattr(response, "data", [])
            if getattr(model, "id", None)
        }

        candidates = [
            model
            for model in PREFERRED_MODELS
            if model in available_ids
        ]

        if candidates:
            return candidates

    except Exception:
        # If model listing is unavailable, try the known fallback list.
        pass

    return FALLBACK_MODELS[:]


def call_groq_completion(
    client: Groq,
    messages: list[dict[str, str]],
    max_tokens: int = 1500,
    temperature: float = 0.25,
) -> str:
    """Generate a completion, retrying only when a model is unavailable."""
    candidates = _model_candidates(client)
    last_error = None

    for model_name in candidates:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_completion_tokens=max_tokens,
                temperature=temperature,
            )

            content = (
                response.choices[0].message.content
                if response.choices
                else None
            )

            if not content or not content.strip():
                raise RuntimeError("Groq returned an empty response.")

            return content.strip()

        except Exception as exc:
            last_error = exc
            status_code = getattr(exc, "status_code", None)

            # Try another model only for a model/request compatibility error.
            # Do not repeatedly retry authentication or rate-limit errors.
            if status_code in {400, 404}:
                continue

            raise RuntimeError(
                "Groq request failed. Check your API key, account limits, "
                f"and model availability. Details: {exc}"
            ) from exc

    raise RuntimeError(
        "None of the configured Groq models could complete the request. "
        "Check the models enabled for your API key. "
        f"Last error: {last_error}"
    )


def chunk_text(text: str, max_chars: int = 7000) -> list[str]:
    """Split a transcript into manageable chunks without dropping content."""
    text = (text or "").strip()

    if not text:
        return []

    words = text.split()
    chunks = []
    current_words = []
    current_length = 0

    for word in words:
        extra_length = len(word) + (1 if current_words else 0)

        if current_words and current_length + extra_length > max_chars:
            chunks.append(" ".join(current_words))
            current_words = []
            current_length = 0

        current_words.append(word)
        current_length += extra_length

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def _language_instruction(language: str) -> str:
    if language == "Hinglish":
        return (
            "Write in natural Hinglish: Hindi written in the Latin alphabet. "
            "Keep technical terms in English."
        )

    return f"Write the answer entirely in {language}."


def _mode_prompt(mode: str, detail_level: str, language: str) -> str:
    lang = _language_instruction(language)

    prompts = {
        "Detailed Study Notes": (
            "Create comprehensive, accurate, exam-ready study notes.\n"
            f"{lang}\n"
            f"Detail level: {detail_level}\n\n"
            "Use these sections:\n"
            "## Core Concept and Overview\n"
            "## Key Topics and Technical Breakdown\n"
            "## Formulas, Definitions and Rules\n"
            "## Practical Examples and Applications\n"
            "## Potential Exam Questions and Answers"
        ),

        "Executive Summary": (
            "Create a concise but complete executive summary.\n"
            f"{lang}\n"
            f"Detail level: {detail_level}\n\n"
            "Cover the main topic, major concepts, important examples, "
            "and final takeaways."
        ),

        "Actionable Bullet Points": (
            "Extract the most important concepts, facts, procedures, "
            "and steps from the lecture.\n"
            f"{lang}\n"
            f"Detail level: {detail_level}\n"
            "Use clear hierarchical bullet points."
        ),

        "Practice Quiz & Flashcards": (
            "Create a revision set using only the lecture content.\n"
            f"{lang}\n\n"
            "### Multiple Choice Questions\n"
            "Create 5 questions, each with 4 options, the correct answer, "
            "and a short explanation.\n\n"
            "### Flashcards\n"
            "Create 5 flashcards using Front and Back format."
        ),

        "Formula & Keyword Cheat Sheet": (
            "Create a compact technical cheat sheet containing important "
            "terms, definitions, formulas, rules, and keywords.\n"
            f"{lang}\n"
            f"Detail level: {detail_level}"
        ),
    }

    return prompts.get(mode, prompts["Detailed Study Notes"])


def _summarize_chunk(
    client: Groq,
    chunk: str,
    part_number: int,
    language: str,
) -> str:
    prompt = (
        "Extract the important factual and technical information from "
        "this lecture section. Do not invent information. Preserve "
        "definitions, formulas, examples, algorithms, and relationships. "
        f"Write in {language}.\n\n"
        f"LECTURE SECTION {part_number}:\n{chunk}"
    )

    return call_groq_completion(
        client,
        [
            {
                "role": "system",
                "content": (
                    "You are a precise academic transcript analyst. "
                    "Use only the supplied lecture section."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
        temperature=0.2,
    )


def _reduce_summaries(
    client: Groq,
    summaries: list[str],
    language: str,
) -> str:
    """Combine summaries in stages so long lectures are not truncated."""
    current = summaries[:]

    while len(current) > 5:
        reduced = []

        for start in range(0, len(current), 4):
            group = current[start:start + 4]

            combined = "\n\n".join(
                f"SECTION SUMMARY {start + index + 1}:\n{item}"
                for index, item in enumerate(group)
            )

            result = call_groq_completion(
                client,
                [
                    {
                        "role": "system",
                        "content": (
                            "Combine academic summaries faithfully. "
                            "Do not invent facts or remove important details."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Combine these summaries in {language}. "
                            "Preserve key concepts, definitions, formulas, "
                            "examples, and relationships.\n\n"
                            f"{combined}"
                        ),
                    },
                ],
                max_tokens=1200,
                temperature=0.2,
            )

            reduced.append(result)

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
        raise ValueError("The transcript is empty.")

    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key, timeout=90, max_retries=1)
    chunks = chunk_text(text)

    if not chunks:
        raise ValueError("The transcript could not be divided into sections.")

    selected_prompt = _mode_prompt(mode, detail_level, language)

    # A short transcript can be processed in one request.
    if len(chunks) == 1:
        return call_groq_completion(
            client,
            [
                {
                    "role": "system",
                    "content": (
                        "You are an accurate academic assistant. "
                        "Use only the supplied lecture transcript. "
                        "Do not invent facts."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{selected_prompt}\n\n"
                        f"--- LECTURE TRANSCRIPT ---\n{chunks[0]}"
                    ),
                },
            ],
            max_tokens=2500,
            temperature=0.25,
        )

    # Summarize every chunk, not just the first few.
    section_summaries = []

    for index, chunk in enumerate(chunks, start=1):
        section_summaries.append(
            _summarize_chunk(client, chunk, index, language)
        )

    combined = _reduce_summaries(
        client,
        section_summaries,
        language,
    )

    final_prompt = (
        f"{selected_prompt}\n\n"
        "The following are summaries of every section of the original "
        "lecture. Synthesize them into one coherent answer. Preserve "
        "important concepts and do not invent facts.\n\n"
        f"--- SECTION SUMMARIES ---\n{combined}"
    )

    return call_groq_completion(
        client,
        [
            {
                "role": "system",
                "content": (
                    "You are an expert academic editor. "
                    "Produce a faithful and well-organized lecture digest."
                ),
            },
            {"role": "user", "content": final_prompt},
        ],
        max_tokens=2500,
        temperature=0.25,
    )


def _compact_transcript_for_chat(
    transcript_text: str,
    max_chars: int = 12000,
) -> str:
    """Keep the beginning, middle, and end when chat context is too large."""
    text = (transcript_text or "").strip()

    if len(text) <= max_chars:
        return text

    part = max_chars // 3
    middle_start = max(0, len(text) // 2 - part // 2)
    middle_end = middle_start + part

    return (
        text[:part]
        + "\n\n[Middle section condensed for context]\n\n"
        + text[middle_start:middle_end]
        + "\n\n[Later section]\n\n"
        + text[-part:]
    )


def ask_video_question(
    transcript_text: str,
    question: str,
    chat_history: list[dict[str, str]],
    api_key: str,
) -> str:
    if not question or not question.strip():
        raise ValueError("Please enter a question.")

    if not transcript_text or not transcript_text.strip():
        raise ValueError("No lecture transcript is available.")

    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key, timeout=60, max_retries=1)
    safe_transcript = _compact_transcript_for_chat(transcript_text)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an academic tutor. Answer using the supplied "
                "lecture transcript. If the transcript does not contain "
                "the answer, clearly say that the information is not "
                "available in the transcript. Do not invent lecture facts.\n\n"
                f"--- LECTURE TRANSCRIPT ---\n{safe_transcript}"
            ),
        }
    ]

    for item in (chat_history or [])[-4:]:
        role = item.get("role")
        content = item.get("content")

        if role in {"user", "assistant"} and content:
            messages.append(
                {"role": role, "content": str(content)}
            )

    messages.append(
        {"role": "user", "content": question.strip()}
    )

    return call_groq_completion(
        client,
        messages,
        max_tokens=1200,
        temperature=0.2,
    )


def generate_mindmap_code(transcript_text: str, api_key: str) -> str:
    if not transcript_text or not transcript_text.strip():
        raise ValueError("The transcript is empty.")

    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key, timeout=60, max_retries=1)
    source = _compact_transcript_for_chat(
        transcript_text,
        max_chars=10000,
    )

    system_prompt = (
        "Create a simple Mermaid flowchart from the lecture.\n"
        "Rules:\n"
        "1. Start with graph TD.\n"
        "2. Use simple alphanumeric node IDs only.\n"
        "3. Use labels in double quotes inside square brackets.\n"
        "4. Keep labels short and readable.\n"
        "5. Return only Mermaid code, without Markdown fences.\n"
        "6. Do not include HTML, scripts, links, or styling directives."
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

    clean = re.sub(
        r"```(?:mermaid)?",
        "",
        raw,
        flags=re.IGNORECASE,
    )
    clean = clean.replace("```", "").strip()
    clean = re.sub(
        r"^\s*mermaid\s*\n",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()

    if not clean:
        raise RuntimeError("The AI returned an empty mind map.")

    if not clean.lower().startswith("graph td"):
        clean = "graph TD\n" + clean

    return clean
