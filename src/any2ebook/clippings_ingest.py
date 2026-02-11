import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import yaml

from .config import Config, ensure_config_path
from .db import ensure_db_path, migrate_db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def read_links_file(path: str | os.PathLike | Path) -> list[str]:
    """Read a text file containing one URL per line."""
    links: list[str] = []
    with open(path, "r", encoding="utf8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if line:
                links.append(line)
    return links

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


def run(config: Config, dry_run: bool = False, links_file: Path | None = None) -> dict:
    db_path = migrate_db(ensure_db_path())
    ready_items = 0
    warnings = 0

    if links_file is not None:
        links = read_links_file(links_file)
        for link in links:
            if not is_valid_http_url(link):
                warnings += 1
                logger.warning("Skipping invalid URL in %s: %s", links_file, link)
                continue
            normalized_link = normalize_url(link)
            if not dry_run:
                upsert_item(db_path, {}, normalized_link, str(links_file))
            ready_items += 1
        return {"ready_items": ready_items, "warnings": warnings}

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
        return {"ready_items": ready_items, "warnings": warnings}

def main():
    config = Config.load(ensure_config_path())
    run(config)

if __name__ == "__main__":
    main()
