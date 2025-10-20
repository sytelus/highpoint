PYTHON ?= python3
VENV_DIR ?= .venv

.PHONY: bootstrap lint test run fmt typeclean clean

bootstrap:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -r requirements.txt
	$(VENV_DIR)/bin/pip install -e .[dev]

lint:
	$(VENV_DIR)/bin/ruff check src tests
	$(VENV_DIR)/bin/black --check src tests
	$(VENV_DIR)/bin/mypy src tests

fmt:
	$(VENV_DIR)/bin/ruff check --fix src tests
	$(VENV_DIR)/bin/black src tests

test:
	$(VENV_DIR)/bin/pytest --cov=src/highpoint --cov-report=term-missing

typeclean:
	rm -rf .mypy_cache/. pytest_cache/. .ruff_cache/

clean: typeclean
	rm -rf $(VENV_DIR) build dist *.egg-info

run:
	$(VENV_DIR)/bin/python -m highpoint.app --help
