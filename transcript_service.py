import re
import youtube_transcript_api

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
    Retrieves English subtitles/transcripts safely across different versions of youtube_transcript_api.
    """
    transcript_data = None
    api_target = getattr(youtube_transcript_api, 'YouTubeTranscriptApi', youtube_transcript_api)

    # Strategy 1: Direct get_transcript call
    if hasattr(api_target, 'get_transcript'):
        try:
            transcript_data = api_target.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
        except Exception:
            try:
                transcript_data = api_target.get_transcript(video_id)
            except Exception:
                transcript_data = None

    # Strategy 2: list_transcripts fallback
    if transcript_data is None and hasattr(api_target, 'list_transcripts'):
        try:
            t_list = api_target.list_transcripts(video_id)
            try:
                transcript_data = t_list.find_manually_created_transcript(['en']).fetch()
            except Exception:
                try:
                    transcript_data = t_list.find_generated_transcript(['en']).fetch()
                except Exception:
                    for t in t_list:
                        transcript_data = t.fetch()
                        break
        except Exception:
            transcript_data = None

    if not transcript_data:
        raise Exception("English subtitles or transcripts are not available for this video.")

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
