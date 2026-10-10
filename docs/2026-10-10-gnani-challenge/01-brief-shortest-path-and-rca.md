# 2026-10-10: Gnani challenge brief, shortest path for the test plan, and RCA of the first attempt

Labels used throughout: **official** (Gnani's challenge page text, pasted by the owner on 2026-10-10), **vendor claim**
(Gnani marketing, not verified by us), **measured** (computed from this repo's data), **read in doc** (stated in an
existing repo doc, not re-run), **synthesis** (my own reasoning).

Not done: the agentic-council plugin is not enabled in this cloud session (`ListPlugins` returned nothing), so this is
one analyst's pass, not a 20-specialist council. Gnani's own site is blocked by this sandbox's network policy; the
challenge text below comes from what the owner pasted, not from a fetch.

---

## 0. Bottom line

1. **The challenge has no scored rubric for the internship.** Shortlisting runs on *verified public engagement on your
   demo post*, then a one-to-one interview. Only the ten ₹50,000 awards have per-award criteria, and they are one line each.
   So the thing being judged is a **public, honest, watchable demo**, not a research report. (official)
2. **Today's repo is strong on measurement and has no demo.** 50 commits, 19-dialect audit, calibrated detector, two
   negative results. No public post, no 60-second video, no scripted call set. 31 days remain (deadline 11:59 PM IST,
   10 Nov 2026, no extensions).
3. **Shortest path:** build one small *synthetic call set* (inbound and outbound, in-domain, consented/scripted), run
   every bucket (a-g) against it with the cheapest test each, keep what moves a number, cut the rest. Section 2.
4. **Your noise idea has a hole:** Prisma's output carries no identifiers. Checked on all 25,139 stored transcripts:
   zero bracket/tag characters, the only non-Devanagari character anywhere is 4 commas. The *human* references carry
   noise tags (15,313 of 25,139 rows), which is why it looks like the signal exists. It doesn't reach Evon. (measured)
5. **RCA headline (section 4):** we measured everything we had data for instead of testing whether the idea changes a
   call outcome. Detection got a day of rigour while the one experiment that tested its value (doc 02) already said
   "no gain" and was never followed up.

---

## 1. What Gnani is offering, and what the evaluation actually is

### 1.1 The challenge (official)

- Theme "Build Sovereign AI for India". Open brief, no problem statement. Must use Gnani models/APIs and name them.
- Up to 100 paid six-month internships from 1 Jan 2027 (stipend up to ₹1 lakh/month, a ceiling). Ten awards, ₹50,000 each.
- Free to enter, 5,000 credits per registrant, solo or pair, enrolled Indian college student, 18+.
- **Selection in five stages:** (1) post a public demo on LinkedIn or X with `#GreatIndianAIInternshipChallenge
  #GnaniAI`; (2) Gnani verifies engagement on nominated posts; (3) submissions reviewed and shortlisted; (4) one-to-one
  interview; (5) written offer.
- **Awards judged "on their own criteria", separate from the internship.** One award per person/team. The ones that
  touch this project:

| Award | Rewards | Fit for this project |
|---|---|---|
| Main Character | Best build in a regional or low-resource Indian language | **Best fit** (Bhojpuri and 18 other varieties) |
| Noise Canceller | Best performance on messy, noisy telephonic audio | Possible via the synthetic-noise bucket (b3) |
| Mixed Vibes | Best code-mixed voice build | Weak: not what we built |
| Jugaad Genius | Most creative/unexpected use of the models | Possible: "listening to what Prisma flattens" |
| Demo Day Drop | Best 60-second demo video | Cheap to add on top of any entry |
| Crowd Favourite | Public votes on LinkedIn/X | Not controllable; bought votes/bots disqualify |

- **Rules that bite us:** use synthetic data only; no real phone numbers, account numbers, Aadhaar, PAN or **recorded
  calls** (record yourself or a teammate with consent; Vaani is a public research dataset of image descriptions, not
  calls). "A demo that fakes a result will cost you more than one that shows an honest limitation." That sentence
  favours our negative-results style, if it is packaged as a demo.
- **Not stated anywhere I have:** score weights, an accuracy threshold, a judge panel, or what the interview covers.
  Treat "explain your build and defend your numbers" as the interview, which is synthesis.

### 1.2 The models: vendor claims against what we measured

| Model | Vendor claim | What this repo measured / read |
|---|---|---|
| **Prisma v2.5** (STT) | 14M+ h telephonic audio; 10+ Indian languages + code-mix; "handles regional accents without special configuration"; <200 ms streaming | No Bhojpuri mode; run in `hi-IN`. Output is **plain text only**: no confidence, no timings, no N-best, no tags (read in doc 06/paralinguistic report; confirmed again above). On 24,986 dialect clips, 0.0-7.5% came back identical to the human transcript and the edit-rate proxy ran 0.24 (Khariboli) to 0.63 (Surjapuri); that proxy is not a true WER. Clips >30 s rejected (docs say 60); HTTP 429 on quick succession. Steering limited to `bias_list` (≤100 words) and `substitution_map` (≤10 rules); `bias_list` never tested. |
| **Timbre v2.5** (TTS, beta) | 10+ Indic languages, "context-aware prosody", reads numerals/lakh-crore correctly | Undocumented input-length cutoff between ~1,500 and 2,800 characters (HTTP 500). A `speed` field exists; whether it is honoured is unverified. No dialect voices. |
| **Evon v3.3** (LLM) | 30B MoE / ~3.5B active, 128K context, 11 Indian languages, Apache 2.0, open weights | Not on the API platform: self-hosted on a Modal A100 (cold start ~3-4 min). Without a system prompt it writes 1,100-6,200+ characters of reasoning, which broke Timbre in 4 of 6 runs. Forced `INTENT/DETAILS/REPLY` fixed it (10/10). Naming "Bhojpuri" as an *output* language caused Bengali-script corruption twice. |

**Capabilities that matter for the plan:** Evon is the only place where "understanding" can be improved. Prisma can only
be nudged (`bias_list`, `substitution_map`). Timbre can only be influenced through the text it receives, plus `speed` and
`voice`.

---

## 2. Shortest path for each bucket

**Rule for this section:** the cheapest test that could kill the idea, run first. Nothing is built until its test says
go. "Cost" is my estimate (synthesis) unless a doc is cited.

### 2.0 Shared setup (do once, ~1-2 days)

1. **Synthetic call set**, scripted and in-domain, no real identifiers: ~40 customer turns for two scenarios.
   *Outbound* = EMI reminder (agent speaks first, customer replies, usually short). *Inbound* = a helpline query (caller
   explains first, usually longer). Write each line in plain Hindi and in 2-3 regional renderings. Record yourself or a
   consenting teammate; keep the scripts as ground truth.
2. **A phone-quality copy of every clip**: 8 kHz resample plus a mixed-in public noise sample (ffmpeg). Because we mixed
   the noise ourselves we know exactly what was said, which the Vaani data never gave us for calls.
3. **One harness** that runs clip → Prisma → Evon → Timbre and logs every intermediate string. Most of this already
   exists in `src/boli_zero/conversation.py`.

Why inbound vs outbound differ (synthesis, to be tested, not assumed): the detector scored **35-40% on 1-6 word inputs
and 50-52% on 11+** (doc 16 F8). Outbound replies are short ("haan", "kal dunga"), so detection is weakest exactly
where outbound needs it. Outbound, however, knows who it is calling, so **state/district or stated language preference
from the CRM can be a free prior** and replace detection. Inbound callers talk longer (better detection) and an IVR can
ask directly. So: outbound = use metadata, inbound = use the transcript.

### 2.1 Bucket table

| Bucket | Shortest path | First test (kill criterion) | Cost / time | Expectation |
|---|---|---|---|---|
| **a) Dialect detection** | Skip a new classifier. Ask Evon directly, in the doc 18 format: "standard Hindi, regional (which?), cannot tell; quote the words that decided it". Compare with the existing detector on held-out windows and the synthetic set. | Does Evon beat the detector's 47% exact label, and stay silent on standard Hindi? If it says "regional" on plain Hindi more than a few percent, drop it. | Modal GPU hours only. ~1 day. | Evidence-surfacing already measured: right *family* 85%, exact only for Bhojpuri/Chhattisgarhi/Garhwali (doc 18). Expect family-level, not exact. |
| **b1) Straightforward, in context** | Freeze today's structured prompt. Fix the known phrasing bug: replies *instruct* the customer instead of *confirming* what they said (doc 02 Q9). | 5-10 scripted lines: does the reply confirm the right amount/date? | Hours. | Already works (10/10); this is polish. |
| **b2) Ambiguity, three levels** | My assumed ladder (please correct): **L1** one word unclear → resolve silently or confirm in passing; **L2** a detail that changes the action is unclear (amount, date, a "not") → confirm explicitly; **L3** intent unclear → one short open question or hand off. Put the L2 confirm rule and the existing `[UNCLEAR]` guard into the Evon template (they exist only on the Claude path today, doc 16 F5). | Seed the synthetic set with 1/3 clean, 1/3 L2, 1/3 L3 lines. Score: did it ask when it should, and stay quiet when it should? | Hours + one run. | Highest value per hour: about 1 in 6 explicit "not" words did not survive Prisma (measured, small sample), and the 67% of damage in multi-word spans cannot be fixed at word level. |
| **b3) Noise → reconstruct the word** | **Do not reconstruct; confirm.** Premise check done: Prisma emits no identifiers (section 0). The only signals are the transcript itself (gaps, odd words, short length) and whatever `denoise`/`raw` fields the API may expose, both untested. | Mask known words in the synthetic set, hand Evon the gappy transcript plus the call context, count right-guess vs wrong-confident-guess. If wrong-confident > right, the rule is "ask, never fill". | ~1 day, API cost small. | Likely a negative result for reconstruction, and a good "honest limitation" for the Noise Canceller entry. Also check Prisma's `bias_list` once (about ₹30-45, doc 16 §3.5): it is the only audio-aware lever. |
| **c) Emotion (data only)** | Add log fields to each turn: lexical anger/stress cues, whether a clarification was asked, outcome. No live use. Prisma exposes no audio features, so acoustic emotion would need our own pipeline on raw audio. | None needed to log. | ~1 hour. | Keep it modest: a 2025 review of 39 studies found **no consistent acoustic pattern for fear or anxiety** (cited in the paralinguistic report); do not label those. |
| **d) Timbre reads Hindi script but sounds like the dialect** | Only word-level flavour is reachable (Hindi spelling is near-phonemic, so Timbre speaks "रउआ/बा/बानी" as written). Accent, rhythm and vowel quality are decided inside Timbre. Build a 20-40 entry **native-reviewed swap table** (pronouns, set phrases, particles), whole-word swaps only, Bhojpuri first, only when detection is confident. Evon's own attempt ("सही कर देब बा") was ungrammatical. | 5-listener A/B on 10 sentences: plain vs flavoured, rated for understandable / natural / respectful-or-mocking. | ~Rs 1 of Timbre per 10 sentences; the real cost is native reviewers. | Riskiest item: over-imitating can sound mocking. Do it last and gate it. This is also the most *demo-able* piece for the Main Character award. |
| **e) Friction reduction (parallel thread)** | See section 3. | n/a | n/a | n/a |
| **f) Temperature by context** | **Pin it and log it; do not vary it.** Today `EvonReply` sends no sampling parameters, so the value in use is whatever the server defaults to, unknown and unlogged (doc 16 F4). Tone comes from instructions, not randomness. | One field in the request, one in the log. | Minutes. | A "happy → hotter" profile is the wrong knob; temperature changes wording variety, not mood, and risks improvised promises in a money call. |
| **g) Add emotion to Timbre via Evon** | Test objectively first: 10 sentences × {plain, punctuation-shaped, `speed` 0.9} = ~30 Timbre calls, measure duration, pauses and pitch range. | If the audio barely changes, stop. | ~₹3-5, an hour or two. | Pauses and pace are real levers; warm/sad/excited colour mostly is not. Confirm `speed` is honoured first. |

