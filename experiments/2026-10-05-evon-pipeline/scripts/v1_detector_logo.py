"""True leave-one-group-out (LOGO) cross-validation for the regional detector.

Replaces the 5-seed GroupShuffleSplit stability check with something more
rigorous, per explicit correction: every (dialect, group) pair is held out
exactly once as test, trained on everything else (all other dialects' full
data + this dialect's other groups), every row gets exactly one genuinely
group-disjoint out-of-fold prediction. No row-level fallback needed -- LOGO
works even for dialects with only 2 groups (Surgujia, Surjapuri), which is
why it replaces the earlier approach rather than supplementing it.

The TF-IDF vectorizer is fit once on the full corpus (vocabulary only, not
label information -- a disclosed, minor simplification to keep 193 LR
refits tractable; each LogisticRegression is still trained fresh per fold
on genuinely held-out labels). Folds run in parallel (ProcessPoolExecutor,
fork-based, Linux default) since each is independent.

Reports BOTH row-weighted and group-balanced recall per dialect (a single
large group, e.g. Khortha's 542-row Jamtara-Male, should not single-handedly
decide whether a dialect "generalizes" -- point 3 of the correction).

No Evon/Prisma calls.
"""

import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regional_fingerprint_audit import DIALECTS, FAMILIES, load_rows  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint" / "regional_fingerprint_audit"

# module-level globals set once in the parent process; inherited by forked
# workers via copy-on-write, avoiding re-pickling the large sparse matrix
# for every one of the 193 tasks.
_X = None
_y = None
_groups = None
_classes = None


def _init_globals(X, y, groups):
    global _X, _y, _groups, _classes
    _X, _y, _groups = X, y, groups
    _classes = sorted(set(y))


def run_fold(args):
    dialect, group, test_idx, train_idx = args
    clf = LogisticRegression(max_iter=400, class_weight="balanced", C=1.0, solver="lbfgs")
    clf.fit(_X[train_idx], _y[train_idx])
    proba = clf.predict_proba(_X[test_idx])
    classes = clf.classes_.tolist()
    sorted_idx = np.argsort(-proba, axis=1)
    out = []
    for row_i, ti in enumerate(test_idx):
        order = sorted_idx[row_i]
        top1 = classes[order[0]]
        top2 = classes[order[1]] if len(order) > 1 else None
        top1_conf = float(proba[row_i, order[0]])
        top2_conf = float(proba[row_i, order[1]]) if top2 else 0.0
        out.append({
            "dialect": dialect, "group": group, "row_i": int(ti),
            "true": _y[ti], "top1": top1, "top1_conf": round(top1_conf, 4),
            "top2": top2, "top2_conf": round(top2_conf, 4), "margin": round(top1_conf - top2_conf, 4),
        })
    return out


