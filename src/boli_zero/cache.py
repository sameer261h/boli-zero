"""On-disk cache for every API request/response, keyed by a deterministic hash.

The key covers the service, operation, JSON params and the sha256 of any file
bytes (not file names), so identical audio or text is never sent, or billed, twice.
Credentials are never part of the key or the stored record.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def request_record(operation: str, params: dict, files: dict[str, bytes]) -> dict:
    return record_from_hashes(operation, params, {name: sha256_hex(data) for name, data in files.items()})


def record_from_hashes(operation: str, params: dict, file_hashes: dict[str, str]) -> dict:
    """The same record when the files' sha256 is already known, so a lookup does not need to read the audio."""
    return {"operation": operation, "params": params, "files": dict(sorted(file_hashes.items()))}


def request_key(service: str, record: dict) -> str:
    payload = json.dumps({"service": service, **record}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256_hex(payload.encode("utf-8"))


class ResponseCache:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _paths(self, service: str, key: str) -> tuple[Path, Path]:
        folder = self.root / service / key[:2]
        return folder / f"{key}.json", folder / f"{key}.bin"

    def get(self, service: str, key: str) -> tuple[dict, bytes | None] | None:
        meta_path, blob_path = self._paths(service, key)
        if not meta_path.exists():
            return None
        entry = json.loads(meta_path.read_text(encoding="utf-8"))
        blob = blob_path.read_bytes() if entry["has_blob"] else None
        return entry["response"], blob

    def get_entry(self, service: str, key: str) -> dict | None:
        """The stored entry (request, response, cached_at) or None. Never touches the network."""
        meta_path, _ = self._paths(service, key)
        return json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else None

    def put(self, service: str, key: str, record: dict, response: dict, blob: bytes | None, origin: dict | None = None) -> None:
        meta_path, blob_path = self._paths(service, key)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        if blob is not None:
            self._atomic_write(blob_path, blob)
        entry = {
            "request": record,
            "response": response,
            "has_blob": blob is not None,
            "origin": origin,  # {'via': 'http', 'host': ...} or {'via': 'injected transport'}; None for entries saved before this existed
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        # Metadata is written last so a half-written entry is never read as a hit.
        self._atomic_write(meta_path, json.dumps(entry, ensure_ascii=False, indent=2).encode("utf-8"))

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