### 2.2 Order of work (synthesis, built from doc 16's pecking order plus the new inbound/outbound split)

1. Shared setup (2.0) and pin/log Evon sampling (f).
2. b2 clarify/confirm rule, then b1 phrasing fix. Cheapest, most protective, already proven on the Claude path.
3. a) Evon-as-detector test; outbound metadata prior vs inbound transcript.
4. b3 masked-word test and the one `bias_list` run.
5. g) and (c) logging.
6. d) last, only if 2-3 give a story worth voicing.

### 2.3 Calendar to the deadline (synthesis)

Today 10 Oct → 10 Nov is 31 days. Roughly: **to 17 Oct** call set and harness; **to 24 Oct** buckets a, b, f, g; **to 31 Oct** b3 and d; **1-7 Nov** 60-second demo and write-up; **8-10 Nov** submit, with buffer.
Start **posting early and honestly** (both hashtags): engagement verification is stage 2 of selection, and organic
engagement takes time. Bought or exchanged engagement is disqualifying.

---

## 3. (e) Reducing friction between people and AI: ten plain sentences

General findings from conversation and customer-service research, matching the repo's own research notes on repair,
clarification, accommodation and turn-taking. These are my summary and were **not re-verified source by source** here.

1. People forgive a machine that is slow or unsure far sooner than one that pretends to understand and gets it wrong.
2. Repeating back the one detail that matters ("so, Monday, you'll pay?") catches most mistakes for the cost of one short sentence.
3. A specific question ("Monday or Tuesday?") works better than "please repeat that".
4. Asking again in exactly the same way makes people louder and slower, which makes them harder to hear, so rephrase instead.
5. People relax when the other side talks a little like them, but copying too much, or too hard, feels like mockery.
6. Short replies with one idea each beat long polite ones, because callers lose the thread and talk over long answers.
7. On a phone, silence feels longer than it is, so a small "ji, ek second" stops people hanging up.
8. Say early what the system cannot do, instead of letting the caller find out after three failed tries.
9. An upset caller needs to hear "sorry for the trouble" before they care how fast the fix is, and the words carry more of that than the voice does.
10. A clear, easy way to reach a human lowers anger even when it is rarely used.

