"""HTTP inspection without requiring external scanners."""
from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from urllib.parse import urljoin


def inspect(url: str, timeout: int = 10) -> list[dict[str, str]]:
    url = url if "://" in url else f"https://{url}"
    request = urllib.request.Request(url, headers={"User-Agent": "KSTT/0.1 authorized-assessment"})
    observations: list[dict[str, str]] = []
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            headers = dict(response.headers.items())
            observations.append({"kind": "http", "target": url, "status": str(response.status), "server": headers.get("Server", ""), "content_type": headers.get("Content-Type", "")})
            for path in ("/robots.txt", "/sitemap.xml"):
                probe = urllib.request.urlopen(urllib.request.Request(urljoin(url, path), headers=request.headers), timeout=timeout)
                observations.append({"kind": "endpoint", "target": probe.url, "status": str(probe.status)})
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        observations.append({"kind": "http", "target": url, "error": str(error)})
    return observations