def main():
    print("Loading rows + vectorizing (once, full corpus vocabulary)...")
    rows = load_rows()
    texts = [r["text"] for r in rows]
    labels = np.array([r["dialect"] for r in rows])
    groups_arr = np.array([r["group"] for r in rows])
    n = len(rows)

    t0 = time.time()
    word_vec = TfidfVectorizer(analyzer="word", token_pattern=r"[ऀ-ॿ]+", ngram_range=(1, 2), min_df=2)
    char_vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 4), min_df=2, max_features=30000)
    Xw = word_vec.fit_transform(texts)
    Xc = char_vec.fit_transform(texts)
    X = hstack([Xw, Xc]).tocsr()
    print(f"  vectorized: {X.shape}, {time.time()-t0:.1f}s")

    # build the 193 (dialect, group) holdout tasks
    by_dialect_group = defaultdict(list)
    for i, (d, g) in enumerate(zip(labels, groups_arr)):
        by_dialect_group[(d, g)].append(i)

    tasks = []
    all_idx = np.arange(n)
    for (d, g), idxs in by_dialect_group.items():
        test_idx = np.array(idxs)
        test_set = set(idxs)
        train_idx = np.array([i for i in all_idx if i not in test_set])
        tasks.append((d, g, test_idx, train_idx))

    print(f"Total (dialect, group) LOGO folds: {len(tasks)}")
    for d in DIALECTS:
        ng = sum(1 for (dd, gg) in by_dialect_group if dd == d)
        print(f"  {d}: {ng} groups -> {ng} folds")

    print("\nRunning folds in parallel (4 workers)...")
    t0 = time.time()
    all_predictions = []
    with ProcessPoolExecutor(max_workers=4, initializer=_init_globals, initargs=(X, labels, groups_arr)) as pool:
        futures = {pool.submit(run_fold, t): t for t in tasks}
        done = 0
        for fut in as_completed(futures):
            all_predictions.extend(fut.result())
            done += 1
            if done % 20 == 0:
                elapsed = time.time() - t0
                print(f"  {done}/{len(tasks)} folds done, {elapsed:.0f}s elapsed, "
                      f"est. total {elapsed/done*len(tasks):.0f}s")
    print(f"All folds done in {time.time()-t0:.0f}s. Total out-of-fold predictions: {len(all_predictions)}")

    with open(OUT_DIR / "logo_predictions.json", "w") as f:
        json.dump(all_predictions, f, ensure_ascii=False)
    print(f"Saved raw predictions to {OUT_DIR / 'logo_predictions.json'}")

    # --- summarize: row-weighted vs group-balanced recall per dialect ---
    print("\n=== Row-weighted vs group-balanced exact recall (TRUE LOGO, every group held out once) ===")
    summary = {}
    for d in DIALECTS:
        d_preds = [p for p in all_predictions if p["true"] == d]
        n_rows = len(d_preds)
        row_weighted = float(np.mean([p["top1"] == d for p in d_preds])) if d_preds else None

        by_group = defaultdict(list)
        for p in d_preds:
            by_group[p["group"]].append(p["top1"] == d)
        group_accs = [float(np.mean(v)) for v in by_group.values()]
        group_balanced = float(np.mean(group_accs)) if group_accs else None
        group_sizes = {g: len(v) for g, v in by_group.items()}
        largest_group_frac = max(group_sizes.values()) / n_rows if n_rows else 0

        top2_hit = float(np.mean([(p["top1"] == d) or (p["top2"] == d) for p in d_preds])) if d_preds else None
        fam_hit = float(np.mean([FAMILIES.get(p["top1"], p["top1"]) == FAMILIES.get(d, d) for p in d_preds])) if d_preds else None

        summary[d] = {
            "n_rows": n_rows, "n_groups": len(by_group),
            "row_weighted_recall": round(row_weighted, 3) if row_weighted is not None else None,
            "group_balanced_recall": round(group_balanced, 3) if group_balanced is not None else None,
            "gap": round(abs(row_weighted - group_balanced), 3) if (row_weighted is not None and group_balanced is not None) else None,
            "largest_group_frac_of_rows": round(largest_group_frac, 3),
            "top2_recall": round(top2_hit, 3) if top2_hit is not None else None,
            "family_recall": round(fam_hit, 3) if fam_hit is not None else None,
        }
        print(f"  {d:15} n={n_rows:5} groups={len(by_group):3}  row_weighted={summary[d]['row_weighted_recall']}  "
              f"group_balanced={summary[d]['group_balanced_recall']}  gap={summary[d]['gap']}  "
              f"largest_group_frac={summary[d]['largest_group_frac_of_rows']}  top2={summary[d]['top2_recall']}  fam={summary[d]['family_recall']}")

    with open(OUT_DIR / "logo_summary.json", "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nSaved summary to {OUT_DIR / 'logo_summary.json'}")

    # --- pooled out-of-fold threshold curves (every row contributes exactly once) ---
    print("\n=== Pooled out-of-fold threshold curves (Level 1 exact, Level 2 family) ===")
    confs = np.array([p["top1_conf"] for p in all_predictions])
    exact_correct = np.array([p["top1"] == p["true"] for p in all_predictions])
    fam_correct = np.array([FAMILIES.get(p["top1"], p["top1"]) == FAMILIES.get(p["true"], p["true"]) for p in all_predictions])

    thresholds = np.arange(0.05, 1.0, 0.05)
    curve = []
    for t in thresholds:
        mask = confs >= t
        if mask.sum() == 0:
            curve.append({"t": round(float(t), 2), "coverage": 0.0, "n": 0, "exact_fcr": None, "fam_fcr": None})
            continue
        coverage = mask.mean()
        exact_fcr = float(np.mean(~exact_correct[mask]))
        fam_fcr = float(np.mean(~fam_correct[mask]))
        curve.append({"t": round(float(t), 2), "coverage": round(float(coverage), 4), "n": int(mask.sum()),
                      "exact_fcr": round(exact_fcr, 4), "fam_fcr": round(fam_fcr, 4)})
    for c in curve:
        print(f"  t={c['t']:.2f} coverage={c['coverage']} n={c['n']:6} exact_false_confident_rate={c['exact_fcr']} fam_false_confident_rate={c['fam_fcr']}")

    recs = {"exact": {}, "family": {}}
    for target in [0.05, 0.10, 0.15]:
        exact_cands = [c for c in curve if c["exact_fcr"] is not None and c["exact_fcr"] <= target]
        fam_cands = [c for c in curve if c["fam_fcr"] is not None and c["fam_fcr"] <= target]
        recs["exact"][str(target)] = min(exact_cands, key=lambda c: c["t"]) if exact_cands else None
        recs["family"][str(target)] = min(fam_cands, key=lambda c: c["t"]) if fam_cands else None
    print("\nRecommended thresholds (pooled out-of-fold, exact):", json.dumps(recs["exact"], indent=2))
    print("Recommended thresholds (pooled out-of-fold, family):", json.dumps(recs["family"], indent=2))

    with open(OUT_DIR / "logo_threshold_curve.json", "w") as f:
        json.dump({"curve": curve, "recommendations": recs}, f, ensure_ascii=False, indent=2)
    print(f"\nSaved threshold curve to {OUT_DIR / 'logo_threshold_curve.json'}")


if __name__ == "__main__":
    main()
