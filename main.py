import math, random, sys, pygame
from gen import generate_map, _find_dead_ends
from engine import (Camera, astar, Car, TileCache, build_world_path, find_nearest_road,
                    get_ports, EMPTY, STRAIGHT, CURVE, TJUNCTION, CROSS, TILE_PORTS, OPPOSITE, DIR_DELTA)
from assets import (place_assets, AssetCache, ASSET_NONE, ASSET_GEROBAK, ASSET_BASECAMP,
                     ASSET_RUMAH, ASSET_POHON, ASSET_NAMES)

W, H = 1280, 800
T = 80; RW = 34; SW = 6; MG = (T - RW) // 2
GCOLS, GROWS = 50, 50
DASH_ON, DASH_OFF = 10, 8
SEED = None

C_BG=(13,15,23); C_GRASS=(16,20,30); C_SW=(35,40,58)
C_ROAD=(28,33,50); C_DASH=(50,58,88); C_NODE=(80,100,160)
C_PATH=(0,210,110); C_EXPLORED=(40,80,140)
C_START=(0,220,80); C_END=(220,50,50); C_HOVER=(255,220,60)
C_UI=(100,130,200); C_UIK=(70,90,140)

# ── Bézier helpers ──
def _bquad(p0,p1,p2,s=24):
    pts=[]
    for i in range(s+1):
        t=i/s; u=1-t
        pts.append((u*u*p0[0]+2*u*t*p1[0]+t*t*p2[0], u*u*p0[1]+2*u*t*p1[1]+t*t*p2[1]))
    return pts

def _offcurve(pts,off,side="left"):
    r=[]; n=len(pts)
    for i in range(n):
        if i==0: dx,dy=pts[1][0]-pts[0][0],pts[1][1]-pts[0][1]
        elif i==n-1: dx,dy=pts[-1][0]-pts[-2][0],pts[-1][1]-pts[-2][1]
        else: dx,dy=pts[i+1][0]-pts[i-1][0],pts[i+1][1]-pts[i-1][1]
        l=math.hypot(dx,dy) or 1; nx,ny=-dy/l,dx/l
        if side=="right": nx,ny=-nx,-ny
        r.append((pts[i][0]+nx*off, pts[i][1]+ny*off))
    return r

def _fband(s,cp,hw,col):
    if len(cp)<2: return
    L=_offcurve(cp,hw,"left"); R=_offcurve(cp,hw,"right")
    p=L+list(reversed(R))
    if len(p)>=3: pygame.draw.polygon(s,col,[(int(a),int(b)) for a,b in p])

def _dashline(s,x1,y1,x2,y2,vert=True):
    ln=(y2-y1) if vert else (x2-x1); pos=0; dr=True
    while pos<ln:
        sg=min(DASH_ON if dr else DASH_OFF, ln-pos)
        if dr:
            if vert: pygame.draw.line(s,C_DASH,(x1,y1+pos),(x1,y1+pos+sg),1)
            else: pygame.draw.line(s,C_DASH,(x1+pos,y1),(x1+pos+sg,y1),1)
        pos+=sg; dr=not dr

def _bdash(s,pts,col,da=10,ga=8):
    acc=0; dr=True
    for i in range(len(pts)-1):
        ax,ay=pts[i]; bx,by=pts[i+1]; sg=math.hypot(bx-ax,by-ay)
        if sg<.001: continue
        dx,dy=(bx-ax)/sg,(by-ay)/sg; t=0
        while t<sg:
            p=da if dr else ga; rm=min(p-acc,sg-t)
            if dr:
                sx2,sy2=ax+dx*t,ay+dy*t; ex2,ey2=ax+dx*(t+rm),ay+dy*(t+rm)
                pygame.draw.line(s,col,(int(sx2),int(sy2)),(int(ex2),int(ey2)),1)
            t+=rm; acc+=rm
            if acc>=p: acc=0; dr=not dr

