"""Configuration loading with a dependency-free YAML-compatible fallback."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = {
    "output_directory": "~/.local/share/kstt/cases",
    "database": "~/.local/share/kstt/kstt.sqlite3",
    "timeout": 30,
    "concurrency": 4,
    "logging_level": "INFO",
    "scan_profiles": {
        "quick": "-T4 --top-ports 100",
        "standard": "-T3 -sV --top-ports 1000",
        "comprehensive": "-T3 -sV -O -p-",
    },
    "tools": {},
}


def config_path() -> Path:
    return Path(os.environ.get("KSTT_CONFIG", "~/.config/kstt/config.yaml")).expanduser()


def _merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: Path | None = None) -> dict[str, Any]:
    selected = path or config_path()
    if not selected.exists():
        return dict(DEFAULT_CONFIG)
    try:
        import yaml  # type: ignore
        loaded = yaml.safe_load(selected.read_text()) or {}
    except ImportError:
        loaded = {}
        for line in selected.read_text().splitlines():
            if ":" in line and not line.startswith(" "):
                key, value = line.split(":", 1)
                loaded[key.strip()] = value.strip().strip('"')
    return _merge(DEFAULT_CONFIG, loaded)
