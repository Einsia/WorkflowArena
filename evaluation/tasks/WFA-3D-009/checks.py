# -*- coding: utf-8 -*-
"""BLD-W09 Forum Romanum — deterministic checks (Harbor verifier).

One Blender extraction (Scene.load) with an extra_py block that measures, per unit collection:
  * column lower diameters (horizontal sections of every <ID>_COL object),
  * up-facing faces (n_z > 0.99) of non-COL/FIG meshes  -> LEVELS / podium top / stair / pedestal,
  * sloped faces (0.05 < n_z < 0.98) of non-COL/FIG meshes -> ROOF form,
  * ray casts / ray sweeps against per-unit BVH trees of non-COL meshes -> RAY (openings, back-wall depth,
    eave, basilica body length/width, rostra curved front, paving),
  * XY convex hull of statue bases -> SHAPE,
  * BVH overlap between unit pairs -> clearance (M14),
  * evaluated face count per mesh object -> B02.
All comparisons happen here in pure Python against answer-key.json.
Items left to the judge model: M13 (render viewpoints), G12 (visual review).
Instanced geometry (collection / geometry-nodes instances) is attributed to the unit of its instancer and classified
by the instancer name (COL / FIG / other); bounding boxes include the extract's instance boxes.
"""
import json, math, re, statistics, traceback, pathlib

from _bld_lib import Scene, ok, bad, close, png_size, load_manifest, gate_group

FACE = {'N': (0.0, 1.0), 'S': (0.0, -1.0), 'E': (1.0, 0.0), 'W': (-1.0, 0.0)}
K = {'doric': 7, 'ionic': 9, 'corinthian': 10}
TREAD = 0.35
POS_TOL = 0.15
LEVEL_MERGE = 0.03
JUDGE_ONLY = {'M13', 'G12'}

PARAM_FIELDS = {
    'temple': ['order', 'D', 'a', 'front_columns', 'flank_columns', 'plan', 'podium_h', 'steps'],
    'tholos': ['order', 'D', 'columns', 'radius', 'roof', 'steps'],
    'porticus': ['follows', 'order', 'D', 'a', 'rows', 'columns_per_row', 'depth', 'roof'],
    'basilica': ['order', 'D', 'colonnade_rows', 'columns_per_row', 'apses', 'windows_per_side', 'doors'],
    'arch': ['order', 'D', 'passages', 'columns_per_face', 'width', 'height'],
    'rostra': ['prows', 'front', 'rear_steps'],
    'statue_base': ['shape', 'tiers', 'figure'],
    'honorific_column': ['order', 'D', 'base_steps', 'crown'],
}

# --------------------------------------------------------------------------------------------
# Blender-side measurement code (executed by _bld_extract.py; reads CFG, writes EXTRA)
# --------------------------------------------------------------------------------------------
EXTRA_PY = r'''
import re, json, math
from mathutils.bvhtree import BVHTree
CFG = json.loads(__CFG__)
GEOM = ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')
top = {c.name: c for c in scene.collection.children}
EXTRA['top'] = list(top.keys())
EXTRA['nf'] = {}; EXTRA['col'] = {}; EXTRA['up'] = {}; EXTRA['slope'] = {}; EXTRA['hull'] = {}
EXTRA['rays'] = {}; EXTRA['sweeps'] = {}; EXTRA['overlap'] = []; EXTRA['err'] = []
COLRE = re.compile(r'^[A-Z]\d\d_COL'); FIGRE = re.compile(r'^[A-Z]\d\d_FIG')

def wmesh(ob):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    if me is None:
        return None
    try:
        if len(me.vertices) > 800000:
            EXTRA['err'].append(ob.name + ': skipped (>800k evaluated vertices)')
            return None
        mw = ev.matrix_world.copy()
        vs = [mw @ v.co for v in me.vertices]
        ps = [tuple(p.vertices) for p in me.polygons]
        es = [tuple(e.vertices) for e in me.edges]
    finally:
        ev.to_mesh_clear()
    return vs, ps, es

def newell(vs, poly):
    nx = ny = nz = 0.0; cx = cy = cz = 0.0; m = len(poly)
    for i in range(m):
        a = vs[poly[i]]; b = vs[poly[(i + 1) % m]]
        nx += (a.y - b.y) * (a.z + b.z); ny += (a.z - b.z) * (a.x + b.x); nz += (a.x - b.x) * (a.y + b.y)
        cx += a.x; cy += a.y; cz += a.z
    L = math.sqrt(nx * nx + ny * ny + nz * nz)
    if L < 1e-12:
        return None
    return (nx / L, ny / L, nz / L, L / 2.0, cx / m, cy / m, cz / m)

# instanced geometry (collection instances, geometry-nodes instances): attributed to the unit of the instancer and
# classified by the instancer's name (COL / FIG / other).  Read inside the iteration (instance objects are transient).
unit_of = {}
for uid in CFG['units'] + ['SITE']:
    c = top.get(uid)
    if c is not None:
        for ob in c.all_objects:
            unit_of.setdefault(ob.name, uid)
INST = {}
EXTRA['inst'] = {}
try:
    nv_tot = 0
    for oi in dg.object_instances:
        if not oi.is_instance or oi.parent is None:
            continue
        pn = oi.parent.original.name if oi.parent.original is not None else oi.parent.name
        uid = unit_of.get(pn)
        if uid is None or oi.object.type != 'MESH':
            continue
        me = oi.object.data
        if me is None or len(me.vertices) == 0:
            continue
        if nv_tot + len(me.vertices) > 2000000:
            EXTRA['err'].append('instances: vertex cap 2M reached, rest skipped'); break
        nv_tot += len(me.vertices)
        mw = oi.matrix_world.copy()
        vs = [mw @ v.co for v in me.vertices]
        INST.setdefault(uid, []).append((pn, vs, [tuple(p.vertices) for p in me.polygons], [tuple(e.vertices) for e in me.edges]))
        EXTRA['inst'][pn] = EXTRA['inst'].get(pn, 0) + len(me.polygons)
except Exception as e:
    EXTRA['err'].append('instances: ' + str(e)[:200])

trees = {}
def unit_geom(c, uid):
    for ob in c.all_objects:
        if ob.type not in GEOM:
            continue
        try:
            g = wmesh(ob)
        except Exception as e:
            EXTRA['err'].append(ob.name + ': ' + str(e)[:120]); continue
        if g is None:
            continue
        EXTRA['nf'][ob.name] = len(g[1])
        yield ob.name, g[0], g[1], g[2], True
    for (pn, vs, ps, es) in INST.get(uid, []):
        yield pn, vs, ps, es, False

def do_unit(uid):
    c = top.get(uid)
    if c is None:
        return
    ncv, ncp, cv, cp = [], [], [], []
    ups, slopes, hullpts = {}, {}, []
    bb = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]
    dk = CFG['col_d'].get(uid)
    for obname, vs, ps, es, real in unit_geom(c, uid):
        for v in vs:
            if v.x < bb[0]: bb[0] = v.x
            if v.y < bb[1]: bb[1] = v.y
            if v.z < bb[2]: bb[2] = v.z
            if v.x > bb[3]: bb[3] = v.x
            if v.y > bb[4]: bb[4] = v.y
            if v.z > bb[5]: bb[5] = v.z
        iscol = bool(COLRE.match(obname)); isfig = bool(FIGRE.match(obname))
        if iscol:
            off = len(cv); cv.extend(vs); cp.extend([tuple(i + off for i in p) for p in ps])
            if dk and vs and real:
                zmin = min(v.z for v in vs); ws = []
                for fr in dk[1]:
                    z0 = zmin + fr * dk[0]; pts = []
                    for (i, j) in es:
                        a, b = vs[i], vs[j]
                        if (a.z - z0) * (b.z - z0) < 0:
                            t = (z0 - a.z) / (b.z - a.z); pts.append((a.x + t * (b.x - a.x), a.y + t * (b.y - a.y)))
                    if len(pts) >= 3:
                        w = 0.0
                        for k in range(12):
                            th = math.pi * k / 12; ca, sa = math.cos(th), math.sin(th)
                            pr = [p[0] * ca + p[1] * sa for p in pts]
                            w = max(w, max(pr) - min(pr))
                        ws.append(round(w, 4))
                    else:
                        ws.append(None)
                EXTRA['col'][obname] = ws
            continue
        off = len(ncv); ncv.extend(vs); ncp.extend([tuple(i + off for i in p) for p in ps])
        if isfig:
            continue
        if uid in CFG['hull_units']:
            step = max(1, len(vs) // 4000)
            hullpts.extend([(round(v.x, 4), round(v.y, 4)) for v in vs[::step]])
        if uid == 'SITE':
            continue
        for p in ps:
            r = newell(vs, p)
            if r is None:
                continue
            nx, ny, nz, A, cx, cy, cz = r
            if nz > 0.99 and cz > 0.02:
                xs = [vs[i].x for i in p]; ys = [vs[i].y for i in p]
                key = (round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2), round(cz, 3))
                ups[key] = ups.get(key, 0.0) + A
            elif 0.05 < nz < 0.98:
                key = (round(nx, 2), round(ny, 2), round(nz, 2), round(cz, 1))
                slopes[key] = slopes.get(key, 0.0) + A
    if ncv and ncp:
        trees[uid] = [BVHTree.FromPolygons(ncv, ncp, all_triangles=False), None, bb]
    if cv and cp:
        trees.setdefault(uid, [None, None, bb])[1] = BVHTree.FromPolygons(cv, cp, all_triangles=False)
    if uid == 'SITE':
        return
    EXTRA['up'][uid] = [list(k[:4]) + [k[4], round(a, 3)] for k, a in list(ups.items())[:30000]]
    EXTRA['slope'][uid] = [list(k) + [round(a, 3)] for k, a in list(slopes.items())[:30000]]
    if hullpts:
        P = sorted(set(hullpts))
        def cr(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        lo, hi = [], []
        for p in P:
            while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
            lo.append(p)
        for p in reversed(P):
            while len(hi) >= 2 and cr(hi[-2], hi[-1], p) <= 0: hi.pop()
            hi.append(p)
        H = lo[:-1] + hi[:-1]
        area = 0.5 * abs(sum(H[i][0] * H[(i + 1) % len(H)][1] - H[(i + 1) % len(H)][0] * H[i][1] for i in range(len(H))))
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        EXTRA['hull'][uid] = {'area': round(area, 4), 'bbox': [min(xs), min(ys), max(xs), max(ys)]}

for uid in CFG['units'] + ['SITE']:
    try:
        do_unit(uid)
    except Exception as e:
        import traceback as _tb
        EXTRA['err'].append('unit ' + uid + ': ' + _tb.format_exc()[-300:])

def cast(uid, o, d, maxd, multi):
    t = trees.get(uid)
    if not t or t[0] is None:
        return None
    o = Vector(o); d = Vector(d).normalized(); out = []; base = 0.0
    while base < maxd and len(out) < (8 if multi else 1):
        loc, nor, idx, dist = t[0].ray_cast(o, d, maxd - base)
        if loc is None:
            break
        base += dist; out.append(round(base, 3))
        o = loc + d * 1e-3; base += 1e-3
    return out

for r in CFG['rays']:
    try:
        EXTRA['rays'][r[0]] = cast(r[1], r[2], r[3], r[4], r[5])
    except Exception as e:
        EXTRA['err'].append('ray ' + r[0] + ': ' + str(e)[:100])
for s in CFG['sweeps']:
    key, uid, o0, st, n, d, maxd, mode = s
    try:
        if uid not in trees:
            EXTRA['sweeps'][key] = None; continue
        vals = []
        for i in range(int(n)):
            o = (o0[0] + st[0] * i, o0[1] + st[1] * i, o0[2] + st[2] * i)
            h = cast(uid, o, d, maxd, False)
            if mode == 'bin':
                vals.append('1' if h else '0')
            else:
                vals.append(h[0] if h else -1)
        EXTRA['sweeps'][key] = ''.join(vals) if mode == 'bin' else vals
    except Exception as e:
        EXTRA['err'].append('sweep ' + key + ': ' + str(e)[:100])

ids = [u for u in CFG['units'] if u in trees]
for i in range(len(ids)):
    for j in range(i + 1, len(ids)):
        a, b = trees[ids[i]], trees[ids[j]]
        A, B = a[2], b[2]
        if A[0] > B[3] or B[0] > A[3] or A[1] > B[4] or B[1] > A[4] or A[2] > B[5] or B[2] > A[5]:
            continue
        n = 0
        try:
            if a[0] and b[0]: n += len(a[0].overlap(b[0]))
            if a[1] and b[0]: n += len(a[1].overlap(b[0]))
            if a[0] and b[1]: n += len(a[0].overlap(b[1]))
        except Exception as e:
            EXTRA['err'].append('overlap: ' + str(e)[:100])
        if n:
            EXTRA['overlap'].append([ids[i], ids[j], n])
'''


