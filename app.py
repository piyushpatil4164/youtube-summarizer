import streamlit as st
import os
from dotenv import load_dotenv
from transcript_service import extract_video_id, get_transcript
from ai_service import generate_summary
from pdf_service import create_pdf

load_dotenv()
default_api_key = os.getenv("GROQ_API_KEY", "")

st.set_page_config(
    page_title="Lecture Digest - AI YouTube Summarizer",
    page_icon="🎓",
    layout="wide"
)

# Custom styling
st.markdown("""
    
""", unsafe_allow_html=True)

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input(
        "Groq API Key",
        type="password",
        value=default_api_key,
        help="Pre-filled from your .env file or enter manually."
    )
    
    st.divider()
    summary_mode = st.selectbox(
        "Select Study Style:",
        [
            "Detailed Study Notes",
            "Executive Summary",
            "Actionable Bullet Points",
            "Practice Quiz & Flashcards"
        ]
    )
    st.info("💡 **Tip:** 'Detailed Study Notes' creates an exam-ready breakdown with definitions and key questions.")

# Main Interface Header
st.title("🎓 AI YouTube Lecture Summarizer & Note Generator")
st.caption("Convert technical lectures and tutorials into structured study notes, cheat sheets, and revision sets.")

# Input Bar
url_input = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=aircAruvnKk")

col_btn, _ = st.columns([1, 3])
with col_btn:
    generate_clicked = st.button("🚀 Generate Notes", type="primary")

if generate_clicked:
    if not url_input.strip():
        st.error("Please enter a valid YouTube URL.")
    elif not api_key.strip():
        st.error("Groq API Key missing. Please provide a key in the sidebar or .env file.")
    else:
        video_id = extract_video_id(url_input)
        if not video_id:
            st.error("Invalid YouTube URL. Please enter a valid link.")
        else:
            try:
                with st.spinner("1/2: Extracting video transcript & timestamps..."):
                    raw_text, structured_segments = get_transcript(video_id)

                with st.spinner(f"2/2: Generating '{summary_mode}' with Llama 3.1..."):
                    summary_result = generate_summary(raw_text, summary_mode, api_key)

                # Store in session state
                st.session_state['summary'] = summary_result
                st.session_state['video_id'] = video_id
                st.session_state['structured_segments'] = structured_segments
                st.success("Study notes generated successfully!")

            except Exception as e:
                st.error(f"Error: {str(e)}")

# Display Output Section
if 'summary' in st.session_state:
    st.divider()
    left_col, right_col = st.columns([3, 2], gap="large")

    with left_col:
        st.subheader("📝 Generated Study Notes")
        st.markdown(st.session_state['summary'])

        st.divider()
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.download_button(
                label="📥 Download Markdown (.md)",
                data=st.session_state['summary'],
                file_name="lecture_notes.md",
                mime="text/markdown"
            )
        with d_col2:
            pdf_bytes = create_pdf(st.session_state['summary'])
            st.download_button(
                label="📄 Download PDF (.pdf)",
                data=pdf_bytes,
                file_name="lecture_notes.pdf",
                mime="application/pdf"
            )

    with right_col:
        st.subheader("📺 Video & Timeline")
        st.video(f"https://www.youtube.com/watch?v={st.session_state['video_id']}")

        with st.expander("🔍 View Timestamped Subtitles", expanded=False):
            for seg in st.session_state['structured_segments'][:100]:
                st.write(f"`{seg['timestamp']}` : {seg['text']}")