"""yt-ai — summarise YouTube videos from their caption transcripts."""

from .summarize import extractive_summary, key_points, summarize
from .transcript import TranscriptError, extract_video_id, fetch_transcript

__version__ = "0.1.0"

__all__ = [
    "TranscriptError",
    "extract_video_id",
    "extractive_summary",
    "fetch_transcript",
    "key_points",
    "summarize",
    "__version__",
]
