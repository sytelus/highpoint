from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

SRC = ROOT / "src"
SRC_STR = str(SRC)
if SRC_STR not in sys.path:
    sys.path.insert(0, SRC_STR)
