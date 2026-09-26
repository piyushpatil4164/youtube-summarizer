import re
from groq import Groq


PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]


def call_groq_completion(
    client: Groq,
    messages: list,
    max_tokens: int = 1500,
    temperature: float = 0.3,
) -> str:

    available_models = []

    try:
        models_data = client.models.list()

        for model in models_data.data:
            model_id = getattr(model, "id", "")

            if not model_id:
                continue

            lower_id = model_id.lower()

            if "whisper" in lower_id:
                continue

            if "guard" in lower_id:
                continue

            if "safeguard" in lower_id:
                continue

            available_models.append(model_id)

    except Exception:
        # If model discovery fails, use the current preferred model.
        available_models = []

    ordered_models = []

    # Prefer currently supported models.
    for model_name in PREFERRED_MODELS:
        if model_name in available_models:
            ordered_models.append(model_name)

    # Then allow other models returned by Groq.
    for model_name in available_models:
        if model_name not in ordered_models:
            ordered_models.append(model_name)

    # Last-resort current model.
    if not ordered_models:
        ordered_models = ["openai/gpt-oss-120b"]

    last_error = None

    for model_name in ordered_models:

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content

            if content:
                return content

        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(
        "Groq failed to generate the requested output. "
        f"Last error: {last_error}"
    )


def chunk_text(text: str, max_chars: int = 12000) -> list[str]:
    """
    Split a transcript into manageable pieces without cutting words.
    """

    text = text.strip()

    if not text:
        return [""]

    words = text.split()

    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:

        word_length = len(word) + 1

        if (
            current_chunk
            and current_length + word_length > max_chars
        ):
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(word)
        current_length += word_length

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def _summarize_chunk(
    client: Groq,
    chunk: str,
    chunk_number: int,
    total_chunks: int,
    language: str,
) -> str:

    prompt = f"""
You are processing part {chunk_number} of {total_chunks}
of a longer educational lecture.

Summarize the important information from this part.

Language:
{language}

Rules:
- Keep important definitions.
- Keep formulas and technical terms.
- Keep important examples.
- Keep important explanations.
- Do not invent information.
- Do not mention that this is a transcript.
- Do not omit important academic concepts.

LECTURE PART:

{chunk}
"""

    messages = [
        {
            "role": "system",
            "content": (
                "You are an academic lecture summarization assistant. "
                "Preserve factual information from the provided lecture."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    return call_groq_completion(
        client,
        messages,
        max_tokens=900,
        temperature=0.2,
    )


def _reduce_summaries(
    client: Groq,
    summaries: list[str],
    language: str,
) -> str:
    """
    Combine chunk summaries into one compact context.

    This prevents the final prompt from becoming too large.
    """

    if len(summaries) == 1:
        return summaries[0]

    current = summaries

    while len(current) > 1:

        next_level = []

        # Combine a few summaries at a time.
        for i in range(0, len(current), 4):

            batch = current[i:i + 4]

            combined = "\n\n".join(
                f"PART SUMMARY {j + 1}:\n{summary}"
                for j, summary in enumerate(batch)
            )

            prompt = f"""
Combine the following lecture summaries into one accurate
academic summary.

Language:
{language}

Rules:
- Preserve important technical details.
- Preserve definitions.
- Preserve formulas.
- Preserve examples.
- Remove repetition.
- Do not invent information.

{combined}
"""

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an academic information synthesis assistant."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ]

            reduced = call_groq_completion(
                client,
                messages,
                max_tokens=1000,
                temperature=0.2,
            )

            next_level.append(reduced)

        current = next_level

    return current[0]


def generate_summary(
    text: str,
    mode: str,
    api_key: str,
    detail_level: str = "Standard",
    language: str = "English",
) -> str:

    if not text or not text.strip():
        raise ValueError("No transcript text was provided.")

    client = Groq(api_key=api_key)

    chunks = chunk_text(text, max_chars=12000)

    lang_instruction = (
        f"Generate the entire response strictly in {language}. "
        "If Hinglish is selected, use natural conversational Hindi "
        "written in the Latin alphabet with technical terms in English."
    )

    prompts = {
        "Detailed Study Notes": (
            "You are an expert academic professor. "
            "Create comprehensive, exam-ready study notes.\n"
            f"{lang_instruction}\n"
            f"Detail Level: {detail_level}\n\n"
            "Structure strictly with these headers:\n"
            "## 📌 Core Concept & Overview\n"
            "## 🔑 Key Topics & Technical Breakdown\n"
            "## 📐 Formulas, Definitions & Rules\n"
            "## 💡 Practical Examples & Applications\n"
            "## ❓ Potential Exam Questions & Answers"
        ),

        "Executive Summary": (
            "Provide a structured executive briefing of this lecture.\n"
            f"{lang_instruction}\n"
            f"Detail Level: {detail_level}\n\n"
            "- **Core Problem / Thesis**\n"
            "- **Key Innovations & Takeaways**\n"
            "- **Final Verdict & Implications**"
        ),

        "Actionable Bullet Points": (
            "Extract critical points, step-by-step instructions, "
            "and key facts.\n"
            f"{lang_instruction}\n"
            f"Detail Level: {detail_level}\n"
            "Use clear hierarchical bullet points with bold keywords."
        ),

        "Practice Quiz & Flashcards": (
            "Create a revision quiz and flashcard set.\n"
            f"{lang_instruction}\n\n"
            "### 🧠 Multiple Choice Questions (5 Questions)\n"
            "Provide 4 options per question with answers and explanations.\n\n"
            "### 🗂️ Flashcard Deck (5 Key Concepts)\n"
            "Format: **Front (Term/Question)** -> **Back (Definition/Answer)**"
        ),

        "Formula & Keyword Cheat Sheet": (
            "Extract all technical terms, definitions, "
            "and equations into a reference cheat sheet.\n"
            f"{lang_instruction}"
        ),
    }

    selected_prompt = prompts.get(
        mode,
        prompts["Detailed Study Notes"],
    )

    # Short transcript: one direct request.
    if len(chunks) == 1:

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an elite academic AI assistant "
                    "dedicated to high-precision study synthesis."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{selected_prompt}\n\n"
                    "--- TRANSCRIPT ---\n"
                    f"{chunks[0]}"
                ),
            },
        ]

        return call_groq_completion(
            client,
            messages,
            max_tokens=2200,
            temperature=0.3,
        )

    # Long transcript:
    # Process EVERY chunk, not only chunks[:3].
    chunk_summaries = []

    for index, chunk in enumerate(chunks):

        summary = _summarize_chunk(
            client=client,
            chunk=chunk,
            chunk_number=index + 1,
            total_chunks=len(chunks),
            language=language,
        )

        chunk_summaries.append(summary)

    combined_context = _reduce_summaries(
        client,
        chunk_summaries,
        language,
    )

    final_messages = [
        {
            "role": "system",
            "content": (
                "You are an elite academic AI assistant. "
                "Create the final study material using only "
                "the information contained in the supplied lecture summaries."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{selected_prompt}\n\n"
                "--- COMPLETE LECTURE SYNTHESIS ---\n"
                f"{combined_context}"
            ),
        },
    ]

    return call_groq_completion(
        client,
        final_messages,
        max_tokens=2400,
        temperature=0.3,
    )


