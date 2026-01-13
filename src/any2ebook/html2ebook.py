import datetime
import logging
import os
import sqlite3

import requests
from ebooklib import epub
from readabilipy import simple_json_from_html_string

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def extract_website_content(url):
    """
    Extracts the main content and title from a website using readabilipy.
    Args:
        url (str): The URL of the website to extract.
    Returns:
        dict: A dictionary with 'title' and 'content' keys.
    """
    response = requests.get(url)
    response.encoding = "utf-8"

    response.raise_for_status()
    # print(response.text)
    readable = simple_json_from_html_string(response.text, url)
    return {"title": readable.get("title", ""), "content": readable.get("content", "")}


def html_to_epub(title, html_content, output_filename):
    """
    Converts HTML content to an EPUB file.
    Args:
        title (str): The title of the EPUB book.
        html_content (str): The HTML content to include in the EPUB.
        output_filename (str): The filename for the output EPUB file.
    """
    book = epub.EpubBook()
    book.set_title(title)
    book.add_author("Unknown")

    chapter = epub.EpubHtml(title=title, file_name="chap_1.xhtml", content=html_content)
    book.add_item(chapter)
    book.toc = (epub.Link("chap_1.xhtml", title, "chap1"),)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]

    epub.write_epub(output_filename, book)


def create_epub_from_urls(urls, output_filename, path_to_db: os.PathLike | None = None):
    added_items = 0
    if len(urls) > 0:
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        book = epub.EpubBook()
        book.set_title("Collected Articles -" + date)
        book.add_author("Unknown")
        chapters = []
        toc = []

        if path_to_db:
            try:
                conn = sqlite3.connect(path_to_db)
                cur = conn.cursor()
            except:
                conn = None
                cur = None
        else:
            conn = None
            cur = None

        for idx, url in enumerate(urls):
            try:
                content = extract_website_content(url)
                title = content["title"] or f"Article {idx + 1}"
                html_content = content["content"]
                chapter = epub.EpubHtml(
                    title=title, file_name=f"chap_{idx + 1}.xhtml", content=html_content
                )
                book.add_item(chapter)
                chapters.append(chapter)
                toc.append(epub.Link(f"chap_{idx + 1}.xhtml", title, f"chap{idx + 1}"))
                added_items += 1
                # Set item as converted
                if cur is not None:
                    cur.execute(
                        "UPDATE items SET status = 'converted' WHERE url = (?)", url,
                    )
                logging.info(f"Added {url}.")
            except Exception as e:
                logging.warning(f"Failed to process {url}: {e}")
                # Set item as failed so that it can be processed later
                # if it fails more than three times then we will discard it
                if cur is not None:
                    # get number of attempts
                    res = cur.execute(
                        "SELECT attempts FROM items WHERE url = (?)", url,
                    )
                    attempts = int(res.fetchone())
                    cur.execute(
                        f"""
                        UPDATE items SET 
                            status = 'failed',
                            attempts = {attempts + 1}
                        WHERE url = (?)
                        """, url,
                    )


        book.toc = tuple(toc)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav"] + chapters
        epub.write_epub(output_filename, book)

    if added_items:
        logging.info(f"✔ Created epub in {str(output_filename)} with {added_items} items.")
    else:
        logging.info("No epub created; there are no items to add.")