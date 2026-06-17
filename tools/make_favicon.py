#!/usr/bin/env python3
"""
Generate PNG app icons from the brand mark (gold diamond on dark).

Writes:
  assets/favicon.png        (32x32  — classic favicon fallback)
  assets/icon-512.png       (512x512 — PWA / apple-touch-icon)

Pure standard library; reuses the rasteriser in make_og_image.py.
Run:  python tools/make_favicon.py
"""

from pathlib import Path

from make_og_image import Canvas, diamond

ROOT = Path(__file__).resolve().parent.parent
GOLD = (212, 160, 23)
DARK = (26, 25, 20)


def make_icon(size, path):
    cv = Canvas(size, size)
    cv.set_bg_gradient(DARK, (38, 36, 30))
    c = size / 2
    cv.fill(diamond(c, c, size * 0.34), GOLD, 1.0)          # solid gold diamond
    cv.fill(diamond(c, c, size * 0.13), DARK, 1.0)          # centre notch (echoes ◈)
    cv.write_png(path)
    print(f"Wrote {path} ({size}x{size})")


def main():
    (ROOT / "assets").mkdir(parents=True, exist_ok=True)
    make_icon(32, ROOT / "assets" / "favicon.png")
    make_icon(512, ROOT / "assets" / "icon-512.png")


if __name__ == "__main__":
    main()
