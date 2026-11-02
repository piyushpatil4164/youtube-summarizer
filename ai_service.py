
import re
from groq import Groq


# ============================================================
# GROQ MODEL SETTINGS
# ============================================================

PREFERRED_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
]

FALLBACK_MODELS = PREFERRED_MODELS.copy()

# Conservative limits to reduce context-length errors.
CHUNK_SIZE = 2500
SUMMARY_OUTPUT_TOKENS = 1200
REDUCE_OUTPUT_TOKENS = 1200


# ============================================================
# MODEL DISCOVERY
# ============================================================

def _model_candidates(client):
    try:
        available_models = {
            model.id for model in client.models.list().data
        }

        candidates = [
            model for model in PREFERRED_MODELS
            if model in available_models
        ]

        return candidates if candidates else FALLBACK_MODELS

    except Exception:
        return FALLBACK_MODELS


# ============================================================
# GROQ COMPLETION WITH AUTOMATIC MODEL SWITCHING
# ============================================================

def call_groq_completion(
    client,
    messages,
    max_tokens=1500,
    temperature=0.25
):
    candidates = _model_candidates(client)
    errors = []

    for model in candidates:
        try:
            request_options = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }

            if model.startswith("openai/gpt-oss"):
                request_options["max_completion_tokens"] = max_tokens
                request_options["reasoning_effort"] = "low"

            elif model == "allam-2-7b":
                request_options["max_tokens"] = min(max_tokens, 4096)

            else:
                request_options["max_tokens"] = max_tokens

            response = client.chat.completions.create(
                **request_options
            )

            if not response.choices:
                errors.append(f"{model}: Empty response")
                continue

            content = response.choices[0].message.content

            if content and content.strip():
                return content.strip()

            errors.append(f"{model}: Empty content")

        except Exception as error:
            error_text = str(error)
            error_lower = error_text.lower()
            status_code = getattr(error, "status_code", None)

            if (
                status_code == 429
                or "rate_limit" in error_lower
                or "rate limit" in error_lower
            ):
                errors.append(f"{model}: Rate limit reached")
                continue

            if (
                status_code == 404
                or "model_not_found" in error_lower
                or "model_not_available" in error_lower
            ):
                errors.append(f"{model}: Model unavailable")
                continue

            if (
                status_code == 400
                and any(term in error_lower for term in (
                    "context",
                    "reduce the length",
                    "messages or completion",
                    "max_tokens",
                    "token limit",
                    "max_completion_tokens",
                ))
            ):
                errors.append(
                    f"{model}: Request exceeded model limits"
                )
                continue

            if status_code is not None and status_code >= 500:
                errors.append(f"{model}: Server error {status_code}")
                continue

            raise RuntimeError(
                f"Groq request failed with {model}: {error_text}"
            ) from error

    raise RuntimeError(
        "All configured Groq models failed.\n\n"
        + "\n".join(errors)
    )


# ============================================================
# TEXT CHUNKING
# ============================================================

def chunk_text(text, max_chars=CHUNK_SIZE):
    text = str(text).strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))

        if end < len(text):
            split_at = text.rfind(" ", start, end)
            if split_at > start:
                end = split_at

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end

    return chunks


# ============================================================
# LANGUAGE INSTRUCTIONS
# ============================================================

def _language_instruction(language):
    instructions = {
        "English": "Write entirely in clear English.",
        "Hindi": "Write in Hindi using Devanagari script.",
        "Hinglish": (
            "Write in natural Hinglish using the Latin alphabet. "
            "Keep technical terms in English."
        ),
        "Spanish": "Write entirely in Spanish.",
        "French": "Write entirely in French.",
        "German": "Write entirely in German.",
    }

    return instructions.get(language, "Write in clear English.")


# ============================================================
# OUTPUT FORMAT INSTRUCTIONS
# ============================================================

