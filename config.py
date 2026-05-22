"""
Seruni Map — Shared Configuration
Tile types, ports, directions, screen settings, and color palette.
"""

# ── Tile Types ──
EMPTY = 0
STRAIGHT = 1
CURVE = 2
TJUNCTION = 3
CROSS = 4

# ── Port Definitions (direction sets per rotation) ──
TILE_PORTS = {
    STRAIGHT: [{0, 2}, {1, 3}],
    CURVE: [{0, 1}, {1, 2}, {2, 3}, {3, 0}],
    TJUNCTION: [{0, 1, 2}, {1, 2, 3}, {2, 3, 0}, {3, 0, 1}],
    CROSS: [{0, 1, 2, 3}],
}
OPPOSITE = {0: 2, 2: 0, 1: 3, 3: 1}
DIR_DELTA = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}

def get_ports(tile_type, rotation):
    """Return the set of open port directions for a tile type and rotation."""
    options = TILE_PORTS.get(tile_type, [])
    if not options:
        return set()
    return options[rotation % len(options)]

# ── Screen & Grid ──
W, H = 1280, 800
T = 80
RW = 34
SW = 6
MG = (T - RW) // 2
GCOLS, GROWS = 80, 80
DASH_ON, DASH_OFF = 10, 8
SEED = None

# ── Color Palette (Dark Theme) ──
C_BG = (13, 15, 23)
C_GRASS = (16, 20, 30)
C_SW = (35, 40, 58)
C_ROAD = (28, 33, 50)
C_DASH = (50, 58, 88)
C_NODE = (80, 100, 160)
C_PATH = (0, 210, 110)
C_EXPLORED = (40, 80, 140)
C_START = (0, 220, 80)
C_END = (220, 50, 50)
C_HOVER = (255, 220, 60)
C_UI = (100, 130, 200)
C_UIK = (70, 90, 140)
