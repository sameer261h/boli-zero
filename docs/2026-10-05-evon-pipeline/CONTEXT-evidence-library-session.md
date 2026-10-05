# Session context: per-variety text markers that survive Prisma (boli-zero)

Handoff file for a fresh cloud session. Everything below is what was decided, built, measured and left open in one long session
(2026-10-05). Branch: `claude/hindi-regional-evidence-library-v5c1aa` (pushed, no PR opened). Repo: `sameer261h/boli-zero`.
Last pushed commit when this file was written: `b08bff7`. Read `data/markers/PHASE4_REPORT.md` and
`data/markers/PHASE2_AND_CAVEATS.md` next to this file for the full tables.

---------------------------------------------------------------------------------------------------------------------------

## 1. What the project is
boli-zero: a Hindi-stack-to-Bhojpuri adapter on Gnani **Prisma** (STT, Hindi mode), **Timbre** (TTS) and **Evon** (LLM, self-hosted
on Modal, OpenAI-compatible, `BOLI_EVON_URL`). Earlier docs (`docs/2026-10-05-evon-pipeline/01-18`) hold prior work. This session
added a marker library so Evon could identify which language/variety a user speaks from Prisma text and reply in it.

## 2. The goal as it finally stood (scope CHANGED twice; the last version wins)
1. The first request was a huge 20-section "evidence library" spec (evidence groups, session accumulator, 5 arms A-E, grounding
   experiment, phonetic safeguard, hard-Hindi destruction test, audio necessity...). I planned it as 13 phases and was told to
   **replace it**.
2. Final scope: for each of **20 groups (19 regional varieties + ordinary Hindi)** produce a clear, validated set of **text markers
   that survive Prisma**, so Evon can identify the language and reply in it. Speaker-agnostic. **Optimise for correct
   identification, NOT for "never flag Hindi"** (a rare reply in the wrong dialect to a Hindi speaker is acceptable).
   Wrong-meaning Prisma errors are rare: ignore them. Skip evidence groups, session scoring, combination search, five-arm comparison.
3. Deliverables: one marker set per group (words, endings, 2-3-word pairs, consistent Prisma habits) revalidated against Hindi and the
   other 18; a confusion table; a rating per group (clear / shared with neighbours / not separable from text); a Hindi-vs-regional
   score tested leave-one-variety-out; an Evon grounding check (markers vs extra transcript context; "not run" if Modal unreachable).

## 3. User rules that still apply (and how they changed)
- **VARIANT RULE:** do NO work on spelling / sound / accent / transliteration variants (bahut/bohot, v/w, sh/s, vowel length, nasal
  marks, है/हैं). If one is hit, print one line beginning `VARIANT FLAG:` and keep going. When markers are complete, STOP and ask the
  user whether to do variant work; wait for a yes. **Status: 1 VARIANT FLAG printed** (copula `छे/छै/छी/छा` and `हे/हवे` are
  separate markers; not merged). **The question "do variant work now?" is still unanswered.**
- **Shared `clean(text)`** for every phase: remove Vaani tags `<...>` `[...]` `{...}`; remove punctuation and danda; drop nasal marks
  (anusvara, chandrabindu) and nukta; digits to one form (ASCII); keep Latin-script words (I lower-case them, an assumption); split
  on spaces. Implemented in `scripts/markers_common.py`.
- Drop place and person names from markers (only a crude district-concentration filter was applied; no name list).
- Process: phases 1+2 parallel, then 3, then 4; originally "pause after each phase". The user later said **"run Phase 3 then 4
  straight through, do not wait"** and **"push is now allowed, no PR"** (this overrode an earlier "local commits only"). A stop hook
  keeps asking to commit+push untracked files; the user said to ignore it for raw data.
- Exclude from git: raw/large data (`hindi/` parquet, audio, anything >25 MB). Small summary files are fine.
- The user wants short answers and cuts off long waits ("don't waste time", "ETA?"). Tool calls that block with `sleep` loops were
  rejected twice: use `run_in_background` + a completion notification instead.

## 4. Data facts (verified)
- Regional corpus: Vaani (`ARTPARK-IISc/Vaani-transcription-part`, gated, HF token injected by the proxy). 19 jsonl files
  `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/<Variety>.jsonl`, 25,139 lines -> **24,962 usable** after dropping
  errors/empties/dups. Schema: `dialect, shard, row_idx, human_transcript, duration_sec, meta{language,gender,state,district,
  referenceImage}, prisma_transcript, latency_sec`. Prisma text is punctuation/tag-free; human text keeps Vaani tags.
