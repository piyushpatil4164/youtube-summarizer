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

def fetch_innertube_captions(video_id: str):
    """
    Directly queries YouTube's Innertube Player API with Android & Web clients.
    Bypasses cloud IP web blocking and consent walls.
    """
    player_url = "https://www.youtube.com/youtubei/v1/player"
    
    # Client 1: Android Client Context
    payload_android = {
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "19.09.37",
                "hl": "en"
            }
        },
        "videoId": video_id
    }
    
    captions = []
    try:
        data = json.dumps(payload_android).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11)"
        }
        req = urllib.request.Request(player_url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            captions = resp_data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    except Exception:
        pass

    # Client 2: Fallback to WEB Client Context
    if not captions:
        try:
            payload_web = {
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": "2.20240101.00.00",
                        "hl": "en"
                    }
                },
                "videoId": video_id
            }
            data_web = json.dumps(payload_web).encode('utf-8')
            headers_web = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            req_web = urllib.request.Request(player_url, data=data_web, headers=headers_web)
            with urllib.request.urlopen(req_web, timeout=10) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                captions = resp_data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
        except Exception:
            pass

    if not captions:
        raise Exception("No subtitle tracks found for this video in YouTube API.")

    # Select English track or fallback to first available
    base_url = None
    for track in captions:
        lang = track.get("languageCode", "").lower()
        if lang.startswith("en"):
            base_url = track.get("baseUrl")
            break
    if not base_url:
        base_url = captions[0].get("baseUrl")

    # Fetch timed text XML
    cap_req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(cap_req, timeout=10) as cap_resp:
        xml_content = cap_resp.read().decode('utf-8', errors='ignore')

    # Parse XML subtitle elements
    root = ET.fromstring(xml_content)
    segments = []
    full_text = []

    for text_elem in root.iter('text'):
        raw_val = text_elem.text
        if raw_val:
            cleaned = html.unescape(raw_val).replace('\n', ' ').strip()
            start_sec = float(text_elem.get('start', 0.0))
            if cleaned:
                full_text.append(cleaned)
                segments.append({
                    "timestamp": format_timestamp(start_sec),
                    "text": cleaned
                })

    if not full_text:
        raise Exception("Parsed subtitle file contained no text.")

    return " ".join(full_text), segments

def get_transcript(video_id: str):
    """
    Multi-tier transcript resolution:
    1. Primary: Direct Innertube API fetch (fast & reliable on cloud IPs)
    2. Fallback: youtube_transcript_api library
    """
    # Strategy 1: Direct YouTube Innertube API
    try:
        return fetch_innertube_captions(video_id)
    except Exception:
        pass

    # Strategy 2: youtube_transcript_api library fallback
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

    raise Exception("Closed captions/transcripts are disabled or unavailable for this video.")
