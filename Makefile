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

.PHONY: demo
demo:
	@set -eu; \
	DEMO_ROOT="$${DEMO_ROOT:-$$(mktemp -d /tmp/any2ebook-demo-XXXXXX)}"; \
	APP_HOME="$$DEMO_ROOT/apphome"; \
	DATA_HOME="$$DEMO_ROOT/data"; \
	CLIPPINGS_DIR="$$DEMO_ROOT/clippings/demo"; \
	OUTPUT_DIR="$$DEMO_ROOT/output"; \
	mkdir -p "$$APP_HOME/config" "$$CLIPPINGS_DIR" "$$OUTPUT_DIR"; \
	printf '%s\n' \
		'---' \
		'title: "Demo clipping"' \
		'source: "https://example.com"' \
		'published: "2026-02-08T00:00:00+00:00"' \
		'created: "2026-02-08T00:00:00+00:00"' \
		'---' \
		'' \
		'Demo body' > "$$CLIPPINGS_DIR/test.md"; \
	printf '%s\n' \
		"clippings_path: \"$$DEMO_ROOT/clippings\"" \
		"input_path:" \
		"output_path: \"$$OUTPUT_DIR\"" > "$$APP_HOME/config/config.yaml"; \
	ANY2EBOOK_HOME="$$APP_HOME" XDG_DATA_HOME="$$DATA_HOME" uv run any2ebook; \
	echo ""; \
	echo "Demo root: $$DEMO_ROOT"; \
	echo "Output directory: $$OUTPUT_DIR"; \
	echo "Generated files:"; \
	ls -lh "$$OUTPUT_DIR"
