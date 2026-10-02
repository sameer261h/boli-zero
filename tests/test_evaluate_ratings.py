import csv
import json

import pytest

from boli_zero import evaluate, ratings


def test_chrf_known_cases():
    assert evaluate.chrf("abcdef", "abcdef") == pytest.approx(100.0)
    assert evaluate.chrf("abcdef", "uvwxyz") == 0.0
    assert 0 < evaluate.chrf("abcdef", "abcxyz") < 100
    assert evaluate.chrf("é", "é") == 100.0  # same text, different Unicode form
    assert evaluate.chrf("abc def", "abcdef") == pytest.approx(100.0)  # whitespace ignored


def write_run(path, refs, predictions, n_eval=None):
    path.mkdir(parents=True)
    (path / "config.json").write_text(json.dumps({"task": "translate", "n_eval": n_eval or len(refs)}))
    (path / "references.jsonl").write_text("".join(json.dumps(r) + "\n" for r in refs))
    (path / "predictions.jsonl").write_text("".join(json.dumps(p) + "\n" for p in predictions))


REFS = [{"id": "e1", "anchor_text": "hindi one", "target_text": "bhoj one"},
        {"id": "e2", "anchor_text": "hindi two", "target_text": "bhoj two"}]


def test_evaluate_run_separates_copying_from_getting_it_right(tmp_path):
    predictions = (
        [{"condition": 0, "id": r["id"], "prediction": r["anchor_text"]} for r in REFS]       # copies the input
        + [{"condition": 10, "id": r["id"], "prediction": r["target_text"]} for r in REFS]    # matches the reference
        + [{"condition": 25, "id": "e1", "prediction": "bhoj one"}]                            # run stopped early
    )
    write_run(tmp_path / "run", REFS, predictions)
    metrics = evaluate.evaluate_run(tmp_path / "run")
    base, zero, ten, twenty_five = (metrics["identity_baseline"], *(metrics["conditions"][k] for k in ("0", "10", "25")))
    assert (base["copy_rate"], base["exact_match"]) == (1.0, 0.0)
    assert zero["chrf"] == base["chrf"] and zero["copy_rate"] == 1.0
    assert (ten["chrf"], ten["exact_match"], ten["copy_rate"]) == (100.0, 1.0, 0.0)
    assert ten["complete"] and not twenty_five["complete"] and twenty_five["n"] == 1


def test_evaluate_run_refuses_runs_without_predictions(tmp_path):
    write_run(tmp_path / "run", REFS, [])
    (tmp_path / "run" / "predictions.jsonl").unlink()
    with pytest.raises(ValueError, match="dry run"):
        evaluate.evaluate_run(tmp_path / "run")


def build_rating_run(path, n=40):
    refs = [{"id": f"i{k:02d}", "anchor_text": f"hindi {k}", "target_text": f"ref {k}"} for k in range(n)]
    preds = [{"condition": c, "id": r["id"], "prediction": f"sys{c} {r['id']}"} for r in refs for c in (0, 10)]
    write_run(path, refs, preds)


def test_export_is_blinded_deterministic_and_matches_its_key(tmp_path):
    build_rating_run(tmp_path / "run")
    first = ratings.export_sheet(tmp_path / "run", "0", "10", 40, 7, tmp_path / "o1")
    second = ratings.export_sheet(tmp_path / "run", "0", "10", 40, 7, tmp_path / "o2")
    assert first.read_bytes() == second.read_bytes()
    key = json.loads((tmp_path / "o1" / "key.json").read_text())
    rows = list(csv.DictReader(first.open(encoding="utf-8")))
    orders = set()
    for row in rows:
        systems = key[row["item_id"]]
        orders.add(tuple(systems))
        assert row["option_1"] == f"sys{systems[0]} {row['item_id']}" and row["option_2"] == f"sys{systems[1]} {row['item_id']}"
    assert orders == {("0", "10"), ("10", "0")}  # position is randomised, not fixed


def test_aggregate_counts_wins_ties_and_rejects_bad_choices(tmp_path):
    build_rating_run(tmp_path / "run")
    sheet = ratings.export_sheet(tmp_path / "run", "0", "10", 40, 7, tmp_path / "o")
    key = json.loads((tmp_path / "o" / "key.json").read_text())
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))

    def fill(name, tie_first=0):
        for i, row in enumerate(rows):
            row["choice"] = "tie" if i < tie_first else str(key[row["item_id"]].index("10") + 1)
        path = tmp_path / f"{name}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    result = ratings.aggregate(tmp_path / "o" / "key.json", [fill("rater_a"), fill("rater_b", tie_first=5)])
    assert result["wins"] == {"10": 75} and result["ties"] == 5
    assert result["win_share_excluding_ties"] == {"10": 1.0}
    assert result["ratings_per_rater"] == {"rater_a": 40, "rater_b": 40}

    rows[0]["choice"] = "banana"
    bad = tmp_path / "rater_c.csv"
    with bad.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="bad choice"):
        ratings.aggregate(tmp_path / "o" / "key.json", [bad])
