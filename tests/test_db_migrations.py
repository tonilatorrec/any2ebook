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
            INSERT INTO runs(run_at, artifact_type, filename, recipe)
            VALUES('2026-01-01T00:00:00+00:00', 'epub', 'out.epub', '')
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
