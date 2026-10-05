# v1 Regional Speech Detector — frozen map, calibration, and runtime decision logic

Supersedes the single-run numbers in `07-regional-speech-fingerprint-audit.md`. That report's classifier
numbers (and the earlier ad-hoc clustering used to propose 6 buckets) are not wrong, but they are each a single
measurement with no error bars — and today's work shows the error bars are often larger than the number itself.
This doc is the corrected, stability-tested version, and it changes several prior conclusions. Where it
disagrees with the earlier report, this doc wins.

## Stage 1 — corrected feature model

The previous "combined" classifier mode (`regional_fingerprint_audit.py`) was a bug: it was actually just
`char_wb(2,4)` alone, mislabeled. There was never a genuine word+char union tested. Fixed in
`scripts/v1_detector.py`: true word TF-IDF, true char TF-IDF, and a real combined mode (hstack of both). Selected
on **validation** accuracy, not test, to keep test honest:

| Mode | VAL acc | VAL top-2 | VAL family | TEST acc | TEST top-2 | TEST family |
|---|---|---|---|---|---|---|
| word | 0.528 | 0.702 | 0.690 | 0.447 | 0.591 | 0.663 |
| char | 0.527 | 0.700 | 0.682 | 0.451 | 0.596 | 0.664 |
| **combined (winner)** | **0.577** | **0.732** | **0.719** | **0.470** | **0.614** | **0.686** |

The genuine combined mode beats both alone by a real, non-trivial margin (~5 points on VAL). This part of the
brief's suspicion was correct — the old "combined" number was never testing what it claimed to.

Re-running the audit after the Bajjika (+57 rows, 3 new districts) and Khortha (+10 rows, last missing group)
pulls: **no dialect's status materially changed from those pulls alone.** Bajjika's group-severity moved
SEVERE→WEAK (2→6 groups); Khortha reached its absolute ceiling (7→8 groups, literally every group that exists
in the source dataset). Classifier F1 for both was unchanged within noise. Confirmed already in chat before this
doc; not repeated in depth here.

## The single most important finding of the day: split instability

Before trusting any per-dialect number, I ran the real combined classifier across **5 different random seeds**
for the group-disjoint split (`scripts/split_stability_check.py`). Result: **16 of 19 dialects show
unstable-to-borderline per-dialect accuracy purely from changing the seed.** Root cause: `GroupShuffleSplit`
assigns whole groups (state|district|gender, the only speaker-proxy this dataset has) to train/test, and most
dialects have only 4-14 of these groups with very uneven sizes (e.g. Khortha's Jamtara-Male group alone holds
542 of 809 rows). Whether that one dominant group lands in train or test — pure chance, per seed — swings the
apparent accuracy by 20-45 percentage points for many dialects. This was always a latent risk (flagged since the
very first audit: "no speaker-ID field, group proxy almost certainly collapses many speakers into one group") but
had never actually been measured until today.

**Practical consequence: every per-dialect number from here on uses the mean across 5 seeds, not a single run.**

| Dialect | Mean exact recall (5 seeds) | Range | Stability verdict | Groups | Severity |
|---|---|---|---|---|---|
| Garhwali | 0.790 | 0.105 | borderline | 4 | WEAK |
| Bhojpuri | 0.709 | 0.139 | borderline | 27 | OK |
| Bajjika | 0.650 | 0.095 | **stable** | 6 | WEAK |
| Khortha | 0.628 | 0.385 | **UNSTABLE** | 8 | WEAK |
| Chhattisgarhi | 0.615 | 0.084 | **stable** | 21 | OK |
| Surjapuri | 0.574 | 0.210 | UNSTABLE | 2 | SEVERE |
| Marwari | 0.535 | 0.175 | borderline | 4 | WEAK |
| Rajasthani | 0.496 | 0.251 | UNSTABLE | 4 | WEAK |
| Maithili | 0.421 | 0.210 | UNSTABLE | 41 | OK |
| Bundeli | 0.374 | 0.351 | UNSTABLE | 6 | WEAK |
| Kumaoni | 0.372 | 0.389 | UNSTABLE | 4 | WEAK |
| Surgujia | 0.362 | 0.038 | **stable*** | 2 | SEVERE |
| Khariboli | 0.326 | 0.194 | borderline | 19 | OK |
| Awadhi | 0.302 | 0.162 | borderline | 9 | OK |
| Jaipuri | 0.294 | 0.412 | UNSTABLE | 4 | WEAK |
| Sadri | 0.333 | 0.459 | UNSTABLE | 4 | WEAK |
| Haryanvi | 0.260 | 0.341 | UNSTABLE | 5 | WEAK |
| Magahi | 0.223 | 0.425 | UNSTABLE | 9 | OK |
| Angika | 0.209 | 0.212 | UNSTABLE | 14 | OK |

