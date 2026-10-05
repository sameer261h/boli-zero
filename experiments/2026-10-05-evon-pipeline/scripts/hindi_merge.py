"""Merge Hindi.jsonl + Hindi.part*.jsonl into Hindi.jsonl, one row per (shard,row_idx), preferring a
successful row over an errored one. Prints counts."""

import json
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint"


def main():
    best = {}
    files = [D / "Hindi.jsonl"] + sorted(D.glob("Hindi.part*.jsonl"))
    n_in = 0
    for p in files:
        if not p.exists():
            continue
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            n_in += 1
            k = (r["shard"], r["row_idx"])
            if k not in best or (best[k].get("error") and not r.get("error")):
                best[k] = r
    tmp = D / "Hindi.jsonl.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for k in sorted(best):
            fh.write(json.dumps(best[k], ensure_ascii=False) + "\n")
    tmp.replace(D / "Hindi.jsonl")
    err = sum(1 for r in best.values() if r.get("error"))
    print(f"merged {n_in} lines -> {len(best)} unique clips, {err} with error, "
          f"{sum(1 for r in best.values() if not r.get('error') and not (r.get('prisma_transcript') or '').strip())} empty transcripts")


if __name__ == "__main__":
    main()
