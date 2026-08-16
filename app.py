import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from transcript_service import extract_video_id, get_transcript
from ai_service import generate_summary, ask_video_question, generate_mindmap_code
from pdf_service import create_pdf

load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="LectureDigest AI — Smart Study Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Key Resolution
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

# Session State Initialization
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "Dark"
if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []

# Top Bar Theme Controls
col_title, col_toggle = st.columns([5, 1.5])
with col_toggle:
    theme_selection = st.radio(
        "Theme",
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

# Theme CSS Injector
if is_dark:
    theme_css = """
    <style>
        .stApp { background-color: #0B0F19 !important; color: #F1F5F9 !important; }
        section[data-testid="stSidebar"] { 
            background-color: #111827 !important; 
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important; 
        }
        header[data-testid="stHeader"] { background-color: transparent !important; }
        header[data-testid="stHeader"] * { color: #F1F5F9 !important; fill: #F1F5F9 !important; }
        
        h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown { color: #F1F5F9 !important; }
        
        .hero-container {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.18) 0%, rgba(168, 85, 247, 0.1) 100%) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 16px;
            padding: 2.2rem 2rem;
            text-align: center;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        .badge {
            background: rgba(99, 102, 241, 0.25) !important;
            color: #818CF8 !important;
            border: 1px solid rgba(99, 102, 241, 0.4) !important;
        }
        .metric-card {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 12px;
            padding: 1.2rem;
            text-align: center;
        }
        .metric-value { color: #818CF8 !important; font-size: 1.7rem; font-weight: 800; }
        .metric-label { color: #94A3B8 !important; font-size: 0.85rem; }
        
        /* Form Inputs & Selects */
        div[data-testid="stTextInput"] input {
            background-color: #1E293B !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
        }
        div[data-baseweb="select"] > div, div[data-baseweb="select"] ul {
            background-color: #1E293B !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
        }
        div[data-baseweb="select"] * {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }
        
        /* Buttons */
        button[kind="secondary"] {
            background-color: #1E293B !important;
            color: #F1F5F9 !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
        }
        button[kind="secondary"]:hover {
            background-color: #334155 !important;
            border-color: #818CF8 !important;
            color: #FFFFFF !important;
        }
        button[kind="primary"] {
            background: linear-gradient(90deg, #6366F1, #4F46E5) !important;
            color: #FFFFFF !important;
            border: none !important;
        }
    </style>
    """
else:
    theme_css = """
    <style>
        .stApp { background-color: #F8FAFC !important; color: #0F172A !important; }
        section[data-testid="stSidebar"] { 
            background-color: #FFFFFF !important; 
            border-right: 1px solid #E2E8F0 !important; 
        }
        
        /* Fix Streamlit Top-Right Header (Share, Star, Menu) */
        header[data-testid="stHeader"] { background-color: transparent !important; }
        header[data-testid="stHeader"] * { 
            color: #0F172A !important; 
            fill: #0F172A !important; 
            opacity: 0.9 !important;
        }
        div[data-testid="stToolbar"] * { 
            color: #0F172A !important; 
            fill: #0F172A !important; 
        }
        
        h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown { color: #0F172A !important; }
        
        .hero-container {
            background: linear-gradient(135deg, #EEF2FF 0%, #FAF5FF 100%) !important;
            border: 1px solid #C7D2FE !important;
            border-radius: 16px;
            padding: 2.2rem 2rem;
            text-align: center;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
        }
        .hero-container h1 { color: #1E1B4B !important; }
        .hero-container p { color: #475569 !important; }
        
        .badge {
            background: #E0E7FF !important;
            color: #4338CA !important;
            border: 1px solid #C7D2FE !important;
        }
        .metric-card {
            background: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px;
            padding: 1.2rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        }
        .metric-value { color: #4F46E5 !important; font-size: 1.7rem; font-weight: 800; }
        .metric-label { color: #64748B !important; font-size: 0.85rem; }
        
        /* Inputs & Sidebar Dropdowns */
        div[data-testid="stTextInput"] input {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
        }
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
        }
        div[data-baseweb="select"] * {
            color: #0F172A !important;
            fill: #0F172A !important;
        }
        ul[data-baseweb="menu"] {
            background-color: #FFFFFF !important;
        }
        ul[data-baseweb="menu"] li {
            color: #0F172A !important;
        }
        
        /* Buttons */
        button[kind="secondary"] {
            background-color: #FFFFFF !important;
            color: #1E293B !important;
            border: 1px solid #CBD5E1 !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
        }
        button[kind="secondary"]:hover {
            background-color: #F1F5F9 !important;
            border-color: #6366F1 !important;
            color: #4F46E5 !important;
        }
        button[kind="primary"] {
            background: linear-gradient(90deg, #4F46E5, #4338CA) !important;
            color: #FFFFFF !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25) !important;
        }
    </style>
    """

st.markdown(theme_css, unsafe_allow_html=True)

# Shared General Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .badge {
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 0.6rem;
    }
    .stButton>button {
        border-radius: 9px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
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
    st.caption("🔒 System secured via Cloud Secret Management.")

# Header Banner
st.markdown("""
<div class="hero-container">
    <div class="badge">⚡ Groq LPU Accelerated</div>
    <h1 style="margin: 0.2rem 0; font-weight: 800; font-size: 2.3rem;">AI YouTube Lecture Digest</h1>
    <p style="margin: 0; font-size: 0.95rem;">Convert video lectures into structured notes, mind maps, quizzes, and searchable subtitles.</p>
</div>
""", unsafe_allow_html=True)

# Quick Sample Links
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

# Video Input
input_val = st.session_state.get('url_input_val', '')
url_input = st.text_input("Enter YouTube Video URL:", value=input_val, placeholder="https://www.youtube.com/watch?v=aircAruvnKk")

col_btn, _ = st.columns([1.5, 4])
with col_btn:
    generate_clicked = st.button("🚀 Process & Generate", type="primary", use_container_width=True)

# Processing Logic
if generate_clicked:
    if not url_input.strip():
        st.error("Please enter a valid YouTube URL.")
    elif not active_api_key:
        st.error("GROQ_API_KEY is not configured in Streamlit Secrets. Please add your key under app Settings > Secrets.")
    else:
        video_id = extract_video_id(url_input)
        if not video_id:
            st.error("Invalid YouTube URL format.")
        else:
            try:
                with st.spinner("Extracting transcript and subtitles..."):
                    raw_text, segments = get_transcript(video_id)

                with st.spinner(f"Generating {summary_mode}..."):
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
                st.session_state['mindmap'] = None

                st.success("Study assets generated successfully!")
            except Exception as e:
                st.error(f"{str(e)}")

# Results Display
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
        tab_notes, tab_chat, tab_mindmap, tab_transcript = st.tabs([
            "📝 AI Notes", 
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
                pdf_bytes = create_pdf(st.session_state['summary'])
                st.download_button(
                    "📄 Download PDF (.pdf)",
                    data=pdf_bytes,
                    file_name="study_notes.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        with tab_chat:
            st.subheader("💬 Ask Doubts from this Lecture")
            user_q = st.text_input("Ask a question:", placeholder="e.g., Explain the algorithm mentioned in the beginning", key="chat_input_field")
            if st.button("Ask AI Assistant"):
                if user_q.strip():
                    with st.spinner("Searching video content..."):
                        ans = ask_video_question(st.session_state['raw_text'], user_q, active_api_key)
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

    with right_view:
        st.subheader("📺 Video Player")
        st.video(f"https://www.youtube.com/watch?v={st.session_state['video_id']}")
