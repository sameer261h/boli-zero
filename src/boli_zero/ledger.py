"""Append-only record of Gnani requests and an estimated-spend cap. Estimates only: the console is the authority."""
from __future__ import annotations

import json
import math
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

PRICE_INR_PER_MINUTE = 27.0 / 60  # docs pricing page, STT REST (Rs 27 per hour)


def estimate_cost_inr(duration_s: float) -> float:
    """Conservative: audio rounded up to the next 0.05 minute. The console billed Rs 0.12 to 0.21 for 16 to 28 s clips."""
    return round(PRICE_INR_PER_MINUTE * math.ceil(duration_s / 60 / 0.05) * 0.05, 2)


class BudgetExceeded(RuntimeError):
    pass


class Ledger:
    def __init__(self, path: Path, budget_inr: float):
        self.path, self.budget_inr = Path(path), float(budget_inr)
        self._lock = threading.Lock()

    def events(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def summary(self) -> dict:
        events = self.events()
        live_ok = [e for e in events if e["outcome"] == "success"]
        failed = [e for e in events if e["outcome"] not in ("success", "cache_replay")]
        spent = round(sum(e["cost_estimate_inr"] for e in live_ok), 2)
        return {"budget_inr": self.budget_inr, "estimated_spent_inr": spent, "remaining_inr": round(self.budget_inr - spent, 2),
                "successful_live_calls": len(live_ok), "failed_calls": len(failed),
                "failures_by_outcome": {o: sum(e["outcome"] == o for e in failed) for o in sorted({e["outcome"] for e in failed})},
                "cache_replays": sum(e["outcome"] == "cache_replay" for e in events)}

    def check(self, cost_inr: float) -> None:
        if self.summary()["estimated_spent_inr"] + cost_inr > self.budget_inr:
            raise BudgetExceeded(f"estimated spend would pass the Rs {self.budget_inr:g} cap for this trial")

    def record(self, **event) -> None:
        line = json.dumps({"time_utc": datetime.now(timezone.utc).isoformat(), **event}, ensure_ascii=False) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())


class ClaudeUsage:
    """Append-only record of Claude requests with a hard cap on estimated dollars and on request count.
    Costs come from the token counts the API reports, priced from the model overview page (checked 2026-10-03)."""

    def __init__(self, path: Path, budget_usd: float = 0.25, max_requests: int = 40):
        self.path, self.budget_usd, self.max_requests = Path(path), float(budget_usd), int(max_requests)
        self._lock = threading.Lock()

    def events(self) -> list[dict]:
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()] if self.path.exists() else []

    def summary(self) -> dict:
        events = self.events()
        done = [e for e in events if e["outcome"] == "success"]
        spent = round(sum(e["cost_usd"] for e in done), 6)
        return {"budget_usd": self.budget_usd, "estimated_spent_usd": spent, "remaining_usd": round(self.budget_usd - spent, 6),
                "requests_sent": len(events), "max_requests": self.max_requests, "successful": len(done),
                "input_tokens": sum(e.get("input_tokens", 0) for e in done), "output_tokens": sum(e.get("output_tokens", 0) for e in done)}

    def check(self, worst_case_usd: float) -> None:
        s = self.summary()
        if s["requests_sent"] >= self.max_requests:
            raise BudgetExceeded(f"the trial's cap of {self.max_requests} Claude requests is reached")
        if s["estimated_spent_usd"] + worst_case_usd > self.budget_usd:
            raise BudgetExceeded(f"a Claude request could pass the ${self.budget_usd:g} cap for this trial")

    def record(self, **event) -> None:
        line = json.dumps({"time_utc": datetime.now(timezone.utc).isoformat(), **event}, ensure_ascii=False) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
