"""Phase 4b: Hindi-vs-regional score and leave-one-variety-out (LOVO).

Score for an utterance: m = max over regional groups of (marker score) - Hindi marker score.
Flag regional if m > t (t >= 0, so an utterance with no evidence is called Hindi).
K (markers per group) and t are chosen on the VAL split of the groups in training, maximising
balanced accuracy (50% Hindi correct, 50% mean per-variety regional recall) -- NOT a Hindi-FPR cap.

For each held-out variety H: train on Hindi + the other 18 (markers AND K/t chosen without H),
then flag ALL of H's clips (H never seen).  In-distribution recall = same procedure with H included,
scored on H's TEST split.  A linear-SVM Hindi-vs-regional model is the statistical ceiling.

Usage: python phase4_lovo.py --seed 0 [--strict]     (one config; run several in parallel)
       python phase4_lovo.py --aggregate
"""

import argparse
import glob
import json

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.svm import LinearSVC

import phase1_markers as pm
from markers_common import OUT, VARIETIES as REG, load_regional, split_groups

KS = (10, 25, 50, 100)


def margin(rows, idx, vec, markers, K, vs):
    S = pm.score_matrix(rows, idx, vec, markers, K, vs)
    h = vs.index("Hindi")
    regi = [i for i, v in enumerate(vs) if v != "Hindi"]
    return S[:, regi].max(1) - S[:, h]


def fit_model(rows, tr, va, vs):
    """Derive markers on train rows of `vs`; choose (K, t) on val rows of `vs`."""
    tri = [i for i in tr if rows[i]["variety"] in vs]
    vai = [i for i in va if rows[i]["variety"] in vs]
    vec = CountVectorizer(analyzer=lambda x: x, binary=True, min_df=3)
    vec.fit([pm.features(rows[i]["prisma"]) for i in tri])
    markers = pm.derive(rows, None, vec, tri, [rows[i]["variety"] for i in tri], vs)
    yv = np.array([rows[i]["variety"] for i in vai])
    best = (-1, None, None)
    for K in KS:
        m = margin(rows, vai, vec, markers, K, vs)
        cands = np.unique(np.concatenate([[0.0], np.quantile(m[m > 0], np.linspace(0.02, 0.98, 25)) if (m > 0).any() else []]))
        for t in cands:
            flag = m > t
            fpr = flag[yv == "Hindi"].mean() if (yv == "Hindi").any() else 0.0
            recs = [flag[yv == v].mean() for v in vs if v != "Hindi" and (yv == v).any()]
            bal = 0.5 * (1 - fpr) + 0.5 * np.mean(recs)
            if bal > best[0]:
                best = (bal, K, float(t))
    return vec, markers, best[1], best[2], best[0]


def svm_binary(rows, tr, vs):
    tri = [i for i in tr if rows[i]["variety"] in vs]
    tx = lambda ii: [" ".join(rows[i]["prisma"]) for i in ii]
    w = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    c = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3, sublinear_tf=True)
    X = hstack([w.fit_transform(tx(tri)), c.fit_transform(tx(tri))]).tocsr()
    y = np.array([rows[i]["variety"] == "Hindi" for i in tri])
    clf = LinearSVC(C=0.5, class_weight="balanced").fit(X, y)
    return lambda ii: ~clf.predict(hstack([w.transform(tx(ii)), c.transform(tx(ii))]).tocsr()).astype(bool)  # True = regional


