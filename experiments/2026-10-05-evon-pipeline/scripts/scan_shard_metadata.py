"""Read per-row metadata + audio filename (NOT audio bytes) from Vaani-transcription-part shards.

Writes a JSONL cache of (language, shard, row_idx, audio_path, meta, transcript) used by
build_shared_1k_manifest.py.  row_idx is the positional index inside the shard parquet.
"""
import json, random, sys
from concurrent.futures import ThreadPoolExecutor
import pyarrow.parquet as pq
from huggingface_hub import HfApi, HfFileSystem

REPO = "ARTPARK-IISc/Vaani-transcription-part"
TARGETS = ["Hindi", "Bhojpuri", "Maithili", "Chhattisgarhi", "Rajasthani", "Garhwali", "Khariboli", "Kumaoni"]
N_HINDI_SHARDS = 12
SEED = 20261005
out_path = sys.argv[1]

api, fs = HfApi(), HfFileSystem()
files = api.list_repo_files(REPO, repo_type="dataset")
jobs = []
for lang in TARGETS:
    shards = sorted(f for f in files if f.startswith(f"audio/{lang}/") and f.endswith(".parquet"))
    if lang == "Hindi":
        shards = sorted(random.Random(SEED).sample(shards, N_HINDI_SHARDS))
    jobs += [(lang, s) for s in shards]
print(len(jobs), "shards", flush=True)

def scan(job):
    lang, shard = job
    for attempt in range(4):
        try:
            pf = pq.ParquetFile(fs.open(f"datasets/{REPO}/{shard}", "rb"))
            names = pf.schema_arrow.names
            cols = [c for c in names if c != "audio"] + ["audio.path"]
            tb = pf.read(columns=cols).to_pylist()
            rows = []
            for i, r in enumerate(tb):
                a = r.pop("audio", None)
                path = a.get("path") if isinstance(a, dict) else None
                rows.append({"language": lang, "shard": shard, "row_idx": i, "audio_path": path,
                             "meta": {k: v for k, v in r.items() if k != "transcript"},
                             "transcript": r.get("transcript")})
            return job, rows, pf.metadata.num_rows
        except Exception as e:
            err = e
    return job, [], f"ERR {err}"

n = 0
with ThreadPoolExecutor(6) as ex, open(out_path, "w") as f:
    for job, rows, info in ex.map(scan, jobs):
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        n += len(rows)
        print(job[1], len(rows), info, flush=True)
print("total", n)
