all: deps lint test

deps:
	@python3 -m pip install --upgrade pip && pip3 install -r requirements-dev.txt

black:
	@black --line-length 120 aio_request tests

isort:
	@isort --line-length 120 --use-parentheses --multi-line 3 --combine-as --trailing-comma aio_request tests

mypy:
	@mypy --strict --ignore-missing-imports aio_request

flake8:
	@flake8 --max-line-length 120 --ignore C901,C812,E203 --extend-ignore W503 aio_request tests

lint: black isort flake8 mypy

test:
	@python3 -m pytest -vv --rootdir tests .

pyenv:
	echo aio-request > .python-version && pyenv install -s 3.10.0 && pyenv virtualenv -f 3.10.0 aio-request
