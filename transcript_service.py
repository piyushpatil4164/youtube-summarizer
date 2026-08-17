import re
import json
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

def extract_video_id(url: str) -> str | None:
    """Extracts standard 11-character YouTube video ID from any valid YouTube URL format."""
    if not url:
        return None
    url = url.strip()
    
    # Handle youtu.be, standard watch, embed, shorts, and query params
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
    """Converts raw float seconds into MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def fetch_via_innertube(video_id: str):
    """Tier 1: Queries YouTube Android Innertube API (bypasses bot restrictions on cloud IPs)."""
    player_url = "https://www.youtube.com/youtubei/v1/player"
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
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        player_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11)"
        }
    )
    
    with urllib.request.urlopen(req, timeout=10) as resp:
        res_data = json.loads(resp.read().decode('utf-8'))
        
    caption_tracks = res_data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    if not caption_tracks:
        raise Exception("No caption tracks in Innertube payload.")
        
    # Find English track or take first available
    base_url = None
    for track in caption_tracks:
        if track.get("languageCode", "").startswith("en"):
            base_url = track.get("baseUrl")
            break
    if not base_url:
        base_url = caption_tracks[0].get("baseUrl")

    # Fetch timed text XML
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
        raise Exception("Innertube XML track had no readable text.")
    return " ".join(full_text), segments

def fetch_via_web_player(video_id: str):
    """Tier 2: Direct timedtext endpoint extraction from web player HTML."""
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(
        watch_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        html_page = resp.read().decode('utf-8', errors='ignore')

    match = re.search(r'"captionTracks":\s*(\[.*?\])', html_page)
    if not match:
        raise Exception("No web player caption tracks found.")

    tracks = json.loads(match.group(1))
    target_url = next((t["baseUrl"] for t in tracks if t.get("languageCode", "").startswith("en")), tracks[0]["baseUrl"])
    
    cap_req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0"})
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
        raise Exception("Web player track had no text lines.")
    return " ".join(full_text), segments

def fetch_via_library(video_id: str):
    """Tier 3: youtube-transcript-api fallback with language search & translation."""
    import youtube_transcript_api
    from youtube_transcript_api import YouTubeTranscriptApi
    
    transcript_data = None
    try:
        t_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            t = t_list.find_transcript(['en', 'en-US', 'en-GB', 'en-IN', 'hi', 'es', 'fr', 'de'])
            transcript_data = t.fetch()
        except Exception:
            for t in t_list:
                transcript_data = t.fetch()
                break
    except Exception:
        pass

    if not transcript_data:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)

    segments, full_text = [], []
    for item in transcript_data:
        text = html.unescape(item.get('text', '')).replace('\n', ' ').strip()
        start_sec = item.get('start', 0.0)
        if text:
            segments.append({"timestamp": format_timestamp(start_sec), "text": text})
            full_text.append(text)

    if not full_text:
        raise Exception("Library returned empty transcript.")
    return " ".join(full_text), segments

def get_transcript(video_id: str):
    """Cascading execution across all 3 tiers."""
    errors = []
    
    # 1. Try Innertube
    try:
        return fetch_via_innertube(video_id)
    except Exception as e:
        errors.append(f"Innertube: {str(e)}")

    # 2. Try Web Player direct
    try:
        return fetch_via_web_player(video_id)
    except Exception as e:
        errors.append(f"WebPlayer: {str(e)}")

    # 3. Try youtube-transcript-api
    try:
        return fetch_via_library(video_id)
    except Exception as e:
        errors.append(f"Library: {str(e)}")

    raise Exception(f"Transcript extraction failed for video ({video_id}). Please verify the video has closed captions/subtitles enabled.")