def run(seed, strict):
    rows, _ = load_regional(True)
    split = split_groups(rows, seed=seed, strict=strict)
    ix = {s: [i for i, x in enumerate(split) if x == s] for s in ("train", "val", "test")}
    hin_test = [i for i in ix["test"] if rows[i]["variety"] == "Hindi"]
    out = {"seed": seed, "strict": strict, "per_variety": {}}

    # in-distribution: one model with every group
    vs = ["Hindi"] + list(REG)
    vec, mk, K, t, bal = fit_model(rows, ix["train"], ix["val"], vs)
    te = ix["test"]
    flag = margin(rows, te, vec, mk, K, vs) > t
    yte = np.array([rows[i]["variety"] for i in te])
    full = {v: float(flag[yte == v].mean()) if (yte == v).any() else None for v in REG}
    full_fpr = float(flag[yte == "Hindi"].mean()) if (yte == "Hindi").any() else None
    out["full"] = {"K": K, "t": t, "val_bal_acc": bal, "hindi_fpr": full_fpr, "n_hindi_test": int((yte == "Hindi").sum())}
    print(f"[{seed} strict={strict}] full model K={K} t={t:.2f} hindi FPR {full_fpr}", flush=True)

    for H in REG:
        vsH = ["Hindi"] + [v for v in REG if v != H]
        vec, mk, K, t, bal = fit_model(rows, ix["train"], ix["val"], vsH)
        hid = [i for i, r in enumerate(rows) if r["variety"] == H]
        mH = margin(rows, hid, vec, mk, K, vsH)
        mT = margin(rows, hin_test, vec, mk, K, vsH) if hin_test else np.array([])
        S = svm_binary(rows, ix["train"], vsH)
        out["per_variety"][H] = {
            "in_dist_recall": full[H],
            "unseen_recall": float((mH > t).mean()),
            "unseen_no_evidence": float((mH == 0).mean()),
            "n_unseen": len(hid),
            "lovo_hindi_fpr": float((mT > t).mean()) if len(mT) else None,
            "K": K, "t": t,
            "svm_unseen_recall": float(S(hid).mean()),
            "svm_hindi_fpr": float(S(hin_test).mean()) if hin_test else None,
        }
        p = out["per_variety"][H]
        print(f"  {H:14s} in-dist {p['in_dist_recall']:.2f} unseen {p['unseen_recall']:.2f} "
              f"(svm {p['svm_unseen_recall']:.2f}) hindiFPR {p['lovo_hindi_fpr']}", flush=True)
    (OUT / f"phase4_lovo_{'strict' if strict else 'primary'}_s{seed}.json").write_text(json.dumps(out, indent=1))


def aggregate():
    files = sorted(glob.glob(str(OUT / "phase4_lovo_*_s*.json")))
    runs = [json.load(open(f)) for f in files]
    print(f"{len(runs)} configs: {[(r['strict'], r['seed']) for r in runs]}")
    print(f"{'variety':14s}{'in-dist':>9s}{'unseen':>8s}{'svm-unseen':>11s}{'noEvid':>8s}{'HindiFPR':>9s}")
    agg = {}
    for v in REG:
        g = lambda k: [r["per_variety"][v][k] for r in runs if r["per_variety"][v][k] is not None]
        agg[v] = {k: float(np.mean(g(k))) for k in ("in_dist_recall", "unseen_recall", "svm_unseen_recall", "unseen_no_evidence", "lovo_hindi_fpr")}
        a = agg[v]
        print(f"{v:14s}{a['in_dist_recall']:9.2f}{a['unseen_recall']:8.2f}{a['svm_unseen_recall']:11.2f}"
              f"{a['unseen_no_evidence']:8.2f}{a['lovo_hindi_fpr']:9.3f}")
    mean = lambda k: float(np.mean([agg[v][k] for v in REG]))
    summ = {k: mean(k) for k in ("in_dist_recall", "unseen_recall", "svm_unseen_recall", "lovo_hindi_fpr")}
    print("MEAN over varieties:", summ)
    (OUT / "phase4_lovo_summary.json").write_text(json.dumps({"per_variety": agg, "mean": summ,
                                                              "configs": [(r["strict"], r["seed"]) for r in runs]}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--aggregate", action="store_true")
    a = ap.parse_args()
    aggregate() if a.aggregate else run(a.seed, a.strict)
