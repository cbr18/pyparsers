#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def walk(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            yield path, type(item).__name__
            yield from walk(item, path)
    elif isinstance(value, list):
        yield prefix, "list"
        for item in value[:3]:
            yield from walk(item, f"{prefix}[]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Encar JSON payload shape.")
    parser.add_argument("json_file", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.json_file.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("SearchResults"), list):
        sample = payload["SearchResults"][0] if payload["SearchResults"] else {}
    else:
        sample = payload

    paths = Counter(walk(sample))
    for (path, type_name), count in sorted(paths.items()):
        print(f"{path}\t{type_name}\t{count}")


if __name__ == "__main__":
    main()
