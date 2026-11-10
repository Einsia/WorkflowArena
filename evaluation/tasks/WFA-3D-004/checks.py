# -*- coding: utf-8 -*-
"""BLD-W04 cathedral: deterministic checks (B01-B08, M01-M11, G01-G13). G14 (VLM blind review) is left to the judge.

One Blender extraction (_bld_extract.py) with:
  verts_regex  -> FLY / CULEE / BUTT (I3 landing), R01 ROSE (I4 PCA), N03/N04 LIGHT (window-head form)
  extra_py     -> material glass properties, camera intrinsics, horizontal sections (PIER z=1.0, TURRET, A01 wall z=5),
                  BVH ray casts (G08 arcade/vault profiles, G11 crowns + shared lines, M11 window openings, G01 tower bands).
All interpretation of the raw numbers happens here in pure Python so it can be smoke-tested with a synthetic extract.
"""
import json, math, os, re, struct, zlib, random
from _bld_lib import Scene, ok, bad, close, png_size, load_manifest, gate_group

UNITS = ['A01', 'E01', 'E02', 'E03', 'E04', 'F01', 'F02', 'F03', 'F04', 'K01', 'K02', 'K03', 'L01', 'L02', 'L03', 'L04',
         'N01', 'N02', 'N03', 'N04', 'N05', 'N06', 'N07', 'N08', 'P01', 'Q01', 'Q02', 'Q03', 'R01', 'R02', 'R03', 'T01', 'T02', 'X01']
GEO = ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')
CODES = ['PIER', 'RIB', 'TRI', 'WIN', 'LIGHT', 'DOOR', 'NICHE', 'KING', 'PORTAL', 'BUTT', 'CULEE', 'FLY', 'PINN', 'SPIRE',
         'ROSE', 'TURRET']
G11_ZMAX = 27.0   # below the roofs (cornice 27.5); vault webs / bosses / transverse arches all lie below
VAULT_UNITS = ['N01', 'N02', 'N03', 'N04', 'N05', 'N06', 'N07', 'N08', 'X01', 'E01', 'E02', 'E03', 'E04', 'Q01', 'Q02', 'Q03', 'A01']


def line_x(k):
    return -63.0 + 7.0 * (k - 1)


# shared grid lines for I2: (name, unitA, unitB, axis, coord, sample positions s along the line).
# |s|<=4 keeps every sample clear of the piers (nave piers r=0.8 at |s|=7, crossing piers r=1.2 at |s|=7).
# N02|N03 and N04|N05: CO-01 makes N03/N04 round (spring 19) while N02/N05 stay pointed (spring 18), so the two
# profiles legitimately differ off-axis; only the crown sample s=0 is compared there.
LINE_S = [-4.0, -2.0, 0.0, 2.0, 4.0]
CO_LINES = ('N02|N03', 'N04|N05')


def shared_lines():
    L = []
    for k in range(1, 8):
        L.append(('N%02d|N%02d' % (k, k + 1), 'N%02d' % k, 'N%02d' % (k + 1), 'x', line_x(k + 1)))
    L += [('N08|X01', 'N08', 'X01', 'x', -7.0), ('X01|Q01', 'X01', 'Q01', 'x', 7.0),
          ('Q01|Q02', 'Q01', 'Q02', 'x', 14.0), ('Q02|Q03', 'Q02', 'Q03', 'x', 21.0),
          ('Q03|A01', 'Q03', 'A01', 'x', 28.0),
          ('X01|E01', 'X01', 'E01', 'y', 7.0), ('E01|E02', 'E01', 'E02', 'y', 14.0),
          ('X01|E03', 'X01', 'E03', 'y', -7.0), ('E03|E04', 'E03', 'E04', 'y', -14.0)]
    return [(n, a, b, ax, c, [0.0] if n in CO_LINES else list(LINE_S)) for n, a, b, ax, c in L]


def crown_points():
    P = {}
    for k in range(1, 9):
        P['N%02d' % k] = (line_x(k) + 3.5, 0.0)
    P['X01'] = (0.0, 0.0)
    P.update({'E01': (0.0, 10.5), 'E02': (0.0, 17.5), 'E03': (0.0, -10.5), 'E04': (0.0, -17.5),
              'Q01': (10.5, 0.0), 'Q02': (17.5, 0.0), 'Q03': (24.5, 0.0), 'A01': (28.5, 0.0)})
    return P


