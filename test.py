import math
import random
import sys

import pygame

# =============================================
# CONFIG
# =============================================
WINDOW_W = 900
WINDOW_H = 900
TILE_SIZE = 80  # px per tile
GRID_COLS = 11
GRID_ROWS = 11
SEED = None  # None = random each run, or set integer for fixed map

# Road anatomy (in px, relative to tile)
ROAD_W = 34  # road band width
SIDEWALK_W = 6  # curb strip width
DASH_ON = 10
DASH_OFF = 8

# Colors
C_BG = (13, 15, 23)
C_GRASS = (16, 20, 30)
C_SIDEWALK = (35, 40, 58)
C_ROAD = (28, 33, 50)
C_DASH = (50, 58, 88)
C_NODE_DOT = (80, 100, 160)
C_GRID_LINE = (22, 26, 38)

# =============================================
# TILE TYPES & PORT DEFINITIONS
# =============================================
EMPTY = 0
STRAIGHT = 1
CURVE = 2
TJUNCTION = 3
CROSS = 4

# Ports: N=0  E=1  S=2  W=3
# Each entry is a tuple of open port sets per rotation
TILE_PORTS = {
    STRAIGHT: [
        {0, 2},  # rot0: N-S  (vertical)
        {1, 3},  # rot1: E-W  (horizontal)
    ],
    CURVE: [
        {0, 1},  # rot0: N-E
        {1, 2},  # rot1: E-S
        {2, 3},  # rot2: S-W
        {3, 0},  # rot3: W-N
    ],
    TJUNCTION: [
        {0, 1, 2},  # rot0: N-E-S
        {1, 2, 3},  # rot1: E-S-W
        {2, 3, 0},  # rot2: S-W-N
        {3, 0, 1},  # rot3: W-N-E
    ],
    CROSS: [
        {0, 1, 2, 3},  # no rotation
    ],
}

OPPOSITE = {0: 2, 2: 0, 1: 3, 3: 1}  # N↔S, E↔W
DIR_DELTA = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}  # N E S W


def get_ports(tile_type, rotation):
    options = TILE_PORTS.get(tile_type, [])
    if not options:
        return set()
    return options[rotation % len(options)]


def can_connect(type_a, rot_a, type_b, rot_b, direction):
    """Does tile_a's port in `direction` match tile_b's opposing port?"""
    ports_a = get_ports(type_a, rot_a)
    ports_b = get_ports(type_b, rot_b)
    return (direction in ports_a) and (OPPOSITE[direction] in ports_b)


# =============================================
# GRID
# =============================================
class Tile:
    def __init__(self):
        self.type = EMPTY
        self.rotation = 0


class Grid:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.cells = [[Tile() for _ in range(cols)] for _ in range(rows)]

    def get(self, col, row):
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.cells[row][col]
        return None

    def set_tile(self, col, row, tile_type, rotation=0):
        self.cells[row][col].type = tile_type
        self.cells[row][col].rotation = rotation

    def is_road(self, col, row):
        t = self.get(col, row)
        return t is not None and t.type != EMPTY


# =============================================
# IMPORT GENERATION FROM gen.py
# =============================================
from gen import generate_map, _find_dead_ends


# =============================================
# BEZIER ROAD RENDERER
# =============================================
T = TILE_SIZE
RW = ROAD_W
SW = SIDEWALK_W
MG = (T - RW) // 2  # margin from tile edge to road edge


def _road_rect_pts(x, y, rot):
    """Returns (rect_x, rect_y, rect_w, rect_h) for a straight road band."""
    if rot == 0:  # vertical
        return (x + MG, y, RW, T)
    else:  # horizontal
        return (x, y + MG, T, RW)


