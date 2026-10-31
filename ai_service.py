
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


# ============================================================
# MODEL DISCOVERY
# ============================================================

def _model_candidates(client):
    """
    Return available models in the preferred order.
    If model discovery fails, use the configured fallback list.
    """
    try:
        available_models = {
            model.id for model in client.models.list().data
        }

        candidates = [
            model
            for model in PREFERRED_MODELS
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
    """
    Try each available model in order.

    A rate limit on one model will not stop attempts on
    the remaining models.
    """

    candidates = _model_candidates(client)
    errors = []

    for model in candidates:
        try:
            request_options = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }

            # GPT-OSS models use max_completion_tokens.
            if model.startswith("openai/gpt-oss"):
                request_options["max_completion_tokens"] = max_tokens
                request_options["reasoning_effort"] = "low"

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

            errors.append(f"{model}: Model returned empty content")

        except Exception as error:
            error_text = str(error)
            error_lower = error_text.lower()

            # Try the next model when this model is rate-limited.
            if (
                "429" in error_text
                or "rate_limit" in error_lower
                or "rate limit" in error_lower
            ):
                errors.append(
                    f"{model}: Rate limit reached. Trying next model."
                )
                continue

            # Try another model if the model or request is unsupported.
            if (
                "404" in error_text
                or "model_not_found" in error_lower
                or "400" in error_text
            ):
                errors.append(f"{model}: {error_text}")
                continue

            # Do not hide authentication, connection, or other errors.
            raise RuntimeError(
                f"Groq request failed with {model}: {error_text}"
            ) from error

    details = "\n".join(errors)

    raise RuntimeError(
        "All configured Groq models failed.\n\n"
        "Possible reasons include exhausted rate limits or "
        "unavailable models.\n\n"
        f"Details:\n{details}"
    )


# ============================================================
# TEXT CHUNKING
# ============================================================

def chunk_text(text, max_chars=7000):
    """
    Split long transcripts into smaller chunks without
    intentionally dropping transcript content.
    """

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

    return instructions.get(
        language,
        "Write in clear English."
    )


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

Keep the points clear and useful.
""",

        "Practice Quiz & Flashcards": """
Create learning material from the transcript.

Include:
- Multiple-choice questions with four options
- Correct answers
- Short explanations
- Flashcards with questions and answers
- A final revision section

Make sure the questions are based on the transcript.
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

Do not invent formulas that are not supported by the transcript.
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
            "Keep the response short and focus only on essential information."
        ),
        "Standard": (
            "Provide balanced explanations with useful details."
        ),
        "In-Depth": (
            "Provide comprehensive explanations, examples and important details."
        ),
    }

    return instructions.get(
        detail_level,
        instructions["Standard"]
    )


# ============================================================
# SUMMARIZE INDIVIDUAL TRANSCRIPT CHUNK
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
                "Do not invent facts or information."
            ),
        },
        {
            "role": "user",
            "content": f"""
Analyze part {chunk_number} of {total_chunks} of a lecture transcript.

Output format:
{_mode_prompt(mode)}

Language:
{_language_instruction(language)}

Detail:
{_detail_instruction(detail_level)}

Important:
- Preserve important information.
- Do not invent facts.
- Identify key concepts and explanations.
- This is one part of a larger transcript.

TRANSCRIPT:
{chunk}
""",
        },
    ]

    return call_groq_completion(
        client,
        messages,
        max_tokens=2500,
        temperature=0.25,
    )


# ============================================================
# REDUCE CHUNK SUMMARIES
# ============================================================

def _reduce_summaries(
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
                "Combine lecture notes without losing important information."
            ),
        },
        {
            "role": "user",
            "content": f"""
Combine the following partial lecture notes into one coherent document.

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
- Do not introduce unsupported facts.

PARTIAL NOTES:
{combined}
""",
        },
    ]

    return call_groq_completion(
        client,
        messages,
        max_tokens=5000,
        temperature=0.25,
    )


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
    chunks = chunk_text(text, max_chars=7000)

    if not chunks:
        raise ValueError("Could not split the transcript into text.")

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
        progress_callback("Combining all lecture notes...")

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

    transcript_context = str(transcript_text or "")[:12000]

    messages = [
        {
            "role": "system",
            "content": f"""
You are an educational assistant answering questions
about a YouTube lecture.

Use the transcript as your main source.
If the answer is not available in the transcript,
clearly say so instead of inventing information.

TRANSCRIPT:
{transcript_context}
""",
        }
    ]

    # Support common chat history formats.
    for item in (chat_history or [])[-6:]:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content", item.get("message", ""))

            if role in ("user", "assistant") and content:
                messages.append({
                    "role": role,
                    "content": str(content),
                })

        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            role, content = item[0], item[1]

            if role in ("user", "assistant") and content:
                messages.append({
                    "role": role,
                    "content": str(content),
                })

    messages.append({
        "role": "user",
        "content": question.strip(),
    })

    return call_groq_completion(
        client,
        messages,
        max_tokens=1500,
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
Connect the main topic to important concepts and subtopics.
""",
        },
        {
            "role": "user",
            "content": f"""
Create a clear concept mind map from this lecture transcript.

TRANSCRIPT:
{str(transcript_text)[:8000]}
""",
        },
    ]

    result = call_groq_completion(
        client,
        messages,
        max_tokens=1800,
        temperature=0.2,
    )

    # Remove accidental Markdown code fences.
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
