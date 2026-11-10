# -*- coding: utf-8 -*-
"""BLD-W03 deterministic checks (modular orbital station "Tianshu").

Covers every rubric item except G14 (blind visual review -> judge model).
One Blender export via Scene.load(); task-specific geometry (BODY extents in ROOT frame,
truss bracing probes, end-effector islands, N3.P3 vacancy, inter-unit interpenetration)
is computed by EXTRA_PY inside Blender and returned in S.data['extra'].
"""
import json, math, re, zlib, struct, pathlib, traceback
from _bld_lib import Scene, ok, bad, close, png_size, load_manifest, gate_group

FRAMES = [1, 60, 120, 180, 200, 240]
CHECK = [1, 60, 120, 180, 240]
ANIM_RE = r'(_ROOT|_P\d+|_BLANKET_\d+|_PANEL_\d+|_EE)$|^SUN$'
POS_TOL, ANG_TOL, TRACK_TOL, EE_TOL = 0.10, 2.0, 3.0, 0.15
CODES = {'N': ['RING'], 'L': ['WIN', 'SITE'], 'K': ['TANK'], 'T': ['BAY'], 'S': ['BLANKET', 'SEG'],
         'R': ['PANEL'], 'A': ['JNT'], 'V': ['WING', 'RCS'], 'E': ['PL']}
MANIFEST_FIELDS = {
    'N': {'length_m', 'diameter_m', 'port_count', 'ring_count'},
    'L': {'length_m', 'diameter_m', 'window_count', 'payload_sites'},
    'K': {'length_m', 'diameter_m', 'tank_count'},
    'T': {'length_m', 'bay_count', 'bracing'},
    'S': {'blanket_length_m', 'blanket_count', 'segments_per_blanket', 'gimbal'},
    'R': {'panel_count', 'panel_length_m'},
    'A': {'dof', 'end_effector'},
    'V': {'length_m', 'diameter_m', 'solar_wings', 'rcs_quads'},
    'E': {'slots_total', 'slots_occupied'},
}
SCENE_FREE = {'B06', 'B07', 'B08'}

