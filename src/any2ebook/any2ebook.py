from . import clippings_ingest, clippings_to_epub
from .config import Config, ensure_config_path

def run(config: Config):
    try:
        clippings_ingest.run(config)
        clippings_to_epub.run(config)
        return True
    except Exception as e:
        print("Error:", e)
        return False

def main():
    config = Config.load(ensure_config_path())
    run(config)

if __name__ == "__main__":
    main()
