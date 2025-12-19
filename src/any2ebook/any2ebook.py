from . import clippings_ingest, clippings_to_epub

def main():
    try:
        clippings_ingest.main()
        clippings_to_epub.main()
        return True
    except Exception as e:
        print("Error:", e)
        return False


if __name__ == "__main__":
    main()
