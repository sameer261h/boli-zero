"""HTTP routes for the spoken conversation. Thin: all behaviour is in conversation.py."""
from __future__ import annotations

import re

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from .conversation import ConversationEngine
from .service import MAX_UPLOAD_BYTES, RecognitionError

ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def _ids(*values: str) -> None:
    if not all(ID.match(v or "") for v in values):
        raise RecognitionError("bad_request", "Malformed conversation or turn id.", 422)


def register(app: FastAPI, engine: ConversationEngine) -> None:
    @app.get("/api/talk/capabilities")
    def capabilities():
        return engine.capabilities()

    @app.post("/api/conversations")
    def start():
        return engine.start()

    @app.delete("/api/conversations/{cid}")
    def end(cid: str):
        _ids(cid)
        return engine.end(cid)

    @app.post("/api/conversations/{cid}/close")  # same as DELETE; lets the page end the conversation as it unloads
    def close(cid: str):
        _ids(cid)
        return engine.end(cid)

    @app.get("/api/conversations/{cid}")
    def snapshot(cid: str):
        _ids(cid)
        return engine.snapshot(cid)

    @app.post("/api/conversations/{cid}/turns")
    def recognize(cid: str, turn_id: str = Form(...), file: UploadFile = File(...)):
        _ids(cid, turn_id)
        return {"turn": engine.recognize(cid, turn_id, file.file.read(MAX_UPLOAD_BYTES + 1))}

    @app.post("/api/conversations/{cid}/turns/{tid}/reply")
    def reply(cid: str, tid: str):
        _ids(cid, tid)
        return {"turn": engine.reply(cid, tid)}

    @app.post("/api/conversations/{cid}/turns/{tid}/speech")
    def speech(cid: str, tid: str):
        _ids(cid, tid)
        return {"turn": engine.speak(cid, tid)}

    @app.get("/api/speech/{audio_id}")
    def speech_audio(audio_id: str):
        audio = engine.audio(audio_id)
        if audio is None:
            raise HTTPException(status_code=404, detail="no such audio")
        return Response(audio, media_type="audio/wav", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
