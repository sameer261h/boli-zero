# 16: Technical logic, difficulty, and pecking order for the remaining roadmap

Answers `15-opus-noise-recovery-and-roadmap-design-prompt.md`. Design only: no pipeline code was changed and no
Evon, Prisma or Timbre API was called. One small offline analysis script was added
(`experiments/2026-10-05-evon-pipeline/scripts/opus_grounding_checks.py`), because several conclusions below
depend on numbers nobody had measured yet; every number labelled "measured today" comes from it and reruns in a
few seconds.

Labels used throughout: **measured** (computed from the repo's data with the script above), **read in code**
(verified by reading the source at the line given), **published** (a cited paper says it), **synthesis** (my own
reasoning, not an established result).

---

## 0. Short version

- **Do not build a text-only Prisma corrector, in any form** (lookup table, noisy channel, constrained LLM
  reranking). Three independent measurements below say the ceiling is too low to pay for the risk of damaging
  correct words. This extends doc 13's negative Bhojpuri result to all 19 dialects and to the context-aware
  methods doc 13 deliberately left out.
- **Handle consequential errors in the conversation, not in the transcript.** Evon should ask or confirm
  when a detail that matters (a "not", an amount, a date, a yes/no) is unclear. The Claude reply path already
  does this, but the Evon path does not.
- **The one cheap lever that uses the audio is already plumbed in and has never been tested:** Prisma's
  `bias_list`. An offline A/B on the existing Vaani clips costs roughly Rs 30-45.
- **(d) dialect-flavoured speech** can be built as a small, native-reviewed word-swap layer, but it is the
  riskiest item and should come last. **(f) temperature** is the wrong knob for tone: pin it once and leave
  it. **(g) emotion through text** is real for pauses and pacing (plus Timbre's `speed` field, which does
  exist), and mostly wishful for actual emotional colour. It is cheap to test objectively before anyone
  argues about it.

---

## 1. Facts found in the code and data that change the brief

These came up while tracing the real pipeline. Some contradict assumptions in doc 15, so they come first.

| # | Finding | Evidence | Why it matters |
|---|---|---|---|
| F1 | Prisma accepts **`bias_list` (up to 100 words), `bias_score`, and `substitution_map` (up to 10 rules)** per request. | read in code: `clients.py:125-135`; README "What testing against Gnani showed" | Doc 15 says "transcript text only" and treats audio-level help as needing new raw-audio work. `bias_list` lets us steer recognition, which does use the acoustics, with no new infrastructure. |
| F2 | A **"boosted" recognition mode already exists** but is locked ("no frozen configuration yet"). `attach_boost` refuses to run unless a validated experiment is cited. The conversation engine always uses `mode="baseline"`. | read in code: `service.py:124-129`, `routing.py:305-312`, `conversation.py:312` | The plumbing for F1 is done. What's missing is the experiment. |
| F3 | Timbre's request includes **`speed`** (default 1.0), and also **`voice`**. | read in code: `clients.py:187-190` | Doc 15 says Timbre has "no prosody parameter at all." Speed is a crude prosody control. Whether Timbre honours non-1.0 values is **unverified**. |
| F4 | `EvonReply` sends **no `temperature` or other sampling parameter**. The body is just `{model, messages}`. | read in code: `conversation.py:170-171`; served by `vllm serve` (`evon_serve.py`) | The temperature in effect today is whatever vLLM resolves by default (the model's `generation_config.json` if vLLM loads it, otherwise 1.0). **Unknown and unlogged.** Item (f) starts by fixing this. |
| F5 | The `[UNCLEAR]` guard and the "ask one short clarifying question instead of guessing" instruction exist **only in the Claude path** (`SYSTEM_PROMPT`). `EVON_TASK_TEMPLATE` has neither. | read in code: `conversation.py:38-52` vs `134-139` | The garbled-speech handling that exists does not reach Evon. |
| F6 | The Claude path's system prompt tells it to **"Talk with the user in Bhojpuri"** for every caller, whatever the detection says. | read in code: `conversation.py:39` | Item (d) already ships, unconditionally and unvalidated, on the Claude path. That contradicts the "default to Hindi when unsure" policy in docs 05 and 09. |
| F7 | The v1 detector is **not a runtime artifact**. It lives in an experiment script, nothing is saved, and scikit-learn is not a dependency in `pyproject.toml`. | read in code: `v1_detector.py` writes JSON results only | "Wire the detector in" has an export step in front of it. Small, but real. |
| F8 | Detector exact accuracy on **1-6 word inputs is 35-40%**, against 50-52% on 11+ words. | measured earlier: `v1_detector_results.json` → `length_accuracy` | Phone turns are short. Run the detector over the **whole conversation so far**, not on each turn alone. |
| F9 | Experiment 2 found that a Bhojpuri grounding card gave **"no material gain"** over the business prompt alone. | doc 02, README | Prior evidence against assuming a dialect hint helps. That run used **clean human text**, though, not Prisma output, so the question is still open where it matters. |
| F10 | All 25k pairs are **Vaani image descriptions** ("a red shirt", "three-storey building"), not conversations. | measured: `referenceImage` field in every `.jsonl` row | Any channel table, LM prior or detector threshold learned here is shifted away from call-centre language. This limits how far every learned component transfers. |

---

## 2. New grounding numbers (measured today)

Script: `scripts/opus_grounding_checks.py`. Clip-level 80/20 split, seed 42, all 19 dialects pooled. It reuses
the repo's own `tokenize`/`SequenceMatcher` alignment, the WRONG rule from `phonetic_filter_classification.py`,
and the functional groups from `consequential_flag.py`, so "consequential error" means exactly the ~19% bucket
from today's audit.

**2.1 The 19% bucket is a minority of what goes wrong.** Weighted by tokens, Prisma's edits split into
multi-word replacement spans **67.3%**, one-for-one substitutions **21.4%**, deletions **7.9%**, and
insertions **3.5%**. The 67.4% / 32.6% / ~19% breakdown only covers the one-for-one substitutions. Most of the
damage is multi-word garbling (for example "ना बेल्ट छो ना" → "इन फील्ड छोड़ना"), which no word-level method can
reach.

**2.2 The "needs fixing" bucket is a long tail, and its head is mostly a grouping leftover.** In
`needs_fixing_wrong_substitutions.csv` (7,327 instances), **72.7% of instances are (dialect, pair) combinations
that occur exactly once**, and the top 1,000 pairs cover only 32.5%. The most frequent rows are largely harmless
variants the functional groups missed: ए→ये (81x; ए sits in the copula group but here is a demonstrative),
अउ→औ, आउ→अऊ, बोहत→बहुत. So ~19% is an upper bound, and the repeated patterns a corrector could learn are
mostly ones that don't need correcting.

**2.3 From Prisma's word alone, you cannot tell which words are wrong.** On held-out data, 1.84% of Prisma
tokens are consequential one-for-one errors. Here is what happens if you flag a token whenever its training-set
error rate is high:

| Flag if P(error \| Prisma word) ≥ | Tokens flagged | Precision | Recall |
|---|---|---|---|
| 0.05 | 6.3% | 7.4% | 25.4% |
| 0.10 | 2.4% | 10.0% | 13.1% |
| 0.20 | 0.7% | 13.8% | 5.5% |
| 0.50 | 0.2% | 15.1% | 1.8% |

At every threshold, at least 85% of flagged words are actually correct. This is doc 13's "attractor word"
finding, restated as an error-detection result.

**2.4 Even when you know which word is wrong, the right answer is usually not in any candidate list you can
build.** For held-out consequential errors:

| Candidate source | Prisma word never seen as an error before | Truth in top-1 | top-3 | top-10 |
|---|---|---|---|---|
| Pooled channel table (all dialects) | 28.8% | 16.4% | 24.8% | 31.2% |
| Per-dialect table, **assuming the dialect is known perfectly** | 49.1% | 15.1% | 21.8% | 24.3% |

Splitting by dialect makes things worse, because the data gets too thin. Knowing the dialect does not rescue a
channel model.

**2.5 The एगो / ओ ambiguity is real but cannot be acted on at runtime.** Human एगो (2,537x) passes through
Prisma **unchanged 67%** of the time. It becomes वो only 26 times (1%). Going the other way, of the 677 times
Prisma outputs वो, only 26 (3.8%) came from एगो. The ambiguity lives in what Prisma does to the source word. At
runtime Evon sees वो, and nothing in the text says it might have been एगो. When एगो survives, Evon sees the
dialect word itself, which is a comprehension question, not a correction one.

**2.6 About one in six explicit "not" words does not survive Prisma.** For unambiguous negators (नहीं, नही,
नइखे, नईखे, नाहीं, मत; 242 occurrences): 66.5% unchanged, 16.1% inside a changed span that still has a
negator, **14.0% replaced with no negator left, 3.3% deleted**. ना/न were left out because they are often tag
or emphatic particles. Small sample, but it marks negation as the single most dangerous error class for a
collections or support call.

---

## 3. Part A: recovering meaning from garbled transcripts

### A.1 LM rescoring and generative post-correction: what the field does

- **Second-pass rescoring** scores a list of alternative transcripts (the N-best list) with a stronger LM and
  picks the best. Example: masked-LM pseudo-log-likelihood scoring (Salazar et al., *Masked Language Model
  Scoring*, ACL 2020, arXiv:1910.14659). **Needs N-best. Prisma returns one string, so this does not apply.**
- **Generative error correction (GER)** gives an LLM the N-best list and lets it write the corrected
  transcript. HyPoradise (Chen et al., NeurIPS 2023 D&B, arXiv:2309.15701) is the open benchmark. It reports
  that GER beats the best a reranker could do and can sometimes recover tokens missing from every hypothesis
  (published). Yang et al. (ASRU 2023, arXiv:2309.15649) use task-activating prompting. The GenSEC challenge
  (Yang et al., SLT 2024, arXiv:2409.09785) makes N-best post-ASR correction a shared task. Ma et al.
  (arXiv:2307.04172) compare unconstrained generation with constrained selection from the N-best list using
  ChatGPT. **The common thread: the gains come from the diversity in the N-best list.** It is the ASR's own
  evidence about what else might have been said.
- **Whispering LLaMA** (Radhakrishnan et al., EMNLP 2023, arXiv:2310.06434) also feeds audio encoder features
  into the corrector. That is a raw-audio method (see A.4).
- **1-best correctors exist.** Examples: Guo et al., *A spelling correction model for end-to-end speech
  recognition*, ICASSP 2019, arXiv:1902.07178; Mani et al., ASR correction as machine translation, ICASSP
  2020, arXiv:2003.07692; FastCorrect, Leng et al., NeurIPS 2021, arXiv:2105.03842. They are trained on large
  paired corpora, often with synthetic TTS-generated pairs, and the published work keeps controlling
  over-correction (damaging correct tokens) as a central concern.

**Does any of it transfer to 1-best-only?** (synthesis) Only in two indirect ways:

1. **Fake an N-best list from the channel table.** Substitute each Prisma token with its historical sources and
   let an LLM choose. §2.4 sets the ceiling: the truth is in the top-10 for only 31% of consequential one-for-one
   errors, which are only ~21% of the edit mass (§2.1). And you must first find the wrong token, which works at
   ≤15% precision (§2.3).
2. **Get a real second hypothesis from Prisma by asking twice**: baseline and with a `bias_list` (F1). That
   produces a genuine, acoustically grounded 2-best, which is the ingredient GER relies on. Cost: twice the
   Prisma spend and ~1 s more latency per turn. This is the only form of the GER idea worth considering here,
   and only if the A/B in §3.5 shows the biased run differs from the baseline in useful ways.

A trained 1-best corrector is out of reach. There are ~6k consequential training errors across 19 dialects,
73% of them seen once (§2.2), and the domain is image descriptions (F10). That is orders of magnitude below what
the cited systems train on.

### A.2 The noisy channel model, with today's confusion tables

The classical form (Kernighan, Church & Gale, COLING 1990; Brill & Moore, ACL 2000; applied to ASR output by
Ringger & Allen, *Error correction via a post-processor for continuous speech recognition*, ICASSP 1996) picks:

```
X* = argmax_X  P(Y | X) · P(X | context)        # channel × prior
```

Today's alignments give an empirical channel `P(Y|X)` per dialect, so the method is technically assembled. The
idea is still current: noisy-channel reranking is used in NMT (Yee et al., EMNLP 2019, arXiv:1908.05731), and
GER can be read as an implicit version of it. **But it fails here for a structural reason, not only because the
data is thin** (synthesis, consistent with §2.3-2.4):

```
posterior odds of correcting Y→X  =  [P(Y|X) / P(Y|Y)]  ×  [P(X|ctx) / P(Y|ctx)]
                                      channel ratio          prior ratio
```

- Prisma's errors **move dialect speech toward standard Hindi**: बहोत→बहुत, रो/रेहो→रही, मा→में, अउ→और. Its
  output is usually *more fluent standard Hindi* than what was said.
- Any LM prior we can actually get (a Hindi LM, or Evon itself) is trained mostly on standard Hindi, so the
  prior ratio **favours the wrong output Y**. The channel ratio is below 1 for attractor words (Y→Y dominates).
  Both factors push against correcting. The posterior only flips when the context makes Y really implausible,
  and Prisma's own fluency makes that rare.
- Fixing the prior would need a dialect LM. The only dialect text available is the ~25k human transcripts,
  which are short image descriptions. Too small and off-domain.

**Verdict: the channel tables are good for diagnosis (they already powered the detector and docs 06/13/14) but
not for correction.**

### A.3 Context-aware correction without open-ended LLM guessing

The proposed method: build a small candidate set per suspect word (`{Y} ∪ topk_sources(Y)`), score each
candidate sentence by LLM log-probability or as a multiple-choice question, and replace when a candidate wins.
This is the most principled of the options and avoids the "LLM's prior world knowledge" objection, because the
LLM only ranks options the data proposed. Its break-even, worked through:

```
At flag threshold 0.10:  of 100 flagged tokens, 10 are real errors, 90 are already correct   (§2.3)
Of the 10 real errors, at most ~3 have the truth in the top-10 candidates                     (§2.4)
=> best case fixes ≈ 3 per 100 flags
=> to break even, the reranker must leave ≥ 87 of the 90 correct tokens alone (≥ 96.7%)
   AND pick exactly the right candidate in all 3 fixable cases
```

A Hindi-trained LM scorer *will* tend to leave correct tokens alone, for the same reason A.2 fails: it prefers
standard forms. So it would mostly keep Y and fix little. Net effect is near zero at the cost of an extra LLM
call per turn. **Difficulty: Hard, and not worth doing** (measured ceiling plus synthesis). This is the same
answer as doc 13, now with context included and the reason quantified.

**What context is good for: repair inside the dialogue.** Spoken-dialogue research treats non-understanding and
misunderstanding as something the dialogue itself recovers from, using explicit or implicit confirmation and
re-prompts (Bohus & Rudnicky, *Sorry, I didn't catch that!*, SIGdial 2005, which compares ten recovery
strategies; Skantze, *Exploring human error recovery strategies*, Speech Communication 45(3), 2005). Here that
becomes:

- **Implicit confirmation of consequential details.** When the reply depends on an amount, a date, a yes/no, or
  a negation, Evon repeats the detail as it understood it ("ठीक है, आप सोमवार को जमा करेंगे?"). If Prisma
  dropped a "not" (§2.6), the caller hears the wrong version and corrects it. That costs one turn, against a
  wrong action on the account.
- **A clarifying question when the utterance can't be followed** (the existing `[UNCLEAR]` mechanism).
- This also covers the 67% of damage in multi-word spans (§2.1), which no word-level method can touch.

### A.4 Raw-audio techniques we don't use yet

First, a correction to the brief: **the raw audio is already in the pipeline.** `ConversationEngine.recognize()`
holds the uploaded bytes (`conversation.py:300`). Getting the audio is not the expensive part. Hosting a speech
model next to Prisma is. The app runs on Vercel serverless (no GPU); Evon already runs on Modal, so a speech
model would live there too.

| Technique | What it buys over text-only | Cost | Honest estimate |
|---|---|---|---|
| **Word confidence** from the recognizer (e.g., Li et al., ICASSP 2021, arXiv:2010.11428) | Fixes §2.3: it locates errors | Prisma doesn't expose it. Would need our own ASR. | Not available on its own. Only comes with the next row. |
| **A second ASR running alongside Prisma, combined by voting** (ROVER, Fiscus, ASRU 1997). Candidates: IndicWav2Vec (Javed et al., AAAI 2022, arXiv:2111.03945; built on wav2vec 2.0, arXiv:2006.11477, and HuBERT, arXiv:2106.07447) or an Indic Conformer, fine-tuned on Vaani. | Where the two systems disagree is a well-established confidence signal. It gives real error *location* and a second hypothesis, i.e., a 2-best for GER. | High: fine-tuning, GPU serving, +0.3-1 s latency, MLOps for a second model | The only path that could plausibly beat text-only methods by a wide margin. Fine-tuning on ~25k image-description clips gives a narrow-domain model, so it may be no better than Prisma on calls. **Do not start unless the `bias_list` A/B shows the audio carries recoverable dialect evidence.** |
| **Acoustic verification of candidates** (forced-align each candidate word to the audio with a CTC model and compare likelihoods) | Replaces the failed channel×prior (A.2) with a real acoustic score | Same model hosting as above, plus alignment code | Still capped by candidate coverage (31%, §2.4) unless the second model proposes its own candidates. Weaker than the ROVER row. |
| **Contextual biasing in the recognizer**: Prisma `bias_list` (F1). Literature: Pundak et al., *Deep context*, SLT 2018, arXiv:1808.02480. | Pushes the decoder toward dialect forms *using acoustic evidence*, before the text is fixed | About Rs 30-45 for an offline A/B. Zero infrastructure. | **Do first.** Known risk: over-biasing inserts the biased words where they weren't said, which the A/B must measure. How Prisma biases internally is undocumented. |

### A.5 Recommendation for the ~19% consequential bucket

1. **Build no corrector.** No lookup, noisy channel, or reranker (A.2, A.3, §2.3-2.4).
2. **Give Evon the clarify-and-confirm behaviour** that the Claude path already has (F5), plus a narrow rule:
   confirm amounts, dates, yes/no and negation implicitly when the reply depends on them. Cheapest change with
   the largest protective effect (§2.6).
3. **Pass the detector's verdict as register context, not as word corrections**: a short, fixed hint per
   hierarchy level (see B0). Its value is unproven (F9), so it ships together with the evaluation in B0.2.
4. **Run the `bias_list` A/B** (§3.5). It is the only audio-aware lever available this month.
5. **Revisit a second ASR only if (4) is positive.** Otherwise the cheap thing (detector + hierarchy +
   clarify) is good enough, because the errors that matter are mostly not recoverable from text, and the
   conversation can recover them.

### §3.5 `bias_list` A/B design (Part A, item 4)

```
data      : Bhojpuri first (27 groups, best-understood); held-out clips NOT used to choose the words
bias words: <=100 dialect forms Prisma normalises away, from per_dialect_results.json
            (e.g. बहोत, गइल, नइखे, रउआ, बानी, रहल ...), chosen on the train split only
arms      : baseline (already cached in the .jsonl, no new spend) vs bias_score in {low, high}
n         : ~400 clips × 2 biased arms ≈ 2 × 400 × ~6 s billed ≈ 80 min ≈ Rs 36 at Rs 27/h (ledger.py:11)
metrics   : WER vs human; consequential-error count (§2 definition); negation survival (§2.6);
            OVER-BIAS rate = biased word appears in Prisma output where the human did not say it
decision  : continue only if consequential errors drop AND over-bias insertions stay below an agreed cap
runtime   : turn 1 baseline; from turn 2, bias list for the detected profile (B0) once Level 1/2 is reached;
            service.options() must take a per-call list instead of the single frozen boost (service.py:124-129)
```

Watch the 429s seen on 2026-10-02 (README): pace the requests.

---

## 4. Part B and the shared foundation

### B0. Shared foundation: the detector hint in `reply()`, and the evaluation harness

Most of Part B depends on two pieces, so they come first.

**B0.1 Wiring (stage 2, `reply()`)**

```
# ConversationEngine.reply(), before the replier call (conversation.py:342)
said   = [t.recognized_text for t in understood_history(conv)] + [turn.recognized_text]
det    = DETECTOR.predict(" ".join(said)[-1500:])        # conversation-level: longer text is more accurate (F8)
tier   = hierarchy(det)                                   # doc 09 Stage 7 rules: L1 / L2 profile / L3 / L4
hint   = HINT[tier.level].format(profile=tier.profile_description)    # fixed strings, no per-word flags
text, usage = self.replier.reply_with_usage(context, turn.recognized_text[:MAX_TEXT_CHARS], hint=hint)
turn.dev["dialect"] = {"level": tier.level, "top1": det.top1, "conf": det.conf, "margin": det.margin}
```

- `EVON_TASK_TEMPLATE` gets a `{hint}` slot **before** "User said:", so Evon never reads the hint as the
  caller's words. `AnthropicReply` appends it to `system`. Both `reply_with_usage` signatures gain
  `hint: str = ""`.
- Level 4 sends an **empty hint**. Most traffic keeps today's behaviour, which limits the damage if hints turn
  out to hurt.
- Hint content describes **comprehension**, never output style. Example for Level 2: "The caller probably
  speaks an eastern regional variety of Hindi. The words come from a Hindi recogniser, which tends to rewrite
  dialect grammar into standard Hindi and can drop short words like 'not'. Reply in simple standard Hindi. If a
  detail you need (amount, date, yes/no, a 'not') is unclear, confirm it." Do not name "Bhojpuri" as a target
  language: naming it in output instructions caused Bengali-script corruption (doc 04/05). Naming it as input
  context is untested, so use a family description.
- Detector export (F7): the shortest path is to pickle the fitted pipeline with scikit-learn pinned and add the
  dependency. Check the Vercel bundle size first (numpy, scipy and scikit-learn together are large). Fallback:
  export idf, vocabularies, LR coefficients pruned to the top features per class, and the isotonic breakpoints
  to JSON, then do inference in pure Python (TF-IDF, then a dot product, then a table lookup).
- Thresholds 0.70/0.45/0.20 come from one split on image-description text (doc 09 caveat, F10). Log
  `turn.dev["dialect"]` on every hosted turn (the `boli_reviews` table already stores the turns) so they can be
  re-checked on real call text.

**Difficulty: Medium** (engineering 1-2 days). The hard part is not the code. It is that F9 says the benefit
may be zero, so this item is only finished when B0.2 has measured it.

**B0.2 Evaluation harness: paired-reference meaning recovery** (synthesis, offline, no audio spend)

The earlier objection that "asking an LLM only measures its prior" is answered by a **control arm**. The LLM's
prior is identical in both arms, so the difference between arms is attributable to the intervention.

```
sample    : ~300 clips from the 25k, stratified by detector level and by "has consequential error"
arm A     : Evon gets the Prisma transcript                      (today)
arm B     : Evon gets the Prisma transcript + hint / clarify rule (intervention)
reference : Evon gets the HUMAN transcript, same probe prompt     (what perfect ASR would give)
probe     : "In one English sentence, what is the speaker describing? Note any 'not'."
score     : judge model answers 3 fixed factual questions written from the human transcript
            (objects, colours/numbers, negation), against each arm's answer; report B-A delta + CI
clarify   : ground truth for "should Evon have asked?" = the clip has a consequential error or a lost
            negation (§2 alignment labels). Report clarify precision (not annoying) and recall (caught it).
```

Cost is Modal GPU time only. Limitation: image descriptions are not business calls, so this measures
comprehension, not call outcomes. A small set of scripted call utterances (doc 02 style, **sent through
Prisma**, not typed clean) should follow once the cheap version shows a signal.

**Difficulty: Medium.** The code is simple. Keeping the judge honest (fixed questions, blind to arm) is the
work.

### B1. Item (d): making Timbre sound more like the caller's dialect, through text

**What can work** (synthesis grounded in how TTS front ends work): Timbre turns Devanagari into sounds. Hindi
spelling is largely phonemic, so **a different spelling or a different word is pronounced differently**. "बा",
"रउआ", "बानी", "हम" will be spoken as written. Dialect flavour at the **word** level is therefore real.
Dialect **accent** is not reachable: intonation contours, vowel quality, rhythm, and Hindi schwa-deletion rules
applied to Bhojpuri words are all decided inside Timbre's Hindi voice.

**Mechanism: a deterministic register layer between Evon and Timbre (stage 3, `speak()`)**

```
# ConversationEngine.speak(), conversation.py:366
text = turn.reply_text[:MAX_TEXT_CHARS]                      # Evon writes plain standard Hindi
if FLAVOUR_ENABLED and tier.level == 1 and tier.variety in REVIEWED_TABLES:
    flavoured = apply_table(text, REVIEWED_TABLES[tier.variety])   # whole-word, context-safe swaps only
    if is_clean_devanagari(flavoured) and changed_words(text, flavoured) <= 3:
        text = flavoured                                     # else fall back to plain text (doc 05 safety gate)
audio, key, info = self._synthesize(text, self.voice, {...}) # info["text_sent"] already records what was spoken
```

- **Why a table, not asking Evon to "speak Bhojpuri"**: Evon's own attempt produced ungrammatical output
  ("सही कर देब बा", `experiment5_results.json`), and naming the language caused script corruption. A table is
  auditable, deterministic and testable. Few-shot style transfer (3/3 in doc 05, N=9) can come later.
- **Generation runs in the opposite direction from correction, so doc 13's problem does not apply.** Going
  standard → dialect has no attractor issue. The constraint is **grammar**: "ठीक है"→"ठीक बा" is a safe whole
  phrase, but "जा रहा है"→"जात बा" is a morphological rewrite. The table should contain only invariant items:
  pronouns and honorifics (आप→रउआ), set phrases, discourse particles, and copula in fixed phrases. Keep it to
  roughly 20-40 entries.
- **Only at Level 1** (≤13% of traffic at an honest error rate, doc 09) and only for varieties with a reviewed
  table. Start with Bhojpuri. Doc 09 is explicit that detection groups are not response groups, so Level 2
  profiles get no flavour.
- Evon's history keeps the standard text (`turn.reply_text`). Only the spoken string changes, so the layer
  cannot leak into Evon's later reasoning.
- **Fix F6 at the same time**: the Claude path should stop asking for Bhojpuri unconditionally and use the same
  gate.

**Risk: mimicking the caller.** Communication Accommodation Theory (Giles and colleagues) separates convergence,
which listeners usually see as warm, from **over-accommodation**, which comes across as patronising or mocking,
especially from an outsider and especially when it is exaggerated (established theory; how it applies to voice
bots is my synthesis). Mitigations: partial convergence only (a few forms, never phonetic caricature), never at
low confidence (a wrong dialect is worse than Hindi), a per-campaign off switch, and native-speaker review of the
table before any caller hears it.

**Evaluation:** a listening test with native speakers. Same replies, plain vs flavoured, rated on
intelligibility, naturalness, and "respectful vs mocking". Timbre spend is about Rs 0.1 per sentence. The cost is
recruiting and paying listeners.

**Difficulty: Hard.** The code is easy (a table and a function). It is hard because (1) the content needs native
linguistic review for each variety, (2) success is a perception judgement that needs human listeners, (3) a
mistake is a social harm, not just a wrong word, and (4) whether Timbre's Hindi voice pronounces dialect
spellings acceptably is unverified.

### B2. Item (f): changing Evon's temperature by context

**What temperature does:** it rescales the next-token distribution. It changes **how varied** the wording is,
not **what tone** is chosen. Tone comes from instructions. High temperature increases degeneration and
incoherence risk (Holtzman et al., ICLR 2020, arXiv:1904.09751). Across temperatures 0.0-1.0, Renze & Guven
(arXiv:2402.05201) found no statistically significant effect on LLM problem-solving accuracy (published). Two
risks specific to Evon (synthesis):

- Evon reasons in a long `<think>` block before `REPLY:`. Raising temperature makes the reasoning longer and more
  wandering, which raises the risk of the old Timbre-breaking length failure and of a missing `REPLY:` line.
  Some 30B-A3B-style reasoning models also recommend *against* greedy decoding (temperature 0) because it can
  loop. Check Evon's model card or `generation_config.json`; this is not verified for Evon.
- In a collections or complaints call, the expensive failure is an **improvised commitment** ("your money will
  be refunded"). Higher temperature makes those more likely. Small talk tolerates variety.

**Mechanism (stage 2 only; temperature never reaches Timbre):**

```
SAMPLING = {"default": {"temperature": T0, "top_p": P0},      # T0, P0 = model-card values, pinned and logged
            "business_critical": {"temperature": T0 - 0.2}}   # aggrieved caller, money, disputes: fewer surprises
profile = "business_critical" if campaign.is_transactional or aggrieved(turn) else "default"
json = {"model": ..., "messages": [...], **SAMPLING[profile]}  # conversation.py:171
turn.dev["reply"]["sampling"] = SAMPLING[profile]
```

There is deliberately **no "happy caller → higher temperature" profile**. Warmth for a happy caller belongs in
the prompt ("respond warmly, keep it brief"), not in randomness. `aggrieved()` can be a few lexical cues for
now; it doubles as the emotion data hook in B4.

**Difficulty: Easy** to build (one JSON field and a lookup). Hard to prove an effect, because temperature
effects are small and noisy and would need many samples per arm with human ratings. **Expected value: low.** The
real win is step 1, pinning and logging the value (F4), which every other evaluation needs for reproducibility.

### B3. Item (g): adding emotion to Timbre's output through what Evon writes

What text can change in a neural TTS (synthesis, from how such systems learn prosody from text; FastSpeech-style
models predict duration and pitch from the input sequence):

| Lever | Plausible effect | Confidence |
|---|---|---|
| Commas, full stops (।), sentence length | Phrase breaks and pauses, pacing | High: almost every TTS front end uses punctuation for breaks |
| "?" at the end | Rising question intonation | High for yes/no questions |
| Lexical softeners and apology words (जी, माफ़ कीजिए, ज़रूर) | Politeness comes through the words themselves; the voice adds little | High that the words carry it, low that the voice adds anything |
| Interjections (अरे, ओह), "!" | Some energy or pitch change, if the training data correlated them | Low and voice-dependent |
| Ellipses, repeated punctuation | Unpredictable: may be ignored, read out, or cause odd pauses | Low; also a parsing risk |
| `speed` field (F3), e.g. 0.9 for complaints | Slower, calmer delivery | Medium, **if Timbre honours it** (unverified) |
| `voice` field | Choose a calmer voice per campaign (not mid-call, which would be jarring) | High that it changes the sound; it is a product choice |

**Mechanism:** (1) one line in `EVON_TASK_TEMPLATE`: "Write it to be spoken: short clauses separated by commas,
end questions with ?, no ellipses or exclamation runs". (2) A deterministic normaliser in `speak()` that
guarantees terminal punctuation and collapses `!!`/`...`. (3) `speed` chosen by the same profile as B2.

**Test this objectively before any listening study (cheap and decisive):** 10 sentences × {plain, punctuation-
shaped, speed 0.9} → about 30 Timbre calls, roughly Rs 3-5. Measure duration, pause count and length, and pitch
range with a pitch tracker. If the audio barely changes, stop. If it does change, run a 5-listener warmth and
naturalness rating.

**Difficulty: Easy-Medium. Verdict: a real lever for pacing and politeness, and largely wishful for emotional
colour (warm vs sad vs excited).** Expect the measurable part to be pauses and speed.

### B4. Item (c): emotion, as data collection only

As requested, no live system. A logging hook: put the B2 `aggrieved()` cue hits, the turn's `understood` flag,
whether a clarification was asked, and the call outcome into `turn.dev`, stored with the audio already kept in
`boli_reviews` (30-day retention, consent notice already in place). Vaani has no emotional speech, so real call
audio is the only useful source. Voice emotion labels are sensitive personal data, so keep them under the same
consent and retention rules. **Difficulty: Easy** (a few fields). The real cost is labelling later.

---

## 5. Lowest-hanging fruit

Doc 15 suggests that wiring the detector into `reply()` is the obvious first move. I'd put it third. It is
cheap, but F9 says its benefit may be zero, and per-turn accuracy on short utterances is weak (F8). These come
first:

1. **Clarify and confirm in the Evon template** (stage 2: `EVON_TASK_TEMPLATE` plus the existing `[UNCLEAR]`
   parse in `reply()`). It costs a few hours. The behaviour already exists and works in the Claude path (F5).
   It goes straight at the most damaging measured error (about 1 in 6 negations lost, §2.6) and at the 67% of
   damage in multi-word spans that nothing else reaches.
2. **Pin Evon's sampling parameters and log them** (one field, `conversation.py:171`). Effort: minutes.
   Without it, no Evon result is reproducible, including every evaluation below.
3. **Detector hint plus the B0.2 evaluation**, shipped together, so the project learns whether the detector
   built today changes Evon's understanding of Prisma text.

The best Part-A bet, `bias_list` A/B, is fourth only because it costs money (about Rs 36) and needs spend
approval. In effort it is just as low-hanging, since the plumbing exists (F2).

---

## 6. Pecking order

| # | Item | Stage | New data/state | Difficulty | Depends on | Why here |
|---|---|---|---|---|---|---|
| 1 | Clarify/confirm rule in Evon template | reply | none | **Easy** (hours) | none | Largest protection for least work; already proven pattern on the Claude path |
| 2 | Pin + log Evon sampling params | reply | model-card values | **Easy** (minutes) | none | Every later Evon measurement needs it |
| 3 | B0.2 evaluation harness | offline | 300-clip sample, judge questions | **Medium** | 2 | Without it, 4, 7 and 8 are opinions |
| 4 | Detector export + conversation-level hint (B0.1) | reply | exported model, `turn.dev["dialect"]` | **Medium** | 3 to prove value | Uses today's main build; F9 means it has to prove itself |
| 5 | `bias_list` A/B (§3.5) | recognize | ~Rs 36 Prisma spend | **Easy-Medium** | spend approval; 4 for runtime use | Only audio-aware lever; decides whether 9 is ever worth it |
| 6 | (g) Objective TTS check: punctuation, speed | speak | ~Rs 5 Timbre spend | **Easy** | none | Cheap stop/go before anyone builds prosody features |
| 7 | (g) Template line + normaliser + speed profile | reply, speak | none | **Easy** | 6 positive | Build only if the audio actually changes |
| 8 | (f) Context sampling profile | reply | `aggrieved()` cues | **Easy** to build, low value | 2, 3 | Mostly done by step 2; profile is a small refinement |
| 9 | (c) Emotion logging fields | all (dev log) | consented call audio | **Easy** | 8's cue function | Pure data collection, can ride along any time |
| 10 | (d) Reviewed register table at Level 1 + fix F6 | speak | native-reviewed table, listener panel | **Hard** | 4 (needs reliable Level 1), listening study | Highest social risk, needs people not code |
| 11 | Second ASR + ROVER / GER | recognize | fine-tuned model on Modal | **Very hard** | 5 positive | Only if the audio carries dialect evidence Prisma throws away |
| no | Any text-only corrector (lookup, noisy channel, reranking) | none | none | none | none | Measured ceiling too low (§2.3-2.4, A.2-A.3) |

Dependency logic: steps 1-2 are free and unblock everything. Step 3 is the gate that turns later items from
claims into measurements. Steps 4 and 5 are the two "use today's work" bets, one on the text side and one on the
audio side, and their results decide whether 10 and 11 are worth their cost. Item (d) is last because it is the
only item where a mistake hurts the caller rather than just failing to help.

---

## 7. Not verified, and open questions

- Whether Timbre honours `speed` ≠ 1.0, and how it treats "?", "!" and "…". Item 6 answers this.
- Evon's actual default sampling values and its model-card recommendation (F4).
- Whether Prisma's `bias_list` behaves like shallow-fusion biasing and how strong over-biasing is. Item 5
  answers this.
- How the detector thresholds and the §2 numbers move on call-centre speech instead of image descriptions (F10).
- Whether naming the variety *as input context* (not as output language) triggers the script-corruption
  behaviour seen in docs 04/05.
- The §2.6 negation figure rests on 242 occurrences across all dialects. Treat it as "roughly 1 in 6", not a
  precise rate.
- Classic citations (Kernighan et al. 1990, Brill & Moore 2000, Ringger & Allen 1996, Fiscus 1997,
  Bohus & Rudnicky 2005, Skantze 2005, Giles' accommodation theory) are cited from established literature.
  Ringger & Allen and Bohus & Rudnicky were confirmed by search today. All arXiv IDs above were checked
  against the arXiv API today.
