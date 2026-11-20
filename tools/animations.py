"""Frames for the corner animations: src/animations/{hearts,robot,bug}.anim.

Two figures, a big and a small one, float up from below the display in the bottom-right corner,
pass through their places in the design (big one at x 62, y 7; small one at x 55, y 11) and fade
into the background near the top. The username is drawn above the animation (z_index in main.js),
so a long scrolling username stays readable.

Hearts and the pink background come from the Figma design. The robot and the bug are drawn in the
same style: a saturated base colour, a darker rim and a light highlight.

    python3 tools/animations.py build/
    for name in hearts robot bug; do
        python3 <firmware>/scripts/seq2anim.py -o src/animations/$name.anim build/${name}_17x16.zip
    done

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
LOOP = 24  # 4 s: a pair of figures, then a short pause

_ = None
HEARTS = {
    "background": "bg_hearts.png",
    "big": [
        ["751568", "C32488", "9F1D79", _, "BC2385", "C7248A", "731467"],
        ["E42B96", "FF30A1", "FF30A1", "F32D9D", "FF30A1", "FF30A1", "D2268F"],
        ["F32D9D", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "D2268F"],
        ["AA1F7E", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "85176E"],
        [_, "C92C8E", "FF50B0", "FF51B1", "FE3DA8", "A21D7A", _],
        [_, _, "CE5CA6", "FEA7D8", "AB3D8C", _, _],
    ],
    "small": [
        [_, "73146C", _, "7A156F", _],
        ["881775", "FF30AC", "EB2CA2", "FF30AB", "BA228C"],
        ["7A156D", "FE2EAB", "FF30AC", "FF30AC", "9F1D7F"],
        [_, "9F2584", "FD70C6", "C03296", _],
        [_, _, "802B7A", _, _],
    ],
}


def sprite(rows, palette):
    return [[palette[c] if c != "." else None for c in row] for row in rows]


ROBOT_PALETTE = {
    "B": "3FA9FF",  # body
    "L": "B8E2FF",  # highlight
    "b": "1E5FA8",  # rim
    "e": "2A6FC0",  # ears
    "W": "FFFFFF",  # eyes
    "m": "9EE7FF",  # mouth
    "t": "FF5A5A",  # antenna light
    "s": "7FA3C8",  # antenna stem
}
ROBOT = {
    "background": "bg_robot.png",
    "big": sprite(
        [
            "...t...",
            "...s...",
            ".LLBBb.",
            "eBWBWBe",
            "eBBBBBe",
            ".BmmmB.",
            ".bbbbb.",
        ],
        ROBOT_PALETTE,
    ),
    "small": sprite(
        [
            "..t..",
            "LBBBb",
            "BWBWB",
            "BmmmB",
            ".bbb.",
        ],
        ROBOT_PALETTE,
    ),
}

BUG_PALETTE = {
    "R": "FF3B3B",  # shell
    "L": "FF9C9C",  # highlight
    "r": "B81E2A",  # rim
    "k": "5A0A12",  # line between the wings
    "S": "2A0A0A",  # spots
    "H": "3A3A3A",  # head
    "h": "8A8A8A",  # head highlight
    "a": "6A6A6A",  # antennae
}
BUG = {
    "background": "bg_bug.png",
    "big": sprite(
        [
            ".a...a.",
            "..HhH..",
            ".LRkRR.",
            "rRSkRSr",
            "rRRkRRr",
            "rSRkRSr",
            ".rRkRr.",
            "..rrr..",
        ],
        BUG_PALETTE,
    ),
    "small": sprite(
        [
            "a...a",
            ".HhH.",
            "LRkRR",
            "RSkSR",
            "rRkRr",
            ".rrr.",
        ],
        BUG_PALETTE,
    ),
}

DECORATIONS = {"hearts": HEARTS, "robot": ROBOT, "bug": BUG}


def fade(top):
    """1 below the username line, then down to 0 over four rows."""
    return {5: 0.8, 4: 0.6, 3: 0.4, 2: 0.2}.get(top, 1.0 if top >= 6 else 0.0)


def frame(index, decoration, background):
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # Delay in frames: when the big figure is at y 7, the small one is at y 11.
    figures = [(decoration["big"], 62, 0), (decoration["small"], 55, 4)]
    for rows, left, delay in figures:
        age = (index - delay) % LOOP
        top = 16 - age  # starts just below the display, rises 1 px per frame
        k = fade(top)
        if k == 0:
            continue
        for dy, row in enumerate(rows):
            for dx, colour in enumerate(row):
                x, y = left + dx, top + dy
                if colour is None or not (0 <= y < 16):
                    continue
                figure = [int(colour[i : i + 2], 16) for i in (0, 2, 4)]
                under = background.getpixel((x, y))[:3]
                mixed = tuple(round(b + (f - b) * k) for f, b in zip(figure, under))
                image.putpixel((x - X0, y - Y0), mixed + (255,))
    return image


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta = {"fps": FPS, "color_mode": "argb8888", "sections": [{"name": "whole", "start": 0, "end": LOOP - 1}]}
    for name, decoration in DECORATIONS.items():
        background = Image.open(ROOT / "src/images" / decoration["background"]).convert("RGB")
        folder = f"{name}_{W}x{H}"
        with zipfile.ZipFile(out / f"{folder}.zip", "w") as archive:
            archive.writestr(f"{folder}/meta.json", json.dumps(meta, indent=2))
            for index in range(LOOP):
                data = BytesIO()
                frame(index, decoration, background).save(data, "PNG")
                archive.writestr(f"{folder}/frame_{index}.png", data.getvalue())


if __name__ == "__main__":
    main(sys.argv[1])
