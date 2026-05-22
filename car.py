"""
Seruni Map — Car
Top-down car following smooth world-space Bézier path.
"""
import math
import pygame


class Car:
    def __init__(self):
        self.world_pts = []
        self.seg_idx = 0
        self.seg_prog = 0.0
        self.speed = 3.0
        self.active = False
        self.finished = False
        self.angle = 0.0
        self.trail = []
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
        while dist > 0 and self.seg_idx < len(self.world_pts) - 1:
            p1 = self.world_pts[self.seg_idx]
            p2 = self.world_pts[self.seg_idx + 1]
            seg_len = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
            if seg_len < 0.001:
                self.seg_idx += 1; self.seg_prog = 0.0; continue
            remaining = seg_len * (1.0 - self.seg_prog)
            if dist >= remaining:
                dist -= remaining; self.seg_idx += 1; self.seg_prog = 0.0
            else:
                self.seg_prog += dist / seg_len; dist = 0
        if self.seg_idx >= len(self.world_pts) - 1:
            self.finished = True
        if self.seg_idx < len(self.world_pts) - 1:
            p1 = self.world_pts[self.seg_idx]
            p2 = self.world_pts[self.seg_idx + 1]
            self.angle = math.atan2(p2[1]-p1[1], p2[0]-p1[0])
        new_pos = self.get_world_pos()
        self.trail.append(new_pos)
        if len(self.trail) > 600: self.trail.pop(0)

    def get_world_pos(self):
        if not self.world_pts: return (0, 0)
        if self.seg_idx >= len(self.world_pts) - 1: return self.world_pts[-1]
        p1 = self.world_pts[self.seg_idx]
        p2 = self.world_pts[self.seg_idx + 1]
        t = min(self.seg_prog, 1.0)
        return (p1[0]+(p2[0]-p1[0])*t, p1[1]+(p2[1]-p1[1])*t)

    def change_speed(self, delta):
        self.speed = max(0.5, min(20.0, self.speed + delta))

    @staticmethod
    def create_sprite(size=40):
        """Draw a top-down car sprite using Pygame primitives."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        bw, bh = int(size*0.42), int(size*0.72)
        bx, by = (size-bw)//2, (size-bh)//2
        pygame.draw.rect(surf, (255,175,40), (bx, by, bw, bh), border_radius=5)
        cw, ch = int(bw*0.72), int(bh*0.32)
        pygame.draw.rect(surf, (200,140,30), ((size-cw)//2, by+int(bh*0.30), cw, ch), border_radius=3)
        ww, wh = int(bw*0.60), int(bh*0.14)
        wx2 = (size-ww)//2
        pygame.draw.rect(surf, (100,160,220), (wx2, by+int(bh*0.18), ww, wh), border_radius=2)
        pygame.draw.rect(surf, (80,130,180), (wx2, by+int(bh*0.68), ww, int(wh*0.8)), border_radius=2)
        whl_w, whl_h = max(3, size//10), max(5, size//7)
        for wy in [by+3, by+bh-whl_h-3]:
            pygame.draw.rect(surf, (35,35,35), (bx-whl_w+2, wy, whl_w, whl_h), border_radius=1)
            pygame.draw.rect(surf, (35,35,35), (bx+bw-2, wy, whl_w, whl_h), border_radius=1)
        for hx in [bx+3, bx+bw-4]:
            pygame.draw.circle(surf, (255,255,210), (hx, by+3), 2)
            pygame.draw.circle(surf, (255,40,40), (hx, by+bh-3), 2)
        return surf

    def draw(self, screen, camera):
        if not self.world_pts: return
        wx, wy = self.get_world_pos()
        sx, sy = camera.world_to_screen(wx, wy)
        car_size = max(8, int(36 * camera.zoom))
        deg = -math.degrees(self.angle) - 90
        key = (car_size, int(deg) % 360)
        if key not in self.sprite_cache:
            base = Car.create_sprite(car_size)
            self.sprite_cache[key] = pygame.transform.rotate(base, deg)
            if len(self.sprite_cache) > 400: self.sprite_cache.clear()
        img = self.sprite_cache[key]
        rect = img.get_rect(center=(int(sx), int(sy)))
        screen.blit(img, rect)
