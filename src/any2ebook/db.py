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
            recipe TEXT NOT NULL
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


def migrate_db(db_path: Path | None = None) -> Path:
    db = ensure_db_path() if db_path is None else Path(db_path)
    conn = sqlite3.connect(db)
    try:
        _create_items_table(conn)
        _create_runs_table_v3(conn)
        _create_run_items_table(conn)
        conn.commit()
        return db
    finally:
        conn.close()


def main():
    migrate_db()


if __name__ == "__main__":
    main()
