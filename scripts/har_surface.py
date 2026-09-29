"""Summarise a HAR into an API surface, without echoing credentials or content.

A HAR with content bodies contains the user's own questions, generated answers,
session cookies and bearer tokens. This reads it to recover structure -- host,
method, path, status, content type, JSON key shape, streaming -- and reports
nothing else. Header values are only ever reported by NAME, and only for the
header names themselves.

Usage:
    python scripts/har_surface.py <file.har> [--stream] [--keys]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

#: Header names whose VALUES are never printed, counted, or stored.
SECRET_HEADERS = {
    "authorization", "cookie", "set-cookie", "proxy-authorization",
    "x-api-key", "x-auth-token", "x-csrf-token", "x-xsrf-token",
    "x-session", "x-amz-security-token", "x-goog-api-key",
}


def shape(value, depth: int = 0):
    """Describe a JSON value's structure. Returns type name or key names.

    Deliberately does not return string values. A field's name and type are
    enough to map an API; the contents are the user's data.
    """
    if depth > 4:
        return "..."
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        # Length only, and only for arrays/objects do we descend.
        return f"string(len~{min(len(value), 9999)})"
    if isinstance(value, list):
        if not value:
            return "array(0)"
        return [f"array({len(value)})", shape(value[0], depth + 1)]
    if isinstance(value, dict):
        return {k: shape(v, depth + 1) for k, v in list(value.items())[:40]}
    return type(value).__name__


def parse_body(text: str | None):
    if not text:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("har")
    ap.add_argument("--stream", action="store_true", help="detail streaming responses")
    ap.add_argument("--keys", action="store_true", help="print JSON key shapes")
    args = ap.parse_args(argv[1:])

    p = Path(args.har)
    if not p.is_file():
        print(f"no such file: {p}")
        return 2

    har = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    entries = har["log"]["entries"]

    by_host = defaultdict(list)
    for e in entries:
        req = e["request"]
        host = req.get("host", "?")
        by_host[host].append(e)

    print(f"file      : {p.name}  ({p.stat().st_size // 1024} KB)")
    print(f"entries   : {len(entries)}")
    print(f"hosts     : {len(by_host)}")
    print()

    print("=" * 78)
    print("HOSTS")
    print("=" * 78)
    for host, es in sorted(by_host.items(), key=lambda kv: -len(kv[1])):
        hosts = Counter(e["request"].get("host", "?") for e in es)
        third = "" if any(
            h in host for h in ("answerthis",)
        ) else "   <- third party"
        print(f"  {host:<46} {len(es):>4} req{third}")

    print()
    print("=" * 78)
    print("API SURFACE  (first-party, non-static)")
    print("=" * 78)
    print(f"  {'METHOD':<7} {'STATUS':<7} {'PATH':<44} {'TYPE':<22} {'SIZE'}")
    seen = set()
    for e in entries:
        req, res = e["request"], e["response"]
        host = req.get("host", "")
        url = req.get("url", "")
        if not any(d in host for d in ("answerthis",)) and "answerthis" not in url:
            continue
        path = url.split("?")[0]
        if re_static(path) or path in seen:
            continue
        seen.add(path)
        mime = (res.get("content", {}).get("mimeType") or "").split(";")[0]
        size = res.get("content", {}).get("size", 0)
        print(f"  {req['method']:<7} {res.get('status','-'):<7} {path[:44]:<44} {mime[:22]:<22} {size}")

    print()
    print("=" * 78)
    print("AUTH: header NAMES present (values never read)")
    print("=" * 78)
    names = Counter()
    for e in entries:
        for h in e["request"].get("headers", []):
            if h["name"].lower() in SECRET_HEADERS:
                names[h["name"]] += 1
    for n, c in names.most_common():
        mark = " <-- credential" if n.lower() in SECRET_HEADERS else ""
        print(f"  {n:<28} on {c:>4} requests  [value withheld]{mark}")
    if not names:
        print("  none")

    if args.stream:
        print()
        print("=" * 78)
        print("STREAMING candidates (long-running or chunked)")
        print("=" * 78)
        for e in entries:
            res = e["response"]
            path = e["request"].get("url", "").split("?")[0]
            mime = res.get("content", {}).get("mimeType", "")
            if "event-stream" in mime or "chunked" in str(res.get("_transferSize")):
                print(f"  {e['request']['method']:<7} {path[:50]:<50} {mime}")
        for e in entries:
            res = e["response"]
            if res.get("status") in (101,):
                path = e["request"].get("url", "").split("?")[0]
                print(f"  101 Switching Protocols  {path[:50]}")

    if args.keys:
        print()
        print("=" * 78)
        print("JSON KEY SHAPES  (names and types; no values)")
        print("=" * 78)
        for e in entries:
            req, res = e["request"], e["response"]
            host = req.get("host", "")
            if "answerthis" not in host:
                continue
            for side, blob in (("REQ", req.get("postData", {}).get("text")),
                               ("RES", res.get("content", {}).get("text"))):
                body = parse_body(blob)
                if body is None:
                    continue
                path = req.get("url", "").split("?")[0]
                print(f"\n  {side} {req['method']} {path[:60]}")
                print(f"     {json.dumps(shape(body), ensure_ascii=False)[:600]}")

    return 0


def re_static(path: str) -> bool:
    exts = (".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2",
            ".ico", ".map", ".webp", ".gif", ".mp4", ".json")
    return path.lower().endswith(exts) or "/_next/" in path or "/assets/" in path


if __name__ == "__main__":
    sys.exit(main(sys.argv))
