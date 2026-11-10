# -*- coding: utf-8 -*-
"""BLD-W02 Concentric Fortress on the Ridge -- deterministic checks.

Design
------
* One Blender run (Scene.load, via _bld_extract.py).  All geometric measurement happens inside Blender in
  `extra_py` (= _GLUE + _CORE below): per-collection BVH trees are built from the evaluated depsgraph (instances
  included), then rays / sections / KD-trees measure every unit at frame 120 and the drawbridge over frames.
  The answer key is embedded into extra_py as CFG, so the measuring code knows where to look (anchors, wall axes,
  storey levels), but the *verdicts* are computed here in pure Python from EXTRA['w02'].
* _CORE is pure Python (math only) and talks to geometry through `R.ray(o, d, maxd) -> (t, normal)|None` and
  `R.near(p) -> dist|None`, so it can be unit-tested outside Blender with a mock ray caster.
* Items returned: B01-B09, M01-M12, G01-G15.  G16 (visual blind review) is left to the judge model.
* postprocess: B01 fail or no unit collections -> everything except B05/B06 fails; non-change-order units missing
  in B02 -> their zone's M/G items fail.
"""
import json, math, os, pathlib, re, struct, zlib, traceback

try:
    from _bld_lib import Scene, ok, bad, close, png_size, load_manifest, gate_group
except Exception:  # pragma: no cover
    raise

UNITS33 = ['T%02d' % i for i in range(1, 13)] + ['W%02d' % i for i in range(1, 15)] + ['G01', 'G02', 'B01', 'K01', 'C01', 'S01', 'P01']
UNITS34 = UNITS33 + ['W15']
WALLS = ['W%02d' % i for i in range(1, 16)]
TOWERS = ['T%02d' % i for i in range(1, 13)]
CHANGED = ['S01', 'T02', 'T08', 'W15']
ZONE_ITEMS = {'A': ('M02', 'G01'), 'B': ('M03', 'G02'), 'C': ('M04', 'G03'), 'D': ('M05', 'G04'),
              'E': ('M06', 'G05'), 'F': ('M07', 'G06'), 'G': ('M08', 'G07')}
PARAM_FIELDS = {
    'tower': ['shape', 'storeys', 'merlons', 'slits_per_storey', 'roof', 'walk_level', 'platform_level'],
    'wall': ['merlons', 'slits', 'buttresses', 'thickness'],
    'gatehouse': ['portcullises', 'arch', 'flank_towers', 'merlons', 'walk_level'],
    'drawbridge': ['planks', 'deck_length'],
    'keep': ['storeys', 'turrets', 'roof', 'windows_per_long_side'],
    'chapel': ['bays', 'apse', 'bell_openings'],
    'stables': ['stall_doors', 'loft_openings'],
    'well': ['posts', 'roof'],
}
DISCRETE = {
    'tower': ['shape', 'storeys', 'merlons', 'slits_per_storey', 'roof'],
    'wall': ['merlons', 'slits', 'buttresses'],
    'gatehouse': ['portcullises', 'arch', 'flank_towers', 'merlons'],
    'drawbridge': ['planks'],
    'keep': ['storeys', 'turrets', 'roof', 'windows_per_long_side'],
    'chapel': ['bays', 'apse', 'bell_openings'],
    'stables': ['stall_doors', 'loft_openings'],
    'well': ['posts', 'roof'],
}
TOL_POS, TOL_Z, TOL_ANG = 0.30, 0.15, 2.0
ANIM_FRAMES = sorted(set(list(range(1, 121, 4)) + [36, 72, 96, 120]))
CHAIN_FRAMES = [1, 36, 72, 120]

