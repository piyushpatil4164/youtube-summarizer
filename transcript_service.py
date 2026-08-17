import re
import html
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def extract_video_id(url: str) -> str | None:
    """Extracts standard 11-character YouTube video ID from any valid YouTube URL."""
    if not url:
        return None
    url = url.strip()
    patterns = [
        r'(?:v=|\/|vi=)([0-9A-Za-z_-]{11})(?:\?|&|$|\/)',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/watch\?.*v=([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
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
    """
    Robust multi-strategy transcript retriever:
    1. Look up transcript list and find manual or generated English tracks.
    2. Fallback to any language track and auto-translate to English.
    3. Direct fetch as last resort.
    """
    transcript_data = None
    fetch_error = None

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Priority 1: Preferred English and common variants
        try:
            target_langs = ['en', 'en-US', 'en-GB', 'en-CA', 'en-IN', 'hi', 'es', 'fr', 'de']
            t = transcript_list.find_transcript(target_langs)
            transcript_data = t.fetch()
        except Exception:
            pass

        # Priority 2: If foreign language only, translate to English
        if not transcript_data:
            try:
                first_track = next(iter(transcript_list))
                if first_track.is_translatable:
                    transcript_data = first_track.translate('en').fetch()
                else:
                    transcript_data = first_track.fetch()
            except Exception:
                pass

    except Exception as e:
        fetch_error = e

    # Priority 3: Direct API call
    if not transcript_data:
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            fetch_error = e

    if not transcript_data:
        raise Exception(f"Closed captions or subtitles are unavailable for this video (ID: {video_id}). Please check that the video has CC enabled on YouTube.")

    full_text_list = []
    segments = []

    for item in transcript_data:
        raw_t = item.get('text', '')
        if raw_t:
            clean_t = html.unescape(raw_t).replace('\n', ' ').strip()
            start_sec = float(item.get('start', 0.0))
            if clean_t:
                full_text_list.append(clean_t)
                segments.append({
                    "timestamp": format_timestamp(start_sec),
                    "text": clean_t
                })

    raw_text = " ".join(full_text_list)
    if not raw_text.strip():
        raise Exception("The extracted subtitle track contains no readable text.")

    return raw_text, segments
