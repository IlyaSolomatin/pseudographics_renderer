"""Pygame-backed pseudographics renderer.

Public API:
    Runtime         — context manager: window, threads, lifecycle
    SymbolGrid      — the (char, color, reverse) grid the renderer paints
    BrailleEngine   — opt-in helper: shape primitives -> Braille chars in a grid
    InputHandler    — `is_held(key)` over pygame events
    DEFAULT_PALETTE — color ID -> RGB lookup
"""

from .braille import BrailleEngine
from .grid import SymbolGrid
from .input import InputHandler
from .palette import DEFAULT_PALETTE
from .runtime import Runtime

__all__ = [
    "Runtime",
    "SymbolGrid",
    "BrailleEngine",
    "InputHandler",
    "DEFAULT_PALETTE",
]
