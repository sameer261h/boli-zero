"""Shared test helpers. All text here is obvious placeholder content, not real Hindi or Bhojpuri."""
import pytest

from boli_zero.config import GnaniConfig
from boli_zero.schema import DatasetRecord


def make_records(n, speakers=None, split="train"):
    return [
        DatasetRecord(
            id=f"id{i:03d}", anchor_language="hi", target_language="bho",
            anchor_text=f"anchor placeholder {i}", target_text=f"target placeholder {i}",
            speaker_id=f"spk{i % speakers}" if speakers else None,
            source="test fixture", license="test only", split=split,
        )
        for i in range(n)
    ]


@pytest.fixture
def config(tmp_path):
    return GnaniConfig(api_key=None, base_url=None, auth_header=None, cache_dir=tmp_path / "cache")


class StubTransport:
    """Stands in for the unwritten HTTP layer; records every request that 'left the machine'."""

    def __init__(self, reply=None):
        self.reply = reply or (lambda operation, params, files: ({"text": "stub output"}, None))
        self.requests = []

    def __call__(self, operation, params, files):
        self.requests.append((operation, params, dict(files)))
        return self.reply(operation, params, files)
