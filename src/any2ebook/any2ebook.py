import argparse
import tempfile
from pathlib import Path

from . import clippings_ingest, clippings_to_epub
from .config import Config, ensure_config_path


def run(
    config: Config,
    links_file: Path | None = None,
    input_dir: Path | None = None,
    dry_run: bool = False,
):
    try:
        report = clippings_ingest.run(
            config,
            dry_run=dry_run,
            links_file=links_file,
            input_dir=input_dir,
        )
        if dry_run:
            print(
                "Dry-run results:",
                f"ready_items={report['ready_items']}",
                f"warnings={report['warnings']}",
                f"files_seen={report['files_seen']}",
                f"files_processed={report['files_processed']}",
                f"files_skipped_unchanged={report['files_skipped_unchanged']}",
                sep=" ",
            )
            return True

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
    file_group = parser.add_mutually_exclusive_group()
    file_group.add_argument(
        "-f",
        "--file",
        dest="links_file",
        help="Optional path to a file containing one URL per line.",
    )
    file_group.add_argument(
        "--input-dir",
        dest="input_dir",
        help="Optional path to a folder with mixed .md/.json files to ingest.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a self-contained test workflow (alias for `any2ebook test`).",
    )
    parser.add_argument(
        "-dry-run",
        "--dry-run",
        action="store_true",
        help="Show what would be ingested without writing to DB or converting.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("test", help="Run a self-contained test workflow.")
    args = parser.parse_args(argv)

    if args.test or args.command == "test":
        ok = run_test_mode()
        raise SystemExit(0 if ok else 1)

    links_file: Path | None = None
    input_dir: Path | None = None
    if args.links_file is not None:
        links_file = Path(args.links_file)
        if not links_file.exists() or not links_file.is_file():
            parser.error(f"links_file does not exist or is not a file: {links_file}")

    config = Config.load(ensure_config_path())
    if args.input_dir is not None:
        input_dir = Path(args.input_dir)
        if not input_dir.exists() or not input_dir.is_dir():
            parser.error(f"input_dir does not exist or is not a directory: {input_dir}")
    elif links_file is None and config.input_path is not None:
        input_dir = config.input_path
        if not input_dir.exists() or not input_dir.is_dir():
            parser.error(f"Configured input_path does not exist or is not a directory: {input_dir}")

    ok = run(config, links_file=links_file, input_dir=input_dir, dry_run=args.dry_run)
    raise SystemExit(0 if ok else 1)

if __name__ == "__main__":
    main()
