#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_local_env():
    env_path = ROOT / ".env.local"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in __import__("os").environ:
            __import__("os").environ[key] = value


load_local_env()

from server_modules.services.daily_feishu_runtime import report_card_data, report_payload
from server_modules.services.feishu_svg_report import overview_svg


def main():
    parser = argparse.ArgumentParser(description="Render the local Feishu overview report as SVG.")
    parser.add_argument("--date", default="", help="Business date, YYYY-MM-DD. Defaults to the report default.")
    parser.add_argument(
        "--output",
        default="/Users/lizizhan/Documents/Deca Growth/feishu_overview_svg_preview.svg",
        help="SVG output path.",
    )
    args = parser.parse_args()

    report = report_payload(args.date)
    card_data = report_card_data(report=report)
    svg = overview_svg(card_data)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
