#!/usr/bin/env bash

set -euo pipefail

: "${OUT_DIR:?Set OUT_DIR to the base output directory first.}"

python main.py --location "Issaquah, WA" --search-radius 10 --results 5 \
  --render-png "$OUT_DIR/highpoint/issaquah.png"
