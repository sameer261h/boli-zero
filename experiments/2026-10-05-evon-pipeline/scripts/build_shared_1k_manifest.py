"""Build the ONE canonical ~1k-clip sample manifest shared by the three Boli
representation experiments (Prisma/grammar, Allosaurus phonotactics,
IndicWav2Vec embeddings). Run once; the output is frozen and must not be
regenerated/resampled afterwards (the script refuses to overwrite it).

Source: gated ARTPARK-IISc/Vaani-transcription-part (same access as
prisma_fingerprint_pull.py). No audio is copied -- only locators + metadata.
`dataset + shard + row_idx` identifies the exact clip (row_idx = positional
row in that parquet shard, same convention as prisma_fingerprint/*.jsonl).

Sampling (neutral -- transcript content is never inspected for markers):
  * Regional targets: candidate pool = rows already in prisma_fingerprint/
    (so a Prisma transcript exists for the grammar arm). Hindi: all rows of
    the Hindi shards; prisma_transcript = null.
  * Drop: duration < 1.0 s, empty/noise-only transcripts, duplicate
    (shard,row_idx), duplicate normalized human transcript, duplicate audio
    bytes hash (Hindi; regional pool hashed when audio is downloaded).
  * Diversity: round-robin across source groups (state|district|gender --
    Vaani exposes no speaker id), with a per-(group, reference image) cap of
    1, so no single group or prompt image dominates; within a group, rows
    are drawn in seeded random order.
"""

import hashlib
import json
import random
import re
import wave
import io
from collections import defaultdict
from pathlib import Path

import pandas as pd
from huggingface_hub import HfApi, hf_hub_download

REPO = "ARTPARK-IISc/Vaani-transcription-part"
TARGETS = ["Hindi", "Bhojpuri", "Maithili", "Chhattisgarhi", "Rajasthani", "Garhwali", "Khariboli", "Kumaoni"]
PER_TARGET = 125
SEED = 20261005
MIN_DUR = 1.0

ROOT = Path(__file__).resolve().parent.parent / "data"
PF_DIR = ROOT / "prisma_fingerprint"
OUT = ROOT / "shared_1k_audio_manifest.jsonl"

TAG_RE = re.compile(r"<[^>]+>|\[[^\]]+\]")


def norm_text(t):
    t = TAG_RE.sub(" ", t or "")
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def wav_dur(b):
    try:
        with wave.open(io.BytesIO(b), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return None


def regional_pool(lang):
    rows = []
    with open(PF_DIR / f"{lang}.jsonl") as f:
        for line in f:
            r = json.loads(line)
            if r.get("error") or not (r.get("prisma_transcript") or "").strip():
                continue
            m = r.get("meta", {})
            rows.append({
                "shard": r["shard"], "row_idx": r["row_idx"],
                "human_transcript": r["human_transcript"],
                "prisma_transcript": r["prisma_transcript"],
                "duration_sec": r.get("duration_sec"),
                "gender": m.get("gender"), "state": m.get("state"),
                "district": m.get("district"), "reference_image": m.get("referenceImage"),
            })
    return rows


def hindi_pool(api):
    files = sorted(f for f in api.list_repo_files(REPO, repo_type="dataset")
                   if "/Hindi/" in f and f.endswith(".parquet"))
    rows = []
    for f in files:
        df = pd.read_parquet(hf_hub_download(REPO, f, repo_type="dataset"))
        for i in range(len(df)):
            r = df.iloc[i]
            text = r.get("transcript")
            a = r.get("audio")
            b = a["bytes"] if isinstance(a, dict) else a
            if text is None or not str(text).strip() or not b:
                continue
            rows.append({
                "shard": f, "row_idx": i, "human_transcript": str(text).strip(),
                "prisma_transcript": None, "duration_sec": wav_dur(b),
                "gender": r.get("gender"), "state": r.get("state"),
                "district": r.get("district"), "reference_image": r.get("referenceImage"),
                "audio_sha1": hashlib.sha1(b).hexdigest(),
            })
    return rows


def sample(rows, n, rng):
    seen_key, seen_text, seen_hash = set(), set(), set()
    groups = defaultdict(list)
    for r in rows:
        k = (r["shard"], r["row_idx"])
        nt = norm_text(r["human_transcript"])
        if k in seen_key or not nt or (r["duration_sec"] or 0) < MIN_DUR:
            continue
        if nt in seen_text or (r.get("audio_sha1") and r["audio_sha1"] in seen_hash):
            continue
        seen_key.add(k); seen_text.add(nt)
        if r.get("audio_sha1"):
            seen_hash.add(r["audio_sha1"])
        r["speaker_or_source_group"] = f"{r['state']}|{r['district']}|{r['gender']}"
        groups[r["speaker_or_source_group"]].append(r)
    for g in groups.values():
        rng.shuffle(g)
    order = sorted(groups)
    rng.shuffle(order)
    picked, used_img = [], set()
    while len(picked) < n and any(groups[g] for g in order):
        for g in order:
            while groups[g]:
                r = groups[g].pop()
                key = (g, r["reference_image"])
                if key in used_img:
                    continue  # same group + same prompt image: near-duplicate risk
                used_img.add(key)
                picked.append(r)
                break
            if len(picked) >= n:
                break
        else:
            # every group exhausted its unique images; relax nothing further
            if not any(groups[g] for g in order):
                break
    return picked


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists and is FROZEN -- refusing to resample.")
    rng = random.Random(SEED)
    api = HfApi()
    out = []
    for lang in TARGETS:
        pool = hindi_pool(api) if lang == "Hindi" else regional_pool(lang)
        picked = sample(pool, PER_TARGET, rng)
        print(f"{lang}: pool={len(pool)} picked={len(picked)} groups={len({p['speaker_or_source_group'] for p in picked})}")
        for p in sorted(picked, key=lambda r: (r["shard"], r["row_idx"])):
            shard_tag = p["shard"].split("/")[-1].replace(".parquet", "")
            out.append({
                "sample_id": f"vaani:{lang}:{shard_tag}:{p['row_idx']}",
                "language": lang,
                "dataset": REPO,
                "shard": p["shard"],
                "row_idx": int(p["row_idx"]),
                "audio_path_or_locator": f"hf://datasets/{REPO}/{p['shard']}#row={int(p['row_idx'])}",
                "human_transcript": p["human_transcript"],
                "prisma_transcript": p["prisma_transcript"],
                "duration_sec": round(p["duration_sec"], 3) if p["duration_sec"] else None,
                "speaker_or_source_group": p["speaker_or_source_group"],
                "gender": p["gender"], "state": p["state"], "district": p["district"],
                "reference_image": p["reference_image"],
            })
    with open(OUT, "w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} rows -> {OUT}")


if __name__ == "__main__":
    main()
