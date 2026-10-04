# Boli experiment 2 report: business task vs business + dialect grounding

Prisma was not evaluated — the 5 statements below are treated as given, final Prisma output per your instruction. Only Evon and Timbre were tested.

## Final comparison table

| Statement | Condition | Intent | Details | Reply | Language | Hallucination | Timbre | Overall |
|---|---|---:|---:|---|---|---|---|---|
| 1 Tomorrow | A Business | 3 | 3 | "कल जमा कर दीजिएगा।" (phrased as an instruction, not a confirmation) | Hindi | None | Success | Good, slightly off in tone |
| 1 Tomorrow | B +Boli | 3 | 3 | "ठीक है, कल जमा कर दीजिए।" (adds acknowledgment opener) | Hindi | None | Success | Good, marginally better tone |
| 2 Monday | A Business | 3 | 3 — correctly resolved सोमारे→Monday **without** the card | Hindi | None | Success | Good |
| 2 Monday | B +Boli | 3 | 3 | Hindi, more polite form | Hindi | None | Success | Good, no material gain over A |
| 3 Two days | A Business | 3 | 3 | Correct extension + salary logic, slight logical inversion (reads as instruction not grant) | Hindi | None | Success | Good |
| 3 Two days | B +Boli | 3 | 3 | Same logic, marginally more polite | Hindi | None | Success | Good, no material gain over A |
| 4 Already paid | A Business | 3 — correctly extracted "payment_made_recently / paid_yesterday" | 3 | "ठिक बा, फोन आज शाम तक बंद हो जाए." — implies resolution, doesn't explicitly confirm receipt | Hindi/Bhojpuri mix ("ठिक बा" is Bhojpuri) | None | Success | Adequate, could confuse customer (no explicit "yes, received") |
| 4 Already paid | B +Boli | 3 — "Payment confirmation / Paid yesterday" | 3 | "भिजवा देंगे, अब कोई कॉल नहीं आएगा." — also implicit, not explicit | Hindi | None | Success | Adequate, same gap as A |
| 5 Half now | A Business | 3 | 3 — correctly captured split payment (half today + next week) | Hindi | None | Success | Good, natural confirmation tone |
| 5 Half now | B +Boli | 3 | 3 | Hindi, near-identical quality | Hindi | None | Success | Good, no material gain over A |

**All 10/10 succeeded on Timbre.** Every REPLY was short (character counts of the extracted replies ranged roughly 15–50 characters — the full raw outputs were 796–4,183 characters, but only the REPLY line was ever sent to Timbre, which is why this worked where the earlier experiment failed.)

---

## Full evidence (key excerpts)

### 1 — "अभी पइसा नइखे, काल्हे जमा कर देब।" (expected: "no money now, will pay tomorrow")
- **A:** INTENT: future_payment · DETAILS: payment tomorrow · **REPLY: "कल जमा कर दीजिएगा।"**
- **B:** INTENT: Payment postpone · DETAILS: Tomorrow payment · **REPLY: "ठीक है, कल जमा कर दीजिए।"**
- Both correctly decoded "काल्हे" = tomorrow and "नइखे" = don't have, with or without the card.

### 2 — "आज पइसा ना बा, सोमारे दे देब।" (expected: "no money today, will pay Monday")
- **A:** INTENT: payment delay request · DETAILS: payment on Monday · **REPLY: "सोमवार को दे देना।"**
- **B:** INTENT: payment_upcoming · DETAILS: Will pay on Monday · **REPLY: "सोमवार को दे दीजिएगा।"**
- **Notable: this is the exact word ("सोमारे") that failed in the previous experiment** (misread as Nepali "soon" in one condition, "tomorrow" in another). Here, **both** conditions — including the one *without* the Boli card — correctly resolved it to Monday.

### 3 — "दू दिन अउरी मोहलत दे दीं, तनखा आवे वाला बा।" (expected: "two more days, salary coming")
- **A:** INTENT: Moratorium request · DETAILS: extension of two days until salary · **REPLY: "हाँ, तनखा आने पर दो दिन में भुगतान कर दीजिएगा।"**
- **B:** same structure · **REPLY: "ठीक है, तनखा आने पर दो दिन बाद भुगतान कर दीजिएगा।"**
- Both correct on "दू दिन" (two days) and "तनखा" (salary). Minor issue in both: the reply reads as *telling the customer when to pay* rather than *granting* the extension they asked for — a tone/logic inversion present in both conditions equally.

