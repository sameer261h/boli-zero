# Phase 2 summary and caveats (read with PHASE4_REPORT.md)

## Hindi data (Vaani `ARTPARK-IISc/Vaani-transcription-part`, `audio/Hindi`)
- 250 parquet shards (193 train / 29 val / 28 test), accessible with the injected HF token, no extra gating.
- Same schema as the regional shards: `audio, language, gender, state, district, transcript, referenceImage`.
- Footers read for 30 evenly spaced shards (8 test / 8 validation / 14 train): 72,690 clips (about 2,400 per shard,
  so roughly 600,000 across all 250 shards, extrapolated, not counted).
- Sample: 4,000 clips, water-filled across 212 state|district|gender cells (cap 29 per cell), 26 states, 3,103 distinct prompts.
  Bihar 1,081 / Uttar Pradesh 515 / Chhattisgarh 323 / Rajasthan 271 / Jharkhand 235 ...
- Prisma: `api.vachana.ai/stt/v3`, same request code as the regional pull (`call_prisma`). Main pass about 8,000 HTTP calls
  (3,815 OK, 4,190 rate-limited 429 that the shared backoff absorbed, 1 Cloudflare 403); retry pass fixed 22 of 23 errored clips.
  Final: 4,000 clips, 1 error (persistent 403), 2 empty transcripts -> 3,997 used.
- Same prompt images as the regional data: 48.5% of Hindi clips are on prompt images that also occur in the regional data
  (both GENERIC and SPECIFIC image types appear in both).

## Spot-check: are Bihar/UP "Hindi" clips really Hindi?
- Read 50 random Bihar/UP clips (printed in `phase2_report.txt`): the large majority are ordinary Hindi. About 2-3 of 50
  show regional features (e.g. `आय रहे है`, `ई तालाब`, `इ तालाब`, `बोहत`). So a few percent of the "Hindi" label is
  regionally coloured Hindi, which is the realistic production case.
- Automatic count with 27 strong single-word regional markers: 9.9% of Bihar/UP clips and 10.0% of the other states fire at
  least one (mostly Rajasthani/Jaipuri entries that are short generic words), so that count is not a clean contamination estimate.

## Caveats that limit every number
1. No speaker IDs. Splits use state|district|gender|prompt (almost row-level: 20,843 groups for about 25,000 clips) or
   state|district|gender (strict, only 106 groups for the regional data). Strict-split recalls are the honest ones.
2. Several varieties have only 2-6 strict groups (Surgujia 2, Surjapuri 2, Garhwali/Kumaoni/Marwari/Rajasthani/Sadri 4, Jaipuri 4),
   so their ratings are low-confidence even where the numbers look good (Surjapuri "clear" rests on 194 clips and 2 cells).
3. The Hindi markers are mostly picture-description vocabulary (`तस्वीर`, `पिक्चर`, `मुझे`, `आ रहा है`). They passed the
   same-prompt topic check, but this data cannot tell real Hindi usage from a collection or instruction-wording difference
   between the Hindi and regional sets. Treat the Hindi marker set as unproven until checked on Hindi from a different source.
4. Sessions were not tested; there are no real call/turn IDs.
5. Evon grounding check: NOT RUN (no `BOLI_EVON_URL`, no reachable Modal endpoint).
6. Hindi-vs-regional operating point maximises balanced accuracy and was not capped on Hindi false flags, as instructed.
   It flags about a third of Hindi clips; the SVM ceiling flags about 33% too at about 0.80 unseen-variety recall.
7. VARIANT FLAG count: 1 (copula `छे/छै/छी/छा` and `हे/हवे` listed as separate markers; no variant work was done).
