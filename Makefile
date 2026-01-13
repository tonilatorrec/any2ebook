install:
	uv tool install git+https://github.com/tonilatorrec/any2ebook.git

.PHONY: update-deps
update-deps:
	uv sync --frozen

build:
	uv run pyinstaller -F -n any2ebook_cli src/any2ebook/any2ebook.py
	uv run pyinstaller -F -w -n any2ebook --paths src --collect-data any2ebook=*.yaml run_gui.py          

.PHONY: test
test:
	uv run pytest

.PHONY: lint
lint: 
	uv run ruff check ./src ./tests --fix
	uv run ruff format ./src ./tests

.PHONY: upgrade
upgrade:
	uv tool upgrade any2ebook