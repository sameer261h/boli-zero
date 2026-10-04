# Part A — Prompt for Codex

---

You're joining an in-progress project: a Bhojpuri/dialect-aware voice pipeline built on Gnani's Prisma (STT) → Evon v3.3 (30B-A3B LLM) → Gnani's Timbre (TTS), all deployed on Modal. Neither Prisma nor Timbre officially support Bhojpuri or any other regional Indic dialect — both only support 10 major Indian languages (Bengali, English, Gujarati, Hindi, Kannada, Malayalam, Marathi, Punjabi, Tamil, Telugu) plus Hinglish. Every dialect speaker's audio gets transcribed by Prisma using `hi-IN` as the closest approximation, producing Hindi-script text that may contain dialect words Prisma transcribed phonetically but didn't normalize.

**What already exists and is validated (don't redo this):**
- A deterministic Bhojpuri marker detector (`boli_identifier.py`): 93 markers, derived by comparing real word frequencies across 5,903 real Bhojpuri transcripts vs 6,840 real Hindi transcripts from the `ARTPARK-IISc/Vaani-transcription-part` dataset (not hand-picked guesses — every marker appeared 0 times in the Hindi set and 35+ times in the Bhojpuri set). Confidence-scored (unique markers / 3, capped at 1.0), 0.67 threshold, defaults to "Hindi" below threshold. Validated: 6/8 true positives, 2/8 appropriately low-confidence, 0/5 false positives on a held-out set.
- The *same derivation technique* generalizes to any of the 59 dialects/languages that have transcribed text in `Vaani-transcription-part` — just rerun the frequency comparison with a different dialect name. Not yet done for dialects beyond Bhojpuri.
- Structured-task prompting for Evon (`INTENT: / DETAILS: / REPLY:` format, extract only REPLY for Timbre) reliably keeps Evon's output short enough for Timbre to succeed — 10/10 across 5 EMI-collections test statements. Before this fix, Evon's raw unstructured replies ranged 1,100-6,200+ characters and broke Timbre roughly half the time (confirmed cutoff somewhere between ~1,500-2,800 characters, never precisely bisected).
- Getting Evon to produce dialect-*flavored* output (not just comprehend dialect input) is unsolved. Explicitly naming "Bhojpuri" as a target language in the prompt caused real script corruption twice — Bengali-script characters mixed into Devanagari output, and separately, Roman-letter transliteration mixed into Devanagari in the same sentence. Avoiding the language name and instead giving either (a) a lexicon substitution card or (b) few-shot style-transfer examples (standard-Hindi sentence → dialect-flavored-Hindi sentence pairs, no language named) avoided corruption entirely across 9 trials — few-shot was more consistent (3/3 flavored) than the lexicon card (2/3). This is weak evidence (N=9), not a proven fix.
- Known real comprehension bugs on ambiguous/evasive customer statements: Evon sometimes flips the subject of reporting verbs (customer says "I'll tell you," Evon's reply says "we'll tell you"), resolves vague statements toward false confidence, and on some categories (genuine hardship, wrong-number) just echoes the customer's statement back instead of generating an actual agent response.

**Your task — design and write the logic for three connected pieces:**

**(a) Multi-dialect identification from Hindi-script text, with false-positive handling, operating within a selectable business context.**
Given Prisma's Hindi-script output (which may be any of several dialects phonetically rendered), identify which dialect (if any) it actually is, using marker sets built the way `boli_identifier.py`'s Bhojpuri set was built (corpus-frequency-derived, not guessed) — assume we will have marker sets for Bhojpuri plus at least 2-3 other dialects by the time this runs (propose which ones are worth prioritizing, and how you'd pick). Design for: multiple business contexts to exist simultaneously (e.g. EMI collections, telecom support, a government/healthcare helpline — give at least 3 concrete ones with their own task templates), ambiguity between closely-related dialects that share vocabulary (e.g. the Bihari family — Bhojpuri/Magahi/Maithili/Angika likely share many markers; a naive highest-match approach may misfire between them), and calibrated confidence handling — not just a binary threshold, but what happens in the gray zone, how false positives get logged/caught, and whether a "confidently wrong dialect" is worse than "correctly defaulted to Hindi" for this use case (argue your position).

**(b) Taking Evon's structured REPLY and enhancing it to sound like the detected dialect**, using the corpus-derived marker dataset as the available resource — not by naming the dialect to Evon (known to corrupt), and not by blind find-replace alone (we found our small hand-built substitution dictionary matched 0/3 of Evon's natural outputs — too narrow, brittle). Propose the actual mechanism: few-shot construction dynamically built from whichever dialect was detected, a verification/retry loop using the same marker-detector run on Evon's *output* to check the flavoring actually took (this was never tested — mechanism B reverted to plain Hindi 1 of 3 times when it was supposed to flavor the output, and nothing caught that), and a deterministic fallback path that's guaranteed to produce *something* dialect-flavored even if generation fails or produces corrupted script.

**(c) Final Timbre call** — explain the real ceiling here: Timbre has no dialect voice options at all (10 languages + Hinglish + auto, nothing else), so "sound like the caller's language" can only ever mean lexical/script-level flavoring of Devanagari text read by the closest-matching Hindi-family voice — not actual dialectal accent or phonology. State this plainly rather than overselling what's achievable, and note any remaining risk (e.g. the Bengali-script corruption bug, if it recurs after enhancement, means Timbre either fails outright or mispronounces badly — propose what should trigger a safe fallback to the plain, un-enhanced Hindi REPLY instead of sending garbled text to a real customer call).

Be concrete — pseudocode or real Python for the identification confidence logic and the retry/fallback state machine, not just prose description. Flag anywhere you think our prior findings (small N, mostly single-operator judgment calls) are too weak to build production logic on top of.

---

# Part B — My own proposed logic

## (a) Multi-dialect identifier

```python
# Per-dialect marker sets, each independently corpus-derived the same way
# Bhojpuri's was (see derive_markers_from_corpus.py — rerun per dialect name).
DIALECT_MARKER_SETS = {
    "bhojpuri": {...},   # done — 93 markers
    "awadhi": {...},     # not yet derived
    "maithili": {...},   # not yet derived
    "magahi": {...},     # not yet derived — high overlap risk with bhojpuri (Bihari family)
}

# Markers that appear in >1 dialect's derived set are "shared family markers" —
# weight them lower than markers exclusive to one dialect, since they can't
# discriminate between closely related dialects.
def compute_exclusive_weights(marker_sets: dict) -> dict:
    from collections import Counter
    all_markers = Counter()
    for markers in marker_sets.values():
        for m in markers:
            all_markers[m] += 1
    # weight = 1 / (number of dialects this marker appears in)
    return {m: 1.0 / count for m, count in all_markers.items()}

def identify_dialect(transcript: str, marker_sets: dict, weights: dict,
                      threshold: float = 0.67, min_margin: float = 0.15) -> dict:
    scores = {}
    for dialect, markers in marker_sets.items():
        matched = [m for m in markers if m in transcript]  # reuse isolation-filter logic
        weighted_score = sum(weights.get(m, 1.0) for m in matched)
        confidence = min(1.0, weighted_score / 3)  # same saturation logic as today
        scores[dialect] = {"confidence": confidence, "matched": matched}

    ranked = sorted(scores.items(), key=lambda x: -x[1]["confidence"])
    top_dialect, top = ranked[0]
    second_confidence = ranked[1][1]["confidence"] if len(ranked) > 1 else 0.0

    if top["confidence"] < threshold:
        return {"dialect": "hindi", "confidence": top["confidence"],
                "reason": "below_threshold", "all_scores": scores}

    if top["confidence"] - second_confidence < min_margin:
        # Two dialects scored close together — likely a shared-family word,
        # not a confident single-dialect match. Default to the shared
        # family's closest "safe" dialect (e.g. Bhojpuri, since it's the
        # best-resourced), but flag it as uncertain for logging.
        return {"dialect": top_dialect, "confidence": top["confidence"],
                "reason": "ambiguous_family_low_margin", "all_scores": scores}

    return {"dialect": top_dialect, "confidence": top["confidence"],
            "reason": "confident", "all_scores": scores}
```

**On the "confidently wrong vs correctly defaulted" question:** defaulting to Hindi is always the safer failure — a Hindi-flavored reply to a Bhojpuri speaker is mildly impersonal but fully intelligible and was already proven to work end-to-end (10/10 Timbre success in the EMI experiment). A *wrong* dialect flavor risks actually confusing the listener or, worse, re-triggering the script-corruption bug on a dialect we have no validated marker set for. The identifier should be tuned to minimize false "confident dialect" calls, even at the cost of more frequent Hindi fallback.

**Business context selection:** don't auto-detect which business context applies from the transcript — that's a separate, much harder and riskier inference. Pass it as a parameter from whatever system is placing the call (the EMI collections bot knows it's doing EMI collections; a telecom IVR knows it's telecom support). Maintain a small registry:

```python
BUSINESS_CONTEXTS = {
    "emi_collections": {"task_template": "...", "domain_vocab_hint": "..."},
    "telecom_support": {"task_template": "...", "domain_vocab_hint": "..."},
    "health_scheme_helpline": {"task_template": "...", "domain_vocab_hint": "..."},  # per SRUTI paper's domains
}
```

## (b) Enhancement + verification loop

```python
def enhance_with_dialect_flavor(reply_text: str, dialect: str, marker_sets: dict,
                                 max_retries: int = 1) -> dict:
    if dialect == "hindi":
        return {"text": reply_text, "flavored": False, "reason": "no_dialect_detected"}

    markers = marker_sets[dialect]
    fewshot_examples = build_fewshot_from_markers(markers, n=2)  # pick 2 high-frequency markers, construct example pairs
    prompt = fewshot_examples + f'\n\nWrite your REPLY in this same speaking style.\n\nStandard: "{reply_text}"\nStyled:'

    for attempt in range(max_retries + 1):
        candidate = call_evon(prompt)
        check = identify_dialect(candidate, {dialect: markers}, weights={m: 1.0 for m in markers},
                                   threshold=0.34)  # lower bar — just checking SOME flavor took
        if check["dialect"] == dialect:
            # also re-run script-sanity check: reject if output contains non-Devanagari,
            # non-ASCII-punctuation characters (catches Bengali/Roman corruption)
            if is_clean_devanagari(candidate):
                return {"text": candidate, "flavored": True, "attempt": attempt}
        # else retry, or fall through to deterministic fallback

    # Guaranteed-safe fallback: deterministic substitution using the corpus
    # markers as find-replace targets against known Hindi equivalents.
    # (Needs a marker -> Hindi-equivalent mapping, which we don't have yet for
    # the corpus-derived set — only for the original 20 hand-picked ones. This
    # is real work still to do: for each corpus marker, map it back to its
    # standard-Hindi equivalent, e.g. रहल -> रहा, गइल -> गया.)
    substituted = apply_deterministic_substitution(reply_text, dialect)
    return {"text": substituted, "flavored": substituted != reply_text, "reason": "fallback_substitution"}

def is_clean_devanagari(text: str) -> bool:
    import re
    # Allow Devanagari block + common punctuation/whitespace/digits only
    return not re.search(r"[^ऀ-ॿ\s.,!?।॥0-9A-Za-z\"'()-]", text) or \
           not re.search(r"[ঀ-৿]", text)  # specifically reject Bengali block
```

The key piece missing today: a **Hindi-equivalent mapping** for each corpus-derived marker, so the deterministic fallback in (b) actually has something to substitute. Right now we only have that mapping for the original 20 hand-picked markers. Building it for the 93 corpus-derived ones (ideally by asking a human Bhojpuri speaker, or very carefully cross-checking each word's standard-Hindi gloss) is real, necessary follow-up work before this fallback is trustworthy.

## (c) Timbre call

No architecture change needed here — same call as today (`language: "auto"`, closest voice). The only new logic is the **pre-flight safety gate**: run `is_clean_devanagari()` on whatever text is about to be sent to Timbre, regardless of whether it came from the enhancement path or the plain fallback. If it fails, send the *original unflavored* Evon REPLY instead — never send a known-corrupted string to a live customer call. This trades "sounds authentically dialectal" for "is guaranteed intelligible," which is the right tradeoff until the enhancement path has a much larger validated sample size than the current single 9-trial round.
