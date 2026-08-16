# 🎓 AI YouTube Lecture Summarizer & Note Generator

An end-to-end AI web application that extracts transcripts from educational YouTube videos and generates structured study notes, cheat sheets, revision quizzes, and downloadable PDFs using Llama 3.1 on Groq.

## 🚀 Live Demo
- **Web App:** [Open AI YouTube Summarizer](https://youtube-summarizer-5ewx3n6ahlujve6ikbzesd.streamlit.app/)

## 🛠️ Features
- **Transcript Extraction:** Automated subtitle extraction with timestamps via `youtube-transcript-api`.
- **Intelligent Chunking:** Map-Reduce processing pipeline to handle long video transcripts without hitting token rate limits.
- **Multiple Note Styles:**
  - Detailed Academic Study Notes (definitions, breakdowns, formulas)
  - Executive Summaries
  - Actionable Bullet Points
  - Practice Quizzes & Flashcards
- **Multi-Format Export:** One-click download as Markdown (`.md`) or formatted PDF (`.pdf`).
- **Synchronized Video Player:** Embedded video with timestamped subtitle navigator.

## 🏗️ Tech Stack
- **Frontend / UI:** Streamlit
- **LLM Inference:** Groq Cloud API (`llama-3.1-8b-instant`)
- **Subtitle Parsing:** `youtube-transcript-api`
- **Document Generation:** `fpdf2`
- **Language:** Python 3.11+

## ⚙️ Local Setup
1. Clone the repository:
   ```bash
   git clone [https://github.com/piyushpatil4164/youtube-summarizer.git](https://github.com/piyushpatil4164/youtube-summarizer.git)
   cd youtube-summarizer