# ----------------------------------------------------------------------------------------------------------------
# Pure-python measurement core (executed inside Blender; also importable for mock tests)
# ----------------------------------------------------------------------------------------------------------------
_CORE = r'''
import math
EPS = 1e-3

def _add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def _mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def hits(R, o, d, maxd, cap=80):
    out = []
    t0 = 0.0
    while R is not None and t0 < maxd and len(out) < cap:
        h = R.ray(_add(o, _mul(d, t0)), d, maxd - t0)
        if h is None:
            break
        t, n = h
        out.append((t0 + t, n))
        t0 += t + EPS
    return out

def first(R, o, d, maxd):
    if R is None:
        return None
    return R.ray(o, d, maxd)

def inside(R, p):
    """robust point-in-solid: outside points always see an entering face first; inside points see an exiting
    face in at least one of three directions (coincident faces of touching solids can mask one direction)."""
    for d in ((0.0, 0.0, 1.0), (0.6, 0.8, 0.0), (-0.48, 0.18, 0.8586)):
        h = first(R, p, d, 300.0)
        if h and _dot(d, h[1]) > 0:
            return True
    return False

def segs(R, o, d, maxd):
    """inside intervals along a ray: distinct hit distances, each gap classified by a midpoint inside() test."""
    ts = []
    for t, n in hits(R, o, d, maxd, cap=200):
        if not ts or t - ts[-1] > 2 * EPS:
            ts.append(t)
    ivs = []
    for i in range(len(ts) - 1):
        a, b = ts[i], ts[i + 1]
        if inside(R, _add(o, _mul(d, (a + b) / 2))):
            if ivs and abs(ivs[-1][1] - a) < 1e-6:
                ivs[-1] = (ivs[-1][0], b)
            else:
                ivs.append((a, b))
    return ivs

class Frame:
    def __init__(self, cx, cy, facing):
        f = math.radians(facing)
        self.cx, self.cy = cx, cy
        self.U = (math.cos(f), math.sin(f), 0.0)
        self.V = (-math.sin(f), math.cos(f), 0.0)
    def w(self, u, v, z):
        return (self.cx + u * self.U[0] + v * self.V[0], self.cy + u * self.U[1] + v * self.V[1], z)
    def dir(self, du, dv):
        return (du * self.U[0] + dv * self.V[0], du * self.U[1] + dv * self.V[1], 0.0)
    def loc(self, x, y):
        dx, dy = x - self.cx, y - self.cy
        return dx * self.U[0] + dy * self.U[1], dx * self.V[0] + dy * self.V[1]

def raster(R, F, z, u0, u1, v0, v1, st):
    nu, nv = int(round((u1 - u0) / st)), int(round((v1 - v0) / st))
    g = [bytearray(nu) for _ in range(nv)]
    d = F.dir(1, 0)
    for j in range(nv):
        v = v0 + (j + 0.5) * st
        o = F.w(u0 - 1.0, v, z)
        for a, b in segs(R, o, d, u1 - u0 + 2.0):
            ia = max(0, int(math.ceil((a - 1.0) / st - 0.5)))
            ib = min(nu - 1, int(math.floor((b - 1.0) / st - 0.5)))
            for i in range(ia, ib + 1):
                g[j][i] = 1
    return {'g': g, 'nu': nu, 'nv': nv, 'u0': u0, 'v0': v0, 'st': st}

def fill(ra):
    g, nu, nv = ra['g'], ra['nu'], ra['nv']
    out = [bytearray(nu) for _ in range(nv)]
    stack = [(i, j) for i in range(nu) for j in (0, nv - 1)] + [(i, j) for j in range(nv) for i in (0, nu - 1)]
    while stack:
        i, j = stack.pop()
        if i < 0 or j < 0 or i >= nu or j >= nv or out[j][i] or g[j][i]:
            continue
        out[j][i] = 1
        stack.extend(((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)))
    f = [bytearray((0 if out[j][i] else 1) for i in range(nu)) for j in range(nv)]
    return dict(ra, g=f)

def cells(ra):
    st = ra['st']
    for j, row in enumerate(ra['g']):
        v = ra['v0'] + (j + 0.5) * st
        for i, x in enumerate(row):
            if x:
                yield ra['u0'] + (i + 0.5) * st, v

def comps(ra, min_cells=4):
    g, nu, nv = ra['g'], ra['nu'], ra['nv']
    seen = [bytearray(nu) for _ in range(nv)]
    out = []
    for j in range(nv):
        for i in range(nu):
            if g[j][i] and not seen[j][i]:
                stack, n, su, sv = [(i, j)], 0, 0.0, 0.0
                seen[j][i] = 1
                bb = [i, j, i, j]
                while stack:
                    a, b = stack.pop()
                    n += 1; su += a; sv += b
                    bb = [min(bb[0], a), min(bb[1], b), max(bb[2], a), max(bb[3], b)]
                    for da in (-1, 0, 1):
                        for db in (-1, 0, 1):
                            x, y = a + da, b + db
                            if 0 <= x < nu and 0 <= y < nv and g[y][x] and not seen[y][x]:
                                seen[y][x] = 1
                                stack.append((x, y))
                if n >= min_cells:
                    st = ra['st']
                    out.append({'area': n * st * st, 'cu': ra['u0'] + (su / n + 0.5) * st, 'cv': ra['v0'] + (sv / n + 0.5) * st,
                                'bb': [ra['u0'] + bb[0] * st, ra['v0'] + bb[1] * st, ra['u0'] + (bb[2] + 1) * st, ra['v0'] + (bb[3] + 1) * st]})
    return out

def bridge(flags, gap, cyclic=False):
    """close False-gaps of <= gap samples that are bounded by True on both sides (ray-sampling slivers)."""
    f = list(flags); n = len(f)
    if gap <= 0 or n == 0 or not any(f):
        return f
    idx = [i for i, x in enumerate(f) if x]
    pairs = list(zip(idx, idx[1:])) + ([(idx[-1], idx[0] + n)] if cyclic else [])
    for a, b in pairs:
        if 1 < b - a <= gap + 1:
            for k in range(a + 1, b):
                f[k % n] = True
    return f

def runs(flags, cyclic=False, min_len=1, gap=0):
    flags = bridge(flags, gap, cyclic)
    n = len(flags)
    if n == 0:
        return 0
    if cyclic and all(flags):
        return 1
    if cyclic and flags[0] and flags[-1]:
        k = 0
        while k < n and flags[k]:
            k += 1
        flags = list(flags[k:]) + list(flags[:k])
    cnt, cur = 0, 0
    for f in list(flags) + [False]:
        if f:
            cur += 1
        else:
            if cur >= min_len:
                cnt += 1
            cur = 0
    return cnt

def run_list(flags, min_len=1, gap=0):
    flags = bridge(flags, gap)
    out, cur, st = [], 0, None
    for k, f in enumerate(list(flags) + [False]):
        if f:
            if cur == 0:
                st = k
            cur += 1
        else:
            if cur >= min_len:
                out.append((st, k - 1))
            cur = 0
    return out

def bbox_local(pts):
    us = [p[0] for p in pts]; vs = [p[1] for p in pts]
    return (min(us), max(us), min(vs), max(vs)) if pts else None

def shape_iou(ra, bb):
    umin, umax, vmin, vmax = bb
    cu, cv = (umin + umax) / 2, (vmin + vmax) / 2
    r = ((umax - umin) + (vmax - vmin)) / 4
    R = (vmax - vmin) / 2
    def m_round(u, v): return (u - cu) ** 2 + (v - cv) ** 2 <= r * r
    def m_sq(u, v): return umin <= u <= umax and vmin <= v <= vmax
    def m_D(u, v):
        c = umax - R
        if u < umin or u > umax or v < vmin or v > vmax: return False
        return u <= c or (u - c) ** 2 + (v - cv) ** 2 <= R * R
    def m_Df(u, v):
        c = umin + R
        if u < umin or u > umax or v < vmin or v > vmax: return False
        return u >= c or (u - c) ** 2 + (v - cv) ** 2 <= R * R
    tm = {'round': m_round, 'square': m_sq, 'D': m_D, 'D_flip': m_Df}
    inter = dict((k, 0) for k in tm); uni = dict((k, 0) for k in tm)
    st = ra['st']
    for j, row in enumerate(ra['g']):
        v = ra['v0'] + (j + 0.5) * st
        for i, x in enumerate(row):
            u = ra['u0'] + (i + 0.5) * st
            for k, f in tm.items():
                t = f(u, v)
                if x and t: inter[k] += 1
                if x or t: uni[k] += 1
    return dict((k, round(inter[k] / uni[k], 4) if uni[k] else 0.0) for k in tm)

def classify_shape(iou):
    best = max(('round', 'square', 'D'), key=lambda k: iou.get(k, 0))
    return best

def terrain_z(Rt, x, y):
    h = first(Rt, (x, y, 400.0), (0.0, 0.0, -1.0), 800.0)
    return 400.0 - h[0] if h else None

def ground_float(R, Rt, pts):
    """per sample: first hit of unit going up from below terrain, minus terrain z."""
    fl, miss = [], 0
    for (x, y) in pts:
        zt = terrain_z(Rt, x, y)
        if zt is None:
            miss += 1; continue
        h = first(R, (x, y, zt - 25.0), (0.0, 0.0, 1.0), 80.0)
        if h is None:
            miss += 1; continue
        fl.append(round(zt - 25.0 + h[0] - zt, 3))
    return {'n': len(pts), 'miss': miss, 'max_float': max(fl) if fl else None,
            'n_float': sum(1 for f in fl if f > 0.10)}

def down_levels(R, x, y, ztop, zbot):
    out = []
    for t, n in hits(R, (x, y, ztop), (0.0, 0.0, -1.0), ztop - zbot):
        out.append((round(ztop - t, 3), round(n[2], 3)))
    return out

def poly_outline(pts_local, step):
    out = []
    n = len(pts_local)
    for k in range(n):
        a = pts_local[k]; b = pts_local[(k + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        m = max(1, int(L / step))
        for i in range(m):
            f = (i + 0.5) / m
            out.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])))
    return out

def tower_footprint_local(p, inset):
    if p['shape'] == 'round':
        r = p['diameter'] / 2 - inset
        return [(r * math.cos(t * math.pi / 36), r * math.sin(t * math.pi / 36)) for t in range(72)]
    if p['shape'] == 'square':
        a = p['side'] / 2 - inset
        return [(-a, -a), (a, -a), (a, a), (-a, a)]
    r, b = p['radius'] - inset, p['back_depth'] - inset
    return [(-b, -r)] + [(r * math.cos(-math.pi / 2 + k * math.pi / 24), r * math.sin(-math.pi / 2 + k * math.pi / 24)) for k in range(25)] + [(-b, r)]

def measure_tower(R, Rt, u):
    p, z0 = u['params'], u['z0']
    F = Frame(u['x'], u['y'], u['facing'])
    size = p.get('diameter') or p.get('side') or 2 * p.get('radius', 5)
    E = size / 2 + 3.0
    out = {}
    ra = raster(R, F, z0 + 1.0, -E, E, -E, E, 0.05)
    fr = fill(ra)
    pts = list(cells(fr))
    bb = bbox_local(pts)
    if not bb:
        return {'present': False}
    out['present'] = True
    out['bb'] = [round(x, 3) for x in bb]
    out['area'] = round(len(pts) * 0.0025, 3)
    iou = shape_iou(fr, bb)
    out['iou'] = iou
    out['shape'] = classify_shape(iou)
    # shell along local axes (inner face from anchor outwards, outer from bb)
    sh = []
    for (du, dv, ext) in ((1, 0, bb[1]), (-1, 0, -bb[0]), (0, 1, bb[3]), (0, -1, -bb[2])):
        # wall thickness = first solid interval met from OUTSIDE going inward (a newel stair / interior fittings at
        # the anchor no longer shorten the inner-face distance)
        ivs = segs(R, F.w(du * (E + 2), dv * (E + 2), z0 + 1.0), F.dir(-du, -dv), E + 2)
        if ivs:
            sh.append(round(ivs[0][1] - ivs[0][0], 3))
    sh.sort()
    out['shell_list'] = sh
    out['shell'] = sh[len(sh) // 2] if sh else None
    # levels (vertical rays near centre)
    ztop = z0 + p['platform_level'] + p.get('parapet', 2) + p.get('roof_rise', 0) + 12
    cnts, plats, firsts = [], [], []
    for (du, dv) in ((0.31, 0.23), (-0.37, 0.19), (0.12, -0.41)):
        x, y, _ = F.w(du, dv, 0)
        lv = down_levels(R, x, y, ztop, z0 - 1.0)
        if lv:
            firsts.append(lv[0])
        ups = [z for z, nz in lv if nz > 0.9 and z > z0 + 0.5]
        cnts.append(len(ups))
        plats.append(max(ups) if ups else None)
    cnts.sort()
    out['storeys_raw'] = cnts[1]
    # storeys / platform: candidate up-facing levels from the 3 central rays plus 6 rays on a ring at 0.6 x the inner
    # half-size; a level counts only if it is a real slab, i.e. solid just below it at >= 5 of the 6 ring points
    # and open just above it (so the level is the slab's top surface; rejects spiral-stair treads, newel tops,
    # landings that cover only part of the interior, and tread tops buried inside a floor slab)
    if p['shape'] == 'round':
        rin = p['diameter'] / 2 - p.get('shell', 1.5)
    elif p['shape'] == 'square':
        rin = p['side'] / 2 - p.get('shell', 1.5)
    else:
        rin = min(p['radius'], p['back_depth']) - p.get('shell', 1.5)
    rr_ = max(0.3, 0.6 * rin)
    ring = [(rr_ * math.cos(math.radians(15 + 60 * k)), rr_ * math.sin(math.radians(15 + 60 * k))) for k in range(6)]
    cand = []
    for (du, dv) in [(0.31, 0.23), (-0.37, 0.19), (0.12, -0.41)] + ring:
        x, y, _ = F.w(du, dv, 0)
        cand.extend(z for z, nz in down_levels(R, x, y, ztop, z0 - 1.0) if nz > 0.9 and z > z0 + 0.5)
    cand.sort()
    lvls = []
    for z in cand:
        if lvls and z - lvls[-1][-1] < 0.1:
            lvls[-1].append(z)
        else:
            lvls.append([z])
    slabs = []
    for c in lvls:
        z = max(c)
        nin = sum(1 for (du, dv) in ring if inside(R, F.w(du, dv, z - 0.03)) and not inside(R, F.w(du, dv, z + 0.03)))
        if nin >= 5:
            slabs.append(round(z, 3))
    out['slab_levels'] = slabs
    out['storeys'] = len(slabs)
    out['platform_z'] = max(slabs) if slabs else None
    fz = firsts[0] if firsts else None
    out['first_hit'] = fz
    # roof
    h = first(R, F.w(0, 0, ztop), (0, 0, -1), ztop - z0)
    out['roof_top'] = round(ztop - h[0], 3) if h else None
    roof = None
    if fz and out['platform_z'] is not None:
        if fz[1] > 0.9 and fz[0] <= out['platform_z'] + 0.3:
            roof = 'platform'
        else:
            zr = z0 + p['platform_level'] + 1.2 + 0.4 * p.get('roof_rise', 4.0)
            rr = fill(raster(R, F, zr, -E, E, -E, E, 0.05))
            rp = list(cells(rr))
            rbb = bbox_local(rp)
            if rbb:
                ri = shape_iou(rr, rbb)
                roof = 'cone' if ri['round'] >= ri['square'] else 'pyramid'
                out['roof_iou'] = ri
    out['roof'] = roof
    # merlons: ring 0.3 inside outer contour at parapet base
    zpl = out['platform_z'] if out['platform_z'] is not None else z0 + p['platform_level']
    zb = zpl + 0.3
    thr = zpl + p.get('parapet', 2.0) - 0.3
    cu, cv = (bb[0] + bb[1]) / 2, (bb[2] + bb[3]) / 2
    if p['shape'] == 'D' or out['shape'] == 'D':
        cu = bb[1] - (bb[3] - bb[2]) / 2
    flags = []
    for k in range(720):
        a = 2 * math.pi * k / 720
        du, dv = math.cos(a), math.sin(a)
        o = F.w(cu + du * (E + 2), cv + dv * (E + 2), zb)
        h = first(R, o, F.dir(-du, -dv), E + 2)
        if not h:
            flags.append(False); continue
        r = E + 2 - h[0] - 0.3
        x, y, _ = F.w(cu + du * r, cv + dv * r, 0)
        zs = zpl + 12 if roof not in ('cone', 'pyramid') else zpl + 1.15
        hh = first(R, (x, y, zs), (0, 0, -1), zs - zpl + 2)
        flags.append(bool(hh and zs - hh[0] > thr))
    out['merlons'] = runs(flags, cyclic=True, gap=2)
    # slits per storey (storeys 2..N), rays from anchor outward, union of three heights
    N, Hp = p['storeys'], p['platform_level']
    rout = []
    for k in range(720):
        a = 2 * math.pi * k / 720
        du, dv = math.cos(a), math.sin(a)
        h = first(R, F.w(du * (E + 2), dv * (E + 2), z0 + 1.0), F.dir(-du, -dv), E + 2)
        rout.append(E + 2 - h[0] if h else E)
    sl = []
    for s in range(1, N):
        zc = z0 + Hp * (s + 0.5) / N
        op = [False] * 720
        for dz in (-0.3, 0.0, 0.3):
            for k in range(720):
                if op[k]: continue
                a = 2 * math.pi * k / 720
                # start 0.3 m inside the expected inner wall face (not at the anchor), so a newel stair or other
                # interior fittings do not mask slits; a start point inside the masonry just sees the exit face
                r0 = max(0.0, rout[k] - p.get('shell', 1.5) - 0.3)
                ca, sa = math.cos(a), math.sin(a)
                h = first(R, F.w(r0 * ca, r0 * sa, zc + dz), F.dir(ca, sa), rout[k] + 0.6 - r0)
                if h is None:
                    op[k] = True
        op = bridge(op, 3, cyclic=True)
        rl = run_list(op)
        if op[0] and op[-1] and len(rl) > 1:
            a0, b0 = rl.pop(0); a1, b1 = rl.pop(-1)
            rl.append((a1, b0 + 720))
        good = 0
        for a0, b0 in rl:
            k = (a0 + b0) // 2 % 720
            width = (b0 - a0 + 1) * 2 * math.pi / 720 * rout[k]
            if 0.06 <= width <= 0.9 and b0 > a0:
                good += 1
        sl.append(good)
        out.setdefault('slit_runs', []).append([round((b0 - a0 + 1) * 2 * math.pi / 720 * rout[(a0 + b0) // 2 % 720], 2) for a0, b0 in rl])
    out['slits'] = sl
    # walk doors toward connecting walls
    doors = {}
    for wid, pt in u.get('joints', {}).items():
        dx, dy = pt[0] - u['x'], pt[1] - u['y']
        L = math.hypot(dx, dy)
        best = 0
        for zc in (z0 + p['walk_level'] + 0.5, z0 + p['walk_level'] + 1.6):
            oks = 0
            for off in (-0.25, 0.0, 0.25):
                nx, ny = -dy / L, dx / L
                h = first(R, (u['x'] + nx * off, u['y'] + ny * off, zc), (dx / L, dy / L, 0), L + 0.3)
                oks += h is None
            best = max(best, oks)
        oks = best
        doors[wid] = oks >= 2
    out['doors'] = doors
    out['ground'] = ground_float(R, Rt, [F.w(a, b, 0)[:2] for a, b in poly_outline(tower_footprint_local(p, 0.2), 0.5)])
    return out

def densify(vs, polys, edges, step):
    """vertices plus points every <= step along every edge (edges list, else polygon edges)."""
    out = list(vs)
    E = list(edges or [])
    if not E:
        for p in polys or []:
            E.extend(zip(p, tuple(p[1:]) + tuple(p[:1])))
    seen = set()
    for a, b in E:
        key = (a, b) if a < b else (b, a)
        if key in seen:
            continue
        seen.add(key)
        A, B = vs[a], vs[b]
        k = int(math.dist(A, B) / step)
        for j in range(1, k + 1):
            f = j / (k + 1)
            out.append((A[0] + (B[0] - A[0]) * f, A[1] + (B[1] - A[1]) * f, A[2] + (B[2] - A[2]) * f))
    return out

def merge_u(us, tol):
    """cluster sorted positions closer than tol; returns cluster means"""
    out = []
    for x in sorted(us):
        if out and x - out[-1][-1] < tol:
            out[-1].append(x)
        else:
            out.append([x])
    return [round(sum(c) / len(c), 2) for c in out]

def grate_groups(verts, polys, u):
    """Portcullis grates as geometry, whether lowered or raised into the slot: mesh islands that are thin along the
    passage axis (<= 0.4 m) and lie in the passage band are grouped when their local bboxes touch; a group counts
    when it spans 90%..(100% + 2 m) of the passage width, is >= 0.4 x passage height tall, sits within the gatehouse
    depth, and has a level bottom edge (lowest points of 8 bins across the central 80% of the width within 0.3 m;
    rejects arch rings / trims) and its bottom no higher than passage height + 1 m (a raised grate hangs in its slot
    just above the passage; masonry above the slot is excluded). Returns the u (passage-axis) positions of the groups."""
    p, z0 = u['params'], u['z0']
    F = Frame(u['x'], u['y'], u['facing'])
    D, pw, ph, fs = p['depth'], p['passage_w'], p['passage_h'], p['flank_size']
    n = len(verts)
    if n == 0:
        return []
    par = list(range(n))
    def fd(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for q in polys:
        r0 = fd(q[0])
        for x in q[1:]:
            r1 = fd(x)
            if r1 != r0:
                par[r1] = r0
    L = []
    for v in verts:
        a, b = F.loc(v[0], v[1])
        L.append((a, b, v[2]))
    isl = {}
    for i in range(n):
        isl.setdefault(fd(i), []).append(i)
    poly_of = {}
    for q in polys:
        poly_of.setdefault(fd(q[0]), []).append(q)
    cand = []
    for r, idx in isl.items():
        us = [L[i][0] for i in idx]; vs = [L[i][1] for i in idx]; zs = [L[i][2] for i in idx]
        bb = [min(us), max(us), min(vs), max(vs), min(zs), max(zs)]
        if bb[1] - bb[0] > 0.4:
            continue
        if bb[3] < -pw / 2 - 1.0 or bb[2] > pw / 2 + 1.0 or bb[4] < z0 - 0.5 or bb[0] < -D / 2 - 0.5 or bb[1] > D / 2 + fs / 2 + 0.5:
            continue
        cand.append([bb, [r]])
    cand.sort(key=lambda c: c[0][0])
    # merge touching candidates (bbox overlap with 0.02 m margin)
    changed = True
    while changed:
        changed = False
        out = []
        for c in cand:
            for o in out:
                a, b = o[0], c[0]
                if a[0] - 0.02 <= b[1] and b[0] - 0.02 <= a[1] and a[2] - 0.02 <= b[3] and b[2] - 0.02 <= a[3] and a[4] - 0.02 <= b[5] and b[4] - 0.02 <= a[5]:
                    o[0] = [min(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), max(a[3], b[3]), min(a[4], b[4]), max(a[5], b[5])]
                    o[1].extend(c[1]); changed = True
                    break
            else:
                out.append(c)
        cand = out
    res = []
    for bb, roots in cand:
        if bb[1] - bb[0] > 0.6:
            continue
        span = bb[3] - bb[2]
        if span < 0.9 * pw or span > pw + 2.0 or abs((bb[2] + bb[3]) / 2) > 0.5:
            continue
        if bb[5] - bb[4] < 0.4 * ph or bb[4] > z0 + ph + 1.0:
            continue
        idx = [i for r in roots for i in isl[r]]
        loc_idx = dict((i, k) for k, i in enumerate(idx))
        pv = [L[i] for i in idx]
        pp = [tuple(loc_idx[i] for i in q) for r in roots for q in poly_of.get(r, [])]
        pts = densify(pv, pp, None, 0.1)
        nb = 8
        lows = [None] * nb
        for (a, b, z) in pts:
            k = int((b + 0.4 * pw) / (0.8 * pw) * nb)
            if 0 <= k < nb and (lows[k] is None or z < lows[k]):
                lows[k] = z
        lw = [x for x in lows if x is not None]
        if len(lw) < 6 or max(lw) - min(lw) > 0.3:
            continue
        res.append(round((bb[0] + bb[1]) / 2, 2))
    return res

def measure_gate(R, Rt, u):
    p, z0 = u['params'], u['z0']
    F = Frame(u['x'], u['y'], u['facing'])
    W, D, pw, fs = p['width'], p['depth'], p['passage_w'], p['flank_size']
    out = {}
    z = z0 + 1.0
    def ext(uu, vv, du, dv, far):
        h = first(R, F.w(uu + du * far, vv + dv * far, z), F.dir(-du, -dv), far + 2)
        return (far - h[0]) if h else None
    vp = ext(-D / 4, 0, 0, 1, W / 2 + 6); vm = ext(-D / 4, 0, 0, -1, W / 2 + 6)
    vm_ = (pw / 2 + W / 2 - fs) / 2
    up = ext(0, vm_, 1, 0, D / 2 + 8); um = ext(0, vm_, -1, 0, D / 2 + 8)
    out['present'] = None not in (vp, vm, up, um)
    if not out['present']:
        return out
    out['W'] = round(vp + vm, 3); out['D'] = round(up + um, 3)
    out['cu'] = round((up - um) / 2, 3); out['cv'] = round((vp - vm) / 2, 3)
    out['u_front'] = round(up, 3)
    a = first(R, F.w(0, 0, z0 + 1.5), F.dir(0, 1), W); b = first(R, F.w(0, 0, z0 + 1.5), F.dir(0, -1), W)
    out['pw'] = round(a[0] + b[0], 3) if a and b else None
    h = first(R, F.w(0, 0, z0 + 0.1), (0, 0, 1), 40)
    out['ph'] = round(0.1 + h[0], 3) if h else None
    # arch at outer mouth
    um0 = up - 0.3
    hs = []
    for vv in (0.0, -pw / 4, pw / 4):
        h = first(R, F.w(um0, vv, z0 + 0.2), (0, 0, 1), 40)
        hs.append(0.2 + h[0] if h else None)
    if None not in hs:
        drop = hs[0] - (hs[1] + hs[2]) / 2
        out['arch_drop_ratio'] = round(drop / pw, 4)
        out['arch'] = 'pointed' if drop >= 0.13 * pw else 'round'
    else:
        out['arch'] = None
    # portcullises: u-slices where vertical rays below the passage ceiling hit a grate across >=90% of width
    nv = 11
    ufl = []
    us = []
    uu = -D / 2 - 0.5
    while uu <= D / 2 + fs / 2 + 0.5:
        hit_idx = []
        for k in range(nv):
            vv = -pw / 2 + 0.1 + (pw - 0.2) * k / (nv - 1)
            hc = first(R, F.w(uu, vv, z0 + 0.3), (0, 0, 1), 30)
            if hc is None:
                continue
            ztop = z0 + 0.3 + hc[0] - 0.05
            h = first(R, F.w(uu, vv, ztop), (0, 0, -1), ztop - z0)
            if h is not None and ztop - h[0] > z0 + 0.2:
                hit_idx.append(k)
        ufl.append(len(hit_idx) >= 6 and (max(hit_idx) - min(hit_idx)) / (nv - 1) >= 0.9)
        us.append(uu)
        uu += 0.02
    rl = run_list(ufl)
    merged = []
    for a0, b0 in rl:
        if merged and us[a0] - us[merged[-1][1]] < 0.3:
            merged[-1] = (merged[-1][0], b0)
        else:
            merged.append((a0, b0))
    out['portcullises'] = len(merged)
    out['portcullis_u'] = [round((us[a0] + us[b0]) / 2, 2) for a0, b0 in merged]
    # flank towers: protruding part area ratio vs fs x fs/2 rectangle at +2 m
    shapes, ratios = [], []
    for s in (-1, 1):
        c = s * (W / 2 - fs / 2)
        ra = raster(R, F, z0 + 2.0, up + 0.05, up + fs / 2 + 1.5, c - fs / 2 - 1.0, c + fs / 2 + 1.0, 0.05)
        cs = comps(ra, 20)
        area = max([x['area'] for x in cs]) if cs else 0.0
        ratio = area / (fs * fs / 2)
        ratios.append(round(ratio, 3))
        shapes.append(None if ratio < 0.4 else ('round' if ratio < 0.89 else 'square'))
    out['flank_ratio'] = ratios
    out['flank_towers'] = shapes[0] if shapes[0] == shapes[1] else None
    # front merlons between flank towers
    zt = z0 + p['height']
    thr = zt + p['parapet'] - 0.3
    flags = []
    vv = -(W / 2 - fs) + 0.1
    while vv <= (W / 2 - fs) - 0.1:
        h = first(R, F.w(up - 0.3, vv, zt + 6), (0, 0, -1), 10)
        flags.append(bool(h and zt + 6 - h[0] > thr))
        vv += 0.05
    out['merlons'] = runs(flags, gap=2)
    gp = []
    for a, b in poly_outline([(-D / 2 + 0.2, -W / 2 + 0.2), (D / 2 - 0.2, -W / 2 + 0.2), (D / 2 - 0.2, W / 2 - 0.2), (-D / 2 + 0.2, W / 2 - 0.2)], 0.5):
        if abs(b) < pw / 2 + 0.3:
            continue
        gp.append(F.w(a, b, 0)[:2])
    out['ground'] = ground_float(R, Rt, gp)
    return out

def measure_wall(R, Rt, Rn, w):
    p = w['params']; ea, eb = w['end_a'], w['end_b']
    t = p['thickness']; par = p['parapet']
    ax, ay = eb[0] - ea[0], eb[1] - ea[1]
    Lc = math.hypot(ax, ay); ax, ay = ax / Lc, ay / Lc
    nx, ny = -ay, ax
    if w['out_sign'] < 0:
        nx, ny = -nx, -ny
    za, zb = ea[2], eb[2]
    def P(s, o, z): return (ea[0] + ax * s + nx * o, ea[1] + ay * s + ny * o, z)
    def zw(s): return za + (zb - za) * s / Lc
    out = {'L': round(Lc, 3)}
    th, off, miss = [], [], 0
    s = 0.5
    while s < Lc - 0.25:
        z = zw(s) - 1.0
        o = P(s, t / 2 + 4, z)
        d = (-nx, -ny, 0.0)
        ivs = segs(R, o, d, t + 8)
        best = None
        for a, b in ivs:
            oa, ob = t / 2 + 4 - a, t / 2 + 4 - b
            if ob <= t / 2 and oa >= -t / 2:
                if best is None or abs((oa + ob) / 2) < abs((best[0] + best[1]) / 2):
                    best = (oa, ob)
        if best is None:
            miss += 1
        else:
            th.append(round(best[0] - best[1], 3)); off.append(round((best[0] + best[1]) / 2, 3))
        s += 1.0
    out['th'] = th; out['off'] = off; out['miss'] = miss
    # walk surface every 0.5 m (0.3 m inside the parapet inner face)
    walk = []
    s = 0.25
    while s < Lc:
        h = first(R, P(s, t / 2 - 0.9, zw(s) + par + 6), (0, 0, -1), par + 12)
        walk.append((round(s, 2), round(zw(s) + par + 6 - h[0], 3) if h else None))
        s += 0.5
    out['walk'] = walk
    def walk_at(s):
        k = min(len(walk) - 1, max(0, int(round((s - 0.25) / 0.5))))
        z = walk[k][1] if walk else None
        return z if z is not None else zw(s)
    # parapet top & merlons along both parapet lines
    for key, side in (('out', 1), ('in', -1)):
        tops, flags = [], []
        s = 0.05
        while s < Lc - 0.025:
            wz = walk_at(s)
            h = first(R, P(s, side * (t / 2 - 0.3), wz + par + 6), (0, 0, -1), par + 12)
            ztop = (wz + par + 6 - h[0]) if h else None
            tops.append((round(s, 2), round(ztop - wz, 3) if ztop is not None else None))
            flags.append(bool(ztop is not None and ztop > wz + par - 0.3))
            s += 0.05
        out['merlons_' + key] = runs(flags, gap=2)
        if key == 'out':
            pars = []
            for k in range(0, len(tops), 20):
                win = [x[1] for x in tops[max(0, k - 30):k + 30] if x[1] is not None]
                pars.append(round(max(win), 3) if win else None)
            out['parapet'] = pars
    # slits: horizontal rays through the wall body at several heights between foot and walk (the sheets give no
    # slit height); a station is open if the ray passes the wall at any of them
    flags = []
    s = 0.3
    while s < Lc - 0.3:
        x, y, _ = P(s, 0, 0)
        zt = terrain_z(Rt, x, y)
        zb_ = zt if zt is not None else zw(s) - 8
        zw_ = walk_at(s)
        opn = False
        for fz in (0.15, 0.3, 0.45, 0.6, 0.75, 0.9):
            zz = zb_ + fz * (zw_ - zb_)
            if first(R, P(s, t / 2 + 0.4, zz), (-nx, -ny, 0.0), t + 0.8) is None:
                opn = True
                break
        flags.append(opn)
        s += 0.05
    out['slits'] = runs(flags, gap=2, min_len=2)
    # buttresses on inner side: solid 0.75 m beyond inner face, 2 m below walk
    flags = []
    s = 0.5
    while s < Lc - 0.5:
        flags.append(inside(R, P(s, -(t / 2 + 0.75), walk_at(s) - 2.0)))
        s += 0.05
    out['buttresses'] = runs(flags, gap=2)
    # grounding along both face lines
    gp = []
    s = 0.25
    while s < Lc:
        for o in (t / 2 - 0.1, -(t / 2 - 0.1)):
            gp.append(P(s, o, 0)[:2])
        s += 0.5
    out['ground'] = ground_float(R, Rt, gp)
    # joints
    joints = {}
    for end, node, E0, dvec, nref in (('a', p['node_a'], ea, (-ax, -ay, 0.0), w['ref_a']), ('b', p['node_b'], eb, (ax, ay, 0.0), w['ref_b'])):
        RN = Rn.get(node)
        res = []
        sE = 0.0 if end == 'a' else Lc
        x0, y0, _ = P(sE, 0, 0)
        zt = terrain_z(Rt, x0, y0)
        dref = math.hypot(nref[0] - x0, nref[1] - y0)
        for lat in (t / 2 - 0.1, -(t / 2 - 0.1)):
            for zz in (E0[2] - 1.0, (zt if zt is not None else E0[2] - 8) + 0.5):
                q = P(sE, lat, zz)
                rec = {'lat': round(lat, 2), 'z': round(zz, 2)}
                o = _add(q, _mul(dvec, -3.0))
                ivn = segs(RN, o, dvec, dref + 15) if RN else []
                sn = (ivn[0][0] - 3.0) if ivn else None
                sin_ = (ivn[0][1] - 3.0) if ivn else 1e9
                far = dref + 6.0
                h = first(R, _add(q, _mul(dvec, far)), _mul(dvec, -1.0), far + 6)
                sw = (far - h[0]) if h else None
                rec['s_node'] = round(sn, 3) if sn is not None else None
                rec['s_inner'] = round(sin_, 3) if sin_ < 1e8 else None
                rec['s_wall'] = round(sw, 3) if sw is not None else None
                res.append(rec)
        joints[end] = res
    out['joints'] = joints
    return out

def measure_keep(R, Rt, u):
    p, z0 = u['params'], u['z0']
    F = Frame(u['x'], u['y'], u['facing'])
    L, W, fb = p['length'], p['width'], p['forebuilding']
    out = {}
    z = z0 + 1.0
    def ext(uu, vv, du, dv, far):
        h = first(R, F.w(uu + du * far, vv + dv * far, z), F.dir(-du, -dv), far + 2)
        return (far - h[0]) if h else None
    up = ext(0, L / 4, 1, 0, W / 2 + 10); um = ext(0, L / 4, -1, 0, W / 2 + 10)
    vp = ext(-W / 4, 0, 0, 1, L / 2 + 8); vm = ext(-W / 4, 0, 0, -1, L / 2 + 8)
    out['present'] = None not in (up, um, vp, vm)
    if not out['present']:
        return out
    out['W'] = round(up + um, 3); out['L'] = round(vp + vm, 3)
    out['cu'] = round((up - um) / 2, 3); out['cv'] = round((vp - vm) / 2, 3)
    ufb = ext(0, 0, 1, 0, W / 2 + 12)
    out['fore_ext'] = round(ufb - up, 3) if ufb is not None else None
    Hp = p['platform_level']
    ztop = z0 + Hp + 3.5 + p.get('roof_rise', 0) + 10
    cnts, plats, firsts = [], [], []
    for (du, dv) in ((1.1, 1.3), (-1.4, 0.9), (0.7, -1.6)):
        x, y, _ = F.w(du, dv, 0)
        lv = down_levels(R, x, y, ztop, z0 - 1)
        if lv: firsts.append(lv[0])
        ups = [zz for zz, nz in lv if nz > 0.9 and zz > z0 + 0.5]
        cnts.append(len(ups)); plats.append(max(ups) if ups else None)
    cnts.sort(); out['storeys'] = cnts[1]
    pl = sorted(x for x in plats if x is not None)
    out['platform_z'] = pl[len(pl) // 2] if pl else None
    h = first(R, F.w(0, 0, ztop), (0, 0, -1), ztop - z0)
    out['roof_top'] = round(ztop - h[0], 3) if h else None
    fz = firsts[0] if firsts else None
    if fz and out['platform_z'] is not None:
        out['roof'] = 'platform' if (fz[1] > 0.9 and fz[0] <= out['platform_z'] + 0.3) else (
            'pyramid' if out['roof_top'] is not None and out['roof_top'] >= out['platform_z'] + 1.0 + 0.8 * p.get('roof_rise', 5.0) else 'other')
    else:
        out['roof'] = None
    # turrets
    zpl = out['platform_z'] if out['platform_z'] is not None else z0 + Hp
    ra = raster(R, F, zpl + 2.6, -W / 2 - 4, W / 2 + 4, -L / 2 - 4, L / 2 + 4, 0.05)
    cu, cv = out['cu'], out['cv']
    for j in range(ra['nv']):
        v = ra['v0'] + (j + 0.5) * 0.05
        for i in range(ra['nu']):
            uu = ra['u0'] + (i + 0.5) * 0.05
            if abs(uu - cu) < W / 2 + 0.05 and abs(v - cv) < L / 2 + 0.05:
                ra['g'][j][i] = 0
    cs = [c for c in comps(ra, 20) if c['area'] >= 0.8]
    out['turrets'] = len(cs)
    ds = []
    for su in (-1, 1):
        for sv in (-1, 1):
            cu0, cv0 = cu + su * W / 2, cv + sv * L / 2
            rr = []
            for du, dv in ((su, 0), (0, sv)):
                h = first(R, F.w(cu0 + du * 6, cv0 + dv * 6, zpl + 2.6), F.dir(-du, -dv), 8)
                if h:
                    rr.append(6 - h[0])
            if len(rr) == 2 and min(rr) > 0.5:
                ds.append(round(rr[0] + rr[1], 3))
    out['turret_d'] = ds
    # windows per long side (faces normal to u), storeys 2..N
    N = p['storeys']
    win = []
    for s in range(1, N):
        zc = z0 + Hp * (s + 0.5) / N
        per = []
        for side in (1, -1):
            flags = []
            vv = -L / 2 + 2.5
            while vv <= L / 2 - 2.5:
                h = first(R, F.w(0, vv, zc), F.dir(side, 0), W / 2 + 0.3)
                flags.append(h is None)
                vv += 0.05
            per.append(runs(flags))
        win.append(per)
    out['windows'] = win
    gp = [F.w(a, b, 0)[:2] for a, b in poly_outline([(-W / 2 + 0.2, -L / 2 + 0.2), (W / 2 - 0.2, -L / 2 + 0.2), (W / 2 - 0.2, L / 2 - 0.2), (-W / 2 + 0.2, L / 2 - 0.2)], 0.5)
          if not (a > W / 2 - 0.5 and abs(b) < fb['length'] / 2 + 0.3)]
    out['ground'] = ground_float(R, Rt, gp)
    return out

def measure_chapel(R, Rt, u):
    p, z0 = u['params'], u['z0']
    F = Frame(u['x'], u['y'], u['facing'])
    L, W, nb = p['nave_length'], p['nave_width'], p['bays']
    out = {}
    z = z0 + 0.5
    def ext(uu, vv, du, dv, far, zz=None):
        h = first(R, F.w(uu + du * far, vv + dv * far, zz if zz is not None else z), F.dir(-du, -dv), far + 2)
        return (far - h[0]) if h else None
    ws = []
    for j in range(nb):
        uu = -L / 2 + L * (j + 0.5) / nb
        a, b = ext(uu, 0, 0, 1, W / 2 + 6), ext(uu, 0, 0, -1, W / 2 + 6)
        if a is not None and b is not None:
            ws.append((a, b))
    up = ext(0, W / 4, 1, 0, L / 2 + 8); um = ext(0, W / 4, -1, 0, L / 2 + W / 2 + 8)
    out['present'] = bool(ws) and up is not None and um is not None
    if not out['present']:
        return out
    ws.sort(key=lambda x: x[0] + x[1])
    a, b = ws[len(ws) // 2]
    out['W'] = round(a + b, 3); out['cv'] = round((a - b) / 2, 3)
    out['u_west'] = round(up, 3); out['u_east'] = round(-um, 3)
    # entrance on facing side
    h = first(R, F.w(up + 3, 0, z0 + 1.0), F.dir(-1, 0), L + 6)
    out['entrance'] = (h is None) or (up + 3 - h[0] < up - 0.25)
    # ridge & eave
    ztop = z0 + p['ridge'] + 8
    h = first(R, F.w(0, 0, ztop), (0, 0, -1), 30)
    out['ridge_z'] = round(ztop - h[0], 3) if h else None
    eav = []
    for sv in (1, -1):
        zz = []
        for vv in (W / 4, W / 2 - 0.3):
            h = first(R, F.w(-L / 2 + L * 1.5 / nb, sv * vv, ztop), (0, 0, -1), 30)
            zz.append(ztop - h[0] if h else None)
        if None not in zz:
            slope = (zz[1] - zz[0]) / (W / 2 - 0.3 - W / 4)
            eav.append(zz[1] + slope * 0.3)
    out['eave_z'] = round(sum(eav) / len(eav), 3) if eav else None
    # windows (bays) and buttresses per side
    zw = z0 + p['eave'] * 0.55
    wins, butts = [], []
    for sv in (1, -1):
        flags = []
        uu = -L / 2 + 0.5
        while uu <= L / 2 - 0.5:
            h = first(R, F.w(uu, 0, zw), F.dir(0, sv), W / 2 + 0.3)
            flags.append(h is None)
            uu += 0.05
        wins.append(runs(flags))
        flags = []
        uu = -L / 2 - 0.8
        while uu <= L / 2 + 0.8:
            h = first(R, F.w(uu, sv * (W / 2 + 2.5), z0 + 1.0), F.dir(0, -sv), 2.5)
            flags.append(bool(h and h[0] < 2.1))
            uu += 0.05
        butts.append(runs(flags))
    out['windows'] = wins; out['butts'] = butts
    # apse profile from east-end centre
    ue = -L / 2
    prof = []
    for k in range(-15, 16):
        a = math.radians(5 * k)
        du, dv = -math.cos(a), math.sin(a)
        h = first(R, F.w(ue + du * 12, dv * 12, z0 + 1.5), F.dir(-du, -dv), 12.5)
        prof.append(round(12 - h[0], 3) if h else None)
    out['apse_prof'] = prof
    ev = [x for x in prof if x is not None]
    if ev:
        mx, mn = max(ev), min(ev)
        if mx < 0.4:
            out['apse'] = 'flat'
        else:
            mid = [x for x in prof[9:22] if x is not None]
            m = sum(mid) / len(mid) if mid else mx
            out['apse'] = 'semicircular' if mid and (max(mid) - min(mid)) / m < 0.03 else 'polygonal'
    else:
        out['apse'] = None
    # bell openings in the bell-cote on the west gable
    zb = z0 + p['ridge'] + 1.05
    flags = []
    vv = -3.0
    while vv <= 3.0:
        h = first(R, F.w(up + 4, vv, zb), F.dir(-1, 0), 8)
        flags.append(h is not None)
        vv += 0.05
    if any(flags):
        i0 = flags.index(True); i1 = len(flags) - 1 - flags[::-1].index(True)
        out['bell_openings'] = runs([not f for f in flags[i0:i1 + 1]])
    else:
        out['bell_openings'] = 0
    gp = [F.w(a, b, 0)[:2] for a, b in poly_outline([(-L / 2 + 0.2, -W / 2 + 0.2), (L / 2 - 0.2, -W / 2 + 0.2), (L / 2 - 0.2, W / 2 - 0.2), (-L / 2 + 0.2, W / 2 - 0.2)], 0.5)
          if not (a > L / 2 - 0.5 and abs(b) < 1.2)]
    out['ground'] = ground_float(R, Rt, gp)
    return out

def measure_well(R, Rt, u):
    p, z0 = u['params'], u['z0']
    F = Frame(u['x'], u['y'], u['facing'])
    d = p['diameter']
    out = {}
    rs = []
    for k in range(16):
        a = 2 * math.pi * (k + 0.5) / 16
        h = first(R, F.w(math.cos(a) * 6, math.sin(a) * 6, z0 + 0.5), F.dir(-math.cos(a), -math.sin(a)), 6.5)
        if h:
            rs.append(6 - h[0])
    out['present'] = len(rs) >= 8
    if not out['present']:
        return out
    rs.sort()
    out['diameter'] = round(2 * rs[len(rs) // 2], 3)
    ax = []
    for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        h = first(R, F.w(du * 6, dv * 6, z0 + 0.5), F.dir(-du, -dv), 6.5)
        ax.append(6 - h[0] if h else None)
    if None not in ax:
        out['cu'] = round((ax[0] - ax[1]) / 2, 3); out['cv'] = round((ax[2] - ax[3]) / 2, 3)
    ct = []
    for a in (45, 135, 225, 315):
        r = d / 2 - 0.2
        x, y, _ = F.w(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), 0)
        lv = down_levels(R, x, y, z0 + 10, z0 - 1)
        c = [zz for zz, nz in lv if nz > 0.7 and zz < z0 + 1.5]
        if c: ct.append(max(c))
    ct.sort()
    out['curb_top'] = ct[len(ct) // 2] if ct else None
    grid = []
    span = d / 2 + 0.3
    for i in range(9):
        uu = -span + 2 * span * i / 8
        row = []
        for j in range(9):
            vv = -span + 2 * span * j / 8
            h = first(R, F.w(uu, vv, z0 + 12), (0, 0, -1), 12 - 2.0)
            row.append(round(z0 + 12 - h[0], 3) if h else None)
        grid.append(row)
    allz = [z for r in grid for z in r if z is not None]
    out['canopy_top'] = max(allz) if allz else None
    if allz and max(allz) - min(allz) > 0.3:
        rngv = []
        for r in grid:
            zz = [z for z in r if z is not None]
            if len(zz) >= 5:
                rngv.append(max(zz) - min(zz))
        rngv.sort()
        out['roof'] = 'gable' if rngv and rngv[len(rngv) // 2] < 0.2 else 'pyramid'
    else:
        out['roof'] = 'flat' if allz else None
    ra = raster(R, F, z0 + 2.2, -d / 2 - 1.5, d / 2 + 1.5, -d / 2 - 1.5, d / 2 + 1.5, 0.02)
    out['posts'] = len(comps(ra, 25))
    out['ground'] = ground_float(R, Rt, [F.w((d / 2 - 0.15) * math.cos(k * math.pi / 8), (d / 2 - 0.15) * math.sin(k * math.pi / 8), 0)[:2] for k in range(16)])
    return out

def measure_stables(R, Rt, u):
    p, z0 = u['params'], u['z0']
    F = Frame(u['x'], u['y'], u['facing'])
    L, D = p['length'], p['depth']
    out = {}
    ub = []
    for vv in (-L / 4, 0.0, L / 4):
        h = first(R, F.w(-2.0, vv, z0 + 1.0), F.dir(1, 0), D + 4)
        ub.append(round(-2.0 + h[0], 3) if h else None)
    out['u_back'] = ub
    a = first(R, F.w(D / 2, L / 2 + 6, z0 + 1.0), F.dir(0, -1), L + 12)
    b = first(R, F.w(D / 2, -L / 2 - 6, z0 + 1.0), F.dir(0, 1), L + 12)
    out['present'] = a is not None and b is not None and None not in ub
    if not out['present']:
        return out
    vmax, vmin = L / 2 + 6 - a[0], -L / 2 - 6 + b[0]
    out['L'] = round(vmax - vmin, 3); out['cv'] = round((vmax + vmin) / 2, 3)
    hs = [first(R, F.w(D + 3, vv, z0 + 0.5), F.dir(-1, 0), D + 4) for vv in (-L / 4, L / 4)]
    out['u_front'] = round(sum(D + 3 - h[0] for h in hs if h) / max(1, sum(1 for h in hs if h)), 3)
    rt = getattr(R, 'ray_tag', None)
    def count_open(zz):
        # an opening / door bay = open doorway, OR a leaf recessed >= 0.03 m behind the facade plane, OR a leaf whose
        # material differs from the facade's dominant material (flush timber leaves in a masonry/plaster front);
        # runs must be >= 0.5 m wide (10 samples) so posts / joints / trims are not counted
        flags, firsts, tags = [], [], []
        vv = vmin + 0.1
        while vv <= vmax - 0.1:
            h = rt(F.w(D + 3, vv, zz), F.dir(-1, 0), D + 4) if rt else first(R, F.w(D + 3, vv, zz), F.dir(-1, 0), D + 4)
            firsts.append(D + 3 - h[0] if h else None)
            tags.append(h[2] if (h and len(h) > 2) else None)
            vv += 0.05
        zs = sorted(x for x in firsts if x is not None)
        face = zs[min(len(zs) - 1, int(len(zs) * 0.8))] if zs else D
        cnt = {}
        for x, tg in zip(firsts, tags):
            if x is not None and tg is not None and abs(x - face) <= 0.03:
                cnt[tg] = cnt.get(tg, 0) + 1
        dom = max(cnt, key=cnt.get) if cnt else None
        for x, tg in zip(firsts, tags):
            flags.append(x is None or x < face - 0.03 or (dom is not None and tg is not None and tg != dom))
        return runs(flags, min_len=10)
    out['stall_doors'] = count_open(z0 + 1.1)
    out['loft_openings'] = count_open(z0 + 2.75)
    gp = [F.w(a_, b_, 0)[:2] for a_, b_ in poly_outline([(0.2, -L / 2 + 0.2), (D - 0.2, -L / 2 + 0.2), (D - 0.2, L / 2 - 0.2), (0.2, L / 2 - 0.2)], 0.5)
          if a_ < D - 0.5]
    out['ground'] = ground_float(R, Rt, gp)
    return out
'''

