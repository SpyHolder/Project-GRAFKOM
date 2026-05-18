"""
Seruni Map — Corridor Snake Growth Generator
Produces winding, organic road networks with minimal intersections.
"""
import random
from collections import deque

# ── Tile constants ──
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


def _is_border(c, r, cols, rows):
    return c == 0 or c == cols - 1 or r == 0 or r == rows - 1


# ─────────────────────────────────────────
# GRID
# ─────────────────────────────────────────
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


# ─────────────────────────────────────────
# CORE HELPERS
# ─────────────────────────────────────────
def _tile_degree(grid, c, r):
    tile = grid.get(c, r)
    if tile is None or tile.type == EMPTY:
        return 0
    ports = get_ports(tile.type, tile.rotation)
    deg = 0
    for d in ports:
        dc, dr = DIR_DELTA[d]
        nb = grid.get(c + dc, r + dr)
        if nb and nb.type != EMPTY:
            if OPPOSITE[d] in get_ports(nb.type, nb.rotation):
                deg += 1
    return deg


def _neighbor_constraints(grid, c, r):
    constraints = {}
    for d, (dc, dr) in DIR_DELTA.items():
        nb = grid.get(c + dc, r + dr)
        if nb is None or nb.type == EMPTY:
            continue
        opp = OPPOSITE[d]
        nb_ports = get_ports(nb.type, nb.rotation)
        constraints[d] = opp in nb_ports
    return constraints


def _get_valid_options(grid, c, r):
    constraints = _neighbor_constraints(grid, c, r)
    valid = []
    for tile_type, rotations in TILE_PORTS.items():
        for rot, ports in enumerate(rotations):
            ok = True
            for d, must_open in constraints.items():
                if (d in ports) != must_open:
                    ok = False
                    break
            if ok:
                valid.append((tile_type, rot))
    return valid


def _get_connecting_options(grid, c, r):
    all_opts = _get_valid_options(grid, c, r)
    result = []
    for tile_type, rot in all_opts:
        ports = get_ports(tile_type, rot)
        for d in ports:
            dc, dr = DIR_DELTA[d]
            nb = grid.get(c + dc, r + dr)
            if nb and nb.type != EMPTY:
                if OPPOSITE[d] in get_ports(nb.type, nb.rotation):
                    result.append((tile_type, rot))
                    break
    return result


def _get_options_with_ports(grid, c, r, required_ports):
    return [(t, rot) for t, rot in _get_valid_options(grid, c, r)
            if required_ports.issubset(get_ports(t, rot))]


def _tile_degree_if_placed(grid, c, r, tile_type, rot):
    ports = get_ports(tile_type, rot)
    deg = 0
    for d in ports:
        dc, dr = DIR_DELTA[d]
        nb = grid.get(c + dc, r + dr)
        if nb and nb.type != EMPTY:
            if OPPOSITE[d] in get_ports(nb.type, nb.rotation):
                deg += 1
    return deg


def _upgrade_tile_port(grid, c, r, port):
    tile = grid.get(c, r)
    if tile is None or tile.type == EMPTY:
        return False
    cur_ports = get_ports(tile.type, tile.rotation)
    if port in cur_ports:
        return True
    needed = cur_ports | {port}
    for tile_type, rotations in TILE_PORTS.items():
        for rot, ports in enumerate(rotations):
            if not needed.issubset(ports):
                continue
            ok = True
            for ep in (ports - cur_ports):
                edc, edr = DIR_DELTA[ep]
                enb = grid.get(c + edc, r + edr)
                if enb and enb.type != EMPTY:
                    if OPPOSITE[ep] not in get_ports(enb.type, enb.rotation):
                        ok = False
                        break
            if ok:
                grid.set_tile(c, r, tile_type, rot)
                return True
    return False


