import streamlit as st
from config import get_groq_api_key
from transcript_service import extract_video_id, get_transcript
from ai_service import generate_summary
from pdf_service import create_pdf

# Page Configuration
st.set_page_config(
    page_title="LectureDigest AI — Smart Video Notes",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Adaptive Theme & Privacy-Friendly CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .hero-container {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(168, 85, 247, 0.08) 100%);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 2.2rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.8rem;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    
    .badge {
        background: rgba(99, 102, 241, 0.15);
        color: #6366F1;
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
        font-size: 2.3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    
    .hero-desc {
        opacity: 0.85;
        font-size: 1.05rem;
        max-width: 650px;
        margin: 0 auto;
    }
    
    .metric-card {
        background: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
    }
    
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #6366F1;
    }
    
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.8;
        margin-top: 0.25rem;
    }
    
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar (Only UI preferences - Zero secrets or key fields)
with st.sidebar:
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
    st.markdown("---")
    st.caption("🔒 System secured via Cloud Secret Management.")

# Hero Header
st.markdown("""
<div class="hero-container">
    <div class="badge">⚡ Groq LPU Accelerated</div>
    <div class="hero-title">AI YouTube Lecture Digest</div>
    <div class="hero-desc">Convert technical lectures and tutorials into exam-ready notes, cheat sheets, and practice sets.</div>
</div>
""", unsafe_allow_html=True)

# Quick Select Samples
col_ex_label, col_ex1, col_ex2, col_ex3 = st.columns([1.5, 2, 2, 2])
with col_ex_label:
    st.markdown("**Try a sample video:**")
with col_ex1:
    if st.button("🧠 Neural Networks (3B1B)", use_container_width=True):
        st.session_state['url_input_val'] = "https://www.youtube.com/watch?v=aircAruvnKk"
with col_ex2:
    if st.button("🐍 Python in 100s", use_container_width=True):
        st.session_state['url_input_val'] = "https://www.youtube.com/watch?v=dhgEAm8384U"
with col_ex3:
    if st.button("🌐 Operating Systems", use_container_width=True):
        st.session_state['url_input_val'] = "https://www.youtube.com/watch?v=26QPDBe-NB8"

# URL Input
input_default = st.session_state.get('url_input_val', '')
url_input = st.text_input(
    "Paste YouTube URL:",
    value=input_default,
    placeholder="e.g. https://www.youtube.com/watch?v=aircAruvnKk"
)

# Process Action
col_btn, _ = st.columns([1, 4])
with col_btn:
    generate_clicked = st.button("⚡ Generate Notes", type="primary", use_container_width=True)

if generate_clicked:
    if not url_input.strip():
        st.error("Please enter a valid YouTube URL.")
    else:
        video_id = extract_video_id(url_input)
        if not video_id:
            st.error("Invalid YouTube URL format.")
        else:
            try:
                # Retrieve secure backend key
                api_key = get_groq_api_key()

                with st.spinner("1/2: Extracting video transcript..."):
                    raw_text, segments = get_transcript(video_id)

                with st.spinner(f"2/2: Generating {summary_mode}..."):
                    notes = generate_summary(raw_text, summary_mode, api_key)

                # Word & Time Calculations
                total_words = len(raw_text.split())
                summary_words = len(notes.split())
                reading_time_mins = max(1, round(total_words / 130))
                time_saved_mins = max(1, round(reading_time_mins - (summary_words / 200)))

                st.session_state['summary'] = notes
                st.session_state['video_id'] = video_id
                st.session_state['segments'] = segments
                st.session_state['total_words'] = total_words
                st.session_state['time_saved'] = time_saved_mins

                st.success("Notes generated successfully!")

            except ValueError as ve:
                st.error(str(ve))
            except Exception as e:
                # Mask internal file system and stack traces
                clean_error = str(e).split("\n")[0]
                st.error(f"Processing failed: {clean_error}")

# Display Output
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
            <div class="metric-label">Timestamped Blocks</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    left_view, right_view = st.columns([3, 2], gap="large")

    with left_view:
        tab_notes, tab_transcript = st.tabs(["📝 AI Generated Notes", "📜 Full Transcript"])

        with tab_notes:
            st.markdown(st.session_state['summary'])
            st.markdown("---")
            
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