- 19 varieties (clips): Bhojpuri 4847, Chhattisgarhi 3687, Maithili 3348, Rajasthani 2440, Garhwali 1893, Marwari 1450, Kumaoni 1141,
  Magahi 930, Bajjika 861, Khortha 809, Khariboli 717, Sadri 678, Angika 557, Surgujia 526, Bundeli 447, Surjapuri 194, Awadhi 187,
  Haryanvi 164, Jaipuri 86.
- **No speaker IDs.** Group proxies: `state|district|gender|prompt` ("primary", 20,843 groups for ~25k clips, so near row-level, leaky)
  and `state|district|gender` ("strict", only 106 groups for the regional data; several varieties have 2-6). Prompt = `referenceImage`
  (each clip describes a picture). ~45% of regional clips are on images unique to their variety, so picture-topic words can leak.
- **Docs 17/18 claim there is no Hindi data; that is WRONG** (not corrected in the docs; the user said "no edits to other docs" in
  the last scope). Vaani has `audio/Hindi`: 250 parquet shards (193 train/29 val/28 test), same schema, no extra gating. Footers of
  30 evenly spaced shards (8 test/8 val/14 train) = 72,690 clips (~2,400/shard; ~600k total, extrapolated).
- **Hindi sample:** 4,000 clips water-filled over 212 state|district|gender cells (cap 29), 26 states, 3,103 prompts; Bihar 1,081,
  UP 515, Chhattisgarh 323, Rajasthan 271, Jharkhand 235 ... 48.5% of Hindi clips use prompt images that also occur in regional data.
  Prisma via `api.vachana.ai/stt/v3` with the *same* `call_prisma` as `prisma_fingerprint_pull.py` (hi-IN, verbatim, retries).
  Main pass ~8,000 HTTP calls (3,815 OK, 4,190 rate-limit 429s absorbed by backoff, 1 Cloudflare 403); retry pass fixed 22/23 errors.
  Final: 4,000 clips, 1 error, 2 empty -> **3,997 used**. Prisma rate limit (~1 call/s effective) is the throughput bottleneck.
- Spot-check of 50 Bihar/UP "Hindi" clips: mostly ordinary Hindi; ~2-3/50 show regional forms (`आय रहे है`, `ई तालाब`, `बोहत`).
  Raw data files are NOT committed: `data/prisma_fingerprint/Hindi.jsonl`, `Hindi.part{0,1,2}.jsonl`,
  `hindi/hindi_metadata.parquet`, `hindi/sample_index.csv` (untracked on purpose; regenerate with the scripts in section 7).

