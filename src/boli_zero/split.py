"""Deterministic train/validation/test split.

    uv run python -m boli_zero.split --seed 42 --train 0.8 --validation 0.1 --test 0.1

Rows are ordered by sha256(seed:group), then filled train -> validation -> test up to
the requested counts. The result does not depend on input row order, so re-running
on the same data and seed gives byte-identical files.
Default grouping is by anchor sentence: every rendering of one Hindi sentence lands in the same split,
so a held-out sentence can never have a sibling rendering in train (that would leak the answer into
few-shot examples and retrieval). Use --group-by speaker_id to hold out whole speakers instead.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from .cache import sha256_hex
from .config import PROCESSED_DIR, SPLITS_DIR
from .schema import DatasetRecord

SPLITS = ("train", "validation", "test")


def load_records(paths: list[Path]) -> tuple[list[DatasetRecord], int]:
    records: dict[str, DatasetRecord] = {}
    duplicates = 0
    for path in sorted(paths):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = DatasetRecord.model_validate_json(line)
                if record.id in records:
                    duplicates += 1
                else:
                    records[record.id] = record
    return list(records.values()), duplicates


def assign_splits(records: list[DatasetRecord], *, seed: int, train: float, validation: float,
                  group_by: str = "anchor_text") -> list[DatasetRecord]:
    groups: dict[str, list[DatasetRecord]] = defaultdict(list)
    for record in records:
        key = getattr(record, group_by) or record.id  # rows without a speaker are their own group
        groups[key].append(record)
    order = sorted(groups, key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest())

    total = len(records)
    target = {"train": round(total * train), "validation": round(total * validation)}
    counts = dict.fromkeys(SPLITS, 0)
    assigned = []
    for key in order:
        if counts["train"] < target["train"]:
            name = "train"
        elif counts["validation"] < target["validation"]:
            name = "validation"
        else:
            name = "test"
        counts[name] += len(groups[key])
        # ponytail: groups larger than one row can overshoot the ratios; exact only when every group has one row.
        assigned.extend(record.model_copy(update={"split": name}) for record in groups[key])
    return assigned


def check_no_leakage(teaching_pool: list[DatasetRecord], held_out: list[DatasetRecord]) -> None:
    """Raise if anything that may be shown to the model (shots, retrieval index) overlaps what it is scored on.

    Call this before every experiment. Checks split labels plus shared ids, anchor sentences and target sentences.
    """
    problems = []
    if any(r.split != "train" for r in teaching_pool):
        problems.append("teaching pool contains records whose split is not 'train'")
    if any(r.split not in ("validation", "test") for r in held_out):
        problems.append("held-out set contains records whose split is not 'validation' or 'test'")
    for field in ("id", "anchor_text", "target_text"):
        shared = {getattr(r, field) for r in teaching_pool} & {getattr(r, field) for r in held_out}
        if shared:
            problems.append(f"{len(shared)} shared {field} value(s), e.g. {sorted(shared)[0]!r}")
    if problems:
        raise ValueError("train/held-out leakage: " + "; ".join(problems))


def write_splits(records: list[DatasetRecord], out_dir: Path, manifest: dict) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name in SPLITS:
        rows = sorted((r for r in records if r.split == name), key=lambda r: r.id)
        counts[name] = len(rows)
        (out_dir / f"{name}.jsonl").write_text("".join(r.model_dump_json() + "\n" for r in rows), encoding="utf-8")
    manifest = {**manifest, "counts": counts}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="*", type=Path, help="default: every file in data/processed")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train", type=float, default=0.8)
    parser.add_argument("--validation", type=float, default=0.1)
    parser.add_argument("--test", type=float, default=0.1)
    parser.add_argument("--group-by", choices=("anchor_text", "id", "speaker_id"), default="anchor_text")
    parser.add_argument("--out", type=Path, default=SPLITS_DIR)
    args = parser.parse_args(argv)

    if abs(args.train + args.validation + args.test - 1) > 1e-9:
        raise SystemExit("--train, --validation and --test must sum to 1")
    inputs = args.inputs or sorted(PROCESSED_DIR.glob("*.jsonl"))
    if not inputs:
        raise SystemExit("no input files: run boli_zero.ingest first")

    records, duplicates = load_records(inputs)
    assigned = assign_splits(records, seed=args.seed, train=args.train, validation=args.validation,
                             group_by=args.group_by)
    manifest = write_splits(assigned, args.out, {
        "seed": args.seed, "ratios": [args.train, args.validation, args.test], "group_by": args.group_by,
        "duplicates_dropped": duplicates,
        "inputs": {path.name: sha256_hex(path.read_bytes()) for path in inputs},
    })
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    if manifest["counts"]["test"] == 0 or manifest["counts"]["validation"] == 0:
        print("warning: validation or test split is empty; the dataset is too small for these ratios")


if __name__ == "__main__":
    main()