### 4 — "हम त काल्हे पइसा जमा कर देले बानी, फेर काहे फोन आ रहल बा?" (expected: "already paid yesterday, why calling?") — hardest case
- **A:** INTENT: payment_made_recently · DETAILS: paid_yesterday · **REPLY: "ठिक बा, फोन आज शाम तक बंद हो जाए."**
- **B:** INTENT: Payment confirmation · DETAILS: Paid yesterday · **REPLY: "भिजवा देंगे, अब कोई कॉल नहीं आएगा."**
- Both correctly decoded "देले बानी" (have already paid) — this is genuinely Bhojpuri past-tense construction, absent from standard Hindi, and both conditions got it right. The Boli card explicitly defines this term, but A got it right without seeing that definition.

### 5 — "पूरा पइसा अभी ना दे पाइब, आधा आज देब बाकी अगिला हफ्ता।" (expected: "can't pay full now, half today + rest next week")
- **A:** **REPLY: "आज आधा भुगतान कर देंगे, बाकी अगले हफ्ते।"**
- **B:** **REPLY: "आधा आज दे रहे हैं, बाकी अगला हफ्ता में दे देंगे."**
- Both correctly captured the split-payment structure. Near-identical quality.

---

## Answers to your 10 questions

**1. How many of 5 understood correctly with business instructions alone (Condition A)?** All 5. Every single Condition A run correctly identified intent and the key date/amount detail, including the two hardest cases (the "already paid" past-tense construction and the "two days + salary" implicit extension request).

**2. How many with the Boli card (Condition B)?** Also all 5 — same hit rate, not higher.

**3. Which specific Bhojpuri words caused failures without Boli?** **None, in this run.** This is the critical finding: in the *previous* experiment, "सोमारे" was genuinely misunderstood without context (misread as Nepali). In *this* experiment, with the tighter business-task prompt alone (no Boli card), Evon correctly resolved सोमारे, नइखे, काल्हे, देले बानी, and ना दे पाइब — all without the glossary.

**4. Did the Boli card fix those failures?** There were no failures to fix in Condition A this time, so this can't be demonstrated here. The card's apparent effect in the previous experiment may have been less about vocabulary and more about the tighter business-task framing itself, which this experiment adds to both conditions equally.

**5. Did either condition hallucinate dates, amounts, or intent?** No. Across all 10 runs, every date (tomorrow, Monday, two days), every split-amount detail (half now/half next week), and every intent label matched the expected meaning. Zero hallucinations observed.

**6. Were replies consistently short enough for Timbre?** Yes — this was the deciding structural fix. Forcing a `REPLY:` field and extracting only that line (not the reasoning, not INTENT/DETAILS) kept every spoken sentence to roughly one line, regardless of how long Evon's internal reasoning ran (up to 4,183 characters in one case) before it.

**7. Did Timbre speak all or most of the responses?** All — 10 of 10, 100% success.

**8. Is Evon adding meaningful reasoning value, or is the grounding card doing most of the work?** Neither, exactly — **the structured task format (forcing INTENT/DETAILS/REPLY) is doing most of the work**, not the Boli card. Evon's underlying comprehension of these specific Bhojpuri constructions appears to already be adequate when given a clear task and output constraint; the extra glossary didn't change outcomes in this run. Be skeptical of over-crediting "Boli" here — the controlled comparison (A vs B, same task format) shows no measurable gain from the card itself.

**9. Could this architecture support an EMI collections voice agent?** Closer to plausible than the previous experiment showed, with one real caveat: comprehension and brevity are solved by this prompt structure, but **several replies are phrased backwards** — telling the customer what to do ("please pay on Monday") rather than confirming what the customer already said they'd do. In a real call this reads as the agent not having listened. That's a prompt-wording issue, fixable, but present in both conditions and not something this experiment was designed to catch — worth a follow-up pass on reply phrasing specifically.

**10. Does a tiny reusable dialect grounding layer materially improve Evon without fine-tuning?** **Not demonstrated in this run — be conservative here, as you asked.** The honest result is: Evon handled these 5 Bhojpuri statements correctly *with the structured business-task prompt alone*, and adding the Boli glossary card produced no measurable improvement in intent accuracy, detail accuracy, or Timbre success (both conditions were already at 5/5 and 10/10 respectively). The strongest claim this data supports is narrower than the Boli hypothesis: **a tightly-scoped business task + forced short-output format reliably fixes the two real problems we found last time (over-reasoning breaking Timbre, and language-identity confusion on dialect words) — independent of whether a dialect glossary is present.** To actually test the Boli hypothesis, you'd need harder/rarer Bhojpuri vocabulary than these 5 statements contained, since nothing here was hard enough to make Condition A fail.
