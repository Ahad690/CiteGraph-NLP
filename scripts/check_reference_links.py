"""Follow every reference DOI to the page a reader would actually land on.

verify_references.py asks Crossref whether a DOI has metadata. That is a
weaker claim than the one a reader makes when they click the link: it says the
record exists, not that https://doi.org/<doi> resolves to a live publisher
page. This script makes the stronger check by following the redirect chain.

    python scripts/check_reference_links.py

A publisher that answers 403 to a scripted request is reported separately from
one that answers 404. The first is a bot wall and the link works in a browser;
the second is a dead link and must be fixed.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
from urllib.parse import urlparse

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = os.path.join(ROOT, "thesis", "evidence", "references_verified.json")

HEADERS = {
    "User-Agent": "CiteGraph-NLP reference checker (mailto:subhan.imran@wozify.com)",
    "Accept": "text/html,application/xhtml+xml,*/*",
}
# 403 and 401 mean a publisher refused a script, not that the link is dead.
BOT_WALL = {401, 403, 429}


async def resolve(client: httpx.AsyncClient, entry: dict) -> dict:
    doi = entry["doi"]
    url = f"https://doi.org/{doi}"
    try:
        response = await client.get(url, follow_redirects=True, timeout=30.0)
        return {
            "key": entry["key"],
            "doi": doi,
            "status": response.status_code,
            "final": str(response.url),
            "host": urlparse(str(response.url)).netloc,
            "hops": len(response.history),
        }
    except Exception as exc:  # noqa: BLE001 - reporting, not handling
        return {"key": entry["key"], "doi": doi, "status": None,
                "final": "", "host": "", "error": type(exc).__name__}


async def main() -> int:
    data = json.load(io.open(RECORD, encoding="utf-8"))
    entries = [r for r in data["verified"] if r.get("doi")]
    print(f"following {len(entries)} DOIs through doi.org\n")

    limits = httpx.Limits(max_connections=8)
    async with httpx.AsyncClient(headers=HEADERS, limits=limits) as client:
        semaphore = asyncio.Semaphore(6)

        async def guarded(entry: dict) -> dict:
            async with semaphore:
                return await resolve(client, entry)

        results = await asyncio.gather(*(guarded(e) for e in entries))

    live = [r for r in results if r["status"] and 200 <= r["status"] < 300]
    walled = [r for r in results if r["status"] in BOT_WALL]
    broken = [r for r in results if r not in live and r not in walled]

    for row in sorted(results, key=lambda r: r["key"]):
        mark = ("ok  " if row in live else "wall" if row in walled else "DEAD")
        status = row["status"] if row["status"] else row.get("error", "?")
        print(f"  [{mark}] {row['key']:<24} {str(status):<5} {row['host'][:46]}")

    print(f"\n  reachable          {len(live):>3}")
    print(f"  publisher bot wall {len(walled):>3}  (link works in a browser)")
    print(f"  broken             {len(broken):>3}")
    if broken:
        print("\n  needs fixing:")
        for row in broken:
            print(f"    {row['key']}  {row['doi']}  -> {row['status'] or row.get('error')}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
