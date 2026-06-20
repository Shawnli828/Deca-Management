#!/usr/bin/env python3
import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from server_modules import app_runtime  # noqa: E402


def main():
    seed_path = PROJECT_DIR / "seed_data.json"
    if not seed_path.is_file():
        raise SystemExit(f"Seed file not found: {seed_path}")

    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    data = payload.get("data")
    if not isinstance(data, list):
        raise SystemExit("seed_data.json must contain {\"data\": [...]}")

    app_runtime.init_db()
    app_runtime.save_data(data)
    print(f"Imported {len(data)} products into {'Postgres' if app_runtime.using_postgres() else 'SQLite'}.")


if __name__ == "__main__":
    main()
