"""Safe external command execution."""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False


def run_command(argv: list[str], timeout: int = 30, output_file: Path | None = None) -> CommandResult:
    if not argv or any(not isinstance(part, str) for part in argv):
        raise ValueError("argv must be a non-empty list of strings")
    started = time.monotonic()
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        result = CommandResult(argv, completed.returncode, completed.stdout, completed.stderr, time.monotonic() - started)
    except FileNotFoundError as error:
        result = CommandResult(argv, 127, "", str(error), time.monotonic() - started)
    except subprocess.TimeoutExpired as error:
        result = CommandResult(argv, 124, error.stdout or "", error.stderr or "", time.monotonic() - started, True)
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(result.stdout + ("\n" + result.stderr if result.stderr else ""))
    return result
