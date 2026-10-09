"""YouTube video-ID parsing and transcript fetching for yt-ai.

Fetching uses the optional ``youtube-transcript-api`` package. Everything
else in this module is pure standard library, so ID parsing can be tested
offline. ``fetch_transcript`` raises :class:`TranscriptError` with a plain
message for every expected failure (missing package, no captions, bad ID)
instead of leaking library exceptions to the CLI.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

__all__ = ["TranscriptError", "extract_video_id", "fetch_transcript"]

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PATH_ID_RE = re.compile(r"^/(?:shorts|embed|live|v)/([A-Za-z0-9_-]{11})(?:[/?#]|$)")


class TranscriptError(Exception):
    """A transcript could not be obtained for a user-facing reason."""


def extract_video_id(url_or_id: str) -> str:
    """Return the 11-character video ID from a YouTube URL or a bare ID.

    Accepts ``watch?v=``, ``youtu.be/``, ``shorts/``, ``embed/``, ``live/``
    and ``m.youtube.com`` forms. Raises ``ValueError`` for anything else.
    """
    if not url_or_id or not isinstance(url_or_id, str):
        raise ValueError("expected a YouTube URL or video ID, got empty input")
    text = url_or_id.strip()
    if _VIDEO_ID_RE.match(text):
        return text
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.hostname or "").lower()
    if host in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.lstrip("/").split("/")[0]
        if _VIDEO_ID_RE.match(candidate):
            return candidate
        raise ValueError(f"no valid video ID in URL: {url_or_id!r}")
    if host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v", [])
            if values and _VIDEO_ID_RE.match(values[0]):
                return values[0]
            raise ValueError(f"no valid 'v' parameter in URL: {url_or_id!r}")
        match = _PATH_ID_RE.match(parsed.path)
        if match:
            return match.group(1)
        raise ValueError(f"unsupported YouTube URL form: {url_or_id!r}")
    raise ValueError(f"not a YouTube URL or video ID: {url_or_id!r}")


def fetch_transcript(video_id: str) -> str:
    """Fetch a video's caption transcript as plain text.

    Requires the optional ``youtube-transcript-api`` package and a video
    that actually has captions. Raises :class:`TranscriptError` otherwise.
    """
    if not _VIDEO_ID_RE.match(video_id or ""):
        raise TranscriptError(f"invalid video ID: {video_id!r}")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise TranscriptError(
            "transcript fetching needs the optional package: "
            "pip install youtube-transcript-api "
            "(or summarise a saved transcript with --file instead)"
        ) from exc
    try:
        # youtube-transcript-api >= 1.0 exposes fetch(); older releases
        # expose get_transcript(). Support both shapes.
        api = YouTubeTranscriptApi()
        if hasattr(api, "fetch"):
            fetched = api.fetch(video_id)
            snippets = [
                getattr(item, "text", None) or item.get("text", "")
                if isinstance(item, dict)
                else str(item)
                for item in fetched
            ]
        else:  # pragma: no cover - depends on installed library version
            snippets = [
                entry.get("text", "")
                for entry in YouTubeTranscriptApi.get_transcript(video_id)
            ]
    except Exception as exc:  # library raises several unrelated types
        raise TranscriptError(
            f"could not fetch a transcript for {video_id}: {exc}"
        ) from exc
    text = " ".join(snippet.strip() for snippet in snippets if snippet.strip())
    if not text:
        raise TranscriptError(f"transcript for {video_id} was empty")
    return text