\* Surgujia's "stability" is an artifact, not a real result — it has only 2 groups ever, so it falls into the
row-level fallback split in all 5 seeds (never actually gets a group-disjoint test). Its apparent consistency
means the measurement bypasses the group mechanism entirely, not that it's robust.

Headline reversal from the earlier report: **Awadhi was reported as 0% accuracy (single run) and described as
"unusable."** That was one unlucky draw. Its 5-seed mean is 30.2% — weak, but completely ordinary for this tier,
not an outlier floor.

## Stage 2 — calibration

Fit isotonic calibration on VAL only (via `sklearn.calibration.CalibratedClassifierCV` + `FrozenEstimator`),
scored strictly on TEST. ECE barely moved (0.063 → 0.064) — isotonic calibration did not meaningfully fix
calibration here, which itself is useful information: the miscalibration isn't a simple monotonic-rescaling
problem, it's more likely a structural confusability problem that calibration alone can't paper over.

**Threshold curves (single split — see caveat below), coverage vs. false-confident rate:**

Level 1 (exact-variety correctness):

| Target false-confident-exact ≤ | Threshold | Coverage |
|---|---|---|
| 5% | 0.85 | 0.5% |
| 10% | 0.75 | 7.2% |
| 15% | 0.70 | 13.0% |

Level 2 (family correctness):

| Target false-confident-family ≤ | Threshold | Coverage |
|---|---|---|
| 5% | 0.70 | 13.0% |
| 10% | 0.55 | 36.3% |
| 15% | 0.45 | 54.7% |

**This is the single clearest, most useful number from the whole exercise: exact-variety identification, held
to an honest error bar, only ever covers 0.5–13% of traffic.** Family-level identification covers up to ~55% at
an acceptable error rate. The rest is, correctly, Level 3/4 territory. This is not a defect to fix — it is what
"knowing when you know" looks like in this data, and it should be presented to Evon as such, not optimized away.

Caveat carried forward honestly: these specific decimal thresholds come from one split. Given the instability
finding above, the exact numbers should be re-averaged across seeds before hard-locking production thresholds —
but the *shape* (exact detection is narrow, family-level is the real workhorse, most traffic lands in
generic/default) is a robust conclusion worth acting on today; refining the decimals is a bounded follow-up, not
a blocker.

## Stage 5 — rebuilt Prisma behavioural similarity (the relationship evidence)

Fixed three things the earlier clustering got wrong: (1) normalized substitution rate by `total_human_words`
(real word-opportunity count) instead of clip count; (2) **downweighted** universal substitutions with an IDF
weight (`log(19/dialect_count)`) instead of deleting them outright, so a pair that's common everywhere but at
very different *rates* still carries signal; (3) compared three independent methods — cosine on the
IDF-weighted vectors, Jaccard on substitution-pair *types*, and Spearman rank-correlation restricted to
substitution types the pair actually shares — and only called a relationship real when multiple methods agreed.

**Named-pair stability test:**

