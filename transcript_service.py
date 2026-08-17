import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

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
    Fetches the subtitle transcript from YouTube.
    Returns full raw string and timestamped segments list.
    """
    try:
        # Fetch transcript using the official class method
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        
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

    except TranscriptsDisabled:
        raise Exception("Transcripts are disabled for this video by the creator.")
    except NoTranscriptFound:
        raise Exception("No English or auto-generated transcript found for this video.")
    except Exception as e:
        raise Exception(f"Could not retrieve transcript: {str(e)}")
