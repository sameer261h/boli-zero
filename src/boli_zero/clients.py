"""Gnani client abstractions: PrismaClient (speech to text), TimbreClient (text to speech), EvonClient (LLM).

Prisma's and Timbre's HTTP calls are written against the documented REST API. Evon is NOT wired (Gnani documents no
hosted endpoint): its `_send` raises NotConfigured with a TODO list. You can always (a) replay anything already in the cache and
(b) inject a `transport` (tests, or a local Evon runtime) without touching the rest of the code.

Normalised contract every transport/`_send` must satisfy:
    transport(operation, params, files) -> (data: dict, blob: bytes | None)
    prisma  "transcribe":  data={"text": str}
    timbre  "synthesize":  data={"content_type": str}, blob=audio bytes
    evon    "generate":    data={"text": str}
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse
from typing import Callable

from .cache import ResponseCache, record_from_hashes, request_key, request_record
from .config import GnaniConfig

Transport = Callable[[str, dict, "dict[str, bytes]"], "tuple[dict, bytes | None]"]


class NotConfigured(RuntimeError):
    """Raised instead of guessing an endpoint or sending a request without credentials."""


class GnaniClient:
    service = ""
    todo = ""  # what must be confirmed before `_send` can be written

    def __init__(self, config: GnaniConfig | None = None, cache: ResponseCache | None = None,
                 transport: Transport | None = None):
        self.config = config or GnaniConfig.from_env()
        self.cache = cache or ResponseCache(self.config.cache_dir)
        self.transport = transport
        self.calls = 0  # requests that actually left the machine (billable)
        self.cache_hits = 0

    @property
    def transport_implemented(self) -> bool:
        return self.transport is not None or type(self)._send is not GnaniClient._send

    def _call(self, operation: str, params: dict, files: dict[str, bytes] | None = None) -> tuple[dict, bytes | None]:
        files = files or {}
        record = request_record(operation, params, files)
        key = request_key(self.service, record)
        hit = self.cache.get(self.service, key)
        if hit is not None:
            self.cache_hits += 1
            return hit
        data, blob = (self.transport or self._send)(operation, params, files)
        self.calls += 1
        origin = {"via": "injected transport"} if self.transport else {"via": "http", "host": urlparse(self.config.base_url or "").netloc}
        self.cache.put(self.service, key, record, data, blob, origin)
        return data, blob

    _http = None

    @property
    def http(self):
        if self._http is None:
            import httpx
            self._http = httpx.Client(timeout=120)
        return self._http

    def key_for(self, operation: str, params: dict, files: dict[str, bytes] | None = None) -> str:
        """The cache key of a request. Safe to hand to a browser: it reveals nothing about credentials."""
        return request_key(self.service, request_record(operation, params, files or {}))

    def peek(self, operation: str, params: dict, files: dict[str, bytes] | None = None) -> dict | None:
        """The cached entry for this exact request, or None. Sends nothing and counts nothing."""
        record = request_record(operation, params, files or {})
        return self.cache.get_entry(self.service, request_key(self.service, record))

    def has_cached(self, operation: str, params: dict, file_hashes: dict[str, str]) -> bool:
        """Cheap existence check by file hash. Reads no audio and sends nothing."""
        return self.cache.get_entry(self.service, request_key(self.service, record_from_hashes(operation, params, file_hashes))) is not None

    def _send(self, operation: str, params: dict, files: dict[str, bytes]) -> tuple[dict, bytes | None]:
        raise NotConfigured(
            f"{self.service}.{operation}: no HTTP transport implemented. TODO: {self.todo} "
            "Then implement `_send` in boli_zero/clients.py (see README, 'Connecting the real APIs')."
        )

    def _require_text(self, data: dict, operation: str) -> str:
        if not isinstance(data.get("text"), str):
            raise ValueError(f"{self.service}.{operation}: transport must return {{'text': str}}, got {sorted(data)}")
        return data["text"]


class GnaniApiError(RuntimeError):
    """The API answered, but not with success. Never cached, so a retry is a fresh request."""

    def __init__(self, status: int, error_type: str, message: str, retry_after: str | None = None):
        super().__init__(f"HTTP {status} {error_type}: {message}" + (f" (Retry-After: {retry_after})" if retry_after else ""))
        self.status, self.error_type, self.retry_after = status, error_type, retry_after


def _audio_name(audio: bytes) -> tuple[str, str]:
    """File name and MIME type for the upload, sniffed from the first bytes. Unknown data is sent as MP3."""
    for magic, name, mime in ((b"RIFF", "audio.wav", "audio/wav"), (b"OggS", "audio.ogg", "audio/ogg"),
                              (b"fLaC", "audio.flac", "audio/flac")):
        if audio.startswith(magic):
            return name, mime
    return "audio.mp3", "audio/mpeg"


class PrismaClient(GnaniClient):
    """Speech to text via the documented REST endpoint (docs.gnani.ai/api/STT/speech-to-text.md, checked 2026-10-02):
    POST {base_url}/stt/v3, multipart form, auth in the header named by GNANI_AUTH_HEADER, up to 60 s of audio.
    Bhojpuri is not an offered language_code; use the nearest offered code and say so wherever results are reported.
    """

    service = "prisma"
    endpoint = "/stt/v3"
    todo = "set GNANI_API_KEY, GNANI_BASE_URL and GNANI_AUTH_HEADER in .env (values are in .env.example)."

    def transcribe(self, audio: bytes | str | Path, language_code: str = "hi-IN", **options) -> str:
        return self.transcribe_detailed(audio, language_code, **options)["text"]

    @staticmethod
    def request_params(language_code: str = "hi-IN", *, format: str = "verbatim", bias_list: list[str] | None = None,
                       bias_score: float | None = None, substitution_map: list[dict] | None = None) -> dict:
        """The API's own field names; unset options are not sent. Also the cache key, so peek and send agree."""
        params = {"language_code": language_code, "format": format}
        if bias_list:
            params["bias_list"] = bias_list  # API limit: 100 words
        if bias_score is not None:
            params["bias_score"] = bias_score
        if substitution_map:
            params.update(enable_substitution=True, substitution_map=substitution_map)  # API limit: 10 rules
        return params

    def transcribe_detailed(self, audio: bytes | str | Path, language_code: str = "hi-IN", **options) -> dict:
        """Returns {'text', 'request_id', 'timestamp'}."""
        audio_bytes = audio if isinstance(audio, bytes) else Path(audio).read_bytes()
        data, _ = self._call("transcribe", self.request_params(language_code, **options), {"audio": audio_bytes})
        self._require_text(data, "transcribe")
        return data

    def has_transcript(self, audio_sha256: str, language_code: str = "hi-IN", **options) -> bool:
        return self.has_cached("transcribe", self.request_params(language_code, **options), {"audio": audio_sha256})

    def peek_transcript(self, audio: bytes, language_code: str = "hi-IN", **options) -> dict | None:
        """The cached entry for this audio and these settings, or None."""
        return self.peek("transcribe", self.request_params(language_code, **options), {"audio": audio})

    def _send(self, operation: str, params: dict, files: dict[str, bytes]) -> tuple[dict, bytes | None]:
        if not self.config.credentials_present:
            raise NotConfigured(f"prisma.{operation}: {self.todo}")
        form = {key: json.dumps(value) if isinstance(value, (list, dict, bool)) else str(value)
                for key, value in params.items()}
        name, mime = _audio_name(files["audio"])
        response = self.http.post(self.config.base_url.rstrip("/") + self.endpoint,
                                  headers={self.config.auth_header: self.config.api_key},
                                  data=form, files={"audio_file": (name, files["audio"], mime)})
        try:
            body = response.json()
        except ValueError:
            raise GnaniApiError(response.status_code, "NON_JSON_RESPONSE", response.text[:200])
        if response.status_code != 200 or not body.get("success"):
            # The docs show {"error": {"type", "message"}}; a rate-limit answer was seen as {"detail": {"error_code", "message"}}.
            error = body.get("error") or (body.get("detail") if isinstance(body.get("detail"), dict) else {}) or {}
            raise GnaniApiError(response.status_code, error.get("type") or error.get("error_code") or "UNKNOWN",
                                error.get("message") or str(body)[:200], response.headers.get("retry-after"))
        return {"text": body["transcript"], "request_id": body.get("request_id"), "timestamp": body.get("timestamp")}, None


