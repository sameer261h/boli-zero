"""Prisma-fingerprint feasibility pull.

For each of 6 well-resourced dialects (Bhojpuri, Magahi, Maithili, Bajjika,
Chhattisgarhi, Garhwali), pull real audio + human transcripts from the gated
ARTPARK-IISc/Vaani-transcription-part dataset, run each clip through Prisma
(hi-IN, verbatim), and save human-vs-Prisma transcript pairs for later
pattern analysis. No audio is re-hosted — only text + metadata is written
to disk/committed, per project policy.

Two modes:

  discover   -- download all available shards per dialect, count usable rows
                (has both audio and a non-empty transcript), no Prisma calls.
                Cheap, use this first to size the job against the credit budget.

  transcribe -- actually call Prisma for up to --per-dialect rows per dialect
                (or all available rows if fewer), with bounded concurrency.
                Writes experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/
                <dialect>.jsonl incrementally (safe to interrupt/resume).

Usage:
  python prisma_fingerprint_pull.py discover
  python prisma_fingerprint_pull.py transcribe --per-dialect 1500 --concurrency 16
"""

import argparse
import io
import json
import time
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from huggingface_hub import HfApi, hf_hub_download

REPO = "ARTPARK-IISc/Vaani-transcription-part"

# All 19 dialects confirmed to have transcript files in Vaani-transcription-part
# (per derive_markers_multi.py's multi_dialect_markers.json). Ordered smallest
# target first, so an interrupted overnight run still touches every dialect
# instead of leaving the ones at the end of the list untouched.
DIALECTS = [
    "Jaipuri", "Haryanvi", "Awadhi", "Surjapuri", "Bundeli", "Surgujia",
    "Angika", "Sadri", "Bajjika", "Khariboli", "Khortha", "Magahi",
    "Kumaoni", "Marwari", "Garhwali", "Rajasthani", "Maithili",
    "Chhattisgarhi", "Bhojpuri",
]

# Caps summing to ~24,000 total calls, staying under the ~25,000-call
# estimate for a 5000-credit Gnani budget (web/index.html: "about ₹0.2 of
# programme credits" per Prisma STT call). From the 2026-10-04 discover run
# across all 19 dialects (69,138 usable rows total): the 9 smallest dialects
# (<=1200 available) take 100% of their population (only ~4,157 calls total,
# since they're small anyway -- a flat proportional split would've left them
# at ~30-70 samples each, too thin to find real patterns in). The remaining
# ~19,843 budget is split proportionally across the 10 larger dialects.
DEFAULT_PER_DIALECT_CAPS = {
    "Bhojpuri": 4316,
    "Chhattisgarhi": 3596,
    "Maithili": 3264,
    "Rajasthani": 2472,
    "Garhwali": 1800,
    "Marwari": 1462,
    "Magahi": 866,
    "Khortha": 804,
    "Bajjika": 705,
    "Angika": 559,
    "Kumaoni": 1142,   # 100% of availability
    "Sadri": 685,      # 100%
    "Khariboli": 718,  # 100%
    "Surgujia": 529,   # 100%
    "Bundeli": 447,    # 100%
    "Surjapuri": 197,  # 100%
    "Awadhi": 187,     # 100%
    "Haryanvi": 165,   # 100%
    "Jaipuri": 87,     # 100%
}

GNANI_URL = "https://api.vachana.ai/stt/v3"
GNANI_LANGUAGE = "hi-IN"
GNANI_FORMAT = "verbatim"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint"
MANIFEST_PATH = OUT_DIR / "discover_manifest.json"


def list_dialect_files(api, dialect):
    files = api.list_repo_files(REPO, repo_type="dataset")
    return sorted(f for f in files if f"/{dialect}/" in f and f.endswith(".parquet"))


def find_text_col(df):
    for c in df.columns:
        lc = c.lower()
        if "transcript" in lc or lc == "text":
            return c
    return None


def find_audio_col(df):
    for c in df.columns:
        if "audio" in c.lower():
            return c
    return None


def iter_rows(df, text_col, audio_col):
    for i in range(len(df)):
        row = df.iloc[i]
        text = row[text_col]
        if text is None or (isinstance(text, float)) or not str(text).strip():
            continue
        audio = row[audio_col]
        audio_bytes = audio["bytes"] if isinstance(audio, dict) else audio
        if not audio_bytes:
            continue
        meta = {c: row[c] for c in df.columns if c not in (text_col, audio_col)}
        meta = {k: (v.item() if hasattr(v, "item") else v) for k, v in meta.items()}
        yield i, str(text).strip(), audio_bytes, meta


