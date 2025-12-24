from __future__ import annotations

import random
import time
from dataclasses import dataclass

from rich.console import Console
from rich.live import Live
from rich.text import Text

VIEW_WIDTH = 80
VIEW_HEIGHT = 20
RUN_HINT = " $ uvx x-mas"


@dataclass
class Particle:
    x: float
    y: float
    char: str
    drift: float
    sway: int
    swept: bool = False
    dark: bool = False


ORNAMENT_ALT = {
    "o": "O",
    "O": "o",
    "@": "*",
    "x": "+",
}


def build_tree_layout(width: int, height: int, rng: random.Random) -> dict:
    ground_y = max(0, height - 2)
    max_height_by_width = max(1, (width - 1) // 2)
    max_available = max(4, ground_y)

    tree_height = min(15, max_height_by_width, max(4, max_available - 4))
    while True:
        trunk_h = max(2, tree_height // 6)
        if tree_height + trunk_h <= max_available:
            break
        tree_height = max(4, max_available - trunk_h)

    top_y = max(0, ground_y - (tree_height + trunk_h))

    trunk_w = max(3, tree_height // 5)
    if trunk_w % 2 == 0:
        trunk_w += 1

    center_x = width // 2
    layout: dict[tuple[int, int], str] = {}
    leaf_positions: list[tuple[int, int]] = []

    for r in range(tree_height):
        y = top_y + r
        left = center_x - r
        right = center_x + r
        if left < 0 or right >= width:
            break
        if r == 0:
            layout[(center_x, y)] = "^"
            continue
        layout[(left, y)] = "/"
        layout[(right, y)] = "\\"
        for x in range(left + 1, right):
            layout[(x, y)] = "^"
            leaf_positions.append((x, y))

    trunk_top = top_y + tree_height
    for y in range(trunk_top, min(trunk_top + trunk_h, ground_y)):
        for x in range(center_x - trunk_w // 2, center_x + trunk_w // 2 + 1):
            if 0 <= x < width:
                layout[(x, y)] = "|"

    star_pos = (center_x, max(0, top_y - 1))

    ornaments: list[tuple[int, int, str]] = []
    target_count = min(len(leaf_positions), max(12, tree_height * 2))

    rows: dict[int, list[int]] = {}
    for lx, ly in leaf_positions:
        rows.setdefault(ly, []).append(lx)

    sorted_y = sorted(rows.keys())
    for y in sorted_y:
        row_x_list = rows[y]
        row_target = max(1, int(len(row_x_list) / len(leaf_positions) * target_count * 1.2))

        rng.shuffle(row_x_list)
        placed_in_row = 0
        for x in row_x_list:
            if len(ornaments) >= target_count or placed_in_row >= row_target:
                break

            is_too_close = False
            for ox, oy, _ in ornaments:
                dist = abs(ox - x) + abs(oy - y)
                if (oy == y and abs(ox - x) < 3) or dist < 2:
                    is_too_close = True
                    break

            if not is_too_close:
                ornaments.append((x, y, rng.choice(["o", "O", "@", "*", "+", "x", "§"])))
                placed_in_row += 1

    if len(ornaments) < target_count:
        shuffled_all = leaf_positions.copy()
        rng.shuffle(shuffled_all)
        for x, y in shuffled_all:
            if len(ornaments) >= target_count:
                break
            if not any(ox == x and oy == y for ox, oy, _ in ornaments):
                ornaments.append((x, y, rng.choice(["o", "O", "@", "*", "+", "x", "§"])))

    solid: set[tuple[int, int]] = set(layout.keys())
    solid.update((ox, oy) for ox, oy, _ in ornaments)
    solid.add(star_pos)

    return {
        "ground_y": ground_y,
        "center_x": center_x,
        "layout": layout,
        "ornaments": ornaments,
        "star_pos": star_pos,
        "solid": solid,
    }


def make_canvas(width: int, height: int) -> list[list[str]]:
    return [[" "] * width for _ in range(height)]


def render_frame(
    width: int,
    height: int,
    scene: dict,
    particles: list[Particle],
    ground_snow: list[int],
    frame: int,
) -> Text:
    grid = [[(" ", "white") for _ in range(width)] for _ in range(height)]
    ground_y = scene["ground_y"]

    if 0 <= ground_y < height:
        for x in range(width):
            grid[ground_y][x] = ("_", "dim white")
        for x in range(width):
            if ground_snow[x] > 0:
                grid[ground_y][x] = ("_", "white")

    for p in particles:
        px, py = int(p.x), int(p.y)
        if 0 <= px < width and 0 <= py < height:
            style = "white" if p.char == "*" else ("dim white" if p.dark else "white")
            grid[py][px] = (p.char, style)

    for (x, y), ch in scene["layout"].items():
        if 0 <= x < width and 0 <= y < height:
            style = "bold green" if ch in ["/", "\\", "^"] else "bold brown"
            grid[y][x] = (ch, style)

    for idx, (x, y, ch) in enumerate(scene["ornaments"]):
        if 0 <= x < width and 0 <= y < height:
            sync_tick = frame // 8

            if (sync_tick + idx) % 2 == 0:
                ch = ORNAMENT_ALT.get(ch, ch)

            colors = [
                "bold red",
                "bold yellow",
                "bold blue",
                "bold cyan",
                "bold magenta",
                "bold bright_yellow",
                "bold bright_red",
                "bold white",
            ]
            style = colors[(idx + sync_tick) % len(colors)]
            grid[y][x] = (ch, style)

    star_x, star_y = scene["star_pos"]
    if 0 <= star_x < width and 0 <= star_y < height:
        star_char = "*" if (frame // 12) % 2 == 0 else "+"
        grid[star_y][star_x] = (star_char, "bold #FFD700")

    if height > 0 and width > 0:
        hint_y = height - 1
        for i, ch in enumerate(RUN_HINT[:width]):
            grid[hint_y][i] = (ch, "dim white")

    result = Text()
    for y in range(height):
        for x in range(width):
            char, style = grid[y][x]
            result.append(char, style=style)
        if y < height - 1:
            result.append("\n")

    msg = "★ MERRY CHRISTMAS & HAPPY NEW YEAR ★"
    msg_width = len(msg)
    padding = (width - msg_width) // 2

    if padding > 0:
        result.append("\n\n" + " " * padding)

        palette = [
            "#D4AF37",
            "#E5C158",
            "#F1D279",
            "#FBE39A",
            "#FFFFFF",
            "#FBE39A",
            "#F1D279",
            "#E5C158",
            "#D4AF37",
            "#B8860B",
            "#8B6508",
            "#B8860B",
        ]

        for i, char in enumerate(msg):
            color_idx = int((frame // 2 - i * 0.6) % len(palette))
            style = f"bold {palette[color_idx]}"
            result.append(char, style=style)

    return result


def spawn_particles(rng: random.Random, width: int, particles: list[Particle], max_particles: int) -> None:
    if len(particles) >= max_particles:
        return
    spawn_count = rng.randint(0, max(2, width // 25))
    for _ in range(spawn_count):
        x = rng.randrange(width)
        ch = rng.choice([".", ".", ".", "*"])
        particles.append(
            Particle(
                x=x,
                y=0,
                char=ch,
                drift=rng.choice([-0.5, 0.0, 0.5]),
                sway=rng.randint(2, 5),
                dark=(ch != "*" and rng.random() < 0.22),
            )
        )


def update_particles(
    rng: random.Random,
    width: int,
    scene: dict,
    particles: list[Particle],
    ground_snow: list[int],
) -> None:
    next_particles: list[Particle] = []
    ground_y: int = scene["ground_y"]
    center_x: int = scene["center_x"]
    solid: set[tuple[int, int]] = scene["solid"]
    layout: dict[tuple[int, int], str] = scene["layout"]

    for p in particles:
        p.sway -= 1
        if p.sway <= 0:
            p.x += p.drift
            p.drift = rng.choice([-0.5, 0.0, 0.5])
            p.sway = rng.randint(6, 15)

        if p.x < 0 or p.x >= width:
            continue

        fall_speed = 0.25
        next_x = p.x
        next_y = p.y + fall_speed

        ix, iy = int(next_x), int(next_y)

        if (ix, iy) in solid:
            p.char = "."
            p.swept = True
            p.dark = False
            hit_ch = layout.get((ix, iy), "")
            if hit_ch == "/":
                dx = -0.6
            elif hit_ch == "\\":
                dx = 0.6
            else:
                dx = -0.6 if ix < center_x else 0.6

            slide_speed = 0.5
            cand_x = next_x + dx
            cand_y = p.y + slide_speed

            for try_dx in (dx, -dx, 0.0):
                tx = cand_x if try_dx == dx else next_x + try_dx
                ty = cand_y
                if 0 <= tx < width and (int(tx), int(ty)) not in solid:
                    next_x, next_y = tx, ty
                    break
            else:
                next_x, next_y = next_x, p.y + slide_speed

        p.x, p.y = next_x, next_y

        if int(p.y) >= ground_y:
            life = rng.randint(6, 12)
            gx = int(p.x)
            if 0 <= gx < width and ground_snow[gx] < life:
                ground_snow[gx] = life
            continue
        next_particles.append(p)
    particles[:] = next_particles


def decay_ground_snow(ground_snow: list[int]) -> None:
    for i, life in enumerate(ground_snow):
        if life > 0:
            ground_snow[i] = life - 1


def main() -> None:
    rng = random.Random(7)
    console = Console()
    width = VIEW_WIDTH
    height = VIEW_HEIGHT

    scene = build_tree_layout(width, height, rng)
    ground_snow = [0] * width
    particles: list[Particle] = []
    max_particles = width * 2

    initial_count = max_particles // 2
    attempts = 0
    while len(particles) < initial_count and attempts < initial_count * 10:
        attempts += 1
        x = rng.uniform(0, width - 1)
        y = rng.uniform(0, scene["ground_y"])
        if (int(x), int(y)) in scene["solid"]:
            continue
        ch = rng.choice([".", ".", ".", "*"])
        particles.append(
            Particle(
                x=x,
                y=y,
                char=ch,
                drift=rng.choice([-0.5, 0.0, 0.5]),
                sway=rng.randint(1, 15),
                dark=(ch != "*" and rng.random() < 0.22),
            )
        )

    frame = 0

    with Live("", console=console, refresh_per_second=20, screen=True) as live:
        while True:
            spawn_particles(rng, width, particles, max_particles)
            update_particles(rng, width, scene, particles, ground_snow)
            decay_ground_snow(ground_snow)
            frame_text = render_frame(width, height, scene, particles, ground_snow, frame)
            live.update(frame_text)
            frame += 1
            time.sleep(0.08)
