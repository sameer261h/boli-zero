# Phonetic-similarity filter: WRONG vs. UNSURE across all 19 dialects

One question: after ignoring differences that are phonetically similar, how many remaining Prisma differences
are clearly wrong vs. genuinely uncertain? All 19 dialects, ~25,000 clips, existing alignment (no redesign —
same `clean()`/`tokenize()`/`align()` already used for `06-prisma-fingerprint-dialect-transformation-analysis.md`).
Script: `scripts/phonetic_filter_classification.py`. No Evon, no corrections built, no classifier.

## Method

Every 1:1 aligned `human_word → prisma_word` substitution across all 19 dialects (38,705 total instances) was
classified by one mechanical rule, applied uniformly:

- **IGNORE** (phonetically/orthographically similar): the two words become identical, or differ by at most 1
  character, after normalizing away two well-established Hindi spelling-convention sources of pure cosmetic
  variation — nukta (सफ़ेद/सफेद), and anusवार as shorthand for nasal-consonant-plus-virama (सुंदर/सुन्दर,
  मंदिर/मन्दिर, लंबा/लम्बा — these are two accepted spellings of the identical word, not an ASR error). This
  second normalization was added after the first pass showed it was needed — four of the top-15 "uncertain"
  cases on the first run were exactly this pattern, which would have been a real undercount of the
  phonetic-similarity filter's own stated scope, not a separate new heuristic.
- **WRONG / UNSURE** for everything that isn't IGNORE, split by normalized edit-distance ratio
  (`edit_distance / max(word length)`): ratio ≥ 0.5 → **WRONG** (most of the word changed, Prisma produced a
  genuinely different word); ratio < 0.5 → **UNSURE** (partial overlap, not confidently callable from the word
  pair alone).

Classification was done once per unique (human_word, prisma_word) pair, then weighted by how many times that
exact pair actually occurred (14,815 unique pairs covering the 38,705 instances) — so a frequent pattern counts
proportionally more than a one-off.

## Headline numbers

**Of all 38,705 Prisma differences, 67.4% disappear after the phonetic-similarity filter. Of the 32.6% that
remain, 76.2% are WRONG and 23.8% are UNSURE.**

| | Count | % of total |
|---|---|---|
| Total token differences | 38,705 | 100% |
| IGNORE (phonetically similar) | 26,095 | 67.4% |
| **Remaining flagged** | **12,610** | **32.6%** |
| — WRONG | 9,610 | 24.8% of total (76.2% of flagged) |
| — UNSURE | 3,000 | 7.8% of total (23.8% of flagged) |

## By dialect

| Dialect | Total | Ignore % | Flagged | WRONG (% of flagged) | UNSURE (% of flagged) |
|---|---|---|---|---|---|
| Bhojpuri | 7,760 | 69.6% | 2,358 | 1,682 (71.3%) | 676 (28.7%) |
| Chhattisgarhi | 5,442 | 65.5% | 1,875 | 1,649 (87.9%) | 226 (12.1%) |
| Maithili | 5,567 | 72.2% | 1,547 | 1,218 (78.7%) | 329 (21.3%) |
| Rajasthani | 3,746 | 58.4% | 1,558 | 1,236 (79.3%) | 322 (20.7%) |
| Garhwali | 2,641 | 58.7% | 1,090 | 832 (76.3%) | 258 (23.7%) |
| Marwari | 2,422 | 58.5% | 1,004 | 712 (70.9%) | 292 (29.1%) |
| Magahi | 1,147 | 66.0% | 390 | 297 (76.2%) | 93 (23.8%) |
| Bajjika | 1,617 | 75.3% | 399 | 324 (81.2%) | 75 (18.8%) |
| Khortha | 841 | 64.3% | 300 | 245 (81.7%) | 55 (18.3%) |
| Angika | 910 | 75.1% | 227 | 170 (74.9%) | 57 (25.1%) |
| Kumaoni | 2,385 | 75.8% | 578 | 320 (55.4%) | 258 (44.6%) |
| Sadri | 730 | 60.8% | 286 | 242 (84.6%) | 44 (15.4%) |
| Khariboli | 1,271 | 79.8% | 257 | 143 (55.6%) | 114 (44.4%) |
| Surgujia | 556 | 59.2% | 227 | 200 (88.1%) | 27 (11.9%) |
| Bundeli | 770 | 70.4% | 228 | 145 (63.6%) | 83 (36.4%) |
| Surjapuri | 197 | 57.4% | 84 | 52 (61.9%) | 32 (38.1%) |
| Awadhi | 247 | 72.9% | 67 | 50 (74.6%) | 17 (25.4%) |
| Haryanvi | 274 | 66.4% | 92 | 65 (70.7%) | 27 (29.3%) |
| Jaipuri | 182 | 76.4% | 43 | 28 (65.1%) | 15 (34.9%) |

Two dialects stand out for an unusually high UNSURE share — **Kumaoni (44.6%) and Khariboli (44.4%)**, both
roughly double the typical ~20-25%. Both are the varieties closest to standard Hindi (lowest divergence overall,
per the original fingerprint report), so this is consistent, not surprising: when a dialect barely differs from
Hindi, the differences that do occur are less likely to be the clean, large, obviously-wrong substitutions and
more likely to be small, ambiguous edits.

