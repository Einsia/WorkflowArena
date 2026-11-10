# -*- coding: utf-8 -*-
"""BLD-W05 Old Harbour Town Block — deterministic checks.

One Blender extraction (Scene.load) with a task-specific extra_py that adds:
  text      FONT object bodies
  slot0     first material-slot name of every *_BODY
  slot0_col per *_BODY: resolved Base Color of slot-0 material (follows a link to an RGB node)
  furn_base per SITE_LAMP/BOLLARD: xy centre of the geometry (incl. children/instances) within 0.5 m of its base
  roof      per <lot>_ROOF: slope-area bins by world direction/angle, max slope face area, z_max,
            ridge_bins (xy bbox of slope-face top edges per 0.05 m z-bin), front-gable profile
            (|v| <= 0.3 band, upper envelope in 0.05 m bins)
  balc      per <lot>_BALC: deck-top z (highest horizontal face group with >= 50 % of the largest group's area)
  nonmanifold  per *_BODY: non-manifold edge count (bmesh, evaluated mesh)
  overlap   per joint pair (BODY/ROOF x BODY/ROOF): common interior volume via 0.2 m voxel ray-parity test
  cams      per CAM_*: loc, view dir, world_to_camera_view range of the 8 bbox corners of every built BODY
G17 (blind visual review) is left to the judge model.
"""
import json, math, re, pathlib, struct, zlib
from _bld_lib import Scene, ok, bad, png_size, load_manifest, gate_group

PALETTE = {'HC-01': '#EDE6D6', 'HC-02': '#E3D3A8', 'HC-03': '#C9A04A', 'HC-04': '#B88A35', 'HC-05': '#A4472E',
           'HC-06': '#7E2F27', 'HC-07': '#3E5F7A', 'HC-08': '#6F8797', 'HC-09': '#6A7A4C', 'HC-10': '#2F4A3A',
           'HC-11': '#9C9A92', 'HC-12': '#4A4A48', 'HC-13': '#D98E62', 'HC-14': '#B59A7A', 'HC-15': '#6D4C55',
           'HC-16': '#A9C6B4'}
FILE_ITEMS = {'B04', 'B06'}
GEOM_TYPES = ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')

EXTRA_PY = r'''
import bmesh, json as _json, math as _m
from mathutils.bvhtree import BVHTree
INFO = _json.loads(__INFO__)
LOTS = INFO['lots']

def _wmesh(ob):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        mw = ev.matrix_world.copy()
        vs = [mw @ v.co for v in me.vertices]
        ps = [tuple(p.vertices) for p in me.polygons]
        es = [tuple(e.vertices) for e in me.edges]
    finally:
        ev.to_mesh_clear()
    return vs, ps, es

def _newell(pts):
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        a = pts[i]; b = pts[(i + 1) % n]
        nx += (a.y - b.y) * (a.z + b.z); ny += (a.z - b.z) * (a.x + b.x); nz += (a.x - b.x) * (a.y + b.y)
    l = _m.sqrt(nx * nx + ny * ny + nz * nz)
    if l < 1e-12:
        return None, 0.0
    return (nx / l, ny / l, nz / l), l / 2

def _base_col(mat):
    # 2026-10-25: Base Color of the first Principled BSDF; follows a link to an RGB node; None + reason otherwise
    if mat is None or not mat.use_nodes or not mat.node_tree:
        return (list(mat.diffuse_color) if mat is not None else None), 'no nodes'
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            inp = n.inputs['Base Color']
            if not inp.is_linked:
                return list(inp.default_value), ''
            src = inp.links[0].from_node
            if src.type == 'RGB':
                return list(src.outputs[0].default_value), 'RGB node'
            return None, 'Base Color linked to ' + src.type
    return None, 'no Principled BSDF'

EXTRA['text'] = {}
EXTRA['slot0'] = {}
EXTRA['slot0_col'] = {}
for ob in scene.objects:
    try:
        if ob.type == 'FONT':
            EXTRA['text'][ob.name] = ob.data.body
        if ob.name.endswith('_BODY'):
            ms = getattr(ob, 'material_slots', [])
            m0 = ms[0].material if len(ms) else None
            EXTRA['slot0'][ob.name] = (m0.name if m0 else None)
            if m0 is not None:
                c, why = _base_col(m0)
                EXTRA['slot0_col'][ob.name] = {'col': [round(x, 4) for x in c] if c else None, 'note': why}
    except Exception as e:
        EXTRA.setdefault('err', []).append(ob.name + ': ' + str(e)[:100])

# 2026-10-25: lamp/bollard base position = xy bbox centre of the evaluated geometry (object, descendants and
# instances) lying within 0.5 m of its lowest point (csv x,y is the post, not a bracket arm)
EXTRA['furn_base'] = {}
_FUR = set(INFO.get('furn') or [])
_fpts = {}
def _addpts(key, ob, mw):
    try:
        ev = ob.evaluated_get(dg) if not getattr(ob, 'is_evaluated', False) else ob
        me = ev.to_mesh()
    except Exception:
        return
    if me is None:
        return
    try:
        _fpts.setdefault(key, []).extend([mw @ v.co for v in me.vertices])
    finally:
        ev.to_mesh_clear()
for fn in _FUR:
    ob = scene.objects.get(fn)
    if ob is None:
        continue
    for o2 in [ob] + list(ob.children_recursive):
        if o2.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            _addpts(fn, o2, o2.evaluated_get(dg).matrix_world.copy())
try:
    for oi in dg.object_instances:
        if not oi.is_instance or oi.parent is None:
            continue
        pn = oi.parent.name
        if pn in _FUR and oi.object.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            _addpts(pn, oi.object, oi.matrix_world.copy())
except Exception as e:
    EXTRA.setdefault('err', []).append('furn instances: ' + str(e)[:150])
for fn, pts in _fpts.items():
    if pts:
        z0 = min(p.z for p in pts)
        lo = [p for p in pts if p.z <= z0 + 0.5]
        EXTRA['furn_base'][fn] = [round((min(p.x for p in lo) + max(p.x for p in lo)) / 2, 4),
                                  round((min(p.y for p in lo) + max(p.y for p in lo)) / 2, 4), round(z0, 4)]

EXTRA['roof'] = {}
for ob in scene.objects:
    if ob.type != 'MESH' or not ob.name.endswith('_ROOF'):
        continue
    try:
        vs, ps, es = _wmesh(ob)
        if not vs:
            continue
        bins = {}; maxsl = 0.0
        tops = {}  # 2026-10-25: horizontal top edges of slope faces, binned by z (0.05 m): zbin -> [minx, miny, maxx, maxy]
        for p in ps:
            pv = [vs[i] for i in p]
            nrm, area = _newell(pv)
            if nrm is None or area <= 0.02:
                continue
            nx, ny, nz = nrm
            if nz < 0:
                nx, ny, nz = -nx, -ny, -nz
            ang = _m.degrees(_m.acos(max(-1.0, min(1.0, nz))))
            if ang < 5 or ang > 85:
                continue
            d = ('+x' if nx > 0 else '-x') if abs(nx) >= abs(ny) else ('+y' if ny > 0 else '-y')
            k = d + '|' + str(int(round(ang)))
            bins[k] = bins.get(k, 0.0) + area
            maxsl = max(maxsl, area)
            fz = max(v.z for v in pv)
            for v in pv:
                if v.z >= fz - 0.02:
                    kb = int(round(v.z / 0.05))
                    t = tops.get(kb)
                    if t is None:
                        tops[kb] = [v.x, v.y, v.x, v.y]
                    else:
                        t[0] = min(t[0], v.x); t[1] = min(t[1], v.y); t[2] = max(t[2], v.x); t[3] = max(t[3], v.y)
        zmax = max(v.z for v in vs)
        top = [v for v in vs if v.z >= zmax - 0.05]
        r = {'slopes': {k: round(a, 4) for k, a in bins.items()}, 'max_slope_face': round(maxsl, 4), 'zmax': round(zmax, 4),
             'ridge': [[round(min(v.x for v in top), 4), round(min(v.y for v in top), 4)],
                       [round(max(v.x for v in top), 4), round(max(v.y for v in top), 4)]],
             'ridge_bins': [[kb] + [round(c, 4) for c in t] for kb, t in sorted(tops.items())][-400:]}
        lid = ob.name[:-5]
        li = LOTS.get(lid)
        if li:
            ax, bax, bl, vsg = li['ax'], li['bax'], li['bl'], li['vs']
            env = {}
            def _put(pt):
                k = int(round(pt[ax] / 0.05))
                if k not in env or pt.z > env[k]:
                    env[k] = pt.z
            for v in vs:
                if abs((v[bax] - bl) * vsg) <= 0.3:
                    _put(v)
            for i, j in es:
                p, q = vs[i], vs[j]
                vp, vq = (p[bax] - bl) * vsg, (q[bax] - bl) * vsg
                if (vp > 0.3 and vq > 0.3) or (vp < -0.3 and vq < -0.3):
                    continue
                if abs(vq - vp) > 1e-9:
                    t0 = (-0.3 - vp) / (vq - vp); t1 = (0.3 - vp) / (vq - vp)
                    lo, hi = max(0.0, min(t0, t1)), min(1.0, max(t0, t1))
                else:
                    lo, hi = 0.0, 1.0
                if hi < lo:
                    continue
                L = (q - p).length * (hi - lo)
                n = max(1, min(4000, int(L / 0.025)))
                for s in range(n + 1):
                    _put(p.lerp(q, lo + (hi - lo) * s / n))
            r['profile'] = [[round(k * 0.05, 3), round(z, 4)] for k, z in sorted(env.items())]
        EXTRA['roof'][ob.name] = r
    except Exception as e:
        EXTRA.setdefault('err', []).append(ob.name + ' roof: ' + str(e)[:200])

EXTRA['balc'] = {}
for ob in scene.objects:
    if ob.type != 'MESH' or not ob.name.endswith('_BALC'):
        continue
    try:
        vs, ps, es = _wmesh(ob)
        grp = {}
        for p in ps:
            nrm, area = _newell([vs[i] for i in p])
            if nrm is None or abs(nrm[2]) < 0.9:
                continue
            z = sum(vs[i].z for i in p) / len(p)
            k = round(z / 0.02)
            grp[k] = grp.get(k, 0.0) + area
        if grp:
            amax = max(grp.values())
            EXTRA['balc'][ob.name] = round(max(k for k, a in grp.items() if a >= 0.5 * amax) * 0.02, 4)
    except Exception as e:
        EXTRA.setdefault('err', []).append(ob.name + ' balc: ' + str(e)[:200])

EXTRA['nonmanifold'] = {}
for ob in scene.objects:
    if ob.type != 'MESH' or not ob.name.endswith('_BODY'):
        continue
    try:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        EXTRA['nonmanifold'][ob.name] = sum(1 for e in bm.edges if not e.is_manifold)
        bm.free()
        ev.to_mesh_clear()
    except Exception as e:
        EXTRA.setdefault('err', []).append(ob.name + ' nm: ' + str(e)[:200])

_BVH = {}
def _bvh(name):
    if name not in _BVH:
        ob = scene.objects.get(name)
        if ob is None or ob.type != 'MESH':
            _BVH[name] = None
        else:
            vs, ps, es = _wmesh(ob)
            _BVH[name] = (BVHTree.FromPolygons(vs, ps), [[min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]]) if ps else None
    return _BVH[name]

_DIR = Vector((1.0, 0.0123, 0.0071)).normalized()
def _inside(t, p):
    c = 0; o = p.copy()
    for _ in range(200):
        h = t.ray_cast(o, _DIR, 1e4)
        if h[0] is None:
            break
        c += 1
        o = h[0] + _DIR * 1e-4
    return c % 2 == 1

EXTRA['overlap'] = {}
for a, b in INFO['pairs']:
    try:
        A, B = _bvh(a), _bvh(b)
        if A is None or B is None:
            continue
        lo = [max(A[1][0][i], B[1][0][i]) for i in range(3)]
        hi = [min(A[1][1][i], B[1][1][i]) for i in range(3)]
        ext = [hi[i] - lo[i] for i in range(3)]
        if min(ext) < 0.06:
            EXTRA['overlap'][a + '|' + b] = 0.0
            continue
        st = 0.2
        while True:
            n = [max(1, int(round(e / st))) for e in ext]
            if n[0] * n[1] * n[2] <= 20000:
                break
            st *= 1.25
        cell = [ext[i] / n[i] for i in range(3)]
        cnt = 0
        for i in range(n[0]):
            for j in range(n[1]):
                for k in range(n[2]):
                    p = Vector((lo[0] + (i + 0.5) * cell[0], lo[1] + (j + 0.5) * cell[1], lo[2] + (k + 0.5) * cell[2]))
                    if _inside(A[0], p) and _inside(B[0], p):
                        cnt += 1
        EXTRA['overlap'][a + '|' + b] = round(cnt * cell[0] * cell[1] * cell[2], 4)
    except Exception as e:
        EXTRA.setdefault('err', []).append(a + '|' + b + ' ov: ' + str(e)[:200])

EXTRA['cams'] = {}
try:
    from bpy_extras.object_utils import world_to_camera_view
    for cn in ('CAM_OVERVIEW', 'CAM_QUAY', 'CAM_MARKET'):
        cam = scene.objects.get(cn)
        if cam is None or cam.type != 'CAMERA':
            continue
        mw = cam.matrix_world
        d = (mw.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
        proj = {}
        for bn in INFO['bodies']:
            ob = scene.objects.get(bn)
            if ob is None:
                continue
            ev = ob.evaluated_get(dg)
            pts = [world_to_camera_view(scene, cam, ev.matrix_world @ Vector(c)) for c in ev.bound_box]
            proj[bn] = [round(min(p.x for p in pts), 4), round(max(p.x for p in pts), 4), round(min(p.y for p in pts), 4),
                        round(max(p.y for p in pts), 4), round(min(p.z for p in pts), 4)]
        EXTRA['cams'][cn] = {'loc': [round(x, 4) for x in mw.translation], 'dir': [round(x, 5) for x in d], 'proj': proj}
except Exception as e:
    EXTRA.setdefault('err', []).append('cams: ' + str(e)[:200])
'''