# --------------------------------------------------------------------------------------------
# configuration from answer key
# --------------------------------------------------------------------------------------------
def unit_frame(u):
    """Return (f, p): unit front vector and a perpendicular, for cardinal facings."""
    fx, fy = FACE[u.get('line_facing') or u['facing']]
    return (fx, fy), (fy, -fx)


def build_cfg(A):
    U = A['units']
    cfg = {'units': sorted(U), 'col_d': {}, 'hull_units': [k for k in U if U[k]['type'] == 'statue_base'],
           'rays': [], 'sweeps': []}
    for uid, u in U.items():
        if 'D' in u:
            fr = [0.10, 0.35, 0.6] if u['order'] == 'doric' else [0.35, 0.6, 1.0]
            cfg['col_d'][uid] = [u['D'], fr]
    # also original orders (T04 ionic->corinthian): same D; fractions identical for ionic/corinthian
    for uid, u in U.items():
        t = u['type']
        if t == 'porticus':
            (fx, fy), _ = unit_frame(u)
            c0, c1 = u['columns_xy'][0], u['columns_xy'][1]
            mx, my = (c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2
            cfg['rays'].append([uid + '_depth', uid, [mx, my, 0.5 * u['col_H']], [-fx, -fy, 0], 40.0, False])
            cfg['rays'].append([uid + '_eave', uid, [mx, my, 200.0], [0, 0, -1], 200.0, True])
        elif t == 'basilica':
            ax, ay = u['anchor']; L, W, R = u['L'], u['W'], u['ridge_h']
            fx, fy = FACE[u['facing']]           # entrance long side (E or W); long axis = y
            off = W / 2 - 2.5
            for sx in (-1, 1):
                cfg['rays'].append([f'{uid}_endN_{sx}', uid, [ax + sx * off, ay + L / 2 + 20, 1.0], [0, -1, 0], 60.0, False])
                cfg['rays'].append([f'{uid}_endS_{sx}', uid, [ax + sx * off, ay - L / 2 - 20, 1.0], [0, 1, 0], 60.0, False])
            for i in range(17):
                y = ay + L * (-0.4 + 0.05 * i)
                cfg['rays'].append([f'{uid}_wE_{i}', uid, [ax + W / 2 + 20, y, 0.3 * R], [-1, 0, 0], 60.0, False])
                cfg['rays'].append([f'{uid}_wW_{i}', uid, [ax - W / 2 - 20, y, 0.3 * R], [1, 0, 0], 60.0, False])
            n = int((L - 0.6) / 0.1) + 1
            cfg['sweeps'].append([f'{uid}_door', uid, [ax + fx * (W / 2 + 1), ay - L / 2 + 0.3, 1.5], [0, 0.1, 0], n,
                                  [-fx, 0, 0], 1 + W / 2, 'bin'])
            z = 0.4 * R
            while z <= 0.9 * R + 1e-6:
                for side, sx in (('E', 1), ('W', -1)):
                    cfg['sweeps'].append([f'{uid}_win_{side}_{z:.1f}', uid, [ax + sx * (W / 2 + 1), ay - L / 2 + 0.3, z],
                                          [0, 0.1, 0], n, [-sx, 0, 0], 1 + W / 2, 'bin'])
                z += 0.5
        elif t == 'arch':
            ax, ay = u['anchor']; W, dp = u['W'], u['depth']
            n = int((W + 2) / 0.02) + 1
            cfg['sweeps'].append([uid + '_pass', uid, [ax - W / 2 - 1, ay - dp / 2 - 3, 1.5], [0.02, 0, 0], n, [0, 1, 0], dp + 6, 'dist'])
            cfg['sweeps'].append([uid + '_top', uid, [ax - W / 2 - 1, ay, 0.05], [0.02, 0, 0], n, [0, 0, 1], 60.0, 'dist'])
            # body depth: N-S rays on the arch axis just above the central passage crown (pedestals / free-standing
            # columns stand beside the piers, not on the axis, so they are not hit)
            zc = u['h_c'] + 0.3
            cfg['rays'].append([uid + '_dS', uid, [ax, ay - dp / 2 - 10, zc], [0, 1, 0], dp + 20, False])
            cfg['rays'].append([uid + '_dN', uid, [ax, ay + dp / 2 + 10, zc], [0, -1, 0], dp + 20, False])
        elif t == 'rostra':
            ax, ay = u['anchor']; (fx, fy) = FACE[u['facing']]
            pr = u['front_rise'] - 0.15
            cfg['rays'].append([uid + '_front', uid, [ax + fx * pr, ay + fy * pr, 50.0], [0, 0, -1], 60.0, False])
    x0, x1, y0, y1 = A['plaza']
    for i in range(5):
        for j in range(5):
            x = x0 + (x1 - x0) * (i + 0.5) / 5; y = y0 + (y1 - y0) * (j + 0.5) / 5
            cfg['rays'].append([f'SITE_g{i}{j}', 'SITE', [x, y, 50.0], [0, 0, -1], 100.0, False])
    return cfg


def extra_code(cfg):
    return EXTRA_PY.replace('__CFG__', repr(json.dumps(cfg)))


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------
def tol(v):
    return max(0.10, 0.03 * abs(v))


def near(a, b, t):
    return a is not None and b is not None and abs(a - b) <= t


def levels(zs, merge=LEVEL_MERGE):
    out = []
    for z in sorted(zs):
        if not out or z - out[-1][-1] > merge:
            out.append([z])
        else:
            out[-1].append(z)
    return [sum(g) / len(g) for g in out]


def order_of(k):
    for name, kk in K.items():
        if abs(k - kk) <= 0.04 * kk:
            return name
    return None


def runs(seq, is_open, min_len):
    """Contiguous runs of open samples -> list of (start, end) indices (inclusive)."""
    out, s = [], None
    for i, v in enumerate(seq):
        o = is_open(v)
        if o and s is None:
            s = i
        if not o and s is not None:
            if i - s >= min_len:
                out.append((s, i - 1))
            s = None
    if s is not None and len(seq) - s >= min_len:
        out.append((s, len(seq) - 1))
    return out


def inner_runs(seq, is_open, min_len):
    """runs() without the runs that touch either end of the sweep (open space beyond the building ends)."""
    return [q for q in runs(seq, is_open, min_len) if q[0] > 0 and q[1] < len(seq) - 1]


class W09:
    def __init__(self, S, A):
        self.S, self.A, self.U = S, A, A['units']
        ex = (S.data or {}).get('extra') or {}
        self.ex = ex
        self.cache = {}

    # --- object helpers
    def names(self, uid, kind=None):
        ns = self.S.coll(uid)
        if kind == 'COL':
            return [n for n in ns if n.startswith(uid + '_COL')]
        if kind == 'FIG':
            return [n for n in ns if n.startswith(uid + '_FIG')]
        if kind == 'PROW':
            return [n for n in ns if n.startswith(uid + '_PROW')]
        if kind == 'NONCOL':
            return [n for n in ns if not re.match(r'^[A-Z]\d\d_(COL|FIG)', n)]
        if kind == 'NONFIG':
            return [n for n in ns if not re.match(r'^[A-Z]\d\d_FIG', n)]
        return ns

    def cols(self, uid):
        if ('cols', uid) in self.cache:
            return self.cache[('cols', uid)]
        out = []
        for n in self.names(uid, 'COL'):
            o = self.S.ob(n)
            if not o or not o.get('bbox_world'):
                continue
            b = o['bbox_world']
            ws = (self.ex.get('col') or {}).get(n) or []
            ws = [w for w in ws if w]
            D = min(ws) if ws else None
            H = b[1][2] - b[0][2]
            out.append({'name': n, 'x': (b[0][0] + b[1][0]) / 2, 'y': (b[0][1] + b[1][1]) / 2, 'zmin': b[0][2],
                        'zmax': b[1][2], 'H': H, 'D': D, 'k': (H / D) if D else None})
        self.cache[('cols', uid)] = out
        return out

    def ups(self, uid):
        return [dict(x0=r[0], y0=r[1], x1=r[2], y1=r[3], z=r[4], a=r[5]) for r in (self.ex.get('up') or {}).get(uid) or []]

    def bbox(self, names):
        """World bbox union of the named objects plus geometry they instance (extract 'instances')."""
        bb = self.S.bbox(names)
        ns = set(names)
        bs = [i['bbox_world'] for i in ((self.S.data or {}).get('instances') or [])
              if i.get('instancer') in ns and i.get('bbox_world') and i.get('type') in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')]
        if bb:
            bs.append(bb)
        if not bs:
            return None
        return [[min(b[0][i] for b in bs) for i in range(3)], [max(b[1][i] for b in bs) for i in range(3)]]

    def zmax(self, names):
        bb = self.bbox(names)
        return bb[1][2] if bb else None

    def ray(self, key):
        return (self.ex.get('rays') or {}).get(key)

    def sweep(self, key):
        return (self.ex.get('sweeps') or {}).get(key)

    @staticmethod
    def uv(u, x, y):
        """Unit-local coords: d = depth behind anchor (positive away from front), v = lateral."""
        (fx, fy), (px, py) = unit_frame(u)
        ax, ay = u['anchor'] if 'anchor' in u else u['first_col']
        return -((x - ax) * fx + (y - ay) * fy), (x - ax) * px + (y - ay) * py

    def rect_uv(self, u, r):
        cs = [self.uv(u, x, y) for x in (r['x0'], r['x1']) for y in (r['y0'], r['y1'])]
        return min(c[0] for c in cs), max(c[0] for c in cs), min(c[1] for c in cs), max(c[1] for c in cs)

    def match_cols(self, uid, key_xy):
        cs = self.cols(uid)
        if len(cs) != len(key_xy):
            return False, f'{uid}: {len(cs)} COL vs {len(key_xy)}'
        used = set()
        for p in key_xy:
            hits = [i for i, c in enumerate(cs) if math.hypot(c['x'] - p[0], c['y'] - p[1]) <= POS_TOL]
            if len(hits) != 1 or hits[0] in used:
                return False, f'{uid}: column at {p} matched {len(hits)}'
            used.add(hits[0])
        return True, f'{uid}: {len(cs)} COL matched'

    def all_k(self, uid, k):
        cs = self.cols(uid)
        if not cs:
            return False, f'{uid}: no COL'
        badc = [c['name'] for c in cs if c['k'] is None or abs(c['k'] - k) > 0.04 * k]
        return (not badc), f'{uid}: H/D!={k} for {badc[:3]}' if badc else f'{uid}: all H/D~{k}'

    # ---------------------------------------------------------------- per-type measurement
    def m_temple(self, uid):
        u = self.U[uid]; cs = self.cols(uid)
        r = {'ok_m': [], 'ok_g': [], 'meas': {}}
        if not cs:
            raise ValueError('no COL')
        for c in cs:
            c['d'], c['v'] = self.uv(u, c['x'], c['y'])
        dmin = min(c['d'] for c in cs)
        front = [c for c in cs if c['d'] <= dmin + 0.3]
        fx_ = statistics.mean(c['x'] for c in front); fy_ = statistics.mean(c['y'] for c in front)
        top = statistics.median(c['zmin'] for c in cs)
        ups = self.ups(uid)
        lev_top = [x for x in ups if abs(x['z'] - top) <= 0.03]
        if not lev_top:
            raise ValueError(f'no podium-top faces at z={top:.2f}')
        R = [self.rect_uv(u, x) for x in lev_top]
        d0 = min(q[0] for q in R); d1 = max(q[1] for q in R); v0 = min(q[2] for q in R); v1 = max(q[3] for q in R)
        dfront = statistics.mean(c['d'] for c in front)
        Wm, Lm, over = v1 - v0, d1 - d0, dfront - d0
        # The sheets draw the top tread at podium-top level in front of the podium edge (side section: N-th tread at
        # hp, spanning [-D-0.35, -D]); that tread is indistinguishable from the podium top.  Accept both conventions
        # and remove the tread from the measured podium length when it is present.
        top_tread = abs(over - (u['D'] + TREAD)) < abs(over - u['D'])
        if top_tread:
            Lm -= TREAD
        ridge = self.zmax(self.names(uid, 'NONCOL'))
        # orientation: podium body behind the front row
        body_behind = (d0 + d1) / 2 > dfront
        sw = u['stair_w']
        reg = (d0 - (u['steps'] * TREAD + 2.0), d0 + 0.5)
        st = []
        for x, q in zip(ups, [self.rect_uv(u, x) for x in ups]):
            if q[1] < reg[0] or q[0] > reg[1]:
                continue
            if q[3] < -sw / 2 + 0.3 or q[2] > sw / 2 - 0.3:
                continue
            st.append((x, q))
        lv = [z for z in levels([x['z'] for x, q in st]) if z <= top + 0.03]
        stairs = [q for x, q in st if x['z'] < top - 0.03 and q[0] < d0 - 0.02]
        swm = (max(q[3] for q in stairs) - min(q[2] for q in stairs)) if stairs else 0.0
        nf = len(front)
        side = [len([c for c in cs if abs(c['v'] - s) <= 0.3]) for s in (min(c['v'] for c in cs), max(c['v'] for c in cs))]
        flank = max(side)
        dmax = max(c['d'] for c in cs)
        back = [c for c in cs if c['d'] >= dmax - 0.3]
        plan = 'peripteral' if (len(back) == nf and flank >= 4) else 'prostyle'
        ks = [c['k'] for c in cs if c['k']]
        m = r['meas'] = dict(anchor=[fx_, fy_], top=top, W=Wm, L=Lm, over=over, ridge=ridge, stair_w=swm,
                             steps=len(lv), front=nf, flank=flank, plan=plan, n=len(cs), body_behind=body_behind,
                             order=order_of(statistics.median(ks)) if ks else None)
        ax, ay = u['anchor']
        r['ok_m'] = [
            (math.hypot(fx_ - ax, fy_ - ay) <= POS_TOL, f'anchor {fx_:.2f},{fy_:.2f}'),
            (body_behind, 'orientation (body behind front row)'),
            (near(Wm, u['W_p'], tol(u['W_p'])), f'W_p {Wm:.2f}/{u["W_p"]}'),
            (near(Lm, u['L_p'], tol(u['L_p'])), f'L_p {Lm:.2f}/{u["L_p"]}'),
            (near(top, u['podium_h'], tol(u['podium_h'])), f'podium top {top:.2f}/{u["podium_h"]}'),
            (near(ridge, u['ridge_z'], tol(u['ridge_z'])), f'ridge {ridge}/{u["ridge_z"]}'),
        ]
        okc, dc = self.match_cols(uid, u['columns_xy'])
        r['ok_g'] = [(okc, dc), (len(lv) == u['steps'], f'steps {len(lv)}/{u["steps"]}')]
        r['ok_order'] = self.all_k(uid, u['k'])
        r['podium'] = [(near(over, u['D'], 0.10) or near(over, u['D'] + TREAD, 0.10),
                        f'overhang {over:.2f}/{u["D"]} (or {u["D"] + TREAD:.2f} with top tread at podium level)'),
                       (near(swm, sw, 0.03 * sw), f'stair_w {swm:.2f}/{sw}')]
        r['counts'] = {'front_columns': nf, 'flank_columns': flank, 'steps': len(lv)}
        return r

    def m_porticus(self, uid):
        u = self.U[uid]; cs = self.cols(uid)
        if not cs:
            raise ValueError('no COL')
        for c in cs:
            c['d'], c['v'] = self.uv(u, c['x'], c['y'])
        rows = levels([c['d'] for c in cs], 0.3)
        per = [len([c for c in cs if abs(c['d'] - rr) <= 0.3]) for rr in rows]
        dep = self.ray(uid + '_depth')
        depth = dep[0] if dep else None
        ev = self.ray(uid + '_eave') or []
        evz = [round(200.0 - h, 3) for h in ev[:4]]     # roof slab above the entablature may give 2 hits first
        eave_ok = any(near(z, u['eave_z'], tol(u['eave_z'])) for z in evz)
        roof = self.roof_form(uid, u['eave_z'] - 0.5)
        r = {'meas': dict(rows=len(rows), per=per, depth=depth, eave=evz, roof=roof)}
        r['ok_m'] = [(near(depth, u['depth'], tol(u['depth'])), f'back wall depth {depth}/{u["depth"]}')]
        if uid not in ('P04', 'P05'):                   # P04/P05 eave (CO-01 cascade) is scored once, in G08
            r['ok_m'].append((eave_ok, f'eave {evz}/{u["eave_z"]}'))
        okc, dc = self.match_cols(uid, u['columns_xy'])
        r['ok_g'] = [(okc, dc), (len(rows) == u['rows'] and all(p == u['n_per_row'] for p in per),
                                 f'rows {len(rows)} per {per} / {u["rows"]}x{u["n_per_row"]}'),
                     (roof == u['roof'], f'roof {roof}/{u["roof"]}')]
        r['ok_order'] = self.all_k(uid, u['k'])
        r['eave_ok'] = (eave_ok, f'eave {evz}/{u["eave_z"]}')
        r['counts'] = {'rows': len(rows), 'columns_per_row': max(per) if per else 0}
        return r

    def roof_form(self, uid, zmin, tholos=False):
        fs = [s for s in (self.ex.get('slope') or {}).get(uid) or [] if s[3] >= zmin]
        if not fs:
            return None
        if tholos:
            tot = sum(s[4] for s in fs)
            mu = sum(s[2] * s[4] for s in fs) / tot
            sd = math.sqrt(sum(s[4] * (s[2] - mu) ** 2 for s in fs) / tot)
            return 'cone' if sd < 0.05 else 'dome'
        cl = []
        for s in fs:
            az = math.degrees(math.atan2(s[1], s[0]))
            for c in cl:
                if abs((az - c[0] + 180) % 360 - 180) < 20:
                    c[1] += s[4]; break
            else:
                cl.append([az, s[4]])
        tot = sum(c[1] for c in cl)
        cl = [c for c in cl if c[1] >= 0.05 * tot]
        if len(cl) == 1:
            return 'shed'
        if len(cl) == 2 and abs(abs((cl[0][0] - cl[1][0] + 180) % 360 - 180) - 180) < 20:
            return 'gable'
        return f'other({len(cl)})'

    def m_tholos(self, uid):
        u = self.U[uid]; cs = self.cols(uid)
        if not cs:
            raise ValueError('no COL')
        cx = statistics.mean(c['x'] for c in cs); cy = statistics.mean(c['y'] for c in cs)
        ax, ay = u['anchor']
        rad = [math.hypot(c['x'] - ax, c['y'] - ay) for c in cs]
        ang = sorted(math.degrees(math.atan2(c['y'] - ay, c['x'] - ax)) % 360 for c in cs)
        gaps = [(ang[(i + 1) % len(ang)] - ang[i]) % 360 for i in range(len(ang))]
        even = len(cs) > 1 and all(abs(g - 360 / len(cs)) <= 2 for g in gaps)
        south = any(abs((a - 270 + 180) % 360 - 180) <= 2 for a in ang)
        top = statistics.median(c['zmin'] for c in cs)
        ctop = statistics.median(c['zmax'] for c in cs)
        ups = self.ups(uid)
        lt = [x for x in ups if abs(x['z'] - top) <= 0.03]
        pr = statistics.mean([(max(x['x1'] for x in lt) - min(x['x0'] for x in lt)) / 2,
                              (max(x['y1'] for x in lt) - min(x['y0'] for x in lt)) / 2]) if lt else None
        rin = (pr or u['podium_r']) - 0.5; rout = (pr or u['podium_r']) + u['steps'] * TREAD + 1.0
        st = []
        for x in ups:
            dx = max(x['x0'] - ax, 0, ax - x['x1']); dy = max(x['y0'] - ay, 0, ay - x['y1'])
            dmin = math.hypot(dx, dy)
            dmax = math.hypot(max(abs(x['x0'] - ax), abs(x['x1'] - ax)), max(abs(x['y0'] - ay), abs(x['y1'] - ay)))
            if dmax >= rin and dmin <= rout and x['z'] <= top + 0.03:
                st.append(x['z'])
        lv = levels(st)
        roof = self.roof_form(uid, ctop, tholos=True)
        r = {'meas': dict(center=[cx, cy], podium_r=pr, col_top=ctop, steps=len(lv), roof=roof, n=len(cs))}
        r['ok_m'] = [(math.hypot(cx - ax, cy - ay) <= POS_TOL, f'centre {cx:.2f},{cy:.2f}'),
                     (near(pr, u['podium_r'], tol(u['podium_r'])) or near(pr, u['podium_r'] + TREAD, tol(u['podium_r'])),
                      f'podium r {pr}/{u["podium_r"]} (or {u["podium_r"] + TREAD:.2f} with top tread at podium level)'),
                     (near(ctop, u['col_top_z'], tol(u['col_top_z'])), f'col top {ctop:.2f}/{u["col_top_z"]}')]
        r['ok_g'] = [(len(cs) == u['n_cols'] and all(abs(x - u['radius']) <= POS_TOL for x in rad) and even and south,
                      f'cols {len(cs)} even={even} south={south}'),
                     (roof == u['roof'], f'roof {roof}/{u["roof"]}'), (len(lv) == u['steps'], f'steps {len(lv)}/{u["steps"]}')]
        r['ok_order'] = self.all_k(uid, u['k'])
        r['counts'] = {'columns': len(cs), 'steps': len(lv)}
        return r

    def m_basilica(self, uid):
        u = self.U[uid]; ax, ay = u['anchor']; L, W = u['L'], u['W']
        nh = [h[0] for s in (-1, 1) for h in [self.ray(f'{uid}_endN_{s}')] if h]
        sh_ = [h[0] for s in (-1, 1) for h in [self.ray(f'{uid}_endS_{s}')] if h]
        if not nh or not sh_:
            raise ValueError('end-wall rays missed')
        yN = ay + L / 2 + 20 - statistics.median(nh); yS = ay - L / 2 - 20 + statistics.median(sh_)
        e = [h[0] for i in range(17) for h in [self.ray(f'{uid}_wE_{i}')] if h]
        w = [h[0] for i in range(17) for h in [self.ray(f'{uid}_wW_{i}')] if h]
        if not e or not w:
            raise ValueError('side-wall rays missed')
        xE = ax + W / 2 + 20 - statistics.median(e); xW = ax - W / 2 - 20 + statistics.median(w)
        cx, cy, Lm, Wm = (xE + xW) / 2, (yN + yS) / 2, yN - yS, xE - xW
        bb = self.bbox(self.names(uid, 'NONCOL'))
        ridge = bb[1][2] if bb else None
        overN = bb[1][1] - yN if bb else None; overS = yS - bb[0][1] if bb else None
        apses = int((overN or 0) > 1.0) + int((overS or 0) > 1.0)
        door = self.sweep(f'{uid}_door') or ''
        # openings = runs of open samples that do not touch the sweep ends (the clerestory / roof are set back from the
        # end walls on the sheet, so the first/last ~2 m of an upper sweep are open air, not windows)
        door_runs = inner_runs(door, lambda c: c == '0', 3)
        doors = len(door_runs)
        win = {}
        for side in ('E', 'W'):
            ks = [k for k in (self.ex.get('sweeps') or {}) if k.startswith(f'{uid}_win_{side}_')]
            win[side] = max([len(inner_runs(self.sweep(k) or '', lambda c: c == '0', 2)) for k in ks] or [0])
            win[side + '_open'] = win[side] > 0
        cs = self.cols(uid)
        rows = levels([c['x'] for c in cs], 0.3) if cs else []
        per = [len([c for c in cs if abs(c['x'] - rr) <= 0.3]) for rr in rows]
        r = {'meas': dict(center=[cx, cy], L=Lm, W=Wm, ridge=ridge, overN=overN, overS=overS, apses=apses, doors=doors,
                          win=win, rows=len(rows), per=per)}
        r['ok_m'] = [(math.hypot(cx - ax, cy - ay) <= POS_TOL, f'centre {cx:.2f},{cy:.2f}'),
                     (near(Lm, L, tol(L)), f'L {Lm:.2f}/{L}'), (near(Wm, W, tol(W)), f'W {Wm:.2f}/{W}'),
                     (near(ridge, u['ridge_h'], tol(u['ridge_h'])), f'ridge {ridge}/{u["ridge_h"]}')]
        g = [(len(cs) == u['n_cols'] and len(rows) == 2 * u['aisles_per_side'] and all(p == u['cols_per_row'] for p in per),
              f'cols {len(cs)} rows {len(rows)} per {per}'),
             (win['E'] == u['windows_per_side'] and win['W'] == u['windows_per_side'], f'windows E{win["E"]} W{win["W"]}'),
             (doors == u['doors'], f'doors {doors}/{u["doors"]}')]
        if uid == 'B01':
            g.append((near(overN, u['apse_r'], 0.20) and near(overS, u['apse_r'], 0.20), f'apses N{overN} S{overS}'))
        r['ok_g'] = g
        r['ok_order'] = self.all_k(uid, u['k'])
        r['open'] = (doors > 0 and win['E_open'] and win['W_open'], f'door open={doors > 0} win E={win["E_open"]} W={win["W_open"]}')
        r['counts'] = {'colonnade_rows': len(rows), 'columns_per_row': max(per) if per else 0, 'apses': apses,
                       'windows_per_side': max(win['E'], win['W']), 'doors': doors}
        return r

    def m_arch(self, uid):
        u = self.U[uid]; ax, ay = u['anchor']; W = u['W']
        ps = self.sweep(uid + '_pass'); tp = self.sweep(uid + '_top')
        if not ps or not tp:
            raise ValueError('passage sweep missing')
        x0 = ax - W / 2 - 1
        rr = runs(ps, lambda d: d == -1 or d is None, 3)
        # drop runs touching the sweep ends (outside the arch)
        rr = [q for q in rr if q[0] > 0 and q[1] < len(ps) - 1]
        ops = []
        for a, b in rr:
            c = (a + b) // 2
            ops.append({'cx': x0 + 0.02 * (a + b) / 2, 'w': 0.02 * (b - a + 1), 'h': (0.05 + tp[c]) if tp[c] not in (-1, None) else None})
        cen = min(ops, key=lambda o: abs(o['cx'] - ax)) if ops else None
        side = [o for o in ops if o is not cen]
        bb = self.bbox(self.names(uid, 'NONFIG'))
        Wm = bb[1][0] - bb[0][0] if bb else None; Hm = bb[1][2] if bb else None
        # body depth / centre from the two N-S rays above the central crown (pedestals and columns excluded)
        dp = u['depth']; hs, hn = self.ray(uid + '_dS'), self.ray(uid + '_dN')
        if hs and hn:
            yS = ay - dp / 2 - 10 + hs[0]; yN = ay + dp / 2 + 10 - hn[0]
            Dm = round(yN - yS, 3); cy = round((yN + yS) / 2, 3)
        else:
            Dm = cy = None
        cs = self.cols(uid)
        nfN = len([c for c in cs if c['y'] > ay]); nfS = len([c for c in cs if c['y'] < ay])
        r = {'meas': dict(openings=ops, W=Wm, H=Hm, depth=Dm, cy=cy, faces=[nfN, nfS])}
        r['ok_m'] = [(cen is not None and abs(cen['cx'] - ax) <= POS_TOL and near(cy, ay, POS_TOL),
                      f'central passage x {cen and round(cen["cx"], 2)} / body y {cy}'),
                     (near(Wm, u['W'], tol(u['W'])), f'W {Wm}/{u["W"]}'), (near(Hm, u['H'], tol(u['H'])), f'H {Hm}/{u["H"]}'),
                     (near(Dm, u['depth'], tol(u['depth'])), f'body depth {Dm}/{u["depth"]}' + ('' if Dm is not None else ' (axis rays above the crown missed)'))]

        def okop(o, w, h):
            return o is not None and near(o['w'], w, 0.03 * w) and near(o['h'], h, 0.03 * h)
        pas_ok = (len(ops) == u['passages'] and okop(cen, u['span_c'], u['h_c'])
                  and all(okop(o, u['span_s'], u['h_s']) for o in side))
        r['pass_ok'] = (pas_ok, 'openings ' + json.dumps([{k: (round(v, 2) if v else v) for k, v in o.items()} for o in ops]))
        r['cols_ok'] = (len(cs) == u['n_cols'] and nfN == nfS == u['cols_per_face'], f'COL {len(cs)} faces N{nfN} S{nfS}')
        r['open'] = (cen is not None and abs(cen['cx'] - ax) <= 1.0, 'N-S ray through anchor open' if cen else 'no opening at anchor')
        r['ok_order'] = self.all_k(uid, u['k'])
        r['counts'] = {'passages': len(ops), 'columns_per_face': max(nfN, nfS)}
        r['cen'] = cen
        return r

    def m_rostra(self, uid):
        u = self.U[uid]; ax, ay = u['anchor']
        ups = self.ups(uid)
        lv = {}
        for x in ups:
            if x['z'] > 1.0:
                k = round(x['z'], 2); lv[k] = lv.get(k, 0) + x['a']
        if not lv:
            raise ValueError('no platform top')
        h = max(lv, key=lv.get)
        tp = [x for x in ups if abs(x['z'] - h) <= 0.03]
        xs0 = min(x['x0'] for x in tp); xs1 = max(x['x1'] for x in tp)
        (fx, fy) = FACE[u['facing']]
        R = [self.rect_uv(u, x) for x in tp]
        back = max(q[1] for q in R)
        cx = (xs0 + xs1) / 2
        fr = self.ray(uid + '_front')
        curved = bool(fr) and (50.0 - fr[0]) > 0.5
        sw = u['rear_stair_w']
        st = []
        for x in ups:
            q = self.rect_uv(u, x)
            if q[1] < back - 0.5 or q[0] > back + u['rear_steps'] * 0.3 + 2.0:
                continue
            if q[3] < -sw / 2 + 0.3 or q[2] > sw / 2 - 0.3:
                continue
            if x['z'] <= h + 0.03:
                st.append(x['z'])
        nst = len(levels(st))
        prows = []
        for n in self.names(uid, 'PROW'):
            b = self.bbox([n])
            if b:
                prows.append([(b[0][i] + b[1][i]) / 2 for i in range(3)])
        prows.sort(key=lambda p: p[0])
        gaps = [math.dist(prows[i], prows[i + 1]) for i in range(len(prows) - 1)]
        even = bool(gaps) and (max(gaps) - min(gaps)) <= 0.10 * statistics.mean(gaps)
        fronthalf = all(self.uv(u, p[0], p[1])[0] <= u['depth'] / 2 for p in prows)
        r = {'meas': dict(h=h, L=xs1 - xs0, depth=back, cx=cx, curved=curved, rear_steps=nst, prows=len(prows), gaps=gaps)}
        r['ok_m'] = [(abs(cx - ax) <= POS_TOL, f'chord mid x {cx:.2f}'), (near(xs1 - xs0, u['L'], tol(u['L'])), f'L {xs1 - xs0:.2f}'),
                     (near(back, u['depth'], tol(u['depth'])), f'depth {back:.2f}/{u["depth"]}'),
                     (near(h, u['h'], tol(u['h'])), f'platform h {h}/{u["h"]}')]
        r['ok_g'] = [(curved == (u['front'] == 'curved'), f'curved front={curved}'), (nst == u['rear_steps'], f'rear steps {nst}/{u["rear_steps"]}')]
        r['prow_ok'] = (len(prows) == u['prows'] and even and fronthalf, f'prows {len(prows)} even={even} fronthalf={fronthalf}')
        r['axis_ok'] = (abs(cx) <= 0.10 and back > 0, f'R01 chord x {cx:.2f}, rear behind={back > 0}')
        r['counts'] = {'prows': len(prows), 'rear_steps': nst}
        return r

    def m_statue(self, uid):
        u = self.U[uid]; ax, ay = u['anchor']
        nb = self.bbox(self.names(uid, 'NONFIG'))
        fb = self.bbox(self.names(uid, 'FIG'))
        if not nb:
            raise ValueError('no base geometry')
        cx, cy = (nb[0][0] + nb[1][0]) / 2, (nb[0][1] + nb[1][1]) / 2
        sx, sy, bh = nb[1][0] - nb[0][0], nb[1][1] - nb[0][1], nb[1][2]
        fig = None; fh = None
        if fb:
            fh = fb[1][2] - fb[0][2]; hm = max(fb[1][0] - fb[0][0], fb[1][1] - fb[0][1])
            fig = 'equestrian' if hm >= 0.6 * fh else ('standing' if hm <= 0.5 * fh else 'ambiguous')
        hull = (self.ex.get('hull') or {}).get(uid)
        shape = None
        if hull:
            b = hull['bbox']; bw, bd = b[2] - b[0], b[3] - b[1]
            ratio = hull['area'] / max(1e-9, bw * bd); asp = max(bw, bd) / max(1e-9, min(bw, bd))
            if ratio > 0.95:
                shape = 'square' if asp <= 1.05 else 'oblong'
            elif 0.70 <= ratio <= 0.86 and asp <= 1.05:
                shape = 'round'
        tiers = len(levels([x['z'] for x in self.ups(uid)], 0.25))
        pa, pb = u['plan_a'], u['plan_b']
        r = {'meas': dict(center=[cx, cy], sx=sx, sy=sy, base_h=bh, fig_h=fh, fig=fig, shape=shape, tiers=tiers)}
        r['ok_m'] = [(math.hypot(cx - ax, cy - ay) <= POS_TOL, f'centre {cx:.2f},{cy:.2f}'),
                     # ±0.20 m floor: the sheet draws a cornice band 0.08 m proud of every tier
                     (near(sx, pa, max(0.20, 0.03 * pa)) and near(sy, pb, max(0.20, 0.03 * pb)), f'plan {sx:.2f}x{sy:.2f}/{pa}x{pb} (tol ±0.20)'),
                     (near(bh, u['base_h'], tol(u['base_h'])), f'base h {bh:.2f}/{u["base_h"]}'),
                     (near(fh, u['figure_h'], 0.05 * u['figure_h']), f'figure h {fh}/{u["figure_h"]}')]
        r['ok_g'] = [(shape == u['shape'], f'shape {shape}/{u["shape"]}'), (fig == u['figure'], f'figure {fig}/{u["figure"]}'),
                     (tiers == u['tiers'], f'tiers {tiers}/{u["tiers"]}')]
        r['counts'] = {'tiers': tiers}
        return r

    def m_honor(self, uid):
        u = self.U[uid]; ax, ay = u['anchor']; cs = self.cols(uid)
        if len(cs) < 1:
            raise ValueError('no COL')
        c = cs[0]
        top = c['zmin']
        ups = self.ups(uid)
        lt = [x for x in ups if abs(x['z'] - top) <= 0.03]
        pw = statistics.mean([max(x['x1'] for x in lt) - min(x['x0'] for x in lt), max(x['y1'] for x in lt) - min(x['y0'] for x in lt)]) if lt else None
        rin = (pw or u['pedestal_w']) / 2 + 0.05; rout = (pw or u['pedestal_w']) / 2 + u['base_steps'] * 0.4 + 1.0
        st = []
        for x in ups:
            dmax = max(abs(x['x0'] - ax), abs(x['x1'] - ax), abs(x['y0'] - ay), abs(x['y1'] - ay))
            dmin = max(max(x['x0'] - ax, 0, ax - x['x1']), max(x['y0'] - ay, 0, ay - x['y1']))
            if dmax >= rin and dmin <= rout and x['z'] < top - 0.03:
                st.append(x['z'])
        lv = levels(st)
        ph = top - (max(lv) if lv else 0.0)
        figs = []
        for n in self.names(uid, 'FIG'):
            b = (self.S.ob(n) or {}).get('bbox_world')
            if b and b[0][2] >= c['zmax'] - 0.5:
                figs.append(n)
        exp_top = u['base_steps'] * 0.3 + u['pedestal_h'] + u['col_H']
        r = {'meas': dict(axis=[c['x'], c['y']], pw=pw, ph=ph, col_top=c['zmax'], steps=len(lv), figs=len(figs))}
        r['ok_m'] = [(len(cs) == 1 and math.hypot(c['x'] - ax, c['y'] - ay) <= POS_TOL, f'{len(cs)} COL at {c["x"]:.2f},{c["y"]:.2f}'),
                     (near(pw, u['pedestal_w'], tol(u['pedestal_w'])), f'pedestal w {pw}/{u["pedestal_w"]}'),
                     (near(ph, u['pedestal_h'], tol(u['pedestal_h'])), f'pedestal h {ph:.2f}/{u["pedestal_h"]}'),
                     (near(c['zmax'], exp_top, tol(exp_top)), f'col top {c["zmax"]:.2f}/{exp_top:.2f}')]
        r['ok_g'] = [(len(lv) == u['base_steps'], f'base steps {len(lv)}/{u["base_steps"]}'),
                     ((len(figs) >= 1) == (u['crown'] == 'statue'), f'crown FIG {len(figs)} / {u["crown"]}')]
        r['ok_order'] = self.all_k(uid, u['k'])
        r['counts'] = {'base_steps': len(lv)}
        return r

    def measure(self, uid):
        if uid in self.cache:
            return self.cache[uid]
        t = self.U[uid]['type']
        fn = {'temple': self.m_temple, 'porticus': self.m_porticus, 'tholos': self.m_tholos, 'basilica': self.m_basilica,
              'arch': self.m_arch, 'rostra': self.m_rostra, 'statue_base': self.m_statue, 'honorific_column': self.m_honor}[t]
        try:
            if not self.S.has_coll(uid) or not self.S.coll(uid):
                raise ValueError('collection missing or empty')
            r = fn(uid)
            r['err'] = None
        except Exception as e:
            notes = [str(x)[:120] for x in (self.ex.get('err') or []) if uid in str(x)][:2]
            r = {'err': f'{uid}: {type(e).__name__}: {e}' + (f' [extract notes: {"; ".join(notes)}]' if notes else '')}
        self.cache[uid] = r
        return r


# --------------------------------------------------------------------------------------------
def summarize(pairs, prefix=''):
    fails = [d for o, d in pairs if not o]
    return (not fails), (prefix + ('; '.join(fails[:6]) if fails else f'{len(pairs)} sub-checks ok'))


def run(ctx):
    res = {}
    A = ctx.get('answer') or json.loads((pathlib.Path(ctx['tests']) / 'answer-key.json').read_text(encoding='utf-8'))
    U = A['units']; ids = sorted(U)
    out = pathlib.Path(ctx['out'])
    items = [i['id'] for i in ctx['items']]

    def put(iid, fn):
        try:
            v = fn()
            res[iid] = ok(v[1]) if v[0] else bad(v[1])
        except Exception as e:
            res[iid] = bad(f'error: {type(e).__name__}: {e} | {traceback.format_exc()[-300:]}')

    # ---------------- file checks (independent of Blender)
    def render_ok(name):
        p = out / 'renders' / name
        if not p.exists():
            return False, f'{name} missing'
        sz = png_size(p)
        if sz != (1920, 1080):
            return False, f'{name} size {sz}'
        try:
            from PIL import Image, ImageStat
            im = Image.open(p).convert('L'); im.thumbnail((480, 270))
            sd = ImageStat.Stat(im).stddev[0]
            return sd > 10, f'{name} 1920x1080 std={sd:.1f}'
        except ImportError:
            return True, f'{name} 1920x1080 (PIL unavailable; blank test skipped)'
        except Exception as e:
            return False, f'{name} decode error {e}'

    put('B04', lambda: render_ok('overview.png'))
    put('B05', lambda: summarize([render_ok('west_colonnade.png'), render_ok('north_temple.png')]))
    man = load_manifest(out)

    def b06():
        if not isinstance(man, list):
            return False, 'manifest.json missing or not an array'
        got = {e.get('id'): e for e in man if isinstance(e, dict)}
        if len(man) != 28 or set(got) != set(ids):
            return False, f'{len(man)} entries; ids diff {sorted(set(ids) ^ set(got))[:6]}'
        badl = []
        for i, e in got.items():
            need = PARAM_FIELDS[U[i]['type']]
            p = e.get('params') if isinstance(e.get('params'), dict) else {}
            miss = [k for k in need if k not in p]
            if e.get('collection') != i or miss or 'built' not in e:
                badl.append(f'{i}:{miss or "collection/built"}')
        return (not badl), ('fields missing ' + '; '.join(badl[:6])) if badl else '28 entries, all fields present'
    put('B06', b06)

    # ---------------- scene
    cfg = build_cfg(A)
    S = Scene.load(ctx, extra_py=extra_code(cfg))
    scene_items = [i for i in items if i not in ('B04', 'B05', 'B06') and i not in JUDGE_ONLY]
    if S.err or not S.data:
        for i in scene_items:
            res[i] = bad(f'scene unavailable: {S.err}')
        ctx['_w09_nhit'] = 0
        return res
    # EXTRA_PY guards every per-object / per-unit / per-ray step itself; an exception that still escapes is a grader
    # bug, not a property of the submission -> surface it (rubric_score marks the items "error", no reward written).
    xerr = [e for e in (S.data.get('errors') or []) if str(e).startswith('extra_py')]
    if xerr:
        raise RuntimeError('EXTRA_PY crashed inside Blender: ' + str(xerr[0])[-600:])
    w = W09(S, A)
    ex = w.ex
    xlog = ex.get('err') or []
    cols = S.data.get('collections', {})
    root = [k for k, v in cols.items() if v.get('parent') is None]
    tops = cols[root[0]]['children'] if root else []
    ctx['_w09_nhit'] = len([t for t in tops if t in U])

    def b01():
        sc = S.data.get('scene') or {}
        okk = sc.get('unit_system') == 'METRIC' and abs(float(sc.get('scale_length', 0)) - 1.0) < 1e-6
        return okk, f"opened; unit_system={sc.get('unit_system')} scale_length={sc.get('scale_length')}"
    put('B01', b01)

    def b02():
        want = set(ids) | {'SITE'}
        nf = ex.get('nf') or {}
        empty = [i for i in ids if not any(S.objects.get(n, {}).get('type') == 'MESH' and (nf.get(n) or 0) > 0 for n in S.coll(i))]
        okk = set(tops) == want and not empty
        det = f'top-level extra {sorted(set(tops) - want)[:5]} missing {sorted(want - set(tops))[:5]} no-mesh {empty[:5]}'
        if xlog:
            det += f' | measurement notes ({len(xlog)}): ' + '; '.join(str(e)[:120] for e in xlog[:3])
        return okk, det
    put('B02', b02)

    def b03():
        sb = w.bbox(S.coll('SITE'))
        x0, x1, y0, y1 = A['plaza']
        if not sb:
            return False, 'no SITE geometry'
        cov = sb[0][0] <= x0 + 0.5 and sb[1][0] >= x1 - 0.5 and sb[0][1] <= y0 + 0.5 and sb[1][1] >= y1 - 0.5
        zs = []
        for i in range(5):
            for j in range(5):
                h = w.ray(f'SITE_g{i}{j}')
                zs.append(None if not h else round(50.0 - h[0], 3))
        zok = all(z is not None and -0.05 <= z <= 0.05 for z in zs)
        return cov and zok, f'SITE bbox {sb[0][:2]}..{sb[1][:2]} covers={cov}; paving z ok={zok} (bad {[z for z in zs if z is None or abs(z) > 0.05][:4]})'
    put('B03', b03)

    def b07():
        suns = [n for n in S.coll('SITE') if (S.ob(n) or {}).get('type') == 'LIGHT' and S.ob(n).get('light', {}).get('type') == 'SUN']
        det = []
        for n in suns:
            m = S.ob(n)['matrix_world']
            d = [-m[0][2], -m[1][2], -m[2][2]]           # matrix_world @ (0,0,-1)
            t = [-x for x in d]                          # towards the sun
            L = math.sqrt(sum(x * x for x in t)) or 1
            el = math.degrees(math.asin(t[2] / L))
            det.append(f'{n}: el={el:.1f} sunx={t[0]:.2f}')
            if 3 <= el <= 17 and t[0] < 0:
                return True, '; '.join(det)
        return False, ('no SUN in SITE' if not suns else '; '.join(det))
    put('B07', b07)

    def b08():
        errs = []
        unit_of = {}
        for uid in ids:
            for n in S.coll(uid):
                unit_of.setdefault(n, set()).add(uid)
        for n in S.objects:
            m = re.match(r'^([A-Z]\d\d)_COL', n)
            if m and unit_of.get(n) != {m.group(1)}:
                errs.append(f'{n} in {sorted(unit_of.get(n, []))}')
        for uid in ids:
            if uid[0] in 'TPBAC' and U[uid]['type'] != 'statue_base' and not w.names(uid, 'COL'):
                errs.append(f'{uid} no COL')
        for uid in ['S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'C01', 'C03']:
            if not w.names(uid, 'FIG'):
                errs.append(f'{uid} no FIG')
        if not w.names('R01', 'PROW'):
            errs.append('R01 no PROW')
        return (not errs), '; '.join(errs[:8]) if errs else 'naming contract ok'
    put('B08', b08)

    # ---------------- zones
    zones = {z['id']: z['units'] for z in A['zones']}
    zone_items = {'A': ('M01', 'G01'), 'B': ('M02', 'G02'), 'C': ('M03', 'G03'), 'D': ('M04', 'G04'), 'E': ('M05', 'G05'), 'F': ('M06', 'G06')}

    def zone_m(z):
        pairs = []
        for uid in zones[z]:
            r = w.measure(uid)
            if r.get('err'):
                pairs.append((False, r['err']))
                continue
            pairs += [(o, f'{uid} {d}') for o, d in r.get('ok_m', [])]
        return summarize(pairs)

    def zone_g(z):
        pairs = []
        for uid in zones[z]:
            r = w.measure(uid)
            if r.get('err'):
                pairs.append((False, r['err']))
                continue
            u = U[uid]
            if uid == 'B02':
                g = [p for p in r['ok_g']]
            elif uid == 'A01':
                g = [r['pass_ok'], r['cols_ok']]
            elif uid == 'A02':
                g = []                                  # passages / column count judged in G07
            elif uid == 'R01':
                g = r['ok_g']                           # prows judged in G07
            else:
                g = list(r.get('ok_g', []))
            # order checks (T04 / P04 / P05 orders are judged in G07 / G08)
            if 'ok_order' in r and uid not in ('T04', 'P04', 'P05'):
                g.append(r['ok_order'])
            if uid == 'A02':
                cs = w.cols(uid)
                Dm = statistics.median([c['D'] for c in cs if c['D']]) if cs else None
                g.append((near(Dm, u['D'], max(0.05, 0.05 * u['D'])), f'A02 D {Dm}/{u["D"]}'))
            pairs += [(o, f'{uid} {d}') for o, d in g]
        return summarize(pairs)

    for z, (mi, gi) in zone_items.items():
        put(mi, lambda z=z: zone_m(z))
        put(gi, lambda z=z: zone_g(z))

    def m07():
        badl = []; n = 0
        for uid in ids:
            if 'D' not in U[uid]:
                continue
            for c in w.cols(uid):
                n += 1
                if c['D'] is None or abs(c['D'] - U[uid]['D']) > max(0.05 * U[uid]['D'], 0.05):
                    badl.append(f"{c['name']} D={c['D']}/{U[uid]['D']}")
        if n == 0:
            return False, 'no COL objects'
        return (not badl), (f'{len(badl)}/{n} off: ' + '; '.join(badl[:5])) if badl else f'{n} columns D ok'
    put('M07', m07)

    def m08():
        badl = []
        for uid in [k for k in ids if U[k]['type'] in ('temple', 'porticus')]:
            cs = w.cols(uid); s = U[uid]['s']
            if len(cs) < 2:
                badl.append(f'{uid} <2 COL'); continue
            for c in cs:
                nn = min(math.hypot(c['x'] - d['x'], c['y'] - d['y']) for d in cs if d is not c)
                if abs(nn - s) > 0.03 * s:
                    badl.append(f"{c['name']} nn={nn:.2f}/{s}"); break
            u = U[uid]
            for c in cs:
                c['d'], c['v'] = W09.uv(u, c['x'], c['y'])
            dmin = min(c['d'] for c in cs)
            fr = sorted(c['v'] for c in cs if c['d'] <= dmin + 0.3)
            gaps = [fr[i + 1] - fr[i] for i in range(len(fr) - 1)]
            if any(abs(g - s) > 0.03 * s for g in gaps):
                badl.append(f'{uid} front gaps {[round(g, 2) for g in gaps][:5]}')
        return (not badl), '; '.join(badl[:6]) if badl else 'all spacings ok'
    put('M08', m08)

    def m09():
        pairs = []
        for uid in ['T01', 'T02', 'T03', 'T04', 'T05']:
            r = w.measure(uid)
            pairs += [(False, r['err'])] if r.get('err') else [(o, f'{uid} {d}') for o, d in r['podium']]
        return summarize(pairs)
    put('M09', m09)

    def m10():
        pairs = []
        for uid in ['B01', 'B02', 'A01', 'A02']:
            r = w.measure(uid)
            pairs.append((False, r['err']) if r.get('err') else (r['open'][0], f'{uid} {r["open"][1]}'))
        return summarize(pairs)
    put('M10', m10)

    def m11():
        if not isinstance(man, list):
            return False, 'manifest missing'
        got = {e.get('id'): e for e in man if isinstance(e, dict)}
        badl = []
        for uid in ids:
            e = got.get(uid)
            if e is None:
                badl.append(f'{uid} not in manifest'); continue
            built = e.get('built') is True
            has = any((ex.get('nf') or {}).get(n, 0) > 0 for n in S.coll(uid))
            if built != has:
                badl.append(f'{uid} built={e.get("built")} geometry={has}'); continue
            if not built:
                continue
            r = w.measure(uid)
            if r.get('err'):
                badl.append(r['err']); continue
            p = e.get('params') or {}
            for k, v in r.get('counts', {}).items():
                try:
                    if int(p.get(k)) != int(v):
                        badl.append(f'{uid}.{k} manifest {p.get(k)} vs measured {v}')
                except Exception:
                    badl.append(f'{uid}.{k} manifest {p.get(k)!r} vs measured {v}')
        return (not badl), '; '.join(badl[:8]) if badl else 'manifest counts match scene'
    put('M11', m11)

    def m12():
        pairs = []
        r = w.measure('T01')
        pairs.append((False, r['err']) if r.get('err') else (abs(r['meas']['anchor'][0]) <= 0.10 and r['meas']['body_behind'],
                                                              f"T01 front x {r['meas']['anchor'][0]:.2f}, body north={r['meas']['body_behind']}"))
        r = w.measure('R01')
        pairs.append((False, r['err']) if r.get('err') else r['axis_ok'])
        r = w.measure('A01')
        pairs.append((False, r['err']) if r.get('err') else (r['cen'] is not None and abs(r['cen']['cx']) <= 0.10,
                                                              f"A01 central passage x {r['cen'] and round(r['cen']['cx'], 3)}"))
        return summarize(pairs)
    put('M12', m12)

    def m14():
        ov = [o for o in ex.get('overlap') or [] if o[0] in U and o[1] in U]
        return (not ov), ('clashes ' + json.dumps(ov[:8])) if ov else 'no inter-unit intersections'
    put('M14', m14)

    def g07():
        pairs = [w.all_k('T04', 10)]
        if len(w.cols('T04')) != 22:
            pairs.append((False, f'T04 COL {len(w.cols("T04"))}/22'))
        r = w.measure('A02')
        pairs += [(False, r['err'])] if r.get('err') else [r['pass_ok'], r['cols_ok']]
        r = w.measure('R01')
        pairs += [(False, r['err'])] if r.get('err') else [r['prow_ok']]
        r = w.measure('B02')
        if r.get('err'):
            pairs.append((False, r['err']))
        else:
            m = r['meas']
            pairs.append((near(m['overS'], 6.5, 0.20) and m['overN'] is not None and m['overN'] <= 0.30,
                          f"B02 apse S {m['overS']} N {m['overN']}"))
        return summarize(pairs)
    put('G07', g07)

    def g08():
        pairs = []
        t4 = [c['D'] for c in w.cols('T04') if c['D']]
        D4 = statistics.median(t4) if t4 else None
        for uid in ('P04', 'P05'):
            pairs.append(w.all_k(uid, 10))
            ds = [c['D'] for c in w.cols(uid) if c['D']]
            Dp = statistics.median(ds) if ds else None
            pairs.append((D4 is not None and Dp is not None and abs(Dp - D4) <= 0.05 * D4, f'{uid} D {Dp} vs T04 {D4}'))
            r = w.measure(uid)
            pairs.append((False, r['err']) if r.get('err') else r['eave_ok'])
        return summarize(pairs)
    put('G08', g08)

    def line(lid, units):
        L = A['integration_lines'][lid]
        ax_ = 0 if L['axis'] == 'x' else 1
        pairs = []
        for uid in units:
            u = U[uid]; cs = w.cols(uid)
            if not cs:
                pairs.append((False, f'{uid} no COL')); continue
            for c in cs:
                c['d'], c['v'] = W09.uv(u, c['x'], c['y'])
            dmin = min(c['d'] for c in cs)
            fr = [c for c in cs if c['d'] <= dmin + 0.3]
            dev = max(abs((c['x'], c['y'])[ax_] - L['value']) for c in fr)
            pairs.append((dev <= 0.10, f'{uid} front-row dev {dev:.2f}'))
            if u['type'] == 'porticus':
                t = U[u['follows']]; tc = w.cols(u['follows'])
                ex_, ey_ = FACE[u['extend']]
                if not tc:
                    pairs.append((False, f'{u["follows"]} no COL')); continue
                for c in tc:
                    c['d'], c['v'] = W09.uv(t, c['x'], c['y'])
                tdmin = min(c['d'] for c in tc)
                tfr = [c for c in tc if c['d'] <= tdmin + 0.3]
                corner = max(tfr, key=lambda c: c['x'] * ex_ + c['y'] * ey_)
                first = min(fr, key=lambda c: math.hypot(c['x'] - corner['x'], c['y'] - corner['y']))
                dx, dy = first['x'] - corner['x'], first['y'] - corner['y']
                dist = math.hypot(dx, dy)
                dirok = dist > 0 and (dx * ex_ + dy * ey_) / dist > 0.9
                pairs.append((abs(dist - t['s']) <= 0.03 * t['s'] and dirok, f'{uid} first col gap {dist:.2f}/{t["s"]} dir={dirok}'))
        return summarize(pairs)
    put('G09', lambda: line('west', ['T02', 'P01', 'P02', 'T03', 'P03']))
    put('G10', lambda: line('east', ['T04', 'P04', 'P05', 'T05', 'P06']))
    put('G11', lambda: line('north', ['T01', 'P07', 'P08']))
    return res


def postprocess(results, ctx):
    items = ctx['items']
    if results.get('B01', {}).get('verdict') == 'fail':
        keep = {'B01', 'B04', 'B05', 'B06', 'M13', 'G12'}
        for it in items:
            if it['id'] not in keep:
                results[it['id']] = {'verdict': 'fail', 'detail': 'gate: B01 failed', 'source': 'gate'}
    if ctx.get('_w09_nhit', 0) < 14:
        grp = re.compile(r'^(zone_|integration|change_)')
        for it in items:
            if grp.match(it.get('group', '')):
                results[it['id']] = {'verdict': 'fail', 'detail': f"gate: only {ctx.get('_w09_nhit', 0)} unit collections at top level (<14)", 'source': 'gate'}
    return results
