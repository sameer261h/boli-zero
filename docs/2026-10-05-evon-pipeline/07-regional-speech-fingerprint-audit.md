# 07: Regional Speech Fingerprint — audit report (Parts 1–3, pre-Evon)

Renamed per explicit instruction: internally this module is called **Regional Speech Fingerprint**, not
"language detection" — Bhojpuri/Magahi/Maithili vs. Hindi gets linguistically and politically messy fast, and we
don't need to take a position on which varieties are "languages" vs. "dialects" to build this.

**Zero Evon calls in this report.** Everything below is a statistical audit of the 24,986 Prisma transcripts we
already collected, using only `prisma_transcript` (what Evon actually sees in production — not the human
reference). Code: `experiments/2026-10-05-evon-pipeline/scripts/regional_fingerprint_audit.py`. Full numeric
results: `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/regional_fingerprint_audit/audit_results.json`.

This is explicitly a "show the work before spending more budget" report, not a finished system. Several findings
below are limitations we found by actually trying, not things I'm flagging defensively — one of them (a) is a real
bug that made four dialects' results meaningless until it was caught and fixed mid-run.

---

## 0. What Prisma exposes beyond the transcript (answered directly, no new work needed)

Verified live, fresh, as part of this pass: Prisma's REST endpoint (what collected all 24,986 rows) returns
**only** `success`, `request_id`, `transcript`, `model`, `processing_time`, `end_to_end_latency`. The two timing
fields are server-side compute latency, not speech timing — not pause structure, not duration, not anything about
the audio itself. No confidence, no timestamps, no N-best, no diarization, no VAD. Our saved dataset has only
transcript text — even the thin latency fields were discarded during collection to keep files small, so there is
nothing to mine here beyond text, by construction.

One avenue not yet tested: a documented streaming WebSocket endpoint (`wss://api.vachana.ai/stt/v3/stream`) adds a
few timing/segment fields — still no confidence/N-best/diarization among named fields, plus one undocumented `raw`
field of unknown content. A plain HTTPS probe against it returned 404, which is inconclusive (WebSocket endpoints
don't answer plain GET) — a real test needs a WS handshake, not yet built. Separately, this is cheap to test (1-2
calls) if useful later; it is not an Evon-budget concern.

The "Prisma struggles in a structured way" angle is real but conceptually different from exposed metadata — it's
visible in the transcript text itself when diffed against a human reference (already done in
`docs/2026-10-05-evon-pipeline/06-*.md`: consistent deletion of dialect deictics, consistent grammatical
normalization). That diff is only computable where we have ground truth — i.e. on this audit corpus — not at
inference time, since Evon never sees a reference transcript in production. What *is* usable live is pattern-
matching against known Prisma-mangling signatures derived here, not an actual diff.

---

## 1. Usable samples per dialect

24,900 of 24,986 rows have a non-empty Prisma transcript (86 rows — mostly a handful per dialect — came back
empty, excluded).

| Dialect | Usable rows | Group-proxy count (see §2) |
|---|---:|---:|
| Bhojpuri | 4,849 | 27 |
| Chhattisgarhi | 3,687 | 21 |
| Maithili | 3,349 | 41 |
| Rajasthani | 2,440 | 4 |
| Garhwali | 1,893 | 4 |
| Marwari | 1,450 | 4 |
| Kumaoni | 1,141 | 4 |
| Magahi | 930 | 9 |
| Bajjika | 804 | 2 |
| Khortha | 799 | 7 |
| Khariboli | 717 | 19 |
| Sadri | 678 | 4 |
| Angika | 557 | 14 |
| Surgujia | 526 | 2 |
| Bundeli | 447 | 6 |
| Surjapuri | 194 | 2 |
| Awadhi | 187 | 9 |
| Haryanvi | 165 | 5 |
| Jaipuri | 87 | 4 |

Row count ranges almost 56x (87 to 4,849) — any evaluation has to report per-dialect numbers, never a single
blended accuracy, or the small dialects become statistically meaningless noise.

## 2. How we split — and the real leakage problem this surfaced

**There is no speaker-ID field anywhere in the Vaani metadata.** Only `state`, `district`, `gender`, `language`,
`referenceImage`. The best available proxy for "speaker group" is `state+district+gender` — and this is a weak
proxy, not a real one: it almost certainly collapses many distinct individual speakers into one group. **This is
reported as a hard limitation, not something we can design around with the data in hand.**

