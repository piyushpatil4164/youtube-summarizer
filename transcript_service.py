"""Fetch YouTube transcripts for AI YouTube Lecture Digest.

Public interface retained for app.py:
    extract_video_id(url) -> str
    get_transcript(video_id, api_key) -> (full_text, timestamped_segments)

Supadata is tried first (so cloud-hosted apps do not depend on direct YouTube
caption requests). youtube-transcript-api is a fallback. SUPADATA_API_KEY is
read from the process environment or Streamlit secrets; ``api_key`` remains in
the function signature for compatibility and is not treated as a Supadata key.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from youtube_transcript_api import YouTubeTranscriptApi

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # Environment variables configured by Streamlit or the hosting platform
    # work without python-dotenv; local .env loading needs that package.
    pass

SUPADATA_BASE_URL = "https://api.supadata.ai/v1"
CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 20
# Supadata says AI transcript requests can take about 100 seconds.
MAX_JOB_WAIT_SECONDS = 120
POLL_INTERVAL_SECONDS = 1
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str:
    """Extract and validate a video ID from a YouTube URL or an ID itself."""
    value = str(url).strip()
    if not value:
        raise ValueError("Please enter a YouTube URL.")
    if VIDEO_ID_RE.fullmatch(value):
        return value

    parsed = urlparse(value if "://" in value else "https://" + value)
    host = (parsed.hostname or "").lower().rstrip(".")
    video_id = ""

    if host in {"youtu.be", "www.youtu.be"}:
        pieces = parsed.path.strip("/").split("/")
        video_id = pieces[0] if pieces else ""
    elif host == "youtube.com" or host.endswith(".youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
                video_id = parts[1]

    if not VIDEO_ID_RE.fullmatch(video_id):
        raise ValueError("Invalid YouTube URL or video ID.")
    return video_id


def _supadata_key() -> str | None:
    key = os.getenv("SUPADATA_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st

        value = st.secrets.get("SUPADATA_API_KEY", "")
        return str(value).strip() or None
    except Exception:
        # Streamlit may be absent or secrets may not be configured locally.
        return None


def format_timestamp(seconds: Any) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError, OverflowError):
        total = 0
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def _to_segments(content: Any) -> list[dict[str, str]]:
    """Normalize Supadata or youtube-transcript-api content to app format."""
    if isinstance(content, dict):
        content = content.get("content", content.get("segments", content.get("transcript", [])))
    if isinstance(content, str):
        text = content.strip()
        return [{"timestamp": "00:00", "text": text}] if text else []
    if not isinstance(content, (list, tuple)):
        # youtube-transcript-api FetchedTranscript is iterable, but may not be a list.
        try:
            content = list(content)
        except (TypeError, ValueError):
            return []

    segments: list[dict[str, str]] = []
    for item in content:
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("transcript") or "").strip()
            if not text:
                continue
            # Supadata offset is milliseconds; youtube-transcript-api start is seconds.
            if "offset" in item:
                try:
                    seconds = float(item["offset"]) / 1000.0
                except (TypeError, ValueError, OverflowError):
                    seconds = 0
            else:
                raw_start = item.get("start", item.get("startTime", 0))
                try:
                    seconds = float(raw_start)
                except (TypeError, ValueError, OverflowError):
                    seconds = 0
            stamp = item.get("timestamp")
            timestamp = str(stamp) if isinstance(stamp, str) and stamp else format_timestamp(seconds)
        else:
            text = str(getattr(item, "text", "") or "").strip()
            if not text:
                continue
            timestamp = format_timestamp(getattr(item, "start", 0))
        segments.append({"timestamp": timestamp, "text": text})
    return segments


def _response_error(response: requests.Response) -> str:
    """Build a useful error without exposing request headers or API keys."""
    try:
        body = response.json()
    except ValueError:
        body = {}
    if isinstance(body, dict):
        code = body.get("error")
        message = body.get("message") or body.get("details")
        if isinstance(code, dict):
            message = code.get("message") or message
            code = code.get("code") or code.get("type")
        parts = [str(part) for part in (code, message) if part]
        if parts:
            return f"Supadata returned HTTP {response.status_code}: {' — '.join(parts)}"
    return f"Supadata returned HTTP {response.status_code}. Check the API key, account credits, and video access."


def _get_json(url: str, *, headers: dict[str, str], params: dict[str, str] | None = None) -> dict[str, Any]:
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
    )
    if not response.ok:
        raise RuntimeError(_response_error(response))
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("Supadata returned a non-JSON response.") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Supadata returned an unexpected response format.")
    return data


def _fetch_supadata(video_id: str, key: str) -> list[dict[str, str]]:
    headers = {"x-api-key": key, "Accept": "application/json"}
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    data = _get_json(
        f"{SUPADATA_BASE_URL}/transcript",
        headers=headers,
        params={"url": video_url, "mode": "auto"},
    )

    job_id = data.get("jobId")
    if job_id:
        deadline = time.monotonic() + MAX_JOB_WAIT_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    "Supadata transcript job is still processing after 120 seconds. Try again shortly."
                )
            time.sleep(min(POLL_INTERVAL_SECONDS, remaining))
            data = _get_json(
                f"{SUPADATA_BASE_URL}/transcript/{job_id}",
                headers=headers,
            )
            status = str(data.get("status", "")).lower()
            if status == "failed":
                detail = data.get("error")
                raise RuntimeError(f"Supadata transcript job failed{': ' + str(detail) if detail else '.'}")
            if status == "completed":
                # Current REST docs show content on the job response. Also accept
                # a nested result object, used by SDK versions/examples.
                data = data.get("result", data)
                if not isinstance(data, dict):
                    raise RuntimeError("Supadata completed the job with an unexpected result format.")
                break
            if status not in {"queued", "active"}:
                raise RuntimeError(f"Supadata returned an unknown transcript job status: {status or 'missing'}.")

    segments = _to_segments(data.get("content", data.get("segments", data.get("transcript", []))))
    if not segments:
        raise RuntimeError("Supadata returned no transcript segments (the video may contain no speech).")
    return segments


def _fetch_youtube(video_id: str) -> list[dict[str, str]]:
    # This is the youtube-transcript-api 1.x interface.
    transcript = YouTubeTranscriptApi().fetch(video_id)
    segments = _to_segments(transcript)
    if not segments:
        raise RuntimeError("YouTube returned no transcript segments.")
    return segments


def get_transcript(
    video_id: str,
    api_key: str | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Return (full_text, timestamped_segments), preserving app.py's contract.

    ``api_key`` is retained for compatibility with app.py. In the supplied app
    it is the Groq key, so Supadata uses SUPADATA_API_KEY from environment or
    Streamlit secrets instead.
    """
    del api_key  # Never send or mistake the Groq key for a Supadata credential.
    video_id = extract_video_id(video_id)
    supadata_key = _supadata_key()
    supadata_error: Exception | None = None

    if supadata_key:
        try:
            segments = _fetch_supadata(video_id, supadata_key)
            return " ".join(part["text"] for part in segments), segments
        except Exception as exc:
            # Continue to the library fallback, but preserve the real reason if
            # it also fails; do not silently hide Supadata's response.
            supadata_error = exc

    try:
        segments = _fetch_youtube(video_id)
        return " ".join(part["text"] for part in segments), segments
    except Exception as youtube_error:
        if supadata_key:
            raise RuntimeError(
                f"Transcript retrieval failed. Supadata: {supadata_error}. "
                f"YouTube fallback: {youtube_error}"
            ) from youtube_error
        raise RuntimeError(
            "No SUPADATA_API_KEY is configured and the YouTube transcript fallback failed: "
            f"{youtube_error}"
        ) from youtube_error
