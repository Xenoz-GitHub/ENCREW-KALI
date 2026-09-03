"""Consent-based public web monitor for authorized diagnostics and labs."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS monitor_sessions (id TEXT PRIMARY KEY, token TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS monitor_visitors (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, ip TEXT, user_agent TEXT, language TEXT, referrer TEXT, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS monitor_events (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, visitor_id TEXT, event_type TEXT NOT NULL, timestamp TEXT NOT NULL, metadata TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS monitor_locations (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, visitor_id TEXT, latitude REAL NOT NULL, longitude REAL NOT NULL, accuracy REAL, timestamp TEXT NOT NULL, consent_state TEXT NOT NULL);
"""
EVENTS = {"SESSION_CREATED", "VISITOR_CONNECTED", "PAGE_LOADED", "LOCATION_PERMISSION_GRANTED", "LOCATION_PERMISSION_DENIED", "LOCATION_RECEIVED", "VISITOR_DISCONNECTED", "SESSION_REVOKED", "SESSION_EXPIRED", "ERROR"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utcnow()).isoformat()


class MonitorStore:
    def __init__(self, database: Path, retention_days: int = 7, location_enabled: bool = True):
        import sqlite3
        self.connection = sqlite3.connect(database.expanduser(), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.commit()
        self.lock = threading.Lock()
        self.retention_days = retention_days
        self.location_enabled = location_enabled

    def create_session(self, expires_hours: int = 24) -> dict[str, str]:
        session_id = secrets.token_hex(3)
        token = secrets.token_urlsafe(24)
        record = {"id": session_id, "token": token, "created_at": iso(), "expires_at": iso(utcnow() + timedelta(hours=expires_hours)), "status": "ACTIVE"}
        with self.lock:
            self.connection.execute("INSERT INTO monitor_sessions VALUES (?, ?, ?, ?, ?)", tuple(record.values()))
            self.connection.commit()
        return record

    def session_by_id(self, session_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM monitor_sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None

    def session_by_token(self, token: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM monitor_sessions WHERE token = ?", (token,)).fetchone()
        if not row: return None
        result = dict(row)
        if result["status"] == "ACTIVE" and datetime.fromisoformat(result["expires_at"]) <= utcnow():
            self.revoke(result["id"], "SESSION_EXPIRED"); result["status"] = "EXPIRED"
        return result if result["status"] == "ACTIVE" else None

    def sessions(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute("SELECT * FROM monitor_sessions ORDER BY created_at DESC")]

    def revoke(self, session_id: str, event_type: str = "SESSION_REVOKED") -> bool:
        with self.lock:
            changed = self.connection.execute("UPDATE monitor_sessions SET status = 'REVOKED' WHERE id = ? AND status = 'ACTIVE'", (session_id,)).rowcount
            if changed: self.connection.commit()
        return bool(changed)

    def add_event(self, token: str, event_type: str, metadata: dict[str, Any] | None = None, visitor: dict[str, str] | None = None) -> dict[str, Any]:
        session = self.session_by_token(token)
        if not session: raise ValueError("invalid or inactive session token")
        if event_type not in EVENTS: raise ValueError("unsupported event type")
        metadata = metadata or {}
        visitor_id = None
        if visitor:
            visitor_id = hashlib.sha256(f"{session['id']}|{visitor.get('ip','')}|{visitor.get('user_agent','')}".encode()).hexdigest()[:20]
            now = iso()
            with self.lock:
                self.connection.execute("INSERT INTO monitor_visitors VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen", (visitor_id, session["id"], visitor.get("ip", ""), visitor.get("user_agent", "")[:500], visitor.get("language", "")[:100], visitor.get("referrer", "")[:1000], now, now))
        event_id = secrets.token_hex(12)
        with self.lock:
            self.connection.execute("INSERT INTO monitor_events VALUES (?, ?, ?, ?, ?, ?)", (event_id, session["id"], visitor_id, event_type, iso(), json.dumps(metadata, separators=(",", ":"))))
            self.connection.commit()
        return {"id": event_id, "session_id": session["id"], "visitor_id": visitor_id, "event_type": event_type, "metadata": metadata}

    def add_location(self, token: str, latitude: float, longitude: float, accuracy: float | None, consent_state: str, visitor: dict[str, str] | None = None) -> dict[str, Any]:
        if not self.location_enabled: raise ValueError("location storage is disabled")
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180): raise ValueError("invalid coordinates")
        session = self.session_by_token(token)
        if not session: raise ValueError("invalid or inactive session token")
        event = self.add_event(token, "LOCATION_RECEIVED", {"accuracy": accuracy, "consent_state": consent_state}, visitor)
        location_id = secrets.token_hex(12)
        with self.lock:
            self.connection.execute("INSERT INTO monitor_locations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (location_id, session["id"], event["visitor_id"], latitude, longitude, accuracy, iso(), consent_state))
            self.connection.commit()
        return {"id": location_id, "session_id": session["id"], "latitude": latitude, "longitude": longitude, "accuracy": accuracy, "consent_state": consent_state}

    def events(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM monitor_events WHERE session_id = ? ORDER BY timestamp", (session_id,))
        return [{**dict(row), "metadata": json.loads(row["metadata"])} for row in rows]

    def locations(self, session_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute("SELECT * FROM monitor_locations WHERE session_id = ? ORDER BY timestamp", (session_id,))]

    def purge(self) -> int:
        cutoff = iso(utcnow() - timedelta(days=self.retention_days))
        with self.lock:
            count = self.connection.execute("DELETE FROM monitor_events WHERE timestamp < ?", (cutoff,)).rowcount
            self.connection.execute("DELETE FROM monitor_locations WHERE timestamp < ?", (cutoff,)); self.connection.commit()
        return count

    def close(self) -> None: self.connection.close()


def visitor_page(token: str) -> str:
    return f'''<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>System Diagnostic</title><style>body{{font:16px system-ui;max-width:38rem;margin:12vh auto;padding:2rem;color:#152238;background:#eef3f7}}main{{background:white;padding:2rem;border-radius:8px;box-shadow:0 8px 30px #1232}}button{{padding:.7rem 1rem}}</style><main><h1>System Diagnostic</h1><p>This page may collect technical connection information for an authorized diagnostic session. Browser location is optional and requires your explicit permission.</p><button id="location">Share location</button><p id="status" role="status"></p></main><script>
const token={json.dumps(token)}, status=document.querySelector('#status');
async function send(path, body) {{ await fetch('/public/'+token+'/'+path, {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}}); }}
send('event',{{event_type:'PAGE_LOADED'}});
document.querySelector('#location').onclick=()=>navigator.geolocation.getCurrentPosition(p=>{{send('event',{{event_type:'LOCATION_PERMISSION_GRANTED'}});send('location',{{latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy,consent_state:'granted',timestamp:Date.now()}});status.textContent='Location shared.'}},()=>{{send('event',{{event_type:'LOCATION_PERMISSION_DENIED'}});status.textContent='Location permission was not granted.'}});
</script></html>'''


def create_app(store: MonitorStore, admin_token: str | None = None):
    try:
        from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse
    except ImportError as error:
        raise RuntimeError("FastAPI and Uvicorn are required: pip install fastapi uvicorn") from error
    app = FastAPI(title="KSTT Web Monitor", docs_url=None, redoc_url=None)
    recent: list[dict[str, Any]] = []
    rate: dict[str, list[float]] = {}

    def client(request: Request) -> dict[str, str]:
        ip = request.client.host if request.client else "unknown"
        trusted = os.environ.get("KSTT_TRUSTED_PROXIES", "127.0.0.1").split(",")
        if ip in trusted and request.headers.get("x-forwarded-for"): ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        return {"ip": ip, "user_agent": request.headers.get("user-agent", ""), "language": request.headers.get("accept-language", ""), "referrer": request.headers.get("referer", "")}

    def allow(ip: str) -> bool:
        now = time.monotonic(); values = [item for item in rate.get(ip, []) if now - item < 60]
        if len(values) >= 60: rate[ip] = values; return False
        values.append(now); rate[ip] = values; return True

    def auth(request: Request) -> None:
        if not admin_token or request.headers.get("authorization") != f"Bearer {admin_token}":
            from fastapi import HTTPException
            raise HTTPException(401, "operator authentication required")

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request); response.headers.update({"X-Content-Type-Options":"nosniff", "X-Frame-Options":"DENY", "Referrer-Policy":"no-referrer"}); return response

    @app.get("/health")
    async def health(): return {"status": "ok"}
    @app.get("/public/{token}", response_class=HTMLResponse)
    async def public(token: str):
        if not store.session_by_token(token):
            from fastapi import HTTPException
            raise HTTPException(404, "session unavailable")
        return visitor_page(token)
    @app.post("/public/{token}/event")
    async def event(token: str, request: Request):
        info = client(request)
        if not allow(info["ip"]):
            from fastapi import HTTPException
            raise HTTPException(429, "rate limit exceeded")
        body = await request.json(); result = store.add_event(token, str(body.get("event_type", "ERROR")), {"path": str(request.url.path)}, info); recent.append(result); return {"accepted": True, "event_id": result["id"]}
    @app.post("/public/{token}/location")
    async def location(token: str, request: Request):
        body = await request.json(); result = store.add_location(token, float(body["latitude"]), float(body["longitude"]), float(body["accuracy"]) if body.get("accuracy") is not None else None, str(body.get("consent_state", "unknown")), client(request)); recent.append({"event_type":"LOCATION_RECEIVED", **result}); return {"accepted": True}
    @app.get("/api/sessions")
    async def api_sessions(request: Request): auth(request); return store.sessions()
    @app.post("/api/sessions")
    async def api_create_session(request: Request):
        auth(request); body = await request.json(); return store.create_session(int(body.get("expires_hours", 24)))
    @app.get("/api/sessions/{session_id}")
    async def api_session(session_id: str, request: Request):
        auth(request); result = store.session_by_id(session_id)
        if not result:
            from fastapi import HTTPException
            raise HTTPException(404, "not found")
        return {**result, "events": store.events(session_id), "locations": store.locations(session_id)}
    @app.post("/api/sessions/{session_id}/revoke")
    async def api_revoke_session(session_id: str, request: Request):
        auth(request)
        if not store.revoke(session_id):
            from fastapi import HTTPException
            raise HTTPException(404, "active session not found")
        return {"id": session_id, "status": "REVOKED"}
    @app.websocket("/ws/{token}")
    async def websocket(ws: WebSocket, token: str):
        await ws.accept(); index = 0
        try:
            while store.session_by_token(token):
                session = store.session_by_token(token)
                while index < len(recent):
                    if session and recent[index].get("session_id") == session["id"]: await ws.send_json(recent[index])
                    index += 1
                await __import__("asyncio").sleep(1)
        except WebSocketDisconnect: return
    app.state.monitor_recent = recent
    return app
