"""v1 Regional Speech Detector -- corrected feature model + real calibration.

Fixes the bug in regional_fingerprint_audit.py: its "combined" mode was
actually just char_wb(2,4) alone, not a real word+char union. This script
builds a genuine word-only, char-only, and combined (word TF-IDF + char
TF-IDF concatenated via hstack) classifier, picks the winning mode on VAL
(not test), calibrates on VAL (isotonic, via CalibratedClassifierCV with
cv="prefit"), and reports every metric on TEST only -- which was untouched
by both training and calibration.

No Evon calls. Pure sklearn on the already-collected Prisma transcripts.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import hstack
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, top_k_accuracy_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regional_fingerprint_audit import (  # noqa: E402
    DIALECTS, FAMILIES, DATA_DIR, load_rows, make_split, report_group_cardinality,
)

OUT_DIR = DATA_DIR / "regional_fingerprint_audit"
OUT_PATH = OUT_DIR / "v1_detector_results.json"


def build_vectorizers(mode):
    if mode == "word":
        return [("word", TfidfVectorizer(analyzer="word", token_pattern=r"[ऀ-ॿ]+", ngram_range=(1, 2), min_df=2))]
    if mode == "char":
        return [("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 4), min_df=2, max_features=30000))]
    if mode == "combined":
        return [
            ("word", TfidfVectorizer(analyzer="word", token_pattern=r"[ऀ-ॿ]+", ngram_range=(1, 2), min_df=2)),
            ("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 4), min_df=2, max_features=30000)),
        ]
    raise ValueError(mode)


class UnionVectorizer:
    """Fit multiple TfidfVectorizers, concatenate (hstack) their outputs."""

    def __init__(self, specs):
        self.specs = specs

    def fit(self, texts):
        for _, vec in self.specs:
            vec.fit(texts)
        return self

    def transform(self, texts):
        mats = [vec.transform(texts) for _, vec in self.specs]
        return mats[0] if len(mats) == 1 else hstack(mats).tocsr()

    def n_features(self):
        return sum(len(vec.vocabulary_) for _, vec in self.specs)


def fit_and_eval(rows, train_idx, val_idx, test_idx, mode):
    train_texts = [rows[i]["text"] for i in train_idx]
    train_labels = [rows[i]["dialect"] for i in train_idx]
    val_texts = [rows[i]["text"] for i in val_idx]
    val_labels = [rows[i]["dialect"] for i in val_idx]
    test_texts = [rows[i]["text"] for i in test_idx]
    test_labels = [rows[i]["dialect"] for i in test_idx]

    uv = UnionVectorizer(build_vectorizers(mode)).fit(train_texts)
    X_train = uv.transform(train_texts)
    X_val = uv.transform(val_texts)
    X_test = uv.transform(test_texts)

    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
    clf.fit(X_train, train_labels)

    classes = clf.classes_.tolist()

    def metrics_for(X, y, proba):
        pred_idx = proba.argmax(axis=1)
        pred = np.array(classes)[pred_idx]
        acc = float(np.mean(pred == np.array(y)))
        top2 = float(top_k_accuracy_score(y, proba, k=2, labels=classes))
        fam_pred = [FAMILIES.get(p, p) for p in pred]
        fam_true = [FAMILIES.get(t, t) for t in y]
        fam_acc = float(np.mean(np.array(fam_pred) == np.array(fam_true)))
        return pred, acc, top2, fam_acc

    val_proba_raw = clf.predict_proba(X_val)
    _, val_acc_raw, val_top2_raw, val_fam_raw = metrics_for(X_val, val_labels, val_proba_raw)

    test_proba_raw = clf.predict_proba(X_test)
    test_pred_raw, test_acc_raw, test_top2_raw, test_fam_raw = metrics_for(X_test, test_labels, test_proba_raw)

    return {
        "mode": mode,
        "n_features": uv.n_features(),
        "clf": clf,
        "uv": uv,
        "classes": classes,
        "val_acc_raw": round(val_acc_raw, 4),
        "val_top2_raw": round(val_top2_raw, 4),
        "val_fam_raw": round(val_fam_raw, 4),
        "test_acc_raw": round(test_acc_raw, 4),
        "test_top2_raw": round(test_top2_raw, 4),
        "test_fam_raw": round(test_fam_raw, 4),
        "test_proba_raw": test_proba_raw,
        "test_pred_raw": test_pred_raw,
        "X_val": X_val,
        "val_labels": val_labels,
        "X_test": X_test,
        "test_labels": test_labels,
    }


def ece(proba_max, correct, n_bins=10):
    bins = np.linspace(0, 1, n_bins + 1)
    bin_idx = np.digitize(proba_max, bins) - 1
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)
    total = 0.0
    report = []
    for b in range(n_bins):
        mask = bin_idx == b
        if mask.sum() == 0:
            continue
        conf = proba_max[mask].mean()
        acc = correct[mask].mean()
        total += (mask.sum() / len(proba_max)) * abs(conf - acc)
        report.append({"bin": f"{bins[b]:.1f}-{bins[b+1]:.1f}", "n": int(mask.sum()),
                        "mean_confidence": round(float(conf), 3), "empirical_accuracy": round(float(acc), 3)})
    return round(total, 4), report


def accuracy_by_length(rows, test_idx, test_labels, pred):
    lengths = np.array([rows[i]["n_words"] for i in test_idx])
    labels = np.array(test_labels)
    bins = [(1, 3), (4, 6), (7, 10), (11, 20), (21, 1000)]
    out = []
    for lo, hi in bins:
        mask = (lengths >= lo) & (lengths <= hi)
        if mask.sum() == 0:
            continue
        acc = np.mean(pred[mask] == labels[mask])
        out.append({"length_range": f"{lo}-{hi if hi < 1000 else '+'}", "n": int(mask.sum()), "accuracy": round(float(acc), 3)})
    return out


def main():
    print("Loading rows...")
    rows = load_rows()
    print(f"Total usable rows: {len(rows)}\n")
    report_group_cardinality(rows)
    train_idx, val_idx, test_idx, fallback_dialects = make_split(rows)

    print("\n=== STAGE 1: Feature mode comparison (selected on VAL, reported on TEST) ===")
    fits = {}
    for mode in ["word", "char", "combined"]:
        fits[mode] = fit_and_eval(rows, train_idx, val_idx, test_idx, mode)
        f = fits[mode]
        print(f"  mode={mode:9} n_features={f['n_features']:6}  VAL acc={f['val_acc_raw']}  "
              f"VAL top2={f['val_top2_raw']}  VAL fam={f['val_fam_raw']}  || "
              f"TEST acc={f['test_acc_raw']} TEST top2={f['test_top2_raw']} TEST fam={f['test_fam_raw']}")

    best_mode = max(fits, key=lambda m: fits[m]["val_acc_raw"])
    print(f"\nBest mode by VAL accuracy: {best_mode}")
    best = fits[best_mode]

    print("\n=== STAGE 2: Calibration (isotonic, fit on VAL, scored on TEST only) ===")
    calibrated = CalibratedClassifierCV(FrozenEstimator(best["clf"]), method="isotonic")
    calibrated.fit(best["X_val"], best["val_labels"])
    classes_cal = calibrated.classes_.tolist()

    test_proba_cal = calibrated.predict_proba(best["X_test"])
    test_pred_cal_idx = test_proba_cal.argmax(axis=1)
    test_pred_cal = np.array(classes_cal)[test_pred_cal_idx]
    test_labels_arr = np.array(best["test_labels"])

    raw_correct = (best["test_pred_raw"] == test_labels_arr)
    cal_correct = (test_pred_cal == test_labels_arr)
    raw_maxp = best["test_proba_raw"].max(axis=1)
    cal_maxp = test_proba_cal.max(axis=1)

    ece_raw, bins_raw = ece(raw_maxp, raw_correct)
    ece_cal, bins_cal = ece(cal_maxp, cal_correct)
    print(f"  ECE before calibration: {ece_raw}")
    print(f"  ECE after  calibration: {ece_cal}")
    print(f"  Accuracy unaffected by calibration (should match): raw={raw_correct.mean():.4f} cal={cal_correct.mean():.4f}")

    # top-1 / top-2 candidates + margin, per test row
    sorted_idx = np.argsort(-test_proba_cal, axis=1)
    top1_idx = sorted_idx[:, 0]
    top2_idx = sorted_idx[:, 1]
    classes_arr = np.array(classes_cal)
    top1_label = classes_arr[top1_idx]
    top2_label = classes_arr[top2_idx]
    top1_conf = test_proba_cal[np.arange(len(test_proba_cal)), top1_idx]
    top2_conf = test_proba_cal[np.arange(len(test_proba_cal)), top2_idx]
    margin = top1_conf - top2_conf

    per_prediction = []
    for i in range(len(test_labels_arr)):
        per_prediction.append({
            "true": test_labels_arr[i],
            "top1": top1_label[i], "top1_conf": round(float(top1_conf[i]), 4),
            "top2": top2_label[i], "top2_conf": round(float(top2_conf[i]), 4),
            "margin": round(float(margin[i]), 4),
            "true_family": FAMILIES.get(test_labels_arr[i], test_labels_arr[i]),
            "top1_family": FAMILIES.get(top1_label[i], top1_label[i]),
            "correct_exact": bool(top1_label[i] == test_labels_arr[i]),
            "correct_family": bool(FAMILIES.get(top1_label[i], top1_label[i]) == FAMILIES.get(test_labels_arr[i], test_labels_arr[i])),
        })

    print("\n=== STAGE 2b: Threshold curves (coverage vs confidently-wrong-exact rate) ===")
    thresholds = np.arange(0.05, 1.0, 0.05)
    curve = []
    for t in thresholds:
        covered = [p for p in per_prediction if p["top1_conf"] >= t]
        if not covered:
            curve.append({"threshold": round(float(t), 2), "coverage": 0.0, "n_covered": 0, "false_confident_exact_rate": None})
            continue
        coverage = len(covered) / len(per_prediction)
        wrong = sum(1 for p in covered if not p["correct_exact"])
        fcr = wrong / len(covered)
        curve.append({"threshold": round(float(t), 2), "coverage": round(coverage, 4), "n_covered": len(covered),
                      "false_confident_exact_rate": round(fcr, 4)})
    for c in curve:
        print(f"  t={c['threshold']:.2f}  coverage={c['coverage']}  n={c['n_covered']:5}  false_confident_exact_rate={c['false_confident_exact_rate']}")

    # recommend thresholds for target false-confident rates
    recs = {}
    for target in [0.05, 0.10, 0.15]:
        candidates = [c for c in curve if c["false_confident_exact_rate"] is not None and c["false_confident_exact_rate"] <= target]
        if candidates:
            best_c = min(candidates, key=lambda c: c["threshold"])  # lowest threshold meeting the bar = max coverage
            recs[target] = best_c
        else:
            recs[target] = None
    print("\nRecommended thresholds:")
    for target, c in recs.items():
        print(f"  target false-confident-exact <= {target:.0%}: {c}")

    print("\n=== STAGE 2c: Per-dialect precision/recall/F1 (calibrated predictions, TEST) ===")
    print(classification_report(test_labels_arr, top1_label, zero_division=0))

    print("\n=== STAGE 4 input: per-dialect exact / top-2 / family accuracy + group severity ===")
    group_report = report_group_cardinality(rows)
    per_dialect_summary = {}
    for d in DIALECTS:
        mask = test_labels_arr == d
        n = int(mask.sum())
        if n == 0:
            per_dialect_summary[d] = {"n_test": 0}
            continue
        exact = float(np.mean(top1_label[mask] == d))
        top2_hit = float(np.mean((top1_label[mask] == d) | (top2_label[mask] == d)))
        fam_hit = float(np.mean([FAMILIES.get(top1_label[i], top1_label[i]) == FAMILIES.get(d, d) for i in range(len(top1_label)) if mask[i]]))
        mean_conf_when_correct = float(top1_conf[mask & (top1_label == d)].mean()) if (mask & (top1_label == d)).sum() else None
        mean_conf_when_wrong = float(top1_conf[mask & (top1_label != d)].mean()) if (mask & (top1_label != d)).sum() else None
        per_dialect_summary[d] = {
            "n_test": n, "exact_recall": round(exact, 3), "top2_recall": round(top2_hit, 3),
            "family_recall": round(fam_hit, 3), "mean_conf_correct": round(mean_conf_when_correct, 3) if mean_conf_when_correct else None,
            "mean_conf_wrong": round(mean_conf_when_wrong, 3) if mean_conf_when_wrong else None,
            "n_groups": group_report[d]["n_groups"], "severity": group_report[d]["severity"],
            "is_fallback_split": d in fallback_dialects,
        }
        print(f"  {d:15} n={n:4}  exact_recall={per_dialect_summary[d]['exact_recall']}  top2={per_dialect_summary[d]['top2_recall']}  "
              f"fam={per_dialect_summary[d]['family_recall']}  conf_if_correct={per_dialect_summary[d]['mean_conf_correct']}  "
              f"conf_if_wrong={per_dialect_summary[d]['mean_conf_wrong']}  groups={per_dialect_summary[d]['n_groups']}({per_dialect_summary[d]['severity']})")

    print("\n=== Length-based accuracy (calibrated top-1, best mode) ===")
    len_acc = accuracy_by_length(rows, test_idx, best["test_labels"], top1_label)
    for l in len_acc:
        print(f"  {l}")

    out = {
        "best_mode": best_mode,
        "mode_comparison": {m: {k: v for k, v in f.items() if k not in ("clf", "uv", "X_val", "X_test", "test_proba_raw", "test_pred_raw", "val_labels", "test_labels")} for m, f in fits.items()},
        "ece_raw": ece_raw, "ece_calibrated": ece_cal,
        "calibration_bins_raw": bins_raw, "calibration_bins_calibrated": bins_cal,
        "threshold_curve": curve,
        "threshold_recommendations": {str(k): v for k, v in recs.items()},
        "per_dialect_summary": per_dialect_summary,
        "length_accuracy": len_acc,
        "fallback_dialects": fallback_dialects,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nSaved to {OUT_PATH}")

    # also dump per-prediction records separately (bigger file)
    with open(OUT_DIR / "v1_per_prediction.json", "w") as f:
        json.dump(per_prediction, f, ensure_ascii=False, indent=2, default=str)
    print(f"Per-prediction records saved to {OUT_DIR / 'v1_per_prediction.json'}")


if __name__ == "__main__":
    main()
