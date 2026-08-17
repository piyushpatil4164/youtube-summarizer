import re
import json
import html
import urllib.request
from youtube_transcript_api import YouTubeTranscriptApi

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

def fetch_from_proxy_api(video_id: str):
    """
    Bypasses YouTube server IP blocks by routing the request through 
    open-source Piped API instances.
    """
    # 3 different proxy servers to ensure it always finds a working connection
    instances = [
        "https://pipedapi.kavin.rocks",
        "https://pipedapi.smnz.de",
        "https://de-api-piped.mint.lgbt"
    ]
    
    data = None
    for api_url in instances:
        try:
            req = urllib.request.Request(f"{api_url}/streams/{video_id}", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                break  # If successful, exit the loop
        except Exception:
            continue
            
    if not data:
        raise Exception("All proxy instances failed.")
        
    subtitles = data.get("subtitles", [])
    if not subtitles:
        raise Exception("No subtitles found in proxy response.")
        
    # Pick English or the first available language track
    target_sub = next((s for s in subtitles if s.get('code', '').startswith('en')), subtitles[0])
    sub_url = target_sub.get('url')
    
    req = urllib.request.Request(sub_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode('utf-8', errors='ignore')
        
    segments = []
    full_text = []
    
    # Parse the returned VTT or XML subtitle file
    if "<?xml" in content or "<transcript" in content or "<text" in content:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(content)
        for elem in root.iter('text'):
            if elem.text:
                line = html.unescape(elem.text).replace('\n', ' ').strip()
                start = float(elem.get('start', 0.0))
                if line:
                    segments.append({"timestamp": format_timestamp(start), "text": line})
                    full_text.append(line)
    else:
        current_sec = 0.0
        for line in content.split('\n'):
            line = line.strip()
            if not line or line == "WEBVTT": continue
            if "-->" in line:
                start_str = line.split("-->")[0].strip()
                parts = start_str.split(':')
                try:
                    if len(parts) == 3:
                        current_sec = float(parts[0])*3600 + float(parts[1])*60 + float(parts[2].replace(',','.'))
                    elif len(parts) == 2:
                        current_sec = float(parts[0])*60 + float(parts[1].replace(',','.'))
                except Exception: pass
                continue
                
            clean_text = re.sub(r'<[^>]+>', '', line)
            clean_text = html.unescape(clean_text).strip()
            if clean_text and not re.match(r'^\d+$', clean_text):
                segments.append({"timestamp": format_timestamp(current_sec), "text": clean_text})
                full_text.append(clean_text)

    if not full_text:
        raise Exception("Parsed subtitle content was empty.")
        
    return " ".join(full_text), segments

def get_transcript(video_id: str):
    """
    Retrieves transcripts by prioritizing the direct YouTube API, 
    and instantly falling back to proxy servers if YouTube blocks the cloud IP.
    """
    # Strategy 1: Direct YouTube Fetch (Works locally, blocked on Cloud)
    try:
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
        
    # Strategy 2: Proxy API Fallback (Bypasses Cloud IP Blocking)
    try:
        return fetch_from_proxy_api(video_id)
    except Exception:
        pass
        
    raise Exception(f"YouTube blocked the server from downloading captions for video ({video_id}). Please click the 'Direct Text' box below and paste the transcript manually.")
