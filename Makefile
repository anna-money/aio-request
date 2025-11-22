all: deps lint test

uv:
	@which uv >/dev/null 2>&1 || { \
		echo "❌ uv is not installed"; \
		exit 1;\
	}

deps: uv
	@uv pip install -e ".[dev]"

format:
	@ruff format aio_request tests example
	@ruff check --fix aio_request tests example

pyright:
	@pyright

lint: format pyright

test:
	@python3 -m pytest -vv --rootdir tests .

pyenv:
	echo aio-request > .python-version && pyenv install -s 3.13 && pyenv virtualenv -f 3.13 aio-request

pyenv-delete:
	pyenv virtualenv-delete -f aio-request
