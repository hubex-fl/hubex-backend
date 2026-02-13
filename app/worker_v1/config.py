from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class WorkerConfig:
    base_url: str
    token: str
    worker_id: str
    lease_seconds: int
    heartbeat_every: int
    poll_delay: float
    definition_key: str | None
    max_runs: int | None


def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise ValueError(f"missing required env: {name}")
    return val


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return int(val)


def _env_float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return float(val)


def load_config_from_env() -> WorkerConfig:
    base_url = os.getenv("HUBEX_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    token = _env("HUBEX_TOKEN")
    worker_id = _env("WORKER_ID")
    lease_seconds = _env_int("LEASE_SECONDS", 60)
    heartbeat_every = _env_int("HEARTBEAT_EVERY", 20)
    poll_delay = _env_float("POLL_DELAY", 2.0)
    definition_key = os.getenv("DEFINITION_KEY")
    if definition_key is not None and definition_key.strip() == "":
        definition_key = None
    max_runs_raw = os.getenv("MAX_RUNS")
    max_runs = int(max_runs_raw) if max_runs_raw not in (None, "") else None

    if not token:
        raise ValueError("HUBEX_TOKEN is required")
    if not (1 <= len(worker_id) <= 96):
        raise ValueError("WORKER_ID must be 1..96 chars")
    if not (1 <= lease_seconds <= 3600):
        raise ValueError("LEASE_SECONDS must be 1..3600")
    if not (1 <= heartbeat_every <= lease_seconds):
        raise ValueError("HEARTBEAT_EVERY must be 1..LEASE_SECONDS")
    if poll_delay <= 0:
        raise ValueError("POLL_DELAY must be > 0")
    if definition_key is not None and not (1 <= len(definition_key) <= 96):
        raise ValueError("DEFINITION_KEY must be 1..96 chars")
    if max_runs is not None and max_runs <= 0:
        raise ValueError("MAX_RUNS must be > 0")

    return WorkerConfig(
        base_url=base_url,
        token=token,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        heartbeat_every=heartbeat_every,
        poll_delay=poll_delay,
        definition_key=definition_key,
        max_runs=max_runs,
    )
