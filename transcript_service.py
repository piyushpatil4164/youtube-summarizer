import re
import json
import html
import urllib.request
import xml.etree.ElementTree as ET

def extract_video_id(url: str) -> str | None:
    """Extracts standard 11-character YouTube video ID from various URL formats."""
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
    """Converts raw seconds into MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def fetch_direct_timedtext(video_id: str):
    """
    Extracts captions directly from YouTube's watch page ytInitialPlayerResponse.
    Bypasses cloud IP blocking without external library dependencies.
    """
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(
        watch_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
    )
    
    with urllib.request.urlopen(req, timeout=12) as response:
        html_content = response.read().decode('utf-8', errors='ignore')

    # Look for captionTracks JSON in player response
    match = re.search(r'"captionTracks":\s*(\[.*?\])', html_content)
    if not match:
        raise Exception("No caption tracks metadata found in YouTube response.")

    caption_tracks = json.loads(match.group(1))
    if not caption_tracks:
        raise Exception("Caption tracks list is empty.")

    # Find English track or fallback to the first track
    target_url = None
    for track in caption_tracks:
        if track.get("languageCode", "").startswith("en"):
            target_url = track.get("baseUrl")
            break
    if not target_url:
        target_url = caption_tracks[0].get("baseUrl")

    # Fetch subtitle XML
    cap_req = urllib.request.Request(
        target_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    )
    with urllib.request.urlopen(cap_req, timeout=12) as cap_resp:
        xml_data = cap_resp.read().decode('utf-8', errors='ignore')

    root = ET.fromstring(xml_data)
    segments = []
    full_text = []

    for elem in root.iter('text'):
        val = elem.text
        if val:
            cleaned = html.unescape(val).replace('\n', ' ').strip()
            start_sec = float(elem.get('start', 0.0))
            if cleaned:
                full_text.append(cleaned)
                segments.append({
                    "timestamp": format_timestamp(start_sec),
                    "text": cleaned
                })

    if not full_text:
        raise Exception("Subtitle XML contained no readable text lines.")

    return " ".join(full_text), segments

def get_transcript(video_id: str):
    """
    Multi-tier transcript extractor:
    1. Direct native timed-text parser
    2. Fallback to youtube_transcript_api package
    """
    # Tier 1: Native direct scraper
    try:
        return fetch_direct_timedtext(video_id)
    except Exception:
        pass

    # Tier 2: youtube_transcript_api fallback
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        
        full_text = []
        segments = []
        for item in transcript_data:
            text = html.unescape(item.get('text', '')).replace('\n', ' ').strip()
            start_sec = item.get('start', 0.0)
            if text:
                full_text.append(text)
                segments.append({
                    "timestamp": format_timestamp(start_sec),
                    "text": text
                })
        if full_text:
            return " ".join(full_text), segments
    except Exception:
        pass

    raise Exception(f"Closed captions or subtitles are unavailable for video ID: {video_id}. Please ensure the video has English or auto-generated subtitles.")
