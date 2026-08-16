import streamlit as st
import os
from dotenv import load_dotenv
from transcript_service import extract_video_id, get_transcript
from ai_service import generate_summary
from pdf_service import create_pdf

load_dotenv()

# Resolve API Key
default_api_key = ""
if "GROQ_API_KEY" in st.secrets:
    default_api_key = st.secrets["GROQ_API_KEY"]
else:
    default_api_key = os.getenv("GROQ_API_KEY", "")

# Page Configuration
st.set_page_config(
    page_title="LectureDigest AI — Smart Video Notes",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling (Dark Modern SaaS Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .hero-container {
        background: linear-gradient(135deg, #1E1E2F 0%, #0F0F1A 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    
    .badge {
        background: rgba(99, 102, 241, 0.2);
        color: #818CF8;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 0.75rem;
        border: 1px solid rgba(99, 102, 241, 0.3);
    }
    
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FFFFFF, #CBD5E1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .hero-desc {
        color: #94A3B8;
        font-size: 1.05rem;
        max-width: 650px;
        margin: 0 auto;
    }
    
    .metric-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
    }
    
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #38BDF8;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94A3B8;
        margin-top: 0.25rem;
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #6366F1, #4F46E5);
        color: white;
        border: none;
        padding: 0.65rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6);
        background: linear-gradient(90deg, #4F46E5, #4338CA);
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown("### ⚙️ Settings & Control")
    user_custom_key = st.text_input(
        "Groq API Key (Optional)",
        type="password",
        value=default_api_key,
        help="Pre-configured on cloud. Enter custom key only if using your personal quota."
    )
    active_api_key = user_custom_key.strip() if user_custom_key.strip() else default_api_key

    st.markdown("---")
    st.markdown("### 🎓 Output Format")
    summary_mode = st.radio(
        "Select Note Style:",
        [
            "Detailed Study Notes",
            "Executive Summary",
            "Actionable Bullet Points",
            "Practice Quiz & Flashcards"
        ],
        index=0
    )

# Hero Header Banner
st.markdown("""
<div class="hero-container">
    <div class="badge">⚡ Groq LPU Powered</div>
    <div class="hero-title">AI YouTube Lecture Digest</div>
    <div class="hero-desc">Turn lengthy video lectures and tutorials into structured, exam-ready study notes and interactive quizzes in seconds.</div>
</div>
""", unsafe_allow_html=True)

# Example Video Quick-Select Pills
col_ex_label, col_ex1, col_ex2, col_ex3 = st.columns([1.5, 2, 2, 2])
with col_ex_label:
    st.markdown("**Try a sample video:**")
with col_ex1:
    if st.button("🧠 Neural Networks (3B1B)"):
        st.session_state['url_input_val'] = "https://www.youtube.com/watch?v=aircAruvnKk"
with col_ex2:
    if st.button("🐍 Python in 100 Seconds"):
        st.session_state['url_input_val'] = "https://www.youtube.com/watch?v=dhgEAm8384U"
with col_ex3:
    if st.button("🌐 Operating Systems"):
        st.session_state['url_input_val'] = "https://www.youtube.com/watch?v=26QPDBe-NB8"

# URL Input Field
input_default = st.session_state.get('url_input_val', '')
url_input = st.text_input(
    "Paste YouTube URL:",
    value=input_default,
    placeholder="e.g. https://www.youtube.com/watch?v=aircAruvnKk"
)

# Execution Action Button
col_btn, _ = st.columns([1, 4])
with col_btn:
    generate_clicked = st.button("⚡ Generate Notes", type="primary", use_container_width=True)

# Processing Logic
if generate_clicked:
    if not url_input.strip():
        st.error("Please enter a valid YouTube URL.")
    elif not active_api_key:
        st.error("Missing Groq API Key. Please add it to your Streamlit secrets or sidebar.")
    else:
        video_id = extract_video_id(url_input)
        if not video_id:
            st.error("Invalid YouTube link format. Please check the URL.")
        else:
            try:
                with st.spinner("Extracting transcript and timestamps..."):
                    raw_text, segments = get_transcript(video_id)

                with st.spinner(f"Synthesizing '{summary_mode}' via Llama 3.1..."):
                    notes = generate_summary(raw_text, summary_mode, active_api_key)

                # Metrics Calculation
                total_words = len(raw_text.split())
                summary_words = len(notes.split())
                reading_time_mins = max(1, round(total_words / 130)) # Avg speaking rate ~130 wpm
                time_saved_mins = max(1, round(reading_time_mins - (summary_words / 200)))

                st.session_state['summary'] = notes
                st.session_state['video_id'] = video_id
                st.session_state['segments'] = segments
                st.session_state['total_words'] = total_words
                st.session_state['time_saved'] = time_saved_mins

                st.success("Notes generated successfully!")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Display Output Dashboard
if 'summary' in st.session_state:
    st.markdown("---")

    # Metrics Highlights Bar
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
            <div class="metric-label">Timestamped Blocks</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main Split View
    left_view, right_view = st.columns([3, 2], gap="large")

    with left_view:
        tab_notes, tab_transcript = st.tabs(["📝 AI Generated Notes", "📜 Full Transcript"])

        with tab_notes:
            st.markdown(st.session_state['summary'])
            st.markdown("---")
            
            # Export Buttons
            exp1, exp2 = st.columns(2)
            with exp1:
                st.download_button(
                    label="📥 Download Markdown (.md)",
                    data=st.session_state['summary'],
                    file_name="lecture_notes.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with exp2:
                pdf_data = create_pdf(st.session_state['summary'])
                st.download_button(
                    label="📄 Download PDF (.pdf)",
                    data=pdf_data,
                    file_name="lecture_notes.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        with tab_transcript:
            for seg in st.session_state['segments']:
                st.markdown(f"**`{seg['timestamp']}`** : {seg['text']}")

    with right_view:
        st.subheader("📺 Video Player")
        st.video(f"https://www.youtube.com/watch?v={st.session_state['video_id']}")
