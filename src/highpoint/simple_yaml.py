"""Minimal YAML loader supporting nested mappings and scalars."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple


def load_yaml(path: Path | str) -> Dict[str, Any]:
    path_obj = Path(path)
    text = path_obj.read_text(encoding="utf-8")
    lines = [
        line.rstrip("\n")
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    data, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise ValueError(f"Failed to parse YAML at {path}")
    return data


def _parse_block(lines: list[str], start: int, indent: int) -> Tuple[Dict[str, Any], int]:
    result: Dict[str, Any] = {}
    index = start
    while index < len(lines):
        line = lines[index]
        stripped = line.lstrip(" ")
        current_indent = len(line) - len(stripped)
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"Unexpected indentation: '{line}'")
        if ":" not in stripped:
            raise ValueError(f"Expected key-value pair: '{line}'")
        key, _, rest = stripped.partition(":")
        key = key.strip()
        remainder = rest.strip()
        index += 1
        if remainder == "":
            child, index = _parse_block(lines, index, indent + 2)
            result[key] = child
        else:
            result[key] = _parse_scalar(remainder)
    return result, index


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if lowered in {"null", "none", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        if "." in value or "e" in value or "E" in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