# ----------------------------------------------------------------------------------------------------------------
# Blender glue (builds BVHs, runs _CORE, drawbridge animation)
# ----------------------------------------------------------------------------------------------------------------
_GLUE = r'''
import json, math, traceback
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
CFG = json.loads(__CFG__)
W2 = {'errors': []}
EXTRA['w02'] = W2
GEOM_TYPES = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}

class RB:
    def __init__(self, verts, polys, tags=None):
        self.t = BVHTree.FromPolygons(verts, polys, all_triangles=False) if polys else None
        self.tags = tags if tags and len(tags) == len(polys) else None
    def ray(self, o, d, maxd):
        if self.t is None or maxd <= 0:
            return None
        loc, nor, idx, dist = self.t.ray_cast(Vector(o), Vector(d), maxd)
        if loc is None:
            return None
        return dist, (nor.x, nor.y, nor.z)
    def ray_tag(self, o, d, maxd):
        """like ray() but also returns the material name of the hit polygon (None if tags unavailable)"""
        if self.t is None or maxd <= 0:
            return None
        loc, nor, idx, dist = self.t.ray_cast(Vector(o), Vector(d), maxd)
        if loc is None:
            return None
        tg = self.tags[idx] if (self.tags is not None and idx is not None and 0 <= idx < len(self.tags)) else None
        return dist, (nor.x, nor.y, nor.z), tg
    def near(self, p):
        if self.t is None:
            return None
        r = self.t.find_nearest(Vector(p))
        return r[3] if r[0] is not None else None

def owner_map(groups):
    """groups: key -> set(object names). returns name -> [keys]"""
    m = {}
    for k, names in groups.items():
        for n in names:
            m.setdefault(n, []).append(k)
    return m

def gather(groups, tag_keys=(), edge_keys=()):
    """evaluated geometry (instances included) per group key: [verts, polys, faces_max, n_verts, poly_tags, edges]
    poly_tags (material name per polygon) only for keys in tag_keys; edges (all mesh edges, incl. loose edges of
    un-bevelled curves) only for keys in edge_keys."""
    dg = bpy.context.evaluated_depsgraph_get()
    om = owner_map(groups)
    acc = dict((k, [[], [], 0, 0, [], []]) for k in groups)
    for inst in dg.object_instances:
        try:
            own = inst.parent if inst.is_instance else inst.object
            on = own.original.name if own is not None else None
            keys = om.get(on)
            if not keys and inst.is_instance:
                on2 = inst.object.original.name
                keys = None
            if not keys:
                continue
            ob = inst.object
            if ob.type not in GEOM_TYPES:
                continue
            mw = inst.matrix_world.copy()
            me = ob.to_mesh()
            if me is None:
                continue
            vs = [tuple(mw @ v.co) for v in me.vertices]
            ps = [tuple(p.vertices) for p in me.polygons]
            nf = len(ps)
            tg = None
            if any(k in tag_keys for k in keys):
                try:
                    sls = [sl.material for sl in ob.material_slots]
                except Exception:
                    sls = []
                mms = list(me.materials)
                mats = []
                for i in range(max(len(sls), len(mms))):
                    m_ = sls[i] if i < len(sls) and sls[i] is not None else (mms[i] if i < len(mms) else None)
                    mats.append(m_.name if m_ is not None else '')
                tg =[(mats[p.material_index] if p.material_index < len(mats) else '') for p in me.polygons]
            es = [tuple(e.vertices) for e in me.edges] if any(k in edge_keys for k in keys) else None
            ob.to_mesh_clear()
            for k in keys:
                a = acc[k]
                off = len(a[0])
                a[0].extend(vs)
                a[1].extend(tuple(off + i for i in p) for p in ps)
                a[2] = max(a[2], nf)
                a[3] += len(vs)
                if k in tag_keys and tg is not None:
                    a[4].extend(tg)
                if k in edge_keys and es is not None:
                    a[5].extend((off + i, off + j) for i, j in es)
        except Exception:
            W2['errors'].append('gather: ' + traceback.format_exc()[-300:])
    return acc

def coll_names(cname):
    c = bpy.data.collections.get(cname)
    if c is None:
        return None
    return set(o.name for o in c.all_objects)

def descendants(name):
    out = {name}
    ch = True
    while ch:
        ch = False
        for o in bpy.data.objects:
            if o.parent is not None and o.parent.name in out and o.name not in out:
                out.add(o.name); ch = True
    return out

scene.frame_set(120)
groups = {}
for uid in CFG['units']:
    s = coll_names(uid)
    if s:
        groups[uid] = s
tob = bpy.data.objects.get('TERRAIN')
if tob is not None:
    groups['__TERRAIN__'] = {'TERRAIN'}
deck = bpy.data.objects.get('B01_DECK')
deck_set = descendants('B01_DECK') if deck is not None else set()
if deck_set:
    groups['__DECK__'] = deck_set
G = gather(groups, tag_keys=('S01',))
W2['faces_max'] = dict((k, v[2]) for k, v in G.items())
W2['n_verts'] = dict((k, v[3]) for k, v in G.items())
RS = {}
for k, v in G.items():
    try:
        RS[k] = RB(v[0], v[1], v[4] if k == 'S01' else None)
    except Exception:
        W2['errors'].append('bvh %s: %s' % (k, traceback.format_exc()[-200:]))
Rt = RS.get('__TERRAIN__')
# M01 terrain probes
W2['terrain_probe'] = [terrain_z(Rt, x, y) if Rt else None for x, y in CFG['probes']]
# static units at frame 120
U = {}
for uid, u in CFG['units'].items():
    R = RS.get(uid)
    if R is None or R.t is None:
        U[uid] = {'present': False, 'reason': 'no collection/geometry'}
        continue
    try:
        typ = u['type']
        if typ == 'tower':
            U[uid] = measure_tower(R, Rt, u)
        elif typ == 'gatehouse':
            U[uid] = measure_gate(R, Rt, u)
            if U[uid].get('present'):
                # portcullis grates anywhere in their slots (lowered or raised): thin grate-like mesh groups
                try:
                    gi = grate_groups(G[uid][0], G[uid][1], u)
                    U[uid]['portcullis_groups_u'] = gi
                    U[uid]['portcullis_ray_u'] = U[uid].get('portcullis_u', [])
                    allu = merge_u(list(U[uid].get('portcullis_u', [])) + list(gi), 0.3)
                    U[uid]['portcullis_u'] = allu
                    U[uid]['portcullises'] = len(allu)
                except Exception:
                    W2['errors'].append('grate_groups %s: %s' % (uid, traceback.format_exc()[-300:]))
        elif typ == 'wall':
            Rn = dict((n, RS.get(n)) for n in (u['params']['node_a'], u['params']['node_b']))
            U[uid] = measure_wall(R, Rt, Rn, u)
        elif typ == 'keep':
            U[uid] = measure_keep(R, Rt, u)
        elif typ == 'chapel':
            U[uid] = measure_chapel(R, Rt, u)
        elif typ == 'well':
            U[uid] = measure_well(R, Rt, u)
        elif typ == 'stables':
            U[uid] = measure_stables(R, Rt, u)
    except Exception:
        U[uid] = {'present': None, 'error': traceback.format_exc()[-600:]}
W2['units'] = U

# ---- drawbridge B01 (deck + chains + abutment)
BR = {}
W2['bridge'] = BR
try:
    bcfg = CFG['bridge']
    H = bcfg['hinge']; f = math.radians(bcfg['facing'])
    Uv = (math.cos(f), math.sin(f)); Vv = (-math.sin(f), math.cos(f))
    def lc(p):
        dx, dy = p[0] - H[0], p[1] - H[1]
        return dx * Uv[0] + dy * Uv[1], dx * Vv[0] + dy * Vv[1], p[2]
    b01 = coll_names('B01') or set()
    if 'B01_DECK' in b01 and '__DECK__' in G:
        dv = G['__DECK__'][0]; dp = G['__DECK__'][1]
        L = [lc(p) for p in dv]
        umin = min(x[0] for x in L); umax = max(x[0] for x in L)
        BR['deck_u'] = [round(umin, 3), round(umax, 3)]
        BR['deck_v'] = [round(min(x[1] for x in L), 3), round(max(x[1] for x in L), 3)]
        BR['deck_top'] = round(max(x[2] for x in L), 3)
        hn = [i for i, x in enumerate(L) if x[0] <= umin + 0.1]
        tp = [i for i, x in enumerate(L) if x[0] >= umax - 0.1]
        zh = max(L[i][2] for i in hn); zt_ = max(L[i][2] for i in tp)
        hn = [i for i in hn if L[i][2] >= zh - 0.05]
        tp = [i for i in tp if L[i][2] >= zt_ - 0.05]
        cmin = min(tp, key=lambda i: L[i][1]); cmax = max(tp, key=lambda i: L[i][1])
        # planks: islands of the deck mesh at frame 120
        par = list(range(len(dv)))
        def fd(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for p in dp:
            r0 = fd(p[0])
            for q in p[1:]:
                r1 = fd(q)
                if r1 != r0:
                    par[r1] = r0
        isl = {}
        for i in range(len(dv)):
            isl.setdefault(fd(i), []).append(i)
        wexp = bcfg['deck_width']
        pk = 0
        for k, idx in isl.items():
            us = [L[i][0] for i in idx]; vs = [L[i][1] for i in idx]
            if max(vs) - min(vs) >= 0.9 * wexp and max(us) - min(us) <= 1.5:
                pk += 1
        BR['islands'] = len(isl); BR['planks'] = pk
        # chain objects: B01 members (not deck) reaching > deck top + 0.5 at frame 120
        others = b01 - deck_set
        g2 = gather(dict((n, {n}) for n in others), edge_keys=set(others))
        chain_names = set(n for n, v in g2.items() if v[0] and max(p[2] for p in v[0]) > BR['deck_top'] + 0.5)
        abut_names = set(n for n, v in g2.items() if v[0]) - chain_names
        BR['chain_objects'] = sorted(chain_names)[:20]
        BR['abut_objects'] = sorted(abut_names)[:20]
        # chain count by proximity clustering (0.15 m cells, 26-neighbourhood) of the chain vertices plus points
        # every <=0.1 m along every mesh edge (polygon edges and loose curve edges), so that a chain modelled as a
        # stretched cylinder / bevelled curve / plain curve with long edges stays one connected component
        cv_ = []
        for n in chain_names:
            cv_.extend(densify(g2[n][0], g2[n][1], g2[n][5], 0.1))
        cellset = set((int(math.floor(p[0] / 0.15)), int(math.floor(p[1] / 0.15)), int(math.floor(p[2] / 0.15))) for p in cv_)
        seen = set(); ncomp = 0
        for c in cellset:
            if c in seen:
                continue
            ncomp += 1
            st = [c]; seen.add(c)
            while st:
                a = st.pop()
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for dz in (-1, 0, 1):
                            b = (a[0] + dx, a[1] + dy, a[2] + dz)
                            if b in cellset and b not in seen:
                                seen.add(b); st.append(b)
        BR['chains'] = ncomp
        # abutment
        Ra = None
        if abut_names:
            av, ap = [], []
            for n in abut_names:
                off = len(av); av.extend(g2[n][0]); ap.extend(tuple(off + i for i in p) for p in g2[n][1])
            Ra = RB(av, ap)
        ab = []
        for uu in bcfg['abut_u']:
            for vv in (-0.8, 0.0, 0.8):
                x = H[0] + uu * Uv[0] + vv * Vv[0]; y = H[1] + uu * Uv[1] + vv * Vv[1]
                rec = {'u': uu, 'v': vv}
                h = Ra.ray((x, y, H[2] + 3), (0, 0, -1), 30) if Ra else None
                rec['top'] = round(H[2] + 3 - h[0], 3) if h else None
                zt = terrain_z(Rt, x, y) if Rt else None
                rec['terrain'] = round(zt, 3) if zt is not None else None
                if zt is not None and Ra:
                    h2 = Ra.ray((x, y, zt - 15), (0, 0, 1), 40)
                    rec['bottom'] = round(zt - 15 + h2[0], 3) if h2 else None
                ab.append(rec)
        BR['abutment'] = ab
        # animation
        Rg = RS.get('G01')
        anim = {}
        nv0 = len(dv)
        for fr in CFG['anim_frames']:
            scene.frame_set(fr)
            gg = gather({'d': deck_set})['d'][0]
            if len(gg) != nv0:
                anim[str(fr)] = {'error': 'vertex count changed %d->%d' % (nv0, len(gg))}
                continue
            hp = [sum(gg[i][k] for i in hn) / len(hn) for k in range(3)]
            tq = [sum(gg[i][k] for i in tp) / len(tp) for k in range(3)]
            dz = tq[2] - hp[2]; dh = math.hypot(tq[0] - hp[0], tq[1] - hp[1])
            rec = {'hinge': [round(x, 3) for x in hp], 'tip': [round(x, 3) for x in tq],
                   'angle': round(math.degrees(math.atan2(abs(dz), dh)), 2)}
            if fr in CFG['chain_frames']:
                cs = gather(dict((n, {n}) for n in chain_names)) if chain_names else {}
                pts = [p for v in cs.values() for p in v[0]]
                if pts:
                    kd = KDTree(len(pts))
                    for i, p in enumerate(pts):
                        kd.insert(p, i)
                    kd.balance()
                    rec['corner_d'] = [round(kd.find(gg[cmin])[2], 3), round(kd.find(gg[cmax])[2], 3)]
                    if Rg and Rg.t:
                        step = max(1, len(pts) // 4000)
                        dd = [Rg.near(pts[i]) for i in range(0, len(pts), step)]
                        dd = [x for x in dd if x is not None]
                        rec['g01_d'] = round(min(dd), 3) if dd else None
                else:
                    rec['corner_d'] = None
            anim[str(fr)] = rec
        BR['anim'] = anim
        scene.frame_set(120)
    else:
        BR['deck'] = False
except Exception:
    BR['error'] = traceback.format_exc()[-800:]
    try:
        scene.frame_set(120)
    except Exception:
        pass
'''


