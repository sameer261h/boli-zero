"""Phase 4c: assemble the final deliverable (data/markers/PHASE4_REPORT.md) from the Phase 3/4 outputs.

20 marker sets (after the picture-topic filter), per-group rating, confusion table, LOVO result,
and the grounding-check status.  A 'clear' rating is downgraded if fewer than 10 markers survive the topic filter.
"""

import json
from pathlib import Path

import numpy as np

from markers_common import OUT, VARIETIES

GROUPS = VARIETIES + ["Hindi"]
MIN_FINAL = 10


def main():
    rat = json.load(open(OUT / "phase3_ratings.json"))
    lib = json.load(open(OUT / "phase4_final_library.json"))
    topic = json.load(open(OUT / "phase4_topic_report.json"))
    lovo = json.load(open(OUT / "phase4_lovo_summary.json")) if (OUT / "phase4_lovo_summary.json").exists() else None
    conf = np.loadtxt(OUT / "phase3_confusion_strict_markers.csv", delimiter=",")
    confp = np.loadtxt(OUT / "phase3_confusion_primary_markers.csv", delimiter=",")
    tab = {t["variety"]: t for t in rat["table"]}
    L = []
    w = L.append

    w("# Phase 4: marker library for 19 regional varieties + ordinary Hindi\n")
    w("Cleaning: shared `clean()`; no spelling/sound-variant work was done (see VARIANT FLAG note). "
      "Markers come from Prisma text, validated on group-disjoint held-out data and against the other 19 groups, "
      "then filtered for picture-topic words using Hindi clips on the same prompt images.\n")
    w("## Ratings\n")
    w("| group | clips | stable | after topic filter | marker recall (strict split) | SVM ceiling (strict) | rating | confidence |")
    w("|---|---|---|---|---|---|---|---|")
    final_rating = {}
    for g in GROUPS:
        t = tab[g]
        kept = len(lib[g])
        rating = t["rating"]
        if rating == "clear markers" and kept < MIN_FINAL:
            rating = "shared with neighbours" if (t["group_recall_strict"] or 0) >= 0.5 else "not separable from text"
        final_rating[g] = rating
        f = lambda x: "n/a" if x is None else f"{x:.2f}"
        w(f"| {g} | {t['clips']} | {t['stable_markers']} | {kept} | {f(t['marker_recall_strict'])} | "
          f"{f(t['svm_ceiling_strict'])} | **{rating}** | {'LOW' if t['low_confidence'] else 'ok'} |")
    w("\nClusters of varieties the text cannot reliably tell apart (SVM confusion >= 15%): "
      + "; ".join("{" + ", ".join(c) + "}" for c in rat["clusters"]) + "\n")

    w("## Confusion (marker model, pooled over 5 seeds, rows=true, share of that group's test clips)\n")
    w("| true | top confusions (>=5%) | no marker fired |")
    w("|---|---|---|")
    labels = GROUPS + ["none"]
    for k, g in enumerate(GROUPS):
        row = conf[k] + confp[k]
        tot = row.sum()
        top = [f"{labels[u]} {row[u]/tot:.0%}" for u in np.argsort(-row) if u != k and u < len(GROUPS) and row[u] / tot >= 0.05][:4]
        w(f"| {g} | {', '.join(top) or '-'} | {row[-1]/tot:.0%} |")

    w("\n## Marker sets (top 15 per group after the topic filter; kind: w=word, e2/e3=ending, b/t=2-/3-word pair)\n")
    for g in GROUPS:
        w(f"### {g} - {final_rating[g]} ({len(lib[g])} markers; topic-flagged {topic[g]['topic_flagged']})")
        for m in lib[g][:15]:
            sh = f" ~{'/'.join(n for n, _ in m['shared_with'])}" if m["shared_with"] else ""
            w(f"- `{m['feature']}` df={m['df']} lift={m['lift']:.0f}x stable={m['stable_runs']}/10"
              f" topic={m['topic_status']}{sh}")
        if topic[g]["flagged_examples"]:
            w(f"  - removed as picture-topic: {', '.join(f for f, _, _ in topic[g]['flagged_examples'][:8])}")
        w("")

    w("## Hindi-vs-regional score, leave-one-variety-out\n")
    if lovo:
        w("| held-out variety | in-distribution recall | UNSEEN recall | SVM unseen (ceiling) | no-evidence share | Hindi FPR |")
        w("|---|---|---|---|---|---|")
        for v, a in lovo["per_variety"].items():
            w(f"| {v} | {a['in_dist_recall']:.2f} | {a['unseen_recall']:.2f} | {a['svm_unseen_recall']:.2f} | "
              f"{a['unseen_no_evidence']:.2f} | {a['lovo_hindi_fpr']:.3f} |")
        m = lovo["mean"]
        w(f"\nMean over varieties: in-distribution {m['in_dist_recall']:.2f}, unseen {m['unseen_recall']:.2f}, "
          f"SVM unseen {m['svm_unseen_recall']:.2f}, Hindi FPR {m['lovo_hindi_fpr']:.3f}. "
          f"Configs: {lovo['configs']}. K and the threshold maximise balanced accuracy; no Hindi-FPR cap was applied.\n")
    else:
        w("LOVO results not available.\n")

    w("## Evon grounding check\n")
    w("**NOT RUN.** `BOLI_EVON_URL` is not set in this environment and no Modal endpoint is reachable, so there is no "
      "downstream Evon to compare 'markers' against 'extra transcript context'. No result is claimed.\n")
    (OUT / "PHASE4_REPORT.md").write_text("\n".join(L), encoding="utf-8")
    print("wrote", OUT / "PHASE4_REPORT.md", len(L), "lines")
    print({g: final_rating[g] for g in GROUPS})


if __name__ == "__main__":
    main()
