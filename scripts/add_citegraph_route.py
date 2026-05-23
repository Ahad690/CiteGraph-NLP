"""Idempotently inject a `location /citegraph/` block into an existing
Nginx server config so the CiteGraph-NLP backend is reachable behind the
shared `hetzner-api.duckdns.org` reverse proxy.

The script:
  1. Removes any legacy `include /etc/nginx/citegraph-proxy.conf;` lines.
  2. Removes any pre-existing `location /citegraph/` blocks (handles nesting).
  3. Validates that the config has the expected `hetzner-api.duckdns.org`
     server block and the `/penora/` location used as an insertion anchor.
  4. Inserts a clean, fully-formed `/citegraph/` location block immediately
     after the closing brace of the `/penora/` location block.

Exit codes:
    0  Inserted or already correctly present.
    1  Config file argument missing / unreadable.
    2  Expected server block or anchor not found.
    3  Resulting config failed shape validation.

The output is intended to be diffable in CI logs without leaking the rest
of the file. Pass `--quiet` to suppress per-step messages.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

CITEGRAPH_BLOCK: List[str] = [
    "",
    "    # === CiteGraph backend (port 8002) ===",
    "    location /citegraph/ {",
    "        proxy_pass http://127.0.0.1:8002/;",
    "        proxy_set_header Host $host;",
    "        proxy_set_header X-Real-IP $remote_addr;",
    "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
    "        proxy_set_header X-Forwarded-Proto $scheme;",
    "    }",
]

EXACT_LOCATION_DIRECTIVE = "location /citegraph/ {"
LEGACY_INCLUDE = "include /etc/nginx/citegraph-proxy.conf"


def strip_legacy_includes(lines: List[str]) -> List[str]:
    """Drop any prior broken include lines."""
    return [l for l in lines if LEGACY_INCLUDE not in l]


def strip_existing_citegraph_blocks(lines: List[str]) -> List[str]:
    """Remove any existing `location /citegraph/ { ... }` blocks (including
    malformed nested ones from earlier deploy attempts), using brace depth."""
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if EXACT_LOCATION_DIRECTIVE in line and "{" in line:
            depth = line.count("{") - line.count("}")
            i += 1
            while i < len(lines) and depth > 0:
                depth += lines[i].count("{") - lines[i].count("}")
                i += 1
            continue
        out.append(line)
        i += 1
    return out


def insert_after_penora(lines: List[str]) -> tuple[List[str], bool]:
    """Insert the CiteGraph block immediately after the `/penora/` location
    closing brace within the `hetzner-api.duckdns.org` server block.

    Returns (new_lines, inserted_flag).
    """
    out: List[str] = []
    in_target_server = False
    server_depth = 0
    in_penora = False
    penora_depth = 0
    inserted = False

    for line in lines:
        out.append(line)
        if inserted:
            continue

        # Track which server block we're in (look for the hetzner-api server_name)
        if "server_name" in line and "hetzner-api" in line:
            in_target_server = True
            # server_depth = 1 means we're inside that server block
            if server_depth == 0:
                server_depth = 1

        if in_target_server:
            # Track penora location boundaries within the target server block
            if "location /penora/" in line and "{" in line:
                in_penora = True
                penora_depth = line.count("{") - line.count("}")
            elif in_penora:
                penora_depth += line.count("{") - line.count("}")
                if penora_depth == 0:
                    in_penora = False
                    out.extend(CITEGRAPH_BLOCK)
                    inserted = True

    return out, inserted


def validate_result(text: str) -> List[str]:
    """Check the generated config for expected shape; return list of errors."""
    errors: List[str] = []
    count = text.count(EXACT_LOCATION_DIRECTIVE)
    if count != 1:
        errors.append(f"Expected exactly one '{EXACT_LOCATION_DIRECTIVE}', found {count}")
    if LEGACY_INCLUDE in text:
        errors.append("Stale citegraph-proxy.conf include remains in config")
    if "proxy_pass http://127.0.0.1:8002/" not in text:
        errors.append("Generated /citegraph/ block is missing the proxy_pass directive")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Path to the Nginx config file")
    parser.add_argument("--quiet", action="store_true", help="Suppress info logs")
    args = parser.parse_args()

    if not args.config.is_file():
        print(f"ERROR: config file not found: {args.config}", file=sys.stderr)
        return 1

    original = args.config.read_text()
    lines = original.split("\n")

    if "hetzner-api" not in original:
        print("ERROR: target server (hetzner-api.duckdns.org) not present in config", file=sys.stderr)
        return 2
    if "location /penora/" not in original:
        print("ERROR: /penora/ insertion anchor not found in config", file=sys.stderr)
        return 2

    lines = strip_legacy_includes(lines)
    lines = strip_existing_citegraph_blocks(lines)
    lines, inserted = insert_after_penora(lines)

    if not inserted:
        print("ERROR: failed to insert /citegraph/ block (no penora close brace within hetzner-api server)", file=sys.stderr)
        return 2

    new_text = "\n".join(lines)
    problems = validate_result(new_text)
    if problems:
        for p in problems:
            print(f"ERROR: {p}", file=sys.stderr)
        return 3

    args.config.write_text(new_text)
    if not args.quiet:
        print("OK: /citegraph/ route inserted after /penora/ block")
    return 0


if __name__ == "__main__":
    sys.exit(main())
