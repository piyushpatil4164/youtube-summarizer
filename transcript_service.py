
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
# GET SUPADATA API KEY
# ============================================================

def get_supadata_api_key():
    """
    Read Supadata API key from Streamlit Secrets or .env.
    """

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
# EXTRACT YOUTUBE VIDEO ID
# ============================================================

def extract_video_id(url):
    """
    Extract YouTube video ID from common YouTube URL formats.
    """

    if not url:
        raise ValueError("Please enter a YouTube URL.")

    url = url.strip()

    parsed = urlparse(url)

    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]

    elif parsed.hostname and (
        parsed.hostname.endswith("youtube.com")
        or parsed.hostname.endswith("youtube-nocookie.com")
    ):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]

        elif parsed.path.startswith(("/embed/", "/shorts/", "/live/")):
            video_id = parsed.path.split("/")[2]

        else:
            video_id = None

    else:
        raise ValueError("Please enter a valid YouTube URL.")

    if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Could not identify a valid YouTube video ID.")

    return video_id


# ============================================================
# CONVERT SUPADATA RESPONSE TO TEXT
# ============================================================

def _extract_transcript_text(data):
    content = data.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []

        for segment in content:
            if isinstance(segment, dict):
                text = segment.get("text", "")
                if text:
                    parts.append(str(text))

        return " ".join(parts).strip()

    return ""


# ============================================================
# SUPADATA TRANSCRIPT RETRIEVAL
# ============================================================

def get_supadata_transcript(video_id, api_key):
    """
    Retrieve a YouTube transcript through Supadata.
    Supports both immediate and asynchronous responses.
    """

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    headers = {
        "x-api-key": api_key,
        "Accept": "application/json",
    }

    params = {
        "url": video_url,
        "text": "true",
        "mode": "auto",
    }

    response = requests.get(
        f"{SUPADATA_URL}/transcript",
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code not in (200, 202):
        raise RuntimeError(
            f"Supadata returned HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    data = response.json()

    # Immediate transcript response
    transcript = _extract_transcript_text(data)

    if transcript:
        return transcript

    # Asynchronous response: poll the returned job ID
    job_id = data.get("jobId")

    if not job_id:
        raise RuntimeError(
            f"Supadata returned no transcript or job ID: {data}"
        )

    for attempt in range(MAX_POLL_ATTEMPTS):
        time.sleep(3)

        job_response = requests.get(
            f"{SUPADATA_URL}/transcript/{job_id}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if job_response.status_code != 200:
            raise RuntimeError(
                f"Supadata job polling failed: "
                f"HTTP {job_response.status_code} "
                f"{job_response.text[:300]}"
            )

        job_data = job_response.json()
        status = job_data.get("status")

        if status == "completed":
            transcript = _extract_transcript_text(job_data)

            if transcript:
                return transcript

            raise RuntimeError(
                "Supadata completed the job but returned empty transcript."
            )

        if status == "failed":
            raise RuntimeError(
                f"Supadata transcript job failed: {job_data}"
            )

    raise TimeoutError(
        "Supadata transcript processing took too long. "
        "Please try again."
    )


# ============================================================
# YOUTUBE-TRANSCRIPT-API FALLBACK
# ============================================================

def get_youtube_library_transcript(video_id):
    """
    Try the official youtube-transcript-api Python package.
    This may still fail if the hosting IP is blocked.
    """

    transcript_api = YouTubeTranscriptApi()

    fetched = transcript_api.fetch(video_id)

    parts = []

    for item in fetched:
        if isinstance(item, dict):
            text = item.get("text", "")
        else:
            text = getattr(item, "text", "")

        if text:
            parts.append(str(text))

    transcript = " ".join(parts).strip()

    if not transcript:
        raise RuntimeError("YouTube returned an empty transcript.")

    return transcript


# ============================================================
# MAIN TRANSCRIPT FUNCTION
# ============================================================

def get_transcript(video_id, api_key=None):
    """
    First try Supadata.
    If unavailable or unsuccessful, try youtube-transcript-api.

    The api_key parameter is retained for compatibility with app.py.
    It is not used as a Supadata key.
    """

    errors = []

    supadata_key = get_supadata_api_key()

    if supadata_key:
        try:
            transcript = get_supadata_transcript(
                video_id,
                supadata_key,
            )

            if transcript:
                return transcript

        except Exception as error:
            errors.append(f"Supadata: {error}")

    else:
        errors.append(
            "SUPADATA_API_KEY is not configured."
        )

    try:
        transcript = get_youtube_library_transcript(video_id)

        if transcript:
            return transcript

    except Exception as error:
        errors.append(f"YouTube Transcript API: {error}")

    raise RuntimeError(
        "Could not retrieve the YouTube transcript.\n\n"
        + "\n\n".join(errors)
        + "\n\nPlease check your Supadata API key or paste "
        "the transcript into the Direct Text / Transcript Input box."
    )
