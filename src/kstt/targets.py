"""Target validation and normalization."""
from __future__ import annotations

import ipaddress
from pathlib import Path
from urllib.parse import urlparse


def normalize_target(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("target cannot be empty")
    candidate = value
    if Path(value).is_file():
        raise ValueError("file targets must be expanded with load_targets()")
    try:
        return str(ipaddress.ip_network(candidate, strict=False)) if "/" in candidate else str(ipaddress.ip_address(candidate))
    except ValueError:
        parsed = urlparse(candidate if "://" in candidate else f"//{candidate}")
        host = parsed.hostname
        if not host or any(char.isspace() for char in host):
            raise ValueError(f"invalid target: {value}")
        return candidate.rstrip("/")


def load_targets(value: str) -> list[str]:
    path = Path(value).expanduser()
    if path.is_file():
        return [normalize_target(line) for line in path.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    return [normalize_target(value)]
