"""Summarisation for yt-ai: extractive by default, LLM when configured.

The extractive summariser is deterministic and works fully offline: it
scores sentences by the normalised frequency of their non-stopwords and
returns the top sentences in their original order. That is the honest
baseline for a transcript full of filler — the sentences carrying the
most repeated key terms are usually the substance.

If ``OPENAI_API_KEY`` is set (and ``use_llm`` is not disabled),
:func:`summarize` asks an OpenAI chat model instead and falls back to the
extractive result if the call fails for any reason.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from collections import Counter

__all__ = ["split_sentences", "extractive_summary", "key_points", "summarize"]

_STOPWORDS = frozenset(
    "a an the and or but if then else when at by for with about into through "
    "after over between out against during without before under around among "
    "am is are was were be been being have has had having do does did doing "
    "would should could ought i you he she it we they them his her its our "
    "their this that these those so too very can will just not no yes of to "
    "in on from as is it it's i'm you're we're they're don't can't won't "
    "like really actually basically literally right okay yeah um uh well "
    "know think mean get got going go one two also".split()
)

_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]+|[^.!?]+$")
_WORD_RE = re.compile(r"[a-z0-9']+")


def split_sentences(text: str) -> list[str]:
    """Split text into trimmed sentences; empty text gives an empty list."""
    if not text:
        return []
    parts = _SENTENCE_RE.findall(" ".join(text.split()))
    return [part.strip() for part in parts if part.strip()]


def _word_frequencies(sentences: list[str]) -> Counter:
    counts: Counter = Counter()
    for sentence in sentences:
        for word in _WORD_RE.findall(sentence.lower()):
            if word not in _STOPWORDS and len(word) > 2:
                counts[word] += 1
    if not counts:
        return counts
    top = counts.most_common(1)[0][1]
    return Counter({word: count / top for word, count in counts.items()})


def _ranked(sentences: list[str]) -> list[tuple[float, int, str]]:
    frequencies = _word_frequencies(sentences)
    ranked = []
    for index, sentence in enumerate(sentences):
        words = _WORD_RE.findall(sentence.lower())
        content = [w for w in words if w in frequencies]
        if not content:
            score = 0.0
        else:
            # Average (not sum) so long rambling sentences do not win
            # just by containing more words.
            score = sum(frequencies[w] for w in content) / len(content)
        ranked.append((score, index, sentence))
    return ranked


def extractive_summary(text: str, max_sentences: int = 5) -> str:
    """Return the top ``max_sentences`` sentences, in original order."""
    if max_sentences < 1:
        raise ValueError("max_sentences must be at least 1")
    sentences = split_sentences(text)
    if not sentences:
        return ""
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    chosen = sorted(_ranked(sentences), key=lambda item: (-item[0], item[1]))[
        :max_sentences
    ]
    return " ".join(sentence for _, _, sentence in sorted(chosen, key=lambda i: i[1]))


def key_points(text: str, max_points: int = 5) -> list[str]:
    """Return the highest-scoring sentences as a bullet-ready list."""
    sentences = split_sentences(text)
    if not sentences or max_points < 1:
        return []
    ranked = sorted(_ranked(sentences), key=lambda item: (-item[0], item[1]))
    chosen = sorted(ranked[:max_points], key=lambda item: item[1])
    return [sentence for _, _, sentence in chosen]


def _llm_summary(text: str, max_sentences: int) -> str:
    """Call an OpenAI chat model. Raises on any failure (caller falls back)."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    model = os.environ.get("YT_AI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You summarise YouTube transcripts accurately. "
                "Never invent facts that are not in the transcript.",
            },
            {
                "role": "user",
                "content": f"Summarise this transcript in at most "
                f"{max_sentences} sentences:\n\n{text[:24000]}",
            },
        ],
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.load(response)
    content = body["choices"][0]["message"]["content"].strip()
    if not content:
        raise RuntimeError("LLM returned an empty summary")
    return content


def summarize(text: str, max_sentences: int = 5, use_llm: bool = True) -> tuple[str, str]:
    """Summarise ``text``; returns ``(summary, method)``.

    ``method`` is ``"llm"`` when the LLM path produced the summary and
    ``"extractive"`` when the offline fallback did (including when no API
    key is configured).
    """
    if not split_sentences(text):
        return "", "extractive"
    if use_llm and os.environ.get("OPENAI_API_KEY"):
        try:
            return _llm_summary(text, max_sentences), "llm"
        except Exception:
            pass  # honest fallback: extractive still gives a real summary
    return extractive_summary(text, max_sentences), "extractive"
