"""Re-parse the raw Evon output from test_language_detection_response.py,
fixing the first-occurrence parsing bug (grabs the model's FINAL committed
answer, after any self-correcting reasoning, not the first mention of the
tag) and measuring how often Evon leaked raw reasoning into the output
despite the structured-format instruction (a format-compliance rate).

Does not call Evon again -- works entirely from the saved raw text.
"""

import json
import re
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
IN_PATH = DATA_DIR / "language_detection_response_results.json"
OUT_PATH = DATA_DIR / "language_detection_response_results_reparsed.json"

DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
LATIN_RE = re.compile(r"[A-Za-z]")


def classify_script(text):
    if not text:
        return "empty"
    has_dev = bool(DEVANAGARI_RE.search(text))
    has_lat = bool(LATIN_RE.search(text))
    if has_dev and not has_lat:
        return "devanagari"
    if has_lat and not has_dev:
        return "latin"
    if has_dev and has_lat:
        return "mixed"
    return "other"


def reparse(raw):
    """Take the LAST occurrence of each tag (the model's final committed
    answer), and detect whether the captured span looks clean (short,
    single-line) or still contains leaked reasoning (long / multi-sentence)."""
    detected, reply = None, None
    detected_clean, reply_clean = True, True

    if "LANGUAGE_DETECTED:" in raw:
        idx = raw.rfind("LANGUAGE_DETECTED:")
        after = raw[idx + len("LANGUAGE_DETECTED:"):]
        # cut at REPLY: if present after this point, else take rest
        if "REPLY:" in after:
            detected_raw = after.split("REPLY:")[0]
        else:
            detected_raw = after
        detected = detected_raw.strip().split("\n")[0].strip().rstrip(".,")
        # clean = short (<=4 words), no reasoning-filler phrases
        word_count = len(detected.split())
        if word_count > 4 or any(w in detected.lower() for w in ["but", "maybe", "i think", "so", "wait"]):
            detected_clean = False

    if "REPLY:" in raw:
        idx = raw.rfind("REPLY:")
        after = raw[idx + len("REPLY:"):]
        reply = after.strip().split("\n")[0].strip()
        word_count = len(reply.split())
        if word_count > 15 or any(w in reply.lower() for w in ["but ", "-> ", "wait,", "i think", "let's", "let us"]):
            reply_clean = False

    return {
        "detected": detected,
        "detected_clean_format": detected_clean,
        "reply": reply,
        "reply_clean_format": reply_clean,
    }


def main():
    results = json.loads(IN_PATH.read_text())
    reparsed = []
    for r in results:
        fixed = reparse(r["raw"])
        rec = dict(r)
        rec["detected"] = fixed["detected"]
        rec["reply"] = fixed["reply"]
        rec["detected_clean_format"] = fixed["detected_clean_format"]
        rec["reply_clean_format"] = fixed["reply_clean_format"]
        rec["reply_script"] = classify_script(fixed["reply"])
        reparsed.append(rec)

    OUT_PATH.write_text(json.dumps(reparsed, ensure_ascii=False, indent=2))

    # --- summary stats ---
    total = len(reparsed)
    detected_clean_n = sum(1 for r in reparsed if r["detected_clean_format"])
    reply_clean_n = sum(1 for r in reparsed if r["reply_clean_format"])
    script_counts = Counter(r["reply_script"] for r in reparsed)

    print(f"Total test cases: {total}")
    print(f"Format-compliant LANGUAGE_DETECTED (short, no leaked reasoning): {detected_clean_n}/{total} ({detected_clean_n/total:.0%})")
    print(f"Format-compliant REPLY (short, no leaked reasoning): {reply_clean_n}/{total} ({reply_clean_n/total:.0%})")
    print(f"Reply script distribution: {dict(script_counts)}")
    print()

    # detection accuracy: broad match (said the true dialect OR said "Hindi" for
    # a closely-related Hindi-family dialect -- scored as "plausible", not "exact")
    exact_match = 0
    hindi_fallback = 0
    wrong_family = 0
    by_dialect = {}
    for r in reparsed:
        gt = r["ground_truth"]
        det = (r["detected"] or "").strip().lower()
        gt_l = gt.lower()
        is_exact = gt_l in det
        is_hindi_fallback = (not is_exact) and "hindi" in det and gt not in ("Hindi", "English")
        is_wrong = not is_exact and not is_hindi_fallback and not (gt_l in det)
        if is_exact:
            exact_match += 1
        elif is_hindi_fallback:
            hindi_fallback += 1
        else:
            wrong_family += 1
        by_dialect.setdefault(gt, {"exact": 0, "hindi_fallback": 0, "wrong": 0, "n": 0})
        by_dialect[gt]["n"] += 1
        if is_exact:
            by_dialect[gt]["exact"] += 1
        elif is_hindi_fallback:
            by_dialect[gt]["hindi_fallback"] += 1
        else:
            by_dialect[gt]["wrong"] += 1

    print(f"Exact dialect/language name match: {exact_match}/{total} ({exact_match/total:.0%})")
    print(f"Fell back to generic 'Hindi' (for a non-Hindi/English dialect): {hindi_fallback}/{total} ({hindi_fallback/total:.0%})")
    print(f"Wrong / unrelated language guessed: {wrong_family}/{total} ({wrong_family/total:.0%})")
    print()
    print("Per-dialect breakdown (exact / hindi-fallback / wrong, out of n):")
    for dialect, counts in by_dialect.items():
        print(f"  {dialect:15} exact={counts['exact']} hindi_fallback={counts['hindi_fallback']} wrong={counts['wrong']}  (n={counts['n']})")


if __name__ == "__main__":
    main()
