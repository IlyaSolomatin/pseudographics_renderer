"""Color palette: integer color IDs map to RGB tuples.

Index 0 is the default color; games that omit a color argument get this.
The default 16-entry palette mirrors the curses ANSI-ish basics so that games
already using `curses.color_pair` IDs port over cleanly.
"""

from __future__ import annotations

RGB = tuple[int, int, int]

DEFAULT_PALETTE: list[RGB] = [
    (200, 200, 200),  # 0  default (light gray)
    (240, 240, 240),  # 1  white
    ( 90, 220, 240),  # 2  cyan
    (240, 220,  90),  # 3  yellow
    ( 90, 220,  90),  # 4  green
    (220, 220, 100),  # 5  yellow-green (planet speck)
    (240, 240, 240),  # 6  white (rocket body)
    (240, 110, 240),  # 7  magenta
    (250, 200,  60),  # 8  orange-yellow (flame hot)
    (230,  80,  60),  # 9  red (flame cool)
    ( 90, 140, 240),  # 10 blue
    (200,  90, 200),  # 11 purple
    (160, 160, 160),  # 12 mid gray
    (110, 110, 110),  # 13 dark gray
    (255, 255, 255),  # 14 bright white
    (  0,   0,   0),  # 15 black
]


def resolve(palette: list[RGB], color_id: int) -> RGB:
    """Look up an RGB; out-of-range IDs fall back to entry 0."""
    if 0 <= color_id < len(palette):
        return palette[color_id]
    return palette[0]
