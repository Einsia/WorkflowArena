# -*- coding: utf-8 -*-
"""BLD-W10 Age-of-sail harbour & fleet — deterministic checks.

One Blender export (Scene.load) with:
  * frames 1..240 (step 2, plus 240) for <ID>_ROOT and L01_ROTOR (roll / rotor motion);
  * extra_py: frame_set(1) then world bbox + matrix of every object and world vertices of the
    measurement meshes (EXTRA['bbox1'|'mw1'|'verts1']) so that all static geometry is measured at frame 1
    regardless of the frame the .blend was saved on.
Items left to the VLM judge: M11 (render framing) and G14 (visual defects checklist).
v0.2 (2026-10-25): exact frame-1 evaluated bboxes, ray profiles for D01 / B01, B01/B02 gates narrowed (see
review/rubric-cleanup-20261025.md).
"""
import math, re, json, pathlib, zlib, struct, traceback
from _bld_lib import Scene, ok, bad, close, png_size, load_manifest, gate_group

SHIPS = ['S%02d' % i for i in range(1, 11)]
UNITS_ORDER = None
MEAS_RE = (r'^(S\d\d_HULL|Q0\d_WALL|P0\d_DECK|B01_MOUND|L01_TOWER|C0[12]_JIB|C03_LEG_\d+|W0\d_ROOF|D01_BASIN)$')
EXTRA_PY = r'''
import re
scene.frame_set(1)
dg1 = bpy.context.evaluated_depsgraph_get()
VR = re.compile(%r)
POOL = set()
for cn in ('C01', 'C02'):
    c = bpy.data.collections.get(cn)
    if c:
        POOL.update(o.name for o in c.all_objects)
try:
    import numpy as _np
except Exception:
    _np = None
bb = {}; mw = {}; vv = {}; errs = []
for ob in scene.objects:
    try:
        mw[ob.name] = [[round(ob.matrix_world[i][j], 6) for j in range(4)] for i in range(4)]
        if ob.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            ev = ob.evaluated_get(dg1)
            m = ev.matrix_world
            me = None
            try:
                me = ev.to_mesh()
            except Exception:
                me = None
            try:
                # v0.2: exact world bbox of the evaluated vertices (same semantics as _bld_extract bbox_world, at frame 1)
                if me is not None and len(me.vertices):
                    n = len(me.vertices)
                    if _np is not None:
                        co = _np.empty(n * 3, dtype=_np.float64); me.vertices.foreach_get('co', co); co = co.reshape(n, 3)
                        M = _np.array([[m[i][j] for j in range(4)] for i in range(4)])
                        w = co @ M[:3, :3].T + M[:3, 3]
                        bb[ob.name] = [[round(float(x), 5) for x in w.min(axis=0)], [round(float(x), 5) for x in w.max(axis=0)]]
                    else:
                        w = None
                        pts = [m @ v.co for v in me.vertices]
                        bb[ob.name] = [[round(min(p[i] for p in pts), 5) for i in range(3)], [round(max(p[i] for p in pts), 5) for i in range(3)]]
                    if ob.type == 'MESH' and (VR.search(ob.name) or ob.name in POOL):
                        step = max(1, n // 40000)
                        if w is not None:
                            vv[ob.name] = [[round(float(c), 3) for c in w[i]] for i in range(0, n, step)]
                        else:
                            vv[ob.name] = [[round(c, 3) for c in (m @ me.vertices[i].co)] for i in range(0, n, step)]
                else:
                    pts = [m @ Vector(c) for c in ev.bound_box]
                    bb[ob.name] = [[round(min(p[i] for p in pts), 5) for i in range(3)], [round(max(p[i] for p in pts), 5) for i in range(3)]]
            finally:
                if me is not None:
                    ev.to_mesh_clear()
    except Exception as e:
        errs.append(ob.name + ': ' + str(e)[:200])
EXTRA['bbox1'] = bb; EXTRA['mw1'] = mw; EXTRA['verts1'] = vv; EXTRA['errors'] = errs[:50]
''' % MEAS_RE

# v0.2 (2026-10-25): downward ray profiles across the graving dock and across the breakwater crest, so that
# low-poly builds (a profile extruded once along the axis) are measured from the surface, not from vertex sampling.
PROF_PY = r'''
import json as _json
_P = _json.loads(__PARAMS__)
try:
    from mathutils.bvhtree import BVHTree
except Exception as e:
    BVHTree = None; errs.append('bvhtree import: ' + str(e)[:200])
def _bvh(name):
    ob = bpy.data.objects.get(name)
    if BVHTree is None or ob is None or ob.type != 'MESH':
        return None
    ev = ob.evaluated_get(dg1); me = ev.to_mesh()
    try:
        m = ev.matrix_world
        vs = [m @ v.co for v in me.vertices]; ps = [tuple(p.vertices) for p in me.polygons]
        return BVHTree.FromPolygons(vs, ps) if ps else None
    finally:
        ev.to_mesh_clear()
def _down(t, x, y, z0):
    h = t.ray_cast(Vector((x, y, z0)), Vector((0.0, 0.0, -1.0)), 1000.0)
    return None if h[0] is None else round(h[0][2], 4)
_prof = {}
for _uid, _obn in (('D01', 'D01_BASIN'), ('B01', 'B01_MOUND')):
    try:
        _t = _bvh(_obn)
        if _t is None:
            continue
        _rows = []
        for _st in _P[_uid]['stations']:
            _row = []
            for _k in range(_P[_uid]['n']):
                _x = _st['x0'] + _st['dx'] * _k; _y = _st['y0'] + _st['dy'] * _k
                _row.append([_k, _down(_t, _x, _y, _P[_uid]['z0'])])
            _rows.append(_row)
        _prof[_uid] = _rows
    except Exception as e:
        errs.append(_uid + ' profile: ' + str(e)[:200])
EXTRA['prof'] = _prof; EXTRA['prof_params'] = _P; EXTRA['errors'] = errs[:50]
'''
PROF_STEP = 0.05


def prof_params(K):
    # station rows: point k = (x0 + dx*k, y0 + dy*k); D01 rows run along +X across the dock at 3 stations in the
    # parallel body, B01 rows run along the seaward normal across the crest at 5 stations along the axis.
    U = K['units']; d = U['D01']; b = U['B01']
    Lw, Wt, cx = d['length_m'], d['top_width_m'], d['entr_x']
    half = Wt / 2 + 4.0; nd = int(round(2 * half / PROF_STEP)) + 1
    ds = [{'x0': cx - half, 'y0': d['entr_y'] + f * Lw, 'dx': PROF_STEP, 'dy': 0.0} for f in (0.35, 0.45, 0.55)]
    rx, ry, hx, hy = b['root_x'], b['root_y'], b['head_x'], b['head_y']
    Ln = math.hypot(hx - rx, hy - ry); ux, uy = (hx - rx) / Ln, (hy - ry) / Ln; nx, ny = -uy, ux
    sh = b['crest_width_m'] / 2 + 15.0; nb = int(round(2 * sh / PROF_STEP)) + 1
    bs = [{'x0': rx + ux * f * Ln - nx * sh, 'y0': ry + uy * f * Ln - ny * sh, 'dx': nx * PROF_STEP, 'dy': ny * PROF_STEP}
          for f in (0.3, 0.4, 0.5, 0.6, 0.7)]
    return {'D01': {'stations': ds, 'n': nd, 'z0': d['coping_m'] + 20.0, 'half': half},
            'B01': {'stations': bs, 'n': nb, 'z0': b['crest_m'] + 20.0, 'half': sh}}


def build_extra_py(K):
    return EXTRA_PY + PROF_PY.replace('__PARAMS__', repr(json.dumps(prof_params(K))))


FRAMES = list(range(1, 241, 2)) + [240]

TOL_POS = 0.30
TOL_FLUSH = 0.05


def L(a, b):
    return close(a, b, 0.03, 0.10)


def fmt(v):
    return 'None' if v is None else (f'{v:.3f}' if isinstance(v, float) else str(v))


# ---------------------------------------------------------------- geometry helpers
def mat_cols(m):
    """rotation columns (normalized) and translation of a 4x4 world matrix."""
    cols = []
    for j in range(3):
        c = [m[0][j], m[1][j], m[2][j]]
        n = math.sqrt(sum(x * x for x in c)) or 1.0
        cols.append([x / n for x in c])
    return cols, [m[0][3], m[1][3], m[2][3]]


def to_local(m, p):
    cols, t = mat_cols(m)
    d = [p[i] - t[i] for i in range(3)]
    return [sum(cols[j][i] * d[i] for i in range(3)) for j in range(3)]


def azim(v):
    return math.degrees(math.atan2(v[1], v[0]))


def adiff(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def clusters(vals, gap):
    vs = sorted(vals)
    out = []
    for v in vs:
        if out and v - out[-1][-1] <= gap:
            out[-1].append(v)
        else:
            out.append([v])
    return out


def width_minmax(pts2):
    """min / max caliper width of 2D point set over directions 0..179 deg."""
    if len(pts2) < 2:
        return None, None
    ws = []
    for d in range(0, 180, 1):
        a = math.radians(d); ux, uy = math.cos(a), math.sin(a)
        pr = [x * ux + y * uy for x, y in pts2]
        ws.append(max(pr) - min(pr))
    return min(ws), max(ws)


def hull2(pts):
    P = sorted(set((round(x, 3), round(y, 3)) for x, y in pts))
    if len(P) < 3:
        return P

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def merge_collinear(poly, closed=True, tol_deg=4.0):
    pts = list(poly)
    changed = True
    while changed and len(pts) > 2:
        changed = False
        n = len(pts)
        rng = range(n) if closed else range(1, n - 1)
        for i in rng:
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6 or math.hypot(c[0] - b[0], c[1] - b[1]) < 1e-6:
                pts.pop(i); changed = True; break
            t = adiff(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), math.degrees(math.atan2(c[1] - b[1], c[0] - b[0])))
            if t < tol_deg:
                pts.pop(i); changed = True; break
    return pts


