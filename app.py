import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from transcript_service import extract_video_id, get_transcript
from ai_service import generate_summary, generate_mindmap_code, generate_interactive_quiz
from pdf_service import create_pdf

load_dotenv()

st.set_page_config(
    page_title="PiFI Yt summarizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_secret(key_name: str) -> str:
    key = None
    try:
        if key_name in st.secrets:
            key = st.secrets[key_name]
    except Exception:
        pass
    if not key:
        key = os.getenv(key_name, "")
    return str(key).strip() if key else ""

active_api_key = get_secret("GROQ_API_KEY")
supadata_api_key = get_secret("SUPADATA_API_KEY")

# Session States
if "url_input_box" not in st.session_state:
    st.session_state["url_input_box"] = ""
if "quiz_data" not in st.session_state:
    st.session_state["quiz_data"] = None
if "user_answers" not in st.session_state:
    st.session_state["user_answers"] = {}
if "quiz_submitted" not in st.session_state:
    st.session_state["quiz_submitted"] = False
if "card_index" not in st.session_state:
    st.session_state["card_index"] = 0
if "show_card_back" not in st.session_state:
    st.session_state["show_card_back"] = False

def set_url(url: str):
    st.session_state["url_input_box"] = url

# Extreme Level Cyber-Glass Dark CSS
LUXURY_DARK_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Deep Cosmic Background */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #171938 0%, #090B13 60%, #05060A 100%) !important;
        color: #F8FAFC !important;
    }

    /* Sidebar Glassmorphism */
    section[data-testid="stSidebar"] {
        background: rgba(13, 17, 30, 0.75) !important;
        backdrop-filter: blur(18px) !important;
        -webkit-backdrop-filter: blur(18px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 10px 0 30px rgba(0, 0, 0, 0.5) !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Hero Banner with Animated Gradient Glow */
    .hero-card {
        background: linear-gradient(135deg, rgba(30, 37, 68, 0.6) 0%, rgba(15, 20, 39, 0.8) 100%) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(129, 140, 248, 0.25) !important;
        border-radius: 20px;
        padding: 3rem 2rem;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px -10px rgba(99, 102, 241, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }

    .hero-card::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 60%);
        pointer-events: none;
    }

    .neon-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(99, 102, 241, 0.15);
        color: #A5B4FC !important;
        border: 1px solid rgba(99, 102, 241, 0.4);
        padding: 0.4rem 1.1rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 1rem;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);
    }

    .hero-title {
        font-size: 3rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #FFFFFF 30%, #A5B4FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.4rem 0 0.8rem 0 !important;
        letter-spacing: -0.02em;
    }

    .hero-subtitle {
        color: #94A3B8 !important;
        font-size: 1.05rem !important;
        max-width: 620px;
        margin: 0 auto !important;
        line-height: 1.6;
    }

    /* Metric Display Cards */
    .metric-card {
        background: rgba(18, 23, 43, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(14px) !important;
        border-radius: 14px;
        padding: 1.3rem;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }

    .metric-card:hover {
        transform: translateY(-3px);
        border-color: rgba(129, 140, 248, 0.5) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.2);
    }

    .metric-val {
        font-size: 2rem !important;
        font-weight: 800 !important;
        color: #818CF8 !important;
        letter-spacing: -0.01em;
    }

    .metric-sub {
        color: #94A3B8 !important;
        font-size: 0.82rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.3rem;
    }

    /* Inputs, Selectors & Text Areas */
    div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
        background: rgba(15, 20, 36, 0.8) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="stTextInput"] input:focus, div[data-testid="stTextArea"] textarea:focus {
        border-color: #6366F1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.3) !important;
        background: rgba(20, 26, 48, 0.9) !important;
    }

    div[data-baseweb="select"] > div {
        background: rgba(15, 20, 36, 0.8) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
    }

    div[data-baseweb="select"] * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }

    ul[data-baseweb="menu"] {
        background: #0F1424 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }

    ul[data-baseweb="menu"] li:hover {
        background: #1E2544 !important;
    }

    /* Buttons */
    button[kind="primary"] {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.7rem 1.4rem !important;
        letter-spacing: 0.02em !important;
        box-shadow: 0 4px 18px rgba(99, 102, 241, 0.4) !important;
        transition: all 0.25s ease !important;
    }

    button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.6) !important;
        background: linear-gradient(135deg, #4F46E5 0%, #4338CA 100%) !important;
    }

    button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.04) !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: #818CF8 !important;
        color: #FFFFFF !important;
        transform: translateY(-2px) !important;
    }

    /* Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(15, 20, 36, 0.6);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        color: #94A3B8 !important;
        font-weight: 600;
        border: none !important;
    }

    .stTabs [aria-selected="true"] {
        background: #1E2544 !important;
        color: #818CF8 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }

    /* Video Frame */
    div[data-testid="stVideo"] {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    }
