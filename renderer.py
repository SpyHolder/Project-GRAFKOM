"""
Seruni Map — Renderer
Bézier road drawing, minimap, and HUD overlay functions.
"""
import math
import pygame
from config import (EMPTY, STRAIGHT, CURVE, TJUNCTION, CROSS,
                    get_ports, T, RW, SW, MG, DASH_ON, DASH_OFF,
                    C_GRASS, C_SW, C_ROAD, C_DASH, C_PATH)
from assets import ASSET_NONE, ASSET_GEROBAK, ASSET_BASECAMP, ASSET_RUMAH, ASSET_POHON


# ═══════════════════════════════════════
# BÉZIER HELPERS
# ═══════════════════════════════════════
def _bquad(p0, p1, p2, s=24):
    pts = []
    for i in range(s + 1):
        t = i / s; u = 1 - t
        pts.append((u*u*p0[0]+2*u*t*p1[0]+t*t*p2[0],
                     u*u*p0[1]+2*u*t*p1[1]+t*t*p2[1]))
    return pts

def _offcurve(pts, off, side="left"):
    r = []; n = len(pts)
    for i in range(n):
        if i == 0: dx, dy = pts[1][0]-pts[0][0], pts[1][1]-pts[0][1]
        elif i == n-1: dx, dy = pts[-1][0]-pts[-2][0], pts[-1][1]-pts[-2][1]
        else: dx, dy = pts[i+1][0]-pts[i-1][0], pts[i+1][1]-pts[i-1][1]
        l = math.hypot(dx, dy) or 1; nx, ny = -dy/l, dx/l
        if side == "right": nx, ny = -nx, -ny
        r.append((pts[i][0]+nx*off, pts[i][1]+ny*off))
    return r

def _fband(s, cp, hw, col):
    if len(cp) < 2: return
    L = _offcurve(cp, hw, "left"); R = _offcurve(cp, hw, "right")
    p = L + list(reversed(R))
    if len(p) >= 3:
        pygame.draw.polygon(s, col, [(int(a), int(b)) for a, b in p])

def _dashline(s, x1, y1, x2, y2, vert=True):
    ln = (y2-y1) if vert else (x2-x1); pos = 0; dr = True
    while pos < ln:
        sg = min(DASH_ON if dr else DASH_OFF, ln-pos)
        if dr:
            if vert: pygame.draw.line(s, C_DASH, (x1, y1+pos), (x1, y1+pos+sg), 1)
            else: pygame.draw.line(s, C_DASH, (x1+pos, y1), (x1+pos+sg, y1), 1)
        pos += sg; dr = not dr

def _bdash(s, pts, col, da=10, ga=8):
    acc = 0; dr = True
    for i in range(len(pts)-1):
        ax, ay = pts[i]; bx, by = pts[i+1]
        sg = math.hypot(bx-ax, by-ay)
        if sg < .001: continue
        dx, dy = (bx-ax)/sg, (by-ay)/sg; t = 0
        while t < sg:
            p = da if dr else ga; rm = min(p-acc, sg-t)
            if dr:
                sx2, sy2 = ax+dx*t, ay+dy*t
                ex2, ey2 = ax+dx*(t+rm), ay+dy*(t+rm)
                pygame.draw.line(s, col, (int(sx2), int(sy2)), (int(ex2), int(ey2)), 1)
            t += rm; acc += rm
            if acc >= p: acc = 0; dr = not dr


# ═══════════════════════════════════════
# TILE DRAWING (for TileCache)
# ═══════════════════════════════════════
def _dsw(s, x, y, tt, rot):
    ports = get_ports(tt, rot); closed = {0,1,2,3} - ports
    for d in closed:
        if d == 0: pygame.draw.rect(s, C_SW, (x+MG, y, RW, SW))
        elif d == 2: pygame.draw.rect(s, C_SW, (x+MG, y+T-SW, RW, SW))
        elif d == 3: pygame.draw.rect(s, C_SW, (x, y+MG, SW, RW))
        elif d == 1: pygame.draw.rect(s, C_SW, (x+T-SW, y+MG, SW, RW))

