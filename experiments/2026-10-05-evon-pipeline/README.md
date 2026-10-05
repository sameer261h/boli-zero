# 2026-10-05: wiring Evon and testing dialect-aware grounding

What this session actually did, in order. Full narrative and evidence in `docs/2026-10-05-evon-pipeline/`; this folder
holds the scripts and the clean (no embedded audio, no gated-dataset re-hosting) data artifacts.

## 1. Deployed Evon for real

`scripts/evon_serve.py` — the official `gnani/gnani-evon-v3.3-30B-A3B` BF16 checkpoint, served via vLLM on a single
Modal A100 80GB. OpenAI-compatible `/v1/chat/completions`, unauthenticated, cold-boots after ~1h idle (~3-4 min,
model load + vLLM graph capture + Mamba kernel warmup). This is the endpoint `BOLI_EVON_URL` in `.env.example`
should point at — see `src/boli_zero/conversation.py:EvonReply` for the actual client, now wired into the app.

Real bugs hit and fixed along the way (all in the image/deploy config, not in this folder, but worth knowing about
if you redeploy): missing `nvcc` in the container broke Mamba kernel JIT compilation; default host memory was too
small to buffer the 63GB checkpoint during load; `max_containers` wasn't set, so retried client requests spun up
duplicate GPU containers (10 at once, once) — see `docs/2026-10-05-evon-pipeline/03-initial-codex-handoff.md`.

## 2. Found Evon's real failure mode, and the fix

Raw Evon output (no system prompt, which this project requires) ranged 1,100–6,200+ characters on open-ended
statements, because it treats any non-question input as a puzzle to reason through at length. This reliably broke
Timbre (undocumented length cutoff somewhere between ~1,500–2,800 characters). The fix that actually worked:
force a structured `INTENT: / DETAILS: / REPLY:` output format and send **only** the `REPLY:` line to Timbre.
10/10 Timbre success once this was in place, vs roughly half failing before. See `01-ambiguity-and-mechanisms-report.md`.

## 3. Tested whether a small Bhojpuri glossary actually helps ("the Boli hypothesis")

Not demonstrated, on the data tested. `scripts/experiment2_evon.py` ran 5 EMI-collections statements through
Evon with and without a hand-written Bhojpuri word-glossary; both conditions scored identically (5/5 correct
intent, 10/10 Timbre success). The structured-task format did the work; the glossary added nothing measurable on
these particular statements, which turned out to be easy enough that the no-glossary condition never failed. See
`02-boli-context-vs-raw-report.md`.

## 4. Built markers from real corpus evidence, not hand-picking

`scripts/derive_markers_from_corpus.py` compares real word frequencies between dialect transcripts and Hindi
transcripts (from the gated `ARTPARK-IISc/Vaani-transcription-part` dataset — requires separate HF access
approval, not re-hosted here) to find words that are genuinely dialect-distinctive, not guessed. Extended to 19
dialects in `derive_markers_multi.py`, then to 14 with proper rigor in `derive_markers_v2.py`:
cross-dialect weighting (a marker shared with 2+ other dialects gets downweighted) and a held-out 80/20 split
(markers derived from 80%, accuracy measured on the untouched 20% — the earlier self-validated numbers were
optimistic, exactly as you'd expect).

**Honest result: single-utterance dialect classification does not work well with this method.** Held-out accuracy
collapsed to 0–16% for most of the closely-related Bihari-family dialects (Magahi, Bajjika, Angika, Maithili vs
Bhojpuri — they share too much vocabulary to separate lexically). Only linguistically distant dialects held up
(Garhwali 72%, the strongest result). See `data/markers_v2.json` for the full confusion matrices.

## 5. Reframed: grounding, not classification

Following that result, the design pivoted (documented in `04-adversarial-review-handoff.md` and
`05-multi-mechanism-design-handoff.md`): don't force a single dialect label. Detect *which specific marker words*
appear in a transcript, surface only those words' meanings to Evon as grounding, and never claim a dialect
identity. `scripts/boli_memory.py` is the first cut at this — a small labeled example bank (hard/adversarial
statements: temporal ambiguity, subject ambiguity, non-commitment, partial payment, already-paid, wrong-borrower,
hardship) plus a disjoint held-out test set, intended for retrieval-based few-shot grounding rather than a
glossary dump. **Not yet run as a scored experiment** — the next real test is Base-Evon vs Evon+retrieved-examples
on business-decision correctness, which is where the actual evidence for or against Boli will come from.

## 6. The Prisma fingerprint, tested at scale — and it's real, with caveats

Scaled the regional-fingerprint question from a handful of hand-picked examples to 24,986 real audio clips across
19 dialects (`scripts/prisma_fingerprint_pull.py`, pulling from `Vaani-transcription-part`, running each clip
through the actual Prisma API), then diffed human transcript against Prisma transcript word-by-word
(`scripts/analyze_prisma_fingerprint.py`). Full writeup: `docs/2026-10-05-evon-pipeline/06-prisma-fingerprint-dialect-transformation-analysis.md`.

**Headline result: yes, there's a real, measurable, dialect-specific fingerprint** — specific dialect marker words
(verified against the earlier `data/markers_v2.json` corpus-derived markers) get transformed in consistent,
high-volume, dialect-specific ways. Rajasthani/Marwari progressive-aspect forms (`रियो`/`रेहो`/`रहियो` →
`रही`/`रहे`) are the cleanest example: dozens to 65 occurrences of the same normalization. But it's not clean
"dialect word → Hindi equivalent" translation throughout — dialect-specific deictics (Garhwali `यख`, Rajasthani
`अठे`, Maithili `एता`, all meaning roughly "here") are mostly **deleted outright or misheard as unrelated words**,
and some content words produce outright multi-word hallucination. Divergence rate also tracks linguistic distance
from Hindi cleanly (Khariboli lowest, Garhwali/Surjapuri highest) — consistent with, and a more tractable signal
than, the earlier failed single-utterance classification attempt in `markers_v2.json`.

Two real data-quality bugs were caught and fixed during this analysis, flagged explicitly in the full report
rather than silently corrected: Unicode NFC normalization (precomposed vs. decomposed Devanagari nukta forms were
being counted as false "substitutions"), and a `difflib` alignment artifact on repeated words within a sentence.

## What's honestly unverified

- `data/bhojpuri_glosses_raw.txt`: Evon-generated Hindi glosses for the top corpus-derived markers. **Several are
  wrong or hallucinated** (e.g. `लोकत = लोकतांत्रिक` ["democratic"?!], `जॉन = जॉन` [unchanged, misread as the
  English name John]). Do not use this file as a trusted grounding resource without a native-speaker pass.
- Every Evon output in this folder came from typed Bhojpuri text standing in for Prisma's output, not real audio
  run through Prisma, except where a script explicitly pulls from `Vaani-transcription-part` (the marker
  derivation only, not the Evon-reply experiments). Flagged throughout the docs; not quietly assumed away.
