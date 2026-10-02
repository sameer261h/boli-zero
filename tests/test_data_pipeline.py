import csv
import json

import pytest

from boli_zero import ingest, split
from conftest import make_records


def write_csv(path, rows, fields=("id", "anchor_text", "target_text", "audio_path", "speaker_id")):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_ingest(path, **kwargs):
    return ingest.ingest(ingest.read_rows(path), anchor_language="hi", target_language="bho",
                         source="test fixture", license="test only", **kwargs)


def test_ingest_counts_valid_invalid_duplicate_and_missing_audio(tmp_path):
    src = tmp_path / "pairs.csv"
    write_csv(src, [
        {"id": "a1", "anchor_text": "one", "target_text": "uno", "audio_path": "present.wav", "speaker_id": "s1"},
        {"id": "", "anchor_text": "two", "target_text": "dos", "audio_path": "gone.wav", "speaker_id": ""},
        {"id": "", "anchor_text": "two", "target_text": "dos", "audio_path": "", "speaker_id": ""},   # duplicate content
        {"id": "", "anchor_text": "three", "target_text": "", "audio_path": "", "speaker_id": ""},   # invalid
    ])
    (tmp_path / "present.wav").write_bytes(b"x")
    records, report = run_ingest(src, audio_root=tmp_path)
    assert (report["read"], report["written"], report["invalid"], report["duplicates"], report["missing_audio"]) == (4, 2, 1, 1, 1)
    assert {r.id for r in records} >= {"a1"} and all(r.source == "test fixture" for r in records)
    assert records[1].id == ingest.make_id("two", "dos")  # generated ids are content hashes, stable across runs


def test_ingest_cli_requires_source_and_license(tmp_path):
    src = tmp_path / "pairs.csv"
    write_csv(src, [])
    with pytest.raises(SystemExit):
        ingest.main([str(src), "--anchor-language", "hi", "--target-language", "bho", "--source", "x"])


def test_split_hits_exact_ratios_and_never_overlaps():
    out = split.assign_splits(make_records(20), seed=1, train=0.8, validation=0.1)
    names = [r.split for r in out]
    assert (names.count("train"), names.count("validation"), names.count("test")) == (16, 2, 2)
    assert len({r.id for r in out}) == 20


def test_renderings_of_one_sentence_never_straddle_train_and_held_out():
    records = []
    for i in range(30):  # 30 anchor sentences, each rendered by two speakers
        for speaker in ("a", "b"):
            records.append(make_records(1)[0].model_copy(update={
                "id": f"s{i}-{speaker}", "anchor_text": f"shared anchor {i}", "target_text": f"rendering {speaker} {i}"}))
    out = split.assign_splits(records, seed=9, train=0.8, validation=0.1)
    where = {}
    for r in out:
        assert where.setdefault(r.anchor_text, r.split) == r.split
    train = [r for r in out if r.split == "train"]
    held = [r for r in out if r.split != "train"]
    split.check_no_leakage(train, held)  # does not raise
    with pytest.raises(ValueError, match="leakage"):
        split.check_no_leakage(train, [train[0].model_copy(update={"split": "test"})])


def test_split_ignores_input_order_and_depends_on_seed():
    records = make_records(40)
    pick = lambda rs, seed: {r.id: r.split for r in split.assign_splits(rs, seed=seed, train=0.8, validation=0.1)}
    assert pick(records, 7) == pick(list(reversed(records)), 7)
    assert pick(records, 7) != pick(records, 8)


def test_split_by_speaker_keeps_each_speaker_in_one_split():
    out = split.assign_splits(make_records(40, speakers=8), seed=3, train=0.6, validation=0.2, group_by="speaker_id")
    seen = {}
    for r in out:
        assert seen.setdefault(r.speaker_id, r.split) == r.split


def test_end_to_end_files_are_byte_identical_across_runs(tmp_path):
    src = tmp_path / "pairs.csv"
    write_csv(src, [{"id": f"r{i}", "anchor_text": f"a{i}", "target_text": f"t{i}", "audio_path": "", "speaker_id": ""}
                    for i in range(30)])
    processed = tmp_path / "processed.jsonl"
    ingest.main([str(src), "--anchor-language", "hi", "--target-language", "bho", "--source", "s", "--license", "l",
                 "--out", str(processed)])
    outputs = []
    for run in ("one", "two"):
        out_dir = tmp_path / run
        split.main([str(processed), "--seed", "5", "--out", str(out_dir)])
        outputs.append({p.name: p.read_bytes() for p in sorted(out_dir.iterdir())})
    assert outputs[0] == outputs[1]
    manifest = json.loads(outputs[0]["manifest.json"])
    assert manifest["counts"] == {"train": 24, "validation": 3, "test": 3}
    assert all(json.loads(line)["split"] == "train" for line in outputs[0]["train.jsonl"].decode().splitlines())
