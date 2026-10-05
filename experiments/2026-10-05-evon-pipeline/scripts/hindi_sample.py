"""Phase 2b: draw a stratified Hindi sample from the sampling frame (hindi_metadata.parquet).

Stratum = state | district | gender. Water-filling allocation: a common per-cell cap is
raised until the total reaches --n, so no single region dominates and small cells are taken whole.
Writes data/prisma_fingerprint/hindi/sample_index.csv and prints the stratification report.

Usage: python hindi_sample.py [--n 4000] [--seed 0]
"""

import argparse
from pathlib import Path

import pandas as pd

from markers_common import clean

HIN = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint" / "hindi"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    df = pd.read_parquet(HIN / "hindi_metadata.parquet")
    print("frame rows:", len(df), "shards:", df.shard.nunique())
    df = df[df.transcript.fillna("").str.strip() != ""].copy()
    df = df[df.transcript.map(lambda t: len(clean(t)) > 0)]
    df["cell"] = df.state + "|" + df.district + "|" + df.gender
    sizes = df.cell.value_counts()
    print("usable rows:", len(df), "cells:", len(sizes))

    lo, hi = 1, int(sizes.max())
    while lo < hi:
        mid = (lo + hi) // 2
        if sizes.clip(upper=mid).sum() >= a.n:
            hi = mid
        else:
            lo = mid + 1
    cap = lo
    parts = [g.sample(n=min(len(g), cap), random_state=a.seed) for _, g in df.groupby("cell")]
    s = pd.concat(parts)
    if len(s) > a.n:  # trim the overshoot from the largest cells only
        s = s.sample(n=a.n, random_state=a.seed) if cap == 1 else (
            s.assign(r=s.groupby("cell").cumcount(ascending=False))
             .sort_values(["r"]).iloc[: a.n].drop(columns="r"))
    s = s.sort_values(["shard", "row_idx"])
    s.to_csv(HIN / "sample_index.csv", index=False)

    print(f"per-cell cap {cap}; sample {len(s)} rows, {s.cell.nunique()} cells, {s.referenceImage.nunique()} prompts")
    print("by state:\n", s.state.value_counts().to_string())
    print("by gender:\n", s.gender.value_counts().to_string())
    print("largest cells:\n", s.cell.value_counts().head(8).to_string())
    print("frame by state (for comparison):\n", df.state.value_counts().to_string())


if __name__ == "__main__":
    main()