# ---------------------------------------------------------------- helpers
def tol(x):
    return max(0.10, 0.03 * abs(float(x)))


def norm_text(s):
    return re.sub(r'\s+', ' ', str(s or '').strip())


def hex_rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


def lin2srgb(c):
    c = max(0.0, min(1.0, float(c)))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


class Row:
    def __init__(self, rid, r):
        self.id = rid
        self.ax = 0 if r['along'] == 'x' else 1
        self.bax = 0 if r['bl_axis'] == 'x' else 1
        self.bl = float(r['bl'])
        self.start, self.end = float(r['start']), float(r['end'])
        self.dir = 1.0 if self.end > self.start else -1.0
        f = r['facing']
        fs = -1.0 if f.startswith('-') else 1.0
        self.vs = -fs  # building extends away from the street
        self.facing = [0.0, 0.0, 0.0]
        self.facing[0 if f.endswith('X') else 1] = fs
        self.length = abs(self.end - self.start)
        self.lots = r['lots']

    def u(self, a):
        return (a - self.start) * self.dir

    def v(self, b):
        return (b - self.bl) * self.vs

    def uvz(self, bb):
        """world bbox -> ((u0,u1),(v0,v1),(z0,z1))"""
        if not bb:
            return None
        us = sorted([self.u(bb[0][self.ax]), self.u(bb[1][self.ax])])
        vs = sorted([self.v(bb[0][self.bax]), self.v(bb[1][self.bax])])
        return us, vs, [bb[0][2], bb[1][2]]

    def seg_u(self, seg):
        return sorted([self.u(seg[0]), self.u(seg[1])])