# ----------------------------------------------------------------------------------------------------------------
# helpers outside Blender
# ----------------------------------------------------------------------------------------------------------------
def _png_rows(path):
    """minimal PNG decoder (non-interlaced, 8/16-bit, colour types 0/2/4/6). returns (w, h, bitdepth, channels, rows)"""
    data = open(path, 'rb').read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not png')
    pos, idat, w = 8, [], None
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', body)
            if il:
                raise ValueError('interlaced png not supported')
        elif typ == b'IDAT':
            idat.append(body)
        elif typ == b'IEND':
            break
        pos += 12 + ln
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    bpp = max(1, ch * bd // 8)
    stride = w * ch * bd // 8
    raw = zlib.decompress(b''.join(idat))
    rows, prev = [], bytearray(stride)
    p = 0
    for _ in range(h):
        ft = raw[p]; line = bytearray(raw[p + 1:p + 1 + stride]); p += 1 + stride
        if ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]; c = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        rows.append(line); prev = line
    return w, h, bd, ch, rows


def heightmap_sampler(path, ext=160.0, px=0.5, zmax=48.0):
    w, h, bd, ch, rows = _png_rows(path)
    if bd == 16:
        vals = [[(r[2 * ch * i] << 8 | r[2 * ch * i + 1]) / 65535.0 * zmax for i in range(w)] for r in rows]
    else:
        vals = [[r[ch * i] / 255.0 * zmax for i in range(w)] for r in rows]

    def H(x, y):
        c = (x + ext) / px
        r = (ext - y) / px
        c0, r0 = max(0, min(w - 2, int(math.floor(c)))), max(0, min(h - 2, int(math.floor(r))))
        fc, fr = c - c0, r - r0
        a = vals[r0][c0] * (1 - fc) + vals[r0][c0 + 1] * fc
        b = vals[r0 + 1][c0] * (1 - fc) + vals[r0 + 1][c0 + 1] * fc
        return a * (1 - fr) + b * fr
    return H


