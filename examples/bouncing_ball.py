"""Bouncing characters — demonstrates direct character-grid usage.

No BrailleEngine here. The game writes characters straight into the grid
(ASCII letters for the balls, box-drawing chars for the border, plain text
for the HUD). Shows that the renderer paints whatever character it's given.

Run:  python -m examples.bouncing_ball
Keys: SPACE = spawn a new ball with random char/color, Q/Esc = quit.
"""

import random
import time

from pseudographics_renderer import Runtime


HUD_ROWS = 1
SPAWN_CHARS = '@*O$&#%+!?ZX'
SPAWN_COLORS = (2, 3, 4, 7, 8, 9)


class Ball:
    __slots__ = ('x', 'y', 'vx', 'vy', 'char', 'color')

    def __init__(self, x, y, vx, vy, char, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.char = char
        self.color = color


def game_loop(grid, input_handler, runtime):
    cols = grid.cols
    rows = grid.rows
    play_bottom = rows - HUD_ROWS - 1   # row where bottom border lives
    hud_row = rows - 1

    inner_left = 1
    inner_right = cols - 2
    inner_top = 1
    inner_bottom = play_bottom - 1

    balls = [
        Ball(20.0,  5.0,  32.0,  24.0, '@', 2),
        Ball(45.0, 10.0, -28.0,  35.0, '*', 3),
        Ball(70.0,  7.0,  25.0, -28.0, 'O', 4),
        Ball(35.0, 14.0, -36.0,  18.0, '$', 7),
        Ball(85.0, 11.0,  30.0, -25.0, '&', 9),
        Ball(55.0, 18.0, -22.0, -32.0, '#', 8),
    ]

    title = ' Bouncing characters — pseudographics_renderer demo '
    physics_dt = 1.0 / 60.0
    timer = 0.0
    space_was_held = False
    rng = random.Random(42)

    while runtime.running:
        if input_handler.is_held('q') or input_handler.is_held('escape'):
            runtime.stop()
            break

        space = input_handler.is_held('space')
        if space and not space_was_held:
            balls.append(Ball(
                cols * 0.5,
                play_bottom * 0.5,
                rng.uniform(20.0, 40.0) * rng.choice([-1, 1]),
                rng.uniform(15.0, 35.0) * rng.choice([-1, 1]),
                rng.choice(SPAWN_CHARS),
                rng.choice(SPAWN_COLORS),
            ))
        space_was_held = space

        # --- Physics ---
        for b in balls:
            b.x += b.vx * physics_dt
            b.y += b.vy * physics_dt
            if b.x < inner_left:
                b.x = inner_left
                b.vx = abs(b.vx)
            elif b.x > inner_right:
                b.x = inner_right
                b.vx = -abs(b.vx)
            if b.y < inner_top:
                b.y = inner_top
                b.vy = abs(b.vy)
            elif b.y > inner_bottom:
                b.y = inner_bottom
                b.vy = -abs(b.vy)
        timer += physics_dt

        # --- Render frame ---
        grid.clear()

        # Top border with centered title.
        border_w = cols - 2
        if len(title) + 4 < border_w:
            lp = (border_w - len(title)) // 2
            rp = border_w - lp - len(title)
            top = '┌' + '─' * lp + title + '─' * rp + '┐'
        else:
            top = '┌' + '─' * border_w + '┐'
        grid.text(0, 0, top, color=1)
        grid.text(play_bottom, 0, '└' + '─' * border_w + '┘', color=1)
        for r in range(1, play_bottom):
            grid.set_cell(r, 0, '│', color=1)
            grid.set_cell(r, cols - 1, '│', color=1)

        # Balls.
        for b in balls:
            grid.set_cell(int(b.y), int(b.x), b.char, color=b.color)

        # HUD (full-width reverse video).
        info = f' Balls: {len(balls):2d}   T: {timer:6.1f}s '
        ctrl = ' [SPACE] spawn   [Q] quit '
        gap = cols - len(info) - len(ctrl)
        hud = info + ' ' * gap + ctrl if gap >= 1 else info.ljust(cols)
        grid.text(hud_row, 0, hud[:cols], color=1, reverse=True)

        grid.present()
        time.sleep(physics_dt)


def main():
    with Runtime(title='Bouncing characters — demo', cols=100, rows=32) as rt:
        rt.run(lambda: game_loop(rt.grid, rt.input_handler, rt))


if __name__ == '__main__':
    main()
