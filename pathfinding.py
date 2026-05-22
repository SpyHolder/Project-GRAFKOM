"""
Seruni Map — Pathfinding
A* algorithm, Bézier world path builder, and nearest road/asset search.
"""
import math
import heapq
from collections import deque
from config import EMPTY, OPPOSITE, DIR_DELTA, get_ports


def astar(grid, start, goal):
    """A* on road network using Manhattan distance heuristic.
    Returns (path, explored) or (None, explored)."""
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


def _bez(p0, p1, p2, steps=12):
    """Quadratic Bézier curve interpolation."""
    pts = []
    for i in range(steps + 1):
        t = i / steps; u = 1 - t
        pts.append((u*u*p0[0]+2*u*t*p1[0]+t*t*p2[0],
                     u*u*p0[1]+2*u*t*p1[1]+t*t*p2[1]))
    return pts


def build_world_path(grid, tile_path, tile_size):
    """Convert A* tile path into smooth world-space Bézier polyline."""
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
                if not world_pts: world_pts.append(sp)
                world_pts.append(ep)
            else:
                curve = _bez(sp, (cx, cy), ep, 14)
                if world_pts: world_pts.extend(curve[1:])
                else: world_pts.extend(curve)
        elif entry_d is None and exit_d is not None:
            world_pts.append((cx, cy))
            world_pts.append(pm[exit_d])
        elif entry_d is not None and exit_d is None:
            if not world_pts: world_pts.append(pm[entry_d])
            world_pts.append((cx, cy))
        else:
            world_pts.append((cx, cy))

    return world_pts


def find_nearest_road(grid, c, r):
    """BFS to find nearest road tile adjacent to (c, r)."""
    for d in range(4):
        dc, dr = DIR_DELTA[d]
        nc, nr = c + dc, r + dr
        if grid.is_road(nc, nr):
            return (nc, nr)
    visited = {(c, r)}
    queue = deque([(c, r)])
    for _ in range(60):
        if not queue: break
        cx2, cy2 = queue.popleft()
        for d in range(4):
            dc, dr = DIR_DELTA[d]
            nc, nr = cx2 + dc, cy2 + dr
            if (nc, nr) in visited: continue
            if not (0 <= nc < grid.cols and 0 <= nr < grid.rows): continue
            visited.add((nc, nr))
            if grid.is_road(nc, nr):
                return (nc, nr)
            queue.append((nc, nr))
    return None
