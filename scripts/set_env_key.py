"""Write a vendor key from a file into .env without ever printing it.

The key is read into memory, written to .env, and the value is never returned to
stdout, logged, or included in any exception message. The script reports only
whether a key was written and how many characters it holds.

An existing assignment is replaced rather than duplicated, so running this twice
does not leave two GLM_API_KEY lines and no indication which one wins.

    python scripts/set_env_key.py GLM_API_KEY <path-to-key-file>
    python scripts/set_env_key.py TYPESAFE_API_KEY <path> --optional
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("name", help="the environment variable to set")
    ap.add_argument("source", help="file holding the key, one line")
    ap.add_argument(
        "--optional",
        action="store_true",
        help="do not fail when the source file is absent",
    )
    args = ap.parse_args(argv[1:])

    name = args.name
    if not name.isidentifier() or name != name.upper():
        print("name must be an UPPER_CASE identifier")
        return 2

    source = Path(args.source)
    if not source.is_file():
        if args.optional:
            print(f"{name}: no key file at {source}, skipped (optional)")
            return 0
        print(f"{name}: no key file at {source}")
        return 1

    # The value is used and discarded. It is never printed, and no exception
    # below interpolates it.
    value = source.read_text(encoding="utf-8").strip()
    if not value:
        print(f"{name}: key file is empty")
        return 1

    existing = ENV.read_text(encoding="utf-8").splitlines() if ENV.is_file() else []
    kept = [line for line in existing if not line.startswith(f"{name}=")]
    kept.append(f"{name}={value}")

    ENV.write_text("\n".join(kept) + "\n", encoding="utf-8")

    # Length only. Enough to tell "wrote something" from "wrote a truncated key",
    # useless for reconstructing it.
    print(f"{name}: written to .env ({len(value)} characters)")
    print("value not printed, not logged, and not in any exception")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