# ── Tile draw (for cache) ──
def _dsw(s,x,y,tt,rot):
    ports=get_ports(tt,rot); closed={0,1,2,3}-ports
    for d in closed:
        if d==0: pygame.draw.rect(s,C_SW,(x+MG,y,RW,SW))
        elif d==2: pygame.draw.rect(s,C_SW,(x+MG,y+T-SW,RW,SW))
        elif d==3: pygame.draw.rect(s,C_SW,(x,y+MG,SW,RW))
        elif d==1: pygame.draw.rect(s,C_SW,(x+T-SW,y+MG,SW,RW))

def _dstr(s,x,y,rot):
    if rot==0:
        pygame.draw.rect(s,C_SW,(x,y,MG,T)); pygame.draw.rect(s,C_SW,(x+T-MG,y,MG,T))
        pygame.draw.rect(s,C_ROAD,(x+MG,y,RW,T)); cx=x+T//2; _dashline(s,cx,y+4,cx,y+T-4,True)
    else:
        pygame.draw.rect(s,C_SW,(x,y,T,MG)); pygame.draw.rect(s,C_SW,(x,y+T-MG,T,MG))
        pygame.draw.rect(s,C_ROAD,(x,y+MG,T,RW)); cy=y+T//2; _dashline(s,x+4,cy,x+T-4,cy,False)

