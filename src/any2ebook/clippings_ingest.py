import logging
import os
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import yaml

from .config import Config, ensure_config_path
from .db import ensure_db_path, migrate_db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _read_links_lines(raw_text: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if line:
            links.append({"payload_ref": line})
    return links


def _json_item_to_link_entry(item: object) -> dict[str, str] | None:
    # Support plain JSON URL arrays: ["https://...", "https://..."].
    if isinstance(item, str):
        return {"payload_ref": item}

    if not isinstance(item, dict):
        return None

    payload_ref = item.get("payload_ref")
    if not isinstance(payload_ref, str):
        return None

    payload_type = item.get("payload_type")
    if payload_type is not None and payload_type != "url":
        return None

    entry: dict[str, str] = {"payload_ref": payload_ref}
    captured_at = item.get("captured_at")
    source = item.get("source")
    if isinstance(captured_at, str):
        entry["captured_at"] = captured_at
    if isinstance(source, str):
        entry["source"] = source
    return entry


def _read_queue_json(raw_text: str) -> list[dict[str, str]]:
    payload = json.loads(raw_text)
    if isinstance(payload, dict):
        if isinstance(payload.get("queue"), list):
            payload = payload["queue"]
        else:
            # Also support a single capture entry object.
            payload = [payload]
    if not isinstance(payload, list):
        raise ValueError(
            "JSON input must be a URL array, a capture-item array, "
            "or an object containing either a capture item or 'queue' array"
        )

    links: list[dict[str, str]] = []
    for item in payload:
        entry = _json_item_to_link_entry(item)
        if entry is not None:
            links.append(entry)
    return links


def read_links_file(path: str | os.PathLike | Path) -> list[dict[str, str]]:
    """
    Read ingest input from either:
    - text with one URL per line, or
    - JSON URL lists, capture queue JSON, or a single capture item JSON.
    """
    with open(path, "r", encoding="utf8") as f:
        raw_text = f.read()

    stripped = raw_text.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            return _read_queue_json(raw_text)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    return _read_links_lines(raw_text)

def find_clipping_files(path: str | os.PathLike) -> list[Path]:
    """
    Return a list of Markdown files inside the vault's Clippings directory.

    Implementation notes:
        - Compute: clippings_path = cfg.vault_path / cfg.clippings_dir_name
        - Recursively glob for '*.md' (or flat, if your folder is flat).
        - Only return files (skip dirs, symlinks if desired).
    """
    files = []
    main_path = Path(path)
    for file_path in main_path.rglob("*/*"):
        if file_path.is_file() and file_path.suffix == ".md":
            files.append(file_path)
    return files


def find_ingest_files(path: str | os.PathLike) -> list[Path]:
    files: list[Path] = []
    main_path = Path(path)
    for file_path in main_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in {".md", ".json"}:
            files.append(file_path)
    return sorted(files, key=lambda p: str(p))


def read_front_matter(file_path: str | os.PathLike | Path) -> dict:
    """
    Read the YAML front matter from a Markdown file and return it as a dict-like mapping.

    Expected behavior:
        - Front matter is bounded by lines starting with '---' (top of file).
        - Parse only the first YAML block; ignore Markdown body.
        - Return {} if no valid YAML is present.
        - You may use a YAML library (e.g., 'yaml.safe_load') in your implementation.

    Raises:
        ValueError: if YAML is syntactically invalid and cannot be parsed.
    """
    lines = []
    with open(file_path, "r", encoding="utf8") as f:
        found_delimiter = False
        for line in f.readlines():
            if line == "---\n" and found_delimiter:
                break
            elif line == "---\n" and not found_delimiter:
                found_delimiter = True
            else:
                lines.append(line)
    fm = yaml.safe_load("".join(lines))
    return fm


def normalize_url(url: str) -> str:
    """
    Normalize URL for deduplication: remove trackers, lowercase host/scheme,
    sort query params, strip fragments.
    """
    p = urlparse(url.strip())
    # lowercase scheme and hostname
    scheme = p.scheme.lower()
    netloc = p.hostname.lower() if p.hostname else ""
    if p.port and p.port not in (80, 443):
        netloc += f":{p.port}"

    # clean query
    query_pairs = parse_qsl(p.query, keep_blank_values=True)
    filtered = [
        (k, v)
        for (k, v) in query_pairs
        if not k.lower().startswith(("utm_", "fbclid", "gclid", "mc_", "ref", "igshid"))
    ]
    filtered.sort()  # order-independent
    clean_query = urlencode(filtered)

    # clean path
    path = p.path
    if path.endswith("/") and path != "/":
        path = path[:-1]

    # rebuild URL
    return urlunparse((scheme, netloc, path, "", clean_query, ""))


def is_valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def upsert_item(
    db_path: Path, item_front_matter: dict, payload_ref: str, md_file_path: str | None
) -> int:
    """
    Insert-or-update an item keyed by payload_ref.
    - Returns the integer primary-key id of the row.
    """

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    sql_query = """
    INSERT INTO items (
        captured_at, payload_ref, payload_type, source
    ) VALUES (
        :captured_at, :payload_ref, :payload_type, :source
    )
    ON CONFLICT(payload_ref) DO UPDATE SET
        source = excluded.source
    RETURNING id;
    """
    captured_at = item_front_matter.get("created") or datetime.now(timezone.utc).isoformat()

    with conn:
        cur.execute(
            sql_query,
            {
                "captured_at": captured_at,
                "payload_ref": payload_ref,
                "payload_type": "url",
                "source": str(md_file_path) if md_file_path is not None else "raw_text",
            },
        )
        row = cur.fetchone()
        return int(row[0])


def _file_fingerprint(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return (int(stat.st_size), int(stat.st_mtime_ns))


def _is_unchanged_successfully_ingested(db_path: Path, file_path: Path) -> bool:
    size, mtime_ns = _file_fingerprint(file_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT size, mtime_ns, status FROM ingest_files WHERE path = ?",
            (str(file_path.resolve()),),
        ).fetchone()
    if row is None:
        return False
    return int(row[0]) == size and int(row[1]) == mtime_ns and row[2] == "ok"


def _mark_ingest_file(db_path: Path, file_path: Path, status: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    size, mtime_ns = _file_fingerprint(file_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO ingest_files(path, size, mtime_ns, last_ingested_at, status)
            VALUES (:path, :size, :mtime_ns, :last_ingested_at, :status)
            ON CONFLICT(path) DO UPDATE SET
                size = excluded.size,
                mtime_ns = excluded.mtime_ns,
                last_ingested_at = excluded.last_ingested_at,
                status = excluded.status
            """,
            {
                "path": str(file_path.resolve()),
                "size": size,
                "mtime_ns": mtime_ns,
                "last_ingested_at": now,
                "status": status,
            },
        )
        conn.commit()


def _ingest_links_entries(
    db_path: Path, entries: list[dict[str, str]], source_file: Path | None, dry_run: bool
) -> tuple[int, int]:
    ready_items = 0
    warnings = 0
    for link_entry in entries:
        link = link_entry["payload_ref"]
        if not is_valid_http_url(link):
            warnings += 1
            logger.warning("Skipping invalid URL in %s: %s", source_file, link)
            continue
        normalized_link = normalize_url(link)
        if not dry_run:
            upsert_item(
                db_path,
                {"created": link_entry.get("captured_at")},
                normalized_link,
                link_entry.get("source") or (str(source_file) if source_file else None),
            )
        ready_items += 1
    return ready_items, warnings


def run(
    config: Config,
    dry_run: bool = False,
    links_file: Path | None = None,
    input_dir: Path | None = None,
) -> dict:
    if links_file is not None and input_dir is not None:
        raise ValueError("Use either links_file or input_dir, not both")

    db_path = migrate_db(ensure_db_path())
    ready_items = 0
    warnings = 0
    files_seen = 0
    files_processed = 0
    files_skipped_unchanged = 0

    if links_file is not None:
        links = read_links_file(links_file)
        files_seen = 1
        files_processed = 1
        added, warns = _ingest_links_entries(db_path, links, links_file, dry_run)
        ready_items += added
        warnings += warns
        return {
            "ready_items": ready_items,
            "warnings": warnings,
            "files_seen": files_seen,
            "files_processed": files_processed,
            "files_skipped_unchanged": files_skipped_unchanged,
        }

    if input_dir is not None:
        for file in find_ingest_files(input_dir):
            files_seen += 1
            try:
                if not dry_run and _is_unchanged_successfully_ingested(db_path, file):
                    files_skipped_unchanged += 1
                    continue

                files_processed += 1
                file_status = "ok"
                if file.suffix.lower() == ".md":
                    front_matter = read_front_matter(file)
                    if not front_matter or "source" not in front_matter or not front_matter["source"]:
                        warnings += 1
                        file_status = "warning"
                        logger.warning("Missing source front matter in %s", file)
                    else:
                        file_url = front_matter["source"]
                        normalized_file_url = normalize_url(file_url)
                        if not dry_run:
                            upsert_item(db_path, front_matter, normalized_file_url, file)
                        ready_items += 1
                elif file.suffix.lower() == ".json":
                    links = read_links_file(file)
                    added, warns = _ingest_links_entries(db_path, links, file, dry_run)
                    ready_items += added
                    warnings += warns
                    if warns > 0:
                        file_status = "warning"

                if not dry_run:
                    _mark_ingest_file(db_path, file, file_status)
            except Exception as e:
                warnings += 1
                logger.warning("Failed to ingest %s: %s", file, e)
                if not dry_run:
                    _mark_ingest_file(db_path, file, "error")
                continue
        return {
            "ready_items": ready_items,
            "warnings": warnings,
            "files_seen": files_seen,
            "files_processed": files_processed,
            "files_skipped_unchanged": files_skipped_unchanged,
        }

    # TODO: should these checks run here or when setting up config?
    else:
        _clippings_path = config.clippings_path
        if _clippings_path is None:
            print("Clippings path not yet set. ", end="")
            while True:
                _clippings_path = input("""Please set path:\n> """)
                if os.path.exists(_clippings_path):
                    break
            config.clippings_path = _clippings_path
        elif not os.path.exists(_clippings_path):
            print("Clippings path does not exist. ", end="")
            while not os.path.exists(_clippings_path):
                _clippings_path = input("""Please set valid path:\n> """)
            config.clippings_path = _clippings_path

        config.save()
        files = find_clipping_files(config.clippings_path)
        for file in files:
            files_seen += 1
            files_processed += 1
            try:
                front_matter = read_front_matter(file)
                if not front_matter or "source" not in front_matter or not front_matter["source"]:
                    warnings += 1
                    logger.warning("Missing source front matter in %s", file)
                    continue
                file_url = front_matter["source"]
                normalized_file_url = normalize_url(file_url)
                if not dry_run:
                    upsert_item(db_path, front_matter, normalized_file_url, file)
                ready_items += 1
            except Exception as e:
                warnings += 1
                logger.warning("Failed to parse front matter in %s: %s", file, e)
                continue
        return {
            "ready_items": ready_items,
            "warnings": warnings,
            "files_seen": files_seen,
            "files_processed": files_processed,
            "files_skipped_unchanged": files_skipped_unchanged,
        }

def main():
    config = Config.load(ensure_config_path())
    run(config)

if __name__ == "__main__":
    main()
