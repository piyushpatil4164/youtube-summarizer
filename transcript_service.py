import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def extract_video_id(url: str) -> str | None:
    """Extracts standard 11-character YouTube video ID from any valid URL."""
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
    Fetches transcript for any video across all available languages
    (manual, auto-generated, or auto-translated).
    """
    transcript_data = None

    try:
        # Step 1: List all transcripts available for this video
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Step 2: Try preferred languages first, otherwise grab the first available track
        try:
            target_langs = ['en', 'en-US', 'en-GB', 'en-IN', 'hi', 'es', 'fr', 'de']
            transcript_obj = transcript_list.find_transcript(target_langs)
            transcript_data = transcript_obj.fetch()
        except Exception:
            # Fallback to the first available transcript regardless of language
            for t in transcript_list:
                try:
                    transcript_data = t.fetch()
                    break
                except Exception:
                    continue

    except Exception:
        # Step 3: Direct API fallback call
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        except TranscriptsDisabled:
            raise Exception("Subtitles/closed captions are disabled for this video by the creator.")
        except NoTranscriptFound:
            raise Exception("No transcript or closed captions found for this video.")
        except Exception as e:
            raise Exception(f"Could not retrieve transcript: {str(e)}")

    if not transcript_data:
        raise Exception("Could not fetch subtitles for this video. Please verify the video has closed captions enabled.")

    full_text_list = []
    segments = []

    for item in transcript_data:
        text = item.get('text', '').replace('\n', ' ').strip()
        start_sec = item.get('start', 0.0)

        if text:
            full_text_list.append(text)
            segments.append({
                "timestamp": format_timestamp(start_sec),
                "text": text
            })

    raw_text = " ".join(full_text_list)
    if not raw_text.strip():
        raise Exception("Retrieved transcript is empty.")

    return raw_text, segments
