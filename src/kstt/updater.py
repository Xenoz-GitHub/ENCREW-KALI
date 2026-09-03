"""GitHub update checks and explicit local repair actions."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY = "Xenoz-GitHub/ENCREW-KALI"
BRANCH = "main"


def local_revision(root: Path | None = None) -> str | None:
    directory = root or Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(["git", "-C", str(directory), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def check_for_update(root: Path | None = None, timeout: int = 3) -> dict[str, str | bool]:
    current = local_revision(root)
    request = urllib.request.Request(f"https://api.github.com/repos/{REPOSITORY}/commits/{BRANCH}", headers={"Accept": "application/vnd.github+json", "User-Agent": "KSTT-update-check"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            latest = json.load(response)["sha"]
    except (OSError, urllib.error.URLError, KeyError, json.JSONDecodeError) as error:
        return {"available": False, "checked": False, "current": current or "unknown", "error": str(error)}
    return {"available": bool(current and current != latest), "checked": True, "current": current or "unknown", "latest": latest}


def apply_update(root: Path | None = None, repair: bool = False) -> dict[str, str | int]:
    directory = root or Path(__file__).resolve().parents[2]
    if not (directory / ".git").exists():
        raise RuntimeError("self-update requires a Git checkout")
    if repair:
        command = [sys.executable, "-m", "pip", "install", "-e", f"{directory}[monitor]"]
    else:
        command = ["git", "-C", str(directory), "pull", "--ff-only"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or "update failed")
    if not repair:
        repair_result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", f"{directory}[monitor]"], capture_output=True, text=True, timeout=120, check=False)
        if repair_result.returncode != 0: raise RuntimeError((repair_result.stderr or repair_result.stdout).strip() or "package reinstall failed")
    return {"status": "updated" if not repair else "repaired", "directory": str(directory), "returncode": result.returncode}
