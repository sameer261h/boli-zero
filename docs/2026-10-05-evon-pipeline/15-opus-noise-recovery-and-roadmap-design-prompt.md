# Prompt for a local Opus Claude Code session: noise/garbled-speech recovery + remaining roadmap design

Paste everything below into a fresh local session. It has no access to today's cloud session, so it's fully
self-contained. This is a **research and design task, not an implementation task** — think deeply, ground
proposals in real published technique where it exists, and be explicit about what's established research vs.
your own reasoning. No code needs to be written; a clear design document is the deliverable.

## Repository access — read the real data, don't just trust this summary

Everything referenced below is committed and pushed to `https://github.com/sameer261h/boli-zero` (branch
`main`). Clone it (or `cd` into it if already local) before starting. The summary below is accurate but
compressed — if anything matters for your design, go read the actual source rather than relying on my
paraphrase of it. Key files, in rough order of relevance to this task:

- `docs/2026-10-05-evon-pipeline/06-prisma-fingerprint-dialect-transformation-analysis.md` — the original
  human-vs-Prisma transformation pattern analysis (item 2 below)
- `docs/2026-10-05-evon-pipeline/09-v1-regional-speech-detector.md` — the frozen detector, 4-level hierarchy,
  calibration, and the full per-dialect confidence map (item 1 below)
- `docs/2026-10-05-evon-pipeline/13-bhojpuri-prisma-reversibility-test.md` — the reversibility test that came
  back negative, with the exact methodology and numbers (item 3 below)
- `docs/2026-10-05-evon-pipeline/14-phonetic-filter-wrong-vs-unsure.md` — the 19-dialect phonetic-similarity
  classification, 67.4%/32.6% split and per-dialect breakdown (item 2 below)
- `docs/2026-10-05-evon-pipeline/12-safe-vs-ambiguous-classification-design.md` — a parallel design doc on
  which Prisma transformations are safe to auto-correct vs. need reasoning, including a worked alignment-method
  comparison that may be directly useful for Part A
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/analysis/per_dialect_results.json` — the raw
  per-dialect substitution/deletion/insertion counts (the actual confusion data mentioned in Part A.2)
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/<Dialect>.jsonl` — the raw ~25,000 paired
  human/Prisma transcripts themselves, if you want to pull your own examples or compute something new
- `experiments/2026-10-05-evon-pipeline/scripts/` — all analysis scripts referenced above, reusable if you want
  to extend any of this analysis rather than starting from scratch
- `src/boli_zero/clients.py` — confirms the exact Prisma and Timbre API surfaces (the hard constraints in
  items 5 and 6 below are verified against this file, not assumed)

## Project context

"Boli" is a voice-AI pipeline: Prisma (a Hindi-only ASR system) transcribes speakers of 19 Indian regional
dialects, then an LLM ("Evon") reasons over the transcript, then a TTS engine ("Timbre") speaks the reply.
Prisma has no dialect-aware mode — it transcribes everything as if it were standard Hindi, which means dialectal
speech gets systematically mis-transcribed in patterned, non-random ways.

## What's already been established today (treat as given, don't re-derive)

1. **A regional-variety detector exists** (word+char TF-IDF + logistic regression, calibrated), with a 4-level
   hierarchy: exact variety → broader family/regional profile → generic "regional Hindi" → standard Hindi
   default, gated by calibrated confidence thresholds. Most dialects land in the "family" or "generic" tiers, not
   exact identification — this was a deliberate, evidence-based design choice, not a shortfall to fix.
2. **A rigorous audit of ~25,000 real audio clips' human-vs-Prisma transcript pairs** found: 67.4% of all
   word-level differences between what was said and what Prisma transcribed are purely phonetic/spelling
   variants (harmless); of the remainder, about three-quarters are genuine substitutions, split further into
   ~22% that don't change meaning (e.g. a dialectal postposition shortening normalized to its standard form) and
   the rest (~19% of all differences) that do change meaning in ways that could mislead a downstream reader.
3. **A specific reversibility test** (can Prisma's known error patterns be auto-corrected by a simple lookup
   table?) came back negative for Bhojpuri: zero safe rules found, because the metric that matters — "when
   Prisma outputs word Y, how often was the real word actually X" (reverse precision) — is almost always too low,
   since Prisma's output vocabulary is dominated by common "attractor" words that are frequently correct on
   their own merits regardless of dialect.
4. **A specific, interesting finding**: two Bhojpuri dialectal words ("ओ" and "एगो", short/colloquial forms)
   were found to be genuinely ambiguous at the word-pair level — each one splits roughly evenly between a
   harmless reading and a meaning-changing one (e.g. "एगो" sometimes means "one/a" — harmless when normalized —
   and sometimes means "that" — a real meaning change), with no way to tell which from the word alone.
