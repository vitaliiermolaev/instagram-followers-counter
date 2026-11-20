"""Frames for src/animations/hearts.anim: two hearts in the bottom-right corner.

The sprites and the background (src/images/bg.png) come from the Figma design. The hearts rise
from below the display to their places in the design (big one at x 62, y 7; small one at x 55,
y 11), stay there, fade into the background and come again. They never go above row 7, so they
don't touch the username (rows 2-6), which may scroll across the whole width.

Builds hearts_17x16.zip (PNG frames + meta.json) for scripts/seq2anim.py from the BUSY Bar firmware:

    python3 tools/hearts.py build/
    python3 <firmware>/scripts/seq2anim.py -o src/animations/hearts.anim build/hearts_17x16.zip

Needs Pillow (the firmware toolchain Python has it).
"""

import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
X0, Y0 = 54, 0  # where main.js places the animation on the front display
W, H = 17, 16
FPS = 6
RISE = 9  # frames for the big heart to rise from below the display to y 7
HOLD = 12  # 2 s in place
FADE = (0.75, 0.5, 0.25)  # fade out in place
PAUSE = 5
LOOP = RISE + HOLD + len(FADE) + 1 + PAUSE  # 5 s

_ = None
BIG = [
    ["751568", "C32488", "9F1D79", _, "BC2385", "C7248A", "731467"],
    ["E42B96", "FF30A1", "FF30A1", "F32D9D", "FF30A1", "FF30A1", "D2268F"],
    ["F32D9D", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "D2268F"],
    ["AA1F7E", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "85176E"],
    [_, "C92C8E", "FF50B0", "FF51B1", "FE3DA8", "A21D7A", _],
    [_, _, "CE5CA6", "FEA7D8", "AB3D8C", _, _],
]
SMALL = [
    [_, "73146C", _, "7A156F", _],
    ["881775", "FF30AC", "EB2CA2", "FF30AB", "BA228C"],
    ["7A156D", "FE2EAB", "FF30AC", "FF30AC", "9F1D7F"],
    [_, "9F2584", "FD70C6", "C03296", _],
    [_, _, "802B7A", _, _],
]
HEARTS = [  # (sprite, x and y in the design)
    (BIG, 62, 7),
    (SMALL, 55, 11),
]


def place(index, rest):
    """Top row and brightness of a heart at this frame."""
    if index < RISE:
        # 1 px per frame; a heart with a shorter way starts later, so both arrive together
        start = RISE - (16 - rest)
        return min(16, 16 - (index + 1 - start)), 1.0
    index -= RISE
    if index < HOLD:
        return rest, 1.0
    index -= HOLD
    if index < len(FADE):
        return rest, FADE[index]
    return rest, 0.0


def frame(index, background):
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for sprite, left, rest in HEARTS:
        top, k = place(index, rest)
        if k == 0:
            continue
        for dy, row in enumerate(sprite):
            for dx, colour in enumerate(row):
                x, y = left + dx, top + dy
                if colour is None or not (0 <= y < 16):
                    continue
                heart = [int(colour[i : i + 2], 16) for i in (0, 2, 4)]
                under = background.getpixel((x, y))[:3]
                mixed = tuple(round(b + (h - b) * k) for h, b in zip(heart, under))
                image.putpixel((x - X0, y - Y0), mixed + (255,))
    return image


def main(out_dir):
    background = Image.open(ROOT / "src/images/bg.png").convert("RGB")
    name = f"hearts_{W}x{H}"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta = {"fps": FPS, "color_mode": "argb8888", "sections": [{"name": "whole", "start": 0, "end": LOOP - 1}]}
    with zipfile.ZipFile(out / f"{name}.zip", "w") as archive:
        archive.writestr(f"{name}/meta.json", json.dumps(meta, indent=2))
        for index in range(LOOP):
            data = BytesIO()
            frame(index, background).save(data, "PNG")
            archive.writestr(f"{name}/frame_{index}.png", data.getvalue())


if __name__ == "__main__":
    main(sys.argv[1])
