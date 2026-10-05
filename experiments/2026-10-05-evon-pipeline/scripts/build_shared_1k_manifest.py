"""Build the ONE canonical ~1k audio manifest reused by all three Boli experiments.

Identity of a clip = (dataset, shard, row_idx), row_idx = positional index in the shard parquet.
Selection is neutral: it never looks at dialect markers, only at metadata (speaker proxy, gender,
state/district, shard, reference image, transcript length) to maximise diversity.

usage: build_shared_1k_manifest.py SCAN_JSONL AUDIO_CACHE_DIR
"""
import hashlib, io, json, random, re, sys, time, wave
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pyarrow.parquet as pq
import requests
from huggingface_hub import HfFileSystem

DATASET = "ARTPARK-IISc/Vaani-transcription-part"
TARGETS = ["Hindi", "Bhojpuri", "Maithili", "Chhattisgarhi", "Rajasthani", "Garhwali", "Khariboli", "Kumaoni"]
PER_LANG, RESERVE, SEED = 125, 25, 20261005
HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data" / "shared_1k_audio_manifest.jsonl"
PRISMA = HERE / "data" / "prisma_fingerprint"
scan_path, cache = Path(sys.argv[1]), Path(sys.argv[2]); cache.mkdir(exist_ok=True, parents=True)
fs = HfFileSystem()

PATH_RE = re.compile(r"^IISc_VaaniProject_(?P<kind>[A-Z])_(?P<state>[A-Za-z]+)_(?P<district>[^_]+)_(?P<spk>.+?)_(?:GENERIC|[A-Za-z]+-SPECIFIC)_\d+_")
TAG = re.compile(r"<[^>]*>|\[[^\]]*\]|\{[^}]*\}")
def clean_len(t): return len(re.sub(r"\s+", "", TAG.sub("", t or "")))

# ---- load scan + existing Prisma rows -------------------------------------------------------
prisma = {}
for f in PRISMA.glob("*.jsonl"):
    for l in open(f):
        r = json.loads(l)
        if r.get("prisma_transcript"):
            prisma[(r["shard"], r["row_idx"])] = r
cand = defaultdict(list)
seen_audio = set()
mism = 0
for l in open(scan_path):
    r = json.loads(l)
    if not r["audio_path"] or r["audio_path"] in seen_audio or clean_len(r["transcript"]) < 3:
        continue
    k = (r["shard"], r["row_idx"])
    if r["language"] != "Hindi":
        p = prisma.get(k)
        if not p: continue
        if p["human_transcript"].strip() != r["transcript"].strip():
            mism += 1; continue          # row_idx alignment check against the earlier Prisma pull
        r["prisma_transcript"], r["duration_sec"] = p["prisma_transcript"], p["duration_sec"]
        if r["duration_sec"] is None or r["duration_sec"] < 1.0: continue
    m = PATH_RE.search(r["audio_path"])
    r["spk"] = f'{m["kind"]}:{m["district"]}:{m["spk"]}' if m else None
    seen_audio.add(r["audio_path"])
    cand[r["language"]].append(r)
print("alignment mismatches vs earlier Prisma pull:", mism, {k: len(v) for k, v in cand.items()}, flush=True)

# ---- diversity-greedy ordering (prefix of the order is always diverse) -----------------------
def lenbin(r): n = clean_len(r["transcript"]); return 0 if n < 25 else 1 if n < 60 else 2 if n < 110 else 3
def order(rows, rng):
    rows = rows[:]; rng.shuffle(rows)
    cnt = defaultdict(Counter); chosen = []
    pool = rows
    while pool and len(chosen) < PER_LANG + RESERVE:
        sub = pool[:600]
        def score(r):
            return (1000 * cnt["spk"][r["spk"]] + 60 * cnt["img"][r["meta"].get("referenceImage")]
                    + 8 * cnt["dist"][r["meta"].get("district")] + 6 * cnt["gender"][r["meta"].get("gender")]
                    + 3 * cnt["shard"][r["shard"]] + 4 * cnt["len"][lenbin(r)] + 2 * cnt["state"][r["meta"].get("state")]
                    + rng.random())
        best = min(sub, key=score)
        chosen.append(best); pool.remove(best)
        cnt["spk"][best["spk"]] += 1; cnt["img"][best["meta"].get("referenceImage")] += 1
        cnt["dist"][best["meta"].get("district")] += 1; cnt["gender"][best["meta"].get("gender")] += 1
        cnt["shard"][best["shard"]] += 1; cnt["len"][lenbin(best)] += 1; cnt["state"][best["meta"].get("state")] += 1
    return chosen
