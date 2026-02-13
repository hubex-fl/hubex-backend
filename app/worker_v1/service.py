from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import httpx

from .client import ApiResponse, post_json
from .config import WorkerConfig


class WorkerMisconfigError(RuntimeError):
    pass


def _log(event: str, **fields: Any) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))


def _claim_payload(config: WorkerConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "worker_id": config.worker_id,
        "lease_seconds": config.lease_seconds,
    }
    if config.definition_key:
        payload["definition_key"] = config.definition_key
    return payload


def _finalize_payload(run: dict[str, Any], config: WorkerConfig) -> dict[str, Any]:
    return {
        "status": "completed",
        "output_json": {
            "ok": True,
            "worker_id": config.worker_id,
            "echo": run.get("input_json"),
        },
        "worker_id": config.worker_id,
    }


def _is_misconfig(resp: ApiResponse) -> bool:
    return resp.status_code in {400, 401, 403} or (
        resp.status_code == 409 and "worker not subscribed" in resp.text
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _heartbeat_loop(
    client: httpx.AsyncClient,
    config: WorkerConfig,
    stop: asyncio.Event,
) -> None:
    url = f"{config.base_url}/api/v1/executions/workers/heartbeat"
    while not stop.is_set():
        resp = await post_json(
            client,
            url,
            config.token,
            {"worker_id": config.worker_id},
        )
        if resp.status_code != 200:
            _log("worker_heartbeat_failed", status=resp.status_code, body=resp.text)
        try:
            await asyncio.wait_for(stop.wait(), timeout=config.heartbeat_every)
        except asyncio.TimeoutError:
            continue


async def _lease_loop(
    client: httpx.AsyncClient,
    config: WorkerConfig,
    run_id: int,
    stop: asyncio.Event,
) -> None:
    url = f"{config.base_url}/api/v1/executions/runs/{run_id}/lease"
    while not stop.is_set():
        resp = await post_json(
            client,
            url,
            config.token,
            {"worker_id": config.worker_id, "lease_seconds": config.lease_seconds},
        )
        if resp.status_code != 200:
            _log("lease_failed", run_id=run_id, status=resp.status_code, body=resp.text)
            stop.set()
            break
        try:
            await asyncio.wait_for(stop.wait(), timeout=config.heartbeat_every)
        except asyncio.TimeoutError:
            continue


async def run_worker(
    config: WorkerConfig,
    client: httpx.AsyncClient,
) -> int:
    _log("worker_start", config=asdict(config))

    registry_stop = asyncio.Event()
    registry_task = asyncio.create_task(_heartbeat_loop(client, config, registry_stop))

    runs_completed = 0
    try:
        while True:
            claim_url = f"{config.base_url}/api/v1/executions/runs/claim-next"
            resp = await post_json(client, claim_url, config.token, _claim_payload(config))
            if resp.status_code == 404:
                await asyncio.sleep(config.poll_delay)
                continue
            if _is_misconfig(resp):
                _log("claim_misconfig", status=resp.status_code, body=resp.text)
                raise WorkerMisconfigError(resp.text)
            if resp.status_code == 409:
                _log("claim_conflict", status=resp.status_code, body=resp.text)
                await asyncio.sleep(config.poll_delay)
                continue
            if resp.status_code != 200:
                _log("claim_error", status=resp.status_code, body=resp.text)
                await asyncio.sleep(config.poll_delay)
                continue

            run = resp.json or {}
            run_id = int(run.get("id", 0))
            if run_id == 0:
                _log("claim_invalid", body=resp.text)
                await asyncio.sleep(config.poll_delay)
                continue

            _log("claim_ok", run_id=run_id)
            stop = asyncio.Event()
            lease_task = asyncio.create_task(_lease_loop(client, config, run_id, stop))
            try:
                finalize_url = f"{config.base_url}/api/v1/executions/runs/{run_id}/finalize"
                finalize_payload = _finalize_payload(run, config)
                finalize_resp = await post_json(client, finalize_url, config.token, finalize_payload)
                if finalize_resp.status_code != 200:
                    _log(
                        "finalize_failed",
                        run_id=run_id,
                        status=finalize_resp.status_code,
                        body=finalize_resp.text,
                    )
                    release_url = f"{config.base_url}/api/v1/executions/runs/{run_id}/release"
                    release_resp = await post_json(
                        client,
                        release_url,
                        config.token,
                        {"worker_id": config.worker_id},
                    )
                    _log(
                        "release_attempted",
                        run_id=run_id,
                        status=release_resp.status_code,
                    )
                else:
                    _log("finalize_ok", run_id=run_id)
            finally:
                stop.set()
                await lease_task

            runs_completed += 1
            if config.max_runs is not None and runs_completed >= config.max_runs:
                _log("worker_done", runs_completed=runs_completed)
                return 0
    except WorkerMisconfigError:
        raise
    except Exception as exc:
        _log("worker_error", error=repr(exc))
        return 1
    finally:
        registry_stop.set()
        await registry_task
        _log("worker_stop", ts=_now_iso())
