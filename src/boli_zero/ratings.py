"""Blinded pairwise sheets for native-speaker ratings, and aggregation of the filled sheets.

    uv run python -m boli_zero.ratings export experiments/first-run --a 0 --b 25 -n 50 --out outputs/ratings
    # each rater fills the `choice` column of their own copy: 1, 2, tie or both_bad
    uv run python -m boli_zero.ratings aggregate outputs/ratings/key.json outputs/ratings/rater_*.csv

Systems are condition numbers from the run ("0", "25") or "reference" (the human reference text).
Raters see two anonymous options in a deterministic, seeded random order.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from .evaluate import read_jsonl
from .schema import RatingRecord


def _outputs(run_dir: Path, system: str, refs: dict[str, dict]) -> dict[str, str]:
    if system == "reference":
        return {i: r["target_text"] for i, r in refs.items()}
    return {row["id"]: row["prediction"] for row in read_jsonl(run_dir / "predictions.jsonl")
            if str(row["condition"]) == system}


def export_sheet(run_dir: Path, system_a: str, system_b: str, n: int, seed: int, out_dir: Path) -> Path:
    refs = {row["id"]: row for row in read_jsonl(run_dir / "references.jsonl")}
    a, b = _outputs(run_dir, system_a, refs), _outputs(run_dir, system_b, refs)
    ids = sorted(set(a) & set(b), key=lambda i: hashlib.sha256(f"{seed}:{i}".encode()).hexdigest())[:n]
    if not ids:
        raise ValueError(f"no items have outputs for both {system_a!r} and {system_b!r}")

    out_dir.mkdir(parents=True, exist_ok=True)
    key, rows = {}, []
    for item in ids:
        swapped = hashlib.sha256(f"{seed}:{item}:swap".encode()).digest()[0] % 2 == 1
        first, second = (system_b, system_a) if swapped else (system_a, system_b)
        texts = {system_a: a[item], system_b: b[item]}
        key[item] = [first, second]
        rows.append({"item_id": item, "anchor_text": refs[item]["anchor_text"],
                     "option_1": texts[first], "option_2": texts[second], "choice": "", "notes": ""})
    (out_dir / "key.json").write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    sheet = out_dir / "sheet_blank.csv"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return sheet


def aggregate(key_path: Path, sheets: list[Path]) -> dict:
    key = json.loads(key_path.read_text(encoding="utf-8"))
    wins, ties, both_bad, per_rater = Counter(), 0, 0, {}
    for sheet in sheets:
        rater = sheet.stem
        with sheet.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if not (row.get("choice") or "").strip():
                    continue  # unrated
                try:
                    record = RatingRecord(item_id=row["item_id"], rater_id=rater, choice=row["choice"].strip().lower(),
                                          notes=row.get("notes") or "")
                except ValidationError as error:
                    raise ValueError(f"{sheet.name}: bad choice for item {row.get('item_id')}: {row.get('choice')!r}") from error
                per_rater[rater] = per_rater.get(rater, 0) + 1
                if record.choice == "tie":
                    ties += 1
                elif record.choice == "both_bad":
                    both_bad += 1
                else:
                    wins[key[record.item_id][int(record.choice) - 1]] += 1
    decided = sum(wins.values())
    return {"ratings_per_rater": per_rater, "wins": dict(wins), "ties": ties, "both_bad": both_bad,
            "win_share_excluding_ties": {s: round(c / decided, 4) for s, c in wins.items()} if decided else {},
            "note": "counts only: with 2-3 raters add agreement and confidence intervals before claiming anything"}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("run_dir", type=Path)
    export.add_argument("--a", required=True, help="system A: condition number or 'reference'")
    export.add_argument("--b", required=True)
    export.add_argument("-n", type=int, default=50)
    export.add_argument("--seed", type=int, default=42)
    export.add_argument("--out", type=Path, required=True)
    agg = sub.add_parser("aggregate")
    agg.add_argument("key", type=Path)
    agg.add_argument("sheets", nargs="+", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.command == "export":
            print(f"wrote {export_sheet(args.run_dir, args.a, args.b, args.n, args.seed, args.out)} and key.json "
                  "(copy the sheet once per rater; keep key.json away from raters)")
        else:
            print(json.dumps(aggregate(args.key, args.sheets), indent=2, ensure_ascii=False))
    except (ValueError, FileNotFoundError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
