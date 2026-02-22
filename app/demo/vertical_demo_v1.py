from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.executions import create_definition, create_run_idempotent
from app.core.security import create_access_token
from app.db.models.audit import AuditV1Entry
from app.db.models.events import EventV1
from app.db.models.executions import ExecutionDefinition, ExecutionRun
from app.db.session import AsyncSessionLocal

DEMO_EVENT_TYPE = "signal.demo_v1"
DEMO_DEFINITION_KEY = "demo.v1"
DEMO_REQUESTED_BY = "demo.vertical_v1"
DEMO_EVENT_STREAM_PREFIX = "device:"
DEMO_SYSTEM_STREAM = "tenant.system"


class DemoSignalNotFound(RuntimeError):
    pass


async def _ensure_definition(db: AsyncSession, key: str) -> ExecutionDefinition:
    existing = await db.scalar(select(ExecutionDefinition).where(ExecutionDefinition.key == key))
    if existing is not None:
        return existing
    return await create_definition(db, key=key, name="Demo v1", version="v1", enabled=True)


async def _find_demo_event(
    db: AsyncSession, *, device_uid: str, trace_id: str
) -> EventV1 | None:
    stream = f"{DEMO_EVENT_STREAM_PREFIX}{device_uid}"
    res = await db.execute(
        select(EventV1)
        .where(
            EventV1.stream == stream,
            EventV1.type == DEMO_EVENT_TYPE,
            EventV1.trace_id == trace_id,
        )
        .order_by(EventV1.id.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def _audit_exists(db: AsyncSession, *, trace_id: str, action: str) -> bool:
    res = await db.execute(
        select(AuditV1Entry.id)
        .where(AuditV1Entry.action == action, AuditV1Entry.trace_id == trace_id)
        .limit(1)
    )
    return res.scalar_one_or_none() is not None


async def _event_exists(db: AsyncSession, *, trace_id: str, event_type: str) -> bool:
    res = await db.execute(
        select(EventV1.id)
        .where(
            EventV1.stream == DEMO_SYSTEM_STREAM,
            EventV1.type == event_type,
            EventV1.trace_id == trace_id,
        )
        .limit(1)
    )
    return res.scalar_one_or_none() is not None


async def create_demo_run_from_event(
    db: AsyncSession,
    *,
    event: EventV1,
    definition_key: str = DEMO_DEFINITION_KEY,
) -> ExecutionRun:
    definition = await _ensure_definition(db, definition_key)
    idempotency_key = f"demo:{event.id}"
    input_json = {
        "correlation_id": event.trace_id,
        "event_id": event.id,
        "stream": event.stream,
        "type": event.type,
        "payload": event.payload,
    }
    run = await create_run_idempotent(
        db,
        definition_id=definition.id,
        idempotency_key=idempotency_key,
        requested_by=DEMO_REQUESTED_BY,
        input_json=input_json,
    )

    if event.trace_id and not await _audit_exists(
        db, trace_id=event.trace_id, action="demo.execution.create"
    ):
        db.add(
            AuditV1Entry(
                actor_type="system",
                actor_id=DEMO_REQUESTED_BY,
                action="demo.execution.create",
                resource=str(run.id),
                audit_metadata={
                    "definition_key": definition.key,
                    "device_uid": event.stream.replace(DEMO_EVENT_STREAM_PREFIX, ""),
                    "event_id": event.id,
                },
                trace_id=event.trace_id,
            )
        )

    if event.trace_id and not await _event_exists(
        db, trace_id=event.trace_id, event_type="execution.demo_v1.created"
    ):
        db.add(
            EventV1(
                stream=DEMO_SYSTEM_STREAM,
                type="execution.demo_v1.created",
                payload={
                    "run_id": run.id,
                    "definition_key": definition.key,
                    "event_id": event.id,
                },
                trace_id=event.trace_id,
            )
        )

    await db.commit()
    return run


async def run_demo_bridge(
    db: AsyncSession,
    *,
    device_uid: str,
    trace_id: str,
    definition_key: str = DEMO_DEFINITION_KEY,
) -> ExecutionRun:
    event = await _find_demo_event(db, device_uid=device_uid, trace_id=trace_id)
    if event is None:
        raise DemoSignalNotFound("demo signal not found")
    return await create_demo_run_from_event(db, event=event, definition_key=definition_key)


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Vertical Demo v1 helpers")
    sub = parser.add_subparsers(dest="cmd", required=True)

    bridge = sub.add_parser("bridge", help="Process demo signal -> execution run")
    bridge.add_argument("--device-uid", required=True)
    bridge.add_argument("--trace-id", required=True)
    bridge.add_argument("--definition-key", default=DEMO_DEFINITION_KEY)

    issue = sub.add_parser("issue-token", help="Issue a demo token with caps")
    issue.add_argument("--user-id", required=True)
    issue.add_argument("--caps", default="")

    args = parser.parse_args()

    if args.cmd == "issue-token":
        caps = [c.strip() for c in str(args.caps).split(",") if c.strip()]
        token = create_access_token(str(args.user_id), caps=caps)
        print(json.dumps({"ok": True, "access_token": token}))
        return 0

    async with AsyncSessionLocal() as db:
        try:
            run = await run_demo_bridge(
                db,
                device_uid=args.device_uid,
                trace_id=args.trace_id,
                definition_key=args.definition_key,
            )
        except DemoSignalNotFound as exc:
            print(json.dumps({"ok": False, "error": str(exc)}))
            return 2

    print(
        json.dumps(
            {
                "ok": True,
                "run_id": run.id,
                "definition_id": run.definition_id,
                "idempotency_key": run.idempotency_key,
            }
        )
    )
    return 0


def main() -> None:
    raise SystemExit(_run())


def _run() -> int:
    import asyncio

    return asyncio.run(_main())


if __name__ == "__main__":
    main()
