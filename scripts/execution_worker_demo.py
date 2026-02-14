from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, Optional

import httpx


def _env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise ValueError(f"missing required env: {name}")
    return val


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return int(val)


async def _post(client: httpx.AsyncClient, url: str, token: str, payload: Dict[str, Any]) -> httpx.Response:
    return await client.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )


async def _heartbeat(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    run_id: int,
    worker_id: str,
    lease_seconds: int,
    heartbeat_every: int,
    stop: asyncio.Event,
) -> None:
    url = f"{base_url}/api/v1/executions/runs/{run_id}/lease"
    while not stop.is_set():
        await asyncio.sleep(heartbeat_every)
        if stop.is_set():
            break
        resp = await _post(client, url, token, {"worker_id": worker_id, "lease_seconds": lease_seconds})
        if resp.status_code != 200:
            print(f"[lease] status={resp.status_code} body={resp.text}")
            stop.set()
            break


async def _worker_registry_heartbeat(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    worker_id: str,
    heartbeat_every: int,
    stop: asyncio.Event,
) -> None:
    url = f"{base_url}/api/v1/executions/workers/heartbeat"
    while not stop.is_set():
        resp = await _post(client, url, token, {"worker_id": worker_id})
        if resp.status_code != 200:
            print(f"[worker-heartbeat] status={resp.status_code} body={resp.text}")
        await asyncio.sleep(heartbeat_every)


async def main() -> int:
    base_url = os.getenv("HUBEX_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    token = _env("HUBEX_TOKEN")
    definition_key = os.getenv("DEFINITION_KEY", "").strip()
    worker_id = _env("WORKER_ID")
    lease_seconds = _env_int("LEASE_SECONDS", 60)
    heartbeat_every = _env_int("HEARTBEAT_EVERY", 30)
    poll_delay = _env_int("POLL_DELAY", 2)
    max_runs = _env_int("MAX_RUNS", 0)
    run_once_raw = os.getenv("RUN_ONCE", "")
    run_once = run_once_raw.lower() in {"1", "true", "yes"}
    if run_once and max_runs <= 0:
        max_runs = 1

    async with httpx.AsyncClient() as client:
        registry_stop = asyncio.Event()
        registry_task = asyncio.create_task(
            _worker_registry_heartbeat(
                client,
                base_url,
                token,
                worker_id,
                heartbeat_every,
                registry_stop,
            )
        )
        try:
            runs_completed = 0
            while True:
                payload: Dict[str, Any] = {
                    "worker_id": worker_id,
                    "lease_seconds": lease_seconds,
                }
                if definition_key:
                    payload["definition_key"] = definition_key

                resp = await _post(
                    client,
                    f"{base_url}/api/v1/executions/runs/claim-next",
                    token,
                    payload,
                )

                if resp.status_code == 404:
                    await asyncio.sleep(poll_delay)
                    continue
                if resp.status_code != 200:
                    print(f"[claim-next] status={resp.status_code} body={resp.text}")
                    await asyncio.sleep(poll_delay)
                    continue

                run = resp.json()
                run_id = run["id"]
                print(f"[claim-next] claimed run_id={run_id}")

                stop = asyncio.Event()
                hb_task = asyncio.create_task(
                    _heartbeat(
                        client,
                        base_url,
                        token,
                        run_id,
                        worker_id,
                        lease_seconds,
                        heartbeat_every,
                        stop,
                    )
                )

                try:
                    await asyncio.sleep(2)
                    finalize = await _post(
                        client,
                        f"{base_url}/api/v1/executions/runs/{run_id}/finalize",
                        token,
                        {"status": "completed", "output_json": {"ok": True}, "worker_id": worker_id},
                    )
                    if finalize.status_code != 200:
                        print(f"[finalize] status={finalize.status_code} body={finalize.text}")
                    else:
                        print(f"[finalize] ok run_id={run_id}")
                except Exception as exc:
                    print(f"[worker] exception={exc!r}")
                    release = await _post(
                        client,
                        f"{base_url}/api/v1/executions/runs/{run_id}/release",
                        token,
                        {"worker_id": worker_id},
                    )
                    print(f"[release] status={release.status_code}")
                finally:
                    stop.set()
                    await hb_task

                runs_completed += 1
                if max_runs and runs_completed >= max_runs:
                    return 0
        finally:
            registry_stop.set()
            await registry_task


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        raise SystemExit(1)