The group-proxy counts above show the severity concretely: Bajjika, Surgujia, and Surjapuri have only **2 groups
total** covering 194–804 rows each. Rajasthani, Garhwali, Marwari, and Kumaoni — some of our largest dialects by
row count — have only **4 groups** each, meaning 1,000+ rows are sorted into just 4 buckets. For these dialects, a
"speaker-disjoint" split is barely more informative than a random split, because the "speakers" being held out are
really just 1-2 recording locations.

**A real bug this caused, caught mid-run**: a standard group-disjoint split (`GroupShuffleSplit`) assigns whole
groups to train/val/test. With only 2 groups, there's a real chance both land in train+val and none in test — and
that's exactly what happened on the first run: **Bajjika, Khortha, Surgujia, and Surjapuri got zero test rows**,
making their confusion-matrix rows silently all-zero. This wasn't a hypothetical risk I'm flagging defensively —
it actually broke the evaluation until caught and fixed.

**Fix applied**: dialects where group-disjoint splitting can't guarantee ≥15 rows in both val and test fall back to
a plain stratified row-level split for *that dialect only* — explicitly logged, not silently merged in as if
equivalent to the real thing. On this run, **9 of 19 dialects required the fallback**: Rajasthani, Marwari,
Bajjika, Khortha, Sadri, Surgujia, Surjapuri, Haryanvi, Jaipuri. For these nine, our held-out accuracy numbers are
**not speaker-independent** — they're measuring "performance on sentences from recording sessions we've already
seen," which is a real-but-weaker guarantee than the other ten dialects get. Final split: 14,430 train / 4,684 val
/ 5,786 test.

**Honest implication**: for roughly half the dialects, we do not currently have enough speaker diversity in this
dataset to claim genuine speaker-independent evaluation. More data collection (or sourcing more Vaani shards, if
more districts/recording sessions exist for these dialects) would be needed to fix this properly, not a smarter
split algorithm.

## 3. Strongest discriminating feature families

Three families were computed from the **train split only** (val/test never touched during feature derivation):

- **Lexical markers** (word unigrams/bigrams, log-odds z-score vs. rest of corpus) — the strongest, cleanest
  signal. Examples: Bhojpuri `बा`(z=43), `एगो`(z=15); Bajjika `हई`(z=39), `गो`(z=16), `तीनगो`/`दुगो`/`चारगो`
  (numeral-classifier forms, z≈11); Chhattisgarhi `हे`(z=43), `दिखत`(z=31); Khortha `हो`(z=32). These are
  mostly copulas, discourse particles, and a few content words — consistent with what the earlier
  human-transcript-derived `markers_v2.json` found, now confirmed on Prisma's *own output* specifically.
