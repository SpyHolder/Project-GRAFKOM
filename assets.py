"""
Seruni Map — Asset System
Gerobak, Basecamp, Rumah, Pohon: placement + Pygame rendering.
"""
import random, math, pygame
from config import DIR_DELTA

# ── Asset types ──
ASSET_NONE = 0
ASSET_GEROBAK = 1
ASSET_BASECAMP = 2
ASSET_RUMAH = 3
ASSET_POHON = 4
ASSET_NAMES = {ASSET_GEROBAK:"Gerobak", ASSET_BASECAMP:"Basecamp",
               ASSET_RUMAH:"Rumah", ASSET_POHON:"Pohon"}


class AssetCell:
    __slots__ = ('type','rotation','variant')
    def __init__(self):
        self.type = ASSET_NONE
        self.rotation = 0
        self.variant = 0

class AssetGrid:
    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.cells = [[AssetCell() for _ in range(cols)] for _ in range(rows)]
    def get(self, c, r):
        if 0<=c<self.cols and 0<=r<self.rows: return self.cells[r][c]
        return None
    def set_asset(self, c, r, atype, rot=0, var=0):
        cl = self.cells[r][c]; cl.type=atype; cl.rotation=rot; cl.variant=var


# ═══════════════════════════════════════
# PLACEMENT
# ═══════════════════════════════════════
def place_assets(road_grid, seed=None):
    rng = random.Random(seed)
    cols, rows = road_grid.cols, road_grid.rows
    ag = AssetGrid(cols, rows)

    # Find roadside empty tiles
    roadside, non_roadside = [], []
    for r in range(rows):
        for c in range(cols):
            if road_grid.is_road(c, r): continue
            dirs = [d for d,(dc,dr) in DIR_DELTA.items() if road_grid.is_road(c+dc, r+dr)]
            if dirs: roadside.append((c, r, dirs))
            else: non_roadside.append((c, r))

    rng.shuffle(roadside)

    # Phase 1: Unique basecamp — prefer near center with good access
    cx, cy = cols//2, rows//2
    roadside.sort(key=lambda x: (-len(x[2]), abs(x[0]-cx)+abs(x[1]-cy)))
    for i,(c,r,dirs) in enumerate(roadside):
        ag.set_asset(c, r, ASSET_BASECAMP, rot=dirs[0], var=0)
        roadside.pop(i); break

    # Phase 2: Place exactly 5-6 gerobaks, spread out
    rng.shuffle(roadside)
    n_gerobak = rng.randint(5, 10)
    placed_gerobak = []
    remaining = []
    for c,r,dirs in roadside:
        if len(placed_gerobak) < n_gerobak:
            # Ensure minimum distance from other gerobaks
            too_close = any(abs(c-gc)+abs(r-gr) < max(cols,rows)//8
                           for gc,gr in placed_gerobak)
            if not too_close:
                ag.set_asset(c, r, ASSET_GEROBAK, rot=rng.choice(dirs), var=rng.randint(0,3))
                placed_gerobak.append((c,r))
                continue
        remaining.append((c, r, dirs))
    # If not enough placed (tiles too clustered), force remaining
    for c,r,dirs in remaining[:]:
        if len(placed_gerobak) >= n_gerobak: break
        ag.set_asset(c, r, ASSET_GEROBAK, rot=rng.choice(dirs), var=rng.randint(0,3))
        placed_gerobak.append((c,r))
        remaining.remove((c,r,dirs))

    # Phase 3: Remaining roadside → rumah 40%, pohon 60%
    for c,r,dirs in remaining:
        if rng.random() < 0.40:
            ag.set_asset(c, r, ASSET_RUMAH, rot=rng.choice(dirs), var=rng.randint(0,3))
        else:
            ag.set_asset(c, r, ASSET_POHON, rot=0, var=rng.randint(0,5))

    # Phase 3: Randomly scatter trees on remaining empty tiles (~60%)
    rng.shuffle(non_roadside)
    tree_chance = 0.6
    for c,r in non_roadside:
        if rng.random() < tree_chance:
            ag.set_asset(c, r, ASSET_POHON, var=rng.randint(0,5))

    return ag


# ═══════════════════════════════════════
# DRAWING — Pygame Primitives (top-down)
# ═══════════════════════════════════════
def _rot_surf(surf, rotation):
    """Rotate surface: 0=N(default), 1=E(-90°), 2=S(180°), 3=W(90°)."""
    if rotation == 0: return surf
    deg = {1: -90, 2: 180, 3: 90}[rotation]
    return pygame.transform.rotate(surf, deg)