def discover():
    # No explicit token: this environment's egress proxy injects the real
    # HF auth header transparently for requests to huggingface.co / *.hf.co.
    api = HfApi()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {}
    for dialect in DIALECTS:
        files = list_dialect_files(api, dialect)
        print(f"=== {dialect}: {len(files)} shard files ===")
        total_rows = 0
        shard_info = []
        for f in files:
            path = hf_hub_download(REPO, f, repo_type="dataset")
            df = pd.read_parquet(path)
            text_col = find_text_col(df)
            audio_col = find_audio_col(df)
            usable = sum(
                1
                for _ in iter_rows(df, text_col, audio_col)
                if text_col and audio_col
            ) if text_col and audio_col else 0
            print(f"  {f}: {len(df)} rows, text_col={text_col}, audio_col={audio_col}, usable={usable}")
            shard_info.append({"file": f, "rows": len(df), "usable": usable, "text_col": text_col, "audio_col": audio_col})
            total_rows += usable
        manifest[dialect] = {"total_usable_rows": total_rows, "shards": shard_info}
        print(f"  -> {dialect} total usable rows: {total_rows}\n")

    with open(MANIFEST_PATH, "w") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    grand_total = sum(d["total_usable_rows"] for d in manifest.values())
    print(f"\nGRAND TOTAL usable rows across {len(DIALECTS)} dialects: {grand_total}")
    print(f"Manifest written to {MANIFEST_PATH}")


def wav_duration_seconds(audio_bytes):
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return None


def call_prisma(audio_bytes, max_retries=8):
    # No explicit API key header: this environment's egress proxy injects
    # the real X-API-Key-ID header transparently for requests to api.vachana.ai.
    import random

    import requests

    for attempt in range(max_retries):
        start = time.time()
        try:
            resp = requests.post(
                GNANI_URL,
                files={"audio_file": ("audio.wav", audio_bytes)},
                data={"language_code": GNANI_LANGUAGE, "format": GNANI_FORMAT},
                timeout=60,
            )
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                return {"error": f"request_exception: {e}", "latency_sec": round(time.time() - start, 2)}
            time.sleep(min(30, 2 * (attempt + 1)) + random.uniform(0, 1))
            continue
        latency = time.time() - start
        if resp.status_code == 429:
            if attempt == max_retries - 1:
                return {"error": "exhausted_retries_429", "latency_sec": round(latency, 2)}
            time.sleep(min(30, 3 * (attempt + 1)) + random.uniform(0, 1))
            continue
        if not resp.ok:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}", "latency_sec": round(latency, 2)}
        try:
            data = resp.json()
        except Exception:
            return {"error": f"bad_json: {resp.text[:500]}", "latency_sec": round(latency, 2)}
        return {"prisma_transcript": data.get("transcript"), "raw": data, "latency_sec": round(latency, 2)}
    return {"error": "exhausted_retries"}


def transcribe_dialect(dialect, per_dialect_target, concurrency):
    out_path = OUT_DIR / f"{dialect}.jsonl"
    already_done = set()
    if out_path.exists():
        with open(out_path) as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                    if not rec.get("error"):  # only successful rows count as done; failures get retried
                        already_done.add((rec["shard"], rec["row_idx"]))
                except Exception:
                    pass
        print(f"  {dialect}: resuming, {len(already_done)} rows already succeeded")

    api = HfApi()
    files = list_dialect_files(api, dialect)

    jobs = []
    for f in files:
        if len(jobs) >= per_dialect_target:
            break
        path = hf_hub_download(REPO, f, repo_type="dataset")
        df = pd.read_parquet(path)
        text_col = find_text_col(df)
        audio_col = find_audio_col(df)
        if not text_col or not audio_col:
            continue
        for row_idx, text, audio_bytes, meta in iter_rows(df, text_col, audio_col):
            if (f, row_idx) in already_done:
                continue
            jobs.append((f, row_idx, text, audio_bytes, meta))
            if len(jobs) >= per_dialect_target:
                break

    print(f"  {dialect}: {len(jobs)} new clips to transcribe (target {per_dialect_target})")

    def process(job):
        shard, row_idx, human_text, audio_bytes, meta = job
        result = call_prisma(audio_bytes)
        record = {
            "dialect": dialect,
            "shard": shard,
            "row_idx": row_idx,
            "human_transcript": human_text,
            "duration_sec": wav_duration_seconds(audio_bytes),
            "meta": meta,
            **result,
        }
        record.pop("raw", None)  # keep file lean; raw kept only transiently for debugging if needed
        return record

    done = 0
    errors = 0
    with open(out_path, "a") as out_fh, ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(process, job): job for job in jobs}
        for fut in as_completed(futures):
            rec = fut.result()
            out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_fh.flush()
            done += 1
            if rec.get("error"):
                errors += 1
            if done % 50 == 0:
                print(f"  {dialect}: {done}/{len(jobs)} done ({errors} errors so far)")

    print(f"  {dialect}: finished. {done} processed, {errors} errors. -> {out_path}")
    return done, errors


def transcribe(per_dialect_target, concurrency):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    grand_done, grand_errors = 0, 0
    for dialect in DIALECTS:
        target = per_dialect_target if per_dialect_target is not None else DEFAULT_PER_DIALECT_CAPS[dialect]
        print(f"=== {dialect} (target {target}) ===")
        d, e = transcribe_dialect(dialect, target, concurrency)
        grand_done += d
        grand_errors += e

    print(f"\nGRAND TOTAL: {grand_done} clips transcribed, {grand_errors} errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("discover")
    p_t = sub.add_parser("transcribe")
    p_t.add_argument(
        "--per-dialect",
        type=int,
        default=None,
        help="Uniform cap per dialect. Omit to use the proportional DEFAULT_PER_DIALECT_CAPS (~24k total).",
    )
    p_t.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    if args.mode == "discover":
        discover()
    else:
        transcribe(args.per_dialect, args.concurrency)
