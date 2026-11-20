"""Frames for the corner animations: src/animations/{hearts,robot,alien}.anim.

Two figures, a big and a small one, float up from below the display in the bottom-right corner,
pass through their places in the design and fade into the background near the top. The username
is drawn above the animation (z_index in main.js), so a long scrolling username stays readable.

Hearts and the pink background come from the Figma design. The robot and the alien follow the
look and the motion of the 🤖 and 👾 Telegram emoji in pixel form, in the same style as the
hearts: a saturated base colour, a darker rim and a light highlight. While they float, the alien
steps and waves, blinks and flashes pink and blue; the robot looks around, blinks, changes its
mouth and tilts its head.

    python3 tools/animations.py build/
    for name in hearts robot alien; do
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
HEART_BIG = [
    ["751568", "C32488", "9F1D79", _, "BC2385", "C7248A", "731467"],
    ["E42B96", "FF30A1", "FF30A1", "F32D9D", "FF30A1", "FF30A1", "D2268F"],
    ["F32D9D", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "D2268F"],
    ["AA1F7E", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "FF30A1", "85176E"],
    [_, "C92C8E", "FF50B0", "FF51B1", "FE3DA8", "A21D7A", _],
    [_, _, "CE5CA6", "FEA7D8", "AB3D8C", _, _],
]
HEART_SMALL = [
    [_, "73146C", _, "7A156F", _],
    ["881775", "FF30AC", "EB2CA2", "FF30AB", "BA228C"],
    ["7A156D", "FE2EAB", "FF30AC", "FF30AC", "9F1D7F"],
    [_, "9F2584", "FD70C6", "C03296", _],
    [_, _, "802B7A", _, _],
]


def paint(rows, palette):
    return [[palette[c] if c != "." else None for c in row] for row in rows]


# --- Alien (👾) --------------------------------------------------------------------------------

ALIEN_COLOURS = {
    "purple": {"P": "9060D0", "L": "B890F0", "r": "5A3590", "t": "C8A8FF"},
    "pink": {"P": "F04888", "L": "FF9CC0", "r": "A02058", "t": "FFC2D8"},
    "blue": {"P": "40C8F0", "L": "A8ECFF", "r": "1E7896", "t": "C8F4FF"},
}
ALIEN_BIG = {  # 9x8; arms down and up, like a step
    "down": [
        ".t.....t.",
        "..t...t..",
        "..LLPPP..",
        ".PPkPkPP.",
        "PPPPPPPPP",
        "P.PPPPP.P",
        "P.r...r.P",
        "..rr.rr..",
    ],
    "up": [
        ".t.....t.",
        "P.t...t.P",
        "P.LLPPP.P",
        "PPPkPkPPP",
        "PPPPPPPPP",
        "..PPPPP..",
        "..r...r..",
        ".rr...rr.",
    ],
}
ALIEN_SMALL = {  # 7x6
    "down": [
        ".t...t.",
        "..LPP..",
        ".PkPkP.",
        "PPPPPPP",
        "P.r.r.P",
        ".rr.rr.",
    ],
    "up": [
        ".t...t.",
        "P.LPP.P",
        "PPkPkPP",
        ".PPPPP.",
        "..r.r..",
        ".rr.rr.",
    ],
}


def alien(sprites, age):
    pose = "down" if (age // 3) % 2 == 0 else "up"  # a step every half second
    colour = {10: "pink", 11: "pink", 12: "blue", 13: "blue"}.get(age, "purple")
    rows = sprites[pose]
    if age in (6, 7):  # blink: the eyes close
        rows = [row.replace("k", "P") for row in rows]
    palette = dict(ALIEN_COLOURS[colour], k="10081C")
    return paint(rows, palette)


# --- Robot (🤖) --------------------------------------------------------------------------------

ROBOT_COLOURS = {
    "o": "FFA51F",  # antenna light
    "p": "7A4FB0",  # antenna base
    "G": "D8EEF0",  # face
    "L": "F4FBFB",  # highlight
    "d": "4E8C9C",  # rim
    "e": "C8282A",  # ears
    "B": "2A8CD0",  # eyes
    "W": "FFFFFF",  # glint, teeth
    "n": "E0302E",  # nose
    "m": "1E3A44",  # mouth
}
ROBOT_BIG = {  # 9x8
    "front": [
        "....o....",
        "...ppp...",
        ".LLGGGGd.",
        "eGWBGWBGe",
        "eGBBGBBGe",
        ".GGGnGGd.",
        ".GmWWWmd.",
        "..ddddd..",
    ],
    "look": [  # the glints move: looking to the side
        "....o....",
        "...ppp...",
        ".LLGGGGd.",
        "eGBWGBWGe",
        "eGBBGBBGe",
        ".GGGnGGd.",
        ".GGmmmGd.",
        "..ddddd..",
    ],
    "blink": [  # happy closed eyes and an "o" mouth
        "....o....",
        "...ppp...",
        ".LLGGGGd.",
        "eGGGGGGGe",
        "eGBBGBBGe",
        ".GGGnGGd.",
        ".GGGmGGd.",
        "..ddddd..",
    ],
}
ROBOT_SMALL = {  # 7x6
    "front": [
        "...o...",
        ".LGGGd.",
        "eWBGWBe",
        ".GGnGd.",
        ".GWWWd.",
        "..ddd..",
    ],
    "look": [
        "...o...",
        ".LGGGd.",
        "eBWGBWe",
        ".GGnGd.",
        ".GmmmG.",
        "..ddd..",
    ],
    "blink": [
        "...o...",
        ".LGGGd.",
        "eBBGBBe",
        ".GGnGd.",
        ".GGmGd.",
        "..ddd..",
    ],
}


def robot(sprites, age):
    face = "look" if 4 <= age < 8 else "blink" if 10 <= age < 13 else "front"
    rows = paint(sprites[face], ROBOT_COLOURS)
    if age in (5, 6, 7):  # a head tilt reads as a 1 px lean on such a small sprite
        rows = [[_] + row[:-1] for row in rows]
    return rows


DECORATIONS = {
    # name: background, then (sprite, x on the display, y of its place in the design) big and small
    "hearts": ("bg_hearts.png", [(lambda age: HEART_BIG, 62, 7), (lambda age: HEART_SMALL, 55, 11)]),
    "robot": ("bg_robot.png", [(lambda age: robot(ROBOT_BIG, age), 61, 7), (lambda age: robot(ROBOT_SMALL, age), 54, 10)]),
    "alien": ("bg_alien.png", [(lambda age: alien(ALIEN_BIG, age), 61, 7), (lambda age: alien(ALIEN_SMALL, age), 54, 10)]),
}


def fade(top):
    """1 below the username line, then down to 0 over four rows."""
    return {5: 0.8, 4: 0.6, 3: 0.4, 2: 0.2}.get(top, 1.0 if top >= 6 else 0.0)


def frame(index, figures, background):
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    big_rest = figures[0][2]
    for sprite, left, rest in figures:
        delay = rest - big_rest  # both reach their places in the design at the same frame
        age = (index - delay) % LOOP
        top = 16 - age  # starts just below the display, rises 1 px per frame
        k = fade(top)
        if k == 0:
            continue
        for dy, row in enumerate(sprite(age)):
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
    for name, (background_file, figures) in DECORATIONS.items():
        background = Image.open(ROOT / "src/images" / background_file).convert("RGB")
        folder = f"{name}_{W}x{H}"
        with zipfile.ZipFile(out / f"{folder}.zip", "w") as archive:
            archive.writestr(f"{folder}/meta.json", json.dumps(meta, indent=2))
            for index in range(LOOP):
                data = BytesIO()
                frame(index, figures, background).save(data, "PNG")
                archive.writestr(f"{folder}/frame_{index}.png", data.getvalue())


if __name__ == "__main__":
    main(sys.argv[1])
