import sqlite3
from pathlib import Path

from any2ebook.clippings_to_epub import get_urls_to_convert, stage_and_convert
from any2ebook.db import migrate_db


def _seed_items(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO items(captured_at, payload_ref, payload_type, source)
            VALUES (?, ?, 'url', ?)
            """,
            [
                ("2026-01-01T00:00:00+00:00", "https://example.com/a", "raw_text"),
                ("2026-01-01T00:00:00+00:00", "https://example.com/b", "raw_text"),
                ("2026-01-01T00:00:00+00:00", "https://example.com/c", "raw_text"),
            ],
        )
        conn.commit()


def test_get_urls_to_convert_excludes_converted_and_failed(tmp_path: Path):
    db_path = tmp_path / "obsidian.db"
    migrate_db(db_path)
    _seed_items(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO runs(run_at, artifact_type, filename, recipe)
            VALUES('2026-01-01T00:00:00+00:00', 'epub', 'out.epub', '')
            """
        )
        run_id = int(conn.execute("SELECT id FROM runs LIMIT 1").fetchone()[0])
        conn.executemany(
            "INSERT INTO run_items(run_id, item_id, action) VALUES (?, ?, ?)",
            [(run_id, 1, "converted"), (run_id, 2, "failed")],
        )
        conn.commit()

    ids, urls = get_urls_to_convert(str(db_path))
    assert ids == [3]
    assert urls == ["https://example.com/c"]


def test_stage_and_convert_records_failed_and_converted(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "obsidian.db"
    output_dir = tmp_path / "out"
    staging_dir = tmp_path / "staging"
    output_dir.mkdir()
    staging_dir.mkdir()

    migrate_db(db_path)
    _seed_items(db_path)

    def fake_create_epub(urls, output_filename, path_to_db=None):
        assert len(urls) == 3
        return [True, False, True]

    monkeypatch.setattr("any2ebook.clippings_to_epub.create_epub_from_urls", fake_create_epub)

    stage_and_convert(
        id_list=[1, 2, 3],
        url_list=[
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
        ],
        path_to_db=str(db_path),
        output_dir=str(output_dir),
        staging_dir=str(staging_dir),
    )

    with sqlite3.connect(db_path) as conn:
        actions = conn.execute(
            "SELECT item_id, action FROM run_items ORDER BY item_id"
        ).fetchall()

    assert actions == [(1, "converted"), (2, "failed"), (3, "converted")]

    ids, urls = get_urls_to_convert(str(db_path))
    assert ids == []
    assert urls == []
