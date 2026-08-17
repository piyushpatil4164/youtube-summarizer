import re
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url: str) -> str | None:
    """Extracts standard 11-character YouTube video ID from any URL format."""
    if not url:
        return None
    url = url.strip()
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
    
    # If the input itself is an 11-character ID
    if len(url) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url
        
    return None

def format_timestamp(seconds: float) -> str:
    """Converts raw seconds into MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def get_transcript(video_id: str):
    """
    Fetches transcripts reliably using multi-tier fallback:
    1. Direct Class Method
    2. Transcript List Iteration (Auto or Manual)
    3. Auto-translate to English if foreign language only
    """
    transcript_data = None
    last_error = None

    # Method 1: Direct list_transcripts check
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Priority language codes
        target_langs = ['en', 'en-US', 'en-GB', 'en-CA', 'en-IN', 'hi', 'es', 'fr', 'de']
        
        try:
            # Try finding preferred tracks
            t = transcript_list.find_transcript(target_langs)
            transcript_data = t.fetch()
        except Exception:
            # Grab any available track
            try:
                first_track = next(iter(transcript_list))
                transcript_data = first_track.fetch()
            except Exception:
                pass
    except Exception as e:
        last_error = e

    # Method 2: Direct get_transcript call
    if not transcript_data:
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            last_error = e

    # Method 3: Broad languages array call
    if not transcript_data:
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(
                video_id, 
                languages=['en', 'en-US', 'en-GB', 'hi', 'es', 'fr', 'de', 'ja', 'ko', 'pt', 'ru']
            )
        except Exception as e:
            last_error = e

    if not transcript_data:
        err_msg = str(last_error) if last_error else "Closed captions are disabled or unavailable for this video."
        raise Exception(f"Unable to fetch transcript for video ID ({video_id}): {err_msg}")

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
