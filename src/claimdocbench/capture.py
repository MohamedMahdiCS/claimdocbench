"""Capture simulation and pixel-level tampering.

Documents are rendered clean, then optionally *forged* (a printed value painted over with a new
one, as a fraudster would do in an image editor), then *captured* as a flatbed scan, a phone
photo, or an unreadable copy. Every geometric change is a homography, so gold field boxes are
moved with exactly the same transform as the pixels.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

Box = tuple[int, int, int, int]  # x, y, width, height


class Quality(StrEnum):
    CLEAN = "clean"  # born-digital
    SCAN = "scan"
    PHOTO = "photo"
    ILLEGIBLE = "illegible"


QUALITY_WEIGHTS = {Quality.CLEAN: 0.4, Quality.SCAN: 0.35, Quality.PHOTO: 0.25}

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


@dataclass(frozen=True)
class Captured:
    image: Image.Image
    homography: np.ndarray  # 3x3, maps clean-image points to captured-image points

    def map_box(self, box: Box) -> Box:
        x, y, w, h = box
        pts = np.array([[x, y, 1], [x + w, y, 1], [x, y + h, 1], [x + w, y + h, 1]], float).T
        out = self.homography @ pts
        out = out[:2] / out[2]
        x0, y0 = out.min(axis=1)
        x1, y1 = out.max(axis=1)
        return round(x0), round(y0), round(x1 - x0), round(y1 - y0)


def _homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """3x3 matrix H with dst ~ H @ src for four point pairs."""
    rows, rhs = [], []
    for (x, y), (u, v) in zip(src, dst, strict=True):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        rhs += [u, v]
    coeffs = np.linalg.solve(np.array(rows, float), np.array(rhs, float))
    return np.append(coeffs, 1.0).reshape(3, 3)


def _warp(
    img: Image.Image, h: np.ndarray, size: tuple[int, int], fill: tuple[int, int, int]
) -> Image.Image:
    inv = np.linalg.inv(h)
    inv = inv / inv[2, 2]
    data = tuple(float(v) for v in inv.flatten()[:8])
    return img.transform(
        size, Image.Transform.PERSPECTIVE, data, resample=Image.Resampling.BICUBIC, fillcolor=fill
    )


def _noise(img: Image.Image, rng: random.Random, sigma: float) -> Image.Image:
    gen = np.random.default_rng(rng.getrandbits(32))
    arr = np.asarray(img, dtype=np.float64) + gen.normal(0, sigma, (img.height, img.width, 3))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _lighting(img: Image.Image, rng: random.Random) -> Image.Image:
    w, h = img.size
    angle = rng.uniform(0, 2 * np.pi)
    xs, ys = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
    ramp = (np.cos(angle) * xs + np.sin(angle) * ys + 1) / 2
    gain = rng.uniform(0.70, 0.85) + ramp * rng.uniform(0.15, 0.30)
    arr = np.asarray(img, dtype=np.float32) * gain[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def capture(img: Image.Image, quality: Quality, rng: random.Random) -> Captured:
    img = img.convert("RGB")
    w, h = img.size
    corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)

    if quality is Quality.CLEAN:
        return Captured(img, np.eye(3))

    if quality is Quality.ILLEGIBLE:
        small = img.resize((max(1, w // 4), max(1, h // 4)), Image.Resampling.BILINEAR)
        blurred = small.resize((w, h), Image.Resampling.BILINEAR).filter(
            ImageFilter.GaussianBlur(rng.uniform(4, 6))
        )
        faded = Image.blend(blurred, Image.new("RGB", (w, h), (225, 222, 214)), 0.55)
        return Captured(_noise(faded, rng, 10), np.eye(3))

    if quality is Quality.SCAN:
        theta = np.radians(rng.uniform(-1.5, 1.5))
        c, s = np.cos(theta), np.sin(theta)
        rot = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        moved = (rot @ np.c_[corners, np.ones(4)].T)[:2].T
        off = -moved.min(axis=0) + 10
        size = (int(np.ceil(np.ptp(moved[:, 0]) + 20)), int(np.ceil(np.ptp(moved[:, 1]) + 20)))
        hmat = _homography(corners, moved + off)
        paper = (rng.randint(236, 248), rng.randint(234, 245), rng.randint(226, 238))
        out = _warp(img, hmat, size, paper)
        tint = Image.new("RGB", out.size, paper)
        out = Image.blend(out, tint, 0.08).filter(ImageFilter.GaussianBlur(0.6))
        return Captured(_noise(out, rng, 4), hmat)

    # PHOTO: perspective on a desk, uneven light, then downscaled like a phone upload.
    margin_x, margin_y = int(w * rng.uniform(0.06, 0.14)), int(h * rng.uniform(0.06, 0.14))
    size = (w + 2 * margin_x, h + 2 * margin_y)
    jitter = 0.05
    shake = np.array(
        [[rng.uniform(-jitter, jitter) * w, rng.uniform(-jitter, jitter) * h] for _ in range(4)]
    )
    dst = corners + np.array([margin_x, margin_y], float) + shake
    hmat = _homography(corners, dst)
    desk = rng.choice([(118, 92, 66), (92, 96, 104), (180, 172, 160), (60, 60, 64)])
    out = _warp(img, hmat, size, desk)
    out = _lighting(out, rng).filter(ImageFilter.GaussianBlur(rng.uniform(0.6, 1.2)))
    out = _noise(out, rng, 6)
    scale = min(1.0, 1600 / max(out.size))
    if scale < 1.0:
        out = out.resize(
            (round(out.width * scale), round(out.height * scale)), Image.Resampling.LANCZOS
        )
        hmat = np.diag([scale, scale, 1.0]) @ hmat
    return Captured(out, hmat)


def save(captured: Captured, path_stem: Path, quality: Quality, rng: random.Random) -> Path:
    if quality is Quality.CLEAN:
        path = path_stem.with_suffix(".png")
        captured.image.save(path, optimize=True)
    else:
        path = path_stem.with_suffix(".jpg")
        captured.image.save(path, quality=rng.randint(72, 90))
    return path


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def forge_text(
    img: Image.Image, box: Box, text: str, rng: random.Random, align_right: bool
) -> tuple[Image.Image, Box]:
    """Paint over a printed value and write a new one, leaving realistic editing traces."""
    img = img.convert("RGB").copy()
    x, y, w, h = box
    arr = np.asarray(img)
    pad = 6
    regions = []
    if y - pad >= 0:
        regions.append(arr[y - pad : y, max(0, x - pad) : x + w + pad])
    if y + h + pad <= arr.shape[0]:
        regions.append(arr[y + h : y + h + pad, max(0, x - pad) : x + w + pad])
    ring = np.concatenate([r.reshape(-1, 3) for r in regions]) if regions else np.empty((0, 3))
    bg = tuple(int(v) for v in np.median(ring, axis=0)) if len(ring) else (255, 255, 255)
    shade = rng.randint(-5, 5)
    patch = tuple(max(0, min(255, c + shade)) for c in bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([x - 2, y - 1, x + w + 2, y + h + 1], fill=patch)
    font = _font(max(10, int(h * rng.uniform(0.72, 0.86))))
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    tw, th = right - left, bottom - top
    tx = (x + w - tw) if align_right else x
    tx += rng.randint(-2, 3)
    ty = y + (h - th) // 2 - top + rng.randint(-2, 2)
    ink = (rng.randint(20, 60), rng.randint(20, 60), rng.randint(20, 60))
    draw.text((tx, ty), text, font=font, fill=ink)
    return img, (int(tx + left), int(ty + top), int(tw), int(th))
