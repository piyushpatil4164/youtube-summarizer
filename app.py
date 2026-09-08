import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from transcript_service import extract_video_id, get_transcript
from ai_service import generate_summary, ask_video_question, generate_mindmap_code
from pdf_service import create_pdf

load_dotenv()

st.set_page_config(
    page_title="AI YouTube Lecture Digest",
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

if "url_input_box" not in st.session_state:
    st.session_state["url_input_box"] = ""
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

def set_url(url: str):
    st.session_state["url_input_box"] = url

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

st.title("⚡ AI YouTube Lecture Digest")
st.caption("Convert video lectures into structured notes, mind maps, and searchable subtitles.")

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
                with st.spinner("Transcribing lecture and subtitles via Groq AI..."):
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
            st.session_state['chat_history'] = []
            st.session_state['mindmap'] = None

            st.success("Study assets generated successfully!")
        except Exception as e:
            st.error(f"{str(e)}")

if 'summary' in st.session_state:
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Words Transcribed", f"{st.session_state.get('total_words', 0):,}")
    m2.metric("Estimated Time Saved", f"~{st.session_state.get('time_saved', 0)} mins")
    m3.metric("Subtitle Blocks", len(st.session_state.get('segments', [])))

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

        with tab_chat:
            st.subheader("💬 Ask Questions About the Lecture")
            for msg in st.session_state['chat_history']:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if user_q := st.chat_input("Ask a doubt about this lecture..."):
                st.session_state['chat_history'].append({"role": "user", "content": user_q})
                with st.chat_message("user"):
                    st.markdown(user_q)

                with st.chat_message("assistant"):
                    with st.spinner("Consulting lecture transcript..."):
                        ans = ask_video_question(st.session_state['raw_text'], user_q, st.session_state['chat_history'], active_api_key)
                        st.markdown(ans)
                        st.session_state['chat_history'].append({"role": "assistant", "content": ans})

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
                    mermaid.initialize({{
                        startOnLoad: true,
                        securityLevel: 'loose'
                    }});
                </script>
                """
                components.html(mermaid_html, height=480, scrolling=True)

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
