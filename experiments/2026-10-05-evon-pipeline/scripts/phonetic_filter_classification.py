"""Classify every aligned human-token -> Prisma-token substitution (all 19
dialects) into IGNORE (phonetically/orthographically similar) vs WRONG vs
UNSURE, per an explicit, narrow task scope: no corrections, no Evon, no new
alignment, minimal added heuristics.

Reuses the exact clean()/tokenize()/align() already used for
06-prisma-fingerprint-dialect-transformation-analysis.md (no redesign).

Phonetic-similarity filter (the one mechanical rule used, applied uniformly,
not escalated per-word): two words are IGNORE if, after normalizing away
diacritics that are common ASR/spelling noise in Devanagari (nukta, and
collapsing the anusvara/chandrabindu nasalization distinction), they become
identical OR are within edit-distance 1. This directly catches the task's
own example (बहोत -> बहुत, a vowel-length spelling variant) and the kind of
cosmetic variation already catalogued in cross_dialect_universal_substitutions.json.

For the remaining (non-ignored) pairs, WRONG vs UNSURE is split by
normalized edit-distance ratio (edit_distance / max(len(x), len(y))): a
large ratio (most of the word changed) -> WRONG (Prisma clearly produced a
different word); a moderate ratio (partial, ambiguous overlap) -> UNSURE.
One consistent rule, not hand-tuned per example -- the "use sentence
context" requirement is handled separately, as a human spot-check of a
frequency-weighted sample of the output, not folded into the mechanical rule.
"""

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_prisma_fingerprint import clean, tokenize, load_dialect, align, DIALECTS  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint" / "regional_fingerprint_audit"

NUKTA = "़"
ANUSVARA = "ं"
CHANDRABINDU = "ँ"
VISARGA = "ः"
VIRAMA = "्"

# standard Hindi spelling convention: anusvara (ं) is a recognized shorthand
# for a homorganic nasal consonant + virama before another consonant --
# सुन्दर/सुंदर, मन्दिर/मंदिर, लम्बा/लंबा, खम्भा/खंभा are the same word, same
# pronunciation, just two accepted spellings. Collapsing नonly "fills in" the
# one requested phonetic-similarity filter correctly; it is not a second,
# separate heuristic.
NASAL_VIRAMA_RE = re.compile(r"[नमङणञ]" + VIRAMA)


def normalize_phonetic(w):
    w = unicodedata.normalize("NFC", w)
    w = w.replace(NUKTA, "")  # सफ़ेद -> सफेद
    w = w.replace(CHANDRABINDU, ANUSVARA)  # यहाँ -> यहां (collapse nasalization marks)
    w = NASAL_VIRAMA_RE.sub(ANUSVARA, w)  # सुन्दर -> सुंदर, मन्दिर -> मंदिर, etc.
    return w