def upper_profile_count(pts2, bucket=0.05):
    """number of corners of the upper convex profile of (u, z) points (vertical end edges removed)."""
    best = {}
    for u, z in pts2:
        k = round(u / bucket)
        if k not in best or z > best[k][1]:
            best[k] = (u, z)
    P = sorted(best.values())
    if len(P) < 2:
        return 0
    up = []
    for p in P:
        while len(up) >= 2 and ((up[-1][0] - up[-2][0]) * (p[1] - up[-2][1]) - (up[-1][1] - up[-2][1]) * (p[0] - up[-2][0])) >= 0:
            up.pop()
        up.append(p)
    return len(merge_collinear(up, closed=False))


def far_pair(pts):
    if len(pts) < 2:
        return None
    c = [sum(p[i] for p in pts) / len(pts) for i in range(3)]
    a = max(pts, key=lambda p: sum((p[i] - c[i]) ** 2 for i in range(3)))
    b = max(pts, key=lambda p: sum((p[i] - a[i]) ** 2 for i in range(3)))
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def aabb_hit(a, b, m=0.05):
    return all(a[0][i] + m < b[1][i] and b[0][i] + m < a[1][i] for i in range(3))


# ---------------------------------------------------------------- PNG helpers
def png_gray_std(p):
    try:
        from PIL import Image
        im = Image.open(p).convert('L')
        im.thumbnail((480, 270))
        px = list(im.getdata())
    except Exception:
        try:
            px = _png_gray_samples(p)
        except ValueError:
            return -1.0  # v0.2: valid PNG in a layout the fallback decoder does not read (interlaced, palette, <8 bit)
        except Exception:
            return None
    if not px:
        return None
    m = sum(px) / len(px)
    return math.sqrt(sum((x - m) ** 2 for x in px) / len(px))