def gray_std(path):
    try:
        from PIL import Image
        im = Image.open(path).convert('L')
        im.thumbnail((480, 270))
        px = list(im.getdata())
    except Exception:
        w, h, bd, ch, rows = _png_rows(path)
        step = 4
        px = []
        bs = 2 if bd == 16 else 1
        for r in rows[::step]:
            for i in range(0, w, step):
                o = i * ch * bs
                if ch >= 3:
                    v = 0.299 * r[o] + 0.587 * r[o + bs] + 0.114 * r[o + 2 * bs]
                else:
                    v = r[o]
                px.append(v)
    n = len(px)
    m = sum(px) / n
    return math.sqrt(sum((p - m) ** 2 for p in px) / n)


def probes():
    xs = [-135, -90, -45, 0, 45, 90, 135]
    pts = [(x, y) for y in xs for x in xs if not (y == -90 and x in (-45, 0, 45))]
    pts += [(-6.0, -93.0), (0.0, -93.0), (6.0, -93.0)]  # ditch bottom
    return pts


def wall_out_sign(w):
    """+1 if the left normal of a->b is the 'outside' (away from origin; east for W15)."""
    ea, eb = w['geom']['end_a'], w['geom']['end_b']
    ax, ay = eb[0] - ea[0], eb[1] - ea[1]
    nx, ny = -ay, ax
    if w['ring'] == 'traverse':
        return 1 if nx > 0 else -1
    mx, my = (ea[0] + eb[0]) / 2, (ea[1] + eb[1]) / 2
    return 1 if nx * mx + ny * my > 0 else -1