class Ctx:
    def __init__(self, ctx, S):
        self.S = S
        self.ak = ctx['answer']
        self.rows = {k: Row(k, v) for k, v in self.ak['rows'].items()}
        self.lots = self.ak['lots']
        self.built = [k for k, v in self.lots.items() if v.get('built')]
        self.row_of = {}
        for rid, r in self.rows.items():
            for l in r.lots:
                self.row_of[l] = r
        self.extra = (S.data or {}).get('extra', {}) if S.data else {}
        self._roofcls = {}
        # 2026-10-25: instanced geometry (collection / geometry-nodes instances) grouped by instancer object
        self.inst = {}
        for it in ((S.data or {}).get('instances') or []):
            if isinstance(it, dict) and it.get('instancer') and it.get('bbox_world') and it.get('type') in GEOM_TYPES:
                self.inst.setdefault(it['instancer'], []).append(it['bbox_world'])

    def ob(self, name):
        return self.S.objects.get(name)

    def bb(self, name):
        """world bbox of the evaluated geometry of an object plus everything it instances (None if neither)."""
        o = self.ob(name)
        if not o:
            return None
        bs = list(self.inst.get(name, []))
        if o.get('type') in GEOM_TYPES and o.get('bbox_world'):
            bs.append(o['bbox_world'])
        if not bs:
            return None
        return [[min(b[0][i] for b in bs) for i in range(3)], [max(b[1][i] for b in bs) for i in range(3)]]

    def lot_names(self, lid, pat):
        r = re.compile('^' + re.escape(lid) + '_' + pat + '$')
        return sorted(n for n in self.S.objects if r.match(n))

    def axis_u(self, lid, k):
        L = self.lots[lid]
        r = self.row_of[lid]
        return r.seg_u(L['seg'])[0] + L['axes'][k - 1]

    def floor_z(self, lid, f):
        L = self.lots[lid]
        return L['h1'] + (f - 2) * L['hu'] if f >= 2 else 0.0

    def tree_bbox(self, name):
        """bbox of an object and all its descendants (for empties/parented assemblies)."""
        names = {name}
        ch = True
        while ch:
            ch = False
            for n, o in self.S.objects.items():
                if n not in names and o.get('parent') in names:
                    names.add(n); ch = True
        bs = [b for b in (self.bb(n) for n in sorted(names)) if b]
        if not bs:
            return None
        return [[min(b[0][i] for b in bs) for i in range(3)], [max(b[1][i] for b in bs) for i in range(3)]]

    def body_eave(self, lid):
        bb = self.bb(lid + '_BODY')
        return bb[1][2] if bb else None

    def roof_class(self, lid):
        if lid in self._roofcls:
            return self._roofcls[lid]
        res = self._classify(lid)
        self._roofcls[lid] = res
        return res

    def _classify(self, lid):
        rs = self.extra.get('roof', {}).get(lid + '_ROOF')
        L = self.lots[lid]
        r = self.row_of[lid]
        if not rs:
            return None, 'no ROOF stats'
        eave = self.body_eave(lid)
        if eave is None:
            eave = L['eave']
        tot = sum(rs['slopes'].values())
        dirs = {}
        angs = []
        a60 = a35 = 0.0
        for k, a in rs['slopes'].items():
            d, ang = k.split('|')
            ang = float(ang)
            axw = 0 if d[1] == 'x' else 1
            key = ('u' if axw == r.ax else 'v')
            dirs[key + d[0]] = dirs.get(key + d[0], 0.0) + a
            if tot > 0 and a >= 0.01 * tot:
                angs.append(ang)
            if ang >= 60:
                a60 += a
            if ang <= 35:
                a35 += a
        present = {k for k, a in dirs.items() if tot > 0 and a >= 0.05 * tot}
        diag = f'zmax-eave={rs["zmax"] - eave:.2f} maxslope={rs["max_slope_face"]:.2f} dirs={sorted(present)}'
        if rs['zmax'] - eave <= 1.5 and rs['max_slope_face'] <= 1.0:
            return 'R5', diag
        spu, spv = ridge_spans(rs, r)
        if present and present <= {'u+', 'u-'}:
            if spv >= 0.6 * L['depth']:
                return 'R1', diag
            return None, diag + f' ridge v-span {spv:.2f} < 0.6*depth'
        if present and present <= {'v+', 'v-'}:
            if spu >= 0.6 * L['width']:
                return 'R2', diag
            return None, diag + f' ridge u-span {spu:.2f} < 0.6*width'
        if present == {'u+', 'u-', 'v+', 'v-'}:
            if tot > 0 and a60 / tot >= 0.15 and a35 / tot >= 0.15:
                return 'R4', diag
            if angs and max(angs) - min(angs) <= 8:
                return 'R3', diag
            return None, diag + f' angle range {min(angs) if angs else 0}-{max(angs) if angs else 0}'
        return None, diag


def ridge_spans(rs, r):
    """2026-10-25: longest horizontal top edge of the slope faces, as (u-span, v-span) in row-local coordinates.
    'ridge_bins' = per 0.05 m z-bin xy bbox of the slope faces' top-edge vertices; adjacent bins are merged. Gable
    copings, stepped-gable tops or bell crowns above the ridge therefore no longer hide the ridge. Falls back to the
    v1 'ridge' box (vertices within 0.05 of ROOF z_max) for extracts without ridge_bins."""
    rbs = rs.get('ridge_bins')
    if not rbs:
        rb = rs.get('ridge') or [[0, 0], [0, 0]]
        ru = sorted([r.u(rb[0][r.ax]), r.u(rb[1][r.ax])])
        rv = sorted([r.v(rb[0][r.bax]), r.v(rb[1][r.bax])])
        return ru[1] - ru[0], rv[1] - rv[0]
    by = {int(b[0]): b[1:] for b in rbs}
    bu = bv = 0.0
    for k in by:
        grp = [by[j] for j in (k - 1, k, k + 1) if j in by]
        lo = [min(g[0] for g in grp), min(g[1] for g in grp)]
        hi = [max(g[2] for g in grp), max(g[3] for g in grp)]
        bu = max(bu, hi[r.ax] - lo[r.ax])
        bv = max(bv, hi[r.bax] - lo[r.bax])
    return bu, bv


def fit_line(pts):
    n = len(pts)
    if n < 2:
        return 0.0
    mx = sum(p[0] for p in pts) / n
    mz = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if sxx < 1e-12:
        return max(abs(p[1] - mz) for p in pts)
    k = sum((p[0] - mx) * (p[1] - mz) for p in pts) / sxx
    return max(abs(p[1] - (mz + k * (p[0] - mx))) for p in pts)


def gable_check(C, lid):
    """returns (ok, detail) for the truth gable of an R1 lot."""
    L = C.lots[lid]
    g = L.get('gable')
    rs = C.extra.get('roof', {}).get(lid + '_ROOF') or {}
    prof = rs.get('profile')
    if not prof:
        return False, 'no gable profile'
    r = C.row_of[lid]
    eave = C.body_eave(lid) or L['eave']
    pts = sorted((r.u(a), z) for a, z in prof if z >= eave + 0.05)
    if len(pts) < 4:
        return False, f'gable profile too sparse ({len(pts)} pts)'
    zt = max(p[1] for p in pts)
    ua = [p[0] for p in pts if p[1] >= zt - 0.02]
    uc = (min(ua) + max(ua)) / 2
    left = [p for p in pts if p[0] <= uc]
    right = [p for p in pts if p[0] >= uc]
    res = max(fit_line(left), fit_line(right))
    if g == 'G-a':
        return res <= 0.10, f'G-a line residual {res:.3f} (<=0.10)'
    if g == 'G-b':
        plats = []
        run = [pts[0]]
        for p in pts[1:]:
            if p[0] - run[-1][0] <= 0.06 and abs(p[1] - run[0][1]) <= 0.05:
                run.append(p)
            else:
                if run[-1][0] - run[0][0] >= 0.15:
                    plats.append(sum(q[1] for q in run) / len(run))
                run = [p]
        if run[-1][0] - run[0][0] >= 0.15:
            plats.append(sum(q[1] for q in run) / len(run))
        lev = []
        for z in sorted(plats):
            if abs(z - eave) <= 0.10:
                continue
            if not lev or z - lev[-1] > 0.05:
                lev.append(z)
        return len(lev) == L['gable_steps'], f'G-b plateau levels {len(lev)} vs steps {L["gable_steps"]}'
    if g == 'G-c':
        nd = len({round(p[1] / 0.05) for p in pts})
        return nd >= 8 and res > 0.15, f'G-c distinct heights {nd} (>=8), residual {res:.3f} (>0.15)'
    return False, f'unknown gable {g}'