def draw_sidewalk(surf, x, y, tile_type, rotation):
    """Draw curb/sidewalk strips on the closed sides of a tile."""
    ports = get_ports(tile_type, rotation)
    closed = {0, 1, 2, 3} - ports
    for d in closed:
        if d == 0:  # N closed
            pygame.draw.rect(surf, C_SIDEWALK, (x + MG, y, RW, SW))
        elif d == 2:  # S closed
            pygame.draw.rect(surf, C_SIDEWALK, (x + MG, y + T - SW, RW, SW))
        elif d == 3:  # W closed
            pygame.draw.rect(surf, C_SIDEWALK, (x, y + MG, SW, RW))
        elif d == 1:  # E closed
            pygame.draw.rect(surf, C_SIDEWALK, (x + T - SW, y + MG, SW, RW))


def draw_straight(surf, x, y, rotation):
    rx, ry, rw, rh = _road_rect_pts(x, y, rotation)
    # sidewalk strips on closed sides
    if rotation == 0:
        pygame.draw.rect(surf, C_SIDEWALK, (x, y, MG, T))
        pygame.draw.rect(surf, C_SIDEWALK, (x + T - MG, y, MG, T))
    else:
        pygame.draw.rect(surf, C_SIDEWALK, (x, y, T, MG))
        pygame.draw.rect(surf, C_SIDEWALK, (x, y + T - MG, T, MG))
    # road surface
    pygame.draw.rect(surf, C_ROAD, (rx, ry, rw, rh))
    # center dashes
    _draw_dashes_straight(surf, x, y, rotation)


def _draw_dashes_straight(surf, x, y, rotation):
    cx = x + T // 2
    cy = y + T // 2
    if rotation == 0:
        _dashes_line(surf, cx, y + 4, cx, y + T - 4, vertical=True)
    else:
        _dashes_line(surf, x + 4, cy, x + T - 4, cy, vertical=False)


def _dashes_line(surf, x1, y1, x2, y2, vertical=True):
    length = (y2 - y1) if vertical else (x2 - x1)
    pos = 0
    drawing = True
    while pos < length:
        seg = DASH_ON if drawing else DASH_OFF
        seg = min(seg, length - pos)
        if drawing:
            if vertical:
                pygame.draw.line(surf, C_DASH, (x1, y1 + pos), (x1, y1 + pos + seg), 1)
            else:
                pygame.draw.line(surf, C_DASH, (x1 + pos, y1), (x1 + pos + seg, y1), 1)
        pos += seg
        drawing = not drawing