</style>
"""

st.markdown(LUXURY_DARK_CSS, unsafe_allow_html=True)

# Sidebar Controls
with st.sidebar:
    st.markdown("### 🛠️ Study Configuration")
    summary_mode = st.selectbox(
        "Format Architecture:",
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
        output_lang = st.selectbox("Target Lang:", ["English", "Hindi", "Hinglish", "Spanish", "French", "German"])

    st.markdown("---")
    st.caption("⚡ Powered by Groq LPU Ultra-Low Latency Inference.")
    st.caption("🔒 Secrets managed via Cloud Keystore.")

# Hero Header
st.markdown("""
<div class="hero-card">
    <div class="neon-badge">⚡ GROQ LPU ACCELERATED</div>
    <h1 class="hero-title">PiFI Yt summarizer</h1>
    <p class="hero-subtitle">Transform hours of complex video lectures into structured academic notes, visual concept maps, and interactive retention decks.</p>
</div>
""", unsafe_allow_html=True)

# Sample Lectures Row
col_lbl, c1, c2, c3 = st.columns([1.5, 2, 2, 2])
with col_lbl:
    st.markdown("<p style='margin-top:0.5rem; font-weight:600;'>Sample Lectures:</p>", unsafe_allow_html=True)
with c1:
    st.button("🧠 Neural Networks", use_container_width=True, on_click=set_url, args=("https://www.youtube.com/watch?v=aircAruvnKk",))
with c2:
    st.button("🐍 Python in 100s", use_container_width=True, on_click=set_url, args=("https://www.youtube.com/watch?v=dhgEAm8384U",))
with c3:
    st.button("🌐 Operating Systems", use_container_width=True, on_click=set_url, args=("https://www.youtube.com/watch?v=26QPDBe-NB8",))

# Main Input
url_input = st.text_input(
    "Paste YouTube URL:", 
    key="url_input_box",
    placeholder="https://www.youtube.com/watch?v=aircAruvnKk"
)

with st.expander("📋 Direct Text / Custom Lecture Ingestion (Optional)"):
    direct_transcript_text = st.text_area("Paste raw notes or transcript text:", height=130)

col_action, _ = st.columns([1.8, 4])
with col_action:
    generate_clicked = st.button("🚀 Synthesize Lecture", type="primary", use_container_width=True)

if generate_clicked:
    target_url = st.session_state.get("url_input_box", "").strip()
    direct_text = direct_transcript_text.strip() if direct_transcript_text else ""
    
    if not target_url and not direct_text:
        st.error("Please enter a valid YouTube URL or paste raw transcript text.")
    elif not active_api_key:
        st.error("GROQ_API_KEY is not configured. Add it inside your Streamlit Cloud Secrets.")
    else:
        raw_text = ""
        segments = []
        parsed_id = extract_video_id(target_url) if target_url else None
        
        try:
            if direct_text:
                raw_text = direct_text
                segments = [{"timestamp": "00:00", "text": p.strip()} for p in direct_text.split('\n') if p.strip()]
                parsed_id = "direct_text"
            else:
                if not parsed_id:
                    raise Exception("Could not detect a valid YouTube Video ID. Please verify the URL.")
                with st.spinner("Retrieving video transcript via AI Pipeline..."):
                    raw_text, segments = get_transcript(parsed_id, active_api_key, supadata_api_key)

            with st.spinner(f"Synthesizing {summary_mode} in {output_lang}..."):
                notes = generate_summary(raw_text, summary_mode, active_api_key, detail_level, output_lang)

            words_total = len(raw_text.split())
            words_sum = len(notes.split())
            mins_orig = max(1, round(words_total / 130))
            saved_est = max(1, round(mins_orig - (words_sum / 200)))

            st.session_state['summary'] = notes
            st.session_state['raw_text'] = raw_text
            st.session_state['video_id'] = parsed_id
            st.session_state['segments'] = segments
            st.session_state['total_words'] = words_total
            st.session_state['time_saved'] = saved_est
            st.session_state['selected_lang'] = output_lang
            st.session_state['mindmap'] = None
            st.session_state['quiz_data'] = None
            st.session_state['user_answers'] = {}
            st.session_state['quiz_submitted'] = False
            st.session_state['card_index'] = 0
            st.session_state['show_card_back'] = False

            st.success("Analysis complete!")
        except Exception as err:
            st.error(f"{str(err)}")

# Render Results
if 'summary' in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{st.session_state.get('total_words', 0):,}</div>
            <div class="metric-sub">Transcript Words</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">~{st.session_state.get('time_saved', 0)} min</div>
            <div class="metric-sub">Study Time Saved</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{len(st.session_state.get('segments', []))}</div>
            <div class="metric-sub">Subtitle Nodes</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        t_notes, t_quiz, t_mind, t_subs = st.tabs([
            "📝 AI Study Notes",
            "🎯 Quiz & Flashcards",
            "🗺️ Concept Mind Map", 
            "📜 Searchable Subtitles"
        ])

        with t_notes:
            st.markdown(st.session_state['summary'])
            st.markdown("---")
            d1, d2 = st.columns(2)
            with d1:
                st.download_button(
                    "📥 Export Markdown (.md)",
                    data=st.session_state['summary'],
                    file_name="lecture_notes.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with d2:
                try:
                    pdf_data = create_pdf(st.session_state['summary'])
                    st.download_button(
                        "📄 Export PDF Document",
                        data=pdf_data,
                        file_name="lecture_notes.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception:
                    st.caption("Standard ASCII encoding preview active for PDF export.")

        with t_quiz:
            st.subheader("🎯 Test Your Retention")
            if not st.session_state.get("quiz_data"):
                if st.button("⚡ Generate Practice Exam & Flashcards", use_container_width=True):
                    with st.spinner("Generating exam items via Groq AI..."):
                        cur_lang = st.session_state.get('selected_lang', 'English')
                        quiz_res = generate_interactive_quiz(st.session_state['raw_text'], active_api_key, cur_lang)
                        st.session_state["quiz_data"] = quiz_res
                        st.session_state["user_answers"] = {}
                        st.session_state["quiz_submitted"] = False
                        st.session_state["card_index"] = 0
                        st.session_state["show_card_back"] = False
                        st.rerun()

            payload = st.session_state.get("quiz_data")
            if payload and payload.get("quiz"):
                q_tab, f_tab = st.tabs(["📝 Multiple Choice Quiz", "🗂️ Flip Flashcards"])

                # MCQ Quiz
                with q_tab:
                    mcqs = payload.get("quiz", [])
                    total_q = len(mcqs)
                    for i, q in enumerate(mcqs):
                        st.markdown(f"**Q{i+1}: {q['question']}**")
                        ans = st.radio(
                            f"Options for Q{i+1}",
                            q["options"],
                            index=None if i not in st.session_state["user_answers"] else q["options"].index(st.session_state["user_answers"][i]),
                            key=f"mcq_radio_{i}",
                            label_visibility="collapsed",
                            disabled=st.session_state["quiz_submitted"]
                        )
                        if ans:
                            st.session_state["user_answers"][i] = ans

                        if st.session_state["quiz_submitted"]:
                            correct = q["options"][q["correct_index"]]
                            if st.session_state["user_answers"].get(i) == correct:
                                st.success(f"✅ Correct! — {q.get('explanation', '')}")
                            else:
                                st.error(f"❌ Incorrect. Correct Answer: **{correct}**\n\n*{q.get('explanation', '')}*")
                        st.markdown("<br>", unsafe_allow_html=True)

                    btn_c1, btn_c2 = st.columns([2, 2])
                    with btn_c1:
                        if not st.session_state["quiz_submitted"]:
                            if st.button("📊 Submit Quiz", type="primary", use_container_width=True):
                                st.session_state["quiz_submitted"] = True
                                st.rerun()
                        else:
                            if st.button("🔄 Retake Quiz", use_container_width=True):
                                st.session_state["user_answers"] = {}
                                st.session_state["quiz_submitted"] = False
                                st.rerun()

                    if st.session_state["quiz_submitted"]:
                        score = sum(1 for i, q in enumerate(mcqs) if st.session_state["user_answers"].get(i) == q["options"][q["correct_index"]])
                        pct = int((score / total_q) * 100)
                        st.markdown(f"""
                        <div class="metric-card" style="margin-top: 1rem;">
                            <div class="metric-val">{score} / {total_q} ({pct}%)</div>
                            <div class="metric-sub">Final Score</div>
                        </div>
                        """, unsafe_allow_html=True)

                # Flashcards
                with f_tab:
                    cards = payload.get("flashcards", [])
                    if cards:
                        ci = st.session_state["card_index"]
                        curr_c = cards[ci]
                        st.caption(f"Concept Card {ci + 1} of {len(cards)}")
                        
                        card_body = curr_c["back"] if st.session_state["show_card_back"] else curr_c["front"]
                        card_tag = "💡 EXPLANATION / DEFINITION" if st.session_state["show_card_back"] else "📌 CONCEPT / TERM"

                        st.markdown(f"""
                        <div style="background: rgba(30, 37, 68, 0.6); border: 2px solid #6366F1; border-radius: 16px; padding: 2.5rem; text-align: center; min-height: 180px; display: flex; flex-direction: column; justify-content: center;">
                            <div style="font-size: 0.75rem; font-weight: 700; color: #818CF8; margin-bottom: 0.5rem; letter-spacing: 0.05em;">{card_tag}</div>
                            <div style="font-size: 1.3rem; font-weight: 600; line-height: 1.5;">{card_body}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)

                        fc1, fc2, fc3 = st.columns([1, 2, 1])
                        with fc1:
                            if st.button("⬅️ Prev", disabled=(ci == 0), use_container_width=True):
                                st.session_state["card_index"] -= 1
                                st.session_state["show_card_back"] = False
                                st.rerun()
                        with fc2:
                            toggle_msg = "🔄 Reveal Term (Front)" if st.session_state["show_card_back"] else "🔄 Flip Card (Show Answer)"
                            if st.button(toggle_msg, use_container_width=True):
                                st.session_state["show_card_back"] = not st.session_state["show_card_back"]
                                st.rerun()
                        with fc3:
                            if st.button("Next ➡️", disabled=(ci == len(cards) - 1), use_container_width=True):
                                st.session_state["card_index"] += 1
                                st.session_state["show_card_back"] = False
                                st.rerun()

        with t_mind:
            st.subheader("🗺️ Hierarchical Mind Map")
            if st.button("Generate Visual Map"):
                with st.spinner("Synthesizing concept graph..."):
                    graph_code = generate_mindmap_code(st.session_state['raw_text'], active_api_key)
                    st.session_state['mindmap'] = graph_code

            if st.session_state.get('mindmap'):
                mermaid_embed = f"""
                <div class="mermaid" style="background-color: transparent;">
                    {st.session_state['mindmap']}
                </div>
                <script type="module">
                    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                    mermaid.initialize({{
                        startOnLoad: true,
                        theme: 'dark',
                        securityLevel: 'loose'
                    }});
                </script>
                """
                components.html(mermaid_embed, height=480, scrolling=True)

        with t_subs:
            st.subheader("📜 Searchable Subtitles")
            filter_query = st.text_input("🔍 Filter keywords:", placeholder="e.g., gradient, weights")
            filtered_subs = [
                s for s in st.session_state['segments'] 
                if not filter_query or filter_query.lower() in s['text'].lower()
            ]
            st.caption(f"Displaying {len(filtered_subs)} segments")
            for sub in filtered_subs[:120]:
                st.markdown(f"**`{sub['timestamp']}`** : {sub['text']}")

    with col_right:
        st.subheader("📺 Video Player")
        current_vid = st.session_state.get('video_id', '')
        if current_vid and current_vid != "direct_text" and len(current_vid) == 11:
            st.video(f"https://www.youtube.com/watch?v={current_vid}")
        else:
            st.markdown("""
            <div style="border: 2px dashed rgba(255, 255, 255, 0.15); border-radius: 14px; padding: 2.5rem 1rem; text-align: center;">
                <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">📝</div>
                <div style="font-weight: 700; font-size: 1.05rem;">Custom Transcript Active</div>
                <div style="font-size: 0.85rem; color: #94A3B8;">Study guides and visual maps generated from direct text ingestion.</div>
            </div>
            """, unsafe_allow_html=True)
