
import os
import re
import time
import requests

from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi


SUPADATA_URL = "https://api.supadata.ai/v1"
REQUEST_TIMEOUT = 30
MAX_POLL_ATTEMPTS = 20


# ============================================================
# API KEY
# ============================================================

def get_supadata_api_key():
    key = os.getenv("SUPADATA_API_KEY")

    if key:
        return key.strip()

    try:
        import streamlit as st
        key = st.secrets.get("SUPADATA_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass

    return None


# ============================================================
# EXTRACT VIDEO ID
# ============================================================

def extract_video_id(url):
    if not url:
        raise ValueError("Please enter a YouTube URL.")

    parsed = urlparse(url.strip())

    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]

    elif parsed.hostname and (
        parsed.hostname.endswith("youtube.com")
        or parsed.hostname.endswith("youtube-nocookie.com")
    ):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]

        elif parsed.path.startswith(("/embed/", "/shorts/", "/live/")):
            parts = parsed.path.strip("/").split("/")
            video_id = parts[1] if len(parts) > 1 else None

        else:
            video_id = None
    else:
        video_id = None

    if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Invalid YouTube video URL.")

    return video_id


# ============================================================
# TIMESTAMP FORMATTING
# ============================================================

def format_timestamp(seconds):
    seconds = max(0, int(seconds))

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining = seconds % 60

    if hours:
        return f"{hours:02d}:{minutes:02d}:{remaining:02d}"

    return f"{minutes:02d}:{remaining:02d}"


# ============================================================
# NORMALIZE TRANSCRIPT SEGMENTS
# ============================================================

def normalize_segments(content):
    """
    Convert transcript content into:
    [
        {"timestamp": "00:00", "text": "..."},
        ...
    ]
    """

    segments = []

    if isinstance(content, str):
        if content.strip():
            segments.append({
                "timestamp": "00:00",
                "text": content.strip()
            })

        return segments

    if not isinstance(content, list):
        return segments

    for item in content:
        if isinstance(item, str):
            text = item.strip()
            timestamp = "00:00"

        elif isinstance(item, dict):
            text = str(item.get("text", "")).strip()

            if not text:
                continue

            # Supadata offset is generally in milliseconds.
            if "offset" in item:
                seconds = float(item["offset"]) / 1000

            elif "start" in item:
                seconds = float(item["start"])

            elif "timestamp" in item:
                timestamp = str(item["timestamp"])
                segments.append({
                    "timestamp": timestamp,
                    "text": text
                })
                continue

            else:
                seconds = 0

            timestamp = format_timestamp(seconds)

        else:
            continue

        if text:
            segments.append({
                "timestamp": timestamp,
                "text": text
            })

    return segments


# ============================================================
# SUPADATA TRANSCRIPT
# ============================================================

def get_supadata_transcript(video_id, api_key):

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    headers = {
        "x-api-key": api_key,
        "Accept": "application/json"
    }

    # Do not request text-only output.
    # We need the original timed segments for subtitles.
    params = {
        "url": video_url,
        "mode": "auto"
    }

    response = requests.get(
        f"{SUPADATA_URL}/transcript",
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT
    )

    if response.status_code not in (200, 202):
        raise RuntimeError(
            f"Supadata HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    data = response.json()

    job_id = data.get("jobId")

    if job_id:
        for _ in range(MAX_POLL_ATTEMPTS):
            time.sleep(3)

            job_response = requests.get(
                f"{SUPADATA_URL}/transcript/{job_id}",
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            if job_response.status_code != 200:
                raise RuntimeError(
                    f"Supadata polling failed: "
                    f"{job_response.text[:300]}"
                )

            data = job_response.json()
            status = data.get("status")

            if status == "completed":
                break

            if status == "failed":
                raise RuntimeError(
                    f"Supadata job failed: {data}"
                )
        else:
            raise TimeoutError(
                "Supadata transcript processing timed out."
            )

    content = data.get("content", "")
    segments = normalize_segments(content)

    if not segments:
        raise RuntimeError(
            "Supadata returned no usable transcript segments."
        )

    full_text = " ".join(
        segment["text"] for segment in segments
    )

    return full_text, segments


# ============================================================
# YOUTUBE TRANSCRIPT API FALLBACK
# ============================================================

def get_youtube_library_transcript(video_id):

    transcript_api = YouTubeTranscriptApi()
    fetched = transcript_api.fetch(video_id)

    segments = []

    for item in fetched:
        if isinstance(item, dict):
            text = item.get("text", "")
            start = item.get("start", 0)
        else:
            text = getattr(item, "text", "")
            start = getattr(item, "start", 0)

        text = str(text).strip()

        if text:
            segments.append({
                "timestamp": format_timestamp(start),
                "text": text
            })

    if not segments:
        raise RuntimeError(
            "YouTube returned an empty transcript."
        )

    full_text = " ".join(
        segment["text"] for segment in segments
    )

    return full_text, segments


# ============================================================
# MAIN FUNCTION
# ============================================================

def get_transcript(video_id, api_key=None):

    errors = []

    supadata_key = get_supadata_api_key()

    if supadata_key:
        try:
            return get_supadata_transcript(
                video_id,
                supadata_key
            )

        except Exception as error:
            errors.append(f"Supadata: {error}")

    else:
        errors.append(
            "SUPADATA_API_KEY is not configured."
        )

    try:
        return get_youtube_library_transcript(video_id)

    except Exception as error:
        errors.append(
            f"YouTube Transcript API: {error}"
        )

    raise RuntimeError(
        "Could not retrieve YouTube transcript.\n\n"
        + "\n\n".join(errors)
        + "\n\nPlease check your Supadata API key "
        "or paste the transcript manually."
    )
