"""Output formatting helpers."""
from __future__ import annotations

import csv
import json
import sys
from typing import Any


def emit(data: Any, fmt: str = "text", quiet: bool = False) -> None:
    if quiet:
        return
    if fmt == "json":
        print(json.dumps(data, indent=2, default=str))
    elif fmt == "csv" and isinstance(data, list):
        if data:
            writer = csv.DictWriter(sys.stdout, fieldnames=data[0].keys())
            writer.writeheader(); writer.writerows(data)
    elif isinstance(data, list):
        for item in data:
            print("  ".join(f"{key}: {value}" for key, value in item.items()))
    elif isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {value}")
    else:
        print(data)
