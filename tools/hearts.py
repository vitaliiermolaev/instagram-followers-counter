"""Frames for src/animations/hearts.anim: hearts floating up in the bottom-right corner.

Builds hearts_13x9.zip (PNG frames + meta.json) for scripts/seq2anim.py from the BUSY Bar firmware:

    python3 tools/hearts.py build/
    python3 <firmware>/scripts/seq2anim.py -o src/animations/hearts.anim build/hearts_13x9.zip

Needs Pillow (the firmware toolchain Python has it).
"""

import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image

W, H = 13, 9
FPS = 6
PERIOD = 9  # frames between two hearts
HEARTS = [  # (sprite, colour, x of the left edge)
    ("big", "pink", 5),
    ("small", "red", 1),
    ("big", "red", 2),
    ("small", "pink", 8),
]
LOOP = PERIOD * len(HEARTS)

SPRITES = {
    # b: base, h: highlight (top right), s: shadow (bottom left)
    "big": ["bb.hh", "sbbbh", ".sbb.", "..s.."],
    "small": ["b.h", "sbb", ".s."],
}
COLOURS = {
    "pink": {"b": (255, 95, 162), "h": (255, 170, 205), "s": (194, 40, 110)},
    "red": {"b": (255, 48, 64), "h": (255, 140, 150), "s": (176, 24, 40)},
}
SWAY = [0, 0, 1, 1, 1, 0, 0, -1, -1, -1]  # 1 px left and right, slowly


def brightness(top):
    """Hearts fade out near the top of the frame, before they reach the username line."""
    return {3: 0.75, 2: 0.5, 1: 0.3, 0: 0.15}.get(top, 1.0 if top > 3 else 0.0)


def frame(index):
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pixels = image.load()
    for number, (sprite, colour, left) in enumerate(HEARTS):
        rows = SPRITES[sprite]
        age = (index - number * PERIOD) % LOOP
        top = H - age  # starts just below the frame, rises 1 px per frame
        if top + len(rows) <= 0 or top >= H:
            continue
        k = brightness(top)
        x0 = left + SWAY[age % len(SWAY)]
        for dy, row in enumerate(rows):
            for dx, cell in enumerate(row):
                x, y = x0 + dx, top + dy
                if cell == "." or not (0 <= x < W and 0 <= y < H) or k == 0:
                    continue
                r, g, b = COLOURS[colour][cell]
                pixels[x, y] = (round(r * k), round(g * k), round(b * k), 255)
    return image


def main(out_dir):
    name = f"hearts_{W}x{H}"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta = {"fps": FPS, "color_mode": "argb8888", "sections": [{"name": "whole", "start": 0, "end": LOOP - 1}]}
    with zipfile.ZipFile(out / f"{name}.zip", "w") as archive:
        archive.writestr(f"{name}/meta.json", json.dumps(meta, indent=2))
        for index in range(LOOP):
            data = BytesIO()
            frame(index).save(data, "PNG")
            archive.writestr(f"{name}/frame_{index}.png", data.getvalue())
    sheet = Image.new("RGBA", (LOOP * (W + 1), H), (40, 40, 40, 255))
    for index in range(LOOP):
        sheet.paste(frame(index), (index * (W + 1), 0))
    sheet.resize((sheet.width * 8, sheet.height * 8), Image.NEAREST).save(out / "sheet.png")


if __name__ == "__main__":
    main(sys.argv[1])
