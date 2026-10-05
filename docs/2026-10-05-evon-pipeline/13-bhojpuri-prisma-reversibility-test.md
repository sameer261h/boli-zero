# Bhojpuri Prisma reversibility test

One question only: **can any recurring Bhojpuri Prisma transcription errors be safely reversed with simple
token-level correction rules?** Reuses the exact `clean()`/`tokenize()`/`align()` logic from
`analyze_prisma_fingerprint.py` (the same alignment already used for `06-prisma-fingerprint-dialect-
transformation-analysis.md`) — no redesign. No Evon, no LLM, no classifier, no other dialects, no
context-aware rules, no hand-curated dictionary. Script: `scripts/bhojpuri_reversibility_test.py`.

## Method

4,849 Bhojpuri clips, 80/20 train/test split (3,879 / 970 clips), fixed seed (42), clip-level random split.

For every recurring 1:1 substitution `human X → prisma Y` found in train:

- **support**: raw occurrence count
- **forward consistency** `P(Prisma=Y | Human=X)`: of all the times the human said X, how often did Prisma output Y
- **reverse precision** `P(Human=X | Prisma=Y)`: of all the times Prisma output Y (from *any* source — X,
  another word entirely, an unrelated multi-word edit, or a pure hallucination with no human-side word at all),
  how often was the real word actually X

Reverse precision is the number that determines whether a "Prisma said Y → correct to X" rule is safe to apply,
and it is **not** the same question as forward consistency. A word can be a very consistent *output* of X and
still be an unsafe correction target, if Y is also commonly the correct word, or commonly comes from several
other sources.

Rules were mined on train only, then applied to test's Prisma transcripts and checked against test's actual
human transcripts, at three support thresholds (10 / 25 / 50) crossed with three reverse-precision thresholds
(90% / 95% / 98%) — 9 combinations total.

## Results

**Every single threshold combination produced zero qualifying rules.**

| min support | min reverse precision | rules | tokens changed | incorrect fixed | correct damaged | net reduction | clips improved | clips worsened |
|---|---|---|---|---|---|---|---|---|
| 10 | 90% | 0 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 10 | 95% | 0 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 10 | 98% | 0 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 25 | 90% | 0 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 25 | 95% | 0 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 25 | 98% | 0 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 50 | 90% | 0 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 50 | 95% | 0 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 50 | 98% | 0 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |

Not a methodology bug — confirmed by inspecting every candidate directly. Of the 63 (X,Y) pairs with support ≥
10, **the single highest reverse precision found anywhere was 66.7%**, and that was at the minimum support
threshold (10 occurrences). Zero candidates reach even 70% reverse precision, let alone the 90% floor tested.

## The six questions

**1. Do safely reversible Bhojpuri Prisma transformations exist?** No — not at any of the tested, deliberately
conservative thresholds (support ≥ 10, reverse precision ≥ 90%).

**2. How many?** Zero, at every threshold combination tested.

**3. How much transcript coverage do they give?** None — zero rules means zero tokens touched.

**4. Do they actually reduce errors on held-out data?** No measurement possible — no rules exist to test.

**5. Five to ten representative "safe" rules?** None exist at the required bar. For transparency, here is the
full ranked list of the *closest* candidates (support ≥ 10, ranked by reverse precision — none clear 70%):

| Human X | Prisma Y | Support | Forward consistency | Reverse precision |
|---|---|---|---|---|
| रहल | रहाल | 10 | 2.7% | 66.7% |
| ओकरा | उकरा | 10 | 11.2% | 62.5% |
| यहाँ | यहां | 53 | 17.4% | 53.5% |
| गइल | गईल | 14 | 8.0% | 48.3% |
| वाइट | व्हाइट | 23 | 57.5% | 42.6% |
| सफेद | सफ़ेद | 33 | 43.4% | 40.7% |
| गइल | गैल | 37 | 21.1% | 37.8% |
| इ | ई | 66 | 8.4% | 36.1% |
| जहाँ | जहां | 24 | 25.3% | 33.8% |

Most of these are spelling-convention pairs (chandrabindu ँ vs. anusvara ं, nukta ज़/sans-nukta ज, vowel-length
ई/इ) where *both* spellings are independently common in the corpus — so there's no safe "correct direction,"
each spelling is sometimes right on its own.

**6. Five representative "tempting but unsafe" transformations** (high forward consistency, making them look
like strong candidates from an aggregated top-list view, but low reverse precision once properly measured):

| Human X | Prisma Y | Support | Forward consistency | Reverse precision | Why it's unsafe |
|---|---|---|---|---|---|
| बहोत | बहुत | 56 | **59.6%** | **4.4%** | बहुत is the standard, extremely common Hindi word for "very" — Prisma outputs it constantly regardless of dialect, so when you see बहुत, it's overwhelmingly because the speaker just said बहुत, not the dialectal बहोत. "Correcting" बहुत → बहोत would wreck the vast majority of genuinely correct transcriptions. |
| लोकत | लौकत | 37 | 64.9% | 28.7% | लौकत is itself a frequent, independently-correct word much of the time |
| लउकत | लौकत | 25 | 59.5% | 19.4% | Same attractor word, different dialectal spelling feeding into it |
| वगैरा | वगैरह | 12 | 92.3% | 30.8% | Despite near-perfect forward consistency (92%!), वगैरह is common enough as a standalone correct word that reverse precision collapses |
| जहां | जहाँ | 34 | 38.6% | 26.6% | Same spelling-convention ambiguity as the "safe" candidates above, just in the opposite direction — both spellings flow into each other roughly symmetrically |

The बहोत→बहुत case is the clearest illustration of why reverse precision, not forward consistency, has to be the
gating metric: 59.6% forward consistency looks like a strong, actionable pattern in isolation, and it's exactly
the kind of pattern the earlier, cruder "top substitution" list would have flagged as a good correction
candidate. Measured the right way, it's one of the least safe rules in the entire dataset.

## Conclusion

**Stop: transformations are too ambiguous to reverse safely.**

At every conservative threshold tested, zero Bhojpuri Prisma transformations meet the bar for a safe,
deterministic, context-free correction rule. The root cause, visible directly in the data: the Prisma output
vocabulary is dominated by a small set of common "attractor" words (बहुत, बा, है, spelling-convention variants)
that are frequently correct on their own merits, so no single upstream dialectal word can be confidently blamed
whenever one of those common words appears. A token-level lookup-table correction layer is not a viable
mechanism for Bhojpuri under this methodology. Any future work on recovering lost information from Prisma's
errors needs context (surrounding words, sentence meaning) to disambiguate — exactly the kind of reasoning this
test was explicitly designed to avoid, which is precisely why it comes back empty. This is a real, negative
result, not a tuning problem to iterate past.