rng = random.Random(SEED)
picked = {lang: order(cand[lang], rng) for lang in TARGETS}

# ---- fetch audio for picked rows: verify identity, hash, duration ----------------------------
def fetch_group(args):
    shard, rows = args
    pf = pq.ParquetFile(fs.open(f"datasets/{DATASET}/{shard}", "rb"))
    bounds, s = [], 0
    for i in range(pf.metadata.num_row_groups):
        n = pf.metadata.row_group(i).num_rows; bounds.append((s, s + n)); s += n
    res = {}
    by_rg = defaultdict(list)
    for r in rows:
        rg = next(i for i, (a, b) in enumerate(bounds) if a <= r["row_idx"] < b); by_rg[rg].append(r)
    for rg, rs in by_rg.items():
        tb = pf.read_row_group(rg).to_pylist()
        for r in rs:
            x = tb[r["row_idx"] - bounds[rg][0]]
            res[r["row_idx"]] = (x["audio"]["path"], x["transcript"], x["audio"]["bytes"])
    return res
groups = defaultdict(list)
for lang in TARGETS:
    for r in picked[lang]: groups[r["shard"]].append(r)
fetched = {}
with ThreadPoolExecutor(6) as ex:
    for (shard, _), res in zip(groups.items(), ex.map(fetch_group, groups.items())):
        for idx, v in res.items(): fetched[(shard, idx)] = v
print("fetched audio rows:", len(fetched), flush=True)

def prisma_call(b):
    for a in range(6):
        try:
            resp = requests.post("https://api.vachana.ai/stt/v3", files={"audio_file": ("audio.wav", b)},
                                 data={"language_code": "hi-IN", "format": "verbatim"}, timeout=60)
            if resp.status_code == 429: time.sleep(3 * (a + 1)); continue
            if resp.ok: return resp.json().get("transcript")
            return None
        except requests.RequestException: time.sleep(2 * (a + 1))
    return None

final, hashes = [], set()
for lang in TARGETS:
    ok = []
    for r in picked[lang]:
        if len(ok) >= PER_LANG: break
        path, tr, b = fetched[(r["shard"], r["row_idx"])]
        if path != r["audio_path"] or tr != r["transcript"] or not b: continue
        h = hashlib.sha256(b).hexdigest()
        if h in hashes: continue
        try:
            with wave.open(io.BytesIO(b)) as w: dur, sr = w.getnframes() / w.getframerate(), w.getframerate()
        except Exception: continue
        if dur < 1.0: continue
        r["duration_sec"], r["sr"], r["sha"], r["bytes"] = round(dur, 3), sr, h, b
        hashes.add(h); ok.append(r)
    if lang == "Hindi":
        with ThreadPoolExecutor(8) as ex: txt = list(ex.map(lambda r: prisma_call(r["bytes"]), ok))
        ok = [dict(r, prisma_transcript=t) for r, t in zip(ok, txt) if t]
        print("Hindi with Prisma transcript:", len(ok), flush=True)
    final += ok

with open(OUT, "w") as f:
    for r in final:
        m = r["meta"]; sid = hashlib.sha1(f'{DATASET}|{r["shard"]}|{r["row_idx"]}'.encode()).hexdigest()[:12]
        sid = f'{r["language"].lower()}_{sid}'
        (cache / f"{sid}.wav").write_bytes(r["bytes"])
        f.write(json.dumps({
            "sample_id": sid, "language": r["language"], "dataset": DATASET, "shard": r["shard"],
            "row_idx": r["row_idx"], "audio_path_or_locator": f'hf://datasets/{DATASET}/{r["shard"]}#row={r["row_idx"]} file={r["audio_path"]}',
            "human_transcript": r["transcript"], "prisma_transcript": r["prisma_transcript"],
            "duration_sec": r["duration_sec"], "speaker_or_source_group": r["spk"], "gender": m.get("gender"),
            "state": m.get("state"), "district": m.get("district"), "reference_image": m.get("referenceImage"),
            "audio_sha256": r["sha"], "audio_filename": r["audio_path"], "sample_rate": r["sr"]}, ensure_ascii=False) + "\n")
print("wrote", len(final), OUT)