def png_std(p):
    try:
        from PIL import Image, ImageStat
        im = Image.open(p).convert('L')
        im.thumbnail((480, 270))
        return ImageStat.Stat(im).stddev[0]
    except ImportError:
        pass
    except Exception:
        return None
    # pure-python fallback (8-bit, non-interlaced)
    try:
        b = open(p, 'rb').read()
        pos, idat, w = 8, b'', None
        while pos < len(b):
            ln = struct.unpack('>I', b[pos:pos + 4])[0]
            t = b[pos + 4:pos + 8]
            d = b[pos + 8:pos + 8 + ln]
            if t == b'IHDR':
                w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', d)
            elif t == b'IDAT':
                idat += d
            pos += 12 + ln
        if bd != 8 or il:
            return None
        ch = {0: 1, 2: 3, 4: 2, 6: 4}.get(ct)
        if not ch:
            return None
        raw = zlib.decompress(idat)
        st = w * ch
        prev = bytearray(st)
        vals = []
        i = 0
        for y in range(h):
            f = raw[i]; line = bytearray(raw[i + 1:i + 1 + st]); i += 1 + st
            for x in range(st):
                a = line[x - ch] if x >= ch else 0
                up = prev[x]
                if f == 1:
                    line[x] = (line[x] + a) & 255
                elif f == 2:
                    line[x] = (line[x] + up) & 255
                elif f == 3:
                    line[x] = (line[x] + ((a + up) >> 1)) & 255
                elif f == 4:
                    c = prev[x - ch] if x >= ch else 0
                    pp = a + up - c
                    pa, pb, pc = abs(pp - a), abs(pp - up), abs(pp - c)
                    line[x] = (line[x] + (a if pa <= pb and pa <= pc else (up if pb <= pc else c))) & 255
            prev = line
            if y % 4 == 0:
                for x in range(0, w, 4):
                    px = line[x * ch:x * ch + min(ch, 3)]
                    vals.append(sum(px) / len(px))
        m = sum(vals) / len(vals)
        return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))
    except Exception:
        return None


# ---------------------------------------------------------------- checks
from contextlib import contextmanager


@contextmanager
def guard(R, ids):
    try:
        yield
    except Exception:
        import traceback
        tb = traceback.format_exc()[-400:]
        for i in ids:
            R[i] = bad('checks error: ' + tb)


