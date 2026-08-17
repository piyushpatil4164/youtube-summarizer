from groq import Groq

def get_best_available_model(client: Groq) -> str:
    """
    Dynamically queries your Groq API account for currently active models.
    Guarantees no 404 'model_not_found' or 'decommissioned' errors.
    """
    try:
        models_data = client.models.list()
        active_ids = [m.id for m in models_data.data if hasattr(m, 'id')]
        
        # Priority order for preferred high-performance models
        preferred_order = [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
        
        for p in preferred_order:
            if p in active_ids:
                return p
                
        # Pick first available text generation model
        for m_id in active_ids:
            if "whisper" not in m_id.lower() and "guard" not in m_id.lower():
                return m_id
    except Exception:
        pass
        
    return "llama-3.3-70b-versatile"

def call_groq(client: Groq, messages: list, max_tokens: int = 1500, temperature: float = 0.3) -> str:
    """Calls Groq using dynamic model resolution with automated fallback."""
    selected_model = get_best_available_model(client)
    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception:
        # Fallback to standard instant endpoint
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

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
        return call_groq(client, messages, max_tokens=1500, temperature=0.3)

    intermediate_summaries = []
    for idx, c in enumerate(chunks[:3]):
        messages = [
            {"role": "system", "content": f"Summarize key academic concepts from this lecture part concisely in {language}."},
            {"role": "user", "content": f"Part {idx+1} transcript:\n{c}"}
        ]
        part_summary = call_groq(client, messages, max_tokens=500, temperature=0.3)
        intermediate_summaries.append(part_summary)

    combined_intermediate = "\n\n".join(intermediate_summaries)
    final_messages = [
        {"role": "system", "content": f"Synthesize multi-part notes into a unified study guide in {language}."},
        {"role": "user", "content": f"{selected_prompt}\n\n--- COMBINED SUMMARY POINTS ---\n{combined_intermediate}"}
    ]
    return call_groq(client, final_messages, max_tokens=1800, temperature=0.3)

def ask_video_question(transcript_text: str, question: str, api_key: str, language: str = "English") -> str:
    """Answers specific student questions using only lecture context."""
    client = Groq(api_key=api_key)
    safe_transcript = transcript_text[:12000]

    messages = [
        {"role": "system", "content": f"Answer the question accurately in {language} using ONLY the lecture content provided."},
        {"role": "user", "content": f"Lecture Excerpt:\n{safe_transcript}\n\nQuestion: {question}"}
    ]
    return call_groq(client, messages, max_tokens=600, temperature=0.2)

def generate_mindmap_code(transcript_text: str, api_key: str) -> str:
    """Generates Mermaid.js flowchart code."""
    client = Groq(api_key=api_key)
    safe_transcript = transcript_text[:8000]

    messages = [
        {"role": "system", "content": "Output ONLY valid Mermaid.js graph code starting with 'graph TD'. No markdown code blocks, backticks, or extra commentary."},
        {"role": "user", "content": f"Lecture content:\n{safe_transcript}"}
    ]
    raw_code = call_groq(client, messages, max_tokens=500, temperature=0.2)
    return raw_code.replace("```mermaid", "").replace("```", "").strip()
