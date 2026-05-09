"""Keyboard input via pygame events.

Same `is_held(key)` API as the existing curses-based InputHandler so games can
swap implementations without changing call sites. True press/release tracking
across all platforms — no Kitty-protocol negotiation, no sticky-key fallback.

`poll()` is a no-op: events are dispatched from the pygame main loop into
`handle_event()` directly. It exists for source compatibility with games that
call `input.poll()` once per tick.
"""

from __future__ import annotations

import threading

import pygame

# pygame keycode -> normalized key name used by the games.
_KEY_MAP = {
    pygame.K_w: 'w',
    pygame.K_a: 'a',
    pygame.K_s: 's',
    pygame.K_d: 'd',
    pygame.K_q: 'q',
    pygame.K_r: 'r',
    pygame.K_v: 'v',
    pygame.K_n: 'n',
    pygame.K_p: 'p',
    pygame.K_UP: 'up',
    pygame.K_DOWN: 'down',
    pygame.K_LEFT: 'left',
    pygame.K_RIGHT: 'right',
    pygame.K_SPACE: 'space',
    pygame.K_RETURN: 'enter',
    pygame.K_ESCAPE: 'escape',
}


class InputHandler:
    def __init__(self):
        self._held: set[str] = set()
        self._lock = threading.Lock()

    # --- Main-thread side (pygame loop) ---

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            key = _KEY_MAP.get(event.key)
            if key is not None:
                with self._lock:
                    self._held.add(key)
        elif event.type == pygame.KEYUP:
            key = _KEY_MAP.get(event.key)
            if key is not None:
                with self._lock:
                    self._held.discard(key)

    # --- Game-thread side ---

    def poll(self) -> None:
        """No-op. Kept for API parity with the curses-based handler."""

    def is_held(self, key: str) -> bool:
        with self._lock:
            return key in self._held
