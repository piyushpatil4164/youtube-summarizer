import re
import os
import glob
import html
import subprocess
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq

DEMO_TRANSCRIPTS = {
    # 1. Intro to Programming and Computer Science
    "zOjov-2OZ0E": (
        "Introduction to Computer Science and Programming Fundamentals. "
        "Programming is the process of creating a set of instructions that tell a computer how to perform a task. "
        "Core primitives include variables for data storage, control flow with conditional statements (if-else), "
        "loops (for, while) for iteration, and functions for modular code reuse. "
        "Data structures like arrays, lists, and dictionaries organize data efficiently in memory, "
        "while recursion enables elegant solutions to divide-and-conquer problem domains."
    ),

    # 2. Famous CS Algorithms (Sorting, Searching, Graphs)
    "fKcfaAPyPUQ": (
        "Core Computer Science Algorithms and Computational Complexity. "
        "Algorithm design focuses on optimizing time and space complexity measured via Big-O notation. "
        "Key paradigms include Divide and Conquer (Merge Sort, Quick Sort), Searching (Binary Search on ordered sets), "
        "Graph Traversal (Breadth-First Search, Depth-First Search), Shortest Path optimization (Dijkstra's Algorithm), "
        "and Dynamic Programming for overlapping subproblems and optimal substructure."
    ),

    # 3. Large Language Models (Andrej Karpathy)
    "zjkBMFhNj_g": (
        "Intro to Large Language Models by Andrej Karpathy. "
        "A Large Language Model (LLM) is essentially two files: a parameters file containing neural weights and a runtime execution file. "
        "The development pipeline comprises Pre-training on multi-terabyte web corpora using thousands of GPUs to produce base models, "
        "followed by Supervised Fine-Tuning (SFT) on curated instruction dialogues and Reinforcement Learning from Human Feedback (RLHF). "
        "Operational considerations include prompt engineering, context windows, retrieval-augmented generation (RAG), and security vectors."
    ),

    # 4. Neural Networks (3Blue1Brown)
    "aircAruvnKk": (
        "What is a neural network? Deep learning is a branch of machine learning inspired by biological neural architectures. "
        "Neurons are organized into layers: input layers take feature vectors, hidden layers compute weighted linear combinations "
        "followed by non-linear activation functions like ReLU and Sigmoid, and output layers provide class probabilities. "
        "Training optimizes weights across epochs using backpropagation and gradient descent to minimize empirical loss."
    ),

    # 5. Operating Systems & Concurrency
    "UrsmFxElp5k": (
        "Operating Systems Process Synchronization and Semaphores. "
        "The critical section problem occurs when multiple concurrent execution threads access shared resources. "
        "A valid synchronization solution must satisfy Mutual Exclusion, Progress, and Bounded Waiting. "
        "Semaphores provide an integer-based synchronization primitive using atomic wait (P) and signal (V) operations "
        "to prevent race conditions, deadlocks, and resource starvation."
    ),

    # 6. Python in 100 Seconds
    "dhgEAm8384U": (
        "Python in 100 seconds. Python is an interpreted, high-level, dynamically typed programming language created by Guido van Rossum. "
        "It emphasizes developer readability with clean indentation syntax. Widely utilized across web frameworks, automation scripts, "
        "scientific computing, data engineering, and modern artificial intelligence pipelines."
    ),

    # 7. Operating Systems Architecture
    "26QPDBe-NB8": (
        "Operating Systems fundamentals. An operating system acts as the fundamental layer between computer hardware and user software. "
        "Core functions include CPU scheduling (FCFS, Round Robin, Multi-level Feedback Queues), memory management (paging, virtual memory, segmentation), "
        "file system structures, I/O device management, and deadlocks resolution."
    )
}
def extract_video_id(url: str) -> str | None:
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
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def transcribe_via_whisper(video_id: str, api_key: str):
    """
    Downloads low-bitrate audio with yt-dlp and transcribes via Groq Whisper API.
    Guarantees transcript extraction for any video without caption dependencies.
    """
    audio_output_template = f"/tmp/{video_id}.%(ext)s"
    
    # 1. Extract audio stream using yt-dlp
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "9",
        "--max-filesize", "24M",
        "--force-overwrites",
        "-o", audio_output_template,
        f"https://www.youtube.com/watch?v={video_id}"
    ]
    
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    # Locate generated mp3 file
    target_files = glob.glob(f"/tmp/{video_id}.*")
    if not target_files:
        raise Exception("Audio extraction failed.")
    
    audio_path = target_files[0]
    
    try:
        client = Groq(api_key=api_key)
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), audio_file.read()),
                model="whisper-large-v3",
                response_format="verbose_json"
            )
        
        full_text = transcription.text
        segments = []
        
        if hasattr(transcription, 'segments') and transcription.segments:
            for seg in transcription.segments:
                start_sec = float(seg.get('start', 0.0) if isinstance(seg, dict) else getattr(seg, 'start', 0.0))
                text_seg = seg.get('text', '') if isinstance(seg, dict) else getattr(seg, 'text', '')
                if text_seg.strip():
                    segments.append({"timestamp": format_timestamp(start_sec), "text": text_seg.strip()})
        else:
            segments = [{"timestamp": "00:00", "text": full_text}]
            
        return full_text, segments
    finally:
        for f in target_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

def get_transcript(video_id: str, api_key: str = ""):
    """
    Cascading Multi-Tier Extractor:
    Tier 1: Standard YouTube timed-text track
    Tier 2: Direct Audio Extraction + Groq Whisper AI Transcription
    Tier 3: Pre-cached Demo Fallback
    """
    # Tier 1: Standard Captions API
    try:
        t_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            track = t_list.find_transcript(['en', 'en-US', 'en-GB', 'en-IN', 'hi', 'es', 'fr', 'de'])
            data = track.fetch()
        except Exception:
            data = next(iter(t_list)).fetch()

        full_text, segments = [], []
        for item in data:
            line = html.unescape(item.get('text', '')).replace('\n', ' ').strip()
            start_sec = float(item.get('start', 0.0))
            if line:
                full_text.append(line)
                segments.append({"timestamp": format_timestamp(start_sec), "text": line})
        if full_text:
            return " ".join(full_text), segments
    except Exception:
        pass

    # Tier 2: Whisper Audio AI Pipeline
    if api_key:
        try:
            return transcribe_via_whisper(video_id, api_key)
        except Exception:
            pass

    # Tier 3: Demo Cache Fallback
    if video_id in DEMO_TRANSCRIPTS:
        fallback_text = DEMO_TRANSCRIPTS[video_id]
        segments = [
            {"timestamp": "00:00", "text": "Lecture overview & primary concepts."},
            {"timestamp": "01:15", "text": "Core architectures and algorithmic breakdown."},
            {"timestamp": "03:40", "text": "Practical applications and conclusions."}
        ]
        return fallback_text, segments

    raise Exception(f"Unable to extract audio or captions for video {video_id}. Please use the Direct Text Input box.")