EXTRA_PY = r'''
import re, json, random
from mathutils.bvhtree import BVHTree
CFG = json.loads(__CFG__)
ERR = []
EXTRA['err'] = ERR
GEO = ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')
C = bpy.data.collections

def _hidden(o):
    # boolean cutters / helper volumes: not rendered or drawn as bounds/wire -> not part of the built geometry
    return bool(o.hide_render) or o.display_type in ('BOUNDS', 'WIRE')

def uobjs(uid, real_only=False):
    c = C.get(uid)
    if not c:
        return []
    out = []
    for o in c.all_objects:
        if o.type in GEO or (not real_only and o.type == 'EMPTY' and o.instance_type == 'COLLECTION' and o.instance_collection):
            out.append(o)
    return out

# instanced geometry (collection instances, geometry-nodes instances) grouped by instancer name; the instance object is
# only valid while iterating, so its world vertices / polygons are copied out here
INST = {}
try:
    _nv = 0
    for oi in dg.object_instances:
        if not oi.is_instance or oi.parent is None or _nv > 3000000:
            continue
        src = oi.object
        if src.type not in GEO:
            continue
        try:
            me = src.to_mesh()
        except Exception:
            continue
        if me is None:
            continue
        mw = oi.matrix_world.copy()
        vs = [mw @ v.co for v in me.vertices]
        ps = [tuple(p.vertices) for p in me.polygons]
        es = [tuple(e.vertices) for e in me.edges]
        src.to_mesh_clear()
        _nv += len(vs)
        INST.setdefault(oi.parent.name, []).append((vs, ps, es))
except Exception as e:
    ERR.append('instances: %r' % e)

def _merge(parts):
    V, P, Ed = [], [], []
    for vs, ps, es in parts:
        off = len(V); V += vs
        P += [tuple(i + off for i in p) for p in ps]
        Ed += [(a + off, b + off) for a, b in es]
    return V, P, Ed

def mesh_world(o):
    """evaluated world geometry of o, plus any instances it generates (GN instances / collection instance)."""
    parts = []
    if o.type in GEO:
        ev = o.evaluated_get(dg)
        try:
            me = ev.to_mesh()
        except Exception:
            me = None
        if me is not None:
            mw = ev.matrix_world.copy()
            parts.append(([mw @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons],
                          [tuple(e.vertices) for e in me.edges]))
            ev.to_mesh_clear()
    parts += INST.get(o.name, [])
    return _merge(parts)

_B = {}
def bvh(uids, excl):
    key = (tuple(uids), excl)
    if key in _B:
        return _B[key]
    r = re.compile(excl) if excl else None
    V, P = [], []
    for uid in uids:
        for o in uobjs(uid):
            if (r and r.search(o.name)) or _hidden(o):
                continue
            vs, ps, _ = mesh_world(o)
            off = len(V); V += vs; P += [tuple(i + off for i in p) for p in ps]
    t = BVHTree.FromPolygons(V, P) if P else None
    _B[key] = t
    return t

def ray(t, o, d, dist=200.0):
    if t is None:
        return None
    h = t.ray_cast(Vector(o), Vector(d).normalized(), dist)
    if h[0] is None:
        return None
    return [round(h[0].x, 4), round(h[0].y, 4), round(h[0].z, 4)]

def ray_hits_z(t, o, zmax, n=8):
    """z of every surface an upward ray from o crosses below zmax (in order)."""
    out = []
    if t is None:
        return out
    p = Vector(o)
    for _ in range(n):
        h = t.ray_cast(p, Vector((0.0, 0.0, 1.0)), zmax - p.z)
        if h[0] is None:
            break
        out.append(round(h[0].z, 4))
        p = Vector((p.x, p.y, h[0].z + 1e-3))
        if p.z >= zmax:
            break
    return out

def section(o, z, cap=800, step=0.03):
    """horizontal section of o at height z: polygon/plane intersection segments, densified every `step` m.
    Half-open crossing test so a vertex loop lying exactly at z still yields the outline."""
    vs, ps, es = mesh_world(o)
    pts = []
    for poly in ps:
        cr = []
        k = len(poly)
        for i in range(k):
            a, b = vs[poly[i]], vs[poly[(i + 1) % k]]
            za, zb = a.z - z, b.z - z
            if (za < 0) != (zb < 0):
                cr.append(a + (b - a) * (za / (za - zb)))
        if len(cr) < 2:
            continue
        if len(cr) > 2:
            c0 = cr[0].copy(); d = cr[1] - cr[0]
            cr.sort(key=lambda q: (q - c0).dot(d))
        for j in range(0, len(cr) - 1, 2):
            p, q = cr[j], cr[j + 1]
            m = max(1, int((q - p).length / step))
            for i in range(m + 1):
                r = p + (q - p) * (i / m)
                pts.append([round(r.x, 4), round(r.y, 4)])
    if not ps:  # wire-only geometry: edge crossings
        for a, b in es:
            za, zb = vs[a].z - z, vs[b].z - z
            if (za < 0) != (zb < 0):
                r = vs[a] + (vs[b] - vs[a]) * (za / (za - zb))
                pts.append([round(r.x, 4), round(r.y, 4)])
    if len(pts) > cap:
        st = len(pts) // cap + 1
        pts = pts[::st]
    return pts

# ---- materials
try:
    M = {}
    for m in bpy.data.materials:
        d = {'transmission': 0.0, 'alpha': 1.0, 'emission': 0.0, 'nodes': [], 'blend': getattr(m, 'blend_method', '')}
        try:
            d['alpha'] = float(m.diffuse_color[3])
        except Exception:
            pass
        if m.use_nodes and m.node_tree:
            for n in m.node_tree.nodes:
                d['nodes'].append(n.type)
                if n.type == 'BSDF_PRINCIPLED':
                    for k, key in (('Transmission Weight', 'transmission'), ('Transmission', 'transmission'), ('Alpha', 'alpha')):
                        if k in n.inputs:
                            d[key] = float(n.inputs[k].default_value)
                    es = 0.0
                    if 'Emission Strength' in n.inputs:
                        es = float(n.inputs['Emission Strength'].default_value)
                    col = None
                    for k in ('Emission Color', 'Emission'):
                        if k in n.inputs:
                            try:
                                col = list(n.inputs[k].default_value)[:3]
                            except Exception:
                                pass
                    if col is not None and max(col) <= 0:
                        es = 0.0
                    d['emission'] = max(d['emission'], es)
        M[m.name] = d
    EXTRA['mat'] = M
except Exception as e:
    ERR.append('mat: %r' % e)

# ---- cameras
try:
    EXTRA['cam'] = {}
    for o in scene.objects:
        if o.type == 'CAMERA':
            c = o.data
            EXTRA['cam'][o.name] = {'type': c.type, 'sensor_fit': c.sensor_fit, 'sensor_width': c.sensor_width,
                                    'sensor_height': c.sensor_height, 'lens': c.lens, 'shift_x': c.shift_x,
                                    'shift_y': c.shift_y, 'ortho_scale': c.ortho_scale}
except Exception as e:
    ERR.append('cam: %r' % e)

# ---- sections: piers z=1.0 (+ vertex centroid z in [0,2]); turrets; apse wall z=5
S = {}; PC = {}
for o in scene.objects:
    if o.type not in GEO:
        continue
    try:
        if re.search(r'_PIER_', o.name):
            S[o.name] = section(o, 1.0)
            vs, _, _ = mesh_world(o)
            low = [v for v in vs if 0.0 <= v.z <= 2.0]
            if low:
                PC[o.name] = [round(sum(v.x for v in low) / len(low), 4), round(sum(v.y for v in low) / len(low), 4)]
        elif re.match(r'^R0[23]_TURRET_', o.name):
            pts = section(o, 10.0)
            if len(pts) < 3:
                pts = section(o, 15.0)
            S[o.name] = pts
    except Exception as e:
        ERR.append('sec %s: %r' % (o.name, e))
EXTRA['sec'] = S; EXTRA['pier_c'] = PC
try:
    pts = []
    for o in uobjs('A01'):
        if not re.search(r'_(LIGHT|WIN|RIB|ROSE|NICHE|PIER)_', o.name) and not _hidden(o):
            pts += [p for p in section(o, 5.0, cap=3000) if p[0] > 28.05]
    EXTRA['apse_sec'] = pts
except Exception as e:
    ERR.append('apse_sec: %r' % e)

# ---- G08: N03/N04 arcade intrados (upward rays along both arcade axes) + vault transverse profile + crown
try:
    G8 = {}
    for uid, x0, x1 in CFG['g08']:
        t = bvh([uid], r'_(LIGHT|ROSE)_')
        d = {'arc': {}, 'vault': {}}
        for side, y in (('N', 7.0), ('S', -7.0)):
            prof = []
            n = int(round((x1 - x0) / 0.05))
            for i in range(n + 1):
                x = x0 + 0.05 * i
                h = ray(t, (x, y, 0.3), (0, 0, 1))
                prof.append([round(x, 3), h[2] if h else None])
            d['arc'][side] = prof
        for tag, x in (('w', x0 + 0.03), ('e', x1 - 0.03)):
            row = {}
            for yy in (-5.5, -4.0, 0.0, 4.0, 5.5):
                h = ray(t, (x, yy, 1.0), (0, 0, 1))
                row['%.1f' % yy] = h[2] if h else None
            d['vault'][tag] = row
        h = ray(t, ((x0 + x1) / 2, 0.0, 1.0), (0, 0, 1))
        d['crown'] = h[2] if h else None
        G8[uid] = d
    EXTRA['g08'] = G8
except Exception as e:
    ERR.append('g08: %r' % e)

# ---- G11: every surface an upward ray crosses below z=27.0 (bay centre; both sides of each shared line, each unit
#      only against its own non-glass geometry). Bosses / transverse arches below the web just add extra hits.
try:
    ZC = CFG['g11_zmax']
    cr = {}
    for uid, (x, y) in CFG['crowns'].items():
        cr[uid] = ray_hits_z(bvh([uid], r'_(LIGHT|ROSE)_'), (x, y, 1.0), ZC)
    lines = {}
    for name, ua, ub, ax, c, ss in CFG['lines']:
        ta = bvh([ua], r'_(LIGHT|ROSE|RIB)_'); tb = bvh([ub], r'_(LIGHT|ROSE|RIB)_')
        smp = []
        for s in ss:
            if ax == 'x':
                pa, pb = (c - 0.05, s, 1.0), (c + 0.05, s, 1.0)
            else:
                pa, pb = (s, c - 0.05 if c > 0 else c + 0.05, 1.0), (s, c + 0.05 if c > 0 else c - 0.05, 1.0)
            smp.append([s, ray_hits_z(ta, pa, ZC), ray_hits_z(tb, pb, ZC)])
        lines[name] = smp
    EXTRA['g11'] = {'crown': cr, 'lines': lines}
except Exception as e:
    ERR.append('g11: %r' % e)

# ---- M11: 12 LIGHT objects, fixed seed, round-robin over units; rays along PCA normal through the light centre
def _min_axis(P):
    # pure-python PCA (Blender 4.3.2 from Debian runs on system Python 3.13 without numpy): eigenvector of the
    # smallest eigenvalue of the 3x3 covariance matrix via cyclic Jacobi rotations (same as numpy eigh column 0)
    import math
    k = float(len(P)); c = [sum(p[i] for p in P) / k for i in range(3)]
    M = [[sum((p[i] - c[i]) * (p[j] - c[j]) for p in P) / k for j in range(3)] for i in range(3)]
    V = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for _ in range(60):
        off = abs(M[0][1]) + abs(M[0][2]) + abs(M[1][2])
        if off < 1e-15:
            break
        for a, b in ((0, 1), (0, 2), (1, 2)):
            if abs(M[a][b]) < 1e-18:
                continue
            th = 0.5 * math.atan2(2.0 * M[a][b], M[b][b] - M[a][a])
            cs, sn = math.cos(th), math.sin(th)
            for r in range(3):
                mra, mrb = M[r][a], M[r][b]
                M[r][a], M[r][b] = cs * mra - sn * mrb, sn * mra + cs * mrb
            for r in range(3):
                mar, mbr = M[a][r], M[b][r]
                M[a][r], M[b][r] = cs * mar - sn * mbr, sn * mar + cs * mbr
            for r in range(3):
                vra, vrb = V[r][a], V[r][b]
                V[r][a], V[r][b] = cs * vra - sn * vrb, sn * vra + cs * vrb
    i0 = min(range(3), key=lambda i: M[i][i])
    return Vector((V[0][i0], V[1][i0], V[2][i0])), Vector(c)


try:
    import math
    by = {}
    for uid in CFG['units']:
        L = sorted(o.name for o in uobjs(uid) if re.match(r'^%s_LIGHT_\d+$' % uid, o.name))
        if L:
            by[uid] = L
    rng = random.Random(20261025)
    us = sorted(by); rng.shuffle(us)
    for uid in us:
        rng.shuffle(by[uid])
    pick = []
    while len(pick) < 12 and any(by.values()):
        for uid in us:
            if by[uid] and len(pick) < 12:
                pick.append((uid, by[uid].pop()))
    res = []
    for uid, nm in pick:
        o = bpy.data.objects[nm]
        vs, _, _ = mesh_world(o)
        if len(vs) < 3:
            res.append({'name': nm, 'unit': uid, 'clear': False, 'why': 'no verts'}); continue
        n, c = _min_axis([(v.x, v.y, v.z) for v in vs]); n = n.normalized()
        t = bvh([uid], r'_(LIGHT|ROSE|WIN|TRI)_')
        h1 = ray(t, c + n * 1.0, -n, 2.5); h2 = ray(t, c - n * 1.0, n, 2.5)
        res.append({'name': nm, 'unit': uid, 'clear': (h1 is None) or (h2 is None), 'hit_out': h1, 'hit_in': h2})
    EXTRA['m11'] = res
except Exception as e:
    ERR.append('m11: %r' % e)

# ---- G01: tower string courses: horizontal rays toward the tower centre on each face, at the face midline and at
#      +-1/3 of the face width (a continuous course shows on all three; belfry sills under the central lancet do not)
try:
    TW = {}
    for uid, cx, cy, top, size in CFG['towers']:
        t = bvh([uid], r'_(LIGHT|WIN|PINN|SPIRE|PORTAL|ROSE)_')
        faces = {}
        for fn, dx, dy in (('W', -1, 0), ('E', 1, 0), ('N', 0, 1), ('S', 0, -1)):
            faces[fn] = {}
            for off in (-size / 3.0, 0.0, size / 3.0):
                ox, oy = (0.0, off) if dx else (off, 0.0)
                prof = []
                z = 0.5
                while z <= top - 0.5 + 1e-9:
                    h = ray(t, (cx + ox + dx * 10.0, cy + oy + dy * 10.0, z), (-dx, -dy, 0), 10.0)
                    prof.append(None if h is None else round((h[0] - cx) * dx + (h[1] - cy) * dy, 4))
                    z += 0.05
                faces[fn]['%.1f' % off] = prof
        TW[uid] = {'z0': 0.5, 'dz': 0.05, 'faces': faces}
    EXTRA['tower'] = TW
except Exception as e:
    ERR.append('tower: %r' % e)
'''


def extra_cfg(A):
    U = A['units']
    cfg = {'units': UNITS,
           'g08': [[u, U[u]['truth']['x0'], U[u]['truth']['x1']] for u in ('N03', 'N04')],
           'crowns': {k: list(v) for k, v in crown_points().items()},
           'lines': [[n, a, b, ax, c, ss] for n, a, b, ax, c, ss in shared_lines()], 'g11_zmax': G11_ZMAX,
           'towers': [[u, U[u]['truth']['cx'], U[u]['truth']['cy'], U[u]['truth']['body_top'], U[u]['truth']['size']] for u in ('T01', 'T02')]}
    return EXTRA_PY.replace('__CFG__', repr(json.dumps(cfg)))


