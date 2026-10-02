"""Sample catalog for the frontend: which recordings exist, their partition, and safe access to their audio.

The browser only ever names a sample by an opaque id. Audio paths come from the catalog file, never from a request,
and are checked to stay inside the configured samples folder.

    uv run python -m boli_zero.catalog build --manifest <reviewed_manifest.json> --samples-root <outputs dir> \
        --duplicates <near_duplicate_check.json> --out <catalog.json> --seed 42
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

PARTITIONS = ("development", "validation", "test")
RATIOS = {"development": 0.5, "validation": 0.25, "test": 0.25}
API_LIMIT_SECONDS = 30.0  # observed 2026-10-02; the docs say 60
SAMPLE_ID = re.compile(r"^[0-9a-f]{16}$")


def sample_id(sha256: str) -> str:
    return sha256[:16]


def _hash(seed: int, key: str) -> str:
    return hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()


def assign_partitions(groups: dict[str, list[str]], forced_development: set[str], seed: int) -> dict[str, str]:
    """Deterministic partition of GROUPS (a group stays together). Forced groups go to development first; the rest are
    ordered by hash and fill development, then validation, then test, up to the target counts."""
    total = len(groups)
    target = {"development": round(total * RATIOS["development"]), "validation": round(total * RATIOS["validation"])}
    placed = {name: 0 for name in PARTITIONS}
    result: dict[str, str] = {}
    for group, members in sorted(groups.items(), key=lambda kv: _hash(seed, kv[0])):
        if forced_development & set(members):
            name = "development"
        elif placed["development"] < target["development"]:
            name = "development"
        elif placed["validation"] < target["validation"]:
            name = "validation"
        else:
            name = "test"
        placed[name] += 1
        result[group] = name
    return result


def build_catalog(manifest: list[dict], duplicate_pairs: list[list[str]], forced_development_ids: set[str], seed: int,
                  extra_groups: dict[str, str] | None = None) -> dict:
    """extra_groups: video id -> group name, for repeated-sentence groups found after the first recognition pass."""
    by_video = {f["inferred_video_id"]: f for f in manifest}
    parent = {v: v for v in by_video}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for a, b in duplicate_pairs:
        union(a, b)
    named: dict[str, list[str]] = {}
    for video, name in (extra_groups or {}).items():
        named.setdefault(name, []).append(video)
    for members in named.values():
        for other in members[1:]:
            union(members[0], other)
    by_group: dict[str, list[str]] = {}
    for video in sorted(by_video):
        by_group.setdefault(find(video), []).append(video)
    groups = {f"group:{root}": members for root, members in by_group.items()}
    partition_of_group = assign_partitions(groups, forced_development_ids, seed)

    entries = []
    for group, members in sorted(groups.items()):
        for video in sorted(members):
            f = by_video[video]
            duplicate_excluded = f["disposition"] == "excluded_probable_audio_duplicate"
            duration = f["container_duration_seconds"]
            entries.append({
                "id": sample_id(f["sha256"]), "sha256": f["sha256"], "video_id": video, "group": group,
                "partition": partition_of_group[group], "duration_s": round(duration, 3),
                "audio_rel_path": f"{f['folder']}/{f['filename']}", "previously_inspected": video in forced_development_ids,
                "eligibility": "duplicate_excluded" if duplicate_excluded else ("eligible" if duration < API_LIMIT_SECONDS else "deferred_over_30s"),
                "reviewed_disposition": f["disposition"],
            })
    return {"seed": seed, "ratios": RATIOS, "samples": sorted(entries, key=lambda e: e["id"])}


class Catalog:
    def __init__(self, path: Path, samples_root: Path):
        self.root = Path(samples_root).resolve()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.samples = {e["id"]: e for e in data["samples"]}
        self.meta = {k: v for k, v in data.items() if k != "samples"}

    def get(self, sid: str) -> dict | None:
        return self.samples.get(sid) if SAMPLE_ID.match(sid or "") else None

    def audio_path(self, sid: str) -> Path | None:
        """The audio file for a catalogued id, or None. Never builds a path from request text."""
        entry = self.get(sid)
        if entry is None:
            return None
        path = (self.root / entry["audio_rel_path"]).resolve()
        return path if path.is_file() and path.is_relative_to(self.root) else None

    def public(self, entry: dict, position: int) -> dict:
        """What the browser may see: no file names, no paths, no video ids."""
        return {k: entry[k] for k in ("id", "partition", "duration_s", "eligibility", "previously_inspected")} | {"label": f"Clip {position:03d}"}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--manifest", type=Path, required=True)
    b.add_argument("--duplicates", type=Path, required=True)
    b.add_argument("--forced-development", type=Path, required=True, help="JSON list of video ids that were already inspected")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))["files"]
    dup = json.loads(args.duplicates.read_text(encoding="utf-8"))["sources"]
    video = lambda path: re.search(r"\[([^\]]+)\]\.mp3$", path).group(1)
    catalog = build_catalog(manifest, [[video(dup[0]), video(dup[1])]], set(json.loads(args.forced_development.read_text())), args.seed)
    args.out.write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({p: sum(e["partition"] == p for e in catalog["samples"]) for p in PARTITIONS}))


if __name__ == "__main__":
    main()
