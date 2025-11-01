import sqlite3

def main():
    conn = sqlite3.connect('obsidian.db') # will create db if it does not exist
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