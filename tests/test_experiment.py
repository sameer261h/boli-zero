import json

import pytest

from boli_zero import experiment as ex
from boli_zero.cache import ResponseCache
from boli_zero.clients import EvonClient
from conftest import StubTransport, make_records


def eval_records(n=3):
    return [r.model_copy(update={"id": f"eval{i}", "split": "validation", "anchor_text": f"eval anchor {i}",
                                 "target_text": f"eval target {i}"}) for i, r in enumerate(make_records(n))]


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_shots_are_deterministic_and_nested():
    train = make_records(60)
    ordered = ex.shot_order(train, 1)
    assert [r.id for r in ordered] == [r.id for r in ex.shot_order(list(reversed(train)), 1)]
    assert {r.id for r in ordered[:10]} <= {r.id for r in ordered[:25]} <= {r.id for r in ordered[:50]}
    assert [r.id for r in ordered] != [r.id for r in ex.shot_order(train, 2)]


def test_prompt_zero_shot_has_no_examples_and_few_shot_keeps_order():
    zero = ex.translation_prompt([], "Q", "hi", "bho", "Devanagari")
    assert "Examples:" not in zero and zero.endswith("Hindi: Q\nBhojpuri:")
    few = ex.translation_prompt(make_records(2), "Q", "hi", "bho", "Devanagari")
    assert "Examples:" in few and few.index("anchor placeholder 0") < few.index("anchor placeholder 1")


def test_first_line_drops_commentary_and_echoed_label():
    assert ex.first_line("\nBhojpuri: the answer\nHere is why...", "Bhojpuri") == "the answer"
    assert ex.first_line("   ", "Bhojpuri") == ""


def test_dry_run_writes_prompts_only_and_reports_skipped_conditions(tmp_path):
    config = ex.run_experiment(train=make_records(30), eval_records=eval_records(), run_dir=tmp_path / "r", dry_run=True)
    assert config["conditions_run"] == [0, 10, 25]
    assert config["conditions_skipped_not_enough_train"] == [50, 100]
    assert config["status"] == "dry-run"
    assert len(jsonl(tmp_path / "r" / "prompts.jsonl")) == 9
    assert not (tmp_path / "r" / "predictions.jsonl").exists()


def test_each_prompt_is_billed_once_and_a_rerun_is_free(config, tmp_path):
    stub = StubTransport(lambda op, p, f: ({"text": "Bhojpuri: pred line\nextra commentary"}, None))
    args = dict(train=make_records(30), eval_records=eval_records(), conditions=[0, 10])
    first = ex.run_experiment(run_dir=tmp_path / "a", client=EvonClient(config, transport=stub), **args)
    rows = jsonl(tmp_path / "a" / "predictions.jsonl")
    assert len(rows) == 6 and {r["prediction"] for r in rows} == {"pred line"} and "extra commentary" in rows[0]["raw"]
    assert (first["status"], first["evon_calls"]) == ("complete", 6)

    second = ex.run_experiment(run_dir=tmp_path / "b", client=EvonClient(config, transport=stub), **args)
    assert (second["evon_calls"], second["evon_cache_hits"], len(stub.requests)) == (0, 6, 6)


def test_run_requires_one_language_pair_and_a_client(tmp_path):
    odd = make_records(1)[0].model_copy(update={"target_language": "mai"})
    with pytest.raises(ValueError, match="language pair"):
        ex.run_experiment(train=make_records(5), eval_records=[odd], run_dir=tmp_path / "x", dry_run=True)
    with pytest.raises(ValueError, match="client"):
        ex.run_experiment(train=make_records(5), eval_records=eval_records(), run_dir=tmp_path / "y")


def test_failed_call_leaves_partial_output_and_marks_the_run_failed(config, tmp_path):
    with pytest.raises(Exception):
        ex.run_experiment(train=make_records(30), eval_records=eval_records(), conditions=[0],
                          run_dir=tmp_path / "f", client=EvonClient(config))  # no transport: NotConfigured
    saved = json.loads((tmp_path / "f" / "config.json").read_text())
    assert saved["status"] == "failed" and (tmp_path / "f" / "prompts.jsonl").exists()


def rules_reply(good_id):
    return json.dumps({
        "lexical_mappings": [
            {"anchor": "a", "target": "b", "confidence": 0.9, "supporting_example_ids": [good_id]},
            {"anchor": "c", "target": "d", "confidence": 0.9, "supporting_example_ids": ["ghost-id"]}],
        "grammatical_patterns": [
            {"category": "x", "description": "y", "confidence": 1.5, "supporting_example_ids": [good_id]}],
        "unresolved_patterns": [{"description": "z", "example_ids": [good_id]}],
    })


def test_parse_rules_keeps_supported_items_and_reports_what_it_dropped():
    shots = make_records(5)
    rules = ex.parse_rules("Sure!\n" + rules_reply(shots[0].id) + "\nDone", shots=shots, anchor_language="hi", target_language="bho")
    assert [m.anchor for m in rules.lexical_mappings] == ["a"]
    assert rules.grammatical_patterns == [] and len(rules.unresolved_patterns) == 1
    assert len(rules.validation_problems) == 2 and "ghost-id" in rules.validation_problems[0]
    with pytest.raises(ValueError):
        ex.parse_rules("no json here", shots=shots, anchor_language="hi", target_language="bho")


def test_rules_task_writes_one_validated_file_per_nonzero_condition(config, tmp_path):
    train = make_records(30)
    good = ex.shot_order(train, 42)[0].id
    stub = StubTransport(lambda op, p, f: ({"text": rules_reply(good)}, None))
    ex.run_experiment(train=train, eval_records=eval_records(), conditions=[0, 10], task="rules",
                      run_dir=tmp_path / "r", client=EvonClient(config, transport=stub))
    assert not (tmp_path / "r" / "rules_0shot.json").exists()
    saved = json.loads((tmp_path / "r" / "rules_10shot.json").read_text())
    assert saved["shots"] == 10 and len(saved["lexical_mappings"]) == 1 and len(saved["validation_problems"]) == 2

    bad = StubTransport(lambda op, p, f: ({"text": "not json"}, None))
    fresh = EvonClient(config, cache=ResponseCache(tmp_path / "other-cache"), transport=bad)
    cfg = ex.run_experiment(train=train, eval_records=eval_records(), conditions=[10], task="rules",
                            run_dir=tmp_path / "bad", client=fresh)
    assert cfg["errors"] and "10-shot" in cfg["errors"][0]


def test_leakage_guard_blocks_overlap_between_teaching_pool_and_held_out(tmp_path):
    train = make_records(30)
    leaky = train[0].model_copy(update={"id": "other-id", "split": "test"})  # same sentences, different id
    with pytest.raises(ValueError, match="anchor_text"):
        ex.run_experiment(train=train, eval_records=[leaky], run_dir=tmp_path / "x", dry_run=True)
    mislabelled = eval_records()[0].model_copy(update={"split": "train"})
    with pytest.raises(ValueError, match="split"):
        ex.run_experiment(train=train, eval_records=[mislabelled], run_dir=tmp_path / "y", dry_run=True)