## 5. Method (Phase 1/3, `scripts/phase1_markers.py`)
Presence features per utterance on cleaned Prisma tokens: word unigrams, 2/3-char endings of words with len>=4, word bigrams and
trigrams. Split group-disjoint **within each variety** 60/20/20 (train/val/test) by the group key (primary or `--strict`), 5 seeds each.
Markers are derived on train only; K (top-K per variety from 10/25/50/100/200) is chosen on val; everything is reported on test.
Marker gate per variety V (log-odds style, one-vs-rest against the macro-average of the other groups):
df>=8 utterances, >=6 groups, if V has >=3 districts then >=2 districts and no district >60% of hits (place/person-name heuristic),
lift f_V/macro-others >= 3, f_V >= 0.7 x best single other variety (shared markers allowed, listed in `shared_with`), Wilson lower
bound of f_V >= 2 x others. Longer units are dropped if a kept constituent already explains their coverage. Utterance score = sum of
weights of distinct markers present; predict argmax, abstain when nothing fires. `baseline()` = linear SVM on word 1-2gram + char
2-4gram tf-idf, balanced classes, same splits: the statistical ceiling.
`scripts/phase1_report.py` aggregates 10 runs: **stable marker = in top-50 of >=6 of 10 runs**; confusion pooled; clusters from SVM
confusion >=15%; **rating rule (fixed in advance):** clear = strict-split marker recall >=0.40 and >=10 stable markers; shared with
neighbours = not clear but recall counting confusion partners (>=15%) as correct >=0.50; else not separable; LOW-CONF flag if <4
state|district|gender cells or <300 clips. `--hindi` on both scripts adds Hindi as a 20th class (Phase 3).
A prompt-leak gate (>=5 prompts, no prompt >30% of hits, matched-prompt lift) was built and then REMOVED at the user's request
(it changed 1-7 markers per variety and did not remove Jaipuri's topic words); topic words are instead caught in Phase 4a.
**Mistake to know about:** I told the user the gate was "still in the file" after an interrupted command had already removed it; the
regenerated results are consistent with the gate-free code (verified: results reproduced exactly after a refactor).

## 6. Results
**Phase 1 (19 regional only), test macro-recall over 5 seeds:** marker-only 0.26-0.31 (primary split), 0.17-0.22 (strict); SVM ceiling
0.46-0.48 (primary), 0.26-0.41 (strict). 19-way identification from Prisma text is hard even for the flexible model; the primary split
flatters both (shared speakers across splits).

**Phase 3/4 ratings (20 groups, strict-split marker recall / SVM ceiling):** clear = Bhojpuri (0.60/0.67, 42 markers),
Chhattisgarhi (0.49/0.60, 41), Garhwali (0.53/0.63, 47), Surjapuri (0.58/0.32, 14, LOW-CONF: 194 clips, 2 cells).
Shared with neighbours = Kumaoni (exact 0.20; counting Garhwali partner 0.69). Not separable = Angika, Awadhi, Bajjika (0 markers),
Bundeli, Haryanvi, Jaipuri, Khariboli, Khortha, Magahi, Maithili, Marwari, Rajasthani (many markers but strict recall 0.03),
Sadri (0 markers), Surgujia, **Hindi** (marker 0.16 / SVM 0.45).
**Stable markers <10 (8 varieties; I once said 10, wrong):** Angika 2, Awadhi 1, Bajjika 0, Bundeli 6-7, Haryanvi 1, Khortha 2,
Magahi 1, Sadri 0. Bajjika/Sadri have ENOUGH clips (861/678); no markers because everything they share is shared with a neighbour
(Bajjika~Bhojpuri/Maithili, Sadri~Chhattisgarhi/Bhojpuri) and fails the lift/neighbour gate, plus only 4-6 strict cells.
SVM clusters (confusion >=15%): {Angika, Magahi, Maithili, Surjapuri}; {Awadhi, Bhojpuri, Chhattisgarhi, Sadri, Surgujia};
{Bundeli, Garhwali, Jaipuri, Khariboli, Kumaoni, Hindi}; {Haryanvi, Marwari, Rajasthani}. Marker confusions: Kumaoni->Garhwali 35%,
Surgujia->Chhattisgarhi 33%, Bajjika->Bhojpuri 33%, Hindi->Kumaoni 24%/Jaipuri 20%.
Real language markers: Bhojpuri `बा/बाटे/जाला/लौकता`; Garhwali+Kumaoni `यख/छन/दिखेण/लग्यु`; Chhattisgarhi `हवे/अऊ/ठन/दिखत हे`;
Maithili `छै/रहल/लागल`; Rajasthani `रही छे/दिखी री/को रग सफेद`. Jaipuri's markers (`बादल`, `सफेद`, `घास`) are likely one speaker/picture
effect (86 clips, 4 cells).
**Phase 4a topic check (Hindi clips on the SAME prompts):** removed Khariboli 17/32 (generic Hindi phrases `यहा पर`, `काफी सारे`),
Kumaoni 9/33, Maithili 6/37, Jaipuri 4/28, Marwari 2/40, Surgujia 2/19. Final library: `data/markers/phase4_final_library.json`.
**Hindi markers (33 stable, 3 unshared)** are picture-description vocabulary: `मुझे`, `तस्वीर`, `पिक्चर`, `आ रहा है`, `इस`. They passed the
topic check but cannot be told apart from a collection/instruction-wording difference between the Hindi and regional sets: UNPROVEN.
**Phase 4b LOVO (6 configs = 3 seeds x primary/strict; mean over 19 varieties):** in-distribution recall 0.55, UNSEEN-variety recall 0.49,
SVM unseen recall 0.80, Hindi false-flag rate ~0.33 (marker model 0.22-0.58 depending on the split; SVM ~0.33). K and the threshold
maximise balanced accuracy (50% Hindi correct + 50% mean regional recall); no Hindi-FPR cap, as instructed. Worst unseen: Khortha 0.16,
Marwari 0.25, Magahi 0.31, Haryanvi 0.35, Rajasthani 0.39. Best: Angika/Surjapuri 0.71. So the marker detector generalises to unseen
varieties only modestly; the statistical model does materially better at a similar Hindi false-flag rate.
**Grounding check (Evon): NOT RUN.** `BOLI_EVON_URL` unset in the cloud environment; no Modal endpoint reachable. Claude-only as a
substitute was offered earlier (Evon via Modal as downstream, Claude as judge was the user's choice) and not done.

## 7. Files (all under `experiments/2026-10-05-evon-pipeline/` unless noted)
Scripts (`scripts/`): `markers_common.py` (clean, loaders, group-disjoint splits), `phase1_markers.py` (derive+eval+SVM; `--hindi`,
`--strict`, `--seed`), `phase1_report.py` (10-run aggregation; `--hindi`), `hindi_footers.py` (parquet footers/metadata by HTTP range;
`--subset test=8,validation=8,train=14`), `hindi_sample.py` (4,000-clip stratified sample), `hindi_pull.py` (Prisma pull; `--nparts 3
--part k`; resumable; counts HTTP calls), `hindi_merge.py` (merge parts, success beats error), `phase2_report.py`, `phase4_topic.py`,
`phase4_lovo.py` (`--seed --strict`, `--aggregate`), `phase4_report.py` (assembles `PHASE4_REPORT.md`), `run_phase3_4.sh`
(orchestrator). Results (`data/markers/`): `phase1_*`, `phase3_*` (20-class), `phase4_*`, `PHASE4_REPORT.md`,
`PHASE2_AND_CAVEATS.md`. Dependencies installed ad hoc (not in `pyproject.toml`): numpy pandas scikit-learn scipy pyarrow fsspec
aiohttp huggingface_hub.
Re-run: `hindi_footers.py --subset test=8,validation=8,train=14 --workers 16` -> `hindi_sample.py --n 4000` -> `hindi_pull.py --nparts 3
--part {0,1,2} --concurrency 3` (about 70 min, rate-limited) -> `hindi_merge.py` -> `run_phase3_4.sh`; then `phase4_report.py`
(the orchestrator copy that already ran did not include that step).
Commits: `995c9e8` Phase 1; `04bb3c8` regeneration without gate + Hindi scripts; `b006503` Phase 2-4 scripts; `8b90f3e` Phase 2-4
results; `b08bff7` logs and pull summaries.

## 8. Environment gotchas (cloud container)
- Egress proxy injects HF and Gnani credentials (no keys needed). `huggingface.co` resolve URLs 302 to a signed CDN; `fsspec` HTTP
  HEAD fails (FileNotFoundError): use the custom `RangeFile` in `hindi_footers.py`.
- `pkill -f <name>` from a Bash tool call kills its own shell (exit 144); use `pgrep -f "^python3 script"` + `kill PID`.
- A `git add` with a non-existent pathspec aborts everything silently into a "nothing committed" state: check the commit happened.
- The sandbox worker restarted several times; background jobs survived, but verify with `ps`.
- Plan mode was active at the start; two `ExitPlanMode` calls were rejected by the user, who replied with new instructions
  (the stale plan file lives in `/root/.claude/plans/`, outside the repo; ignore it).
- Do not name the model in commits/PRs. Commit trailers requested by the harness: `Co-Authored-By` and `Claude-Session`.

## 9. Open items / next steps (none started)
1. **Ask-and-wait:** the user has not answered whether to start variant work. Do not start it without a yes.
2. Check the Hindi markers against Hindi from a **different source** (e.g. FLEURS/Common Voice Hindi) to separate real Hindi usage from
   Vaani collection artifacts; and read a larger Bihar/UP sample for label noise.
3. Grounding check needs an Evon endpoint (`BOLI_EVON_URL`); otherwise decide on a Claude-only substitute.
4. Hindi-vs-regional: the SVM clearly beats the markers on unseen varieties; decide whether markers are only for the 4 clear varieties
   and a statistical model handles the rest.
5. Doc 18's "no Hindi data exists" claim is still uncorrected in the repo (needs the user's OK to edit those docs).
6. Sessions/multi-turn accumulation was never tested (no real session IDs).
7. Possibly commit the 4,000 raw Hindi transcripts (text only, a few MB) if the user wants; not committed so far.
8. No PR has been opened (user instruction); the stop hook will keep flagging the untracked raw Hindi data.