| Pair | Cosine | Jaccard | Spearman (shared) | Verdict |
|---|---|---|---|---|
| Magahi ↔ Bajjika | 0.461 | 0.159 | 0.591 (n=11) | **STRONG** |
| Maithili ↔ Angika | 0.805 | 0.356 | 0.731 (n=21) | **STRONG** |
| Kumaoni ↔ Khariboli | 0.458 | 0.250 | 0.681 (n=16) | **STRONG** |
| Marwari ↔ Rajasthani | 0.626 | 0.290 | 0.232 (n=18) | MODERATE (but unambiguously each other's #1 partner) |
| Surgujia ↔ Chhattisgarhi | 0.650 | 0.231 | 0.291 (n=15) | MODERATE |
| Bundeli ↔ Khariboli | 0.295 | 0.194 | 0.856 (n=13) | MODERATE |
| Kumaoni ↔ Garhwali | 0.215 | 0.159 | 0.043 (n=11) | WEAK — despite both being "Pahari" by the assumed linguistic family |
| Khortha ↔ Surjapuri | 0.091 | 0.026 | n/a (n=2) | **UNSUPPORTED** |

**Two prior conclusions are directly destroyed by this more rigorous pass:**

1. **Khortha+Surjapuri, previously proposed as a stable bucket, is unsupported.** Only 2 shared substitution
   types; cosine 0.091 (noise level). Checked Surjapuri's actual strongest partner across all 19 — it's
   **Maithili (0.682)**, not Khortha. The old pairing came from a cruder, non-opportunity-normalized,
   hard-deletion method and does not survive.
2. **The proposed 4-way Sadri+Surgujia+Awadhi+Haryanvi bucket is destroyed as a 4-way.** Pairwise:

   | Pair | Verdict |
   |---|---|
   | Sadri ↔ Surgujia | STRONG |
   | Sadri ↔ Awadhi | MODERATE |
   | Surgujia ↔ Awadhi | UNSUPPORTED |
   | Sadri ↔ Haryanvi | UNSUPPORTED (0 shared substitution types) |
   | Surgujia ↔ Haryanvi | UNSUPPORTED |
   | Awadhi ↔ Haryanvi | UNSUPPORTED |

   **Haryanvi does not belong in this group at all.** Checking each member's single strongest partner among
   all 19 confirms it: Sadri→Chhattisgarhi (0.504), Surgujia→Chhattisgarhi (0.650), Awadhi→Sadri (0.420), but
   **Haryanvi's best match anywhere is Awadhi at a mere 0.098** — essentially no relationship to anything.
   Chhattisgarhi, not any of the three, is the real anchor of this cluster. Corrected group: **Chhattisgarhi
   (anchor) + Sadri + Surgujia + Awadhi**, Haryanvi dropped to its own isolate.

**A new relationship the old analysis missed entirely:** Maithili↔Angika is the single strongest pairwise
relationship found anywhere in the whole dataset (cosine 0.805), and checking Surjapuri's real best partners
reveals a genuine triangle: Maithili↔Angika STRONG, Maithili↔Surjapuri 0.682, Angika↔Surjapuri 0.566. Maithili is
the central/richest node (3,349 rows, 41 groups); Angika and Surjapuri are both smaller and should route to it,
not stand alone.

**Confirmed true isolates — no real partner anywhere in the 19:** Haryanvi (best match 0.098), Khortha (best
match 0.091), Jaipuri (best match 0.159, weak lean toward Khariboli).

## Stage 3 — the four hierarchy levels (confirmed, built on the numbers above)

1. **Level 1 — exact variety.** Only when `top1_conf ≥ ~0.70` *and* the predicted dialect is in the A-tier
   (independently-justified) list below. ~13% of traffic at an honest ≤15% error rate — rare by design, not a bug.
2. **Level 2 — master regional profile.** `top1_conf` in roughly [0.45, 0.70), or top1 is a dialect assigned to a
   named profile below. Covers the bulk of real, usable signal (up to ~55% of traffic at ≤15% family-error).
3. **Level 3 — generic regional-Hindi.** Evidence says non-standard, but neither exact variety nor a specific
   named family clears the bar. Covers dialects whose only ties are WEAK/MODERATE-but-generic (Kumaoni,
   Khariboli, Bundeli — see below) and any low-but-nonzero-confidence prediction elsewhere.
4. **Level 4 — Hindi / default.** Confidence floor not met at all.

## Stage 4 — A/B/C/D/E re-classification of all 19 (adversarial re-evaluation, not a re-stamp of the old 5)

- **A — independent profile strongly justified:** Bhojpuri, Garhwali, **Chhattisgarhi**. (Chhattisgarhi is now
  the single most trustworthy of the three — "stable" verdict, OK groups, good anchor for its own periphery
  cluster.)
- **A → demoted to B this round:** **Rajasthani** (mean 49.6%, UNSTABLE, hard 2-district ceiling — was reported
  "Medium-High" off a single run; does not survive multi-seed testing) and **Khortha** (mean 62.8% looks decent,
  but UNSTABLE range of 38.5pp, and its data is now fully exhausted — 8/8 groups, nothing left to pull that
  could ever fix this instability). Both still used as the best available anchor for a dependent variety, but
  neither should be presented to Evon as confidently independent.
- **B — independent profile plausible, real caveat:** Rajasthani (caveat: hard ceiling, unstable), Khortha
  (caveat: unstable, unfixable), **Bajjika** (mean 65%, actually *stable* across seeds — decent signal, caveat is
  thin speaker-group diversity, not instability).
- **C — should use a broader regional/family profile (named, multi-member, real STRONG/MODERATE evidence):**
  **Maithili** (own exact-ID unreliable despite excellent data — 41 groups, never fallback; problem is intrinsic
  confusability, not volume; anchors its own "Maithili-type / Bihari-central" profile), **Khariboli, Kumaoni,
  Bundeli** (route to Level 3 generic regional-Hindi specifically — their mutual ties are real but WEAK-MODERATE
  and generic in character, not specific enough to deserve a named family the way Bihari-overlap does).
- **D — borrow softly from a stronger neighbour (asymmetric, single-neighbor lean):** **Magahi** (borrows
  Bajjika's profile — mutual STRONG tie, but Bajjika's own detector confidence, 65%, is 3x Magahi's, 22%, so this
  is not a symmetric pairing), **Angika, Surjapuri** (both borrow from the Maithili-anchored profile), **Marwari**
  (borrows Rajasthani's profile — MODERATE-but-unambiguous tie, each other's clear #1 partner).
- **E — generic regional-Hindi/Hindi fallback only:** **Haryanvi** (no real self-signal, no real partner
  anywhere — true isolate), **Jaipuri** (tiny exhausted data, UNSTABLE, weakest lean of anyone, too thin to name
  a relationship with confidence), **Sadri, Surgujia, Awadhi** land here too in terms of *exact* reliability but
  are better described under C/D since they do have a real, named anchor (Chhattisgarhi) — listed under D in the
  final table for clarity, not E.

## Stage 6 — the evidence graph (not a forced cluster count)

```
Bhojpuri (A, isolate-strong)        Garhwali (A, isolate-strong)

Chhattisgarhi (A, anchor)
   STRONG → Sadri
   MODERATE → Surgujia, Awadhi

Maithili (C, anchor, "Bihari-central")
   STRONG → Angika
   (0.682) → Surjapuri
   Angika STRONG → Surjapuri (0.566) [triangle]

Bajjika (B, anchor)
   STRONG → Magahi

Rajasthani (B, anchor)
   MODERATE-but-clear → Marwari

Khariboli (weak anchor, routes to Level 3)
   MODERATE/WEAK → Kumaoni, Bundeli

Khortha (B, true isolate — no edges above WEAK to anyone)
Haryanvi (E, true isolate)
Jaipuri (E, near-isolate, weak lean to Khariboli only)
```

Final count: **3 independent profiles (A), 2 independent-with-caveat (B) that also anchor dependents, 2 named
master regional profiles beyond the A-anchored ones (Bihari-central, Bajjika/Magahi), 1 generic-regional-Hindi
catch-all (Khariboli/Kumaoni/Bundeli), 4 soft-borrow relationships (Marwari→Rajasthani, Magahi→Bajjika,
Angika→Maithili, Surjapuri→Maithili), 3 true isolates with no usable relationship (Khortha, Haryanvi, Jaipuri).**
This is deliberately not six neat buckets — several of the old buckets didn't survive, and the honest shape is
lumpier than that.

## Stage 7 — runtime decision logic

```
Prisma transcript
      ↓
Regional detector (combined word+char TF-IDF + LogisticRegression, isotonic-calibrated)
      ↓
top1 label + calibrated confidence, top2 label + confidence, margin
      ↓
Is top1 in {Bhojpuri, Garhwali, Chhattisgarhi} AND top1_conf >= 0.70?
      ├── yes → Level 1: exact regional variety accepted
      │
      └── no
           ↓
    Does top1 (or its assigned anchor) belong to a named profile AND top1_conf >= 0.45?
           ├── yes → Level 2: master regional profile
           │          (Bhojpuri-family / Chhattisgarhi-periphery / Bihari-central / Bajjika-Magahi / Rajasthani-Marwari)
           │
           └── no
                ↓
         top1_conf >= ~0.20 (clearly not defaulting to Hindi/Khariboli-as-noise)?
                ├── yes → Level 3: regional-Hindi (non-standard, family unresolved)
                └── no  → Level 4: Hindi / default
```

Thresholds above are from Stage 2's single-split curves; treat the 0.70/0.45/0.20 cut points as directionally
right (confirmed by the coverage/error tradeoff shape) but schedule a quick multi-seed re-average before
hard-locking them for production — this is the one piece of "deeper research" being explicitly deferred per the
brief's own instruction not to let this become an endless project.

## Stage 8 — frozen provisional map (all 19)

| Variety | Own profile? | Master profile if not | Soft-borrow | Exact-detection quality | Fallback | Primary evidence | Main caveat |
|---|---|---|---|---|---|---|---|
| Bhojpuri | **A** | — | — | Good (71% mean, borderline-stable) | Level 1 | 27 groups, OK severity | Mild seed sensitivity (64-78%) |
| Garhwali | **A** | — | — | Good (79% mean, borderline-stable, most consistently high) | Level 1 | 4 groups but hard ceiling confirmed (only 2 districts ever exist) | Can never improve further; accept as-is |
| Chhattisgarhi | **A** | — | — | Good, most trustworthy (62% mean, genuinely stable) | Level 1 | 21 groups, OK, anchors its own periphery cluster | None material |
| Rajasthani | **B** | Rajasthani-family | anchors Marwari | Mediocre, UNSTABLE (50% mean, 25pp range) | Level 2 (own-label), Level 1 only if conf spikes | Best partner for Marwari by far (0.626) | Hard 2-district ceiling; demoted from earlier "independent" call |
| Khortha | **B** | — (true isolate) | none | Decent mean but UNSTABLE (63% mean, 38.5pp range) | Level 2/3 depending on live confidence | Fully exhausted data (8/8 groups) | Instability is now permanent/unfixable |
| Marwari | **D** | Rajasthani-family | → Rajasthani | Mediocre (54% mean, borderline) | Level 2 via Rajasthani-family | Mutual #1 partner with Rajasthani | Shares Rajasthani's hard ceiling |
| Maithili | **C** | Bihari-central (self-anchored) | — | Weak despite rich data (42% mean, UNSTABLE) | Level 2 (as family, not exact) | 41 groups — best speaker diversity of any dialect | Problem is confusability, not data; unfixable by more pulling |
| Angika | **D** | Bihari-central | → Maithili | Weak (21% mean, UNSTABLE) | Level 2 via Bihari-central | STRONG tie to Maithili (0.805, strongest pair in dataset) | Intrinsically confusable |
| Surjapuri | **D** | Bihari-central | → Maithili | Mean looks ok (57%) but UNSTABLE, tiny exhausted data | Level 2 via Bihari-central | Real tie to Maithili (0.682) and Angika (0.566) | Only 194 total rows ever; SEVERE groups |
| Bajjika | **B** | — (anchor) | anchors Magahi | Decent and genuinely stable (65% mean) | Level 1 possible at high conf, else Level 2 | Stable across seeds; real anchor for Magahi | Still only 6 groups (WEAK), thin speaker diversity |
| Magahi | **D** | Bajjika-Magahi overlap | → Bajjika | Weak (22% mean, UNSTABLE, worst range of all) | Level 2 via Bajjika | STRONG tie to Bajjika (mutual #1) | Own data OK (9 groups) — purely a confusability problem |
| Khariboli | **C** | Generic regional-Hindi | — | Weak (33% mean, borderline) | Level 3 | Closest variety to standard Hindi by design | Not fixable — the "problem" is being genuinely close to Hindi |
| Kumaoni | **C** | Generic regional-Hindi | — | Weak (37% mean, UNSTABLE) | Level 3 | Best tie is Khariboli (0.458), not its assumed Pahari sibling Garhwali (0.215, WEAK) | Family assumption (Pahari) not supported by evidence |
| Bundeli | **C** | Generic regional-Hindi | — | Weak (37% mean, UNSTABLE) | Level 3 | Moderate tie to Khariboli (0.295) | Thin, generic evidence only |
| Sadri | **D** | Chhattisgarhi-periphery | → Chhattisgarhi | Weak (33% mean, UNSTABLE) | Level 2 via Chhattisgarhi-periphery | STRONG tie to Surgujia, strongest overall to Chhattisgarhi (0.504) | Tiny groups (4), WEAK severity |
| Surgujia | **D** | Chhattisgarhi-periphery | → Chhattisgarhi | Weak but oddly stable only because it bypasses the group split (36% mean) | Level 2 via Chhattisgarhi-periphery | Strongest tie of anyone to Chhattisgarhi (0.650) | Only 2 groups ever; "stability" is an artifact |
| Awadhi | **D** | Chhattisgarhi-periphery | → Chhattisgarhi/Sadri | Weak (30% mean, borderline — NOT 0% as previously reported) | Level 2 via Chhattisgarhi-periphery | Moderate tie to Sadri (0.420) and Chhattisgarhi (0.391) | Previous "unusable" label was a single-run artifact; corrected here |
| Haryanvi | **E** | — | none | Weak (26% mean, UNSTABLE) | Level 4 (Hindi/default) | No real self-signal, no real partner anywhere (best match 0.098) | True isolate; was wrongly bucketed with Sadri/Surgujia/Awadhi before |
| Jaipuri | **E** | — | weak lean only, not asserted | Weak (29% mean, UNSTABLE, tiny n) | Level 4 (Hindi/default) | Best match anywhere only 0.159 (Khariboli) | 87 total rows ever; too thin to name any relationship with confidence |

**Counts:** 3 independent profiles (A) · 2 independent-with-caveat (B) · 2 named master regional profiles beyond
the A-anchors (Bihari-central: Maithili+Angika+Surjapuri; Bajjika-Magahi overlap) · 1 generic regional-Hindi
catch-all (Khariboli+Kumaoni+Bundeli) · 4 soft-borrow relationships (Marwari→Rajasthani, Magahi→Bajjika,
Angika→Maithili, Surjapuri→Maithili) · 1 additional periphery profile anchored by an independent dialect
(Chhattisgarhi+Sadri+Surgujia+Awadhi) · 2 true isolates with Hindi-only fallback (Haryanvi, Jaipuri).

**What changed from the pre-today picture, stated plainly:** Rajasthani and Khortha lost their "independent"
status; Awadhi's "unusable" label is corrected to "weak but normal"; Khortha+Surjapuri as a pair is dead;
Haryanvi is removed from the Chhattisgarhi-periphery bucket entirely; a new, strong Maithili-Angika-Surjapuri
relationship was found that the earlier clustering missed; Kumaoni's real tie is to Khariboli, not to Garhwali as
the assumed Pahari family would suggest.
