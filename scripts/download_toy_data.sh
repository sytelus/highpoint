#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${SCRIPT_DIR%/scripts}"
python "$ROOT/scripts/fetch_datasets.py" --region toy "$@"
