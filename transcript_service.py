import re
import youtube_transcript_api
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

def get_transcript(video_id: str):
    """
    Safely retrieves subtitles/transcripts using multiple fallback strategies.
    Returns: raw_text (str), segments (list)
    """
    transcript_data = None

    # Strategy 1: Direct Class Call
    try:
        if hasattr(YouTubeTranscriptApi, 'get_transcript'):
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception:
        transcript_data = None

    # Strategy 2: Instance Call
    if not transcript_data:
        try:
            api_instance = YouTubeTranscriptApi()
            if hasattr(api_instance, 'get_transcript'):
                transcript_data = api_instance.get_transcript(video_id)
        except Exception:
            transcript_data = None

    # Strategy 3: Transcript List Finder (Supports Auto-Generated and Multilingual)
    if not transcript_data:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Try manually created transcript first, fallback to generated
            try:
                transcript_obj = transcript_list.find_manually_created_transcript(['en', 'hi', 'es', 'fr', 'de'])
            except Exception:
                transcript_obj = transcript_list.find_generated_transcript(['en', 'hi', 'es', 'fr', 'de'])
            
            transcript_data = transcript_obj.fetch()
        except Exception:
            # Last attempt: grab the first available transcript in any language
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                for t in transcript_list:
                    transcript_data = t.fetch()
                    break
            except Exception as final_err:
                raise Exception(f"Subtitles are unavailable or disabled for this video: {str(final_err)}")

    if not transcript_data:
        raise Exception("Could not fetch subtitles for this video. Please ensure the video has closed captions/subtitles enabled.")

    # Process and build segments
    full_text_list = []
    segments = []

    for item in transcript_data:
        text = item.get('text', '').strip()
        start_time = item.get('start', 0.0)

        if text:
            full_text_list.append(text)
            segments.append({
                "timestamp": format_timestamp(start_time),
                "text": text
            })

    raw_text = " ".join(full_text_list)
    return raw_text, segments