# ----------------------------------------------------------------------------- Blender-side code
EXTRA_PY = r'''
import json, time
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P = json.loads(PJSON)
T0 = time.time()
GEO = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}
R_PORT, PLANE_TOL, R_FACE = 1.0, 0.15, 2.5   # G13 port-contact exclusion (see rubric G13)
EXTRA['errors'] = []

def err(tag, e):
    EXTRA['errors'].append(tag + ': ' + repr(e)[:300])

def coll_objs(c):
    col = bpy.data.collections.get(c)
    return [o for o in col.all_objects if o.name in scene.objects] if col else []

def _own_mesh(ev, mw):
    try:
        me = ev.to_mesh()
    except Exception:
        return [], [], []
    if me is None:
        return [], [], []
    try:
        vs = [mw @ v.co for v in me.vertices]
        ps = [tuple(p.vertices) for p in me.polygons]
        es = [tuple(e.vertices) for e in me.edges]
    finally:
        ev.to_mesh_clear()
    return vs, ps, es

def _cat(parts):
    V, PL, EL = [], [], []
    for vs, ps, es in parts:
        off = len(V)
        V += vs
        PL += [tuple(i + off for i in p) for p in ps]
        EL += [tuple(i + off for i in e) for e in es]
    return V, PL, EL

# v2 (2026-10-25): instanced geometry (collection instances, geometry-nodes instances) is realised per instancer,
# extracted inside the depsgraph iteration (instance data is only valid there). Rebuilt after every frame change.
INST = {}
def build_inst(dg):
    INST.clear()
    n = 0
    try:
        for oi in dg.object_instances:
            if not oi.is_instance or oi.parent is None:
                continue
            src = oi.object
            if src is None or src.type not in GEO:
                continue
            g = _own_mesh(src, oi.matrix_world.copy())
            if g[0]:
                INST.setdefault(oi.parent.original.name, []).append(g)
                n += 1
            if n >= 20000:
                err('instances', 'capped at 20000')
                break
    except Exception as e:
        err('instances', e)

def mesh_world(o, dg):
    """evaluated mesh of o in world coordinates, plus the geometry it instances (GN / collection instances)."""
    try:
        ev = o.evaluated_get(dg)
        parts = [_own_mesh(ev, ev.matrix_world.copy())] if o.type in GEO else []
    except Exception:
        parts = []
    parts += INST.get(o.name, [])
    return _cat(parts)

def unit_geom(U, dg):
    V, PL, EL = _cat([mesh_world(o, dg) for o in coll_objs(U) if o.type in GEO or o.name in INST])
    return V, PL

def set_frame(f):
    scene.frame_set(int(f))
    d = bpy.context.evaluated_depsgraph_get()
    d.update()
    build_inst(d)
    return d

dg = set_frame(1)

# 1) BODY extents in ROOT local frame (frame 1; V2 at frame 180 is rigid so frame 1 is fine)
EXTRA['body'] = {}
for U in P['units']:
    try:
        r = scene.objects.get(U + '_ROOT'); b = scene.objects.get(U + '_BODY')
        if r is None or b is None:
            continue
        inv = r.matrix_world.inverted_safe()
        vs, ps, es = mesh_world(b, dg)
        if not vs:
            EXTRA['body'][U] = {'n': 0}
            continue
        L = [inv @ v for v in vs]
        EXTRA['body'][U] = {'n': len(L), 'min': [min(p[i] for p in L) for i in range(3)],
                            'max': [max(p[i] for p in L) for i in range(3)],
                            'rmax': max(math.hypot(p[1], p[2]) for p in L)}
    except Exception as e:
        err('body ' + U, e)

# 2) truss bracing probes on the local +Y face
EXTRA['truss'] = {}
for U, sp in P['truss'].items():
    try:
        r = scene.objects.get(U + '_ROOT')
        if r is None:
            continue
        V, PL = unit_geom(U, dg)
        if not PL:
            EXTRA['truss'][U] = {'bays': [], 'note': 'no polygons'}
            continue
        bvh = BVHTree.FromPolygons(V, PL)
        mw = r.matrix_world
        L, W, H, n = sp['L'], sp['W'], sp['H'], sp['bays']
        bw = L / n
        out = []
        for i in range(n):
            x0 = -L / 2 + i * bw
            row = []
            for diag in (0, 1):
                ds = []
                for t in (0.25, 0.75):
                    z = (-H / 2 + t * H) if diag == 0 else (H / 2 - t * H)
                    hit = bvh.find_nearest(mw @ Vector((x0 + t * bw, W / 2, z)))
                    ds.append(round(hit[3], 4) if hit and hit[0] is not None else 1e9)
                row.append(ds)
            out.append(row)
        EXTRA['truss'][U] = {'bays': out}
    except Exception as e:
        err('truss ' + U, e)

# 3) end effector form
EXTRA['effector'] = {}
for U, sp in P['arms'].items():
    try:
        e = scene.objects.get(U + '_EFFECTOR'); ee = scene.objects.get(U + '_EE')
        if e is None or ee is None:
            EXTRA['effector'][U] = {'missing': True}
            continue
        ax = Vector(sp['axis']).normalized()
        c = ee.matrix_world.translation.copy()
        # v2: the effector is <id>_EFFECTOR plus all of its child meshes (fingers / snare wires may be separate objects)
        vs, ps, es = _cat([mesh_world(x, dg) for x in [e] + list(e.children_recursive)
                           if x.type in GEO or x.name in INST])
        par = list(range(len(vs)))
        def fd(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for a, b in es:
            ra, rb = fd(a), fd(b)
            if ra != rb:
                par[ra] = rb
        mx = {}
        for i, v in enumerate(vs):
            r_ = fd(i); s = (v - c).dot(ax)
            mx[r_] = max(mx.get(r_, -1e9), s)
        near = 0
        for v in vs:
            d = v - c; s = d.dot(ax)
            if -0.5 <= s <= 0.5 and (d - ax * s).length < 0.1:
                near += 1
        hit = False
        if ps:
            bvh = BVHTree.FromPolygons(vs, ps)
            h = bvh.ray_cast(c - ax * 0.5, ax, 1.0)
            hit = h[0] is not None
        EXTRA['effector'][U] = {'islands': len(mx), 'protruding': sum(1 for v in mx.values() if v >= 0.2),
                                'axis_hit': hit, 'near_axis_verts': near}
    except Exception as e:
        err('effector ' + U, e)

# 4) N3.P3 vacancy (frames 1/180/240)
EXTRA['n3p3'] = {}
n3 = {o.name for o in coll_objs('N3')}
for f in (1, 180, 240):
    try:
        dg = set_frame(f)
        po = scene.objects.get('N3_P3')
        p = po.matrix_world.translation.copy() if po else Vector(P['n3p3'])
        offs = []
        for o in scene.objects:
            if o.name in n3 or o.type in ('LIGHT', 'CAMERA'):
                continue
            if o.type == 'EMPTY':
                if (o.matrix_world.translation - p).length < 0.5:
                    offs.append(o.name)
                continue
            if o.type not in GEO and o.name not in INST:
                continue
            try:
                ev = o.evaluated_get(dg)
                mw = ev.matrix_world
                if o.type in GEO:
                    bb = [mw @ Vector(cc) for cc in ev.bound_box]
                    near_bb = not any(p[i] < min(q[i] for q in bb) - 0.6 or p[i] > max(q[i] for q in bb) + 0.6 for i in range(3))
                else:
                    near_bb = False
                hitp = False
                if near_bb and o.type == 'MESH':
                    try:
                        res = o.closest_point_on_mesh(mw.inverted_safe() @ p, distance=50.0, depsgraph=dg)
                        hitp = bool(res[0]) and ((mw @ res[1]) - p).length < 0.5
                        near_bb = False if res[0] else near_bb
                    except Exception:
                        pass   # faceless mesh etc. -> vertex/edge distance below
                if not hitp and (near_bb or o.name in INST):
                    vs, ps, es = mesh_world(o, dg)
                    hitp = any((v - p).length < 0.5 for v in vs)
                    if not hitp:
                        for a_, b_ in es:
                            A_, B_ = vs[a_], vs[b_]; d_ = B_ - A_; L2 = d_.length_squared
                            t_ = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, (p - A_).dot(d_) / L2))
                            if (A_ + d_ * t_ - p).length < 0.5:
                                hitp = True; break
                if hitp:
                    offs.append(o.name)
            except Exception as e:
                err('n3p3 %s %s' % (f, o.name), e)
        EXTRA['n3p3'][str(f)] = offs[:30]
    except Exception as e:
        err('n3p3 %s' % f, e)

# 5) interpenetration between unit collections (frames 1/120/240)
G = {'complete': True, 'frames': {}}
try:
    for f in (1, 120, 240):
        dg = set_frame(f)
        # linked port faces: (centre, outward normal) from the scene port empties, plus the key's static port centres
        ports = []
        for (a, pa, b, pb) in P['links']:
            for nm in (a + '_' + pa, b + '_' + pb):
                o = scene.objects.get(nm)
                if o is not None:
                    mwp = o.matrix_world
                    ports.append((mwp.translation.copy(), mwp.col[2].to_3d().normalized()))
        ports += [(Vector(q['pos']), Vector(q['n'])) for q in P['port_key_static']]
        data = {}
        for U in P['units']:
            V, PL = unit_geom(U, dg)
            if not PL:
                continue
            mn = [min(v[i] for v in V) for i in range(3)]; mx = [max(v[i] for v in V) for i in range(3)]
            data[U] = (V, PL, BVHTree.FromPolygons(V, PL), mn, mx)
        G.setdefault('scanned', {})[str(f)] = sorted(data)

        def port_contact(ptsA, ptsB):
            # v2: contact at a mating interface is allowed: (a) any vertex/centroid of EITHER triangle within R_PORT of a
            # linked port centre, or (b) both triangles have a vertex within PLANE_TOL of that port face plane and R_FACE of its centre.
            for pp, nn in ports:
                if min((q - pp).length for q in ptsA + ptsB) <= R_PORT:
                    return True
                if (any(abs((q - pp).dot(nn)) <= PLANE_TOL and (q - pp).length <= R_FACE for q in ptsA) and
                        any(abs((q - pp).dot(nn)) <= PLANE_TOL and (q - pp).length <= R_FACE for q in ptsB)):
                    return True
            return False
        hits = []
        us = sorted(data)
        for i in range(len(us)):
            for j in range(i + 1, len(us)):
                A, B = data[us[i]], data[us[j]]
                if any(A[3][k] > B[4][k] + 0.01 or B[3][k] > A[4][k] + 0.01 for k in range(3)):
                    continue
                ov = A[2].overlap(B[2])
                rem = 0
                for ia, ib in ov[:20000]:
                    pa_ = [A[0][k] for k in A[1][ia]]
                    pb_ = [B[0][k] for k in B[1][ib]]
                    pa_.append(sum(pa_, Vector((0, 0, 0))) / len(pa_))
                    pb_.append(sum(pb_, Vector((0, 0, 0))) / len(pb_))
                    if not port_contact(pa_, pb_):
                        rem += 1
                if rem:
                    hits.append([us[i], us[j], rem])
                if time.time() - T0 > 900:
                    G['complete'] = False
                    break
            if not G['complete']:
                break
        G['frames'][str(f)] = hits
        if not G['complete']:
            break
except Exception as e:
    G['complete'] = False
    err('g13', e)
EXTRA['g13'] = G
EXTRA['elapsed_s'] = round(time.time() - T0, 1)
'''