def _scene_items(C, out, items):
    S = C.S
    texts = C.extra.get('text', {})
    slot0 = C.extra.get('slot0', {})
    mats = S.data.get('materials', {})
    sc = S.data.get('scene') or {}
    R = {}
    ak = C.ak
    lots = C.lots

    # B01
    with guard(R, ['B01']):
        sc = S.data.get('scene') or {}
        if sc.get('unit_system') == 'METRIC' and abs(float(sc.get('scale_length', 0)) - 1.0) < 1e-6:
            R['B01'] = ok(f'METRIC scale_length={sc.get("scale_length")} blender={S.data.get("blender_version")}')
        else:
            R['B01'] = bad(f'unit_system={sc.get("unit_system")} scale_length={sc.get("scale_length")}')

    # B02
    with guard(R, ['B02']):
        need = [l for r in C.rows.values() for l in r.lots] + ['SITE']
        miss = [n for n in need if not S.has_coll(n)]
        R['B02'] = ok('all 31 collections present') if not miss else bad(f'missing collections: {miss}')

    # B03
    with guard(R, ['B03']):
        errs = []
        for lid in C.built:
            inc = set(S.coll(lid))
            for suf, ty in (('BODY', 'MESH'), ('ROOF', 'MESH'), ('SIGN', 'FONT')):
                n = f'{lid}_{suf}'
                o = C.ob(n)
                if n not in inc or not o or o.get('type') != ty:
                    errs.append(f'{n}' + ('' if o else ' missing') + (f' type={o.get("type")}' if o and o.get('type') != ty else '') +
                                (' not in collection' if o and n not in inc else ''))
        R['B03'] = ok(f'{len(C.built)} lots have BODY/ROOF/SIGN') if not errs else bad('; '.join(errs[:8]))

    # B05
    with guard(R, ['B05']):
        e = []
        for c in ('CAM_OVERVIEW', 'CAM_QUAY', 'CAM_MARKET'):
            o = C.ob(c)
            if not o or o.get('type') != 'CAMERA':
                e.append(f'{c} missing/not camera')
        if list(sc.get('res') or [])[:3] != [1920, 1080, 100]:
            e.append(f'render res {sc.get("res")}')
        R['B05'] = ok('cameras + 1920x1080@100%') if not e else bad('; '.join(e))

    # B07
    with guard(R, ['B07']):
        site = set(S.coll('SITE'))
        # 2026-10-25: water / ground may be split over several SITE meshes; the union of their xy boxes must cover
        # the sample grid (0.5 m) of the basin strip / Quay Street. Water: top face z_max in [-1.3,-1.1], y_max <= 0.5.
        wb, gb = [], []
        for n in site:
            o = C.ob(n)
            b = C.bb(n) if o and o.get('type') == 'MESH' else None
            if not b:
                continue
            if -1.3 <= b[1][2] <= -1.1 and b[1][1] <= 0.5:
                wb.append((n, b))
            if -0.1 <= b[1][2] <= 0.1:
                gb.append((n, b))

        def covers(bs, xs, ys):
            return bool(bs) and all(any(b[0][0] - 0.01 <= x <= b[1][0] + 0.01 and b[0][1] - 0.01 <= y <= b[1][1] + 0.01
                                        for _, b in bs) for x in xs for y in ys)
        gx = [0.05 + 0.5 * i for i in range(184)] + [91.85]
        water = [n for n, _ in wb] if covers(wb, gx, [-1.0]) else None
        ground = [n for n, _ in gb] if covers(gb, gx, [0.05 + 0.5 * j for j in range(24)] + [11.95]) else None
        fur = {f['id'] for f in ak['furniture']}
        have = {n for n in site if re.match(r'^SITE_(LAMP|BOLLARD)_\d+$|^SITE_BOAT_\d+$', n)}
        e = []
        if not water:
            e.append('no water surface (SITE meshes with z_max in [-1.3,-1.1], y_max<=0.5 covering x 0..91.9 at y=-1.0)')
        if not ground:
            e.append('Quay Street ground not covered (SITE meshes with z_max in [-0.1,0.1] covering x 0..91.9, y 0..12)')
        if have != fur:
            e.append(f'furniture name mismatch: missing {sorted(fur - have)[:6]} extra {sorted(have - fur)[:6]}')
        R['B07'] = ok(f'water={water} ground={ground} furniture {len(have)}') if not e else bad('; '.join(e))

    # M01-M06 massing
    with guard(R, ['M01','M02','M03','M04','M05','M06']):
        for zi, z in enumerate(ak['zones']):
            e = []
            for lid in z['units']:
                L = lots[lid]
                if not L.get('built'):
                    continue
                r = C.row_of[lid]
                q = r.uvz(C.bb(lid + '_BODY'))
                if not q:
                    e.append(f'{lid}_BODY missing'); continue
                (u0, u1), (v0, v1), (z0, z1) = q
                su = r.seg_u(L['seg'])
                if abs(u0 - su[0]) > 0.10 or abs(u1 - su[1]) > 0.10:
                    e.append(f'{lid} u [{u0:.2f},{u1:.2f}] vs [{su[0]:.2f},{su[1]:.2f}]')
                if abs(v0) > 0.05:
                    e.append(f'{lid} v_min {v0:.3f}')
                if abs(v1 - L['depth']) > tol(L['depth']):
                    e.append(f'{lid} depth {v1:.2f} vs {L["depth"]}')
                if not -0.10 <= z0 <= 0.10:
                    e.append(f'{lid} z_min {z0:.2f}')
                if abs(z1 - L['eave']) > tol(L['eave']):
                    e.append(f'{lid} eave {z1:.2f} vs {L["eave"]}')
            R[f'M0{zi + 1}'] = ok(f'zone {z["id"]} massing ok') if not e else bad('; '.join(e[:8]))

    # M07-M12 signs + colour
    with guard(R, ['M07','M08','M09','M10','M11','M12']):
        texts = C.extra.get('text', {})
        slot0 = C.extra.get('slot0', {})
        slot0c = C.extra.get('slot0_col', {})
        mats = S.data.get('materials', {})
        for zi, z in enumerate(ak['zones']):
            e = []
            for lid in z['units']:
                L = lots[lid]
                if not L.get('built'):
                    continue
                r = C.row_of[lid]
                sn = lid + '_SIGN'
                o = C.ob(sn)
                if not o or o.get('type') != 'FONT':
                    e.append(f'{sn} missing/not FONT')
                else:
                    if norm_text(texts.get(sn)) != L['sign_text']:
                        e.append(f'{sn} text {texts.get(sn)!r}')
                    q = r.uvz(o.get('bbox_world'))
                    if not q:
                        e.append(f'{sn} no bbox')
                    else:
                        uc, vc, zc = [(a + b) / 2 for a, b in q]
                        su = r.seg_u(L['seg'])
                        if not (su[0] <= uc <= su[1] and -1.5 <= vc <= 0.3 and 1.8 <= zc <= L['h1'] + 0.6):
                            e.append(f'{sn} centre u={uc:.2f} v={vc:.2f} z={zc:.2f}')
                    m = o.get('matrix_world')
                    zax = [m[0][2], m[1][2], m[2][2]]
                    ln = math.sqrt(sum(x * x for x in zax)) or 1
                    dp = sum(zax[i] / ln * r.facing[i] for i in range(3))
                    if dp < 0.9:
                        e.append(f'{sn} +Z.facing={dp:.2f}')
                    else:
                        # 2026-10-25: reading direction: local +X along the viewer's right ((-facing) x Z), local +Y up
                        X = [m[0][0], m[1][0], m[2][0]]
                        Y = [m[0][1], m[1][1], m[2][1]]
                        right = [-r.facing[1], r.facing[0], 0.0]
                        lx = math.sqrt(sum(t * t for t in X)) or 1
                        xr = sum(X[i] / lx * right[i] for i in range(3))
                        if xr < 0.9 or Y[2] <= 0:
                            e.append(f'{sn} mirrored/upside-down (+X.right={xr:.2f}, +Y.z={Y[2]:.2f})')
                bn = lid + '_BODY'
                mn = slot0.get(bn)
                if mn != L['colour']:
                    e.append(f'{bn} slot0 material {mn!r} vs {L["colour"]}')
                else:
                    sc0 = slot0c.get(bn)
                    if sc0 is not None:  # 2026-10-25: resolved Base Color (follows an RGB node link)
                        col = sc0.get('col')
                    else:  # extracts without slot0_col
                        col = (mats.get(mn) or {}).get('base_color')
                        if (mats.get(mn) or {}).get('base_color_linked'):
                            col = None
                    ref = hex_rgb(PALETTE[L['colour']])
                    if not col or any(abs(lin2srgb(col[i]) - ref[i]) > 0.03 for i in range(3)):
                        e.append(f'{mn} colour {col} vs sRGB {PALETTE[L["colour"]]}' +
                                 (f' ({sc0.get("note")})' if sc0 and sc0.get('note') else ''))
            R[f'M{7 + zi:02d}'] = ok(f'zone {z["id"]} signs/colours ok') if not e else bad('; '.join(e[:8]))

    # M13 lamps / bollards
    with guard(R, ['M13']):
        e = []
        for f in ak['furniture']:
            if f['kind'] not in ('LAMP', 'BOLLARD'):
                continue
            bb = C.tree_bbox(f['id']) if C.ob(f['id']) else None
            if not bb:
                e.append(f'{f["id"]} missing'); continue
            fb = C.extra.get('furn_base', {}).get(f['id'])
            if fb:  # 2026-10-25: centre of the geometry within 0.5 m of the base (post), not of the whole lamp
                cx, cy = fb[0], fb[1]
            else:
                cx, cy = (bb[0][0] + bb[1][0]) / 2, (bb[0][1] + bb[1][1]) / 2
            if math.hypot(cx - f['x'], cy - f['y']) > 0.30:
                e.append(f'{f["id"]} xy ({cx:.2f},{cy:.2f})')
            h = f['height']
            if f['kind'] == 'LAMP' and not (h - 0.2 <= bb[1][2] <= h + 0.6):
                e.append(f'{f["id"]} z_max {bb[1][2]:.2f}')
            if f['kind'] == 'BOLLARD' and (abs(bb[1][2] - h) > 0.10 or not -0.10 <= bb[0][2] <= 0.10):
                e.append(f'{f["id"]} z {bb[0][2]:.2f}..{bb[1][2]:.2f}')
        R['M13'] = ok('lamps and bollards placed') if not e else bad('; '.join(e[:8]))

    # M15 animation
    with guard(R, ['M15']):
        e = []
        fps = (sc.get('fps') or 0) / (sc.get('fps_base') or 1)
        if sc.get('frame_start') != 1 or sc.get('frame_end') != 240 or abs(fps - 24) > 1e-6:
            e.append(f'frames {sc.get("frame_start")}-{sc.get("frame_end")} fps {fps}')
        frames = list(range(1, 241, 4))
        for f in ak['furniture']:
            if f['kind'] != 'BOAT':
                continue
            n = f['id']
            if not C.ob(n):
                e.append(f'{n} missing'); continue
            bb = C.tree_bbox(n)
            if not bb:
                e.append(f'{n} no geometry'); continue
            sx, sy = bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]
            cx, cy = (bb[0][0] + bb[1][0]) / 2, (bb[0][1] + bb[1][1]) / 2
            if math.hypot(cx - f['x'], cy - f['y']) > 0.5:
                e.append(f'{n} centre ({cx:.2f},{cy:.2f})')
            ln = max(sx, sy)
            if abs(ln - f['length']) > 0.10 * f['length']:
                e.append(f'{n} length {ln:.2f}')
            Lax = [1.0, 0.0, 0.0] if sx >= sy else [0.0, 1.0, 0.0]
            yw = math.radians(f.get('yaw_deg') or 0)
            fw = [math.cos(yw), math.sin(yw), 0.0]
            if Lax[0] * fw[0] + Lax[1] * fw[1] < 0:
                Lax = [-Lax[0], -Lax[1], 0.0]
            stb = [Lax[1], -Lax[0], 0.0]
            ms = [S.at(fr, n) for fr in frames]
            if any(m is None for m in ms):
                e.append(f'{n} not sampled in animation'); continue
            p0 = S.loc(ms[0])
            drift = max(math.dist(S.loc(m), p0) for m in ms)
            if drift > 0.05:
                e.append(f'{n} translation drift {drift:.3f}')
            ts, rolls = [], []
            for fr, m in zip(frames, ms):
                up = S.axis(m, 2)
                l = math.sqrt(sum(x * x for x in up)) or 1
                rolls.append(math.degrees(math.atan2(sum(up[i] * stb[i] for i in range(3)) / l, up[2] / l)))
                ts.append((fr - 1) / 24.0)
            best = None
            T = 2.0
            while T <= 8.0001:
                w = 2 * math.pi / T
                s = [math.sin(w * t) for t in ts]; c = [math.cos(w * t) for t in ts]
                ss = sum(x * x for x in s); cc = sum(x * x for x in c); sc_ = sum(x * y for x, y in zip(s, c))
                sy_ = sum(x * y for x, y in zip(s, rolls)); cy_ = sum(x * y for x, y in zip(c, rolls))
                det = ss * cc - sc_ * sc_
                if abs(det) > 1e-9:
                    a = (sy_ * cc - cy_ * sc_) / det; b = (cy_ * ss - sy_ * sc_) / det
                    sse = sum((r_ - a * si - b * ci) ** 2 for r_, si, ci in zip(rolls, s, c))
                    if best is None or sse < best[0]:
                        best = (sse, T, a, b)
                T += 0.005
            if not best:
                e.append(f'{n} roll fit failed'); continue
            _, T, a, b = best
            A = math.hypot(a, b)
            ph = math.degrees(math.atan2(b, a))
            dph = abs((ph - f['roll_phase_deg'] + 180) % 360 - 180)
            if abs(A - f['roll_amp_deg']) > 0.5 or abs(T - f['roll_period_s']) > 0.15 or dph > 15:
                e.append(f'{n} fit A={A:.2f} T={T:.3f} phase={ph:.1f} (want {f["roll_amp_deg"]},{f["roll_period_s"]},{f["roll_phase_deg"]})')
        R['M15'] = ok('frames/fps ok; boats roll per spec') if not e else bad('; '.join(e[:6]))

    # M16 cameras
    with guard(R, ['M16']):
        cams = C.extra.get('cams', {})
        bodies = [l + '_BODY' for l in C.built]
        e = []

        def infr(cam, names):
            bad_ = []
            pr = cams.get(cam, {}).get('proj', {})
            for n in names:
                p = pr.get(n)
                if not p or p[0] < 0 or p[1] > 1 or p[2] < 0 or p[3] > 1 or p[4] <= 0:
                    bad_.append(n[:3])
            return bad_
        q = cams.get('CAM_QUAY')
        if not q:
            e.append('CAM_QUAY missing')
        else:
            ab = [l + '_BODY' for l in C.built if l[0] in 'AB']
            bq = infr('CAM_QUAY', ab)
            if bq or q['loc'][1] >= 0:
                e.append(f'CAM_QUAY y={q["loc"][1]:.1f} out-of-frame {bq}')
        m = cams.get('CAM_MARKET')
        if not m:
            e.append('CAM_MARKET missing')
        else:
            x, y, z = m['loc']
            d = m['dir']
            ang = math.degrees(math.acos(max(-1, min(1, d[1] / (math.sqrt(sum(t * t for t in d)) or 1)))))
            if not (43.20 <= x <= 51.20 and 12 <= y <= 32 and 1.4 <= z <= 1.8 and ang <= 20):
                e.append(f'CAM_MARKET loc ({x:.1f},{y:.1f},{z:.2f}) angle to +Y {ang:.1f}')
        o = cams.get('CAM_OVERVIEW')
        if not o:
            e.append('CAM_OVERVIEW missing')
        else:
            bb = S.bbox(bodies)
            cen = Scene.center(bb) if bb else [46, 50, 0]
            bo = infr('CAM_OVERVIEW', bodies)
            if not (o['loc'][0] > cen[0] and o['loc'][1] < cen[1] and o['loc'][2] > 30) or bo:
                e.append(f'CAM_OVERVIEW loc {o["loc"]} centre ({cen[0]:.1f},{cen[1]:.1f}) out-of-frame {bo[:8]}')
        R['M16'] = ok('cameras placed') if not e else bad('; '.join(e))

    # G01-G06 facades
    with guard(R, ['G01','G02','G03','G04','G05','G06']):
        for zi, z in enumerate(ak['zones']):
            e = []
            for lid in z['units']:
                L = lots[lid]
                if L.get('built'):
                    e += facade_errs(C, lid)
            R[f'G0{zi + 1}'] = ok(f'zone {z["id"]} facades ok') if not e else bad('; '.join(e[:8]))

    # G07-G12 roofs + components
    with guard(R, ['G07','G08','G09','G10','G11','G12']):
        for zi, z in enumerate(ak['zones']):
            e = []
            for lid in z['units']:
                L = lots[lid]
                if L.get('built'):
                    e += roof_errs(C, lid)
            R[f'G{7 + zi:02d}'] = ok(f'zone {z["id"]} roofs/components ok') if not e else bad('; '.join(e[:8]))

    # G13 merge
    with guard(R, ['G13']):
        e = []
        if not S.has_coll('C03'):
            e.append('collection C03 missing')
        elif S.coll('C03'):
            e.append(f'C03 not empty: {S.coll("C03")[:5]}')
        rc = C.rows['C']
        cu = rc.seg_u(C.ak['original_lots']['C03']['seg']) if 'C03' in C.ak.get('original_lots', {}) else [13.6, 22.3]
        for n, o in S.objects.items():
            if n.startswith('C02_') or not re.search(r'_(BODY|ROOF)$', n):
                continue
            q = rc.uvz(C.bb(n))
            if not q:
                continue
            (u0, u1), (v0, v1), _ = q
            if v1 > -2 and v0 < 25 and u0 < cu[1] - 0.05 and u1 > cu[0] + 0.05:
                e.append(f'{n} intrudes on former C03 lot')
        L = lots['C02']
        q = rc.uvz(C.bb('C02_BODY'))
        if not q:
            e.append('C02_BODY missing')
        else:
            (u0, u1), (v0, v1), (z0, z1) = q
            if abs(u0 - 7.4) > 0.10 or abs(u1 - 22.3) > 0.10 or abs(v1 - v0 - 13.0) > 0.10 or abs(z1 - 13.7) > 0.10:
                e.append(f'C02_BODY u[{u0:.2f},{u1:.2f}] depth {v1 - v0:.2f} eave {z1:.2f}')
        ws = {n.split('_WIN_')[1] for n in C.lot_names('C02', r'WIN_\d+_\d+')}
        if ws != set(L['windows']):
            e.append(f'C02 windows {sorted(ws)}')
        cls, dg = C.roof_class('C02')
        rz = (C.extra.get('roof', {}).get('C02_ROOF') or {}).get('zmax')
        if cls != 'R2' or rz is None or abs(rz - 19.15) > tol(19.15):
            e.append(f'C02 roof {cls} top {rz} ({dg})')
        ndm = len(C.lot_names('C02', r'DORM_\d+'))
        if ndm != 3:
            e.append(f'C02 dormers {ndm}')
        if norm_text(texts.get('C02_SIGN')) != 'REDERIJ HOLM & ZONEN':
            e.append(f'C02 sign {texts.get("C02_SIGN")!r}')
        if slot0.get('C02_BODY') != 'HC-07':
            e.append(f'C02 material {slot0.get("C02_BODY")}')
        R['G13'] = ok('merge C02+C03 applied') if not e else bad('; '.join(e[:8]))

    # G14 storey additions
    with guard(R, ['G14']):
        e = []
        c4, c2 = C.body_eave('C04'), C.body_eave('C02')
        if c4 is None or abs(c4 - 13.7) > 0.10 or c2 is None or abs(c4 - c2) > 0.05:
            e.append(f'C04 eave {c4} vs C02 {c2}')
        ws = {n.split('_WIN_')[1] for n in C.lot_names('C04', r'WIN_\d+_\d+')}
        if ws != {'2_1', '2_3', '3_1', '4_1'}:
            e.append(f'C04 windows {sorted(ws)}')
        ld = {n.split('_LOAD_')[1] for n in C.lot_names('C04', r'LOAD_\d+')}
        if ld != {'2', '3', '4'}:
            e.append(f'C04 loads {sorted(ld)}')
        ez = C.body_eave('E02')
        if ez is None or abs(ez - 18.0) > 0.10:
            e.append(f'E02 eave {ez}')
        ws = {n.split('_WIN_')[1] for n in C.lot_names('E02', r'WIN_\d+_\d+')}
        if ws != set(lots['E02']['windows']):
            e.append(f'E02 windows {sorted(ws)}')
        rz = (C.extra.get('roof', {}).get('E02_ROOF') or {}).get('zmax')
        if rz is None or abs(rz - 22.95) > tol(22.95):
            e.append(f'E02 roof top {rz}')
        fz = C.body_eave('F03')
        if fz is None or abs(fz - 17.2) > 0.10:
            e.append(f'F03 eave {fz}')
        ws = {n.split('_WIN_')[1] for n in C.lot_names('F03', r'WIN_\d+_\d+')}
        if ws != {'2_2', '3_2', '4_1', '5_1'}:
            e.append(f'F03 windows {sorted(ws)}')
        cls, dg = C.roof_class('F03')
        rz = (C.extra.get('roof', {}).get('F03_ROOF') or {}).get('zmax')
        if cls != 'R5' or rz is None or abs(rz - 18.1) > 0.10:
            e.append(f'F03 roof {cls} top {rz}')
        R['G14'] = ok('CO items 2-4 applied') if not e else bad('; '.join(e[:8]))

    # G15 frontage / projections
    with guard(R, ['G15']):
        e = []
        lim = {'BODY': 0.05, 'ROOF': 0.6, 'WIN': 0.3, 'DOOR': 0.3, 'LOAD': 0.3, 'COL': 0.3,
               'SIGN': 1.5, 'BALC': 1.5, 'HOIST': 1.5, 'DORM': 1.5}
        vmins = {}
        ends = {}
        for rid, row in C.rows.items():
            bl_ = [l for l in row.lots if lots[l].get('built')]
            if bl_:
                ends.setdefault(bl_[0], [False, False])[0] = True
                ends.setdefault(bl_[-1], [False, False])[1] = True
        for lid in C.built:
            r = C.row_of[lid]
            L = lots[lid]
            su = r.seg_u(L['seg'])
            # 2026-10-25: at the open outer end of a row (no neighbour) ROOF and decorative parts may overhang <= 0.6
            fst, lst = ends.get(lid, [False, False])
            q = r.uvz(C.bb(lid + '_BODY'))
            if not q:
                e.append(f'{lid}_BODY missing'); continue
            vmins[lid] = q[1][0]
            if abs(q[1][0]) > 0.05:
                e.append(f'{lid}_BODY v_min {q[1][0]:.3f}')
            for n in S.coll(lid):
                bbn = C.bb(n)
                if not bbn:
                    continue
                qq = r.uvz(bbn)
                cat = n[len(lid) + 1:].split('_')[0] if n.startswith(lid + '_') else ''
                lm = lim.get(cat, 0.6)
                if -qq[1][0] > lm + 1e-6:
                    e.append(f'{n} projects {-qq[1][0]:.2f} > {lm}')
                oh = 0.6 if cat not in ('BODY', 'WIN', 'DOOR', 'LOAD', 'COL', 'BALC', 'DORM') else 0.05
                ulo = su[0] - (oh if fst else 0.05)
                uhi = su[1] + (oh if lst else 0.05)
                if cat not in ('HOIST', 'SIGN') and (qq[0][0] < ulo - 1e-6 or qq[0][1] > uhi + 1e-6):
                    e.append(f'{n} u [{qq[0][0]:.2f},{qq[0][1]:.2f}] beyond lot [{su[0]:.2f},{su[1]:.2f}]')
        for grp in ('AB', 'CD'):
            vv = [v for l, v in vmins.items() if l[0] in grp]
            if vv and max(vv) - min(vv) > 0.05:
                e.append(f'rows {grp} v_min spread {max(vv) - min(vv):.3f}')
        R['G15'] = ok('frontage continuous, projections within limits') if not e else bad('; '.join(e[:8]))

    # G16 party walls
    with guard(R, ['G16']):
        e = []
        ov = C.extra.get('overlap', {})
        nm = C.extra.get('nonmanifold', {})
        for j in ak['joints']:
            l, rr = j['left'], j['right']
            row = C.row_of[l]
            ub = row.u(j['at'])
            ql, qr = row.uvz(C.bb(l + '_BODY')), row.uvz(C.bb(rr + '_BODY'))
            if not ql or not qr:
                e.append(f'{l}/{rr} BODY missing'); continue
            if abs(ql[0][1] - ub) > 0.03 or abs(qr[0][0] - ub) > 0.03:
                e.append(f'{l}/{rr} joint {ql[0][1]:.3f}/{qr[0][0]:.3f} vs {ub:.2f}')
            for a in ('BODY', 'ROOF'):
                for b in ('BODY', 'ROOF'):
                    k = f'{l}_{a}|{rr}_{b}'
                    if a == 'BODY' and b == 'BODY' and k not in ov:
                        e.append(f'{k} overlap not measured')
                    elif ov.get(k, 0) > 0.05:
                        e.append(f'{k} interpenetration {ov[k]:.3f} m3')
        for rid, row in C.rows.items():
            bl = [l for l in row.lots if lots[l].get('built')]
            qf, ql = row.uvz(C.bb(bl[0] + '_BODY')), row.uvz(C.bb(bl[-1] + '_BODY'))
            if not qf or not ql or abs(qf[0][0]) > 0.05 or abs(ql[0][1] - row.length) > 0.05:
                e.append(f'row {rid} ends {qf[0][0] if qf else None}/{ql[0][1] if ql else None} vs 0/{row.length:.2f}')
        for lid in C.built:
            k = nm.get(lid + '_BODY')
            if k is None:
                e.append(f'{lid}_BODY manifold not measured')
            elif k:
                e.append(f'{lid}_BODY non-manifold edges {k}')
        R['G16'] = ok(f'{len(ak["joints"])} joints exact, rows closed, bodies manifold') if not e else bad('; '.join(e[:8]))

    # M14 manifest consistency
    with guard(R, ['M14']):
        R['M14'] = manifest_consistency(C, out)
    return R


