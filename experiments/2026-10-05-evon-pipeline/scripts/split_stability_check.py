"""Multi-seed stability check: does per-dialect accuracy swing wildly across
reasonable, equally-valid group-split choices? If so, any single run's
per-dialect number (including v1_detector.py's) should not be trusted alone,
especially for dialects near the OK/WEAK group-count boundary (Magahi=9,
Angika=14, Khortha=8) where group-size skew can dump a huge, unrepresentative
fraction of one dialect's rows into test purely by chance.

Trains the 'combined' (word+char) classifier fresh for each of 5 seeds,
reports per-dialect exact recall range. No Evon calls.
"""

import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regional_fingerprint_audit import DIALECTS, load_rows, make_split  # noqa: E402

SEEDS = [1, 7, 42, 123, 2024]


def run_seed(rows, seed):
    train_idx, val_idx, test_idx, fallback = make_split(rows, seed=seed)
    train_texts = [rows[i]["text"] for i in train_idx]
    train_labels = [rows[i]["dialect"] for i in train_idx]
    test_texts = [rows[i]["text"] for i in test_idx]
    test_labels = np.array([rows[i]["dialect"] for i in test_idx])

    word_vec = TfidfVectorizer(analyzer="word", token_pattern=r"[ऀ-ॿ]+", ngram_range=(1, 2), min_df=2)
    char_vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 4), min_df=2, max_features=30000)
    word_vec.fit(train_texts)
    char_vec.fit(train_texts)
    X_train = hstack([word_vec.transform(train_texts), char_vec.transform(train_texts)]).tocsr()
    X_test = hstack([word_vec.transform(test_texts), char_vec.transform(test_texts)]).tocsr()

    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
    clf.fit(X_train, train_labels)
    pred = clf.predict(X_test)

    per_dialect = {}
    for d in DIALECTS:
        mask = test_labels == d
        n = int(mask.sum())
        acc = float(np.mean(pred[mask] == d)) if n else None
        per_dialect[d] = {"n_test": n, "exact_recall": round(acc, 3) if acc is not None else None}
    return per_dialect, fallback


def main():
    print("Loading rows...")
    rows = load_rows()
    print(f"Total rows: {len(rows)}\n")

    all_results = defaultdict(list)
    all_n = defaultdict(list)
    fallback_counts = defaultdict(int)

    for seed in SEEDS:
        print(f"=== seed={seed} ===")
        per_dialect, fallback = run_seed(rows, seed)
        for d in fallback:
            fallback_counts[d] += 1
        for d in DIALECTS:
            r = per_dialect[d]["exact_recall"]
            n = per_dialect[d]["n_test"]
            all_results[d].append(r)
            all_n[d].append(n)
            print(f"  {d:15} n_test={n:4} exact_recall={r}")

    print("\n=== STABILITY SUMMARY across 5 seeds ===")
    print(f"{'Dialect':15} {'n_test range':15} {'recall min':11} {'recall max':11} {'recall range':13} {'fallback count':14} verdict")
    unstable = []
    for d in DIALECTS:
        vals = [v for v in all_results[d] if v is not None]
        ns = all_n[d]
        if not vals:
            print(f"  {d:15} no valid runs")
            continue
        rmin, rmax = min(vals), max(vals)
        rrange = rmax - rmin
        verdict = "UNSTABLE" if rrange > 0.20 else ("borderline" if rrange > 0.10 else "stable")
        if verdict != "stable":
            unstable.append(d)
        print(f"  {d:15} {min(ns):4}-{max(ns):<9} {rmin:<11.3f} {rmax:<11.3f} {rrange:<13.3f} {fallback_counts[d]}/5{'':10} {verdict}")

    print(f"\nDialects with UNSTABLE or borderline per-dialect accuracy across reasonable split choices: {unstable}")
    print("These dialects' single-run numbers (from v1_detector.py or the earlier audit) should NOT be")
    print("treated as a fixed ground truth -- the split itself materially changes the apparent result.")

    import json
    out = {}
    for d in DIALECTS:
        vals = [v for v in all_results[d] if v is not None]
        ns = all_n[d]
        out[d] = {
            "seed_recalls": all_results[d], "seed_n_test": ns,
            "mean_recall": round(float(np.mean(vals)), 3) if vals else None,
            "median_recall": round(float(np.median(vals)), 3) if vals else None,
            "min_recall": round(min(vals), 3) if vals else None,
            "max_recall": round(max(vals), 3) if vals else None,
            "range": round(max(vals) - min(vals), 3) if vals else None,
            "fallback_count_of_5": fallback_counts[d],
            "verdict": ("UNSTABLE" if vals and (max(vals) - min(vals)) > 0.20 else ("borderline" if vals and (max(vals) - min(vals)) > 0.10 else "stable")),
        }
    with open(Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint" / "regional_fingerprint_audit" / "split_stability_results.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nSaved per-dialect seed stats to split_stability_results.json")


if __name__ == "__main__":
    main()