## 10 representative WRONG examples (by frequency, with real sentence context)

| Human | Prisma | Count | Context |
|---|---|---|---|
| हेय | है | 178 | "...तीन मंजिला बिल्डिंग **हेय**।" → "...बिल्डिंग **है**" — dialectal copula spelling, flagged WRONG by the mechanical rule (2-character edit) despite being arguably a close phonetic variant; see limitations below |
| इ | ये | 165 | demonstrative pronoun substitution |
| हे | हैं | 146 | copula number/form change |
| म | में | 130 | "लाल **म** के शर्ट पहन" → "लाल **में** के शर्ट पहन" — dialectal locative postposition शortened form replaced with standard में |
| ए | ये | 129 | demonstrative substitution |
| रो | रही | 93 | "...परिक्रमा कर **रो** है..." → "...कर **रही** है" — Rajasthani dialectal progressive-aspect marker normalized to standard Hindi grammar; a real grammatical-information loss, not just a spelling change |
| अउ | और | 84 | Chhattisgarhi conjunction ("and") replaced with standard form |
| रहियो | रही | 68 | same progressive-aspect normalization pattern as रो→रही |
| रेहो | रही | 65 | same pattern again — one of the cleanest, most consistent dialectal-grammar-erasure patterns in the whole dataset |
| मा | में | 61 | locative postposition, dialectal → standard |

## 10 representative UNSURE examples (by frequency, with real sentence context)

| Human | Prisma | Count | Context |
|---|---|---|---|
| बोहोत | बहुत | 195 | "...**बोहोत** सारे मूर्ति..." → "...**बहुत** सारे मूर्ति..." — almost certainly the same spelling-convention variation as the task's own example (बहोत→बहुत), just with an extra vowel; falls just outside the edit-distance-1 cutoff (distance 2) — a disclosed boundary case, see limitations |
| वाइट | व्हाइट | 125 | English loanword "white," two accepted transliterations |
| वगेरा | वगैरह | 36 | "etc." — spelling variant, borderline |
| देखिये | देखिए | 26 | polite-imperative spelling variant ("look"), genuinely ambiguous whether this is dialect or just casual spelling |
| हमर | हमारे | 18 | "**हमर** गाँव मा..." → "**हमारे** गाँव में..." — Chhattisgarhi dialectal possessive pronoun normalized to standard; some real grammatical content here, genuinely hard to call purely cosmetic |
| दिखेरो | दिखीरु | 18 | both sides look like ASR-garbled forms of a "looks/appears" verb — genuinely unclear which (if either) is more "correct" |
| ए_टी_एम | एटीएम | 15 | "ATM" — underscore-segmented vs. standard spelling of the same acronym |
| येल्लो | येलो | 15 | "yellow" loanword, double-vs-single consonant transliteration |
| पेहेन | पहन | 12 | "wear" — could be a genuine dialectal vowel-insertion pattern or casual spelling |
| खातिर | खाती | 9 | "for the sake of" vs. a feminine participle — genuinely different meaning, but short word pair makes the edit-distance ratio ambiguous |

## Known limitations of this specific filter (disclosed, not hidden)

- **Character edit-distance is an orthographic proxy for phonetic similarity, not a true phonetic measure.**
  हेय→है and हे→हैं (two of the most frequent "WRONG" entries, 178 and 146 occurrences) are real dialectal
  copula-spelling variants that a fluent reader would likely judge phonetically close — but adding/dropping the
  glide य or changing a vowel sign crosses the edit-distance threshold mechanically. These areландед WRONG by the
  stated rule, not because the rule is broken, but because orthographic distance and spoken-sound distance
  diverge for this specific class of word.
- **बोहोत→बहुत (195 occurrences, the single most frequent UNSURE item) is almost certainly the same phenomenon
  as the task's own worked example (बहोत→बहुत)**, just with one extra character — it falls into UNSURE only
  because it needs 2 edits instead of 1. A reader may reasonably judge this should be IGNORE; the number is
  reported as UNSURE under the disclosed, uniformly-applied threshold rather than special-cased.
- **रो/रहियो/रेहो → रही** (Rajasthani progressive-aspect dialectal markers, 226 combined occurrences in the
  WRONG top-10 alone) are mechanically WRONG (real word change) but represent a different *kind* of difference
  than most other WRONG entries — Prisma isn't mishearing a random word, it's systematically erasing a specific
  dialectal grammatical marker in favor of standard Hindi grammar. This is accurately WRONG under the task's
  definition ("Prisma clearly changed the word/meaning"), but it's worth knowing this is a structured,
  predictable kind of WRONG, not noise — consistent with everything found in the original fingerprint analysis.

## Answer to the key question

**67.4% of all Prisma differences across the 19 dialects disappear once phonetically/orthographically similar
pairs are filtered out. Of the remaining 32.6%, just over three-quarters (76.2%) are clearly wrong substitutions,
and just under a quarter (23.8%) are genuinely ambiguous from the word pair and context alone.**
