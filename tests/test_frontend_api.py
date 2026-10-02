"""Backend behaviour behind the recognition page: samples, audio access, uploads, error states, cost control.

Prisma is replaced by a mock HTTP server shaped like the documented API, so nothing here proves real recognition.
Audio is generated tones; no real recording or Bhojpuri claim is involved.
"""
import hashlib
import io
import json
import shutil
import threading
import time
import wave

import httpx
import pytest
from fastapi.testclient import TestClient

from boli_zero import catalog as cat
from boli_zero.app import create_app
from boli_zero.cache import ResponseCache
from boli_zero.clients import PrismaClient
from boli_zero.config import GnaniConfig
from boli_zero.ledger import Ledger, estimate_cost_inr
from boli_zero.service import MAX_UPLOAD_BYTES, RecognitionService, inspect_upload, sniff_format

pytestmark = pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe is needed to check recording length")
KEY = "SECRET-KEY-do-not-leak"
BHOJPURI_TEXT = "हिंदी सेंटेंस है आप कहाँ जा रहे हैं इसको कैसे बोलेंगे रउआ कहाँ जात बानी"


def wav_bytes(seconds, rate=8000):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((b"\x10\x20" * int(rate * seconds)))
    return buffer.getvalue()


class Upstream:
    """Mock of Prisma's REST endpoint. `mode` switches behaviour between calls; every request is recorded."""

    def __init__(self):
        self.mode, self.requests, self.delay, self.text = "ok", [], 0.0, BHOJPURI_TEXT

    def __call__(self, request):
        self.requests.append(request.content)
        time.sleep(self.delay)
        if self.mode == "network":
            raise httpx.ConnectError("boom", request=request)
        if self.mode == "429":
            return httpx.Response(429, json={"detail": {"error_code": "RATE_LIMITED", "message": "Rate limit exceeded"}}, headers={"retry-after": "7"})
        if self.mode == "403":
            return httpx.Response(403, json={"success": False, "error": {"type": "FORBIDDEN", "message": f"bad credentials for {KEY}"}})
        if self.mode == "500":
            return httpx.Response(500, json={"success": False, "error": {"type": "API_ERROR", "message": "internal"}})
        if self.mode == "duration":
            return httpx.Response(400, json={"success": False, "error": {"type": "MAX_AUDIO_DURATION_EXCEEDED", "message": "too long"}})
        if self.mode == "html":
            return httpx.Response(502, text="<html>bad gateway</html>")
        return httpx.Response(200, json={"success": True, "request_id": f"mock-{len(self.requests)}", "timestamp": "t", "transcript": self.text})


@pytest.fixture
def world(tmp_path):
    root = tmp_path / "samples"
    (root / "usable").mkdir(parents=True)
    files = {"short": wav_bytes(3), "other": wav_bytes(4), "long": wav_bytes(31), "dup": wav_bytes(3.5)}
    samples = []
    for name, data in files.items():
        (root / "usable" / f"{name}.wav").write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        samples.append({"id": cat.sample_id(sha), "sha256": sha, "video_id": name, "group": f"group:{name}", "partition": "development",
                        "duration_s": {"short": 3.0, "other": 4.0, "long": 31.0, "dup": 3.5}[name], "audio_rel_path": f"usable/{name}.wav",
                        "previously_inspected": False, "reviewed_disposition": "x",
                        "eligibility": {"long": "deferred_over_30s", "dup": "duplicate_excluded"}.get(name, "eligible")})
    # a catalog entry that tries to point outside the samples folder
    secret = tmp_path / "outside.wav"; secret.write_bytes(wav_bytes(1))
    samples.append({"id": "0" * 16, "sha256": "0" * 64, "video_id": "evil", "group": "g", "partition": "test", "duration_s": 1.0,
                    "audio_rel_path": "../outside.wav", "previously_inspected": False, "reviewed_disposition": "x", "eligibility": "eligible"})
    (tmp_path / "catalog.json").write_text(json.dumps({"samples": samples}))
    ids = {s["video_id"]: s["id"] for s in samples}

    def make(key=KEY, budget=25.0, boost=None, dev_vocab=None, upstream=None):
        upstream = upstream or Upstream()
        config = GnaniConfig(key, "https://api.example.invalid" if key else None, "X-API-Key-ID" if key else None, tmp_path / "cache")
        prisma = PrismaClient(config)
        prisma._http = httpx.Client(transport=httpx.MockTransport(upstream))
        ledger = Ledger(tmp_path / "ledger.jsonl", budget)
        service = RecognitionService(prisma, ledger, boost=boost, dev_vocab=dev_vocab)
        app = create_app(prisma=prisma, catalog=cat.Catalog(tmp_path / "catalog.json", root), service=service,
                         experiments_dir=tmp_path / "e", splits_dir=tmp_path / "s", processed_dir=tmp_path / "p")
        return TestClient(app), upstream, service, ledger

    return make, ids, files, tmp_path