def facade_errs(C, lid):
    L = C.lots[lid]
    r = C.row_of[lid]
    e = []
    names = C.lot_names(lid, r'WIN_\d+_\d+')
    ws = {n.split('_WIN_')[1] for n in names}
    if ws != set(L['windows']):
        e.append(f'{lid} windows missing {sorted(set(L["windows"]) - ws)} extra {sorted(ws - set(L["windows"]))}')
    for key in sorted(ws & set(L['windows'])):
        q = r.uvz(C.bb(f'{lid}_WIN_{key}'))
        if not q:
            e.append(f'{lid}_WIN_{key} no bbox'); continue
        (u0, u1), (v0, v1), (z0, z1) = q
        uc, vc, zc = (u0 + u1) / 2, (v0 + v1) / 2, (z0 + z1) / 2
        ut = r.u(L['window_centers_along'][key])
        zt = L['window_floor_z'][key] + 0.90 + L['win_h'] / 2
        if abs(uc - ut) > 0.15 or abs(zc - zt) > 0.20 or abs(vc) > 0.6 or abs((u1 - u0) - L['win_w']) > tol(L['win_w']) \
                or abs((z1 - z0) - L['win_h']) > 0.10:
            e.append(f'{lid}_WIN_{key} c=({uc:.2f},{vc:.2f},{zc:.2f}) want u={ut:.2f} z={zt:.2f}; size {u1 - u0:.2f}x{z1 - z0:.2f}')
    door = C.ob(lid + '_DOOR')
    if L.get('door_axis'):
        q = r.uvz(C.bb(lid + '_DOOR')) if door else None
        if not q:
            e.append(f'{lid}_DOOR missing')
        else:
            uc = sum(q[0]) / 2
            ut = r.u(L['door_center_along'])
            if abs(uc - ut) > 0.20 or q[2][0] > 0.10:
                e.append(f'{lid}_DOOR u={uc:.2f} want {ut:.2f} z_min={q[2][0]:.2f}')
    elif door:
        e.append(f'{lid}_DOOR present but not on sheet')
    lds = C.lot_names(lid, r'LOAD_\d+')
    lf = {n.split('_LOAD_')[1] for n in lds}
    if lf != set(L.get('loads') or []):
        e.append(f'{lid} LOAD floors {sorted(lf)} vs {L.get("loads")}')
    elif lds:
        ut = r.u(L['load_center_along'])
        for n in lds:
            q = r.uvz(C.bb(n))
            if not q or abs(sum(q[0]) / 2 - ut) > 0.20:
                e.append(f'{n} off load axis')
    return e


