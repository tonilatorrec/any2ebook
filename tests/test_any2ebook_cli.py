from pathlib import Path

import pytest

from any2ebook import any2ebook
from any2ebook.config import Config


def test_main_passes_optional_links_file_to_run(monkeypatch, tmp_path: Path):
    """`any2ebook -f <file>` should forward the parsed file path into `run()`."""
    links_file = tmp_path / "blablabla.links"
    links_file.write_text("https://example.com\n", encoding="utf8")
    config = Config(config_path=tmp_path / "config.yaml", output_path=tmp_path)

    monkeypatch.setattr("any2ebook.any2ebook.ensure_config_path", lambda: tmp_path / "config.yaml")
    monkeypatch.setattr("any2ebook.any2ebook.Config.load", lambda _: config)

    called = {}

    def fake_run(cfg, links_file=None, input_dir=None, dry_run=False):
        called["config"] = cfg
        called["links_file"] = links_file
        called["input_dir"] = input_dir
        called["dry_run"] = dry_run
        return True

    monkeypatch.setattr("any2ebook.any2ebook.run", fake_run)

    with pytest.raises(SystemExit) as exc:
        any2ebook.main(["-f", str(links_file)])
    assert exc.value.code == 0

    # CLI wiring should preserve both config and the file argument.
    assert called["config"] is config
    assert called["links_file"] == links_file
    assert called["input_dir"] is None
    assert called["dry_run"] is False


def test_main_passes_optional_input_dir_to_run(monkeypatch, tmp_path: Path):
    input_dir = tmp_path / "inbox"
    input_dir.mkdir()
    config = Config(config_path=tmp_path / "config.yaml", output_path=tmp_path)

    monkeypatch.setattr("any2ebook.any2ebook.ensure_config_path", lambda: tmp_path / "config.yaml")
    monkeypatch.setattr("any2ebook.any2ebook.Config.load", lambda _: config)

    called = {}

    def fake_run(cfg, links_file=None, input_dir=None, dry_run=False):
        called["config"] = cfg
        called["links_file"] = links_file
        called["input_dir"] = input_dir
        called["dry_run"] = dry_run
        return True

    monkeypatch.setattr("any2ebook.any2ebook.run", fake_run)

    with pytest.raises(SystemExit) as exc:
        any2ebook.main(["--input-dir", str(input_dir)])
    assert exc.value.code == 0

    assert called["config"] is config
    assert called["links_file"] is None
    assert called["input_dir"] == input_dir
    assert called["dry_run"] is False


def test_main_passes_dry_run_flag_to_run(monkeypatch, tmp_path: Path):
    links_file = tmp_path / "links.txt"
    links_file.write_text("https://example.com\n", encoding="utf8")
    config = Config(config_path=tmp_path / "config.yaml", output_path=tmp_path)

    monkeypatch.setattr("any2ebook.any2ebook.ensure_config_path", lambda: tmp_path / "config.yaml")
    monkeypatch.setattr("any2ebook.any2ebook.Config.load", lambda _: config)

    called = {}

    def fake_run(cfg, links_file=None, input_dir=None, dry_run=False):
        called["config"] = cfg
        called["links_file"] = links_file
        called["input_dir"] = input_dir
        called["dry_run"] = dry_run
        return True

    monkeypatch.setattr("any2ebook.any2ebook.run", fake_run)

    with pytest.raises(SystemExit) as exc:
        any2ebook.main(["--dry-run", "-f", str(links_file)])
    assert exc.value.code == 0

    assert called["config"] is config
    assert called["links_file"] == links_file
    assert called["input_dir"] is None
    assert called["dry_run"] is True


def test_main_rejects_combined_file_and_input_dir(monkeypatch, tmp_path: Path):
    links_file = tmp_path / "links.txt"
    links_file.write_text("https://example.com\n", encoding="utf8")
    input_dir = tmp_path / "inbox"
    input_dir.mkdir()
    config = Config(config_path=tmp_path / "config.yaml", output_path=tmp_path)

    monkeypatch.setattr("any2ebook.any2ebook.ensure_config_path", lambda: tmp_path / "config.yaml")
    monkeypatch.setattr("any2ebook.any2ebook.Config.load", lambda _: config)

    with pytest.raises(SystemExit):
        any2ebook.main(["-f", str(links_file), "--input-dir", str(input_dir)])


def test_run_test_mode_is_non_interactive_and_uses_links_file(monkeypatch, tmp_path: Path):
    config = Config(config_path=tmp_path / "config.yaml", output_path=tmp_path)
    monkeypatch.setattr("any2ebook.any2ebook.ensure_config_path", lambda: tmp_path / "config.yaml")
    monkeypatch.setattr("any2ebook.any2ebook.Config.load", lambda _: config)

    called = {}

    def fake_ingest_run(cfg, dry_run=False, links_file=None, input_dir=None):
        called["config"] = cfg
        called["dry_run"] = dry_run
        called["links_file"] = links_file
        called["input_dir"] = input_dir
        return {"ready_items": 1, "warnings": 0}

    monkeypatch.setattr("any2ebook.any2ebook.clippings_ingest.run", fake_ingest_run)
    monkeypatch.setattr(
        "builtins.input",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("input() should not be called")),
    )

    ok = any2ebook.run_test_mode()

    assert ok is True
    assert called["config"] is config
    assert called["dry_run"] is True
    assert called["links_file"] is not None
    assert called["links_file"].suffix == ".txt"
    assert called["input_dir"] is None
