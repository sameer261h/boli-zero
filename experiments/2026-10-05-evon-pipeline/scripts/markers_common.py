"""Shared helpers for the marker-library phases: clean(), loaders, group-disjoint splits.

clean(text) is the single cleaning function used by every phase:
  - remove Vaani tags  <...>  [...]  {...}
  - remove punctuation and danda
  - drop nasal marks (anusvara, chandrabindu) and nukta
  - one form for digits (Devanagari -> ASCII)
  - keep Latin-script words (lower-cased)
  - split on spaces
No spelling/sound-variant handling beyond that (variant rule).
"""

import json
import random
import re
import unicodedata
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint"
OUT = Path(__file__).resolve().parent.parent / "data" / "markers"

VARIETIES = [
    "Angika", "Awadhi", "Bajjika", "Bhojpuri", "Bundeli", "Chhattisgarhi",
    "Garhwali", "Haryanvi", "Jaipuri", "Khariboli", "Khortha", "Kumaoni",
    "Magahi", "Maithili", "Marwari", "Rajasthani", "Sadri", "Surgujia",
    "Surjapuri",
]

_TAG = re.compile(r"<[^>]*>|\[[^\]]*\]|\{[^}]*\}")
_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_DROP = {"ँ", "ं", "़", "‍", "‌"}  # chandrabindu, anusvara, nukta, ZWJ, ZWNJ


def clean(text):
    t = _TAG.sub(" ", text or "")
    t = unicodedata.normalize("NFD", t).translate(_DIGITS)
    t = "".join(c for c in t if c not in _DROP)
    t = unicodedata.normalize("NFC", t)
    t = "".join(c if unicodedata.category(c)[0] in "LMN" else " " for c in t)
    return t.lower().split()


def load_jsonl(path, label=None):
    """Rows with usable Prisma text; dedup on (shard,row_idx). Returns (rows, stats)."""
    rows, seen = [], set()
    stats = {"lines": 0, "dup": 0, "error": 0, "empty_prisma": 0, "kept": 0}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        stats["lines"] += 1
        key = (r.get("shard"), r.get("row_idx"))
        if key in seen:
            stats["dup"] += 1
            continue
        seen.add(key)
        if r.get("error"):
            stats["error"] += 1
            continue
        p = clean(r.get("prisma_transcript"))
        if not p:
            stats["empty_prisma"] += 1
            continue
        m = r.get("meta") or {}
        rows.append({
            "variety": label or r["dialect"],
            "state": m.get("state") or "NA",
            "district": m.get("district") or "NA",
            "gender": m.get("gender") or "NA",
            "prompt": m.get("referenceImage") or "NA",
            "human": clean(r.get("human_transcript")),
            "prisma": p,
            "dur": r.get("duration_sec"),
            "shard": r.get("shard"),
            "row_idx": r.get("row_idx"),
        })
        stats["kept"] += 1
    return rows, stats


def load_regional():
    rows, stats = [], {}
    for v in VARIETIES:
        r, s = load_jsonl(DATA / f"{v}.jsonl", v)
        rows += r
        stats[v] = s
    return rows, stats


def group_key(r, strict=False):
    """Primary: state|district|gender|prompt (as specified). strict: without prompt."""
    k = f"{r['state']}|{r['district']}|{r['gender']}"
    return k if strict else k + "|" + r["prompt"]


def split_groups(rows, fracs=(0.6, 0.2, 0.2), seed=0, strict=False):
    """Group-disjoint train/val/test split, done separately inside every variety.
    Returns list of split labels aligned with rows."""
    rng = random.Random(seed)
    by_var = {}
    for i, r in enumerate(rows):
        by_var.setdefault(r["variety"], {}).setdefault(group_key(r, strict), []).append(i)
    label = [None] * len(rows)
    for v, groups in by_var.items():
        keys = sorted(groups)
        rng.shuffle(keys)
        n = sum(len(groups[k]) for k in keys)
        cum, names = 0, ("train", "val", "test")
        for k in keys:
            frac = cum / n
            s = names[0] if frac < fracs[0] else names[1] if frac < fracs[0] + fracs[1] else names[2]
            for i in groups[k]:
                label[i] = s
            cum += len(groups[k])
    return label
