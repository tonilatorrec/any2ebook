import os

from . import clippings_ingest
from . import clippings_to_epub

def main():
    clippings_ingest.main()
    clippings_to_epub.main()

if __name__ == '__main__':
    main()
