default: type

venv:
	python3 -m venv ./venv
	./venv/bin/python3 -m pip install --upgrade pip
	./venv/bin/python3 -m pip install -r requirements.txt
	./venv/bin/python3 -m pip install -r alexandria_api_requirements.txt
	./venv/bin/python3 -m pip install -r dev_requirements.txt

.PHONY: format
format: venv
	./venv/bin/yapf -p -r -i alexandria_api.py command.py hermes.py htypes.py jdb.py lite_oil.py lite.py priv.ex.py priv.py schema.py scrape.py skitter_client.py skitter.py store.py util.py weaver_client.py adapter/ view/

.PHONY: format-diff
format-diff: venv
	./venv/bin/yapf -p -r -d alexandria_api.py command.py hermes.py htypes.py jdb.py lite_oil.py lite.py priv.ex.py priv.py schema.py scrape.py skitter_client.py skitter.py store.py util.py weaver_client.py adapter/ view/

.PHONY: type
type: venv
	./venv/bin/mypy hermes.py alexandria_api.py

.PHONY: lint
lint: type
	./venv/bin/ruff check .

.PHONY: lint-fix
lint-fix: type
	./venv/bin/ruff check . --fix
