"""Command-line entry points. Run as `python -m app.cli <command>`."""

import sys

from app.core.database import SessionLocal
from app.core.seed import seed_demo_data, seed_demo_users


def cmd_seed() -> None:
    db = SessionLocal()
    try:
        new_users = seed_demo_users(db)
        print(f"seed: {new_users} demo user(s) created.")
        stats = seed_demo_data(db)
        non_zero = {k: v for k, v in stats.items() if v}
        if non_zero:
            print(f"seed: demo data created — {non_zero}")
        else:
            print("seed: demo data already in place.")
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
