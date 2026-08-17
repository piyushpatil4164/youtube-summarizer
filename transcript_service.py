import re
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url: str) -> str | None:
    """Extracts standard 11-character YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|\/|vi=)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/watch\?.*v=([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_timestamp(seconds: float) -> str:
    """Converts raw seconds into MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def get_transcript(video_id: str):
    """
    Robust transcript extractor with multi-tier fallbacks:
    1. Check all available transcripts via list_transcripts (manual & generated)
    2. Fallback to direct get_transcript calls across major language codes
    """
    transcript_data = None

    # Strategy 1: Iterate transcript list
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Priority order for preferred languages
        preferred_langs = ['en', 'en-US', 'en-GB', 'en-CA', 'en-IN', 'hi', 'es', 'fr', 'de']
        
        try:
            t = transcript_list.find_transcript(preferred_langs)
            transcript_data = t.fetch()
        except Exception:
            # Grab the first available track if preferred codes are not found
            for t in transcript_list:
                transcript_data = t.fetch()
                break
    except Exception:
        pass

    # Strategy 2: Direct API fetch without language constraints
    if not transcript_data:
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception:
            pass

    # Strategy 3: Direct API fetch with broad language array
    if not transcript_data:
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(
                video_id, 
                languages=['en', 'en-US', 'en-GB', 'hi', 'es', 'fr', 'de', 'ja', 'ko', 'pt', 'ru']
            )
        except Exception:
            pass

    if not transcript_data:
        raise Exception("Could not find subtitles or transcripts for this video. Please verify closed captions are available.")

    full_text_list = []
    segments = []

    for item in transcript_data:
        text = item.get('text', '').replace('\n', ' ').strip()
        start_time = item.get('start', 0.0)

        if text:
            full_text_list.append(text)
            segments.append({
                "timestamp": format_timestamp(start_time),
                "text": text
            })

    raw_text = " ".join(full_text_list)
    return raw_text, segments
