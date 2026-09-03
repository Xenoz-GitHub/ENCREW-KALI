#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(uname -s)" != "Linux" ]; then
	echo "KSTT is a Kali Linux tool. Run uninstall.sh from Kali Linux." >&2
	exit 1
fi
if [ "$(id -u)" -eq 0 ]; then
	rm -f /usr/local/bin/kstt
	rm -rf /opt/kstt
else
	rm -f "$HOME/.local/bin/kstt"
	rm -rf "$HOME/.local/share/kstt"
fi
printf 'KSTT executable and installed runtime removed. User configuration and data were preserved.\n'