# ----------------------------------------------------------------------------- vector helpers
def v_sub(a, b): return [a[i] - b[i] for i in range(3)]
def v_dot(a, b): return sum(a[i] * b[i] for i in range(3))
def v_len(a): return math.sqrt(v_dot(a, a))
def v_norm(a):
    l = v_len(a)
    return [x / l for x in a] if l > 1e-12 else [0.0, 0.0, 0.0]
def v_cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
def ang(a, b):
    a, b = v_norm(a), v_norm(b)
    return math.degrees(math.acos(max(-1.0, min(1.0, v_dot(a, b)))))
def col(m, i): return [m[0][i], m[1][i], m[2][i]]
def loc(m): return [m[0][3], m[1][3], m[2][3]]
def rot_cols(m): return [v_norm(col(m, i)) for i in range(3)]
def to_local(mroot, p):
    """world point -> ROOT local (orthonormalised rotation, no scale)."""
    R = rot_cols(mroot)
    d = v_sub(p, loc(mroot))
    return [v_dot(R[i], d) for i in range(3)]
def dir_local(mroot, d):
    R = rot_cols(mroot)
    return [v_dot(R[i], d) for i in range(3)]


def sun(f):
    b = math.radians(15.0)
    p = math.radians(20.0 + 0.6 * (f - 1))
    return [math.cos(b) * math.cos(p), math.sin(b), math.cos(b) * math.sin(p)]


# ----------------------------------------------------------------------------- PNG non-blank
def _png_gray_samples(path, step=4):
    """Pure-python PNG decoder (non-interlaced, 8/16 bit, types 0/2/4/6). Returns sampled gray list."""
    data = open(path, 'rb').read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    pos, idat, hdr = 8, [], None
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            hdr = struct.unpack('>IIBBBBB', body)
        elif typ == b'IDAT':
            idat.append(body)
        elif typ == b'IEND':
            break
        pos += 12 + ln
    w, h, bd, ct, _, _, il = hdr
    if il != 0 or ct not in (0, 2, 4, 6) or bd not in (8, 16):
        return None
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    bpp = ch * bd // 8
    stride = w * bpp
    raw = zlib.decompress(b''.join(idat))
    prev = bytearray(stride)
    out = []
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
                a = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif ft == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]; c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c; pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        prev = line
        if y % step == 0:
            for x in range(0, w, step):
                o = x * bpp
                if bd == 16:
                    vals = [line[o + 2 * k] for k in range(ch)]
                else:
                    vals = [line[o + k] for k in range(ch)]
                g = vals[0] if ch <= 2 else (0.299 * vals[0] + 0.587 * vals[1] + 0.114 * vals[2])
                out.append(g)
    return out


def png_nonblank(path):
    """(ok, detail): gray std > 8 and >2% of pixels differ (>8 levels) from the dominant gray."""
    g = None
    try:
        from PIL import Image
        im = Image.open(path).convert('L')
        im = im.resize((480, 270))
        g = list(im.getdata())
    except Exception:
        try:
            g = _png_gray_samples(path)
        except Exception as e:
            return False, f'decode error {e}'
    if not g:
        return False, 'cannot decode'
    n = len(g)
    m = sum(g) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in g) / n)
    hist = {}
    for x in g:
        hist[int(x)] = hist.get(int(x), 0) + 1
    mode = max(hist, key=hist.get)
    frac = sum(1 for x in g if abs(x - mode) > 8) / n
    return (sd > 8 and frac > 0.02), f'std={sd:.1f} nonmono={frac:.3f}'