What to use now (synthesis): items 2, 3, 6, 8 map straight onto b2 and b1; 5 is the warning label on bucket d; 9 is the
safe part of g (words and pacing, not "emotion in the voice").

---

## 4. What was done, and root-cause analysis

### 4.1 What was done (read in docs/README, dates from git)

All 50 commits are dated 2026-10-05. Sequence: wire Evon on Modal → two Evon experiments on **typed** Bhojpuri → marker
derivation from Vaani → pivot to "grounding, not classification" → pull 24,986 clips through Prisma (19 dialects) →
fingerprint analysis → v1 detector → stability/CV rework → Bhojpuri reversibility test (negative) → phonetic filter →
many review/design prompts for other models → docs 16-18. I cannot tell from git how long each step took, only the order.

### 4.2 What went wrong, why, and what it cost

| # | What went wrong | Root cause | Evidence | Effect |
|---|---|---|---|---|
| 1 | **Built detection before showing detection changes an outcome.** | Hypothesis ("dialect grounding helps Evon") went in as a premise, not as the first test. | Doc 02: A and B both 5/5, "no measurable benefit"; README says the retrieval-grounding comparison is "not yet run as a scored experiment". The detector, 19-dialect audit and calibration followed anyway. | The biggest single block of effort sits on an unproven value chain. |
| 2 | **Wrong test data.** | Streetlight effect: we analysed what we had (25k Vaani pairs), not what the product sees. | All pairs are **image descriptions** ("a red shirt"), not calls (doc 16 F10); no standard-Hindi Prisma control exists (doc 18 §1); no 8 kHz phone audio. | Every threshold, channel table and lexicon is shifted off-domain. Transfer to calls is unmeasured. |
| 3 | **Early experiments bypassed Prisma and were too easy.** | Skipped audio because no recordings existed and fake TTS audio was ruled out. | Docs 01/02: Evon fed *typed* Bhojpuri. Experiment 2 was so easy that the no-glossary arm never failed (5/5). | A test that cannot fail cannot tell you the idea works. Only exposed one real comprehension miss (सोमारे, doc 01). |
| 4 | **Found the real blocker (output length vs Timbre) late.** | No end-to-end smoke test on day one. | Timbre failed 4 of 6 runs before the structured format; 10/10 after. | The best result of the project was an engineering fix, discovered after the research started. |
| 5 | **Measurement errors and single-run claims.** | Rigour applied after the numbers were quoted, not before. | "Combined" classifier was actually char-only; unicode NFC bug inflated divergence; difflib repeat-word artifact; Awadhi reported 0% then 30% on re-run; 16 of 19 dialects unstable across seeds; "group" was a collection proxy, not a speaker. | Corrections were honest and documented, but they overturned earlier conclusions (Rajasthani/Khortha demoted, Khortha+Surjapuri bucket dead, Haryanvi mis-bucketed). |
| 6 | **Over-investing in rigour on a low-value question.** | No stopping rule tied to a decision. | Leave-one-group-out run started, ~15% done, killed, replaced with a 15-seed version after a cost/benefit check (doc 09). | Roughly two hours (per doc 09) spent on routing-tier precision the decision did not need. |
| 7 | **Label noise in the data went unnoticed until late.** | Trusted dataset labels. | Kumaoni clips were recorded in Garhwal districts; 13/187 "Awadhi" clips are Marathi (doc 18 §2.7-2.8). | Part of the "Garhwali and Kumaoni are related" and "Awadhi ties to Chhattisgarhi" findings may be label artifacts. |
| 8 | **A premise that does not hold: "Prisma leaves identifiers in noise".** | Confused the human reference's noise tags with Prisma's output. | 0 of 25,139 Prisma transcripts contain a tag or bracket (measured today). | The noise-reconstruction design (b3) has no signal in the form assumed. |
| 9 | **Shipped an unvalidated behaviour.** | Feature added before a gate existed. | Claude path tells the model to "Talk with the user in Bhojpuri" for every caller (doc 16 F6) while docs 05/09 say default to Hindi when unsure. The Evon path lacks the clarify/`[UNCLEAR]` guard (F5). | Contradicts the project's own safety policy. |
| 10 | **Known reply-quality bugs left open.** | Moved on to the next question. | Replies tell the customer what to do rather than confirm (doc 02 Q9); subject flips ("I'll tell" → "we'll tell"); echoes on hardship cases (doc 05). | Real calls would read as "the agent did not listen". |
| 11 | **Document sprawl.** | Many prompts written for other models (docs 08, 10, 11, 15, 17) and overlapping answers. | Two files numbered 18; doc 07's numbers superseded by doc 09; stale tables kept with "supersedes" notes. | Hard for a new reader (or a judge) to find the current truth. |
| 12 | **No demo and no challenge-shaped goal.** | Built as a research programme and a hosted trial (Vercel, Postgres, ledgers, 161 tests), not as something to show in 60 seconds. | No post, video, or scripted call set in the repo; the README states "no accuracy has been measured". | Stage 1 of selection (a public demo) has not started. |
| 13 | **Infrastructure time sink.** | Self-hosting a 63 GB model with no hosted option. | Missing `nvcc`, too little host memory, 10 duplicate GPU containers from retries (experiments README). | Cost and delay; but the Evon requirement is the challenge's, not ours. |

