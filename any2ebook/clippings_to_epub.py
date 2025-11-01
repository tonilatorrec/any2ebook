# here i can just call html2ebook.create_epub_from_urls() with all the 
# clippings selected in clippings_staging.py

import sqlite3
import datetime
import yaml
import os

from html2ebook import create_epub_from_urls

def get_urls_to_convert(path_to_db: str) -> list[str]:
    """Staging"""
    conn = sqlite3.connect(path_to_db) # will create db if it does not exist
    cur = conn.cursor()
    with conn:
        query = cur.execute('SELECT id, url FROM items WHERE status IN ("new", "failed")')
        res = query.fetchall()

        ids = [r[0] for r in res]
        urls = [r[1] for r in res]

        # Save changes
        conn.execute(
           f"""
            UPDATE items SET status = 'staged' WHERE id IN ({','.join('?'*len(ids))});
            """, ids
        )
    return ids, urls

def stage_and_convert(id_list: list[int], url_list: list[str], path_to_db: str, output_dir: str, staging_dir: str) -> None:
    datetime_str = datetime.datetime.now().strftime("%Y-%m-%d")
    idx_runs = 1
    if os.path.exists(os.path.join(staging_dir, datetime_str + '.txt')):
        while os.path.exists(os.path.join(staging_dir, datetime_str + '_' + str(idx_runs))):
            idx_runs += 1
        staging_path = os.path.join(staging_dir, datetime_str + '_' + str(idx_runs) + '.txt')
    else:
        staging_path = os.path.join(staging_dir, datetime_str + '.txt')

    with open(staging_path, 'w') as f:
        for url in url_list:
            f.write(url + '\n')

    if os.path.exists(os.path.join(output_dir, datetime_str + '.epub')):
        while os.path.exists(os.path.join(output_dir, datetime_str + '_' + str(idx_runs))):
            idx_runs += 1
        output_path = os.path.join(output_dir, datetime_str + '_' + str(idx_runs) + '.epub')
    else:
        output_path = os.path.join(output_dir, datetime_str + '.epub')

    create_epub_from_urls(url_list, output_path)

    # Save changes in Obsidian database
    conn = sqlite3.connect(path_to_db) # will create db if it does not exist
    cur = conn.cursor()
    with conn:
        conn.execute(
            f"""
            UPDATE items SET status = 'converted' WHERE id IN ({','.join('?'*len(id_list))});
            """, id_list
        )    

def main():
    ids, urls = get_urls_to_convert('obsidian.db') # -> list[tuple[str]]

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    inbox_path = config['Inbox path']
    if inbox_path is None:
        print("Inbox path not yet set. ", end="")
        while True:
            inbox_path = input(
            """Please set path:\n> """
            )
            if os.path.exists(inbox_path):
                break
        config['Inbox path'] = inbox_path
    elif not os.path.exists(inbox_path):
        print("Inbox path does not exist. ", end="")
        while not os.path.exists(inbox_path):
            inbox_path = input(
            """Please set valid path:\n> """
        )
        config['Inbox path'] = inbox_path

    if not os.path.exists(os.path.join(inbox_path, 'staging')):
        os.mkdir(os.path.join(inbox_path, 'staging')) 
    staging_path = os.path.join(inbox_path, 'staging')

    stage_and_convert(ids, urls, 'obsidian.db', '../output', staging_path)

if __name__ == '__main__':
    main()