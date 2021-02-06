all: deps lint test

deps:
	@python3 -m pip install --upgrade pip && pip3 install -r requirements-dev.txt

black:
	@black --line-length 120 aio_request tests

isort:
	@isort --line_length 120 --use_parentheses --combine_as_imports --include_trailing_comma aio_request tests

mypy:
	@mypy --strict --ignore-missing-imports aio_request

flake8:
	@flake8 --max-line-length 120 --ignore C901,C812,E203 --extend-ignore W503 aio_request tests

lint: black isort flake8 mypy

test:
	@python3 -m pytest -vv --rootdir tests .
