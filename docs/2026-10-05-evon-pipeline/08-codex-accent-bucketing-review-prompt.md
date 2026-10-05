# Prompt for Codex: stress-test the Regional Speech Fingerprint bucketing logic

Paste everything below to Codex as-is. It has no access to this conversation, so the prompt is self-contained.

---

## Context

This is the "Boli" project (`sameer261h/boli-zero`): a voice pipeline, Prisma (Gnani STT, hi-IN mode) → Evon (an LLM) → Timbre (TTS), aimed at handling Indian regional dialects naturally. Prisma only does Hindi-mode transcription — there is no dialect-aware ASR. The working hypothesis ("Boli") is that Prisma's *errors* when transcribing dialect speech as if it were Hindi are not random noise but a systematic, dialect-specific "fingerprint" that could ground Evon's responses (e.g., telling Evon "this speaker's input likely came from a dialect that drops word-final nasalization" rather than claiming a dialect label).

We pulled 24,986 real audio clips across 19 regional varieties from the gated `ARTPARK-IISc/Vaani-transcription-part` HF dataset, ran each through the real Prisma API, and have the human transcript + Prisma transcript + state/district/gender metadata for every clip. No audio is stored, only text + metadata, in `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/<Dialect>.jsonl`.

The 19 varieties: Bhojpuri, Chhattisgarhi, Maithili, Rajasthani, Garhwali, Marwari, Magahi, Bajjika, Khortha, Angika, Kumaoni, Sadri, Khariboli, Surgujia, Bundeli, Surjapuri, Awadhi, Haryanvi, Jaipuri.

## The two questions we are actually trying to answer

**Question 1 (classification/separability — "can Evon tell these apart from text alone"):** For each of the 19 varieties, is single-utterance identification from Prisma's transcript reliable enough to treat it as its own identity, or should it be merged into a shared bucket with others? This is about **data strength and confusability**, independent of whether the varieties sound alike.

**Question 2 (phonetic/acoustic similarity — "do these varieties get mis-heard by Prisma in the same way"):** Independent of classification confidence, which varieties' *error patterns* (what Prisma substitutes/deletes/hallucinates) resemble each other? This is a proxy for "do these dialects sound similar to a Hindi-trained ASR ear," since we have no raw audio features, only the ASR's behavior on it.

The point of combining them: **Question 1 decides whether a variety is allowed to stand alone at all. Question 2 decides, among the varieties that Question 1 says are too weak to stand alone, which ones should share a single "fingerprint card" fed to Evon.** We are explicitly trying to avoid two failure modes: (a) bucketing a variety that's actually strong just because it's phonetically close to something else ("accent bucketing regardless of data" — wrong), and (b) refusing to bucket a genuinely weak variety just because we haven't proven phonetic similarity ("bucketing only where data is strong" — also wrong, leaves weak varieties pretending to be exact when they're not). The instruction we're working from is: **bucket based on where the evidence is constrained (Question 1's weak dialects), using Question 2 only to decide bucket membership, not to override Question 1's "this one is fine standalone" calls.**

## What we did for Question 1

Script: `experiments/2026-10-05-evon-pipeline/scripts/regional_fingerprint_audit.py`. Zero LLM calls — pure text/metadata analysis on the already-pulled transcripts. Key steps:

1. **Group-disjoint train/val/test split.** No true speaker ID exists in the Vaani metadata, so `state|district|gender` is used as a speaker-group proxy. `GroupShuffleSplit` on groups, not rows, to prevent leakage. **9 of 19 dialects** (Rajasthani, Marwari, Bajjika, Khortha, Sadri, Surgujia, Surjapuri, Haryanvi, Jaipuri) have too few groups (≤8, some as low as 2) for a true group split, so they fall back to row-level stratified splitting — their held-out numbers are explicitly flagged as **not truly speaker-disjoint**, i.e. optimistic.
2. **TF-IDF + Logistic Regression** 19-way classifier, three feature modes (word n-grams, char n-grams, combined). Combined mode: exact accuracy 54%, family-level accuracy 71%, ECE (calibration error) 0.14 — poor calibration, flagged as not usable for a real confidence score yet.
3. Per-dialect precision/recall/F1 on the held-out split is the primary evidence for "is this variety separable."

Full results: `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/regional_fingerprint_audit/audit_results.json`. Full writeup: `docs/2026-10-05-evon-pipeline/07-regional-speech-fingerprint-audit.md`.

Resulting confidence tiers (recall/precision on the combined-feature classifier, cross-checked against group-cardinality severity):