def levenshtein(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * lb
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[lb]


def classify_pair(x, y):
    xn, yn = normalize_phonetic(x), normalize_phonetic(y)
    d_norm = levenshtein(xn, yn)
    if xn == yn or d_norm <= 1:
        return "IGNORE", d_norm
    d_raw = levenshtein(x, y)
    ratio = d_raw / max(len(x), len(y))
    if ratio >= 0.5:
        return "WRONG", d_raw
    return "UNSURE", d_raw


def main():
    print("Loading all 19 dialects and extracting 1:1 substitution instances...")
    instance_counts = Counter()  # (dialect, x, y) -> count
    example_sentences = defaultdict(list)  # (x,y) -> list of (dialect, human_sentence, prisma_sentence)

    for dialect in DIALECTS:
        rows = load_dialect(dialect)
        for r in rows:
            h_tokens = tokenize(r["human_transcript"])
            p_tokens = tokenize(r["prisma_transcript"])
            if not h_tokens or h_tokens == p_tokens:
                continue
            ops = align(h_tokens, p_tokens)
            for tag, h_span, p_span in ops:
                if tag == "replace" and len(h_span) == 1 and len(p_span) == 1:
                    x, y = h_span[0], p_span[0]
                    if x != y:
                        instance_counts[(dialect, x, y)] += 1
                        if len(example_sentences[(x, y)]) < 3:
                            example_sentences[(x, y)].append(
                                (dialect, r["human_transcript"][:120], r["prisma_transcript"][:120]))

    total_instances = sum(instance_counts.values())
    print(f"Total token differences: {total_instances}")

    # classify unique (x,y) pairs once (phonetic similarity doesn't depend on dialect)
    global_pair_counts = Counter()
    for (d, x, y), c in instance_counts.items():
        global_pair_counts[(x, y)] += c

    pair_classification = {}
    for (x, y) in global_pair_counts:
        label, dist = classify_pair(x, y)
        pair_classification[(x, y)] = label

    # aggregate totals
    label_instance_counts = Counter()
    for (x, y), count in global_pair_counts.items():
        label_instance_counts[pair_classification[(x, y)]] += count

    ignore_n = label_instance_counts["IGNORE"]
    wrong_n = label_instance_counts["WRONG"]
    unsure_n = label_instance_counts["UNSURE"]
    flagged_n = wrong_n + unsure_n

    print(f"\n=== OVERALL ===")
    print(f"Total token differences: {total_instances}")
    print(f"IGNORE: {ignore_n} ({ignore_n/total_instances:.1%})")
    print(f"Remaining flagged: {flagged_n} ({flagged_n/total_instances:.1%})")
    print(f"  WRONG: {wrong_n} ({wrong_n/flagged_n:.1%} of flagged, {wrong_n/total_instances:.1%} of total)")
    print(f"  UNSURE: {unsure_n} ({unsure_n/flagged_n:.1%} of flagged, {unsure_n/total_instances:.1%} of total)")

    # per-dialect breakdown
    print(f"\n=== BY DIALECT ===")
    dialect_breakdown = {}
    for dialect in DIALECTS:
        d_total = sum(c for (d, x, y), c in instance_counts.items() if d == dialect)
        d_ignore = sum(c for (d, x, y), c in instance_counts.items() if d == dialect and pair_classification[(x, y)] == "IGNORE")
        d_wrong = sum(c for (d, x, y), c in instance_counts.items() if d == dialect and pair_classification[(x, y)] == "WRONG")
        d_unsure = sum(c for (d, x, y), c in instance_counts.items() if d == dialect and pair_classification[(x, y)] == "UNSURE")
        d_flagged = d_wrong + d_unsure
        dialect_breakdown[dialect] = {
            "total": d_total, "ignore": d_ignore, "ignore_pct": round(100 * d_ignore / d_total, 1) if d_total else 0,
            "flagged": d_flagged,
            "wrong": d_wrong, "wrong_pct_of_flagged": round(100 * d_wrong / d_flagged, 1) if d_flagged else 0,
            "unsure": d_unsure, "unsure_pct_of_flagged": round(100 * d_unsure / d_flagged, 1) if d_flagged else 0,
        }
        print(f"  {dialect:15} total={d_total:5} ignore={d_ignore:5}({dialect_breakdown[dialect]['ignore_pct']}%) "
              f"flagged={d_flagged:5}  WRONG={d_wrong:5}({dialect_breakdown[dialect]['wrong_pct_of_flagged']}%) "
              f"UNSURE={d_unsure:5}({dialect_breakdown[dialect]['unsure_pct_of_flagged']}%)")

    # representative examples, weighted by frequency (most common flagged pairs first)
    wrong_pairs = sorted([(xy, c) for xy, c in global_pair_counts.items() if pair_classification[xy] == "WRONG"],
                          key=lambda kv: -kv[1])
    unsure_pairs = sorted([(xy, c) for xy, c in global_pair_counts.items() if pair_classification[xy] == "UNSURE"],
                           key=lambda kv: -kv[1])

    print(f"\n=== Top 15 WRONG examples (by frequency) ===")
    for (x, y), c in wrong_pairs[:15]:
        print(f"  {x!r} -> {y!r}  (x{c})")

    print(f"\n=== Top 15 UNSURE examples (by frequency) ===")
    for (x, y), c in unsure_pairs[:15]:
        print(f"  {x!r} -> {y!r}  (x{c})")

    out = {
        "total_instances": total_instances,
        "ignore": ignore_n, "ignore_pct": round(100 * ignore_n / total_instances, 1),
        "flagged": flagged_n,
        "wrong": wrong_n, "wrong_pct_of_flagged": round(100 * wrong_n / flagged_n, 1),
        "unsure": unsure_n, "unsure_pct_of_flagged": round(100 * unsure_n / flagged_n, 1),
        "by_dialect": dialect_breakdown,
        "top_wrong": [{"human": x, "prisma": y, "count": c} for (x, y), c in wrong_pairs[:30]],
        "top_unsure": [{"human": x, "prisma": y, "count": c} for (x, y), c in unsure_pairs[:30]],
    }
    with open(OUT_DIR / "phonetic_filter_classification.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # save example sentences for the top items, for the spot-check
    spot_check = {}
    for (x, y), c in (wrong_pairs[:10] + unsure_pairs[:10]):
        spot_check[f"{x}->{y}"] = {"count": c, "label": pair_classification[(x, y)],
                                     "examples": example_sentences.get((x, y), [])}
    with open(OUT_DIR / "phonetic_filter_spot_check_sentences.json", "w") as f:
        json.dump(spot_check, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {OUT_DIR / 'phonetic_filter_classification.json'}")
    print(f"Spot-check sentences saved to {OUT_DIR / 'phonetic_filter_spot_check_sentences.json'}")


if __name__ == "__main__":
    main()
