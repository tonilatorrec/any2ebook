import os
from pathlib import Path
import sqlite3
import yaml
import hashlib
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from any2ebook.paths import ensure_config
from .create_obsidian_db import db_path


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
    for file_path in main_path.glob("*/*"):
        if file_path.is_file() and file_path.suffix == '.md':
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
    with open(file_path, 'r', encoding='utf8') as f:
        found_delimiter = False
        for line in f.readlines():
            if line == '---\n' and found_delimiter:
                break
            elif line == '---\n' and not found_delimiter:
                found_delimiter = True
            else:
                lines.append(line)
    fm = yaml.safe_load(''.join(lines))   
    return fm

def hash_url(url: str) -> str:
    """
    Compute a stable content hash for a normalized URL.

    Implementation hints:
        - Use SHA-1 or SHA-256 of the normalized URL string.
        - Return the hex digest.
    """    

def normalize_url(url: str) -> str:
    """
    Normalize URL for deduplication: remove trackers, lowercase host/scheme,
    sort query params, strip fragments.
    """
    p = urlparse(url.strip())
    # lowercase scheme and hostname
    scheme = p.scheme.lower()
    netloc = p.hostname.lower() if p.hostname else ''
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

def hash_url(url: str) -> str:
    """Return a short stable SHA1 hash of the normalized URL."""
    norm = normalize_url(url)
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()

def upsert_item(
        db_path: Path,
        item_front_matter: dict,
        url_hash: str,
        md_file_path: str
):
    """
    Insert-or-update an item keyed by url_hash.
    - Does NOT change status/attempts during scans; only refreshes light metadata + last_seen.
    - Returns the integer primary-key id of the row.
    """

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    sql_query = """
    INSERT INTO items (
        url, url_hash, obsidian_path, status, title, author, published,
        created, attempts, last_error
    ) VALUES (
        :url, :url_hash, :obsidian_path, "new", :title, :author,
        :published, :created, 0, NULL
    )
    ON CONFLICT(url_hash) DO UPDATE SET
        title = COALESCE(excluded.title, items.title),
        author = COALESCE(excluded.author, items.author),
        published = COALESCE(excluded.published, items.published),
        created = COALESCE(excluded.created, items.created),
        obsidian_path = excluded.obsidian_path
    RETURNING id;
    """
    with conn:
        cur.execute(sql_query, 
                    {"url": item_front_matter['source'],
                    "url_hash": url_hash,
                    "obsidian_path": str(md_file_path),
                    "title": item_front_matter['title'],
                    "author": None if item_front_matter['author'] is None else item_front_matter['author'][0].strip('[[').strip(']]'),
                    "published": item_front_matter['published'],
                    "created": item_front_matter['created']})
        row = cur.fetchone()
        return int(row[0])

def main():
    cfg_path = ensure_config()
    with open(cfg_path, 'r') as f:
        config = yaml.safe_load(f)

    obsidian_clippings_path = config['Obsidian clippings path']
    if obsidian_clippings_path is None:
        print("Obsidian clippings path not yet set. ", end="")
        while True:
            obsidian_clippings_path = input(
            """Please set path:\n> """
            )
            if os.path.exists(obsidian_clippings_path):
                break
        config['Obsidian clippings path'] = obsidian_clippings_path
    elif not os.path.exists(obsidian_clippings_path):
        print("Obsidian clippings path does not exist. ", end="")
        while not os.path.exists(obsidian_clippings_path):
            obsidian_clippings_path = input(
            """Please set valid path:\n> """
        )
        config['Obsidian clippings path'] = obsidian_clippings_path
    else:
        pass

    with open(cfg_path, 'w') as f:
        yaml.dump(config, f)

    files = find_clipping_files(obsidian_clippings_path)
    for file in files:
        front_matter = read_front_matter(file)
        file_url = front_matter['source']
        normalized_file_url = hash_url(file_url)
        id = upsert_item(db_path(), front_matter, normalized_file_url,
                    file)
        print(id)
if __name__ == '__main__':
    main()