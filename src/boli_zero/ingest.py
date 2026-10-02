"""Convert a CSV/JSONL of aligned pairs into the canonical dataset format.

    uv run python -m boli_zero.ingest data/raw/pairs.csv --anchor-language hi \
        --target-language bho --source "<where it came from>" --license "<licence>"

`--source` and `--license` are required on purpose: no data enters without both.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import unicodedata
from pathlib import Path

from pydantic import ValidationError

from .config import PROCESSED_DIR, RAW_DIR
from .schema import DatasetRecord


def read_rows(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)
    elif suffix == ".jsonl":
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)
    else:
        raise SystemExit(f"unsupported input type {suffix!r}: use .csv or .jsonl")


def make_id(anchor: str, target: str) -> str:
    text = unicodedata.normalize("NFC", f"{anchor.strip()}\x1f{target.strip()}")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def ingest(rows, *, anchor_language: str, target_language: str, source: str, license: str,
           anchor_col: str = "anchor_text", target_col: str = "target_text", id_col: str = "id",
           audio_col: str = "audio_path", speaker_col: str = "speaker_id",
           audio_root: Path | None = RAW_DIR) -> tuple[list[DatasetRecord], dict]:
    report = {"read": 0, "written": 0, "invalid": 0, "duplicates": 0, "missing_audio": 0, "errors": []}
    records: dict[str, DatasetRecord] = {}
    for row in rows:
        report["read"] += 1
        anchor, target = (row.get(anchor_col) or "").strip(), (row.get(target_col) or "").strip()
        try:
            record = DatasetRecord(
                id=(row.get(id_col) or "").strip() or make_id(anchor, target),
                anchor_language=anchor_language, target_language=target_language,
                anchor_text=anchor, target_text=target,
                audio_path=row.get(audio_col), speaker_id=row.get(speaker_col),
                source=source, license=license,
            )
        except ValidationError as error:
            report["invalid"] += 1
            if len(report["errors"]) < 5:
                report["errors"].append(f"row {report['read']}: {error.errors()[0]['loc']} {error.errors()[0]['msg']}")
            continue
        if record.id in records:
            report["duplicates"] += 1
            continue
        if record.audio_path and audio_root is not None:
            audio = Path(record.audio_path)
            if not (audio if audio.is_absolute() else audio_root / audio).exists():
                report["missing_audio"] += 1
        records[record.id] = record
    report["written"] = len(records)
    return list(records.values()), report


def write_jsonl(records, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path)
    parser.add_argument("--anchor-language", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--source", required=True, help="where the data came from")
    parser.add_argument("--license", required=True, help="licence / consent basis")
    parser.add_argument("--out", type=Path, help="default: data/processed/<input name>.jsonl")
    for name, default in (("anchor-col", "anchor_text"), ("target-col", "target_text"), ("id-col", "id"),
                          ("audio-col", "audio_path"), ("speaker-col", "speaker_id")):
        parser.add_argument(f"--{name}", default=default)
    parser.add_argument("--audio-root", type=Path, default=RAW_DIR)
    args = parser.parse_args(argv)

    records, report = ingest(
        read_rows(args.input), anchor_language=args.anchor_language, target_language=args.target_language,
        source=args.source, license=args.license, anchor_col=args.anchor_col, target_col=args.target_col,
        id_col=args.id_col, audio_col=args.audio_col, speaker_col=args.speaker_col, audio_root=args.audio_root,
    )
    out = args.out or PROCESSED_DIR / f"{args.input.stem}.jsonl"
    write_jsonl(records, out)
    print(json.dumps({"out": str(out), **report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
