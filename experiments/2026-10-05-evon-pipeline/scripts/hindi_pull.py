"""Phase 2c: run the sampled Hindi clips through Prisma, writing Hindi.jsonl in the regional schema.

Request settings and rate-limit handling are the SAME code as the regional pull
(prisma_fingerprint_pull.call_prisma: hi-IN, verbatim, 8 retries, 429 backoff).
Only the sampled rows' row groups are downloaded (HTTP range). Resumable: rows already
written without error are skipped. Counts every HTTP call and status code.

Usage: python hindi_pull.py [--concurrency 8] [--limit N]
"""

import argparse
import io
import json
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import requests

import prisma_fingerprint_pull as pull
from hindi_footers import RangeFile, shard_url
from markers_common import DATA, clean

HIN = DATA / "hindi"
OUT = DATA / "Hindi.jsonl"

CALLS, STATUS, LOCK = Counter(), Counter(), threading.Lock()
_orig_post = requests.post


def counting_post(*args, **kw):
    try:
        r = _orig_post(*args, **kw)
        with LOCK:
            CALLS["http_calls"] += 1
            STATUS[r.status_code] += 1
        return r
    except requests.RequestException as e:
        with LOCK:
            CALLS["http_calls"] += 1
            STATUS[type(e).__name__] += 1
        raise


requests.post = counting_post


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()

    sample = pd.read_csv(HIN / "sample_index.csv")
    if a.limit:
        sample = sample.head(a.limit)
    done = set()
    if OUT.exists():
        for line in open(OUT, encoding="utf-8"):
            r = json.loads(line)
            if not r.get("error"):
                done.add((r["shard"], r["row_idx"]))
    sample = sample[[(s, i) not in done for s, i in zip(sample.shard, sample.row_idx)]]
    print(f"{len(sample)} clips to do ({len(done)} already done)", flush=True)

    n_done = n_err = 0
    with open(OUT, "a", encoding="utf-8") as out, ThreadPoolExecutor(a.concurrency) as pool:
        for shard, grp in sample.groupby("shard"):
            fh = RangeFile(shard_url(shard))
            pf = pq.ParquetFile(fh)
            starts, acc = [], 0
            for g in range(pf.num_row_groups):
                starts.append(acc)
                acc += pf.metadata.row_group(g).num_rows
            starts.append(acc)
            want = {int(r): row for r, row in zip(grp.row_idx, grp.itertuples())}
            jobs = []
            for g in range(pf.num_row_groups):
                idxs = [i for i in want if starts[g] <= i < starts[g + 1]]
                if not idxs:
                    continue
                t = pf.read_row_group(g, columns=["audio"]).to_pandas()
                for i in idxs:
                    au = t.audio.iloc[i - starts[g]]
                    jobs.append((i, au["bytes"] if isinstance(au, dict) else au))

            def work(job):
                i, audio = job
                w = want[i]
                res = pull.call_prisma(audio)
                res.pop("raw", None)
                rec = {
                    "dialect": "Hindi", "shard": shard, "row_idx": i,
                    "human_transcript": w.transcript,
                    "duration_sec": pull.wav_duration_seconds(audio),
                    "meta": {"language": "Hindi", "gender": w.gender, "state": w.state,
                             "district": w.district, "referenceImage": w.referenceImage},
                    **res,
                }
                rec["human_clean"] = clean(w.transcript)
                rec["prisma_clean"] = clean(rec.get("prisma_transcript"))
                return rec

            for fut in as_completed([pool.submit(work, j) for j in jobs]):
                rec = fut.result()
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                n_done += 1
                n_err += bool(rec.get("error"))
            print(f"  {shard}: total {n_done} done, {n_err} errors, http {dict(CALLS)} {dict(STATUS)}", flush=True)

    summary = {"clips_processed": n_done, "errors": n_err, "http_calls": CALLS["http_calls"],
               "status_counts": {str(k): v for k, v in STATUS.items()}}
    (HIN / "pull_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
