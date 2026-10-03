# boli-zero

Experimental system for adapting a standard Indian-language AI stack (Gnani Prisma, Timbre, Evon) to
regional languages it does not support. First target: Hindi to Bhojpuri.

**Status: scaffold.** No Gnani endpoint, credential, dataset, score or sample result is included. The three
Gnani clients are interfaces with the HTTP layer left as TODO until access is confirmed. Everything else
(data intake, deterministic splits, caching, experiment runner, evaluation, rating sheets, demo app) works
and is tested without any Gnani access.

## Architecture

```
 CSV / JSONL pairs
        |  boli_zero.ingest        validate + normalise -> data/processed/*.jsonl
        v
   canonical records
        |  boli_zero.split         deterministic, leak-proof -> data/splits/{train,validation,test}.jsonl + manifest.json
        v
 train (teaching pool) --------+------------------- validation / test (held out, never shown to a model)
                               |                                  |
                   boli_zero.experiment  -- 0/10/25/50/100-shot --> experiments/<run>/predictions.jsonl
                               |                 (or --task rules -> rules_<k>shot.json)
                               v
                         EvonClient  -- every call goes through the cache --> .cache/api/
                               |
                         (TODO) Gnani Evon
                               
 boli_zero.evaluate  <run>   chrF / exact match / copy rate + "do nothing" baseline -> metrics.json
 boli_zero.ratings           blinded A/B sheets for native speakers -> aggregate
 boli_zero.app (FastAPI)     status, dataset, experiments, try-a-rewrite page at /
 PrismaClient, TimbreClient  same cache + TODO transport (not used by the experiment runner yet)
```

Why these choices:
- **Splits group by anchor sentence.** If two speakers render the same Hindi sentence, both renderings stay in
  one split. Otherwise a held-out sentence would have its answer sitting in the few-shot examples.
- **Shots are nested.** One seeded ordering of train; 10-shot is the first 10, 25-shot the first 25, and so on.
  Differences between conditions come from more examples, not different ones.
- **Every API call is cached** by a hash of service, operation, params and the sha256 of any audio bytes.
  Identical text or audio is never sent twice, credentials are never stored, and cached answers replay with no
  credentials at all.
- **Identity baseline.** `evaluate` scores "return the Hindi unchanged" too. A condition that does not beat it
  has learned nothing.

## Setup

```bash
cd boli-zero
uv sync
cp .env.example .env      # leave blank until access is confirmed
uv run pytest             # 38 tests, no network, no Gnani access needed
```

## Commands

1. **Ingest** pairs (`--source` and `--license` are mandatory; a CSV template is at `data/raw/template.csv`):
   ```bash
   uv run python -m boli_zero.ingest data/raw/pairs.csv --anchor-language hi --target-language bho \
       --source "<where it came from>" --license "<licence or consent basis>"
   ```
   Column names are configurable (`--anchor-col`, `--target-col`, `--id-col`, `--audio-col`, `--speaker-col`).
   Output: `data/processed/pairs.jsonl` plus a report of invalid, duplicate and missing-audio rows.

2. **Split** (deterministic: same data + seed = byte-identical files):
   ```bash
   uv run python -m boli_zero.split --seed 42 --train 0.8 --validation 0.1 --test 0.1
   ```
   Use `--group-by speaker_id` to hold out whole speakers. Output: `data/splits/`.

3. **Experiment, dry run** (builds every prompt, calls nothing):
   ```bash
   uv run python -m boli_zero.experiment --name first-dry-run --dry-run
   ```
   Conditions with more shots than the train split holds are skipped and recorded, not faked.

4. **Experiment, real** (needs Evon wired up, see below):
   ```bash
   uv run python -m boli_zero.experiment --name first-run                  # translate, validation split
   uv run python -m boli_zero.experiment --name rules-run --task rules     # learned-rule induction
   ```
   Use `--eval-split test` once, for final numbers only.

5. **Evaluate** a finished translate run:
   ```bash
   uv run python -m boli_zero.evaluate experiments/first-run
   ```

6. **Native-speaker ratings** (pairwise, blinded, e.g. 0-shot vs 25-shot, or vs the human reference):
   ```bash
   uv run python -m boli_zero.ratings export experiments/first-run --a 0 --b 25 -n 50 --out outputs/ratings
   # each rater fills the `choice` column of their own copy: 1, 2, tie or both_bad
   uv run python -m boli_zero.ratings aggregate outputs/ratings/key.json outputs/ratings/rater_*.csv
   ```

7. **Demo app**:
   ```bash
   uv run uvicorn boli_zero.app:app --reload     # open http://127.0.0.1:8000
   ```
   Routes that need Gnani return `503` with the TODO text until the HTTP layer exists.

## Connecting the real APIs

Prisma (speech to text) is wired to the documented REST endpoint and has been run live on five clips; see the
trial report in the audio audit folder. Timbre and Evon are not wired. Take details from the Gnani docs or console.

Observed 2026-10-02 (differs from the docs in two places): Bhojpuri is not an offered language (use the nearest
offered code and say so); clips over 30 s are rejected with HTTP 400 although the docs say 60 s; two requests
in quick succession triggered HTTP 429, so space calls about 20 s apart. Documented tuning levers for Prisma are
`bias_list` (up to 100 words) and `substitution_map` (up to 10 rules); there is no documented fine-tuning.

- [x] Prisma: key in `.env`, `PrismaClient` calls `POST /stt/v3`.
- [ ] Fill `.env`: key, base URL(s), auth header name.
- [ ] Decide how Evon is reached: Gnani-hosted endpoint, or self-run from the open weights.
      A self-run runtime can be passed as `EvonClient(transport=...)` without changing any other code.