- **Word-ending suffixes** (morphology proxy) — real signal, but noisier and more erratic than lexical markers.
  Several extreme log-odds ratios (Garhwali `-णि` x1017, Surgujia `-जग` x323) come from suffixes with very low
  absolute frequency (5-10 occurrences) — these ratios are driven by small-sample noise, not robust morphological
  rules, and should not be trusted at face value without more data. The more credible morphology signals are the
  ones with both a high ratio *and* reasonable frequency (e.g. Bajjika's cluster of verb-aspect endings `-इत`,
  `-ैत`, `-लै`; Rajasthani's `-भो`, `-रु`).
- **Character n-grams** — captured mostly the same information as word markers plus morphology, via a different
  route; didn't surface qualitatively new signal in this pass.

**Did richer features materially beat marker words?** Honestly, barely, on raw accuracy: word-only TF-IDF got
54.9% exact accuracy, char n-grams 55.5%, the combined char_wb representation 54.3% — all within ~1 point of each
other. Where the richer representation *did* help meaningfully was **calibration** (§7) — the combined mode had
the lowest ECE (0.140 vs. 0.180–0.199 for the simpler modes), i.e. its confidence scores were somewhat more
trustworthy, even though its raw accuracy wasn't better. **Answering the explicit question**: morphology +
subword patterns did not unlock a new tier of accuracy over lexical markers in this pass — the lexical markers
were already capturing most of the available signal. This could change with a larger dataset (several of the
suffix signals are currently noise-limited), but as collected today, the old marker-word approach is not leaving
large amounts of signal on the table from these particular feature families.

## 4. Separable vs. intrinsically confusable dialects

Against a **22.5% majority-class baseline** (always guessing Bhojpuri, the largest class in this test set), the
best model (char n-grams) reached **55.5% exact accuracy** and **72.0% family-level accuracy** (see §8 for family
groupings) on the held-out test set — a real, substantial lift (+33 points exact), not noise.

The explicitly requested Bihari-family confusion matrix (char mode, rows=true, cols=predicted):

| True \ Pred | Bhojpuri | Magahi | Maithili | Angika | Bajjika |
|---|---:|---:|---:|---:|---:|
| **Bhojpuri** | 997 | 39 | 22 | 5 | 11 |
| **Magahi** | 25 | 47 | 54 | 7 | 13 |
| **Maithili** | 32 | 51 | 363 | 44 | 81 |
| **Angika** | 7 | 13 | 28 | 9 | 1 |
| **Bajjika** | 8 | 16 | 10 | 2 | 104 |

- **Bhojpuri is cleanly separable** (997/1,074 ≈ 93% correct within this cluster) — it has the most training data
  (largest dialect) and the most distinct lexical profile (`बा`, `एगो`, `बाटे` at very high z-scores).
- **Bajjika is separable once actually measured correctly** (104/140 ≈ 74%) — its numeral-classifier markers
  (`तीनगो`/`दुगो`/`चारगो`) and copula `हई` are quite distinctive. (This dialect is also one of the 9 using the
  row-level fallback split, so treat this number as less rigorously validated than Bhojpuri's.)
  - **Angika is barely separable at all** (9/58 ≈ 16% recall) — it gets scattered across Bhojpuri, Magahi,
    Maithili, and Bajjika roughly evenly. This matches the earlier session's finding (`markers_v2.json`) that
    closely-related Bihari dialects share too much vocabulary for reliable lexical discrimination — Angika in
  particular appears to sit in the overlap zone of all its neighbors rather than having a clearly distinct profile.
- **Magahi is weak** (47/146 ≈ 32% recall, confused roughly equally with Maithili and Bhojpuri) — smaller dataset
  (930 rows) likely compounds this.
- **Maithili has the most absolute confusion volume** (363 correct, but 81 misclassified as Bajjika, 51 as
  Magahi, 44 as Angika) — it's also the dialect most other Bihari varieties get mistaken *for*, suggesting its
  lexical profile is closer to a "central" or default Bihari-family pattern than a distinctive one.

**Honest conclusion**: exact 19-way identification is reliable for distinctive, well-resourced dialects (Bhojpuri,
and apparently Bajjika) and unreliable for the Angika/Magahi tier specifically — consistent with, not contradicting,
the earlier classification failure. Family-level identification (72%) is substantially more trustworthy than
exact-label identification (55%) across the board, and this gap is largest exactly within the Bihari cluster.

## 5. Is the old marker-only method leaving signal on the table?

Partially, but not dramatically, per §3. The clearest gain over a pure hand-picked marker-word approach isn't a
different feature family — it's **systematic, corpus-derived discovery** of markers (log-odds z-scores on the
actual Prisma-output distribution) rather than hand-picking, which the project was already moving toward with
`markers_v2.json`. The new contribution here is doing this specifically on **Prisma's output**, not the human
reference — which matters because that's what Evon will actually see, and Prisma's own transformation behavior
(see §0) could in principle shift which words are discriminative relative to the ground-truth-transcript-derived
markers. A direct overlap comparison between the two marker lists (old human-transcript-derived vs. new
Prisma-output-derived) hasn't been run yet — flagged as a natural next check, not done in this pass.

## 6. Proposed fingerprint representation

Not yet built as an Evon-facing prompt (that's Part 4/8 work, intentionally deferred). Based on what's separable
(§4), the representation should **not** force a single 19-way label. Directionally, something like:

```
REGIONAL_EVIDENCE
family: Bihari | confidence: 0.81
candidates:
  Bhojpuri    0.68   evidence: बा, एगो, बाटे
  Bajjika     0.12   evidence: (weak/shared markers)
  Maithili    0.08
  exact_variety: Bhojpuri (confident)  |  OR  |  exact_variety: uncertain (Bihari family only)
```

— i.e. hierarchical (family first, exact variety only when warranted), matching §4's finding that family-level
accuracy is the more trustworthy signal. The exact confidence numbers need real calibration work (§7) before they
mean anything, not cosmetic placeholders.

## 7. Confidence calibration — currently poor, flagged plainly

Expected Calibration Error (ECE) on held-out test: word mode 0.180, char mode 0.199, combined mode 0.140. These
are **not good** — for reference, a well-calibrated classifier scores well under 0.05. This means the model's own
`predict_proba` confidence values do **not** currently track real accuracy reliably — a stated "0.81 confidence"
prediction is not trustworthy at face value yet. Per the explicit instruction not to invent confidence values
unless they empirically correlate with accuracy: **they currently don't, well enough.** This needs a dedicated
calibration pass (temperature scaling or isotonic regression fit on the validation split, which exists and hasn't
been touched for this purpose yet) before any confidence number is exposed downstream. Not done in this pass —
correctly sequenced to come after the feature/representation questions above, not before.

## 8. Independent evaluation sources — not yet sourced

This is Part 5/6 work and **has not been done yet**, correctly, per the instruction to pause before the big
experiment. What's needed: real, independently-sourced material (external dialect corpora, published linguistic
examples, independently-labeled audio/video) for at least Bhojpuri, Maithili, Magahi, Chhattisgarhi, Garhwali,
Rajasthani/Marwari, plus Hindi/Hinglish/English — specifically **not** LLM-generated "dialect-like" sentences as
the primary evaluation set, since those risk exaggerating stereotypical markers and making the task artificially
easy. Sourcing this properly is its own research task (likely needs targeted web search for existing academic
dialect corpora or linguistically-documented example sentences) — not attempted here since it wasn't asked for in
this pass, and doing it hastily would undermine the whole point of having a genuinely independent eval set.

## 9. Proposed A/B design (not yet run)

As specified in the brief — conditions A (transcript only) through F (deterministic classifier + Evon as
second-stage reasoner) — against the external eval set from §8, scoring exact/top-2/family/Hindi-vs-regional
accuracy, false-confident-classification rate, abstention quality, and calibration. Not run. Given §7's finding
that our own classifier's confidence isn't yet trustworthy, condition E (deterministic classifier alone) needs the
calibration fix from §7 before it's a fair comparison point — testing an uncalibrated classifier against Evon
would bias the comparison.

## 10. Reasons this experiment could still mislead us

Being explicit about this rather than letting it go unsaid:

- **The 9-dialect fallback-split problem (§2) is the single biggest risk.** Accuracy numbers for Rajasthani,
  Marwari, Bajjika, Khortha, Sadri, Surgujia, Surjapuri, Haryanvi, and Jaipuri are optimistic relative to true
  held-out performance, because the "held-out" rows for those dialects likely still share a recording session
  (and thus a specific speaker's voice/microphone/background) with training rows. We don't know by how much
  without more diverse data.
- **Recording-session confounds beyond speaker identity**: `district` likely also correlates with recording
  equipment, background noise profile, and interview script/prompt set (visible in the `referenceImage` field —
  many clips across dialects reference the same generic prompt images, suggesting a shared elicitation protocol).
  A classifier could partly be learning "which recording batch" rather than "which dialect," and our group proxy
  can't fully separate these.
- **Garhwali and Maithili both show some rows recorded in Uttarakhand/Uttarkashi** in this metadata — geography
  and self-reported dialect label don't always align cleanly in a crowd-collected dataset; a small amount of
  mislabeling is plausible and not something this audit can detect or correct.
- **Utterance-length sensitivity is real and large**: accuracy on 1-3 word utterances (30-33%) is barely better
  than random family-guessing, while 20+-word utterances hit 58-59%. Any production deployment will see plenty of
  short utterances, and this pattern means the fingerprint will be systematically less useful exactly when the
  customer says less — a real, not hypothetical, constraint on how this gets used.
- **Poor calibration (§7) means any A/B test run before fixing it risks comparing Evon against an unfairly
  weak/noisy deterministic baseline** — calibration-induced noise could masquerade as "Evon beats the classifier"
  when it's really "the classifier's confidence output isn't trustworthy yet."

**Overall**: this audit found real, usable signal (char/word markers give meaningful lift over majority-class
baseline, especially at family level) but also found two genuine, non-cosmetic problems (speaker-leakage risk for
half the dialects, and poor confidence calibration) that would make an immediate Evon A/B test premature. Fixing
calibration is cheap (local computation, no new calls). Fixing the speaker-leakage problem requires more diverse
data, which may not be available without a new collection effort.
