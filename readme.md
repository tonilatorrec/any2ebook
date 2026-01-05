# any2ebook

Converts [Obsidian clippings](https://obsidian.md/clipper) to epub files to be read in ebook readers

Obsidian clipping files should have the following properties in the YAML front matter, which are included in the default template:
- `title`
- `source` which should be the clipping URL
- `published` 
- `created`

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
- **Clippings path**: the path to the parent folder where each Obsidian clipping is stored as an .md file. This folder can be set for each template in the Obsidian Web Clipper extension options.
- **Output path**: the path to the folder where the epub files will be stored.  
