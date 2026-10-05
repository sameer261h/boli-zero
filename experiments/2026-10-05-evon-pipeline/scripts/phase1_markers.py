"""Phase 1: marker sets for the 19 regional varieties from log-odds on cleaned Prisma text.

Features (per utterance, presence only): word unigrams, 2/3-char word endings,
word bigrams and trigrams. Markers are derived on TRAIN groups only, K is chosen on
VAL groups, everything is reported on held-out TEST groups.

Usage: python phase1_markers.py [--strict] [--seed 0]
  default split key  : state|district|gender|prompt  (as specified)
  --strict split key : state|district|gender        (far fewer groups; closer to speaker-disjoint)
"""

import argparse
import json
import math
import sys
from collections import Counter, defaultdict

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from scipy.sparse import hstack
from sklearn.svm import LinearSVC

from markers_common import OUT, VARIETIES, group_key, load_regional, split_groups

HINDI = "--hindi" in sys.argv  # Phase 3: Hindi becomes a 20th class
if HINDI:
    VARIETIES = VARIETIES + ["Hindi"]
PREFIX = "phase3" if HINDI else "phase1"

EPS = 5e-4
MIN_DF = 8            # utterances in the variety (train)
MIN_GROUPS = 6        # distinct split-groups
MIN_DISTRICTS = 2     # if the variety has >= 3 districts
MAX_DISTRICT_SHARE = 0.6  # place/person-name heuristic: concentrated in one district -> drop
NEIGHBOR_RATIO = 0.7  # V must be within 0.7x of the best other variety (shared markers allowed, listed in shared_with)
MIN_LIFT = 3.0        # f_V / macro-average of the other 18 varieties
KS = (10, 25, 50, 100, 200)


def features(toks):
    f = set()
    n = len(toks)
    for i, t in enumerate(toks):
        f.add("w:" + t)
        if len(t) >= 4:
            f.add("e2:" + t[-2:])
            f.add("e3:" + t[-3:])
        if i + 1 < n:
            f.add("b:" + t + " " + toks[i + 1])
        if i + 2 < n:
            f.add("t:" + t + " " + toks[i + 1] + " " + toks[i + 2])
    return list(f)


def wilson_lb(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - a) / d)


def parts(feat):
    """Constituents of a feature, used for redundancy pruning."""
    kind, s = feat.split(":", 1)
    if kind in ("b", "t"):
        return [("w:" + w) for w in s.split(" ")] + [
            f"e{k}:{w[-k:]}" for w in s.split(" ") for k in (2, 3) if len(w) >= 4]
    return []


def derive(rows, split, vec, Xtr_idx, ytr, vs=None):
    """Return {variety: [marker dicts sorted best-first]} derived from train only."""
    vs = vs or VARIETIES
    Xtr = vec.transform([features(rows[i]["prisma"]) for i in Xtr_idx]).tocsc()
    names = np.array(vec.get_feature_names_out())
    V = len(vs)
    vi = {v: k for k, v in enumerate(vs)}
    y = np.array([vi[v] for v in ytr])
    NV = np.bincount(y, minlength=V).astype(float)
    Y = sparse.csr_matrix((np.ones(len(y)), (y, np.arange(len(y)))), shape=(V, len(y)))
    D = np.asarray((Y @ Xtr).todense())            # V x F utterance counts
    Fr = D / NV[:, None]
    tot = Fr.sum(0)
    # human-side counts (same features on human tokens) for "Prisma habit" analysis
    Xh = vec.transform([features(rows[i]["human"]) for i in Xtr_idx]).tocsc()
    Dh = np.asarray((Y @ Xh).todense())
    gk = [group_key(rows[i]) for i in Xtr_idx]
    dk = [rows[i]["district"] for i in Xtr_idx]
    n_dist = {v: len({d for d, yy in zip(dk, y) if yy == vi[v]}) for v in vs}

    out = {}
    for v in vs:
        k = vi[v]
        fV = Fr[k]
        others = (tot - fV) / (V - 1)
        lift = fV / (others + EPS)
        mx = np.max(np.delete(Fr, k, axis=0), axis=0)
        cand = np.where((D[k] >= MIN_DF) & (lift >= MIN_LIFT) & (fV >= NEIGHBOR_RATIO * mx))[0]
        rowsV = np.where(y == k)[0]
        res = []
        for c in cand:
            col = Xtr[:, c]
            hit = col.indices[np.isin(col.indices, rowsV)]
            groups = {gk[h] for h in hit}
            dists = Counter(dk[h] for h in hit)
            if len(groups) < MIN_GROUPS:
                continue
            if n_dist[v] >= 3:
                if len(dists) < MIN_DISTRICTS or max(dists.values()) / len(hit) > MAX_DISTRICT_SHARE:
                    continue
            lb = wilson_lb(D[k, c], NV[k])
            if lb < 2 * others[c]:
                continue
            nb = [(vs[u], round(float(Fr[u, c]), 4)) for u in range(V)
                  if u != k and Fr[u, c] >= 0.3 * fV[c]]
            res.append({
                "feature": str(names[c]),
                "kind": str(names[c]).split(":", 1)[0],
                "df": int(D[k, c]), "f_V": round(float(fV[c]), 5),
                "f_others_macro": round(float(others[c]), 5),
                "f_max_other": round(float(mx[c]), 5),
                "lift": round(float(lift[c]), 2),
                "w": round(float(math.log((lb + EPS) / (others[c] + EPS))), 3),
                "groups": len(groups), "districts": len(dists),
                "shared_with": nb,
                "human_df": int(Dh[k, c]),
                "asr_ratio": round(float((D[k, c] + 1) / (Dh[k, c] + 1)), 2),
            })
        res.sort(key=lambda r: -r["w"] * math.log(1 + r["df"]))
        # redundancy: drop a longer unit whose coverage is mostly explained by an already kept constituent
        kept, kf = [], {}
        for r in res:
            ps = [p for p in parts(r["feature"]) if p in kf]
            if any(r["df"] <= 2.0 * kf[p] and r["df"] >= 0 and kf[p] >= 0.5 * r["df"] for p in ps):
                continue
            kept.append(r)
            kf[r["feature"]] = r["df"]
        out[v] = kept
    return out


