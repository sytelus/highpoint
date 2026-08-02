from __future__ import annotations

from pathlib import Path

import pytest
from scripts import fetch_datasets


def test_download_success__publishes_complete_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "nested" / "asset.bin"
    destination.parent.mkdir(parents=True)
    destination.touch()

    def retrieve(_url: str, filename: str | Path) -> tuple[str, None]:
        path = Path(filename)
        path.write_bytes(b"complete")
        return str(path), None

    monkeypatch.setattr(fetch_datasets, "urlretrieve", retrieve)

    fetch_datasets.download("https://example.invalid/asset", destination, dry_run=False)

    assert destination.read_bytes() == b"complete"
    assert not destination.with_name("asset.bin.part").exists()


def test_download_failure__removes_partial_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "asset.bin"

    def retrieve(_url: str, filename: str | Path) -> tuple[str, None]:
        Path(filename).write_bytes(b"partial")
        raise OSError("connection lost")

    monkeypatch.setattr(fetch_datasets, "urlretrieve", retrieve)

    with pytest.raises(RuntimeError, match="Failed to download"):
        fetch_datasets.download("https://example.invalid/asset", destination, dry_run=False)

    assert not destination.exists()
    assert not destination.with_name("asset.bin.part").exists()


def test_download_dry_run__does_not_create_directories(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "asset.bin"

    fetch_datasets.download("https://example.invalid/asset", destination, dry_run=True)

    assert not destination.parent.exists()
