"""SymbolGrid — the contract between the game and the renderer.

A 2D grid of (char, color, reverse) cells. The game fills the back buffer;
`present()` swaps it with the front buffer that the renderer reads.

This is the only structure the renderer paints from. It knows nothing about
Braille, shapes, or pixels — just characters in cells.
"""

from __future__ import annotations

import threading


class SymbolGrid:
    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols
        size = rows * cols
        self._back_chars: list[str] = [' '] * size
        self._back_colors = bytearray(size)
        self._back_reverse = bytearray(size)
        self._front_chars: list[str] = [' '] * size
        self._front_colors = bytearray(size)
        self._front_reverse = bytearray(size)
        self._lock = threading.Lock()

    # --- Game-thread side (writes into back buffer) ---

    def clear(self) -> None:
        size = self.rows * self.cols
        # Reassigning is faster than zero-fill loops.
        self._back_chars = [' '] * size
        self._back_colors = bytearray(size)
        self._back_reverse = bytearray(size)

    def text(self, row: int, col: int, text: str, color: int = 0, reverse: bool = False) -> None:
        if not (0 <= row < self.rows):
            return
        base = row * self.cols
        rev = 1 if reverse else 0
        c8 = color & 0xFF
        for i, ch in enumerate(text):
            c = col + i
            if c < 0:
                continue
            if c >= self.cols:
                break
            idx = base + c
            self._back_chars[idx] = ch
            self._back_colors[idx] = c8
            self._back_reverse[idx] = rev

    def set_cell(self, row: int, col: int, char: str, color: int = 0, reverse: bool = False) -> None:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            idx = row * self.cols + col
            self._back_chars[idx] = char
            self._back_colors[idx] = color & 0xFF
            self._back_reverse[idx] = 1 if reverse else 0

    def present(self) -> None:
        """Atomically swap back and front buffers."""
        with self._lock:
            self._back_chars, self._front_chars = self._front_chars, self._back_chars
            self._back_colors, self._front_colors = self._front_colors, self._back_colors
            self._back_reverse, self._front_reverse = self._front_reverse, self._back_reverse

    # --- Renderer-thread side (reads front buffer) ---

    def snapshot(self) -> tuple[list[str], bytes, bytes]:
        """Stable copy of the current front buffer."""
        with self._lock:
            return (
                list(self._front_chars),
                bytes(self._front_colors),
                bytes(self._front_reverse),
            )
