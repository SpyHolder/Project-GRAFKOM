"""
Seruni Map — Main Entry Point
Game loop, event handling, state management.
"""
import random, sys, pygame
from collections import deque

from config import *
from gen import generate_map, _find_dead_ends
from pathfinding import astar, build_world_path, find_nearest_road
from camera import Camera, TileCache
from car import Car
from assets import (place_assets, AssetCache, ASSET_NONE, ASSET_GEROBAK,
                    ASSET_BASECAMP, ASSET_RUMAH, ASSET_POHON, ASSET_NAMES)
from renderer import draw_tile, build_minimap


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Seruni Map — A* Pathfinding")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 13)
    font_b = pygame.font.SysFont("consolas", 28, bold=True)
    seed = SEED if SEED else random.randint(0, 0xFFFFFF)

    # ── Helpers ──
    def show_loading(msg="Generating map..."):
        screen.fill(C_BG)
        t = font_b.render(msg, True, C_UI)
        screen.blit(t, (W//2 - t.get_width()//2, H//2 - 20))
        pygame.display.flip()

    def rebuild(s):
        show_loading()
        g = generate_map(GCOLS, GROWS, seed=s)
        rc = sum(1 for r in range(g.rows) for c in range(g.cols)
                 if g.cells[r][c].type != EMPTY)
        de = _find_dead_ends(g)
        dc = sum(1 for c2, r2 in de if 0 < c2 < g.cols-1 and 0 < r2 < g.rows-1)
        show_loading("Placing assets...")
        ag = place_assets(g, seed=s)
        return g, ag, rc, dc

    # ── Init ──
    grid, asset_grid, road_count, dead_count = rebuild(seed)
    world_w, world_h = GCOLS * T, GROWS * T
    cam = Camera(world_w, world_h, W, H)

    draw_map = {STRAIGHT: draw_tile, CURVE: draw_tile,
                TJUNCTION: draw_tile, CROSS: draw_tile}
    tcache = TileCache(T, draw_map)
    tcache.build(C_GRASS, C_ROAD, C_SW)
    acache = AssetCache(T); acache.build()

    car = Car(); show_nodes = False; follow_car = False
    start_pt = end_pt = path_result = world_path = None
    explored_set = set()
    select_mode = 0; start_is_asset = end_is_asset = False
    minimap_surf, minimap_sc = build_minimap(grid, asset_grid)

    def get_road_cells():
        return [(c, r) for r in range(grid.rows) for c in range(grid.cols)
                if grid.cells[r][c].type != EMPTY]

    def find_nearest_asset(sc, sr, types=(ASSET_GEROBAK, ASSET_BASECAMP)):
        """BFS from (sc,sr) to find nearest asset of given types."""
        visited = {(sc, sr)}; queue = deque([(sc, sr)])
        while queue:
            cx2, cy2 = queue.popleft()
            for d in range(4):
                dc, dr = DIR_DELTA[d]
                nc, nr = cx2 + dc, cy2 + dr
                if (nc, nr) in visited: continue
                if not (0 <= nc < GCOLS and 0 <= nr < GROWS): continue
                visited.add((nc, nr))
                if asset_grid.cells[nr][nc].type in types:
                    return (nc, nr)
                queue.append((nc, nr))
        return None

    def do_pathfind():
        nonlocal path_result, world_path, explored_set, minimap_surf, minimap_sc
        if start_pt and end_pt:
            sp = find_nearest_road(grid, *start_pt) if start_is_asset else start_pt
            ep = find_nearest_road(grid, *end_pt) if end_is_asset else end_pt
            if sp and ep:
                path_result, explored_set = astar(grid, sp, ep)
                world_path = build_world_path(grid, path_result, T) if path_result else None
            else:
                path_result = world_path = None; explored_set = set()
            minimap_surf, minimap_sc = build_minimap(grid, asset_grid, path_result)
        else:
            path_result = world_path = None; explored_set = set()
            minimap_surf, minimap_sc = build_minimap(grid, asset_grid)

    def clear_all():
        nonlocal start_pt, end_pt, path_result, world_path, explored_set
        nonlocal select_mode, start_is_asset, end_is_asset, minimap_surf, minimap_sc
        start_pt = end_pt = path_result = world_path = None
        explored_set = set(); select_mode = 0
        start_is_asset = end_is_asset = False; car.reset()
        minimap_surf, minimap_sc = build_minimap(grid, asset_grid)

    # ══════════════════════════════════
    # GAME LOOP
    # ══════════════════════════════════
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        mx, my = pygame.mouse.get_pos()
        wmx, wmy = cam.screen_to_world(mx, my)
        hover_c, hover_r = int(wmx // T), int(wmy // T)
        in_bounds = 0 <= hover_c < GCOLS and 0 <= hover_r < GROWS
        hover_on_road = in_bounds and grid.cells[hover_r][hover_c].type != EMPTY
        hover_on_asset = (in_bounds and asset_grid.cells[hover_r][hover_c].type
                          in (ASSET_GEROBAK, ASSET_BASECAMP, ASSET_RUMAH))
        hover_valid = hover_on_road or hover_on_asset

        # ── Events ──
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_r:
                    seed = random.randint(0, 0xFFFFFF)
                    grid, asset_grid, road_count, dead_count = rebuild(seed)
                    world_w, world_h = GCOLS*T, GROWS*T
                    cam = Camera(world_w, world_h, W, H)
                    tcache.build(C_GRASS, C_ROAD, C_SW); acache.build()
                    clear_all()
                elif ev.key == pygame.K_n:
                    show_nodes = not show_nodes
                elif ev.key == pygame.K_p:
                    rc = get_road_cells()
                    if rc:
                        start_pt = random.choice(rc); start_is_asset = False
                        end_pt = None; path_result = world_path = None
                        explored_set = set(); select_mode = 1; car.reset()
                elif ev.key == pygame.K_g:
                    if start_pt:
                        dest = find_nearest_asset(start_pt[0], start_pt[1], (ASSET_GEROBAK,))
                        if dest:
                            end_pt = dest; end_is_asset = True
                            select_mode = 0; do_pathfind()
                elif ev.key == pygame.K_b:
                    if start_pt:
                        dest = find_nearest_asset(start_pt[0], start_pt[1], (ASSET_BASECAMP,))
                        if dest:
                            end_pt = dest; end_is_asset = True
                            select_mode = 0; do_pathfind()
                elif ev.key == pygame.K_SPACE:
                    if world_path and not car.active: car.start(world_path)
                    elif car.active: car.active = not car.active
                elif ev.key == pygame.K_f:
                    follow_car = not follow_car
                elif ev.key == pygame.K_c:
                    clear_all()
                elif ev.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    car.change_speed(0.5)
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    car.change_speed(-0.5)
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    if hover_valid:
                        is_asset = hover_on_asset and not hover_on_road
                        if select_mode == 0:
                            start_pt = (hover_c, hover_r)
                            end_pt = path_result = world_path = None
                            explored_set = set(); select_mode = 1
                            start_is_asset = is_asset; car.reset()
                        elif select_mode == 1:
                            end_pt = (hover_c, hover_r); select_mode = 0
                            end_is_asset = is_asset; do_pathfind()
                    else:
                        cam.start_drag(mx, my)
                elif ev.button == 3: cam.start_drag(mx, my)
                elif ev.button == 4: cam.zoom_at(mx, my, 1.15)
                elif ev.button == 5: cam.zoom_at(mx, my, 1/1.15)
            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button in (1, 3): cam.stop_drag()
            elif ev.type == pygame.MOUSEMOTION:
                cam.do_drag(mx, my)

        # ── Update ──
        if car.active and not car.finished: car.update(dt, T)
        if follow_car and car.active:
            wx, wy = car.get_world_pos(); cam.center_on(wx, wy, 0.1)

        # ══════════════════════════════════
        # RENDER
        # ══════════════════════════════════
        screen.fill(C_BG)
        lod = cam.get_lod()
        c0, c1, r0, r1 = cam.get_visible_tiles(T, GCOLS, GROWS)

        # Tiles & Assets
        if lod == 0:
            ac_col = {ASSET_GEROBAK: (140,100,30), ASSET_BASECAMP: (160,120,40),
                      ASSET_RUMAH: (40,45,58), ASSET_POHON: (14,32,18)}
            for r in range(r0, r1):
                for c in range(c0, c1):
                    sx, sy = cam.world_to_screen(c*T, r*T)
                    sz = max(1, int(T*cam.zoom))
                    if grid.cells[r][c].type != EMPTY:
                        pygame.draw.rect(screen, C_ROAD, (int(sx), int(sy), sz, sz))
                    else:
                        at = asset_grid.cells[r][c].type
                        col = ac_col.get(at, C_GRASS)
                        pygame.draw.rect(screen, col, (int(sx), int(sy), sz, sz))
        else:
            for r in range(r0, r1):
                for c in range(c0, c1):
                    t = grid.cells[r][c]
                    sx, sy = cam.world_to_screen(c*T, r*T)
                    sz = int(T * cam.zoom)
                    if sz < 2: continue
                    surf = tcache.get(t.type, t.rotation, lod)
                    if surf:
                        if sz != T:
                            screen.blit(pygame.transform.scale(surf, (sz, sz)),
                                       (int(sx), int(sy)))
                        else:
                            screen.blit(surf, (int(sx), int(sy)))
                    if t.type == EMPTY:
                        ac2 = asset_grid.cells[r][c]
                        if ac2.type != ASSET_NONE:
                            asurf = acache.get(ac2.type, ac2.rotation, ac2.variant)
                            if asurf:
                                if sz != T:
                                    screen.blit(pygame.transform.scale(asurf, (sz, sz)),
                                               (int(sx), int(sy)))
                                else:
                                    screen.blit(asurf, (int(sx), int(sy)))

        # Nodes overlay
        if show_nodes and lod >= 2:
            for r in range(r0, r1):
                for c in range(c0, c1):
                    t = grid.cells[r][c]
                    if t.type in (CURVE, TJUNCTION, CROSS):
                        sx, sy = cam.world_to_screen((c+.5)*T, (r+.5)*T)
                        pygame.draw.circle(screen, C_NODE,
                            (int(sx), int(sy)), max(2, int(4*cam.zoom)))

        # Explored cells
        if explored_set and lod >= 1:
            sz = max(1, int(T*cam.zoom))
            es = pygame.Surface((sz, sz), pygame.SRCALPHA); es.fill((40,80,140,50))
            for c, r in explored_set:
                if c0 <= c < c1 and r0 <= r < r1:
                    sx, sy = cam.world_to_screen(c*T, r*T)
                    screen.blit(es, (int(sx), int(sy)))

        # Path line
        if world_path and len(world_path) >= 2:
            pw = max(2, int(6*cam.zoom))
            for i in range(len(world_path)-1):
                s1 = cam.world_to_screen(world_path[i][0], world_path[i][1])
                s2 = cam.world_to_screen(world_path[i+1][0], world_path[i+1][1])
                pygame.draw.line(screen, C_PATH,
                    (int(s1[0]), int(s1[1])), (int(s2[0]), int(s2[1])), pw)

        # Start / End markers
        mr = max(4, int(12*cam.zoom))
        if start_pt:
            sx, sy = cam.world_to_screen((start_pt[0]+.5)*T, (start_pt[1]+.5)*T)
            pygame.draw.circle(screen, C_START, (int(sx), int(sy)), mr)
            if cam.zoom > 0.3:
                lbl = "A"
                if start_is_asset:
                    at = asset_grid.cells[start_pt[1]][start_pt[0]].type
                    lbl = ASSET_NAMES.get(at, "A")
                lt = font.render(lbl, True, (255,255,255))
                screen.blit(lt, (int(sx)-lt.get_width()//2, int(sy)-lt.get_height()//2))
        if end_pt:
            sx, sy = cam.world_to_screen((end_pt[0]+.5)*T, (end_pt[1]+.5)*T)
            pygame.draw.circle(screen, C_END, (int(sx), int(sy)), mr)
            if cam.zoom > 0.3:
                lbl = "B"
                if end_is_asset:
                    at = asset_grid.cells[end_pt[1]][end_pt[0]].type
                    lbl = ASSET_NAMES.get(at, "B")
                lt = font.render(lbl, True, (255,255,255))
                screen.blit(lt, (int(sx)-lt.get_width()//2, int(sy)-lt.get_height()//2))

        # Hover highlight
        if hover_valid and not cam.dragging:
            sx, sy = cam.world_to_screen(hover_c*T, hover_r*T)
            sz = max(1, int(T*cam.zoom))
            hs = pygame.Surface((sz, sz), pygame.SRCALPHA); hs.fill((255,220,60,40))
            screen.blit(hs, (int(sx), int(sy)))
            if hover_on_asset and cam.zoom > 0.25:
                at = asset_grid.cells[hover_r][hover_c].type
                tip = font.render(ASSET_NAMES.get(at, ""), True, (255,220,100))
                screen.blit(tip, (int(sx)+2, int(sy)-16))

        # Car + trail
        car.draw(screen, cam)
        if car.trail and lod >= 1:
            tw = max(1, int(3*cam.zoom)); step = max(1, len(car.trail)//150)
            for i in range(0, len(car.trail)-step, step):
                w1, w2 = car.trail[i], car.trail[i+step]
                s1 = cam.world_to_screen(w1[0], w1[1])
                s2 = cam.world_to_screen(w2[0], w2[1])
                pygame.draw.line(screen, (255,175,40),
                    (int(s1[0]), int(s1[1])), (int(s2[0]), int(s2[1])), tw)

        # Minimap
        mm_x = W - minimap_surf.get_width() - 12
        mm_y = H - minimap_surf.get_height() - 12
        pygame.draw.rect(screen, (10,12,20),
            (mm_x-4, mm_y-4, minimap_surf.get_width()+8, minimap_surf.get_height()+8),
            border_radius=4)
        screen.blit(minimap_surf, (mm_x, mm_y))
        vl, vt = cam.screen_to_world(0, 0)
        vr, vb = cam.screen_to_world(W, H)
        rl = mm_x + int(vl/T*minimap_sc)
        rt2 = mm_y + int(vt/T*minimap_sc)
        rw = max(2, int((vr-vl)/T*minimap_sc))
        rh = max(2, int((vb-vt)/T*minimap_sc))
        pygame.draw.rect(screen, (200,200,200,180), (rl, rt2, rw, rh), 1)
        if car.active and car.world_pts:
            cwx, cwy = car.get_world_pos()
            cmx = mm_x + int(cwx/T*minimap_sc)
            cmy = mm_y + int(cwy/T*minimap_sc)
            pygame.draw.circle(screen, (255,200,40), (cmx, cmy), 3)

        # HUD
        lines = [f"Seed: {seed:06X}   Grid: {GCOLS}x{GROWS}   Roads: {road_count}"
                 f"   Zoom: {cam.zoom:.2f}x   LOD: {['LOW','MED','HIGH'][lod]}"]
        if start_pt:
            sn = (ASSET_NAMES.get(asset_grid.cells[start_pt[1]][start_pt[0]].type, "Road")
                  if start_is_asset else "Road")
            en = (ASSET_NAMES.get(asset_grid.cells[end_pt[1]][end_pt[0]].type, "Road")
                  if end_pt and end_is_asset else ("Road" if end_pt else "(click)"))
            plen = len(path_result) if path_result else "N/A"
            lines.append(f"Start: {sn}{start_pt}  End: {en}{end_pt or ''}  Path: {plen} tiles")
        elif select_mode == 0:
            lines.append("Click road/building to set START")
        else:
            lines.append("Click to set END  |  [G] Nearest Gerobak  |  [B] Nearest Basecamp")
        if car.active:
            lines.append(f"Speed: {car.speed:.1f} t/s  "
                         f"{'FINISHED' if car.finished else 'MOVING'}")
        for i, ln in enumerate(lines):
            ts = font.render(ln, True, C_UI)
            bg = pygame.Surface((ts.get_width()+8, ts.get_height()+2), pygame.SRCALPHA)
            bg.fill((13,15,23,180))
            screen.blit(bg, (8, 8+i*18)); screen.blit(ts, (12, 9+i*18))

        ctrls = ["[R] New map", "[P] Random start", "[G] → Gerobak", "[B] → Basecamp",
                 "[Space] Car", "[F] Follow", "[C] Clear", "[N] Nodes",
                 "[+/-] Speed", "[ESC] Quit"]
        for i, ct in enumerate(ctrls):
            ts = font.render(ct, True, C_UIK)
            bg = pygame.Surface((ts.get_width()+8, ts.get_height()+2), pygame.SRCALPHA)
            bg.fill((13,15,23,160))
            screen.blit(bg, (8, H-12-(len(ctrls)-i)*17))
            screen.blit(ts, (12, H-11-(len(ctrls)-i)*17))

        pygame.display.flip()

    pygame.quit(); sys.exit()


if __name__ == "__main__":
    main()
