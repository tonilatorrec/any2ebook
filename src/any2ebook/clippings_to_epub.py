import datetime
import logging
import os
import sqlite3
import sys
from pathlib import Path

from .config import Config, ensure_config_path
from .db import ensure_db_path, migrate_db
from .html2ebook import create_epub_from_urls

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _ensure_parent_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _fsync_file(path: str) -> None:
    with open(path, "rb") as f:
        os.fsync(f.fileno())


def _fsync_dir(path: str) -> None:
    # Directory fsync is not reliably supported on Windows Python file descriptors.
    if os.name == "nt":
        return
    dir_path = str(Path(path).parent)
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    dir_fd = os.open(dir_path, flags)
    try:
        os.fsync(dir_fd)
    except OSError:
        # Some filesystems/OS combinations don't allow fsync on directory fds.
        logger.debug("Skipping directory fsync for %s on %s", dir_path, sys.platform, exc_info=True)
    finally:
        os.close(dir_fd)


def _atomic_finalize_file(tmp_path: str, final_path: str) -> None:
    _fsync_file(tmp_path)
    os.replace(tmp_path, final_path)
    _fsync_dir(final_path)


def _cleanup_file(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        logger.warning("Failed to cleanup file %s", path, exc_info=True)


def get_urls_to_convert(path_to_db: str) -> tuple[list[int], list[str]]:
    """Pick URL payloads that have never been converted and never failed before."""
    conn = sqlite3.connect(path_to_db)  # will create db if it does not exist
    cur = conn.cursor()
    with conn:
        query = cur.execute(
            """
            SELECT i.id, i.payload_ref
            FROM items i
            WHERE i.payload_type = 'url'
              AND NOT EXISTS (
                  SELECT 1
                  FROM run_items ri
                  WHERE ri.item_id = i.id AND ri.action IN ('converted', 'failed')
              )
            """
        )
        res = query.fetchall()

        ids = [r[0] for r in res]
        urls = [r[1] for r in res]
    return ids, urls


def stage_and_convert(
    id_list: list[int],
    url_list: list[str],
    path_to_db: str,
    output_dir: str,
    staging_dir: str,
) -> None:
    datetime_str = datetime.datetime.now().strftime("%Y-%m-%d")
    idx_runs = 1
    if os.path.exists(os.path.join(staging_dir, datetime_str + ".txt")):
        while os.path.exists(os.path.join(staging_dir, datetime_str + "_" + str(idx_runs) + ".txt")):
            idx_runs += 1
        staging_path = os.path.join(staging_dir, datetime_str + "_" + str(idx_runs) + ".txt")
    else:
        staging_path = os.path.join(staging_dir, datetime_str + ".txt")

    with open(staging_path, "w") as f:
        for url in url_list:
            f.write(url + "\n")

    if os.path.exists(os.path.join(output_dir, datetime_str + ".epub")):
        while os.path.exists(os.path.join(output_dir, datetime_str + "_" + str(idx_runs) + ".epub")):
            idx_runs += 1
        output_path = os.path.join(output_dir, datetime_str + "_" + str(idx_runs) + ".epub")
    else:
        output_path = os.path.join(output_dir, datetime_str + ".epub")

    tmp_output_path = output_path + ".tmp"
    _cleanup_file(tmp_output_path)

    conn = sqlite3.connect(path_to_db)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        cur.execute(
            """
            INSERT INTO runs(run_at, artifact_type, filename, recipe, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (datetime.datetime.now().isoformat(), "epub", output_path, "", "in_progress"),
        )
        run_id = int(cur.lastrowid)
        try:
            item_results = create_epub_from_urls(url_list, tmp_output_path)
            if len(item_results) != len(id_list):
                raise RuntimeError("Mismatch between conversion results and selected items.")

            has_converted = any(item_results)
            if has_converted:
                if not os.path.exists(tmp_output_path):
                    raise RuntimeError("EPUB conversion reported success but artifact file is missing.")
                _ensure_parent_dir(output_path)
                _atomic_finalize_file(tmp_output_path, output_path)
                final_filename = output_path
            else:
                _cleanup_file(tmp_output_path)
                final_filename = ""

            converted = []
            failed = []
            for item_id, is_ok in zip(id_list, item_results):
                if is_ok and has_converted:
                    converted.append((run_id, item_id, "converted"))
                else:
                    failed.append((run_id, item_id, "failed"))

            cur.executemany(
                "INSERT INTO run_items(run_id, item_id, action) VALUES (?, ?, ?)",
                converted + failed,
            )
            cur.execute(
                "UPDATE runs SET filename = ?, status = ? WHERE id = ?",
                (final_filename, "committed", run_id),
            )
            conn.commit()
        except KeyboardInterrupt:
            conn.rollback()
            _cleanup_file(tmp_output_path)
            raise
        except Exception:
            conn.rollback()
            _cleanup_file(tmp_output_path)
            raise
    finally:
        conn.close()

def run(config: Config):
    db_path = migrate_db(ensure_db_path())
    ids, urls = get_urls_to_convert(db_path)  # -> list[tuple[str]]

    _output_path = config.output_path
    if _output_path is None:
        print("Output path not yet set. ", end="")
        while True:
            _output_path = input("""Please set path:\n> """)
            if os.path.exists(_output_path):
                break
        config.output_path = _output_path
    elif not os.path.exists(_output_path):
        k = input("Output path does not exist. Create? [y/n]")
        os.makedirs(k)
        config.output_path = _output_path

    config.save()

    staging_path = os.path.join(config.config_path.parent, "staging")
    if not os.path.exists(staging_path):
        os.mkdir(staging_path)

    stage_and_convert(ids, urls, db_path, _output_path, staging_path)

def main():
    config = Config.load(ensure_config_path())
    run(config)

if __name__ == "__main__":
    main()
