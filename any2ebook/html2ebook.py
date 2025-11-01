import requests
from readabilipy import simple_json_from_html_string
from ebooklib import epub

def extract_website_content(url):
    """
    Extracts the main content and title from a website using readabilipy.
    Args:
        url (str): The URL of the website to extract.
    Returns:
        dict: A dictionary with 'title' and 'content' keys.
    """
    response = requests.get(url)
    response.encoding = 'utf-8'
    
    response.raise_for_status()
    print(response.text)
    readable = simple_json_from_html_string(response.text, url)
    return {
        'title': readable.get('title', ''),
        'content': readable.get('content', '')
    }

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
    book.add_author('Unknown')

    chapter = epub.EpubHtml(title=title, file_name='chap_1.xhtml', content=html_content)
    book.add_item(chapter)
    book.toc = (epub.Link('chap_1.xhtml', title, 'chap1'),)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav', chapter]

    epub.write_epub(output_filename, book)

def create_epub_from_urls(urls, output_filename):
    book = epub.EpubBook()
    book.set_title('Collected Articles')
    book.add_author('Unknown')
    chapters = []
    toc = []
    for idx, url in enumerate(urls):
        try:
            content = extract_website_content(url)
            title = content['title'] or f'Article {idx+1}'
            html_content = content['content']
            chapter = epub.EpubHtml(title=title, file_name=f'chap_{idx+1}.xhtml', content=html_content)
            book.add_item(chapter)
            chapters.append(chapter)
            toc.append(epub.Link(f'chap_{idx+1}.xhtml', title, f'chap{idx+1}'))
        except Exception as e:
            print(f"Failed to process {url}: {e}")
    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapters
    epub.write_epub(output_filename, book)

