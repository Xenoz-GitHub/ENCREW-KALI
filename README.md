# Kali Security Testing Toolkit (KSTT)

KSTT is a modular, CLI-first orchestration framework for CTFs, labs, intentionally vulnerable applications, and explicitly authorized assessments. It stores targets and case metadata in SQLite and never installs or runs external security tools automatically.

## Platform

KSTT is intentionally supported only on Kali Linux. Windows, macOS, WSL distributions that do not identify as Kali, and other Linux distributions are rejected by both the CLI and installer. Use a Kali Linux VM or native Kali installation for development and operation.

## Install

```bash
chmod +x install.sh
sudo ./install.sh
kstt --help
kstt doctor
```

This is the first-time Kali setup. With `sudo`, the installer copies KSTT to `/opt/kstt`, creates an isolated Python environment there, and installs the global command at `/usr/local/bin/kstt`. It also installs the optional monitor dependencies and initializes the database. For a user-only install on Kali, run `./install.sh`; that uses `~/.local/share/kstt` and `~/.local/bin/kstt`.

If `kstt` is not found after a user-only install, run `export PATH="$HOME/.local/bin:$PATH"` or open a new terminal. On Kali, avoid installing into the system Python directly; the installer uses a virtual environment for this reason.

For development, use `PYTHONPATH=src python -m kstt --help` or install with `python -m pip install -e .`. Add monitor dependencies with `python -m pip install -e '.[monitor]'`.

## Commands

```text
kstt doctor
kstt target add <target>
kstt target list
kstt target remove <target>
kstt case create <name>
kstt case list
kstt recon <target>
kstt scan <target>
kstt enumerate <target>
kstt web <url>
kstt analyze <case>
kstt report <case>
kstt monitor create
kstt monitor start --local
kstt monitor doctor
kstt monitor show <id>
kstt monitor revoke <id>
kstt monitor purge
kstt monitor export <id>
kstt update --check
kstt update --apply
kstt update --repair
```

All commands support `--format text|json|csv` and `--quiet`. External adapters are designed around argument arrays, timeouts, captured output, and explicit exit status. Missing Kali utilities are reported by `doctor` rather than treated as fatal.

## Updates

Normal text startup performs a short, non-destructive check against the GitHub default branch and reports when an update is available. It never replaces files automatically. Run `kstt update --apply` to use `git pull --ff-only` and reinstall the package, or `kstt update --repair` to reinstall the current checkout without pulling. Set `KSTT_SKIP_UPDATE_CHECK=1` for offline environments.

## Configuration

KSTT reads `~/.config/kstt/config.yaml`, overridable with `KSTT_CONFIG`. The repository provides `config/config.yaml`. Database and case output paths can be changed there.

## Web monitor

The optional FastAPI monitor serves a consent notice and records only request metadata plus browser geolocation explicitly granted through the standard Geolocation API. Start it locally with `kstt monitor start --local`, then create a link with `kstt monitor create`. Set `KSTT_ADMIN_TOKEN` before exposing operator API routes. Configure `monitor.base_url`, host, port, expiry, retention, and `location_enabled` in YAML. Public HTTPS requires a separately configured reverse proxy or explicitly installed `cloudflared`; KSTT never creates external accounts or credentials.

## Testing

```bash
python -m pytest
```

Tests use temporary SQLite databases and do not require a live target or Kali utilities.

## Safety and limitations

Use only within written authorization and defined scope. The monitor does not bypass browser permissions or collect cookies, passwords, files, camera, microphone, clipboard, or browser history. Forwarded IP headers are trusted only from configured proxies. WebSocket watching and tunnel process supervision remain conservative extension points. It does not claim that queued commands were executed.
