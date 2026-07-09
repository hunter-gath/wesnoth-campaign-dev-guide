#!/usr/bin/env python3
"""Regenerate the simple placeholder PNGs used by the Hunter Gath tutorial."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]

def make(path, size, label):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, (49, 73, 50))
    draw = ImageDraw.Draw(img)
    w, h = size
    draw.rectangle([10, 10, w - 11, h - 11], outline=(230, 220, 170), width=max(2, w // 80))
    draw.line([15, h - 20, w - 15, 20], fill=(180, 140, 80), width=max(2, w // 90))
    draw.text((20, h // 2 - 10), label, fill=(245, 235, 200))
    img.save(path)

make(ROOT / "images/misc/hunter-gath-icon.png", (72, 72), "HG")
make(ROOT / "images/portraits/hunter-gath.png", (350, 350), "Hunter Gath")
make(ROOT / "images/story/hunter-gath-forest.png", (1024, 768), "Northern Timberline")
