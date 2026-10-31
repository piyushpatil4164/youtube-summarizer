import html
import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

from config import get_youtube_proxy_url


SUPPORTED_LANGUAGES = [
    "en",
    "en-US",
    "en-GB",
    "en-IN",
    "hi",
    "es",
    "fr",
    "de",
]

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "youtu.be",
    "www.youtu.be",
}


def extract_video_id(url: str) -> str | None:
    """Extract an 11-character YouTube video ID from supported URL formats."""
    if not url:
        return None

    value = url.strip()

    # Also allow a user to paste the video ID directly.
    if VIDEO_ID_PATTERN.fullmatch(value):
        return value

    try:
        parsed = urlparse(value)

        # Require a valid YouTube hostname.
        host = (parsed.hostname or "").lower()
        if host not in YOUTUBE_HOSTS:
            return None

        path_parts = [part for part in parsed.path.split("/") if part]

        if host.endswith("youtu.be"):
            video_id = path_parts[0] if path_parts else None

        elif parsed.path.rstrip("/") == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]

        elif len(path_parts) >= 2 and path_parts[0] in {
            "embed",
            "shorts",
            "live",
            "v",
        }:
            video_id = path_parts[1]

        else:
            return None

        if video_id and VIDEO_ID_PATTERN.fullmatch(video_id):
            return video_id

    except Exception:
        return None

    return None


def format_timestamp(seconds: float) -> str:
    """Convert seconds into MM:SS or HH:MM:SS."""
    total = max(0, int(float(seconds or 0)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def _create_youtube_api() -> YouTubeTranscriptApi:
    """Create the transcript client, optionally using the configured proxy."""
    proxy_url = get_youtube_proxy_url()

    if not proxy_url:
        return YouTubeTranscriptApi()

    proxy_config = GenericProxyConfig(
        http_url=proxy_url,
        https_url=proxy_url,
    )

    return YouTubeTranscriptApi(proxy_config=proxy_config)


def _convert_transcript(fetched_transcript):
    """Convert the library's fetched transcript into plain text and segments."""
    full_text = []
    segments = []

    for item in fetched_transcript:
        raw_text = getattr(item, "text", "")
        start_seconds = getattr(item, "start", 0)

        line = html.unescape(str(raw_text))
        line = line.replace("\n", " ").strip()

        if not line:
            continue

        full_text.append(line)
        segments.append(
            {
                "timestamp": format_timestamp(start_seconds),
                "text": line,
            }
        )

    if not full_text:
        raise ValueError("The selected YouTube transcript contains no text.")

    return " ".join(full_text), segments


def get_transcript(video_id: str, api_key: str = ""):
    """
    Fetch real YouTube captions.

    Returns:
        tuple[str, list[dict]]: transcript text and timestamped segments.

    The api_key argument is retained for compatibility with the existing app.
    It is not needed by youtube-transcript-api.
    """
    if not video_id or not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError(
            "Invalid YouTube video ID. Please enter a valid YouTube URL."
        )

    try:
        youtube_api = _create_youtube_api()

        # Current youtube-transcript-api API (v1.x).
        transcript_list = youtube_api.list(video_id)

        try:
            transcript_track = transcript_list.find_transcript(
                SUPPORTED_LANGUAGES
            )
        except Exception:
            # If preferred languages are unavailable, use the first track.
            transcript_track = next(iter(transcript_list), None)

        if transcript_track is None:
            raise ValueError("No caption tracks are available for this video.")

        fetched_transcript = transcript_track.fetch()
        return _convert_transcript(fetched_transcript)

    except Exception as exc:
        error_name = type(exc).__name__
        error_detail = str(exc).strip()

        proxy_is_configured = bool(get_youtube_proxy_url())

        if error_name in {"IpBlocked", "RequestBlocked"}:
            message = (
                "YouTube blocked the server's IP address while requesting "
                "captions. This commonly happens on cloud hosting platforms."
            )

            if not proxy_is_configured:
                message += (
                    "\n\nNo YOUTUBE_PROXY_URL is configured. A compatible "
                    "proxy may help, but it is not guaranteed to work."
                )

        elif error_name == "TranscriptsDisabled":
            message = "Captions are disabled for this YouTube video."

        elif error_name == "NoTranscriptFound":
            message = (
                "No transcript was found in the supported languages "
                "for this video."
            )

        elif error_name in {"VideoUnavailable", "AgeRestricted"}:
            message = (
                "This video is unavailable to the transcript service or "
                "has an access restriction."
            )

        else:
            message = (
                f"Could not retrieve captions ({error_name})."
            )

        if error_detail:
            message += f"\n\nTechnical details: {error_detail}"

        message += (
            "\n\nYou can still use the app by pasting the lecture transcript "
            "into the Direct Text / Transcript Input box."
        )

        raise RuntimeError(message) from exc