def _png_gray_samples(p, step=8):
    data = pathlib.Path(p).read_bytes()
    pos = 8; idat = b''; w = h = ct = bd = il = None
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]; typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]; pos += 12 + ln
        if typ == b'IHDR':
            w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', body)
        elif typ == b'IDAT':
            idat += body
        elif typ == b'IEND':
            break
    ch = {0: 1, 2: 3, 4: 2, 6: 4}.get(ct)
    if il or bd not in (8, 16) or not ch:
        raise ValueError(f'unsupported PNG layout (bit depth {bd}, colour type {ct}, interlace {il})')
    bps = bd // 8  # v0.2: 16-bit PNGs: filters work on bytes (bpp = ch*2); sample the high byte of each channel
    raw = zlib.decompress(idat); stride = w * ch * bps
    prev = bytearray(stride); out = []
    ch_b = ch * bps
    for y in range(h):
        f = raw[y * (stride + 1)]; line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - ch_b] if i >= ch_b else 0; b = prev[i]; c = prev[i - ch_b] if i >= ch_b else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                pp = a + b - c; pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        if y % step == 0:
            for x in range(0, w, step):
                q = x * ch_b
                out.append(line[q] if ch <= 2 else (line[q] * 299 + line[q + bps] * 587 + line[q + 2 * bps] * 114) // 1000)
        prev = line
    return out


# ---------------------------------------------------------------- scene accessor
class G:
    def __init__(self, S, key):
        self.S, self.K = S, key
        ex = (S.data or {}).get('extra') or {}
        self.bb1 = ex.get('bbox1') or {}
        self.mw1 = ex.get('mw1') or {}
        self.v1 = ex.get('verts1') or {}
        self.prof = ex.get('prof') or {}
        self.U = key['units']
        self.PP = prof_params(key)

    def bbox(self, name):
        b = self.bb1.get(name)
        if b is None:
            o = self.S.ob(name)
            b = o.get('bbox_world') if o else None
        return b

    def bbox_union(self, names):
        bs = [self.bbox(n) for n in names]
        bs = [b for b in bs if b]
        if not bs:
            return None
        return [[min(b[0][i] for b in bs) for i in range(3)], [max(b[1][i] for b in bs) for i in range(3)]]

    def mw(self, name):
        m = self.mw1.get(name)
        if m is None:
            o = self.S.ob(name)
            m = o.get('matrix_world') if o else None
        return m

    def verts(self, name):
        v = self.v1.get(name)
        if v:
            return v
        b = self.bbox(name)
        if b:  # fallback: bbox corners
            return [[b[i][0], b[j][1], b[k][2]] for i in (0, 1) for j in (0, 1) for k in (0, 1)]
        return None

    def exists(self, name, coll=None):
        o = self.S.ob(name)
        if not o:
            return False
        return True if coll is None else name in self.S.coll(coll)

    def names(self, uid, regex):
        r = re.compile(regex)
        return sorted(n for n in self.S.coll(uid) if r.search(n))

    def meshes(self, uid):
        return [n for n in self.S.coll(uid) if (self.S.ob(n) or {}).get('type') == 'MESH']


# ---------------------------------------------------------------- ray profiles (v0.2)
def prof_rows(g, uid):
    """rows of (s, z) along each station; s = signed distance from the row centre, z None where the ray missed."""
    rows = g.prof.get(uid) or []
    half = g.PP[uid]['half']; out = []
    for row in rows:
        try:
            out.append([(-half + int(k) * PROF_STEP, (float(z) if z is not None else None)) for k, z in row])
        except Exception:
            continue
    return out


def plateaus(row, dz=0.02, min_len=0.3):
    """maximal runs of consecutive hits with |z step| <= dz and horizontal length >= min_len: (z_mean, s0, s1)."""
    out = []; run = []

    def flush():
        if run and (run[-1][0] - run[0][0]) >= min_len - 1e-6:
            out.append((sum(z for _, z in run) / len(run), run[0][0], run[-1][0]))
    for s_, z in row:
        if z is None:
            flush(); run = []; continue
        if run and (abs(z - run[-1][1]) > dz or abs(z - run[0][1]) > 2.5 * dz):  # ramps are not plateaus
            flush(); run = []
        run.append((s_, z))
    flush()
    return out


def inner_span(row, inside, s_c=0.0):
    """width of the contiguous run of rays satisfying inside(z) around s_c; edges at midpoints to the first outside ray."""
    idx = min(range(len(row)), key=lambda i: abs(row[i][0] - s_c)) if row else None
    if idx is None or not inside(row[idx][1]):
        return None
    i0 = idx
    while i0 - 1 >= 0 and inside(row[i0 - 1][1]):
        i0 -= 1
    i1 = idx
    while i1 + 1 < len(row) and inside(row[i1 + 1][1]):
        i1 += 1
    if i0 == 0 or i1 == len(row) - 1:
        return None  # run reaches the end of the scan: no edge found
    return (row[i1][0] + row[i1 + 1][0]) / 2 - (row[i0 - 1][0] + row[i0][0]) / 2


def median(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def mode(v):
    v = [x for x in v if x is not None]
    return max(set(v), key=v.count) if v else None


def dock_prof(g, zc):
    """D01 from downward rays across the parallel body: top width, floor level and altar count per station (medians)."""
    u = g.U['D01']; rows = prof_rows(g, 'D01')
    if not rows:
        return None
    tws, fls, als = [], [], []
    for row in rows:
        hits = [(s_, z) for s_, z in row if z is not None]
        if not hits:
            continue
        cop = max(z for _, z in hits)
        tws.append(inner_span(row, lambda z: z is not None and z < cop - 0.05))
        cen = [z for s_, z in hits if abs(s_) < u['entrance_width_m'] / 2]
        fl = min(cen) if cen else None
        fls.append(fl)
        if fl is not None:
            lv = clusters([p[0] for p in plateaus(row) if fl + 0.1 < p[0] < cop - 0.1], 0.05)
            als.append(len(lv))
    return {'top_w': median(tws), 'floor': median(fls), 'altars': mode(als), 'stations': len(rows)}


def bw_prof(g, crest):
    """B01 crest width from rays across the trunk (along the seaward normal) at 0.3..0.7 L (median): width of the
    contiguous run of hits within 0.03 m of the crest level around the highest hit (edges at midpoints between rays)."""
    rows = prof_rows(g, 'B01')
    if not rows:
        return None
    ws = []
    for row in rows:
        hits = [(s_, z) for s_, z in row if z is not None]
        if not hits:
            continue
        sc = max(hits, key=lambda h: h[1])[0]
        ws.append(inner_span(row, lambda z: z is not None and z >= crest - 0.03, sc))
    return median(ws)


# ---------------------------------------------------------------- per-unit measurement
def m_ship(g, sid):
    """returns (errs, meas) for zone dims; meas holds discrete values too."""
    u = g.U[sid]; errs = []; me = {}
    root = f'{sid}_ROOT'; hull = f'{sid}_HULL'
    if not g.exists(root) or not g.exists(hull):
        return [f'{sid}: ROOT/HULL missing'], me
    M = g.mw(root)
    hv = g.verts(hull)
    loc = [to_local(M, p) for p in hv]
    xs = [p[0] for p in loc]; ys = [p[1] for p in loc]; zs = [p[2] for p in loc]
    Lm, Bm, Tm = max(xs) - min(xs), max(ys) - min(ys), -min(zs)
    me.update(L=Lm, B=Bm, T=Tm)
    # freeboard: gunwale height at midship from station maxima
    band = [p for p in loc if abs(p[0]) <= 0.25 * u['loa_m']]
    st = {}
    for p in band:
        k = round(p[0] / max(0.02 * u['loa_m'], 0.05))
        st[k] = max(st.get(k, -1e9), p[2])
    f = None
    if st:
        items = sorted((k * max(0.02 * u['loa_m'], 0.05), z) for k, z in st.items())
        left = [s for s in items if s[0] <= 0]; right = [s for s in items if s[0] >= 0]
        if left and right:
            (x0, z0), (x1, z1) = left[-1], right[0]
            f = z0 if abs(x1 - x0) < 1e-6 else z0 + (z1 - z0) * (0 - x0) / (x1 - x0)
        else:
            f = min(items, key=lambda s: abs(s[0]))[1]
    me['f'] = f
    for nm, a, b in (('L', Lm, u['loa_m']), ('B', Bm, u['beam_m']), ('T', Tm, u['draft_m']), ('f', f, u['freeboard_m'])):
        if a is None or not L(a, b):
            errs.append(f'{sid} {nm}={fmt(a)} vs {b}')
    hs, ps = u['mast_heights_m'], u['mast_pos_from_stern_m']
    for n in range(1, u['masts'] + 1):
        mn = f'{sid}_MAST_{n}'
        bb = g.bbox(mn)
        if not bb:
            errs.append(f'{mn} missing'); continue
        c = [(bb[0][i] + bb[1][i]) / 2 for i in range(3)]
        top_local = max(to_local(M, [bb[i][0], bb[j][1], bb[k][2]])[2] for i in (0, 1) for j in (0, 1) for k in (0, 1))
        a = to_local(M, c)[0] + Lm / 2
        if not L(top_local, hs[n - 1]):
            errs.append(f'{mn} h={top_local:.2f} vs {hs[n-1]}')
        if not L(a, ps[n - 1]):
            errs.append(f'{mn} a={a:.2f} vs {ps[n-1]}')
    return errs, me


def ship_discrete(g, sid):
    d = {}
    masts = g.names(sid, rf'^{sid}_MAST_\d+$'); d['masts'] = len(masts)
    nm = max([int(x.rsplit('_', 1)[1]) for x in masts] + [0])
    yards = [len(g.names(sid, rf'^{sid}_YARD_{n}_\d+$')) for n in range(1, max(nm, 1) + 1)]
    d['yards_per_mast'] = yards
    d['gaff_masts'] = sorted(int(x.rsplit('_', 1)[1]) for x in g.names(sid, rf'^{sid}_GAFF_\d+$'))
    d['jibs'] = len(g.names(sid, rf'^{sid}_JIB_\d+$'))
    ps = g.names(sid, rf'^{sid}_PORT_S_\d+$'); pp = g.names(sid, rf'^{sid}_PORT_P_\d+$')
    d['ports_per_side'] = len(ps); d['ports_port'] = len(pp)
    zs = []
    for n in ps:
        b = g.bbox(n)
        if b:
            zs.append((b[0][2] + b[1][2]) / 2)
    d['gun_decks'] = len(clusters(zs, 0.5)) if zs else 0
    # nearest berth mark
    m = g.mw(f'{sid}_ROOT')
    if m:
        x, y = m[0][3], m[1][3]
        d['berth'] = min(g.K['berths'], key=lambda b: math.hypot(b['mark_x'] - x, b['mark_y'] - y))['berth']
    return d


def ship_discrete_errs(g, sid, skip_rig=False):
    u = g.U[sid]; d = ship_discrete(g, sid); e = []
    want = dict(masts=u['masts'], ports_per_side=u['ports_per_side'], gun_decks=u['gun_decks'])
    if not skip_rig:
        want.update(yards_per_mast=u['yards_per_mast'], gaff_masts=sorted(u['gaff_masts']), jibs=u['jibs'])
    for k, v in want.items():
        if d.get(k) != v:
            e.append(f'{sid} {k}={d.get(k)} vs {v}')
    if d.get('ports_port') != u['ports_per_side']:
        e.append(f'{sid} PORT_P={d.get("ports_port")} vs {u["ports_per_side"]}')
    return e


def m_quay(g, q, coping=True):
    u = g.U[q]; e = []
    w = f'{q}_WALL'; bb = g.bbox(w)
    if not bb:
        return [f'{w} missing']
    x1, x2, y0, y1 = bb[0][0], bb[1][0], bb[0][1], bb[1][1]
    if abs(x1 - u['face_x1']) > TOL_POS or abs(x2 - u['face_x2']) > TOL_POS:
        e.append(f'{q} x={x1:.2f}..{x2:.2f} vs {u["face_x1"]}..{u["face_x2"]}')
    if not L(x2 - x1, u['length_m']):
        e.append(f'{q} length {x2-x1:.2f}')
    if abs(y0) > TOL_POS:
        e.append(f'{q} face line y={y0:.2f}')
    if not L(y1 - y0, u['apron_depth_m']):
        e.append(f'{q} depth {y1-y0:.2f} vs {u["apron_depth_m"]}')
    if coping:
        c = quay_coping(g, q)
        if c is None or abs(c - u['coping_m']) > TOL_FLUSH:
            e.append(f'{q} coping {fmt(c)} vs {u["coping_m"]}')
    return e


def quay_coping(g, q):
    vs = g.verts(f'{q}_WALL')
    if not vs:
        return None
    band = [p[2] for p in vs if -0.5 <= p[1] <= 2.0]
    return max(band) if band else max(p[2] for p in vs)


def pier_meas(g, p):
    u = g.U[p]; me = {}
    dv = g.verts(f'{p}_DECK'); bb = g.bbox(f'{p}_DECK')
    if not dv or not bb:
        return None
    L0 = u['length_m']
    near = [v for v in dv if v[1] > -0.5 * L0]
    if near:
        me['width'] = max(v[0] for v in near) - min(v[0] for v in near)
        me['cx'] = (max(v[0] for v in near) + min(v[0] for v in near)) / 2
    me['ymax'] = bb[1][1]; me['ztop'] = bb[1][2]
    me['ext_x'] = bb[1][0] - bb[0][0]; me['ext_y'] = bb[1][1] - bb[0][1]
    if 'head_width_m' in u:
        far = [v for v in dv if v[1] < -(L0 + 1.0 - u['head_length_m'] / 2)]
        if far:
            me['head_w'] = max(v[0] for v in far) - min(v[0] for v in far)
        side = [v for v in dv if abs(v[0] - u['root_x']) > u['width_m'] / 2 + 1.0]
        if side:
            me['head_l'] = max(v[1] for v in side) - min(v[1] for v in side)
    piles = g.names(p, rf'^{p}_PILE_\d+$')
    cs = []
    for n in piles:
        b = g.bbox(n)
        if b:
            cs.append(((b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2))
    me['piles'] = len(piles)
    cl = clusters([c[1] for c in cs], 0.5)
    me['bents'] = len(cl)
    me['bent_counts'] = [len(c) for c in sorted(cl, key=lambda c: -sum(c) / len(c))]  # from root outwards
    ys = sorted((sum(c) / len(c) for c in cl), reverse=True)
    if len(ys) >= 2:
        me['length'] = ys[0] - ys[-1] if abs(ys[0]) < 1.0 else -ys[-1]
        me['spacing'] = (ys[0] - ys[-1]) / (len(ys) - 1)
        # axis: x of bent centroids vs y
        xb = []
        for c in cl:
            yc = sum(c) / len(c)
            xs = [q[0] for q in cs if abs(q[1] - yc) <= 0.5]
            xb.append((yc, sum(xs) / len(xs)))
        xb.sort()
        dx = xb[-1][1] - xb[0][1]; dy = xb[-1][0] - xb[0][0]
        me['axis_err'] = abs(math.degrees(math.atan2(dx, dy))) if dy else 90.0
    else:
        me['length'] = (bb[1][1] - bb[0][1]) - (1.0 if 'head_width_m' in u else 0.0)
    return me


def m_pier(g, p):
    u = g.U[p]; e = []
    me = pier_meas(g, p)
    if me is None:
        return [f'{p}_DECK missing']
    if not L(me.get('length'), u['length_m']):
        e.append(f'{p} length {fmt(me.get("length"))} vs {u["length_m"]}')
    if not L(me.get('width'), u['width_m']):
        e.append(f'{p} width {fmt(me.get("width"))} vs {u["width_m"]}')
    if not L(me.get('spacing'), u['bent_spacing_m']):
        e.append(f'{p} spacing {fmt(me.get("spacing"))} vs {u["bent_spacing_m"]}')
    if me.get('cx') is None or abs(me['cx'] - u['root_x']) > TOL_POS or abs(me['ymax'] - u['root_y']) > TOL_POS:
        e.append(f'{p} root ({fmt(me.get("cx"))},{fmt(me.get("ymax"))}) vs ({u["root_x"]},0)')
    if 'head_width_m' in u:
        if not L(me.get('head_w'), u['head_width_m']):
            e.append(f'{p} head width {fmt(me.get("head_w"))} vs {u["head_width_m"]}')
        if not L(me.get('head_l'), u['head_length_m']):
            e.append(f'{p} head length {fmt(me.get("head_l"))} vs {u["head_length_m"]}')
    return e


def pier_discrete_errs(g, p):
    u = g.U[p]; me = pier_meas(g, p) or {}; e = []
    if me.get('bents') != u['bents']:
        e.append(f'{p} bents {me.get("bents")} vs {u["bents"]}')
    if me.get('piles') != u['piles']:
        e.append(f'{p} piles {me.get("piles")} vs {u["piles"]}')
    want = [u['piles_per_bent']] * u['bents']
    if 'head_bents' in u:
        want = [u['piles_per_bent']] * (u['bents'] - u['head_bents']) + [u['head_piles_per_bent']] * u['head_bents']
    if me.get('bent_counts') != want:
        e.append(f'{p} piles per bent {me.get("bent_counts")} vs {want}')
    return e


def quay_discrete_errs(g, q):
    u = g.U[q]; e = []
    nb = len(g.names(q, rf'^{q}_BOLLARD_\d+$'))
    st = g.names(q, rf'^{q}_STAIR_\d+$')
    if nb != u['bollards']:
        e.append(f'{q} bollards {nb} vs {u["bollards"]}')
    if len(st) != u['stairs']:
        e.append(f'{q} stairs {len(st)} vs {u["stairs"]}')
    else:
        pos = sorted(((g.bbox(n)[0][0] + g.bbox(n)[1][0]) / 2 - u['face_x1']) for n in st if g.bbox(n))
        want = sorted(u['stair_pos_from_west_m'])
        if len(pos) != len(want) or any(abs(a - b) > 0.5 for a, b in zip(pos, want)):
            e.append(f'{q} stair pos {[round(x, 2) for x in pos]} vs {want}')
    return e


def crane_meas(g, c):
    u = g.U[c]; me = {}
    hb = g.verts(f'{c}_HOUSE')
    if not hb:
        return None
    parts = [f'{c}_HOUSE'] + g.names(c, rf'^{c}_WHEEL_\d+$')
    bbs = [g.bbox(n) for n in parts if g.bbox(n)]
    base = min(b[0][2] for b in bbs); me['base'] = base
    low = [p for p in hb if p[2] < base + 0.9 * u['house_h_m']] or hb
    xs = [p[0] for p in low]; ys = [p[1] for p in low]
    me['foot'] = sorted([max(xs) - min(xs), max(ys) - min(ys)])
    me['cx'], me['cy'] = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    wheels = g.names(c, rf'^{c}_WHEEL_\d+$'); me['wheels'] = len(wheels)
    me['wheel_d'] = [max(g.bbox(n)[1][i] - g.bbox(n)[0][i] for i in range(3)) for n in wheels if g.bbox(n)]
    jv = g.verts(f'{c}_JIB')
    if jv:
        me['jib_len'] = far_pair(jv)
        tip = max(jv, key=lambda p: p[2])
        me['jib_tip_h'] = tip[2] - base
        me['jib_heading'] = azim([tip[0] - me['cx'], tip[1] - me['cy']])
    # roof form from pooled collection verts above eaves near the house footprint
    pool = []
    for n in g.meshes(c):
        if re.search(r'_(JIB|WHEEL_\d+)$', n):
            continue
        b = g.bbox(n)  # v0.2: finials / king posts / small fittings must not define the ridge: keep HOUSE + roof-sized parts
        if n != f'{c}_HOUSE' and 'ROOF' not in n.upper() and (not b or max(b[1][0] - b[0][0], b[1][1] - b[0][1]) < 0.5 * u['house_w_m']):
            continue
        for p in g.v1.get(n) or []:
            if p[2] > base + u['house_h_m'] - 0.3 and abs(p[0] - me['cx']) < u['house_w_m'] and abs(p[1] - me['cy']) < u['house_d_m']:
                pool.append(p)
    if pool:
        top = max(p[2] for p in pool)
        tv = [(p[0], p[1]) for p in pool if p[2] >= top - 0.05]
        span = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in tv for b in tv) if len(tv) > 1 else 0.0
        me['ridge_span'] = span
        me['roof'] = 'gable' if span > 0.5 * u['house_w_m'] else ('pyramid' if span < 0.25 * u['house_w_m'] else 'unknown')
    return me


def m_crane(g, c):
    u = g.U[c]; e = []
    me = crane_meas(g, c)
    if me is None:
        return [f'{c}_HOUSE missing']
    want = sorted([u['house_w_m'], u['house_d_m']])
    if not all(L(a, b) for a, b in zip(me['foot'], want)):
        e.append(f'{c} house {[round(x, 2) for x in me["foot"]]} vs {want}')
    if math.hypot(me['cx'] - u['x'], me['cy'] - u['y']) > TOL_POS:
        e.append(f'{c} base centre ({me["cx"]:.2f},{me["cy"]:.2f}) vs ({u["x"]},{u["y"]})')
    if not me['wheel_d'] or not all(L(d, u['wheel_diam_m']) for d in me['wheel_d']):
        e.append(f'{c} wheel D {[round(x, 2) for x in me["wheel_d"]]} vs {u["wheel_diam_m"]}')
    if not L(me.get('jib_len'), u['jib_len_m']):
        e.append(f'{c} jib length {fmt(me.get("jib_len"))} vs {u["jib_len_m"]}')
    if not L(me.get('jib_tip_h'), u['jib_tip_h_m']):
        e.append(f'{c} jib tip h {fmt(me.get("jib_tip_h"))} vs {u["jib_tip_h_m"]}')
    return e


def crane_discrete_errs(g, c):
    u = g.U[c]; me = crane_meas(g, c) or {}; e = []
    if me.get('wheels') != u['wheels']:
        e.append(f'{c} wheels {me.get("wheels")} vs {u["wheels"]}')
    if me.get('roof') != u['roof']:
        e.append(f'{c} roof {me.get("roof")} (ridge span {fmt(me.get("ridge_span"))}) vs {u["roof"]}')
    if me.get('jib_heading') is None or adiff(me['jib_heading'], u['jib_heading_deg']) > 3.0:
        e.append(f'{c} jib heading {fmt(me.get("jib_heading"))} vs {u["jib_heading_deg"]}')
    return e


def sheer_meas(g):
    u = g.U['C03']; me = {}
    legs = g.names('C03', r'^C03_LEG_\d+$'); me['legs'] = len(legs)
    me['backstays'] = len(g.names('C03', r'^C03_BACKSTAY_\d+$'))
    lv = [g.verts(n) for n in legs[:2]]
    if len(lv) < 2 or not all(lv):
        return me
    feet = []
    for vs in lv:
        z0 = min(p[2] for p in vs); bot = [p for p in vs if p[2] < z0 + 0.3]
        feet.append([sum(p[i] for p in bot) / len(bot) for i in range(3)] + [z0])
    me['leg_len'] = [far_pair(vs) for vs in lv]
    me['spread'] = math.hypot(feet[0][0] - feet[1][0], feet[0][1] - feet[1][1])
    mid = [(feet[0][i] + feet[1][i]) / 2 for i in range(2)]; me['mid'] = mid
    base = min(f[3] for f in feet); me['base'] = base
    allv = lv[0] + lv[1]; zt = max(p[2] for p in allv)
    topv = [p for p in allv if p[2] > zt - 0.3]
    apex = [sum(p[i] for p in topv) / len(topv) for i in range(3)]
    me['apex_h'] = zt - base
    hd = [apex[0] - mid[0], apex[1] - mid[1]]
    me['rake'] = math.degrees(math.atan2(math.hypot(*hd), apex[2] - base))
    me['rake_heading'] = azim(hd)
    return me


def m_sheer(g):
    u = g.U['C03']; me = sheer_meas(g); e = []
    if 'leg_len' not in me:
        return ['C03 legs missing']
    if not all(L(x, u['leg_len_m']) for x in me['leg_len']):
        e.append(f'C03 leg len {[round(x, 2) for x in me["leg_len"]]}')
    if not L(me['spread'], u['foot_spread_m']):
        e.append(f'C03 foot spread {me["spread"]:.2f}')
    if not L(me['apex_h'], u['apex_h_m']):
        e.append(f'C03 apex h {me["apex_h"]:.2f} vs {u["apex_h_m"]}')
    if math.hypot(me['mid'][0] - u['x'], me['mid'][1] - u['y']) > TOL_POS:
        e.append(f'C03 mid-feet {[round(x, 2) for x in me["mid"]]}')
    q1 = g.U['Q01']['coping_m']
    if abs(me['base'] - q1) > TOL_FLUSH:
        e.append(f'C03 feet z {me["base"]:.3f} vs Q01 coping {q1}')
    return e


def sheer_discrete_errs(g):
    u = g.U['C03']; me = sheer_meas(g); e = []
    if me.get('legs') != u['legs']:
        e.append(f'C03 legs {me.get("legs")}')
    if me.get('backstays') != u['backstays']:
        e.append(f'C03 backstays {me.get("backstays")}')
    if me.get('rake') is None or abs(me['rake'] - u['rake_deg']) > 2.0:
        e.append(f'C03 rake {fmt(me.get("rake"))} vs {u["rake_deg"]}')
    if me.get('rake_heading') is None or adiff(me['rake_heading'], u['rake_heading_deg']) > 3.0:
        e.append(f'C03 rake heading {fmt(me.get("rake_heading"))} vs {u["rake_heading_deg"]}')
    return e


def wh_meas(g, w):
    u = g.U[w]; me = {}
    bb = g.bbox(f'{w}_BODY'); rb = g.bbox(f'{w}_ROOF')
    if not bb or not rb:
        return None
    me['len'] = bb[1][0] - bb[0][0]; me['dep'] = bb[1][1] - bb[0][1]
    me['cx'] = (bb[1][0] + bb[0][0]) / 2; me['cy'] = (bb[1][1] + bb[0][1]) / 2
    me['zb'] = bb[0][2]
    me['eave'] = rb[0][2] - u['base_z_m']
    me['ridge'] = max(rb[1][2], bb[1][2]) - u['base_z_m']
    wins = g.names(w, rf'^{w}_WIN_\d+$'); doors = g.names(w, rf'^{w}_DOOR_\d+$')
    cen = lambda n: [(g.bbox(n)[0][i] + g.bbox(n)[1][i]) / 2 for i in range(3)] if g.bbox(n) else None
    wc = [c for c in map(cen, wins) if c]; dc = [c for c in map(cen, doors) if c]
    me['front_y'] = (sum(c[1] for c in wc + dc) / len(wc + dc)) if (wc or dc) else None
    me['floors'] = len(clusters([c[2] for c in wc], 0.8)) if wc else 0
    bx = clusters([c[0] for c in wc + dc], 1.0)
    me['bays'] = len(bx)
    centers = [sum(c) / len(c) for c in bx]
    dbays = sorted({min(range(len(centers)), key=lambda i: abs(centers[i] - c[0])) + 1 for c in dc}) if centers else []
    me['door_bays'] = dbays
    hs = g.names(w, rf'^{w}_HOIST_\d+$'); me['hoists'] = len(hs)
    hb = sorted({min(range(len(centers)), key=lambda i: abs(centers[i] - cen(n)[0])) + 1 for n in hs if cen(n)}) if centers else []
    me['hoist_bays'] = hb
    rv = g.verts(f'{w}_ROOF')
    if rv and len(rv) > 3:
        top = max(p[2] for p in rv)
        ridge = [p for p in rv if p[2] >= top - 0.05]
        span = max(p[0] for p in ridge) - min(p[0] for p in ridge)
        me['ridge_ratio'] = span / u['length_m']
        # cross-section profile from all roof verts projected on (y, z) (extruded roofs only have verts at the ends)
        me['profile_pts'] = upper_profile_count([(p[1], p[2]) for p in rv])
        if me['ridge_ratio'] < 0.85:
            me['roof'] = 'hipped'
        elif me['profile_pts'] >= 5:
            me['roof'] = 'gambrel'
        elif me['profile_pts'] in (3, 4):
            me['roof'] = 'gable'
        else:
            me['roof'] = 'unknown'
    return me


def m_wh(g, w):
    u = g.U[w]; me = wh_meas(g, w); e = []
    if me is None:
        return [f'{w} BODY/ROOF missing']
    for nm, a, b in (('length', me['len'], u['length_m']), ('depth', me['dep'], u['depth_m']),
                     ('eave', me['eave'], u['eave_h_m']), ('ridge', me['ridge'], u['ridge_h_m'])):
        if not L(a, b):
            e.append(f'{w} {nm} {a:.2f} vs {b}')
    if math.hypot(me['cx'] - u['x'], me['cy'] - u['y']) > TOL_POS:
        e.append(f'{w} centre ({me["cx"]:.2f},{me["cy"]:.2f}) vs ({u["x"]},{u["y"]})')
    if abs(me['zb'] - u['base_z_m']) > TOL_FLUSH:
        e.append(f'{w} base z {me["zb"]:.3f}')
    if me['front_y'] is None or me['front_y'] > me['cy'] - u['depth_m'] / 4:
        e.append(f'{w} front facade not facing -Y (win/door mean y {fmt(me["front_y"])})')
    return e


def wh_discrete_errs(g, w):
    u = g.U[w]; me = wh_meas(g, w) or {}; e = []
    for k, v in (('bays', u['bays']), ('floors', u['floors']), ('hoists', u['hoists']), ('roof', u['roof'])):
        if me.get(k) != v:
            e.append(f'{w} {k}={me.get(k)} vs {v}' + (f' (ridge/L {fmt(me.get("ridge_ratio"))}, profile {me.get("profile_pts")})' if k == 'roof' else ''))
    if me.get('door_bays') != sorted(u['hoist_bays']):
        e.append(f'{w} door bays {me.get("door_bays")} vs {sorted(u["hoist_bays"])}')
    if me.get('hoist_bays') != sorted(u['hoist_bays']):
        e.append(f'{w} hoist bays {me.get("hoist_bays")} vs {sorted(u["hoist_bays"])}')
    return e


def dock_meas(g):
    u = g.U['D01']; me = {}
    vs = g.verts('D01_BASIN'); bb = g.bbox('D01_BASIN')
    if not vs or not bb:
        return None
    cx = u['entr_x']; Lw = u['length_m']; Wt = u['top_width_m']
    zc = max(p[2] for p in vs); me['coping'] = zc
    me['ymin'] = bb[0][1]; me['cx'] = (bb[0][0] + bb[1][0]) / 2
    top = [p for p in vs if p[2] >= zc - 0.05]
    head = [p for p in top if abs(p[0] - cx) < 2.0 and p[1] > Lw / 2]
    me['length'] = min(p[1] for p in head) if head else bb[1][1]
    mid = [p for p in top if 0.3 * Lw < p[1] < 0.6 * Lw]
    l = [cx - p[0] for p in mid if p[0] < cx]; r = [p[0] - cx for p in mid if p[0] > cx]
    me['top_w'] = (min(l) + min(r)) if l and r else None
    ent = [p for p in top if p[1] < 3.0]
    l = [cx - p[0] for p in ent if p[0] < cx]; r = [p[0] - cx for p in ent if p[0] > cx]
    me['ent_w'] = (min(l) + min(r)) if l and r else None
    inner = [p for p in vs if abs(p[0] - cx) < Wt / 2 + 0.2 and 6.0 < p[1] < Lw - Wt / 2]
    cl = clusters([p[2] for p in inner], 0.05)
    floor = None
    for c in cl:
        zc0 = sum(c) / len(c)
        cnt = sum(1 for p in inner if abs(p[2] - zc0) <= 0.05 and abs(p[0] - cx) < u['entrance_width_m'] / 2)
        if cnt >= 2:
            floor = zc0; break
    me['floor'] = floor
    if floor is not None:
        me['altars'] = sum(1 for c in cl if floor + 0.1 < sum(c) / len(c) < zc - 0.1)
    # v0.2: surface ray profile (independent of vertex placement) overrides the vertex sampling when available
    pr = dock_prof(g, zc)
    if pr:
        me['method'] = f'ray profile ({pr["stations"]} stations)'
        me['top_w'], me['floor'] = pr['top_w'], pr['floor']
        me['altars'] = pr['altars'] if pr['floor'] is not None else None
    else:
        me['method'] = 'vertex sampling'
    r0 = Wt / 2; cy = Lw - r0; tgt = [(cx + s * r0 * math.cos(math.radians(45)), cy + r0 * math.sin(math.radians(45))) for s in (-1, 1)]
    me['semicircle'] = all(any(math.hypot(p[0] - t[0], p[1] - t[1]) < 1.0 for p in top) for t in tgt)
    me['keel_blocks'] = len(g.names('D01', r'^D01_KEELBLOCK_\d+$'))
    me['gates'] = len(g.names('D01', r'^D01_GATE_\d+$'))
    return me


def m_dock(g):
    u = g.U['D01']; me = dock_meas(g); e = []
    if me is None:
        return ['D01_BASIN missing']
    for nm, a, b in (('length', me['length'], u['length_m']), ('top width', me['top_w'], u['top_width_m']),
                     ('entrance', me['ent_w'], u['entrance_width_m']), ('floor', me['floor'], u['floor_m'])):
        if a is None or not L(a, b):
            e.append(f'D01 {nm} {fmt(a)} vs {b}')
    if abs(me['coping'] - u['coping_m']) > TOL_FLUSH:
        e.append(f'D01 coping {me["coping"]:.3f} vs {u["coping_m"]}')
    if abs(me['ymin'] - u['entr_y']) > TOL_POS or abs(me['cx'] - u['entr_x']) > TOL_POS:
        e.append(f'D01 entrance centre ({me["cx"]:.2f},{me["ymin"]:.2f})')
    return e


def dock_discrete_errs(g):
    u = g.U['D01']; me = dock_meas(g) or {}; e = []
    if me.get('altars') != u['altars']:
        e.append(f'D01 altars {me.get("altars")} vs {u["altars"]}')
    if me.get('keel_blocks') != u['keel_blocks']:
        e.append(f'D01 keel blocks {me.get("keel_blocks")}')
    if me.get('gates') != u['gate_leaves']:
        e.append(f'D01 gate leaves {me.get("gates")}')
    if not me.get('semicircle'):
        e.append('D01 head not semicircular (no coping-edge vertex on 45° arc points)')
    return e


def bw_meas(g):
    u = g.U['B01']; me = {}
    vs = g.verts('B01_MOUND')
    if not vs:
        return None
    rx, ry, hx, hy = u['root_x'], u['root_y'], u['head_x'], u['head_y']
    Ln = math.hypot(hx - rx, hy - ry); ux, uy = (hx - rx) / Ln, (hy - ry) / Ln; nx, ny = -uy, ux  # n -> seaward
    crest = max(p[2] for p in vs); me['crest'] = crest
    top = [((p[0] - rx) * ux + (p[1] - ry) * uy, (p[0] - rx) * nx + (p[1] - ry) * ny) for p in vs if p[2] >= crest - 0.1]
    if not top:
        return me
    tmax = max(t for t, s in top); tmin = min(t for t, s in top)
    midb = [s for t, s in top if 0.2 * Ln < t < 0.8 * Ln]
    if not midb:  # v0.2: trunk extruded in one segment -> crest vertices only at the root/head ends; drop the head
        midb = [s for t, s in top if t < tmax - 2 * u['head_radius_m'] - 0.5]
    me['crest_w'] = (max(midb) - min(midb)) if midb else None
    pw = bw_prof(g, crest)  # v0.2: ray profile across the trunk overrides vertex sampling when available
    if pw is not None or g.prof.get('B01'):
        me['crest_w'] = pw
    headr = [(t, s) for t, s in top if t > tmax - 3 * u['head_radius_m']]
    R = max(abs(s) for t, s in headr) if headr else None
    me['R'] = R
    if R:
        tc = tmax - R; sc = (max(s for t, s in headr) + min(s for t, s in headr)) / 2
        me['length'] = tc - tmin
        me['head_xy'] = (rx + ux * tc + nx * sc, ry + uy * tc + ny * sc)
    pars = g.names('B01', r'^B01_PARAPET_\d+$'); me['segments'] = len(pars)
    sides = []; ph = []
    for n in pars:
        b = g.bbox(n)
        if b:
            c = [(b[0][i] + b[1][i]) / 2 for i in range(2)]
            sides.append((c[0] - rx) * nx + (c[1] - ry) * ny); ph.append(b[1][2] - crest)
    me['parapet_side'] = 'seaward' if sides and all(s > 0 for s in sides) else ('harbour' if sides and all(s < 0 for s in sides) else 'mixed')
    me['parapet_h'] = ph
    return me


def m_bw(g):
    u = g.U['B01']; me = bw_meas(g); e = []
    if me is None:
        return ['B01_MOUND missing']
    if abs(me['crest'] - u['crest_m']) > TOL_FLUSH and not L(me['crest'], u['crest_m']):
        e.append(f'B01 crest {me["crest"]:.2f}')
    for nm, a, b in (('crest width', me.get('crest_w'), u['crest_width_m']), ('head R', me.get('R'), u['head_radius_m']),
                     ('length', me.get('length'), u['length_m'])):
        if a is None or not L(a, b):
            e.append(f'B01 {nm} {fmt(a)} vs {b}')
    if me.get('head_xy') is None or math.hypot(me['head_xy'][0] - u['head_x'], me['head_xy'][1] - u['head_y']) > TOL_POS:
        e.append(f'B01 head centre {me.get("head_xy")}')
    if not me['parapet_h'] or not all(L(h, u['parapet_h_m']) for h in me['parapet_h']):
        e.append(f'B01 parapet h {[round(h, 2) for h in me["parapet_h"]][:4]} vs {u["parapet_h_m"]}')
    return e


def lh_meas(g):
    u = g.U['L01']; me = {}
    tv = g.verts('L01_TOWER')
    if not tv:
        return None
    z0, z1 = min(p[2] for p in tv), max(p[2] for p in tv)
    me['base'] = z0; me['tower_h'] = z1 - z0
    bot = [(p[0], p[1]) for p in tv if p[2] < z0 + 0.3]; topv = [(p[0], p[1]) for p in tv if p[2] > z1 - 0.3]
    me['base_w'] = width_minmax(bot); me['top_w'] = width_minmax(topv)
    if bot:
        me['base_c'] = (sum(p[0] for p in bot) / len(bot), sum(p[1] for p in bot) / len(bot))
        hl = merge_collinear(hull2(bot))
        me['hull_n'] = len(hl)
        me['section'] = 'round' if len(hl) >= 24 else {8: 'octagon', 6: 'hexagon'}.get(len(hl), f'{len(hl)}-gon')
    allb = g.bbox_union([n for n in g.meshes('L01') if not re.search(r'_BEAM_\d+$', n)])  # v0.2: beam volumes excluded
    me['total_h'] = allb[1][2] - z0 if allb else None
    beams = [n for n in g.names('L01', r'^L01_BEAM_\d+$') if is_child_of(g, n, 'L01_ROTOR')]
    me['beams'] = len(beams); me['beam_names'] = beams
    bz = [(g.bbox(n)[0][2] + g.bbox(n)[1][2]) / 2 for n in beams if g.bbox(n)]
    rm = g.mw('L01_ROTOR')
    me['focal'] = (sum(bz) / len(bz) - z0) if bz else ((rm[2][3] - z0) if rm else None)
    me['bands'] = len(g.names('L01', r'^L01_BAND_\d+$'))
    me['windows'] = len(g.names('L01', r'^L01_WINDOW_\d+$'))
    return me


def is_child_of(g, n, parent):
    seen = 0; o = g.S.ob(n)
    while o and seen < 50:
        p = o.get('parent')
        if p == parent:
            return True
        o = g.S.ob(p) if p else None; seen += 1
    return False


def m_lh(g):
    u = g.U['L01']; me = lh_meas(g); e = []
    if me is None:
        return ['L01_TOWER missing']
    for nm, w, b in (('base dia', me['base_w'], u['base_diam_m']), ('top dia', me['top_w'], u['top_diam_m'])):
        if not w or not (L(w[0], b) or L(w[1], b)):
            e.append(f'L01 {nm} min/max {w} vs {b}')
    for nm, a, b in (('tower h', me['tower_h'], u['tower_h_m']), ('focal h', me['focal'], u['focal_h_m']), ('total h', me['total_h'], u['total_h_m'])):
        if a is None or not L(a, b):
            e.append(f'L01 {nm} {fmt(a)} vs {b}')
    return e


def lh_discrete_errs(g):
    u = g.U['L01']; me = lh_meas(g) or {}; e = []
    for k, v in (('section', u['section']), ('bands', u['red_bands']), ('windows', u['windows']), ('beams', u['beams'])):
        if me.get(k) != v:
            e.append(f'L01 {k}={me.get(k)} vs {v}')
    return e


# ---------------------------------------------------------------- motion
def series(S, name):
    out = []
    for f in FRAMES:
        m = S.at(f, name)
        if m:
            out.append((f, m))
    return out


def roll_check(S, sid, Tr):
    ser = series(S, f'{sid}_ROOT')
    if len(ser) < 60:
        return f'{sid}: ROOT not sampled ({len(ser)} frames)'
    m1 = ser[0][1]
    if ser[0][0] != 1:
        return f'{sid}: frame 1 missing'
    c1, t1 = mat_cols(m1)
    roll0 = math.degrees(math.asin(max(-1, min(1, c1[1][2]))))
    if abs(roll0) > 0.2:
        return f'{sid}: frame-1 roll {roll0:.2f}°'
    ts, ph = [], []
    for f, m in ser:
        c, t = mat_cols(m)
        if math.dist(t, t1) > 0.05:
            return f'{sid}: ROOT moves {math.dist(t, t1):.3f} m at f{f}'
        dx = math.degrees(math.acos(max(-1, min(1, sum(c[0][i] * c1[0][i] for i in range(3))))))
        if dx > 0.3:
            return f'{sid}: pitch/yaw change {dx:.2f}° at f{f}'
        y = c[1]; z1 = c1[2]; y1 = c1[1]
        phi = math.degrees(math.atan2(sum(y[i] * z1[i] for i in range(3)), sum(y[i] * y1[i] for i in range(3))))
        ts.append((f - 1) / 24.0); ph.append(phi)
    amp = max(abs(p) for p in ph)
    if abs(amp - 2.0) > 0.3:
        return f'{sid}: roll amplitude {amp:.2f}°'
    zc = [0.0]
    for i in range(1, len(ph)):
        a, b = ph[i - 1], ph[i]
        if a == 0 and i > 1:
            continue
        if (a < 0 < b) or (a > 0 > b) or (b == 0 and a != 0):
            zc.append(ts[i - 1] + (ts[i] - ts[i - 1]) * (0 - a) / (b - a))
    if len(zc) < 3:
        return f'{sid}: <2 zero crossings, cannot get period'
    T = 2 * (zc[-1] - zc[0]) / (len(zc) - 1)
    if abs(T - Tr) > 0.05 * Tr:
        return f'{sid}: roll period {T:.2f}s vs {Tr}'
    s = 1 if sum(p * math.sin(2 * math.pi * t / T) for t, p in zip(ts, ph)) >= 0 else -1
    res = math.sqrt(sum((p - s * amp * math.sin(2 * math.pi * t / T)) ** 2 for t, p in zip(ts, ph)) / len(ph))
    if res > 0.3 * amp:
        return f'{sid}: not sinusoidal (rms resid {res:.2f}°)'
    return None


def rotor_meas(S, g):
    ser = series(S, 'L01_ROTOR')
    me = {'n': len(ser)}
    if len(ser) < 60:
        return me
    az = []
    for f, m in ser:
        c, t = mat_cols(m)
        az.append(azim(c[0]))
    un = [az[0]]
    for a in az[1:]:
        d = (a - un[-1] % 360 + 180) % 360 - 180
        un.append(un[-1] + d)
    fs = [f for f, m in ser]
    me['az1'] = az[0] if fs[0] == 1 else None
    inc = [(un[i] - un[i - 1]) / (fs[i] - fs[i - 1]) for i in range(1, len(un))]
    mi = sum(inc) / len(inc)
    me['omega'] = mi
    me['cv'] = (math.sqrt(sum((x - mi) ** 2 for x in inc) / len(inc)) / abs(mi)) if mi else 1e9
    me['monotone_ccw'] = all(x > 0 for x in inc)
    n = len(fs); mf = sum(fs) / n; mu = sum(un) / n
    me['omega_fit'] = sum((f - mf) * (a - mu) for f, a in zip(fs, un)) / sum((f - mf) ** 2 for f in fs)
    c, t = mat_cols(ser[0][1])
    me['xy'] = (t[0], t[1])
    return me


# ---------------------------------------------------------------- main
def run(ctx):
    R = {}
    K = ctx.get('answer') or json.loads((pathlib.Path(ctx['tests']) / 'answer-key.json').read_text(encoding='utf-8'))
    items = {i['id']: i for i in ctx['items']}
    out = pathlib.Path(ctx['out'])

    def guard(iid, fn):
        try:
            R[iid] = fn()
        except Exception:
            R[iid] = bad('check error: ' + traceback.format_exc()[-400:])

    # ---- file-level checks (independent of Blender)
    def png_item(names):
        msgs = []; notes = []
        for n in names:
            p = out / 'renders' / n
            if not p.exists():
                msgs.append(f'{n} missing'); continue
            sz = png_size(p)
            if sz != (1920, 1080):
                msgs.append(f'{n} size {sz}'); continue
            sd = png_gray_std(p)
            if sd == -1.0:
                notes.append(f'{n}: blank test skipped (PNG layout not decodable without PIL)')
            elif sd is None or sd <= 8:
                msgs.append(f'{n} blank/undecodable (std {fmt(sd)})')
        return bad('; '.join(msgs)) if msgs else ok(', '.join(names) + ' 1920x1080, non-blank' + ('; ' + '; '.join(notes) if notes else ''))
    guard('B06', lambda: png_item(['overview.png']))
    guard('B07', lambda: png_item(['central_quay.png', 'lighthouse.png']))

    man = load_manifest(out)
    REQ = {'ship': ['rig_type', 'masts', 'yards_per_mast', 'gaff_masts', 'jibs', 'ports_per_side', 'gun_decks', 'loa_m', 'beam_m', 'draft_m', 'berth', 'roll_period_s'],
           'quay': ['length_m', 'coping_m', 'bollards', 'stairs'], 'pier': ['length_m', 'width_m', 'bents', 'piles', 'deck_top_m'],
           'breakwater': ['length_m', 'crest_m', 'segments', 'parapet_side'],
           'lighthouse': ['section', 'tower_h_m', 'red_bands', 'windows', 'beams', 'period_s', 'beam1_azimuth_deg'],
           'treadwheel_crane': ['wheels', 'wheel_diam_m', 'roof', 'jib_len_m', 'jib_heading_deg'],
           'sheer_legs': ['leg_len_m', 'foot_spread_m', 'rake_deg', 'backstays'],
           'warehouse': ['bays', 'floors', 'roof', 'hoists', 'eave_h_m', 'ridge_h_m'],
           'dry_dock': ['length_m', 'altars', 'keel_blocks', 'gate']}
    mand = {}

    def b08():
        if not isinstance(man, dict) or not isinstance(man.get('units'), list):
            return bad('manifest.json missing or no units list')
        ids = [x.get('id') for x in man['units'] if isinstance(x, dict)]
        if len(man['units']) != 26 or sorted(ids) != sorted(K['units']):
            return bad(f'{len(man["units"])} entries; ids mismatch {sorted(set(K["units"]) ^ set(ids))[:6]}')
        miss = []
        for x in man['units']:
            mand[x['id']] = x
            ps = x.get('params') or {}
            need = REQ[K['units'][x['id']]['type']]
            m = [k for k in need if k not in ps]
            if m:
                miss.append(f'{x["id"]}:{m}')
        return bad('missing params ' + '; '.join(miss[:6])) if miss else ok('26 entries with all required params')
    guard('B08', b08)

    # ---- scene
    S = Scene.load(ctx, frames=FRAMES, anim_regex=r'^(S\d\d_ROOT|L01_ROTOR)$', extra_py=build_extra_py(K))
    scene_items = ['B01', 'B02', 'B03', 'B04', 'B05', 'M01', 'M02', 'M03', 'M04', 'M05', 'M06', 'M07', 'M08', 'M09', 'M10',
                   'G01', 'G02', 'G03', 'G04', 'G05', 'G06', 'G07', 'G08', 'G09', 'G10', 'G11', 'G12', 'G13']
    if S.err or not S.data:
        for i in scene_items:
            R[i] = bad(f'scene unavailable: {S.err}')
        return R
    ctx['_w10_scene_ok'] = True
    # v0.2: number of answer-key unit IDs that exist as collections (B02 group gate only when < GATE_MIN_UNITS)
    ctx['_w10_nunits'] = sum(1 for uid in K['units'] if S.has_coll(uid))
    g = G(S, K)
    U = K['units']
    ZONES = K['zones']

    def b01():
        sc = S.data.get('scene') or {}
        if sc.get('unit_system') == 'METRIC' and abs(float(sc.get('scale_length', 0)) - 1.0) < 1e-6:
            return ok(f'Blender {S.data.get("blender_version")}; METRIC, scale 1.0')
        return bad(f'unit_system={sc.get("unit_system")} scale={sc.get("scale_length")}')
    guard('B01', b01)

    def b02():
        e = []
        names = set((S.data.get('collections') or {}).keys())
        miss = [x for x in list(U) + ['SITE'] if x not in names]
        if miss:
            e.append(f'missing collections {miss}')
        owner = {}
        for uid in U:
            ms = g.meshes(uid)
            if uid in names and not ms:
                e.append(f'{uid} has no mesh')
            for n in ms:
                owner.setdefault(n, set()).add(uid)
        shared = [f'{n}:{sorted(v)}' for n, v in owner.items() if len(v) > 1]
        if shared:
            e.append(f'shared meshes {shared[:4]}')
        return bad('; '.join(e)) if e else ok('26 unit collections + SITE; meshes disjoint')
    guard('B02', b02)

    def b03():
        e = []
        req = []
        for s in SHIPS:
            req += [(s, f'{s}_ROOT', 'EMPTY'), (s, f'{s}_HULL', 'MESH')]
        req += [(q, f'{q}_WALL', 'MESH') for q in ('Q01', 'Q02', 'Q03')] + [(p, f'{p}_DECK', 'MESH') for p in ('P01', 'P02', 'P03')]
        req += [('B01', 'B01_MOUND', 'MESH'), ('L01', 'L01_TOWER', 'MESH'), ('L01', 'L01_ROTOR', 'EMPTY|MESH'),
                ('C01', 'C01_HOUSE', 'MESH'), ('C02', 'C02_HOUSE', 'MESH'), ('C03', 'C03_LEG_1', 'MESH'), ('C03', 'C03_LEG_2', 'MESH'),
                ('D01', 'D01_BASIN', 'MESH'), ('SITE', 'SITE_WATER', 'MESH')]
        for w in ('W01', 'W02', 'W03', 'W04'):
            req += [(w, f'{w}_BODY', 'MESH'), (w, f'{w}_ROOF', 'MESH')]
        for c, n, t in req:
            o = S.ob(n)
            if not o:
                e.append(f'{n} missing')
            elif o.get('type') not in t.split('|'):
                e.append(f'{n} type {o.get("type")}')
            elif n not in S.coll(c):
                e.append(f'{n} not in {c}')
        return bad('; '.join(e[:10]) + (f' (+{len(e)-10})' if len(e) > 10 else '')) if e else ok(f'{len(req)} primary objects OK')
    guard('B03', b03)

    def b04():
        bb = g.bbox('SITE_WATER')
        if not bb:
            return bad('SITE_WATER missing')
        if abs(bb[1][2]) > 0.05:
            return bad(f'water top z {bb[1][2]:.3f}')
        pts = [(b['mark_x'], b['mark_y']) for b in K['berths']] + [tuple(K['interfaces']['I3_lighthouse_on_head']['center_xy'])]
        out_ = [p for p in pts if not (bb[0][0] <= p[0] <= bb[1][0] and bb[0][1] <= p[1] <= bb[1][1])]
        return bad(f'not covering {out_}') if out_ else ok(f'top z {bb[1][2]:.3f}; covers all marks + head')
    guard('B04', b04)

    def b05():
        sc = S.data.get('scene') or {}
        v = (sc.get('frame_start'), sc.get('frame_end'), sc.get('fps'), sc.get('fps_base'))
        return ok(str(v)) if v[0] == 1 and v[1] == 240 and v[2] == 24 and abs(float(v[3] or 0) - 1.0) < 1e-6 else bad(f'start/end/fps/fps_base={v}')
    guard('B05', b05)

    # ---- zones (dimensions)
    def zone_dims(z):
        e = []
        for uid in ZONES[z]['units']:
            if not S.has_coll(uid) or not g.meshes(uid):
                e.append(f'{uid} missing'); continue
            t = U[uid]['type']
            try:
                if t == 'ship':
                    e += m_ship(g, uid)[0]
                elif t == 'quay':
                    e += m_quay(g, uid, coping=(uid != 'Q02'))
                elif t == 'pier':
                    e += m_pier(g, uid)
                elif t == 'treadwheel_crane':
                    e += m_crane(g, uid)
                elif t == 'sheer_legs':
                    e += m_sheer(g)
                elif t == 'warehouse':
                    e += m_wh(g, uid)
                elif t == 'dry_dock':
                    e += m_dock(g)
                elif t == 'breakwater':
                    e += m_bw(g)
                elif t == 'lighthouse':
                    e += m_lh(g)
            except Exception as ex:
                e.append(f'{uid} error {ex}')
        return bad('; '.join(e[:8]) + (f' (+{len(e)-8})' if len(e) > 8 else '')) if e else ok(f'zone {z}: {len(ZONES[z]["units"])} units within tolerance')
    for iid, z in (('M01', 'A'), ('M02', 'B'), ('M03', 'C'), ('M04', 'D'), ('M05', 'E'), ('M06', 'F')):
        guard(iid, lambda z=z: zone_dims(z))

    # ---- zones (discrete)
    def zone_disc(z):
        e = []
        for uid in ZONES[z]['units']:
            if not S.has_coll(uid) or not g.meshes(uid):
                e.append(f'{uid} missing'); continue
            t = U[uid]['type']
            try:
                if t == 'ship':
                    e += ship_discrete_errs(g, uid, skip_rig=(uid == 'S05'))
                elif t == 'quay':
                    e += quay_discrete_errs(g, uid)
                elif t == 'pier':
                    e += pier_discrete_errs(g, uid)
                elif t == 'treadwheel_crane':
                    e += crane_discrete_errs(g, uid)
                elif t == 'sheer_legs':
                    e += sheer_discrete_errs(g)
                elif t == 'warehouse':
                    e += wh_discrete_errs(g, uid)
                elif t == 'dry_dock':
                    e += dock_discrete_errs(g)
                elif t == 'breakwater':
                    me = bw_meas(g) or {}
                    if me.get('segments') != U['B01']['segments']:
                        e.append(f'B01 parapet segments {me.get("segments")}')
                    if me.get('parapet_side') != U['B01']['parapet_side']:
                        e.append(f'B01 parapet side {me.get("parapet_side")}')
                elif t == 'lighthouse':
                    e += lh_discrete_errs(g)
            except Exception as ex:
                e.append(f'{uid} error {ex}')
        return bad('; '.join(e[:8]) + (f' (+{len(e)-8})' if len(e) > 8 else '')) if e else ok(f'zone {z}: discrete features exact')
    for iid, z in (('G01', 'A'), ('G02', 'B'), ('G03', 'C'), ('G04', 'D'), ('G05', 'E'), ('G06', 'F')):
        guard(iid, lambda z=z: zone_disc(z))

    # ---- fleet draft
    def m07():
        e = []
        for s in SHIPS:
            m = g.mw(f'{s}_ROOT'); hb = g.bbox(f'{s}_HULL')
            if not m or not hb:
                e.append(f'{s} missing'); continue
            if abs(m[2][3]) > 0.05:
                e.append(f'{s} ROOT z {m[2][3]:.3f}')
            if not L(hb[0][2], U[s]['keel_z_m']):
                e.append(f'{s} keel z {hb[0][2]:.2f} vs {U[s]["keel_z_m"]}')
        return bad('; '.join(e)) if e else ok('10 ships: ROOT z=0, keel at -T')
    guard('M07', m07)

    def m08():
        e = [x for x in (roll_check(S, s, U[s]['roll_period_s']) for s in SHIPS) if x]
        return bad('; '.join(e[:5])) if e else ok('10 ships roll 2° sinusoid at Tr, upright at f1')
    guard('M08', m08)

    rot = {}

    def m09():
        rot.update(rotor_meas(S, g))
        if rot.get('n', 0) < 60:
            return bad(f'L01_ROTOR not animated/sampled ({rot.get("n")} frames)')
        e = []
        cxy = K['interfaces']['I3_lighthouse_on_head']['center_xy']
        if math.hypot(rot['xy'][0] - cxy[0], rot['xy'][1] - cxy[1]) > TOL_POS:
            e.append(f'rotor xy {rot["xy"]}')
        if not rot['monotone_ccw']:
            e.append('not monotone CCW')
        if rot['cv'] > 0.05:
            e.append(f'non-uniform (cv {rot["cv"]:.3f})')
        if rot.get('az1') is None or adiff(rot['az1'], U['L01']['beam1_azimuth_deg']) > 3:
            e.append(f'frame-1 +X azimuth {fmt(rot.get("az1"))}')
        me = lh_meas(g) or {}
        bn = me.get('beam_names') or []
        if len(bn) != 2:
            e.append(f'beams parented to rotor: {len(bn)}')
        else:
            rm = g.mw('L01_ROTOR'); t = [rm[0][3], rm[1][3]]
            az = [azim([(g.bbox(n)[0][0] + g.bbox(n)[1][0]) / 2 - t[0], (g.bbox(n)[0][1] + g.bbox(n)[1][1]) / 2 - t[1]]) for n in bn]
            if abs(adiff(az[0], az[1]) - 180) > 3:
                e.append(f'beam separation {adiff(az[0], az[1]):.1f}°')
        return bad('; '.join(e)) if e else ok(f'CCW uniform, f1 az {rot["az1"]:.1f}°, 2 beams 180° apart')
    guard('M09', m09)

    def g10():
        if not rot:
            rot.update(rotor_meas(S, g))
        w = rot.get('omega_fit')
        if not w:
            return bad('rotor not animated')
        T = 360.0 / abs(w) / 24.0
        return ok(f'period {T:.3f}s') if abs(T - U['L01']['period_s']) <= 0.02 * U['L01']['period_s'] else bad(f'period {T:.3f}s vs {U["L01"]["period_s"]}')
    guard('G10', g10)

    # ---- manifest consistency
    def m10():
        if not mand:
            return bad('manifest unusable (see B08)')
        e = []
        for uid, u in U.items():
            ps = (mand.get(uid) or {}).get('params') or {}
            t = u['type']; meas = {}
            if t == 'ship':
                d = ship_discrete(g, uid)
                meas = {k: d.get(k) for k in ('masts', 'yards_per_mast', 'gaff_masts', 'jibs', 'ports_per_side', 'gun_decks', 'berth')}
            elif t == 'quay':
                meas = {'bollards': len(g.names(uid, rf'^{uid}_BOLLARD_\d+$')), 'stairs': len(g.names(uid, rf'^{uid}_STAIR_\d+$'))}
            elif t == 'pier':
                pm = pier_meas(g, uid) or {}
                meas = {'bents': pm.get('bents'), 'piles': pm.get('piles')}
            elif t == 'warehouse':
                wm = wh_meas(g, uid) or {}
                meas = {k: wm.get(k) for k in ('bays', 'floors', 'hoists')}
            elif t == 'dry_dock':
                dm = dock_meas(g) or {}
                meas = {'altars': dm.get('altars'), 'keel_blocks': dm.get('keel_blocks')}
            elif t == 'lighthouse':
                lm = lh_meas(g) or {}
                meas = {'red_bands': lm.get('bands'), 'windows': lm.get('windows'), 'beams': lm.get('beams')}
            elif t == 'treadwheel_crane':
                meas = {'wheels': len(g.names(uid, rf'^{uid}_WHEEL_\d+$'))}
            elif t == 'sheer_legs':
                meas = {'backstays': len(g.names(uid, r'^C03_BACKSTAY_\d+$'))}
            for k, v in meas.items():
                dv = ps.get(k)
                if k == 'gaff_masts' and isinstance(dv, list):
                    dv = sorted(dv)
                if v is None or dv != v:
                    e.append(f'{uid}.{k}: manifest {dv} vs scene {v}')
        return bad('; '.join(e[:8]) + (f' (+{len(e)-8})' if len(e) > 8 else '')) if e else ok('manifest discrete params match scene counts')
    guard('M10', m10)

    # ---- change order
    def g07():
        e = []
        for s in ('S03', 'S07'):
            m = g.mw(f'{s}_ROOT')
            if not m:
                e.append(f'{s} missing'); continue
            want = K['interfaces']['I1_berthing'][s]
            d = math.hypot(m[0][3] - want['root_xy'][0], m[1][3] - want['root_xy'][1])
            h = azim(mat_cols(m)[0][0])
            if d > 2.0 or adiff(h, want['heading_deg']) > 5:
                e.append(f'{s} off {d:.2f} m, heading {h:.1f} vs {want["heading_deg"]} ({want["berth"]})')
        return bad('; '.join(e)) if e else ok('S03→BT10, S07→BT06')
    guard('G07', g07)

    def g08():
        e = []
        y1 = len(g.names('S05', r'^S05_YARD_1_\d+$')); y2 = len(g.names('S05', r'^S05_YARD_2_\d+$'))
        j = len(g.names('S05', r'^S05_JIB_\d+$'))
        if y1 != 3: e.append(f'fore yards {y1}')
        if y2 != 0: e.append(f'main yards {y2}')
        if not g.exists('S05_GAFF_2'): e.append('S05_GAFF_2 missing')
        if g.exists('S05_GAFF_1'): e.append('S05_GAFF_1 present')
        if j != 3: e.append(f'jibs {j}')
        me = [x for x in m_ship(g, 'S05')[0] if 'MAST' in x]
        e += me
        return bad('; '.join(e)) if e else ok('S05 brigantine: 3/0 yards, GAFF_2, 3 jibs')
    guard('G08', g08)

    def g09():
        e = []
        q = quay_coping(g, 'Q02'); d = g.bbox('P01_DECK')
        cb = [g.bbox(n) for n in ['C01_HOUSE'] + g.names('C01', r'^C01_WHEEL_\d+$') if g.bbox(n)]
        want = U['Q02']['coping_m']
        if q is None or abs(q - want) > TOL_FLUSH: e.append(f'Q02 coping {fmt(q)}')
        if not d or abs(d[1][2] - want) > TOL_FLUSH: e.append(f'P01 deck top {fmt(d[1][2] if d else None)}')
        cz = min(b[0][2] for b in cb) if cb else None
        if cz is None or abs(cz - want) > TOL_FLUSH: e.append(f'C01 base {fmt(cz)}')
        return bad('; '.join(e)) if e else ok(f'Q02/P01/C01 at {want:+.2f}')
    guard('G09', g09)

    # ---- integration
    def g11():
        e = []
        Bd = {b['berth']: b for b in K['berths']}
        shipobjs = {}
        for s in SHIPS:
            want = K['interfaces']['I1_berthing'][s]
            m = g.mw(f'{s}_ROOT'); hv = g.verts(f'{s}_HULL')
            if not m or not hv:
                e.append(f'{s} missing'); continue
            d = math.hypot(m[0][3] - want['root_xy'][0], m[1][3] - want['root_xy'][1])
            h = azim(mat_cols(m)[0][0])
            if d > TOL_POS: e.append(f'{s} pos off {d:.2f}')
            if adiff(h, want['heading_deg']) > 2: e.append(f'{s} heading {h:.1f}')
            b = Bd[want['berth']]
            gap = min((p[0] - b['fender_x1']) * b['water_nx'] + (p[1] - b['fender_y1']) * b['water_ny'] for p in hv)
            if abs(gap - 1.5) > 0.3: e.append(f'{s} gap {gap:.2f}')
            shipobjs[s] = [(n, g.bbox(n)) for n in g.meshes(s) if g.bbox(n)]
        others = [(n, g.bbox(n)) for n in ('Q01_WALL', 'Q02_WALL', 'Q03_WALL') if g.bbox(n)]
        for p in ('P01', 'P02', 'P03'):  # pier decks as sub-boxes (T-shaped P03 would give a false AABB clash)
            dv = g.verts(f'{p}_DECK'); u = U[p]
            if not dv:
                continue
            parts = [[v for v in dv if abs(v[0] - u['root_x']) <= u['width_m'] / 2 + 0.3]]
            if 'head_width_m' in u:
                parts.append([v for v in dv if v[1] <= -(u['length_m'] + 1.0 - u['head_length_m']) + 0.3])
            for k, pv in enumerate(parts):
                if pv:
                    others.append((f'{p}_DECK[{k}]', [[min(v[i] for v in pv) for i in range(3)], [max(v[i] for v in pv) for i in range(3)]]))
        ss = list(shipobjs)
        for i, a in enumerate(ss):
            for na, ba in shipobjs[a]:
                for nb, bb in others:
                    if aabb_hit(ba, bb):
                        e.append(f'{na} x {nb}'); break
            for bsid in ss[i + 1:]:
                hit = next(((na, nb) for na, ba in shipobjs[a] for nb, bb in shipobjs[bsid] if aabb_hit(ba, bb)), None)
                if hit:
                    e.append(f'{hit[0]} x {hit[1]}')
        return bad('; '.join(e[:8]) + (f' (+{len(e)-8})' if len(e) > 8 else '')) if e else ok('10 ships berthed: pos/heading/gap OK, no clashes')
    guard('G11', g11)

    def g12():
        e = []
        for p in ('P01', 'P02', 'P03'):
            me = pier_meas(g, p)
            if not me:
                e.append(f'{p} missing'); continue
            if abs(me['ymax']) > 0.15: e.append(f'{p} root gap {me["ymax"]:.3f}')
            if me.get('axis_err') is None or me['axis_err'] > 1.0 or me['ext_y'] <= me['ext_x']:
                e.append(f'{p} axis err {fmt(me.get("axis_err"))}')
            q = quay_coping(g, U[p]['host_quay'])
            if q is None or abs(me['ztop'] - q) > TOL_FLUSH: e.append(f'{p} deck {me["ztop"]:.3f} vs {U[p]["host_quay"]} {fmt(q)}')
        return bad('; '.join(e)) if e else ok('3 piers abut faces, flush with host copings')
    guard('G12', g12)

    def g13():
        me = lh_meas(g); vs = g.verts('B01_MOUND')
        if not me or not vs:
            return bad('L01_TOWER or B01_MOUND missing')
        tv = g.verts('L01_TOWER'); z0 = me['base']
        sl = [p for p in tv if p[2] < z0 + 0.3]
        c = (sum(p[0] for p in sl) / len(sl), sum(p[1] for p in sl) / len(sl))
        cxy = K['interfaces']['I3_lighthouse_on_head']['center_xy']
        e = []
        if math.hypot(c[0] - cxy[0], c[1] - cxy[1]) > TOL_POS: e.append(f'tower centre {c[0]:.2f},{c[1]:.2f}')
        near = [p[2] for p in vs if math.hypot(p[0] - cxy[0], p[1] - cxy[1]) <= 3.0]
        if not near:  # low-poly roundhead cap without a centre vertex: use the head disc rim
            near = [p[2] for p in vs if math.hypot(p[0] - cxy[0], p[1] - cxy[1]) <= U['B01']['head_radius_m'] + 0.5]
        top = max(near) if near else None
        if top is None or abs(top - z0) > TOL_FLUSH: e.append(f'tower base {z0:.3f} vs head top {fmt(top)}')
        return bad('; '.join(e)) if e else ok('L01 centred and seated on B01 head')
    guard('G13', g13)
    return R


GATE_MIN_UNITS = 13  # half of the 26 unit collections


def postprocess(results, ctx):
    items = ctx['items']
    if '_checks_error' in results:
        return results  # checks.py crashed: keep the 'error' verdicts so that no reward is written
    # v0.2: the whole-task gate fires only when scene.blend is missing / cannot be opened / exported; a units-only
    # B01 failure (not METRIC or scale != 1) costs B01 alone.
    if not ctx.get('_w10_scene_ok'):
        for it in items:
            if it['id'] != 'B01':
                results[it['id']] = {'verdict': 'fail', 'detail': 'gate: B01 failed (scene.blend missing/unopenable)', 'source': 'gate'}
        return results
    # v0.2: the B02 group gate means "no collection contract": fewer than 13 of the 26 unit collections exist.
    # Any other B02 failure (one unit missing, a shared mesh) costs B02 itself; the zone/fleet/... items that need
    # the missing unit fail on their own measurements.
    n = ctx.get('_w10_nunits', 0)
    if n < GATE_MIN_UNITS:
        grp = lambda it: str(it.get('group', '')).startswith('zone_') or it.get('group') in ('fleet', 'change', 'integration', 'manifest')
        for it in items:
            if grp(it) and it['id'] != 'B02':
                results[it['id']] = {'verdict': 'fail', 'detail': f'gate: no collection contract ({n}/26 unit collections < {GATE_MIN_UNITS})', 'source': 'gate'}
    return results