def roof_errs(C, lid):
    L = C.lots[lid]
    r = C.row_of[lid]
    e = []
    cls, dg = C.roof_class(lid)
    if cls != L['roof']:
        e.append(f'{lid} roof class {cls} vs {L["roof"]} ({dg})')
    elif L['roof'] == 'R1' and L.get('gable'):
        g, d = gable_check(C, lid)
        if not g:
            e.append(f'{lid} gable {L["gable"]}: {d}')
    rz = (C.extra.get('roof', {}).get(lid + '_ROOF') or {}).get('zmax')
    if rz is None or abs(rz - L['top']) > tol(L['top']):
        e.append(f'{lid} roof top {rz} vs {L["top"]}')
    dm = C.lot_names(lid, r'DORM_\d+')
    if len(dm) != (L.get('dormers') or 0):
        e.append(f'{lid} dormers {len(dm)} vs {L.get("dormers") or 0}')
    for n in dm:
        q = r.uvz(C.bb(n))
        if not q:
            e.append(f'{n} no bbox'); continue
        vc, zc = sum(q[1]) / 2, sum(q[2]) / 2
        if not (0 < vc < L['depth'] / 2 and L['eave'] < zc < L['top']):
            e.append(f'{n} centre v={vc:.2f} z={zc:.2f}')
    cols = C.lot_names(lid, r'COL_\d+')
    want = (L['arcade_bays'] + 1) if L.get('arcade_bays') else 0
    if len(cols) != want:
        e.append(f'{lid} columns {len(cols)} vs {want}')
    for n in cols:
        q = r.uvz(C.bb(n))
        if not q or abs(sum(q[1]) / 2) > 0.30 or q[2][0] > 0.10:
            e.append(f'{n} placement')
    h = C.ob(lid + '_HOIST')
    if L.get('hoist'):
        q = r.uvz(C.bb(lid + '_HOIST')) if h else None
        if not q:
            e.append(f'{lid}_HOIST missing')
        else:
            la = L.get('load_center_along')
            ut = r.u(la) if la is not None else C.axis_u(lid, L['load_axis'])
            uc, zc = sum(q[0]) / 2, sum(q[2]) / 2
            if abs(uc - ut) > 0.30 or zc < L['eave'] - 1.2 or not -1.5 <= q[1][0] <= -0.3:
                e.append(f'{lid}_HOIST u={uc:.2f} want {ut:.2f} z={zc:.2f} v_min={q[1][0]:.2f}')
    elif h:
        e.append(f'{lid}_HOIST present but not on sheet')
    b = C.ob(lid + '_BALC')
    if L.get('balcony'):
        B = L['balcony']
        q = r.uvz(C.bb(lid + '_BALC')) if b else None
        if not q:
            e.append(f'{lid}_BALC missing')
        else:
            top = C.extra.get('balc', {}).get(lid + '_BALC')
            fz = C.floor_z(lid, B['floor'])
            a0, a1 = C.axis_u(lid, B['from_axis']), C.axis_u(lid, B['to_axis'])
            if top is None or abs(top - fz) > 0.25:
                e.append(f'{lid}_BALC deck {top} vs floor {fz:.2f}')
            if not (q[0][0] <= a0 - 0.6 and q[0][1] >= a1 + 0.6 and q[0][0] >= a0 - 1.2 and q[0][1] <= a1 + 1.2):
                e.append(f'{lid}_BALC u [{q[0][0]:.2f},{q[0][1]:.2f}] axes {a0:.2f}-{a1:.2f}')
            if not -1.2 <= q[1][0] <= -0.8:
                e.append(f'{lid}_BALC v_min {q[1][0]:.2f}')
    elif b:
        e.append(f'{lid}_BALC present but not on sheet')
    return e


