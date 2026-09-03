"""Command-line interface for KSTT."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .database import Database
from .dependencies import detect_tools
from .output import emit
from .targets import normalize_target
from .modules import analysis, recon, scanning, web
from .modules.reporting import export_case
from . import plugins
from .monitor import MonitorStore, create_app
from .updater import apply_update, check_for_update

BANNER = r"""
    _____ _   _  _____ _______ _______ _____  _____  _____  _____
 | ____| \ | |/ ____|__   __|__   __|  __ \|  __ \|  __ \|  __ \
 | |__  |  \| | |       | |     | |  | |__) | |__) | |__) | |__) |
 |  __| | . ` | |       | |     | |  |  _  /|  ___/|  ___/|  ___/
 | |____| |\  | |____   | |     | |  | | \ \| |    | |    | |
 |______|_| \_|\_____|  |_|     |_|  |_|  \_\_|    |_|    |_|

                         ENCRYPTED CREW TOOLS KALI
"""


def require_kali_linux() -> None:
    if sys.platform != "linux":
        raise SystemExit("KSTT runs only on Kali Linux. Windows and other operating systems are not supported.")
    release = Path("/etc/os-release")
    values: dict[str, str] = {}
    if release.exists():
        for line in release.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
    if values.get("ID") != "kali":
        raise SystemExit("KSTT runs only on Kali Linux. Kali was not detected in /etc/os-release.")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="kstt", description="Kali Security Testing Toolkit for authorized environments")
    root.add_argument("--version", action="version", version=__version__)
    root.add_argument("--format", choices=["text", "json", "csv"], default="text")
    root.add_argument("--json", dest="format", action="store_const", const="json")
    root.add_argument("--text", dest="format", action="store_const", const="text")
    root.add_argument("--csv", dest="format", action="store_const", const="csv")
    root.add_argument("--quiet", action="store_true")
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("db-init")
    target = sub.add_parser("target"); target_sub = target.add_subparsers(dest="target_command", required=True)
    add = target_sub.add_parser("add"); add.add_argument("target")
    target_sub.add_parser("list")
    target_sub.add_parser("export")
    remove = target_sub.add_parser("remove"); remove.add_argument("target")
    case = sub.add_parser("case"); case_sub = case.add_subparsers(dest="case_command", required=True)
    create = case_sub.add_parser("create"); create.add_argument("name")
    case_sub.add_parser("list")
    case_sub.add_parser("status")
    case_sub.add_parser("open").add_argument("name")
    case_sub.add_parser("export").add_argument("name")
    for name in ("recon", "enumerate", "analyze"):
        command = sub.add_parser(name); command.add_argument("target")
    scan = sub.add_parser("scan"); scan.add_argument("target"); scan.add_argument("--profile", choices=["quick", "standard", "comprehensive"], default="standard")
    web = sub.add_parser("web"); web.add_argument("url")
    report = sub.add_parser("report"); report.add_argument("case"); report.add_argument("--type", choices=["md", "json"], default="md")
    plugin = sub.add_parser("plugin"); plugin_sub = plugin.add_subparsers(dest="plugin_command", required=True)
    plugin_sub.add_parser("list")
    install = plugin_sub.add_parser("install"); install.add_argument("path")
    update = sub.add_parser("update"); update.add_argument("--check", action="store_true"); update.add_argument("--apply", action="store_true"); update.add_argument("--repair", action="store_true")
    monitor = sub.add_parser("monitor"); monitor_sub = monitor.add_subparsers(dest="monitor_command", required=True)
    monitor_sub.add_parser("create")
    monitor_sub.add_parser("list")
    for name in ("show", "revoke", "watch"):
        monitor_sub.add_parser(name).add_argument("id")
    export_monitor = monitor_sub.add_parser("export"); export_monitor.add_argument("id"); export_monitor.add_argument("--no-location", action="store_true")
    start = monitor_sub.add_parser("start"); start.add_argument("--local", action="store_true"); start.add_argument("--public", action="store_true")
    public = monitor_sub.add_parser("public"); public.add_argument("--watch", action="store_true"); public.add_argument("--no-watch", action="store_true")
    monitor_sub.add_parser("dashboard"); monitor_sub.add_parser("purge"); monitor_sub.add_parser("doctor"); monitor_sub.add_parser("dev")
    tunnel = monitor_sub.add_parser("tunnel"); tunnel_sub = tunnel.add_subparsers(dest="tunnel_command", required=True)
    tunnel_sub.add_parser("start"); tunnel_sub.add_parser("stop"); tunnel_sub.add_parser("status")
    return root


def monitor_cli(args: argparse.Namespace, config: dict, db: Database, output) -> None:
    monitor_config = config.get("monitor", {})
    store = MonitorStore(Path(config["database"]), int(monitor_config.get("retention_days", 7)), bool(monitor_config.get("location_enabled", True)))
    try:
        if args.monitor_command == "create":
            session = store.create_session(int(monitor_config.get("expires_hours", 24)))
            base = monitor_config.get("base_url", f"http://127.0.0.1:{monitor_config.get('port', 8080)}").rstrip("/")
            output({**session, "url": f"{base}/public/{session['token']}"}, args.format, args.quiet)
        elif args.monitor_command == "list": output(store.sessions(), args.format, args.quiet)
        elif args.monitor_command == "show":
            session = store.session_by_id(args.id)
            if not session: raise ValueError(f"monitor session not found: {args.id}")
            output({**session, "events": store.events(args.id), "locations": store.locations(args.id)}, args.format, args.quiet)
        elif args.monitor_command == "revoke":
            if not store.revoke(args.id): raise ValueError(f"active monitor session not found: {args.id}")
            output({"id": args.id, "status": "REVOKED"}, args.format, args.quiet)
        elif args.monitor_command == "purge": output({"deleted_events": store.purge()}, args.format, args.quiet)
        elif args.monitor_command == "doctor":
            import importlib.util, shutil
            try:
                import fastapi  # type: ignore
                fastapi_status = "OK"
            except Exception as error:
                fastapi_status = f"ERROR: {type(error).__name__}"
            output([{"check": "Python", "status": "OK"}, {"check": "FastAPI", "status": fastapi_status}, {"check": "Database", "status": "OK"}, {"check": "cloudflared", "status": "INSTALLED" if shutil.which("cloudflared") else "MISSING"}], args.format, args.quiet)
        elif args.monitor_command == "export":
            session = store.session_by_id(args.id)
            if not session: raise ValueError(f"monitor session not found: {args.id}")
            output({**session, "events": store.events(args.id), "locations": store.locations(args.id)}, args.format, args.quiet)
        elif args.monitor_command in ("start", "dev", "public"):
            try: import uvicorn
            except Exception as error: raise ValueError("FastAPI/Uvicorn dependencies are unavailable or incompatible: pip install -U fastapi uvicorn pydantic pydantic-core") from error
            try:
                app = create_app(store, os.environ.get("KSTT_ADMIN_TOKEN"))
            except Exception as error:
                raise ValueError("FastAPI dependencies are unavailable or incompatible: install with pip install -U fastapi uvicorn pydantic pydantic-core") from error
            print(f"Local URL:\nhttp://127.0.0.1:{monitor_config.get('port', 8080)}")
            uvicorn.run(app, host=str(monitor_config.get("host", "127.0.0.1")), port=int(monitor_config.get("port", 8080)), log_level="info")
        elif args.monitor_command == "tunnel":
            import shutil
            if not shutil.which("cloudflared"): raise ValueError("cloudflared is not installed; install it explicitly before starting a tunnel")
            output({"status": "available", "command": "cloudflared tunnel"}, args.format, args.quiet)
        elif args.monitor_command in ("watch", "dashboard"):
            output({"status": "not_connected", "message": "Use the FastAPI WebSocket endpoint /ws/<token> with a WebSocket client."}, args.format, args.quiet)
    finally:
        store.close()


def main(argv: list[str] | None = None) -> None:
    require_kali_linux()
    raw = list(sys.argv[1:] if argv is None else argv)
    # Accept global presentation flags after a subcommand for shell-friendly usage.
    for flag in ("--quiet", "--json", "--text", "--csv"):
        if flag in raw:
            raw.remove(flag); raw.insert(0, flag)
    if "--format" in raw:
        index = raw.index("--format")
        value = raw.pop(index); format_value = raw.pop(index)
        raw[0:0] = [value, format_value]
    args = parser().parse_args(raw)
    if args.format == "text" and not args.quiet and os.environ.get("KSTT_NO_BANNER") != "1": print(BANNER)
    if args.command != "update" and os.environ.get("KSTT_SKIP_UPDATE_CHECK") != "1":
        update_status = check_for_update()
        if update_status.get("available") and args.format == "text" and not args.quiet:
            print("Update available. Run: kstt update --apply")
    config = load_config()
    db = Database(Path(config["database"]))
    try:
        if args.command == "doctor":
            emit(detect_tools(), args.format, args.quiet)
        elif args.command == "update":
            if args.apply or args.repair:
                emit(apply_update(repair=args.repair), args.format, args.quiet)
            else:
                emit(check_for_update(), args.format, args.quiet)
        elif args.command == "db-init":
            emit({"status": "initialized", "database": str(db.path)}, args.format, args.quiet)
        elif args.command == "target":
            if args.target_command == "add": db.add_target(normalize_target(args.target))
            elif args.target_command == "remove": db.remove_target(normalize_target(args.target))
            elif args.target_command == "export": emit(db.targets(), "json", args.quiet)
            if args.target_command == "export": return
            emit(db.targets(), args.format, args.quiet)
        elif args.command == "case":
            if args.case_command == "create": db.create_case(args.name)
            elif args.case_command == "open":
                if not db.case(args.name): raise ValueError(f"case not found: {args.name}")
            elif args.case_command == "export":
                path = export_case(db, args.name, Path(config["output_directory"]).expanduser(), "json")
                emit({"report": str(path)}, args.format, args.quiet); return
            emit(db.cases(), args.format, args.quiet)
        elif args.command == "recon":
            observations = recon.collect(normalize_target(args.target))
            emit(observations, args.format, args.quiet)
        elif args.command == "scan":
            result = scanning.run(normalize_target(args.target), profile=args.profile, timeout=int(config["timeout"]))
            emit({"argv": result.argv, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "duration": result.duration, "timed_out": result.timed_out}, args.format, args.quiet)
        elif args.command == "web":
            emit(web.inspect(args.url, timeout=int(config["timeout"])), args.format, args.quiet)
        elif args.command == "enumerate":
            emit({"target": normalize_target(args.target), "status": "ready", "message": "Enumeration consumes stored scan observations when available."}, args.format, args.quiet)
        elif args.command == "analyze":
            observations = db.observations(args.target)
            findings = [analysis.finding_from_observation(item["data"]) for item in observations]
            for finding in findings: db.add_finding(finding["id"], args.target, finding)
            emit(findings, args.format, args.quiet)
        elif args.command == "report":
            path = export_case(db, args.case, Path(config["output_directory"]).expanduser(), args.type)
            emit({"report": str(path), "case": args.case}, args.format, args.quiet)
        elif args.command == "plugin":
            if args.plugin_command == "install": plugins.install(args.path)
            emit(plugins.list_plugins(), args.format, args.quiet)
        elif args.command == "monitor":
            monitor_cli(args, config, db, emit)
    except (ValueError, OSError) as error:
        print(f"kstt: {error}", file=sys.stderr)
        raise SystemExit(2)
    finally:
        db.close()

if __name__ == "__main__":
    main()