def _mode_prompt(mode):
    prompts = {
        "Detailed Study Notes": """
Create detailed, well-organized study notes.

Include:
- A suitable title
- Introduction and overview
- Main concepts and explanations
- Important definitions
- Examples where useful
- Key points
- A short conclusion

Use headings, subheadings and bullet points.
""",

        "Executive Summary": """
Create a concise executive summary.

Include:
- Main topic
- Most important ideas
- Key findings
- Important conclusions

Avoid unnecessary details.
""",

        "Actionable Bullet Points": """
Convert the transcript into organized bullet points.

Include:
- Main ideas
- Important facts
- Key takeaways
- Practical steps or applications
- Important conclusions
""",

        "Practice Quiz & Flashcards": """
Create learning material from the transcript.

Include:
- Multiple-choice questions with four options
- Correct answers
- Short explanations
- Flashcards with questions and answers
- A final revision section

Base questions on the transcript.
""",

        "Formula & Keyword Cheat Sheet": """
Create a revision cheat sheet.

Include:
- Important keywords
- Definitions
- Formulas, if present
- Important concepts
- Short explanations
- Important relationships between concepts

Do not invent formulas.
""",
    }

    return prompts.get(
        mode,
        prompts["Detailed Study Notes"]
    )


# ============================================================
# DETAIL LEVEL
# ============================================================

def _detail_instruction(detail_level):
    instructions = {
        "Concise": (
            "Keep the response short and focus on essential information."
        ),
        "Standard": (
            "Provide balanced explanations with useful details."
        ),
        "In-Depth": (
            "Provide comprehensive explanations and important details."
        ),
    }

    return instructions.get(
        detail_level,
        instructions["Standard"]
    )


# ============================================================
# SUMMARIZE ONE TRANSCRIPT CHUNK
# ============================================================

def _summarize_chunk(
    client,
    chunk,
    chunk_number,
    total_chunks,
    mode,
    language,
    detail_level
):
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert educational assistant. "
                "Analyze lecture transcripts accurately. "
                "Do not invent facts."
            ),
        },
        {
            "role": "user",
            "content": f"""
Analyze part {chunk_number} of {total_chunks}.

Output format:
{_mode_prompt(mode)}

Language:
{_language_instruction(language)}

Detail:
{_detail_instruction(detail_level)}

Preserve important concepts and explanations.
This is one part of a larger lecture.

TRANSCRIPT:
{chunk}
""",
        },
    ]

    return call_groq_completion(
        client,
        messages,
        max_tokens=SUMMARY_OUTPUT_TOKENS,
        temperature=0.25,
    )


# ============================================================
# REDUCE A SMALL GROUP OF SUMMARIES
# ============================================================

def _reduce_batch(
    client,
    summaries,
    mode,
    language,
    detail_level
):
    combined = "\n\n".join(summaries)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert educational editor. "
                "Combine lecture notes accurately and concisely."
            ),
        },
        {
            "role": "user",
            "content": f"""
Combine these partial lecture notes.

Output format:
{_mode_prompt(mode)}

Language:
{_language_instruction(language)}

Detail:
{_detail_instruction(detail_level)}

Requirements:
- Remove repeated information.
- Preserve important concepts.
- Organize information logically.
- Do not invent facts.
- Keep the result concise but useful.

PARTIAL NOTES:
{combined}
""",
        },
    ]

    return call_groq_completion(
        client,
        messages,
        max_tokens=REDUCE_OUTPUT_TOKENS,
        temperature=0.25,
    )


# ============================================================
# HIERARCHICAL SUMMARY REDUCTION
# ============================================================

def _reduce_summaries(
    client,
    summaries,
    mode,
    language,
    detail_level
):
    if not summaries:
        raise ValueError("No summaries available to combine.")

    current = list(summaries)

    # Combine only two summaries per request.
    # Repeat until one final summary remains.
    while len(current) > 1:
        next_level = []

        for index in range(0, len(current), 2):
            batch = current[index:index + 2]

            if len(batch) == 1:
                next_level.append(batch[0])
                continue

            result = _reduce_batch(
                client=client,
                summaries=batch,
                mode=mode,
                language=language,
                detail_level=detail_level,
            )

            next_level.append(result)

        current = next_level

    return current[0]


