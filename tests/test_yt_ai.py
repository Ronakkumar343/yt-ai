"""Unit tests for yt-ai. Run: python -m unittest discover -s tests -v"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from yt_ai import extract_video_id, extractive_summary, key_points, summarize
from yt_ai.cli import main
from yt_ai.summarize import split_sentences
from yt_ai.transcript import TranscriptError, fetch_transcript

SAMPLE = (
    "Photosynthesis is how plants make food. Plants use sunlight to turn "
    "water and carbon dioxide into sugar and oxygen. This process happens "
    "inside chloroplasts, which contain a green pigment called chlorophyll. "
    "Um, so yeah, welcome back to the channel everyone. Photosynthesis "
    "matters because nearly all life on Earth depends on the oxygen and "
    "food it produces. Scientists measure photosynthesis by tracking "
    "oxygen release in leaves. Remember to like the video and subscribe "
    "for more content every single week."
)


class VideoIdTests(unittest.TestCase):
    def test_bare_id(self):
        self.assertEqual(extract_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_watch_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_short_forms(self):
        for url in (
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        ):
            self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ", url)

    def test_rejects_non_youtube(self):
        for bad in ("", "https://example.com/watch?v=dQw4w9WgXcQ",
                    "https://www.youtube.com/watch", "not a url"):
            with self.assertRaises(ValueError, msg=bad):
                extract_video_id(bad)


class SummarizeTests(unittest.TestCase):
    def test_split_sentences(self):
        self.assertEqual(
            split_sentences("One. Two? Three!"), ["One.", "Two?", "Three!"]
        )
        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("No terminator"), ["No terminator"])

    def test_summary_prefers_substance_over_filler(self):
        summary = extractive_summary(SAMPLE, max_sentences=3)
        self.assertIn("Photosynthesis", summary)
        self.assertNotIn("subscribe", summary)
        self.assertEqual(len(split_sentences(summary)), 3)

    def test_summary_preserves_original_order(self):
        sentences = split_sentences(extractive_summary(SAMPLE, max_sentences=4))
        positions = [SAMPLE.index(sentence) for sentence in sentences]
        self.assertEqual(positions, sorted(positions))

    def test_short_text_returned_whole(self):
        self.assertEqual(extractive_summary("Only one. And two.", 5),
                         "Only one. And two.")
        self.assertEqual(extractive_summary("", 5), "")

    def test_bad_sentence_count(self):
        with self.assertRaises(ValueError):
            extractive_summary(SAMPLE, max_sentences=0)

    def test_key_points(self):
        points = key_points(SAMPLE, max_points=3)
        self.assertEqual(len(points), 3)
        self.assertTrue(all("subscribe" not in p for p in points))

    def test_summarize_without_key_is_extractive(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            summary, method = summarize(SAMPLE, max_sentences=3)
        self.assertEqual(method, "extractive")
        self.assertIn("Photosynthesis", summary)

    def test_summarize_falls_back_when_llm_fails(self):
        env = {"OPENAI_API_KEY": "test-key-not-real"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("yt_ai.summarize._llm_summary",
                           side_effect=RuntimeError("boom")):
            summary, method = summarize(SAMPLE, max_sentences=2)
        self.assertEqual(method, "extractive")
        self.assertTrue(summary)


class FetchTests(unittest.TestCase):
    def test_invalid_id_raises_transcript_error(self):
        with self.assertRaises(TranscriptError):
            fetch_transcript("nope")


class CliTests(unittest.TestCase):
    def _run_file(self, text, extra=()):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(text)
            path = handle.name
        try:
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, {}, clear=True), \
                    redirect_stdout(out), redirect_stderr(err):
                code = main(["--file", path, "--no-llm", *extra])
            return code, out.getvalue(), err.getvalue()
        finally:
            os.unlink(path)

    def test_cli_summarises_file(self):
        code, out, _ = self._run_file(SAMPLE)
        self.assertEqual(code, 0)
        self.assertIn("Summary (extractive):", out)
        self.assertIn("Key points:", out)
        self.assertIn("Photosynthesis", out)

    def test_cli_empty_file_fails_cleanly(self):
        code, _, err = self._run_file("   ")
        self.assertEqual(code, 1)
        self.assertIn("empty", err)

    def test_cli_no_source_fails_cleanly(self):
        err = io.StringIO()
        with redirect_stderr(err):
            code = main([])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
