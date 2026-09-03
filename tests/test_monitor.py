from pathlib import Path

import pytest

from kstt.monitor import MonitorStore


def test_session_token_and_revocation(tmp_path: Path):
    store = MonitorStore(tmp_path / "monitor.sqlite3")
    session = store.create_session()
    assert len(session["token"]) >= 24
    assert store.session_by_token(session["token"])["id"] == session["id"]
    assert store.revoke(session["id"])
    assert store.session_by_token(session["token"]) is None
    store.close()


def test_event_and_consented_location(tmp_path: Path):
    store = MonitorStore(tmp_path / "monitor.sqlite3")
    session = store.create_session()
    visitor = {"ip": "192.0.2.1", "user_agent": "test", "language": "en", "referrer": ""}
    event = store.add_event(session["token"], "PAGE_LOADED", {"path": "/"}, visitor)
    assert event["visitor_id"]
    location = store.add_location(session["token"], 14.5995, 120.9842, 30, "granted", visitor)
    assert location["latitude"] == 14.5995
    with pytest.raises(ValueError):
        store.add_location(session["token"], 100, 0, None, "granted", visitor)
    store.close()