def manifest_consistency(C, out):
    man = load_manifest(out)
    if not isinstance(man, list):
        return bad('manifest missing/not a list')
    by = {m.get('id'): m for m in man if isinstance(m, dict)}
    e = []
    texts = C.extra.get('text', {})
    slot0 = C.extra.get('slot0', {})
    for lid, L in C.lots.items():
        m = by.get(lid)
        if not m:
            e.append(f'{lid} not in manifest'); continue
        p = m.get('params') or {}
        if not L.get('built'):
            if m.get('built') is not False or p.get('merged_into') != L.get('merged_into'):
                e.append(f'{lid} should be built:false merged_into {L.get("merged_into")}')
            continue
        if m.get('built') is not True:
            e.append(f'{lid} built={m.get("built")}'); continue
        ws = {n.split('_WIN_')[1] for n in C.lot_names(lid, r'WIN_\d+_\d+')}
        if set(p.get('windows') or []) != ws:
            e.append(f'{lid} windows manifest!=scene')
        fl = [int(k.split('_')[0]) for k in ws] + [int(n.split('_LOAD_')[1]) for n in C.lot_names(lid, r'LOAD_\d+')]
        st = max(fl) if fl else None
        ev = C.body_eave(lid)
        if p.get('storeys') != st or ev is None or abs(ev - (L['h1'] + (st - 1) * L['hu'] if st else 0)) > tol(ev):
            e.append(f'{lid} storeys manifest {p.get("storeys")} scene {st} eave {ev}')
        cls, _ = C.roof_class(lid)
        if cls is not None and p.get('roof') != cls:  # undecided roof form is penalised by G07-G12 only
            e.append(f'{lid} roof manifest {p.get("roof")} scene {cls}')
        if norm_text(p.get('sign_text')) != norm_text(texts.get(lid + '_SIGN')):
            e.append(f'{lid} sign_text mismatch')
        if p.get('colour') != slot0.get(lid + '_BODY'):
            e.append(f'{lid} colour manifest {p.get("colour")} scene {slot0.get(lid + "_BODY")}')
    return ok('manifest agrees with scene') if not e else bad('; '.join(e[:8]))


def _file_items(ctx):
    out = pathlib.Path(ctx['out'])
    R = {}
    e = []
    for n in ('overview', 'quay', 'market'):
        p = out / 'renders' / f'{n}.png'
        if not p.exists():
            e.append(f'{n}.png missing'); continue
        sz = png_size(p)
        if sz != (1920, 1080):
            e.append(f'{n}.png size {sz}'); continue
        sd = png_std(p)
        if sd is None or sd <= 8:
            e.append(f'{n}.png blank/undecodable (std={sd})')
    R['B04'] = ok('3 renders 1920x1080 non-blank') if not e else bad('; '.join(e))
    man = load_manifest(out)
    e = []
    ids = {f'{z}{i:02d}' for z in 'ABCDEF' for i in range(1, 6)}
    if not isinstance(man, list):
        e.append('manifest.json missing or not an array')
    else:
        if len(man) != 30:
            e.append(f'{len(man)} entries')
        got = {m.get('id') for m in man if isinstance(m, dict)}
        if got != ids:
            e.append(f'id set mismatch (missing {sorted(ids - got)[:5]})')
        for m in man:
            if not isinstance(m, dict) or not all(k in m for k in ('id', 'collection', 'built', 'params')) \
                    or not isinstance(m.get('built'), bool):
                e.append(f'bad entry {str(m)[:60]}'); break
    R['B06'] = ok('manifest: 30 well-formed entries') if not e else bad('; '.join(e))
    return R


def _info(ak):
    lots = {}
    rows = {k: Row(k, v) for k, v in ak['rows'].items()}
    for rid, r in rows.items():
        for l in r.lots:
            lots[l] = {'ax': r.ax, 'bax': r.bax, 'bl': r.bl, 'vs': r.vs}
    built = [k for k, v in ak['lots'].items() if v.get('built')]
    pairs = []
    for j in ak['joints']:
        for a in ('BODY', 'ROOF'):
            for b in ('BODY', 'ROOF'):
                pairs.append([f'{j["left"]}_{a}', f'{j["right"]}_{b}'])
    furn = [f['id'] for f in ak['furniture'] if f['kind'] in ('LAMP', 'BOLLARD')]
    return {'lots': lots, 'bodies': [l + '_BODY' for l in built], 'pairs': pairs, 'furn': furn}


def run(ctx):
    R = {}
    items = [i['id'] for i in ctx['items']]
    try:
        R.update(_file_items(ctx))
    except Exception as ex:
        R['B04'] = bad(f'error {ex}'); R['B06'] = bad(f'error {ex}')
    scene_ids = [i for i in items if i not in FILE_ITEMS and i != 'G17']
    try:
        extra = EXTRA_PY.replace('__INFO__', repr(json.dumps(_info(ctx['answer']))))
        S = Scene.load(ctx, frames=list(range(1, 241, 4)), anim_regex=r'^SITE_BOAT_\d+$', extra_py=extra)
    except Exception as ex:
        S = Scene(None, f'scene load error: {ex}')
    if S.err or not S.data:
        for i in scene_ids:
            R[i] = bad(f'scene unavailable: {S.err}')
        return R
    C = Ctx(ctx, S)
    try:
        sr = _scene_items(C, ctx['out'], items)
    except Exception:
        import traceback
        tb = traceback.format_exc()[-500:]
        sr = {}
        # fall back to per-item isolation
        for i in scene_ids:
            sr[i] = bad('checks error: ' + tb)
    for i in scene_ids:
        R[i] = sr.get(i, bad('not evaluated'))
    xerr = (S.data.get('extra') or {}).get('err')
    if xerr:
        R.setdefault('B01', ok())['detail'] += f' | extra_py warnings: {xerr[:3]}'
    return R


def postprocess(results, ctx):
    items = ctx['items']
    zone_ids = {f'M{i:02d}' for i in range(1, 13)} | {f'G{i:02d}' for i in range(1, 17)}
    results = gate_group(results, items, ['B01'], lambda it: it['id'] not in ('B04', 'B06'),
                         'gate: B01 failed (scene.blend not openable / not metric)')
    results = gate_group(results, items, ['B02'], lambda it: it['id'] in zone_ids,
                         'gate: B02 failed (collection contract)')
    return results
