all: deps lint test

deps:
	@python3 -m pip install --upgrade pip && pip3 install -r requirements-dev.txt

black:
	@black --line-length 120 aio_request tests example

isort:
	@isort --line-length 120 --use-parentheses --multi-line 3 --combine-as --trailing-comma aio_request tests example

pyright:
	pyright

flake8:
	@flake8 --max-line-length 120 --ignore C901,C812,E203,E704 --extend-ignore W503 aio_request tests example

lint: black isort flake8 pyright

test:
	@python3 -m pytest -vv --rootdir tests .

pyenv:
	echo aio-request > .python-version && pyenv install -s 3.13 && pyenv virtualenv -f 3.13 aio-request

pyenv-delete:
	pyenv virtualenv-delete -f aio-request