def draw_gerobak(size=80):
    """Top-down coffee cart: warm orange body, wheels, canopy."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size//2, size//2
    # Shadow
    pygame.draw.ellipse(s, (10,12,18), (cx-20, cy-16, 40, 36))
    # Cart body
    bw, bh = int(size*0.38), int(size*0.48)
    bx, by = cx-bw//2, cy-bh//2+2
    pygame.draw.rect(s, (190,130,35), (bx, by, bw, bh), border_radius=4)
    pygame.draw.rect(s, (210,150,45), (bx+2, by+2, bw-4, bh-4), border_radius=3)
    # Canopy/umbrella
    pygame.draw.ellipse(s, (220,165,55,200), (cx-bw//2-5, by-8, bw+10, int(bh*0.45)))
    pygame.draw.ellipse(s, (235,180,65,160), (cx-bw//2-2, by-5, bw+4, int(bh*0.38)))
    # Wheels
    for wy in [by+bh-3, by+bh+2]:
        pygame.draw.circle(s, (40,40,40), (bx+2, wy), 4)
        pygame.draw.circle(s, (40,40,40), (bx+bw-2, wy), 4)
        pygame.draw.circle(s, (60,60,60), (bx+2, wy), 2)
        pygame.draw.circle(s, (60,60,60), (bx+bw-2, wy), 2)
    # Handle
    pygame.draw.line(s, (160,110,30), (cx, by+bh), (cx, by+bh+10), 2)
    pygame.draw.line(s, (160,110,30), (cx-6, by+bh+10), (cx+6, by+bh+10), 2)
    # Coffee cup detail
    cw, ch = 8, 6
    pygame.draw.rect(s, (240,200,140), (cx-cw//2, cy-ch//2, cw, ch), border_radius=1)
    pygame.draw.arc(s, (200,160,100), (cx+cw//2-1, cy-ch//2-1, 5, ch), -1.5, 1.5, 1)
    return s


def draw_basecamp(size=80):
    """Top-down Seruni cafe: large building, brown roof, coffee sign."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size//2, size//2
    # Shadow
    pygame.draw.rect(s, (10,12,18), (8, 10, size-16, size-16), border_radius=4)
    # Building base
    bw, bh = int(size*0.75), int(size*0.72)
    bx, by = cx-bw//2, cy-bh//2
    pygame.draw.rect(s, (60,45,25), (bx, by, bw, bh), border_radius=3)
    # Roof
    pygame.draw.rect(s, (80,55,30), (bx+2, by+2, bw-4, bh-4), border_radius=2)
    # Roof ridge line
    pygame.draw.line(s, (100,70,35), (cx, by+4), (cx, by+bh-4), 2)
    # Walls visible under roof edges
    pygame.draw.rect(s, (50,38,22), (bx, by, bw, 4))
    pygame.draw.rect(s, (50,38,22), (bx, by+bh-4, bw, 4))
    # Door (front, top)
    dw, dh = 12, 10
    pygame.draw.rect(s, (140,100,50), (cx-dw//2, by-2, dw, dh), border_radius=2)
    pygame.draw.rect(s, (170,120,60), (cx-dw//2+2, by, dw-4, dh-3), border_radius=1)
    # Windows
    wn_s = 8
    for wx in [bx+8, bx+bw-8-wn_s]:
        pygame.draw.rect(s, (90,120,160,150), (wx, cy-wn_s//2, wn_s, wn_s), border_radius=1)
        pygame.draw.line(s, (60,45,25), (wx+wn_s//2, cy-wn_s//2), (wx+wn_s//2, cy+wn_s//2), 1)
    # Coffee sign (☕ circle emblem)
    pygame.draw.circle(s, (200,150,50), (cx, cy+2), 10)
    pygame.draw.circle(s, (80,55,30), (cx, cy+2), 8)
    # Cup in sign
    pygame.draw.rect(s, (220,180,100), (cx-4, cy, 8, 6), border_radius=1)
    pygame.draw.arc(s, (200,160,80), (cx+3, cy-2, 4, 5), -1.5, 1.5, 1)
    # Awning stripes at front
    for i in range(4):
        c1 = (200,145,45) if i%2==0 else (220,165,60)
        pygame.draw.rect(s, c1, (bx+4+i*((bw-8)//4), by-5, (bw-8)//4, 5))
    return s


def draw_rumah(size=80):
    """Top-down house: gray walls, dark blue roof, windows."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size//2, size//2
    # Shadow
    pygame.draw.rect(s, (10,12,18), (12, 14, size-24, size-24), border_radius=3)
    # Building
    bw, bh = int(size*0.55), int(size*0.58)
    bx, by = cx-bw//2, cy-bh//2
    pygame.draw.rect(s, (42,48,62), (bx, by, bw, bh), border_radius=2)
    # Roof (dark blue)
    pygame.draw.rect(s, (30,38,65), (bx+2, by+2, bw-4, bh-4), border_radius=2)
    # Roof ridge
    pygame.draw.line(s, (40,50,80), (cx, by+3), (cx, by+bh-3), 2)
    # Door
    dw, dh = 8, 8
    pygame.draw.rect(s, (70,60,50), (cx-dw//2, by-1, dw, dh), border_radius=2)
    # Windows
    wn = 6
    pygame.draw.rect(s, (60,80,120,120), (bx+5, cy-wn//2, wn, wn), border_radius=1)
    pygame.draw.rect(s, (60,80,120,120), (bx+bw-5-wn, cy-wn//2, wn, wn), border_radius=1)
    # Window cross lines
    for wx in [bx+5, bx+bw-5-wn]:
        pygame.draw.line(s, (30,38,65), (wx+wn//2, cy-wn//2), (wx+wn//2, cy+wn//2), 1)
        pygame.draw.line(s, (30,38,65), (wx, cy), (wx+wn, cy), 1)
    return s


def draw_pohon(size=80, variant=0):
    """Top-down tree with visible trunk, roots, and layered canopy."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size//2, size//2
    rng = random.Random(variant * 137 + 42)
    base_g = 35 + rng.randint(-8, 8)
    canopy_r = 14 + rng.randint(-3, 5)
    # Shadow
    pygame.draw.circle(s, (8,10,16), (cx+3, cy+3), canopy_r+4)
    # Trunk (prominent, visible extending from canopy)
    trunk_w = max(4, canopy_r // 2)
    trunk_h = max(8, canopy_r)
    trunk_col = (55+rng.randint(-10,10), 38+rng.randint(-5,5), 22)
    trunk_dark = (40+rng.randint(-8,8), 28+rng.randint(-4,4), 16)
    # Main trunk
    tx, ty = cx - trunk_w//2, cy - trunk_h//4
    pygame.draw.rect(s, trunk_col, (tx, ty, trunk_w, trunk_h), border_radius=2)
    # Trunk bark texture line
    pygame.draw.line(s, trunk_dark, (cx, ty+2), (cx, ty+trunk_h-2), 1)
    # Root branches extending from trunk base
    root_y = ty + trunk_h - 2
    for rx, ry_off in [(-trunk_w, 2), (trunk_w, 3), (-trunk_w//2, 4)]:
        pygame.draw.line(s, trunk_dark, (cx, root_y), (cx+rx, root_y+ry_off), 2)
    # Canopy layers (3-4 overlapping circles)
    offsets = [(0, -2), (rng.randint(-4,4), rng.randint(-4,2)),
              (rng.randint(-3,3), rng.randint(-3,3))]
    if variant > 2:
        offsets.append((rng.randint(-3,3), rng.randint(-2,2)))
    # Dark base layer
    for ox, oy in offsets:
        g = base_g + rng.randint(-8, -2)
        r_adj = canopy_r + rng.randint(0, 3)
        pygame.draw.circle(s, (12, g, 14), (cx+ox, cy+oy-1), r_adj)
    # Main canopy
    for ox, oy in offsets:
        g = base_g + rng.randint(-3, 5)
        r_adj = canopy_r + rng.randint(-2, 1)
        pygame.draw.circle(s, (15, g, 18), (cx+ox, cy+oy-2), r_adj)
    # Highlight spots
    pygame.draw.circle(s, (22, base_g+15, 25), (cx-3, cy-4), canopy_r//2)
    pygame.draw.circle(s, (25, base_g+18, 28, 120), (cx-5, cy-5), canopy_r//3)
    return s


# ═══════════════════════════════════════
# ASSET CACHE
# ═══════════════════════════════════════
class AssetCache:
    def __init__(self, tile_size):
        self.ts = tile_size
        self.surfs = {}

    def build(self):
        T = self.ts
        # Gerobak: 4 rotations
        base = draw_gerobak(T)
        for rot in range(4):
            self.surfs[(ASSET_GEROBAK, rot, 0)] = _rot_surf(base, rot)
        # Basecamp: 4 rotations
        base = draw_basecamp(T)
        for rot in range(4):
            self.surfs[(ASSET_BASECAMP, rot, 0)] = _rot_surf(base, rot)
        # Rumah: 4 rotations
        base = draw_rumah(T)
        for rot in range(4):
            self.surfs[(ASSET_RUMAH, rot, 0)] = _rot_surf(base, rot)
        # Pohon: 6 variants (no rotation)
        for v in range(6):
            self.surfs[(ASSET_POHON, 0, v)] = draw_pohon(T, v)

    def get(self, atype, rot, var):
        if atype == ASSET_POHON:
            return self.surfs.get((ASSET_POHON, 0, var % 6))
        return self.surfs.get((atype, rot % 4, 0))
