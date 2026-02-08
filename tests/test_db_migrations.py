import sqlite3
from pathlib import Path

from any2ebook.db import migrate_db


def _items_columns(db_path: Path) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("PRAGMA table_info(items)").fetchall()
    return [row[1] for row in rows]


def test_migrate_creates_latest_schema_for_new_db(tmp_path: Path):
    db_path = tmp_path / "obsidian.db"
    migrate_db(db_path)

    with sqlite3.connect(db_path) as conn:
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])

    assert version == 2
    assert _items_columns(db_path) == [
        "id",
        "captured_at",
        "payload_ref",
        "payload_type",
        "source",
    ]


def test_migrate_v1_to_v2_maps_old_fields_into_new_items_schema(tmp_path: Path):
    db_path = tmp_path / "obsidian.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE items(
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                url_hash TEXT NOT NULL UNIQUE,
                obsidian_path TEXT NOT NULL,
                status TEXT NOT NULL,
                title TEXT,
                author TEXT,
                published TEXT,
                created TEXT,
                attempts INTEGER NOT NULL,
                last_error TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO items(url, url_hash, obsidian_path, status, attempts)
            VALUES('https://example.com/a', 'hash-a', '/vault/a.md', 'new', 0)
            """
        )
        conn.execute("PRAGMA user_version = 1")
        conn.commit()

    migrate_db(db_path)

    with sqlite3.connect(db_path) as conn:
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        rows = conn.execute(
            "SELECT payload_ref, payload_type, source, captured_at FROM items"
        ).fetchall()
        conn.execute(
            """
            INSERT INTO items(captured_at, payload_ref, payload_type, source)
            VALUES('2026-01-01T00:00:00+00:00', 'https://example.com/b', 'url', 'raw_text')
            """
        )
        conn.commit()

    assert version == 2
    assert len(rows) == 1
    assert rows[0][0:3] == ("https://example.com/a", "url", "/vault/a.md")
    assert rows[0][3]


def test_migrate_legacy_unversioned_schema(tmp_path: Path):
    db_path = tmp_path / "obsidian.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE items(
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                url_hash TEXT NOT NULL UNIQUE,
                obsidian_path TEXT NOT NULL,
                status TEXT NOT NULL,
                title TEXT,
                author TEXT,
                published TEXT,
                created TEXT,
                attempts INTEGER NOT NULL,
                last_error TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO items(url, url_hash, obsidian_path, status, attempts)
            VALUES('https://example.com/legacy', 'hash-legacy', '/vault/legacy.md', 'new', 0)
            """
        )
        conn.commit()

    migrate_db(db_path)

    with sqlite3.connect(db_path) as conn:
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        row = conn.execute(
            "SELECT payload_ref, source FROM items WHERE payload_ref = 'https://example.com/legacy'"
        ).fetchone()

    assert version == 2
    assert _items_columns(db_path) == [
        "id",
        "captured_at",
        "payload_ref",
        "payload_type",
        "source",
    ]
    assert row == ("https://example.com/legacy", "/vault/legacy.md")
