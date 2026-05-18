"""
Seruni Map Engine — Camera, A*, Car, TileCache
"""
import math
import heapq
import pygame

# Tile constants (mirrored from gen.py)
EMPTY = 0
STRAIGHT = 1
CURVE = 2
TJUNCTION = 3
CROSS = 4
TILE_PORTS = {
    STRAIGHT: [{0, 2}, {1, 3}],
    CURVE: [{0, 1}, {1, 2}, {2, 3}, {3, 0}],
    TJUNCTION: [{0, 1, 2}, {1, 2, 3}, {2, 3, 0}, {3, 0, 1}],
    CROSS: [{0, 1, 2, 3}],
}
OPPOSITE = {0: 2, 2: 0, 1: 3, 3: 1}
DIR_DELTA = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}

def get_ports(tile_type, rotation):
    options = TILE_PORTS.get(tile_type, [])
    if not options:
        return set()
    return options[rotation % len(options)]


# ═══════════════════════════════════════
# CAMERA
# ═══════════════════════════════════════
class Camera:
    def __init__(self, world_w, world_h, screen_w, screen_h):
        self.x = world_w / 2
        self.y = world_h / 2
        self.zoom = 1.00
        self.min_zoom = 0.06
        self.max_zoom = 3.0
        self.sw = screen_w
        self.sh = screen_h
        self.dragging = False
        self.drag_start = None
        self.drag_cam = None

    def world_to_screen(self, wx, wy):
        return ((wx - self.x) * self.zoom + self.sw / 2,
                (wy - self.y) * self.zoom + self.sh / 2)

    def screen_to_world(self, sx, sy):
        return ((sx - self.sw / 2) / self.zoom + self.x,
                (sy - self.sh / 2) / self.zoom + self.y)

    def get_visible_tiles(self, tile_size, cols, rows):
        lx, ty = self.screen_to_world(0, 0)
        rx, by = self.screen_to_world(self.sw, self.sh)
        c0 = max(0, int(lx / tile_size) - 1)
        c1 = min(cols, int(rx / tile_size) + 2)
        r0 = max(0, int(ty / tile_size) - 1)
        r1 = min(rows, int(by / tile_size) + 2)
        return c0, c1, r0, r1

    def get_lod(self):
        if self.zoom > 0.5:
            return 2  # HIGH
        if self.zoom > 0.2:
            return 1  # MEDIUM
        return 0      # LOW

    def zoom_at(self, mx, my, factor):
        wx, wy = self.screen_to_world(mx, my)
        self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))
        nwx, nwy = self.screen_to_world(mx, my)
        self.x -= (nwx - wx)
        self.y -= (nwy - wy)

    def start_drag(self, mx, my):
        self.dragging = True
        self.drag_start = (mx, my)
        self.drag_cam = (self.x, self.y)

    def do_drag(self, mx, my):
        if not self.dragging:
            return
        dx = (mx - self.drag_start[0]) / self.zoom
        dy = (my - self.drag_start[1]) / self.zoom
        self.x = self.drag_cam[0] - dx
        self.y = self.drag_cam[1] - dy

    def stop_drag(self):
        self.dragging = False

    def center_on(self, wx, wy, lerp_t=0.08):
        self.x += (wx - self.x) * lerp_t
        self.y += (wy - self.y) * lerp_t


