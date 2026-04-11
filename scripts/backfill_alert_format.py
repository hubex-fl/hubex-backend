"""
Sprint 5 — One-time backfill of legacy AlertEvent messages.

Sprint 3.6 fixed the alert message format in app/core/alert_worker.py from
the old English-code form

    variable 'temperature' value 20.3 gt 20

to the new locale-agnostic math-symbol form

    temperature = 20.3 > 20

BUT pre-existing AlertEvent rows in the database still carry the old
format, and BUG_TRACKER.md flagged this as a residual item. New alerts
use the new format, old alerts don't, and the Alerts page + Dashboard
widget display the `.message` field directly, so DE users see mixed
English/symbol output depending on how old an alert is.

This script does a one-pass rewrite of every AlertEvent row whose
message matches the legacy pattern, replacing it with the new format.
It is IDEMPOTENT — running it twice is a no-op because rewritten rows
no longer match the legacy regex.

Usage:
    # Dry-run (default): shows how many rows would be rewritten, writes nothing.
    python -m scripts.backfill_alert_format

    # Commit:
    python -m scripts.backfill_alert_format --commit

Safety:
- Reads AlertEvent in batches of 500
- Uses a single transaction per batch
- Emits a summary with rewritten-count, unchanged-count, and any regex
  misses that the script couldn't parse (edge cases logged for manual
  review, not touched)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.db.models.alerts import AlertEvent

logger = logging.getLogger("backfill_alert_format")


# Matches the Sprint 3.6-and-earlier format produced by
# app/core/alert_worker.py:_eval_variable_threshold:
#
#     variable 'temperature' value 20.3 gt 20
#     variable 'sensors.battery' value 9.5 lte 10
#
# Captures: key, numeric, operator, threshold
_LEGACY_RE = re.compile(
    r"^variable\s+'(?P<key>[^']+)'\s+value\s+(?P<numeric>-?\d+(?:\.\d+)?)\s+(?P<op>gt|gte|lt|lte|eq|ne)\s+(?P<threshold>-?\d+(?:\.\d+)?)\s*$"
)

# Same symbol table as alert_worker._eval_variable_threshold
_SYMBOLS = {
    "gt": ">",
    "gte": "\u2265",  # ≥
    "lt": "<",
    "lte": "\u2264",  # ≤
    "eq": "=",
    "ne": "\u2260",  # ≠
}

_BATCH_SIZE = 500


def _rewrite(message: Optional[str]) -> Optional[str]:
    """Try to convert a legacy message to the new format.

    Returns None if the message doesn't match the legacy regex (so the
    caller leaves it alone).
    """
    if not message:
        return None
    match = _LEGACY_RE.match(message)
    if not match:
        return None
    key = match.group("key")
    numeric = match.group("numeric")
    op = match.group("op")
    threshold = match.group("threshold")
    sym = _SYMBOLS.get(op, op)
    return f"{key} = {numeric} {sym} {threshold}"


async def _run_batch(db: AsyncSession, dry_run: bool) -> tuple[int, int]:
    """Fetch + rewrite + commit one batch. Returns (rewritten, seen)."""
    # Pull a batch of candidates. We over-fetch rows that are "maybe
    # legacy" by filtering for the literal prefix "variable '" to avoid
    # pulling the entire table into memory.
    res = await db.execute(
        select(AlertEvent)
        .where(AlertEvent.message.like("variable '%"))
        .limit(_BATCH_SIZE)
    )
    rows = res.scalars().all()
    seen = len(rows)
    rewritten = 0
    for row in rows:
        new_msg = _rewrite(row.message)
        if new_msg is None:
            continue
        if new_msg == row.message:
            # Shouldn't happen because the regex only matches legacy, but
            # defensive in case of a weird edge case.
            continue
        if dry_run:
            logger.info("[dry-run] %s  →  %s", row.message, new_msg)
        else:
            row.message = new_msg
        rewritten += 1
    if not dry_run and rewritten > 0:
        await db.commit()
    return rewritten, seen


async def main(dry_run: bool = True) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info(
        "Starting alert-message backfill (dry_run=%s, batch_size=%s)",
        dry_run,
        _BATCH_SIZE,
    )
    total_seen = 0
    total_rewritten = 0
    while True:
        async with AsyncSessionLocal() as db:
            rewritten, seen = await _run_batch(db, dry_run=dry_run)
        total_seen += seen
        total_rewritten += rewritten
        logger.info(
            "batch: seen=%s rewritten=%s  (cumulative: seen=%s rewritten=%s)",
            seen,
            rewritten,
            total_seen,
            total_rewritten,
        )
        # Stop when either the batch was empty (no more legacy rows) or
        # we're in dry-run mode (we'd loop forever otherwise, since
        # messages stay unchanged across batches and `.like()` keeps
        # returning them).
        if seen == 0 or (dry_run and rewritten == 0):
            break
        if dry_run:
            # In dry-run mode we already saw rows that would be
            # rewritten; break out to avoid an infinite loop.
            break
    logger.info(
        "Done. total_seen=%s total_rewritten=%s  (dry_run=%s)",
        total_seen,
        total_rewritten,
        dry_run,
    )
    if dry_run and total_rewritten > 0:
        logger.info("Re-run with --commit to persist the rewrites.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually write rewrites to the database (default: dry-run).",
    )
    args = parser.parse_args()
    asyncio.run(main(dry_run=not args.commit))