def build_cfg(ak):
    U = ak['units']
    units = {}
    joints = {}
    for j in ak['interfaces']['wall_node_joints']:
        joints.setdefault(j['node'], {})[j['wall']] = j['point']
    for uid, u in U.items():
        t = u['type']
        if t == 'drawbridge':
            continue
        c = {'type': t, 'params': u['params']}
        for k in ('x', 'y', 'facing', 'z0'):
            if k in u:
                c[k] = u[k]
        if t == 'tower':
            c['joints'] = joints.get(uid, {})
        if t == 'wall':
            c['end_a'], c['end_b'] = u['geom']['end_a'], u['geom']['end_b']
            c['out_sign'] = wall_out_sign(u)
            c['ref_a'] = [U[u['params']['node_a']]['x'], U[u['params']['node_a']]['y']]
            c['ref_b'] = [U[u['params']['node_b']]['x'], U[u['params']['node_b']]['y']]
        units[uid] = c
    b = U['B01']
    sp = b['geom']['abutment_span_from_hinge']
    bridge = {'hinge': b['geom']['hinge_mid'], 'facing': U['G01']['facing'], 'deck_width': b['params']['deck_width'],
              'abut_u': [round(sp[0] + 0.2, 2), round((sp[0] + sp[1]) / 2, 2), round(sp[1] - 0.2, 2)]}
    return {'units': units, 'bridge': bridge, 'probes': probes(), 'anim_frames': ANIM_FRAMES, 'chain_frames': CHAIN_FRAMES}


def make_extra_py(cfg):
    return _GLUE.replace('__CFG__', repr(json.dumps(cfg))) .replace('import json, math, traceback\n', 'import json, math, traceback\n' + _CORE + '\n', 1)


# ----------------------------------------------------------------------------------------------------------------
# verdict helpers
# ----------------------------------------------------------------------------------------------------------------
def _c(a, b):
    return a is not None and close(a, b, 0.03, 0.10)


def frac_ok(vals, pred):
    v = [x for x in vals if x is not None]
    return (sum(1 for x in v if pred(x)) / len(v)) if v else 0.0


def tower_expect_bb(p):
    if p['shape'] == 'round':
        r = p['diameter'] / 2
        return (-r, r, -r, r)
    if p['shape'] == 'square':
        a = p['side'] / 2
        return (-a, a, -a, a)
    return (-p['back_depth'], p['radius'], -p['radius'], p['radius'])


def judge_tower(m, u):
    """returns (M_ok, M_detail, G_ok, G_detail, measured_discrete)"""
    p, z0 = u['params'], u['z0']
    if not m or not m.get('present'):
        return False, 'tower geometry missing', False, 'tower geometry missing', {}
    bb, eb = m['bb'], tower_expect_bb(p)
    fails = []
    if not _c(bb[1] - bb[0], eb[1] - eb[0]) or not _c(bb[3] - bb[2], eb[3] - eb[2]):
        fails.append('size %.2fx%.2f vs %.2fx%.2f' % (bb[1] - bb[0], bb[3] - bb[2], eb[1] - eb[0], eb[3] - eb[2]))
    cu, cv = (bb[0] + bb[1]) / 2 - (eb[0] + eb[1]) / 2, (bb[2] + bb[3]) / 2
    if math.hypot(cu, cv) > TOL_POS:
        fails.append('centre off %.2f m' % math.hypot(cu, cv))
    if p['shape'] == 'D' and not (m['iou'].get('D', 0) > m['iou'].get('D_flip', 0)):
        fails.append('D-tower semicircle not on facing side')
    pz = m.get('platform_z')
    if pz is None or abs(pz - (z0 + p['platform_level'])) > TOL_Z:
        fails.append('platform z %s vs %.2f' % (pz, z0 + p['platform_level']))
    Mok = not fails
    Md = 'ok' if Mok else '; '.join(fails)
    meas = {'shape': m.get('shape'), 'storeys': m.get('storeys'), 'merlons': m.get('merlons'),
            'slits_per_storey': (m['slits'][0] if m.get('slits') and len(set(m['slits'])) == 1 else m.get('slits')),
            'roof': m.get('roof')}
    gf = []
    for k in ('shape', 'storeys', 'merlons', 'roof'):
        if meas[k] != p[k]:
            gf.append('%s %s vs %s' % (k, meas[k], p[k]))
    sl = m.get('slits') or []
    if len(sl) != p['storeys'] - 1 or any(x != p['slits_per_storey'] for x in sl):
        gf.append('slits/storey %s vs %d' % (sl, p['slits_per_storey']))
    if p['roof'] in ('cone', 'pyramid'):
        rt = m.get('roof_top')
        if rt is None or rt < z0 + p['platform_level'] + 1.2 + 0.8 * p['roof_rise']:
            gf.append('roof top %s too low' % rt)
    Gok = not gf
    return Mok, Md, Gok, ('ok' if Gok else '; '.join(gf)), meas


