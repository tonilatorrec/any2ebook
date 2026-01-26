import argparse

from . import clippings_ingest, clippings_to_epub
from .config import Config, ensure_config_path


def run(config: Config):
    try:
        clippings_ingest.run(config)
        clippings_to_epub.run(config)
        return True
    except Exception as e:
        print("Error:", e)
        return False

def run_test_mode() -> bool:
    config = Config.load(ensure_config_path())
    report = clippings_ingest.run(config, dry_run=True)
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

    config = Config.load(ensure_config_path())
    run(config)

if __name__ == "__main__":
    main()
