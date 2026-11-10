# -*- coding: utf-8 -*-
"""BLD-W01 Axial Palace Compound - deterministic checks.

Covers B01-B04, B06, B07, M01-M11, G01-G13 fully; B05 only its file part (missing / not 1920x1080 /
blank -> fail; otherwise left to the VLM veto). G14 (blind visual review) is left to the judge.
One Blender extraction (_bld_extract.py) with an extra_py block that computes:
  roofs        : per roof object - zmin/zmax, top-band vertices, vertical-plane clusters (axis/coord/sign/area)
  ql_rays      : per bridge - horizontal +X rays at z=-0.5 and z=+0.3 every 0.25 m over the bridge's Y extent
  site_rays    : SITE-only vertical rays at (+-30, 22/30/38), every surface crossed (list of z)
  lw_prof      : per corridor roof_1 - transverse profiles z(lateral) at 30/50/70 % of every segment
  lw05_old_route_verts : LW05 vertices inside x[30,32] y[215,235]
All geometry is the evaluated mesh (modifiers / geometry nodes / curves) plus instanced geometry of the object
(2026-10-25 cleanup; see review/rubric-cleanup-20261025.md).
All truth values come from answer-key.json units_final (change order CO-01 applied).
"""
import json, math, re, pathlib, traceback
from _bld_lib import Scene, ok, bad, close, png_size, load_manifest, gate_group

POS = 0.5
GEOM = ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')
SCENE_ITEMS = ['B01', 'B02', 'B03', 'B04'] + ['M%02d' % i for i in range(1, 12)] + ['G%02d' % i for i in range(1, 14)]

EXTRA_PY = r'''
import re, json
from mathutils.bvhtree import BVHTree
# 2026-10-25 real-image fix: Blender 4.3.2 (Debian) runs on the system python3.13 which has no numpy;
# pure-python float64 replacement of the former numpy code (same values, same ordering).

GEO_T = ('MESH', 'CURVE', 'SURFACE', 'FONT', 'META')
LWSEG = json.loads(r"""__LWSEG__""")

def _m4(mw):
    return [[float(mw[i][j]) for j in range(4)] for i in range(4)]

# instanced geometry (collection instances / geometry-nodes instances), keyed by the instancing object
INST = {}
try:
    for oi in dg.object_instances:
        if not oi.is_instance or oi.parent is None or oi.object is None or oi.object.type not in GEO_T:
            continue
        INST.setdefault(oi.parent.original.name, []).append((oi.object.original.name, _m4(oi.matrix_world)))
except Exception as e:
    EXTRA['instances_error'] = str(e)[:300]

_LOCAL = {}

def _local(name):
    """evaluated mesh of object `name` in local coords -> (co list of (x,y,z), tris list of (i,j,k)); cached."""
    if name in _LOCAL:
        return _LOCAL[name]
    ob = bpy.data.objects.get(name)
    res = ([], [])
    if ob is not None and ob.type in GEO_T:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        try:
            if me is not None:
                n = len(me.vertices)
                fl = [0.0] * (n * 3)
                if n:
                    me.vertices.foreach_get('co', fl)
                me.calc_loop_triangles()
                t = len(me.loop_triangles)
                ix = [0] * (t * 3)
                if t:
                    me.loop_triangles.foreach_get('vertices', ix)
                res = (list(zip(fl[0::3], fl[1::3], fl[2::3])), list(zip(ix[0::3], ix[1::3], ix[2::3])))
        finally:
            ev.to_mesh_clear()
    _LOCAL[name] = res
    return res

def _xf(co, M):
    (a, b, c, d), (e, f, g, h), (i, j, k, l) = M[0], M[1], M[2]
    return [(a * x + b * y + c * z + d, e * x + f * y + g * z + h, i * x + j * y + k * z + l) for x, y, z in co]

def _npw(ob):
    """world-space evaluated geometry of `ob` incl. geometry it instances -> (co, tris)."""
    parts = []
    if ob.type in GEO_T:
        co, idx = _local(ob.name)
        parts.append((co, idx, _m4(ob.evaluated_get(dg).matrix_world)))
    for src, M in INST.get(ob.name, [])[:20000]:
        co, idx = _local(src)
        parts.append((co, idx, M))
    C, T, off = [], [], 0
    for co, idx, M in parts:
        if not len(co):
            continue
        C.extend(_xf(co, M)); T.extend((p + off, q + off, r + off) for p, q, r in idx); off += len(co)
    return C, T

def _geo(ob):
    return ob.type in GEO_T or ob.name in INST

def _rnd(x):  # numpy.round (half to even) == python round on floats
    return int(round(x))

RX = re.compile(r'^(DN|MN|PD|TT|LW)\d\d_roof_\d+$')
R = {}
for ob in scene.objects:
    if not _geo(ob) or not RX.match(ob.name):
        continue
    try:
        co, idx = _npw(ob)
        if len(co) == 0:
            R[ob.name] = {'n': 0}
            continue
        z0 = min(v[2] for v in co); z1 = max(v[2] for v in co)
        band = [v for v in co if v[2] >= z1 - 0.3]
        if len(band) > 3000:
            L = len(band); step = (L - 1) / 2999.0
            band = [band[int(q * step)] for q in range(2999)] + [band[L - 1]]
        planes = []
        if len(idx):
            acc = {}
            for p, q, r in idx:
                A_, B_, C_ = co[p], co[q], co[r]
                ux, uy, uz = B_[0] - A_[0], B_[1] - A_[1], B_[2] - A_[2]
                vx, vy, vz = C_[0] - A_[0], C_[1] - A_[1], C_[2] - A_[2]
                cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
                nn = math.sqrt(cx * cx + cy * cy + cz * cz); ar = nn * 0.5
                if not ar > 1e-9:
                    continue
                cen = ((A_[0] + B_[0] + C_[0]) / 3.0, (A_[1] + B_[1] + C_[1]) / 3.0, (A_[2] + B_[2] + C_[2]) / 3.0)
                if not cen[2] > z0 + 1.0:
                    continue
                cr = (cx, cy)
                for ax in (0, 1):
                    nv = cr[ax] / (2 * ar)
                    if abs(nv) > 0.95:
                        key = _rnd(cen[ax] / 0.1) * 2 + (1 if nv > 0 else 0)
                        s_ = acc.setdefault((ax, key), [0.0, 0.0]); s_[0] += ar; s_[1] += cen[2] * ar
            for ax in (0, 1):
                for k in sorted(kk for (a2, kk) in acc if a2 == ax):
                    A, Z = acc[(ax, k)]
                    if A >= 0.3:
                        planes.append({'axis': ax, 'coord': round((k // 2) * 0.1, 3), 'sign': 1 if k % 2 else -1,
                                       'area': round(float(A), 3), 'zc': round(float(Z / A), 3)})
        planes.sort(key=lambda p: -p['area'])
        R[ob.name] = {'n': int(len(co)), 'zmin': round(z0, 4), 'zmax': round(z1, 4),
                      'top_band': [[round(float(x), 3) for x in v] for v in band], 'planes': planes[:400]}
    except Exception as e:
        R[ob.name] = {'error': str(e)[:300]}
EXTRA['roofs'] = R

def _tree(names):
    V = []; T = []; off = 0; lo = [1e9] * 3; hi = [-1e9] * 3
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is None or not _geo(ob):
            continue
        co, idx = _npw(ob)
        if len(co) == 0 or len(idx) == 0:
            continue
        lo = [min(lo[i], min(v[i] for v in co)) for i in range(3)]
        hi = [max(hi[i], max(v[i] for v in co)) for i in range(3)]
        V.extend(co); T.extend((p + off, q + off, r + off) for p, q, r in idx); off += len(co)
    return (BVHTree.FromPolygons(V, T) if T else None), lo, hi

# bridges: horizontal +X rays at two heights (z=-0.5 inside the river, z=+0.3 just above the banks), every 0.25 m
# along Y over the whole bridge extent; arch openings = miss runs bounded by hits on both sides (counted in checks).
Q = {}
for col in bpy.data.collections:
    if not re.match(r'^QL\d\d$', col.name):
        continue
    try:
        tree, lo, hi = _tree([o.name for o in col.all_objects])
        if tree is None:
            Q[col.name] = {'hits_by_z': None}
            continue
        y0 = lo[1] + 0.125
        ny = max(0, min(400, int((hi[1] - y0) / 0.25) + 1))
        hz = {}
        for zr in (-0.5, 0.3):
            hits = []
            for i in range(ny):
                y = y0 + 0.25 * i
                loc = tree.ray_cast(Vector((lo[0] - 5, y, zr)), Vector((1, 0, 0)), (hi[0] - lo[0]) + 10)[0]
                hits.append(loc is not None)
            hz[str(zr)] = hits
        Q[col.name] = {'y0': round(y0, 4), 'dy': 0.25, 'hits_by_z': hz}
    except Exception as e:
        Q[col.name] = {'error': str(e)[:300]}
EXTRA['ql_rays'] = Q

# SITE: every surface crossed by a downward ray (water planes above the bed are allowed)
SR = {}
try:
    col = bpy.data.collections.get('SITE')
    tree = _tree([o.name for o in col.all_objects])[0] if col else None
    for x in (30, -30):
        for y in (22, 30, 38):
            zs = []
            if tree:
                o = Vector((x, y, 200.0))
                for _ in range(30):
                    loc = tree.ray_cast(o, Vector((0, 0, -1)), 400.0)[0]
                    if loc is None:
                        break
                    zs.append(round(loc.z, 4))
                    o = Vector((x, y, loc.z - 1e-3))
            SR['%d,%d' % (x, y)] = zs
except Exception as e:
    SR['error'] = str(e)[:300]
EXTRA['site_rays'] = SR

# corridor roofs: transverse profile z(lateral) by vertical rays at 30/50/70 % of every segment
LP = {}
for uid, spec in LWSEG.items():
    ob = bpy.data.objects.get(uid + '_roof_1')
    if ob is None or not _geo(ob):
        continue
    try:
        tree, lo, hi = _tree([ob.name])
        if tree is None:
            LP[uid] = {'error': 'no roof geometry'}
            continue
        w = spec['w']; half = w / 2 + 1.5; nl = int(round(2 * half / 0.05))
        segs = []
        for s in spec['segs']:
            al = s['al']; lt = 1 - al
            sts = []
            for f in (0.3, 0.5, 0.7):
                pa = s['a0'] + (s['a1'] - s['a0']) * f
                prof = []
                for k in range(nl + 1):
                    off = -half + 0.05 * k
                    p = [0.0, 0.0]; p[al] = pa; p[lt] = s['lat'] + off
                    loc = tree.ray_cast(Vector((p[0], p[1], hi[2] + 5)), Vector((0, 0, -1)), hi[2] - lo[2] + 10)[0]
                    prof.append([round(off, 3), round(loc.z, 4) if loc is not None else None])
                sts.append(prof)
            segs.append(sts)
        LP[uid] = {'segs': segs}
    except Exception as e:
        LP[uid] = {'error': str(e)[:300]}
EXTRA['lw_prof'] = LP

try:
    col = bpy.data.collections.get('LW05'); cnt = 0
    if col:
        for o in col.all_objects:
            if _geo(o):
                co = _npw(o)[0]
                if len(co):
                    cnt += sum(1 for v in co if 30 <= v[0] <= 32 and 215 <= v[1] <= 235)
    EXTRA['lw05_old_route_verts'] = cnt if col else None
except Exception as e:
    EXTRA['lw05_old_route_verts_error'] = str(e)[:300]
'''


