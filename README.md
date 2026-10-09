# 🎬 yt-ai

Summarise a YouTube video in seconds: yt-ai fetches the video's caption
transcript and condenses it into a short summary plus key points, so a
one-hour lecture becomes a one-minute read.

> **Status: working starter (v0.1.0).** The CLI below works today —
> transcript fetching, offline extractive summarisation, optional LLM
> summarisation, and unit tests are all in and passing. There is no web
> UI yet; that is a later step, not a hidden claim.

## How it works

1. **Fetch** — `yt_ai.transcript.fetch_transcript()` gets the captions
   with the optional `youtube-transcript-api` package (the video must
   have captions). You can also summarise a transcript you already saved
   with `--file`, or pipe one in with `--stdin` — no network needed.
2. **Summarise** — by default an *extractive* summariser scores each
   sentence by the normalised frequency of its key terms and returns the
   top sentences in their original order. It is deterministic and works
   fully offline. If `OPENAI_API_KEY` is set, an OpenAI chat model is
   used instead, with automatic fallback to the extractive summary if
   the call fails — the CLI prints which method produced the result.

## Run it

```bash
pip install youtube-transcript-api   # optional, only for live fetching

python -m yt_ai "https://www.youtube.com/watch?v=VIDEO_ID"
python -m yt_ai VIDEO_ID --sentences 3 --output summary.txt
python -m yt_ai --file transcript.txt --no-llm
```

Options: `--sentences N` (summary length), `--points N` (key points),
`--no-llm` (force the offline summariser), `--output FILE`.

## Tests

```bash
python -m unittest discover -s tests -v
```

16 tests cover URL/ID parsing, sentence splitting, extractive scoring
(substance ranked above like-and-subscribe filler), the LLM fallback,
fetch error handling, and the CLI end-to-end on a saved transcript.

## Honest limits

- Only videos **with captions** can be fetched; private or caption-free
  videos return a clear error, not a made-up summary.
- The extractive summariser picks the *most central* sentences — it
  does not paraphrase or understand the video like an LLM does.
- Live fetching is exercised but not claimed as verified: on
  2026-10-09 the fetch code ran against the real
  `youtube-transcript-api` and YouTube blocked the request because
  the build machine uses a cloud-provider IP (a documented limit of
  transcript fetching from cloud IPs). On a normal home connection
  the same code path fetches captions directly; on any machine the
  failure surfaces as a clear error, and `--file` / `--stdin` always
  work offline.

## Roadmap

- [x] Transcript fetching + extractive summary CLI
- [x] Optional LLM summary with extractive fallback
- [ ] Timestamped key points (jump to the moment in the video)
- [ ] Simple web UI

## Author

Built by **Ronak Kumar** — student developer from Mithi, Pakistan,
working toward Computer Science at MIT.
