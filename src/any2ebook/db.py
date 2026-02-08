import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

APP_NAME = "any2ebook"
LATEST_SCHEMA_VERSION = 2


def user_data_dir(app: str = APP_NAME) -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / app
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return base / app


def ensure_db_path(base_dir: Path | None = None) -> Path:
    d = base_dir or user_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "obsidian.db"


def _create_items_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE items(
            id INTEGER PRIMARY KEY,
            captured_at TEXT NOT NULL,
            payload_ref TEXT NOT NULL UNIQUE,
            payload_type TEXT NOT NULL,
            source TEXT NOT NULL
        )
        """
    )

def _create_aux_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs(
            id INTEGER PRIMARY KEY,
            run_at TEXT NOT NULL,
            total_found INTEGER,
            total_new INTEGER,
            total_converted INTEGER,
            total_failed INTEGER
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_items(
            run_id INTEGER,
            item_id INTEGER,
            action TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(id),
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
        """
    )


def _create_schema_v2(conn: sqlite3.Connection) -> None:
    _create_items_table(conn)
    _create_aux_tables(conn)


def _has_items_table(conn: sqlite3.Connection) -> bool:
    cur = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='items'")
    return cur.fetchone() is not None


def _has_any_user_table(conn: sqlite3.Connection) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' LIMIT 1"
    )
    return cur.fetchone() is not None


def _items_columns(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("PRAGMA table_info(items)").fetchall()
    return [row[1] for row in rows]


def _is_v1_items_schema(conn: sqlite3.Connection) -> bool:
    cols = set(_items_columns(conn))
    return {
        "url",
        "url_hash",
        "obsidian_path",
        "status",
        "attempts",
    }.issubset(cols)


def _is_v2_items_schema(conn: sqlite3.Connection) -> bool:
    cols = set(_items_columns(conn))
    return {"captured_at", "payload_ref", "payload_type", "source"}.issubset(cols)


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.executescript(
        f"""
        PRAGMA foreign_keys=OFF;
        BEGIN;
        ALTER TABLE items RENAME TO items_v1_backup;
        CREATE TABLE items(
            id INTEGER PRIMARY KEY,
            captured_at TEXT NOT NULL,
            payload_ref TEXT NOT NULL UNIQUE,
            payload_type TEXT NOT NULL,
            source TEXT NOT NULL
        );
        INSERT INTO items(
            id, captured_at, payload_ref, payload_type, source
        )
        SELECT
            id,
            COALESCE(created, '{now}'),
            url,
            'url',
            COALESCE(obsidian_path, 'obsidian_clipping')
        FROM items_v1_backup;
        DROP TABLE items_v1_backup;
        COMMIT;
        PRAGMA foreign_keys=ON;
        """
    )
    _create_aux_tables(conn)


def migrate_db(db_path: Path | None = None) -> Path:
    db = ensure_db_path() if db_path is None else Path(db_path)
    conn = sqlite3.connect(db)
    try:
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])

        if version == 0:
            if not _has_any_user_table(conn):
                _create_schema_v2(conn)
                conn.execute(f"PRAGMA user_version = {LATEST_SCHEMA_VERSION}")
                conn.commit()
                return db

            if _has_items_table(conn) and _is_v1_items_schema(conn):
                version = 1
            elif _has_items_table(conn) and _is_v2_items_schema(conn):
                version = 2
            else:
                _create_schema_v2(conn)
                conn.execute(f"PRAGMA user_version = {LATEST_SCHEMA_VERSION}")
                conn.commit()
                return db

        if version == 1:
            _migrate_v1_to_v2(conn)
            conn.execute("PRAGMA user_version = 2")
            conn.commit()
            return db

        if version == 2:
            _create_aux_tables(conn)
            conn.execute("PRAGMA user_version = 2")
            conn.commit()
            return db

        raise RuntimeError(
            f"Unsupported database schema version {version}. Latest supported is {LATEST_SCHEMA_VERSION}."
        )
    finally:
        conn.close()


def main():
    migrate_db()


if __name__ == "__main__":
    main()
