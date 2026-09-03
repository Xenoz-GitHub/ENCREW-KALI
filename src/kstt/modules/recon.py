"""Low-impact reconnaissance helpers."""
from __future__ import annotations

import socket
from urllib.parse import urlparse


def collect(target: str) -> list[dict[str, str]]:
    host = urlparse(target).hostname or target
    observations = [{"kind": "target", "target": target, "host": host}]
    try:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, None)})
        observations.append({"kind": "dns", "target": target, "host": host, "addresses": ",".join(addresses)})
    except socket.gaierror as error:
        observations.append({"kind": "dns", "target": target, "host": host, "error": str(error)})
    return observations