- **High:** Bhojpuri (P.89/R.77, 27 speaker-groups, proper disjoint split)
- **Medium-High:** Garhwali (P.79/R.64, but only 4 groups / not disjoint — entire Vaani dataset has only 2 districts for Garhwali, ever)
- **Medium:** Chhattisgarhi (P.74/R.43), Rajasthani (P.70/R.52, same hard-ceiling caveat — only 2 districts exist), Khortha (P.48/R.79, small n, not disjoint)
- **Medium-Low:** Maithili (P.63/R.42) — note Maithili has *good* group diversity (41 groups) yet is still confusable; flagged as intrinsic confusability with other Bihari varieties, not a data-volume problem
- **Low-Medium:** Bajjika (P.46/R.65, only 2 groups pre-pull — see below), Marwari (P.45/R.55, hard ceiling — only 3 districts exist, and the 3rd has 2 rows total)
- **Low:** Surgujia, Sadri, Kumaoni, Bundeli, Haryanvi, Khariboli, Surjapuri (various reasons — small n, hard ceilings, or genuine closeness to standard Hindi)
- **Very low:** Jaipuri (17 test rows), Magahi (P.17/R.15 despite OK group diversity — intrinsic confusability), Angika (P.10/R.17, worst of the 19, also OK group diversity), Awadhi (0/22 correct, and the *entire* dataset for Awadhi is only 187 rows — a hard data floor, not a pull-more-data problem)

We also directly checked, per dialect, whether the *full* Vaani dataset (not just our sample) has more district/speaker diversity available to pull. Finding: **most of the weak dialects are already at or near 100% of all data that will ever exist** — Awadhi, Bundeli, Haryanvi, Jaipuri, Kumaoni, Surgujia, Sadri, Surjapuri are all pulled at 97-100% of their total existence in the dataset. Rajasthani and Garhwali have hard 2-district ceilings regardless of volume pulled. The only case with a genuine, clean additional-diversity opportunity was Bajjika (3 entirely untouched districts, Muzaffarpur/Samastipur/Sitamarhi, 57 rows total) — we just pulled all 57 of those (0 errors), closing that gap. Khortha has ~1,800 more rows available but they'd mostly land in districts/genders we already have some coverage of, so the expected diversity gain is marginal, not unequivocal.

## What we did for Question 2

Two independent signals, computed from the already-collected data, no new calls:

**Signal A — classifier confusion matrix** (from the same audit_results.json, combined-feature mode, 19×19 matrix, row-normalized). **We think this signal is partially confounded**: e.g. Awadhi (22 test rows, 0% recall) gets predicted as Bhojpuri (the largest class, 1,304 test rows) 41% of the time, while Bhojpuri is almost never predicted as Awadhi — this looks like a small-class-defaults-to-big-class artifact of class imbalance, not genuine phonetic similarity. We are not confident this signal is clean.

**Signal B — Prisma ASR transformation-pattern similarity.** Source: `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/analysis/per_dialect_results.json` (per-dialect: clip_count, word_edit_rate_proxy, and a `top_substitutions` list of up to 40 `[[human_word, prisma_word], count]` pairs — the word-level diffs between human and Prisma transcripts, already computed by `scripts/analyze_prisma_fingerprint.py`). We built a per-dialect vector over the union of all substitution-pair types (value = count / clip_count, to normalize for different sample sizes), after removing 13 pairs flagged as "universal" in `cross_dialect_universal_substitutions.json` (substitutions like है↔हैं or मे→में that occur in 5+ dialects and would otherwise just measure "closeness to generic Hindi ASR behavior" rather than mutual similarity). Cosine similarity between these vectors, converted to a distance matrix, hierarchical clustering (`scipy.cluster.hierarchy.linkage`, average linkage).

We chose the number of clusters (k) by silhouette score, scanning k=2..11 (code and raw scores available on request / reproducible from the files above — happy to paste the exact script). **Silhouette scores were weak everywhere: peak ~0.20 at k=6, rising only to 0.24 at k=10 by fragmenting into mostly singletons/pairs.** We interpreted this as "no strong natural clustering exists in this data," and picked k=6 as the smallest k where real, stable sub-clusters emerge (pairs/groups that hold together across k=3 through k=6), rather than treating k=6 as a confidently "correct" number.

Restricting that clustering to only the dialects Question 1 already flagged as too weak to stand alone (excluding Bhojpuri, Garhwali, Chhattisgarhi, Rajasthani, Khortha, which test says are fine individually even if their ASR-error-pattern vector happens to look unusual), we landed on:

