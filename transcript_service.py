import re
import html
from youtube_transcript_api import YouTubeTranscriptApi


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


def extract_video_id(url: str) -> str | None:
    """
    Extract an 11-character YouTube video ID from common YouTube URL formats.
    """

    if not url:
        return None

    url = url.strip()

    # Remove markdown/link punctuation that users sometimes paste.
    url = re.sub(r"[\[\]\(\)]", " ", url)

    patterns = [
        # Standard watch URLs:
        # https://www.youtube.com/watch?v=XXXXXXXXXXX
        # https://www.youtube.com/watch?feature=shared&v=XXXXXXXXXXX
        r"(?:youtube\.com/watch\?[^#\s]*?\bv=)"
        r"([0-9A-Za-z_-]{11})(?:[?&#/\s]|$)",

        # Embed:
        r"(?:youtube\.com/embed/)"
        r"([0-9A-Za-z_-]{11})(?:[?&#/\s]|$)",

        # Shorts:
        r"(?:youtube\.com/shorts/)"
        r"([0-9A-Za-z_-]{11})(?:[?&#/\s]|$)",

        # Live:
        r"(?:youtube\.com/live/)"
        r"([0-9A-Za-z_-]{11})(?:[?&#/\s]|$)",

        # Old /v/ format:
        r"(?:youtube\.com/v/)"
        r"([0-9A-Za-z_-]{11})(?:[?&#/\s]|$)",

        # youtu.be:
        r"(?:youtu\.be/)"
        r"([0-9A-Za-z_-]{11})(?:[?&#/\s]|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)

    # Allow a raw YouTube video ID.
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", url):
        return url

    # Last-resort search for an 11-character video ID in pasted text.
    for token in url.split():
        clean_token = re.sub(r"[^0-9A-Za-z_-]", "", token)

        if re.fullmatch(r"[0-9A-Za-z_-]{11}", clean_token):
            return clean_token

    return None


def format_timestamp(seconds: float) -> str:
    """Convert seconds into MM:SS or HH:MM:SS."""

    seconds = max(0, int(seconds))

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def _convert_transcript_data(data):
    """
    Convert both old and new youtube-transcript-api transcript formats
    into the dictionaries expected by the Streamlit application.
    """

    # Newer versions return FetchedTranscript.
    # Convert it to the older list-of-dictionaries format when possible.
    if hasattr(data, "to_raw_data"):
        try:
            data = data.to_raw_data()
        except Exception:
            pass

    full_text = []
    segments = []

    for item in data:

        # Older versions return dictionaries.
        if isinstance(item, dict):
            text = item.get("text", "")
            start = item.get("start", 0.0)

        # Newer versions may return FetchedTranscriptSnippet objects.
        else:
            text = getattr(item, "text", "")
            start = getattr(item, "start", 0.0)

        text = html.unescape(str(text))
        text = text.replace("\n", " ").strip()

        try:
            start_seconds = float(start)
        except (TypeError, ValueError):
            start_seconds = 0.0

        if text:
            full_text.append(text)

            segments.append(
                {
                    "timestamp": format_timestamp(start_seconds),
                    "text": text,
                }
            )

    return " ".join(full_text), segments


def _get_transcript_list(video_id: str):
    """
    Retrieve the transcript list.

    Supports both:
      - current youtube-transcript-api
      - older versions of the package
    """

    api = YouTubeTranscriptApi()

    # Current API.
    if hasattr(api, "list"):
        return api.list(video_id)

    # Compatibility with older versions.
    if hasattr(YouTubeTranscriptApi, "list_transcripts"):
        return YouTubeTranscriptApi.list_transcripts(video_id)

    raise RuntimeError(
        "Your installed youtube-transcript-api version is incompatible. "
        "Please reinstall the package from requirements.txt."
    )


def get_transcript(video_id: str, api_key: str = ""):
    """
    Fetch a real YouTube transcript.

    api_key is kept in the function signature so the existing app.py
    does not need to change its function call.
    """

    if not video_id:
        raise ValueError(
            "Could not find a valid YouTube video ID. "
            "Please paste a complete YouTube video URL."
        )

    if not re.fullmatch(r"[0-9A-Za-z_-]{11}", video_id):
        raise ValueError(
            "Invalid YouTube video ID. "
            "Please check the YouTube URL and try again."
        )

    try:
        transcript_list = _get_transcript_list(video_id)

        # First try the languages useful for this application.
        transcript = None

        try:
            transcript = transcript_list.find_transcript(
                SUPPORTED_LANGUAGES
            )
        except Exception:
            pass

        # If none of the preferred languages exists,
        # use the first available transcript.
        if transcript is None:
            try:
                transcript = next(iter(transcript_list))
            except StopIteration:
                raise RuntimeError(
                    "YouTube returned no available captions for this video."
                )

        data = transcript.fetch()

        full_text, segments = _convert_transcript_data(data)

        if not full_text:
            raise RuntimeError(
                "A transcript track was found, but it contained no usable text."
            )

        return full_text, segments

    except Exception as exc:

        error_text = str(exc).strip()

        if not error_text:
            error_text = "Unknown YouTube transcript error."

        raise RuntimeError(
            f"Could not retrieve captions for this YouTube video.\n\n"
            f"Video ID: {video_id}\n"
            f"Reason: {error_text}\n\n"
            f"Possible reasons:\n"
            f"• The video has no captions.\n"
            f"• Captions are disabled by the uploader.\n"
            f"• YouTube temporarily blocked the transcript request.\n"
            f"• The video is unavailable or region-restricted.\n"
            f"• The installed youtube-transcript-api package needs updating."
        ) from exc
