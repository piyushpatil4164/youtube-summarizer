"""Fast transcript retrieval for AI YouTube Lecture Digest.

Drop this module beside app.py. get_transcript(video_id, api_key) keeps the
existing app contract: (full_text, [{"timestamp": ..., "text": ...}, ...]).
"""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlparse, parse_qs

import requests
from youtube_transcript_api import YouTubeTranscriptApi

SUPADATA_URL = "https://api.supadata.ai/v1"
CONNECT_TIMEOUT = 3.05
READ_TIMEOUT = 8
MAX_SUPADATA_WAIT = 12.0
POLL_INTERVALS = (0.5, 1.0, 2.0, 3.0, 3.0)

def extract_video_id(url: str) -> str:
    """Extract and validate a YouTube video ID from a URL or ID."""

    value = str(url).strip()

    if not value:
        raise ValueError("Please enter a YouTube URL.")

    # Accept a video ID directly.
    if len(value) == 11 and all(
        c.isalnum() or c in "-_" for c in value
    ):
        return value

    parsed = urlparse(
        value if "://" in value else "https://" + value
    )

    host = parsed.netloc.lower().split(":")[0]
    video_id = ""

    if host in ("youtu.be", "www.youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]

    elif host.endswith("youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]

        elif any(
            part in parsed.path
            for part in ("/shorts/", "/embed/", "/live/")
        ):
            video_id = parsed.path.rstrip("/").split("/")[-1]

    if len(video_id) != 11 or not all(
        c.isalnum() or c in "-_" for c in video_id
    ):
        raise ValueError("Invalid YouTube URL or video ID.")

    return video_id

def _supadata_key() -> str | None:
    key = os.getenv("SUPADATA_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st

        return str(st.secrets.get("SUPADATA_API_KEY", "")).strip() or None
    except Exception:
        return None


def format_timestamp(seconds: Any) -> str:
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError, OverflowError):
        total = 0
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def _segments(content: Any) -> list[dict[str, str]]:
    if isinstance(content, dict):
        # Some responses wrap timed entries in a nested data/result object.
        content = content.get("content", content.get("segments", content.get("transcript", [])))
    if isinstance(content, str):
        content = [{"text": content, "start": 0}] if content.strip() else []
    if not isinstance(content, (list, tuple)):
        return []

    result: list[dict[str, str]] = []
    for item in content:
        if isinstance(item, str):
            text, stamp = item.strip(), "00:00"
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("transcript") or "").strip()
            if not text:
                continue
            if item.get("timestamp") is not None and not isinstance(item.get("timestamp"), (int, float)):
                stamp = str(item["timestamp"])
            else:
                start = item.get("start", item.get("offset", item.get("startTime", 0)))
                # Supadata's offset is milliseconds; start/startTime are seconds.
                if "offset" in item and "start" not in item and "startTime" not in item:
                    try:
                        start = float(start) / 1000
                    except (TypeError, ValueError, OverflowError):
                        start = 0
                stamp = format_timestamp(start)
        else:
            text = str(getattr(item, "text", "") or "").strip()
            if not text:
                continue
            stamp = format_timestamp(getattr(item, "start", 0))
        if text:
            result.append({"timestamp": stamp, "text": text})
    return result


def _fetch_supadata(video_id: str, key: str) -> list[dict[str, str]]:
    headers = {"x-api-key": key, "Accept": "application/json"}
    response = requests.get(
        f"{SUPADATA_URL}/transcript",
        headers=headers,
        params={"url": f"https://www.youtube.com/watch?v={video_id}", "mode": "auto"},
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Unexpected Supadata response")

    job_id = data.get("jobId")
    if job_id:
        deadline = time.monotonic() + MAX_SUPADATA_WAIT
        for delay in POLL_INTERVALS:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(delay, remaining))
            poll = requests.get(
                f"{SUPADATA_URL}/transcript/{job_id}",
                headers=headers,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            poll.raise_for_status()
            data = poll.json()
            if not isinstance(data, dict):
                raise ValueError("Unexpected Supadata job response")
            status = str(data.get("status", "")).lower()
            if status in {"completed", "succeeded", "success"}:
                break
            if status in {"failed", "error"}:
                raise RuntimeError("Supadata transcript job failed")
            if time.monotonic() >= deadline:
                break
        else:
            data = {}
        if str(data.get("status", "")).lower() not in {"completed", "succeeded", "success"}:
            raise TimeoutError("Supadata transcript job did not complete within the wait limit")

    segments = _segments(data.get("content", data.get("segments", data.get("transcript", []))))
    if not segments:
        raise ValueError("Supadata returned no usable transcript segments")
    return segments


def _fetch_youtube(video_id: str) -> list[dict[str, str]]:
    # youtube-transcript-api 1.x interface; handle its FetchedTranscript items.
    fetched = YouTubeTranscriptApi().fetch(video_id)
    result = _segments(list(fetched))
    if not result:
        raise ValueError("YouTube returned no usable transcript segments")
    return result


def get_transcript(video_id: str, api_key: str | None = None) -> tuple[str, list[dict[str, str]]]:
    """Return transcript text and timestamped segments, with fast provider fallback.

    ``api_key`` is retained for app.py compatibility. The app currently passes
    its Groq key here, so Supadata credentials are read only from
    SUPADATA_API_KEY / Streamlit secrets and never logged.
    """
    del api_key  # Do not accidentally treat the app's Groq key as Supadata's.
    key = _supadata_key()
    segments: list[dict[str, str]] | None = None
    if key:
        try:
            segments = _fetch_supadata(video_id, key)
        except Exception:
            # Provider errors may include request details; deliberately avoid logging them.
            pass
    if segments is None:
        segments = _fetch_youtube(video_id)
    return " ".join(item["text"] for item in segments), segments
