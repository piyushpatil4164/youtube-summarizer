import re
import json
import html
import urllib.request
import xml.etree.ElementTree as ET

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

def fetch_direct_captions(video_id: str):
    """Directly scrapes YouTube player metadata for captions without library dependencies."""
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(
        watch_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
    )
    
    with urllib.request.urlopen(req, timeout=12) as response:
        html_page = response.read().decode('utf-8', errors='ignore')

    match = re.search(r'"captionTracks":\s*(\[.*?\])', html_page)
    if not match:
        raise Exception("No caption tracks metadata found in YouTube response.")

    tracks = json.loads(match.group(1))
    if not tracks:
        raise Exception("Caption tracks list is empty.")

    # Select English or first available caption track
    target_url = None
    for track in tracks:
        lang = track.get("languageCode", "").lower()
        if lang.startswith("en"):
            target_url = track.get("baseUrl")
            break
    if not target_url:
        target_url = tracks[0].get("baseUrl")

    # Fetch subtitle XML
    cap_req = urllib.request.Request(
        target_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(cap_req, timeout=12) as cap_resp:
        xml_data = cap_resp.read().decode('utf-8', errors='ignore')

    root = ET.fromstring(xml_data)
    segments, full_text = [], []

    for elem in root.iter('text'):
        val = elem.text
        if val:
            cleaned = html.unescape(val).replace('\n', ' ').strip()
            start_sec = float(elem.get('start', 0.0))
            if cleaned:
                segments.append({
                    "timestamp": format_timestamp(start_sec),
                    "text": cleaned
                })
                full_text.append(cleaned)

    if not full_text:
        raise Exception("Subtitle track contained no readable lines.")

    return " ".join(full_text), segments

def get_transcript(video_id: str):
    """Multi-tiered transcript retriever."""
    # 1. Primary: Direct native fetcher
    try:
        return fetch_direct_captions(video_id)
    except Exception:
        pass

    # 2. Fallback: Safe library import
    try:
        import sys
        if 'youtube_transcript_api' in sys.modules:
            yta = sys.modules['youtube_transcript_api']
            api_cls = getattr(yta, 'YouTubeTranscriptApi', None)
            if api_cls and hasattr(api_cls, 'get_transcript'):
                data = api_cls.get_transcript(video_id)
                full_text = [html.unescape(i.get('text', '')).strip() for i in data if i.get('text')]
                segments = [{"timestamp": format_timestamp(i.get('start', 0.0)), "text": html.unescape(i.get('text', '')).strip()} for i in data if i.get('text')]
                return " ".join(full_text), segments
    except Exception:
        pass

    raise Exception(f"Closed captions or subtitles are unavailable for video ID: {video_id}. Please verify the video has English or auto-generated subtitles enabled.")
