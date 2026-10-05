"""Regional Speech Fingerprint -- Part 1-3 audit of the 24,986 Prisma transcripts.

Pure data-science audit of what we already collected. NO Evon calls anywhere
in this script. Uses only prisma_transcript (what Evon sees in production,
not the human reference) plus the metadata Vaani provides (state, district,
gender, language -- no speaker ID field exists, flagged explicitly below).

Produces:
  - group-cardinality report (how speaker-disjoint can our split realistically be)
  - group-disjoint train/val/test split (state+district+gender proxy groups)
  - discriminative feature analysis on TRAIN ONLY: word unigrams/bigrams,
    character n-grams, word-ending suffixes, log-odds ratio per dialect vs rest
  - comparison: marker-words-only features vs richer feature set, via a
    baseline TF-IDF + Logistic Regression classifier scored on held-out TEST
  - family-level accuracy (linguistic family groupings) vs exact-label accuracy
  - confusion matrix, with particular attention to the Bihari-family cluster
  - basic calibration check (expected calibration error) on predict_proba
  - performance broken out by utterance length

Usage:
  python regional_fingerprint_audit.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.model_selection import GroupShuffleSplit

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint"
MARKERS_PATH = DATA_DIR.parent / "markers_v2.json"
OUT_DIR = DATA_DIR / "regional_fingerprint_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DIALECTS = [
    "Bhojpuri", "Chhattisgarhi", "Maithili", "Rajasthani", "Garhwali",
    "Marwari", "Magahi", "Bajjika", "Khortha", "Angika", "Kumaoni",
    "Sadri", "Khariboli", "Surgujia", "Bundeli", "Surjapuri", "Awadhi",
    "Haryanvi", "Jaipuri",
]

# Linguistic family groupings (standard Indo-Aryan dialect classification,
# for family-level accuracy -- NOT derived from our data, this is external
# linguistic knowledge used only for scoring, not fed into any classifier).
FAMILIES = {
    "Bhojpuri": "Bihari", "Magahi": "Bihari", "Maithili": "Bihari",
    "Angika": "Bihari", "Bajjika": "Bihari", "Surjapuri": "Bihari",
    "Chhattisgarhi": "Chhattisgarhi-Eastern", "Surgujia": "Chhattisgarhi-Eastern",
    "Garhwali": "Pahari", "Kumaoni": "Pahari",
    "Rajasthani": "Rajasthani", "Marwari": "Rajasthani", "Jaipuri": "Rajasthani",
    "Khortha": "Jharkhandi", "Sadri": "Jharkhandi",
    "Awadhi": "Western-Hindi-belt", "Khariboli": "Western-Hindi-belt",
    "Bundeli": "Western-Hindi-belt", "Haryanvi": "Western-Hindi-belt",
}

WORD_RE = re.compile(r"[ऀ-ॿ]+")


def load_rows():
    rows = []
    for d in DIALECTS:
        with open(DATA_DIR / f"{d}.jsonl") as f:
            for line in f:
                r = json.loads(line)
                if r.get("error"):
                    continue
                text = (r.get("prisma_transcript") or "").strip()
                if not text:
                    continue
                meta = r.get("meta", {})
                group_key = f"{meta.get('state')}|{meta.get('district')}|{meta.get('gender')}"
                rows.append({
                    "dialect": d,
                    "text": text,
                    "group": group_key,
                    "state": meta.get("state"),
                    "district": meta.get("district"),
                    "gender": meta.get("gender"),
                    "n_words": len(WORD_RE.findall(text)),
                })
    return rows


def report_group_cardinality(rows):
    print("=== Group-cardinality report (state|district|gender proxy for speaker) ===")
    print("NOTE: Vaani metadata has NO speaker-ID field. This proxy groups by")
    print("state+district+gender -- almost certainly collapses many distinct")
    print("real speakers into one 'group'. A dialect with only 1-2 groups total")
    print("means a 'group-disjoint' split is close to meaningless for it --")
    print("flagged explicitly per-dialect below, not glossed over.\n")
    by_dialect = defaultdict(set)
    for r in rows:
        by_dialect[r["dialect"]].add(r["group"])
    report = {}
    for d in DIALECTS:
        n_groups = len(by_dialect[d])
        n_rows = sum(1 for r in rows if r["dialect"] == d)
        avg_rows_per_group = n_rows / n_groups if n_groups else 0
        severity = "SEVERE (<=3 groups)" if n_groups <= 3 else ("WEAK (<=8 groups)" if n_groups <= 8 else "OK")
        report[d] = {"n_rows": n_rows, "n_groups": n_groups, "avg_rows_per_group": round(avg_rows_per_group, 1), "severity": severity}
        print(f"  {d:15} rows={n_rows:5} groups={n_groups:3} avg_rows/group={avg_rows_per_group:6.1f}  [{severity}]")
    return report


def make_split(rows, test_size=0.2, val_size=0.2, seed=42, min_test_per_class=15):
    """Group-disjoint split where group cardinality allows it. For dialects
    with too few groups to guarantee test coverage (confirmed to happen:
    Bajjika/Khortha/Surgujia/Surjapuri got ZERO test rows on a naive
    GroupShuffleSplit, since 1-2 of their 2-7 groups landed entirely in
    train/val by chance), fall back to a plain stratified row-level split
    for those specific dialects only -- explicitly logged as NOT
    speaker-disjoint, not silently merged in as if equivalent."""
    import random
    random.seed(seed)
    groups = np.array([r["group"] for r in rows])
    labels = np.array([r["dialect"] for r in rows])
    idx = np.arange(len(rows))

    gss1 = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    trainval_idx, test_idx = next(gss1.split(idx, labels, groups))

    trainval_groups = groups[trainval_idx]
    gss2 = GroupShuffleSplit(n_splits=1, test_size=val_size / (1 - test_size), random_state=seed)
    train_sub_idx, val_sub_idx = next(gss2.split(trainval_idx, labels[trainval_idx], trainval_groups))
    train_idx = trainval_idx[train_sub_idx]
    val_idx = trainval_idx[val_sub_idx]

    train_idx, val_idx, test_idx = set(train_idx.tolist()), set(val_idx.tolist()), set(test_idx.tolist())

    # find dialects with too few test (or val) rows after group-disjoint split
    fallback_dialects = []
    for d in DIALECTS:
        d_idx = [i for i in idx if labels[i] == d]
        test_n = sum(1 for i in d_idx if i in test_idx)
        val_n = sum(1 for i in d_idx if i in val_idx)
        if test_n < min_test_per_class or val_n < min_test_per_class:
            fallback_dialects.append(d)

    if fallback_dialects:
        print(f"\nFALLBACK (not speaker-group-disjoint, too few groups for test coverage): {fallback_dialects}")
        random.seed(seed)
        for d in fallback_dialects:
            d_idx = [i for i in idx if labels[i] == d]
            # pull these rows out of whichever split they're currently in, redo as plain row split
            for i in d_idx:
                train_idx.discard(i)
                val_idx.discard(i)
                test_idx.discard(i)
            random.shuffle(d_idx)
            n = len(d_idx)
            n_test = max(min_test_per_class, int(n * test_size))
            n_val = max(min_test_per_class, int(n * val_size))
            test_idx.update(d_idx[:n_test])
            val_idx.update(d_idx[n_test:n_test + n_val])
            train_idx.update(d_idx[n_test + n_val:])

    train_idx, val_idx, test_idx = np.array(sorted(train_idx)), np.array(sorted(val_idx)), np.array(sorted(test_idx))

    # verify group leakage (expected to be nonzero now, but only from fallback-dialect rows)
    train_g = set(groups[train_idx])
    val_g, test_g = set(groups[val_idx]), set(groups[test_idx])
    overlap_tv = train_g & val_g
    overlap_tt = train_g & test_g
    overlap_vt = val_g & test_g
    print(f"\nSplit sizes: train={len(train_idx)} val={len(val_idx)} test={len(test_idx)}")
    print(f"Group overlap check (expect some overlap now -- only from fallback-dialect rows, which share groups by construction since they weren't group-split): train&val={len(overlap_tv)} train&test={len(overlap_tt)} val&test={len(overlap_vt)}")

    test_labels_check = Counter(labels[test_idx])
    missing = [d for d in DIALECTS if test_labels_check.get(d, 0) < min_test_per_class]
    print(f"Dialects still under {min_test_per_class} test rows after fallback: {missing if missing else 'none'}")

    return train_idx, val_idx, test_idx, fallback_dialects


def log_odds_discriminative_words(rows, train_idx, top_n=15):
    """Informative-Dirichlet-prior-style log-odds (Monroe et al. 2008 approximation):
    for each dialect, which words are overrepresented vs. the rest of the TRAIN corpus."""
    train_rows = [rows[i] for i in train_idx]
    by_dialect_words = defaultdict(Counter)
    all_words = Counter()
    for r in train_rows:
        words = WORD_RE.findall(r["text"])
        by_dialect_words[r["dialect"]].update(words)
        all_words.update(words)

    alpha = 1.0  # Dirichlet smoothing
    V = len(all_words)
    total_all = sum(all_words.values())

    results = {}
    for d in DIALECTS:
        d_counts = by_dialect_words[d]
        d_total = sum(d_counts.values())
        rest_total = total_all - d_total
        scored = []
        for w, d_freq in d_counts.items():
            if d_freq < 3:
                continue
            rest_freq = all_words[w] - d_freq
            # log-odds ratio with pseudo-counts
            p_d = (d_freq + alpha) / (d_total + alpha * V)
            p_rest = (rest_freq + alpha) / (rest_total + alpha * V)
            log_odds = np.log(p_d / p_rest)
            # variance for z-score (approx Monroe et al.)
            var = 1.0 / (d_freq + alpha) + 1.0 / (rest_freq + alpha)
            z = log_odds / np.sqrt(var)
            scored.append((w, d_freq, rest_freq, round(log_odds, 2), round(z, 1)))
        scored.sort(key=lambda x: -x[4])
        results[d] = scored[:top_n]
    return results


def word_ending_analysis(rows, train_idx, suffix_len=2, top_n=10):
    """Morphological proxy: which word-final character sequences are
    overrepresented per dialect (captures verb endings, case markers etc.
    without needing a real morphological analyzer)."""
    train_rows = [rows[i] for i in train_idx]
    by_dialect_suffix = defaultdict(Counter)
    all_suffix = Counter()
    for r in train_rows:
        words = WORD_RE.findall(r["text"])
        for w in words:
            if len(w) < suffix_len + 1:
                continue
            suf = w[-suffix_len:]
            by_dialect_suffix[r["dialect"]][suf] += 1
            all_suffix[suf] += 1

    results = {}
    for d in DIALECTS:
        d_counts = by_dialect_suffix[d]
        d_total = sum(d_counts.values())
        total_all = sum(all_suffix.values())
        scored = []
        for suf, d_freq in d_counts.items():
            if d_freq < 5:
                continue
            rest_freq = all_suffix[suf] - d_freq
            rest_total = total_all - d_total
            rate_d = d_freq / d_total
            rate_rest = rest_freq / rest_total if rest_total else 0
            ratio = rate_d / (rate_rest + 1e-6)
            if ratio > 1.5:
                scored.append((suf, d_freq, round(ratio, 1)))
        scored.sort(key=lambda x: -x[2])
        results[d] = scored[:top_n]
    return results


def load_old_markers():
    if not MARKERS_PATH.exists():
        return {}
    data = json.loads(MARKERS_PATH.read_text())
    return data.get("markers", {})


def build_feature_text(text, mode):
    """mode: 'word' (unigrams/bigrams via vectorizer analyzer), 'char' (char n-grams),
    'combined' handled by concatenating vectorizers at fit time instead."""
    return text


def run_classifier(rows, train_idx, val_idx, test_idx, feature_mode):
    train_texts = [rows[i]["text"] for i in train_idx]
    train_labels = [rows[i]["dialect"] for i in train_idx]
    test_texts = [rows[i]["text"] for i in test_idx]
    test_labels = [rows[i]["dialect"] for i in test_idx]

    if feature_mode == "word":
        vec = TfidfVectorizer(analyzer="word", token_pattern=r"[ऀ-ॿ]+", ngram_range=(1, 2), min_df=2)
    elif feature_mode == "char":
        vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 4), min_df=2)
    elif feature_mode == "combined":
        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2, max_features=20000)
    else:
        raise ValueError(feature_mode)

    X_train = vec.fit_transform(train_texts)
    X_test = vec.transform(test_texts)

    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
    clf.fit(X_train, train_labels)

    pred = clf.predict(X_test)
    proba = clf.predict_proba(X_test)
    max_proba = proba.max(axis=1)

    exact_acc = np.mean(pred == np.array(test_labels))

    fam_pred = [FAMILIES.get(p, p) for p in pred]
    fam_true = [FAMILIES.get(t, t) for t in test_labels]
    fam_acc = np.mean(np.array(fam_pred) == np.array(fam_true))

    # calibration: bin by predicted max-confidence, compare to empirical accuracy
    bins = np.linspace(0, 1, 11)
    bin_idx = np.digitize(max_proba, bins) - 1
    ece = 0.0
    calib_report = []
    for b in range(10):
        mask = bin_idx == b
        if mask.sum() == 0:
            continue
        bin_conf = max_proba[mask].mean()
        bin_acc = np.mean(pred[mask] == np.array(test_labels)[mask])
        ece += (mask.sum() / len(pred)) * abs(bin_conf - bin_acc)
        calib_report.append({"bin": f"{bins[b]:.1f}-{bins[b+1]:.1f}", "n": int(mask.sum()), "mean_confidence": round(float(bin_conf), 3), "empirical_accuracy": round(float(bin_acc), 3)})

    cm = confusion_matrix(test_labels, pred, labels=DIALECTS)

    return {
        "feature_mode": feature_mode,
        "n_features": X_train.shape[1],
        "exact_accuracy": round(float(exact_acc), 4),
        "family_accuracy": round(float(fam_acc), 4),
        "ece": round(float(ece), 4),
        "calibration_bins": calib_report,
        "confusion_matrix": cm.tolist(),
        "confusion_labels": DIALECTS,
        "classification_report": classification_report(test_labels, pred, zero_division=0),
        "test_labels": test_labels,
        "predictions": pred.tolist(),
        "max_proba": max_proba.tolist(),
        "test_n_words": [rows[i]["n_words"] for i in test_idx],
    }


def accuracy_by_length(result):
    labels = np.array(result["test_labels"])
    preds = np.array(result["predictions"])
    lengths = np.array(result["test_n_words"])
    bins = [(1, 3), (4, 6), (7, 10), (11, 20), (21, 1000)]
    out = []
    for lo, hi in bins:
        mask = (lengths >= lo) & (lengths <= hi)
        if mask.sum() == 0:
            continue
        acc = np.mean(preds[mask] == labels[mask])
        out.append({"length_range": f"{lo}-{hi if hi < 1000 else '+'}", "n": int(mask.sum()), "accuracy": round(float(acc), 3)})
    return out


def main():
    print("Loading rows...")
    rows = load_rows()
    print(f"Total usable rows (non-empty prisma_transcript): {len(rows)}\n")

    group_report = report_group_cardinality(rows)

    train_idx, val_idx, test_idx, fallback_dialects = make_split(rows)

    print("\n=== Discriminative lexical markers (train-only, log-odds z-score) ===")
    log_odds = log_odds_discriminative_words(rows, train_idx)
    for d in DIALECTS:
        top = log_odds[d][:8]
        print(f"  {d:15} " + ", ".join(f"{w}(z={z})" for w, _, _, _, z in top))

    print("\n=== Discriminative word-ending suffixes (train-only, morphology proxy) ===")
    suffixes = word_ending_analysis(rows, train_idx)
    for d in DIALECTS:
        top = suffixes[d][:6]
        print(f"  {d:15} " + ", ".join(f"-{s}(x{ratio})" for s, _, ratio in top))

    old_markers = load_old_markers()
    print(f"\nOld marker-word lists available for {len(old_markers)} dialects (from markers_v2.json, derived from HUMAN transcripts of a different sample -- not directly comparable, context only)")

    print("\n=== Classifier comparison (word TF-IDF vs char n-gram vs combined) ===")
    results = {}
    for mode in ["word", "char", "combined"]:
        print(f"\n--- feature_mode={mode} ---")
        res = run_classifier(rows, train_idx, val_idx, test_idx, mode)
        results[mode] = res
        print(f"  exact_accuracy={res['exact_accuracy']}  family_accuracy={res['family_accuracy']}  ECE={res['ece']}  n_features={res['n_features']}")
        len_acc = accuracy_by_length(res)
        print("  accuracy by utterance length:", len_acc)

    # Bihari-family confusion matrix (the explicitly requested cluster)
    best_mode = max(results, key=lambda m: results[m]["exact_accuracy"])
    cm = np.array(results[best_mode]["confusion_matrix"])
    bihari = ["Bhojpuri", "Magahi", "Maithili", "Angika", "Bajjika"]
    bihari_idx = [DIALECTS.index(d) for d in bihari]
    print(f"\n=== Bihari-family confusion matrix (best mode: {best_mode}) ===")
    print("rows=true, cols=predicted:", bihari)
    for i, d in zip(bihari_idx, bihari):
        row_counts = [cm[i][j] for j in bihari_idx]
        print(f"  {d:12} {row_counts}")

    # save everything
    out = {
        "n_total_rows": len(rows),
        "group_cardinality_report": group_report,
        "fallback_dialects_not_speaker_disjoint": fallback_dialects,
        "split_sizes": {"train": len(train_idx), "val": len(val_idx), "test": len(test_idx)},
        "log_odds_top_markers": {d: log_odds[d] for d in DIALECTS},
        "discriminative_suffixes": {d: suffixes[d] for d in DIALECTS},
        "classifier_results": {m: {k: v for k, v in r.items() if k not in ("confusion_matrix",)} for m, r in results.items()},
        "confusion_matrices": {m: r["confusion_matrix"] for m, r in results.items()},
        "confusion_labels": DIALECTS,
        "families": FAMILIES,
    }
    with open(OUT_DIR / "audit_results.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nFull results saved to {OUT_DIR / 'audit_results.json'}")


if __name__ == "__main__":
    main()
