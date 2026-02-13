from pathlib import Path

import pytest

from any2ebook import any2ebook
from any2ebook.config import Config


def test_main_passes_optional_links_file_to_run(monkeypatch, tmp_path: Path):
    """`any2ebook -f <file>` should forward the parsed file path into `run()`."""
    # create test file with a fake link
    links_file = tmp_path / "links.txt"
    links_file.write_text("https://example.com\n", encoding="utf8")

    # create test Config object with a fake path
    config = Config(config_path=tmp_path / "config.yaml", output_path=tmp_path)

    # in order for the program not to check the fake config path, we need to 
    # patch the functions where the config is parsed / checked.
    # patch ensure_config_path() to always return the path to the fake config path
    # so that ensure_config_path() does not create a default config file in that fake path
    monkeypatch.setattr("any2ebook.any2ebook.ensure_config_path", lambda: tmp_path / "config.yaml")
    
    # patch Config.load() to always return the test config we created
    # so that it does not raise ConfigNotFoundError because the (fake) config path does not exist
    monkeypatch.setattr("any2ebook.any2ebook.Config.load", lambda _: config)

    called = {}

    def fake_run(cfg, links_file=None, input_dir=None, dry_run=False):
        # just stores the arguments passed to any2ebook.run(); 
        # `called` is defined outside the function
        called["config"] = cfg
        called["links_file"] = links_file
        called["input_dir"] = input_dir
        called["dry_run"] = dry_run
        return True

    # patch any2ebook.run() so that it does not do any ingestion/conversion
    # when any2ebook.main() calls any2ebook.run() -> fake_run(), it will
    # also pass the arguments that would have been passed to any2ebook.run()
    monkeypatch.setattr("any2ebook.any2ebook.run", fake_run)

    # test that any2ebook.main() runs succesfully with the patched fake_run()
    with pytest.raises(SystemExit) as exc:
        any2ebook.main(["-f", str(links_file)])
    assert exc.value.code == 0

    # test that the arguments passed to any2ebook.run() and therefore fake_run()
    # are the correct ones, especially links_file
    # CLI wiring should preserve both config and the file argument.
    assert called["config"] is config
    assert called["links_file"] == links_file
    assert called["input_dir"] is None
    assert called["dry_run"] is False


def test_main_passes_optional_input_dir_to_run(monkeypatch, tmp_path: Path):
    """`any2ebook --input-dir <input_dir>` should forward the parsed input_dir into `run()`.
    This is the same function as test_main_passes_optional_links_file_to_run() but 
    testing --input-dir instead of -f."""

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
    """`any2ebook --dry-run` should forward the dry_run flag into `run()`.
    This is the same function as test_main_passes_optional_links_file_to_run() but 
    testing --dry-run instead of -f."""

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
    """`any2ebook.main()` should not accept both -f and --input-dir.
    """
    
    links_file = tmp_path / "links.txt"
    links_file.write_text("https://example.com\n", encoding="utf8")
    input_dir = tmp_path / "inbox"
    input_dir.mkdir()
    config = Config(config_path=tmp_path / "config.yaml", output_path=tmp_path)

    monkeypatch.setattr("any2ebook.any2ebook.ensure_config_path", lambda: tmp_path / "config.yaml")
    monkeypatch.setattr("any2ebook.any2ebook.Config.load", lambda _: config)

    # here we do not need to patch any2ebook.run() because the parser error is raised before
    # argparse errors make the program exit with code 2
    with pytest.raises(SystemExit) as exc:
        any2ebook.main(["-f", str(links_file), "--input-dir", str(input_dir)])
    assert exc.value.code == 2


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
