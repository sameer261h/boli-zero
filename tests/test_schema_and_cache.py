import pytest
from pydantic import ValidationError

from boli_zero.cache import ResponseCache
from boli_zero.clients import EvonClient, NotConfigured, PrismaClient, TimbreClient
from boli_zero.config import GnaniConfig
from boli_zero.schema import DatasetRecord
from conftest import StubTransport, make_records


def test_schema_fields_match_the_spec_in_order():
    assert list(DatasetRecord.model_fields) == [
        "id", "anchor_language", "target_language", "anchor_text", "target_text",
        "audio_path", "speaker_id", "source", "license", "split"]


def test_schema_rejects_missing_text_and_unknown_fields():
    base = make_records(1)[0].model_dump()
    with pytest.raises(ValidationError):
        DatasetRecord(**{**base, "target_text": "   "})
    with pytest.raises(ValidationError):
        DatasetRecord(**{**base, "surprise": "x"})
    with pytest.raises(ValidationError):
        DatasetRecord(**{**base, "license": ""})


def test_schema_normalises_unicode_and_blank_optionals():
    record = DatasetRecord(**{**make_records(1)[0].model_dump(), "anchor_text": "é", "audio_path": ""})
    assert record.anchor_text == "é"
    assert record.audio_path is None


def test_identical_requests_are_sent_once(config):
    stub = StubTransport()
    client = EvonClient(config, transport=stub)
    assert client.generate("hello") == "stub output"
    assert client.generate("hello") == "stub output"
    assert (client.calls, client.cache_hits, len(stub.requests)) == (1, 1, 1)
    client.generate("hello", temperature=0.7)  # any param change is a new request
    assert len(stub.requests) == 2


def test_audio_is_keyed_by_content_not_file_name(config, tmp_path):
    stub = StubTransport()
    client = PrismaClient(config, transport=stub)
    (tmp_path / "a.wav").write_bytes(b"same bytes")
    (tmp_path / "b.wav").write_bytes(b"same bytes")
    (tmp_path / "c.wav").write_bytes(b"other bytes")
    client.transcribe(tmp_path / "a.wav")
    client.transcribe(tmp_path / "b.wav")
    assert len(stub.requests) == 1
    client.transcribe(tmp_path / "c.wav")
    assert len(stub.requests) == 2


def test_cache_persists_and_serves_without_credentials_or_transport(config):
    EvonClient(config, transport=StubTransport()).generate("persist me")
    fresh = EvonClient(config)  # no transport, no credentials, new object
    assert fresh.generate("persist me") == "stub output"
    assert fresh.calls == 0


def test_uncached_call_without_transport_raises_not_configured(config):
    with pytest.raises(NotConfigured, match="TODO"):
        EvonClient(config).generate("never sent")
    assert EvonClient(config).transport_implemented is False


def test_api_key_is_never_written_to_the_cache(tmp_path):
    secret = "SECRET-KEY-123"
    config = GnaniConfig(api_key=secret, base_url="https://example.invalid", auth_header="X-Key", cache_dir=tmp_path / "c")
    EvonClient(config, transport=StubTransport()).generate("hi")
    files = [p for p in (tmp_path / "c").rglob("*") if p.is_file()]
    assert files and all(secret not in p.read_text(errors="ignore") for p in files)


def test_timbre_audio_round_trips_through_the_cache(config):
    stub = StubTransport(lambda op, params, files: ({"content_type": "audio/x-test"}, b"\x00\x01audio"))
    client = TimbreClient(config, transport=stub)
    assert client.synthesize("text") == b"\x00\x01audio"
    assert client.synthesize("text") == b"\x00\x01audio"
    assert len(stub.requests) == 1


def test_transport_output_that_breaks_the_contract_is_rejected(config):
    bad = StubTransport(lambda op, params, files: ({"answer": "x"}, None))
    with pytest.raises(ValueError, match="text"):
        EvonClient(config, transport=bad).generate("hi")
    with pytest.raises(ValueError, match="audio"):
        TimbreClient(config, transport=StubTransport(lambda *a: ({}, None))).synthesize("hi")
