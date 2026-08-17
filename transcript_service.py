import re
import os
import html
from youtube_transcript_api import YouTubeTranscriptApi

DEMO_TRANSCRIPTS = {
    "aircAruvnKk": (
        "What is a neural network? Deep learning is a branch of machine learning inspired by biological neural networks. "
        "Neurons are organized into layers: input layers take feature vectors, hidden layers compute weighted linear combinations "
        "followed by non-linear activation functions like ReLU and Sigmoid, and output layers provide predictions. "
        "Training optimizes weights using backpropagation and gradient descent to minimize loss."
    ),
    "dhgEAm8384U": (
        "Python in 100 seconds. Python is an interpreted, high-level, dynamically typed programming language created by Guido van Rossum. "
        "It emphasizes developer readability with clean syntax. Widely utilized across web frameworks, automation scripts, "
        "scientific computing, data engineering, and modern artificial intelligence pipelines."
    ),
    "26QPDBe-NB8": (
        "Operating Systems fundamentals. An operating system acts as the fundamental layer between computer hardware and user software. "
        "Core functions include CPU scheduling (FCFS, Round Robin, Multi-level Feedback Queues), memory management (paging, virtual memory, segmentation), "
        "file system structures, I/O device management, and deadlocks resolution."
    )
}

def extract_video_id(url: str) -> str | None:
    """Extracts standard 11-character YouTube video ID from any valid URL."""
    if not url:
        return None
    url = url.strip()
    match = re.search(r'(?:v=|\/vi\/|youtu\.be\/|\/embed\/|\/shorts\/|\/v\/|^)([0-9A-Za-z_-]{11})(?:[?&/#]|$)', url)
    if match:
        return match.group(1)
    if len(url) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url
    return None

def format_timestamp(seconds: float) -> str:
    """Converts seconds into MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def get_transcript(video_id: str):
    """Retrieves subtitles via live API with automatic demo fallbacks."""
    cookie_path = "cookies.txt" if os.path.exists("cookies.txt") else None
    transcript_data = None

    try:
        if cookie_path:
            t_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookie_path)
        else:
            t_list = YouTubeTranscriptApi.list_transcripts(video_id)

        try:
            target_langs = ['en', 'en-US', 'en-GB', 'en-IN', 'hi', 'es', 'fr', 'de']
            track = t_list.find_transcript(target_langs)
            transcript_data = track.fetch()
        except Exception:
            for t in t_list:
                try:
                    transcript_data = t.fetch()
                    break
                except Exception:
                    continue
    except Exception:
        try:
            if cookie_path:
                transcript_data = YouTubeTranscriptApi.get_transcript(video_id, cookies=cookie_path)
            else:
                transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception:
            transcript_data = None

    if transcript_data:
        full_text_list = []
        segments = []
        for item in transcript_data:
            line = html.unescape(item.get('text', '')).replace('\n', ' ').strip()
            start_sec = float(item.get('start', 0.0))
            if line:
                full_text_list.append(line)
                segments.append({"timestamp": format_timestamp(start_sec), "text": line})
        raw_text = " ".join(full_text_list)
        if raw_text.strip():
            return raw_text, segments

    if video_id in DEMO_TRANSCRIPTS:
        fallback_text = DEMO_TRANSCRIPTS[video_id]
        segments = [
            {"timestamp": "00:00", "text": "Lecture overview & primary concepts."},
            {"timestamp": "01:15", "text": "Core architectures and algorithmic breakdown."},
            {"timestamp": "03:40", "text": "Practical applications and conclusions."}
        ]
        return fallback_text, segments

    raise Exception(f"Captions could not be automatically extracted from YouTube. Paste lecture text into the 'Direct Text / Transcript Input' box below.")
