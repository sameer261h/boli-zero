"""Prisma's HTTP call, checked against a mock server shaped like the documented API. No network, no credentials."""
import json

import httpx
import pytest

from boli_zero.clients import GnaniApiError, NotConfigured, PrismaClient
from boli_zero.config import GnaniConfig

OK = {"success": True, "request_id": "req_1", "timestamp": "20251226_143052.123", "transcript": "mock transcript"}


def make_client(tmp_path, handler, key="test-key"):
    config = GnaniConfig(api_key=key, base_url="https://api.example.invalid", auth_header="X-API-Key-ID",
                         cache_dir=tmp_path / "cache")
    client = PrismaClient(config)
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_request_matches_the_documented_shape(tmp_path):
    seen = {}

    def handler(request):
        seen.update(url=str(request.url), header=request.headers.get("x-api-key-id"), body=request.content)
        return httpx.Response(200, json=OK)

    client = make_client(tmp_path, handler)
    result = client.transcribe_detailed(b"ID3fake-mp3-bytes", "hi-IN", bias_list=["अलग", "बा"],
                                        substitution_map=[{"from": "a", "to": "b"}])
    assert result == {"text": "mock transcript", "request_id": "req_1", "timestamp": "20251226_143052.123"}
    assert seen["url"] == "https://api.example.invalid/stt/v3" and seen["header"] == "test-key"
    body = seen["body"].decode("utf-8", errors="ignore")
    for expected in ('name="audio_file"; filename="audio.mp3"', "audio/mpeg", 'name="language_code"', "hi-IN",
                     'name="format"', "verbatim", 'name="bias_list"', json.dumps(["अलग", "बा"]),
                     'name="enable_substitution"', "true", 'name="substitution_map"', json.dumps([{"from": "a", "to": "b"}])):
        assert expected in body, expected


def test_optional_fields_are_not_sent_unless_set(tmp_path):
    seen = {}
    client = make_client(tmp_path, lambda request: (seen.update(body=request.content), httpx.Response(200, json=OK))[1])
    assert client.transcribe(b"RIFFfake-wav-bytes") == "mock transcript"
    body = seen["body"].decode("utf-8", errors="ignore")
    assert 'filename="audio.wav"' in body and "bias_list" not in body and "substitution_map" not in body


def test_identical_audio_is_sent_once(tmp_path):
    calls = []
    client = make_client(tmp_path, lambda request: (calls.append(1), httpx.Response(200, json=OK))[1])
    client.transcribe(b"same bytes", "hi-IN")
    client.transcribe(b"same bytes", "hi-IN")
    client.transcribe(b"same bytes", "ta-IN")  # a different language setting is a different request
    assert len(calls) == 2 and client.cache_hits == 1


def test_error_responses_raise_and_are_not_cached(tmp_path):
    state = {"fail": True}

    def handler(request):
        if state["fail"]:
            return httpx.Response(403, json={"success": False, "error": {"type": "FORBIDDEN", "message": "bad key"}})
        return httpx.Response(200, json=OK)

    client = make_client(tmp_path, handler)
    with pytest.raises(GnaniApiError, match="403 FORBIDDEN: bad key"):
        client.transcribe(b"audio")
    state["fail"] = False
    assert client.transcribe(b"audio") == "mock transcript"  # the failure was not remembered


def test_missing_credentials_raise_not_configured_before_any_request(tmp_path):
    config = GnaniConfig(None, None, None, tmp_path / "cache")
    with pytest.raises(NotConfigured, match="GNANI_API_KEY"):
        PrismaClient(config).transcribe(b"audio")


def test_rate_limit_answer_shape_seen_in_practice_is_understood(tmp_path):
    body = {"detail": {"error_code": "RATE_LIMITED", "message": "Rate limit exceeded", "status_code": 429}}
    client = make_client(tmp_path, lambda request: httpx.Response(429, json=body, headers={"retry-after": "30"}))
    with pytest.raises(GnaniApiError, match=r"429 RATE_LIMITED: Rate limit exceeded \(Retry-After: 30\)") as caught:
        client.transcribe(b"audio")
    assert caught.value.status == 429


# --- Timbre (text to speech), same mock-server approach -----------------------------------------------------------------
def make_timbre(tmp_path, handler, key="test-key"):
    from boli_zero.clients import TimbreClient
    config = GnaniConfig(api_key=key, base_url="https://api.example.invalid" if key else None, auth_header="X-API-Key-ID" if key else None,
                         cache_dir=tmp_path / "cache")
    client = TimbreClient(config)
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_timbre_request_matches_the_documented_shape_and_audio_is_cached(tmp_path):
    seen = []

    def handler(request):
        seen.append((str(request.url), request.headers.get("x-api-key-id"), json.loads(request.content)))
        return httpx.Response(200, content=b"RIFF....WAVEfake", headers={"content-type": "audio/wav"})

    client = make_timbre(tmp_path, handler)
    assert client.synthesize("नमस्ते") == b"RIFF....WAVEfake"
    assert client.synthesize("नमस्ते") == b"RIFF....WAVEfake" and len(seen) == 1 and client.cache_hits == 1
    url, header, body = seen[0]
    assert url == "https://api.example.invalid/api/v1/tts/inference" and header == "test-key"
    assert body == {"text": "नमस्ते", "voice": "Nalini", "model": "timbre-v2.5", "language": "hi-IN", "speed": 1.0,
                    "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2, "encoding": "linear_pcm", "container": "wav"}}
    client.synthesize("नमस्ते", voice="Deepak")  # a different voice is a different request
    assert len(seen) == 2
    assert client.key_for("synthesize", client.request_params("नमस्ते")) != client.key_for("synthesize", client.request_params("नमस्ते", voice="Deepak"))


def test_timbre_errors_and_non_audio_answers_are_not_cached_or_played(tmp_path):
    state = {"answer": httpx.Response(403, json={"success": False, "error": {"type": "FORBIDDEN", "message": "bad key"}})}
    client = make_timbre(tmp_path, lambda request: state["answer"])
    with pytest.raises(GnaniApiError, match="403 FORBIDDEN"):
        client.synthesize("x")
    state["answer"] = httpx.Response(200, text="<html>not audio</html>", headers={"content-type": "text/html"})
    with pytest.raises(GnaniApiError, match="UNEXPECTED_RESPONSE"):
        client.synthesize("x")
    state["answer"] = httpx.Response(200, content=b"", headers={"content-type": "audio/wav"})
    with pytest.raises(GnaniApiError):
        client.synthesize("x")
    state["answer"] = httpx.Response(429, json={"detail": {"error_code": "RATE_LIMITED", "message": "slow down"}}, headers={"retry-after": "9"})
    with pytest.raises(GnaniApiError, match="Retry-After: 9"):
        client.synthesize("x")
    state["answer"] = httpx.Response(200, content=b"RIFFwav", headers={"content-type": "audio/wav"})
    assert client.synthesize("x") == b"RIFFwav"  # earlier failures were not remembered


def test_timbre_without_credentials_is_not_configured(tmp_path):
    client = make_timbre(tmp_path, lambda request: httpx.Response(200), key=None)
    with pytest.raises(NotConfigured, match="GNANI_API_KEY"):
        client.synthesize("x")