- [ ] Implement `_send` in `TimbreClient` and `EvonClient` (`src/boli_zero/clients.py`): endpoint, auth, request
      encoding, and map the vendor response to the normalised shape in that file's docstring.
      Timbre's documented route is `POST /api/v1/tts/inference` (no Bhojpuri language code); Evon has no hosted endpoint.
- [ ] Add the model name/version to the request params once known, so a model upgrade cannot be served from a
      stale cache entry.
- [ ] Run one tiny experiment (`--limit 3 --conditions 0`) and inspect `predictions.jsonl` by hand first.

## Language labelling and routing (provisional)

`boli_zero.routing` proposes a variety for a recording and picks the Prisma mode it is sent in. It is a layer around
Gnani, not a new Prisma language and not validated language identification (Gnani documents none for audio).

- Labels: `hindi`, `bhojpuri_candidate`, `bundeli_candidate`, `related_variety_uncertain`, `other_or_insufficient`,
  and `<name>_candidate` only when evidence is supplied. A clip can carry several (mixed lessons).
- Shown to the user for an unsupported variety: "Likely Bhojpuri; recognized using Hindi mode." The label is never
  changed to Hindi; the submitted language code, raw output and any boosted output are separate fields.
- Evidence is the raw Prisma output checked against a short, unreviewed marker table, plus a hedge flag from saved
  audio-model assessments. Filenames, script and resemblance to Hindi are not evidence. No numerical confidence.
- Bundeli exists as a candidate but is unverified: the table never produces it.
- Demonstration on the five saved trial clips: `outputs/language_routing_trial/` in the audio audit folder.

```bash
uv run pytest tests/test_routing.py
```

## Recognition page (local frontend)

`web/lab.html` (served at `/lab`) is the page; `app.py` serves it. Pick a sample recording or upload your own (WAV, MP3, OGG, FLAC, AAC or
M4A, 10 MB and 30 s at most), run Prisma, and see the exact returned text, the proposed variety with its evidence and, where
both exist, baseline versus boosted text. Everything is proposal-only: no training happens and nothing is called verified.

```bash
BOLI_CATALOG=<catalog.json> BOLI_SAMPLES_ROOT=<folder holding usable/ and non_usable/> \
BOLI_LEDGER=<spend_ledger.jsonl> BOLI_BUDGET_INR=25 \
uv run uvicorn boli_zero.app:app --host 127.0.0.1 --port 8010
```

Optional: `BOLI_BOOST_CONFIG` (frozen boost settings enable the boosted mode) and `BOLI_DEV_VOCAB` (extra, unverified word forms
for the experimental label view). The key stays in `.env` on the server; it is never sent to the browser.

- Samples are named only by an opaque id from the catalog; the audio route serves nothing else and never builds a path from a request.
- Uploads are checked on the server (format by content, length with ffprobe, size) before anything is sent. Recordings of 30 s
  or more are refused, not cut: Prisma rejected longer audio when tested, although its docs say 60 s.
- Each live request is capped by an estimated-spend ledger, only one request per audio runs at a time, and every result is cached,
  so a repeat is free. The page says whether a result is a live call, a saved replay, or (never in normal use) a mock.
- Failure states shown with their own messages: bad file, over length, no credentials, rejected key, rate limit (with a retry
  countdown), Gnani processing error, unreachable, spend cap reached, empty result.
- `catalog.py` builds deterministic development/validation/test partitions by group; the sample recordings have unknown licence,
  so keep them off any shared host.

## Spoken conversation (main page)

`web/index.html` is a conversation screen: tap the microphone, speak, and the answer is spoken back; earlier turns are kept
as bounded context. The recognition lab described above lives at `/lab`. Each turn runs three idempotent steps, so a retry
resumes at the failed step without a duplicate turn or charge:

1. Recognition: the browser records 16 kHz mono WAV and the server sends it to Prisma in Hindi mode (a workaround: Prisma has no Bhojpuri).
2. Reply: Claude through the Anthropic Messages API (Gnani documents no text-reply service and Evon has no hosted endpoint). It is used
   only if `ANTHROPIC_API_KEY` is in the local `.env`; otherwise the page shows what it heard and says it cannot answer. The
   instructions travel in the `system` field and the recognized words only as user messages; context is the last six exchanges;
   replies are capped at 120 tokens; a dollar cap and a request cap (`BOLI_CLAUDE_*`) stop requests before they are exceeded.
3. Speech: Timbre (documented REST endpoint) with a Hindi voice reading the reply. Pronunciation of Bhojpuri by a Hindi voice is unverified.

The microphone is disabled while the assistant speaks, so it cannot record its own voice. Ending a conversation discards any step
still running for it.

## Data policy

- Every record carries `source` and `license`. Do not ingest data whose licence you cannot name.
- The Gnani challenge rules say not to use real phone numbers, account numbers, Aadhaar, PAN or recorded calls.
  Use open datasets, scripts, or recordings made with explicit consent.
- `data/raw`, `data/processed`, `data/splits` and `outputs` are git-ignored on purpose.

## Known limits

- chrF is a close approximation, not sacreBLEU. Use the same code for every comparison; swap in sacrebleu before
  publishing numbers.
- Reference text scores overlap with one translator's phrasing, not naturalness. Final claims need native raters.
- Rating aggregation gives counts only (no agreement statistic or confidence interval yet).
- Rule induction trusts model self-reported confidence; it is not calibrated.
- Voice cloning, audio features and fine-tuning are out of scope for this scaffold.

## Layout

```
src/boli_zero/  config  schema  cache  clients  ingest  split  experiment  evaluate  ratings  app
web/index.html  demo page          tests/  38 tests          docs/CONTRACTS.md  interface proposal
data/{raw,processed,splits}  experiments/  outputs/
```
