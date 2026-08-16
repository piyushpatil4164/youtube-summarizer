import re
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url: str) -> str | None:
    """Extracts the 11-character video ID from various YouTube URL formats."""
    if not url:
        return None

    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url.strip())
        if match:
            return match.group(1)
            
    return None


def format_timestamp(seconds: float) -> str:
    """Converts float seconds into human-readable HH:MM:SS or MM:SS format."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def get_transcript(video_id: str) -> tuple[str, list[dict]]:
    """
    Fetches the transcript for a given video ID across all library versions.
    """
    raw_data = None
    
    # Strategy 1: Modern Instance fetch
    try:
        raw_data = YouTubeTranscriptApi().fetch(video_id)
    except Exception:
        pass

    # Strategy 2: Instance get_transcript
    if raw_data is None:
        try:
            raw_data = YouTubeTranscriptApi().get_transcript(video_id)
        except Exception:
            pass

    # Strategy 3: Module direct fetch
    if raw_data is None:
        try:
            raw_data = youtube_transcript_api.YouTubeTranscriptApi.get_transcripts([video_id])[0][video_id]
        except Exception:
            pass

    # Strategy 4: Legacy Static Method
    if raw_data is None:
        try:
            raw_data = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            raise RuntimeError(f"Could not retrieve transcript: {str(e)}")

    if not raw_data:
        raise ValueError("No transcript or subtitles available for this video.")

    full_text_list = []
    structured_segments = []

    for item in raw_data:
        text = getattr(item, 'text', None) or (item.get('text') if isinstance(item, dict) else str(item))
        start = getattr(item, 'start', None) or (item.get('start', 0.0) if isinstance(item, dict) else 0.0)

        cleaned_line = str(text).replace('\n', ' ').strip()
        if cleaned_line:
            full_text_list.append(cleaned_line)
            structured_segments.append({
                "timestamp": format_timestamp(float(start)),
                "seconds": float(start),
                "text": cleaned_line
            })

    full_text = " ".join(full_text_list)
    return full_text, structured_segments
