all: deps lint test

uv:
	@which uv >/dev/null 2>&1 || { \
		echo "❌ uv is not installed"; \
		exit 1;\
	}

deps: uv
	@uv sync --all-extras

format:
	@uv run ruff format aio_request tests example
	@uv run ruff check --fix aio_request tests example

pyright:
	@uv run pyright

lint: format pyright

test:
	@uv run pytest -vv --rootdir tests .
