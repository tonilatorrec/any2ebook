import sqlite3
from pathlib import Path

from any2ebook.db import migrate_db


def _items_columns(db_path: Path) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("PRAGMA table_info(items)").fetchall()
    return [row[1] for row in rows]


def _runs_columns(db_path: Path) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("PRAGMA table_info(runs)").fetchall()
    return [row[1] for row in rows]


def _run_items_columns(db_path: Path) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("PRAGMA table_info(run_items)").fetchall()
    return [row[1] for row in rows]


def test_migrate_db_creates_current_schema(tmp_path: Path):
    db_path = tmp_path / "any2ebook.db"
    migrate_db(db_path)

    assert _items_columns(db_path) == [
        "id",
        "captured_at",
        "payload_ref",
        "payload_type",
        "source",
    ]
    assert _runs_columns(db_path) == [
        "id",
        "run_at",
        "artifact_type",
        "filename",
        "recipe",
        "status",
    ]
    assert _run_items_columns(db_path) == ["run_id", "item_id", "action"]


def test_migrate_db_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "any2ebook.db"
    migrate_db(db_path)
    migrate_db(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO items(captured_at, payload_ref, payload_type, source)
            VALUES('2026-01-01T00:00:00+00:00', 'https://example.com/a', 'url', 'raw_text')
            """
        )
        conn.execute(
            """
            INSERT INTO runs(run_at, artifact_type, filename, recipe, status)
            VALUES('2026-01-01T00:00:00+00:00', 'epub', 'out.epub', '', 'committed')
            """
        )
        conn.execute(
            """
            INSERT INTO run_items(run_id, item_id, action)
            VALUES(1, 1, 'converted')
            """
        )
        conn.commit()

        item_count = int(conn.execute("SELECT COUNT(*) FROM items").fetchone()[0])
        run_count = int(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
        run_item_count = int(conn.execute("SELECT COUNT(*) FROM run_items").fetchone()[0])

    assert item_count == 1
    assert run_count == 1
    assert run_item_count == 1


def test_migrate_db_upgrades_runs_table_missing_status(tmp_path: Path):
    db_path = tmp_path / "any2ebook.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE runs(
                id INTEGER PRIMARY KEY,
                run_at TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                recipe TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO runs(run_at, artifact_type, filename, recipe)
            VALUES('2026-01-01T00:00:00+00:00', 'epub', 'out.epub', '')
            """
        )
        conn.commit()

    migrate_db(db_path)

    assert "status" in _runs_columns(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT status FROM runs WHERE id = 1").fetchone()
    assert row == ("committed",)


def test_migrate_db_upgrades_legacy_runs_totals_schema(tmp_path: Path):
    db_path = tmp_path / "any2ebook.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE runs(
                id INTEGER PRIMARY KEY,
                run_at TEXT NOT NULL,
                status TEXT NOT NULL,
                total INTEGER,
                total_found INTEGER,
                total_new INTEGER,
                total_failed INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO runs(run_at, status, total, total_found, total_new, total_failed)
            VALUES('2026-01-01T00:00:00+00:00', 'committed', 10, 10, 7, 3)
            """
        )
        conn.commit()

    migrate_db(db_path)

    cols = set(_runs_columns(db_path))
    assert {"artifact_type", "filename", "recipe", "status"}.issubset(cols)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT artifact_type, filename, recipe, status FROM runs WHERE id = 1"
        ).fetchone()
    assert row == ("epub", "", "", "committed")
