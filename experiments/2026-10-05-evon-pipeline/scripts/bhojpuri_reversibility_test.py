"""Bhojpuri Prisma-transcription reversibility test.

One question only: can recurring Bhojpuri Prisma errors be safely reversed
with simple token-level correction rules (Prisma said Y -> correct to X)?

Reuses the exact clean()/tokenize()/align() logic from analyze_prisma_fingerprint.py
(no redesign of alignment). No Evon, no LLM, no classifier, no other dialects,
no context-aware rules -- a plain frequency/precision table + threshold sweep.

Key metric: REVERSE PRECISION P(Human=X | Prisma=Y) -- when Prisma outputs Y,
how often was the real word actually X? This is what determines whether a
"Y -> X" correction rule is safe to apply, not forward consistency P(Y|X)
alone (a Y could be highly consistent as an OUTPUT of X and still be an
unsafe correction target if Y commonly means other things too).
"""

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_prisma_fingerprint import clean, tokenize, load_dialect, align  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint" / "regional_fingerprint_audit"
SEED = 42


def per_clip_token_accounting(h_tokens, p_tokens):
    """Returns: (sub_counts: Counter[(X,Y)] for 1:1 replace ops,
                 y_occurrence_source: list of (Y_token, source) for every Prisma
                 token occurrence, where source is 'EQUAL' (Y unchanged from
                 human Y), a specific human word X (1:1 substitution X->Y),
                 'OTHER_MULTIWORD' (came out of a multi-word replace block,
                 true source ambiguous at token level), or 'INSERTED' (no
                 human-side token at all))."""
    sub_counts = Counter()
    y_sources = []  # (Y, source)

    if h_tokens == p_tokens:
        for y in p_tokens:
            y_sources.append((y, "EQUAL"))
        return sub_counts, y_sources

    ops = align(h_tokens, p_tokens)
    for tag, h_span, p_span in ops:
        if tag == "equal":
            # align() only returns non-equal ops; equal spans are implicit
            # gaps -- handled below by reconstructing full coverage instead.
            continue
    # align() (per analyze_prisma_fingerprint.py) only returns NON-equal ops
    # and skips equal spans silently, so we can't reconstruct full token
    # coverage from its output alone. Recompute with raw SequenceMatcher
    # here to get full opcode coverage including equal spans.
    from difflib import SequenceMatcher
    sm = SequenceMatcher(None, h_tokens, p_tokens, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        h_span = tuple(h_tokens[i1:i2])
        p_span = tuple(p_tokens[j1:j2])
        if tag == "equal":
            for y in p_span:
                y_sources.append((y, "EQUAL"))
        elif tag == "replace" and len(h_span) == 1 and len(p_span) == 1:
            x, y = h_span[0], p_span[0]
            if x != y:
                sub_counts[(x, y)] += 1
                y_sources.append((y, x))
            else:
                y_sources.append((y, "EQUAL"))
        elif tag == "replace":
            for y in p_span:
                y_sources.append((y, "OTHER_MULTIWORD"))
        elif tag == "insert":
            for y in p_span:
                y_sources.append((y, "INSERTED"))
        elif tag == "delete":
            pass  # no prisma-side token produced
    return sub_counts, y_sources


def main():
    rows = load_dialect("Bhojpuri")
    print(f"Loaded {len(rows)} Bhojpuri clips with both transcripts")

    random.seed(SEED)
    indices = list(range(len(rows)))
    random.shuffle(indices)
    n_train = int(len(indices) * 0.8)
    train_idx, test_idx = indices[:n_train], indices[n_train:]
    print(f"Train: {len(train_idx)} clips, Test: {len(test_idx)} clips (seed={SEED})")

    # ---- TRAIN: discover candidate rules ----
    train_sub_counts = Counter()  # (X,Y) -> count
    train_x_total = Counter()  # X -> total occurrences of X in human transcripts (train)
    train_y_total = Counter()  # Y -> total occurrences of Y in prisma transcripts (train)

    for i in train_idx:
        r = rows[i]
        h_tokens = tokenize(r["human_transcript"])
        p_tokens = tokenize(r["prisma_transcript"])
        if not h_tokens or not p_tokens:
            continue
        for x in h_tokens:
            train_x_total[x] += 1
        subs, y_sources = per_clip_token_accounting(h_tokens, p_tokens)
        for (x, y), c in subs.items():
            train_sub_counts[(x, y)] += c
        for y, src in y_sources:
            train_y_total[y] += 1

    print(f"Distinct (X,Y) substitution pairs in train: {len(train_sub_counts)}")

    candidate_rules = []
    for (x, y), support in train_sub_counts.items():
        fwd = support / train_x_total[x] if train_x_total[x] else 0.0
        rev = support / train_y_total[y] if train_y_total[y] else 0.0
        candidate_rules.append({"x": x, "y": y, "support": support,
                                 "forward_consistency": round(fwd, 4), "reverse_precision": round(rev, 4)})
    candidate_rules.sort(key=lambda r: -r["support"])

    with open(OUT_DIR / "bhojpuri_reversibility_candidates.json", "w") as f:
        json.dump(candidate_rules, f, ensure_ascii=False, indent=2)

    # ---- TEST: build full ground-truth per-Prisma-token accounting ----
    test_clip_data = []  # list of (p_tokens, y_sources) per clip
    for i in test_idx:
        r = rows[i]
        h_tokens = tokenize(r["human_transcript"])
        p_tokens = tokenize(r["prisma_transcript"])
        if not h_tokens or not p_tokens:
            continue
        _, y_sources = per_clip_token_accounting(h_tokens, p_tokens)
        test_clip_data.append(y_sources)

    print(f"Test clips with usable token accounting: {len(test_clip_data)}")

    # ---- threshold sweep ----
    results = []
    for min_support in [10, 25, 50]:
        for min_precision in [0.90, 0.95, 0.98]:
            rules = {r["y"]: r["x"] for r in candidate_rules
                     if r["support"] >= min_support and r["reverse_precision"] >= min_precision}
            n_rules = len(rules)

            tokens_changed = 0
            incorrect_fixed = 0
            correct_damaged = 0
            clips_improved = 0
            clips_worsened = 0
            clips_unchanged = 0

            for y_sources in test_clip_data:
                clip_fixed = 0
                clip_damaged = 0
                for y, source in y_sources:
                    if y not in rules:
                        continue
                    x = rules[y]
                    tokens_changed += 1
                    # ground truth: was prisma's token Y actually correct here?
                    was_correct = (source == "EQUAL")  # prisma's Y matched human's Y
                    # after applying rule, token becomes X. Is X now correct?
                    now_correct = (source == x)  # the true human word at this position was X
                    if not was_correct and now_correct:
                        incorrect_fixed += 1
                        clip_fixed += 1
                    elif was_correct and not now_correct:
                        correct_damaged += 1
                        clip_damaged += 1
                    # else: was wrong and still wrong (different error), or was
                    # correct and still correct (shouldn't happen since y!=x) --
                    # no net change to count either way
                net = clip_fixed - clip_damaged
                if net > 0:
                    clips_improved += 1
                elif net < 0:
                    clips_worsened += 1
                else:
                    clips_unchanged += 1

            n_test_clips = len(test_clip_data)
            results.append({
                "min_support": min_support, "min_precision": min_precision,
                "n_rules": n_rules, "tokens_changed": tokens_changed,
                "incorrect_fixed": incorrect_fixed, "correct_damaged": correct_damaged,
                "net_reduction": incorrect_fixed - correct_damaged,
                "pct_clips_improved": round(100 * clips_improved / n_test_clips, 2) if n_test_clips else 0,
                "pct_clips_worsened": round(100 * clips_worsened / n_test_clips, 2) if n_test_clips else 0,
            })
            print(f"support>={min_support:3} prec>={min_precision:.2f}: rules={n_rules:3} "
                  f"changed={tokens_changed:5} fixed={incorrect_fixed:4} damaged={correct_damaged:4} "
                  f"net={incorrect_fixed - correct_damaged:4} "
                  f"clips_improved={results[-1]['pct_clips_improved']}% clips_worsened={results[-1]['pct_clips_worsened']}%")

    with open(OUT_DIR / "bhojpuri_reversibility_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # representative safe / unsafe examples for the report
    safe_examples = [r for r in candidate_rules if r["support"] >= 25 and r["reverse_precision"] >= 0.95]
    safe_examples.sort(key=lambda r: -r["support"])
    tempting_unsafe = [r for r in candidate_rules if r["support"] >= 25 and r["forward_consistency"] >= 0.5 and r["reverse_precision"] < 0.7]
    tempting_unsafe.sort(key=lambda r: -r["support"])

    print("\n=== Representative SAFE rules (support>=25, reverse_precision>=0.95) ===")
    for r in safe_examples[:10]:
        print(f"  {r['x']!r} -> {r['y']!r}  support={r['support']} fwd={r['forward_consistency']} rev_prec={r['reverse_precision']}")

    print("\n=== Representative TEMPTING BUT UNSAFE (high forward consistency, low reverse precision) ===")
    for r in tempting_unsafe[:10]:
        print(f"  {r['x']!r} -> {r['y']!r}  support={r['support']} fwd={r['forward_consistency']} rev_prec={r['reverse_precision']}")

    with open(OUT_DIR / "bhojpuri_reversibility_examples.json", "w") as f:
        json.dump({"safe": safe_examples[:15], "tempting_unsafe": tempting_unsafe[:15]}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
