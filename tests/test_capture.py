import random

import numpy as np
from PIL import Image, ImageDraw

from claimdocbench.capture import Quality, capture, forge_text


def _page_with_block() -> tuple[Image.Image, tuple[int, int, int, int]]:
    img = Image.new("RGB", (600, 400), "white")
    box = (220, 150, 160, 60)
    ImageDraw.Draw(img).rectangle([box[0], box[1], box[0] + box[2], box[1] + box[3]], fill="black")
    return img, box


def _dark_fraction(img: Image.Image, box: tuple[int, int, int, int]) -> float:
    x, y, w, h = box
    arr = np.asarray(img.convert("L"))[max(0, y) : y + h, max(0, x) : x + w]
    return float((arr < 100).mean())


def test_box_mapping_follows_the_pixels_for_every_capture_quality() -> None:
    img, box = _page_with_block()
    for quality in (Quality.CLEAN, Quality.SCAN, Quality.PHOTO):
        for seed in range(5):
            cap = capture(img, quality, random.Random(seed))
            mapped = cap.map_box(box)
            # The mapped box is an axis-aligned hull of a slightly rotated/warped block,
            # so most (not all) of it is still dark.
            assert _dark_fraction(cap.image, mapped) > 0.6, (quality, seed)


def test_illegible_capture_destroys_detail() -> None:
    img = Image.new("RGB", (400, 200), "white")
    ImageDraw.Draw(img).rectangle([20, 80, 120, 84], fill="black")  # a thin stroke of "ink"
    out = capture(img, Quality.ILLEGIBLE, random.Random(1)).image
    before = np.asarray(img.convert("L"))[75:90, 15:125]
    after = np.asarray(out.convert("L"))[75:90, 15:125]
    assert np.percentile(before, 1) < 10
    assert np.percentile(after, 1) > 80  # the stroke has washed out


def test_forge_text_replaces_the_value_and_reports_its_new_box() -> None:
    img = Image.new("RGB", (400, 120), (250, 248, 240))
    draw = ImageDraw.Draw(img)
    draw.text((300, 50), "RM45.00", fill="black")
    box = (296, 46, 70, 22)
    forged, new_box = forge_text(img, box, "RM145.00", random.Random(0), align_right=True)
    x, _, w, h = new_box
    assert w > 0 and h > 0
    assert x + w <= 400
    assert forged.tobytes() != img.tobytes()
