
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


# ============================================================
# EXTRACT YOUTUBE VIDEO ID
# ============================================================

def extract_video_id(url: str) -> str | None:
    """Extract an 11-character YouTube video ID."""

    if not url:
        return None

    value = url.strip()

    if VIDEO_ID_PATTERN.fullmatch(value):
        return value

    # Allow URLs pasted without https://
    if "://" not in value:
        value = "https://" + value

    try:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()

        if host not in YOUTUBE_HOSTS:
            return None

        path_parts = [
            part for part in parsed.path.split("/") if part
        ]

        if host.endswith("youtu.be"):
            video_id = path_parts[0] if path_parts else None

        elif parsed.path.rstrip("/") == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]

        elif (
            len(path_parts) >= 2
            and path_parts[0] in {"embed", "shorts", "live", "v"}
        ):
            video_id = path_parts[1]

        else:
            return None

        if video_id and VIDEO_ID_PATTERN.fullmatch(video_id):
            return video_id

    except Exception:
        return None

    return None


# ============================================================
# FORMAT TIMESTAMP
# ============================================================

def format_timestamp(seconds: float) -> str:
    """Convert seconds into MM:SS or HH:MM:SS."""

    total = max(0, int(float(seconds or 0)))

    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


# ============================================================
# CREATE YOUTUBE TRANSCRIPT CLIENT
# ============================================================

def _create_youtube_api():
    """Create the API client, optionally using a configured proxy."""

    proxy_url = get_youtube_proxy_url()

    if not proxy_url:
        return YouTubeTranscriptApi()

    proxy_config = GenericProxyConfig(
        http_url=proxy_url,
        https_url=proxy_url,
    )

    return YouTubeTranscriptApi(
        proxy_config=proxy_config
    )


# ============================================================
# CONVERT TRANSCRIPT INTO TEXT AND SEGMENTS
# ============================================================

def _convert_transcript(fetched_transcript):
    """Convert fetched captions into plain text and timestamped segments."""

    full_text = []
    segments = []

    for item in fetched_transcript:

        if isinstance(item, dict):
            raw_text = item.get("text", "")
            start_seconds = item.get("start", 0)
        else:
            raw_text = getattr(item, "text", "")
            start_seconds = getattr(item, "start", 0)

        line = html.unescape(str(raw_text))
        line = line.replace("\n", " ").strip()

        if not line:
            continue

        full_text.append(line)

        segments.append({
            "timestamp": format_timestamp(start_seconds),
            "text": line,
        })

    if not full_text:
        raise ValueError(
            "The selected YouTube transcript contains no readable text."
        )

    return " ".join(full_text), segments


# ============================================================
# PRIORITIZE AVAILABLE CAPTION TRACKS
# ============================================================

def _get_ordered_tracks(transcript_list):
    """
    Prefer supported languages.
    Within each language, prefer manually created captions.
    Try other available languages if preferred ones are missing.
    """

    tracks = list(transcript_list)

    def sort_key(track):
        language = getattr(track, "language_code", "")

        is_generated = getattr(
            track,
            "is_generated",
            False
        )

        try:
            language_rank = SUPPORTED_LANGUAGES.index(language)
        except ValueError:
            language_rank = len(SUPPORTED_LANGUAGES)

        return (
            language_rank,
            bool(is_generated),
        )

    return sorted(tracks, key=sort_key)


# ============================================================
# CLASSIFY YOUTUBE ERRORS
# ============================================================

def _friendly_error(exc, proxy_is_configured):
    error_name = type(exc).__name__
    error_detail = str(exc).strip()

    if error_name in {"IpBlocked", "RequestBlocked"}:
        message = (
            "YouTube blocked the server's IP address while requesting "
            "captions. This commonly happens on cloud hosting platforms."
        )

        if not proxy_is_configured:
            message += (
                "\n\nNo YOUTUBE_PROXY_URL is configured. "
                "A compatible proxy may help, but it is not guaranteed."
            )

    elif error_name in {
        "TranscriptsDisabled",
        "CaptionsDisabled",
    }:
        message = (
            "Captions are disabled for this YouTube video. "
            "The transcript service cannot retrieve captions "
            "that YouTube does not make available."
        )

    elif error_name == "NoTranscriptFound":
        message = (
            "No transcript was found for this video, "
            "including the available language options."
        )

    elif error_name in {
        "VideoUnavailable",
        "AgeRestricted",
    }:
        message = (
            "This video is unavailable to the transcript service "
            "or has an access restriction."
        )

    else:
        message = (
            f"Could not retrieve captions ({error_name})."
        )

    if error_detail:
        message += f"\n\nTechnical details: {error_detail}"

    return message


# ============================================================
# GET YOUTUBE TRANSCRIPT
# ============================================================

def get_transcript(video_id: str, api_key: str = ""):
    """
    Retrieve YouTube captions.

    Returns:
        tuple[str, list[dict]]:
            Full transcript text and timestamped subtitle segments.

    api_key is retained for compatibility with app.py.
    It is not required by youtube-transcript-api.
    """

    if not video_id or not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError(
            "Invalid YouTube video ID. Please enter a valid YouTube URL."
        )

    proxy_is_configured = bool(get_youtube_proxy_url())

    try:
        youtube_api = _create_youtube_api()

        # Retrieve all available caption tracks.
        transcript_list = youtube_api.list(video_id)

    except Exception as exc:
        message = _friendly_error(
            exc,
            proxy_is_configured
        )

        message += (
            "\n\nYou can still use the app by pasting the lecture "
            "transcript into the Direct Text / Transcript Input box."
        )

        raise RuntimeError(message) from exc

    # Sort preferred languages first, then try other languages.
    try:
        tracks = _get_ordered_tracks(transcript_list)

    except Exception as exc:
        raise RuntimeError(
            f"Could not read available caption tracks: {exc}"
        ) from exc

    if not tracks:
        raise RuntimeError(
            "No caption tracks are available for this video. "
            "Check whether subtitles are enabled on YouTube."
        )

    fetch_errors = []

    # Try every available track until one can be fetched.
    for track in tracks:

        language = getattr(
            track,
            "language_code",
            "unknown"
        )

        try:
            fetched_transcript = track.fetch()

            transcript_text, segments = _convert_transcript(
                fetched_transcript
            )

            return transcript_text, segments

        except Exception as exc:
            fetch_errors.append(
                f"{language}: {type(exc).__name__}: {str(exc)}"
            )

            continue

    error_details = "\n".join(fetch_errors[:5])

    raise RuntimeError(
        "Caption tracks were found, but none could be downloaded.\n\n"
        f"Technical details:\n{error_details}\n\n"
        "You can still use the app by pasting the lecture transcript "
        "into the Direct Text / Transcript Input box."
    )