# ═══════════════════════════════════════
# A* PATHFINDING
# ═══════════════════════════════════════
def astar(grid, start, goal):
    """A* on road network. Returns (path, explored) or (None, explored)."""
    if start == goal:
        return [start], set()
    open_set = [(0, 0, start)]
    came_from = {}
    g_score = {start: 0}
    explored = set()
    counter = 1

    while open_set:
        _, _, current = heapq.heappop(open_set)
        if current in explored:
            continue
        explored.add(current)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path, explored

        c, r = current
        tile = grid.get(c, r)
        if tile is None or tile.type == EMPTY:
            continue
        ports = get_ports(tile.type, tile.rotation)
        for d in ports:
            dc, dr = DIR_DELTA[d]
            nc, nr = c + dc, r + dr
            nb = grid.get(nc, nr)
            if nb is None or nb.type == EMPTY:
                continue
            if OPPOSITE[d] not in get_ports(nb.type, nb.rotation):
                continue
            ng = g_score[current] + 1
            if ng < g_score.get((nc, nr), 1e9):
                came_from[(nc, nr)] = current
                g_score[(nc, nr)] = ng
                f = ng + abs(nc - goal[0]) + abs(nr - goal[1])
                heapq.heappush(open_set, (f, counter, (nc, nr)))
                counter += 1
    return None, explored


# ═══════════════════════════════════════
# BÉZIER WORLD PATH BUILDER
# ═══════════════════════════════════════
def _bez(p0, p1, p2, steps=12):
    pts = []
    for i in range(steps + 1):
        t = i / steps; u = 1 - t
        pts.append((u*u*p0[0]+2*u*t*p1[0]+t*t*p2[0],
                    u*u*p0[1]+2*u*t*p1[1]+t*t*p2[1]))
    return pts

