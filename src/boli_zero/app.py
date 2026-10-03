"""FastAPI backend + static demo page.

    uv run uvicorn boli_zero.app:app --reload      # then open http://127.0.0.1:8000

Every Gnani-backed route returns 503 with the NotConfigured message until the real
HTTP calls are implemented. Nothing here fabricates a result.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from . import conversation_routes
from .contributions import ContributionStore, register as register_contributions
from .catalog import Catalog
from .clients import EvonClient, NotConfigured, PrismaClient, TimbreClient
from .config import EXPERIMENTS_DIR, PROCESSED_DIR, ROOT, SPLITS_DIR
from .conversation import AnthropicReply, ConversationEngine
from .experiment import load_split, shot_order, translation_prompt
from .ledger import ClaudeUsage, Ledger
from .service import LANGUAGE_CODE, MAX_UPLOAD_BYTES, RecognitionError, RecognitionService, inspect_upload

WEB_DIR = ROOT / "web"


class TranslateRequest(BaseModel):
    text: str
    shots: int = 0
    anchor_language: str = "hi"
    target_language: str = "bho"
    script: str = "Devanagari"
    seed: int = 42


def replier_from_env():
    """Claude as the reply generator, only if a key is configured locally (ANTHROPIC_API_KEY in the environment or .env)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    usage = ClaudeUsage(Path(os.environ.get("BOLI_CLAUDE_USAGE") or ROOT / ".cache" / "claude_usage.jsonl"),
                        float(os.environ.get("BOLI_CLAUDE_BUDGET_USD") or 0.25), int(os.environ.get("BOLI_CLAUDE_MAX_REQUESTS") or 40))
    return AnthropicReply(key, os.environ.get("BOLI_REPLY_MODEL") or AnthropicReply.DEFAULT_MODEL, usage, os.environ.get("ANTHROPIC_BASE_URL") or None)


class SampleRecognizeRequest(BaseModel):
    mode: str = "baseline"


def _json_file(env_name: str):
    path = os.environ.get(env_name)
    return json.loads(Path(path).read_text(encoding="utf-8")) if path and Path(path).is_file() else None


def catalog_from_env() -> Catalog | None:
    catalog, root = os.environ.get("BOLI_CATALOG"), os.environ.get("BOLI_SAMPLES_ROOT")
    return Catalog(Path(catalog), Path(root)) if catalog and root and Path(catalog).is_file() else None


def service_from_env(prisma: PrismaClient) -> RecognitionService:
    ledger = Ledger(Path(os.environ.get("BOLI_LEDGER") or ROOT / ".cache" / "spend_ledger.jsonl"), float(os.environ.get("BOLI_BUDGET_INR") or 25))
    return RecognitionService(prisma, ledger, boost=_json_file("BOLI_BOOST_CONFIG"), dev_vocab=_json_file("BOLI_DEV_VOCAB"))


class SynthesizeRequest(BaseModel):
    text: str
    voice: str | None = None