### 4.3 Root causes, ranked (synthesis)

1. **Idea-before-evidence ordering.** The test that could falsify the value of dialect grounding was small, ran first,
   said "no gain", and did not redirect the plan.
2. **Data-driven instead of decision-driven.** Work followed what could be measured at scale (25k pairs), not what a
   call needs.
3. **No success metric tied to the challenge.** Nothing says what a finished demo shows or which award is the target.
4. **Rigour without a stopping rule.** Each correction was right; the sum went past what any decision needed.
5. **No call-shaped, noise-shaped, ground-truth test set.** Everything downstream inherits this gap.

### 4.4 What went *right* (keep, and show it)

- **Structured `INTENT/DETAILS/REPLY` output** made Timbre reliable. This is a genuine, reusable finding.
- **Negative results with numbers:** no safe text-only Prisma corrector exists (0 rules at any threshold; best reverse
  precision 66.7%; doc 13), extended to all 19 dialects (doc 16 §2.3-2.4). Under the challenge's own "honest limitation"
  rule this is a *feature* of a demo, not a flaw.
- **Evidence-gate design (doc 18):** surface only visibly non-Hindi forms and abstain otherwise: 0 false alarms on
  near-Hindi windows, 63% coverage on regional five-turn windows (measured, off-domain).
- **Honest reporting habit:** corrections were disclosed in the docs rather than hidden.

---

## 5. Not verified, and decisions needed from you

- Official scoring weights, interview content, and per-award judging detail: **not available** (not in the pasted text).
- Whether Prisma accepts `bias_list` usefully, honours any `denoise` option, or exposes anything in the streaming `raw`
  field: **untested**.
- Whether Timbre honours `speed` ≠ 1.0: **untested**.
- Whether Evon, asked directly, can tell Bhojpuri/Garhwali from standard Hindi: **untested** (the key experiment in 2.1a).
- **Your three ambiguity levels (Lvl-1,2,3):** I assumed a word/detail/intent ladder; tell me your definition and I will
  align bucket b2.
- **Which award to target.** Recommendation: Main Character (regional language), with a 60-second cut for Demo Day Drop.
  You can only win one.
- **Who speaks and reviews.** Buckets b and d need native-speaker scripts and review; who is that for each variety?