def _flood_fill(grid, start_c, start_r):
    if not grid.is_road(start_c, start_r):
        return set()
    visited = {(start_c, start_r)}
    queue = deque([(start_c, start_r)])
    while queue:
        cx, cy = queue.popleft()
        tile = grid.get(cx, cy)
        for d in get_ports(tile.type, tile.rotation):
            dc, dr = DIR_DELTA[d]
            nc, nr = cx + dc, cy + dr
            if (nc, nr) in visited:
                continue
            nb = grid.get(nc, nr)
            if nb and nb.type != EMPTY:
                if OPPOSITE[d] in get_ports(nb.type, nb.rotation):
                    visited.add((nc, nr))
                    queue.append((nc, nr))
    return visited


def _all_road_cells(grid):
    roads = set()
    for r in range(grid.rows):
        for c in range(grid.cols):
            if grid.is_road(c, r):
                roads.add((c, r))
    return roads


def _find_dead_ends(grid):
    dead = []
    for r in range(grid.rows):
        for c in range(grid.cols):
            if grid.is_road(c, r) and _tile_degree(grid, c, r) <= 1:
                dead.append((c, r))
    return dead


def _bfs_path_to_target(grid, start_c, start_r, targets):
    visited = {(start_c, start_r)}
    queue = deque([(start_c, start_r, [(start_c, start_r)])])
    while queue:
        cx, cy, path = queue.popleft()
        if (cx, cy) in targets and (cx, cy) != (start_c, start_r):
            return path
        for d in range(4):
            dc, dr = DIR_DELTA[d]
            nc, nr = cx + dc, cy + dr
            if (nc, nr) in visited:
                continue
            nb = grid.get(nc, nr)
            if nb is None:
                continue
            if nb.type == EMPTY or (nc, nr) in targets:
                visited.add((nc, nr))
                queue.append((nc, nr, path + [(nc, nr)]))
    return None


# ─────────────────────────────────────────
# ANTI-CLUSTER: count nearby intersections
# ─────────────────────────────────────────
def _count_nearby_intersections(grid, c, r, radius=2):
    """Count T-junction and Cross tiles within `radius` manhattan distance."""
    count = 0
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            if dc == 0 and dr == 0:
                continue
            if abs(dc) + abs(dr) > radius:
                continue
            nb = grid.get(c + dc, r + dr)
            if nb and nb.type in (TJUNCTION, CROSS):
                count += 1
    return count


def _has_adjacent_intersection(grid, c, r):
    """True if any direct neighbor is a T-junction or Cross."""
    for d in range(4):
        dc, dr = DIR_DELTA[d]
        nb = grid.get(c + dc, r + dr)
        if nb and nb.type in (TJUNCTION, CROSS):
            return True
    return False


# ─────────────────────────────────────────
# FIND TILE FOR INCOMING→OUTGOING
# ─────────────────────────────────────────
def _find_tile_for_ports(grid, c, r, incoming, outgoing):
    """Find the simplest tile that has both incoming and outgoing ports
    and satisfies neighbor constraints."""
    required = {incoming, outgoing}
    options = _get_options_with_ports(grid, c, r, required)
    if not options:
        return None
    # Prefer STRAIGHT > CURVE > TJUNCTION > CROSS (fewest ports)
    options.sort(key=lambda o: len(get_ports(o[0], o[1])))
    return options[0]