def ask_video_question(
    transcript_text: str,
    question: str,
    chat_history: list,
    api_key: str,
) -> str:

    client = Groq(api_key=api_key)

    # Keep the existing chat feature safe for very large transcripts.
    # The complete transcript is summarized before normal chat use.
    if len(transcript_text) > 30000:

        chunks = chunk_text(transcript_text, max_chars=10000)

        summaries = []

        for index, chunk in enumerate(chunks):

            summary = _summarize_chunk(
                client,
                chunk,
                index + 1,
                len(chunks),
                "English",
            )

            summaries.append(summary)

        safe_transcript = _reduce_summaries(
            client,
            summaries,
            "English",
        )

    else:
        safe_transcript = transcript_text

    messages = [
        {
            "role": "system",
            "content": (
                "You are an academic tutor assisting a student "
                "with this video lecture.\n\n"
                "Answer the student's question accurately using "
                "ONLY the provided lecture information.\n"
                "If the information is not available, say so clearly.\n\n"
                f"--- LECTURE ---\n{safe_transcript}"
            ),
        }
    ]

    for item in chat_history[-6:]:
        messages.append(
            {
                "role": item["role"],
                "content": item["content"],
            }
        )

    messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    return call_groq_completion(
        client,
        messages,
        max_tokens=800,
        temperature=0.2,
    )


def generate_mindmap_code(
    transcript_text: str,
    api_key: str,
) -> str:

    client = Groq(api_key=api_key)

    if len(transcript_text) > 20000:

        chunks = chunk_text(transcript_text, max_chars=10000)

        summaries = []

        for index, chunk in enumerate(chunks):

            summary = _summarize_chunk(
                client,
                chunk,
                index + 1,
                len(chunks),
                "English",
            )

            summaries.append(summary)

        safe_transcript = _reduce_summaries(
            client,
            summaries,
            "English",
        )

    else:
        safe_transcript = transcript_text

    system_prompt = (
        "You are an expert flowchart creator. "
        "Convert the lecture into clean Mermaid.js syntax.\n"
        "RULES:\n"
        "1. Start strictly with 'graph TD'\n"
        "2. Node IDs must be simple alphanumeric strings without spaces\n"
        "3. Wrap node labels in square brackets with double quotes\n"
        "4. Do NOT use colons, parentheses, or commas inside node labels\n"
        "5. Return ONLY raw valid Mermaid syntax. "
        "No markdown backticks."
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": (
                "Lecture:\n"
                f"{safe_transcript}"
            ),
        },
    ]

    raw_code = call_groq_completion(
        client,
        messages,
        max_tokens=700,
        temperature=0.1,
    )

    clean = re.sub(
        r"```(?:mermaid)?",
        "",
        raw_code,
        flags=re.IGNORECASE,
    )

    clean = clean.replace("```", "").strip()

    if not clean.startswith("graph"):
        clean = "graph TD\n" + clean

    return clean
