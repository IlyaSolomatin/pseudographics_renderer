"""BrailleEngine — converts shape calls into Braille characters in a SymbolGrid.

The engine holds an internal subcell pixel buffer (2x4 dots per character cell)
and exposes the usual drawing primitives (line, circle, filled_circle, pixel,
polyline, text). `commit_to(grid)` walks the buffer, derives a Unicode Braille
codepoint per cell, picks the dominant color among lit subpixels, and writes
the result into the grid.

The engine is opt-in: a game that doesn't need subcell resolution (an ASCII
roguelike, a text UI) can ignore it entirely and write to the grid directly.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pygame

from .grid import SymbolGrid


_BRAILLE_BASE = 0x2800

DEFAULT_FONT_NAME = "menlo,monaco,courier,couriernew,monospace"
DEFAULT_FONT_SIZE = 11

# Cache of rasterized glyph bitmaps, keyed by (font_name, font_size, bold).
# Each entry maps char -> (width, height, 1-bit bytearray of length w*h).
_GLYPH_CACHES: dict[tuple[str, int, bool], dict[str, tuple[int, int, bytearray]]] = {}


def _get_glyph_cache(font_name: str, font_size: int, bold: bool) -> dict:
    key = (font_name, font_size, bold)
    cache = _GLYPH_CACHES.get(key)
    if cache is not None:
        return cache

    if not pygame.font.get_init():
        pygame.font.init()
    font = pygame.font.SysFont(font_name, font_size, bold=bold)

    cache = {}
    for code in range(32, 127):
        ch = chr(code)
        surf = font.render(ch, False, (255, 255, 255), (0, 0, 0))
        w, h = surf.get_size()
        bits = bytearray(w * h)
        for y in range(h):
            for x in range(w):
                if surf.get_at((x, y))[0] > 128:
                    bits[y * w + x] = 1
        cache[ch] = (w, h, bits)
    _GLYPH_CACHES[key] = cache
    return cache


def prebuild_glyphs(
    font_name: str = DEFAULT_FONT_NAME,
    font_size: int = DEFAULT_FONT_SIZE,
    bold: bool = False,
) -> None:
    """Eagerly rasterize the glyph cache for a font/size so the first frame has no hitch."""
    _get_glyph_cache(font_name, font_size, bold)

# Bit-weight matrix indexed [dy][dx] for vectorized codepoint computation.
# Encodes Unicode dot numbering (dot 1 -> bit 0, dot 4 -> bit 3, dot 7 -> bit 6,
# dot 8 -> bit 7).
_BRAILLE_WEIGHTS = np.array(
    [
        [1 << 0, 1 << 3],   # dy=0  (dots 1, 4)
        [1 << 1, 1 << 4],   # dy=1  (dots 2, 5)
        [1 << 2, 1 << 5],   # dy=2  (dots 3, 6)
        [1 << 6, 1 << 7],   # dy=3  (dots 7, 8)
    ],
    dtype=np.uint16,
)


class BrailleEngine:
    """Subcell pixel buffer + drawing primitives + grid commit.

    Coordinates passed to drawing methods are in *Braille subpixel space*:
    one engine cell is 2 columns x 4 rows of subpixels, so `pixel_w = 2*cols`
    and `pixel_h = 4*rows`.
    """

    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows
        self.pixel_w = cols * 2
        self.pixel_h = rows * 4
        size = self.pixel_w * self.pixel_h
        self._lit = bytearray(size)
        self._color = bytearray(size)

    # --- Frame lifecycle ---

    def clear(self) -> None:
        size = self.pixel_w * self.pixel_h
        self._lit = bytearray(size)
        self._color = bytearray(size)

    # --- Drawing primitives (subpixel coordinates) ---

    def pixel(self, x: float, y: float, color: int = 0) -> None:
        ix = int(round(x))
        iy = int(round(y))
        if 0 <= ix < self.pixel_w and 0 <= iy < self.pixel_h:
            idx = iy * self.pixel_w + ix
            self._lit[idx] = 1
            self._color[idx] = color & 0xFF

    def line(self, x0: float, y0: float, x1: float, y1: float, color: int = 0) -> None:
        """Parametric stepping at 2x oversample — clean Braille rasterization."""
        dx = x1 - x0
        dy = y1 - y0
        dist = max(abs(dx), abs(dy), 1.0)
        steps = int(dist * 2)
        if steps == 0:
            self.pixel(x0, y0, color)
            return
        inv = 1.0 / steps
        set_pixel = self.pixel
        for i in range(steps + 1):
            t = i * inv
            set_pixel(x0 + t * dx, y0 + t * dy, color)

    def polyline(self, points: Iterable[tuple[float, float]], color: int = 0) -> None:
        prev = None
        for p in points:
            if prev is not None:
                self.line(prev[0], prev[1], p[0], p[1], color)
            prev = p

    def circle(self, cx: float, cy: float, r: float, color: int = 0) -> None:
        circumference = max(int(2 * math.pi * r * 2), 16)
        set_pixel = self.pixel
        for i in range(circumference):
            angle = 2 * math.pi * i / circumference
            set_pixel(cx + r * math.cos(angle), cy + r * math.sin(angle), color)

    def filled_circle(self, cx: float, cy: float, r: float, color: int = 0) -> None:
        ri = int(r) + 1
        r_sq = r * r
        set_pixel = self.pixel
        for dy in range(-ri, ri + 1):
            dx_max = math.sqrt(max(r_sq - dy * dy, 0))
            for dx in range(int(-dx_max), int(dx_max) + 1):
                set_pixel(cx + dx, cy + dy, color)

    def text(
        self,
        s: str,
        x: float,
        y: float,
        color: int = 0,
        font_size: int = DEFAULT_FONT_SIZE,
        font_name: str = DEFAULT_FONT_NAME,
        bold: bool = False,
    ) -> int:
        """Draw `s` starting at (x, y) in subpixel coords.

        Each glyph pixel becomes one Braille subpixel. Returns the x advance
        (subpixel coord just past the last glyph) so callers can chain runs.
        """
        cache = _get_glyph_cache(font_name, font_size, bold)
        fallback = cache.get('?')
        set_pixel = self.pixel
        cx = int(x)
        iy = int(y)
        for ch in s:
            glyph = cache.get(ch) or fallback
            if glyph is None:
                continue
            gw, gh, bits = glyph
            for gy in range(gh):
                base = gy * gw
                py = iy + gy
                for gx in range(gw):
                    if bits[base + gx]:
                        set_pixel(cx + gx, py, color)
            cx += gw
        return cx

    def measure_text(
        self,
        s: str,
        font_size: int = DEFAULT_FONT_SIZE,
        font_name: str = DEFAULT_FONT_NAME,
        bold: bool = False,
    ) -> tuple[int, int]:
        """Return (width, height) of `s` in subpixels at the given font."""
        cache = _get_glyph_cache(font_name, font_size, bold)
        fallback = cache.get('?')
        if not s:
            return (0, 0)
        width = sum((cache.get(ch) or fallback)[0] for ch in s)
        height = max((cache.get(ch) or fallback)[1] for ch in s)
        return (width, height)

    # --- Bake into grid ---

    def commit_to(self, grid: SymbolGrid, row_offset: int = 0, col_offset: int = 0) -> None:
        """Compute Braille codepoint + dominant color per cell, write to grid.

        Cells with no lit subpixels are skipped (the grid retains whatever was
        there before — typically blank).
        """
        if self.pixel_w == 0 or self.pixel_h == 0:
            return

        # Vectorized codepoint per cell.
        lit_arr = np.frombuffer(self._lit, dtype=np.uint8).reshape(self.rows, 4, self.cols, 2)
        codes_2d = (lit_arr * _BRAILLE_WEIGHTS[None, :, None, :]).sum(axis=(1, 3))

        rows_idx, cols_idx = np.nonzero(codes_2d)
        if rows_idx.size == 0:
            return

        lit = self._lit
        col = self._color
        pw = self.pixel_w
        grid_cols = grid.cols
        back_chars = grid._back_chars
        back_colors = grid._back_colors

        for r, c in zip(rows_idx.tolist(), cols_idx.tolist()):
            base_y = r * 4
            base_x = c * 2
            # Walk the 8 subpixels, count colors among lit ones.
            counts: dict[int, int] = {}
            row0 = base_y * pw
            row1 = row0 + pw
            row2 = row1 + pw
            row3 = row2 + pw
            for off in (
                row0 + base_x, row0 + base_x + 1,
                row1 + base_x, row1 + base_x + 1,
                row2 + base_x, row2 + base_x + 1,
                row3 + base_x, row3 + base_x + 1,
            ):
                if lit[off]:
                    cc = col[off]
                    counts[cc] = counts.get(cc, 0) + 1

            color_id = max(counts, key=lambda k: (counts[k], k))
            code = int(codes_2d[r, c])

            grid_row = r + row_offset
            grid_col = c + col_offset
            if 0 <= grid_row < grid.rows and 0 <= grid_col < grid_cols:
                idx = grid_row * grid_cols + grid_col
                back_chars[idx] = chr(_BRAILLE_BASE + code)
                back_colors[idx] = color_id