def _dcurv(s,x,y,rot):
    cx,cy=x+T//2,y+T//2
    pm={0:(x+T//2,y),1:(x+T,y+T//2),2:(x+T//2,y+T),3:(x,y+T//2)}
    pp={0:(0,1),1:(1,2),2:(2,3),3:(3,0)}
    pf,pt=pp[rot]; cc=_bquad(pm[pf],(cx,cy),pm[pt],32)
    _dsw(s,x,y,CURVE,rot); _fband(s,cc,RW//2,C_ROAD); _bdash(s,cc,C_DASH)

def _dtjunc(s,x,y,rot):
    ports=list(get_ports(TJUNCTION,rot)); ctr=(x+T//2,y+T//2)
    pm={0:(x+T//2,y),1:(x+T,y+T//2),2:(x+T//2,y+T),3:(x,y+T//2)}
    _dsw(s,x,y,TJUNCTION,rot)
    for i,p1 in enumerate(ports):
        for p2 in ports[i+1:]:
            c2=_bquad(pm[p1],ctr,pm[p2],24); _fband(s,c2,RW//2,C_ROAD); _bdash(s,c2,C_DASH)
    pygame.draw.circle(s,C_ROAD,(int(ctr[0]),int(ctr[1])),RW//3+1)

def _dcross(s,x,y,rot=0):
    ctr=(x+T//2,y+T//2)
    pm={0:(x+T//2,y),1:(x+T,y+T//2),2:(x+T//2,y+T),3:(x,y+T//2)}
    for p1 in range(4):
        for p2 in range(p1+1,4):
            c2=_bquad(pm[p1],ctr,pm[p2],24); _fband(s,c2,RW//2,C_ROAD)
    pygame.draw.circle(s,C_ROAD,(int(ctr[0]),int(ctr[1])),RW//3+2)
    cr=max(2,MG-4)
    for px,py in [(x,y),(x+T,y),(x,y+T),(x+T,y+T)]: pygame.draw.circle(s,C_SW,(px,py),cr)
    for p1,p2 in [(0,2),(1,3)]:
        c2=_bquad(pm[p1],ctr,pm[p2],24); _bdash(s,c2,C_DASH)

def _dtile(s,x,y,tt,rot):
    if tt==STRAIGHT: _dstr(s,x,y,rot)
    elif tt==CURVE: _dcurv(s,x,y,rot)
    elif tt==TJUNCTION: _dtjunc(s,x,y,rot)
    elif tt==CROSS: _dcross(s,x,y,rot)

# ── Minimap ──
def build_minimap(grid, asset_grid=None, path=None, sz=180):
    cols,rows=grid.cols,grid.rows; sc=sz/max(cols,rows)
    s=pygame.Surface((int(cols*sc)+2,int(rows*sc)+2)); s.fill((20,24,35))
    ac = {ASSET_GEROBAK:(180,130,40), ASSET_BASECAMP:(200,150,50), ASSET_RUMAH:(50,55,70), ASSET_POHON:(18,38,22)}
    for r in range(rows):
        for c in range(cols):
            px,py=int(c*sc),int(r*sc); ps=max(1,int(sc))
            if grid.cells[r][c].type!=EMPTY:
                pygame.draw.rect(s,(50,60,90),(px,py,ps,ps))
            elif asset_grid:
                at=asset_grid.cells[r][c].type
                if at!=ASSET_NONE:
                    pygame.draw.rect(s,ac.get(at,(20,24,35)),(px,py,ps,ps))
    if path:
        for c2,r2 in path:
            pygame.draw.rect(s,C_PATH,(int(c2*sc),int(r2*sc),max(1,int(sc)),max(1,int(sc))))
    return s, sc

# ══════════════════════════════════
# MAIN
# ══════════════════════════════════
def main():
    pygame.init()
    screen=pygame.display.set_mode((W,H))
    pygame.display.set_caption("Seruni Map — A* Pathfinding")
    clock=pygame.time.Clock()
    font=pygame.font.SysFont("consolas",13)
    font_b=pygame.font.SysFont("consolas",28,bold=True)
    seed=SEED if SEED else random.randint(0,0xFFFFFF)

    def show_loading(msg="Generating map..."):
        screen.fill(C_BG)
        t=font_b.render(msg,True,C_UI)
        screen.blit(t,(W//2-t.get_width()//2,H//2-20)); pygame.display.flip()

    def rebuild(s):
        show_loading()
        g=generate_map(GCOLS,GROWS,seed=s)
        rc=sum(1 for r in range(g.rows) for c in range(g.cols) if g.cells[r][c].type!=EMPTY)
        de=_find_dead_ends(g)
        dc=sum(1 for c2,r2 in de if 0<c2<g.cols-1 and 0<r2<g.rows-1)
        show_loading("Placing assets...")
        ag=place_assets(g, seed=s)
        return g, ag, rc, dc

    grid, asset_grid, road_count, dead_count = rebuild(seed)
    world_w,world_h=GCOLS*T,GROWS*T
    cam=Camera(world_w,world_h,W,H)

    draw_map={STRAIGHT:_dtile,CURVE:_dtile,TJUNCTION:_dtile,CROSS:_dtile}
    tcache=TileCache(T,draw_map); tcache.build(C_GRASS,C_ROAD,C_SW)
    acache=AssetCache(T); acache.build()

    car=Car(); show_nodes=False; follow_car=False
    start_pt=None; end_pt=None; path_result=None; world_path=None; explored_set=set()
    select_mode=0; start_is_asset=False; end_is_asset=False
    minimap_surf,minimap_sc=build_minimap(grid,asset_grid)

    def get_road_cells():
        return [(c,r) for r in range(grid.rows) for c in range(grid.cols) if grid.cells[r][c].type!=EMPTY]

    def do_pathfind():
        nonlocal path_result, world_path, explored_set, minimap_surf, minimap_sc
        if start_pt and end_pt:
            # Resolve asset positions to nearest road
            sp = find_nearest_road(grid, *start_pt) if start_is_asset else start_pt
            ep = find_nearest_road(grid, *end_pt) if end_is_asset else end_pt
            if sp and ep:
                path_result, explored_set = astar(grid, sp, ep)
                world_path = build_world_path(grid, path_result, T) if path_result else None
            else:
                path_result=world_path=None; explored_set=set()
            minimap_surf, minimap_sc = build_minimap(grid, asset_grid, path_result)
        else:
            path_result=world_path=None; explored_set=set()
            minimap_surf, minimap_sc = build_minimap(grid, asset_grid)

    def clear_all():
        nonlocal start_pt,end_pt,path_result,world_path,explored_set,select_mode
        nonlocal start_is_asset,end_is_asset,minimap_surf,minimap_sc
        start_pt=end_pt=path_result=world_path=None; explored_set=set()
        select_mode=0; start_is_asset=end_is_asset=False; car.reset()
        minimap_surf,minimap_sc=build_minimap(grid,asset_grid)

    running=True
    while running:
        dt=clock.tick(60)/1000.0
        mx,my=pygame.mouse.get_pos()
        wmx,wmy=cam.screen_to_world(mx,my)
        hover_c,hover_r=int(wmx//T),int(wmy//T)
        hover_on_road = (0<=hover_c<GCOLS and 0<=hover_r<GROWS and grid.cells[hover_r][hover_c].type!=EMPTY)
        hover_on_asset = (0<=hover_c<GCOLS and 0<=hover_r<GROWS and
                          asset_grid.cells[hover_r][hover_c].type in (ASSET_GEROBAK,ASSET_BASECAMP,ASSET_RUMAH))
        hover_valid = hover_on_road or hover_on_asset

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            elif ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: running=False
                elif ev.key==pygame.K_r:
                    seed=random.randint(0,0xFFFFFF)
                    grid,asset_grid,road_count,dead_count=rebuild(seed)
                    world_w,world_h=GCOLS*T,GROWS*T; cam=Camera(world_w,world_h,W,H)
                    tcache.build(C_GRASS,C_ROAD,C_SW); acache.build(); clear_all()
                elif ev.key==pygame.K_n: show_nodes=not show_nodes
                elif ev.key==pygame.K_p:
                    rc=get_road_cells()
                    if len(rc)>=2:
                        mn=max(GCOLS,GROWS)//4
                        for _ in range(200):
                            a,b=random.sample(rc,2)
                            if abs(a[0]-b[0])+abs(a[1]-b[1])>=mn: break
                        start_pt,end_pt=a,b; select_mode=0
                        start_is_asset=end_is_asset=False; do_pathfind()
                elif ev.key==pygame.K_SPACE:
                    if world_path and not car.active: car.start(world_path)
                    elif car.active: car.active=not car.active
                elif ev.key==pygame.K_f: follow_car=not follow_car
                elif ev.key==pygame.K_c: clear_all()
                elif ev.key in (pygame.K_EQUALS,pygame.K_PLUS,pygame.K_KP_PLUS): car.change_speed(0.5)
                elif ev.key in (pygame.K_MINUS,pygame.K_KP_MINUS): car.change_speed(-0.5)
            elif ev.type==pygame.MOUSEBUTTONDOWN:
                if ev.button==1:
                    if hover_valid:
                        is_asset = hover_on_asset and not hover_on_road
                        if select_mode==0:
                            start_pt=(hover_c,hover_r); end_pt=None; path_result=None
                            world_path=None; explored_set=set(); select_mode=1
                            start_is_asset=is_asset; car.reset()
                        elif select_mode==1:
                            end_pt=(hover_c,hover_r); select_mode=0
                            end_is_asset=is_asset; do_pathfind()
                    else: cam.start_drag(mx,my)
                elif ev.button==3: cam.start_drag(mx,my)
                elif ev.button==4: cam.zoom_at(mx,my,1.15)
                elif ev.button==5: cam.zoom_at(mx,my,1/1.15)
            elif ev.type==pygame.MOUSEBUTTONUP:
                if ev.button in (1,3): cam.stop_drag()
            elif ev.type==pygame.MOUSEMOTION: cam.do_drag(mx,my)

        if car.active and not car.finished: car.update(dt,T)
        if follow_car and car.active:
            wx,wy=car.get_world_pos(); cam.center_on(wx,wy,0.1)

        # ── RENDER ──
        screen.fill(C_BG)
        lod=cam.get_lod()
        c0,c1,r0,r1=cam.get_visible_tiles(T,GCOLS,GROWS)

        if lod==0:
            ac_col={ASSET_GEROBAK:(140,100,30),ASSET_BASECAMP:(160,120,40),
                    ASSET_RUMAH:(40,45,58),ASSET_POHON:(14,32,18)}
            for r in range(r0,r1):
                for c in range(c0,c1):
                    sx,sy=cam.world_to_screen(c*T,r*T); sz=max(1,int(T*cam.zoom))
                    t=grid.cells[r][c]
                    if t.type!=EMPTY:
                        pygame.draw.rect(screen,C_ROAD,(int(sx),int(sy),sz,sz))
                    else:
                        at=asset_grid.cells[r][c].type
                        col=ac_col.get(at,C_GRASS)
                        pygame.draw.rect(screen,col,(int(sx),int(sy),sz,sz))
        else:
            for r in range(r0,r1):
                for c in range(c0,c1):
                    t=grid.cells[r][c]; sx,sy=cam.world_to_screen(c*T,r*T)
                    sz=int(T*cam.zoom)
                    if sz<2: continue
                    # Road tile
                    surf=tcache.get(t.type,t.rotation,lod)
                    if surf:
                        if sz!=T: screen.blit(pygame.transform.scale(surf,(sz,sz)),(int(sx),int(sy)))
                        else: screen.blit(surf,(int(sx),int(sy)))
                    # Asset overlay
                    if t.type==EMPTY:
                        ac2=asset_grid.cells[r][c]
                        if ac2.type!=ASSET_NONE:
                            asurf=acache.get(ac2.type,ac2.rotation,ac2.variant)
                            if asurf:
                                if sz!=T: screen.blit(pygame.transform.scale(asurf,(sz,sz)),(int(sx),int(sy)))
                                else: screen.blit(asurf,(int(sx),int(sy)))

        # Nodes
        if show_nodes and lod>=2:
            for r in range(r0,r1):
                for c in range(c0,c1):
                    t=grid.cells[r][c]
                    if t.type in (CURVE,TJUNCTION,CROSS):
                        sx,sy=cam.world_to_screen((c+.5)*T,(r+.5)*T)
                        pygame.draw.circle(screen,C_NODE,(int(sx),int(sy)),max(2,int(4*cam.zoom)))

        # Explored
        if explored_set and lod>=1:
            sz=max(1,int(T*cam.zoom)); es=pygame.Surface((sz,sz),pygame.SRCALPHA); es.fill((40,80,140,50))
            for c,r in explored_set:
                if c0<=c<c1 and r0<=r<r1:
                    sx,sy=cam.world_to_screen(c*T,r*T); screen.blit(es,(int(sx),int(sy)))

        # Path
        if world_path and len(world_path)>=2:
            pw=max(2,int(6*cam.zoom))
            for i in range(len(world_path)-1):
                s1=cam.world_to_screen(world_path[i][0],world_path[i][1])
                s2=cam.world_to_screen(world_path[i+1][0],world_path[i+1][1])
                pygame.draw.line(screen,C_PATH,(int(s1[0]),int(s1[1])),(int(s2[0]),int(s2[1])),pw)

        # Start/End markers
        mr=max(4,int(12*cam.zoom))
        if start_pt:
            sx,sy=cam.world_to_screen((start_pt[0]+.5)*T,(start_pt[1]+.5)*T)
            pygame.draw.circle(screen,C_START,(int(sx),int(sy)),mr)
            if cam.zoom>0.3:
                lbl="A"
                if start_is_asset:
                    at=asset_grid.cells[start_pt[1]][start_pt[0]].type
                    lbl=ASSET_NAMES.get(at,"A")
                lt=font.render(lbl,True,(255,255,255))
                screen.blit(lt,(int(sx)-lt.get_width()//2,int(sy)-lt.get_height()//2))
        if end_pt:
            sx,sy=cam.world_to_screen((end_pt[0]+.5)*T,(end_pt[1]+.5)*T)
            pygame.draw.circle(screen,C_END,(int(sx),int(sy)),mr)
            if cam.zoom>0.3:
                lbl="B"
                if end_is_asset:
                    at=asset_grid.cells[end_pt[1]][end_pt[0]].type
                    lbl=ASSET_NAMES.get(at,"B")
                lt=font.render(lbl,True,(255,255,255))
                screen.blit(lt,(int(sx)-lt.get_width()//2,int(sy)-lt.get_height()//2))

        # Hover
        if hover_valid and not cam.dragging:
            sx,sy=cam.world_to_screen(hover_c*T,hover_r*T); sz=max(1,int(T*cam.zoom))
            hs=pygame.Surface((sz,sz),pygame.SRCALPHA); hs.fill((255,220,60,40))
            screen.blit(hs,(int(sx),int(sy)))
            # Tooltip for asset
            if hover_on_asset and cam.zoom>0.25:
                at=asset_grid.cells[hover_r][hover_c].type
                tip=font.render(ASSET_NAMES.get(at,""),True,(255,220,100))
                screen.blit(tip,(int(sx)+2,int(sy)-16))

        car.draw(screen,cam)
        # Trail
        if car.trail and lod>=1:
            tw=max(1,int(3*cam.zoom)); step=max(1,len(car.trail)//150)
            for i in range(0,len(car.trail)-step,step):
                w1,w2=car.trail[i],car.trail[i+step]
                s1=cam.world_to_screen(w1[0],w1[1]); s2=cam.world_to_screen(w2[0],w2[1])
                pygame.draw.line(screen,(255,175,40),(int(s1[0]),int(s1[1])),(int(s2[0]),int(s2[1])),tw)

        # Minimap
        mm_x,mm_y=W-minimap_surf.get_width()-12,H-minimap_surf.get_height()-12
        pygame.draw.rect(screen,(10,12,20),(mm_x-4,mm_y-4,minimap_surf.get_width()+8,minimap_surf.get_height()+8),border_radius=4)
        screen.blit(minimap_surf,(mm_x,mm_y))
        vl,vt=cam.screen_to_world(0,0); vr,vb=cam.screen_to_world(W,H)
        rl=mm_x+int(vl/T*minimap_sc); rt2=mm_y+int(vt/T*minimap_sc)
        rw=max(2,int((vr-vl)/T*minimap_sc)); rh=max(2,int((vb-vt)/T*minimap_sc))
        pygame.draw.rect(screen,(200,200,200,180),(rl,rt2,rw,rh),1)
        if car.active and car.world_pts:
            cwx,cwy=car.get_world_pos()
            cmx=mm_x+int(cwx/T*minimap_sc); cmy=mm_y+int(cwy/T*minimap_sc)
            pygame.draw.circle(screen,(255,200,40),(cmx,cmy),3)

        # HUD
        lines=[f"Seed: {seed:06X}   Grid: {GCOLS}x{GROWS}   Roads: {road_count}   Zoom: {cam.zoom:.2f}x   LOD: {['LOW','MED','HIGH'][lod]}"]
        if start_pt:
            sn = ASSET_NAMES.get(asset_grid.cells[start_pt[1]][start_pt[0]].type,"Road") if start_is_asset else "Road"
            en = ASSET_NAMES.get(asset_grid.cells[end_pt[1]][end_pt[0]].type,"Road") if end_pt and end_is_asset else ("Road" if end_pt else "(click)")
            lines.append(f"Start: {sn}{start_pt}  End: {en}{end_pt or ''}  Path: {len(path_result) if path_result else 'N/A'} tiles")
        elif select_mode==0: lines.append("Click road or building to set START")
        else: lines.append("Click road or building to set END")
        if car.active: lines.append(f"Speed: {car.speed:.1f} t/s  {'FINISHED' if car.finished else 'MOVING'}")
        for i,ln in enumerate(lines):
            ts=font.render(ln,True,C_UI); bg=pygame.Surface((ts.get_width()+8,ts.get_height()+2),pygame.SRCALPHA)
            bg.fill((13,15,23,180)); screen.blit(bg,(8,8+i*18)); screen.blit(ts,(12,9+i*18))

        ctrls=["[R] New map","[P] Random path","[Space] Start car","[F] Follow","[C] Clear","[N] Nodes","[+/-] Speed","[ESC] Quit"]
        for i,ct in enumerate(ctrls):
            ts=font.render(ct,True,C_UIK); bg=pygame.Surface((ts.get_width()+8,ts.get_height()+2),pygame.SRCALPHA)
            bg.fill((13,15,23,160)); screen.blit(bg,(8,H-12-(len(ctrls)-i)*17)); screen.blit(ts,(12,H-11-(len(ctrls)-i)*17))

        pygame.display.flip()
    pygame.quit(); sys.exit()

if __name__=="__main__":
    main()
