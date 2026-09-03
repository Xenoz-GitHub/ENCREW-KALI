from pathlib import Path

from kstt.database import Database
from kstt.targets import normalize_target


def test_normalize_targets():
    assert normalize_target("192.168.1.1") == "192.168.1.1"
    assert normalize_target("192.168.1.0/24") == "192.168.1.0/24"
    assert normalize_target("https://example.test/") == "https://example.test"


def test_database_round_trip(tmp_path: Path):
    db = Database(tmp_path / "test.sqlite3")
    db.add_target("example.test")
    db.create_case("demo")
    assert db.targets() == ["example.test"]
    assert db.case("demo")["status"] == "open"
    db.close()
