"""A content-addressed cache for provider answers.

WHY THIS IS KEYED BY CONTENT AND NOT BY ARGUMENT LIST

A Jev answer is a pure function of (instructions, criteria, question type) and the
model id. So the cache key is a hash of the exact request body plus the model,
and a hit means the same question was already answered by the same model. There
is no "which run was this" component, and that is the point: a cache keyed by run
id would miss on every run and be a cache in name only.

THE KEY IS WHAT MAKES IT HONEST

Including the model id is not an optimisation detail. `jev-latest` moves under a
fixed request, so a cache without it would serve last month's answer under
today's model name and report it as current. Pin the model and the cache
invalidates itself when the pin changes, which is what you want from a
reproducibility tool.

WHAT IS NOT CACHED, AND WHY THAT MATTERS

A cached answer records the cost that was actually paid the first time and
reports it again. It does NOT record a new charge against today's ceiling,
because no money changed hands. The budget is a record of real spend, so a cache
hit that inflated it would make the daily ceiling measure something other than
spend. A test asserts this, because a cache that lies about cost is worse than no
cache.

A CACHE HIT IS NOT A PROVIDER CALL

That is the property worth having and the one worth testing: on a hit the
transport is never touched. A cache that still opens a connection and asks is
slower than no cache and pays for the privilege.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from citegraph.config import settings

logger = logging.getLogger(__name__)

#: Bumped when the SHAPE of a cached record changes, so an old file is a miss
#: rather than a KeyError. Version 1 is the first layout.
SCHEMA_VERSION = 1


def cache_key(provider: str, model: str, body: dict[str, Any]) -> str:
    """A stable digest of the request.

    sort_keys so that a dict built in a different order still hits. The usual
    reason a content-hash cache silently never hits is that two equal objects
    serialise differently, and then the cache is a slow copy of the network.
    """
    canonical = json.dumps(
        {"provider": provider, "model": model, "body": body},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ProviderCache:
    """Append-only JSONL cache on disk, one record per line.

    JSONL rather than a single JSON blob or sqlite: an append cannot corrupt the
    file, so a crash mid-write costs the last record and nothing else, and a
    reader can stream it without loading the whole history.
    """

    def __init__(self, path: str | Path | None = None, ttl_s: float | None = None) -> None:
        self.path = Path(path or settings.provider_cache_path)
        self.ttl_s = settings.provider_cache_ttl_s if ttl_s is None else ttl_s

    # --- reads ---------------------------------------------------------------

    def get(self, key: str) -> dict[str, Any] | None:
        """The cached body for a key, or None.

        Any malformed line is skipped rather than raised. A cache is an
        optimisation, and an optimisation that can take down a run is not one.
        """
        try:
            raw = self.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            if record.get("version") != SCHEMA_VERSION:
                continue
            if record.get("key") != key:
                continue
            if self._expired(record):
                continue
            body = record.get("body")
            if isinstance(body, dict):
                return body
        return None

    def _expired(self, record: dict[str, Any]) -> bool:
        if self.ttl_s <= 0:
            return False
        stored = record.get("stored_at")
        if not isinstance(stored, (int, float)):
            # An entry with no usable timestamp is treated as expired rather
            # than as fresh. Serving an answer of unknown age under the current
            # model name is the failure this whole cache is designed to prevent.
            return True
        return (time.time() - float(stored)) > self.ttl_s

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    # --- writes --------------------------------------------------------------

    def put(self, key: str, body: dict[str, Any], *, provider: str, model: str) -> None:
        """Record an answer. Never raises: a cache that cannot be written is a
        slow run, not a broken one."""
        record = {
            "version": SCHEMA_VERSION,
            "key": key,
            "provider": provider,
            "model": model,
            "body": body,
            "stored_at": time.time(),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except OSError as exc:
            logger.warning("provider cache: could not write (%s)", exc.__class__.__name__)

    def clear(self) -> None:
        try:
            os.remove(self.path)
        except OSError:
            pass


def _cache() -> ProviderCache:
    return ProviderCache()


async def cached_post(
    provider: Any,
    path: str,
    body: dict[str, Any],
    *,
    model: str,
) -> tuple[dict[str, Any], bool]:
    """POST through a provider, reusing a cached answer when there is one.

    Returns (body, from_cache). The caller records usage and cost either way;
    a hit reports the usage stored with the original answer rather than a fresh
    charge, because a hit spends nothing.

    The response object is not returned. Both callers read the model and the
    usage out of the parsed body, so carrying it would be a second way to get
    the same fact, and a way to get a DIFFERENT one if the two ever disagreed.
    """
    cache = _cache()
    key = cache_key(provider.name, model, body)

    cached = cache.get(key)
    if cached is not None:
        logger.debug("provider cache hit for %s", provider.name)
        return cached, True

    result, _response = await provider.post_json(path, body)
    cache.put(key, result, provider=provider.name, model=model)
    return result, False


__all__ = ["SCHEMA_VERSION", "ProviderCache", "cache_key", "cached_post"]
