#!/usr/bin/env bash

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

echo "[highpoint] Using Python interpreter: ${PYTHON_BIN}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Error: ${PYTHON_BIN} not found on PATH." >&2
  exit 1
fi

if [ ! -d "${VENV_DIR}" ]; then
  echo "[highpoint] Creating virtual environment at ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

echo "[highpoint] Upgrading pip, wheel, and setuptools"
python -m pip install --upgrade pip setuptools wheel

echo "[highpoint] Installing project (editable) with dev extras"
python -m pip install -e ".[dev]"

echo "[highpoint] Installation complete. Activate the environment with:"
echo "  source ${VENV_DIR}/bin/activate"
