# Prompt for ChatGPT: verify the "safe vs. ambiguous Prisma transformation" classification logic

Paste everything below as-is. It has no access to prior conversation, so it's self-contained.

---

## Context

This is the "Boli" project: a voice pipeline where Prisma (a Hindi-only ASR system) transcribes speakers of
regional Hindi dialects, and we've found that Prisma's transcription *errors* are not random — they follow
systematic, dialect-specific patterns (e.g., a Rajasthani speaker saying "री" often gets transcribed as "रही").
We have 25,000+ real audio clips across 19 regional varieties, each with both a human reference transcript and
Prisma's actual output, so we can directly measure these error patterns at scale.

## The goal

We want to split Prisma's known transformation patterns into two categories:

1. **Safe/deterministic**: patterns where, whenever the dialectal word X appears, Prisma reliably does the same
   specific thing to it (always becomes Y, or always gets deleted, etc.) — these could be auto-corrected by a
   simple lookup table, no reasoning required, before the transcript ever reaches our LLM.
2. **Ambiguous/context-dependent**: patterns where X's fate varies a lot depending on context — these need real
   reasoning (by an LLM, with the specific pattern surfaced as a hint) to resolve, if they can be resolved at all.

## What we just measured, and why it changes the plan

Our first instinct was: look at the pre-aggregated "top substitution" counts per dialect (e.g., "री → रही,
occurred 166 times") and assume high raw frequency implies a safe, dominant pattern. **We tested this properly
just now by computing the FULL outcome distribution for a few example words — not just their single most common
outcome — and the result undercuts that assumption badly:**

| Dialect | Word | All observed outcomes (with %) | Verdict |
|---|---|---|---|
| Rajasthani | री | → रही (53.0%), → "रही छै" [multi-word] (6.4%), → "दिखीरी" [multi-word] (3.8%), → "दिखेरी" [multi-word] (3.8%), DELETED (3.2%), → "रही है" [multi-word] (1.3%), ...more | Only ~53% consistent — far from clean |
| Rajasthani | है | DELETED (24.0%), → हैं (6.2%), → "रहे हैं" [multi] (5.3%), UNCHANGED (5.0%), → "खड़े हैं" [multi] (2.0%), → "रहे" [multi] (1.8%), ...long tail | No dominant outcome at all — despite है→हैं being one of the most frequent patterns *across all 19 dialects*, treated earlier as a safe "universal" normalization |
| Garhwali | यख (a deictic meaning "here") | DELETED (9.6%), → एक (8.8%), → "यखमा" [multi] (6.0%), → "यखमा जी" [multi] (2.4%), → यक (2.0%), → या (1.6%), ...long tail | Scattered, no safe default — consistent with this being a known hard case (content word, not just orthography) |
| Garhwali | भौत (dialectal "very") | → बहुत (30.3%) + several multi-word variants also landing on बहुत-ish output (roughly 40% combined) | The *cleanest* of the four tested, but still not dominant in the simple sense |
| Bhojpuri | है | UNCHANGED (24.5%), → हैं (22.5%), DELETED (14.5%), → ह (2.9%), → बा (1.2%), → हई (1.2%) | Also scattered — है is apparently one of the messiest words in the whole dataset, not a safe one |
| Bhojpuri | बा (a real dialect marker, existential "is/am/are") | UNCHANGED (10.6%), DELETED (9.0%), then a long tail of small multi-word outcomes | Scattered, not safe |

So: of 6 hand-picked words that *looked* like strong candidates from the aggregated top-list view, **none cleared
a reasonable "safe" bar (we'd want something like 70%+ consistency) when every outcome was counted, not just the
top one.** This is a real, measured result, not a guess.

**One likely confound we noticed but haven't isolated yet**: several of the "outcomes" above are multi-word
blocks (e.g., "रही छै", "यखमा जी", "रहा हलवा") produced by our word-alignment step (`difflib.SequenceMatcher`)
merging the target word's substitution together with a neighboring word that *also* changed in the same
sentence. This could be artificially inflating the apparent diversity of outcomes — the target word's "true"
individual transformation might be the same each time, just obscured inside different multi-word blocks because
of what else happened to be next to it. We have not yet tested whether collapsing/re-examining these multi-word
cases (e.g., checking just the first token of each multi-word output, or re-aligning with a different method)
reveals more consistency underneath.

## What we want you to pressure-test

1. **Is our conclusion ("frequent ≠ safe, almost nothing we tested is cleanly deterministic") actually right, or
   could the multi-word alignment artifact be hiding real consistency?** What's the right way to test this — e.g.,
   should we re-run `difflib` alignment with different parameters, use a proper word-level sequence aligner
   (like a Needleman-Wunsch style aligner instead of a generic diff), or collapse multi-word outcomes by their
   first/head word before measuring consistency?

2. **What's the right statistical measure for "safe/deterministic" here**, given real-world messiness like this?
   Options we're considering, tell us which is soundest or propose better:
   - A hard threshold on raw consistency (e.g., "safe if top outcome ≥ 70% of all occurrences, with ≥ 10
     occurrences total") — simple but our data suggests almost nothing clears 70%.
   - Shannon entropy over the full outcome distribution (low entropy = safe, high entropy = ambiguous) instead of
     a single-outcome percentage — handles the "many small outcomes" case better than a threshold on the top
     answer alone.
   - **Semantic-equivalence clustering**: instead of requiring one *exact* output string to dominate, group
     outcomes that don't change meaning (e.g., है / हैं / UNCHANGED could arguably be treated as one "safe"
     cluster, since they're just verb-agreement/tense variants of "to be" in Hindi and auto-correcting between
     them loses nothing) and measure consistency *within that cluster* rather than per-exact-string. Is this
     linguistically sound, or does it risk silently erasing real dialectal information (e.g., is a dialect's
     choice of हैं vs है sometimes meaningful, not just cosmetic)?
   - Something else entirely you'd recommend for this exact problem (observed-input → variable-output
     consistency estimation with a long tail of low-count outcomes).

3. **Is 10,000+ occurrences-with-long-tail typical of this kind of analysis**, or does the long tail itself
   suggest our underlying word-alignment step is too noisy to trust for this specific sub-task (as opposed to the
   aggregate dialect-fingerprinting we already did successfully with the same alignment method)?

4. **Minimum sample size / statistical confidence**: we have anywhere from ~90 to ~900 tracked occurrences per
   word in these examples. What's a defensible minimum count before we trust a consistency percentage at all,
   given this is going to gate an automated "silently correct this without asking anyone" behavior in a
   production voice pipeline — i.e., the cost of being wrong (silently "fixing" something that was actually said
   differently) should weigh into how conservative the threshold is.

5. **Deletions and insertions specifically**: our current thinking is these should almost never be classified
   "safe" even if frequent, because there's no way to know *what* to re-insert from a deletion (we only know
   something was dropped) — reasoning/context is unavoidable there, unlike a 1:1 substitution where at least a
   candidate replacement word exists. Do you agree, or is there a principled way to treat some deletions as
   safe too (e.g., deletion of purely grammatical particles that don't change meaning if silently omitted from
   the record Evon sees)?

## What we want back

A concrete, defensible scoring rule (or confirmation that our semantic-clustering idea above is the right one,
with specifics on how to validate it) that we can implement directly — not general ML-pipeline advice. Flag
anything in our reasoning above that's wrong, overconfident, or needs a different experiment before we trust it.
We are specifically worried about shipping a "safe auto-correct" layer that's actually wrong often enough to
matter, so err on the side of telling us our bar is too low rather than too high.

## Hard constraints

- This is a pure methodology/statistics question. No audio or new data collection is needed to answer it — we
  have the full per-clip human/Prisma transcript pairs already and can recompute anything you suggest.
- Be specific and reference the actual numbers above, not generic advice about ASR error correction.
