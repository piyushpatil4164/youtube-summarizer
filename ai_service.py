import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor

from groq import Groq


# Groq model settings
PREFERRED_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
]
FALLBACK_MODELS = PREFERRED_MODELS.copy()

# 3500 reduces the number of requests while keeping each prompt moderate.
CHUNK_SIZE = 3500
SUMMARY_OUTPUT_TOKENS = 1200
REDUCE_OUTPUT_TOKENS = 1200

_MODEL_CANDIDATES_CACHE = None
_MODEL_CANDIDATES_LOCK = threading.Lock()


def _model_candidates(client):
    """Discover preferred models once per app process, not on every request."""
    global _MODEL_CANDIDATES_CACHE
    if _MODEL_CANDIDATES_CACHE is not None:
        return _MODEL_CANDIDATES_CACHE

    with _MODEL_CANDIDATES_LOCK:
        if _MODEL_CANDIDATES_CACHE is not None:
            return _MODEL_CANDIDATES_CACHE
        try:
            available = {model.id for model in client.models.list().data}
            discovered = [m for m in PREFERRED_MODELS if m in available]
            _MODEL_CANDIDATES_CACHE = discovered or FALLBACK_MODELS
        except Exception:
            _MODEL_CANDIDATES_CACHE = FALLBACK_MODELS
        return _MODEL_CANDIDATES_CACHE


def call_groq_completion(client, messages, max_tokens=1500, temperature=0.25):
    errors = []
    for model in _model_candidates(client):
        try:
            options = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if model.startswith("openai/gpt-oss"):
                options["max_completion_tokens"] = max_tokens
                options["reasoning_effort"] = "low"
            else:
                options["max_tokens"] = min(max_tokens, 4096) if model == "allam-2-7b" else max_tokens

            response = client.chat.completions.create(**options)
            if response.choices:
                content = response.choices[0].message.content
                if content and content.strip():
                    return content.strip()
            errors.append(f"{model}: Empty response")
        except Exception as error:
            message = str(error)
            lowered = message.lower()
            status = getattr(error, "status_code", None)
            if (
                status == 429 or "rate_limit" in lowered or "rate limit" in lowered
            ):
                errors.append(f"{model}: Rate limit reached")
                continue
            if (
                status == 404
                or "model_not_found" in lowered
                or "model_not_available" in lowered
            ):
                errors.append(f"{model}: Model unavailable")
                continue
            if status == 400 and any(term in lowered for term in (
                "context", "reduce the length", "messages or completion",
                "max_tokens", "token limit", "max_completion_tokens",
            )):
                errors.append(f"{model}: Request exceeded model limits")
                continue
            if status is not None and status >= 500:
                errors.append(f"{model}: Server error {status}")
                continue
            raise RuntimeError(f"Groq request failed with {model}: {message}") from error

    raise RuntimeError("All configured Groq models failed.\n\n" + "\n".join(errors))


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


def _language_instruction(language):
    instructions = {
        "English": "Write entirely in clear English.",
        "Hindi": "Write in Hindi using Devanagari script.",
        "Hinglish": "Write in natural Hinglish using the Latin alphabet. Keep technical terms in English.",
        "Spanish": "Write entirely in Spanish.",
        "French": "Write entirely in French.",
        "German": "Write entirely in German.",
    }
    return instructions.get(language, "Write in clear English.")


def _mode_prompt(mode):
    prompts = {
        "Detailed Study Notes": """
Create detailed, well-organized study notes. Include a suitable title, an introduction and overview, main concepts and explanations, important definitions, examples where useful, key points, and a short conclusion. Use headings, subheadings, and bullet points.
""",
        "Executive Summary": """
Create a concise executive summary covering the main topic, most important ideas, key findings, and conclusions. Avoid unnecessary details.
""",
        "Actionable Bullet Points": """
Convert the transcript into organized bullet points covering main ideas, important facts, key takeaways, practical steps or applications, and conclusions.
""",
        "Practice Quiz & Flashcards": """
Create multiple-choice questions with four options, correct answers and short explanations, plus flashcards and a final revision section. Base everything on the transcript.
""",
        "Formula & Keyword Cheat Sheet": """
Create a revision cheat sheet with keywords, definitions, formulas if present, important concepts, short explanations, and relationships. Do not invent formulas.
""",
    }
    return prompts.get(mode, prompts["Detailed Study Notes"])


def _detail_instruction(detail_level):
    instructions = {
        "Concise": "Keep the response short and focus on essential information.",
        "Standard": "Provide balanced explanations with useful details.",
        "In-Depth": "Provide comprehensive explanations and important details.",
    }
    return instructions.get(detail_level, instructions["Standard"])


def _summarize_chunk(client, chunk, chunk_number, total_chunks, mode, language, detail_level):
    messages = [
        {
            "role": "system",
            "content": "You are an expert educational assistant. Analyze lecture transcripts accurately. Do not invent facts.",
        },
        {
            "role": "user",
            "content": f"""
Analyze part {chunk_number} of {total_chunks}.

Output format:
{_mode_prompt(mode)}

Language: {_language_instruction(language)}
Detail: {_detail_instruction(detail_level)}

Preserve important concepts and explanations. This is one part of a larger lecture.

TRANSCRIPT:
{chunk}
""",
        },
    ]
    return call_groq_completion(
        client, messages, max_tokens=SUMMARY_OUTPUT_TOKENS, temperature=0.25
    )


