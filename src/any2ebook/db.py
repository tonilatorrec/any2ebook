import os
import sqlite3
import sys
from pathlib import Path

APP_NAME = "any2ebook"


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
    return d / "any2ebook.db"


def _create_items_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items(
            id INTEGER PRIMARY KEY,
            captured_at TEXT NOT NULL,
            payload_ref TEXT NOT NULL UNIQUE,
            payload_type TEXT NOT NULL,
            source TEXT NOT NULL
        )
        """
    )

def _create_runs_table_v3(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs(
            id INTEGER PRIMARY KEY,
            run_at TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            recipe TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )


def _create_run_items_table(conn: sqlite3.Connection) -> None:
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


def _create_ingest_files_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ingest_files(
            path TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            last_ingested_at TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _assert_current_schema(conn: sqlite3.Connection) -> None:
    expected = {
        "items": {"id", "captured_at", "payload_ref", "payload_type", "source"},
        "runs": {"id", "run_at", "artifact_type", "filename", "recipe", "status"},
        "run_items": {"run_id", "item_id", "action"},
        "ingest_files": {"path", "size", "mtime_ns", "last_ingested_at", "status"},
    }
    for table, cols in expected.items():
        table_cols = _table_columns(conn, table)
        if not cols.issubset(table_cols):
            raise RuntimeError(
                f"Unsupported database schema in table '{table}'. "
                f"Expected columns: {sorted(cols)}. Found: {sorted(table_cols)}."
            )


def _upgrade_runs_table_if_needed(conn: sqlite3.Connection) -> None:
    runs_cols = _table_columns(conn, "runs")
    if "artifact_type" not in runs_cols:
        conn.execute(
            "ALTER TABLE runs ADD COLUMN artifact_type TEXT NOT NULL DEFAULT 'epub'"
        )
    if "filename" not in runs_cols:
        conn.execute(
            "ALTER TABLE runs ADD COLUMN filename TEXT NOT NULL DEFAULT ''"
        )
    if "recipe" not in runs_cols:
        conn.execute(
            "ALTER TABLE runs ADD COLUMN recipe TEXT NOT NULL DEFAULT ''"
        )
    if "status" not in runs_cols:
        conn.execute(
            "ALTER TABLE runs ADD COLUMN status TEXT NOT NULL DEFAULT 'committed'"
        )


def _run_items_fk_targets(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("PRAGMA foreign_key_list(run_items)").fetchall()
    return {row[3]: row[2] for row in rows}


def _repair_run_items_table_if_needed(conn: sqlite3.Connection) -> None:
    targets = _run_items_fk_targets(conn)
    if targets.get("run_id") == "runs" and targets.get("item_id") == "items":
        return

    conn.executescript(
        """
        PRAGMA foreign_keys=OFF;
        BEGIN;
        CREATE TABLE run_items_new(
            run_id INTEGER,
            item_id INTEGER,
            action TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(id),
            FOREIGN KEY(item_id) REFERENCES items(id)
        );
        INSERT INTO run_items_new(run_id, item_id, action)
        SELECT run_id, item_id, action FROM run_items;
        DROP TABLE run_items;
        ALTER TABLE run_items_new RENAME TO run_items;
        COMMIT;
        PRAGMA foreign_keys=ON;
        """
    )


def migrate_db(db_path: Path | None = None) -> Path:
    db = ensure_db_path() if db_path is None else Path(db_path)
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        _create_items_table(conn)
        _create_runs_table_v3(conn)
        _create_run_items_table(conn)
        _create_ingest_files_table(conn)
        _upgrade_runs_table_if_needed(conn)
        _repair_run_items_table_if_needed(conn)
        _assert_current_schema(conn)
        conn.commit()
        return db
    finally:
        conn.close()


def main():
    migrate_db()


if __name__ == "__main__":
    main()
