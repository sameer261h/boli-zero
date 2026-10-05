# 06: The Prisma fingerprint, tested at scale — dialect-specific transcription transformation patterns

## What this is

Earlier work (`04-adversarial-review-handoff.md`, `05-multi-mechanism-design-handoff.md`) pivoted away from
single-utterance dialect classification (which failed — see `markers_v2.json`, 0–16% held-out accuracy for most
Bihari-family dialects) toward a different question: when Prisma (Gnani's hi-IN speech-to-text) transcribes real
dialectal speech, does it transform specific words in *consistent, recurring* ways — a "fingerprint" of how the
model mishears or normalizes each dialect — rather than failing randomly?

This report answers that question directly, using real data: 24,986 real audio clips across 19 dialects from the
gated `ARTPARK-IISc/Vaani-transcription-part` dataset (human reference transcript already present in the dataset),
each run through Prisma (`gnani-prisma-v2.5`, `hi-IN`, `verbatim`), then diffed word-by-word against the human
transcript. Pull script: `experiments/2026-10-05-evon-pipeline/scripts/prisma_fingerprint_pull.py`. Analysis
script: `experiments/2026-10-05-evon-pipeline/scripts/analyze_prisma_fingerprint.py`. Raw per-clip pairs:
`experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/<Dialect>.jsonl` (text only, no audio re-hosted, per
this project's data-handling policy). Aggregated results:
`experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/analysis/`.

**Short answer: yes, there is a real, measurable, dialect-specific fingerprint**, distinguishable from generic ASR
noise — specific dialectal words get mapped to specific substitutions (or deletions) consistently, hundreds of
times, within a dialect. But the fingerprint looks more like *the audible signature of a model struggling with
unfamiliar phonology* than clean "dialect word → standard Hindi equivalent" normalization. Details and caveats
below.

## Methodology, including two real bugs caught and fixed

1,426–14,134 clips exist per dialect (6,241–63,151 cells of raw data per dialect sampled at ~24–100% of what was
available — see `discover_manifest.json` for exact per-dialect availability and the pull script's
`DEFAULT_PER_DIALECT_CAPS` for the proportional budget allocation actually used).

Before diffing, the human transcript is cleaned to strip annotation conventions that Prisma, transcribing raw
audio, could never reproduce: `<tag>...</tag>` wrappers (noise/pause/echo markers — text kept, tags stripped),
`[bracket]` markers (`[inaudible]`, `[breathing]` — removed entirely, no speech content), `{gloss}` annotations
after code-switched words (`एटीएम {atm}` → `एटीएम` — gloss stripped, word kept), trailing `--` for cut-off
utterances, and all punctuation (Prisma's output contains none at all, so punctuation is stripped from the human
side too for a fair comparison). Word-level alignment then uses `difflib.SequenceMatcher`.

Two data-quality bugs were caught during this analysis and are worth flagging honestly rather than quietly fixing:

1. **Unicode normalization.** A meaningful fraction of apparent "substitutions" were actually the *same word*
   encoded with different Devanagari codepoint sequences (precomposed vs. base+combining-nukta forms of
   characters like ड़/ढ़/फ़) — visually identical, byte-different. Confirmed directly: `h == p` was `False` for
   pairs that printed identically. Fixed with `unicodedata.normalize("NFC", ...)` before comparison. This
   inflated every dialect's apparent divergence rate; after the fix, "identical clip" rates rose and edit-rate
   proxies dropped across the board (e.g. Khariboli: identical-rate 5.0% → 7.0%, edit-rate 0.273 → 0.243).
2. **Repeated-word alignment artifacts.** When a word repeats within a sentence, `SequenceMatcher` sometimes
   aligns one occurrence to a different occurrence of the same word, producing a nominal "replace" block that
   actually maps a word to itself. Fixed by discarding any aligned pair where the human and Prisma spans are
   textually identical.

Both are disclosed here because the headline numbers below depend on them, and an unflagged version of this
analysis would have overstated divergence.

**Caveat on the comparison itself:** the "word edit rate proxy" (aligned edit operations ÷ human word count) is
*not* a real WER — it conflates genuine Prisma mis-transcription with any residual annotation-cleaning
imperfection and with cases where the human transcript itself contains disfluency the model never had a chance to
reproduce identically (e.g., stutters). Treat the numbers as a *relative* cross-dialect signal, not an absolute
accuracy figure.

## Finding 1: divergence rate tracks linguistic distance from standard Hindi

| Dialect | Clips | Identical | Edit-rate proxy |
|---|---:|---:|---:|
| Surjapuri | 194 | 1.6% | 0.633 |
| Garhwali | 1,893 | 0.4% | 0.583 |
| Sadri | 678 | 3.1% | 0.563 |
| Haryanvi | 165 | 0.0% | 0.511 |
| Surgujia | 526 | 4.0% | 0.490 |
| Awadhi | 187 | 5.3% | 0.490 |
| Bajjika | 804 | 1.0% | 0.486 |
| Marwari | 1,450 | 2.0% | 0.468 |
| Khortha | 799 | 2.6% | 0.465 |
| Rajasthani | 2,440 | 2.1% | 0.461 |
| Chhattisgarhi | 3,687 | 2.2% | 0.459 |
| Angika | 557 | 1.3% | 0.452 |
| Maithili | 3,349 | 2.0% | 0.430 |
| Magahi | 930 | 7.5% | 0.374 |
| Bhojpuri | 4,849 | 3.3% | 0.373 |
| Bundeli | 447 | 3.8% | 0.303 |
| Jaipuri | 87 | 5.8% | 0.275 |
| Kumaoni | 1,141 | 3.8% | 0.270 |
| Khariboli | 717 | 7.0% | 0.243 |

Khariboli — the Delhi-area dialect essentially closest to standard Hindi — has the lowest edit rate by a wide
margin. Garhwali and Surjapuri, phonologically and lexically far from Hindi, are worst. This is the first-order
signal, and it's consistent with the earlier (failed) classification work: these dialects really are harder for a
Hindi-trained model in proportion to their actual linguistic distance, it's just that *classifying* them from one
short utterance doesn't work well, while *measuring divergence given known ground truth* does show a clean
gradient.

## Finding 2: a layer of universal, non-dialect-specific normalization exists

Thirteen substitution patterns recur across three or more dialects — these are **not** a dialect fingerprint, they
look like generic model behavior independent of dialect:

| Human | Prisma | # dialects |
|---|---|---:|
| है | हैं | 13 |
| मे | में | 10 |
| हैं | है | 10 |
| यहाँ | यहां | 6 |
| के | का | 5 |
| बहोत / बोहोत | बहुत | 5 |
| हे | है | 5 |
| यहां | यहाँ | 4 |
| के | की | 4 |
| ए | ये | 3 |
| छै | छे | 3 |
| हेय | है | 3 |

Two different phenomena are mixed in here and should not be read the same way:

- **है ↔ हैं (bidirectional, 13 + 10 dialects)** is not spelling drift — it's genuine singular/plural copula
  disagreement, going both directions roughly equally often. The honest reading is that Prisma is *inconsistent*
  about number agreement when normalizing dialectal verb forms into standard Hindi, not that it has a
  directional "correction" policy.
- **यहाँ ↔ यहां, मे → में** are pure orthographic convention (chandrabindu vs. anusvara, space vs. conjunct) —
  this reflects transcriber spelling habits versus Prisma's output convention, not a speech-recognition
  phenomenon at all. This is noise in the "fingerprint" signal, not part of it, and should be filtered out of
  any downstream feature built from this data.
- **हे/छै/हेय → है/छे (copula normalization)** is the one universal pattern that *is* linguistically real: many
  Bihari- and Rajasthani-family dialects use a distinct copula form (हे, छै, हेय) where standard Hindi uses है,
  and Prisma collapses these toward Hindi's form consistently across dialect families. This is a genuine,
  reusable signal — just not a *dialect-specific* one, since it fires the same way across several unrelated
  dialects.

## Finding 3: the real fingerprint is in dialect-specific marker-word transformations, and it is substantial

Cross-referencing against the dialect markers already derived in `data/markers_v2.json` (the earlier, separate
corpus-frequency-based marker work) shows **specific marker words transformed in specific, highly consistent ways,
hundreds of times per dialect.** A sample (full data in `analysis/per_dialect_results.json`):

- **Bhojpuri**: `लोकत`/`लउकत` ("appears/seems") → `लौकत` (49 + 30 occurrences) — not normalized to a Hindi word,
  *reinterpreted as a different-sounding non-word*, suggesting Prisma doesn't recognize this lexical item at all
  and is pattern-matching on phonetics alone. `हमनी` ("we", Bhojpuri-specific plural) → `हमने` (14x) *is* a real
  Hindi-ward normalization.
- **Garhwali**: `भौत`/`बहौत` ("very") → `बहुत` (42 + 18x) — clean normalization to standard Hindi. But `यख`
  ("here") is either **deleted outright** (24x) or **misheard as `एक`** "one" (22x) — a dialectal deictic that
  Prisma apparently cannot parse as a word at all, so it's dropped or guessed into an unrelated common word.
- **Chhattisgarhi**: `अऊ`/`अउ` ("and") is deleted (34x, 97x) nearly as often as it's correctly normalized to
  `और` (27x) — roughly a coin flip between recognizing it and losing it entirely. `हावे`/`हावय` (copula) → `हवे`
  (35x + 24x) is a clean, consistent normalization.
- **Rajasthani/Marwari**: `अठे` ("here") is deleted (52x, 10x) or phonetically reinterpreted as `अटे` (23x,
  16x) — the same "can't parse this deictic" pattern as Garhwali's `यख`. Progressive-aspect markers `रियो`/
  `रेहो`/`रहियो` consistently collapse to standard Hindi `रही`/`रहे` (dozens to 65 occurrences each) — this is
  the single cleanest, highest-volume dialect-specific grammatical normalization found in the whole dataset.
- **Maithili**: `एता`/`एते` ("here"/"this much") mostly **deleted** rather than translated; `केना` ("how") once
  produced an unrelated 9-word hallucinated phrase.
- **Magahi/Bajjika**: shorter, less-common dialect words (`रोडवा`, `झक्कास`, `होऊ`) sometimes produce long,
  semantically unrelated multi-word insertions rather than a clean substitution or deletion — e.g. `रोडवा` →
  `हाँ इसमें है हमारे रोड बाप है रोड बाप`. This looks like genuine model hallucination under acoustic/lexical
  confusion, not normalization of any kind.

**The pattern across dialects**: deictics and locatives unfamiliar to the model (`यख`, `अठे`, `एता`) are the
least reliably handled — frequently deleted or wildly misheard, rarely cleanly normalized. Grammatical markers
with a clear 1:1 Hindi analogue (progressive aspect, copula forms) normalize cleanly and very consistently. Content
words specific to a dialect and phonetically distant from any Hindi word are the ones most likely to produce
outright hallucination (long unrelated insertions) rather than either correct recognition or graceful degradation.

## Finding 4: deletions and insertions are themselves patterned, not random

Looking at what Prisma drops versus what it adds (not just substitutes) across dialects, both lists are dominated
by short grammatical words — copulas, conjunctions, the number "one" (`एक`), common postpositions (`के`/`में`) —
appearing as both frequent *deletions* and frequent *insertions* in the same dialect. This is consistent with a
model that's uncertain about grammatical function words specifically when the surrounding phonology is
unfamiliar — it both over-inserts and under-produces the same small set of high-frequency words, rather than
reliably getting them right or reliably getting them wrong in one direction.

## What this does and doesn't support

**Supports**: the original Prisma-fingerprint hypothesis, in a more specific form than first proposed. There is a
real, high-volume, measurable signal in *how* Prisma transforms dialectal speech — but it's concentrated in a
closed-ish set of grammatical markers (copulas, aspect markers, a handful of deictics) per dialect family, not a
diffuse property of the whole transcript. A grounding mechanism built on this would do better targeting "does this
transcript contain one of this dialect's known-volatile markers" (e.g., Rajasthani `रियो`-family forms, Garhwali/
Rajasthani locative deictics) than treating the fingerprint as a general-purpose dialect classifier.

**Does not support**: using this as evidence that Prisma "understands" dialects or normalizes them coherently to
Hindi. A meaningful fraction of the divergence — especially for content words and short deictics — is deletion or
outright hallucination, not normalization. Any product built on "Prisma mishears X as Y, so ground Evon with that
knowledge" needs to handle the case where X is simply dropped or replaced with semantically unrelated content, not
just the case where X→Y is a clean substitution.

**Unverified / not yet done**: this analysis is entirely text-level (cleaned transcript diffs). It does not look at
acoustic features, confidence scores, or timing (Prisma's actual API exposes none of these — see
`reports/Boli paralinguistic interaction state.md` for the detailed accounting of what Prisma does and doesn't
expose). It also doesn't yet test whether these specific marker transformations are stable *across speakers* within
a dialect or driven by a handful of individual speakers' idiosyncratic pronunciation — the data has speaker
metadata (`gender`, `district`, `state`) that would let this be checked but it hasn't been, yet.
