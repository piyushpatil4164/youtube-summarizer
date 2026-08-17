import re
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url: str) -> str | None:
    """Extracts standard 11-character YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_timestamp(seconds: float) -> str:
    """Converts raw float seconds into MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def process_transcript_items(transcript_data):
    """Formats raw transcript items into full text and timestamped segments."""
    full_text_list = []
    segments = []

    for item in transcript_data:
        text = item.get('text', '').strip()
        start_time = item.get('start', 0.0)

        if text:
            # Clean up newlines within single subtitle blocks
            cleaned_line = text.replace('\n', ' ')
            full_text_list.append(cleaned_line)
            segments.append({
                "timestamp": format_timestamp(start_time),
                "text": cleaned_line
            })

    raw_text = " ".join(full_text_list)
    return raw_text, segments

def get_transcript(video_id: str):
    """
    Fetches transcript with multi-level fallbacks:
    1. Direct English list lookup (en, en-US, en-GB, en-CA, en-IN, en-AU)
    2. Auto-generated English tracks
    3. Auto-translates to English if original subtitles are in another language
    4. Direct fetch fallback
    """
    transcript_data = None

    # Strategy 1: Search via transcript list with English priority
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Look for English (manual or auto-generated)
        try:
            transcript_obj = transcript_list.find_transcript([
                'en', 'en-US', 'en-GB', 'en-CA', 'en-IN', 'en-AU'
            ])
            transcript_data = transcript_obj.fetch()
        except Exception:
            # If not in English, grab first available track and auto-translate to English
            try:
                first_track = next(iter(transcript_list))
                if first_track.is_translatable:
                    translated_track = first_track.translate('en')
                    transcript_data = translated_track.fetch()
                else:
                    transcript_data = first_track.fetch()
            except Exception:
                transcript_data = None
    except Exception:
        transcript_data = None

    # Strategy 2: Direct API fetch fallback
    if not transcript_data:
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception:
            transcript_data = None

    if not transcript_data:
        raise Exception("Subtitles/closed captions are disabled or unavailable for this video.")

    return process_transcript_items(transcript_data)
