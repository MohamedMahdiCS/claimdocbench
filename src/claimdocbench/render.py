"""Renders document specs to PNG with headless Chromium and records field boxes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

from jinja2 import (
    BaseLoader,
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    StrictUndefined,
    select_autoescape,
)
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from claimdocbench.documents import DocSpec

DEVICE_SCALE = 2

_FIELD_JS = """
(root) => {
  const r0 = root.getBoundingClientRect();
  return Array.from(root.querySelectorAll('[data-field]')).map(el => {
    const r = el.getBoundingClientRect();
    return {name: el.dataset.field, text: el.innerText,
            box: [r.left - r0.left, r.top - r0.top, r.width, r.height]};
  });
}
"""


@dataclass(frozen=True)
class RenderedField:
    name: str
    printed: str
    box: tuple[int, int, int, int]  # x, y, width, height in image pixels


@dataclass(frozen=True)
class RenderedDoc:
    path: Path
    width: int
    height: int
    fields: tuple[RenderedField, ...]


class Renderer:
    """Reuses one browser page for every document. Use as a context manager."""

    def __init__(self) -> None:
        loaders: list[BaseLoader] = [PackageLoader("claimdocbench", "templates")]
        private = Path(os.environ.get("CLAIMDOCBENCH_PRIVATE_TEMPLATES", "private/templates"))
        if private.is_dir():  # held-out layouts, kept out of the public repo until the reveal
            loaders.append(FileSystemLoader(str(private)))
        self.env = Environment(
            loader=ChoiceLoader(loaders),
            autoescape=select_autoescape(["html", "j2"]),
            undefined=StrictUndefined,
        )
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    def __enter__(self) -> Renderer:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._page = self._browser.new_page(device_scale_factor=DEVICE_SCALE)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def html(self, spec: DocSpec) -> str:
        return self.env.get_template(f"{spec.template}.html.j2").render(**spec.context)

    def render(self, spec: DocSpec, out: Path) -> RenderedDoc:
        if self._page is None:
            raise RuntimeError("Renderer must be used as a context manager")
        page = self._page
        page.set_content(self.html(spec), wait_until="load")
        doc = page.locator(".doc")
        doc.screenshot(path=str(out))
        raw: list[dict[str, Any]] = doc.evaluate(_FIELD_JS)
        size = doc.bounding_box()
        assert size is not None
        fields = tuple(
            RenderedField(
                name=f["name"],
                printed=f["text"],
                box=(
                    round(f["box"][0] * DEVICE_SCALE),
                    round(f["box"][1] * DEVICE_SCALE),
                    round(f["box"][2] * DEVICE_SCALE),
                    round(f["box"][3] * DEVICE_SCALE),
                ),
            )
            for f in raw
        )
        return RenderedDoc(
            out, round(size["width"] * DEVICE_SCALE), round(size["height"] * DEVICE_SCALE), fields
        )