# ─────────────────────────────────────────
# CORRIDOR GROWTH ENGINE
# ─────────────────────────────────────────
def _grow_corridor(grid, start_c, start_r, start_dir, rng, max_len=None, cols=11, rows=11):
    """
    Grow a winding corridor from (start_c, start_r) in direction start_dir.
    Returns number of tiles placed.
    The corridor turns every 2-5 tiles using CURVE tiles for organic paths.
    """
    if max_len is None:
        max_len = rng.randint(4, max(5, (cols + rows) // 3))

    c, r, d = start_c, start_r, start_dir
    placed = 0
    straight_count = 0
    turn_after = rng.randint(2, 4)  # turn after this many straight tiles

    for step in range(max_len):
        dc, dr = DIR_DELTA[d]
        nc, nr = c + dc, r + dr

        # Bounds check
        if not (0 <= nc < cols and 0 <= nr < rows):
            break

        # Hit existing road → try to connect and stop
        if grid.is_road(nc, nr):
            _upgrade_tile_port(grid, c, r, d)
            _upgrade_tile_port(grid, nc, nr, OPPOSITE[d])
            break

        # Decide: continue straight or turn?
        incoming = OPPOSITE[d]
        outgoing = d  # default: straight

        if straight_count >= turn_after:
            # Time to turn — pick left or right
            turn_dir = (d + 1) % 4 if rng.random() < 0.5 else (d + 3) % 4
            # Check if turn is possible (not out of bounds in 2 steps)
            tdc, tdr = DIR_DELTA[turn_dir]
            future_c, future_r = nc + tdc, nr + tdr
            if 0 <= future_c < cols and 0 <= future_r < rows:
                outgoing = turn_dir
                straight_count = 0
                turn_after = rng.randint(2, 4)

        # Find appropriate tile
        tile_info = _find_tile_for_ports(grid, nc, nr, incoming, outgoing)
        if tile_info is None:
            # Try just incoming (straight continuation)
            tile_info = _find_tile_for_ports(grid, nc, nr, incoming, d)
            outgoing = d
        if tile_info is None:
            break

        # Anti-cluster: reject if this would be an intersection next to another
        if tile_info[0] in (TJUNCTION, CROSS):
            if _has_adjacent_intersection(grid, nc, nr):
                # Try simpler tile instead
                simple = [(t, rot) for t, rot in _get_options_with_ports(grid, nc, nr, {incoming})
                          if t in (STRAIGHT, CURVE)]
                if simple:
                    tile_info = simple[0]
                    outgoing = d  # just go straight
                else:
                    break

        # Place tile
        grid.set_tile(nc, nr, tile_info[0], tile_info[1])
        placed += 1

        # Ensure previous tile connects forward
        if grid.is_road(c, r):
            _upgrade_tile_port(grid, c, r, d)

        # Advance
        c, r = nc, nr
        actual_ports = get_ports(tile_info[0], tile_info[1])
        if outgoing in actual_ports:
            d = outgoing
            if outgoing == start_dir or tile_info[0] == STRAIGHT:
                straight_count += 1
            else:
                straight_count = 0
        else:
            # Tile doesn't have outgoing port, stop
            break

    return placed


# ─────────────────────────────────────────
# BORDER EXIT TARGETS
# ─────────────────────────────────────────
def _choose_border_exits(cols, rows, rng):
    exits = set()
    inner_c = list(range(2, cols - 2))  # avoid corners more
    inner_r = list(range(2, rows - 2))
    for side in range(4):
        n = rng.randint(2, 3)
        if side == 0:
            for ci in rng.sample(inner_c, min(n, len(inner_c))):
                exits.add((ci, 0))
        elif side == 1:
            for ri in rng.sample(inner_r, min(n, len(inner_r))):
                exits.add((cols - 1, ri))
        elif side == 2:
            for ci in rng.sample(inner_c, min(n, len(inner_c))):
                exits.add((ci, rows - 1))
        else:
            for ri in rng.sample(inner_r, min(n, len(inner_r))):
                exits.add((0, ri))
    return exits


# ─────────────────────────────────────────
# BUILD PATH (for border connections)
# ─────────────────────────────────────────
def _build_road_along_path(grid, path, rng):
    placed = 0
    for i in range(len(path)):
        c, r = path[i]
        if grid.is_road(c, r):
            if i + 1 < len(path):
                nc, nr = path[i + 1]
                for d in range(4):
                    dc, dr = DIR_DELTA[d]
                    if c + dc == nc and r + dr == nr:
                        _upgrade_tile_port(grid, c, r, d)
                        break
            continue
        prev_dir = None
        if i > 0:
            pc, pr = path[i - 1]
            for d in range(4):
                dc, dr = DIR_DELTA[d]
                if c + dc == pc and r + dr == pr:
                    prev_dir = d
                    break
        next_dir = None
        if i + 1 < len(path):
            nc, nr = path[i + 1]
            for d in range(4):
                dc, dr = DIR_DELTA[d]
                if c + dc == nc and r + dr == nr:
                    next_dir = d
                    break
        required = set()
        if prev_dir is not None:
            required.add(prev_dir)
        if next_dir is not None:
            required.add(next_dir)
        if not required:
            continue

        # Try exact match first (both prev and next)
        options = _get_options_with_ports(grid, c, r, required)

        # Fallback: just prev_dir, but prefer options pointing toward next
        if not options and prev_dir is not None:
            options = _get_options_with_ports(grid, c, r, {prev_dir})
            if options and next_dir is not None:
                # Strongly prefer options that also have next_dir port
                with_next = [o for o in options
                             if next_dir in get_ports(o[0], o[1])]
                if with_next:
                    options = with_next

        if not options:
            options = _get_connecting_options(grid, c, r)
        if not options:
            break

        # Prefer exact port count match (STRAIGHT/CURVE with exactly
        # the needed ports, not extras that open to empty cells)
        options.sort(key=lambda o: (
            # 1) Fewest extra ports beyond required
            len(get_ports(o[0], o[1]) - required),
            # 2) Prefer STRAIGHT/CURVE over intersections
            0 if o[0] in (STRAIGHT, CURVE) else 1,
            # 3) Fewest total ports
            len(get_ports(o[0], o[1]))
        ))
        grid.set_tile(c, r, options[0][0], options[0][1])
        placed += 1
    return placed


# ─────────────────────────────────────────
# DEAD-END HEALING
# ─────────────────────────────────────────
def _heal_dead_ends_v2(grid, seed_c, seed_r, rng):
    cols, rows = grid.cols, grid.rows
    for _pass in range(15):
        dead = _find_dead_ends(grid)
        interior_dead = [(c, r) for c, r in dead
                         if not _is_border(c, r, cols, rows)]
        if not interior_dead:
            break
        progress = False
        for c, r in interior_dead:
            if not grid.is_road(c, r) or _tile_degree(grid, c, r) >= 2:
                continue
            tile = grid.get(c, r)
            ports = get_ports(tile.type, tile.rotation)
            unconnected = []
            for d in ports:
                dc, dr = DIR_DELTA[d]
                nb = grid.get(c + dc, r + dr)
                if nb is None:
                    continue
                if nb.type == EMPTY:
                    unconnected.append(d)
                elif OPPOSITE[d] not in get_ports(nb.type, nb.rotation):
                    unconnected.append(d)
            free_dirs = [d for d in range(4) if d not in ports]
            healed = False

            # Strategy 1: extend toward border
            for d in unconnected + free_dirs:
                dc, dr = DIR_DELTA[d]
                nc, nr = c + dc, r + dr
                nb = grid.get(nc, nr)
                if nb is None or nb.type != EMPTY:
                    continue
                border_targets = {(bc, br) for br in range(rows)
                                  for bc in range(cols)
                                  if _is_border(bc, br, cols, rows)
                                  and not grid.is_road(bc, br)}
                if not border_targets:
                    continue
                path = _bfs_path_to_target(grid, nc, nr, border_targets)
                if path and len(path) <= 8:
                    if d not in ports:
                        _upgrade_tile_port(grid, c, r, d)
                    if _build_road_along_path(grid, [(c, r)] + path, rng) > 0:
                        healed = progress = True
                        break
            if healed:
                continue

            # Strategy 2: loop to nearby road
            for d in unconnected + free_dirs:
                dc, dr = DIR_DELTA[d]
                nc, nr = c + dc, r + dr
                nb = grid.get(nc, nr)
                if nb is None or nb.type != EMPTY:
                    continue
                nearby = {(cc, rr)
                          for rr in range(max(0, r-4), min(rows, r+5))
                          for cc in range(max(0, c-4), min(cols, c+5))
                          if (cc, rr) != (c, r) and grid.is_road(cc, rr)}
                path = _bfs_path_to_target(grid, nc, nr, nearby)
                if path and len(path) <= 5:
                    if d not in ports:
                        _upgrade_tile_port(grid, c, r, d)
                    if _build_road_along_path(grid, [(c, r)] + path, rng) > 0:
                        healed = progress = True
                        break
            if healed:
                continue

            # Strategy 3: upgrade tile
            opts = _get_valid_options(grid, c, r)
            opts.sort(key=lambda o: _tile_degree_if_placed(
                grid, c, r, o[0], o[1]), reverse=True)
            if opts and _tile_degree_if_placed(grid, c, r, opts[0][0], opts[0][1]) >= 2:
                grid.set_tile(c, r, opts[0][0], opts[0][1])
                progress = True
                continue

            # Strategy 4: remove
            grid.set_tile(c, r, EMPTY, 0)
            progress = True

        if not progress:
            break


# ═══════════════════════════════════════════
# MAIN GENERATION — Corridor Snake Growth
# ═══════════════════════════════════════════
def generate_map(cols, rows, seed=None):
    rng = random.Random(seed)
    grid = Grid(cols, rows)
    seed_c, seed_r = cols // 2, rows // 2

    # Phase 1: Place seed — use a STRAIGHT or CURVE, NOT cross
    # Start with a simple straight tile
    start_dir = rng.choice([0, 1, 2, 3])
    grid.set_tile(seed_c, seed_r, STRAIGHT, start_dir % 2)

    target_exits = _choose_border_exits(cols, rows, rng)
    max_roads = int(cols * rows * 0.35)

    # Phase 2: Grow corridors from tips
    # Initial tips: grow from seed in both directions of the straight
    seed_ports = list(get_ports(STRAIGHT, start_dir % 2))
    tips = [(seed_c, seed_r, d) for d in seed_ports]
    rng.shuffle(tips)
    road_count = 1

    max_iterations = cols * rows * 2
    iteration = 0

    while tips and road_count < max_roads and iteration < max_iterations:
        iteration += 1
        # Pick a random tip
        idx = rng.randint(0, len(tips) - 1)
        tc, tr, td = tips.pop(idx)

        # Don't grow from non-road tiles
        if not grid.is_road(tc, tr):
            continue

        # Grow a corridor
        corridor_len = rng.randint(3, max(4, min(cols, rows) // 2))
        before = road_count
        road_count_before = len(_all_road_cells(grid))

        placed = _grow_corridor(grid, tc, tr, td, rng,
                                max_len=corridor_len, cols=cols, rows=rows)
        road_count = len(_all_road_cells(grid))

        # Find the end of the corridor and spawn branch tips
        if placed > 0:
            # Walk along the corridor to find tip cells for branching
            c, r, d = tc, tr, td
            for step in range(placed + 1):
                dc, dr = DIR_DELTA[d]
                nc, nr = c + dc, r + dr
                if not grid.is_road(nc, nr):
                    break
                tile = grid.get(nc, nr)
                tile_ports = get_ports(tile.type, tile.rotation)

                # Maybe spawn a branch (low probability to keep it sparse)
                if step > 1 and rng.random() < 0.18 and road_count < max_roads:
                    branch_dirs = [(d + 1) % 4, (d + 3) % 4]
                    rng.shuffle(branch_dirs)
                    for bd in branch_dirs:
                        # Check anti-cluster before branching
                        if _count_nearby_intersections(grid, nc, nr, 2) >= 1:
                            continue
                        bdc, bdr = DIR_DELTA[bd]
                        bnc, bnr = nc + bdc, nr + bdr
                        bnb = grid.get(bnc, bnr)
                        if bnb and bnb.type == EMPTY:
                            if _upgrade_tile_port(grid, nc, nr, bd):
                                tips.append((nc, nr, bd))
                                break

                # Find outgoing direction
                outgoing = None
                for pd in tile_ports:
                    if pd != OPPOSITE[d]:
                        pdc, pdr = DIR_DELTA[pd]
                        pnb = grid.get(nc + pdc, nr + pdr)
                        if pnb and pnb.type != EMPTY:
                            outgoing = pd
                            break
                if outgoing is None:
                    # End of corridor — add as tip for future growth
                    for pd in tile_ports:
                        pdc, pdr = DIR_DELTA[pd]
                        pnb = grid.get(nc + pdc, nr + pdr)
                        if pnb and pnb.type == EMPTY:
                            tips.append((nc, nr, pd))
                            break
                    break
                c, r, d = nc, nr, outgoing

        # Replenish tips if running low
        if len(tips) < 2 and road_count < max_roads:
            all_r = list(_all_road_cells(grid))
            rng.shuffle(all_r)
            for rc, rr in all_r[:10]:
                tile = grid.get(rc, rr)
                ports = get_ports(tile.type, tile.rotation)
                for dd in ports:
                    pdc, pdr = DIR_DELTA[dd]
                    pnb = grid.get(rc + pdc, rr + pdr)
                    if pnb and pnb.type == EMPTY:
                        tips.append((rc, rr, dd))
                        break
                if len(tips) >= 3:
                    break

    # Phase 3: Force border exits
    for ec, er in target_exits:
        if grid.is_road(ec, er):
            continue
        road_cells = _all_road_cells(grid)
        path = _bfs_path_to_target(grid, ec, er, road_cells)
        if path:
            _build_road_along_path(grid, list(reversed(path)), rng)

    # Phase 4: Dead-end healing
    _heal_dead_ends_v2(grid, seed_c, seed_r, rng)

    # Phase 5: Cleanup — remove isolated tiles
    for r in range(rows):
        for c in range(cols):
            if grid.is_road(c, r) and _tile_degree(grid, c, r) == 0:
                grid.set_tile(c, r, EMPTY, 0)

    # Keep largest connected component
    all_roads = _all_road_cells(grid)
    if all_roads:
        remaining = set(all_roads)
        components = []
        while remaining:
            start = next(iter(remaining))
            comp = _flood_fill(grid, start[0], start[1])
            components.append(comp)
            remaining -= comp
        if len(components) > 1:
            components.sort(key=len, reverse=True)
            main = components[0]
            for comp in components[1:]:
                best_dist = 9999
                best_a = best_b = None
                for a in comp:
                    for b in main:
                        dd = abs(a[0]-b[0]) + abs(a[1]-b[1])
                        if dd < best_dist:
                            best_dist = dd
                            best_a, best_b = a, b
                if best_a and best_b and best_dist <= 6:
                    path = _bfs_path_to_target(
                        grid, best_a[0], best_a[1], {best_b})
                    if path:
                        _build_road_along_path(grid, path, rng)
                        main = main | comp
                        continue
                for cx, cy in comp:
                    grid.set_tile(cx, cy, EMPTY, 0)

    # Final dead-end healing (two passes for robustness)
    _heal_dead_ends_v2(grid, seed_c, seed_r, rng)
    _heal_dead_ends_v2(grid, seed_c, seed_r, rng)

    # Absolute last resort: iteratively remove interior dead-ends
    for _cleanup in range(20):
        remaining_dead = [
            (c, r) for c, r in _find_dead_ends(grid)
            if not _is_border(c, r, cols, rows) and _tile_degree(grid, c, r) <= 1
        ]
        if not remaining_dead:
            break
        for c, r in remaining_dead:
            if grid.is_road(c, r) and _tile_degree(grid, c, r) <= 1:
                grid.set_tile(c, r, EMPTY, 0)
        # Clean up isolated tiles
        for r2 in range(rows):
            for c2 in range(cols):
                if grid.is_road(c2, r2) and _tile_degree(grid, c2, r2) == 0:
                    grid.set_tile(c2, r2, EMPTY, 0)

    return grid
