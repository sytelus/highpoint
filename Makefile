PYTHON ?= python3
VENV_DIR ?= .venv

.PHONY: bootstrap install lint fmt test clean-cache clean run

bootstrap: install

install:
	./install.sh

lint:
	$(VENV_DIR)/bin/python -m ruff check src tests scripts main.py
	$(VENV_DIR)/bin/python -m black --check src tests scripts main.py
	$(VENV_DIR)/bin/python -m mypy --strict src tests scripts main.py

fmt:
	$(VENV_DIR)/bin/python -m ruff check --fix src tests scripts main.py
	$(VENV_DIR)/bin/python -m black src tests scripts main.py

test:
	$(VENV_DIR)/bin/python -m pytest --cov=highpoint --cov-report=term-missing

clean-cache:
	rm -rf .mypy_cache .pytest_cache .ruff_cache

clean: clean-cache
	rm -rf $(VENV_DIR) build dist *.egg-info

run:
	$(VENV_DIR)/bin/python -m highpoint.app --help
