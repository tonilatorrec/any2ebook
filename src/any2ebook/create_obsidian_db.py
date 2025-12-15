import sqlite3
import os
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

def db_path() -> Path:
    d = user_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "obsidian.db"

def main():
    db = db_path()
    conn = sqlite3.connect(db) # will create db if it does not exist
    cursor = conn.cursor()

    # create "items" table which stores information about the clippings
    cursor.execute(
        """
        create table items(
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

    cursor.execute(
        """
        create table runs(
            id INTEGER PRIMARY KEY,
            run_at TEXT NOT NULL,
            total_found INTEGER,
            total_new INTEGER,
            total converted INTEGER,
            total_failed INTEGER
        )
        """
    )

    cursor.execute(
        """
        create table run_items(
            run_id INTEGER,
            item_id INTEGER,
            action TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(id),
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
        """
    )

if __name__ == '__main__':
    main()