5. **Hard constraint discovered**: Prisma's real API response contains ONLY `{success, request_id, transcript,
   model, processing_time, end_to_end_latency}` — no confidence score, no N-best alternatives, no word timing,
   no diarization, no signal-quality estimate. Any proposal must work with transcript text alone (plus whatever
   raw audio access can independently be added later), not assume ASR-internal signals that don't exist in this
   integration.
6. **Timbre (the TTS) has no prosody/emotion/accent API parameter at all.** Any proposal involving Timbre's
   output must work by changing what TEXT is sent to it, not by calling an API feature that doesn't exist.

## What you're being asked to design

### Part A — noise/garbled-speech recovery: what does the state of the art actually do, and what's applicable here

The core unresolved question from today's work: when Prisma produces a transcript with a word that's likely
wrong (either because it's a known unreliable pattern, or because something about the context suggests an error),
is there a principled way to recover more of the original intended meaning than the raw garbled text gives —
given the hard constraint above (no ASR-internal signals, transcript text only, 25,000 paired examples already
available for grounding/validation)?

Research and report on, with real citations where they exist (arXiv, ACL anthology, etc. — flag clearly if
something is your own synthesis rather than an established result):

1. **ASR error correction via language model rescoring/post-editing** — the established literature on using a
   secondary LM to "clean up" ASR output (e.g., N-best rescoring, LM-based post-correction, "Whispering"-style
   approaches, GenSEC-style shared tasks). What's the actual state of the art, and does any of it transfer to a
   setting with only 1-best transcript text (no N-best list, no lattice) available?
2. **Noisy-channel models** — the classical (1980s ASR, still foundational) technique of combining a channel
   model P(observed|intended) with a language-model prior P(intended), applied to error correction. Is this
   still used/relevant, and how would you combine it with the dialect-specific confusion statistics already
   collected (today's work computed real P(Prisma output | human word) tables per dialect — these could serve
   as an empirical channel model)?
3. **Context-aware correction without a full classifier** — given the finding that word-pair-level rules don't
   work (reverse precision too low), what techniques exist for using surrounding-sentence context to disambiguate
   a likely-wrong word, that stop short of "just ask an LLM to guess" (which this project has explicitly already
   tried and rejected as methodologically weak — it only measures the LLM's prior world-knowledge, not whether
   the dialect-specific data actually helps)? Think about: constrained decoding/reranking against a small
   candidate set (e.g., the top-k words historically observed as outcomes of a given Prisma output, generated
   from the already-collected confusion data), perplexity-based candidate scoring, or other approaches that use
   the LLM's judgment on a *narrowed* candidate set rather than open-ended guessing.
4. **What raw-audio-level techniques exist** that this project doesn't currently have access to but could add
   later (word-level confidence estimation, phoneme-level confusion networks, self-supervised speech
   representations like wav2vec2/HuBERT for acoustic similarity) — and for each, estimate honestly whether it
   would plausibly outperform the text-only approaches above enough to justify the much higher engineering cost
   of adding raw audio access to this pipeline (today's team is explicitly cost/engineering-effort-conscious —
   multiple pieces of work today were deliberately killed or scaled down mid-run when the cost didn't justify the
   incremental value, so don't recommend something expensive without being explicit about what it buys over the
   cheaper alternative).
5. **A concrete recommendation**: given everything above, what should Boli actually do about genuinely
   consequential, low-confidence Prisma errors (the ~19% "needs fixing" bucket from today's audit) — flag to
   Evon with a confidence hint and let it reason within context? Attempt constrained re-ranking against a small
   candidate set? Do nothing beyond what's already built (the detector + hierarchy)? Be willing to recommend
   "the cheap thing already built is probably good enough, here's why" if that's the honest conclusion.

### Part B — the remaining roadmap items (think and propose logic for each, this project's words verbatim)

The project owner described the "final shape" of this system as covering, across inbound and outbound call
contexts: (a) dialect detection [done, see above], (b) dialect processing in context — straightforward cases,
ambiguity handling [done, see the 4-level hierarchy above], and the noise/reconstruction question [Part A above],
(c) emotion detection [explicitly deprioritized by the project owner — data-collection/cataloguing only, not a
live system, don't design this in depth], (d) **"layering or enhancing Evon's actual response so the model gives
Timbre the response in a way that Timbre reads out the Hindi script but is now sounding like the dialect
instead"** — i.e., since Timbre can't control its own accent, can choosing specific Hindi spellings/word choices
in the TEXT sent to Timbre make standard Hindi text-to-speech sound more dialect-flavored when read aloud? Design
this concretely — what's actually buildable here, what are the risks (today's research found that mimicking a
user's dialect back at them is flagged in the literature as culturally sensitive/stereotyping-risk territory —
account for this), (f) **temperature modifications for different contexts** (non-business conversation, a happy
customer, a very aggrieved customer) — given temperature only affects Evon's text generation and never reaches
Timbre, design concretely how/when Evon's temperature should shift by context, and (g) **"empowering Timbre via
something we tell Evon to do" to add emotion to Timbre's output** — since Timbre has zero emotion API, what can
punctuation, phrasing, and word choice in the text Evon sends actually achieve, and is this a real, testable
lever or mostly wishful thinking? Be honest if the answer is "marginal at best."

## What to produce

A single, clearly structured design document (markdown). For Part A, prioritize depth and real citations over
breadth — better to properly ground 3 techniques than list 10 superficially. For Part B, a concrete proposal per
item (d, f, g), each with: what's buildable today with zero new infrastructure, what would need more
engineering, and an honest assessment of expected value vs. effort (this project has repeatedly killed
over-engineered work today in favor of cheaper alternatives that captured most of the value — match that
discipline). Do not write implementation code. Do not call any Evon/Prisma API (you don't have access to them
from a local session anyway) — this is a pure research and design task.
