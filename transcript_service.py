import re
import json
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

def extract_video_id(url: str) -> str | None:
    """Extracts the 11-character YouTube video ID from any valid YouTube URL format."""
    if not url:
        return None
    url = url.strip()
    
    match = re.search(r'(?:v=|\/vi\/|youtu\.be\/|\/embed\/|\/shorts\/|\/v\/|^)([0-9A-Za-z_-]{11})(?:[?&/#]|$)', url)
    if match:
        return match.group(1)
        
    if len(url) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url
        
    return None

def format_timestamp(seconds: float) -> str:
    """Formats raw seconds into MM:SS display format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def parse_timedtext_payload(content: str):
    """Parses JSON3 or XML subtitle payloads into structured transcript segments."""
    segments = []
    full_text = []

    # 1. Parse JSON3 format
    if content.strip().startswith("{"):
        try:
            data = json.loads(content)
            events = data.get("events", [])
            for event in events:
                segs = event.get("segs", [])
                line = "".join([s.get("utf8", "") for s in segs]).replace('\n', ' ').strip()
                if line:
                    start_sec = float(event.get("tStartMs", 0)) / 1000.0
                    segments.append({"timestamp": format_timestamp(start_sec), "text": line})
                    full_text.append(line)
            if full_text:
                return " ".join(full_text), segments
        except Exception:
            pass

    # 2. Parse XML via Regex fallback
    xml_matches = re.findall(r'<text[^>]*start="([\d\.]+)"[^>]*>(.*?)</text>', content, re.DOTALL)
    if xml_matches:
        for start_str, raw_t in xml_matches:
            line = html.unescape(raw_t).replace('\n', ' ').strip()
            if line:
                start_sec = float(start_str)
                segments.append({"timestamp": format_timestamp(start_sec), "text": line})
                full_text.append(line)
        if full_text:
            return " ".join(full_text), segments

    # 3. Parse XML via ElementTree
    try:
        root = ET.fromstring(content)
        for elem in root.iter('text'):
            if elem.text:
                line = html.unescape(elem.text).replace('\n', ' ').strip()
                start_sec = float(elem.get('start', 0.0))
                if line:
                    segments.append({"timestamp": format_timestamp(start_sec), "text": line})
                    full_text.append(line)
    except Exception:
        pass

    if full_text:
        return " ".join(full_text), segments
    raise Exception("Extracted subtitle data contains no readable dialogue.")

def fetch_innertube(video_id: str, client_name: str = "IOS"):
    """Fetches caption tracks via YouTube Innertube client endpoints."""
    url = "https://www.youtube.com/youtubei/v1/player"
    
    if client_name == "IOS":
        payload = {
            "context": {
                "client": {
                    "clientName": "IOS",
                    "clientVersion": "19.29.1",
                    "deviceModel": "iPhone16,2",
                    "userAgent": "com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X; en_US)",
                    "hl": "en",
                    "gl": "US"
                }
            },
            "videoId": video_id
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X; en_US)"
        }
    else:
        payload = {
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "19.09.37",
                    "hl": "en",
                    "gl": "US"
                }
            },
            "videoId": video_id
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11)"
        }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    tracks = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    if not tracks:
        raise Exception("No caption tracks returned in player metadata.")

    # Prioritize English, fallback to first available track
    target_url = None
    for t in tracks:
        lang = t.get("languageCode", "").lower()
        if lang.startswith("en"):
            target_url = t.get("baseUrl")
            break
    if not target_url:
        target_url = tracks[0].get("baseUrl")

    cap_req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(cap_req, timeout=10) as cap_resp:
        content = cap_resp.read().decode('utf-8', errors='ignore')

    return parse_timedtext_payload(content)

def get_transcript(video_id: str):
    """Cascades through multiple fetch methods to extract video subtitles."""
    # 1. Try iOS Player Client
    try:
        return fetch_innertube(video_id, client_name="IOS")
    except Exception:
        pass

    # 2. Try Android Player Client
    try:
        return fetch_innertube(video_id, client_name="ANDROID")
    except Exception:
        pass

    # 3. Fallback: youtube-transcript-api package
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        t_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            track = t_list.find_transcript(['en', 'en-US', 'en-GB', 'en-IN', 'hi', 'es', 'fr', 'de'])
            data = track.fetch()
        except Exception:
            data = next(iter(t_list)).fetch()

        full_text, segments = [], []
        for item in data:
            line = html.unescape(item.get('text', '')).replace('\n', ' ').strip()
            start_sec = float(item.get('start', 0.0))
            if line:
                full_text.append(line)
                segments.append({"timestamp": format_timestamp(start_sec), "text": line})
        if full_text:
            return " ".join(full_text), segments
    except Exception:
        pass

    raise Exception(f"Captions could not be automatically extracted for video ID: {video_id}. Use the 'Paste Transcript Manually' box to provide lecture text directly.")