# ----------------------------------------------------------------------------- main
def run(ctx):
    res = {}
    key = ctx.get('answer') or json.loads((pathlib.Path(ctx['tests']) / 'answer-key.json').read_text(encoding='utf-8'))
    items = [i['id'] for i in ctx['items']]
    out = pathlib.Path(ctx['out'])
    KU = key['units']
    UNITS = list(KU.keys())
    ZONES = {z['id']: z['units'] for z in key['zones']}

    def guard(iid, fn):
        try:
            r = fn()
            res[iid] = r
        except Exception:
            res[iid] = bad('check error: ' + traceback.format_exc()[-400:])

    # ---------------- file-only items
    def b67(names):
        msgs, good = [], True
        for nm in names:
            p = out / 'renders' / nm
            if not p.exists():
                good = False; msgs.append(f'{nm} missing'); continue
            sz = png_size(p)
            if sz != (1920, 1080):
                good = False; msgs.append(f'{nm} size {sz}'); continue
            okb, d = png_nonblank(p)
            msgs.append(f'{nm} {d}')
            good = good and okb
        return (ok if good else bad)('; '.join(msgs))
    guard('B06', lambda: b67(['overview.png']))
    guard('B07', lambda: b67(['stbd_truss.png', 'forward.png']))

    man = load_manifest(out)

    def b08():
        if not isinstance(man, dict) or not isinstance(man.get('units'), list):
            return bad('manifest.json missing or invalid')
        us = man['units']
        if len(us) != 28:
            return bad(f'units has {len(us)} entries')
        errs = []
        ids = []
        for e in us:
            if not isinstance(e, dict) or not {'id', 'collection', 'built', 'params'} <= set(e):
                errs.append(f'bad entry {str(e)[:60]}'); continue
            ids.append(e['id'])
            t = str(e['id'])[:1]
            if t not in MANIFEST_FIELDS or not isinstance(e['params'], dict):
                errs.append(f'{e["id"]}: unknown type/params'); continue
            if set(e['params']) != MANIFEST_FIELDS[t]:
                errs.append(f'{e["id"]}: fields {sorted(e["params"])}')
        if set(ids) != set(UNITS):
            errs.append(f'ids mismatch: missing {sorted(set(UNITS) - set(ids))} extra {sorted(set(ids) - set(UNITS))}')
        return bad('; '.join(errs[:8])) if errs else ok('28 entries, schema ok')
    guard('B08', b08)

    # ---------------- scene
    S = Scene.load(ctx, frames=FRAMES, anim_regex=ANIM_RE, extra_py=_extra_code(key))
    if S.err or not S.data:
        why = f'scene not measurable: {S.err}'
        for iid in items:
            if iid not in SCENE_FREE and iid != 'G14':
                res[iid] = bad(why)
        return res
    O = S.objects
    EX = (S.data.get('extra') or {})
    ctx['_w03_scene_ok'] = True

    def M(name, f=1):
        m = S.at(f, name)
        if m is None and name in O:
            m = O[name]['matrix_world']   # fallback: saved-frame matrix
        return m

    def in_coll(U, name):
        return name in set(S.coll(U))

    def codes(U, code):
        r = re.compile(rf'^{re.escape(U)}_{code}_\d{{2,}}$')
        return [n for n in S.coll(U) if r.match(n)]

    def ports(U):
        r = re.compile(rf'^{re.escape(U)}_P\d+$')
        return sorted(n for n in S.coll(U) if r.match(n))

    def seg_counts(U):
        bl = codes(U, 'BLANKET')
        segs = codes(U, 'SEG')
        return {b: sum(1 for s in segs if (O.get(s) or {}).get('parent') == b) for b in bl}

    def ufr(U):
        return 180 if U == 'V2' else 1

    BODY = EX.get('body') or {}

    def body_nv(U):
        # evaluated vertex count of <U>_BODY: extractor n_verts (evaluated mesh) or EXTRA body count (incl. instances)
        return max((O.get(f'{U}_BODY') or {}).get('n_verts') or 0, (BODY.get(U) or {}).get('n') or 0)

    # B01
    def b01():
        sc = S.data.get('scene') or {}
        if sc.get('unit_system') != 'METRIC' or abs(float(sc.get('scale_length', 0)) - 1) > 1e-6:
            return bad(f"unit_system={sc.get('unit_system')} scale_length={sc.get('scale_length')}")
        return ok(f"opened in Blender {S.data.get('blender_version')}; METRIC, scale 1")
    guard('B01', b01)

    def b02():
        miss = [u for u in UNITS + ['SITE'] if not S.has_coll(u)]
        return bad(f'missing collections {miss}') if miss else ok('28 unit collections + SITE')
    guard('B02', b02)

    def b03():
        errs = []
        for U in UNITS:
            r, b = f'{U}_ROOT', f'{U}_BODY'
            if not in_coll(U, r) or (O.get(r) or {}).get('type') != 'EMPTY':
                errs.append(f'{r} missing/not EMPTY'); continue
            if not in_coll(U, b) or (O.get(b) or {}).get('type') != 'MESH' or not body_nv(U) > 0:
                errs.append(f'{b} missing/empty'); continue
            p, seen = O[b].get('parent'), 0
            while p and p != r and seen < 50:
                p = (O.get(p) or {}).get('parent'); seen += 1
            if p != r:
                errs.append(f'{b} not under {r}')
        return bad('; '.join(errs[:8]) + (f' (+{len(errs) - 8})' if len(errs) > 8 else '')) if errs else ok('28/28 ROOT+BODY')
    guard('B03', b03)

    def b04():
        site = set(S.coll('SITE'))
        errs = []
        if 'SUN' not in site or (O.get('SUN') or {}).get('type') != 'LIGHT' or (O['SUN'].get('light') or {}).get('type') != 'SUN':
            errs.append('SUN sun-light missing in SITE')
        for c in ('CAM_OVERVIEW', 'CAM_STBD', 'CAM_FWD'):
            if c not in site or (O.get(c) or {}).get('type') != 'CAMERA':
                errs.append(f'{c} missing')
        return bad('; '.join(errs)) if errs else ok('SUN + 3 cameras in SITE')
    guard('B04', b04)

    def b05():
        sc = S.data.get('scene') or {}
        g = sc.get('frame_start') == 1 and sc.get('frame_end') == 240 and sc.get('fps') == 24 and abs(float(sc.get('fps_base', 0)) - 1) < 1e-6
        return (ok if g else bad)(f"{sc.get('frame_start')}-{sc.get('frame_end')} @ {sc.get('fps')}/{sc.get('fps_base')}")
    guard('B05', b05)

    # ---------------- poses
    def pose_err(U):
        k = KU[U]
        m = M(f'{U}_ROOT', ufr(U))
        if m is None:
            return f'{U}_ROOT missing'
        d = v_len(v_sub(loc(m), k['origin_world']))
        if d > POS_TOL:
            return f'{U} origin off {d:.3f} m'
        for i, a in enumerate('xyz'):
            e = ang(col(m, i), k['axes_world'][a])
            if e > ANG_TOL:
                return f'{U} axis {a} off {e:.1f} deg'
            s = v_len(col(m, i))
            if abs(s - 1) > 0.01:
                return f'{U} scale {s:.3f}'
        return None

    for zid, iid in zip('ABCDE', ['M01', 'M02', 'M03', 'M04', 'M05']):
        def f_(zid=zid):
            errs = [e for e in (pose_err(U) for U in ZONES[zid]) if e]
            return bad('; '.join(errs)) if errs else ok(f'zone {zid}: {len(ZONES[zid])} ROOT poses ok')
        guard(iid, f_)

    # ---------------- BODY dims

    def ext(U):
        b = BODY.get(U)
        if not b or not b.get('n'):
            return None
        return [b['max'][i] - b['min'][i] for i in range(3)]

    def dims_err(U):
        k = KU[U]; t = k['type']; bd = k.get('body') or {}
        b = BODY.get(U)
        e = ext(U)
        if e is None:
            return f'{U}_BODY not measured'
        chk = []
        if t in 'NLV':
            chk = [('x', e[0], bd['L']), ('y', e[1], bd['D']), ('z', e[2], bd['D'])]
        elif t == 'K':
            chk = [('x', e[0], bd['L']), ('2*rmax', 2 * b['rmax'], bd['D'])]
        elif t in 'TE':
            chk = [('x', e[0], bd['L']), ('y', e[1], bd['W']), ('z', e[2], bd['H'])]
        elif t in 'SR':
            chk = [('x', e[0], bd['L'])]
        elif t == 'A':
            chk = [('top z', b['max'][2], k['extra']['h0'])]
        bads = [f'{n}={m:.2f} vs {v}' for n, m, v in chk if not close(m, v)]
        return f'{U}: ' + ', '.join(bads) if bads else None

    for zid, iid in zip('ABCDE', ['M06', 'M07', 'M08', 'M09', 'M10']):
        def f_(zid=zid):
            errs = [e for e in (dims_err(U) for U in ZONES[zid]) if e]
            return bad('; '.join(errs)) if errs else ok(f'zone {zid}: BODY dims ok')
        guard(iid, f_)

    # ---------------- M11 ports
    def m11():
        errs = []
        for U in UNITS:
            want = sorted(f'{U}_{p}' for p in KU[U]['ports_world'])
            got = ports(U)
            if got != want:
                errs.append(f'{U}: {got} != {want}')
        return bad('; '.join(errs[:6])) if errs else ok('all port empty sets match')
    guard('M11', m11)

    # ---------------- M12 manifest consistency
    CNT_FIELDS = {'ring_count': 'RING', 'window_count': 'WIN', 'payload_sites': 'SITE', 'tank_count': 'TANK',
                  'bay_count': 'BAY', 'blanket_count': 'BLANKET', 'panel_count': 'PANEL', 'dof': 'JNT',
                  'solar_wings': 'WING', 'rcs_quads': 'RCS', 'slots_occupied': 'PL'}

    def m12():
        if not isinstance(man, dict) or not isinstance(man.get('units'), list):
            return bad('manifest missing/invalid')
        errs = []
        for e in man['units']:
            try:
                U = e['id']; p = e.get('params') or {}
                if U not in KU:
                    errs.append(f'unknown id {U}'); continue
                t = KU[U]['type']
                has_body = body_nv(U) > 0 and in_coll(U, f'{U}_BODY')
                if bool(e.get('built')) != has_body:
                    errs.append(f'{U}: built={e.get("built")} but BODY present={has_body}'); continue
                if not e.get('built'):
                    continue
                for fld, code in CNT_FIELDS.items():
                    if fld in p and p[fld] != len(codes(U, code)):
                        errs.append(f'{U}.{fld}={p[fld]} vs {len(codes(U, code))}')
                if 'port_count' in p and p['port_count'] != len(ports(U)):
                    errs.append(f'{U}.port_count={p["port_count"]} vs {len(ports(U))}')
                if 'segments_per_blanket' in p:
                    sc = seg_counts(U)
                    if not sc or any(v != p['segments_per_blanket'] for v in sc.values()):
                        errs.append(f'{U}.segments_per_blanket={p["segments_per_blanket"]} vs {sorted(set(sc.values()))}')
                ex = ext(U)
                if 'length_m' in p:
                    if ex is None or not close(p['length_m'], ex[0], rel=0.03, abs_=0.0):
                        errs.append(f'{U}.length_m={p["length_m"]} vs {None if ex is None else round(ex[0], 2)}')
                if 'diameter_m' in p:
                    md = None if ex is None else (2 * BODY[U]['rmax'] if t == 'K' else max(ex[1], ex[2]))
                    if md is None or not close(p['diameter_m'], md, rel=0.03, abs_=0.0):
                        errs.append(f'{U}.diameter_m={p["diameter_m"]} vs {None if md is None else round(md, 2)}')
            except Exception as ex_:
                errs.append(f'entry error {ex_}')
        return bad('; '.join(errs[:8]) + (f' (+{len(errs) - 8})' if len(errs) > 8 else '')) if errs else ok('manifest consistent with scene')
    guard('M12', m12)

    # ---------------- M13 SUN
    def m13():
        errs = []
        for f in CHECK:
            m = S.at(f, 'SUN')
            if m is None:
                return bad(f'SUN not sampled at frame {f}')
            e = ang(col(m, 2), sun(f))
            if e > ANG_TOL:
                errs.append(f'f{f}: {e:.1f} deg')
        return bad('; '.join(errs)) if errs else ok('SUN +Z tracks S(f)')
    guard('M13', m13)

    # ---------------- M14 V2 motion
    def m14():
        ms = {f: S.at(f, 'V2_ROOT') for f in FRAMES}
        if any(v is None for v in ms.values()):
            return bad('V2_ROOT not sampled')
        p = {f: loc(m) for f, m in ms.items()}
        D = v_len(v_sub(p[180], p[1]))
        errs = []
        if abs(D - 40) > 0.5:
            errs.append(f'travel {D:.2f} m')
        for f in (60, 120):
            t = (f - 1) / 179.0
            q = [p[1][i] + t * (p[180][i] - p[1][i]) for i in range(3)]
            dd = v_len(v_sub(p[f], q))
            if dd > 0.3:
                errs.append(f'f{f} off line/time {dd:.2f} m')
        R1 = rot_cols(ms[1])
        for f in FRAMES[1:]:
            Rf = rot_cols(ms[f])
            e = max(ang(R1[i], Rf[i]) for i in range(3))
            if e > 1.0:
                errs.append(f'attitude change f{f} {e:.2f} deg')
        for f in (200, 240):
            dd = v_len(v_sub(p[f], p[180]))
            if dd > 0.02:
                errs.append(f'moves after 180 ({f}: {dd:.3f} m)')
        return bad('; '.join(errs)) if errs else ok(f'uniform straight approach {D:.2f} m, hold after 180')
    guard('M14', m14)

    # ---------------- M15 EE
    def m15():
        errs = []
        for U in ('A1', 'A2'):
            m = M(f'{U}_EE', 1)
            if m is None:
                errs.append(f'{U}_EE missing'); continue
            d = v_len(v_sub(loc(m), KU[U]['ee_world']))
            if d > EE_TOL:
                errs.append(f'{U}_EE off {d:.2f} m')
        return bad('; '.join(errs)) if errs else ok('A1/A2 EE within 0.15 m')
    guard('M15', m15)

    # ---------------- G01-G05 discrete features
    TR = EX.get('truss') or {}
    EF = EX.get('effector') or {}

    def side_err(U, code, sign):
        ns = codes(U, code)
        m = M(f'{U}_ROOT', 1)
        cs = [S.center(O[n]['bbox_world']) for n in ns if O.get(n, {}).get('bbox_world')]
        if not cs or m is None:
            return f'{U}: {code} centroid not measurable'
        c = [sum(x[i] for x in cs) / len(cs) for i in range(3)]
        z = to_local(m, c)[2]
        return None if z * sign > 0 else f'{U}: {code} centroid local z={z:.2f}'

    def bracing_of(U):
        t = TR.get(U)
        if not t or not t.get('bays'):
            return None, 'no probe data'
        kinds = []
        for row in t['bays']:
            pres = [max(ds) <= 0.15 for ds in row]
            kinds.append(sum(pres))
        if all(k == 2 for k in kinds):
            return 'X', kinds
        if all(k == 1 for k in kinds):
            return 'warren', kinds
        return 'mixed', kinds

    def feat_err(U):
        k = KU[U]; t = k['type']; p = k['params']
        errs = []
        def cnt(code, want):
            n = len(codes(U, code))
            if n != want:
                errs.append(f'{U} {code}={n}/{want}')
        if t == 'N':
            if len(ports(U)) != p['port_count']:
                errs.append(f'{U} ports={len(ports(U))}/{p["port_count"]}')
            cnt('RING', p['ring_count'])
        elif t == 'L':
            cnt('WIN', p['window_count']); cnt('SITE', p['payload_sites'])
            for code, sg in (('SITE', 1), ('WIN', -1)):
                e = side_err(U, code, sg)
                if e:
                    errs.append(e)
        elif t == 'K':
            cnt('TANK', p['tank_count'])
        elif t == 'T':
            cnt('BAY', p['bay_count'])
            kind, info = bracing_of(U)
            if kind != p['bracing']:
                errs.append(f'{U} bracing={kind} {info} want {p["bracing"]}')
        elif t == 'S':
            cnt('BLANKET', p['blanket_count'])
            sc = seg_counts(U)
            if not sc or any(v != p['segments_per_blanket'] for v in sc.values()):
                errs.append(f'{U} SEG/blanket={sorted(set(sc.values()))} want {p["segments_per_blanket"]}')
        elif t == 'R':
            cnt('PANEL', p['panel_count'])
        elif t == 'A':
            cnt('JNT', p['dof'])
            e = EF.get(U)
            if not e or e.get('missing'):
                errs.append(f'{U} effector/EE missing')
            elif p['end_effector'] == 'gripper':
                if e['protruding'] < 2:
                    errs.append(f'{U} gripper: protruding parts={e["protruding"]}')
            else:
                if e['islands'] != 1 or e['axis_hit'] or e['near_axis_verts'] > 0:
                    errs.append(f'{U} snare: islands={e["islands"]} axis_hit={e["axis_hit"]} near={e["near_axis_verts"]}')
        elif t == 'V':
            cnt('WING', p['solar_wings']); cnt('RCS', p['rcs_quads'])
        elif t == 'E':
            cnt('PL', p['slots_occupied'])
        return '; '.join(errs) or None

    for zid, iid in zip('ABCDE', ['G01', 'G02', 'G03', 'G04', 'G05']):
        def f_(zid=zid):
            errs = [e for e in (feat_err(U) for U in ZONES[zid]) if e]
            return bad('; '.join(errs)) if errs else ok(f'zone {zid}: discrete features exact')
        guard(iid, f_)

    # ---------------- link mating
    def port_pose(name, f):
        m = M(name, f)
        if m is None:
            return None
        return loc(m), v_norm(col(m, 2)), v_norm(col(m, 1))

    def mate_err(a, pa, b, pb, f):
        A, B = port_pose(f'{a}_{pa}', f), port_pose(f'{b}_{pb}', f)
        if A is None or B is None:
            return f'{a}.{pa}-{b}.{pb}: port empty missing'
        d = v_len(v_sub(A[0], B[0]))
        en = ang(A[1], [-x for x in B[1]])
        ek = ang(A[2], B[2])
        if d > POS_TOL or en > ANG_TOL or ek > ANG_TOL:
            return f'{a}.{pa}-{b}.{pb} f{f}: d={d:.2f} n={en:.1f} k={ek:.1f}'
        return None

    def local_port_err(U, P_, f):
        k = KU[U]
        mr = M(f'{U}_ROOT', f)
        pp = port_pose(f'{U}_{P_}', f)
        if mr is None or pp is None:
            return f'{U}.{P_}: missing'
        ax = [k['axes_world'][a] for a in 'xyz']
        kw = k['ports_world'][P_]
        exp_p = [v_dot(ax[i], v_sub(kw['pos'], k['origin_world'])) for i in range(3)]
        exp_n = [v_dot(ax[i], kw['n']) for i in range(3)]
        exp_k = [v_dot(ax[i], kw['k']) for i in range(3)]
        gp = to_local(mr, pp[0]); gn = dir_local(mr, pp[1]); gk = dir_local(mr, pp[2])
        d = v_len(v_sub(gp, exp_p))
        if d > 0.05 or ang(gn, exp_n) > ANG_TOL or ang(gk, exp_k) > ANG_TOL:
            return f'{U}.{P_} local pose off (d={d:.2f}, n={ang(gn, exp_n):.1f}, k={ang(gk, exp_k):.1f})'
        return None

    def link_frame(a, b):
        return 180 if 'V2' in (a, b) else 1

    # G06
    def g06():
        errs = []
        e = dims_err('N2')
        if e:
            errs.append(e)
        if len(codes('N2', 'RING')) != KU['N2']['params']['ring_count']:
            errs.append(f"N2 RING={len(codes('N2', 'RING'))}")
        if ports('N2') != sorted(f'N2_{p}' for p in KU['N2']['ports_world']):
            errs.append(f'N2 ports {ports("N2")}')
        for P_, kw in KU['N2']['ports_world'].items():
            pp = port_pose(f'N2_{P_}', 1)
            if pp is None:
                continue
            d = v_len(v_sub(pp[0], kw['pos']))
            if d > POS_TOL or ang(pp[1], kw['n']) > ANG_TOL or ang(pp[2], kw['k']) > ANG_TOL:
                errs.append(f'N2.{P_} world pose off d={d:.2f}')
        for a, pa, b, pb in (('L1', 'P2', 'N2', 'P1'), ('N2', 'P4', 'V1', 'P1'), ('N2', 'P2', 'L2', 'P1'), ('N2', 'P3', 'L3', 'P1')):
            e = mate_err(a, pa, b, pb, 1)
            if e:
                errs.append(e)
        return bad('; '.join(errs[:6])) if errs else ok('N2 Mk-B built and 4 links mate')
    guard('G06', g06)

    # G07
    def g07():
        errs = []
        e = mate_err('N2', 'P5', 'V2', 'P1', 180)
        if e:
            errs.append(e)
        A, B = port_pose('N2_P5', 1), port_pose('V2_P1', 1)
        if A is None or B is None:
            errs.append('N2_P5/V2_P1 missing at f1')
        else:
            d = v_sub(B[0], A[0]); al = v_dot(d, A[1]); lat = v_len([d[i] - al * A[1][i] for i in range(3)])
            if abs(al - 40) > 0.5 or lat > 0.5:
                errs.append(f'f1 V2_P1 along={al:.2f} lateral={lat:.2f}')
        n3 = EX.get('n3p3') or {}
        miss = sorted({'1', '180', '240'} - set(n3), key=int)
        if miss:
            errs.append(f'N3.P3 vacancy not measured at frames {miss}')
        for f, offs in n3.items():
            if offs:
                errs.append(f'N3.P3 occupied f{f}: {offs[:4]}')
        return bad('; '.join(errs)) if errs else ok('V2 docks at N2.P5 from 40 m; N3.P3 vacant')
    guard('G07', g07)

    # G08
    def g08():
        errs = []
        e = ext('T4')
        if e is None or not close(e[0], KU['T4']['body']['L']):
            errs.append(f'T4 length {None if e is None else round(e[0], 2)}')
        if len(codes('T4', 'BAY')) != KU['T4']['params']['bay_count']:
            errs.append(f"T4 BAY={len(codes('T4', 'BAY'))}")
        for U in ('S3', 'T5', 'S4', 'R2', 'R4'):
            m = M(f'{U}_ROOT', 1)
            if m is None:
                errs.append(f'{U}_ROOT missing'); continue
            d = v_len(v_sub(loc(m), KU[U]['origin_world']))
            if d > POS_TOL:
                errs.append(f'{U} origin off {d:.2f} m')
        return bad('; '.join(errs)) if errs else ok('T4 extended + ripple units placed')
    guard('G08', g08)

    # blankets
    def blanket_err(U):
        k = KU[U]
        bl = codes(U, 'BLANKET')
        if not bl:
            return f'{U}: no BLANKET'
        ax = k['gimbal_axis_world']
        errs = []
        for b in bl:
            ref = None
            for f in CHECK:
                m = S.at(f, b)
                if m is None:
                    errs.append(f'{b} not sampled'); break
                s = sun(f)
                if k['params']['gimbal'] == '1-axis':
                    tgt = v_norm([s[i] - v_dot(s, ax) * ax[i] for i in range(3)])
                    la = v_norm(dir_local(m, ax))
                    if ref is None:
                        ref = la
                    elif ang(la, ref) > ANG_TOL:
                        errs.append(f'{b} alpha axis drifts f{f}')
                else:
                    tgt = s
                e = ang(col(m, 2), tgt)
                if e > TRACK_TOL:
                    errs.append(f'{b} f{f} {e:.1f} deg')
                    break
        return '; '.join(errs[:4]) or None

    guard('G09', lambda: (lambda e: bad(e) if e else ok('S4 two-axis blankets = S(f)'))(blanket_err('S4')))

    # G10
    def g10():
        errs = []
        for a, pa, b, pb in key['links']:
            e = mate_err(a, pa, b, pb, link_frame(a, b))
            if e:
                errs.append(e)
            for U, P_ in ((a, pa), (b, pb)):
                e = local_port_err(U, P_, ufr(U))
                if e:
                    errs.append(e)
        return bad(f'{len(errs)} issues: ' + '; '.join(errs[:6])) if errs else ok(f'{len(key["links"])} links mate; port locals match sheets')
    guard('G10', g10)

    def g11():
        errs = [e for e in (blanket_err(U) for U in ('S1', 'S2', 'S3')) if e]
        return bad('; '.join(errs)) if errs else ok('S1-S3 blankets track the Sun')
    guard('G11', g11)

    def g12():
        errs = []
        lim_s, lim_a = math.sin(math.radians(3)), math.sin(math.radians(2))
        for U in ('R1', 'R2', 'R3', 'R4'):
            pn = codes(U, 'PANEL')
            if not pn:
                errs.append(f'{U}: no PANEL'); continue
            ax = KU[U]['rotary_axis_world']
            for pnl in pn:
                for f in CHECK:
                    m = S.at(f, pnl)
                    if m is None:
                        errs.append(f'{pnl} not sampled'); break
                    n = v_norm(col(m, 2))
                    if abs(v_dot(n, sun(f))) > lim_s or abs(v_dot(n, ax)) > lim_a:
                        errs.append(f'{pnl} f{f} n.S={v_dot(n, sun(f)):.3f} n.axis={v_dot(n, ax):.3f}'); break
        return bad('; '.join(errs[:6])) if errs else ok('radiator panels edge-on, rotating about own axes')
    guard('G12', g12)

    def g13():
        g = EX.get('g13')
        if not g:
            return bad('interpenetration not measured')
        if not g.get('complete'):
            return bad(f'interpenetration scan incomplete (time cap) {g.get("frames")}')
        hits = [(f, h) for f, hs in g.get('frames', {}).items() for h in hs]
        if len(g.get('frames', {})) < 3:
            return bad('not all frames scanned')
        sc = g.get('scanned') or {}
        short = {f: sorted(set(UNITS) - set(sc.get(f, []))) for f in ('1', '120', '240')}
        short = {f: v for f, v in short.items() if v}
        if short:   # v2: no vacuous pass on units without faced geometry
            return bad('units without faced geometry (not scanned): ' + '; '.join(f'f{f} {v[:8]}' for f, v in short.items()))
        return bad('; '.join(f'f{f} {h[0]}x{h[1]} ({h[2]} tri pairs)' for f, h in hits[:6])) if hits else ok('no inter-unit intersections at f1/120/240')
    guard('G13', g13)

    if EX.get('errors'):
        res['_w03_extract_errors'] = {'verdict': 'na', 'detail': str(EX['errors'])[:600]}
    return {k: v for k, v in res.items() if k in items or k.startswith('_')}


