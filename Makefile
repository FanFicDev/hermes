default: type lint format

venv:
	python3 -m venv ./venv
	./venv/bin/python3 -m pip install --upgrade pip
	./venv/bin/python3 -m pip install -r requirements.txt
	./venv/bin/python3 -m pip install -r alexandria_api_requirements.txt
	./venv/bin/python3 -m pip install -r dev_requirements.txt

.PHONY: format
format: venv
	./venv/bin/ruff format .

.PHONY: format-diff
format-diff: venv
	./venv/bin/ruff format . --diff

.PHONY: type
type: venv
	./venv/bin/mypy hermes.py alexandria_api.py

.PHONY: lint
lint: type
	./venv/bin/ruff check .

.PHONY: lint-fix
lint-fix: type
	./venv/bin/ruff check . --fix