def _reduce_batch(client, summaries, mode, language, detail_level):
    combined = "\n\n".join(summaries)
    messages = [
        {
            "role": "system",
            "content": "You are an expert educational editor. Combine lecture notes accurately and concisely.",
        },
        {
            "role": "user",
            "content": f"""
Combine these partial lecture notes.

Output format:
{_mode_prompt(mode)}

Language: {_language_instruction(language)}
Detail: {_detail_instruction(detail_level)}

Requirements: remove repetition, preserve important concepts, organize logically,
do not invent facts, and keep the result concise but useful.

PARTIAL NOTES:
{combined}
""",
        },
    ]
    return call_groq_completion(
        client, messages, max_tokens=REDUCE_OUTPUT_TOKENS, temperature=0.25
    )


def _reduce_summaries(client, summaries, mode, language, detail_level):
    if not summaries:
        raise ValueError("No summaries available to combine.")
    current = list(summaries)
    while len(current) > 1:
        next_level = []
        for index in range(0, len(current), 4):
            batch = current[index:index + 4]
            if len(batch) == 1:
                next_level.append(batch[0])
            else:
                next_level.append(_reduce_batch(
                    client, batch, mode, language, detail_level
                ))
        current = next_level
    return current[0]


def generate_summary(
    text,
    mode,
    api_key,
    detail_level="Standard",
    language="English",
    progress_callback=None,
):
    if not text or not str(text).strip():
        raise ValueError("Transcript text is empty.")
    if not api_key:
        raise ValueError("Groq API key is missing.")

    client = Groq(api_key=api_key)
    chunks = chunk_text(text, max_chars=CHUNK_SIZE)
    if not chunks:
        raise ValueError("Could not split transcript into text.")

    if progress_callback:
        progress_callback(f"Summarizing {len(chunks)} transcript parts in parallel...")

    def summarize_one(item):
        index, chunk = item
        return _summarize_chunk(
            client=client,
            chunk=chunk,
            chunk_number=index,
            total_chunks=len(chunks),
            mode=mode,
            language=language,
            detail_level=detail_level,
        )

    # Keep concurrency modest to reduce the chance of Groq rate limits.
    with ThreadPoolExecutor(max_workers=3) as executor:
        partial_summaries = list(executor.map(
            summarize_one, enumerate(chunks, start=1)
        ))

    if len(partial_summaries) == 1:
        return partial_summaries[0]
    if progress_callback:
        progress_callback("Combining lecture notes in groups...")
    return _reduce_summaries(
        client=client,
        summaries=partial_summaries,
        mode=mode,
        language=language,
        detail_level=detail_level,
    )


def ask_video_question(transcript_text, question, chat_history, api_key):
    if not api_key:
        raise ValueError("Groq API key is missing.")
    if not question or not question.strip():
        raise ValueError("Please enter a question.")
    client = Groq(api_key=api_key)
    transcript_context = str(transcript_text or "")[:6000]
    messages = [{
        "role": "system",
        "content": f"""
You are an educational assistant answering questions about a YouTube lecture.
Use the transcript as your main source. If the answer is not available, say so.

TRANSCRIPT:
{transcript_context}
""",
    }]
    for item in (chat_history or [])[-6:]:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content", item.get("message", ""))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            role, content = item[0], item[1]
        else:
            continue
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": str(content)[:1500]})
    messages.append({"role": "user", "content": question.strip()})
    return call_groq_completion(
        client, messages, max_tokens=1200, temperature=0.3
    )


def generate_mindmap_code(transcript_text, api_key):
    if not api_key:
        raise ValueError("Groq API key is missing.")
    if not transcript_text or not str(transcript_text).strip():
        raise ValueError("Transcript text is empty.")

    client = Groq(api_key=api_key)
    messages = [
        {
            "role": "system",
            "content": '''
Create a concept mind map from the lecture transcript.
Return ONLY valid JSON with this structure:
{"nodes": ["Main topic", "Concept 1"], "edges": [[0, 1]]}
Include 5 to 15 short labels. The first node is the main topic.
Edges are pairs of valid node indexes starting at 0.
Do not include Markdown fences or other text.
''',
        },
        {
            "role": "user",
            "content": "Create the mind map from this transcript:\n\n" + str(transcript_text)[:4000],
        },
    ]
    result = call_groq_completion(
        client, messages, max_tokens=1200, temperature=0.2
    )
    result = re.sub(r"^```(?:json)?\s*", "", result.strip(), flags=re.IGNORECASE)
    result = re.sub(r"\s*```$", "", result.strip())
    try:
        data = json.loads(result)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "The AI returned invalid mind map data. Please generate the map again."
        ) from exc

    nodes = data.get("nodes") if isinstance(data, dict) else None
    edges = data.get("edges") if isinstance(data, dict) else None
    if not isinstance(nodes, list) or not nodes:
        raise RuntimeError("The AI returned a mind map with no concepts.")

    clean_nodes = []
    for label in nodes[:15]:
        label = str(label).replace('"', "'").replace("\\", " ").replace("\n", " ").strip()
        clean_nodes.append(" ".join(label.split())[:90] or "Concept")

    lines = ["graph TD"]
    lines.extend(f'    N{i}["{label}"]' for i, label in enumerate(clean_nodes))
    valid_edges = 0
    if isinstance(edges, list):
        for edge in edges:
            if (
                isinstance(edge, list)
                and len(edge) == 2
                and all(isinstance(i, int) and 0 <= i < len(clean_nodes) for i in edge)
            ):
                lines.append(f"    N{edge[0]} --> N{edge[1]}")
                valid_edges += 1
    if not valid_edges and len(clean_nodes) > 1:
        lines.extend(f"    N{i} --> N{i + 1}" for i in range(len(clean_nodes) - 1))
    return "\n".join(lines)
