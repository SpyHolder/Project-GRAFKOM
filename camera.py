"""
Seruni Map — Camera System
Viewport management, zoom-at-cursor, panning, LOD selection, and tile caching.
"""
import pygame
from config import (EMPTY, STRAIGHT, CURVE, TJUNCTION, CROSS,
                    TILE_PORTS, get_ports)


class Camera:
    def __init__(self, world_w, world_h, screen_w, screen_h):
        self.x = world_w / 2
        self.y = world_h / 2
        self.zoom = 0.35
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
        if self.zoom > 0.5: return 2   # HIGH
        if self.zoom > 0.2: return 1   # MEDIUM
        return 0                       # LOW

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
        if not self.dragging: return
        dx = (mx - self.drag_start[0]) / self.zoom
        dy = (my - self.drag_start[1]) / self.zoom
        self.x = self.drag_cam[0] - dx
        self.y = self.drag_cam[1] - dy

    def stop_drag(self):
        self.dragging = False

    def center_on(self, wx, wy, lerp_t=0.08):
        self.x += (wx - self.x) * lerp_t
        self.y += (wy - self.y) * lerp_t


class TileCache:
    """Pre-renders tiles to surfaces for fast blitting."""
    def __init__(self, tile_size, draw_funcs):
        self.ts = tile_size
        self.draw_funcs = draw_funcs
        self.high = {}
        self.medium = {}

    def build(self, grass_color, road_color, sidewalk_color):
        T2 = self.ts; MG2 = (T2 - 34) // 2; RW2 = 34
        for tt in [STRAIGHT, CURVE, TJUNCTION, CROSS]:
            for rot in range(len(TILE_PORTS[tt])):
                s = pygame.Surface((T2, T2)); s.fill(grass_color)
                self.draw_funcs[tt](s, 0, 0, tt, rot)
                self.high[(tt, rot)] = s

        for tt in [STRAIGHT, CURVE, TJUNCTION, CROSS]:
            for rot in range(len(TILE_PORTS[tt])):
                s = pygame.Surface((T2, T2)); s.fill(grass_color)
                ports = get_ports(tt, rot)
                pygame.draw.rect(s, road_color, (MG2, MG2, RW2, RW2))
                for p in ports:
                    if p == 0: pygame.draw.rect(s, road_color, (MG2, 0, RW2, T2//2))
                    elif p == 1: pygame.draw.rect(s, road_color, (T2//2, MG2, T2//2, RW2))
                    elif p == 2: pygame.draw.rect(s, road_color, (MG2, T2//2, RW2, T2//2))
                    elif p == 3: pygame.draw.rect(s, road_color, (0, MG2, T2//2, RW2))
                for d in ({0,1,2,3} - ports):
                    if d == 0: pygame.draw.rect(s, sidewalk_color, (MG2, 0, RW2, 4))
                    elif d == 2: pygame.draw.rect(s, sidewalk_color, (MG2, T2-4, RW2, 4))
                    elif d == 3: pygame.draw.rect(s, sidewalk_color, (0, MG2, 4, RW2))
                    elif d == 1: pygame.draw.rect(s, sidewalk_color, (T2-4, MG2, 4, RW2))
                self.medium[(tt, rot)] = s

        e = pygame.Surface((T2, T2)); e.fill(grass_color)
        self.high[(EMPTY, 0)] = e
        self.medium[(EMPTY, 0)] = e

    def get(self, tile_type, rotation, lod):
        key = (tile_type, rotation)
        if tile_type == EMPTY: key = (EMPTY, 0)
        if lod >= 2: return self.high.get(key)
        return self.medium.get(key)