# --- Bezier helpers ---
def _bezier_quad(p0, p1, p2, steps=24):
    """Quadratic Bezier from p0 to p2 with control p1."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        bx = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
        by = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
        pts.append((bx, by))
    return pts


def _offset_curve(pts, offset, normal_side="left"):
    """Offset a polyline by `offset` px to left or right."""
    result = []
    n = len(pts)
    for i in range(n):
        if i == 0:
            dx = pts[1][0] - pts[0][0]
            dy = pts[1][1] - pts[0][1]
        elif i == n - 1:
            dx = pts[-1][0] - pts[-2][0]
            dy = pts[-1][1] - pts[-2][1]
        else:
            dx = pts[i + 1][0] - pts[i - 1][0]
            dy = pts[i + 1][1] - pts[i - 1][1]
        l = math.hypot(dx, dy)
        if l < 1e-9:
            l = 1
        nx, ny = -dy / l, dx / l  # left normal
        if normal_side == "right":
            nx, ny = -nx, -ny
        result.append((pts[i][0] + nx * offset, pts[i][1] + ny * offset))
    return result


def _filled_band(surf, center_pts, half_w, color):
    """Draw a filled road band around a center polyline."""
    if len(center_pts) < 2:
        return
    left = _offset_curve(center_pts, half_w, "left")
    right = _offset_curve(center_pts, half_w, "right")
    poly = left + list(reversed(right))
    if len(poly) >= 3:
        pygame.draw.polygon(surf, color, [(int(p[0]), int(p[1])) for p in poly])


def draw_curve(surf, x, y, rotation):
    """
    Smooth quarter-circle road bend using offset Bezier bands.
    rot0: N-port → E-port  (enters from top, exits right)
    rot1: E → S
    rot2: S → W
    rot3: W → N
    """
    cx = x + T // 2
    cy = y + T // 2

    # Port midpoints (world coords)
    port_mid = {
        0: (x + T // 2, y),  # N
        1: (x + T, y + T // 2),  # E
        2: (x + T // 2, y + T),  # S
        3: (x, y + T // 2),  # W
    }
    # Corner control points for each rotation
    corners = {
        0: (x + T, y),  # rot0 N-E: top-right corner
        1: (x + T, y + T),  # rot1 E-S: bottom-right
        2: (x, y + T),  # rot2 S-W: bottom-left
        3: (x, y),  # rot3 W-N: top-left
    }
    port_pairs = {0: (0, 1), 1: (1, 2), 2: (2, 3), 3: (3, 0)}

    p_from, p_to = port_pairs[rotation]
    start = port_mid[p_from]
    end = port_mid[p_to]
    ctrl = (cx, cy)  # center = inward bend

    center_curve = _bezier_quad(start, ctrl, end, steps=32)

    # sidewalk on closed sides
    draw_sidewalk(surf, x, y, CURVE, rotation)

    # road band
    _filled_band(surf, center_curve, RW // 2, C_ROAD)

    # center dash
    _draw_bezier_dashes(surf, center_curve, C_DASH)


def _draw_bezier_dashes(surf, pts, color, dash=10, gap=8):
    acc = 0
    drawing = True
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        seg = math.hypot(bx - ax, by - ay)
        if seg < 0.001:
            continue
        dx, dy = (bx - ax) / seg, (by - ay) / seg
        t = 0
        while t < seg:
            period = dash if drawing else gap
            rem = min(period - acc, seg - t)
            if drawing:
                sx, sy = ax + dx * t, ay + dy * t
                ex, ey = ax + dx * (t + rem), ay + dy * (t + rem)
                pygame.draw.line(surf, color, (int(sx), int(sy)), (int(ex), int(ey)), 1)
            t += rem
            acc += rem
            if acc >= period:
                acc = 0
                drawing = not drawing


def draw_tjunction(surf, x, y, rotation):
    """T-junction with inward-curving Bézier arcs between port pairs."""
    ports = list(get_ports(TJUNCTION, rotation))
    center = (x + T // 2, y + T // 2)
    port_mid = {
        0: (x + T // 2, y),
        1: (x + T, y + T // 2),
        2: (x + T // 2, y + T),
        3: (x, y + T // 2),
    }

    # sidewalk on closed side
    draw_sidewalk(surf, x, y, TJUNCTION, rotation)

    # Draw Bézier arcs between all port pairs using CENTER as control
    # Adjacent pairs → inward concave curves; Opposite pairs → straight
    for i, p1 in enumerate(ports):
        for p2 in ports[i+1:]:
            start = port_mid[p1]
            end = port_mid[p2]
            curve = _bezier_quad(start, center, end, steps=24)
            _filled_band(surf, curve, RW // 2, C_ROAD)
            _draw_bezier_dashes(surf, curve, C_DASH)

    # Center fill for smooth merge
    pygame.draw.circle(surf, C_ROAD, (int(center[0]), int(center[1])), RW // 3 + 1)


def draw_cross(surf, x, y):
    """Cross intersection with inward-curving Bézier arcs."""
    center = (x + T // 2, y + T // 2)
    port_mid = {
        0: (x + T // 2, y),
        1: (x + T, y + T // 2),
        2: (x + T // 2, y + T),
        3: (x, y + T // 2),
    }

    # Draw all 6 port pairs through center (inward curves for adjacent,
    # straight for opposite)
    for p1 in range(4):
        for p2 in range(p1+1, 4):
            start = port_mid[p1]
            end = port_mid[p2]
            curve = _bezier_quad(start, center, end, steps=24)
            _filled_band(surf, curve, RW // 2, C_ROAD)

    # Center fill
    pygame.draw.circle(surf, C_ROAD, (int(center[0]), int(center[1])), RW // 3 + 2)

    # Subtle corner sidewalk curbs
    curb_r = max(2, MG - 4)
    for px, py in [(x, y), (x + T, y), (x, y + T), (x + T, y + T)]:
        pygame.draw.circle(surf, C_SIDEWALK, (px, py), curb_r)

    # Dashes on straight-throughs only
    for p1, p2 in [(0, 2), (1, 3)]:
        start = port_mid[p1]
        end = port_mid[p2]
        curve = _bezier_quad(start, center, end, steps=24)
        _draw_bezier_dashes(surf, curve, C_DASH)


def draw_tile(surf, col, row, tile, ox=0, oy=0):
    x = ox + col * T
    y = oy + row * T
    if tile.type == EMPTY:
        pygame.draw.rect(surf, C_GRASS, (x, y, T, T))
        return
    pygame.draw.rect(surf, C_GRASS, (x, y, T, T))
    if tile.type == STRAIGHT:
        draw_straight(surf, x, y, tile.rotation)
    elif tile.type == CURVE:
        draw_curve(surf, x, y, tile.rotation)
    elif tile.type == TJUNCTION:
        draw_tjunction(surf, x, y, tile.rotation)
    elif tile.type == CROSS:
        draw_cross(surf, x, y)


def draw_grid(surf, grid, ox=0, oy=0):
    for r in range(grid.rows):
        for c in range(grid.cols):
            draw_tile(surf, c, r, grid.cells[r][c], ox, oy)


def draw_node_dots(surf, grid, ox=0, oy=0):
    """Debug: highlight intersection nodes."""
    for r in range(grid.rows):
        for c in range(grid.cols):
            tile = grid.cells[r][c]
            if tile.type in (CURVE, TJUNCTION, CROSS):
                sx = ox + c * T + T // 2
                sy = oy + r * T + T // 2
                pygame.draw.circle(surf, C_NODE_DOT, (sx, sy), 4)


# =============================================
# MAIN
# =============================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Seruni Map — Grid + Bézier")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 13)
    font_s = pygame.font.SysFont("monospace", 11)

    seed = SEED if SEED is not None else random.randint(0, 0xFFFFFF)

    def rebuild(s):
        g = generate_map(GRID_COLS, GRID_ROWS, seed=s)
        road_count = sum(
            1
            for r in range(g.rows)
            for c in range(g.cols)
            if g.cells[r][c].type != EMPTY
        )
        all_dead = _find_dead_ends(g)
        # Only count interior dead-ends (border ones are acceptable exits)
        dead = sum(1 for c, r in all_dead
                   if c > 0 and c < g.cols-1 and r > 0 and r < g.rows-1)
        return g, road_count, dead

    grid, road_count, dead_count = rebuild(seed)

    # center the grid on screen
    def get_offset(g):
        gw = g.cols * T
        gh = g.rows * T
        return (WINDOW_W - gw) // 2, (WINDOW_H - gh) // 2

    show_nodes = True
    running = True

    while running:
        ox, oy = get_offset(grid)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    seed = random.randint(0, 0xFFFFFF)
                    grid, road_count, dead_count = rebuild(seed)
                if event.key == pygame.K_n:
                    show_nodes = not show_nodes

        screen.fill(C_BG)
        draw_grid(screen, grid, ox, oy)
        if show_nodes:
            draw_node_dots(screen, grid, ox, oy)

        # HUD
        lines = [
            f"Seed     : {seed:06X}",
            f"Tiles    : {GRID_COLS}x{GRID_ROWS}",
            f"Roads    : {road_count}",
            f"Dead ends: {dead_count}",
            "",
            "[R] New map",
            "[N] Toggle nodes",
            "[ESC] Quit",
        ]
        for i, line in enumerate(lines):
            color = (100, 130, 200) if not line.startswith("[") else (70, 90, 140)
            surf = font.render(line, True, color)
            screen.blit(surf, (14, 14 + i * 18))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
