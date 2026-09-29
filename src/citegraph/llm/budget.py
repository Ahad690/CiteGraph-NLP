"""A daily ceiling on provider spend, recorded where a purge cannot reach it.

THE SHAPE OF THE LIMIT IS DELIBERATE, and it is a DAILY budget rather than a
per-run one. A per-run ceiling stops a run part-way through and hands back a
broken artifact. The Terminux project measured the reason: one real turn
accumulated 1.6M prompt tokens, because every round re-sends the conversation,
so runaway cost is quadratic, not linear. Their budget bounds a TURN by tokens
and lets the model close out with what it has; the equivalent here is to let a
run finish and stop the NEXT one.

So: the day has a ceiling. Reaching it means provider calls stop being made and
the deterministic path carries on. A run must always finish.

WHY AN APPEND-ONLY FILE RATHER THAN THE DATABASE. Terminus keeps its spend
record in `var/cost_record.jsonl` for a reason that was learned the hard way: on
2026-09-04 the ledger read $0.1435 across 128 rows in the morning and $0.0317
across 19 in the afternoon, because a purge of test accounts removed their rows.
Nothing was mis-billed and half the evidence of spend was simply gone. This
project purges test artifacts too, so the record goes to a file for the same
reason.

AN UNPRICED CALL IS RECORDED, NOT SKIPPED. A provider that does not report a
cost gets its tokens recorded and its cost estimated from a configured rate. A
budget that silently ignored unpriced calls would be a budget with a hole in it.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from citegraph.config import settings

logger = logging.getLogger(__name__)

#: Used only when a provider reports tokens but no price. Deliberately
#: conservative: over-estimating our own cost is recoverable, under-estimating is
#: a surprise bill.
FALLBACK_USD_PER_MTOK = 1.00

_lock = Lock()


def _today() -> str:
    """The UTC day, as an ISO date.

    UTC and not date.today(), because the record's timestamp is already UTC.
    Pairing a UTC timestamp with a local-time day key means the same entry is
    filed under a different day depending on where the server is, so a daily
    ceiling resets at a boundary nobody can state, and the ledger cannot be
    audited against a wall clock. A budget that is meant to be bounded has to
    have a day that means one thing.
    """
    return datetime.now(timezone.utc).date().isoformat()


def _record_path() -> Path:
    path = Path(settings.provider_cost_record)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[3] / path
    return path


def _append(row: dict) -> None:
    """Append one row. Never rewrites, so a purge cannot remove history."""
    path = _record_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        # Losing the cost record is worse than losing the ceiling, but failing a
        # research run because a directory is unwritable is worse still. Say so
        # and carry on.
        logger.error("provider cost record could not be written: %s", exc)


def spend_today() -> float:
    """What has been spent since midnight UTC.

    Read from the file rather than from memory so a restart does not reset the
    budget. A restart that silently refills the daily ceiling is a budget with no
    limit in it.
    """
    path = _record_path()
    if not path.is_file():
        return 0.0
    today = _today()
    total = 0.0
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("day") == today and row.get("cost_usd") is not None:
                    total += float(row["cost_usd"])
    except OSError as exc:
        logger.error("provider cost record could not be read: %s", exc)
    return total


def budget_remaining() -> float:
    return max(0.0, settings.provider_daily_budget_usd - spend_today())


def budget_exhausted() -> bool:
    return spend_today() >= settings.provider_daily_budget_usd


def record(
    provider: str,
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float | None,
) -> float:
    """Record one call and return the cost attributed to it.

    A provider that reports its own cost is believed. One that does not is
    estimated from tokens, and the row records which it was, because a future
    reader cannot otherwise tell a measured price from a guess.
    """
    with _lock:
        if cost_usd is None:
            cost_usd = (input_tokens + output_tokens) / 1_000_000 * FALLBACK_USD_PER_MTOK
            price_source = "estimated"
        else:
            price_source = "reported"

        _append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "day": _today(),
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
                "price_source": price_source,
            }
        )
        return cost_usd


def remaining_summary() -> str:
    """For a log line or an operator check. Contains no key material."""
    return (
        f"provider budget: ${spend_today():.4f} of "
        f"${settings.provider_daily_budget_usd:.2f} used today, "
        f"${budget_remaining():.4f} remaining"
    )
