# Experiment report: does business context improve Evon's handling of Bhojpuri customer replies?

## Important deviation from spec — read first

**Prisma was skipped entirely.** No real spoken audio existed for the three exact test sentences you wrote, and per your own instruction I did not synthesize fake Bhojpuri audio with Hindi TTS. The three Bhojpuri sentences were fed to Evon as plain text, standing in for what would have been Prisma's output. **This means Prisma's transcription accuracy was NOT tested in this experiment** — only Evon's comprehension of correctly-typed Bhojpuri text, with and without context. Treat the "Prisma" score column as N/A throughout.

Evon settings were identical across all 6 runs: same endpoint, no system prompt in either condition, no `max_tokens` cap (same as all prior baseline tests), same temperature/sampling (defaults, untouched).

---

## Comparison table

| Phrase | Condition | Prisma | Intent understood? | Key details | Response language (full output) | Evon chars | Hallucination | Timbre | Overall |
|---|---|---|---|---|---|---:|---|---|---|
| 1 Easy | A Raw | N/A | Yes (3/3) — promise to pay Monday | Monday ✓ | Mixed (EN reasoning → HI answer) | 1,347 | Minor | **Success** (200) | Good |
| 1 Easy | B Context | N/A | Yes (3/3) — explicitly tied to EMI | Monday ✓ | Mixed (EN reasoning → HI answer) | 4,345 | Minor | **Fail** (500) | Mixed — better framing, unusable audio |
| 2 Medium | A Raw | N/A | Partial (1/3) — misreads "सोमारे" as Nepali "soon" | Monday ✗ (wrong language guessed) | **Mixed/Nepali** — wrong language entirely | 3,827 | **Significant** | Fail (500) | Poor |
| 2 Medium | B Context | N/A | Partial (2/3) — "no money now" ✓, timing wrong ("tomorrow" not Monday) | Monday ✗ | Mixed (EN reasoning → HI answer) | 2,759 | Minor | Fail (500) | Mixed — better language, still wrong detail |
| 3 Hard | A Raw | N/A | Good (2/3) — 2-day extension + salary, assumes employer/HR context | 2 days ✓, salary ✓ | Mixed (EN reasoning → HI+EN answer) | 1,584 | Minor | **Success** (200) | Good, slightly off-context |
| 3 Hard | B Context | N/A | Good (3/3) — extension + salary, explicitly tied to EMI due date | 2 days ✓, salary ✓ | Mixed (EN reasoning → HI answer) | 3,840 | Minor | Fail (500) | Best understanding, unusable audio |

---

## Full evidence

### Test 1A — Raw
**Transcript (used as proxy for Prisma output):** हम सोमवार के पैसा जमा कर देब।
**Evon request:** the transcript alone, nothing else.
**Evon raw output (1,347 chars, 327 completion tokens):**
> We are given a user message... [reasons in English that the user is confirming payment Monday] ...
> **Final: "ठीक है, सोमवार को जमा कर देंगे।"** ("Okay, will deposit on Monday.")

**Timbre:** Success, 200, 8.2MB audio (~85s).

### Test 1B — Context
**Evon request:** EMI-lender context template + the same transcript.
**Evon raw output (4,345 chars, 989 completion tokens):**
> Explicitly reasons about "the customer called because they were supposed to pay an EMI today"... considers whether today is before/after Monday... drafts several Hindi responses...
> **Final: "आपकी सूचना के लिए धन्यवाद। सोमवार को आपके ईएमआई का भुगतान प्राप्त कर लिया जाएगा..."** ("Thank you for informing us. Your EMI payment will be received on Monday...")

**Timbre:** Fail, 500, "We are facing technical difficulties."

### Test 2A — Raw
**Transcript:** अभी पइसा नइखे, सोमारे जमा कर देब।
**Evon raw output (3,827 chars, 1,064 completion tokens):**
> Reasons that "सोमारे" might be **Nepali** for "soon." Explicitly says: *"the user wrote in Nepali... So I need to reply in Nepali."*
> **Final (in Nepali, not Hindi or Bhojpuri): "पनि छ। तिमी पइसा जमा गर्नुहोस्, हामी त्यसपछि प्रोसेस गर्छौं।"**

This is a real comprehension failure — Evon invented an entirely wrong language identity for a genuine Bhojpuri word and replied in Nepali, which a Bhojpuri/Hindi speaker would not understand well.

**Timbre:** Fail, 500.

### Test 2B — Context
**Evon raw output (2,759 chars, 664 completion tokens):**
> Correctly translates "अभी पइसा नइखे" as "I don't have money now." Misreads "सोमारे" as "tomorrow" (actual meaning: "on Monday" — Bhojpuri cognate of Hindi सोमवार). Frames itself explicitly as the lender's representative.
> **Final: "अच्छा, हम आपके कल के भुगतान को स्वीकार करते हैं। कृपया समय रहते भुगतान कर दें।"** ("Alright, we accept your payment tomorrow. Please pay on time.")

Context fixed the language-identity failure (no more Nepali) and kept the lender framing, but the specific day is still wrong.

**Timbre:** Fail, 500.