def _extra_code(key):
    KU = key['units']
    P = {
        'units': list(KU.keys()),
        'truss': {U: {'L': v['body']['L'], 'W': v['body']['W'], 'H': v['body']['H'], 'bays': v['params']['bay_count']}
                  for U, v in KU.items() if v['type'] == 'T'},
        'arms': {U: {'axis': [v['ee_world'][i] - v['joints_world'][-2][i] for i in range(3)]}
                 for U, v in KU.items() if v['type'] == 'A'},
        'n3p3': KU['N3']['ports_world']['P3']['pos'],
        'links': key['links'],
        'port_key_static': [{'pos': KU[a]['ports_world'][pa]['pos'], 'n': KU[a]['ports_world'][pa]['n']}
                            for a, pa, b, pb in key['links'] if 'V2' not in (a, b)],
    }
    return 'PJSON = ' + repr(json.dumps(P)) + '\n' + EXTRA_PY


def postprocess(results, ctx):
    items = ctx['items']
    if ctx.get('_w03_scene_ok') and results.get('B02', {}).get('verdict') == 'fail':
        gate_group(results, items, ['B02'],
                   lambda it: str(it.get('group', '')).startswith('zone_') or it.get('group') in ('integration', 'change'),
                   'gate: B02 failed (unit collections missing) -> zone/integration/change groups 0')
    return results
