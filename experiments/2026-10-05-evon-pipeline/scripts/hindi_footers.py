"""Phase 2a: read parquet footers + non-audio columns of Vaani Hindi shards by HTTP range.

No audio is downloaded. Writes data/prisma_fingerprint/hindi/footer_report.json and
hindi_metadata.parquet (one row per clip: shard, row_idx, metadata, transcript).

Usage: python hindi_footers.py [--limit N]
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import io

import requests
import pandas as pd
import pyarrow.parquet as pq
from huggingface_hub import HfApi

REPO = "ARTPARK-IISc/Vaani-transcription-part"
OUT = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint" / "hindi"


class RangeFile(io.RawIOBase):
    """Seekable read-only file over HTTP range requests (follows the HF CDN redirect once)."""

    def __init__(self, url):
        self.url, self.pos = url, 0
        r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=60)
        r.raise_for_status()
        self.url = r.url  # signed CDN URL
        self.size = int(r.headers["Content-Range"].split("/")[1])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def _get(self, start, end):
        for attempt in range(4):
            try:
                r = requests.get(self.url, headers={"Range": f"bytes={start}-{end}"}, timeout=120)
                if r.status_code in (200, 206):
                    return r.content
            except requests.RequestException:
                pass
        raise IOError(f"range {start}-{end} failed")

    def read(self, n=-1):
        if n < 0 or self.pos + n > self.size:
            n = self.size - self.pos
        if n <= 0:
            return b""
        data = self._get(self.pos, self.pos + n - 1)
        self.pos += len(data)
        return data

    def readinto(self, b):
        d = self.read(len(b))
        b[: len(d)] = d
        return len(d)


def shard_url(path):
    return f"https://huggingface.co/datasets/{REPO}/resolve/main/{path}"


def read_shard(path):
    fh = RangeFile(shard_url(path))
    if True:
        pf = pq.ParquetFile(fh)
        names = pf.schema_arrow.names
        schema = {n: str(pf.schema_arrow.field(n).type) for n in names}
        n = pf.metadata.num_rows
        cols = [c for c in names if "audio" not in c.lower()]
        df = pf.read(columns=cols).to_pandas()
    df.insert(0, "row_idx", range(len(df)))
    df.insert(0, "shard", path)
    return {"path": path, "rows": n, "schema": schema}, df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    files = sorted(
        f for f in HfApi().list_repo_files(REPO, repo_type="dataset")
        if f.startswith("audio/Hindi/") and f.endswith(".parquet")
    )
    if args.limit:
        files = files[: args.limit]
    print(f"{len(files)} Hindi shards")

    infos, frames, failed = [], [], []

    def work(p):
        try:
            return read_shard(p)
        except Exception as e:
            return {"path": p, "error": f"{type(e).__name__}: {e}"[:300]}, None

    with ThreadPoolExecutor(args.workers) as ex:
        for i, (info, df) in enumerate(ex.map(work, files), 1):
            if df is None:
                failed.append(info)
            else:
                infos.append(info)
                frames.append(df)
            if i % 25 == 0:
                print(f"  {i}/{len(files)} shards", flush=True)

    meta = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    meta.to_parquet(OUT / "hindi_metadata.parquet")
    report = {
        "shards_ok": len(infos),
        "shards_failed": failed,
        "total_rows": int(sum(i["rows"] for i in infos)),
        "schema_example": infos[0]["schema"] if infos else None,
        "schemas_identical": len({json.dumps(i["schema"], sort_keys=True) for i in infos}) <= 1,
        "rows_by_split": {
            s: int(sum(i["rows"] for i in infos if f"/{s}-" in i["path"]))
            for s in ("train", "validation", "test")
        },
    }
    (OUT / "footer_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
