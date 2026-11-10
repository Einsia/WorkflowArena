# -*- coding: utf-8 -*-
"""BLD-W06 Mechanical Astronomical Clock Tower - deterministic checks.

One Blender extraction (Scene.load) with a task-specific extra_py that, inside Blender:
  * profiles every named gear (tooth count by 0.5 deg radial bins, tip/root radius, genus, XZ-silhouette
    hole count, layer y);
  * steps frames 1..1440 once and records, for every moving named part, the unwrapped rotation
    about world +Y relative to frame 1, origin drift and rotation-axis deviation;
  * records weight bottom z per frame, striker hammer-to-BL1 distance per frame, hand directions
    at frames 1/721, pendulum length (pivot -> bob centre), chapter ring / plate radii, AS1 islands,
    TW4 section hull, storey wall-face spans (ray-cast medians), east-wall ray-cast cut ratio,
    TW3 opening island centroids, text-object bodies.
2026-10-25 cleanup: see review/rubric-cleanup-20261025.md.
Items not returned here (G11; the form parts of G02/G09) go to the judge model; G02/G09 deterministic
parts are AND-ed in postprocess (judge can only veto).
"""
import json, math, re, pathlib, shutil, subprocess, zlib, struct

from _bld_lib import Scene, ok, bad, close, png_size, load_manifest, gate_group

UNITS = ['TW1', 'TW2', 'TW3', 'TW4', 'DL1', 'AS1', 'DL2', 'CR1', 'MP1', 'GT1', 'GT9', 'ES1', 'PD1', 'WT1',
         'GT2', 'GT5', 'GT3', 'GT6', 'GT4', 'WT2', 'GT7', 'GT8', 'BL1', 'BL2', 'GT10', 'AU1', 'AU2', 'AU3']
COMPONENTS = {'TW1': ['door', 'buttress', 'course'], 'TW2': ['window', 'pilaster'], 'TW3': ['opening', 'post'],
              'TW4': ['dormer', 'pinnacle'], 'DL1': ['marker', 'tick'], 'AS1': ['star', 'division', 'circle'],
              'DL2': ['division'], 'CR1': ['segment', 'medallion'], 'MP1': ['moon', 'star'], 'AU1': ['fig'],
              'AU2': ['fig'], 'BL1': ['canon', 'hammer'], 'BL2': ['canon', 'hammer'], 'WT2': ['disc'], 'GT8': ['vane']}
COMP_RE = '^(' + '|'.join(f'{u}_({"|".join(c)})' for u, c in COMPONENTS.items()) + ')$'
MOVERS_EXTRA = ['DL1_minute', 'DL1_hour', 'AS1_rete', 'DL2_disc', 'CR1_ring', 'MP1_disc', 'PD1_pendulum', 'ES1_anchor',
                'GT8_fly', 'WT1_drum', 'WT2_drum', 'AU1_wheel', 'AU2_wheel', 'AU3_cam', 'AU3_arm']
ARBOR_EXTRA_REPS = {'M': ['DL1_minute'], 'H': ['DL1_hour'], 'R': ['AS1_rete'], 'D24': ['DL2_disc'], 'C': ['CR1_ring'],
                    'MO': ['MP1_disc'], 'P1': ['AU1_wheel'], 'P2': ['AU2_wheel'], 'SB': ['AU3_cam', 'WT2_drum'],
                    'G': ['WT1_drum'], 'F': ['GT8_fly']}
SCENE_GROUPS = ('scene', 'integration', 'motion', 'change', 'manifest')
NF = 1440

# ---------------------------------------------------------------------------------------------
# Pure helpers (also exec'd inside Blender as part of EXTRA_PY; keep them dependency-free)
PURE = r'''
def _wrap180(a):
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a

def teeth_profile(V2, E, cx, cz, nb=720):
    """V2: [(x,z)], E: [(i,j)] outline edges. Count contiguous angular runs above (r_tip+r_root)/2."""
    best = [-1.0] * nb
    two = 2 * math.pi
    def put(x, z):
        r = math.hypot(x - cx, z - cz)
        b = int((math.atan2(z - cz, x - cx) % two) / two * nb) % nb
        if r > best[b]:
            best[b] = r
    for x, z in V2:
        put(x, z)
    for i, j in E:
        x1, z1 = V2[i]; x2, z2 = V2[j]
        L = math.hypot(x2 - x1, z2 - z1)
        if L <= 0:
            continue
        rm = max(1e-4, math.hypot((x1 + x2) / 2 - cx, (z1 + z2) / 2 - cz))
        step = max(1e-5, 0.4 * rm * two / nb)
        n = min(4000, int(L / step) + 1)
        for k in range(1, n):
            t = k / n
            put(x1 + (x2 - x1) * t, z1 + (z2 - z1) * t)
    if max(best) < 0:
        return None
    first = next(i for i in range(nb) if best[i] >= 0)
    last = best[first]
    for k in range(nb):
        i = (first + k) % nb
        if best[i] < 0:
            best[i] = last
        else:
            last = best[i]
    rt, rr = max(best), min(best)
    if rt <= 0 or (rt - rr) < 0.01 * rt:
        return {'teeth': 0, 'r_tip': rt, 'r_root': rr}
    thr = (rt + rr) / 2
    hi = [b > thr for b in best]
    n = sum(1 for i in range(nb) if hi[i] and not hi[i - 1])
    return {'teeth': n, 'r_tip': rt, 'r_root': rr}

def genus_of(nV, E, P):
    """Sum over islands of (2 - (V - E + F)) / 2."""
    par = list(range(nV))
    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for i, j in E:
        a, b = f(i), f(j)
        if a != b:
            par[a] = b
    for p in P:
        for k in range(1, len(p)):
            a, b = f(p[0]), f(p[k])
            if a != b:
                par[a] = b
    cv, ce, cf = {}, {}, {}
    for i in range(nV):
        r = f(i); cv[r] = cv.get(r, 0) + 1
    for i, j in E:
        r = f(i); ce[r] = ce.get(r, 0) + 1
    for p in P:
        if p:
            r = f(p[0]); cf[r] = cf.get(r, 0) + 1
    g = 0.0
    for r in cv:
        g += (2 - (cv[r] - ce.get(r, 0) + cf.get(r, 0))) / 2.0
    return g, len(cv)

def island_groups(nV, E):
    par = list(range(nV))
    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for i, j in E:
        a, b = f(i), f(j)
        if a != b:
            par[a] = b
    g = {}
    for i in range(nV):
        g.setdefault(f(i), []).append(i)
    return list(g.values())

def hull_corners(pts, min_turn_deg=15.0):
    pts = sorted(set((round(x, 4), round(y, 4)) for x, y in pts))
    if len(pts) < 3:
        return 0
    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]
    n = len(h)
    c = 0
    for i in range(n):
        a, b, d = h[i - 1], h[i], h[(i + 1) % n]
        a1 = math.atan2(b[1] - a[1], b[0] - a[0]); a2 = math.atan2(d[1] - b[1], d[0] - b[0])
        if abs(_wrap180(math.degrees(a2 - a1))) > min_turn_deg:
            c += 1
    return c
'''
exec(PURE)