# ============================================================
# GENERATE FINAL SUMMARY
# ============================================================

def generate_summary(
    text,
    mode,
    api_key,
    detail_level="Standard",
    language="English",
    progress_callback=None
):
    if not text or not str(text).strip():
        raise ValueError("Transcript text is empty.")

    if not api_key:
        raise ValueError("Groq API key is missing.")

    client = Groq(api_key=api_key)

    chunks = chunk_text(
        text,
        max_chars=CHUNK_SIZE
    )

    if not chunks:
        raise ValueError("Could not split transcript into text.")

    partial_summaries = []

    for index, chunk in enumerate(chunks, start=1):

        if progress_callback:
            progress_callback(
                f"Summarizing transcript part {index} of {len(chunks)}..."
            )

        result = _summarize_chunk(
            client=client,
            chunk=chunk,
            chunk_number=index,
            total_chunks=len(chunks),
            mode=mode,
            language=language,
            detail_level=detail_level,
        )

        partial_summaries.append(result)

    if len(partial_summaries) == 1:
        return partial_summaries[0]

    if progress_callback:
        progress_callback("Combining lecture notes in smaller groups...")

    return _reduce_summaries(
        client=client,
        summaries=partial_summaries,
        mode=mode,
        language=language,
        detail_level=detail_level,
    )


# ============================================================
# CHAT WITH VIDEO
# ============================================================

def ask_video_question(
    transcript_text,
    question,
    chat_history,
    api_key
):
    if not api_key:
        raise ValueError("Groq API key is missing.")

    if not question or not question.strip():
        raise ValueError("Please enter a question.")

    client = Groq(api_key=api_key)

    transcript_context = str(transcript_text or "")[:6000]

    messages = [
        {
            "role": "system",
            "content": f"""
You are an educational assistant answering questions
about a YouTube lecture.

Use the transcript as your main source.
If the answer is not available, say so.

TRANSCRIPT:
{transcript_context}
""",
        }
    ]

    for item in (chat_history or [])[-6:]:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content", item.get("message", ""))

            if role in ("user", "assistant") and content:
                messages.append({
                    "role": role,
                    "content": str(content)[:1500],
                })

        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            role, content = item[0], item[1]

            if role in ("user", "assistant") and content:
                messages.append({
                    "role": role,
                    "content": str(content)[:1500],
                })

    messages.append({
        "role": "user",
        "content": question.strip(),
    })

    return call_groq_completion(
        client,
        messages,
        max_tokens=1200,
        temperature=0.3,
    )


# ============================================================
# GENERATE CONCEPT MIND MAP
# ============================================================

def generate_mindmap_code(transcript_text, api_key):
    if not api_key:
        raise ValueError("Groq API key is missing.")

    if not transcript_text or not str(transcript_text).strip():
        raise ValueError("Transcript text is empty.")

    client = Groq(api_key=api_key)

    messages = [
        {
            "role": "system",
            "content": """
You create educational concept mind maps using Mermaid.

Return ONLY valid Mermaid flowchart code.
Start with graph TD.
Do not use Markdown code fences.
Use short node labels.
Connect the main topic to important concepts.
""",
        },
        {
            "role": "user",
            "content": f"""
Create a clear concept mind map from this lecture.

TRANSCRIPT:
{str(transcript_text)[:4000]}
""",
        },
    ]

    result = call_groq_completion(
        client,
        messages,
        max_tokens=1200,
        temperature=0.2,
    )

    result = re.sub(
        r"^```(?:mermaid)?\s*",
        "",
        result.strip(),
        flags=re.IGNORECASE,
    )

    result = re.sub(
        r"\s*```$",
        "",
        result.strip(),
    )

    if not result.strip().startswith("graph"):
        raise RuntimeError(
            "The AI returned invalid mind map code. Please try again."
        )

    return result.strip()
