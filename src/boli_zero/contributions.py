"""Explicitly opted-in recordings, kept private on a persistent local volume."""
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from pathlib import Path

from fastapi import File, Form, Header, HTTPException, UploadFile

from .service import MAX_UPLOAD_BYTES, inspect_upload

CONSENT_VERSION = "boli-zero-contribution-v1"


class ContributionStore:
    def __init__(self, path):
        self.path = Path(path)

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        os.chmod(self.path, 0o600)
        db.execute("CREATE TABLE IF NOT EXISTS contributions (id TEXT PRIMARY KEY, token_hash TEXT, created REAL, audio BLOB, metadata TEXT)")
        db.execute("DELETE FROM contributions WHERE created < ?", (time.time() - 30 * 86400,))
        db.commit()
        return db

    def save(self, audio, metadata, receipt=None):
        cid, token = (receipt["contribution_id"], receipt["withdrawal_token"]) if receipt else (uuid.uuid4().hex, secrets.token_urlsafe(32))
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO contributions VALUES (?,?,?,?,?)", (cid, hashlib.sha256(token.encode()).hexdigest(), time.time(), audio, json.dumps(metadata, ensure_ascii=False)))
            saved = db.execute("SELECT token_hash,audio,metadata FROM contributions WHERE id=?", (cid,)).fetchone()
            verify_retry(saved, token, audio, metadata)
        return {"contribution_id": cid, "withdrawal_token": token, "retention_days": 30}

    def withdraw(self, cid, token):
        with self.connect() as db:
            cur = db.execute("DELETE FROM contributions WHERE id=? AND token_hash=?", (cid, hashlib.sha256(token.encode()).hexdigest()))
            return cur.rowcount == 1


def verify_retry(saved, token, audio, metadata):
    old = json.loads(saved[2]) if isinstance(saved[2], str) else saved[2]
    fields = ('consent_version', 'corrected_text_user_supplied', 'feedback')
    if saved[0] != hashlib.sha256(token.encode()).hexdigest() or bytes(saved[1]) != audio or any(old.get(k) != metadata.get(k) for k in fields):
        raise HTTPException(409, "This receipt already belongs to a different contribution. The saved recording was not changed.")


def register(app, engine, store):
    @app.post("/api/contributions")
    def contribute(conversation_id: str = Form(...), turn_id: str = Form(...), consent: bool = Form(False),
                   consent_version: str = Form(...), contribution_id: str = Form(...), withdrawal_token: str = Form(...), corrected_text: str = Form(""), feedback: str = Form(""), file: UploadFile = File(...)):
        if not re.fullmatch(r"[0-9a-f]{32}", contribution_id) or not re.fullmatch(r"[A-Za-z0-9_-]{32,64}", withdrawal_token):
            raise HTTPException(422, "A valid private withdrawal receipt is required before saving.")
        if not consent or consent_version != CONSENT_VERSION:
            raise HTTPException(422, "Explicit current contribution consent is required.")
        if len(corrected_text) > 4000 or len(feedback) > 2000:
            raise HTTPException(422, "Contribution text is too long.")
        conv = engine._live(conversation_id)
        turn = conv.turns.get(turn_id)
        if not turn:
            raise HTTPException(404, "No recognized turn exists for this contribution.")
        audio = file.file.read(MAX_UPLOAD_BYTES + 1)
        info = inspect_upload(audio)
        if info['format'] != 'wav':
            raise HTTPException(415, "Contributions must use the browser WAV recording.")
        return store.save(audio, {"consent_version": CONSENT_VERSION, "scope": "private Boli Zero evaluation and future model improvement; no voice cloning or public redistribution",
                                 "audio": info, "recognized_text_unverified": turn.recognized_text, "reply_text_unverified": turn.reply_text,
                                 "corrected_text_user_supplied": corrected_text, "feedback": feedback, "training_status": "collected_not_trained",
                                 "capture": "browser capture-rate mono PCM16; device/browser may process microphone audio", "recognition": turn.dev.get('recognition')}, {"contribution_id": contribution_id, "withdrawal_token": withdrawal_token})

    @app.delete("/api/contributions/{cid}")
    def withdraw(cid: str, authorization: str = Header("")):
        if not authorization.startswith("Bearer ") or not store.withdraw(cid, authorization[7:]):
            raise HTTPException(404, "Contribution or receipt not found.")
        return {"deleted": True}