# ---------------------------------------------------------------------------------------------
EXTRA_PY = r'''
import json, math, re
from mathutils import Vector, Matrix
CFG = json.loads(__CFG__)
''' + PURE + r'''
ERR = []
EXTRA['errors'] = ERR
OBJ = scene.objects

def _dg():
    return bpy.context.evaluated_depsgraph_get()

def mdata(ob, world=True):
    ev = ob.evaluated_get(_dg())
    me = ev.to_mesh()
    try:
        mw = ev.matrix_world.copy()
        if len(me.vertices) > 400000:
            return None
        V = [tuple(mw @ v.co) for v in me.vertices] if world else [tuple(v.co) for v in me.vertices]
        E = [tuple(e.vertices) for e in me.edges]
        P = [tuple(p.vertices) for p in me.polygons]
        m3 = mw.to_3x3()
        SE = set()
        for p in me.polygons:
            n = (m3 @ p.normal)
            if n.length > 0 and abs(n.normalized().y) < 0.3:
                for ek in p.edge_keys:
                    SE.add(tuple(ek))
        return V, E, P, list(SE)
    finally:
        ev.to_mesh_clear()

def colobjs(cname):
    c = bpy.data.collections.get(cname)
    return list(c.all_objects) if c else []

def meshes_with_children(ob):
    out = [ob] if ob.type == 'MESH' else []
    for ch in ob.children_recursive:
        if ch.type == 'MESH':
            out.append(ch)
    return out

def sil_holes(ob, cx, cz, rlim, N=240, min_cells=6):
    """2026-10-25: spoke windows counted on the XZ silhouette (works for gears assembled from non-manifold /
    overlapping parts, where the genus test fails). Rasterise every face triangle (world XZ) on an NxN grid over
    the disc of radius rlim about (cx, cz); empty cells not connected to the area outside rlim are holes;
    returns the number of hole regions with >= min_cells cells.
    Real-image fix (2026-10-25): the Debian Blender 4.3.2 in workflowarena-original-cdc-tools runs on the system
    python3.13 without numpy, so this is pure Python (same cell-centre / barycentric rule as the former numpy code)."""
    import math as _mm
    ev = ob.evaluated_get(_dg())
    me = ev.to_mesh()
    try:
        me.calc_loop_triangles()
        nt, nv = len(me.loop_triangles), len(me.vertices)
        if nt == 0 or nt > 400000 or rlim <= 0:
            return None
        co = [0.0] * (nv * 3)
        me.vertices.foreach_get('co', co)
        tri = [0] * (nt * 3)
        me.loop_triangles.foreach_get('vertices', tri)
        M = ev.matrix_world
        m00, m01, m02, m03 = M[0][0], M[0][1], M[0][2], M[0][3]
        m20, m21, m22, m23 = M[2][0], M[2][1], M[2][2], M[2][3]
    finally:
        ev.to_mesh_clear()
    h = 2.0 * rlim / N
    GX = [0.0] * nv
    GZ = [0.0] * nv
    for i in range(nv):
        x, y, z = co[3 * i], co[3 * i + 1], co[3 * i + 2]
        GX[i] = (m00 * x + m01 * y + m02 * z + m03 - cx + rlim) / h - 0.5   # cell centres at integers
        GZ[i] = (m20 * x + m21 * y + m22 * z + m23 - cz + rlim) / h - 0.5
    grid = [bytearray(N) for _ in range(N)]   # [iz][ix]
    e = 1e-6
    fl, ce = _mm.floor, _mm.ceil
    for t in range(nt):
        ia, ib, ic = tri[3 * t], tri[3 * t + 1], tri[3 * t + 2]
        ax, az, bx, bz, cx_, cz_ = GX[ia], GZ[ia], GX[ib], GZ[ib], GX[ic], GZ[ic]
        den = (bz - cz_) * (ax - cx_) + (cx_ - bx) * (az - cz_)
        if abs(den) < 1e-9:
            continue
        x0 = max(int(fl(min(ax, bx, cx_))), 0); x1 = min(int(ce(max(ax, bx, cx_))), N - 1)
        z0 = max(int(fl(min(az, bz, cz_))), 0); z1 = min(int(ce(max(az, bz, cz_))), N - 1)
        if x0 > x1 or z0 > z1:
            continue
        k1x, k1z = (bz - cz_) / den, (cx_ - bx) / den
        k2x, k2z = (cz_ - az) / den, (ax - cx_) / den
        for Z in range(z0, z1 + 1):
            row = grid[Z]
            dz = Z - cz_
            for X in range(x0, x1 + 1):
                if row[X]:
                    continue
                dx = X - cx_
                l1 = k1x * dx + k1z * dz
                if l1 < -e:
                    continue
                l2 = k2x * dx + k2z * dz
                if l2 >= -e and 1 - l1 - l2 >= -e:
                    row[X] = 1
    c0 = (N - 1) / 2.0
    r2 = rlim * rlim
    outside = [bytearray(1 if ((ix - c0) ** 2 + (iz - c0) ** 2) * h * h > r2 else 0 for ix in range(N)) for iz in range(N)]
    # cells reachable from the region outside rlim through empty cells (== the former iterative dilation)
    reach = [bytearray(r) for r in outside]
    stack = [(iz, ix) for iz in range(N) for ix in range(N) if outside[iz][ix]]
    while stack:
        a, b_ = stack.pop()
        for c, d in ((a + 1, b_), (a - 1, b_), (a, b_ + 1), (a, b_ - 1)):
            if 0 <= c < N and 0 <= d < N and not reach[c][d] and (not grid[c][d] or outside[c][d]):
                reach[c][d] = 1; stack.append((c, d))
    seen = [bytearray(N) for _ in range(N)]
    holes = 0
    for iz in range(N):
        for ix in range(N):
            if grid[iz][ix] or reach[iz][ix] or seen[iz][ix]:
                continue
            stack = [(iz, ix)]; seen[iz][ix] = 1; n = 0
            while stack:
                a, b_ = stack.pop(); n += 1
                for c, d in ((a + 1, b_), (a - 1, b_), (a, b_ + 1), (a, b_ - 1)):
                    if 0 <= c < N and 0 <= d < N and not grid[c][d] and not reach[c][d] and not seen[c][d]:
                        seen[c][d] = 1; stack.append((c, d))
            if n >= min_cells:
                holes += 1
    return holes

scene.frame_set(1)

# ---- gear profiles
G = {}
for name in CFG['profile']:
    ob = OBJ.get(name)
    if ob is None or ob.type != 'MESH':
        continue
    try:
        d = mdata(ob)
        if d is None:
            G[name] = {'error': 'too many verts'}; continue
        V, E, P, SE = d
        o = ob.matrix_world.translation
        V2 = [(v[0], v[2]) for v in V]
        tp = teeth_profile(V2, SE if SE else E, o.x, o.z) or {}
        g, nis = genus_of(len(V), E, P)
        ys = [v[1] for v in V] or [0.0]
        G[name] = {'teeth': tp.get('teeth'), 'r_tip': tp.get('r_tip'), 'r_root': tp.get('r_root'), 'genus': g,
                   'islands': nis, 'y_mid': (min(ys) + max(ys)) / 2, 'y_min': min(ys), 'y_max': max(ys),
                   'ox': o.x, 'oy': o.y, 'oz': o.z}
        if name in CFG['spoke_gears'] and tp.get('r_root') and tp.get('r_tip'):
            rl = tp['r_root'] - 0.25 * (tp['r_tip'] - tp['r_root'])
            try:
                G[name]['sil_holes'] = sil_holes(ob, o.x, o.z, rl)
            except Exception as e:
                ERR.append(f'silhouette {name}: {e}')
    except Exception as e:
        ERR.append(f'profile {name}: {e}')
EXTRA['gear'] = G

# ---- radial stats about own origin (XZ) for discs/wheels/drums/hands/arm
RAD = {}
for name in CFG['radial']:
    ob = OBJ.get(name)
    if ob is None or ob.type != 'MESH':
        continue
    try:
        V = mdata(ob)[0]
        o = ob.matrix_world.translation
        rs = [math.hypot(v[0] - o.x, v[2] - o.z) for v in V] or [0.0]
        RAD[name] = {'rmax': max(rs), 'rmin': min(rs), 'ox': o.x, 'oy': o.y, 'oz': o.z}
    except Exception as e:
        ERR.append(f'radial {name}: {e}')
EXTRA['radial'] = RAD

def bbox_area_xz(ob):
    try:
        ev = ob.evaluated_get(_dg())
        pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
        return (max(p.x for p in pts) - min(p.x for p in pts)) * (max(p.z for p in pts) - min(p.z for p in pts))
    except Exception:
        return 0.0

comp_re = re.compile(CFG['comp_re_loose'])
# ---- DL1 chapter ring = largest DL1 mesh other than hands / countable components
try:
    cands = [o for o in colobjs('DL1') if o.type == 'MESH' and o.name not in ('DL1_minute', 'DL1_hour') and not comp_re.match(o.name)]
    if cands:
        ob = max(cands, key=bbox_area_xz)
        V = mdata(ob)[0]
        mx, mz = CFG['ports']['M']
        rs = [math.hypot(v[0] - mx, v[2] - mz) for v in V]
        EXTRA['dl1_ring'] = {'name': ob.name, 'rmax': max(rs), 'rmin': min(rs)}
except Exception as e:
    ERR.append(f'dl1_ring: {e}')

# ---- AS1 plate + islands (ecliptic ring search)
try:
    rx, rz = CFG['ports']['R']
    cands = [o for o in colobjs('AS1') if o.type == 'MESH' and not comp_re.match(o.name)]
    plate = [o for o in cands if o.name != 'AS1_rete']
    if plate:
        ob = max(plate, key=bbox_area_xz)
        V = mdata(ob)[0]
        EXTRA['as1_plate'] = {'name': ob.name, 'rmax': max(math.hypot(v[0] - rx, v[2] - rz) for v in V)}
    isl = []
    for ob in cands:
        d = mdata(ob)
        if not d:
            continue
        V, E, P, SE = d
        if len(V) > 200000:
            continue
        for grp in island_groups(len(V), E + [(p[0], q) for p in P for q in p[1:]]):
            xs = [V[i][0] for i in grp]; zs = [V[i][2] for i in grp]
            w, h = max(xs) - min(xs), max(zs) - min(zs)
            if w > 0.3 and h > 0.3:
                isl.append({'obj': ob.name, 'w': w, 'h': h, 'cx': (max(xs) + min(xs)) / 2, 'cz': (max(zs) + min(zs)) / 2})
    EXTRA['as1_islands'] = isl[:200]
except Exception as e:
    ERR.append(f'as1: {e}')

# ---- pendulum length (pivot -> bob centre), rotation-invariant (2026-10-25 fix: the old 'lowest 20% of
#      vertices' centroid sat on the bottom of the bob and read ~9.5% long)
#      axis = pivot -> farthest vertex (XZ); bob = vertices with lateral offset > 0.035 m from that axis in the
#      outer half; bob centre = midpoint of their extent along the axis (symmetric bob).
try:
    ob = OBJ.get('PD1_pendulum')
    if ob is not None:
        V = []
        for m in meshes_with_children(ob):
            d = mdata(m)
            if d:
                V += d[0]
        px, pz = CFG['pivot']
        P2 = [(v[0] - px, v[2] - pz) for v in V]
        if P2:
            far = max(P2, key=lambda q: q[0] * q[0] + q[1] * q[1])
            dmax = math.hypot(far[0], far[1])
            res = {'dmax': dmax, 'bob_len': None, 'n_bob': 0}
            if dmax > 1e-6:
                ux, uz = far[0] / dmax, far[1] / dmax
                al = [(q[0] * ux + q[1] * uz, abs(q[0] * uz - q[1] * ux)) for q in P2]
                bob = [a for a, l in al if l > 0.035 and a > 0.5 * dmax]
                if bob:
                    res['bob_len'] = (min(bob) + max(bob)) / 2
                    res['n_bob'] = len(bob)
                    res['bob_extent'] = max(bob) - min(bob)
            EXTRA['pd1'] = res
except Exception as e:
    ERR.append(f'pd1: {e}')

# ---- storey wall-face spans (2026-10-25: replaces the collection bbox for widths; buttresses, plinth,
#      string course, cornice and pinnacles legitimately stick out of the 8.4/7.6 footprint on the sheets).
#      Per storey: BVH of all its evaluated geometry; 9x9 rays per face from 10 m outside, inside a band that
#      avoids corners/plinth/cornice; the median hit coordinate is the wall face.
try:
    from mathutils.bvhtree import BVHTree
    WS = {}
    for cn, z0, z1, half, faces in CFG['wallspan']:
        Vs, Ps = [], []
        for ob in colobjs(cn):
            if ob.type not in ('MESH', 'CURVE', 'SURFACE', 'FONT', 'META'):
                continue
            try:
                d = mdata(ob)
            except Exception:
                d = None
            if not d:
                continue
            off = len(Vs)
            Vs += d[0]
            Ps += [[i + off for i in p] for p in d[2] if len(p) >= 3]
        if not Ps:
            WS[cn] = None
            continue
        bvh = BVHTree.FromPolygons([Vector(v) for v in Vs], Ps)
        res = {}
        for fk in faces:
            hits = []
            for a in range(9):
                lat = -half + 2 * half * (a + 0.5) / 9
                for b in range(9):
                    z = z0 + (z1 - z0) * (b + 0.5) / 9
                    if fk == 'xm':
                        o_, d_, k_ = (-10.0, lat, z), (1.0, 0.0, 0.0), 0
                    elif fk == 'xp':
                        o_, d_, k_ = (10.0, lat, z), (-1.0, 0.0, 0.0), 0
                    elif fk == 'ym':
                        o_, d_, k_ = (lat, -10.0, z), (0.0, 1.0, 0.0), 1
                    else:
                        o_, d_, k_ = (lat, 10.0, z), (0.0, -1.0, 0.0), 1
                    r = bvh.ray_cast(Vector(o_), Vector(d_))
                    if r[0] is not None:
                        hits.append(r[0][k_])
            hits.sort()
            res[fk] = {'med': hits[len(hits) // 2] if hits else None, 'n': len(hits)}
        WS[cn] = res
    EXTRA['wallspan'] = WS
except Exception as e:
    ERR.append(f'wallspan: {e}')

# ---- TW4 section hull at z = 22.5
try:
    zc = CFG['tw4_z']
    pts = []
    for ob in colobjs('TW4'):
        if ob.type != 'MESH' or comp_re.match(ob.name):
            continue
        V, E, P, SE = mdata(ob)
        for i, j in E:
            a, b = V[i], V[j]
            if (a[2] - zc) * (b[2] - zc) < 0:
                t = (zc - a[2]) / (b[2] - a[2])
                pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    EXTRA['tw4_hull'] = hull_corners(pts) if pts else 0
    EXTRA['tw4_npts'] = len(pts)
except Exception as e:
    ERR.append(f'tw4: {e}')

# ---- TW3 opening island centroids (single-object build)
try:
    CI = {}
    for name in CFG['centroids']:
        ob = OBJ.get(name)
        if ob is None or ob.type != 'MESH':
            continue
        V, E, P, SE = mdata(ob)
        CI[name] = [[sum(V[i][k] for i in g) / len(g) for k in range(3)] for g in island_groups(len(V), E)]
    EXTRA['centroids'] = CI
except Exception as e:
    ERR.append(f'centroids: {e}')

# ---- text objects
try:
    EXTRA['fonts'] = [{'name': o.name, 'colls': [c.name for c in o.users_collection], 'body': o.data.body}
                      for o in OBJ if o.type == 'FONT']
except Exception as e:
    ERR.append(f'fonts: {e}')

# ---- east wall ray cast
try:
    tw = {}
    for cn in ('TW2', 'TW3'):
        tw[cn] = set(o.name for o in colobjs(cn))
    res = {}
    for cn, z0, z1, w in CFG['eastcut']:
        hit = tot = 0
        dgx = _dg()
        for iy in range(50):
            y = -w / 2 + 0.1 + (w - 0.2) * (iy + 0.5) / 50
            for iz in range(50):
                z = z0 + 0.05 + (z1 - z0 - 0.1) * (iz + 0.5) / 50
                tot += 1
                r = scene.ray_cast(dgx, Vector((10.0, y, z)), Vector((-1.0, 0.0, 0.0)))
                if r[0] and r[1].x >= 3.4 and r[1].x <= 4.3:
                    o = r[4]
                    nm = getattr(getattr(o, 'original', o), 'name', '')
                    if nm in tw['TW2'] or nm in tw['TW3']:
                        hit += 1
        res[cn] = hit / tot
    EXTRA['eastcut'] = res
except Exception as e:
    ERR.append(f'eastcut: {e}')

# ---- per-frame loop
MV = [OBJ.get(n) for n in CFG['movers']]
MV = [o for o in MV if o is not None]
R1 = {o.name: o.matrix_world.to_3x3().normalized() for o in MV}
O1 = {o.name: o.matrix_world.translation.copy() for o in MV}
R1i = {k: v.inverted() for k, v in R1.items()}
ANG = {o.name: [0.0] for o in MV}
PREV = {o.name: 0.0 for o in MV}
DRIFT = {o.name: 0.0 for o in MV}
AXD = {o.name: 0.0 for o in MV}
HANDLOC = {}
for hn in ('DL1_minute', 'DL1_hour'):
    ob = OBJ.get(hn)
    if ob is not None and ob.type == 'MESH':
        try:
            HANDLOC[hn] = [Vector(v) for v in mdata(ob, world=False)[0]]
        except Exception as e:
            ERR.append(f'hand {hn}: {e}')
HANDS = {}
mx, mz = CFG['ports']['M']

def hand_dir(hn):
    ob = OBJ.get(hn)
    mw = ob.matrix_world
    best = None
    for v in HANDLOC[hn]:
        w = mw @ v
        d = math.hypot(w.x - mx, w.z - mz)
        if best is None or d > best[0]:
            best = (d, w)
    d, w = best
    return {'angle': math.degrees(math.atan2(w.x - mx, w.z - mz)) % 360.0, 'len': d}

WTS = {}
for wn in ('WT1_weight', 'WT2_weight'):
    ob = OBJ.get(wn)
    if ob is not None:
        WTS[wn] = (ob, [])

def zmin_of(ob):
    zs = []
    dgx = _dg()
    for m in meshes_with_children(ob):
        ev = m.evaluated_get(dgx)
        zs += [(ev.matrix_world @ Vector(c)).z for c in ev.bound_box]
    return min(zs) if zs else None

# striker: hammer points (arm-local) and BL1 BVH
STRK = None
try:
    from mathutils.bvhtree import BVHTree
    arm = OBJ.get('AU3_arm'); bell = OBJ.get('BL1_bell')
    if arm is not None and bell is not None and bell.type == 'MESH':
        Vb, Eb, Pb, _ = mdata(bell)
        bvh = BVHTree.FromPolygons([Vector(v) for v in Vb], [list(p) for p in Pb])
        ainv = arm.matrix_world.inverted()
        pts = []
        for m in meshes_with_children(arm):
            pts += [ainv @ Vector(v) for v in mdata(m)[0]]
        if pts:
            rmax = max(p.length for p in pts)
            far = [p for p in pts if p.length >= 0.6 * rmax]
            step = max(1, len(far) // 600)
            STRK = {'bvh': bvh, 'pts': far[::step], 'dist': [], 'pen': []}
            EXTRA['arm_len'] = rmax
except Exception as e:
    ERR.append(f'striker init: {e}')

def strike_sample():
    mw = OBJ.get('AU3_arm').matrix_world
    dmin = 1e9; pen = 0.0
    for p in STRK['pts']:
        w = mw @ p
        r = STRK['bvh'].find_nearest(w)
        if r[0] is None:
            continue
        loc, nrm, idx, dist = r
        if dist < dmin:
            dmin = dist
        s = (w - loc).dot(nrm)
        if s < 0 and dist < 0.2 and dist > pen:
            pen = dist
    STRK['dist'].append(round(dmin, 4)); STRK['pen'].append(round(pen, 4))

for f in range(1, CFG['nf'] + 1):
    try:
        if f > 1:
            scene.frame_set(f)
        for o in MV:
            n = o.name
            if f > 1:
                mw = o.matrix_world
                Rr = mw.to_3x3().normalized() @ R1i[n]
                th = math.degrees(math.atan2(Rr[0][2], Rr[0][0]))
                ANG[n].append(ANG[n][-1] + _wrap180(th - PREV[n]))
                PREV[n] = th
                t = mw.translation
                dd = math.hypot(t.x - O1[n].x, t.z - O1[n].z)
                if dd > DRIFT[n]:
                    DRIFT[n] = dd
                q = Rr.to_quaternion()
                if q.angle > math.radians(5) and q.angle < math.radians(355):
                    ax = q.axis
                    dev = math.degrees(math.acos(min(1.0, abs(ax.y) / max(1e-9, ax.length))))
                    if dev > AXD[n]:
                        AXD[n] = dev
        if f in (1, 721):
            for hn in HANDLOC:
                HANDS.setdefault(hn, {})['f%d' % f] = hand_dir(hn)
        for wn, (ob, lst) in WTS.items():
            lst.append(zmin_of(ob))
        if STRK:
            strike_sample()
    except Exception as e:
        ERR.append(f'frame {f}: {e}')
        if len(ERR) > 150:
            break
ROT = {}
for o in MV:
    Rr = o.matrix_world.to_3x3().normalized() @ R1i[o.name]
    ROT[o.name] = math.degrees(Rr.to_quaternion().angle)
EXTRA['movers'] = {o.name: {'ang': [round(a, 4) for a in ANG[o.name]], 'drift': DRIFT[o.name], 'axis_dev': AXD[o.name],
                            'rot_last': ROT[o.name], 'o1': list(O1[o.name])} for o in MV}
EXTRA['hands'] = HANDS
EXTRA['weights'] = {k: v[1] for k, v in WTS.items()}
if STRK:
    EXTRA['strike'] = {'dist': STRK['dist'], 'pen': STRK['pen']}
scene.frame_set(1)
'''


