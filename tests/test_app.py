import json

from fastapi.testclient import TestClient

from boli_zero.app import create_app
from boli_zero.clients import EvonClient, PrismaClient, TimbreClient
from conftest import StubTransport, make_records


def make_client(config, tmp_path, evon_transport=None, prisma_transport=None):
    app = create_app(PrismaClient(config, transport=prisma_transport), TimbreClient(config),
                     EvonClient(config, transport=evon_transport),
                     experiments_dir=tmp_path / "exp", splits_dir=tmp_path / "splits", processed_dir=tmp_path / "processed")
    return TestClient(app)


def test_page_and_status_are_honest_about_missing_access(config, tmp_path):
    client = make_client(config, tmp_path)
    assert "Boli Zero" in client.get("/").text and "Tap to talk" in client.get("/").text  # main page is the conversation screen
    assert "boli-zero" in client.get("/lab").text  # developer page
    status = client.get("/api/status").json()
    assert set(status) == {"prisma", "timbre", "evon"}
    assert all(not s["credentials_present"] for s in status.values())
    assert {name: s["transport_implemented"] for name, s in status.items()} == {"prisma": True, "timbre": True, "evon": False}


def test_gnani_routes_return_503_with_the_todo_until_wired(config, tmp_path):
    client = make_client(config, tmp_path)
    response = client.post("/api/translate", json={"text": "anything"})
    assert response.status_code == 503 and "TODO" in response.json()["detail"]
    assert client.post("/api/synthesize", json={"text": "x"}).status_code == 503
    assert client.post("/api/transcribe", files={"audio": ("a.wav", b"bytes", "audio/wav")}).status_code == 503


def test_translate_uses_the_requested_number_of_examples(config, tmp_path):
    (tmp_path / "splits").mkdir()
    (tmp_path / "splits" / "train.jsonl").write_text("".join(r.model_dump_json() + "\n" for r in make_records(12)))
    stub = StubTransport()
    client = make_client(config, tmp_path, evon_transport=stub)
    body = client.post("/api/translate", json={"text": "my sentence", "shots": 10}).json()
    assert body["output"] == "stub output" and body["prompt"].count("Hindi:") == 11  # 10 examples + the query
    assert "my sentence" in stub.requests[0][1]["prompt"]


def test_translate_with_examples_but_no_split_is_a_clear_409(config, tmp_path):
    client = make_client(config, tmp_path, evon_transport=StubTransport())
    assert client.post("/api/translate", json={"text": "x", "shots": 10}).status_code == 409


def test_transcribe_returns_the_transport_text(config, tmp_path):
    client = make_client(config, tmp_path, prisma_transport=StubTransport(lambda *a: ({"text": "heard this"}, None)))
    response = client.post("/api/transcribe", files={"audio": ("a.wav", b"bytes", "audio/wav")}, data={"language": "hi"})
    assert response.json() == {"text": "heard this"}


def test_dataset_and_experiment_endpoints_read_what_is_on_disk(config, tmp_path):
    client = make_client(config, tmp_path)
    assert client.get("/api/dataset").json() == {"processed_records": 0, "splits": None}
    assert client.get("/api/experiments").json() == []

    (tmp_path / "processed").mkdir()
    (tmp_path / "processed" / "x.jsonl").write_text("".join(r.model_dump_json() + "\n" for r in make_records(4)))
    (tmp_path / "splits").mkdir()
    (tmp_path / "splits" / "manifest.json").write_text(json.dumps({"counts": {"train": 3, "validation": 1, "test": 0}}))
    run = tmp_path / "exp" / "run1"
    run.mkdir(parents=True)
    (run / "config.json").write_text(json.dumps({"task": "translate", "status": "complete"}))
    (run / "metrics.json").write_text(json.dumps({"conditions": {}}))

    assert client.get("/api/dataset").json()["processed_records"] == 4
    assert client.get("/api/dataset").json()["splits"]["counts"]["train"] == 3
    runs = client.get("/api/experiments").json()
    assert runs[0]["name"] == "run1" and runs[0]["metrics"] == {"conditions": {}}