def build_world_path(grid, tile_path, tile_size):
    """Convert A* tile path into smooth world-space Bézier points."""
    if not tile_path:
        return []
    T = tile_size
    if len(tile_path) == 1:
        c, r = tile_path[0]
        return [((c + 0.5) * T, (r + 0.5) * T)]

    world_pts = []
    for i in range(len(tile_path)):
        c, r = tile_path[i]
        cx, cy = c * T + T // 2, r * T + T // 2
        pm = {0: (c*T + T//2, r*T),
              1: (c*T + T,     r*T + T//2),
              2: (c*T + T//2,  r*T + T),
              3: (c*T,         r*T + T//2)}

        # Determine entry/exit directions
        entry_d = exit_d = None
        if i > 0:
            pc, pr = tile_path[i - 1]
            for d, (ddx, ddy) in DIR_DELTA.items():
                if c + ddx == pc and r + ddy == pr:
                    entry_d = d; break
        if i < len(tile_path) - 1:
            nc, nr = tile_path[i + 1]
            for d, (ddx, ddy) in DIR_DELTA.items():
                if c + ddx == nc and r + ddy == nr:
                    exit_d = d; break

        if entry_d is not None and exit_d is not None:
            sp, ep = pm[entry_d], pm[exit_d]
            if OPPOSITE.get(entry_d) == exit_d:
                # Straight through
                if not world_pts:
                    world_pts.append(sp)
                world_pts.append(ep)
            else:
                # Curve through center
                curve = _bez(sp, (cx, cy), ep, 14)
                if world_pts:
                    world_pts.extend(curve[1:])
                else:
                    world_pts.extend(curve)
        elif entry_d is None and exit_d is not None:
            # First tile: center to exit
            world_pts.append((cx, cy))
            world_pts.append(pm[exit_d])
        elif entry_d is not None and exit_d is None:
            # Last tile: entry to center
            if not world_pts:
                world_pts.append(pm[entry_d])
            world_pts.append((cx, cy))
        else:
            world_pts.append((cx, cy))

    return world_pts


# ═══════════════════════════════════════
# CAR (follows world-space Bézier path)
# ═══════════════════════════════════════
class Car:
    def __init__(self):
        self.world_pts = []   # smooth world-space polyline
        self.seg_idx = 0      # current segment index
        self.seg_prog = 0.0   # 0-1 progress along segment
        self.speed = 3.0      # tiles per second
        self.active = False
        self.finished = False
        self.angle = 0.0
        self.trail = []       # list of (wx, wy) for trail
        self.sprite_cache = {}

    def start(self, world_pts):
        self.world_pts = list(world_pts)
        self.seg_idx = 0
        self.seg_prog = 0.0
        self.active = True
        self.finished = False
        self.trail = []
        if len(world_pts) >= 2:
            dx = world_pts[1][0] - world_pts[0][0]
            dy = world_pts[1][1] - world_pts[0][1]
            self.angle = math.atan2(dy, dx)

    def reset(self):
        self.world_pts = []
        self.seg_idx = 0
        self.seg_prog = 0.0
        self.active = False
        self.finished = False
        self.trail = []

    def update(self, dt, tile_size):
        if not self.active or self.finished or len(self.world_pts) < 2:
            return
        px_per_sec = self.speed * tile_size
        dist = px_per_sec * dt
        # Record trail position
        old_pos = self.get_world_pos()
        while dist > 0 and self.seg_idx < len(self.world_pts) - 1:
            p1 = self.world_pts[self.seg_idx]
            p2 = self.world_pts[self.seg_idx + 1]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 0.001:
                self.seg_idx += 1
                self.seg_prog = 0.0
                continue
            remaining = seg_len * (1.0 - self.seg_prog)
            if dist >= remaining:
                dist -= remaining
                self.seg_idx += 1
                self.seg_prog = 0.0
            else:
                self.seg_prog += dist / seg_len
                dist = 0
        if self.seg_idx >= len(self.world_pts) - 1:
            self.finished = True
        # Update angle
        if self.seg_idx < len(self.world_pts) - 1:
            p1 = self.world_pts[self.seg_idx]
            p2 = self.world_pts[self.seg_idx + 1]
            self.angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        # Trail
        new_pos = self.get_world_pos()
        self.trail.append(new_pos)
        if len(self.trail) > 600:
            self.trail.pop(0)

    def get_world_pos(self):
        if not self.world_pts:
            return (0, 0)
        if self.seg_idx >= len(self.world_pts) - 1:
            return self.world_pts[-1]
        p1 = self.world_pts[self.seg_idx]
        p2 = self.world_pts[self.seg_idx + 1]
        t = min(self.seg_prog, 1.0)
        return (p1[0] + (p2[0] - p1[0]) * t,
                p1[1] + (p2[1] - p1[1]) * t)

    def change_speed(self, delta):
        self.speed = max(0.5, min(20.0, self.speed + delta))

    @staticmethod
    def create_sprite(size=40):
        """Draw a top-down car using Pygame primitives."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        bw = int(size * 0.42)
        bh = int(size * 0.72)
        bx = (size - bw) // 2
        by = (size - bh) // 2
        pygame.draw.rect(surf, (255, 175, 40), (bx, by, bw, bh), border_radius=5)
        cw, ch = int(bw * 0.72), int(bh * 0.32)
        cx2 = (size - cw) // 2
        cy2 = by + int(bh * 0.30)
        pygame.draw.rect(surf, (200, 140, 30), (cx2, cy2, cw, ch), border_radius=3)
        ww, wh = int(bw * 0.60), int(bh * 0.14)
        wx2 = (size - ww) // 2
        wy2 = by + int(bh * 0.18)
        pygame.draw.rect(surf, (100, 160, 220), (wx2, wy2, ww, wh), border_radius=2)
        ry = by + int(bh * 0.68)
        pygame.draw.rect(surf, (80, 130, 180), (wx2, ry, ww, int(wh * 0.8)), border_radius=2)
        whl_w, whl_h = max(3, size // 10), max(5, size // 7)
        for wy3 in [by + 3, by + bh - whl_h - 3]:
            pygame.draw.rect(surf, (35, 35, 35), (bx - whl_w + 2, wy3, whl_w, whl_h), border_radius=1)
            pygame.draw.rect(surf, (35, 35, 35), (bx + bw - 2, wy3, whl_w, whl_h), border_radius=1)
        for hx in [bx + 3, bx + bw - 4]:
            pygame.draw.circle(surf, (255, 255, 210), (hx, by + 3), 2)
        for hx in [bx + 3, bx + bw - 4]:
            pygame.draw.circle(surf, (255, 40, 40), (hx, by + bh - 3), 2)
        return surf

    def draw(self, screen, camera):
        if not self.world_pts:
            return
        wx, wy = self.get_world_pos()
        sx, sy = camera.world_to_screen(wx, wy)
        car_size = max(8, int(36 * camera.zoom))
        deg = -math.degrees(self.angle) - 90
        key = (car_size, int(deg) % 360)
        if key not in self.sprite_cache:
            base = Car.create_sprite(car_size)
            self.sprite_cache[key] = pygame.transform.rotate(base, deg)
            if len(self.sprite_cache) > 400:
                self.sprite_cache.clear()
        img = self.sprite_cache[key]
        rect = img.get_rect(center=(int(sx), int(sy)))
        screen.blit(img, rect)


# ═══════════════════════════════════════
# TILE CACHE
# ═══════════════════════════════════════
class TileCache:
    """Pre-renders tiles to surfaces for fast blitting."""
    def __init__(self, tile_size, draw_funcs):
        self.ts = tile_size
        self.draw_funcs = draw_funcs  # dict of draw functions
        self.high = {}
        self.medium = {}
        self.low_colors = {EMPTY: (16, 20, 30), STRAIGHT: (28, 33, 50),
                           CURVE: (28, 33, 50), TJUNCTION: (32, 38, 56),
                           CROSS: (36, 42, 60)}

    def build(self, grass_color, road_color, sidewalk_color):
        T = self.ts
        MG = (T - 34) // 2
        RW = 34
        # HIGH quality: use existing draw functions
        for tt in [STRAIGHT, CURVE, TJUNCTION, CROSS]:
            rots = len(TILE_PORTS[tt])
            for rot in range(rots):
                s = pygame.Surface((T, T))
                s.fill(grass_color)
                self.draw_funcs[tt](s, 0, 0, tt, rot)
                self.high[(tt, rot)] = s

        # MEDIUM quality: simple rects
        for tt in [STRAIGHT, CURVE, TJUNCTION, CROSS]:
            rots = len(TILE_PORTS[tt])
            for rot in range(rots):
                s = pygame.Surface((T, T))
                s.fill(grass_color)
                ports = get_ports(tt, rot)
                # Center
                pygame.draw.rect(s, road_color, (MG, MG, RW, RW))
                for p in ports:
                    if p == 0:
                        pygame.draw.rect(s, road_color, (MG, 0, RW, T // 2))
                    elif p == 1:
                        pygame.draw.rect(s, road_color, (T // 2, MG, T // 2, RW))
                    elif p == 2:
                        pygame.draw.rect(s, road_color, (MG, T // 2, RW, T // 2))
                    elif p == 3:
                        pygame.draw.rect(s, road_color, (0, MG, T // 2, RW))
                # Sidewalk on closed sides
                closed = {0, 1, 2, 3} - ports
                for d in closed:
                    if d == 0:
                        pygame.draw.rect(s, sidewalk_color, (MG, 0, RW, 4))
                    elif d == 2:
                        pygame.draw.rect(s, sidewalk_color, (MG, T - 4, RW, 4))
                    elif d == 3:
                        pygame.draw.rect(s, sidewalk_color, (0, MG, 4, RW))
                    elif d == 1:
                        pygame.draw.rect(s, sidewalk_color, (T - 4, MG, 4, RW))
                self.medium[(tt, rot)] = s

        # Empty
        e = pygame.Surface((T, T))
        e.fill(grass_color)
        self.high[(EMPTY, 0)] = e
        self.medium[(EMPTY, 0)] = e

    def get(self, tile_type, rotation, lod):
        key = (tile_type, rotation)
        if tile_type == EMPTY:
            key = (EMPTY, 0)
        if lod >= 2:
            return self.high.get(key)
        elif lod >= 1:
            return self.medium.get(key)
        return self.medium.get(key)
