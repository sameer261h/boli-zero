"""Upload validation and the one code path that turns audio into a labelled Prisma result (used by the app and the batch scripts).

Rules this module enforces: nothing longer than the observed 30 s Prisma limit is sent (never truncated), identical
audio is never sent twice (cache, plus one request in flight per audio), live calls stop at the estimated-spend cap,
and every outcome is written to the ledger.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import threading
from pathlib import Path

import httpx

from .catalog import API_LIMIT_SECONDS
from .clients import GnaniApiError, NotConfigured, PrismaClient
from .ledger import BudgetExceeded, Ledger, estimate_cost_inr
from .routing import label_clip

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MIN_SECONDS = 0.3
SUPPORTED_FORMATS = ("wav", "mp3", "ogg", "flac", "aac", "m4a")  # the formats Prisma's docs list
LANGUAGE_CODE = "hi-IN"


class RecognitionError(Exception):
    """A user-visible failure with a stable code, so the page can show the right state."""

    def __init__(self, code: str, message: str, status: int, **extra):
        super().__init__(message)
        self.code, self.message, self.status, self.extra = code, message, status, extra


def sniff_format(data: bytes) -> str | None:
    head = data[:12]
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:4] == b"OggS":
        return "ogg"
    if head[:4] == b"fLaC":
        return "flac"
    if head[4:8] == b"ftyp":
        return "m4a"
    if head[:3] == b"ID3":
        return "mp3"
    if len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0:
        return "mp3" if head[1] & 0x06 else "aac"  # layer bits 00 mean ADTS AAC
    return None


def inspect_upload(data: bytes) -> dict:
    """Validate an upload. Returns {format, duration_s, size, sha256} or raises RecognitionError. Nothing is sent anywhere."""
    if not data:
        raise RecognitionError("empty_file", "The file is empty.", 422)
    if len(data) > MAX_UPLOAD_BYTES:
        raise RecognitionError("file_too_large", f"The file is larger than {MAX_UPLOAD_BYTES // 1024 // 1024} MB.", 413)
    fmt = sniff_format(data)
    if fmt is None:
        raise RecognitionError("unsupported_format", "This is not a supported audio file. Use " + ", ".join(SUPPORTED_FORMATS) + ".", 415)
    with tempfile.NamedTemporaryFile(suffix="." + fmt) as handle:  # name is ours, never the uploaded file's
        handle.write(data)
        handle.flush()
        try:
            probe = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_entries",
                                    "format=duration:stream=codec_type", "-i", handle.name],
                                   capture_output=True, text=True, timeout=20)
        except FileNotFoundError:
            raise RecognitionError("cannot_check_duration", "ffprobe is not installed, so the length cannot be checked.", 503)
        except subprocess.TimeoutExpired:
            raise RecognitionError("unreadable_audio", "Reading the file took too long.", 422)
    try:
        info = json.loads(probe.stdout or "{}")
        duration = float(info["format"]["duration"])
        kinds = [s["codec_type"] for s in info.get("streams", [])]
    except (KeyError, ValueError, TypeError):
        raise RecognitionError("unreadable_audio", "The file looks like audio but could not be decoded, or its length is unknown.", 422)
    if probe.returncode != 0 or "audio" not in kinds or "video" in kinds:
        raise RecognitionError("unreadable_audio", "The file has no readable audio track, or it contains video.", 422)
    if duration < MIN_SECONDS:
        raise RecognitionError("too_short", "The recording is too short to recognize.", 422)
    if duration >= API_LIMIT_SECONDS:
        raise RecognitionError("too_long", f"The recording is {duration:.1f} s. Prisma accepted at most 30 s when tested; "
                                           "the file is not truncated. Upload a shorter recording.", 422)
    return {"format": fmt, "duration_s": round(duration, 3), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class RecognitionService:
    def __init__(self, prisma: PrismaClient, ledger: Ledger, boost: dict | None = None, dev_vocab: dict | None = None):
        self.prisma, self.ledger, self.boost, self.dev_vocab = prisma, ledger, boost, dev_vocab
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    @property
    def modes(self) -> dict:
        return {"baseline": True, "boosted": bool(self.boost)}

    def options(self, mode: str) -> dict:
        if mode == "baseline":
            return {}
        if mode == "boosted" and self.boost:
            return {"bias_list": self.boost["bias_list"], "bias_score": self.boost["bias_score"]}
        raise RecognitionError("mode_unavailable", "Boosted recognition has no frozen configuration yet." if mode == "boosted" else f"Unknown mode {mode!r}.", 409)

    def _lock_for(self, key: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    def cached(self, audio: bytes, duration_s: float, mode: str = "baseline", sample: dict | None = None) -> dict | None:
        """The saved result for this audio and mode, built from the cache only. Sends and spends nothing."""
        entry = self.prisma.peek_transcript(audio, LANGUAGE_CODE, **self.options(mode))
        return self._payload(entry["response"], entry, "cache", duration_s, mode, sample) if entry else None

    def recognize(self, audio: bytes, duration_s: float, *, mode: str = "baseline", sample: dict | None = None) -> dict:
        if duration_s >= API_LIMIT_SECONDS:
            raise RecognitionError("too_long", "Longer than Prisma's observed 30 s limit; not truncated.", 422)
        options = self.options(mode)
        sha = hashlib.sha256(audio).hexdigest()
        who = {"audio_sha256": sha[:16], "sample_id": (sample or {}).get("id"), "mode": mode, "duration_s": round(duration_s, 3)}
        with self._lock_for(sha + mode):  # a second click on the same audio waits, then finds the cache
            entry = self.prisma.peek_transcript(audio, LANGUAGE_CODE, **options)
            if entry:
                self.ledger.record(outcome="cache_replay", cost_estimate_inr=0, **who)
                return self._payload(entry["response"], entry, "cache", duration_s, mode, sample)
            cost = estimate_cost_inr(duration_s)
            try:
                self.ledger.check(cost)
                data = self.prisma.transcribe_detailed(audio, LANGUAGE_CODE, **options)
            except BudgetExceeded as error:
                self.ledger.record(outcome="budget_blocked", cost_estimate_inr=0, **who)
                raise RecognitionError("budget_exhausted", str(error), 409)
            except NotConfigured as error:
                self.ledger.record(outcome="not_configured", cost_estimate_inr=0, **who)
                raise RecognitionError("not_configured", "Gnani credentials are not configured on the server, and this audio has no saved result.", 503)
            except GnaniApiError as error:
                outcome, code, status, message = self._classify(error)
                self.ledger.record(outcome=outcome, cost_estimate_inr=0, gnani_status=error.status, gnani_error=error.error_type, **who)
                raise RecognitionError(code, message, status, retry_after=error.retry_after or "20") from error
            except httpx.HTTPError as error:
                self.ledger.record(outcome="network_error", cost_estimate_inr=0, **who)
                raise RecognitionError("gnani_unreachable", "Could not reach Gnani (network error or timeout).", 502) from error
            self.ledger.record(outcome="success", cost_estimate_inr=cost, request_id=data.get("request_id"), **who)
            entry = self.prisma.peek_transcript(audio, LANGUAGE_CODE, **options)
            return self._payload(data, entry, "live", duration_s, mode, sample)

    @staticmethod
    def _classify(error: GnaniApiError) -> tuple[str, str, int, str]:
        if error.status == 429:
            return "rate_limited", "rate_limited", 429, "Gnani is rate-limiting requests. Wait a little and try again."
        if error.status in (401, 403):
            return "auth_error", "gnani_auth", 502, "Gnani rejected the server's API key. The key may be wrong, revoked, or missing the speech-to-text scope."
        if error.status == 400 and "DURATION" in error.error_type:
            return "duration_rejected", "gnani_rejected_duration", 422, "Gnani rejected the recording as too long."
        if error.status == 400:
            return "input_rejected", "gnani_rejected_input", 422, f"Gnani rejected the recording: {error.error_type}."
        return "processing_error", "gnani_unavailable", 502, f"Gnani had a processing problem (HTTP {error.status}). Try again later."

    def _payload(self, data: dict, entry: dict | None, source: str, duration_s: float, mode: str, sample: dict | None) -> dict:
        raw = data["text"]
        clip = {"sample_id": (sample or {}).get("id"), "duration_s": round(duration_s, 3)}
        routed = label_clip(raw_output=raw, submitted_language_code=LANGUAGE_CODE, request_id=data.get("request_id"), clip=clip,
                            source="live Prisma request" if source == "live" else "saved response replayed from the local cache")
        with_dev = None
        if self.dev_vocab:
            with_dev = label_clip(raw_output=raw, submitted_language_code=LANGUAGE_CODE, request_id=data.get("request_id"), clip=clip,
                                  extra_markers=self.dev_vocab["markers"]).identification
        return {
            "mode": mode, "source": source, "empty_transcript": not raw.strip(),
            "cached_at": (entry or {}).get("cached_at"), "origin": (entry or {}).get("origin"),
            "settings": {"language_code": LANGUAGE_CODE, "format": "verbatim", **({"bias_words": len(self.boost["bias_list"]), "bias_score": self.boost["bias_score"]} if mode == "boosted" else {})},
            "recognition": routed.recognition, "identification": routed.identification, "routes": [r.model_dump() for r in routed.routes],
            "identification_with_dev_vocabulary": with_dev,
            "bhojpuri_note": "Bhojpuri is not an offered Prisma language, so audio is sent in Hindi mode. A label such as Likely Bhojpuri is a proposal and is kept as proposed.",
        }
