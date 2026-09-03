#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rm -f "$HOME/.local/bin/kstt"
rm -rf "$ROOT/.venv"
printf 'KSTT executable and virtual environment removed. User data was preserved.\n'
