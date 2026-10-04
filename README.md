# boli-zero

[![tests](https://github.com/sameer261h/boli-zero/actions/workflows/test.yml/badge.svg)](https://github.com/sameer261h/boli-zero/actions/workflows/test.yml)

An experiment in making a standard Indian-language voice stack work with a regional language it does not support:
**speak Bhojpuri to it, hear Bhojpuri back.** Built with [Gnani.ai](https://www.gnani.ai) speech models for the
Great Indian AI Internship Challenge. This is an independent project and is not affiliated with or endorsed by Gnani.

## Status

Early and honest. What exists is a working, tested prototype and the tooling to measure it. What does **not** exist
yet is any claim about accuracy: no benchmark, no native-speaker rating, no trained model.

- **Spoken conversation** (page `/`): tap the microphone, speak, hear a spoken reply. Each turn is three steps:
  recognise (Gnani Prisma, in Hindi mode because Prisma offers no Bhojpuri), reply (Evon if `BOLI_EVON_URL` is set,
  else Claude as a fallback — see below), speak (Gnani Timbre, a Hindi voice). Pronunciation of Bhojpuri by a Hindi
  voice is unverified.
- **Recognition lab** (page `/lab`): run Prisma on sample or uploaded audio and inspect exactly what came back, with
  a provisional, hedged guess at the variety. It never claims a recording is verified Bhojpuri.
- **Experiment tooling**: dataset intake, deterministic leak-proof splits, few-shot runner, scoring against held-out
  references with a "do nothing" baseline, and blinded rating sheets for native speakers. A real Evon connection now
  exists (see `experiments/2026-10-05-evon-pipeline/`); most of this tooling's real runs are still unexercised
  against it.
- **Private hosted trial**: an invitation-only deployment (Vercel + Postgres) used for small tests. It is not a public
  service and its address is not published.

| Gnani model | Status here |
|---|---|
| Prisma (speech to text) | Wired to the documented REST endpoint; run live on trial clips. |
| Timbre (text to speech) | Wired to the documented REST endpoint; used for spoken replies. |
| Evon (language model) | **Now wired.** Gnani documents no hosted endpoint, so this is the official `gnani/gnani-evon-v3.3-30B-A3B` BF16 checkpoint self-hosted on Modal (vLLM, single A100 80GB) and called via an OpenAI-compatible endpoint — see `src/boli_zero/conversation.py:EvonReply` and `experiments/2026-10-05-evon-pipeline/`. Claude remains the fallback when `BOLI_EVON_URL` is unset. |

## Quick start

Needs [uv](https://docs.astral.sh/uv/) and `ffprobe` (from ffmpeg) for non-WAV audio checks.

```bash
git clone https://github.com/sameer261h/boli-zero && cd boli-zero
uv sync
cp .env.example .env          # add your own keys; never commit this file
uv run pytest                 # 161 tests, no network and no keys needed
uv run uvicorn boli_zero.app:app --port 8000     # http://127.0.0.1:8000
```

Without keys the pages load and say what is missing; nothing is faked.

## Configuration

Set in `.env` (see `.env.example`). Spend is capped by design: requests stop before a cap would be passed.

| Variable | Purpose |
|---|---|
| `GNANI_API_KEY`, `GNANI_BASE_URL`, `GNANI_AUTH_HEADER` | Gnani speech API access, from the Gnani console and docs. |
| `BOLI_EVON_URL` | A self-hosted Evon endpoint (see `experiments/2026-10-05-evon-pipeline/`). Preferred reply provider when set. |
| `BOLI_EVON_MODEL` | Model path sent in the Evon request; defaults to the official checkpoint's HF path. |
| `ANTHROPIC_API_KEY` | Fallback replies with Claude, used only when `BOLI_EVON_URL` is unset. Without either, the page shows what it heard and cannot answer. |
| `BOLI_REPLY_MODEL` | Claude reply model; only models with a known price are accepted. |
| `BOLI_CLAUDE_BUDGET_USD`, `BOLI_CLAUDE_MAX_REQUESTS` | Hard caps on estimated reply spend and request count. |
| `BOLI_BUDGET_INR`, `BOLI_LEDGER` | Estimated-spend cap and ledger file for Gnani calls. |
| `BOLI_VOICE` | A documented Timbre voice name. |
| `BOLI_CACHE_DIR` | Where API responses are cached (default `.cache/api`). |

Hosted-only: `DATABASE_URL`, `BOLI_INVITE_PASSWORD`, `BOLI_OPEN_ACCESS`, `BOLI_PRIOR_GNANI_SPEND_INR`
(see `deploy/` and `src/boli_zero/hosted.py`).

## What testing against Gnani showed (2026-10-02)

Our own observations; they differ from the docs in two places and may have changed.
- Bhojpuri is not an offered Prisma language, so the nearest offered code is used and the interface says so.
- Clips over 30 s were rejected with HTTP 400 although the docs say 60 s.
- Two requests in quick succession returned HTTP 429.
- The only documented ways to steer Prisma are `bias_list` (up to 100 words) and `substitution_map` (up to 10 rules).
  No fine-tuning is documented.

## What testing Evon showed (2026-10-05)

Full writeup in `experiments/2026-10-05-evon-pipeline/`. The short version:
- Evon's raw output (no system prompt, as this project requires) reliably ran 1,100–6,200+ characters on
  open-ended statements, because it treats any non-question input as something to reason through at length. This
  broke Timbre about half the time — Timbre has an undocumented length cutoff somewhere between ~1,500–2,800
  characters. The fix: force `INTENT: / DETAILS: / REPLY:` structured output, send only the `REPLY:` line to
  Timbre. 10/10 success once in place.
- A hand-written Bhojpuri glossary given to Evon alongside the business task added no measurable benefit over the
  task prompt alone, on the statements tested. The structured-output format did the actual work.
- Corpus-derived dialect markers (real word-frequency comparison, not guessing) separate well-resourced, distant
  dialects (Garhwali) from Hindi, but do not reliably separate closely related dialects (Bhojpuri/Magahi/
  Bajjika/Angika/Maithili) from each other at the single-utterance level — held-out accuracy for that cluster was
  0–34%. This pushed the design toward marker-based *grounding* (surface only the specific words that matched,
  with their meanings) rather than a dialect *classifier*.

## How a turn works

1. The browser records 16 kHz mono WAV and the server sends it to Prisma.
2. Claude replies in Bhojpuri. Instructions travel in the `system` field and the recognised words only as user
   messages; context is the last six exchanges; replies are capped at 120 tokens. If the words are nonsense or
   another language or variety, the reply says it did not understand, and that turn is kept out of later context.
3. Timbre speaks the reply. The microphone is disabled while it plays.

Each step is idempotent and cached, so a retry resumes at the failed step with no duplicate turn or charge.

## Experiment tooling

```bash
uv run python -m boli_zero.ingest data/raw/pairs.csv --anchor-language hi --target-language bho \
    --source "<where it came from>" --license "<licence or consent basis>"   # source and licence are mandatory
uv run python -m boli_zero.split --seed 42                                   # deterministic, grouped by anchor sentence
uv run python -m boli_zero.experiment --name dry --dry-run                   # builds prompts, calls nothing
uv run python -m boli_zero.evaluate experiments/<run>                        # chrF, exact match, copy rate, baseline
uv run python -m boli_zero.ratings export experiments/<run> --a 0 --b 25 -n 50 --out outputs/ratings
```

Design choices that matter:
- Splits group by Hindi sentence, so a held-out sentence never has a sibling rendering in the teaching set.
- Few-shot sets are nested (the 10-shot examples are inside the 25-shot set), so differences come from more
  examples, not different ones.
- Every API call is cached by a hash of the request and audio bytes; credentials are never stored.
- `evaluate` also scores "return the Hindi unchanged". A system that cannot beat that has learned nothing.

Data contracts are in [docs/CONTRACTS.md](docs/CONTRACTS.md) (design notes, proposal v0).

## Privacy and data

- Do not ingest data whose licence you cannot name. `data/raw`, `data/processed`, `data/splits` and `outputs`
  are git-ignored on purpose, and no recordings or datasets are in this repository.
- The challenge rules forbid real phone numbers, account numbers, Aadhaar, PAN and recorded calls. Use open data,
  scripts, or recordings made with explicit consent.
- In the private hosted trial, recordings and replies are kept for 30 days so the maker can check accuracy, and a
  speaker can separately opt in to contribute a recording with a transcript correction. Contributions are
  withdrawable with a private receipt, are not used for training, and are not shared or used for voice cloning.

## Known limits

- No accuracy has been measured. Anything on the pages is proposal-only until native speakers rate it.
- chrF here approximates sacreBLEU; use one implementation for every comparison and swap in `sacrebleu` before
  publishing numbers. It scores overlap with one translator's phrasing, not naturalness.
- Rating aggregation gives counts only (no agreement statistic or confidence interval).
- The hosted trial serialises requests and is not built for more than a handful of testers.

## Layout

```
src/boli_zero/   app, conversation, service, clients (Gnani), routing, ledger, contributions, hosted,
                 ingest, split, experiment, evaluate, ratings
web/             index.html (lab, /lab) and talk.html (conversation, /)
deploy/          Vercel + Postgres setup and owner-only review/export scripts
tests/           161 tests
docs/            design notes
```

## License

[MIT](LICENSE).