def build_extra_py(ak):
    gears = list(ak['gears'].keys())
    ports = {k: v for k, v in ak['interfaces']['coaxial_ports'].items()}
    cfg = {
        'profile': gears + ['AU3_cam'],
        'radial': ['DL2_disc', 'CR1_ring', 'MP1_disc', 'AU1_wheel', 'AU2_wheel', 'WT1_drum', 'WT2_drum', 'DL1_minute',
                   'DL1_hour', 'AU3_arm', 'AS1_rete'],
        'movers': gears + MOVERS_EXTRA,
        'ports': ports,
        'comp_re_loose': '^(' + '|'.join(f'{u}_({"|".join(c)})' for u, c in COMPONENTS.items()) + r')(_\d+)?$',
        'centroids': ['TW3_opening'],
        'tw4_z': 22.5,
        'eastcut': [['TW2', 6.0, 15.6, 8.4], ['TW3', 15.6, 21.2, 7.6]],
        'nf': NF,
        'pivot': ak['units']['ES1']['derived']['anchor_pivot_xz'],
        # [collection, z_lo, z_hi, lateral half-range, faces]; bands avoid plinth (0.6), string course (5.7-5.95),
        # TW2 cornice (15.2-15.6), corner buttresses/pinnacles; TW2/TW3 east wall is cut away -> no 'xp'
        'wallspan': [['TW1', 1.0, 5.5, 3.3, ['xm', 'xp', 'ym', 'yp']], ['TW2', 6.5, 15.0, 3.3, ['xm', 'ym', 'yp']],
                     ['TW3', 15.9, 20.4, 2.9, ['xm', 'ym', 'yp']], ['TW4', 21.3, 21.7, 2.9, ['xm', 'xp', 'ym', 'yp']]],
        'spoke_gears': [n for n in gears if n not in ('MP1_ring', 'ES1_escape')],
    }
    return EXTRA_PY.replace('__CFG__', repr(json.dumps(cfg)))