- **Real, stable bucket:** Sadri, Surgujia, Awadhi, Haryanvi (Chhattisgarhi-periphery pattern)
- **Real, stable bucket:** Khortha, Surjapuri
- **Real, stable bucket:** Magahi, Bajjika
- **Lean on, don't merge:** Marwari (only ever paired with Rajasthani, which stands alone fine — so Marwari borrows lightly from Rajasthani's register rather than getting its own bucket)
- **Explicitly NOT bucketed, left individual with a generic/default Hindi register fallback:** Maithili, Kumaoni, Khariboli, Jaipuri, Angika, Bundeli — these never form a stable pair with anything at any k we tried. We considered forcing them into one leftover bucket but decided that would be inventing structure the data doesn't support.

## What we want from you

Be adversarial. We do not want validation — we want the holes found before we build Evon-facing fingerprint cards on top of this.

1. **Check our clustering methodology.** Is cosine similarity on normalized substitution-count vectors, after stripping "universal" substitutions, a defensible way to proxy phonetic similarity from ASR error behavior? What would you do differently — a different distance metric, a different normalization (e.g., TF-IDF-style weighting of substitution pairs instead of raw rate), Jaccard on substitution *sets* instead of cosine on rate vectors, something else entirely?
2. **Stress-test the "universal substitution" removal step.** We removed 13 pairs that appear in 5+ dialects' top-40 lists. Is a frequency-based cutoff like that defensible, or could it be throwing away real signal (e.g., a substitution that's universal but at very different *rates* per dialect might still be informative, and raw removal discards that)?
3. **Stress-test the k=6 choice.** We picked k=6 because silhouette peaked locally there before degenerating into singletons. Silhouette maxed at only ~0.24 (weak by conventional thresholds). Is there a better validity index for this kind of sparse, high-dimensional, count-based data (e.g., gap statistic, Davies-Bouldin, something built for cosine-distance hierarchical clustering specifically)? Would a different clustering algorithm (e.g., spectral clustering on the similarity graph, or DBSCAN to explicitly allow "no cluster" outliers like Garhwali) give a more defensible answer than forcing every dialect into some flat k?
4. **Check whether we're missing a confound in Signal A (confusion matrix).** Is our suspicion correct that it's biased by class imbalance? Is there a way to de-bias it (e.g., balanced class weighting during classifier training, or normalizing the confusion matrix by both row AND column before using it) that would make it a trustworthy second signal instead of one we're discounting?
5. **Suggest additional parameters/features that could raise our confidence beyond text-derived signals.** We only have: human transcript, Prisma transcript, audio duration (`duration_sec`), state, district, gender. We do NOT have raw audio, phoneme alignments, or any acoustic features — Prisma's API returns only `{transcript, model, processing_time, end_to_end_latency}`, confirmed directly against the live API, nothing else. Given that hard constraint, what's the highest-value next feature to add from what we *could* still extract cheaply (e.g., character-level edit-distance alignment position within the word — prefix vs. suffix vs. medial substitutions — duration-normalized speech rate as a weak prosody proxy, syllable-count mismatches, retranscribing a small sample with a phoneme-level grapheme-to-phoneme converter to compare phonetic rather than orthographic substitution patterns)? Rank your suggestions by expected signal gain vs. implementation cost, assuming no new Prisma/Evon API calls are approved yet — if a suggestion requires new audio/API calls, say so explicitly and estimate how many calls it would need.
6. **Specifically sanity-check Marwari's "lean on Rajasthani" call and the 6-variety "leave individual" list.** Did we make the right judgment call there, or is there a cleaner way to handle "this variety has no clean bucket partner" (e.g., should it just get Hindi's generic register with zero dialect-specific markers at all, versus something softer)?

## Files to inspect directly (don't just trust this summary)

- `experiments/2026-10-05-evon-pipeline/scripts/regional_fingerprint_audit.py` — Question 1 methodology
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/regional_fingerprint_audit/audit_results.json` — Question 1 full results (confusion matrices, group cardinality, calibration)
- `experiments/2026-10-05-evon-pipeline/scripts/analyze_prisma_fingerprint.py` — how per-dialect substitution patterns were extracted
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/analysis/per_dialect_results.json` — Question 2 raw substitution data
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/analysis/cross_dialect_universal_substitutions.json` — the 13 removed "universal" pairs
- `docs/2026-10-05-evon-pipeline/07-regional-speech-fingerprint-audit.md` — full narrative writeup of Question 1, including all caveats and known ways the experiment could mislead (§10)
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/*.jsonl` — the raw 24,986+57 human-vs-Prisma transcript pairs with metadata, if you want to recompute anything from scratch

## Hard constraints

- Do not call Prisma or any LLM API. This is a pure analysis/methodology review task.
- Do not assume more data is always the answer — we've already shown most of these dialects are at or near 100% of all data that will ever exist in this dataset.
- Be specific and cite exact numbers/files, not general ML-clustering advice.
