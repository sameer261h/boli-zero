"""Score a finished experiment run against held-out references.

    uv run python -m boli_zero.evaluate experiments/first-run

Reports per condition: mean chrF, exact-match rate, and copy rate (the model returned the
anchor sentence unchanged). Also reports an identity baseline: the score you get by doing nothing
(output = the Hindi input). A system that cannot beat that has learned nothing.
Manual native-speaker ratings are handled in boli_zero.ratings.
"""
from __future__ import annotations

import argparse
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip()


def _ngrams(text: str, n: int) -> Counter:
    squashed = "".join(text.split())
    return Counter(squashed[i:i + n] for i in range(len(squashed) - n + 1))


def chrf(hypothesis: str, reference: str, max_n: int = 6, beta: float = 2.0) -> float:
    """Character n-gram F-score on a 0-100 scale (whitespace ignored).

    ponytail: approximates sacreBLEU's chrF (orders 1-6, beta 2) without its edge-case handling.
    Compare numbers only within this project, or swap in sacrebleu if results are published.
    """
    hypothesis, reference = _nfc(hypothesis), _nfc(reference)
    precisions, recalls = [], []
    for n in range(1, max_n + 1):
        hyp, ref = _ngrams(hypothesis, n), _ngrams(reference, n)
        if not hyp or not ref:
            continue
        overlap = sum((hyp & ref).values())
        precisions.append(overlap / sum(hyp.values()))
        recalls.append(overlap / sum(ref.values()))
    if not precisions:
        return 100.0 if hypothesis == reference else 0.0
    p, r = mean(precisions), mean(recalls)
    return 0.0 if p + r == 0 else 100 * (1 + beta ** 2) * p * r / (beta ** 2 * p + r)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate_run(run_dir: Path) -> dict:
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    if config["task"] != "translate":
        raise ValueError("only translation runs have predictions to score")
    refs = {row["id"]: row for row in read_jsonl(run_dir / "references.jsonl")}
    predictions = run_dir / "predictions.jsonl"
    if not predictions.exists():
        raise ValueError("no predictions.jsonl: this run was a dry run or failed before the first call")

    by_condition: dict[int, list[tuple[str, str, str]]] = defaultdict(list)  # (prediction, reference, anchor)
    for row in read_jsonl(predictions):
        ref = refs[row["id"]]
        by_condition[row["condition"]].append((row["prediction"], ref["target_text"], ref["anchor_text"]))

    def summarise(rows, expected):
        return {
            "n": len(rows), "complete": len(rows) == expected,
            "chrf": round(mean(chrf(p, r) for p, r, _ in rows), 2),
            "exact_match": round(mean(_nfc(p) == _nfc(r) for p, r, _ in rows), 4),
            "copy_rate": round(mean(_nfc(p) == _nfc(a) for p, _, a in rows), 4),
        }

    n_eval = config["n_eval"]
    identity = [(r["anchor_text"], r["target_text"], r["anchor_text"]) for r in refs.values()]
    return {
        "run": run_dir.name, "n_eval": n_eval,
        "identity_baseline": summarise(identity, n_eval),
        "conditions": {str(k): summarise(rows, n_eval) for k, rows in sorted(by_condition.items())},
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        metrics = evaluate_run(args.run_dir)
    except ValueError as error:
        raise SystemExit(str(error))
    (args.run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"{'condition':<18}{'n':>5}{'chrF':>8}{'exact':>8}{'copy':>8}")
    rows = [("identity (no-op)", metrics["identity_baseline"])] + [(f"{k}-shot", v) for k, v in metrics["conditions"].items()]
    for label, row in rows:
        flag = "" if row["complete"] else "  (incomplete run)"
        print(f"{label:<18}{row['n']:>5}{row['chrf']:>8.2f}{row['exact_match']:>8.3f}{row['copy_rate']:>8.3f}{flag}")


if __name__ == "__main__":
    main()
