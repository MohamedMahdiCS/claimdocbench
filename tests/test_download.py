import io
import zipfile
from pathlib import Path
from typing import Any

import pytest

from claimdocbench import download as dl
from claimdocbench.dataset import tree_hash


def _zip(entries: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in entries.items():
            zf.writestr(name, text)
    return buf.getvalue()


def _serve(monkeypatch: pytest.MonkeyPatch, payload: bytes, expected: dict[str, Any]) -> None:
    monkeypatch.setattr("urllib.request.urlopen", lambda url, timeout=0: io.BytesIO(payload))
    monkeypatch.setattr(dl, "frozen_splits", lambda: expected)


def test_download_verifies_the_frozen_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "src" / "dev"
    src.mkdir(parents=True)
    (src / "index.json").write_text("{}")
    digest, _ = tree_hash(src)
    _serve(monkeypatch, _zip({"dev/index.json": "{}"}), {"dev": {"sha256": digest}})
    assert (dl.download("dev", tmp_path / "out") / "index.json").exists()


def test_tampered_download_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, _zip({"dev/index.json": "{changed}"}), {"dev": {"sha256": "0" * 64}})
    with pytest.raises(ValueError, match="hash mismatch"):
        dl.download("dev", tmp_path / "out")


def test_zip_cannot_write_outside_the_target(tmp_path: Path) -> None:
    archive = tmp_path / "evil.zip"
    archive.write_bytes(_zip({"../escape.txt": "x"}))
    with pytest.raises(ValueError, match="unsafe path"):
        dl._safe_extract(archive, tmp_path / "x")