### Test 3A — Raw
**Transcript:** दू दिन मोहलत दे दीं, तनखा आवे वाला बा।
**Evon raw output (1,584 chars, 406 completion tokens):**
> Correctly parses "दू दिन" (two days), "मोहलत" (extension/grace), "तनखा" (salary). Assumes an employer/HR context (reasonable guess, not given).
> **Final: "सही है, तनखा मिल जाएगी। अपना खाता चेक करते रहें या HR से बात करें... Take care!"**

**Timbre:** Success, 200, 9.4MB audio (~98s).

### Test 3B — Context
**Evon raw output (3,840 chars, 996 completion tokens):**
> Correctly parses all key entities, explicitly reasons about the EMI due date and the customer needing to pay once salary arrives, resolves internal ambiguity about who granted the extension.
> **Final: "हमने आपकी EMI के लिए दो दिनों की मोहलत दे दी है। आपका तनखा आज शाम तक आ जाएगी तो कृपया उसी समय भुगतान कर दीजिए..."** — the single most contextually correct and complete answer of all 6 runs.

**Timbre:** Fail, 500.

---

## Answers to your 7 questions (conservative)

**1. Does context materially improve interpretation?** Partially, yes — but unevenly. On Test 2, context eliminated a serious failure mode (Evon inventing a wrong language — Nepali — for a Bhojpuri word) and kept the lender framing. On Test 3, context produced the single best, most complete answer of the experiment. On Test 1, both conditions already understood the easy phrase correctly — context added lender-specific framing but no comprehension gain, since there was nothing to gain. **Context helps on medium/hard ambiguity, not on easy phrases that already work.**

**2. Does context reduce over-reasoning?** No — the opposite. Context conditions were longer in 2 of 3 phrases (1B: 4,345 vs 1,347; 3B: 3,840 vs 1,584) and shorter in only one (2B: 2,759 vs 3,827). Context gives Evon more to reason about (the EMI scenario, the due date, who's calling whom), which on average produced *more* text, not less.

**3. Does Evon understand dialect-specific vocabulary (नइखे, सोमारे, मोहलत, तनखा)?** Mixed and genuinely instructive:
   - **नइखे** (Bhojpuri negation): understood correctly in both Test 2 conditions ("don't have money now").
   - **सोमारे** (Bhojpuri "on Monday"): **misunderstood in both conditions** — raw guessed it was Nepali for "soon," context guessed "tomorrow." Neither got "Monday."
   - **मोहलत** (grace period/extension): correctly understood in both Test 3 conditions — but this is standard Hindi/Urdu vocabulary, not Bhojpuri-specific, so this isn't evidence of dialect understanding.
   - **तनखा** (salary): correctly understood in both — also standard Hindi/Urdu, not Bhojpuri-specific.
   So of the two genuinely Bhojpuri-specific words tested, one (नइखे) was understood and one (सोमारे) was not, in either condition.

**4. Does context improve response-language alignment?** Yes, measurably. Test 2A replied in **Nepali** — the only fully wrong-language response in the experiment — and context (2B) fixed that back to Hindi. Elsewhere, both conditions replied in Hindi for the final answer regardless. But every single one of the 6 raw outputs (the full text sent to Timbre) was **Mixed language** — English chain-of-thought reasoning followed by a Hindi final line — because there is no system prompt suppressing the visible reasoning. This mixed-language reasoning text is itself a problem independent of context.

**5. Does it reduce output enough to make Timbre more reliable?** No. Timbre succeeded on exactly 2 of 6 runs, and **both successes were Condition A (raw), not B (context)**. All 3 context-grounded runs failed on Timbre. Context made replies longer on average, which made Timbre less reliable, not more.

**6. Which failure matters most after this test?**
   In order of impact on this specific business use case:
   1. **Excessive generation / lack of output control** — this is the dominant failure. It broke Timbre in 4 of 6 runs regardless of context, and it's the direct cause of #2.
   2. **Response-language selection** — the full output is always English-reasoning-then-target-language-answer, which is unnatural for TTS and caused the one severe comprehension failure (Nepali in 2A).
   3. **Bhojpuri comprehension** — real but narrower than expected: standard Hindi/Urdu loanwords (मोहलत, तनखा) are understood fine; genuine Bhojpuri-specific forms (सोमारे) are not.
   4. **Intent reasoning** — generally sound once vocabulary is parsed correctly; not the bottleneck.
   5. **Timbre limitations** — real (the ~1,500–2,800 character cutoff), but downstream of #1, not an independent root cause.
   (Prisma transcription accuracy cannot be ranked — it wasn't tested here.)

**7. Is a loan-collections workflow technically plausible on this stack right now?** **Not as currently configured, no.** The core blocker is structural, not marginal: Evon's unconstrained chain-of-thought reasoning makes its raw output too long for Timbre to speak in the majority of real cases (4/6 here), and this persists whether or not business context is given. A production collections agent needs every customer interaction to produce speakable audio — a 33% Timbre success rate is not viable. Getting this plausible would require resolving the "no post-processing, no system prompt, but bounded output" tension that was flagged as an open problem after the first round of testing — business context alone does not resolve it, and in fact tends to make the raw-output-length problem slightly worse.