def lw_spec(U):
    """corridor segment geometry passed into EXTRA_PY (from answer-key units_final)."""
    out = {}
    for uid, u in U.items():
        if u.get('type') != 'LW':
            continue
        segs = []
        for s in u['segments']:
            al = 0 if s['direction'] in ('E', 'W') else 1
            segs.append({'al': al, 'a0': s['start'][al], 'a1': s['end'][al], 'lat': s['start'][1 - al]})
        out[uid] = {'w': u['width_m'], 'segs': segs}
    return out

VERTS_RE = r'^(RG\d\d_(dial|gnomon|vessel)|DL\d\d_body|QL\d\d_deck|LW\d\d_(platform_1|wall_\d+))$'

# ---------------------------------------------------------------- helpers

def cluster(vals, gap=0.3):
    v = sorted(vals)
    if not v:
        return []
    out = [[v[0]]]
    for x in v[1:]:
        if x - out[-1][-1] > gap:
            out.append([x])
        else:
            out[-1].append(x)
    return out


def axes(u):
    """(frontage axis idx, depth axis idx, front at max(+1)/min(-1) of depth axis)."""
    f = u.get('facing', 'S')
    return {'S': (0, 1, -1), 'N': (0, 1, 1), 'W': (1, 0, -1), 'E': (1, 0, 1)}.get(f, (0, 1, -1))