def _dstr(s, x, y, rot):
    if rot == 0:
        pygame.draw.rect(s, C_SW, (x, y, MG, T))
        pygame.draw.rect(s, C_SW, (x+T-MG, y, MG, T))
        pygame.draw.rect(s, C_ROAD, (x+MG, y, RW, T))
        _dashline(s, x+T//2, y+4, x+T//2, y+T-4, True)
    else:
        pygame.draw.rect(s, C_SW, (x, y, T, MG))
        pygame.draw.rect(s, C_SW, (x, y+T-MG, T, MG))
        pygame.draw.rect(s, C_ROAD, (x, y+MG, T, RW))
        _dashline(s, x+4, y+T//2, x+T-4, y+T//2, False)

def _dcurv(s, x, y, rot):
    cx, cy = x+T//2, y+T//2
    pm = {0:(x+T//2, y), 1:(x+T, y+T//2), 2:(x+T//2, y+T), 3:(x, y+T//2)}
    pp = {0:(0,1), 1:(1,2), 2:(2,3), 3:(3,0)}
    pf, pt = pp[rot]; cc = _bquad(pm[pf], (cx, cy), pm[pt], 32)
    _dsw(s, x, y, CURVE, rot); _fband(s, cc, RW//2, C_ROAD); _bdash(s, cc, C_DASH)

def _dtjunc(s, x, y, rot):
    ports = list(get_ports(TJUNCTION, rot)); ctr = (x+T//2, y+T//2)
    pm = {0:(x+T//2, y), 1:(x+T, y+T//2), 2:(x+T//2, y+T), 3:(x, y+T//2)}
    _dsw(s, x, y, TJUNCTION, rot)
    for i, p1 in enumerate(ports):
        for p2 in ports[i+1:]:
            c2 = _bquad(pm[p1], ctr, pm[p2], 24)
            _fband(s, c2, RW//2, C_ROAD); _bdash(s, c2, C_DASH)
    pygame.draw.circle(s, C_ROAD, (int(ctr[0]), int(ctr[1])), RW//3+1)

def _dcross(s, x, y, rot=0):
    ctr = (x+T//2, y+T//2)
    pm = {0:(x+T//2, y), 1:(x+T, y+T//2), 2:(x+T//2, y+T), 3:(x, y+T//2)}
    for p1 in range(4):
        for p2 in range(p1+1, 4):
            c2 = _bquad(pm[p1], ctr, pm[p2], 24)
            _fband(s, c2, RW//2, C_ROAD)
    pygame.draw.circle(s, C_ROAD, (int(ctr[0]), int(ctr[1])), RW//3+2)
    cr = max(2, MG-4)
    for px, py in [(x, y), (x+T, y), (x, y+T), (x+T, y+T)]:
        pygame.draw.circle(s, C_SW, (px, py), cr)
    for p1, p2 in [(0, 2), (1, 3)]:
        c2 = _bquad(pm[p1], ctr, pm[p2], 24); _bdash(s, c2, C_DASH)

def draw_tile(s, x, y, tt, rot):
    """Draw a single road tile (dispatches to type-specific function)."""
    if tt == STRAIGHT: _dstr(s, x, y, rot)
    elif tt == CURVE: _dcurv(s, x, y, rot)
    elif tt == TJUNCTION: _dtjunc(s, x, y, rot)
    elif tt == CROSS: _dcross(s, x, y, rot)


# ═══════════════════════════════════════
# MINIMAP
# ═══════════════════════════════════════
def build_minimap(grid, asset_grid=None, path=None, sz=180):
    cols, rows = grid.cols, grid.rows
    sc = sz / max(cols, rows)
    s = pygame.Surface((int(cols*sc)+2, int(rows*sc)+2))
    s.fill((20, 24, 35))
    ac = {ASSET_GEROBAK: (180,130,40), ASSET_BASECAMP: (200,150,50),
          ASSET_RUMAH: (50,55,70), ASSET_POHON: (18,38,22)}
    for r in range(rows):
        for c in range(cols):
            px, py = int(c*sc), int(r*sc)
            ps = max(1, int(sc))
            if grid.cells[r][c].type != EMPTY:
                pygame.draw.rect(s, (50,60,90), (px, py, ps, ps))
            elif asset_grid:
                at = asset_grid.cells[r][c].type
                if at != ASSET_NONE:
                    pygame.draw.rect(s, ac.get(at, (20,24,35)), (px, py, ps, ps))
    if path:
        for c2, r2 in path:
            pygame.draw.rect(s, C_PATH,
                (int(c2*sc), int(r2*sc), max(1, int(sc)), max(1, int(sc))))
    return s, sc
