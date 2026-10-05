"""Phase 2 report on the pulled Hindi sample: Prisma errors, prompt-image overlap with the regional
data, and a 50-clip Bihar/UP spot-check for 'is this really Hindi?'.

The spot-check prints transcripts for reading AND counts hits of strong regional markers
(unshared stable markers of Bhojpuri/Maithili/Magahi/Rajasthani... from the Phase 1 library),
so contamination is visible both by eye and by number.
"""

import json
import random
from collections import Counter

from markers_common import DATA, OUT, VARIETIES, load_regional

HIN = DATA / "hindi"


def main():
    rows, st = load_regional(True)
    hin = [r for r in rows if r["variety"] == "Hindi"]
    reg = [r for r in rows if r["variety"] != "Hindi"]
    print("Hindi load stats:", st["Hindi"])
    print("pull summary:", (HIN / "pull_summary.json").read_text() if (HIN / "pull_summary.json").exists() else "n/a")

    rp = {r["prompt"] for r in reg}
    hp = Counter(r["prompt"] for r in hin)
    shared = sum(c for p, c in hp.items() if p in rp)
    print(f"\nPROMPT IMAGES: Hindi clips {len(hin)}, distinct prompts {len(hp)}; "
          f"clips on prompts that also occur in regional data: {shared} ({shared/len(hin):.1%})")
    kinds = Counter(("SPECIFIC" if "SPECIFIC" in p else "GENERIC" if "GENERIC" in p else "other") for p in hp.elements())
    print("Hindi clip prompt kinds:", dict(kinds))
    rk = Counter(("SPECIFIC" if "SPECIFIC" in r["prompt"] else "GENERIC" if "GENERIC" in r["prompt"] else "other") for r in reg)
    print("regional clip prompt kinds:", dict(rk))
    print("Hindi by state:", Counter(r["state"] for r in hin).most_common(10))
    print("Hindi duration median/mean:", sorted(r["dur"] or 0 for r in hin)[len(hin) // 2],
          sum((r["dur"] or 0) for r in hin) / len(hin))

    lib = json.load(open(OUT / "phase1_marker_library.json"))
    strong = {}
    for v, ms in lib.items():
        for m in ms:
            if m["kind"] == "w" and not m["shared_with"] and m["df"] >= 15:
                strong.setdefault(m["feature"][2:], v)
    print(f"\nstrong single-word regional markers used for contamination count: {len(strong)}")

    def hits(r):
        return sorted({strong[t] for t in r["prisma"] if t in strong})

    sel = [r for r in hin if r["state"] in ("Bihar", "UttarPradesh")]
    allhit = sum(1 for r in sel if hits(r))
    print(f"Bihar/UP Hindi clips: {len(sel)}; with >=1 strong regional marker: {allhit} ({allhit/len(sel):.1%})")
    for st_ in ("Bihar", "UttarPradesh"):
        s2 = [r for r in sel if r["state"] == st_]
        h2 = sum(1 for r in s2 if hits(r))
        print(f"   {st_}: {len(s2)} clips, {h2} with a regional marker ({h2/max(len(s2),1):.1%})")
    others = [r for r in hin if r["state"] not in ("Bihar", "UttarPradesh")]
    ho = sum(1 for r in others if hits(r))
    print(f"   other states: {len(others)} clips, {ho} with a regional marker ({ho/max(len(others),1):.1%})")
    print("   which varieties' markers fire on Bihar/UP Hindi:", Counter(v for r in sel for v in hits(r)).most_common(8))

    random.seed(0)
    print("\n--- 50 random Bihar/UP Hindi clips (state | human | Prisma | regional-marker hits) ---")
    for r in random.sample(sel, min(50, len(sel))):
        print(f"{r['state'][:5]}|{r['district']}|{' '.join(r['human'])[:90]} || {' '.join(r['prisma'])[:90]} || {hits(r)}")


if __name__ == "__main__":
    main()
