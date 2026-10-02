"""Few-shot experiment runner: 0 / 10 / 25 / 50 / 100 shots, translation or rule induction.

    uv run python -m boli_zero.experiment --name first-run --dry-run   # build prompts only, no API call
    uv run python -m boli_zero.experiment --name first-run             # needs a working EvonClient

Shots come from one seeded ordering of the train split, so the 10-shot set is
contained in the 25-shot set, and so on. Differences between conditions then
reflect more examples, not different examples.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import ExitStack
from pathlib import Path

from pydantic import ValidationError

from .clients import EvonClient, NotConfigured
from .config import EXPERIMENTS_DIR, SPLITS_DIR
from .schema import DatasetRecord, GrammaticalPattern, LearnedRules, LexicalMapping, UnresolvedPattern
from .split import check_no_leakage

CONDITIONS = (0, 10, 25, 50, 100)
# Display names for prompts only; any other code is used as-is.
LANGUAGE_NAMES = {"hi": "Hindi", "bho": "Bhojpuri", "mai": "Maithili", "mag": "Magahi", "awa": "Awadhi",
                  "te": "Telugu", "ta": "Tamil", "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi",
                  "bn": "Bengali", "gu": "Gujarati"}


def load_split(path: Path) -> list[DatasetRecord]:
    return [DatasetRecord.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def shot_order(train: list[DatasetRecord], seed: int) -> list[DatasetRecord]:
    return sorted(train, key=lambda r: hashlib.sha256(f"{seed}:{r.id}".encode()).hexdigest())


def _name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


def translation_prompt(shots: list[DatasetRecord], text: str, anchor: str, target: str, script: str) -> str:
    a, t = _name(anchor), _name(target)
    lines = [f"Rewrite the {a} sentence in {t}, written in {script} script. Keep the meaning. "
             f"Reply with only the {t} sentence."]
    if shots:
        lines += ["", "Examples:"]
        for shot in shots:
            lines += [f"{a}: {shot.anchor_text}", f"{t}: {shot.target_text}", ""]
    else:
        lines.append("")
    lines += [f"{a}: {text}", f"{t}:"]
    return "\n".join(lines)


def rules_prompt(shots: list[DatasetRecord], anchor: str, target: str) -> str:
    a, t = _name(anchor), _name(target)
    lines = [
        f"You are a linguist. Below are paired {a} and {t} sentences. Infer the systematic differences "
        f"between them using only these examples, not outside knowledge of {t}.",
        "Return ONLY one JSON object with these keys:",
        '  "lexical_mappings": [{"anchor": str, "target": str, "confidence": 0-1, "supporting_example_ids": [str]}]',
        '  "grammatical_patterns": [{"category": str, "description": str, "anchor_form": str|null, '
        '"target_form": str|null, "confidence": 0-1, "supporting_example_ids": [str]}]',
        '  "unresolved_patterns": [{"description": str, "example_ids": [str]}]',
        "supporting_example_ids must be ids from the examples below. Put differences you cannot explain "
        "from the examples in unresolved_patterns.",
        "", "Examples:",
    ]
    for shot in shots:
        lines += [f"[{shot.id}] {a}: {shot.anchor_text}", f"[{shot.id}] {t}: {shot.target_text}"]
    return "\n".join(lines)


def parse_rules(text: str, *, shots: list[DatasetRecord], anchor_language: str, target_language: str) -> LearnedRules:
    """Validate model output against the rule schema. Items citing ids that were never shown are dropped and reported."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object found in model output")
    raw = json.loads(text[start:end + 1])
    if not isinstance(raw, dict):
        raise ValueError("model output JSON is not an object")
    shown = {shot.id for shot in shots}
    problems: list[str] = []

    def keep(label, model, id_attr):
        kept = []
        for index, item in enumerate(raw.get(label) or []):
            try:
                obj = model.model_validate(item)
            except ValidationError as error:
                first = error.errors()[0]
                problems.append(f"{label}[{index}] dropped: {first['loc']} {first['msg']}")
                continue
            unknown = sorted(set(getattr(obj, id_attr)) - shown)
            if unknown:
                problems.append(f"{label}[{index}] dropped: cites ids that were not shown {unknown}")
                continue
            kept.append(obj)
        return kept

    return LearnedRules(
        anchor_language=anchor_language, target_language=target_language, shots=len(shots),
        lexical_mappings=keep("lexical_mappings", LexicalMapping, "supporting_example_ids"),
        grammatical_patterns=keep("grammatical_patterns", GrammaticalPattern, "supporting_example_ids"),
        unresolved_patterns=keep("unresolved_patterns", UnresolvedPattern, "example_ids"),
        validation_problems=problems,
    )


def first_line(text: str, label: str) -> str:
    """Models sometimes add commentary or echo the 'Bhojpuri:' label; keep the first non-empty line, label removed."""
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[len(label) + 1:].strip() if line.startswith(f"{label}:") else line
    return ""


def _dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _line(handle, data: dict) -> None:
    handle.write(json.dumps(data, ensure_ascii=False) + "\n")
    handle.flush()  # partial runs stay on disk if a later call fails