# --- samples and audio access -----------------------------------------------------------------------------------------
def test_sample_list_exposes_no_file_names_paths_or_video_ids(world):
    make, ids, *_ = world
    client, *_ = make()
    body = client.get("/api/samples").json()
    assert body["configured"] and len(body["samples"]) == 5
    text = json.dumps(body)
    assert all(token not in text for token in ("short.wav", "usable/", "../", "video_id", "sha256", "audio_rel_path"))
    assert all(set(s) == {"id", "partition", "duration_s", "eligibility", "previously_inspected", "label", "saved"} for s in body["samples"])
    assert body["modes"] == {"baseline": True, "boosted": False}


def test_audio_is_served_only_for_catalogued_ids(world):
    make, ids, files, tmp_path = world
    client, *_ = make()
    ok = client.get(f"/api/samples/{ids['short']}/audio")
    assert ok.status_code == 200 and ok.content == files["short"] and ok.headers["cache-control"] == "private, no-store"
    for bad in ("../../etc/passwd", "..%2f..%2fetc%2fpasswd", "deadbeefdeadbeef", "%2e%2e", ids["short"] + "/../x", "not-an-id"):
        assert client.get(f"/api/samples/{bad}/audio").status_code in (404, 405), bad
    assert client.get(f"/api/samples/{'0' * 16}/audio").status_code == 404  # catalog entry escaping the samples folder


# --- recognition of samples ---------------------------------------------------------------------------------------------
def test_sample_recognition_live_then_cache_with_exact_raw_text_and_required_wording(world):
    make, ids, *_ = world
    client, upstream, service, ledger = make()
    sid = ids["short"]
    assert client.get(f"/api/samples/{sid}/results").json()["baseline"] is None
    first = client.post(f"/api/samples/{sid}/recognize", json={"mode": "baseline"}).json()
    assert first["source"] == "live" and first["origin"]["via"] == "http"
    assert first["recognition"]["raw_output"] == BHOJPURI_TEXT
    assert first["identification"]["summary"] == "Mixed: Hindi | Likely Bhojpuri; recognized using Hindi mode."
    assert first["recognition"]["submitted_language_code"] == "hi-IN"
    second = client.post(f"/api/samples/{sid}/recognize", json={"mode": "baseline"}).json()
    assert second["source"] == "cache" and len(upstream.requests) == 1
    assert client.get(f"/api/samples/{sid}/results").json()["baseline"]["recognition"]["raw_output"] == BHOJPURI_TEXT
    summary = ledger.summary()
    assert (summary["successful_live_calls"], summary["failed_calls"], summary["cache_replays"]) == (1, 0, 1)
    assert [s["saved"]["baseline"] for s in client.get("/api/samples").json()["samples"] if s["id"] == sid] == [True]