def eig3(C):
    """Jacobi eigen-decomposition of symmetric 3x3 -> (vals, vecs as columns list)."""
    A = [row[:] for row in C]
    V = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for _ in range(60):
        p, q, mx = 0, 1, 0.0
        for i in range(3):
            for j in range(i + 1, 3):
                if abs(A[i][j]) > mx:
                    p, q, mx = i, j, abs(A[i][j])
        if mx < 1e-14:
            break
        th = 0.5 * math.atan2(2 * A[p][q], A[q][q] - A[p][p])
        c, s = math.cos(th), math.sin(th)
        for k in range(3):
            akp, akq = A[k][p], A[k][q]
            A[k][p], A[k][q] = c * akp - s * akq, s * akp + c * akq
        for k in range(3):
            apk, aqk = A[p][k], A[q][k]
            A[p][k], A[q][k] = c * apk - s * aqk, s * apk + c * aqk
        for k in range(3):
            vkp, vkq = V[k][p], V[k][q]
            V[k][p], V[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    vals = [A[i][i] for i in range(3)]
    vecs = [[V[k][i] for k in range(3)] for i in range(3)]
    return vals, vecs


def pca(pts):
    n = len(pts)
    if n < 4:
        return None
    m = [sum(p[i] for p in pts) / n for i in range(3)]
    C = [[sum((p[i] - m[i]) * (p[j] - m[j]) for p in pts) / n for j in range(3)] for i in range(3)]
    vals, vecs = eig3(C)
    order = sorted(range(3), key=lambda i: vals[i])
    return [vecs[i] for i in order]  # smallest -> largest variance


def hull_area(pts):
    p = sorted(set((round(a, 4), round(b, 4)) for a, b in pts))
    if len(p) < 3:
        return 0.0

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for q in p:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(p):
        while len(up) >= 2 and cr(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    h = lo[:-1] + up[:-1]
    return abs(sum(h[i][0] * h[(i + 1) % len(h)][1] - h[(i + 1) % len(h)][0] * h[i][1] for i in range(len(h)))) / 2


def fill_shape(pts):
    """square if convex-hull area / bbox area > 0.9 else round."""
    if not pts or len(pts) < 3:
        return None, None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ba = (max(xs) - min(xs)) * (max(ys) - min(ys))
    if ba <= 1e-9:
        return None, None
    r = hull_area([(p[0], p[1]) for p in pts]) / ba
    return ('square' if r > 0.9 else 'round'), round(r, 3)


def png_std(p):
    """Grey std of a PNG (PIL if available, else a pure-Python 8-bit decoder). None if undecodable."""
    try:
        from PIL import Image, ImageStat
        im = Image.open(p).convert('L')
        im.thumbnail((480, 270))
        return ImageStat.Stat(im).stddev[0]
    except ImportError:
        pass
    except Exception:
        return None
    try:
        import zlib, struct
        b = open(p, 'rb').read()
        pos, idat, W = 8, b'', None
        while pos < len(b):
            ln = struct.unpack('>I', b[pos:pos + 4])[0]; typ = b[pos + 4:pos + 8]; dat = b[pos + 8:pos + 8 + ln]
            if typ == b'IHDR':
                W, H, bd, ct, _, _, il = struct.unpack('>IIBBBBB', dat)
            elif typ == b'IDAT':
                idat += dat
            pos += 12 + ln
        if bd != 8 or il != 0 or ct not in (0, 2, 4, 6):
            return None
        bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
        raw = zlib.decompress(idat); stride = W * bpp
        prev = bytearray(stride); vals = []
        for y in range(H):
            f = raw[y * (stride + 1)]; line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
            if f == 1:
                for i in range(bpp, stride):
                    line[i] = (line[i] + line[i - bpp]) & 255
            elif f == 2:
                for i in range(stride):
                    line[i] = (line[i] + prev[i]) & 255
            elif f == 3:
                for i in range(stride):
                    line[i] = (line[i] + ((line[i - bpp] if i >= bpp else 0) + prev[i]) // 2) & 255
            elif f == 4:
                for i in range(stride):
                    a = line[i - bpp] if i >= bpp else 0; c = prev[i - bpp] if i >= bpp else 0; bb = prev[i]
                    pa, pb, pc = abs(bb - c), abs(a - c), abs(a + bb - 2 * c)
                    line[i] = (line[i] + (a if pa <= pb and pa <= pc else bb if pb <= pc else c)) & 255
            if y % 8 == 0:
                for x in range(0, W, 8):
                    o = x * bpp
                    vals.append(line[o] if bpp <= 2 else (line[o] + line[o + 1] + line[o + 2]) / 3)
            prev = line
        m = sum(vals) / len(vals)
        return (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
    except Exception:
        return None


# ---------------------------------------------------------------- measurement layer

class Meas:
    def __init__(self, S, A):
        self.S, self.A = S, A
        self.U = A.get('units_final', {})
        self.X = (S.data or {}).get('extra', {}) or {}
        self.IB = {}  # instancer name -> bboxes of the geometry it instances (collection / GN instances)
        for it in (S.data or {}).get('instances') or []:
            if isinstance(it, dict) and it.get('instancer') and it.get('bbox_world') and \
                    it.get('type') in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
                self.IB.setdefault(it['instancer'], []).append(it['bbox_world'])

    # -- object access
    def parts(self, uid, kind):
        return sorted(self.S.objs_in(uid, r'^%s_%s_\d+$' % (re.escape(uid), kind)))

    def one(self, uid, kind):
        n = '%s_%s' % (uid, kind)
        return n if n in self.S.coll(uid) and n in self.S.objects else None

    def bb(self, names):
        if names is None:
            return None
        if isinstance(names, str):
            names = [names]
        names = [n for n in names if n]
        bs = []
        own = self.S.bbox(names)
        if own:
            bs.append(own)
        for n in names:
            bs += self.IB.get(n, [])
        if not bs:
            return None
        return [[min(b[0][i] for b in bs) for i in range(3)], [max(b[1][i] for b in bs) for i in range(3)]]

    def cbb(self, cname):
        """collection bbox incl. instanced geometry of its objects"""
        return self.bb(self.S.coll(cname))

    def ctr(self, name):
        return Scene.center(self.bb(name))

    def zmax(self, names):
        b = self.bb(names)
        return b[1][2] if b else None

    def verts(self, name):
        return (self.S.objects.get(name) or {}).get('verts_world')

    def ext(self, unit_name, kind):
        b = self.bb(unit_name)
        return b

    # -- building discrete measurements
    def building(self, uid):
        u = self.U[uid]
        a, b, fs = axes(u)
        r = {}
        cols = [c for c in (self.ctr(n) for n in self.parts(uid, 'col')) if c]
        r['columns'] = len(cols)
        if cols:
            bv = [c[b] for c in cols]
            e = max(bv) if fs > 0 else min(bv)
            r['bays_front'] = len(cluster([c[a] for c in cols if abs(c[b] - e) <= 0.3])) - 1
            av = [c[a] for c in cols]
            r['bays_depth'] = len(cluster([c[b] for c in cols if abs(c[a] - max(av)) <= 0.3])) - 1
            r['col_a'] = (min(av), max(av))
        r['platform_tiers'] = len(self.parts(uid, 'platform'))
        roofs = self.parts(uid, 'roof')
        r['eaves'] = len(roofs)
        r['dougong'] = len(self.parts(uid, 'dougong')) > 0
        doors = [c for c in (self.ctr(n) for n in self.parts(uid, 'door')) if c]
        r['door_bays'] = len(doors)
        r['door_a'] = [d[a] for d in doors]
        r['roof'], r['roof_why'] = self.roof_form(uid, u, roofs, r)
        r['platform_top'] = self.zmax(self.parts(uid, 'platform'))
        r['ridge_top'] = self.zmax(roofs)
        return r

    def roof_feat(self, name):
        return (self.X.get('roofs') or {}).get(name)

    def roof_form(self, uid, u, roofs, r):
        if not roofs:
            return None, 'no roof object'
        top = max(roofs, key=lambda n: (self.zmax(n) if self.zmax(n) is not None else -1e9))
        f = self.roof_feat(top)
        rb = self.bb(top)
        if not f or 'top_band' not in f or not rb:
            return None, 'no roof features for %s' % top
        a, b, _ = axes(u)
        zt = f['zmax']
        tc = [v for v in f['top_band'] if v[2] >= zt - 0.1]
        if tc:
            span = math.hypot(max(v[0] for v in tc) - min(v[0] for v in tc), max(v[1] for v in tc) - min(v[1] for v in tc))
            # a finial (宝顶, drawn 0.9 m) belongs to the roof, so the apex cluster may be up to 10 % of the platform
            lim = max(0.6, 0.1 * min(u.get('footprint_front_m') or 0, u.get('footprint_depth_m') or 0))
            if span < lim:
                return 'cuanjian', 'top cluster span %.2f < %.2f' % (span, lim)
        lo, hi = rb[0][a], rb[1][a]
        planes = merge_planes(f.get('planes', []))
        gab = [p for p in planes if p['axis'] == a and p['area'] > 2 and lo + 0.3 < p['coord'] < hi - 0.3]
        if gab:
            return 'xieshan', 'inset gable plane area %.1f at %.2f' % (gab[0]['area'], gab[0]['coord'])
        rid = [v[a] for v in f['top_band'] if v[2] >= zt - 0.3]
        ridge = (max(rid) - min(rid)) if rid else 0.0
        span_a = (r['col_a'][1] - r['col_a'][0]) if r.get('col_a') else u.get('col_span_front_m') or 0
        bigv = [p for p in planes if p['area'] > 2]
        if ridge < 0.8 * span_a and not bigv:
            return 'wudian', 'ridge %.2f < 0.8*%.2f' % (ridge, span_a)
        walls = self.parts(uid, 'wall')
        wb = self.bb(walls) if walls else None
        if wb:
            wlo, whi = wb[0][a], wb[1][a]
        elif r.get('col_a'):
            wlo, whi = r['col_a'][0] - 0.5, r['col_a'][1] + 0.5
        else:
            return None, 'no wall/column reference for overhang'
        ov = min(hi - whi, wlo - lo)
        if ov >= 0.3:
            return 'xuanshan', 'overhang %.2f' % ov
        if ov <= 0.15:
            return 'yingshan', 'overhang %.2f' % ov
        return None, 'ambiguous overhang %.2f (ridge %.2f)' % (ov, ridge)

    # -- corridor
    def seg_axes(self, s):
        al = 0 if s['direction'] in ('E', 'W') else 1
        return al, 1 - al

    def corridor(self, uid):
        u = self.U[uid]
        w = u['width_m']
        r = {'segments': []}
        cols = [c for c in (self.ctr(n) for n in self.parts(uid, 'col')) if c]
        for s in u['segments']:
            al, lt = self.seg_axes(s)
            s0, s1 = sorted([s['start'][al], s['end'][al]])
            sl = s['start'][lt]
            row = [c[al] for c in cols if abs(abs(c[lt] - sl) - w / 2) <= 0.5 and s0 - 0.3 <= c[al] <= s1 + 0.3]
            r['segments'].append({'bays': len(cluster(row)) - 1 if row else 0})
        walls = self.parts(uid, 'wall')
        r['gallery'] = 'single' if walls else 'double'
        r['roof'], r['roof_why'] = self.lw_roof(uid, u)
        r['platform_top'] = self.zmax(self.parts(uid, 'platform'))
        r['ridge_top'] = self.zmax(self.one(uid, 'roof_1'))
        # wall sides: straight wall objects (thin bbox) are assigned to a segment by axis + overlap;
        # combined (L-shaped) wall objects are judged from their vertices (required side only).
        straight, combined = [], []
        for n in walls:
            bb = self.bb(n)
            if not bb:
                continue
            sz = Scene.size(bb)
            if min(sz[0], sz[1]) <= 1.5:
                thin = 0 if sz[0] <= sz[1] else 1
                straight.append((thin, (bb[0][thin] + bb[1][thin]) / 2, bb[0][1 - thin], bb[1][1 - thin]))
            else:
                combined += (self.verts(n) or corners_of(bb))
        side_ok, why = True, []
        sv = {'N': (1, 1), 'S': (1, -1), 'E': (0, 1), 'W': (0, -1)}
        for i, s in enumerate(u['segments']):
            al, lt = self.seg_axes(s)
            s0, s1 = sorted([s['start'][al], s['end'][al]])
            sl = s['start'][lt]
            req = [sv[x][1] for x in u['wall_sides'] if sv[x][0] == lt]
            mine = [(c - sl) for th, c, a0, a1 in straight
                    if th == lt and min(a1, s1) - max(a0, s0) >= min(1.0, 0.5 * (s1 - s0)) and abs(c - sl) <= w / 2 + 1.0]
            for sg in (1, -1):
                has = any(sg * d > w / 4 for d in mine)
                if not has and combined and sg in req:
                    has = any(s0 - w <= p[al] <= s1 + w and w / 4 < sg * (p[lt] - sl) <= w / 2 + 1.0 for p in combined)
                if sg in req and not has:
                    side_ok = False
                    why.append('seg%d: no wall on side %+d' % (i + 1, sg))
                if sg not in req and has:
                    side_ok = False
                    why.append('seg%d: unexpected wall on side %+d' % (i + 1, sg))
        r['wall_sides_ok'], r['wall_why'] = side_ok, why
        return r

    def lw_roof(self, uid, u):
        """juanpeng vs jianshan from transverse profiles of roof_1 (EXTRA lw_prof).
        Straight lines are fitted to each slope over |lat| in [0.15w, 0.28w] and [0.28w, 0.45w] and extrapolated to
        the centreline; e = max(extrapolated apex) - crest height (max z within |lat| <= 0.6 m).
        Pointed (jianshan) ridge, incl. a ridge cap / bar on the apex: e <= 0.04; rolled (juanpeng) ridge: e >= 0.07."""
        p = (self.X.get('lw_prof') or {}).get(uid)
        if not p:
            return None, 'no roof_1 profile'
        if 'error' in p:
            return None, 'profile error: %s' % p['error']
        w = u['width_m']
        es = []
        for si, sts in enumerate(p.get('segs') or []):
            ev = []
            for prof in sts:
                e = lw_apex_excess(prof, w)
                if e is not None:
                    ev.append(e)
            if not ev:
                return None, 'seg%d: profile too sparse' % (si + 1)
            es.append(sorted(ev)[len(ev) // 2])
        if len(es) != len(u['segments']):
            return None, 'profiles for %d of %d segments' % (len(es), len(u['segments']))
        txt = 'apex excess per segment %s' % [round(x, 3) for x in es]
        if all(x >= 0.07 for x in es):
            return 'juanpeng', txt
        if all(x <= 0.04 for x in es):
            return 'jianshan', txt
        return None, 'ambiguous/mixed ' + txt

    # -- pavilion
    def pavilion(self, uid):
        u = self.U[uid]
        cols = [c for c in (self.ctr(n) for n in self.parts(uid, 'col')) if c]
        r = {'columns': len(cols), 'eaves': len(self.parts(uid, 'roof')), 'stele': self.one(uid, 'stele') is not None}
        pc = self.ctr(self.one(uid, 'platform_1')) or [u['cx'], u['cy'], 0]
        if len(cols) >= 4:
            rad = [math.hypot(c[0] - pc[0], c[1] - pc[1]) for c in cols]
            m = sum(rad) / len(rad)
            r['plan'] = 'octagon' if (len(cols) >= 6 and max(abs(x - m) for x in rad) <= 0.05 * m) else 'square'
        else:
            r['plan'] = None
        rr = dict(r)
        rr['col_a'] = None
        if cols:
            rr['col_a'] = (min(c[0] for c in cols), max(c[0] for c in cols))
        r['roof'], r['roof_why'] = self.roof_form(uid, u, self.parts(uid, 'roof'), rr)
        r['platform_top'] = self.zmax(self.parts(uid, 'platform'))
        r['ridge_top'] = self.zmax(self.parts(uid, 'roof'))
        return r

    # -- small units
    def bridge(self, uid):
        u = self.U[uid]
        r = {}
        posts = [c for c in (self.ctr(n) for n in self.parts(uid, 'post')) if c]
        db = self.bb(self.one(uid, 'deck'))
        cx = Scene.center(db)[0] if db else u['cx']
        l = sum(1 for p in posts if p[0] < cx); rr = sum(1 for p in posts if p[0] > cx)
        r['posts'] = (l, rr)
        r['posts_per_side'] = l if l == rr else None
        q = (self.X.get('ql_rays') or {}).get(uid) or {}
        hz = q.get('hits_by_z')
        if not isinstance(hz, dict) or not hz:
            r['arches'] = None
        else:
            # openings = miss runs with a hit (bridge body) before and after them; max over the two ray heights
            r['arches_by_z'] = {z: bounded_miss_runs(h) for z, h in hz.items() if isinstance(h, list)}
            r['arches'] = max(r['arches_by_z'].values()) if r['arches_by_z'] else None
        dv = self.verts(self.one(uid, 'deck')) if self.one(uid, 'deck') else None
        cy = Scene.center(db)[1] if db else u['cy']
        if dv:
            near = [v[2] for v in dv if abs(v[1] - u['cy']) <= 0.5]
            r['crown'] = max(near) if near else (db[1][2] if db else None)
        else:
            r['crown'] = db[1][2] if db else None
        r['deck_bb'] = db
        return r

    def lion(self, uid):
        r = {'base_tiers': len(self.parts(uid, 'base'))}
        ball, cub = self.one(uid, 'ball') is not None, self.one(uid, 'cub') is not None
        r['sex'] = 'male' if ball and not cub else 'female' if cub and not ball else None
        hc = self.ctr(self.one(uid, 'head')) if self.one(uid, 'head') else None
        bc = self.ctr(self.one(uid, 'base_1')) if self.one(uid, 'base_1') else None
        r['head_south'] = bool(hc and bc and hc[1] < bc[1] - 0.05)
        r['lion'] = self.one(uid, 'lion') is not None
        r['height'] = self.zmax(self.S.coll(uid))
        r['base_top'] = self.zmax(self.parts(uid, 'base'))
        return r

    def road(self, uid):
        rb = self.bb(self.one(uid, 'road'))
        return {'slabs': len(self.parts(uid, 'slab')), 'curb': len(self.parts(uid, 'curb')) > 0, 'bb': rb,
                'height': rb[1][2] if rb else None}

    def instrument(self, uid):
        u = self.U[uid]
        r = {'base_tiers': len(self.parts(uid, 'base')), 'base_top': self.zmax(self.parts(uid, 'base'))}
        if u.get('kind') == 'sundial':
            dv, gv = self.verts('%s_dial' % uid), self.verts('%s_gnomon' % uid)
            r['dial_ok'], r['dial_why'] = False, 'no dial/gnomon vertices'
            if dv and gv:
                pd, pg = pca(dv), pca(gv)
                if pd and pg:
                    n = pd[0]
                    if n[2] < 0:
                        n = [-x for x in n]
                    elev = math.degrees(math.asin(max(-1, min(1, n[2] / math.sqrt(sum(x * x for x in n))))))
                    g = pg[2]
                    cosang = abs(sum(g[i] * n[i] for i in range(3))) / (math.sqrt(sum(x * x for x in g)) * math.sqrt(sum(x * x for x in n)))
                    ang = math.degrees(math.acos(max(-1, min(1, cosang))))
                    want = 90 - u['dial_tilt_deg']
                    r['dial_tilt'] = round(90 - elev, 2)
                    r['dial_ok'] = abs(elev - want) <= 2 and n[1] > 0 and n[2] > 0 and ang < 5
                    r['dial_why'] = 'normal elev %.1f (want %.1f) n=%s gnomon-normal %.1f deg' % (elev, want, [round(x, 2) for x in n], ang)
        else:
            vv = self.verts('%s_vessel' % uid)
            r['vessel_shape'], r['fill'] = fill_shape(vv) if vv else (None, None)
            r['ears'] = len(self.parts(uid, 'ear'))
        return r

    def vessel(self, uid):
        bv = self.verts('%s_body' % uid)
        sh, fr = fill_shape(bv) if bv else (None, None)
        return {'legs': len(self.parts(uid, 'leg')), 'ears': len(self.parts(uid, 'ear')), 'rings': len(self.parts(uid, 'ring')),
                'body': sh, 'fill': fr, 'height': self.zmax(self.S.coll(uid))}

    def measure(self, uid):
        t = self.U[uid]['type']
        fn = {'DN': self.building, 'MN': self.building, 'PD': self.building, 'LW': self.corridor, 'TT': self.pavilion,
              'QL': self.bridge, 'SS': self.lion, 'YD': self.road, 'RG': self.instrument, 'DL': self.vessel}[t]
        try:
            return fn(uid)
        except Exception as e:
            return {'error': '%s: %s' % (type(e).__name__, e)}


def bounded_miss_runs(hits):
    runs, seen_hit, in_miss = 0, False, False
    for x in hits:
        if x:
            if in_miss and seen_hit:
                runs += 1
            seen_hit, in_miss = True, False
        else:
            in_miss = True
    return runs


def corners_of(bb):
    return [[x, y, z] for x in (bb[0][0], bb[1][0]) for y in (bb[0][1], bb[1][1]) for z in (bb[0][2], bb[1][2])]


def merge_planes(planes):
    out = []
    for ax in (0, 1):
        for sg in (1, -1):
            ps = sorted([p for p in planes if p['axis'] == ax and p['sign'] == sg], key=lambda p: p['coord'])
            cur = None
            for p in ps:
                if cur and p['coord'] - cur['last'] <= 0.15:
                    cur['area'] += p['area']; cur['last'] = p['coord']
                else:
                    if cur:
                        out.append(cur)
                    cur = {'axis': ax, 'sign': sg, 'coord': p['coord'], 'last': p['coord'], 'area': p['area']}
            if cur:
                out.append(cur)
    return out


def _line_at0(pts):
    """least-squares z = a + b*d over [(d, z)], returns a (value at d = 0)"""
    n = len(pts)
    if n < 3:
        return None
    md = sum(p[0] for p in pts) / n; mz = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - md) ** 2 for p in pts)
    if sxx <= 1e-12:
        return None
    b = sum((p[0] - md) * (p[1] - mz) for p in pts) / sxx
    return mz - b * md


def lw_apex_excess(prof, w):
    pts = [(float(l), float(z)) for l, z in (prof or []) if z is not None]
    crest = [z for l, z in pts if abs(l) <= 0.6]
    if not crest:
        return None
    ztop = max(crest)
    best = None
    for r0, r1 in ((0.15, 0.28), (0.28, 0.45)):
        a = []
        for sg in (1, -1):
            v = _line_at0([(abs(l), z) for l, z in pts if sg * l > 0 and r0 * w <= abs(l) <= r1 * w])
            if v is not None:
                a.append(v)
        if len(a) == 2:
            e = sum(a) / 2 - ztop
            best = e if best is None else max(best, e)
    return best


# ---------------------------------------------------------------- placement / discrete comparisons

def placement(M, uid):
    u = M.U[uid]
    t = u['type']
    if t in ('DN', 'MN', 'PD', 'TT'):
        bb = M.bb(M.one(uid, 'platform_1'))
        if not bb:
            return False, '%s_platform_1 missing' % uid
        c, s = Scene.center(bb), Scene.size(bb)
        a, b, _ = axes(u)
        ef, ed = u['footprint_front_m'], u['footprint_depth_m']
        okk = abs(c[0] - u['cx']) <= POS and abs(c[1] - u['cy']) <= POS and close(s[a], ef) and close(s[b], ed)
        return okk, '%s c=(%.2f,%.2f) size a=%.2f b=%.2f want (%s,%s) %sx%s' % (uid, c[0], c[1], s[a], s[b], u['cx'], u['cy'], ef, ed)
    if t == 'LW':
        bb = M.bb(M.one(uid, 'platform_1'))
        if not bb:
            return False, '%s_platform_1 missing' % uid
        hw = u['width_m'] / 2 + 0.6
        segs = u['segments']
        lo, hi = [1e9, 1e9], [-1e9, -1e9]
        for i, s in enumerate(segs):
            al, lt = M.seg_axes(s)
            st, en = s['start'][al], s['end'][al]
            d = 1 if en >= st else -1
            es = hw if i > 0 else 0.0
            ee = hw if i < len(segs) - 1 else 0.0
            a0, a1 = sorted([st - d * es, en + d * ee])
            lo[al] = min(lo[al], a0); hi[al] = max(hi[al], a1)
            lo[lt] = min(lo[lt], s['start'][lt] - hw); hi[lt] = max(hi[lt], s['start'][lt] + hw)
        ec = [(lo[i] + hi[i]) / 2 for i in range(2)]; es_ = [hi[i] - lo[i] for i in range(2)]
        c, s = Scene.center(bb), Scene.size(bb)
        okk = all(abs(c[i] - ec[i]) <= POS for i in range(2)) and all(close(s[i], es_[i]) for i in range(2))
        return okk, '%s c=(%.2f,%.2f) s=(%.2f,%.2f) want c=(%.2f,%.2f) s=(%.2f,%.2f)' % (uid, c[0], c[1], s[0], s[1], ec[0], ec[1], es_[0], es_[1])
    if t == 'QL':
        bb = M.bb(M.one(uid, 'deck'))
        if not bb:
            return False, '%s_deck missing' % uid
        c, s = Scene.center(bb), Scene.size(bb)
        okk = abs(c[0] - u['cx']) <= POS and abs(c[1] - u['cy']) <= POS and close(s[1], u['deck_length_m']) and close(s[0], u['deck_width_m'])
        return okk, '%s c=(%.2f,%.2f) L=%.2f W=%.2f' % (uid, c[0], c[1], s[1], s[0])
    if t == 'YD':
        bb = M.bb(M.one(uid, 'road'))
        if not bb:
            return False, '%s_road missing' % uid
        c, s = Scene.center(bb), Scene.size(bb)
        okk = (abs(c[0] - u['cx']) <= POS and abs(bb[0][1] - u['y_start']) <= POS and abs(bb[1][1] - u['y_end']) <= POS
               and close(s[1], u['length_m']) and close(s[0], u['width_m']))
        return okk, '%s y=[%.2f,%.2f] W=%.2f cx=%.2f' % (uid, bb[0][1], bb[1][1], s[0], c[0])
    bb = M.bb(M.one(uid, 'base_1'))
    if not bb:
        return False, '%s_base_1 missing' % uid
    c = Scene.center(bb)
    okk = abs(c[0] - u['cx']) <= POS and abs(c[1] - u['cy']) <= POS
    return okk, '%s base c=(%.2f,%.2f)' % (uid, c[0], c[1])


def discrete(M, uid, m, with_body=False):
    """Compare measured discrete features with truth; returns list of mismatch strings."""
    u = M.U[uid]
    t = u['type']
    e = []
    if 'error' in m:
        return ['%s measure error %s' % (uid, m['error'])]

    def chk(k, mv, tv):
        if mv != tv:
            e.append('%s.%s=%s want %s' % (uid, k, mv, tv))
    if t in ('DN', 'MN', 'PD'):
        for k in ('bays_front', 'bays_depth', 'platform_tiers', 'eaves', 'dougong', 'door_bays'):
            chk(k, m.get(k), u[k])
        if m.get('roof') != u['roof']:
            e.append('%s.roof=%s want %s (%s)' % (uid, m.get('roof'), u['roof'], m.get('roof_why')))
        a = axes(u)[0]
        cen = u['cx'] if a == 0 else u['cy']
        half = (u['mingjian_m'] + (u['door_bays'] - 1) * u['cijian_m']) / 2 + 0.3
        off = [round(x - cen, 2) for x in m.get('door_a', []) if abs(x - cen) > half]
        if off:
            e.append('%s doors outside central %d bays: %s' % (uid, u['door_bays'], off))
    elif t == 'TT':
        chk('plan', m.get('plan'), u['plan']); chk('columns', m.get('columns'), u['columns'])
        chk('eaves', m.get('eaves'), u['eaves']); chk('stele', m.get('stele'), True)
    elif t == 'LW':
        ms = [s['bays'] for s in m.get('segments', [])]
        chk('segment_bays', ms, [s['bays'] for s in u['segments']])
        chk('gallery', m.get('gallery'), u['gallery'])
        if not m.get('wall_sides_ok'):
            e.append('%s walls %s' % (uid, m.get('wall_why')))
        if m.get('roof') != u['roof']:
            e.append('%s.roof=%s want %s (%s)' % (uid, m.get('roof'), u['roof'], m.get('roof_why')))
    elif t == 'QL':
        if m.get('arches') != u['arches']:
            e.append('%s.arches=%s want %s (by ray height %s)' % (uid, m.get('arches'), u['arches'], m.get('arches_by_z')))
        chk('posts', m.get('posts'), (u['posts_per_side'], u['posts_per_side']))
    elif t == 'SS':
        chk('sex', m.get('sex'), u['sex']); chk('base_tiers', m.get('base_tiers'), u['base_tiers'])
        chk('head_south', m.get('head_south'), True)
    elif t == 'YD':
        chk('slabs', m.get('slabs'), u['slabs']); chk('curb', m.get('curb'), u['curb'])
    elif t == 'RG':
        chk('base_tiers', m.get('base_tiers'), u['base_tiers'])
        if u.get('kind') == 'sundial':
            if not m.get('dial_ok'):
                e.append('%s dial: %s' % (uid, m.get('dial_why')))
        else:
            chk('vessel_shape', m.get('vessel_shape'), u['vessel_shape']); chk('ears', m.get('ears'), u['ears'])
    elif t == 'DL':
        for k in ('legs', 'ears', 'rings'):
            chk(k, m.get(k), u[k])
        if with_body:
            chk('body', m.get('body'), u['body'])
    return e


def vertical(M, uid, m):
    u = M.U[uid]
    t = u['type']
    e = []
    if 'error' in m:
        return ['%s measure error' % uid]
    if t in ('DN', 'MN', 'PD', 'TT', 'LW'):
        pt, rt = m.get('platform_top'), m.get('ridge_top')
        if pt is None or not close(pt, u['platform_top_m'], 0.03, 0.10):
            e.append('%s platform_top=%s want %s' % (uid, pt, u['platform_top_m']))
        if rt is None or not close(rt, u['ridge_top_m'], 0.05, 0.30):
            e.append('%s ridge_top=%s want %s' % (uid, rt, u['ridge_top_m']))
    elif t == 'QL':
        if m.get('crown') is None or not close(m['crown'], u['crown_height_m']):
            e.append('%s crown=%s want %s' % (uid, m.get('crown'), u['crown_height_m']))
    elif t == 'SS':
        if m.get('height') is None or not close(m['height'], u['height_m']):
            e.append('%s height=%s want %s' % (uid, m.get('height'), u['height_m']))
        if m.get('base_top') is None or not close(m['base_top'], u['base_height_m']):
            e.append('%s base=%s want %s' % (uid, m.get('base_top'), u['base_height_m']))
    elif t == 'YD':
        if m.get('height') is None or not close(m['height'], u['height_m']):
            e.append('%s road top=%s want %s' % (uid, m.get('height'), u['height_m']))
    elif t == 'RG':
        if m.get('base_top') is None or not close(m['base_top'], u['base_height_m']):
            e.append('%s base=%s want %s' % (uid, m.get('base_top'), u['base_height_m']))
    elif t == 'DL':
        if m.get('height') is None or not close(m['height'], u['height_m']):
            e.append('%s height=%s want %s' % (uid, m.get('height'), u['height_m']))
    return e


def r3(x):
    return round(x, 3) if isinstance(x, (int, float)) else x


def junction(M, j, lw_name=None):
    lw = j['lw']
    lb = M.bb('%s_platform_1' % lw if ('%s_platform_1' % lw) in M.S.coll(lw) else None)
    ub = M.bb('%s_platform_1' % j['unit'] if ('%s_platform_1' % j['unit']) in M.S.coll(j['unit']) else None)
    if not lb or not ub:
        return False, '%s %s: platform missing' % (lw, j['end'])
    side = j['side']
    if side == 'S':
        al, le, ue, d = 1, lb[1][1], ub[0][1], ub[0][1] - lb[1][1]
    elif side == 'N':
        al, le, ue, d = 1, lb[0][1], ub[1][1], lb[0][1] - ub[1][1]
    elif side == 'E':
        al, le, ue, d = 0, lb[0][0], ub[1][0], lb[0][0] - ub[1][0]
    else:
        al, le, ue, d = 0, lb[1][0], ub[0][0], ub[0][0] - lb[1][0]
    lt = 1 - al
    v = M.verts('%s_platform_1' % lw)
    if not v:
        return False, '%s %s: no platform vertices' % (lw, j['end'])
    near = [p[lt] for p in v if abs(p[al] - le) <= 0.5]
    if not near:
        return False, '%s %s: no verts near end face' % (lw, j['end'])
    lc = (max(near) + min(near)) / 2
    okk = abs(d) <= 0.15 and abs(lc - j['point'][lt]) <= 0.2
    return okk, '%s.%s->%s.%s gap %.3f lateral %.3f (want %.2f)' % (lw, j['end'], j['unit'], side, d, lc, j['point'][lt])


def mirror_ok(M, a, b):
    A, B = M.cbb(a), M.cbb(b)
    if not A or not B:
        return False, '%s/%s bbox missing' % (a, b)
    e = [abs(A[0][0] + B[1][0]), abs(A[1][0] + B[0][0]), abs(A[0][1] - B[0][1]), abs(A[1][1] - B[1][1]),
         abs(A[0][2] - B[0][2]), abs(A[1][2] - B[1][2])]
    return max(e) <= 0.2, '%s~%s max dev %.3f' % (a, b, max(e))


# ---------------------------------------------------------------- run

MAN_FIELDS = {
    'DN': ['bays_front', 'bays_depth', 'platform_tiers', 'platform_top_m', 'roof', 'eaves', 'dougong', 'door_bays', 'ridge_top_m'],
    'TT': ['plan', 'columns', 'roof', 'eaves', 'platform_top_m'],
    'LW': ['segments', 'gallery', 'roof', 'platform_top_m'],
    'QL': ['arches', 'posts_per_side', 'deck_length_m'],
    'SS': ['sex', 'base_tiers', 'height_m'],
    'YD': ['length_m', 'width_m', 'slabs', 'curb'],
    'RG': ['base_tiers'],
    'DL': ['legs', 'ears', 'rings'],
}
MAN_FIELDS['MN'] = MAN_FIELDS['PD'] = MAN_FIELDS['DN']


def safe(res, iid, fn):
    try:
        res[iid] = fn()
    except Exception as e:
        res[iid] = bad('check error: %s: %s' % (type(e).__name__, str(e)[:300]))


def run(ctx):
    res = {}
    out = pathlib.Path(ctx['out'])
    A = ctx.get('answer') or json.loads((pathlib.Path(ctx['tests']) / 'answer-key.json').read_text(encoding='utf-8'))
    U = A['units_final']
    ids = sorted(U)

    # ---- file items (independent of Blender)
    def b05():
        p = out / 'renders' / 'overview.png'
        sz = png_size(p) if p.exists() else None
        if sz != (1920, 1080):
            return bad('overview.png missing or size %s' % (sz,))
        sd = png_std(p)
        if sd is not None and sd <= 8:
            return bad('overview.png blank (std %.2f)' % sd)
        return None  # deterministic part passed -> VLM veto decides
    try:
        v = b05()
        if v is not None:
            res['B05'] = v
    except Exception as e:
        res['B05'] = bad('check error %s' % e)

    def b06():
        msg = []
        for nm in ('axis_south.png', 'east_wing.png'):
            p = out / 'renders' / nm
            sz = png_size(p) if p.exists() else None
            if sz != (1920, 1080):
                msg.append('%s size %s' % (nm, sz)); continue
            sd = png_std(p)
            if sd is not None and sd <= 8:
                msg.append('%s blank std %.2f' % (nm, sd))
        return bad('; '.join(msg)) if msg else ok('both renders 1920x1080, non-blank')
    safe(res, 'B06', b06)

    man = load_manifest(out)

    def b07():
        if not isinstance(man, list):
            return bad('manifest.json missing or not an array')
        if len(man) != 36:
            return bad('manifest has %d entries' % len(man))
        seen, err = set(), []
        for it in man:
            if not isinstance(it, dict) or not {'id', 'collection', 'built', 'params'} <= set(it):
                err.append('entry missing keys: %s' % str(it)[:80]); continue
            uid = it['id']; seen.add(uid)
            if uid not in U:
                err.append('unknown id %s' % uid); continue
            t = U[uid]['type']
            need = list(MAN_FIELDS[t])
            if t == 'RG':
                need.append('dial_tilt_deg' if U[uid].get('kind') == 'sundial' else 'vessel_shape')
            p = it['params'] if isinstance(it['params'], dict) else {}
            miss = [k for k in need if k not in p]
            if miss:
                err.append('%s missing %s' % (uid, miss))
        if set(U) - seen:
            err.append('ids absent: %s' % sorted(set(U) - seen))
        return bad('; '.join(err)[:600]) if err else ok('36 entries with all per-type fields')
    safe(res, 'B07', b07)

    # ---- scene
    S = Scene.load(ctx, frames=None, islands_regex=None, verts_regex=VERTS_RE,
                   extra_py=EXTRA_PY.replace('__LWSEG__', json.dumps(lw_spec(U))))
    blend = out / 'scene.blend'
    if S.err or not blend.exists():
        why = S.err or 'scene.blend missing'
        for i in SCENE_ITEMS:
            res[i] = bad('scene unavailable: %s' % why)
        return res
    M = Meas(S, A)
    meas = {uid: (M.measure(uid) if uid in S._all else {'error': 'collection %s missing' % uid}) for uid in ids}
    ctx['_w01_meas'] = meas

    res['B01'] = ok('extraction ok (Blender %s), %d objects' % (S.data.get('blender_version'), len(S.objects)))

    def b02():
        sc = S.data.get('scene') or {}
        bb = M.cbb('MN01')
        good = sc.get('unit_system') == 'METRIC' and sc.get('length_unit') == 'METERS' and abs(float(sc.get('scale_length', 0)) - 1) < 1e-6
        zmin = bb[0][2] if bb else None
        g2 = zmin is not None and -0.05 <= zmin <= 0.05
        return (ok if good and g2 else bad)('units %s/%s/%s; MN01 min z %s' % (sc.get('unit_system'), sc.get('length_unit'), sc.get('scale_length'), r3(zmin)))
    safe(res, 'B02', b02)

    def b03():
        err = []
        for c in ids + ['SITE']:
            if not S.has_coll(c):
                err.append('%s missing' % c); continue
            # evaluated vertex count (modifiers / geometry nodes / curves count) or instanced geometry
            if not any(((S.ob(n) or {}).get('type') in GEOM and ((S.ob(n) or {}).get('n_verts') or 0) > 0) or M.IB.get(n)
                       for n in S.coll(c)):
                err.append('%s has no geometry' % c)
        return bad('; '.join(err)[:600]) if err else ok('36 unit collections + SITE, each with geometry')
    safe(res, 'B03', b03)

    def b04():
        err = []
        for uid in ids:
            t = U[uid]['type']
            if t in ('DN', 'MN', 'PD', 'TT', 'LW'):
                if not M.one(uid, 'platform_1'): err.append(uid + '_platform_1')
                if not M.parts(uid, 'col'): err.append(uid + '_col_###')
                if not M.one(uid, 'roof_1'): err.append(uid + '_roof_1')
            else:
                need = {'QL': ['deck'], 'SS': ['lion'], 'YD': ['road'], 'DL': ['body'],
                        'RG': ['dial'] if U[uid].get('kind') == 'sundial' else ['vessel']}[t]
                for k in need:
                    if not M.one(uid, k): err.append('%s_%s' % (uid, k))
        return bad('missing: ' + ', '.join(err)[:580]) if err else ok('required named parts present in all 36 units')
    safe(res, 'B04', b04)

    zones = {z['id']: z['units'] for z in A['zones']}
    for k, zid in enumerate('ABCDEF'):
        def mz(zid=zid):
            det, allok = [], True
            for uid in zones[zid]:
                o, d = placement(M, uid)
                allok &= o
                if not o: det.append('FAIL ' + d)
            return ok('zone %s all %d units placed/sized' % (zid, len(zones[zid]))) if allok else bad('; '.join(det))
        safe(res, 'M%02d' % (k + 1), mz)

    def vert_item(units):
        def f():
            err = []
            for uid in units:
                err += vertical(M, uid, meas[uid])
            return bad('; '.join(err)) if err else ok('%d units within tolerance' % len(units))
        return f
    safe(res, 'M07', vert_item(['MN01', 'MN02', 'MN03', 'DN01', 'DN02', 'DN03', 'DN04', 'DN05']))
    safe(res, 'M08', vert_item(['PD0%d' % i for i in range(1, 7)] + ['TT01', 'TT02'] + ['LW0%d' % i for i in range(1, 9)]))
    safe(res, 'M09', vert_item(['QL01', 'QL02', 'QL03', 'SS01', 'SS02', 'YD01', 'YD02', 'RG01', 'RG02', 'DL01', 'DL02', 'DL03']))

    def m10():
        if not isinstance(man, list):
            return bad('manifest unavailable')
        by = {it.get('id'): it for it in man if isinstance(it, dict)}
        err = []
        for uid in ids:
            it = by.get(uid)
            if not it or not isinstance(it.get('params'), dict):
                err.append('%s no entry' % uid); continue
            p, m, t = it['params'], meas[uid], U[uid]['type']
            if it.get('built') is False:
                if any((S.ob(n) or {}).get('type') in GEOM or M.IB.get(n) for n in S.coll(uid)):
                    err.append('%s built=false but geometry present' % uid)
                continue
            if 'error' in m:
                err.append('%s: %s' % (uid, m['error'])); continue

            def cmp(k, mv):
                if p.get(k) != mv:
                    err.append('%s.%s manifest=%s measured=%s' % (uid, k, p.get(k), mv))
            if t in ('DN', 'MN', 'PD'):
                for k in ('bays_front', 'bays_depth', 'platform_tiers', 'roof', 'eaves', 'dougong', 'door_bays'):
                    cmp(k, m.get(k))
            elif t == 'TT':
                for k in ('plan', 'columns', 'roof', 'eaves'):
                    cmp(k, m.get(k))
            elif t == 'LW':
                segs = p.get('segments')
                mb = [s['bays'] for s in m.get('segments', [])]
                pb = [s.get('bays') for s in segs] if isinstance(segs, list) and all(isinstance(s, dict) for s in segs) else segs
                if pb != mb:
                    err.append('%s.segments bays manifest=%s measured=%s' % (uid, pb, mb))
                cmp('gallery', m.get('gallery')); cmp('roof', m.get('roof'))
            elif t == 'QL':
                cmp('arches', m.get('arches')); cmp('posts_per_side', m.get('posts_per_side'))
            elif t == 'SS':
                cmp('sex', m.get('sex')); cmp('base_tiers', m.get('base_tiers'))
            elif t == 'YD':
                cmp('slabs', m.get('slabs')); cmp('curb', m.get('curb'))
            elif t == 'RG':
                cmp('base_tiers', m.get('base_tiers'))
                if U[uid].get('kind') != 'sundial':
                    cmp('vessel_shape', m.get('vessel_shape'))
            elif t == 'DL':
                for k in ('legs', 'ears', 'rings'):
                    cmp(k, m.get(k))
        return bad('; '.join(err)[:600]) if err else ok('manifest discrete params agree with measurements (36 units)')
    safe(res, 'M10', m10)

    def m11():
        err = []
        sb = M.cbb('SITE')
        ex = A['site_extent']
        if not sb or sb[0][0] > ex['x_min'] + 0.5 or sb[1][0] < ex['x_max'] - 0.5 or sb[0][1] > ex['y_min'] + 0.5 or sb[1][1] < ex['y_max'] - 0.5:
            err.append('SITE bbox %s does not cover site' % sb)
        rays = M.X.get('site_rays') or {}

        def zs(k):
            v = rays.get(k)
            return [v] if isinstance(v, (int, float)) else [z for z in (v or []) if isinstance(z, (int, float))]
        for x in (30, -30):
            zb = zs('%d,30' % x)
            # the channel must be open at ground level (first surface below -0.1, e.g. a water plane) and some
            # surface crossed by the ray must be the bed at -1.5 +- 0.2
            if not zb or zb[0] >= -0.1 or not any(-1.7 <= z <= -1.3 for z in zb):
                err.append('river at (%d,30) surfaces z=%s' % (x, zb[:6]))
            for y in (22, 38):
                z = zs('%d,%d' % (x, y))
                if not z or abs(z[0]) > 0.1:
                    err.append('bank at (%d,%d) z=%s' % (x, y, z[:1]))
        for q in ('QL01', 'QL02', 'QL03'):
            db = M.bb(M.one(q, 'deck'))
            if not db or db[0][1] > 25 or db[1][1] < 35:
                err.append('%s deck does not span y25-35' % q)
        return bad('; '.join(err)) if err else ok('site extent, river bed -1.5, banks 0, bridges span')
    safe(res, 'M11', m11)

    gz = {'G01': ('A', False), 'G02': ('B', False), 'G03': ('C', False), 'G04': ('D', False), 'G05': ('E', False), 'G06': ('F', True)}
    for gid, (zid, body) in gz.items():
        def gf(zid=zid, body=body):
            err = []
            for uid in zones[zid]:
                err += discrete(M, uid, meas[uid], with_body=body)
            return bad('; '.join(err)[:600]) if err else ok('zone %s discrete features all match' % zid)
        safe(res, gid, gf)

    def g07():
        m = meas['DN04']; e = []
        if m.get('eaves') != 2: e.append('roofs=%s' % m.get('eaves'))
        if m.get('roof') != 'xieshan': e.append('upper roof=%s (%s)' % (m.get('roof'), m.get('roof_why')))
        p1, p2 = M.bb(M.one('DN04', 'platform_1')), M.bb(M.one('DN04', 'platform_2'))
        if not (p1 and close(Scene.size(p1)[0], 42.6) and close(Scene.size(p1)[1], 22.8)): e.append('platform_1 %s' % (Scene.size(p1) if p1 else None))
        if not (p2 and close(Scene.size(p2)[0], 40.2) and close(Scene.size(p2)[1], 20.4)): e.append('platform_2 %s' % (Scene.size(p2) if p2 else None))
        if m.get('platform_tiers') != 2: e.append('tiers=%s' % m.get('platform_tiers'))
        if m.get('platform_top') is None or not close(m['platform_top'], 3.9): e.append('platform top %s' % r3(m.get('platform_top')))
        if m.get('ridge_top') is None or not close(m['ridge_top'], 21.3, 0.05, 0.30): e.append('ridge %s' % r3(m.get('ridge_top')))
        return bad('DN04: ' + '; '.join(e)) if e else ok('DN04 double-eave xieshan, 2 tiers, +3.90/+21.30')
    safe(res, 'G07', g07)

    def g08():
        e = []
        for uid in ('PD03', 'PD04'):
            m = meas[uid]
            if m.get('roof') != 'xieshan': e.append('%s roof=%s (%s)' % (uid, m.get('roof'), m.get('roof_why')))
            if m.get('eaves') != 1: e.append('%s eaves=%s' % (uid, m.get('eaves')))
            if not m.get('dougong'): e.append('%s no dougong' % uid)
            if m.get('ridge_top') is None or not close(m['ridge_top'], 10.0, 0.05, 0.30): e.append('%s ridge %s' % (uid, r3(m.get('ridge_top'))))
        o, d = mirror_ok(M, 'PD03', 'PD04')
        if not o: e.append(d)
        return bad('; '.join(e)) if e else ok('PD03/PD04 xieshan + dougong + ridge 10.0, mirrored')
    safe(res, 'G08', g08)

    def g09():
        e = []
        m = meas['LW05']
        if [s['bays'] for s in m.get('segments', [])] != [13, 14]: e.append('bays %s' % [s['bays'] for s in m.get('segments', [])])
        for j in A['junctions']:
            if j['lw'] in ('LW05', 'LW06'):
                o, d = junction(M, j)
                if not o: e.append(d)
        n = M.X.get('lw05_old_route_verts')
        if n is None or n != 0: e.append('LW05 verts at DN03 east gable: %s' % n)
        return bad('; '.join(e)) if e else ok('LW05 rerouted to MN03 (13+14 bays), old route clear, LW06 unchanged')
    safe(res, 'G09', g09)

    def g10():
        e = []
        for a, b in A['symmetry_pairs']:
            o, d = mirror_ok(M, a, b)
            if not o: e.append(d)
        for uid in A['axis_units']:
            bb = M.cbb(uid)
            if not bb or abs((bb[0][0] + bb[1][0]) / 2) > 0.2:
                e.append('%s centre x %s' % (uid, r3((bb[0][0] + bb[1][0]) / 2) if bb else None))
        return bad('; '.join(e)) if e else ok('8 mirror pairs and 11 axis units symmetric')
    safe(res, 'G10', g10)

    def g11():
        e, n = [], 0
        for j in A['junctions']:
            o, d = junction(M, j)
            n += 1
            if not o: e.append(d)
        return bad('%d/%d junctions fail: ' % (len(e), n) + '; '.join(e)) if e else ok('all %d junctions within 0.15/0.2 m' % n)
    safe(res, 'G11', g11)

    def g12():
        e, grp = [], {}
        for uid in ids:
            g = U[uid].get('grade')
            if g is None:
                continue
            pt = meas[uid].get('platform_top')
            if pt is None:
                e.append('%s platform missing' % uid); continue
            grp.setdefault(int(g), []).append(pt)
        for g in (1, 2, 3):
            if grp.get(g) and grp.get(g + 1) and not min(grp[g]) > max(grp[g + 1]):
                e.append('grade %d min %.2f <= grade %d max %.2f' % (g, min(grp[g]), g + 1, max(grp[g + 1])))
        return bad('; '.join(e)[:600]) if e else ok('grade ordering strict (absolute platform tops are judged in M07/M08)')
    safe(res, 'G12', g12)

    def g13():
        e = []
        for yd in ('YD01', 'YD02'):
            u = U[yd]
            rb = M.bb(M.one(yd, 'road'))
            fb, tb = M.bb(M.one(u['from_unit'], 'platform_1')), M.bb(M.one(u['to_unit'], 'platform_1'))
            if not (rb and fb and tb):
                e.append('%s road or end platforms missing' % yd); continue
            cx = (rb[0][0] + rb[1][0]) / 2
            d1, d2 = rb[0][1] - fb[1][1], tb[0][1] - rb[1][1]
            if abs(cx) > 0.2 or abs(d1) > 0.15 or abs(d2) > 0.15:
                e.append('%s cx %.2f gapS %.3f gapN %.3f' % (yd, cx, d1, d2))
        return bad('; '.join(e)) if e else ok('YD01/YD02 centred and butting both platforms')
    safe(res, 'G13', g13)
    return res


def postprocess(results, ctx):
    items = ctx['items']
    return gate_group(results, items, ['B01', 'B03'], lambda it: it['id'] not in ('B05', 'B06', 'B07'),
                      'group gate: B01 or B03 failed -> scene group zeroed')
