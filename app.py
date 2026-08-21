import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from transcript_service import extract_video_id, get_transcript
from ai_service import generate_summary, ask_video_question, generate_mindmap_code, generate_interactive_quiz_data
from pdf_service import create_pdf

load_dotenv()

st.set_page_config(
    page_title="LectureDigest AI — Smart Study Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

def resolve_api_key() -> str:
    key = None
    try:
        if "GROQ_API_KEY" in st.secrets:
            key = st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    if not key:
        key = os.getenv("GROQ_API_KEY", "")
    return key.strip() if key else ""

active_api_key = resolve_api_key()

# Session State Initializations
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "Dark"
if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []
if "url_input_box" not in st.session_state:
    st.session_state["url_input_box"] = ""
if "flashcard_idx" not in st.session_state:
    st.session_state["flashcard_idx"] = 0
if "show_card_answer" not in st.session_state:
    st.session_state["show_card_answer"] = False
if "quiz_submitted" not in st.session_state:
    st.session_state["quiz_submitted"] = False
if "interactive_study_data" not in st.session_state:
    st.session_state["interactive_study_data"] = None

def set_url(url: str):
    st.session_state["url_input_box"] = url

col_title, col_toggle = st.columns([5, 1.5])
with col_toggle:
    theme_selection = st.radio(
        "Theme Toggle",
        options=["🌙 Dark", "☀️ Light"],
        index=0 if st.session_state["theme_mode"] == "Dark" else 1,
        horizontal=True,
        label_visibility="collapsed"
    )
    chosen_mode = "Dark" if "Dark" in theme_selection else "Light"
    if chosen_mode != st.session_state["theme_mode"]:
        st.session_state["theme_mode"] = chosen_mode
        st.rerun()

is_dark = st.session_state["theme_mode"] == "Dark"

DARK_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #0B0F19 !important; color: #F8FAFC !important; }
    section[data-testid="stSidebar"] { background-color: #111827 !important; border-right: 1px solid rgba(255, 255, 255, 0.08) !important; }
    header[data-testid="stHeader"] { background-color: transparent !important; }
    header[data-testid="stHeader"] button, header[data-testid="stHeader"] a, header[data-testid="stHeader"] svg, div[data-testid="stToolbar"] svg, div[data-testid="stToolbar"] button {
        color: #F8FAFC !important; fill: #F8FAFC !important; stroke: #F8FAFC !important; opacity: 0.95 !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, label, div, .stMarkdown { color: #F8FAFC !important; }
    .hero-container {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(168, 85, 247, 0.12) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 16px; padding: 2.2rem 2rem; text-align: center; margin-bottom: 1.5rem; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    .badge { background: rgba(99, 102, 241, 0.3) !important; color: #A5B4FC !important; border: 1px solid rgba(99, 102, 241, 0.5) !important; }
    .metric-card {
        background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px; padding: 1.2rem; text-align: center; transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover { transform: translateY(-2px); border-color: #818CF8 !important; }
    .metric-value { color: #818CF8 !important; font-size: 1.7rem; font-weight: 800; }
    .metric-label { color: #94A3B8 !important; font-size: 0.85rem; }
    .flashcard-box {
        background: #1E293B; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 14px;
        padding: 2.2rem; min-height: 180px; display: flex; flex-direction: column; justify-content: center;
        align-items: center; text-align: center; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3); margin-bottom: 1rem;
    }
    div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
        background-color: #1E293B !important; color: #FFFFFF !important; border: 1px solid rgba(255, 255, 255, 0.18) !important; border-radius: 8px;
    }
    div[data-testid="stTextInput"] input:focus, div[data-testid="stTextArea"] textarea:focus { border-color: #818CF8 !important; box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.25) !important; }
    div[data-baseweb="select"] > div {
        background-color: #1E293B !important; color: #FFFFFF !important; border: 1px solid rgba(255, 255, 255, 0.18) !important; border-radius: 8px;
    }
    div[data-baseweb="select"] * { color: #FFFFFF !important; fill: #FFFFFF !important; }
    ul[data-baseweb="menu"] { background-color: #1E293B !important; }
    ul[data-baseweb="menu"] li:hover { background-color: #334155 !important; }
    button[kind="secondary"] {
        background-color: #1E293B !important; color: #F8FAFC !important; border: 1px solid rgba(255, 255, 255, 0.12) !important; border-radius: 8px; transition: all 0.2s ease-in-out !important;
    }
    button[kind="secondary"]:hover {
        background-color: #334155 !important; border-color: #818CF8 !important; color: #FFFFFF !important; transform: translateY(-2px) !important; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
    }
    button[kind="primary"] {
        background: linear-gradient(90deg, #6366F1, #4F46E5) !important; color: #FFFFFF !important; border: none !important; border-radius: 8px; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4) !important; transition: all 0.2s ease-in-out !important;
    }
    button[kind="primary"]:hover { background: linear-gradient(90deg, #4F46E5, #4338CA) !important; transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6) !important; }
</style>
"""

LIGHT_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #F8FAFC !important; color: #0F172A !important; }
    section[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0 !important; box-shadow: 2px 0 10px rgba(0, 0, 0, 0.02) !important; }
    header[data-testid="stHeader"] { background-color: transparent !important; }
    header[data-testid="stHeader"] button, header[data-testid="stHeader"] a, header[data-testid="stHeader"] svg, div[data-testid="stToolbar"] svg, div[data-testid="stToolbar"] button {
        color: #0F172A !important; fill: #0F172A !important; stroke: #0F172A !important; opacity: 0.95 !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, label, div, .stMarkdown { color: #0F172A !important; }
    .hero-container {
        background: linear-gradient(135deg, #FFFFFF 0%, #EEF2FF 100%) !important; border: 1px solid #C7D2FE !important; border-radius: 16px; padding: 2.2rem 2rem; text-align: center; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(99, 102, 241, 0.08);
    }
    .badge { background: #EEF2FF !important; color: #4F46E5 !important; border: 1px solid #C7D2FE !important; }
    .metric-card {
        background: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-radius: 12px; padding: 1.2rem; text-align: center; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03); transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover { transform: translateY(-2px); border-color: #6366F1 !important; box-shadow: 0 6px 16px rgba(99, 102, 241, 0.1); }
    .metric-value { color: #4F46E5 !important; font-size: 1.7rem; font-weight: 800; }
    .metric-label { color: #64748B !important; font-size: 0.85rem; font-weight: 500; }
    .flashcard-box {
        background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 14px;
        padding: 2.2rem; min-height: 180px; display: flex; flex-direction: column; justify-content: center;
        align-items: center; text-align: center; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); margin-bottom: 1rem;
    }
    div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
        background-color: #FFFFFF !important; color: #0F172A !important; border: 1px solid #CBD5E1 !important; border-radius: 8px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }
    div[data-testid="stTextInput"] input:focus, div[data-testid="stTextArea"] textarea:focus { border-color: #4F46E5 !important; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15) !important; }
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important; color: #0F172A !important; border: 1px solid #CBD5E1 !important; border-radius: 8px;
    }
    div[data-baseweb="select"] * { color: #0F172A !important; fill: #0F172A !important; }
    button[kind="secondary"] {
        background-color: #FFFFFF !important; color: #1E293B !important; border: 1px solid #CBD5E1 !important; border-radius: 8px; transition: all 0.2s ease-in-out !important;
    }
    button[kind="secondary"]:hover {
        background-color: #EEF2FF !important; border-color: #6366F1 !important; color: #4F46E5 !important; transform: translateY(-2px) !important;
    }
    button[kind="primary"] {
        background: linear-gradient(90deg, #4F46E5, #4338CA) !important; color: #FFFFFF !important; border: none !important; border-radius: 8px; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3) !important;
    }
    button[kind="primary"]:hover { background: linear-gradient(90deg, #4338CA, #3730A3) !important; transform: translateY(-2px) !important; }
</style>
"""

st.markdown(DARK_CSS if is_dark else LIGHT_CSS, unsafe_allow_html=True)
st.markdown("""
<style>
    .badge { padding: 0.35rem 0.85rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; display: inline-block; margin-bottom: 0.6rem; }
    .stButton>button { font-weight: 600; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🛠️ Study Controls")
    summary_mode = st.selectbox(
        "Output Format:",
        [
            "Detailed Study Notes",
            "Executive Summary",
            "Actionable Bullet Points",
            "Practice Quiz & Flashcards",
            "Formula & Keyword Cheat Sheet"
        ]
    )
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        detail_level = st.selectbox("Depth:", ["Standard", "Concise", "In-Depth"])
    with col_s2:
        output_lang = st.selectbox("Language:", ["English", "Hindi", "Hinglish", "Spanish", "French", "German"])

    st.markdown("---")
    st.caption("🔒 System secured via Cloud Secret Management.")

st.markdown("""
<div class="hero-container">
    <div class="badge">⚡ Groq LPU Accelerated</div>
    <h1 style="margin: 0.2rem 0; font-weight: 800; font-size: 2.3rem;">AI YouTube Lecture Digest</h1>
    <p style="margin: 0; font-size: 0.95rem;">Convert video lectures into structured notes, mind maps, quizzes, and searchable subtitles.</p>
</div>
""", unsafe_allow_html=True)

col_lbl, c1, c2, c3 = st.columns([1.5, 2, 2, 2])
with col_lbl:
    st.markdown("**Sample Lectures:**")
with c1:
    st.button("🧠 Neural Networks", use_container_width=True, on_click=set_url, args=("https://www.youtube.com/watch?v=aircAruvnKk",))
with c2:
    st.button("🐍 Python in 100s", use_container_width=True, on_click=set_url, args=("https://www.youtube.com/watch?v=dhgEAm8384U",))
with c3:
    st.button("🌐 Operating Systems", use_container_width=True, on_click=set_url, args=("https://www.youtube.com/watch?v=26QPDBe-NB8",))

url_input = st.text_input(
    "Enter YouTube Video URL:", 
    key="url_input_box",
    placeholder="https://www.youtube.com/watch?v=aircAruvnKk"
)

with st.expander("📋 Direct Text / Transcript Input (Optional)"):
    direct_transcript_text = st.text_area("Paste raw transcript or lecture notes here:", height=130)

col_btn, _ = st.columns([1.5, 4])
with col_btn:
    generate_clicked = st.button("🚀 Process & Generate", type="primary", use_container_width=True)

if generate_clicked:
    target_url = st.session_state.get("url_input_box", "").strip()
    direct_text = direct_transcript_text.strip() if direct_transcript_text else ""
    
    if not target_url and not direct_text:
        st.error("Please enter a YouTube URL or paste transcript text.")
    elif not active_api_key:
        st.error("GROQ_API_KEY is not configured in Streamlit Secrets. Please add your key under app Settings > Secrets.")
    else:
        raw_text = ""
        segments = []
        video_id = extract_video_id(target_url) if target_url else "direct_text"
        
        try:
            if direct_text:
                raw_text = direct_text
                segments = [{"timestamp": "00:00", "text": p.strip()} for p in direct_text.split('\n') if p.strip()]
            else:
                with st.spinner("Extracting lecture content..."):
                    raw_text, segments = get_transcript(video_id, active_api_key)

            with st.spinner(f"Generating {summary_mode} in {output_lang}..."):
                notes = generate_summary(raw_text, summary_mode, active_api_key, detail_level, output_lang)

            total_words = len(raw_text.split())
            summary_words = len(notes.split())
            read_time = max(1, round(total_words / 130))
            time_saved = max(1, round(read_time - (summary_words / 200)))

            st.session_state['summary'] = notes
            st.session_state['raw_text'] = raw_text
            st.session_state['video_id'] = video_id
            st.session_state['segments'] = segments
            st.session_state['total_words'] = total_words
            st.session_state['time_saved'] = time_saved
            st.session_state['selected_lang'] = output_lang
            st.session_state['mindmap'] = None
            st.session_state['interactive_study_data'] = None
            st.session_state['quiz_submitted'] = False
            st.session_state['flashcard_idx'] = 0
            st.session_state['show_card_answer'] = False

            st.success("Study assets generated successfully!")
        except Exception as e:
            st.error(f"{str(e)}")

if 'summary' in st.session_state:
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{st.session_state.get('total_words', 0):,}</div>
            <div class="metric-label">Words Transcribed</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">~{st.session_state.get('time_saved', 0)} mins</div>
            <div class="metric-label">Estimated Time Saved</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(st.session_state.get('segments', []))}</div>
            <div class="metric-label">Subtitle Blocks</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    left_col, right_col = st.columns([3, 2], gap="large")

    with left_col:
        tab_notes, tab_quiz, tab_chat, tab_mindmap, tab_transcript = st.tabs([
            "📝 AI Notes",
            "🎯 Interactive Quiz",
            "💬 Chat with Video", 
            "🗺️ Concept Mind Map", 
            "📜 Searchable Subtitles"
        ])

        with tab_notes:
            st.markdown(st.session_state['summary'])
            st.markdown("---")
            d1, d2 = st.columns(2)
            with d1:
                st.download_button(
                    "📥 Download Markdown (.md)",
                    data=st.session_state['summary'],
                    file_name="study_notes.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with d2:
                try:
                    pdf_bytes = create_pdf(st.session_state['summary'])
                    st.download_button(
                        "📄 Download PDF (.pdf)",
                        data=pdf_bytes,
                        file_name="study_notes.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception:
                    st.caption("PDF export preview is optimized for standard character sets.")

        with tab_quiz:
            st.subheader("🎯 Interactive Knowledge Check & Revision Deck")
            
            if st.session_state.get("interactive_study_data") is None:
                if st.button("⚡ Generate Interactive MCQ & Flashcards Deck", type="primary"):
                    with st.spinner("Analyzing lecture to construct questions..."):
                        quiz_data = generate_interactive_quiz_data(st.session_state['raw_text'], active_api_key)
                        st.session_state["interactive_study_data"] = quiz_data
                        st.rerun()
            else:
                study_data = st.session_state["interactive_study_data"]
                quiz_items = study_data.get("quiz", [])
                flashcard_items = study_data.get("flashcards", [])

                subtab_mcq, subtab_cards = st.tabs(["🧠 Multiple Choice Quiz", "🗂️ Interactive Flashcards"])

                with subtab_mcq:
                    user_answers = {}
                    for idx, q_item in enumerate(quiz_items):
                        st.markdown(f"**Q{idx + 1}: {q_item.get('question')}**")
                        opts = q_item.get("options", [])
                        user_answers[idx] = st.radio(
                            f"Select an answer for Q{idx + 1}:",
                            opts,
                            key=f"mcq_radio_{idx}",
                            label_visibility="collapsed"
                        )
                        st.markdown("<br>", unsafe_allow_html=True)

                    c_submit, _ = st.columns([2, 3])
                    with c_submit:
                        if st.button("Submit Quiz Answers", type="primary", use_container_width=True):
                            st.session_state["quiz_submitted"] = True

                    if st.session_state.get("quiz_submitted"):
                        st.markdown("---")
                        score = 0
                        for idx, q_item in enumerate(quiz_items):
                            correct_ans = q_item.get("correct_answer")
                            chosen_ans = user_answers.get(idx)
                            is_correct = chosen_ans == correct_ans
                            if is_correct:
                                score += 1
                                st.success(f"**Q{idx + 1}: Correct!** ✅ — {chosen_ans}")
                            else:
                                st.error(f"**Q{idx + 1}: Incorrect.** ❌ (Your choice: {chosen_ans}) | **Correct Answer:** {correct_ans}")
                            st.info(f"💡 *Explanation:* {q_item.get('explanation')}")

                        st.markdown(f"### 🏆 Final Score: `{score} / {len(quiz_items)}` ({int((score/len(quiz_items))*100)}%)")

                with subtab_cards:
                    if flashcard_items:
                        curr_card_idx = st.session_state["flashcard_idx"] % len(flashcard_items)
                        curr_card = flashcard_items[curr_card_idx]

                        st.caption(f"Card {curr_card_idx + 1} of {len(flashcard_items)}")
                        
                        card_content = curr_card.get("back") if st.session_state["show_card_answer"] else curr_card.get("front")
                        card_label = "💡 Answer / Definition" if st.session_state["show_card_answer"] else "📌 Concept / Term"

                        st.markdown(f"""
                        <div class="flashcard-box">
                            <span style="font-size: 0.85rem; font-weight: 700; color: #818CF8; margin-bottom: 0.5rem;">{card_label}</span>
                            <div style="font-size: 1.15rem; font-weight: 600;">{card_content}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        fc_col1, fc_col2, fc_col3 = st.columns([1.5, 2, 1.5])
                        with fc_col1:
                            if st.button("⬅️ Previous Card", use_container_width=True):
                                st.session_state["flashcard_idx"] = (st.session_state["flashcard_idx"] - 1) % len(flashcard_items)
                                st.session_state["show_card_answer"] = False
                                st.rerun()
                        with fc_col2:
                            toggle_text = "🙈 Hide Answer" if st.session_state["show_card_answer"] else "🔄 Flip / Reveal Answer"
                            if st.button(toggle_text, use_container_width=True):
                                st.session_state["show_card_answer"] = not st.session_state["show_card_answer"]
                                st.rerun()
                        with fc_col3:
                            if st.button("Next Card ➡️", use_container_width=True):
                                st.session_state["flashcard_idx"] = (st.session_state["flashcard_idx"] + 1) % len(flashcard_items)
                                st.session_state["show_card_answer"] = False
                                st.rerun()

        with tab_chat:
            st.subheader("💬 Ask Doubts from this Lecture")
            user_q = st.text_input("Ask a question:", placeholder="e.g., Explain the algorithm mentioned in the beginning", key="chat_input_field")
            if st.button("Ask AI Assistant"):
                if user_q.strip():
                    with st.spinner("Searching video content..."):
                        cur_lang = st.session_state.get('selected_lang', 'English')
                        ans = ask_video_question(st.session_state['raw_text'], user_q, active_api_key, cur_lang)
                        st.session_state['qa_history'].append({"q": user_q, "a": ans})

            for chat in reversed(st.session_state['qa_history']):
                st.markdown(f"**Q:** {chat['q']}")
                st.info(f"**A:** {chat['a']}")

        with tab_mindmap:
            st.subheader("🗺️ Hierarchical Mind Map")
            if st.button("Generate Visual Map"):
                with st.spinner("Generating flowchart structure..."):
                    mm_code = generate_mindmap_code(st.session_state['raw_text'], active_api_key)
                    st.session_state['mindmap'] = mm_code

            if st.session_state.get('mindmap'):
                mermaid_html = f"""
                <div class="mermaid" style="background-color: transparent;">
                    {st.session_state['mindmap']}
                </div>
                <script type="module">
                    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                    mermaid.initialize({{ startOnLoad: true, theme: '{"dark" if is_dark else "default"}' }});
                </script>
                """
                components.html(mermaid_html, height=450, scrolling=True)

        with tab_transcript:
            st.subheader("📜 Searchable Subtitles")
            search_term = st.text_input("🔍 Filter keywords:", placeholder="e.g., gradient descent")
            filtered = [
                s for s in st.session_state['segments'] 
                if not search_term or search_term.lower() in s['text'].lower()
            ]
            st.caption(f"Showing {len(filtered)} matching segments")
            for seg in filtered[:120]:
                st.markdown(f"**`{seg['timestamp']}`** : {seg['text']}")

    with right_col:
        st.subheader("📺 Video Player")
        if st.session_state.get('video_id') and st.session_state['video_id'] != "direct_text":
            st.video(f"https://www.youtube.com/watch?v={st.session_state['video_id']}")
        else:
            st.info("Direct text input mode active.")
