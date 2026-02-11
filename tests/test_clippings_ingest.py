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
    assert report == {"ready_items": 2, "warnings": 1}

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT payload_ref, source FROM items ORDER BY payload_ref"
        ).fetchall()

    # utm_* query params are stripped during URL normalization.
    assert rows == [
        ("https://example.com/a", str(links_file)),
        ("https://example.com/b", str(links_file)),
    ]
