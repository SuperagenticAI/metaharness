from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_table(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def select_harness(prompt: str, table: dict) -> str:
    lowered = prompt.lower()
    for rule in table.get("rules") or []:
        tokens = rule.get("when") or []
        if any(str(token).lower() in lowered for token in tokens):
            return str(rule["harness"])
    default = table.get("default") or {}
    if isinstance(default, dict):
        return str(default.get("harness") or "pi")
    return str(default)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select a harness for a task prompt.")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--table", default="routing.json")
    args = parser.parse_args(argv)
    table_path = Path(args.table)
    if not table_path.is_file():
        table_path = Path(__file__).resolve().parent / args.table
    print(select_harness(args.prompt, load_table(table_path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
