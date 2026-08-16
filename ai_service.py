from groq import Groq

def generate_summary(text: str, mode: str, api_key: str, detail_level: str = "Standard", language: str = "English") -> str:
    """Generates structured notes based on selected study mode, detail level, and language."""
    client = Groq(api_key=api_key)
    
    # Truncate to avoid context window overflow
    processed_text = text[:30000]
    
    prompts = {
        "Detailed Study Notes": (
            f"You are an expert university professor. Create comprehensive, exam-ready study notes from this lecture transcript.\n"
            f"Target Language: {language}\n"
            f"Detail Level: {detail_level}\n\n"
            "Structure your response strictly as follows:\n"
            "## 📌 Core Concept & Overview\n(2-3 clear introductory paragraphs)\n\n"
            "## 🔑 Key Topics & Technical Deep-Dive\n(Use bullet points, bold terms, and clear subheadings)\n\n"
            "## 📐 Formulas, Definitions & Rules\n(List all key terms, laws, and equations)\n\n"
            "## 💡 Practical Examples & Applications\n(Concrete real-world use cases mentioned)\n\n"
            "## ❓ Potential Exam Questions\n(3-5 challenging questions with brief answers)"
        ),
        "Executive Summary": (
            f"You are a lead technical researcher. Provide a high-level executive briefing of this video in {language}.\n"
            f"Detail Level: {detail_level}\n\n"
            "Include: \n"
            "- **Problem Statement / Context**\n"
            "- **Key Innovations / Takeaways**\n"
            "- **Strategic Implications / Conclusion**"
        ),
        "Actionable Bullet Points": (
            f"Extract the most important points, step-by-step instructions, and key facts from this transcript in {language}.\n"
            f"Detail Level: {detail_level}\n"
            "Use hierarchical bullet points with bold keywords."
        ),
        "Practice Quiz & Flashcards": (
            f"Create a revision quiz and flashcard set in {language} from this transcript.\n\n"
            "### 🧠 Multiple Choice Questions (5 Questions)\n"
            "Provide 4 options per question, clearly marking the correct answer with an explanation.\n\n"
            "### 🗂️ Flashcard Deck (5 Key Concepts)\n"
            "Format as: **Front (Term/Question)** -> **Back (Definition/Answer)**"
        ),
        "Formula & Keyword Cheat Sheet": (
            f"Extract all technical terminology, definitions, and mathematical/scientific formulas from this transcript in {language}.\n"
            "Format as a clean reference table or categorized list."
        )
    }

    selected_prompt = prompts.get(mode, prompts["Detailed Study Notes"])

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are an elite academic AI assistant dedicated to high-precision educational note synthesis."},
            {"role": "user", "content": f"{selected_prompt}\n\n--- TRANSCRIPT ---\n{processed_text}"}
        ],
        temperature=0.3,
        max_tokens=2500
    )
    return response.choices[0].message.content


def ask_video_question(transcript_text: str, question: str, api_key: str) -> str:
    """Answers user questions strictly based on the provided video transcript."""
    client = Groq(api_key=api_key)
    processed_text = transcript_text[:25000]

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are an AI teaching assistant. Answer the student's question accurately using ONLY the video transcript provided. If the answer is not in the transcript, state that clearly."},
            {"role": "user", "content": f"Transcript:\n{processed_text}\n\nQuestion: {question}"}
        ],
        temperature=0.2,
        max_tokens=800
    )
    return response.choices[0].message.content


def generate_mindmap_code(transcript_text: str, api_key: str) -> str:
    """Generates Mermaid.js flowchart code representing lecture hierarchy."""
    client = Groq(api_key=api_key)
    processed_text = transcript_text[:15000]

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are an expert in visual knowledge graphs. Output ONLY valid Mermaid.js graph code starting with 'graph TD' representing the hierarchical structure of this lecture. Do not wrap in markdown quotes or backticks, just raw Mermaid syntax."},
            {"role": "user", "content": f"Transcript:\n{processed_text}"}
        ],
        temperature=0.2,
        max_tokens=600
    )
    raw_code = response.choices[0].message.content.strip()
    return raw_code.replace("```mermaid", "").replace("```", "").strip()
