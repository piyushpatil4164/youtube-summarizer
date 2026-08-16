import streamlit as st
import streamlit.components.v1 as components
from config import get_groq_api_key
from transcript_service import extract_video_id, get_transcript
from ai_service import generate_summary, ask_video_question, generate_mindmap_code
from pdf_service import create_pdf

# Page Configuration
st.set_page_config(
    page_title="LectureDigest AI — Smart Study Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "theme" not in st.session_state:
    st.session_state["theme"] = "Dark"
if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []

# Theme-Adaptive CSS
is_dark = st.session_state["theme"] == "Dark"
bg_color = "#0e1117" if is_dark else "#FFFFFF"
card_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.03)"
border_color = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.1)"
text_color = "#FAFAFA" if is_dark else "#1E293B"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    * {{
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}
    
    .hero-container {{
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.1) 100%);
        border: 1px solid {border_color};
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        text-align: center;
    }}
    
    .badge {{
        background: rgba(99, 102, 241, 0.2);
        color: #818CF8;
        padding: 0.3rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 0.5rem;
    }}
    
    .metric-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }}
    
    .metric-value {{
        font-size: 1.6rem;
        font-weight: 700;
        color: #6366F1;
    }}
    
    .metric-label {{
        font-size: 0.8rem;
        opacity: 0.8;
        margin-top: 0.2rem;
    }}
    
    .stButton>button {{
        border-radius: 8px;
        font-weight: 600;
    }}
</style>
""", unsafe_allow_html=True)

# Top Bar: Theme Switcher & Status
col_head, col_theme = st.columns([5, 1])
with col_theme:
    selected_theme = st.radio(
        "Theme",
        options=["Dark", "Light"],
        horizontal=True,
        index=0 if is_dark else 1,
        label_visibility="collapsed"
    )
    if selected_theme != st.session_state["theme"]:
        st.session_state["theme"] = selected_theme
        st.rerun()

# Sidebar: Advanced Customization
with st.sidebar:
    st.markdown("### ⚙️ Study Controls")
    
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
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        detail_level = st.selectbox("Depth:", ["Standard", "Concise", "In-Depth"])
    with col_opt2:
        output_lang = st.selectbox("Language:", ["English", "Hindi", "Hinglish", "Spanish", "French"])

    st.markdown("---")
    st.markdown("### 💡 Quick Tips")
    st.caption("• Use **Practice Quiz** before exams for rapid recall.")
    st.caption("• Use **Chat with Video** tab to resolve specific equations or questions.")
    st.markdown("---")
    st.caption("🔒 Secured via Cloud Secret Management.")

# Hero Header
st.markdown("""
<div class="hero-container">
    <div class="badge">⚡ Groq LPU Accelerated</div>
    <h1 style="margin: 0.2rem 0; font-weight: 800; font-size: 2.2rem;">AI YouTube Lecture Digest</h1>
    <p style="margin: 0; opacity: 0.85; font-size: 0.95rem;">Transform technical lectures and tutorials into structured notes, mind maps, quizzes, and searchable transcripts.</p>
</div>
""", unsafe_allow_html=True)

# Quick Samples
col_lbl, c1, c2, c3 = st.columns([1.5, 2, 2, 2])
with col_lbl:
    st.markdown("**Sample Lectures:**")
with c1:
    if st.button("🧠 Neural Networks", use_container_width=True):
        st.session_state['url_input_val'] = "https://www.youtube.com/watch?v=aircAruvnKk"
with c2:
    if st.button("🐍 Python in 100s", use_container_width=True):
        st.session_state['url_input_val'] = "https://www.youtube.com/watch?v=dhgEAm8384U"
with c3:
    if st.button("🌐 Operating Systems", use_container_width=True):
        st.session_state['url_input_val'] = "https://www.youtube.com/watch?v=26QPDBe-NB8"

# URL Input
input_val = st.session_state.get('url_input_val', '')
url_input = st.text_input("Enter YouTube Video URL:", value=input_val, placeholder="https://www.youtube.com/watch?v=aircAruvnKk")

col_btn, _ = st.columns([1.5, 4])
with col_btn:
    generate_clicked = st.button("🚀 Process & Generate", type="primary", use_container_width=True)

# Generation Execution
if generate_clicked:
    if not url_input.strip():
        st.error("Please enter a valid YouTube URL.")
    else:
        video_id = extract_video_id(url_input)
        if not video_id:
            st.error("Invalid YouTube URL format.")
        else:
            try:
                api_key = get_groq_api_key()

                with st.spinner("Extracting transcript and subtitles..."):
                    raw_text, segments = get_transcript(video_id)

                with st.spinner(f"Generating {summary_mode}..."):
                    notes = generate_summary(raw_text, summary_mode, api_key, detail_level, output_lang)

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
                st.session_state['mindmap'] = None

                st.success("Study assets generated successfully!")
            except Exception as e:
                clean_err = str(e).split("\n")[0]
                st.error(f"Error: {clean_err}")

# Output Section
if 'summary' in st.session_state:
    st.markdown("---")
    
    # Analytics Metrics
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
            <div class="metric-label">Time Saved</div>
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
        tab_notes, tab_chat, tab_mindmap, tab_transcript = st.tabs([
            "📝 AI Notes", 
            "💬 Chat with Video", 
            "🗺️ Concept Mind Map", 
            "📜 Searchable Subtitles"
        ])

        # TAB 1: AI Notes & Downloads
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
                pdf_bytes = create_pdf(st.session_state['summary'])
                st.download_button(
                    "📄 Download PDF (.pdf)",
                    data=pdf_bytes,
                    file_name="study_notes.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        # TAB 2: Chat with Video Q&A
        with tab_chat:
            st.subheader("💬 Ask Doubts from this Lecture")
            st.caption("Ask questions about equations, concepts, or timestamps discussed in this video.")
            
            user_q = st.text_input("Ask a question:", placeholder="e.g., What was the main assumption in step 2?", key="chat_input_field")
            if st.button("Ask AI Assistant"):
                if user_q.strip():
                    with st.spinner("Searching video content..."):
                        ans = ask_video_question(st.session_state['raw_text'], user_q, get_groq_api_key())
                        st.session_state['qa_history'].append({"q": user_q, "a": ans})

            for chat in reversed(st.session_state['qa_history']):
                st.markdown(f"**Q:** {chat['q']}")
                st.info(f"**A:** {chat['a']}")

        # TAB 3: Visual Mind Map
        with tab_mindmap:
            st.subheader("🗺️ Hierarchical Mind Map")
            if st.button("Generate Visual Map"):
                with st.spinner("Generating flowchart structure..."):
                    mm_code = generate_mindmap_code(st.session_state['raw_text'], get_groq_api_key())
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

        # TAB 4: Searchable Subtitle Navigator
        with tab_transcript:
            st.subheader("📜 Searchable Subtitles")
            search_term = st.text_input("🔍 Filter keywords in subtitles:", placeholder="e.g., gradient descent")
            
            filtered = [
                s for s in st.session_state['segments'] 
                if not search_term or search_term.lower() in s['text'].lower()
            ]
            
            st.caption(f"Showing {len(filtered)} matching segments")
            for seg in filtered[:120]:
                st.markdown(f"**`{seg['timestamp']}`** : {seg['text']}")

    with right_col:
        st.subheader("📺 Video Player")
        st.video(f"https://www.youtube.com/watch?v={st.session_state['video_id']}")
