import sqlite3
from pathlib import Path

from any2ebook.clippings_ingest import run
from any2ebook.config import Config


def test_run_ingests_links_file_without_prompting_for_clippings_path(monkeypatch, tmp_path: Path):
    """
    File-ingest mode should:
    - read one URL per line,
    - skip invalid lines,
    - avoid interactive clippings-path prompts/config writes,
    - persist normalized valid URLs with source set to the file path.
    """
    db_path = tmp_path / "any2ebook.db"
    links_file = tmp_path / "links.txt"
    links_file.write_text(
        "\n".join(
            [
                "https://example.com/a?utm_source=newsletter",
                "not-a-url",
                "https://example.com/b",
            ]
        ),
        encoding="utf8",
    )

    monkeypatch.setattr("any2ebook.clippings_ingest.ensure_db_path", lambda: db_path)
    monkeypatch.setattr(
        "builtins.input",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("input() should not be called")),
    )

    config = Config(config_path=tmp_path / "config.yaml", clippings_path=None, output_path=tmp_path)
    monkeypatch.setattr(
        Config,
        "save",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("save() should not be called")),
    )

    report = run(config, links_file=links_file)
    # 2 valid URLs, 1 invalid line.
    assert report == {
        "ready_items": 2,
        "warnings": 1,
        "files_seen": 1,
        "files_processed": 1,
        "files_skipped_unchanged": 0,
    }

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT payload_ref, source FROM items ORDER BY payload_ref"
        ).fetchall()

    # utm_* query params are stripped during URL normalization.
    assert rows == [
        ("https://example.com/a", str(links_file)),
        ("https://example.com/b", str(links_file)),
    ]


def test_run_ingests_capture_queue_json_file(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "any2ebook.db"
    queue_file = tmp_path / "aku_capture_queue.json"
    queue_file.write_text(
        """
        [
          {
            "captured_at": "2026-02-12T15:23:11.465Z",
            "source": "browser_extension",
            "payload_type": "url",
            "payload_ref": "https://example.com/a?utm_source=newsletter"
          },
          {
            "captured_at": "2026-02-12T15:23:12.465Z",
            "source": "browser_extension",
            "payload_type": "url",
            "payload_ref": "https://example.com/b"
          },
          {
            "payload_type": "note",
            "payload_ref": "ignored"
          }
        ]
        """.strip(),
        encoding="utf8",
    )

    monkeypatch.setattr("any2ebook.clippings_ingest.ensure_db_path", lambda: db_path)
    monkeypatch.setattr(
        "builtins.input",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("input() should not be called")),
    )

    config = Config(config_path=tmp_path / "config.yaml", clippings_path=None, output_path=tmp_path)
    monkeypatch.setattr(
        Config,
        "save",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("save() should not be called")),
    )

    report = run(config, links_file=queue_file)
    assert report == {
        "ready_items": 2,
        "warnings": 0,
        "files_seen": 1,
        "files_processed": 1,
        "files_skipped_unchanged": 0,
    }

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT payload_ref, source FROM items ORDER BY payload_ref"
        ).fetchall()

    assert rows == [
        ("https://example.com/a", "browser_extension"),
        ("https://example.com/b", "browser_extension"),
    ]


def test_run_ingests_mixed_input_dir(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "any2ebook.db"
    input_dir = tmp_path / "inbox"
    input_dir.mkdir()

    (input_dir / "capture.json").write_text(
        """
        [
          {
            "captured_at": "2026-02-12T15:23:11.465Z",
            "source": "browser_extension",
            "payload_type": "url",
            "payload_ref": "https://example.com/json"
          }
        ]
        """.strip(),
        encoding="utf8",
    )
    (input_dir / "clip.md").write_text(
        "---\nsource: \"https://example.com/md?utm_source=newsletter\"\n---\n# Title\n",
        encoding="utf8",
    )

    monkeypatch.setattr("any2ebook.clippings_ingest.ensure_db_path", lambda: db_path)
    config = Config(config_path=tmp_path / "config.yaml", clippings_path=None, output_path=tmp_path)

    report = run(config, input_dir=input_dir)
    assert report == {
        "ready_items": 2,
        "warnings": 0,
        "files_seen": 2,
        "files_processed": 2,
        "files_skipped_unchanged": 0,
    }

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT payload_ref, source FROM items ORDER BY payload_ref"
        ).fetchall()

    assert rows == [
        ("https://example.com/json", "browser_extension"),
        ("https://example.com/md", str(input_dir / "clip.md")),
    ]


def test_run_input_dir_skips_unchanged_files(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "any2ebook.db"
    input_dir = tmp_path / "inbox"
    input_dir.mkdir()
    queue_file = input_dir / "capture.json"
    queue_file.write_text(
        """
        [
          {
            "source": "browser_extension",
            "payload_type": "url",
            "payload_ref": "https://example.com/once"
          }
        ]
        """.strip(),
        encoding="utf8",
    )

    monkeypatch.setattr("any2ebook.clippings_ingest.ensure_db_path", lambda: db_path)
    config = Config(config_path=tmp_path / "config.yaml", clippings_path=None, output_path=tmp_path)

    first = run(config, input_dir=input_dir)
    second = run(config, input_dir=input_dir)

    assert first["files_processed"] == 1
    assert first["files_skipped_unchanged"] == 0
    assert second["files_processed"] == 0
    assert second["files_skipped_unchanged"] == 1
