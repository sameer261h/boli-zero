# Prompt (for Opus, Astra, or any capable model): can Evon recognize "this isn't Hindi" and the actual dialect, using our fingerprint signatures?

Paste everything below into a fresh session. It has no access to prior conversation, so it's self-contained.
This is a **design task**, not an implementation task, and it has two required deliverables (see "What to
produce" at the end) — a best-case technical design, and a plain-English translation of that design for a
non-technical reader. Don't skip the second one.

## Repository access — read the real data yourself, don't just trust this summary

Everything referenced is committed at `https://github.com/sameer261h/boli-zero` (branch `main`). Clone it before
starting. Key files, in order of relevance:

- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/regional_fingerprint_audit/audit_results.json`
  — the real, per-dialect **discriminative lexical markers** (log-odds z-scores — which words are genuinely
  overrepresented in a dialect's speech vs. everyone else's, e.g. Bhojpuri "बा"/z=43.0, "एगो"/z=15.1), plus
  discriminative word-ending suffixes (morphology proxy), classifier confusion matrices, and calibration data.
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/analysis/per_dialect_results.json` — per-dialect
  substitution/deletion/insertion patterns (what Prisma actually does to dialectal words).
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/regional_fingerprint_audit/needs_fixing_wrong_substitutions.csv`
  — 5,948 real (dialect, human_word, Prisma_word) pairs where Prisma's mistranscription actually changes
  meaning, with Roman transliteration for readability.
- `docs/2026-10-05-evon-pipeline/09-v1-regional-speech-detector.md` — the existing calibrated detector and its
  4-level confidence hierarchy (exact variety → family → generic regional-Hindi → standard Hindi default). Any
  proposal here should build on this, not duplicate or contradict it.
- `docs/2026-10-05-evon-pipeline/12-safe-vs-ambiguous-classification-design.md` and
  `docs/2026-10-05-evon-pipeline/14-phonetic-filter-wrong-vs-unsure.md` — which Prisma transformations are safe
  to silently ignore vs. which are genuinely consequential (relevant to what evidence is even worth surfacing).
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/<Dialect>.jsonl` — the raw ~25,000 paired
  human/Prisma transcripts, if you want real examples to test your proposed logic against.
- `src/boli_zero/conversation.py` — the real pipeline. `ConversationEngine.reply()` currently sends Evon
  *only* the raw Prisma transcript (`EvonReply.reply_with_usage(context, turn.recognized_text)`) — no detector
  output, no markers, nothing from the fingerprint work is wired in anywhere today. This is the actual
  integration point your design has to plug into.

## The question

Prisma (Hindi-only ASR) transcribes everything as if it were standard Hindi, so a dialectal speaker's words get
silently flattened into Hindi spelling even when the grammar/vocabulary used isn't actually Hindi. Using the
dialect "fingerprint" data already collected (the discriminative markers above — real, data-derived, not
invented), we want Evon (the downstream LLM, which has no system prompt by design — see `EvonReply`'s docstring
for why) to be able to:

**(a) Recognize that the input is NOT standard Hindi** — even though Prisma transcribed it as if it were.

**(b) Identify the actual language/dialect the speaker intended**, with genuine confidence, not a guess.

## The explicit design constraint from the project owner (read carefully, this rules out the obvious approaches)

Two approaches were already proposed and explicitly rejected as the wrong design:

1. **Just telling Evon the label** ("the speaker is using Bhojpuri") — rejected as "obviously dumb," because it
   hands Evon a conclusion as trivia with nothing to verify it against or reason from.
2. **A vague hedge** ("this transcript may contain mistranscriptions, read charitably") — also rejected, because
   it doesn't give Evon anything *concrete* to reason with, and doesn't let Evon do real work.

**What's wanted instead**: Evon should reach its own conclusion by reasoning over *concrete linguistic evidence*
— specific marker words/patterns actually found in this transcript, surfaced raw (not pre-interpreted) — using
its own knowledge of Hindi and regional grammar/phonetics to do the actual recognition work, the way a human
Hindi speaker with some regional exposure would read a sentence and notice "that word doesn't belong in standard
Hindi, this looks like a Bhojpuri construction." Our job is to surface good evidence, not hand down a verdict.

Design concretely around this constraint. If you think the constraint itself is wrong (e.g., if there's a strong
reason the evidence-based approach won't work as well as a direct label), say so explicitly and argue for an
alternative — don't silently ignore the constraint, but don't follow it blindly either if the data doesn't
support it.

## What "best case" needs to grapple with (use the real data to check these, don't just theorize)

1. **Which markers to surface, and how many.** The discriminative-marker lists in `audit_results.json` go many
   entries deep per dialect with a wide range of statistical strength (z-scores from the 40s down to single
   digits). Surfacing every marker that technically matches is not the same as surfacing good evidence — test
   against real transcripts whether a small number of strong markers works better than a long list of weak ones.
2. **Dialects that are barely different from Hindi.** Not every one of the 19 varieties has strong, unambiguous
   markers — some (see the detector doc) are close enough to standard Hindi that "this is not Hindi" may not be
   a meaningful claim at all for them. Your design needs to handle this honestly, not force every transcript
   into a "yes it's a dialect" framing.
3. **Markers that are themselves ambiguous.** Today's work found specific words (documented in the needs_fixing
   CSV and the Bhojpuri analysis) that genuinely split between multiple different meanings/sources depending on
   context — surfacing these as if they were unambiguous evidence would be actively misleading. Decide how
   evidence selection should handle this.
4. **Validate against real examples.** Pull several real transcripts from the jsonl files — a clear case, a
   marginal case, and a case from a dialect with weak detector confidence — and walk through exactly what
   evidence your design would surface and what you'd expect/hope Evon to conclude from it. Show your work, don't
   just assert it would work.

## What to produce

Two required deliverables, written to a **new file**: `docs/2026-10-05-evon-pipeline/18-evon-non-hindi-recognition-design.md`
(don't edit this prompt file). Commit and push it when done.

1. **Best-case technical logic**: the concrete design — what evidence gets extracted from a transcript, how it's
   selected/filtered, exactly what gets added to Evon's prompt (today's template has no system prompt, single
   user-turn only — work within or explicitly propose changing that), and how confidence/abstention is handled
   (tie back to the existing 4-level hierarchy in doc 09 rather than inventing a parallel one). Pseudocode where
   it clarifies the mechanism. Validate it against the real examples per point 4 above.
2. **"Dumbdumb" translation**: immediately after, a short, plain-English section — no jargon, no architecture
   diagrams, explain it the way you'd explain it to a smart person who doesn't know NLP — that says, in simple
   terms, what the system actually does and why it's expected to work.

Do not write implementation code (pseudocode for mechanism clarity is fine). Do not call any Evon/Prisma API.
