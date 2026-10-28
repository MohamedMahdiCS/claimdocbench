"""Downloads a released split and checks it against the frozen fingerprint."""

from __future__ import annotations

import json
import shutil
import tempfile
import urllib.request
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import Any

from claimdocbench.dataset import tree_hash

RELEASE_URL = "https://github.com/MohamedMahdiCS/claimdocbench/releases/download/{tag}/{name}"
DEFAULT_TAG = "v0.1.0"


def frozen_splits() -> dict[str, Any]:
    packaged = files("claimdocbench").joinpath("data/splits.json")
    if packaged.is_file():
        raw = packaged.read_text(encoding="utf-8")
    else:  # editable install: read the repo copy
        raw = (Path(__file__).resolve().parents[2] / "splits" / "manifest.json").read_text("utf-8")
    splits: dict[str, Any] = json.loads(raw)["splits"]
    return splits


def _safe_extract(archive: Path, dest: Path) -> None:
    root = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            target = (dest / member.filename).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"unsafe path in archive: {member.filename}")
        zf.extractall(dest)


def download(split: str, out: Path, tag: str = DEFAULT_TAG) -> Path:
    expected = frozen_splits()[split]
    name = f"claimdocbench-{tag.rsplit('.', 1)[0]}-{split}.zip"
    target = out / split
    if target.exists():
        raise FileExistsError(f"{target} already exists; remove it to download again")
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / name
        with (
            urllib.request.urlopen(RELEASE_URL.format(tag=tag, name=name), timeout=600) as r,
            archive.open("wb") as fh,
        ):
            shutil.copyfileobj(r, fh)
        _safe_extract(archive, Path(tmp) / "x")
        # The held-out archive is the whole private folder (secret layouts + split), which is
        # what its fingerprint was committed over before any system was tuned.
        root = Path(tmp) / "x" / ("private" if split == "heldout" else split)
        digest, count = tree_hash(root)
        if digest != expected["sha256"]:
            raise ValueError(f"{split}: hash mismatch ({count} files); download may be corrupt")
        shutil.move(str(root / split if split == "heldout" else root), target)
    return target
