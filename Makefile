.DEFAULT_GOAL := all

.PHONY: .pre-commit
.pre-commit: .uv
	@uv run pre-commit -V || uv pip install pre-commit

.PHONY: .uv  # Ensure uv is installed
.uv:
	@uv -V || echo 'install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: all  # Perform checks for continuous integration
all: lint typecheck test

.PHONY: clean  # Clear cache and build artifacts
clean:
	uv run pre-commit uninstall
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]'`
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf dist
	rm -rf *.egg-info

.PHONY: help  # Display this message
help:
	@grep -E \
		'^.PHONY: .*?# .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ".PHONY: |# "}; {printf "\033[1;36m%-19s\033[0m %s\n", $$2, $$3}'

.PHONY: install  # Install the library, dependencies, and hooks for local development
install: .uv
	uv sync --frozen
	uv run pre-commit install --install-hooks

.PHONY: format  # Format files
format: .uv
	uv run ruff check --fix
	uv run ruff format
	uv run taplo format
	uv run mbake format Makefile
	uv run python scripts/format_json.py $$(find . -name '*.json' -not -path '*/.venv/*' -not -path '*/*_cache/*')
	uv run python scripts/format_yaml.py $$(find . -name '*.yaml' -o -name '*.yml' | grep -v '.venv' | grep -v '_cache')

.PHONY: lint  # Lint source code
lint: .uv
	uv run ruff check
	uv run ruff format --check
	uv run taplo format --check
	uv run mbake format --check Makefile
	uv run typos

.PHONY: test  # Test suite (use ARGS="" to filter)
test: .uv
	uv run pytest $(ARGS)

.PHONY: typecheck  # Type check source code
typecheck: .uv
	uv run ty check