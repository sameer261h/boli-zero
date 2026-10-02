"""Paths and environment config. No Gnani endpoint or credential is hardcoded here."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SPLITS_DIR = ROOT / "data" / "splits"
EXPERIMENTS_DIR = ROOT / "experiments"
OUTPUTS_DIR = ROOT / "outputs"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Tiny .env reader: KEY=VALUE lines, existing environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _env(name: str) -> str | None:
    return os.environ.get(name) or None


@dataclass(frozen=True)
class GnaniConfig:
    api_key: str | None
    base_url: str | None
    auth_header: str | None
    cache_dir: Path

    @classmethod
    def from_env(cls) -> "GnaniConfig":
        load_dotenv()
        cache = _env("BOLI_CACHE_DIR")
        return cls(
            api_key=_env("GNANI_API_KEY"),
            base_url=_env("GNANI_BASE_URL"),
            auth_header=_env("GNANI_AUTH_HEADER"),
            cache_dir=Path(cache) if cache else ROOT / ".cache" / "api",
        )

    @property
    def credentials_present(self) -> bool:
        return bool(self.api_key and self.base_url and self.auth_header)