# ======================================================================= helpers
def safe(fn):
    def w(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:
            import traceback
            return bad('check error: %r %s' % (e, traceback.format_exc()[-300:]))
    return w


def geo_objs(S, uid):
    return [n for n in S.coll(uid) if (S.ob(n) or {}).get('type') in GEO]


def named(S, uid, code):
    """countable objects <UID>_<CODE>_<nn>: geometry objects, or an EMPTY that instances geometry (collection instance)."""
    r = re.compile(r'^%s_%s_\d+$' % (uid, code))
    insts = {i.get('instancer') for i in (S.data or {}).get('instances') or []}
    return [n for n in S.coll(uid) if r.match(n) and ((S.ob(n) or {}).get('type') in GEO
                                                      or ((S.ob(n) or {}).get('type') == 'EMPTY' and n in insts))]


def cnt(S, uid, code):
    return len(named(S, uid, code))


def inst_boxes(S, uid):
    """world bboxes of instanced geometry (collection / geometry-nodes instances) whose instancer is in the unit."""
    return _inst_of(S, set(S.coll(uid)))


def _inst_of(S, names):
    return [i['bbox_world'] for i in (S.data or {}).get('instances') or []
            if i.get('instancer') in names and i.get('bbox_world') and i.get('type') in GEO]


def _union(bs):
    bs = [b for b in bs if b]
    if not bs:
        return None
    return [[min(x[0][i] for x in bs) for i in range(3)], [max(x[1][i] for x in bs) for i in range(3)]]


def bb(S, names):
    """union world bbox of the named objects: own evaluated geometry (objects whose evaluated mesh is empty, e.g. a
    geometry-nodes carrier that only emits instances, contribute no box of their own) plus the instances they emit."""
    names = list(names)
    own = []
    for n in names:
        o = S.ob(n) or {}
        if o.get('type') in GEO and o.get('bbox_world') and o.get('n_verts', 1) != 0:
            own.append(o['bbox_world'])
    return _union(own + _inst_of(S, set(names)))


def unit_bbox(S, uid):
    """union bbox of a unit's geometry objects plus the unit's instanced geometry."""
    return bb(S, S.coll(uid))


def unit_zmax(S, uid):
    b = unit_bbox(S, uid)
    return b[1][2] if b else None


def cen(S, n):
    b = bb(S, [n])
    return Scene.center(b) if b else None


def zmax(S, names):
    b = bb(S, names)
    return b[1][2] if b else None


def png_nonblank(p):
    """grayscale std > 8; PIL if available else a small pure-python PNG decoder (8-bit, non-interlaced)."""
    try:
        from PIL import Image
        im = Image.open(p).convert('L')
        im.thumbnail((480, 270))
        px = list(im.getdata())
    except ImportError:
        px = _png_gray(p)
    if not px:
        return None
    m = sum(px) / len(px)
    return math.sqrt(sum((v - m) ** 2 for v in px) / len(px))


def _png_gray(p):
    data = open(p, 'rb').read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    pos, idat, w = 8, b'', None
    while pos < len(data):
        ln, = struct.unpack('>I', data[pos:pos + 4]); typ = data[pos + 4:pos + 8]; body = data[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', body)
        elif typ == b'IDAT':
            idat += body
        pos += 12 + ln
    if bd != 8 or il != 0 or ct not in (0, 2, 4, 6):
        return None
    bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(idat); stride = w * bpp
    prev = bytearray(stride); out = []; i = 0
    for y in range(h):
        f = raw[i]; line = bytearray(raw[i + 1:i + 1 + stride]); i += 1 + stride
        if f == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 255
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif f == 3:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif f == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0; b = prev[x]; c = prev[x - bpp] if x >= bpp else 0
                pp = a + b - c; pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        if y % 8 == 0:
            out += [line[x] for x in range(0, stride, bpp * 8)]
        prev = line
    return out


# ---- 2D shape helpers
def hull(pts):
    P = sorted(set((round(p[0], 5), round(p[1], 5)) for p in pts))
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


def hull_corners(pts, turn_deg=12.0, merge=0.0):
    """number of corners of the convex hull: the turning angle at each hull vertex is measured between neighbours at
    least `merge` away along the hull (so densified straight edges and rounding jitter do not split a corner), and a
    run of consecutive vertices above `turn_deg` counts as one corner."""
    H = hull(pts)
    n = len(H)
    if n < 3:
        return 0
    seg = [math.hypot(H[(i + 1) % n][0] - H[i][0], H[(i + 1) % n][1] - H[i][1]) for i in range(n)]
    per = sum(seg)
    w = min(merge, per / 16.0) if merge > 0 else 0.0
    mark = []
    for i in range(n):
        j, d = i, 0.0
        while True:
            j = (j - 1) % n; d += seg[j]
            if d >= w or j == (i + 1) % n:
                break
        k, d = i, 0.0
        while True:
            d += seg[k]; k = (k + 1) % n
            if d >= w or k == (i - 1) % n:
                break
        a, b, c = H[j], H[i], H[k]
        a1 = math.atan2(b[1] - a[1], b[0] - a[0]); a2 = math.atan2(c[1] - b[1], c[0] - b[0])
        mark.append(abs((math.degrees(a2 - a1) + 180) % 360 - 180) >= turn_deg)
    # a marked vertex starts a new corner unless the previous vertex is marked and lies within 2*w (same corner)
    same = [mark[i] and mark[(i - 1) % n] and seg[(i - 1) % n] < 2 * w for i in range(n)]
    if all(same):
        return 1 if n else 0
    return sum(1 for i in range(n) if mark[i] and not same[i])


def radial_profile(pts, nb=72, c=None):
    if c is None:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    r = [None] * nb
    for x, y in pts:
        a = math.atan2(y - c[1], x - c[0]) % (2 * math.pi)
        k = int(a / (2 * math.pi) * nb) % nb
        d = math.hypot(x - c[0], y - c[1])
        if r[k] is None or d > r[k]:
            r[k] = d
    # fill gaps by nearest neighbour
    if all(v is None for v in r):
        return r
    for k in range(nb):
        if r[k] is None:
            for s in range(1, nb):
                for kk in ((k + s) % nb, (k - s) % nb):
                    if r[kk] is not None:
                        r[k] = r[kk]; break
                if r[k] is not None:
                    break
    return r


def peaks(r, win, prom):
    n = len(r); c = 0
    for i in range(n):
        nb = [r[(i + j) % n] for j in range(-win, win + 1)]
        if r[i] >= max(nb) and r[i] > r[(i - 1) % n] - 1e-9 and r[i] - min(nb) >= prom:
            # count flat plateaus once
            if r[(i - 1) % n] == r[i]:
                continue
            c += 1
    return c


def concave_frac(pts, tol):
    """fraction of section points lying deeper than tol inside the convex hull (compound piers are concave)."""
    H = hull(pts)
    if len(H) < 3:
        return 0.0
    def dseg(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]; L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
    deep = sum(1 for p in pts if min(dseg(p, H[i - 1], H[i]) for i in range(len(H))) > tol)
    return deep / len(pts)


def pier_class(pts):
    if not pts or len(pts) < 6:
        return None, 'no section'
    r = radial_profile(pts, 72)
    mean = sum(r) / len(r)
    dev = (max(r) - min(r)) / mean
    hc8 = hull_corners(pts, 12.0, merge=0.02 * mean)
    if hc8 == 8 and concave_frac(pts, 0.04 * mean) < 0.1:
        return 'OCT', 'dev=%.3f hull=8' % dev
    if dev < 0.05:
        return 'CYL', 'dev=%.3f' % dev
    pk = peaks(r, 4, 0.12 * mean)
    if pk in (4, 8) and dev > 0.12 and concave_frac(pts, 0.04 * mean) >= 0.1:
        return 'CMP%d' % pk, 'dev=%.3f peaks=%d' % (dev, pk)
    hc = hull_corners(pts, 12.0, merge=0.02 * mean)
    if hc == 8:
        return 'OCT', 'dev=%.3f hull=%d' % (dev, hc)
    return 'UNK', 'dev=%.3f peaks=%d hull=%d' % (dev, pk, hc)


def arch_ratio(profile, pad=0.025):
    """profile: [[s, h or None], ...] intrados/top profile along the span. Returns (rho, detail) with rho = rise/half-span
    estimated from the drop between crown and quarter points (semicircle -> 1.0; pointed -> >1.3)."""
    P = [(s, h) for s, h in profile if h is not None]
    if len(P) < 5:
        return None, 'too few samples'
    hmin = min(h for _, h in P)
    run = [(s, h) for s, h in P if h > hmin + 0.3]
    if len(run) < 5:
        return None, 'no opening'
    # longest contiguous run
    best, cur = [], [run[0]]
    for a, b in zip(run, run[1:]):
        if b[0] - a[0] <= 0.11:
            cur.append(b)
        else:
            best = max(best, cur, key=len); cur = [b]
    best = max(best, cur, key=len)
    s0, s1 = best[0][0], best[-1][0]
    a = (s1 - s0) / 2 + pad; c = (s0 + s1) / 2
    zc = max(h for _, h in best)

    def at(s):
        for (p, hp), (q, hq) in zip(best, best[1:]):
            if p <= s <= q:
                return hp + (hq - hp) * (s - p) / (q - p) if q > p else hp
        return None
    hl, hr = at(c - a / 2), at(c + a / 2)
    if hl is None or hr is None:
        return None, 'interp fail'
    q = zc - (hl + hr) / 2
    rho = q / (a * (1 - math.sqrt(3) / 2))
    return rho, 'half=%.2f crown=%.2f rho=%.2f' % (a, zc, rho)


def upper_profile(verts, axis=0, step=0.05):
    """top outline of a planar object's vertices in (axis, z): upper hull."""
    pts = sorted((v[axis], v[2]) for v in verts)
    up = []
    for p in pts:
        while len(up) >= 2 and ((up[-1][0] - up[-2][0]) * (p[1] - up[-2][1]) - (up[-1][1] - up[-2][1]) * (p[0] - up[-2][0])) >= 0:
            up.pop()
        up.append(p)
    if len(up) < 2:
        return []
    s0, s1 = up[0][0], up[-1][0]
    out = []; s = s0; j = 0
    while s <= s1 + 1e-9:
        while j < len(up) - 2 and up[j + 1][0] < s:
            j += 1
        (p, hp), (q, hq) = up[j], up[j + 1]
        out.append([s, hp + (hq - hp) * (s - p) / (q - p) if q > p else max(hp, hq)])
        s += step
    # add a low baseline at both ends so arch_ratio finds the opening edges
    base = min(v[2] for v in verts)
    return [[s0 - step, base]] + out + [[s1 + step, base]]


def pca_normal(V):
    n = len(V)
    m = [sum(v[i] for v in V) / n for i in range(3)]
    C = [[sum((v[i] - m[i]) * (v[j] - m[j]) for v in V) / n for j in range(3)] for i in range(3)]
    # Jacobi eigen decomposition (3x3 symmetric)
    A = [row[:] for row in C]; E = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for _ in range(50):
        p, q = max(((0, 1), (0, 2), (1, 2)), key=lambda t: abs(A[t[0]][t[1]]))
        if abs(A[p][q]) < 1e-12:
            break
        th = 0.5 * math.atan2(2 * A[p][q], A[q][q] - A[p][p])
        c, s = math.cos(th), math.sin(th)
        for k in range(3):
            akp, akq = A[k][p], A[k][q]
            A[k][p] = c * akp - s * akq; A[k][q] = s * akp + c * akq
        for k in range(3):
            apk, aqk = A[p][k], A[q][k]
            A[p][k] = c * apk - s * aqk; A[q][k] = s * apk + c * aqk
        for k in range(3):
            ekp, ekq = E[k][p], E[k][q]
            E[k][p] = c * ekp - s * ekq; E[k][q] = s * ekp + c * ekq
    i = min(range(3), key=lambda k: A[k][k])
    return m, [E[0][i], E[1][i], E[2][i]]


def rings_of(S, names, plane):
    """ROSE object centres -> radial clusters. plane=('y','z') or ('x','z'). returns (counts inner->outer, dia_from_bbox)"""
    ia = {'x': 0, 'y': 1, 'z': 2}
    a, b = ia[plane[0]], ia[plane[1]]
    cs = [cen(S, n) for n in names]
    cs = [c for c in cs if c]
    if not cs:
        return [], None, None
    ca = sum(c[a] for c in cs) / len(cs); cb = sum(c[b] for c in cs) / len(cs)
    rr = sorted(math.hypot(c[a] - ca, c[b] - cb) for c in cs)
    groups = [[rr[0]]]
    for r in rr[1:]:
        if r - groups[-1][-1] > 0.3:
            groups.append([r])
        else:
            groups[-1].append(r)
    U = bb(S, names)
    dia = max(U[1][a] - U[0][a], U[1][b] - U[0][b]) if U else None
    return [len(g) for g in groups], dia, (ca, cb)


def rose_dia_ok(u, dia, D):
    """R01: diameter of the whole R01 collection (frame included) within +-3% (>=0.15). R02/R03: union bbox of the ROSE
    panes, which sit inside the tracery / frame, so up to 0.8 m smaller than the drawn diameter is accepted."""
    if dia is None:
        return False
    hi = D + max(0.03 * D, 0.15)
    lo = D - max(0.03 * D, 0.15) if u == 'R01' else D - 0.8
    return lo <= dia <= hi


def project(cam_ob, cam_x, res, p):
    M = cam_ob['matrix_world']
    loc = [M[0][3], M[1][3], M[2][3]]
    ax = []
    for i in range(3):
        v = [M[0][i], M[1][i], M[2][i]]; l = math.sqrt(sum(t * t for t in v)) or 1.0
        ax.append([t / l for t in v])
    d = [p[i] - loc[i] for i in range(3)]
    xc, yc, zc = (sum(d[i] * ax[k][i] for i in range(3)) for k in range(3))
    rx, ry = float(res[0]), float(res[1])
    fit = (cam_x or {}).get('sensor_fit', 'AUTO')
    sw = (cam_x or {}).get('sensor_width') or cam_ob.get('sensor_width') or 36.0
    sh = (cam_x or {}).get('sensor_height') or 24.0
    lens = (cam_x or {}).get('lens') or cam_ob.get('lens') or 50.0
    sx, sy = (cam_x or {}).get('shift_x', 0.0), (cam_x or {}).get('shift_y', 0.0)
    if (cam_x or {}).get('type') == 'ORTHO':
        os_ = cam_x.get('ortho_scale', 7.0)
        big = max(rx, ry)
        return 0.5 + xc / os_ * big / rx + sx * big / rx, 0.5 + yc / os_ * big / ry + sy * big / ry, True
    if zc >= -1e-6:
        return None, None, False
    if fit == 'VERTICAL' or (fit == 'AUTO' and ry > rx):
        fy = lens / (sh if fit == 'VERTICAL' else sw)
        v = 0.5 + fy * yc / -zc; u = 0.5 + fy * (ry / rx) * xc / -zc
    else:
        fx = lens / sw
        u = 0.5 + fx * xc / -zc; v = 0.5 + fx * (rx / ry) * yc / -zc
    big = max(rx, ry)
    return u + sx * big / rx, v + sy * big / ry, True


def view_dir(cam_ob):
    M = cam_ob['matrix_world']
    v = [-M[0][2], -M[1][2], -M[2][2]]; l = math.sqrt(sum(t * t for t in v)) or 1.0
    return [t / l for t in v]


def ang(u, v):
    d = sum(a * b for a, b in zip(u, v)) / ((math.sqrt(sum(a * a for a in u)) * math.sqrt(sum(b * b for b in v))) or 1)
    return math.degrees(math.acos(max(-1.0, min(1.0, d))))


def is_glass(md):
    if not md:
        return False
    nodes = set(md.get('nodes') or [])
    return (md.get('transmission', 0) >= 0.5 or md.get('alpha', 1) <= 0.9 or md.get('emission', 0) > 0
            or bool(nodes & {'BSDF_GLASS', 'EMISSION', 'BSDF_TRANSLUCENT', 'BSDF_REFRACTION'}))


# ======================================================================= run
def run(ctx):
    A = ctx['answer']; U = A['units']
    items = [i['id'] for i in ctx['items']]
    out = ctx['out']
    R = {}
    S = Scene.load(ctx, frames=[], islands_regex=None,
                   verts_regex=r'(^[FL]0\d_(FLY|CULEE|BUTT)_\d+$)|(^R01_ROSE_\d+$)|(^N0[34]_LIGHT_\d+$)',
                   extra_py=extra_cfg(A))
    E = (S.data or {}).get('extra') or {}
    scene_items = [i for i in items if i not in ('B05', 'B06', 'B07', 'G14')]
    if S.err:
        for i in scene_items:
            R[i] = bad('scene unavailable: %s' % S.err)
    T = lambda u: U[u]['truth']

    # ---------------------------------------------------------------- files (independent of Blender)
    @safe
    def render_check(files, cams):
        msgs = []; good = True
        for f in files:
            p = os.path.join(str(out), 'renders', f)
            sz = png_size(p)
            if sz != (1920, 1080):
                good = False; msgs.append('%s size=%s' % (f, sz)); continue
            sd = png_nonblank(p)
            if sd is None or sd <= 8:
                good = False; msgs.append('%s std=%s' % (f, sd))
            else:
                msgs.append('%s ok std=%.1f' % (f, sd))
        if S.err:
            good = False; msgs.append('cameras unverifiable: %s' % S.err)
        else:
            site = set(S.coll('SITE'))
            for c in cams:
                o = S.ob(c)
                if not o or o.get('type') != 'CAMERA' or c not in site:
                    good = False; msgs.append('%s missing/not CAMERA/not in SITE' % c)
        return (ok if good else bad)('; '.join(msgs))
    R['B05'] = render_check(['overview.png'], ['CAM_OVERVIEW'])
    R['B06'] = render_check(['nave_push.png', 'chevet.png'], ['CAM_NAVE', 'CAM_CHEVET'])

    man = load_manifest(out)
    mu = {}
    if isinstance(man, dict) and isinstance(man.get('units'), list):
        for e in man['units']:
            if isinstance(e, dict) and 'id' in e:
                mu[e['id']] = e

    @safe
    def b07():
        if man is None:
            return bad('manifest.json missing or unparsable')
        if not isinstance(man.get('units'), list) or len(man['units']) != 34:
            return bad('units list len=%s' % (len(man.get('units', [])) if isinstance(man.get('units'), list) else None))
        if set(mu) != set(UNITS):
            return bad('ids mismatch: missing %s extra %s' % (sorted(set(UNITS) - set(mu)), sorted(set(mu) - set(UNITS))))
        probs = []
        for u in UNITS:
            e = mu[u]
            if e.get('collection') != u:
                probs.append('%s collection=%r' % (u, e.get('collection')))
            if not S.err and not S.has_coll(e.get('collection') or ''):
                probs.append('%s collection not in scene' % u)
            need = set(U[u]['manifest_params'])
            have = set((e.get('params') or {}).keys()) if isinstance(e.get('params'), dict) else set()
            if need - have:
                probs.append('%s missing %s' % (u, sorted(need - have)))
        return bad('; '.join(probs)) if probs else ok('34 units, collections match, all param fields present')
    R['B07'] = b07()

    if S.err:
        return {k: v for k, v in R.items() if k in items}

    # ---------------------------------------------------------------- base
    @safe
    def b01():
        sc = S.data.get('scene') or {}
        if sc.get('unit_system') == 'METRIC' and abs(float(sc.get('scale_length', 0)) - 1.0) < 1e-6:
            return ok('METRIC, scale_length=1.0; blender %s' % S.data.get('blender_version'))
        return bad('unit_system=%s scale_length=%s' % (sc.get('unit_system'), sc.get('scale_length')))
    R['B01'] = b01()

    cols = S.data.get('collections') or {}
    root = next((k for k, v in cols.items() if v.get('parent') is None), None)

    def under(c, targets):
        while c is not None:
            if c in targets:
                return True
            c = cols.get(c, {}).get('parent')
        return False

    @safe
    def b02():
        miss = [u for u in UNITS + ['SITE'] if u not in cols]
        if miss:
            return bad('missing collections: %s' % miss)
        tg = set(UNITS) | {'SITE'}
        rogue = []
        for c, v in cols.items():
            if c in tg or c == root or under(c, tg):
                continue
            if any((S.ob(n) or {}).get('type') == 'MESH' for n in v.get('objects', [])):
                rogue.append(c)
        return bad('other collections holding meshes: %s' % rogue) if rogue else ok('34 unit collections + SITE')
    R['B02'] = b02()

    @safe
    def b03():
        empty = []
        for u in UNITS:
            g = [n for n in S.coll(u) if (S.ob(n) or {}).get('type') == 'MESH' and (S.ob(n).get('n_faces') or 0) > 0]
            g += [n for n in S.coll(u) if (S.ob(n) or {}).get('type') in GEO[1:] and S.ob(n).get('bbox_world')]
            if not g and not inst_boxes(S, u):
                empty.append(u)
        inside = set()
        for u in UNITS + ['SITE']:
            inside |= set(S.coll(u))
        stray = [n for n, o in S.objects.items() if o.get('type') == 'MESH' and n not in inside]
        if empty or stray:
            return bad('empty units %s; stray meshes %s' % (empty, stray[:10]))
        return ok('all 34 non-empty, no stray meshes')
    R['B03'] = b03()

    @safe
    def b04():
        """>=95% of names in unit collections start with '<ID>_'; no malformed countable names, i.e. names that are a
        countable element name except for the format (missing/joined number, Blender '.001' suffix, wrong unit id).
        Free names that merely contain a code as a word (R02_ROSE_FRAME, P01_PORTAL_ARCH) are allowed."""
        tot = good = 0; viol = []
        cand = re.compile(r'^[A-Z]\d\d_(%s)(_?\d*)(\.\d+)?$' % '|'.join(CODES))
        for u in UNITS:
            exact = re.compile(r'^%s_(%s)_\d+$' % (u, '|'.join(CODES)))
            for n in S.coll(u):
                tot += 1
                if n.startswith(u + '_'):
                    good += 1
                if cand.match(n) and not exact.match(n):
                    viol.append(n)
        ratio = good / tot if tot else 0
        if ratio >= 0.95 and not viol:
            return ok('prefix ratio %.3f, 0 malformed countable names' % ratio)
        return bad('prefix ratio %.3f (%d/%d); malformed countable names %d e.g. %s' % (ratio, good, tot, len(viol), viol[:6]))
    R['B04'] = b04()


    @safe
    def b08():
        bs = [x for x in (unit_bbox(S, u) for u in UNITS) if x]
        if not bs:
            return bad('no geometry')
        b = [[min(x[0][i] for x in bs) for i in range(3)], [max(x[1][i] for x in bs) for i in range(3)]]
        c = (abs(b[0][0] + 72.4) <= 1.5 and abs(b[1][0] - 39.96) <= 1.5 and abs(b[0][1] + 23.5) <= 1.5
             and abs(b[1][1] - 23.5) <= 1.5 and 60 <= b[1][2] <= 76)
        return (ok if c else bad)('union bbox x[%.2f,%.2f] y[%.2f,%.2f] zmax %.2f' % (b[0][0], b[1][0], b[0][1], b[1][1], b[1][2]))
    R['B08'] = b08()

    # ---------------------------------------------------------------- mid: placement
    def unit_bbox_ok(u):
        e = U[u]['expected_bbox']; b = unit_bbox(S, u)
        if not b:
            return False, '%s empty' % u
        dev = [b[0][0] - e[0], b[1][0] - e[1], b[0][1] - e[2], b[1][1] - e[3]]
        zs = [72.0, 64.0] if u in ('T01', 'T02') else [e[4]]
        zok = any(close(b[1][2], z, 0.03, 0.3) for z in zs)
        good = all(abs(d) <= 0.8 for d in dev) and zok
        return good, '%s [%.2f,%.2f,%.2f,%.2f,%.2f]%s' % (u, b[0][0], b[1][0], b[0][1], b[1][1], b[1][2], '' if good else ' X')

    zones = {z['id']: z['units'] for z in A['zones']}
    for mid, z in zip(['M01', 'M02', 'M03', 'M04', 'M05', 'M06', 'M07'], ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7']):
        @safe
        def mz(z=z):
            rs = [unit_bbox_ok(u) for u in zones[z]]
            return (ok if all(r[0] for r in rs) else bad)('; '.join(r[1] for r in rs))
        R[mid] = mz()

    # ---------------------------------------------------------------- measured quantities used by M08 / G*
    def rose_meas(u):
        names = named(S, u, 'ROSE')
        plane = ('y', 'z') if u == 'R01' else ('x', 'z')
        rings, dia, c = rings_of(S, names, plane)
        if u == 'R01':
            b = unit_bbox(S, 'R01')
            if b:
                dia = max(b[1][1] - b[0][1], b[1][2] - b[0][2])
        return rings, dia

    def spire_top(u):
        return zmax(S, named(S, u, 'SPIRE'))

    def body_top(u):
        ns = [n for n in geo_objs(S, u) if not re.match(r'^%s_(SPIRE|PINN)_' % u, n)]
        ns = [n for n in ns if (bb(S, [n]) or [[0, 0, 0]])[0][2] < T(u)['body_top'] - 0.3]
        return zmax(S, ns)

    def butt_top(u):
        bs = named(S, u, 'BUTT')
        zs = [zmax(S, [n]) for n in bs]
        return sorted(zs)[len(zs) // 2] if zs else None

    # ---------------------------------------------------------------- M08 manifest vs measured
    @safe
    def m08():
        if not mu:
            return bad('no manifest units')
        agree = 0; notes = []
        for u in UNITS:
            e = mu.get(u)
            if not e:
                notes.append('%s absent' % u); continue
            has_geo = bool(geo_objs(S, u)) or bool(inst_boxes(S, u))
            if e.get('built') is False:
                good = not has_geo
                agree += good
                if not good:
                    notes.append('%s built:false but has geometry' % u)
                continue
            if not has_geo:
                notes.append('%s built but empty' % u); continue
            p = e.get('params') or {}; t = U[u]['type']; mis = []
            try:
                if t == 'NAVE_BAY':
                    if cnt(S, u, 'LIGHT') != 2 * int(p['clerestory_lights']): mis.append('LIGHT')
                    if cnt(S, u, 'TRI') != 2 * int(p['triforium_openings_per_side']): mis.append('TRI')
                    if cnt(S, u, 'RIB') != int(p['rib_count']): mis.append('RIB')
                elif t == 'AISLE':
                    if cnt(S, u, 'LIGHT') != sum(int(x) for x in p['bay_lights']): mis.append('LIGHT')
                    bt = butt_top(u)
                    if bt is None or abs(bt - float(p['buttress_top_z'])) > 0.15: mis.append('BUTT z')
                elif t == 'FLYER':
                    fl = p['flyers']
                    if cnt(S, u, 'FLY') != sum(int(d['tiers']) for d in fl): mis.append('FLY')
                    if cnt(S, u, 'PINN') != sum(int(d['pinnacles']) for d in fl): mis.append('PINN')
                    if cnt(S, u, 'CULEE') != len(fl): mis.append('CULEE')
                elif t == 'TOWER':
                    lt = 4 * int(p['belfry_lancets_per_face'])
                    if lt not in (cnt(S, u, 'LIGHT'), cnt(S, u, 'WIN')): mis.append('lancets')
                    if cnt(S, u, 'PINN') != int(p['spire_pinnacles']): mis.append('PINN')
                    st = spire_top(u)
                    if st is None or abs(st - float(p['spire_tip_z'])) > 0.3: mis.append('spire z')
                elif t == 'WEST_FRONT':
                    if cnt(S, u, 'KING') != int(p['gallery_niches']): mis.append('KING')
                    if cnt(S, u, 'PINN') != int(p['gable_pinnacles']): mis.append('PINN')
                elif t in ('ROSE', 'TRANSEPT_FRONT'):
                    rings, dia = rose_meas(u)
                    rl = [int(x) for x in p['ring_lights']]
                    if cnt(S, u, 'ROSE') != sum(rl) or rings != rl: mis.append('rings %s' % rings)
                    dk = 'diameter' if t == 'ROSE' else 'rose_diameter'
                    if not rose_dia_ok(u, dia, float(p[dk])): mis.append('dia')
                    if t == 'TRANSEPT_FRONT' and cnt(S, u, 'PORTAL') != int(p['portals']): mis.append('PORTAL')
                elif t == 'CROSSING':
                    if 4 * int(p['belfry_openings_per_face']) not in (cnt(S, u, 'LIGHT'), cnt(S, u, 'WIN')): mis.append('openings')
                    if cnt(S, u, 'PINN') != int(p['tower_pinnacles']): mis.append('PINN')
                    if cnt(S, u, 'RIB') != int(p['rib_count']): mis.append('RIB')
                    st = spire_top(u)
                    if st is None or abs(st - float(p['fleche_tip_z'])) > 0.3: mis.append('fleche z')
                elif t == 'TRANSEPT_BAY':
                    if cnt(S, u, 'LIGHT') != int(p['lights_west']) + int(p['lights_east']): mis.append('LIGHT')
                    if cnt(S, u, 'TRI') != 2 * int(p['triforium_openings_per_side']): mis.append('TRI')
                    if cnt(S, u, 'RIB') != int(p['rib_count']): mis.append('RIB')
                elif t == 'CHOIR_BAY':
                    if cnt(S, u, 'LIGHT') != int(p['lights_north']) + int(p['lights_south']): mis.append('LIGHT')
                    if cnt(S, u, 'NICHE') != 2 * int(p['niches_per_side']): mis.append('NICHE')
                    if cnt(S, u, 'RIB') != int(p['rib_count']): mis.append('RIB')
                elif t == 'APSE':
                    if cnt(S, u, 'WIN') != int(p['sides']): mis.append('WIN')
                    if cnt(S, u, 'LIGHT') != int(p['sides']) * int(p['lights_per_window']): mis.append('LIGHT')
                    if cnt(S, u, 'RIB') != int(p['rib_count']): mis.append('RIB')
                elif t == 'CHAPEL':
                    if cnt(S, u, 'WIN') != int(p['sides']): mis.append('WIN')
                    if cnt(S, u, 'LIGHT') != int(p['sides']) * int(p['lights_per_window']): mis.append('LIGHT')
                    z = unit_zmax(S, u)
                    if z is None or abs(z - float(p['roof_tip_z'])) > 0.3: mis.append('roof z')
            except Exception as ex:
                mis.append('params error %r' % ex)
            if mis:
                notes.append('%s: %s' % (u, ','.join(mis)))
            else:
                agree += 1
        frac = agree / 34.0
        return (ok if frac >= 0.9 else bad)('consistent %d/34 (%.0f%%). %s' % (agree, frac * 100, '; '.join(notes[:12])))
    R['M08'] = m08()

    # ---------------------------------------------------------------- M09 cameras
    @safe
    def m09():
        res = (S.data.get('scene') or {}).get('res') or [1920, 1080, 100]
        cx = E.get('cam') or {}
        msgs = []; good = True
        for c in ('CAM_NAVE', 'CAM_CHEVET', 'CAM_OVERVIEW'):
            if (S.ob(c) or {}).get('type') != 'CAMERA':
                return bad('%s missing' % c)
        o = S.ob('CAM_NAVE'); l = o['location']; d = view_dir(o)
        a = ang(d, [1, 0, 0]); pitch = math.degrees(math.asin(max(-1, min(1, d[2]))))
        g = -63 <= l[0] <= -49 and abs(l[1]) <= 1.0 and 1.2 <= l[2] <= 2.5 and a <= 10 and abs(pitch) <= 10
        good &= g; msgs.append('NAVE loc=%s ang=%.1f pitch=%.1f %s' % ([round(t, 2) for t in l], a, pitch, 'ok' if g else 'X'))
        o = S.ob('CAM_CHEVET'); l = o['location']; d = view_dir(o)
        a = ang(d, [-1, 0, 0])
        g = l[0] > 40 and abs(l[1]) <= 6 and a <= 15
        good &= g; msgs.append('CHEVET loc=%s ang=%.1f %s' % ([round(t, 2) for t in l], a, 'ok' if g else 'X'))
        o = S.ob('CAM_OVERVIEW'); l = o['location']
        g = l[0] < -20 and l[1] > 20 and l[2] > 40
        for u in ('T01', 'F01', 'E02', 'A01'):
            b = unit_bbox(S, u)
            if not b:
                g = False; msgs.append('%s empty' % u); continue
            uu, vv, front = project(o, cx.get('CAM_OVERVIEW'), res, Scene.center(b))
            inside = front and 0 <= uu <= 1 and 0 <= vv <= 1
            g &= inside
            if not inside:
                msgs.append('%s out of frame (%s,%s)' % (u, uu, vv))
        good &= g; msgs.append('OVERVIEW loc=%s %s' % ([round(t, 2) for t in l], 'ok' if g else 'X'))
        return (ok if good else bad)('; '.join(msgs))
    R['M09'] = m09()

    # ---------------------------------------------------------------- M10 glass
    @safe
    def m10():
        mats = E.get('mat')
        if mats is None:
            return bad('material extraction missing')
        probs = []; nglass = 0
        for u in UNITS:
            gl = named(S, u, 'LIGHT') + named(S, u, 'ROSE')
            if not gl:
                continue
            others = [n for n in geo_objs(S, u) if not re.search(r'_(LIGHT|ROSE|WIN)_', n)]
            freq = {}
            for n in others:
                for m in (S.ob(n) or {}).get('materials', []):
                    freq[m] = freq.get(m, 0) + 1
            wall = max(freq, key=freq.get) if freq else None
            for n in gl:
                ms = (S.ob(n) or {}).get('materials', [])
                nglass += 1
                if not ms:
                    probs.append('%s no material' % n)
                elif not all(is_glass(mats.get(m)) for m in ms):
                    probs.append('%s not transmissive/emissive %s' % (n, ms))
                elif wall is not None and wall in ms:
                    probs.append('%s same material as wall %s' % (n, wall))
        if nglass == 0:
            return bad('no LIGHT/ROSE objects')
        return bad('%d problems: %s' % (len(probs), '; '.join(probs[:8]))) if probs else ok('%d glazing objects ok' % nglass)
    R['M10'] = m10()

    # ---------------------------------------------------------------- M11 real openings
    @safe
    def m11():
        m = E.get('m11')
        if m is None:
            return bad('ray-cast extraction missing')
        n = len(m); units = len({r['unit'] for r in m}); clear = sum(1 for r in m if r.get('clear'))
        g = n >= 12 and units >= 6 and clear >= 10
        return (ok if g else bad)('sampled %d lights over %d units, clear %d (need 12/>=6/>=10)' % (n, units, clear))
    R['M11'] = m11()

    # ---------------------------------------------------------------- G01 Z1
    def storeys_meas(u):
        """string courses: runs projecting >=0.05 m beyond the face (median), 0.05-1.5 m high, not touching the bottom or
        top of the scan; a face shows a course when >=2 of its 3 scan lines (midline, +-1/3 width) do; a course counts
        when it shows on >=2 faces at the same height (+-0.3). storeys = courses + 1."""
        tw = (E.get('tower') or {}).get(u)
        if not tw:
            return None, 'no tower scan'
        z0, dz = tw['z0'], tw['dz']; top = T(u)['body_top']

        def runs_of(prof):
            vals = sorted(v for v in prof if v is not None)
            if len(vals) < 20:
                return []
            base = vals[len(vals) // 2]
            runs = []; st = None
            for i, v in enumerate(prof + [None]):
                z = z0 + dz * i
                pr = v is not None and v >= base + 0.05
                if pr and st is None:
                    st = i
                elif not pr and st is not None:
                    h = (i - st) * dz
                    zc = z0 + dz * (st + i - 1) / 2
                    if 0.05 <= h <= 1.5 and st > 0 and i < len(prof) and 1.0 <= zc <= top - 1.0:
                        runs.append(zc)
                    st = None
            return runs

        def cluster(zs):
            out = []
            for z in sorted(zs):
                if out and z - out[-1][-1] <= 0.3:
                    out[-1].append(z)
                else:
                    out.append([z])
            return [sum(c) / len(c) for c in out]

        face_z = {}
        for fn, scans in tw['faces'].items():
            if isinstance(scans, list):          # legacy single midline profile
                scans = {'0.0': scans}
            rs = [runs_of(p) for p in scans.values()]
            need = 2 if len(rs) >= 3 else 1
            face_z[fn] = [z for z in cluster([z for r in rs for z in r])
                          if sum(1 for r in rs if any(abs(x - z) <= 0.3 for x in r)) >= need]
        good = [z for z in cluster([z for r in face_z.values() for z in r])
                if sum(1 for r in face_z.values() if any(abs(x - z) <= 0.3 for x in r)) >= 2]
        return len(good) + 1, 'courses at %s' % [round(z, 2) for z in good]

    @safe
    def g01():
        msgs = []; g = True
        for u in ('T01', 'T02'):
            t = T(u)
            lt = 4 * t['lancets']
            c1 = lt in (cnt(S, u, 'LIGHT'), cnt(S, u, 'WIN'))
            c2 = cnt(S, u, 'PINN') == t['pinn']
            st, why = storeys_meas(u)
            c3 = st == t['storeys']
            g &= c1 and c2 and c3
            msgs.append('%s lancets(L%d/W%d vs %d) PINN %d/%d storeys %s/%d (%s)' % (u, cnt(S, u, 'LIGHT'), cnt(S, u, 'WIN'), lt,
                                                                                 cnt(S, u, 'PINN'), t['pinn'], st, t['storeys'], why))
        t = T('P01')
        c = cnt(S, 'P01', 'KING') == t['kings'] and cnt(S, 'P01', 'PINN') == t['gable_pinn']
        g &= c; msgs.append('P01 KING %d/%d PINN %d/%d' % (cnt(S, 'P01', 'KING'), t['kings'], cnt(S, 'P01', 'PINN'), t['gable_pinn']))
        rings, dia = rose_meas('R01'); t = T('R01')
        c = rings == t['rings'] and rose_dia_ok('R01', dia, t['dia'])
        g &= c; msgs.append('R01 rings %s/%s dia %s/%s' % (rings, t['rings'], dia and round(dia, 2), t['dia']))
        return (ok if g else bad)('; '.join(msgs))
    R['G01'] = g01()

    # ---------------------------------------------------------------- G02 / G03 nave
    secs = E.get('sec') or {}

    def pier_ok(u):
        ps = named(S, u, 'PIER')
        if len(ps) != 2:
            return False, '%s PIER n=%d' % (u, len(ps))
        cl = [pier_class(secs.get(n)) for n in ps]
        good = all(c[0] == T(u)['pier'] for c in cl)
        return good, '%s pier %s/%s' % (u, [c[0] for c in cl], T(u)['pier'])

    def nave_zone(us, full):
        msgs = []; g = True
        for u in us:
            t = T(u); o = U[u]['original_sheet']
            po, pm = pier_ok(u)
            tri = cnt(S, u, 'TRI') == 2 * o['tri']
            ok_u = po and tri; m = '%s TRI %d/%d' % (pm, cnt(S, u, 'TRI'), 2 * o['tri'])
            if full(u):
                li = named(S, u, 'LIGHT')
                n_n = sum(1 for n in li if (cen(S, n) or [0, 0])[1] > 0)
                lok = len(li) == 2 * t['lights'] and n_n == t['lights']
                rok = cnt(S, u, 'RIB') == U[u]['expected_counts']['RIB']
                ok_u &= lok and rok
                m += ' LIGHT %d(N%d)/%d RIB %d/%d' % (len(li), n_n, 2 * t['lights'], cnt(S, u, 'RIB'), U[u]['expected_counts']['RIB'])
            g &= ok_u; msgs.append(m)
        return (ok if g else bad)('; '.join(msgs))
    R['G02'] = safe(nave_zone)(['N01', 'N02', 'N03', 'N04'], lambda u: u in ('N01', 'N02'))
    R['G03'] = safe(nave_zone)(['N05', 'N06', 'N07', 'N08'], lambda u: True)

    # ---------------------------------------------------------------- G04 / G05 flanks
    def aisle_ok(u):
        t = T(u); msgs = []
        li = named(S, u, 'LIGHT')
        seq = [0, 0, 0, 0]
        for n in li:
            x = cen(S, n)[0]; k = int((x - t['x0']) // 7.0)
            if 0 <= k < 4:
                seq[k] += 1
        g = seq == t['bay_lights']; msgs.append('%s lights %s/%s' % (u, seq, t['bay_lights']))
        ds = named(S, u, 'DOOR')
        if len(ds) != 1:
            g = False; msgs.append('DOOR n=%d' % len(ds))
        else:
            x = cen(S, ds[0])[0]; k = int((x - t['x0']) // 7.0) + 1
            g &= k == t['door_bay']; msgs.append('door bay %d/%d' % (k, t['door_bay']))
        bs = named(S, u, 'BUTT')
        xs = sorted(cen(S, n)[0] for n in bs)
        if len(xs) != len(t['butt_x']) or any(abs(a - b) > 0.15 for a, b in zip(xs, t['butt_x'])):
            g = False; msgs.append('BUTT x %s/%s' % ([round(x, 2) for x in xs], t['butt_x']))
        zs = [zmax(S, [n]) for n in bs]
        if not zs or any(abs(z - t['butt_top']) > 0.1 for z in zs):
            g = False; msgs.append('BUTT top %s/%s' % ([round(z, 2) for z in zs], t['butt_top']))
        return g, ' '.join(msgs)

    def flyer_ok(u):
        t = T(u); g = True; msgs = []
        rem = [line_x(k) for k in t.get('removed_lines', [])]
        for code, key in (('FLY', 'tiers'), ('PINN', 'pinn'), ('CULEE', None)):
            objs = named(S, u, code)
            xs = [cen(S, n)[0] for n in objs]
            per = []
            for d in t['lines']:
                k = sum(1 for x in xs if abs(x - d['x']) < 1.0)
                exp = d[key] if key else 1
                per.append('%d/%d' % (k, exp))
                g &= k == exp
            stray = [x for x in xs if all(abs(x - d['x']) >= 1.0 for d in t['lines']) and all(abs(x - r) >= 1.0 for r in rem)]
            g &= not stray
            msgs.append('%s %s%s' % (code, per, ' stray %d' % len(stray) if stray else ''))
        return g, '%s %s' % (u, ' '.join(msgs))

    def flank(us):
        rs = [aisle_ok(u) if u[0] == 'L' else flyer_ok(u) for u in us]
        return (ok if all(r[0] for r in rs) else bad)('; '.join(r[1] for r in rs))
    R['G04'] = safe(flank)(['L01', 'L02', 'F01', 'F02'])
    R['G05'] = safe(flank)(['L03', 'L04', 'F03', 'F04'])

    # ---------------------------------------------------------------- G06 crossing / transept
    @safe
    def g06():
        g = True; msgs = []
        t = T('X01'); st = spire_top('X01')
        c = (4 * t['openings'] in (cnt(S, 'X01', 'LIGHT'), cnt(S, 'X01', 'WIN')) and cnt(S, 'X01', 'PINN') == t['pinn']
             and cnt(S, 'X01', 'RIB') == U['X01']['expected_counts']['RIB'] and st is not None and abs(st - t['fleche_tip']) <= 0.3)
        g &= c; msgs.append('X01 LIGHT %d WIN %d/%d PINN %d/%d RIB %d/%d fleche %s/%s' % (cnt(S, 'X01', 'LIGHT'), cnt(S, 'X01', 'WIN'), 4 * t['openings'], cnt(S, 'X01', 'PINN'),
                                                                               t['pinn'], cnt(S, 'X01', 'RIB'), U['X01']['expected_counts']['RIB'], st and round(st, 2), t['fleche_tip']))
        for u in ('E01', 'E02', 'E03', 'E04'):
            t = T(u); li = named(S, u, 'LIGHT')
            w = sum(1 for n in li if cen(S, n)[0] < 0); e = len(li) - w
            c = (w == t['lights_a'] and e == t['lights_b'] and cnt(S, u, 'TRI') == 2 * t['tri']
                 and cnt(S, u, 'RIB') == U[u]['expected_counts']['RIB'])
            g &= c; msgs.append('%s W%d/%d E%d/%d TRI %d RIB %d%s' % (u, w, t['lights_a'], e, t['lights_b'], cnt(S, u, 'TRI'), cnt(S, u, 'RIB'), '' if c else ' X'))
        for u in ('R02', 'R03'):
            t = T(u); rings, dia = rose_meas(u)
            tur = named(S, u, 'TURRET')
            sides = [hull_corners(secs.get(n) or [], 12.0, merge=0.05) for n in tur]
            c = (cnt(S, u, 'PORTAL') == t['portals'] and rings == t['rings'] and rose_dia_ok(u, dia, t['dia'])
                 and len(tur) == 2 and all(s == t['turret_sides'] for s in sides))
            g &= c; msgs.append('%s PORTAL %d/%d rings %s/%s dia %s/%s turret %s/%d' % (u, cnt(S, u, 'PORTAL'), t['portals'], rings, t['rings'],
                                                                                    dia and round(dia, 2), t['dia'], sides, t['turret_sides']))
        return (ok if g else bad)('; '.join(msgs))
    R['G06'] = g06()

    # ---------------------------------------------------------------- G07 choir / chevet
    def apse_sides(pts):
        if not pts or len(pts) < 10:
            return None
        nb = 90; env = [None] * nb
        for x, y in pts:
            th = math.degrees(math.atan2(y, x - 28.0))
            if -90 < th < 90:
                k = min(nb - 1, int((th + 90) / 180 * nb))
                r = math.hypot(x - 28.0, y)
                if env[k] is None or r > env[k]:
                    env[k] = r
        idx = [i for i in range(nb) if env[i] is not None]
        if len(idx) < 10:
            return None
        for i in range(nb):
            if env[i] is None:
                lo = max([j for j in idx if j < i], default=None); hi = min([j for j in idx if j > i], default=None)
                env[i] = env[lo] if hi is None else (env[hi] if lo is None else env[lo] + (env[hi] - env[lo]) * (i - lo) / (hi - lo))
        mean = sum(env) / nb; c = 0
        for i in range(1, nb - 1):
            w = [env[j] for j in range(max(0, i - 4), min(nb, i + 5))]
            if env[i] <= min(w) and max(w) - env[i] >= 0.012 * mean and env[i - 1] > env[i]:
                c += 1
        return c

    @safe
    def g07():
        g = True; msgs = []
        for u in ('Q01', 'Q02', 'Q03'):
            t = T(u); li = named(S, u, 'LIGHT')
            n = sum(1 for x in li if cen(S, x)[1] > 0); s = len(li) - n
            c = n == t['lights_a'] and s == t['lights_b'] and cnt(S, u, 'NICHE') == 2 * t['niches'] and cnt(S, u, 'RIB') == U[u]['expected_counts']['RIB']
            g &= c; msgs.append('%s N%d/%d S%d/%d NICHE %d RIB %d%s' % (u, n, t['lights_a'], s, t['lights_b'], cnt(S, u, 'NICHE'), cnt(S, u, 'RIB'), '' if c else ' X'))
        t = T('A01'); sd = apse_sides(E.get('apse_sec'))
        c = (cnt(S, 'A01', 'WIN') == t['sides'] and cnt(S, 'A01', 'LIGHT') == t['sides'] * t['lights']
             and cnt(S, 'A01', 'RIB') == t['ribs'] and sd == t['sides'])
        g &= c; msgs.append('A01 WIN %d LIGHT %d RIB %d wall-sides %s / %d' % (cnt(S, 'A01', 'WIN'), cnt(S, 'A01', 'LIGHT'), cnt(S, 'A01', 'RIB'), sd, t['sides']))
        for u in ('K01', 'K02', 'K03'):
            t = T(u); z = unit_zmax(S, u)
            c = cnt(S, u, 'WIN') == t['sides'] and cnt(S, u, 'LIGHT') == t['sides'] * t['lights'] and z is not None and abs(z - t['roof_tip']) <= 0.3
            g &= c; msgs.append('%s WIN %d/%d LIGHT %d/%d roof %s/%s' % (u, cnt(S, u, 'WIN'), t['sides'], cnt(S, u, 'LIGHT'), t['sides'] * t['lights'], z and round(z, 2), t['roof_tip']))
        return (ok if g else bad)('; '.join(msgs))
    R['G07'] = g07()

    # ---------------------------------------------------------------- G08 CO item 1
    @safe
    def g08():
        g = True; msgs = []
        G8 = E.get('g08') or {}
        for u in ('N03', 'N04'):
            o = U[u]['original_sheet']; m = []
            rib = cnt(S, u, 'RIB'); li = named(S, u, 'LIGHT')
            nN = sum(1 for n in li if cen(S, n)[1] > 0)
            c = rib == 0 and len(li) == 2 and nN == 1
            m.append('RIB %d LIGHT %d(N%d)' % (rib, len(li), nN))
            po, pm = pier_ok(u)
            c &= po and cnt(S, u, 'TRI') == 2 * o['tri']; m.append('%s TRI %d/%d' % (pm, cnt(S, u, 'TRI'), 2 * o['tri']))
            d = G8.get(u)
            if not d:
                c = False; m.append('no profile data')
            else:
                for side in ('N', 'S'):
                    rho, why = arch_ratio(d['arc'].get(side) or [])
                    c &= rho is not None and 0.9 <= rho <= 1.1; m.append('arcade%s %s' % (side, why))
                cr = d.get('crown')
                c &= cr is not None and abs(cr - 26.0) <= 0.15; m.append('crown %s' % cr)
                sp = []
                for tag, row in (d.get('vault') or {}).items():
                    h0 = row.get('0.0')
                    for y1 in ('4.0', '5.5', '-4.0', '-5.5'):
                        h1 = row.get(y1)
                        if h0 is None or h1 is None or h0 - h1 <= 0.05:
                            continue
                        dd = h0 - h1; yy = abs(float(y1)); Rr = (dd * dd + yy * yy) / (2 * dd)
                        sp.append(h0 - Rr)
                spring = sorted(sp)[len(sp) // 2] if sp else None
                c &= spring is not None and abs(spring - 19.0) <= 0.25; m.append('spring %s' % (spring and round(spring, 2)))
            for n in li:
                V = (S.ob(n) or {}).get('verts_world')
                if not V:
                    c = False; m.append('%s no verts' % n); continue
                rho, why = arch_ratio(upper_profile(V, 0), pad=0.0)
                c &= rho is not None and 0.9 <= rho <= 1.1; m.append('%s head %s' % (n, why))
            g &= c; msgs.append('%s: %s' % (u, ', '.join(m)))
        return (ok if g else bad)('; '.join(msgs))
    R['G08'] = g08()

    # ---------------------------------------------------------------- G09 CO items 2, 3
    @safe
    def g09():
        g = True; msgs = []
        hits = []
        for n, o in S.objects.items():
            if re.match(r'^[A-Z]\d\d_(FLY|CULEE|PINN)_\d+$', n) and o.get('bbox_world'):
                c = Scene.center(o['bbox_world'])
                if abs(c[0] + 42.0) < 1.0 and 7.6 <= abs(c[1]) <= 17.0:
                    hits.append(n)
        g &= not hits; msgs.append('line-4 flyer parts %s' % hits[:6])
        for u in ('L01', 'L03'):
            b = [n for n in named(S, u, 'BUTT') if abs(cen(S, n)[0] + 42.0) < 0.5]
            g &= len(b) == 1; msgs.append('%s BUTT@line4 %d' % (u, len(b)))
        for u in ('F01', 'F03'):
            xs = [cen(S, n)[0] for n in named(S, u, 'FLY')]
            for d in T(u)['lines']:
                k = sum(1 for x in xs if abs(x - d['x']) < 1.0)
                g &= k == d['tiers']
            msgs.append('%s kept lines FLY %s' % (u, [sum(1 for x in xs if abs(x - d['x']) < 1.0) for d in T(u)['lines']]))
        for u in ('T01', 'T02'):
            st, bt = spire_top(u), body_top(u)
            c = st is not None and abs(st - 72.0) <= 0.3 and bt is not None and abs(bt - 44.0) <= 0.3
            g &= c; msgs.append('%s spire %s body %s' % (u, st and round(st, 2), bt and round(bt, 2)))
        return (ok if g else bad)('; '.join(msgs))
    R['G09'] = g09()

    # ---------------------------------------------------------------- G10 I1 pier grid
    @safe
    def g10():
        pc = E.get('pier_c') or {}
        pts = {}
        for k in range(1, 9):
            for y in (7.0, -7.0):
                pts[(line_x(k), y)] = 'N%02d' % k
        for x in (-7.0, 7.0):
            for y in (7.0, -7.0):
                pts[(x, y)] = 'X01'
        piers = [n for n, o in S.objects.items() if re.match(r'^[A-Z]\d\d_PIER_\d+$', n) and o.get('type') in GEO]
        owner = {}
        for u in UNITS:
            for n in S.coll(u):
                owner.setdefault(n, u)
        match = {p: [] for p in pts}; extra = []
        for n in piers:
            c = pc.get(n) or (cen(S, n) or [None, None])[:2]
            if c[0] is None:
                extra.append(n); continue
            best = min(pts, key=lambda p: math.hypot(p[0] - c[0], p[1] - c[1]))
            if math.hypot(best[0] - c[0], best[1] - c[1]) <= 0.3:
                match[best].append(n)
            elif owner.get(n, '')[:1] in ('N', 'X'):
                extra.append(n)
        probs = []
        for p, ns in match.items():
            if len(ns) != 1:
                probs.append('%s n=%d' % (p, len(ns)))
            elif owner.get(ns[0]) != pts[p]:
                probs.append('%s owned by %s (want %s)' % (p, owner.get(ns[0]), pts[p]))
        if extra:
            probs.append('extra PIER %s' % extra[:6])
        return bad('; '.join(probs[:10])) if probs else ok('20 grid points, one pier each, ownership correct')
    R['G10'] = g10()

    # ---------------------------------------------------------------- G11 I2 vault continuity
    @safe
    def g11():
        d = E.get('g11')
        if not d:
            return bad('ray-cast extraction missing')
        tol = 0.15

        def hl(v):   # hit list (legacy extracts stored [with RIB, without RIB] first hits)
            return [z for z in (v or []) if z is not None]
        probs = []
        for u in VAULT_UNITS:
            hs = hl(d['crown'].get(u))
            if not any(abs(z - 26.0) <= tol for z in hs):
                probs.append('%s crown hits %s' % (u, hs[:4]))
        nl = 0
        for name, ua, ub, ax, c, ss in shared_lines():
            smp = d['lines'].get(name) or []
            got = {round(float(e[0]), 2): e for e in smp if isinstance(e, list) and len(e) == 3}
            badn = 0
            for s0 in ss:
                e = got.get(round(s0, 2))
                ha, hb = (hl(e[1]), hl(e[2])) if e else ([], [])
                if not ha or not hb or not any(abs(za - zb) <= tol for za in ha for zb in hb):
                    badn += 1
            nl += 1
            if badn:
                probs.append('%s %d/%d samples mismatched%s' % (name, badn, len(ss), ' (crown only, CO-01)' if len(ss) == 1 else ''))
        return bad('; '.join(probs[:12])) if probs else ok('17 crowns at 26.0, %d shared lines continuous' % nl)
    R['G11'] = g11()

    # ---------------------------------------------------------------- G12 I3 flyer landing
    @safe
    def g12():
        probs = []; nfly = 0
        for f, l2 in (('F01', ('L01', 'L02')), ('F02', ('L01', 'L02')), ('F03', ('L03', 'L04')), ('F04', ('L03', 'L04'))):
            butts = [n for l in l2 for n in named(S, l, 'BUTT')]
            culs = named(S, f, 'CULEE')
            for c in culs:
                V = (S.ob(c) or {}).get('verts_world') or []
                if not V:
                    probs.append('%s no verts' % c); continue
                z0 = min(v[2] for v in V); low = [v for v in V if v[2] <= z0 + 0.05]
                cx = sum(v[0] for v in low) / len(low)
                if not butts:
                    probs.append('%s no BUTT' % c); continue
                b = min(butts, key=lambda n: abs(cen(S, n)[0] - cx))
                BV = (S.ob(b) or {}).get('verts_world') or []
                if not BV:
                    probs.append('%s no verts' % b); continue
                z1 = max(v[2] for v in BV); top = [v for v in BV if v[2] >= z1 - 0.05]
                inside = (min(v[0] for v in low) >= min(v[0] for v in top) - 0.1 and max(v[0] for v in low) <= max(v[0] for v in top) + 0.1
                          and min(v[1] for v in low) >= min(v[1] for v in top) - 0.1 and max(v[1] for v in low) <= max(v[1] for v in top) + 0.1)
                if not inside or abs(z0 - z1) > 0.1:
                    probs.append('%s on %s inside=%s dz=%.2f' % (c, b, inside, z0 - z1))
            for fl in named(S, f, 'FLY'):
                nfly += 1
                V = (S.ob(fl) or {}).get('verts_world') or []
                if not V:
                    probs.append('%s no verts' % fl); continue
                ys = sorted(abs(v[1]) for v in V); lo, hi = ys[0], ys[-1]; span = hi - lo
                up = [v for v in V if abs(v[1]) <= lo + 0.05 * span + 1e-6]
                dn = [v for v in V if abs(v[1]) >= hi - 0.05 * span - 1e-6]
                if abs(lo - 7.6) > 0.15 or not all(18.0 <= v[2] <= 26.0 for v in up):
                    probs.append('%s upper |y|=%.2f z=[%.1f,%.1f]' % (fl, lo, min(v[2] for v in up), max(v[2] for v in up)))
                p = [sum(v[i] for v in dn) / len(dn) for i in range(3)]
                best = None
                for c in culs:
                    b = bb(S, [c])
                    if not b:
                        continue
                    dd = math.sqrt(sum(max(b[0][i] - p[i], 0, p[i] - b[1][i]) ** 2 for i in range(3)))
                    best = dd if best is None else min(best, dd)
                if best is None or best > 0.15:
                    probs.append('%s lower end %.2f m from culee' % (fl, best if best is not None else -1))
        if nfly == 0:
            probs.append('no FLY')
        return bad('; '.join(probs[:10])) if probs else ok('%d flyers land correctly' % nfly)
    R['G12'] = g12()

    # ---------------------------------------------------------------- G13 I4 west symmetry
    @safe
    def g13():
        b1, b2 = unit_bbox(S, 'T01'), unit_bbox(S, 'T02')
        if not b1 or not b2:
            return bad('tower empty')
        c1, c2 = Scene.center(b1), Scene.center(b2)
        sym = abs(c1[0] - c2[0]) <= 0.1 and abs(abs(c1[1]) - abs(c2[1])) <= 0.1 and c1[1] * c2[1] < 0 and abs(b1[1][2] - b2[1][2]) <= 0.1
        V = [v for n in named(S, 'R01', 'ROSE') for v in ((S.ob(n) or {}).get('verts_world') or [])]
        if len(V) < 10:
            return bad('towers sym=%s; R01 ROSE verts missing' % sym)
        rb = bb(S, named(S, 'R01', 'ROSE')); rc = Scene.center(rb)
        m, nrm = pca_normal(V)
        a = ang([abs(t) for t in nrm], [1, 0, 0])
        r = abs(rc[1]) <= 0.1 and abs(rc[2] - 22.0) <= 0.15 and -72.4 <= m[0] <= -71.6 and a <= 3.0
        return (ok if sym and r else bad)('towers c=%s/%s top %.2f/%.2f sym=%s; rose centre y=%.2f z=%.2f x=%.2f normal∠X=%.1f°' % (
            [round(t, 2) for t in c1[:2]], [round(t, 2) for t in c2[:2]], b1[1][2], b2[1][2], sym, rc[1], rc[2], m[0], a))
    R['G13'] = g13()

    if E.get('err'):
        for k in ('M10', 'M11', 'G01', 'G08', 'G10', 'G11'):
            if k in R and R[k]['verdict'] == 'fail':
                R[k]['detail'] = (R[k]['detail'] + ' | extract errors: ' + '; '.join(E['err'])[:200])[:600]
    return {k: v for k, v in R.items() if k in items}


def postprocess(results, ctx):
    """B02 collection contract failed -> every mid/gate criterion measured per collection scores 0 (G14 VLM is exempt)."""
    keep = {k: v for k, v in results.items() if isinstance(v, dict) and v.get('verdict') == 'fail'}
    results = gate_group(results, ctx['items'], ['B02'], lambda it: it.get('tier') in ('mid', 'gate') and it['id'] != 'G14',
                         'gate: B02 collection contract failed')
    for k, v in keep.items():   # already-failing items keep their own (more specific) detail
        results[k] = v
    return results