def run_experiment(*, train: list[DatasetRecord], eval_records: list[DatasetRecord], run_dir: Path,
                   conditions=CONDITIONS, seed: int = 42, task: str = "translate", script: str = "Devanagari",
                   client: EvonClient | None = None, dry_run: bool = False, extra: dict | None = None) -> dict:
    pairs = {(r.anchor_language, r.target_language) for r in (*train, *eval_records)}
    if len(pairs) != 1:
        raise ValueError(f"expected exactly one (anchor, target) language pair, found {sorted(pairs)}")
    anchor, target = pairs.pop()
    if client is None and not dry_run:
        raise ValueError("a client is required unless dry_run=True")
    check_no_leakage(train, eval_records)

    ordered = shot_order(train, seed)
    active = [k for k in conditions if k <= len(ordered)]
    skipped = [k for k in conditions if k > len(ordered)]
    run_dir.mkdir(parents=True)
    (run_dir / "references.jsonl").write_text(
        "".join(json.dumps({"id": r.id, "anchor_text": r.anchor_text, "target_text": r.target_text}, ensure_ascii=False) + "\n"
                for r in eval_records), encoding="utf-8")
    config = {"task": task, "seed": seed, "anchor_language": anchor, "target_language": target, "script": script,
              "conditions_run": active, "conditions_skipped_not_enough_train": skipped,
              "n_train": len(train), "n_eval": len(eval_records), "dry_run": dry_run, "prompt_version": 1,
              **(extra or {})}
    errors: list[str] = []
    status = "failed"
    try:
        with ExitStack() as stack:
            prompts = stack.enter_context((run_dir / "prompts.jsonl").open("w", encoding="utf-8"))
            if task == "translate":
                predictions = None if dry_run else stack.enter_context((run_dir / "predictions.jsonl").open("w", encoding="utf-8"))
                for k in active:
                    for record in eval_records:
                        prompt = translation_prompt(ordered[:k], record.anchor_text, anchor, target, script)
                        _line(prompts, {"condition": k, "id": record.id, "prompt": prompt})
                        if predictions is not None:
                            raw = client.generate(prompt)
                            _line(predictions, {"condition": k, "id": record.id,
                                                "prediction": first_line(raw, _name(target)), "raw": raw})
            elif task == "rules":
                for k in (k for k in active if k > 0):
                    shots = ordered[:k]
                    prompt = rules_prompt(shots, anchor, target)
                    _line(prompts, {"condition": k, "id": None, "prompt": prompt})
                    if dry_run:
                        continue
                    raw = client.generate(prompt, max_tokens=4096)
                    (run_dir / f"rules_{k}shot.raw.txt").write_text(raw, encoding="utf-8")
                    try:
                        rules = parse_rules(raw, shots=shots, anchor_language=anchor, target_language=target)
                        _dump(run_dir / f"rules_{k}shot.json", rules.model_dump())
                    except ValueError as error:
                        errors.append(f"{k}-shot: {error}")
            else:
                raise ValueError(f"unknown task {task!r}")
        status = "dry-run" if dry_run else "complete"
    finally:
        config.update(status=status, errors=errors,
                      evon_calls=getattr(client, "calls", 0), evon_cache_hits=getattr(client, "cache_hits", 0))
        _dump(run_dir / "config.json", config)
    return config


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True, help="run folder name under experiments/")
    parser.add_argument("--task", choices=("translate", "rules"), default="translate")
    parser.add_argument("--conditions", type=int, nargs="+", default=list(CONDITIONS))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-split", choices=("validation", "test"), default="validation",
                        help="use validation while developing; touch test once for final numbers")
    parser.add_argument("--limit", type=int, help="evaluate only the first N items of the split")
    parser.add_argument("--script", default="Devanagari", help="script the target text is written in")
    parser.add_argument("--dry-run", action="store_true", help="write prompts only; make no API calls")
    parser.add_argument("--splits-dir", type=Path, default=SPLITS_DIR)
    parser.add_argument("--out-dir", type=Path, default=EXPERIMENTS_DIR)
    args = parser.parse_args(argv)

    try:
        train = load_split(args.splits_dir / "train.jsonl")
        eval_records = load_split(args.splits_dir / f"{args.eval_split}.jsonl")
    except FileNotFoundError as error:
        raise SystemExit(f"{error.filename} not found: run boli_zero.ingest and boli_zero.split first")
    if args.limit:
        eval_records = eval_records[:args.limit]
    manifest = args.splits_dir / "manifest.json"
    manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.exists() else None
    run_dir = args.out_dir / args.name
    if run_dir.exists():
        raise SystemExit(f"{run_dir} already exists: pick a new --name (cached API responses make reruns free)")

    client = None if args.dry_run else EvonClient()
    try:
        config = run_experiment(train=train, eval_records=eval_records, run_dir=run_dir, conditions=args.conditions,
                                seed=args.seed, task=args.task, script=args.script, client=client,
                                dry_run=args.dry_run, extra={"eval_split": args.eval_split, "splits_manifest_sha256": manifest_sha})
    except NotConfigured as error:
        raise SystemExit(f"{error}\nPartial output (if any) is in {run_dir}")
    print(json.dumps(config, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
