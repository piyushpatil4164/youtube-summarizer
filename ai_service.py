import math
from groq import Groq

def chunk_text(text: str, max_chars: int = 12000) -> list[str]:
    """Splits long text into manageable chunks to stay well below the 6000 TPM limit."""
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
    """Generates structured notes safely within Groq TPM limits using Map-Reduce for long transcripts."""
    client = Groq(api_key=api_key)
    chunks = chunk_text(text, max_chars=11000)
    
    prompts = {
        "Detailed Study Notes": (
            f"You are an expert university professor. Create comprehensive, exam-ready study notes in {language}.\n"
            f"Detail Level: {detail_level}\n\n"
            "Structure strictly with these headers:\n"
            "## 📌 Core Concept & Overview\n"
            "## 🔑 Key Topics & Technical Breakdown\n"
            "## 📐 Formulas, Definitions & Rules\n"
            "## 💡 Practical Examples & Applications\n"
            "## ❓ Potential Exam Questions & Answers"
        ),
        "Executive Summary": (
            f"Provide a structured executive briefing of this content in {language}.\n"
            f"Detail Level: {detail_level}\n\n"
            "- **Core Problem / Thesis**\n"
            "- **Key Innovations & Takeaways**\n"
            "- **Final Verdict & Implications**"
        ),
        "Actionable Bullet Points": (
            f"Extract the most critical points, step-by-step instructions, and key facts in {language}.\n"
            f"Detail Level: {detail_level}\n"
            "Use clear hierarchical bullet points with bold keywords."
        ),
        "Practice Quiz & Flashcards": (
            f"Create a revision quiz and flashcard set in {language}.\n\n"
            "### 🧠 Multiple Choice Questions (5 Questions)\n"
            "Provide 4 options per question with answers and explanations.\n\n"
            "### 🗂️ Flashcard Deck (5 Key Concepts)\n"
            "Format: **Front (Term/Question)** -> **Back (Definition/Answer)**"
        ),
        "Formula & Keyword Cheat Sheet": (
            f"Extract all technical terms, definitions, and formulas into a structured reference guide in {language}."
        )
    }

    selected_prompt = prompts.get(mode, prompts["Detailed Study Notes"])

    # If short video, process in single call
    if len(chunks) == 1:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an elite academic AI assistant dedicated to high-precision study synthesis."},
                {"role": "user", "content": f"{selected_prompt}\n\n--- TRANSCRIPT ---\n{chunks[0]}"}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content

    # If long lecture, summarize sections first then synthesize (Map-Reduce)
    intermediate_summaries = []
    for idx, c in enumerate(chunks[:3]):  # Cap at top sections to avoid rate throttling
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Summarize key academic concepts and facts from this lecture part concisely."},
                {"role": "user", "content": f"Part {idx+1} transcript:\n{c}"}
            ],
            temperature=0.3,
            max_tokens=500
        )
        intermediate_summaries.append(resp.choices[0].message.content)

    combined_intermediate = "\n\n".join(intermediate_summaries)

    # Final synthesis
    final_response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You synthesize multi-part lecture notes into a final unified study guide."},
            {"role": "user", "content": f"{selected_prompt}\n\n--- COMBINED SUMMARY POINTS ---\n{combined_intermediate}"}
        ],
        temperature=0.3,
        max_tokens=1800
    )
    return final_response.choices[0].message.content


def ask_video_question(transcript_text: str, question: str, api_key: str) -> str:
    """Answers user questions safely within TPM context limits."""
    client = Groq(api_key=api_key)
    safe_transcript = transcript_text[:11000]

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Answer the question accurately using ONLY the lecture content provided. If not covered, state so."},
            {"role": "user", "content": f"Lecture Excerpt:\n{safe_transcript}\n\nQuestion: {question}"}
        ],
        temperature=0.2,
        max_tokens=600
    )
    return response.choices[0].message.content


def generate_mindmap_code(transcript_text: str, api_key: str) -> str:
    """Generates Mermaid.js flowchart syntax within token limits."""
    client = Groq(api_key=api_key)
    safe_transcript = transcript_text[:8000]

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Output ONLY valid Mermaid.js graph code starting with 'graph TD'. No markdown code blocks, backticks, or extra explanation."},
            {"role": "user", "content": f"Lecture content:\n{safe_transcript}"}
        ],
        temperature=0.2,
        max_tokens=500
    )
    raw_code = response.choices[0].message.content.strip()
    return raw_code.replace("```mermaid", "").replace("```", "").strip()
