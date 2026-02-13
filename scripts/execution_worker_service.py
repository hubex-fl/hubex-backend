from __future__ import annotations

import argparse
import asyncio
import sys

import httpx

from app.worker_v1.config import load_config_from_env
from app.worker_v1.service import WorkerMisconfigError, run_worker


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HUBEX execution worker v1")
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument("--definition-key", type=str, default=None)
    return parser.parse_args()


def _override_config(config, args: argparse.Namespace):
    data = config.__dict__.copy()
    if args.max_runs is not None:
        data["max_runs"] = args.max_runs
    if args.definition_key is not None:
        definition_key = args.definition_key.strip() or None
        data["definition_key"] = definition_key
    return config.__class__(**data)


async def _main() -> int:
    args = _parse_args()
    config = load_config_from_env()
    config = _override_config(config, args)

    async with httpx.AsyncClient() as client:
        try:
            return await run_worker(config, client)
        except WorkerMisconfigError:
            return 2


def main() -> int:
    try:
        return asyncio.run(_main())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