def test_deferred_and_duplicate_clips_are_never_sent(world):
    make, ids, *_ = world
    client, upstream, *_ = make()
    long = client.post(f"/api/samples/{ids['long']}/recognize", json={"mode": "baseline"})
    assert (long.status_code, long.json()["error"]["code"]) == (422, "deferred_over_30s")
    dup = client.post(f"/api/samples/{ids['dup']}/recognize", json={"mode": "baseline"})
    assert (dup.status_code, dup.json()["error"]["code"]) == (409, "duplicate_excluded")
    assert client.post("/api/samples/ffffffffffffffff/recognize", json={"mode": "baseline"}).status_code == 404
    assert upstream.requests == []


def test_empty_transcript_is_reported_as_an_empty_result_not_a_failure(world):
    make, ids, *_ = world
    client, upstream, *_ = make()
    upstream.text = ""
    body = client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "baseline"}).json()
    assert body["empty_transcript"] is True and body["recognition"]["raw_output"] == ""
    assert body["identification"]["parts"][0]["label"] == "other_or_insufficient"


# --- uploads --------------------------------------------------------------------------------------------------------
def upload(client, data, name="clip.wav", mode="baseline"):
    return client.post("/api/recognize/upload", files={"file": (name, data, "application/octet-stream")}, data={"mode": mode})


@pytest.mark.parametrize("data,status,code", [
    (b"", 422, "empty_file"),
    (b"just some text, not audio at all", 415, "unsupported_format"),
    (b"\x89PNG\r\n\x1a\n" + b"0" * 200, 415, "unsupported_format"),
    (b"RIFF\x24\x00\x00\x00WAVEjunkjunkjunkjunkjunk", 422, "unreadable_audio"),
    (b"ID3" + b"\x00" * 64, 422, "unreadable_audio"),
    (wav_bytes(31), 422, "too_long"),
    (wav_bytes(0.1), 422, "too_short"),
    (b"RIFF" + b"\x00" * (MAX_UPLOAD_BYTES + 10), 413, "file_too_large"),
], ids=["empty", "plain-text", "png", "wav-header-with-junk", "mp3-header-with-junk", "over-30s", "under-0.3s", "over-10MB"])  # short ids: pytest puts them in the environment
def test_bad_uploads_are_refused_with_a_reason_and_never_sent(world, data, status, code):
    make, *_ = world
    client, upstream, *_ = make()
    response = upload(client, data)
    assert (response.status_code, response.json()["error"]["code"]) == (status, code)
    assert upstream.requests == []


def test_upload_without_a_file_part_is_a_clear_bad_request(world):
    make, *_ = world
    client, upstream, *_ = make()
    response = client.post("/api/recognize/upload", data={"mode": "baseline"})
    assert (response.status_code, response.json()["error"]["code"]) == (422, "bad_request") and upstream.requests == []


def test_valid_upload_is_recognized_then_replayed_and_the_file_name_is_ignored(world):
    make, *_ = world
    client, upstream, *_ = make()
    first = upload(client, wav_bytes(3), name="../../etc/passwd").json()
    assert first["source"] == "live" and first["upload"]["format"] == "wav" and abs(first["upload"]["duration_s"] - 3) < 0.1
    again = upload(client, wav_bytes(3), name="different-name.wav").json()
    assert again["source"] == "cache" and len(upstream.requests) == 1


def test_format_sniffing_matches_the_documented_formats():
    assert sniff_format(wav_bytes(1)) == "wav" and sniff_format(b"OggS" + b"0" * 20) == "ogg" and sniff_format(b"fLaC" + b"0" * 20) == "flac"
    assert sniff_format(b"\x00\x00\x00\x20ftypM4A " + b"0" * 20) == "m4a" and sniff_format(b"ID3\x04" + b"0" * 20) == "mp3"
    assert sniff_format(b"\xff\xfb\x90\x00" + b"0" * 20) == "mp3" and sniff_format(b"\xff\xf1\x50\x80" + b"0" * 20) == "aac"
    assert sniff_format(b"plain text") is None
    assert inspect_upload(wav_bytes(2))["duration_s"] == pytest.approx(2, abs=0.05)