def judge_wall(m, u):
    p, g = u['params'], u['geom']
    if not m or m.get('present') is False or 'th' not in m:
        return False, 'wall geometry missing', False, 'wall geometry missing', {}, False
    t = p['thickness']
    fails = []
    if m['miss']:
        fails.append('%d/%d axis sections empty (wall does not cover end_a->end_b)' % (m['miss'], m['miss'] + len(m['th'])))
    nb = p['buttresses']
    butt_like = [x for x in m['th'] if t + 0.8 <= x <= t + 2.2]
    ths = [x for x in m['th'] if not (t + 0.8 <= x <= t + 2.2)] if len(butt_like) <= 2 * nb + 2 else m['th']
    fth = frac_ok(ths, lambda x: close(x, t, 0.03, 0.10))
    if fth < 0.85:
        fails.append('thickness ok in %.0f%% of sections (median %s vs %.2f)' % (100 * fth, sorted(m['th'])[len(m['th']) // 2] if m['th'] else None, t))
    offs = [o for o, th in zip(m['off'], m['th']) if th <= t + 0.5]
    off_ok = bool(offs) and all(abs(o) <= TOL_POS for o in offs) and not m['miss']
    if not off_ok:
        fails.append('axis offset max %s' % (max(abs(o) for o in offs) if offs else None))
    fp = frac_ok(m.get('parapet') or [], lambda x: close(x, p['parapet'], 0.03, 0.10))
    if fp < 0.85:
        fails.append('parapet height ok in %.0f%% of windows' % (100 * fp))
    Mok = not fails
    meas = {'merlons': m.get('merlons_out'), 'slits': m.get('slits'), 'buttresses': m.get('buttresses')}
    gf = ['%s %s vs %s' % (k, meas[k], p[k]) for k in ('merlons', 'slits', 'buttresses') if meas[k] != p[k]]
    return Mok, ('ok' if Mok else '; '.join(fails)), not gf, ('ok' if not gf else '; '.join(gf)), meas, off_ok


def joint_ok(recs):
    bads = []
    for r in recs or []:
        sn, sw, si = r.get('s_node'), r.get('s_wall'), r.get('s_inner')
        if sn is None or sw is None:
            bads.append('lat %.2f z %.2f: %s missing' % (r['lat'], r['z'], 'node' if sn is None else 'wall'))
            continue
        gap = sn - sw
        if gap > 0.10:
            bads.append('gap %.2f' % gap)
        elif -gap > 1.5:
            bads.append('protrudes %.2f into node' % -gap)
        elif si is not None and sw > si + 0.02:
            bads.append('passes node inner face')
    if not recs:
        bads.append('no joint data')
    return not bads, ('ok' if not bads else ', '.join(bads[:4]))


def walk_ok(m, u):
    g = u['geom']
    w = [x for x in (m or {}).get('walk', [])]
    if not w or any(z is None for _, z in w):
        return False, 'walk surface missing at %d samples' % sum(1 for _, z in w if z is None) if w else 'no walk data'
    L = m['L']
    za, zb = g['end_a'][2], g['end_b'][2]
    s0, z0_ = w[0]; s1, z1_ = w[-1]
    ea = abs(z0_ - (za + (zb - za) * s0 / L)); eb_ = abs(z1_ - (za + (zb - za) * s1 / L))
    dev = max(abs(z - (z0_ + (z1_ - z0_) * (s - s0) / max(1e-6, s1 - s0))) for s, z in w)
    ok_ = ea <= TOL_Z and eb_ <= TOL_Z and dev <= TOL_Z
    return ok_, 'end err %.3f/%.3f, max dev from single grade %.3f' % (ea, eb_, dev)


def end_walk_ok(m, u, end):
    g = u['geom']
    w = (m or {}).get('walk') or []
    if not w:
        return False, 'no walk data'
    s, z = w[0] if end == 'a' else w[-1]
    L = m['L']
    za, zb = g['end_a'][2], g['end_b'][2]
    e = None if z is None else abs(z - (za + (zb - za) * s / L))
    return (e is not None and e <= TOL_Z), 'walk end err %s' % (None if e is None else round(e, 3))


def judge_gate(m, u):
    p, z0 = u['params'], u['z0']
    if not m or not m.get('present'):
        return False, 'gatehouse geometry missing', False, 'gatehouse geometry missing', {}
    f = []
    if not _c(m['W'], p['width']): f.append('width %.2f vs %.2f' % (m['W'], p['width']))
    if not _c(m['D'], p['depth']): f.append('depth %.2f vs %.2f' % (m['D'], p['depth']))
    if math.hypot(m['cu'], m['cv']) > TOL_POS: f.append('centre off %.2f' % math.hypot(m['cu'], m['cv']))
    if not _c(m.get('pw'), p['passage_w']): f.append('passage w %s vs %.2f' % (m.get('pw'), p['passage_w']))
    if not _c(m.get('ph'), p['passage_h']): f.append('passage h %s vs %.2f' % (m.get('ph'), p['passage_h']))
    meas = {k: m.get(k) for k in ('portcullises', 'arch', 'flank_towers', 'merlons')}
    gf = ['%s %s vs %s' % (k, meas[k], p[k]) for k in meas if meas[k] != p[k]]
    return not f, ('ok' if not f else '; '.join(f)), not gf, ('ok' if not gf else '; '.join(gf)), meas


def judge_keep(m, u):
    p, z0 = u['params'], u['z0']
    if not m or not m.get('present'):
        return False, 'keep geometry missing', False, 'keep geometry missing', {}
    f = []
    if not _c(m['L'], p['length']): f.append('length %.2f vs %.2f' % (m['L'], p['length']))
    if not _c(m['W'], p['width']): f.append('width %.2f vs %.2f' % (m['W'], p['width']))
    if math.hypot(m['cu'], m['cv']) > TOL_POS: f.append('centre off')
    pz = m.get('platform_z')
    if pz is None or abs(pz - (z0 + p['platform_level'])) > TOL_Z: f.append('platform z %s vs %.2f' % (pz, z0 + p['platform_level']))
    td = m.get('turret_d') or []
    if not td or not all(_c(d, p['turret_diameter']) for d in td): f.append('turret diameters %s vs %.2f' % (td, p['turret_diameter']))
    fe = m.get('fore_ext')
    if fe is None or fe < 3.0: f.append('forebuilding not on facing side (ext %s)' % fe)
    wins = m.get('windows') or []
    wv = wins[0][0] if wins and all(a == b == wins[0][0] for a, b in wins) else wins
    meas = {'storeys': m.get('storeys'), 'turrets': m.get('turrets'), 'roof': m.get('roof'), 'windows_per_long_side': wv}
    gf = ['%s %s vs %s' % (k, meas[k], p[k]) for k in meas if meas[k] != p[k]]
    if len(wins) != p['storeys'] - 1:
        gf.append('window storeys %d vs %d' % (len(wins), p['storeys'] - 1))
    return not f, ('ok' if not f else '; '.join(f)), not gf, ('ok' if not gf else '; '.join(gf)), meas


def judge_chapel(m, u):
    p, z0 = u['params'], u['z0']
    if not m or not m.get('present'):
        return False, 'chapel geometry missing', False, 'chapel geometry missing', {}
    f = []
    L, W = p['nave_length'], p['nave_width']
    ext = 0.0
    if p['apse'] != 'flat':
        ext = math.sqrt(max(0.0, (W / 2) ** 2 - (W / 4) ** 2))
    east = m['u_east'] + ext
    Lm = m['u_west'] - east
    if not _c(Lm, L): f.append('nave length %.2f vs %.2f' % (Lm, L))
    if not _c(m['W'], W): f.append('nave width %.2f vs %.2f' % (m['W'], W))
    cu = (m['u_west'] + east) / 2
    if math.hypot(cu, m['cv']) > TOL_POS: f.append('centre off %.2f' % math.hypot(cu, m['cv']))
    if m.get('eave_z') is None or abs(m['eave_z'] - (z0 + p['eave'])) > TOL_Z: f.append('eave z %s vs %.2f' % (m.get('eave_z'), z0 + p['eave']))
    if m.get('ridge_z') is None or abs(m['ridge_z'] - (z0 + p['ridge'])) > TOL_Z: f.append('ridge z %s vs %.2f' % (m.get('ridge_z'), z0 + p['ridge']))
    if not m.get('entrance'): f.append('no entrance on facing side')
    wi, bu = m.get('windows') or [None, None], m.get('butts') or [None, None]
    bays = wi[0] if (wi[0] == wi[1] and bu[0] == bu[1] and bu[0] == (wi[0] or 0) + 1) else {'windows': wi, 'buttresses': bu}
    meas = {'bays': bays, 'apse': m.get('apse'), 'bell_openings': m.get('bell_openings')}
    gf = ['%s %s vs %s' % (k, meas[k], p[k]) for k in meas if meas[k] != p[k]]
    return not f, ('ok' if not f else '; '.join(f)), not gf, ('ok' if not gf else '; '.join(gf)), meas


def judge_well(m, u):
    p, z0 = u['params'], u['z0']
    if not m or not m.get('present'):
        return False, 'well geometry missing', False, 'well geometry missing', {}
    f = []
    if not _c(m.get('diameter'), p['diameter']): f.append('curb diameter %s vs %.2f' % (m.get('diameter'), p['diameter']))
    if 'cu' in m and math.hypot(m['cu'], m['cv']) > TOL_POS: f.append('centre off')
    if m.get('curb_top') is None or abs(m['curb_top'] - (z0 + p['curb_height'])) > TOL_Z: f.append('curb top %s vs %.2f' % (m.get('curb_top'), z0 + p['curb_height']))
    if m.get('canopy_top') is None or abs(m['canopy_top'] - (z0 + p['canopy_top'])) > TOL_Z: f.append('canopy top %s vs %.2f' % (m.get('canopy_top'), z0 + p['canopy_top']))
    meas = {'posts': m.get('posts'), 'roof': m.get('roof')}
    gf = ['%s %s vs %s' % (k, meas[k], p[k]) for k in meas if meas[k] != p[k]]
    return not f, ('ok' if not f else '; '.join(f)), not gf, ('ok' if not gf else '; '.join(gf)), meas


def judge_bridge(br, ak, terrain_ok_fn=None):
    """M02 part (deck at 120 + abutment presence) and G01 part (planks, chains)."""
    b = ak['units']['B01']; p, g = b['params'], b['geom']
    if not br or br.get('deck') is False or 'deck_u' not in br:
        return False, 'B01_DECK missing', False, 'B01_DECK missing', {}
    f = []
    Lm = br['deck_u'][1] - br['deck_u'][0]
    Wm = br['deck_v'][1] - br['deck_v'][0]
    if not _c(Lm, p['deck_length']): f.append('deck length %.2f vs %.2f' % (Lm, p['deck_length']))
    if not _c(Wm, p['deck_width']): f.append('deck width %.2f vs %.2f' % (Wm, p['deck_width']))
    if abs(br['deck_top'] - g['deck_top_level']) > TOL_Z: f.append('deck top %.2f vs %.2f' % (br['deck_top'], g['deck_top_level']))
    ab = br.get('abutment') or []
    if sum(1 for r in ab if r.get('top') is not None) < 2: f.append('no abutment within abutment span')
    meas = {'planks': br.get('planks'), 'deck_length': round(Lm, 3)}
    gf = []
    if br.get('planks') != p['planks']: gf.append('planks %s vs %d' % (br.get('planks'), p['planks']))
    if br.get('chains') != p['chains']: gf.append('chains %s vs %d' % (br.get('chains'), p['chains']))
    return not f, ('ok' if not f else '; '.join(f)), not gf, ('ok' if not gf else '; '.join(gf)), meas


def judge_stables(m, u, ak):
    """G12"""
    p = u['params']
    if not m or not m.get('present'):
        return False, 'stables geometry missing', {}
    f = []
    if m.get('stall_doors') != p['stall_doors']: f.append('stall doors %s vs %d' % (m.get('stall_doors'), p['stall_doors']))
    ub = m.get('u_back') or []
    if not ub or any(x is None or abs(x) > 0.10 for x in ub): f.append('back wall to W12 inner face %s (need |d|<=0.10)' % ub)
    if m.get('cv') is None or abs(m['cv']) > TOL_POS: f.append('plan midpoint off anchor %.2f' % (m.get('cv') or 99))
    meas = {'stall_doors': m.get('stall_doors'), 'loft_openings': m.get('loft_openings')}
    return not f, ('ok' if not f else '; '.join(f)), meas


# ----------------------------------------------------------------------------------------------------------------
def run(ctx):
    R = {}
    out = pathlib.Path(ctx['out'])
    ak = ctx.get('answer') or json.loads((pathlib.Path(ctx['tests']) / 'answer-key.json').read_text(encoding='utf-8'))
    AU = ak['units']

    def put(i, fn):
        try:
            v = fn()
            R[i] = ok(v[1]) if v[0] else bad(v[1])
        except Exception:
            R[i] = bad('check error: ' + traceback.format_exc()[-400:])

    # ---- file-level checks (no Blender needed)
    def render_chk(names):
        msgs, good = [], True
        for n in names:
            pth = out / 'renders' / n
            sz = png_size(pth) if pth.exists() else None
            if sz != (1920, 1080):
                good = False; msgs.append('%s size %s' % (n, sz)); continue
            sd = gray_std(pth)
            if sd <= 10:
                good = False
            msgs.append('%s 1920x1080 std %.1f' % (n, sd))
        return good, '; '.join(msgs)
    put('B05', lambda: render_chk(['overview.png']))
    put('B06', lambda: render_chk(['gate.png', 'traverse.png']))
    man = load_manifest(out)

    # ---- scene
    S = None
    try:
        cfg = build_cfg(ak)
        S = Scene.load(ctx, frames=[1, 120], anim_regex=r'^B01_DECK$', extra_py=make_extra_py(cfg), timeout=2400)
    except Exception:
        S = Scene(None, 'scene load error: ' + traceback.format_exc()[-300:])
    if S.err or not S.data:
        why = 'scene unavailable: %s' % (S.err or 'no data')
        for it in ctx['items']:
            if it['id'] not in R and it['id'] != 'G16':
                R[it['id']] = bad(why)
        # B07 is file-level
        put('B07', lambda: manifest_shape(man, set()))
        return R
    D = S.data
    X = (D.get('extra') or {}).get('w02') or {}
    MU = X.get('units') or {}
    if not X:
        errs = (D.get('errors') or [])[-3:]
        for it in ctx['items']:
            if it['id'] not in R and it['id'] not in ('G16',):
                R[it['id']] = bad('in-Blender measurement failed: %s' % errs)
        put('B01', lambda: b01(D))
        put('B02', lambda: b02(S))
        put('B07', lambda: manifest_shape(man, set(k for k in UNITS34 if S.has_coll(k))))
        put('B08', lambda: b08(D))
        put('B09', lambda: b09(S))
        return R

    put('B01', lambda: b01(D))
    put('B02', lambda: b02(S))

    def b03():
        fm = X.get('faces_max') or {}
        badu = [k for k in UNITS34 if (fm.get(k) or 0) < 6]
        return (not badu), ('all 34 unit collections hold geometry' if not badu else 'empty/missing: %s' % badu)
    put('B03', b03)

    def b04():
        t = S.ob('TERRAIN')
        if not t or 'SITE' not in (t.get('collections') or []) and 'TERRAIN' not in S.coll('SITE'):
            return False, 'TERRAIN not in SITE'
        bb = t.get('bbox_world')
        nv = max(t.get('n_verts') or 0, (X.get('n_verts') or {}).get('__TERRAIN__') or 0)
        okb = bb and bb[0][0] <= -159 and bb[0][1] <= -159 and bb[1][0] >= 159 and bb[1][1] >= 159
        return bool(okb and nv >= 321 * 321), 'bbox %s, verts %d' % (bb, nv)
    put('B04', b04)
    put('B07', lambda: manifest_shape(man, set(k for k in UNITS34 if S.has_coll(k))))
    put('B08', lambda: b08(D))
    put('B09', lambda: b09(S))

    # ---- M01 terrain
    def m01():
        H = heightmap_sampler(str(pathlib.Path(ctx['input']) / 'site' / 'heightmap.png'))
        pr = X.get('terrain_probe') or []
        pts = probes()
        errs = []
        for (x, y), z in zip(pts, pr):
            e = None if z is None else abs(z - H(x, y))
            errs.append(e)
        badn = sum(1 for e in errs if e is None or e > 0.30)
        mx = max([e for e in errs if e is not None] or [None]) if errs else None
        return (len(errs) == len(pts) and badn == 0), '%d/%d probes within 0.30 m (max err %s)' % (len(pts) - badn, len(pts), None if mx is None else round(mx, 3))
    put('M01', m01)

    # ---- per-unit judgements
    J = {}   # uid -> dict(M=(ok,d), G=(ok,d), meas)
    for uid in UNITS34:
        u = AU[uid]; t = u['type']; m = MU.get(uid)
        try:
            if t == 'tower':
                a = judge_tower(m, u); J[uid] = {'M': a[:2], 'G': a[2:4], 'meas': a[4]}
            elif t == 'wall':
                a = judge_wall(m, u); J[uid] = {'M': a[:2], 'G': a[2:4], 'meas': a[4], 'axis_ok': a[5]}
            elif t == 'gatehouse':
                a = judge_gate(m, u); J[uid] = {'M': a[:2], 'G': a[2:4], 'meas': a[4]}
            elif t == 'keep':
                a = judge_keep(m, u); J[uid] = {'M': a[:2], 'G': a[2:4], 'meas': a[4]}
            elif t == 'chapel':
                a = judge_chapel(m, u); J[uid] = {'M': a[:2], 'G': a[2:4], 'meas': a[4]}
            elif t == 'well':
                a = judge_well(m, u); J[uid] = {'M': a[:2], 'G': a[2:4], 'meas': a[4]}
            elif t == 'drawbridge':
                a = judge_bridge(X.get('bridge'), ak); J[uid] = {'M': a[:2], 'G': a[2:4], 'meas': a[4]}
            elif t == 'stables':
                a = judge_stables(m, u, ak); J[uid] = {'G': a[:2], 'meas': a[2]}
        except Exception:
            J[uid] = {'M': (False, 'judge error ' + traceback.format_exc()[-200:]), 'G': (False, 'judge error'), 'meas': {}}

    for z in ak['zones']:
        mid, gid = ZONE_ITEMS[z['id']]
        us = [x for x in z['units'] if x not in CHANGED]

        def zm(us=us, key='M'):
            bads = ['%s: %s' % (x, J[x][key][1]) for x in us if not J[x][key][0]]
            return (not bads), ('all %d units ok' % len(us) if not bads else ' | '.join(bads))
        put(mid, lambda us=us: zm(us, 'M'))
        put(gid, lambda us=us: zm(us, 'G'))

    # ---- M09 manifest consistency
    def m09():
        if not isinstance(man, list):
            return False, 'manifest missing or not an array'
        by = {}
        for e in man:
            if isinstance(e, dict) and e.get('id'):
                by[e['id']] = e
        bads = []
        for uid in UNITS34:
            e = by.get(uid)
            if e is None:
                bads.append('%s not declared' % uid); continue
            if e.get('built') is False:
                if S.has_coll(uid) and (X.get('faces_max') or {}).get(uid):
                    bads.append('%s built:false but collection has geometry' % uid)
                continue
            t = AU[uid]['type']
            pr = e.get('params') or {}
            meas = J.get(uid, {}).get('meas') or {}
            for k in DISCRETE[t]:
                mv = meas.get(k)
                dv = pr.get(k)
                if mv is None or dv != mv:
                    bads.append('%s.%s declared %s measured %s' % (uid, k, dv, mv))
        return (not bads), ('declared discrete params match measurement' if not bads else '; '.join(bads[:12]) + (' ...(+%d)' % (len(bads) - 12) if len(bads) > 12 else ''))
    put('M09', m09)

    # ---- M10 / M11 drawbridge animation
    br = X.get('bridge') or {}
    def m10():
        an = br.get('anim') or {}
        if not an:
            return False, 'no deck animation data (%s)' % br.get('error', 'B01_DECK missing')
        A = {int(k): v for k, v in an.items()}
        if any('angle' not in A.get(f, {}) for f in ANIM_FRAMES):
            return False, 'deck sampling failed at frames %s' % [f for f in ANIM_FRAMES if 'angle' not in A.get(f, {})][:6]
        f = []
        if abs(A[1]['angle'] - 90) > 3: f.append('frame1 angle %.1f' % A[1]['angle'])
        for fr in (72, 96, 120):
            if abs(A[fr]['angle']) > TOL_ANG: f.append('frame%d angle %.1f' % (fr, A[fr]['angle']))
        seq = [A[fr]['angle'] for fr in ANIM_FRAMES if fr <= 72]
        if any(seq[i + 1] > seq[i] + 0.5 for i in range(len(seq) - 1)): f.append('lowering not monotonic')
        hs = [A[fr]['hinge'] for fr in ANIM_FRAMES]
        c = [sum(h[k] for h in hs) / len(hs) for k in range(3)]
        spread = max(math.dist(h, c) for h in hs)
        if spread > 0.05: f.append('hinge moves %.3f m' % spread)
        hm = ak['units']['B01']['geom']['hinge_mid']
        if abs(c[2] - hm[2]) > TOL_Z: f.append('hinge z %.2f vs %.2f' % (c[2], hm[2]))
        if math.hypot(c[0] - hm[0], c[1] - hm[1]) > TOL_POS: f.append('hinge xy off %.2f' % math.hypot(c[0] - hm[0], c[1] - hm[1]))
        return (not f), ('ok: f1 %.1f deg, f72 %.1f deg' % (A[1]['angle'], A[72]['angle']) if not f else '; '.join(f))
    put('M10', m10)

    def m11():
        an = br.get('anim') or {}
        g = ak['units']['B01']['geom']
        f = []
        for fr in CHAIN_FRAMES:
            a = an.get(str(fr)) or {}
            cd, gd = a.get('corner_d'), a.get('g01_d')
            if not cd or any(x is None or x > 0.30 for x in cd): f.append('f%d chain-to-deck-corner %s' % (fr, cd))
            if gd is None or gd > 0.30: f.append('f%d chain-to-G01 %s' % (fr, gd))
        ab = br.get('abutment') or []
        tops = [r for r in ab if r.get('top') is not None]
        if len(tops) < 2:
            f.append('abutment not found in span')
        else:
            if any(abs(r['top'] - g['abutment_top']) > TOL_Z for r in tops): f.append('abutment top %s vs %.2f' % ([r['top'] for r in tops], g['abutment_top']))
            if any(r.get('bottom') is None or r['bottom'] - (r.get('terrain') or 0) > 0.10 for r in tops): f.append('abutment not grounded')
        return (not f), ('ok' if not f else '; '.join(f[:6]))
    put('M11', m11)

    # ---- M12 axes of W01-W14
    def m12():
        bads = [w for w in WALLS[:14] if not J[w].get('axis_ok')]
        return (not bads), ('all 14 wall axes within 0.30 m' if not bads else 'off-axis/missing: %s' % bads)
    put('M12', m12)

    # ---- G08/G09 changed towers
    def changed_tower(uid):
        u = AU[uid]; m = MU.get(uid) or {}
        a = judge_tower(m, u)
        f = []
        if not a[0]: f.append(a[1])
        if not a[2]: f.append(a[3])
        sh = m.get('shell')
        if sh is None or not close(sh, u['params']['shell'], 0.03, 0.10): f.append('shell %s vs %.2f' % (sh, u['params']['shell']))
        # walk-door openings are not a stated requirement (instruction rule 7 lists slits, windows, gate passages and
        # bell openings only); the walk-door LEVEL is checked through the adjoining wall ends in G11/G14.
        dr = m.get('doors') or {}
        return (not f), ('ok' if not f else '; '.join(f)) + ' (info: walk-door rays %s)' % dr
    put('G08', lambda: changed_tower('T02'))
    put('G09', lambda: changed_tower('T08'))

    def g10():
        u = AU['W15']; m = MU.get('W15') or {}
        a = judge_wall(m, u)
        f = []
        if not a[0]: f.append(a[1])
        if not a[2]: f.append(a[3])
        if m.get('merlons_in') == u['params']['merlons']: f.append('merlons also on west parapet line')
        wo = walk_ok(m, u)
        if not wo[0]: f.append(wo[1])
        return (not f), ('ok' if not f else '; '.join(f))
    put('G10', g10)

    def g11():
        f = []
        for w, end in (('W02', 'b'), ('W03', 'a'), ('W09', 'b'), ('W10', 'a')):
            m = MU.get(w) or {}
            jo = joint_ok((m.get('joints') or {}).get(end))
            if not jo[0]: f.append('%s.%s %s' % (w, end, jo[1]))
            we = end_walk_ok(m, AU[w], end)
            if not we[0]: f.append('%s.%s %s' % (w, end, we[1]))
        return (not f), ('ok' if not f else '; '.join(f))
    put('G11', g11)
    put('G12', lambda: J['S01']['G'])

    def g13():
        f = []
        for w in WALLS:
            m = MU.get(w) or {}
            for end in ('a', 'b'):
                jo = joint_ok((m.get('joints') or {}).get(end))
                if not jo[0]: f.append('%s.%s %s' % (w, end, jo[1]))
        return (not f), ('30/30 joints tight' if not f else '%d joint(s) bad: %s' % (len(f), '; '.join(f[:6])))
    put('G13', g13)

    def g14():
        f = []
        for w in WALLS:
            r = walk_ok(MU.get(w), AU[w])
            if not r[0]: f.append('%s %s' % (w, r[1]))
        return (not f), ('15/15 walks continuous' if not f else '; '.join(f[:6]))
    put('G14', g14)

    def g15():
        f = []
        for uid in UNITS34:
            if uid == 'B01':
                continue
            g = (MU.get(uid) or {}).get('ground')
            if not g:
                f.append('%s no data' % uid); continue
            hit = g['n'] - g['miss']
            if g['n'] == 0 or hit < 0.7 * g['n']:
                f.append('%s footprint samples hit %d/%d' % (uid, hit, g['n']))
            elif g['n_float']:
                f.append('%s floats (max %.2f m)' % (uid, g['max_float']))
        return (not f), ('all units grounded' if not f else '; '.join(f[:8]))
    put('G15', g15)
    return R


def b01(D):
    sc = D.get('scene') or {}
    okk = sc.get('unit_system') == 'METRIC' and sc.get('length_unit') == 'METERS' and abs((sc.get('scale_length') or 0) - 1) < 1e-6
    return okk, 'opens; units %s/%s scale %s; blender %s' % (sc.get('unit_system'), sc.get('length_unit'), sc.get('scale_length'), D.get('blender_version'))


def b02(S):
    need = UNITS33 + ['SITE']
    miss = [k for k in need if not S.has_coll(k)]
    return (not miss), ('33 unit collections + SITE present' if not miss else 'missing: %s' % miss)


def b08(D):
    sc = D.get('scene') or {}
    fps = (sc.get('fps') or 0) / (sc.get('fps_base') or 1)
    okk = sc.get('frame_start') == 1 and sc.get('frame_end') == 120 and abs(fps - 24) < 1e-6
    return okk, 'frames %s-%s fps %.3f' % (sc.get('frame_start'), sc.get('frame_end'), fps)


def b09(S):
    if 'B01_DECK' not in S.coll('B01'):
        return False, 'B01_DECK not in collection B01'
    a, b = S.at(1, 'B01_DECK'), S.at(120, 'B01_DECK')
    if a is None or b is None:
        return False, 'B01_DECK not sampled'
    diff = max(abs(a[i][j] - b[i][j]) for i in range(4) for j in range(4))
    return diff > 1e-4, 'matrix_world difference f1 vs f120: %.4f' % diff


def manifest_shape(man, built_colls):
    if not isinstance(man, list):
        return False, 'manifest.json missing or not an array'
    bads = []
    ids = set()
    for e in man:
        if not isinstance(e, dict) or not all(k in e for k in ('id', 'collection', 'built', 'params')):
            bads.append('entry missing fields: %s' % str(e)[:60]); continue
        ids.add(e['id'])
        uid = e['id']
        t = None
        try:
            t = json.loads((pathlib.Path(__file__).parent / 'answer-key.json').read_text(encoding='utf-8'))['units'].get(uid, {}).get('type')
        except Exception:
            pass
        if t and isinstance(e['params'], dict) and e.get('built'):
            miss = [k for k in PARAM_FIELDS[t] if k not in e['params']]
            if miss:
                bads.append('%s params missing %s' % (uid, miss))
    miss_ids = sorted(built_colls - ids)
    if miss_ids:
        bads.append('built collections without entry: %s' % miss_ids)
    return (not bads), ('%d entries ok' % len(man) if not bads else '; '.join(bads[:8]))


def postprocess(results, ctx):
    items = ctx['items']
    v = lambda i: results.get(i, {}).get('verdict')
    b02d = results.get('B02', {}).get('detail', '')
    no_units = 'missing' in b02d and all(u in b02d for u in UNITS33)
    if v('B01') == 'fail' or no_units:
        for it in items:
            if it['id'] not in ('B01', 'B05', 'B06'):
                results[it['id']] = {'verdict': 'fail', 'detail': 'gate: B01 failed or no unit collections', 'source': 'gate'}
        return results
    m = re.search(r'missing: \[(.*)\]', b02d)
    if v('B02') == 'fail' and m:
        missing = set(re.findall(r"'([A-Z]\d\d)'", m.group(1)))
        ak = ctx.get('answer') or {}
        for z in ak.get('zones', []):
            # zone M/G items exclude the change-order units (they are judged by G08-G12), so only a missing
            # non-changed unit gates its zone
            zmiss = (missing - set(CHANGED)) & set(z['units'])
            if zmiss:
                for i in ZONE_ITEMS[z['id']]:
                    results[i] = {'verdict': 'fail', 'detail': 'gate: zone %s unit(s) %s missing (B02)' % (z['id'], sorted(zmiss)), 'source': 'gate'}
    return results
