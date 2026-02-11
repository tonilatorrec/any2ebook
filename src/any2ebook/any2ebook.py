import argparse
import tempfile
from pathlib import Path

from . import clippings_ingest, clippings_to_epub
from .config import Config, ensure_config_path


def run(config: Config, links_file: Path | None = None):
    try:
        clippings_ingest.run(config, links_file=links_file)
        clippings_to_epub.run(config)
        return True
    except Exception as e:
        print("Error:", e)
        return False

def run_test_mode() -> bool:
    config = Config.load(ensure_config_path())
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=True, encoding="utf8") as f:
        f.write("https://example.com\n")
        f.flush()
        report = clippings_ingest.run(config, dry_run=True, links_file=Path(f.name))
    print(
        "Test mode results:",
        f"ready_items={report['ready_items']}",
        f"warnings={report['warnings']}",
        sep=" ",
    )
    return True

def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(prog="any2ebook")
    parser.add_argument(
        "-f",
        "--file",
        dest="links_file",
        help="Optional path to a file containing one URL per line.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a self-contained test workflow (alias for `any2ebook test`).",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("test", help="Run a self-contained test workflow.")
    args = parser.parse_args(argv)

    if args.test or args.command == "test":
        ok = run_test_mode()
        raise SystemExit(0 if ok else 1)

    links_file: Path | None = None
    if args.links_file is not None:
        links_file = Path(args.links_file)
        if not links_file.exists() or not links_file.is_file():
            parser.error(f"links_file does not exist or is not a file: {links_file}")

    config = Config.load(ensure_config_path())
    run(config, links_file=links_file)

if __name__ == "__main__":
    main()