# ---------------------------------------------------------------------------------------------
# image std (B04/B05)
def _png_gray_std_pure(p):
    data = pathlib.Path(p).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    pos, idat, w = 8, b'', None
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', body)
        elif typ == b'IDAT':
            idat += body
        pos += 12 + ln
    if w is None or bd != 8 or il != 0 or ct not in (0, 2, 4, 6):
        return None
    bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(idat)
    stride = w * bpp
    prev = bytearray(stride)
    vals = []
    i = 0
    for y in range(h):
        ft = raw[i]; line = bytearray(raw[i + 1:i + 1 + stride]); i += 1 + stride
        if ft == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 255
        elif ft == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif ft == 3:
            for x in range(stride):
                line[x] = (line[x] + ((line[x - bpp] if x >= bpp else 0) + prev[x]) // 2) & 255
        elif ft == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]; c = prev[x - bpp] if x >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        if y % 8 == 0:
            for x in range(0, w, 8):
                o = x * bpp
                vals.append(line[o] if bpp < 3 else (299 * line[o] + 587 * line[o + 1] + 114 * line[o + 2]) / 1000)
    n = len(vals)
    m = sum(vals) / n
    return math.sqrt(sum((v - m) ** 2 for v in vals) / n)


def gray_std(p):
    try:
        from PIL import Image
        im = Image.open(p).convert('L')
        im.thumbnail((480, 270))
        px = list(im.getdata())
        m = sum(px) / len(px)
        return math.sqrt(sum((v - m) ** 2 for v in px) / len(px))
    except ImportError:
        pass
    except Exception:
        return None
    try:
        if shutil.which('ffmpeg'):
            o = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', 'scale=480:270', '-f', 'rawvideo',
                                '-pix_fmt', 'gray', '-'], capture_output=True, timeout=60).stdout
            if o:
                m = sum(o) / len(o)
                return math.sqrt(sum((v - m) ** 2 for v in o) / len(o))
    except Exception:
        pass
    try:
        return _png_gray_std_pure(p)
    except Exception:
        return None


# ---------------------------------------------------------------------------------------------
def _slope(y):
    n = len(y)
    if n < 2:
        return None
    mx = (n - 1) / 2
    my = sum(y) / n
    num = sum((i - mx) * (v - my) for i, v in enumerate(y))
    den = sum((i - mx) ** 2 for i in range(n))
    return num / den


def _turning_points(y, h):
    """Indices of alternating extrema with hysteresis h (no boundary points). Returns [(idx, 'max'|'min')]."""
    out = []
    if not y:
        return out
    direction = 0
    ext_i, ext_v = 0, y[0]
    lo_i, lo_v, hi_i, hi_v = 0, y[0], 0, y[0]
    for i, v in enumerate(y):
        if direction == 0:
            if v > hi_v:
                hi_i, hi_v = i, v
            if v < lo_v:
                lo_i, lo_v = i, v
            if hi_v - lo_v > h:
                direction = 1 if hi_i > lo_i else -1
                ext_i, ext_v = (hi_i, hi_v) if direction == 1 else (lo_i, lo_v)
        elif direction == 1:
            if v > ext_v:
                ext_i, ext_v = i, v
            elif ext_v - v > h:
                out.append((ext_i, 'max'))
                direction, ext_i, ext_v = -1, i, v
        else:
            if v < ext_v:
                ext_i, ext_v = i, v
            elif v - ext_v > h:
                out.append((ext_i, 'min'))
                direction, ext_i, ext_v = 1, i, v
    return out


