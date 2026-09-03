#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null || { echo "Python 3.11+ is required" >&2; exit 1; }
"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required")
PY
"$PYTHON" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/pip" install -e "$ROOT"
"$ROOT/.venv/bin/pip" install -e "$ROOT[monitor]"
mkdir -p "$HOME/.config/kstt" "$HOME/.local/share/kstt/cases"
if [ ! -f "$HOME/.config/kstt/config.yaml" ]; then cp "$ROOT/config/config.yaml" "$HOME/.config/kstt/config.yaml"; fi
if [ "$(id -u)" -eq 0 ]; then
    BIN_DIR="/usr/local/bin"
else
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
fi
ln -sf "$ROOT/.venv/bin/kstt" "$BIN_DIR/kstt"
"$ROOT/.venv/bin/kstt" db-init
cat <<'BANNER'

    ENCRYPTED CREW TOOLS KALI
    Installation complete. KSTT is ready.
BANNER
printf 'KSTT installed. Ensure %s is on PATH.\n' "$BIN_DIR"
