"""Grounding numbers for docs/2026-10-05-evon-pipeline/16-opus-technical-logic-and-pecking-order.md.

Four text-only questions, all on the existing ~25k human/Prisma pairs, reusing tokenize()/load_dialect() from
analyze_prisma_fingerprint.py and the WRONG + functional-group logic from phonetic_filter_classification.py /
consequential_flag.py (no new alignment, no new definitions):

1. Edit mix: how much of the edit mass is 1:1 substitution at all (the only kind the 19% figure covers)?
2. Locatability: from Prisma's word alone, can we tell which output tokens are consequential errors?
3. Candidate ceiling: for a consequential error Y, is the true word among Y's top-k historical sources
   (the best case for any noisy-channel / constrained-reranking corrector)? Pooled and per oracle dialect.
4. Two spot checks: what Prisma does with एगो / ओ, and whether explicit negation words survive.

Split: clip-level 80/20, seed 42, all dialects pooled. Runs in a few seconds.
Usage: python opus_grounding_checks.py
"""
import ast
import random
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze_prisma_fingerprint import tokenize, load_dialect, DIALECTS  # noqa: E402
from phonetic_filter_classification import classify_pair  # noqa: E402

# consequential_flag.py runs its analysis at import time, so lift its GROUPS literal instead of importing it
_ns = {}
for _node in ast.parse((HERE / "consequential_flag.py").read_text()).body:
    if isinstance(_node, ast.Assign) and getattr(_node.targets[0], "id", None) == "GROUPS":
        exec(compile(ast.Module([_node], []), "consequential_flag.py", "exec"), _ns)
GROUPS = _ns["GROUPS"]


def group_of(w):
    return next((i for i, g in enumerate(GROUPS) if w in g), None)


def consequential(x, y):
    if x == y or classify_pair(x, y)[0] != "WRONG":
        return False
    gx = group_of(x)
    return not (gx is not None and gx == group_of(y))


def events(row):
    """Prisma tokens, {prisma index: true human word} for consequential 1:1 errors, and token-weighted edit mix."""
    h, p = tokenize(row["human_transcript"]), tokenize(row["prisma_transcript"])
    bad, ops = {}, Counter()
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, h, p, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        one_to_one = tag == "replace" and i2 - i1 == 1 and j2 - j1 == 1
        ops["replace 1:1" if one_to_one else tag] += max(i2 - i1, j2 - j1)
        if one_to_one and consequential(h[i1], p[j1]):
            bad[j1] = h[i1]
    return p, bad, ops


def main():
    rows = [r for d in DIALECTS for r in load_dialect(d)]
    random.Random(42).shuffle(rows)
    cut = int(len(rows) * 0.8)
    train, test = rows[:cut], rows[cut:]

    seen, wrong_as, sources, dialect_sources, mix = Counter(), Counter(), defaultdict(Counter), defaultdict(Counter), Counter()
    for r in train:
        p, bad, ops = events(r)
        mix += ops
        seen.update(p)
        for j, x in bad.items():
            wrong_as[p[j]] += 1
            sources[p[j]][x] += 1
            dialect_sources[(r["dialect"], p[j])][x] += 1
    print("1. edit mix (train, token-weighted):", {k: f"{v / sum(mix.values()):.1%}" for k, v in mix.most_common()})

    scored, n_tok, errors = [], 0, []
    for r in test:
        p, bad, _ = events(r)
        n_tok += len(p)
        scored += [(wrong_as[y] / seen[y] if seen[y] else None, j in bad) for j, y in enumerate(p)]
        errors += [(r["dialect"], p[j], x) for j, x in bad.items()]
    print(f"2. test Prisma tokens {n_tok}, consequential 1:1 errors {len(errors)} ({len(errors) / n_tok:.2%})")
    for th in (0.05, 0.1, 0.2, 0.5):
        flagged = [b for s, b in scored if s is not None and s >= th]
        print(f"   flag if train P(error | Prisma word) >= {th}: flags {len(flagged) / n_tok:.1%} of tokens, "
              f"precision {sum(flagged) / max(1, len(flagged)):.1%}, recall {sum(flagged) / len(errors):.1%}")

    for name, table, key in (("pooled", sources, lambda d, y: y), ("oracle dialect", dialect_sources, lambda d, y: (d, y))):
        hits, unseen = Counter(), 0
        for d, y, x in errors:
            ranked = [w for w, _ in table[key(d, y)].most_common()]
            unseen += not ranked
            for k in (1, 3, 10):
                hits[k] += x in ranked[:k]
        print(f"3. [{name}] Prisma word never seen as an error in train: {unseen / len(errors):.1%}; true word in top-1 "
              f"{hits[1] / len(errors):.1%}, top-3 {hits[3] / len(errors):.1%}, top-10 {hits[10] / len(errors):.1%}")

    fate = {"एगो": Counter(), "ओ": Counter()}
    neg = {"नहीं", "नही", "नइखे", "नईखे", "मत", "नाहीं"}  # unambiguous negators only: ना/न are often tag particles
    neg_fate, prisma_counts, came_from = Counter(), Counter(), Counter()
    for r in (r for d in DIALECTS for r in load_dialect(d)):
        h, p = tokenize(r["human_transcript"]), tokenize(r["prisma_transcript"])
        prisma_counts.update(p)
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, h, p, autojunk=False).get_opcodes():
            span = p[j1:j2]
            for i in range(i1, i2):
                w = h[i]
                if w in fate:
                    out = "unchanged" if tag == "equal" else span[0] if tag == "replace" and i2 - i1 == j2 - j1 == 1 else tag + " (span)"
                    fate[w][out] += 1
                    if out == "वो":
                        came_from[w] += 1
                if w in neg:
                    neg_fate["unchanged" if tag == "equal" else "deleted" if tag == "delete"
                             else "replaced, negation kept" if any(t in neg for t in span) else "replaced, negation lost"] += 1
    for w, c in fate.items():
        print(f"4a. human {w} ({sum(c.values())}x): {c.most_common(5)}")
    print(f"4a. Prisma वो appears {prisma_counts['वो']}x; from एगो {came_from['एगो']}, from ओ {came_from['ओ']}")
    n = sum(neg_fate.values())
    print(f"4b. explicit negation words ({n}x):", {k: f"{v / n:.1%}" for k, v in neg_fate.most_common()})


if __name__ == "__main__":
    main()