def score_matrix(rows, idx, vec, markers, K, vs=None):
    """Sum of weights of distinct markers present, per variety. Returns (n x V)."""
    vs = vs or VARIETIES
    X = vec.transform([features(rows[i]["prisma"]) for i in idx]).tocsc()
    fi = {f: j for j, f in enumerate(vec.get_feature_names_out())}
    S = np.zeros((len(idx), len(vs)))
    for k, v in enumerate(vs):
        for m in markers[v][:K]:
            j = fi.get(m["feature"])
            if j is None:
                continue
            col = X[:, j].indices
            S[col, k] += m["w"]
    return S


def evaluate(S, truth, vs=None):
    vs = vs or VARIETIES
    vi = {v: k for k, v in enumerate(vs)}
    y = np.array([vi[t] for t in truth])
    has = S.max(1) > 0
    pred = np.where(has, S.argmax(1), -1)
    V = len(vs)
    conf = np.zeros((V, V + 1), int)
    for a, p in zip(y, pred):
        conf[a, p if p >= 0 else V] += 1
    rec = {}
    for k, v in enumerate(vs):
        n = conf[k].sum()
        rec[v] = {"n": int(n), "recall": conf[k, k] / n if n else None,
                  "coverage": 1 - conf[k, V] / n if n else None}
    macro = np.mean([r["recall"] for r in rec.values() if r["recall"] is not None])
    return conf, rec, float(macro), float(has.mean())



def baseline(rows, idx):
    """Statistical ceiling: linear SVM on word 1-2gram + char 2-4gram tf-idf, balanced classes, same splits."""
    tx = lambda ii: [" ".join(rows[i]["prisma"]) for i in ii]
    w = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    c = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3, sublinear_tf=True)
    Xtr = hstack([w.fit_transform(tx(idx["train"])), c.fit_transform(tx(idx["train"]))]).tocsr()
    Xte = hstack([w.transform(tx(idx["test"])), c.transform(tx(idx["test"]))]).tocsr()
    ytr = [rows[i]["variety"] for i in idx["train"]]
    yte = np.array([rows[i]["variety"] for i in idx["test"]])
    clf = LinearSVC(C=0.5, class_weight="balanced").fit(Xtr, ytr)
    pred = clf.predict(Xte)
    per = {v: float((pred[yte == v] == v).mean()) if (yte == v).any() else None for v in VARIETIES}
    conf = np.zeros((len(VARIETIES), len(VARIETIES)), int)
    vi = {v: k for k, v in enumerate(VARIETIES)}
    for t, p in zip(yte, pred):
        conf[vi[t], vi[p]] += 1
    return float(np.mean([x for x in per.values() if x is not None])), per, conf.tolist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--hindi", action="store_true", help="20-class run: Hindi as an extra group (read at import via sys.argv)")
    a = ap.parse_args()
    tag = ("strict" if a.strict else "primary") + f"_s{a.seed}"
    OUT.mkdir(parents=True, exist_ok=True)

    rows, stats = load_regional(HINDI)
    split = split_groups(rows, seed=a.seed, strict=a.strict)
    idx = {s: [i for i, x in enumerate(split) if x == s] for s in ("train", "val", "test")}
    ng = {s: len({group_key(rows[i], a.strict) for i in idx[s]}) for s in idx}
    print(tag, {s: (len(idx[s]), ng[s]) for s in idx})

    vec = CountVectorizer(analyzer=lambda x: x, binary=True, min_df=3)
    vec.fit([features(rows[i]["prisma"]) for i in idx["train"]])
    print("vocab", len(vec.vocabulary_))
    markers = derive(rows, split, vec, idx["train"], [rows[i]["variety"] for i in idx["train"]])
    for v in VARIETIES:
        print(f"  {v:14s} markers={len(markers[v])}")

    ytv = [rows[i]["variety"] for i in idx["val"]]
    best = {}
    for K in KS:
        S = score_matrix(rows, idx["val"], vec, markers, K)
        _, _, macro, cov = evaluate(S, ytv)
        print(f"  K={K}: val macro-recall {macro:.3f} coverage {cov:.3f}")
        best[K] = macro
    K = max(best, key=best.get)
    print("chosen K", K)

    yte = [rows[i]["variety"] for i in idx["test"]]
    S = score_matrix(rows, idx["test"], vec, markers, K)
    conf, rec, macro, cov = evaluate(S, yte)
    print(f"TEST macro-recall {macro:.3f} coverage {cov:.3f}")

    bmacro, bper, bconf = baseline(rows, idx)
    print(f"BASELINE (svm n-gram ceiling) TEST macro-recall {bmacro:.3f}")
    res = {"baseline_macro_recall": bmacro, "baseline_per_variety": bper, "baseline_confusion": bconf, "tag": tag, "K": K, "val_macro": best, "test_macro_recall": macro,
           "test_coverage": cov, "groups": ng, "per_variety": rec,
           "confusion": conf.tolist(), "labels": VARIETIES + ["none"],
           "markers": {v: markers[v][:200] for v in VARIETIES}, "load_stats": stats}
    (OUT / f"{PREFIX}_{tag}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("wrote", OUT / f"{PREFIX}_{tag}.json")


if __name__ == "__main__":
    main()
