"""Nmap profile command construction and execution."""
from __future__ import annotations

import shlex
from pathlib import Path
from ..config import load_config
from ..runner import CommandResult, run_command


def build_nmap_command(target: str, profile: str = "standard", config: dict | None = None) -> list[str]:
    settings = config or load_config()
    profiles = settings.get("scan_profiles", {})
    if profile not in profiles:
        raise ValueError(f"unknown scan profile: {profile}")
    return ["nmap", *shlex.split(profiles[profile]), "-oX", "-", target]


def run(target: str, profile: str = "standard", timeout: int = 30, output_file: Path | None = None) -> CommandResult:
    return run_command(build_nmap_command(target, profile), timeout=timeout, output_file=output_file)
