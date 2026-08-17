import re
import json
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from youtube_transcript_api import YouTubeTranscriptApi

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

def fetch_via_player_api(video_id: str):
    """Fetches captions using Innertube Android Client payload."""
    url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "19.09.37",
                "hl": "en"
            }
        },
        "videoId": video_id
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11)"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    tracks = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    if not tracks:
        raise Exception("No tracks available via Innertube API.")

    base_url = next((t["baseUrl"] for t in tracks if t.get("languageCode", "").startswith("en")), tracks[0]["baseUrl"])
    
    cap_req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(cap_req, timeout=10) as cap_resp:
        xml_data = cap_resp.read().decode('utf-8', errors='ignore')

    root = ET.fromstring(xml_data)
    segments, full_text = [], []
    for elem in root.iter('text'):
        if elem.text:
            text = html.unescape(elem.text).replace('\n', ' ').strip()
            start_sec = float(elem.get('start', 0.0))
            if text:
                segments.append({"timestamp": format_timestamp(start_sec), "text": text})
                full_text.append(text)

    if not full_text:
        raise Exception("Parsed empty XML caption content.")
    return " ".join(full_text), segments

def get_transcript(video_id: str):
    """Multi-tiered transcript retrieval."""
    # Strategy 1: YouTubeTranscriptApi List search
    try:
        t_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            t = t_list.find_transcript(['en', 'en-US', 'en-GB', 'en-IN', 'hi', 'es', 'fr', 'de'])
            data = t.fetch()
        except Exception:
            data = next(iter(t_list)).fetch()

        full_text, segments = [], []
        for item in data:
            t_str = html.unescape(item.get('text', '')).replace('\n', ' ').strip()
            s_sec = item.get('start', 0.0)
            if t_str:
                full_text.append(t_str)
                segments.append({"timestamp": format_timestamp(s_sec), "text": t_str})
        if full_text:
            return " ".join(full_text), segments
    except Exception:
        pass

    # Strategy 2: Direct Innertube player endpoint
    try:
        return fetch_via_player_api(video_id)
    except Exception:
        pass

    # Strategy 3: Direct API fallback
    try:
        data = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = [html.unescape(i['text']).replace('\n', ' ').strip() for i in data if i.get('text')]
        segments = [{"timestamp": format_timestamp(i['start']), "text": html.unescape(i['text']).replace('\n', ' ').strip()} for i in data if i.get('text')]
        if full_text:
            return " ".join(full_text), segments
    except Exception:
        pass

    raise Exception(f"YouTube blocked or could not find captions for ID ({video_id}). Use the 'Paste Transcript Manually' box below.")
