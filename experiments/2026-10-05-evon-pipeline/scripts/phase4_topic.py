"""Phase 4a: picture-topic check. For every stable marker of every group, compare its rate in the group's
clips with its rate in HINDI clips of the SAME prompt images.

If a marker is just describing the picture, Hindi speakers describing the same picture use it too, so
rate_Hindi(shared prompts) is comparable to rate_V(shared prompts) -> flagged TOPIC and removed.
Markers with too little shared-prompt evidence are kept but marked untested.

Reads data/markers/phase3_marker_library.json; writes phase4_final_library.json and phase4_topic_report.json.
"""

import json
from collections import defaultdict

from markers_common import OUT, VARIETIES, load_regional
from phase1_markers import features

TOPIC_RATIO = 0.5   # Hindi rate on shared prompts >= 0.5 x group rate on shared prompts -> topic word
MIN_HITS = 3        # group hits on shared prompts needed to test


def main():
    rows, _ = load_regional(True)
    lib = json.load(open(OUT / "phase3_marker_library.json"))
    hin = [r for r in rows if r["variety"] == "Hindi"]
    hprompts = defaultdict(list)
    for r in hin:
        hprompts[r["prompt"]].append(r)
    feats = {}

    def F(r):
        k = id(r)
        if k not in feats:
            feats[k] = set(features(r["prisma"]))
        return feats[k]

    report, final = {}, {}
    byv = defaultdict(list)
    for r in rows:
        if r["variety"] != "Hindi":
            byv[r["variety"]].append(r)
    for v, ms in lib.items():
        if v == "Hindi":
            # a Hindi marker is topic-driven if regional speakers on the same prompts use it as often
            src = [r for r in rows if r["variety"] != "Hindi" and r["prompt"] in hprompts]
            ref = hin
        else:
            src = [r for r in byv[v] if r["prompt"] in hprompts]
            ref = [x for p in {r["prompt"] for r in src} for x in hprompts[p]]
        other = ref if v != "Hindi" else None
        keep, flagged, untested = [], [], 0
        for m in ms:
            f = m["feature"]
            if v == "Hindi":
                shared_p = {r["prompt"] for r in hin}
                grp = [r for r in hin if r["prompt"] in {x["prompt"] for x in src}]
                cmp_ = src
            else:
                grp, cmp_ = src, ref
            kg = sum(1 for r in grp if f in F(r))
            kc = sum(1 for r in cmp_ if f in F(r))
            ng, nc = len(grp), len(cmp_)
            status = "untested"
            if kg >= MIN_HITS and nc >= 20:
                rg, rc = kg / ng, kc / nc
                status = "topic" if rc >= TOPIC_RATIO * rg else "ok"
            m2 = dict(m, topic_status=status, shared_prompt_hits=kg, shared_prompt_n=ng, compare_hits=kc, compare_n=nc)
            if status == "topic":
                flagged.append(m2)
            else:
                keep.append(m2)
                untested += status == "untested"
        final[v] = keep
        report[v] = {"stable": len(ms), "kept": len(keep), "topic_flagged": len(flagged), "kept_untested": untested,
                     "flagged_examples": [(m["feature"], m["shared_prompt_hits"], m["compare_hits"]) for m in flagged[:12]]}
        print(f"{v:14s} stable={len(ms):4d} kept={len(keep):4d} topic-flagged={len(flagged):3d} untested-kept={untested:3d}  "
              f"e.g. {[f['feature'] for f in flagged[:6]]}")
    (OUT / "phase4_final_library.json").write_text(json.dumps(final, ensure_ascii=False, indent=1))
    (OUT / "phase4_topic_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
