import os
import shutil

import clippings_ingest
import clippings_to_epub

def main():
    if not os.path.exists('config.yaml'):
        shutil.copy('config_sample.yaml', 'config.yaml')
    if not os.path.exists('../output'):
        os.mkdir('../output')
    clippings_ingest.main()
    clippings_to_epub.main()

if __name__ == '__main__':
    main()
