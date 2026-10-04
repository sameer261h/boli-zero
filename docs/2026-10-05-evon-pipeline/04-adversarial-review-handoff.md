# Codex: adversarial review of the Gnani Bhojpuri voice pipeline work

You are reviewing a long experimental session building a Bhojpuri-capable voice pipeline (Evon v3.3 on Modal + Gnani's Prisma STT and Timbre TTS). Your job: **find the holes, false confidence, and things that will break in production.** Do not validate anything just because it "worked" in a small test. Be skeptical by default.

## What's actually deployed (real, running infrastructure)

- **Evon v3.3** (30B-A3B, BF16, NemotronH architecture) on Modal, single A100 80GB via vLLM. OpenAI-compatible endpoint, no system prompt, no auth.
- **Prisma** (Gnani hosted STT, `api.vachana.ai/stt/v3`) and **Timbre** (Gnani hosted TTS, `api.vachana.ai/api/v1/tts/inference`) — real paid APIs, called directly.
- An orchestration endpoint on Modal chaining Prisma → Evon → Timbre.
- All of this has been tested with real spoken Bhojpuri audio (from the gated, licensed `ARTPARK-IISc/Vaani` dataset) and with typed Bhojpuri text standing in for Prisma output in later rounds.

## Hard constraint that shaped everything

**Bhojpuri is not an officially supported language on Prisma or Timbre.** Both only support Bengali, English, Gujarati, Hindi, Kannada, Malayalam, Marathi, Punjabi, Tamil, Telugu (+ Hinglish on Timbre). Every test used `hi-IN` as the closest approximation for Prisma, and `auto`/`hi-IN` for Timbre. This is a permanent constraint, not a bug to fix.

## What we found, round by round — find the holes in each claim

### 1. Prisma transcribes Bhojpuri-as-Hindi surprisingly well
On the one real audio sample with a human-verified ground-truth transcript, Prisma's `verbatim` output was essentially word-for-word identical. **Adversarial question: this is N=1. Is there any reason to believe this generalizes, or did we just get a lucky speaker/sample?** We never tested a second ground-truth-labeled sample.

### 2. Evon over-reasons on open-ended statements, not short inputs
Short input ≠ short output. A 57-character Bhojpuri statement produced a 6,244-character Evon reply because Evon treated a plain description as a riddle to solve. This is root-caused to "no system prompt + non-question input," not to Bhojpuri specifically — reproduced with plain English and Hindi too.
**Adversarial question: is "no system prompt" actually a hard requirement from the business, or was it a self-imposed constraint from early in the session that may no longer make sense now that we're deep into prompt-engineering structured tasks (INTENT/DETAILS/REPLY) anyway?** Worth checking — later experiments already violate the spirit of "no system prompt" by giving Evon elaborate structured-output task instructions. Is there still a real "no system prompt" rule, or did it quietly get dropped?

### 3. Timbre has an undocumented length cutoff
Confirmed: 1,135 chars succeeded, 1,347 chars succeeded, 2,759+ and up all failed with a generic 500 "technical difficulties" error. **The exact threshold was never properly bisected — we have a range (~1,500–2,800 chars), not a number.** Also never confirmed whether the limit is in characters, bytes, or tokens, or whether it varies by script/language.

### 4. Structured task prompting (INTENT/DETAILS/REPLY, extract only REPLY) fixed both #2 and #3
10/10 Timbre successes once only the REPLY line was sent, across 5 realistic EMI customer statements, in two conditions (business-prompt-only vs business-prompt + dialect glossary).
**Adversarial question: this was tested on exactly 5 statements, all collections-call language. Does it hold on statements requiring a longer *necessary* answer (e.g., explaining a multi-step process)? We've only proven short Timbre-safe answers work for *short-answerable* intents.**

### 5. The dialect glossary card added no measurable benefit over business-prompt-alone
Both conditions hit 5/5 correct intent and 10/10 Timbre success. Headline claim from this round: **the "Boli hypothesis" (tiny reusable dialect card unlocks comprehension) was NOT demonstrated** — the structured task format did the work, not the glossary.
**Adversarial question: is 5 statements, all fairly clean single-fact declaratives, a fair test of this hypothesis at all? We explicitly noted afterward that nothing in that round was hard enough to make the no-glossary condition fail.**

### 6. On harder/ambiguous statements, real comprehension bugs surfaced
- Subject-flip bug: customer says "I'll tell you," Evon's reply says "We'll tell you" (happened twice, independently).
- On evasive/vague statements, Evon resolves ambiguity toward false confidence (invented a specific commitment where none existed).
- On "customer already paid" and "wrong number" categories, Evon's reply just echoed the customer's own statement back instead of generating an actual agent response.
**Adversarial question: these bugs appeared on exactly 6 new statements, informally designed by the human operator in this session, not by a domain expert in collections scripting. Are these representative failure categories, or cherry-picked/anecdotal? No statistical claim should be made from N=6 hand-picked examples.**

### 7. Direct "respond in Bhojpuri" instruction is unreliable and sometimes corrupts script
Tested 3 times total (across two separate attempts): one produced clean, grammatically real Bhojpuri (बा-copula, correct morphology). Two others produced **literal Bengali-script characters mixed into Devanagari text**, and a separate dedicated-translation attempt produced **Roman/Latin-letter transliteration instead of Devanagari** in one case and **mixed Devanagari+Roman in the same sentence** in another.
**Adversarial question: N=3 for the corruption claim, N=3 for the clean-Bhojpuri claim's counter-evidence. This is a strong enough failure mode (nonsense script = literally unspeakable by TTS) that it needs far more repetition before anyone treats "sometimes it works" as a usable strategy. What's the actual corruption rate — 2/6? Higher? We don't know.**

### 8. Avoiding the word "Bhojpuri" and instead giving style cues worked better
Two mechanisms tested without ever naming the target language to Evon: a lexicon card (2/3 dialect-flavored, 1/3 reverted to plain Hindi) and few-shot style examples (3/3 dialect-flavored, zero script corruption across all 9 outputs in that round).
**Adversarial question: is "never naming Bhojpuri" actually the causal fix, or coincidence from a small sample? We have zero corruption events in 9 trials here vs corruption in roughly half of the ~5-6 trials where "Bhojpuri" was named explicitly — that's suggestive, not proven. Also: these 9 outputs were visually inspected by the human operator, not scored by a native Bhojpuri speaker. Nobody has confirmed these actually sound authentically Bhojpuri to a real speaker — only that they contain known marker words (बा, देब) and aren't script-garbled.**

### 9. A deterministic marker-based language identifier was built and validated
Checks a transcript against ~20 known Bhojpuri marker words/forms, with a confidence score (unique markers / 3, capped at 1.0) and a 0.67 threshold that defaults to "Hindi" below it. Validated: 6/8 true-Bhojpuri statements correctly flagged, 2/8 appropriately low-confidence (single-marker, correctly defaulted to Hindi per the threshold rule), 5/5 Hindi statements correctly NOT flagged (after fixing a word-boundary bug that initially false-positived on "बाइके" containing "बा").
**Adversarial question: the marker list (~20 words) was hand-assembled by the operator across this session, not sourced from a linguistic authority. Coverage is unknown and unmeasured — we have no idea what fraction of real Bhojpuri utterances contain zero of these 20 markers and would be silently misclassified as Hindi. N=13 total validation cases is not a real validation set.**

### 10. Research literature check (AI4Bharat/IIT Madras paper on rural Bhojpuri ASR)
Confirmed Bhojpuri ASR is a genuinely unsolved, industry-wide hard problem (29.1% best-case WER vs 15% for Hindi, even with dedicated training data + synthetic augmentation). Also found their own result that **just mixing in Hindi training data gave inconsistent, near-zero net benefit** — which should make us skeptical of how far "treat Bhojpuri as Hindi" can really go for Prisma, long-term, even though it worked on our one test sample.

### 11. Scaling beyond Bhojpuri to Vaani's other ~135 dialects — not yet attempted
Checked: Vaani has 136 folders under `audio/`, many of which are state-name catch-alls, not real dialects. Of those, only 59 languages/dialects have any transcribed text at all (2,041 hours total, wildly uneven distribution — unknown how many hours per dialect). Checked for existing published lexicons: found one real one (IIT BHU NLP Lab, GitHub `singhakr/Bhojpuri-Magahi-and-Maithili-Linguistic-Resources`) covering only 3 of the ~59 transcribed dialects (Bhojpuri, Magahi, Maithili) — and even that lexicon's `Meaning` field was unfilled placeholder text in the sample checked, and it's WX-transliterated, not Devanagari. **No usable multi-dialect marker resource exists off-the-shelf.** A general "markers for all Vaani dialects" system would require either (a) hand-curating ~56+ more dialects with no available linguistic source material for most of them, or (b) a corpus-frequency-derived approach (compare each dialect's transcripts against a Hindi reference corpus, extract statistically over-represented words) — untested, and only viable for dialects with enough transcribed volume, which is unknown per-dialect.

## Where we actually stand right now — be blunt

- **Core pipeline works mechanically.** Audio in, transcript out, LLM reply out, speech out — the wiring is solid and has been load-bearing through many iterations.
- **The single biggest unresolved problem is Evon's raw output length/behavior**, not Bhojpuri comprehension specifically. Structured-task prompting is a real, working mitigation for this — but only tested on short-answerable business intents.
- **The "Boli hypothesis"** (a small reusable dialect grounding layer meaningfully improves comprehension) **has not been demonstrated.** Every test so far either didn't need the glossary (statements too easy) or showed no measurable gain from it.
- **Making Evon's output actually *sound* Bhojpuri (not just mechanically Hindi) is still an open, partially-solved problem.** Avoiding naming the language and using few-shot style examples is the most promising lead, with zero script-corruption in its one 9-trial round — but that's one round, unverified by a native speaker, and the failure mode when it breaks (wrong Unicode script entirely) is catastrophic for production use, not a quality nit.
- **Every quantitative claim in this document is based on very small N (3–13 trials per claim).** Nothing here should be treated as statistically validated. This entire session is a fast exploratory spike, not a benchmark.
- **No native Bhojpuri speaker has evaluated any output for actual authenticity/naturalness.** All judgments of "sounds Bhojpuri" so far are the operator pattern-matching on known marker words appearing in Devanagari text — not a real listening evaluation by someone who speaks the dialect.
- **A general solution for Vaani's other ~58 transcribed dialects does not exist and has not been scoped for effort.** The IIT BHU lexicon covers 3 of them with real caveats; the rest would need new work with no clear data foundation for most.

## Your job

1. Poke holes in anything above that sounds more confident than the evidence supports.
2. Identify which of the 11 findings are actually load-bearing for a real product decision vs which are session-level curiosities that shouldn't influence anything yet.
3. Propose what the next 2-3 actually rigorous experiments should be, given everything above, prioritized by what would most change the current "where we stand" assessment if it came out differently.
4. Flag any contradiction between findings (e.g., #3's Timbre length cutoff vs #4's "structured prompting fixes it" — does #4 actually guarantee compliance, or did we just get lucky 10/10 times with short collections-call answers specifically?).
