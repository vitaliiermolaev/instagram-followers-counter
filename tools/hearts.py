"""Frames for src/animations/hearts.anim: two hearts floating up in the bottom-right corner.

The sprites and the background (src/images/bg.png) come from the Figma design. The hearts pass
through their places in the design (big one at x 62, y 7; small one at x 55, y 11) and fade into
the background near the top. The username is drawn above them (z_index in main.js), so a long
scrolling username stays readable.

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
LOOP = 24  # 4 s: a pair of hearts, then a short pause

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
HEARTS = [  # (sprite, x on the display, delay in frames)
    (BIG, 62, 0),
    (SMALL, 55, 4),  # 4 frames behind: when the big heart is at y 7, the small one is at y 11
]


def fade(top):
    """1 below the username line, then down to 0 over four rows."""
    return {5: 0.8, 4: 0.6, 3: 0.4, 2: 0.2}.get(top, 1.0 if top >= 6 else 0.0)


def frame(index, background):
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for sprite, left, delay in HEARTS:
        age = (index - delay) % LOOP
        top = 16 - age  # starts just below the display, rises 1 px per frame
        k = fade(top)
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
