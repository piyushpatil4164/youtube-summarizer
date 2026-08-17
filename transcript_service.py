import re
import json
import urllib.request
import xml.etree.ElementTree as ET

def extract_video_id(url: str) -> str | None:
    """Extracts the 11-character YouTube video ID from various URL formats."""
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
            
    if len(url) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url
        
    return None

def format_timestamp(seconds: float) -> str:
    """Converts seconds into MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def fetch_direct_youtube_captions(video_id: str):
    """
    Direct standalone subtitle fetcher using YouTube's timed-text endpoint.
    Zero dependency on external library class structures.
    """
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    req = urllib.request.Request(watch_url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    # Extract captionTracks JSON from page metadata
    match = re.search(r'"captionTracks":\s*(\[.*?\])', html)
    if not match:
        raise Exception("No subtitle tracks found in video player data.")

    caption_tracks = json.loads(match.group(1))
    if not caption_tracks:
        raise Exception("Subtitle track list is empty.")

    # Select English or first available language track
    selected_url = None
    for track in caption_tracks:
        if track.get("languageCode", "").startswith("en"):
            selected_url = track.get("baseUrl")
            break
    if not selected_url:
        selected_url = caption_tracks[0].get("baseUrl")

    # Fetch JSON3 format captions
    captions_req = urllib.request.Request(selected_url + "&fmt=json3", headers=headers)
    with urllib.request.urlopen(captions_req, timeout=12) as resp:
        caption_json = json.loads(resp.read().decode('utf-8', errors='ignore'))

    events = caption_json.get("events", [])
    segments = []
    full_text = []

    for event in events:
        segs = event.get("segs", [])
        text = "".join([s.get("utf8", "") for s in segs]).replace('\n', ' ').strip()
        if text:
            start_ms = event.get("tStartMs", 0)
            start_sec = start_ms / 1000.0
            segments.append({
                "timestamp": format_timestamp(start_sec),
                "text": text
            })
            full_text.append(text)

    if not full_text:
        raise Exception("Parsed caption track contained no text.")

    return " ".join(full_text), segments

def get_transcript(video_id: str):
    """
    Multi-tier transcript extractor:
    1. Direct native YouTube captions scraper (fastest & most reliable)
    2. Fallback to youtube_transcript_api package if available
    """
    # 1. Primary: Direct native player captions fetch
    try:
        return fetch_direct_youtube_captions(video_id)
    except Exception:
        pass

    # 2. Secondary: youtube_transcript_api fallback
    try:
        import youtube_transcript_api
        api = getattr(youtube_transcript_api, 'YouTubeTranscriptApi', youtube_transcript_api)
        
        transcript_data = None
        if hasattr(api, 'get_transcript'):
            transcript_data = api.get_transcript(video_id)
        elif hasattr(api, 'list_transcripts'):
            t_list = api.list_transcripts(video_id)
            for t in t_list:
                transcript_data = t.fetch()
                break

        if transcript_data:
            full_text = []
            segments = []
            for item in transcript_data:
                text = item.get('text', '').replace('\n', ' ').strip()
                start_time = item.get('start', 0.0)
                if text:
                    full_text.append(text)
                    segments.append({
                        "timestamp": format_timestamp(start_time),
                        "text": text
                    })
            return " ".join(full_text), segments
    except Exception:
        pass

    raise Exception("Closed captions/transcripts are disabled or unavailable for this video.")
