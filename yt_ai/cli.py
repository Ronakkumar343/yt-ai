"""Command-line interface for yt-ai.

Usage:
    python -m yt_ai <youtube-url-or-video-id> [--sentences N] [--output FILE]
    python -m yt_ai --file transcript.txt      # summarise a saved transcript
    python -m yt_ai --stdin                     # read a transcript from stdin
"""

from __future__ import annotations

import argparse
import sys

from .summarize import key_points, summarize
from .transcript import TranscriptError, extract_video_id, fetch_transcript

__all__ = ["build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-ai",
        description="Summarise a YouTube video from its caption transcript.",
    )
    parser.add_argument("source", nargs="?", help="YouTube URL or 11-character video ID")
    parser.add_argument("--file", help="summarise a transcript saved in this text file")
    parser.add_argument("--stdin", action="store_true", help="read the transcript from stdin")
    parser.add_argument(
        "--sentences", type=int, default=5,
        help="maximum sentences in the summary (default: 5)",
    )
    parser.add_argument(
        "--points", type=int, default=5,
        help="maximum key points to list (default: 5)",
    )
    parser.add_argument("--no-llm", action="store_true",
                        help="force the offline extractive summariser")
    parser.add_argument("--output", help="also write the result to this file")
    return parser


def _load_transcript(args: argparse.Namespace) -> str:
    if args.file:
        with open(args.file, encoding="utf-8") as handle:
            return handle.read()
    if args.stdin:
        return sys.stdin.read()
    if not args.source:
        raise TranscriptError("give a YouTube URL/ID, or use --file / --stdin")
    return fetch_transcript(extract_video_id(args.source))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.sentences < 1:
        print("error: --sentences must be at least 1", file=sys.stderr)
        return 2
    try:
        transcript = _load_transcript(args)
    except (TranscriptError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not transcript.strip():
        print("error: transcript is empty", file=sys.stderr)
        return 1
    summary, method = summarize(
        transcript, max_sentences=args.sentences, use_llm=not args.no_llm
    )
    lines = [f"Summary ({method}):", summary, "", "Key points:"]
    lines += [f"- {point}" for point in key_points(transcript, args.points)]
    output = "\n".join(lines) + "\n"
    print(output, end="")
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
