"""Command-line entry points. Run as `python -m app.cli <command>`."""

import sys

from app.core.database import SessionLocal
from app.core.seed import seed_demo_users


def cmd_seed() -> None:
    db = SessionLocal()
    try:
        created = seed_demo_users(db)
        print(f"seed: {created} demo user(s) created.")
    finally:
        db.close()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m app.cli <seed>", file=sys.stderr)
        return 2

    command = argv[1]
    if command == "seed":
        cmd_seed()
        return 0

    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
