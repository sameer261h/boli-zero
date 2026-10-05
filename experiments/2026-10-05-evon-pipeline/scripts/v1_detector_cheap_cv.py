"""Cheap replacement for the killed full-LOGO run: ~15 repeated GroupShuffleSplit
seeds instead of all 193 exhaustive leave-one-group-out folds. Captures most of
the same statistical value (stability estimate + row-weighted vs group-balanced
recall per dialect) at a fraction of the compute cost -- a deliberate, explicit
engineering-ROI tradeoff, not a methodology downgrade nobody decided on.

Also pools in whatever real LOGO predictions were checkpointed before the kill
(logo_predictions.jsonl) as bonus, free signal -- not discarded.
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regional_fingerprint_audit import DIALECTS, FAMILIES, load_rows, make_split  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint" / "regional_fingerprint_audit"
SEEDS = list(range(1, 16))  # 15 seeds


def run_seed(rows, texts, labels, groups_arr, seed):
    train_idx, val_idx, test_idx, fallback = make_split(rows, seed=seed)
    word_vec = TfidfVectorizer(analyzer="word", token_pattern=r"[ऀ-ॿ]+", ngram_range=(1, 2), min_df=2)
    char_vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 4), min_df=2, max_features=30000)
    train_texts = [texts[i] for i in train_idx]
    word_vec.fit(train_texts)
    char_vec.fit(train_texts)
    X_train = hstack([word_vec.transform(train_texts), char_vec.transform(train_texts)]).tocsr()
    test_texts = [texts[i] for i in test_idx]
    X_test = hstack([word_vec.transform(test_texts), char_vec.transform(test_texts)]).tocsr()

    clf = LogisticRegression(max_iter=400, class_weight="balanced", C=1.0)
    clf.fit(X_train, [labels[i] for i in train_idx])
    pred = clf.predict(X_test)

    out = []
    for i, p in zip(test_idx, pred):
        out.append({"dialect": labels[i], "group": groups_arr[i], "top1": p, "true": labels[i]})
    return out


def main():
    print("Loading rows...")
    rows = load_rows()
    texts = [r["text"] for r in rows]
    labels = [r["dialect"] for r in rows]
    groups_arr = [r["group"] for r in rows]

    all_predictions = []

    # fold in whatever real LOGO predictions survived the kill, as bonus signal
    logo_ckpt = OUT_DIR / "logo_predictions.jsonl"
    if logo_ckpt.exists():
        with open(logo_ckpt) as f:
            for line in f:
                rec = json.loads(line)
                all_predictions.append({"dialect": rec["dialect"], "group": rec["group"],
                                         "top1": rec["top1"], "true": rec["true"], "source": "logo_partial"})
        print(f"Folded in {len(all_predictions)} surviving predictions from the killed full-LOGO run")

    t0 = time.time()
    for seed in SEEDS:
        print(f"=== seed {seed} ({SEEDS.index(seed)+1}/{len(SEEDS)}) ===")
        preds = run_seed(rows, texts, labels, groups_arr, seed)
        for p in preds:
            p["source"] = f"seed_{seed}"
        all_predictions.extend(preds)
        elapsed = time.time() - t0
        done = SEEDS.index(seed) + 1
        print(f"  {elapsed:.0f}s elapsed, est. total {elapsed/done*len(SEEDS):.0f}s")

    print(f"\nTotal predictions pooled (partial-LOGO + {len(SEEDS)} seeds): {len(all_predictions)}")

    # --- row-weighted vs group-balanced recall per dialect ---
    summary = {}
    for d in DIALECTS:
        d_preds = [p for p in all_predictions if p["true"] == d]
        n = len(d_preds)
        if n == 0:
            summary[d] = {"n": 0}
            continue
        row_weighted = float(np.mean([p["top1"] == d for p in d_preds]))
        by_group = defaultdict(list)
        for p in d_preds:
            by_group[p["group"]].append(p["top1"] == d)
        group_accs = [float(np.mean(v)) for v in by_group.values()]
        group_balanced = float(np.mean(group_accs))
        fam_hit = float(np.mean([FAMILIES.get(p["top1"], p["top1"]) == FAMILIES.get(d, d) for p in d_preds]))
        summary[d] = {
            "n_pooled_predictions": n, "n_distinct_groups_seen": len(by_group),
            "row_weighted_recall": round(row_weighted, 3),
            "group_balanced_recall": round(group_balanced, 3),
            "gap": round(abs(row_weighted - group_balanced), 3),
            "family_recall": round(fam_hit, 3),
        }

    print(f"\n{'Dialect':15} {'n_pred':7} {'n_groups':9} {'row_weighted':13} {'group_balanced':15} {'gap':6} {'family':7}")
    for d in DIALECTS:
        s = summary[d]
        if s.get("n", -1) == 0:
            print(f"{d:15} no data")
            continue
        print(f"{d:15} {s['n_pooled_predictions']:<7} {s['n_distinct_groups_seen']:<9} "
              f"{s['row_weighted_recall']:<13} {s['group_balanced_recall']:<15} {s['gap']:<6} {s['family_recall']:<7}")

    with open(OUT_DIR / "cheap_cv_summary.json", "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {OUT_DIR / 'cheap_cv_summary.json'}")


if __name__ == "__main__":
    main()