class TimbreClient(GnaniClient):
    """Text to speech via the documented REST endpoint (docs.gnani.ai/api/TTS/tts-inference.md, checked 2026-10-03):
    POST {base_url}/api/v1/tts/inference with a JSON body, auth in the header named by GNANI_AUTH_HEADER; the answer is
    the audio itself. Bhojpuri is not an offered language: text is sent with the nearest offered language (hi-IN) and a
    Hindi voice, and how well that pronounces Bhojpuri is unverified.
    """

    service = "timbre"
    endpoint = "/api/v1/tts/inference"
    MODEL = "timbre-v2.5"
    DEFAULT_VOICE = "Nalini"  # a Hindi voice from the documented catalog
    AUDIO_CONFIG = {"sample_rate": 24000, "num_channels": 1, "sample_width": 2, "encoding": "linear_pcm", "container": "wav"}
    todo = "set GNANI_API_KEY, GNANI_BASE_URL and GNANI_AUTH_HEADER in .env (values are in .env.example)."

    @classmethod
    def request_params(cls, text: str, language: str = "hi-IN", voice: str | None = None, speed: float = 1.0) -> dict:
        """The API's own field names. Also the cache key, so identical text is never synthesized (or billed) twice."""
        return {"text": text, "voice": voice or cls.DEFAULT_VOICE, "model": cls.MODEL, "language": language, "speed": speed,
                "audio_config": dict(cls.AUDIO_CONFIG)}

    def synthesize(self, text: str, language: str = "hi-IN", voice: str | None = None, speed: float = 1.0) -> bytes:
        _, blob = self._call("synthesize", self.request_params(text, language, voice, speed))
        if blob is None:
            raise ValueError("timbre.synthesize: transport returned no audio bytes")
        return blob

    def _send(self, operation: str, params: dict, files: dict[str, bytes]) -> tuple[dict, bytes | None]:
        if not self.config.credentials_present:
            raise NotConfigured(f"timbre.{operation}: {self.todo}")
        response = self.http.post(self.config.base_url.rstrip("/") + self.endpoint,
                                  headers={self.config.auth_header: self.config.api_key}, json=params)
        content_type = response.headers.get("content-type", "")
        if response.status_code == 200 and content_type.startswith("audio/") and response.content:
            return {"content_type": content_type.split(";")[0], "bytes": len(response.content)}, response.content
        try:
            body = response.json()
        except ValueError:
            body = {}
        error = body.get("error") or (body.get("detail") if isinstance(body.get("detail"), dict) else {}) or {}
        raise GnaniApiError(response.status_code, error.get("type") or error.get("error_code") or "UNEXPECTED_RESPONSE",
                            error.get("message") or f"HTTP {response.status_code}, content type {content_type or 'none'}",
                            response.headers.get("retry-after"))


class EvonClient(GnaniClient):
    service = "evon"
    todo = ("confirm how Evon is reached: a Gnani-hosted endpoint (path, auth, model name) or a self-run "
            "runtime from the open weights (then pass it as `transport`). Map the output to {'text': str}.")

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
        data, _ = self._call("generate", {"prompt": prompt, "max_tokens": max_tokens, "temperature": temperature})
        return self._require_text(data, "generate")
