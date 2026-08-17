import re
import json
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

def extract_video_id(url: str) -> str | None:
    """Extracts standard 11-character YouTube video ID from any valid YouTube URL."""
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
    """Converts seconds into MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def parse_timedtext_response(content: str):
    """Parses both XML and JSON3 timed text subtitles cleanly."""
    segments = []
    full_text = []

    # 1. Try JSON3 format
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

    # 2. Try XML regex extraction
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

    # 3. Try standard XML parser
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
    raise Exception("Caption stream contained no readable text.")

def fetch_innertube_client(video_id: str, client_type: str = "IOS"):
    """Queries Innertube API with mobile clients that bypass cloud datacenter IP blocks."""
    url = "https://www.youtube.com/youtubei/v1/player"
    
    if client_type == "IOS":
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
    elif client_type == "ANDROID":
        payload = {
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "19.09.37",
                    "androidSdkVersion": 30,
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
    else:
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB_EMBEDDED_PLAYER",
                    "clientVersion": "1.20240210.01.00",
                    "hl": "en"
                },
                "thirdParty": {
                    "embedUrl": f"https://www.youtube.com/embed/{video_id}"
                }
            },
            "videoId": video_id
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    tracks = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    if not tracks:
        raise Exception("No caption tracks in player response.")

    target_url = None
    for t in tracks:
        lang = t.get("languageCode", "").lower()
        if lang.startswith("en"):
            target_url = t.get("baseUrl")
            break
    if not target_url:
        target_url = tracks[0].get("baseUrl")

    # Fetch subtitle stream
    cap_req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(cap_req, timeout=10) as cap_resp:
        content = cap_resp.read().decode('utf-8', errors='ignore')

    return parse_timedtext_response(content)

def get_transcript(video_id: str):
    """Cascades through iOS, Android, and Web Embedded clients to retrieve transcripts."""
    # 1. Try iOS Player Client (Bypasses bot check on cloud IPs)
    try:
        return fetch_innertube_client(video_id, client_type="IOS")
    except Exception:
        pass

    # 2. Try Android Player Client
    try:
        return fetch_innertube_client(video_id, client_type="ANDROID")
    except Exception:
        pass

    # 3. Try Web Embedded Player Client
    try:
        return fetch_innertube_client(video_id, client_type="WEB_EMBEDDED")
    except Exception:
        pass

    # 4. Fallback: youtube-transcript-api library
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
            start_sec = item.get('start', 0.0)
            if line:
                full_text.append(line)
                segments.append({"timestamp": format_timestamp(start_sec), "text": line})
        if full_text:
            return " ".join(full_text), segments
    except Exception:
        pass

    raise Exception(f"No English or auto-generated captions were found for video ID: {video_id}. You can paste lecture text directly using the backup box below.")
