#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
if [ "$(uname -s)" != "Linux" ]; then
    echo "KSTT is only supported on Kali Linux. This installer cannot run on Windows or macOS." >&2
    exit 1
fi
if [ ! -r /etc/os-release ] || ! grep -Eq '^ID=kali([[:space:]]|$)' /etc/os-release; then
    echo "KSTT requires Kali Linux. Kali was not detected in /etc/os-release." >&2
    exit 1
fi
command -v "$PYTHON" >/dev/null || { echo "Python 3.11+ is required" >&2; exit 1; }
"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required")
PY
if [ "$(id -u)" -eq 0 ]; then
    INSTALL_DIR="/opt/kstt"
    BIN_DIR="/usr/local/bin"
else
    INSTALL_DIR="$HOME/.local/share/kstt"
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
fi
VENV_DIR="$INSTALL_DIR/venv"
SOURCE_DIR="$INSTALL_DIR/source"
mkdir -p "$INSTALL_DIR" "$HOME/.config/kstt" "$HOME/.local/share/kstt/cases"
rm -rf "$SOURCE_DIR"
cp -R "$ROOT" "$SOURCE_DIR"
rm -rf "$SOURCE_DIR/.venv" "$SOURCE_DIR/.pytest_cache"
"$PYTHON" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install "$SOURCE_DIR[monitor]"
if [ ! -f "$HOME/.config/kstt/config.yaml" ]; then cp "$ROOT/config/config.yaml" "$HOME/.config/kstt/config.yaml"; fi
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/kstt" <<EOF
#!/usr/bin/env bash
export KSTT_SOURCE_DIR="$SOURCE_DIR"
exec "$VENV_DIR/bin/kstt" "\$@"
EOF
chmod +x "$BIN_DIR/kstt"
KSTT_SKIP_UPDATE_CHECK=1 "$BIN_DIR/kstt" db-init
cat <<'BANNER'

    ENCRYPTED CREW TOOLS KALI
    Installation complete. KSTT is ready.
BANNER
printf 'KSTT installed globally at %s. Ensure %s is on PATH.\n' "$INSTALL_DIR" "$BIN_DIR"
