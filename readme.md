# any2ebook

Converts links (for now [Obsidian clippings](https://obsidian.md/clipper)) to epub files to be read in ebook readers. Websites are converted to readable text using the [Readability](https://github.com/mozilla/readability) tool through the [ReadabiliPy](https://github.com/alan-turing-institute/ReadabiliPy) Python wrapper.

Obsidian clipping files should have a `source` property in the YAML front matter, which is the clipping URL. It is included in the defualt template.

## Setup
Install using `uv`:
```
uv tool install git+https://github.com/tonilatorrec/any2ebook.git
```

Upgrade:
```
uv tool upgrade any2ebook
```

Remove:
```
uv tool uninstall any2ebook
```

Or with `make`, this also creates the cli and gui executables:
```
make install
make build
```
## Run
```
any2ebook
```

The first time the program runs, it will ask for the following paths:
- **Clippings path**: the path to the top-level folder of the Obsidian clippings stored as .md files. This folder can be set for each template in the Obsidian Web Clipper extension options.
- **Output path**: the path to the folder where the epub files will be stored.  

Each URL is attempted once; if the conversion fails it will be recorded and skipped in future runs. 

