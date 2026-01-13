import datetime
import logging
import os
import sqlite3

from .config import Config, ensure_config_path
from .db import ensure_db_path
from .html2ebook import create_epub_from_urls

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_urls_to_convert(path_to_db: str) -> list[str]:
    """Staging"""
    conn = sqlite3.connect(path_to_db)  # will create db if it does not exist
    cur = conn.cursor()
    with conn:
        query = cur.execute('SELECT id, url FROM items WHERE status IN ("new", "failed") AND attempts < 3')
        res = query.fetchall()

        ids = [r[0] for r in res]
        urls = [r[1] for r in res]

        # Save changes
        conn.execute(
            f"""
            UPDATE items SET status = 'staged' WHERE id IN ({",".join("?" * len(ids))});
            """,
            ids,
        )
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
        while os.path.exists(os.path.join(staging_dir, datetime_str + "_" + str(idx_runs))):
            idx_runs += 1
        staging_path = os.path.join(staging_dir, datetime_str + "_" + str(idx_runs) + ".txt")
    else:
        staging_path = os.path.join(staging_dir, datetime_str + ".txt")

    with open(staging_path, "w") as f:
        for url in url_list:
            f.write(url + "\n")

    if os.path.exists(os.path.join(output_dir, datetime_str + ".epub")):
        while os.path.exists(os.path.join(output_dir, datetime_str + "_" + str(idx_runs))):
            idx_runs += 1
        output_path = os.path.join(output_dir, datetime_str + "_" + str(idx_runs) + ".epub")
    else:
        output_path = os.path.join(output_dir, datetime_str + ".epub")

    create_epub_from_urls(url_list, output_path)

    # Save changes in Obsidian database
    conn = sqlite3.connect(path_to_db)  # will create db if it does not exist
    with conn:
        conn.execute(
            f"""
            UPDATE items SET status = 'converted' WHERE id IN ({",".join("?" * len(id_list))});
            """,
            id_list,
        )

def run(config: Config):
    ids, urls = get_urls_to_convert(ensure_db_path())  # -> list[tuple[str]]

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

    stage_and_convert(ids, urls, ensure_db_path(), _output_path, staging_path)

def main():
    config = Config.load(ensure_config_path())
    run(config)

if __name__ == "__main__":
    main()