# --- failure states ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("mode,status,code", [("429", 429, "rate_limited"), ("403", 502, "gnani_auth"), ("500", 502, "gnani_unavailable"),
                                              ("network", 502, "gnani_unreachable"), ("duration", 422, "gnani_rejected_duration"), ("html", 502, "gnani_unavailable")])
def test_upstream_failures_become_specific_errors_cost_nothing_and_are_not_cached(world, mode, status, code):
    make, ids, *_ = world
    client, upstream, service, ledger = make()
    upstream.mode = mode
    response = client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "baseline"})
    assert (response.status_code, response.json()["error"]["code"]) == (status, code)
    if mode == "429":
        assert response.headers["retry-after"] == "7"
    assert KEY not in response.text
    summary = ledger.summary()
    assert (summary["estimated_spent_inr"], summary["failed_calls"], summary["successful_live_calls"]) == (0, 1, 0)
    upstream.mode = "ok"  # recovery: the failure was not remembered
    assert client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "baseline"}).json()["source"] == "live"


def test_missing_credentials_block_new_audio_but_saved_results_still_replay(world):
    make, ids, files, tmp_path = world
    client, *_ = make()
    client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "baseline"})  # saves a result
    bare, upstream, *_ = make(key=None)
    assert bare.get("/api/samples").json()["samples"]
    replay = bare.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "baseline"}).json()
    assert replay["source"] == "cache"
    fresh = bare.post(f"/api/samples/{ids['other']}/recognize", json={"mode": "baseline"})
    assert (fresh.status_code, fresh.json()["error"]["code"]) == (503, "not_configured") and upstream.requests == []


def test_repeated_clicks_on_the_same_audio_make_one_request(world):
    make, ids, *_ = world
    _, upstream, service, ledger = make()
    upstream.delay = 0.3
    entry = json.loads((world[3] / "catalog.json").read_text())["samples"][0]
    audio = (world[3] / "samples" / entry["audio_rel_path"]).read_bytes()
    results = []
    threads = [threading.Thread(target=lambda: results.append(service.recognize(audio, entry["duration_s"], sample=entry))) for _ in range(5)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert len(upstream.requests) == 1 and sorted(r["source"] for r in results) == ["cache"] * 4 + ["live"]
    assert ledger.summary()["successful_live_calls"] == 1


def test_spend_cap_blocks_live_calls_but_not_replays(world):
    make, ids, *_ = world
    assert estimate_cost_inr(3) == 0.02 and estimate_cost_inr(4) == 0.05 and estimate_cost_inr(30) > estimate_cost_inr(15) > 0
    client, upstream, service, ledger = make(budget=0.05)
    assert client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "baseline"}).status_code == 200  # Rs 0.02 of 0.05
    blocked = client.post(f"/api/samples/{ids['other']}/recognize", json={"mode": "baseline"})  # would reach 0.07
    assert (blocked.status_code, blocked.json()["error"]["code"]) == (409, "budget_exhausted") and len(upstream.requests) == 1
    assert client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "baseline"}).json()["source"] == "cache"
    assert ledger.summary()["estimated_spent_inr"] == 0.02 and ledger.summary()["failures_by_outcome"] == {"budget_blocked": 1}


# --- raw text vs. labels vs. boost ---------------------------------------------------------------------------------------
def test_labels_can_change_without_changing_the_raw_transcript(world):
    make, ids, *_ = world
    client, upstream, *_ = make(dev_vocab={"markers": {"एकदम": "test-only form", "मजेदार": "test-only form"}})
    upstream.text = "चलो यहाँ एकदम मजेदार जगह देखो"
    body = client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "baseline"}).json()
    assert body["recognition"]["raw_output"] == upstream.text  # exactly what came back
    assert "Related variety, uncertain" in body["identification"]["summary"]  # reviewed table: no evidence
    assert "Likely Bhojpuri" in body["identification_with_dev_vocabulary"]["summary"]  # extra forms change the proposal only
    again = client.get(f"/api/samples/{ids['short']}/results").json()["baseline"]
    assert again["recognition"]["raw_output"] == upstream.text


