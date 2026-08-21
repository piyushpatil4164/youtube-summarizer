import os
import re
import json
from groq import Groq

def call_groq_completion(client: Groq, messages: list, max_tokens: int = 1500, temperature: float = 0.3) -> str:
    """
    Dynamically queries your Groq account to find all active chat models.
    Tries each available model automatically to prevent 404 or decommission errors.
    """
    available_models = []
    try:
        models_data = client.models.list()
        for m in models_data.data:
            m_id = getattr(m, 'id', '')
            if m_id and "whisper" not in m_id.lower() and "guard" not in m_id.lower() and "distil" not in m_id.lower():
                available_models.append(m_id)
    except Exception:
        pass

    priority = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]
    
    ordered_models = []
    for p in priority:
        if p in available_models and p not in ordered_models:
            ordered_models.append(p)
    for m in available_models:
        if m not in ordered_models:
            ordered_models.append(m)

    if not ordered_models:
        ordered_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-8b-8192"]

    last_error = None
    for model_name in ordered_models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            continue

    raise Exception(f"Failed to generate output with available Groq models: {str(last_error)}")

def chunk_text(text: str, max_chars: int = 14000) -> list[str]:
    """Splits transcript text into bounded chunks to stay within TPM limits."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_length += len(word) + 1
        current_chunk.append(word)
        if current_length >= max_chars:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks if chunks else [text]

def generate_summary(text: str, mode: str, api_key: str, detail_level: str = "Standard", language: str = "English") -> str:
    """Generates structured notes in the selected language."""
    client = Groq(api_key=api_key)
    chunks = chunk_text(text, max_chars=13000)
    
    lang_instruction = (
        f"Generate the entire response STRICTLY in {language}. "
        "If Hinglish is selected, use natural conversational Hindi written in the Latin alphabet with technical terms in English."
    )

    prompts = {
        "Detailed Study Notes": (
            f"You are an expert academic professor. Create comprehensive, exam-ready study notes.\n"
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
            f"Provide a structured executive briefing of this lecture.\n"
            f"{lang_instruction}\n"
            f"Detail Level: {detail_level}\n\n"
            "- **Core Problem / Thesis**\n"
            "- **Key Innovations & Takeaways**\n"
            "- **Final Verdict & Implications**"
        ),
        "Actionable Bullet Points": (
            f"Extract critical points, step-by-step instructions, and key facts.\n"
            f"{lang_instruction}\n"
            f"Detail Level: {detail_level}\n"
            "Use clear hierarchical bullet points with bold keywords."
        ),
        "Practice Quiz & Flashcards": (
            f"Create a revision quiz and flashcard set.\n"
            f"{lang_instruction}\n\n"
            "### 🧠 Multiple Choice Questions (5 Questions)\n"
            "Provide 4 options per question with answers and explanations.\n\n"
            "### 🗂️ Flashcard Deck (5 Key Concepts)\n"
            "Format: **Front (Term/Question)** -> **Back (Definition/Answer)**"
        ),
        "Formula & Keyword Cheat Sheet": (
            f"Extract all technical terms, definitions, and equations into a reference cheat sheet.\n"
            f"{lang_instruction}"
        )
    }

    selected_prompt = prompts.get(mode, prompts["Detailed Study Notes"])

    if len(chunks) == 1:
        messages = [
            {"role": "system", "content": "You are an elite academic AI assistant dedicated to high-precision study synthesis."},
            {"role": "user", "content": f"{selected_prompt}\n\n--- TRANSCRIPT ---\n{chunks[0]}"}
        ]
        return call_groq_completion(client, messages, max_tokens=1500, temperature=0.3)

    intermediate_summaries = []
    for idx, c in enumerate(chunks[:3]):
        messages = [
            {"role": "system", "content": f"Summarize key academic concepts from this lecture part concisely in {language}."},
            {"role": "user", "content": f"Part {idx+1} transcript:\n{c}"}
        ]
        part_summary = call_groq_completion(client, messages, max_tokens=500, temperature=0.3)
        intermediate_summaries.append(part_summary)

    combined_intermediate = "\n\n".join(intermediate_summaries)
    final_messages = [
        {"role": "system", "content": f"Synthesize multi-part notes into a unified study guide in {language}."},
        {"role": "user", "content": f"{selected_prompt}\n\n--- COMBINED SUMMARY POINTS ---\n{combined_intermediate}"}
    ]
    return call_groq_completion(client, final_messages, max_tokens=1800, temperature=0.3)

def generate_mindmap_code(transcript_text: str, api_key: str) -> str:
    """Generates clean, sanitized Mermaid.js flowchart code."""
    client = Groq(api_key=api_key)
    safe_transcript = transcript_text[:8000]

    system_prompt = (
        "You are an expert flowchart creator. Convert the lecture into a clean, valid Mermaid.js graph.\n"
        "RULES:\n"
        "1. Start strictly with 'graph TD'\n"
        "2. Node IDs must be simple alphanumeric strings without spaces (e.g., A, B1, C2)\n"
        "3. Always wrap node text inside square brackets and double quotes, like: A[\"Core Topic\"] --> B[\"Sub Concept\"]\n"
        "4. Do NOT use special characters like colons, parentheses, or single quotes inside node labels\n"
        "5. Output ONLY raw Mermaid syntax. Do not wrap in markdown code blocks, backticks, or write explanations."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Lecture excerpt:\n{safe_transcript}"}
    ]
    raw_code = call_groq_completion(client, messages, max_tokens=500, temperature=0.1)
    
    clean = re.sub(r'```(?:mermaid)?', '', raw_code).replace('```', '').strip()
    if not clean.startswith("graph"):
        clean = "graph TD\n" + clean

    return clean

def generate_interactive_quiz(transcript_text: str, api_key: str, language: str = "English") -> dict:
    """Generates structured MCQs and Flashcards in pure JSON format."""
    client = Groq(api_key=api_key)
    safe_transcript = transcript_text[:12000]

    system_prompt = (
        "You are an expert exam creator. Generate an interactive quiz and flashcard deck from the lecture.\n"
        f"Language: {language}\n"
        "Return ONLY a valid, raw JSON object (no markdown, no ```json codeblocks) with this exact schema:\n"
        "{\n"
        '  "quiz": [\n'
        '    {\n'
        '      "question": "Question text here?",\n'
        '      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        '      "correct_index": 0,\n'
        '      "explanation": "Why this option is correct."\n'
        '    }\n'
        '  ],\n'
        '  "flashcards": [\n'
        '    {\n'
        '      "front": "Key Term / Concept",\n'
        '      "back": "Detailed concise explanation/definition"\n'
        '    }\n'
        '  ]\n'
        "}\n"
        "Provide exactly 5 high-yield MCQs and 5 flashcards."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Lecture Transcript:\n{safe_transcript}"}
    ]

    raw_response = call_groq_completion(client, messages, max_tokens=1500, temperature=0.2)
    clean_json = raw_response.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(clean_json)
    except Exception:
        match = re.search(r"\{.*\}", clean_json, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {"quiz": [], "flashcards": []}
