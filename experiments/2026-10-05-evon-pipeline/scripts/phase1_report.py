"""Phase 1 aggregation: stable marker library, confusion table, clusters, ratings.

Reads data/markers/phase1_{primary,strict}_s{0..4}.json written by phase1_markers.py.

Pre-specified rating rule (set before looking at ratings):
  clear                  : strict-split marker recall >= 0.40 and >= 10 stable markers
  shared with neighbours : not clear, but recall counting any confusion partner (>=15% of the
                           variety's baseline-model confusion mass) as correct is >= 0.50
  not separable          : everything else
  low-confidence flag    : fewer than 4 state|district|gender cells or < 300 clips
Stable marker = in the top-50 of >= 6 of the 10 runs.
"""

import json
from collections import Counter, defaultdict

import numpy as np

from markers_common import OUT, VARIETIES, group_key, load_regional

TOPK, MIN_RUNS, PARTNER_SHARE = 50, 6, 0.15
V = len(VARIETIES)


def main():
    runs = {}
    for kind in ("primary", "strict"):
        for s in range(5):
            runs[(kind, s)] = json.load(open(OUT / f"phase1_{kind}_s{s}.json"))

    # stable marker library
    cnt = defaultdict(Counter)
    detail = {}
    for (kind, s), r in runs.items():
        for v in VARIETIES:
            for m in r["markers"][v][:TOPK]:
                cnt[v][m["feature"]] += 1
                detail.setdefault((v, m["feature"]), m)
    library = {}
    for v in VARIETIES:
        lst = []
        for f, c in cnt[v].most_common():
            if c < MIN_RUNS:
                break
            m = dict(detail[(v, f)])
            m["stable_runs"] = c
            lst.append(m)
        lst.sort(key=lambda m: (-m["stable_runs"], -m["w"]))
        library[v] = lst

    # pooled confusions (marker model and svm baseline) per split key
    def pooled(kind, key):
        M = np.zeros_like(np.array(runs[(kind, 0)][key]), dtype=float)
        for s in range(5):
            M += np.array(runs[(kind, s)][key])
        return M

    conf = {k: pooled(k, "confusion") for k in ("primary", "strict")}       # V x (V+1)
    bconf = {k: pooled(k, "baseline_confusion") for k in ("primary", "strict")}  # V x V
    allb = bconf["primary"] + bconf["strict"]

    # clusters from baseline confusion
    share = allb / np.maximum(allb.sum(1, keepdims=True), 1)
    adj = (share >= PARTNER_SHARE) | (share.T >= PARTNER_SHARE)
    np.fill_diagonal(adj, False)
    comp, seen = [], set()
    for i in range(V):
        if i in seen:
            continue
        stack, c = [i], set()
        while stack:
            a = stack.pop()
            if a in c:
                continue
            c.add(a)
            stack += [b for b in range(V) if adj[a, b] and b not in c]
        seen |= c
        comp.append(sorted(c))

    rows, _ = load_regional()
    cells = defaultdict(set)
    nclips = Counter()
    for r in rows:
        cells[r["variety"]].add(group_key(r, True))
        nclips[r["variety"]] += 1

    table = []
    for k, v in enumerate(VARIETIES):
        n_s = conf["strict"][k].sum()
        rec_s = conf["strict"][k, k] / n_s if n_s else None
        n_p = conf["primary"][k].sum()
        rec_p = conf["primary"][k, k] / n_p if n_p else None
        brec_s = bconf["strict"][k, k] / max(bconf["strict"][k].sum(), 1)
        brec_p = bconf["primary"][k, k] / max(bconf["primary"][k].sum(), 1)
        partners = [u for u in range(V) if u != k and share[k, u] >= PARTNER_SHARE]
        m = conf["strict"] + 0  # grouped recall on marker model, strict split
        grp = (m[k, k] + sum(m[k, u] for u in partners)) / n_s if n_s else None
        # top marker-model confusions (primary+strict pooled)
        mm = conf["primary"][k] + conf["strict"][k]
        tot = mm.sum()
        conf_top = [(VARIETIES[u], round(float(mm[u] / tot), 2)) for u in np.argsort(-mm)[:4]
                    if u != k and u < V and mm[u] / tot >= 0.05]
        nstable = len(library[v])
        uniq = sum(1 for m_ in library[v] if not m_["shared_with"])
        if rec_s is not None and rec_s >= 0.40 and nstable >= 10:
            rating = "clear markers"
        elif grp is not None and grp >= 0.50:
            rating = "shared with neighbours"
        else:
            rating = "not separable from text"
        low = len(cells[v]) < 4 or nclips[v] < 300
        table.append({
            "variety": v, "clips": nclips[v], "state_district_gender_cells": len(cells[v]),
            "stable_markers": nstable, "stable_unshared_markers": uniq,
            "marker_recall_primary": None if rec_p is None else round(float(rec_p), 3),
            "marker_recall_strict": None if rec_s is None else round(float(rec_s), 3),
            "svm_ceiling_primary": round(float(brec_p), 3), "svm_ceiling_strict": round(float(brec_s), 3),
            "group_recall_strict": None if grp is None else round(float(grp), 3),
            "confusion_partners_svm": [VARIETIES[u] for u in partners],
            "top_marker_confusions": conf_top,
            "rating": rating, "low_confidence": bool(low),
        })

    (OUT / "phase1_marker_library.json").write_text(json.dumps(library, ensure_ascii=False, indent=1))
    (OUT / "phase1_ratings.json").write_text(json.dumps(
        {"clusters": [[VARIETIES[i] for i in c] for c in comp if len(c) > 1],
         "table": table}, ensure_ascii=False, indent=1))
    np.savetxt(OUT / "phase1_confusion_strict_markers.csv", conf["strict"], fmt="%d", delimiter=",",
               header=",".join(VARIETIES + ["none"]))
    np.savetxt(OUT / "phase1_confusion_primary_markers.csv", conf["primary"], fmt="%d", delimiter=",",
               header=",".join(VARIETIES + ["none"]))
    np.savetxt(OUT / "phase1_confusion_svm_pooled.csv", allb, fmt="%d", delimiter=",", header=",".join(VARIETIES))

    print("clusters (SVM confusion >= 15%):", [[VARIETIES[i] for i in c] for c in comp if len(c) > 1])
    hdr = f"{'variety':14s}{'clips':>6s}{'cells':>6s}{'stab':>5s}{'unsh':>5s}{'mkP':>6s}{'mkS':>6s}{'svmP':>6s}{'svmS':>6s}{'grpS':>6s}  rating"
    print(hdr)
    for t in table:
        f = lambda x: "  n/a" if x is None else f"{x:6.2f}"
        print(f"{t['variety']:14s}{t['clips']:6d}{t['state_district_gender_cells']:6d}{t['stable_markers']:5d}"
              f"{t['stable_unshared_markers']:5d}{f(t['marker_recall_primary'])}{f(t['marker_recall_strict'])}"
              f"{f(t['svm_ceiling_primary'])}{f(t['svm_ceiling_strict'])}{f(t['group_recall_strict'])}  "
              f"{t['rating']}{' [LOW-CONF]' if t['low_confidence'] else ''}")
    print("\nconfusions (marker model):")
    for t in table:
        print(f"  {t['variety']:14s} -> {t['top_marker_confusions']}")


if __name__ == "__main__":
    main()
