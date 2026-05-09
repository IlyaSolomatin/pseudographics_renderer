"""Composites a SymbolGrid onto a pygame screen.

The renderer paints whatever characters the grid contains. It maintains a
glyph atlas keyed by (char, color, reverse) -> pre-rendered Surface.

For most codepoints the atlas builds glyphs with `pygame.font.render`. For
Unicode Braille (U+2800..U+28FF) the atlas falls back to hand-drawn dots —
SDL_ttf can't read Braille glyphs from typical system fonts, so we draw them
ourselves. This is a font-coverage workaround, not part of the contract: from
the game's side, Braille codepoints are just regular characters in the grid.
"""

from __future__ import annotations

import pygame

from .grid import SymbolGrid


_BRAILLE_BASE = 0x2800

# Bit -> (col_idx, row_idx) within the cell's 2x4 dot grid.
_BIT_TO_DOT_POS: tuple[tuple[int, int], ...] = (
    (0, 0),  # dot 1
    (0, 1),  # dot 2
    (0, 2),  # dot 3
    (1, 0),  # dot 4
    (1, 1),  # dot 5
    (1, 2),  # dot 6
    (0, 3),  # dot 7
    (1, 3),  # dot 8
)


class Surface:
    def __init__(
        self,
        grid: SymbolGrid,
        palette: list[tuple[int, int, int]],
        cell_pixel_w: int = 8,
        cell_pixel_h: int = 16,
        font_size: int = 14,
        font_name: str | None = None,
        dot_size: int | None = None,
    ):
        self.grid = grid
        self.palette = palette
        self.cell_w = cell_pixel_w
        self.cell_h = cell_pixel_h

        if dot_size is None:
            dot_size = max(1, min(cell_pixel_w // 2 - 2, cell_pixel_h // 4 - 2, 3))
        self.dot_size = dot_size

        if font_name is None:
            font_name = (
                pygame.font.match_font('menlo,monaco,consolas,couriernew,monospace')
                or pygame.font.get_default_font()
            )
        self._font = pygame.font.Font(font_name, font_size)
        self._atlas: dict[tuple[str, int, bool], pygame.Surface] = {}

    def window_size(self) -> tuple[int, int]:
        return (self.grid.cols * self.cell_w, self.grid.rows * self.cell_h)

    # --- Per-frame composition ---

    def blit(self, screen: pygame.Surface) -> None:
        chars, colors, reverses = self.grid.snapshot()
        cols = self.grid.cols
        rows = self.grid.rows
        cell_w, cell_h = self.cell_w, self.cell_h
        atlas = self._atlas

        blits: list[tuple[pygame.Surface, tuple[int, int]]] = []
        for row in range(rows):
            base = row * cols
            y = row * cell_h
            for col in range(cols):
                idx = base + col
                ch = chars[idx]
                rev = bool(reverses[idx])
                if ch == ' ' and not rev:
                    continue

                color = colors[idx]
                key = (ch, color, rev)
                surf = atlas.get(key)
                if surf is None:
                    surf = self._build_glyph(ch, color, rev)
                    atlas[key] = surf

                blits.append((surf, (col * cell_w, y)))

        if blits:
            screen.blits(blits, doreturn=False)

    # --- Glyph atlas builders ---

    def _resolve_color(self, color_id: int) -> tuple[int, int, int]:
        palette = self.palette
        if 0 <= color_id < len(palette):
            return palette[color_id]
        return palette[0]

    def _build_glyph(self, char: str, color: int, reverse: bool) -> pygame.Surface:
        codepoint = ord(char)
        fg = self._resolve_color(color)
        if 0x2800 <= codepoint <= 0x28FF:
            return self._build_braille_glyph(codepoint - _BRAILLE_BASE, fg, reverse)
        return self._build_font_glyph(char, fg, reverse)

    def _build_font_glyph(self, char: str, fg: tuple[int, int, int], reverse: bool) -> pygame.Surface:
        if reverse:
            return self._font.render(char, True, (0, 0, 0), fg)
        return self._font.render(char, True, fg)

    def _build_braille_glyph(self, code: int, fg: tuple[int, int, int], reverse: bool) -> pygame.Surface:
        if reverse:
            surf = pygame.Surface((self.cell_w, self.cell_h))
            surf.fill(fg)
            dot_color = (0, 0, 0)
        else:
            surf = pygame.Surface((self.cell_w, self.cell_h), pygame.SRCALPHA)
            dot_color = fg

        dot_region_w = self.cell_w / 2
        dot_region_h = self.cell_h / 4
        ds = self.dot_size
        half = ds / 2
        for bit in range(8):
            if code & (1 << bit):
                cx_idx, cy_idx = _BIT_TO_DOT_POS[bit]
                cx = dot_region_w * (cx_idx + 0.5)
                cy = dot_region_h * (cy_idx + 0.5)
                rect = pygame.Rect(int(cx - half), int(cy - half), ds, ds)
                surf.fill(dot_color, rect)

        return surf
