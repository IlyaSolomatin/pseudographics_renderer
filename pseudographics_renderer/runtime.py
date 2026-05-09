"""Lifecycle: pygame on main thread, game on a worker thread.

Use as a context manager:

    with Runtime(title="My Game", cols=120, rows=40) as rt:
        engine = BrailleEngine(cols=rt.cols, rows=rt.rows - 1)  # last row = HUD
        rt.run(lambda: my_game(rt.grid, engine, rt.input_handler, rt))

`rt.run(fn)` blocks until `fn` returns or the window closes. Pygame must own
the main thread (macOS hard requirement); the game runs on a worker.
"""

from __future__ import annotations

import threading
from typing import Callable

import pygame

from .grid import SymbolGrid
from .input import InputHandler
from .palette import DEFAULT_PALETTE
from .surface import Surface


class Runtime:
    def __init__(
        self,
        title: str = "Pseudographics",
        cols: int = 120,
        rows: int = 40,
        cell_pixel: tuple[int, int] = (8, 16),
        palette: list[tuple[int, int, int]] | None = None,
        display_fps: int = 60,
        font_size: int = 14,
        background: tuple[int, int, int] = (0, 0, 0),
        dot_size: int | None = None,
    ):
        self.title = title
        self.cols = cols
        self.rows = rows
        self.cell_pixel = cell_pixel
        self.palette = palette if palette is not None else DEFAULT_PALETTE
        self.display_fps = display_fps
        self.font_size = font_size
        self.background = background
        self.dot_size = dot_size

        self.grid: SymbolGrid | None = None
        self.input_handler: InputHandler | None = None
        self.surface: Surface | None = None
        self.screen: pygame.Surface | None = None

        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def stop(self) -> None:
        self._running = False

    # --- Context manager ---

    def __enter__(self) -> "Runtime":
        pygame.init()
        pygame.display.set_caption(self.title)

        self.grid = SymbolGrid(self.rows, self.cols)
        self.input_handler = InputHandler()
        self.surface = Surface(
            self.grid,
            self.palette,
            cell_pixel_w=self.cell_pixel[0],
            cell_pixel_h=self.cell_pixel[1],
            font_size=self.font_size,
            dot_size=self.dot_size,
        )

        win_w = self.cols * self.cell_pixel[0]
        win_h = self.rows * self.cell_pixel[1]
        self.screen = pygame.display.set_mode((win_w, win_h))

        self._running = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._running = False
        pygame.quit()

    # --- Main loop ---

    def run(self, game_func: Callable[[], None]) -> None:
        game_thread = threading.Thread(target=self._game_wrapper, args=(game_func,), daemon=True)
        game_thread.start()

        clock = pygame.time.Clock()
        try:
            while self._running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                        break
                    self.input_handler.handle_event(event)
                if not self._running:
                    break

                self.screen.fill(self.background)
                self.surface.blit(self.screen)
                pygame.display.flip()
                clock.tick(self.display_fps)
        finally:
            self._running = False
            game_thread.join(timeout=1.0)

    def _game_wrapper(self, game_func: Callable[[], None]) -> None:
        try:
            game_func()
        finally:
            self._running = False
