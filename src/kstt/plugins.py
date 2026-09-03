"""Minimal user plugin registry."""
from __future__ import annotations

import json
from pathlib import Path


def registry_path() -> Path:
    return Path.home() / ".config" / "kstt" / "plugins.json"


def list_plugins() -> list[dict]:
    path = registry_path()
    return json.loads(path.read_text()) if path.exists() else []


def install(path: str) -> dict:
    source = Path(path).expanduser().resolve()
    if not source.exists() or source.suffix != ".py":
        raise ValueError("plugin must be an existing Python file")
    registry_path().parent.mkdir(parents=True, exist_ok=True)
    plugins = [item for item in list_plugins() if item["path"] != str(source)]
    item = {"name": source.stem, "path": str(source)}; plugins.append(item)
    registry_path().write_text(json.dumps(plugins, indent=2)); return item