def _cw(a, b):
    """absolute angular difference in degrees."""
    d = (a - b) % 360.0
    return min(d, 360.0 - d)


def _dxz(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


_DEFER = {}


_GATE = {}


def run(ctx):
    R = {}
    _DEFER.clear(); _GATE.clear()
    ak = ctx.get('answer') or json.loads((pathlib.Path(ctx['tests']) / 'answer-key.json').read_text(encoding='utf-8'))
    out = pathlib.Path(ctx['out'])
    items = {i['id'] for i in ctx['items']}

    # ---------- file-only items
    def render_ok(fn):
        p = out / 'renders' / fn
        if not p.exists():
            return False, f'{fn} missing'
        sz = png_size(p)
        if sz != (1920, 1080):
            return False, f'{fn} size {sz}'
        s = gray_std(p)
        if s is None:
            return False, f'{fn} could not be decoded'
        if s < 8:
            return False, f'{fn} gray std {s:.2f} < 8 (blank)'
        return True, f'{fn} 1920x1080 std {s:.1f}'
    try:
        a, d = render_ok('overview.png')
        R['B04'] = ok(d) if a else bad(d)
    except Exception as e:
        R['B04'] = bad(f'error {e}')
    try:
        r1 = render_ok('cutaway.png'); r2 = render_ok('front_dials.png')
        R['B05'] = ok(r1[1] + '; ' + r2[1]) if (r1[0] and r2[0]) else bad(r1[1] + '; ' + r2[1])
    except Exception as e:
        R['B05'] = bad(f'error {e}')
    man = load_manifest(out)
    try:
        if not isinstance(man, list):
            R['B06'] = bad('manifest.json missing/unparseable or not an array')
        else:
            miss = [i for i, e in enumerate(man) if not (isinstance(e, dict) and all(k in e for k in ('id', 'collection', 'built', 'params')))]
            ids = [e.get('id') for e in man if isinstance(e, dict)]
            if len(man) != 28 or miss or set(ids) != set(UNITS):
                R['B06'] = bad(f'len={len(man)} entries_missing_fields={miss[:5]} missing_ids={sorted(set(UNITS) - set(ids))} extra={sorted(set(ids) - set(UNITS))[:5]}')
            else:
                R['B06'] = ok('28 entries, fields ok, ids match')
    except Exception as e:
        R['B06'] = bad(f'error {e}')

    # ---------- scene
    try:
        S = Scene.load(ctx, islands_regex=COMP_RE, extra_py=build_extra_py(ak), timeout=3000)
    except Exception as e:
        S = Scene(None, f'Scene.load error {e}')
    scene_items = [i['id'] for i in ctx['items'] if i['id'] not in ('B04', 'B05', 'B06', 'G11')]
    if S.err or not S.data:
        why = f'scene unavailable: {S.err}'
        _GATE['core_fail'] = why
        for i in scene_items:
            if i in ('G02', 'G09'):
                _DEFER[i] = (False, why)
            R[i] = bad(why)
        for i in ('G02', 'G09'):
            R.pop(i, None)
        return R

    O = S.objects
    X = S.data.get('extra') or {}
    GP = X.get('gear', {})
    MV = X.get('movers', {})
    RAD = X.get('radial', {})
    gears = ak['gears']
    ports = ak['interfaces']['coaxial_ports']
    arbors = ak['arbors']

    def guard(iid, fn):
        try:
            R[iid] = fn()
        except Exception as e:
            R[iid] = bad(f'check error: {type(e).__name__}: {e}')

    # B01
    def b01():
        sc = S.data.get('scene', {})
        p = []
        if sc.get('unit_system') != 'METRIC':
            p.append(f"unit_system={sc.get('unit_system')}")
        if not close(sc.get('scale_length', 0), 1.0, 0, 1e-6):
            p.append(f"scale_length={sc.get('scale_length')}")
        _GATE['core_fail'] = '; '.join(p)  # opens + units: the only part that gates other items
        if not S.has_coll('SITE'):
            p.append('no SITE collection')
        return bad('; '.join(p)) if p else ok('opens; METRIC; scale 1.0; SITE present')
    guard('B01', b01)

    def b02():
        miss = [u for u in UNITS if not S.has_coll(u)]
        empty = [u for u in UNITS if S.has_coll(u) and not any(O.get(n, {}).get('type') == 'MESH' for n in S.coll(u))]
        return bad(f'missing={miss} no_mesh={empty}') if (miss or empty) else ok('28 unit collections, each with mesh')
    guard('B02', b02)

    def b03():
        sc = S.data.get('scene', {})
        v = (sc.get('frame_start'), sc.get('frame_end'), sc.get('fps'), sc.get('fps_base'))
        good = v[0] == 1 and v[1] == 1440 and v[2] == 24 and abs(float(v[3] or 0) - 1.0) < 1e-6
        return ok(f'frames/fps {v}') if good else bad(f'frames/fps {v}')
    guard('B03', b03)

    def b07():
        m = MV.get('DL1_minute')
        if not m:
            return bad('DL1_minute missing or not sampled')
        d31 = abs(m['ang'][30] - m['ang'][0]) if len(m['ang']) > 30 else 0
        rot = [g for g in gears if g in MV and MV[g].get('ang') and max(abs(a) for a in MV[g]['ang']) > 1.0]
        good = d31 > 1.0 and len(rot) >= 20
        return (ok if good else bad)(f'minute f1->f31 {d31:.1f} deg; gears rotated f1->f1440: {len(rot)}')
    guard('B07', b07)

    WSP = X.get('wallspan') or {}

    def wall_widths(u):
        """Measured outer wall-face widths (x, y) of a storey from the ray-cast medians; None if not measurable.
        TW2/TW3 have no east wall: x width = 2*|west face|."""
        w = WSP.get(u) or {}
        g = lambda k: (w.get(k) or {}).get('med')
        xm, xp, ym, yp = g('xm'), g('xp'), g('ym'), g('yp')
        if u in ('TW2', 'TW3'):
            wx = -2 * xm if xm is not None else None
        else:
            wx = xp - xm if (xm is not None and xp is not None) else None
        wy = yp - ym if (ym is not None and yp is not None) else None
        return wx, wy

    def b08():
        bb = S.bbox(sum((S.coll(u) for u in ('TW1', 'TW2', 'TW3', 'TW4')), []))
        if not bb:
            return bad('no TW geometry')
        wx, wy = wall_widths('TW1')
        good = (wx is not None and wy is not None and abs(wx - 8.4) <= 0.15 and abs(wy - 8.4) <= 0.15
                and abs(bb[0][2]) <= 0.05 and abs(bb[1][2] - 31.0) <= 0.3)
        f = lambda v: 'n/a' if v is None else f'{v:.3f}'
        return (ok if good else bad)(f'TW1 wall faces x {f(wx)} y {f(wy)} (want 8.4±0.15); TW z {bb[0][2]:.3f}..{bb[1][2]:.3f}')
    guard('B08', b08)

    def b09():
        r = X.get('dl1_ring')
        if not r or r['name'] not in O:
            return bad('no DL1 chapter-ring candidate')
        bb = O[r['name']].get('bbox_world')
        c = S.center(bb)
        good = _dxz((c[0], c[2]), ports['M']) <= 0.03 and -4.40 <= bb[0][1] <= -4.15
        return (ok if good else bad)(f"{r['name']} centre xz ({c[0]:.3f},{c[2]:.3f}); min y {bb[0][1]:.3f}")
    guard('B09', b09)

    # M01
    def m01():
        p = []
        for u in ('TW1', 'TW2', 'TW3', 'TW4'):
            pr = ak['units'][u]['params']
            bb = S.coll_bbox(u)
            if not bb:
                p.append(f'{u} empty'); continue
            w = pr.get('width', pr.get('base'))
            wx, wy = wall_widths(u)
            # TW4: the drawn finial star rays reach ~31.23 above the dimensioned 31.0
            top_hi = 0.35 if u == 'TW4' else 0.15
            okz = abs(bb[0][2] - pr['z0']) <= 0.15 and -0.15 <= bb[1][2] - pr['z1'] <= top_hi
            okw = wx is not None and wy is not None and abs(wx - w) <= 0.15 and abs(wy - w) <= 0.15
            if not (okz and okw):
                f = lambda v: 'n/a' if v is None else f'{v:.2f}'
                p.append(f'{u} z {bb[0][2]:.2f}-{bb[1][2]:.2f} wall faces {f(wx)}x{f(wy)} (want {pr["z0"]}-{pr["z1"]}, {w})')
        ec = X.get('eastcut') or {}
        for u in ('TW2', 'TW3'):
            v = ec.get(u)
            if v is None or v > 0.30:
                p.append(f'{u} east-wall hit ratio {v}')
        return bad('; '.join(p)) if p else ok(f'storeys within 0.15; east cut ratios {ec}')
    guard('M01', m01)

    def tol(a, b):
        return a is not None and abs(a - b) <= max(0.03 * b, 0.03)

    def m02():
        p = []
        r = X.get('dl1_ring')
        if not r or not (tol(2 * r['rmax'], 3.0) and tol(2 * r['rmin'], 2.36)):
            p.append(f'DL1 ring OD/ID {r and round(2 * r["rmax"], 3)}/{r and round(2 * r["rmin"], 3)}')
        for n, L in (('DL1_minute', 1.38), ('DL1_hour', 0.98)):
            v = RAD.get(n, {}).get('rmax')
            if not tol(v, L):
                p.append(f'{n} len {v}')
        pl = X.get('as1_plate')
        if not pl or not tol(2 * pl['rmax'], 2.30):
            p.append(f'AS1 plate D {pl and round(2 * pl["rmax"], 3)}')
        rr = ports['R']
        ecl = [i for i in X.get('as1_islands', []) if tol(i['w'], 1.44) and tol(i['h'], 1.44)
               and abs(_dxz((i['cx'], i['cz']), rr) - 0.33) <= 0.03]
        if not ecl:
            p.append('no AS1 island ~D1.44 offset 0.33 from R (ecliptic ring)')
        for n, D in (('CR1_ring', 1.40), ('MP1_disc', 0.60), ('DL2_disc', 1.32)):
            v = RAD.get(n, {}).get('rmax')
            if v is None or not tol(2 * v, D):
                p.append(f'{n} D {v and round(2 * v, 3)} want {D}')
        return bad('; '.join(p)) if p else ok('all zone B sizes within max(3%,0.03)')
    guard('M02', m02)

    def m03():
        p = []
        for n, port in (('DL2_disc', 'D24'), ('CR1_ring', 'C'), ('MP1_disc', 'MO'), ('AS1_rete', 'M')):
            m = MV.get(n)
            if not m:
                p.append(f'{n} missing'); continue
            d = _dxz((m['o1'][0], m['o1'][2]), ports[port])
            if d > 0.02 or m['drift'] > 0.005:
                p.append(f'{n} off {d:.3f} drift {m["drift"]:.4f}')
        return bad('; '.join(p)) if p else ok('dials coaxial with D24/C/MO/M, no drift')
    guard('M03', m03)

    def gear_size(names):
        p = []
        for n in names:
            g = GP.get(n)
            if not g or g.get('r_tip') is None:
                p.append(f'{n} missing'); continue
            t = gears[n]
            # ES1_escape: sheet dimension 0.180 (tip_d_m) or the global rule m(z+2) (tip_d_rule_m) are both accepted
            want = [t['tip_d_m']] + ([t['tip_d_rule_m']] if t.get('tip_d_rule_m') else [])
            if all(abs(2 * g['r_tip'] - w) > 0.02 * w for w in want) or abs(g['y_mid'] - t['y']) > 0.03:
                p.append(f"{n} tipD {2 * g['r_tip']:.3f}/{'|'.join(str(w) for w in want)} y {g['y_mid']:.3f}/{t['y']}")
        return p

    def by_units(us):
        return [n for n, g in gears.items() if g['unit'] in us]

    def m04():
        p = gear_size(by_units(('GT1', 'GT9', 'ES1')))
        return bad('; '.join(p)) if p else ok('zone C gears tip D ±2%, layer y ±0.03')
    guard('M04', m04)

    def m05():
        p = gear_size(by_units(('GT2', 'GT5', 'GT3', 'GT6', 'GT4', 'MP1')))
        return bad('; '.join(p)) if p else ok('zone D gears + MP1_ring tip D ±2%, layer y ±0.03')
    guard('M05', m05)

    def m06():
        p = gear_size(by_units(('GT7', 'GT8')))
        for b in ('BL1', 'BL2'):
            pr = ak['units'][b]['params']
            o = O.get(f'{b}_bell')
            if not o or not o.get('bbox_world'):
                p.append(f'{b}_bell missing'); continue
            bb = o['bbox_world']; sz = S.size(bb)
            lip = max(sz[0], sz[1])
            cx, cy = (bb[0][0] + bb[1][0]) / 2, (bb[0][1] + bb[1][1]) / 2
            if abs(lip - pr['lip_d']) > 0.03 * pr['lip_d'] or abs(sz[2] - pr['height']) > 0.03 * pr['height'] \
                    or abs(cx - pr['centre_xz'][0]) > 0.05 or abs(bb[0][2] - pr['centre_xz'][1]) > 0.05 or abs(cy) > 0.05:
                p.append(f'{b} lipD {lip:.3f} H {sz[2]:.3f} lip centre ({cx:.2f},{cy:.2f},{bb[0][2]:.2f})')
        return bad('; '.join(p)) if p else ok('GT7/GT8 sized; bells per sheets')
    guard('M06', m06)

    def m07():
        p = gear_size(by_units(('GT10',)))
        for n, port in (('AU1_wheel', 'P1'), ('AU2_wheel', 'P2')):
            r = RAD.get(n)
            if not r:
                p.append(f'{n} missing'); continue
            if abs(2 * r['rmax'] - 1.40) > 0.03 * 1.40 or _dxz((r['ox'], r['oz']), ports[port]) > 0.02:
                p.append(f"{n} D {2 * r['rmax']:.3f} origin ({r['ox']:.3f},{r['oz']:.3f})")
        a = RAD.get('AU3_arm')
        if not a:
            p.append('AU3_arm missing')
        elif _dxz((a['ox'], a['oz']), (1.15, 19.5)) > 0.05 or abs(a['rmax'] - 0.90) > 0.05 * 0.90:
            p.append(f"AU3_arm pivot ({a['ox']:.3f},{a['oz']:.3f}) len {a['rmax']:.3f}")
        return bad('; '.join(p)) if p else ok('GT10 sized; parade wheels on P1/P2; AU3 arm ok')
    guard('M07', m07)

    def m08():
        p = []
        piv = ak['units']['ES1']['derived']['anchor_pivot_xz']
        a = O.get('ES1_anchor')
        if not a:
            p.append('ES1_anchor missing')
        elif _dxz((a['location'][0], a['location'][2]), piv) > 0.02:
            p.append(f"anchor pivot {a['location']}")
        pdm = X.get('pd1') or {}
        L0 = ak['units']['PD1']['params']['length']; bd = ak['units']['PD1']['params']['bob_d']
        if pdm.get('dmax') is None:
            p.append('PD1 pendulum not measured')
        else:
            L = pdm['bob_len'] if pdm.get('bob_len') is not None else pdm['dmax'] - bd / 2
            if abs(L - L0) > 0.02 * L0:
                p.append(f"pendulum length {L:.3f} (bob-centre {pdm.get('bob_len')}, farthest {pdm['dmax']:.3f})")
        for dn, D, gn in (('WT1_drum', 0.60, 'GT1_a'), ('WT2_drum', 0.44, 'GT7_a')):
            r = RAD.get(dn); g = GP.get(gn)
            if not r or not g:
                p.append(f'{dn}/{gn} missing'); continue
            if abs(2 * r['rmax'] - D) > max(0.03 * D, 0.01) or _dxz((r['ox'], r['oz']), (g['ox'], g['oz'])) > 0.02:
                p.append(f"{dn} D {2 * r['rmax']:.3f} off-axis {_dxz((r['ox'], r['oz']), (g['ox'], g['oz'])):.3f}")
        return bad('; '.join(p)) if p else ok('anchor pivot, pendulum length, drums ok')
    guard('M08', m08)

    def m09():
        p = []
        m = MV.get('DL1_minute'); h = (X.get('hands') or {}).get('DL1_hour', {}).get('f1')
        mf = (X.get('hands') or {}).get('DL1_minute', {}).get('f1')
        if not m or not mf:
            p.append('minute hand missing')
        else:
            s = _slope(m['ang'])
            if abs(s - 3.0) > 0.005 * 3.0:
                p.append(f'minute {s:.4f} deg/frame')
            if _cw(mf['angle'], 0) > 2:
                p.append(f"minute f1 at {mf['angle']:.1f}")
        if not h or _cw(h['angle'], 300) > 2:
            p.append(f"hour f1 at {h and round(h['angle'], 1)}")
        g = MV.get('GT7_a')
        if not g:
            p.append('GT7_a missing')
        else:
            s = _slope(g['ang'])
            if abs(s + 0.75) > 0.005 * 0.75:
                p.append(f'GT7_a {s:.4f} deg/frame')
        return bad('; '.join(p)) if p else ok('minute +3.000, 12 o\'clock; hour at 10; SB -0.750')
    guard('M09', m09)

    def m10():
        p = []
        for n in gears:
            m = MV.get(n)
            if not m:
                p.append(f'{n} missing'); continue
            amp = max(abs(a) for a in m['ang'])
            if m['drift'] > 0.005 or m['axis_dev'] > 1.0 or amp < 1.0:
                p.append(f"{n} drift {m['drift']:.4f} axis {m['axis_dev']:.2f} amp {amp:.1f}")
        return bad(f'{len(p)} bad: ' + '; '.join(p[:12])) if p else ok('46 gears rotate about own Y-parallel axes')
    guard('M10', m10)

    def m11():
        if not isinstance(man, list):
            return bad('manifest unusable')
        built, p = 0, []
        for e in man:
            if not isinstance(e, dict) or not str(e.get('id', '')).startswith('GT') or e.get('built') is not True:
                continue
            built += 1
            teeth = (e.get('params') or {}).get('teeth') or {}
            if not teeth:
                p.append(f"{e['id']} no teeth"); continue
            for lab, z in teeth.items():
                n = lab if str(lab).startswith(e['id'] + '_') else f"{e['id']}_{lab}"
                meas = GP.get(n, {}).get('teeth')
                if meas is None or int(meas) != int(z):
                    p.append(f'{n} declared {z} measured {meas}')
        if built < 8:
            p.append(f'only {built} trains built=true')
        return bad('; '.join(p[:12])) if p else ok(f'{built} built trains; declared teeth == measured')
    guard('M11', m11)

    def m12():
        m = MV.get('PD1_pendulum')
        if not m:
            return bad('PD1_pendulum missing')
        a = m['ang']; mu = sum(a) / len(a); y = [v - mu for v in a]
        zc = [i + y[i] / (y[i] - y[i + 1]) for i in range(len(y) - 1) if (y[i] < 0 <= y[i + 1]) or (y[i] >= 0 > y[i + 1])]
        if len(zc) < 3:
            return bad('pendulum does not swing')
        per = 2 * (zc[-1] - zc[0]) / (len(zc) - 1)
        tp = _turning_points(y, 0.5)
        amp = sum(abs(y[i]) for i, _ in tp) / len(tp) if tp else 0
        piv = ak['units']['ES1']['derived']['anchor_pivot_xz']
        off = _dxz((m['o1'][0], m['o1'][2]), piv)
        T = ak['units']['PD1']['derived']['period_frames']
        good = abs(per - T) <= 0.03 * T and abs(amp - 4.0) <= 0.5 and off <= 0.02 and m['drift'] <= 0.005
        return (ok if good else bad)(f'period {per:.2f} (want {T:.1f}), amplitude {amp:.2f}, pivot off {off:.3f}')
    guard('M12', m12)

    def m13():
        p = []
        W = X.get('weights') or {}
        for n, u in (('WT1_weight', 'WT1'), ('WT2_weight', 'WT2')):
            z = [v for v in (W.get(n) or []) if v is not None]
            dv = ak['units'][u]['derived']; z0 = ak['units'][u]['params']['start_bottom_z']
            if len(z) < NF:
                p.append(f'{n} not sampled'); continue
            drop = z[0] - z[-1]
            mono = all(z[i + 1] <= z[i] + 1e-4 for i in range(len(z) - 1))
            if abs(drop - dv['drop_m_f1_to_f1440']) > 0.05 * dv['drop_m_f1_to_f1440'] or not mono or abs(z[0] - z0) > 0.05:
                p.append(f'{n} start {z[0]:.3f} drop {drop:.3f} monotonic {mono}')
        return bad('; '.join(p)) if p else ok('weights descend by drum arc, monotonic')
    guard('M13', m13)

    def m14():
        H = X.get('hands') or {}
        mm = H.get('DL1_minute', {}).get('f721'); hh = H.get('DL1_hour', {}).get('f721')
        if not mm or not hh:
            return bad('hands missing')
        good = _cw(mm['angle'], 0) <= 2 and _cw(hh['angle'], 120) <= 2
        return (ok if good else bad)(f"f721 minute {mm['angle']:.1f} hour {hh['angle']:.1f}")
    guard('M14', m14)

    def m15():
        p = []
        pairs = {frozenset((m['a'], m['b'])) for m in ak['meshes']}
        names = [n for n in gears if n in GP and GP[n].get('r_tip')]
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                ga, gb = GP[a], GP[b]
                if frozenset((a, b)) in pairs or abs(ga['y_mid'] - gb['y_mid']) >= 0.05:
                    continue
                d = _dxz((ga['ox'], ga['oz']), (gb['ox'], gb['oz']))
                if d < ga['r_tip'] + gb['r_tip'] - 0.002:
                    p.append(f'{a}x{b} d {d:.3f} < {ga["r_tip"] + gb["r_tip"]:.3f}')
        for n in names:
            bb = O.get(n, {}).get('bbox_world')
            if bb and (max(abs(bb[0][0]), abs(bb[1][0])) > 4.2 or max(abs(bb[0][1]), abs(bb[1][1])) > 4.2):
                p.append(f'{n} outside tower')
        if len(names) < len(gears):
            p.append(f'{len(gears) - len(names)} gears missing')
        return bad('; '.join(p[:12])) if p else ok('no same-layer interference; all gears inside')
    guard('M15', m15)

    # counts
    def count(u, c):
        nn = [n for n in O if re.fullmatch(rf'{u}_{c}_\d+', n)]
        if nn:
            return len(nn), 'objects'
        o = O.get(f'{u}_{c}')
        if o:
            ni = sum(1 for i in (S.data.get('instances') or []) if i.get('instancer') == f'{u}_{c}')
            return (o.get('islands') or 0) + ni, ('islands+instances' if ni else 'islands')
        return 0, 'none'

    def check_counts(spec):
        p = []
        for (u, c), want in spec.items():
            n, how = count(u, c)
            if n != want:
                p.append(f'{u}_{c}={n}({how}) want {want}')
        return p

    def tw3_faces():
        nn = sorted(n for n in O if re.fullmatch(r'TW3_opening_\d+', n))
        if nn:
            cs = [S.center(O[n]['bbox_world']) for n in nn if O[n].get('bbox_world')]
        else:
            cs = (X.get('centroids') or {}).get('TW3_opening') or []
        f = {'N': 0, 'S': 0, 'E': 0, 'W': 0}
        for c in cs:
            if abs(c[0]) > abs(c[1]):
                f['E' if c[0] > 0 else 'W'] += 1
            else:
                f['N' if c[1] > 0 else 'S'] += 1
        return f

    def g01():
        tw = ak['units']
        p = check_counts({('TW1', 'door'): tw['TW1']['params']['front_door_arches'],
                          ('TW1', 'buttress'): 4 * tw['TW1']['params']['buttresses_per_corner'],
                          ('TW1', 'course'): tw['TW1']['params']['string_courses'],
                          ('TW2', 'window'): tw['TW2']['params']['side_windows_west'],
                          ('TW2', 'pilaster'): tw['TW2']['params']['pilasters_front'],
                          ('TW3', 'post'): tw['TW3']['params']['balustrade_posts'],
                          ('TW3', 'opening'): 6,
                          ('TW4', 'dormer'): tw['TW4']['params']['dormers'],
                          ('TW4', 'pinnacle'): tw['TW4']['params']['corner_pinnacles']})
        f = tw3_faces()
        if not (f['N'] == 2 and f['S'] == 2 and f['W'] == 2 and f['E'] == 0):
            p.append(f'TW3 openings per face {f}')
        if X.get('tw4_hull') != 8:
            p.append(f"TW4 section corners at z=22.5: {X.get('tw4_hull')}")
        return bad('; '.join(p)) if p else ok('zone A counts, TW3 2/face N-S-W, TW4 octagonal')
    guard('G01', g01)

    # G02 deterministic part (counts) -> deferred AND with judge (hand-tip forms)
    try:
        p = check_counts({('DL1', 'marker'): 12, ('DL1', 'tick'): 60, ('AS1', 'star'): 7, ('AS1', 'division'): 12,
                          ('AS1', 'circle'): 3, ('CR1', 'segment'): 12, ('CR1', 'medallion'): 12, ('MP1', 'moon'): 2,
                          ('MP1', 'star'): 9, ('DL2', 'division'): 24})
        _DEFER['G02'] = (not p, '; '.join(p) if p else 'zone B counts ok (hand-tip forms left to judge)')
    except Exception as e:
        _DEFER['G02'] = (False, f'check error {e}')

    def teeth_spokes(names):
        p = []
        for n in names:
            g = GP.get(n); t = gears[n]
            if not g:
                p.append(f'{n} missing'); continue
            if g.get('teeth') != t['z']:
                p.append(f"{n} teeth {g.get('teeth')}/{t['z']}")
            if n != 'MP1_ring' and n != 'ES1_escape':
                ok_sp = (t['spokes'], t['spokes'] + 1)
                if g.get('genus') not in ok_sp and g.get('sil_holes') not in ok_sp:
                    p.append(f"{n} genus {g.get('genus')} silhouette holes {g.get('sil_holes')} spokes {t['spokes']}")
        return p

    def g03():
        p = teeth_spokes(by_units(('GT1', 'GT9', 'ES1')))
        return bad('; '.join(p)) if p else ok('zone C teeth and spokes exact')
    guard('G03', g03)

    def g04():
        p = teeth_spokes(by_units(('GT2', 'GT5', 'GT3', 'GT6', 'GT4', 'MP1')))
        return bad('; '.join(p[:14])) if p else ok('zone D teeth (incl. CO-01) and spokes exact')
    guard('G04', g04)

    def g05():
        p = teeth_spokes(by_units(('GT7', 'GT8', 'GT10')))
        p += check_counts({('GT8', 'vane'): 4, ('BL1', 'canon'): 6, ('BL1', 'hammer'): 1, ('BL2', 'canon'): 4,
                           ('BL2', 'hammer'): 2, ('WT2', 'disc'): 5, ('AU1', 'fig'): 8})
        lob = GP.get('AU3_cam', {}).get('teeth')
        if lob != 8:
            p.append(f'AU3_cam lobes {lob}')
        return bad('; '.join(p[:14])) if p else ok('zone E/F teeth, spokes and counts exact')
    guard('G05', g05)

    def g06():
        p = []
        for m in ak['meshes']:
            a, b = GP.get(m['a']), GP.get(m['b'])
            if not a or not b:
                p.append(f"{m['a']}-{m['b']} missing"); continue
            d = _dxz((a['ox'], a['oz']), (b['ox'], b['oz']))
            if abs(d - m['centre_distance_m']) > max(0.01 * m['centre_distance_m'], 0.002) or abs(a['y_mid'] - b['y_mid']) > 0.03:
                p.append(f"{m['a']}-{m['b']} cd {d:.4f}/{m['centre_distance_m']} dy {a['y_mid'] - b['y_mid']:.3f}")
        for n, g in gears.items():
            if g['arbor'] in ('D24', 'C', 'MO', 'P1', 'P2', 'H', 'R', 'SB') and n in GP:
                d = _dxz((GP[n]['ox'], GP[n]['oz']), ports[g['arbor']])
                if d > 0.02:
                    p.append(f"{n} off port {g['arbor']} {d:.3f}")
        return bad('; '.join(p[:12])) if p else ok('23 meshes at standard centre distance, same layer; outputs coaxial')
    guard('G06', g06)

    def omega(n):
        m = MV.get(n)
        return (m['ang'][-1] - m['ang'][0]) / (len(m['ang']) - 1) if m and len(m['ang']) > 1 else None

    def g07():
        p = []
        for arb, a in arbors.items():
            reps = [n for n, g in gears.items() if g['arbor'] == arb] + ARBOR_EXTRA_REPS.get(arb, [])
            reps = [n for n in reps if n in MV]
            if not reps:
                p.append(f'{arb}: no representative'); continue
            want = a['omega_deg_per_frame']
            for n in reps:
                w = omega(n)
                if w is None or w * want <= 0 or abs(w - want) > 0.01 * abs(want):
                    p.append(f'{arb}/{n} {w if w is None else round(w, 5)} want {want}')
        return bad(f'{len(p)} bad: ' + '; '.join(p[:12])) if p else ok('25 arbors within 1%, directions correct')
    guard('G07', g07)

    def g08():
        p = []
        for n, z in (('GT4_c', 32), ('GT4_d', 22), ('GT4_e', 22), ('MP1_ring', 114)):
            if GP.get(n, {}).get('teeth') != z:
                p.append(f"{n} teeth {GP.get(n, {}).get('teeth')}/{z}")
        a, b = GP.get('GT4_e'), GP.get('MP1_ring')
        if a and b:
            d = _dxz((a['ox'], a['oz']), (b['ox'], b['oz']))
            if abs(d - 0.68) > 0.002:
                p.append(f'GT4_e-MP1_ring cd {d:.4f}')
        else:
            p.append('GT4_e/MP1_ring missing')
        w = [omega(n) for n in ('MP1_ring', 'MP1_disc') if n in MV]
        want = arbors['MO']['omega_deg_per_frame']
        if not w or any(x is None or abs(x - want) > 0.01 * abs(want) for x in w):
            p.append(f'MO omega {w}')
        return bad('; '.join(p)) if p else ok('CO-01 moon train applied (32/22/22/114, cd 0.680, MO -0.0936)')
    guard('G08', g08)

    # G09: diameter + AU2 + TW3 deterministic; roman numerals via text objects if any, else judge (veto only)
    try:
        p = []
        v = RAD.get('DL2_disc', {}).get('rmax')
        if v is None or abs(2 * v - 1.32) > 0.03 * 1.32:
            p.append(f'DL2_disc D {v and round(2 * v, 3)}')
        p += check_counts({('AU2', 'fig'): 10})
        f = tw3_faces()
        if not (f['N'] == 2 and f['S'] == 2 and f['W'] == 2):
            p.append(f'TW3 openings per face {f}')
        dl2c = set(S.coll('DL2'))
        fonts = [t for t in (X.get('fonts') or []) if t['name'] in dl2c or 'DL2' in t.get('colls', [])]
        if fonts:
            body = ''.join(t.get('body', '') for t in fonts)
            if re.search(r'\d', body) or not re.search(r'[IVX]', body):
                p.append(f'DL2 text not roman: {body[:60]!r}')
            R['G09'] = bad('; '.join(p)) if p else ok('DL2 D1.32 roman text; AU2 10 figs; TW3 2/face')
        else:
            _DEFER['G09'] = (not p, '; '.join(p) if p else 'D1.32, AU2 10, TW3 2/face ok; roman numerals (mesh) left to judge')
    except Exception as e:
        _DEFER['G09'] = (False, f'check error {e}')

    def g10():
        p = []
        a, pd = MV.get('ES1_anchor'), MV.get('PD1_pendulum')
        if not a or not pd:
            p.append('anchor/pendulum missing')
        else:
            dmax = max(abs(x - y) for x, y in zip(a['ang'], pd['ang']))
            if dmax > 0.5 or _dxz((a['o1'][0], a['o1'][2]), (pd['o1'][0], pd['o1'][2])) > 0.02:
                p.append(f'anchor vs pendulum max diff {dmax:.2f} deg')
        arm = MV.get('AU3_arm'); st = X.get('strike')
        if not arm or not st:
            p.append('striker/bell not measured')
        else:
            tp = _turning_points(arm['ang'], 1.0)
            dist = st['dist']; pen = st['pen']
            mx = [i for i, k in tp if k == 'max']; mn = [i for i, k in tp if k == 'min']
            def md(ix):
                return sum(dist[i] for i in ix) / len(ix) if ix else 1e9
            drops = mx if md(mx) < md(mn) else mn
            n = len(drops)
            badc = [i + 1 for i in drops if dist[i] > 0.03 or pen[i] > 0.02]
            if abs(n - 23) > 1:
                p.append(f'strikes {n}')
            if badc:
                p.append(f'{len(badc)} strikes without contact (e.g. frames {badc[:5]})')
        return bad('; '.join(p)) if p else ok('anchor locked to pendulum; 23±1 strikes with contact')
    guard('G10', g10)

    return {k: v for k, v in R.items() if k in items}


def postprocess(results, ctx):
    items = ctx['items']
    for iid, (passed, detail) in _DEFER.items():
        cur = results.get(iid, {})
        if not passed:
            results[iid] = {'verdict': 'fail', 'detail': 'deterministic part failed: ' + detail, 'source': 'checks'}
        else:
            results[iid] = dict(cur, detail=(detail + ' | judge: ' + str(cur.get('reason', cur.get('detail', ''))))[:600])
    # gate only on the core of B01 (scene opens, METRIC, scale 1.0); a missing SITE collection fails B01 alone
    if _GATE.get('core_fail'):
        for it in items:
            if it['id'] != 'B01' and (it.get('group') in SCENE_GROUPS or str(it.get('group', '')).startswith('zone')):
                results[it['id']] = {'verdict': 'fail', 'source': 'gate',
                                     'detail': 'gate: scene.blend not usable / units: ' + str(_GATE['core_fail'])[:300]}
    return results
