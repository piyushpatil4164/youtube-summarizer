import os
import time
from groq import Groq

def split_text_into_chunks(text: str, max_chars: int = 10000) -> list[str]:
    """Splits long text into manageable chunks to stay well within Groq TPM limits."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1
        if current_length >= max_chars:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def generate_summary(transcript_text: str, mode: str, api_key: str | None = None) -> str:
    """
    Generates structured educational notes from video transcripts with automatic
    chunk handling to stay within token limits.
    """
    resolved_key = api_key or os.getenv("GROQ_API_KEY")
    if not resolved_key:
        raise ValueError("API Key is missing. Please provide a valid Groq API Key.")

    client = Groq(api_key=resolved_key)

    prompts = {
        "Executive Summary": (
            "Provide a concise executive summary of the lecture. Structure with:\n"
            "1. **Core Objective & Main Premise**\n"
            "2. **Top 3–5 Key Takeaways**\n"
            "3. **Concluding Thoughts**"
        ),
        "Detailed Study Notes": (
            "Act as an expert academic tutor. Create comprehensive, structured study notes from this lecture transcript:\n"
            "1. **Overview & High-Level Summary**\n"
            "2. **Detailed Topic-by-Topic Breakdown** (with definitions and clear explanations)\n"
            "3. **Key Concepts & Terminology Cheat Sheet**\n"
            "4. **Important Review Questions with Answers**"
        ),
        "Actionable Bullet Points": (
            "Extract all actionable insights, key steps, and essential takeaways into a clean, hierarchical bulleted list."
        ),
        "Practice Quiz & Flashcards": (
            "Generate an interactive revision set based on the lecture:\n"
            "- 5 Multiple Choice Questions (include Question, Options A-D, Correct Answer, and a brief explanation)\n"
            "- 5 Short Flashcard Concept Questions with direct answers."
        )
    }

    selected_prompt = prompts.get(mode, prompts["Detailed Study Notes"])

    # If transcript is long, summarize chunks first
    chunks = split_text_into_chunks(transcript_text, max_chars=9000)

    if len(chunks) == 1:
        text_to_process = chunks[0]
    else:
        intermediate_summaries = []
        for i, chunk in enumerate(chunks[:3]):  # Process top key sections safely
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Extract the key educational concepts and facts from this section."},
                    {"role": "user", "content": f"Lecture Section {i+1}:\n{chunk}"}
                ],
                max_tokens=600,
                temperature=0.2
            )
            intermediate_summaries.append(resp.choices[0].message.content.strip())
            time.sleep(0.5)

        text_to_process = "\n\n".join(intermediate_summaries)

    system_prompt = (
        "You are an elite educational AI assistant. Your goal is to convert lecture material into "
        "well-organized, clear Markdown notes. Use bold text, bullet points, and clean formatting."
    )

    user_prompt = f"""
Lecture Context:
\"\"\"
{text_to_process}
\"\"\"

Task:
{selected_prompt}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=1500
    )

    return response.choices[0].message.content