def test_boosted_mode_needs_a_frozen_config_and_is_stored_apart_from_baseline(world):
    make, ids, *_ = world
    client, upstream, *_ = make()
    refused = client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "boosted"})
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "mode_unavailable") and upstream.requests == []

    client, upstream, *_ = make(boost={"bias_list": ["रउआ", "बानी"], "bias_score": 1.0})
    base = client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "baseline"}).json()
    upstream.text = "रउआ कहाँ जात बानी बानी"
    boosted = client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "boosted"}).json()
    sent = upstream.requests[1].decode("utf-8", errors="ignore")
    assert "bias_list" in sent and "bias_score" in sent and "bias_list" not in upstream.requests[0].decode("utf-8", errors="ignore")
    both = client.get(f"/api/samples/{ids['short']}/results").json()
    assert both["baseline"]["recognition"]["raw_output"] == BHOJPURI_TEXT == base["recognition"]["raw_output"]
    assert both["boosted"]["recognition"]["raw_output"] == "रउआ कहाँ जात बानी बानी" and boosted["settings"]["bias_words"] == 2


# --- secrets -------------------------------------------------------------------------------------------------------------
def test_the_api_key_never_appears_in_responses_ledger_cache_or_the_page(world):
    make, ids, files, tmp_path = world
    client, upstream, service, ledger = make()
    seen = [client.get("/").text, client.get("/api/status").text, client.get("/api/samples").text, client.get("/api/budget").text]
    for mode in ("ok", "403", "429", "500", "network"):
        upstream.mode = mode
        seen.append(client.post(f"/api/samples/{ids['short']}/recognize", json={"mode": "baseline"}).text)
    seen.append(upload(client, wav_bytes(3)).text)
    assert all(KEY not in text for text in seen)
    for path in tmp_path.rglob("*"):
        if path.is_file() and path.suffix in (".json", ".jsonl"):
            assert KEY not in path.read_text(errors="ignore"), path


# --- catalog partitions ----------------------------------------------------------------------------------------------------
def _manifest(n):
    return [{"inferred_video_id": f"v{i:03d}", "sha256": hashlib.sha256(str(i).encode()).hexdigest(), "container_duration_seconds": 10 + i % 25,
             "folder": "usable", "filename": f"f{i}.mp3", "disposition": "x"} for i in range(n)]


def test_partitions_are_deterministic_order_independent_and_keep_groups_whole():
    manifest = _manifest(60)
    pairs, forced = [["v001", "v002"]], {"v003", "v004"}
    a = cat.build_catalog(manifest, pairs, forced, seed=1)
    b = cat.build_catalog(list(reversed(manifest)), pairs, forced, seed=1)
    part = lambda c: {e["video_id"]: e["partition"] for e in c["samples"]}
    assert part(a) == part(b) and part(a) != part(cat.build_catalog(manifest, pairs, forced, seed=2))
    assert part(a)["v001"] == part(a)["v002"] and part(a)["v003"] == part(a)["v004"] == "development"
    counts = {p: sum(v == p for v in part(a).values()) for p in cat.PARTITIONS}
    assert counts["development"] >= 29 and counts["validation"] in range(14, 17) and sum(counts.values()) == 60
    repeated = cat.build_catalog(manifest, pairs, forced, seed=1, extra_groups={"v010": "same-sentence", "v011": "same-sentence", "v012": "same-sentence"})
    assert len({part(repeated)[v] for v in ("v010", "v011", "v012")}) == 1