def create_app(prisma: PrismaClient | None = None, timbre: TimbreClient | None = None, evon: EvonClient | None = None,
               experiments_dir: Path = EXPERIMENTS_DIR, splits_dir: Path = SPLITS_DIR,
               processed_dir: Path = PROCESSED_DIR, catalog: Catalog | None = None,
               service: RecognitionService | None = None, engine: ConversationEngine | None = None) -> FastAPI:
    app = FastAPI(title="boli-zero")
    prisma, timbre, evon = prisma or PrismaClient(), timbre or TimbreClient(), evon or EvonClient()
    catalog = catalog or catalog_from_env()
    service = service or service_from_env(prisma)
    engine = engine or ConversationEngine(service, timbre, service.ledger, replier_from_env(), os.environ.get("BOLI_VOICE") or None)
    conversation_routes.register(app, engine)
    register_contributions(app, engine, ContributionStore(os.environ.get("BOLI_CONTRIBUTIONS_DB") or ROOT / ".cache" / "contributions.sqlite"))
    positions = {sid: n for n, sid in enumerate(sorted(catalog.samples), 1)} if catalog else {}
    saved_memo: dict[str, dict] = {}

    def saved_flags(sid: str) -> dict:
        if sid not in saved_memo:  # looked up by the catalog's recorded hash: no audio is read to build the list
            sha = catalog.samples[sid]["sha256"]
            saved_memo[sid] = {mode: bool(service.modes[mode] and service.prisma.has_transcript(sha, LANGUAGE_CODE, **service.options(mode))) for mode in ("baseline", "boosted")}
        return saved_memo[sid]

    @app.exception_handler(RecognitionError)
    async def recognition_error(request, error: RecognitionError):
        headers = {"Retry-After": str(error.extra["retry_after"])} if error.code == "rate_limited" and error.extra.get("retry_after") else {}
        return JSONResponse(status_code=error.status, headers=headers,
                            content={"error": {"code": error.code, "message": error.message, **error.extra}})

    @app.exception_handler(RequestValidationError)
    async def bad_request(request, error: RequestValidationError):
        if request.url.path.startswith(("/api/recognize", "/api/conversations")) or request.url.path.endswith("/recognize"):
            return JSONResponse(status_code=422, content={"error": {"code": "bad_request", "message": "The request was malformed (for example, no file was attached)."}})
        return await request_validation_exception_handler(request, error)

    def guarded(call):
        try:
            return call()
        except NotConfigured as error:
            raise HTTPException(status_code=503, detail=str(error))

    @app.get("/")
    def index():
        return FileResponse(WEB_DIR / "talk.html")  # the conversation screen

    @app.get("/lab")
    def lab_page():
        return FileResponse(WEB_DIR / "index.html")  # developer page: samples, evidence, partitions, comparisons

    @app.get("/api/status")
    def status():
        return {c.service: {"credentials_present": c.config.credentials_present,
                            "transport_implemented": c.transport_implemented,
                            "api_calls": c.calls, "cache_hits": c.cache_hits}
                for c in (prisma, timbre, evon)}

    def entry_or_404(sid: str) -> dict:
        entry = catalog.get(sid) if catalog else None
        if entry is None:
            raise HTTPException(status_code=404, detail="unknown sample")
        return entry

    @app.get("/api/samples")
    def samples():
        if catalog is None:
            return {"configured": False, "samples": [], "modes": service.modes}
        return {"configured": True, "modes": service.modes, "limits": {"max_seconds": 30, "max_upload_mb": MAX_UPLOAD_BYTES // 1024 // 1024},
                "samples": [catalog.public(e, positions[sid]) | {"saved": saved_flags(sid)} for sid, e in sorted(catalog.samples.items())]}

    @app.get("/api/samples/{sid}/audio")
    def sample_audio(sid: str):
        entry_or_404(sid)
        path = catalog.audio_path(sid)
        if path is None:
            raise HTTPException(status_code=404, detail="audio file is not available")
        return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

    @app.get("/api/samples/{sid}/results")
    def sample_results(sid: str):
        entry = entry_or_404(sid)
        path = catalog.audio_path(sid)
        audio = path.read_bytes() if path else b""
        out = {"sample": catalog.public(entry, positions[sid]), "baseline": None, "boosted": None, "boosted_available": service.modes["boosted"]}
        if audio:
            for mode in ("baseline", "boosted"):
                if service.modes[mode]:
                    out[mode] = service.cached(audio, entry["duration_s"], mode, entry)
        return out

    @app.post("/api/samples/{sid}/recognize")
    def sample_recognize(sid: str, request: SampleRecognizeRequest):
        entry = entry_or_404(sid)
        if entry["eligibility"] == "deferred_over_30s":
            raise RecognitionError("deferred_over_30s", "This recording is longer than Prisma's 30 s limit. It is not truncated, and no segmentation method is available, so it is deferred.", 422)
        if entry["eligibility"] == "duplicate_excluded":
            raise RecognitionError("duplicate_excluded", "This recording is a probable duplicate of another clip, so it is not sent separately.", 409)
        path = catalog.audio_path(sid)
        if path is None:
            raise HTTPException(status_code=404, detail="audio file is not available")
        try:
            return service.recognize(path.read_bytes(), entry["duration_s"], mode=request.mode, sample=entry)
        finally:
            saved_memo.pop(sid, None)

    @app.post("/api/recognize/upload")
    def recognize_upload(file: UploadFile = File(...), mode: str = Form("baseline")):
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        info = inspect_upload(data)
        return {**service.recognize(data, info["duration_s"], mode=mode), "upload": {"format": info["format"], "duration_s": info["duration_s"], "size_bytes": info["size"]}}

    @app.get("/api/budget")
    def budget():
        return service.ledger.summary()

    @app.get("/api/dataset")
    def dataset():
        manifest = splits_dir / "manifest.json"
        processed = sum(1 for f in sorted(processed_dir.glob("*.jsonl"))
                        for line in f.read_text(encoding="utf-8").splitlines() if line.strip())
        return {"processed_records": processed,
                "splits": json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else None}

    @app.get("/api/experiments")
    def experiments():
        runs = []
        for config in sorted(experiments_dir.glob("*/config.json")):
            metrics = config.parent / "metrics.json"
            runs.append({"name": config.parent.name, "config": json.loads(config.read_text(encoding="utf-8")),
                         "metrics": json.loads(metrics.read_text(encoding="utf-8")) if metrics.exists() else None})
        return runs

    @app.post("/api/translate")
    def translate(request: TranslateRequest):
        shots = []
        if request.shots:
            train = splits_dir / "train.jsonl"
            if not train.exists():
                raise HTTPException(status_code=409, detail="no train split yet: run ingest and split first")
            shots = shot_order(load_split(train), request.seed)[:request.shots]
        prompt = translation_prompt(shots, request.text, request.anchor_language, request.target_language, request.script)
        return {"prompt": prompt, "output": guarded(lambda: evon.generate(prompt))}

    @app.post("/api/transcribe")
    async def transcribe(audio: UploadFile = File(...), language: str = Form("hi-IN")):
        data = await audio.read()
        return {"text": guarded(lambda: prisma.transcribe(data, language))}

    @app.post("/api/synthesize")
    def synthesize(request: SynthesizeRequest):
        # ponytail: media type is a placeholder until Timbre's real output format is confirmed.
        return Response(engine.synthesize_text(request.text, request.voice), media_type="application/octet-stream")

    return app


app = create_app()
