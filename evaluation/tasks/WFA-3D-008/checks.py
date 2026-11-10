# -*- coding: utf-8 -*-
"""BLD-W08 Qinglan Junction - deterministic checks (31 of 32 rubric items; G13 is left to the VLM judge).

One Blender export (Scene.load) with a task-specific extra_py that adds to EXTRA:
  axes   {name: [chain, ...]}         world polylines of every *_AXIS / *_AXIS_MAIN / *_AXIS_DIV object
  parts  {name: {...}}                per-object islands (centroid, foot centroid, bbox) for countable parts
  obb    {name: {...}}                horizontal-PCA oriented box of DECK / BODY / PORTAL objects
  vplane {name: az}                   dominant vertical-plane normal azimuth (mod 180) of PORTAL / WING objects
  roof   {name: {bins, flat, total}}  area histogram of sloped roof-face azimuths
  portal {name: {...}}                ray-cast hit grid through the portal end wall (opening / face measurement)
  veh    {name: {...}}                vehicle length along local X (incl. children) + dominant material
  mats   {name: {...}}                base / emission colours
  rays   {id: {...}}                  B08 downward ray tests
Every item is wrapped: an exception becomes 'fail' with the traceback tail; S.err fails every scene item.
"""
import json, math, re, traceback
from _bld_lib import Scene, ok, bad, close, png_size, load_manifest, gate_group

STATE = {}
TRACKS = [f"T{i:02d}" for i in range(1, 13)]
TURNOUTS = ["D01", "D02", "D03"]
PLATFORMS = ["P01", "P02", "P03"]
BUILDINGS = ["S01", "S02"]
SIGNALS = ["X01", "X02", "X03", "X04", "X05"]
PORTALS = ["G01", "G02"]
BRIDGES = ["B01", "B02"]
TRAINS = ["R1", "R2", "R3"]
ALL_UNITS = TRACKS + TURNOUTS + PLATFORMS + BUILDINGS + SIGNALS + PORTALS + BRIDGES + TRAINS
PART_RE = r"_(MAST|COL|BENCH|OPENING|VOUSSOIR|PIER|DIAG|ARCH|AXLE|WING|LAMP|MACHINE)"
WATER_RE = re.compile(r"(?i)water|river|creek|stream|lake|brook|水|河|涧")

EXTRA_PY = r'''
import json, math, re
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree
P = json.loads(__P__)
PART = re.compile(P["part_re"])
E = EXTRA
for k in ("axes", "parts", "obb", "vplane", "roof", "portal", "veh", "mats", "rays", "err"):
    E[k] = {} if k != "err" else []

def _mesh(ob):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    return ev, me

def _r(v):
    return [round(v[0], 4), round(v[1], 4), round(v[2], 4)]

def _cap(pl, n=6000):
    if len(pl) <= n:
        return pl
    st = len(pl) / float(n)
    out = [pl[int(i * st)] for i in range(n)]
    out[-1] = pl[-1]
    return out

def _chains(me, mw):
    n = len(me.vertices)
    adj = [[] for _ in range(n)]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b); adj[b].append(a)
    seen = [False] * n
    out = []
    order = sorted(range(n), key=lambda i: len(adj[i]) != 1)
    for s in order:
        if seen[s] or not adj[s]:
            continue
        ch = [s]; seen[s] = True; cur = s
        while True:
            nx = [j for j in adj[cur] if not seen[j]]
            if not nx:
                break
            cur = nx[0]; seen[cur] = True; ch.append(cur)
        if len(ch) > 1:
            out.append(_cap([_r(mw @ me.vertices[i].co) for i in ch]))
    return out

def _splines(ob, nurbs_ok=False):
    mw = ob.matrix_world
    out = []
    for sp in ob.data.splines:
        if sp.type == "NURBS" and not nurbs_ok:
            return []   # NURBS control points lie off the evaluated curve -> use the evaluated to_mesh chain instead
        pts = []
        if sp.type == "BEZIER":
            bp = sp.bezier_points; n = len(bp)
            segs = n - 1 + (1 if sp.use_cyclic_u else 0)
            for i in range(segs):
                a = bp[i]; b = bp[(i + 1) % n]
                seg = geometry.interpolate_bezier(a.co, a.handle_right, b.handle_left, b.co, 33)
                pts += [_r(mw @ v) for v in (seg if i == 0 else seg[1:])]
        else:
            pts = [_r(mw @ Vector(p.co[:3])) for p in sp.points]
        if len(pts) > 1:
            out.append(_cap(pts))
    return out

def axis_chains(ob):
    res = []
    if ob.type == "CURVE":
        try:
            res = _splines(ob)   # high-resolution sampling of the spline itself (preferred)
        except Exception as ex:
            E["err"].append("spline %s: %s" % (ob.name, ex))
        if res:
            return res
    try:
        ev, me = _mesh(ob)
        try:
            if me is not None and len(me.polygons) == 0 and len(me.edges) > 0:
                res = _chains(me, ev.matrix_world)
        finally:
            ev.to_mesh_clear()
    except Exception as ex:
        E["err"].append("axis %s: %s" % (ob.name, ex))
    if not res and ob.type == "CURVE":
        res = _splines(ob, nurbs_ok=True)   # last resort (e.g. bevelled NURBS curve): control polygon
    return res

def world_verts(ob, cap=60000):
    ev, me = _mesh(ob)
    try:
        mw = ev.matrix_world
        vs = me.vertices
        st = max(1, len(vs) // cap)
        return [mw @ vs[i].co for i in range(0, len(vs), st)]
    finally:
        ev.to_mesh_clear()

def part_info(ob):
    ev, me = _mesh(ob)
    try:
        mw = ev.matrix_world
        n = len(me.vertices)
        if n == 0:
            return {"n": 0, "islands": []}
        co = [mw @ v.co for v in me.vertices]
        zmin_o = min(c.z for c in co)
        fx = [c for c in co if c.z <= zmin_o + 0.3]
        foot_o = [sum(c.x for c in fx) / len(fx), sum(c.y for c in fx) / len(fx), zmin_o]
        info = {"n": n, "foot": foot_o, "c": [sum(c.x for c in co) / n, sum(c.y for c in co) / n, sum(c.z for c in co) / n]}
        if n > 300000:
            info["islands"] = None
            return info
        par = list(range(n))
        def f(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for e in me.edges:
            a, b = f(e.vertices[0]), f(e.vertices[1])
            if a != b:
                par[a] = b
        g = {}
        for i in range(n):
            r = f(i); c = co[i]
            d = g.get(r)
            if d is None:
                d = g[r] = [0, 0.0, 0.0, 0.0, [1e9] * 3, [-1e9] * 3]
            d[0] += 1; d[1] += c.x; d[2] += c.y; d[3] += c.z
            for k in range(3):
                d[4][k] = min(d[4][k], c[k]); d[5][k] = max(d[5][k], c[k])
        ft = {}
        for i in range(n):
            r = f(i); c = co[i]
            if c.z <= g[r][4][2] + 0.3:
                t = ft.setdefault(r, [0, 0.0, 0.0]); t[0] += 1; t[1] += c.x; t[2] += c.y
        isl = []
        for r, d in g.items():
            t = ft[r]
            isl.append({"n": d[0], "c": [d[1] / d[0], d[2] / d[0], d[3] / d[0]], "foot": [t[1] / t[0], t[2] / t[0], d[4][2]],
                        "mn": d[4], "mx": d[5]})
        isl.sort(key=lambda x: -x["n"])
        info["islands"] = isl[:3000]
        info["n_islands"] = len(isl)
        return info
    finally:
        ev.to_mesh_clear()

def faces_world(ob):
    ev, me = _mesh(ob)
    try:
        mw = ev.matrix_world
        co = [mw @ v.co for v in me.vertices]
        out = []
        for p in me.polygons:
            vs = [co[i] for i in p.vertices]
            nx = ny = nz = 0.0
            for i in range(len(vs)):
                a = vs[i]; b = vs[(i + 1) % len(vs)]
                nx += (a.y - b.y) * (a.z + b.z); ny += (a.z - b.z) * (a.x + b.x); nz += (a.x - b.x) * (a.y + b.y)
            ar = math.sqrt(nx * nx + ny * ny + nz * nz) / 2.0
            if ar > 1e-9:
                out.append((nx / (2 * ar), ny / (2 * ar), nz / (2 * ar), ar))
        return out
    finally:
        ev.to_mesh_clear()

def vplane_az(ob):
    fs = faces_world(ob)
    if True:
        h = [0.0] * 180
        for nx, ny, nz, ar in fs:
            if abs(nz) < 0.3:
                a = int(math.degrees(math.atan2(ny, nx)) % 180.0) % 180
                h[a] += ar
        if sum(h) <= 0:
            return None
        sm = [sum(h[(i + k) % 180] for k in range(-2, 3)) for i in range(180)]
        i = max(range(180), key=lambda j: sm[j])
        num = sum(h[(i + k) % 180] * (i + k) for k in range(-2, 3)); den = sm[i]
        return (num / den) % 180.0 if den else float(i)

def roof_bins(ob):
    fs = faces_world(ob)
    if True:
        bins = [0.0] * 36; flat = 0.0; tot = 0.0
        for nx, ny, nz, ar in fs:
            if nz <= 0.0:
                continue
            tot += ar
            if nz >= 0.995:
                flat += ar
            elif nz > 0.2:
                bins[int(math.degrees(math.atan2(ny, nx)) % 360.0) // 10 % 36] += ar
        return {"bins": bins, "flat": flat, "total": tot}

def obb(ob):
    vs = world_verts(ob)
    if not vs:
        return None
    n = len(vs)
    mx = sum(v.x for v in vs) / n; my = sum(v.y for v in vs) / n
    sxx = sum((v.x - mx) ** 2 for v in vs); syy = sum((v.y - my) ** 2 for v in vs); sxy = sum((v.x - mx) * (v.y - my) for v in vs)
    th = 0.5 * math.atan2(2 * sxy, sxx - syy)
    ux, uy = math.cos(th), math.sin(th)
    us = [(v.x - mx) * ux + (v.y - my) * uy for v in vs]
    ws = [-(v.x - mx) * uy + (v.y - my) * ux for v in vs]
    u0, u1, w0, w1 = min(us), max(us), min(ws), max(ws)
    cu, cw = (u0 + u1) / 2, (w0 + w1) / 2
    return {"az": math.degrees(th), "L": u1 - u0, "W": w1 - w0, "zmin": min(v.z for v in vs), "zmax": max(v.z for v in vs),
            "c": [mx + cu * ux - cw * uy, my + cu * uy + cw * ux]}

def portal_scan(ob, az, box):
    # the clear opening is bounded by the end wall AND its arch stones (<ID>_VOUSSOIR*): a headwall hole cut to the
    # voussoir extrados with the stones seated in it is a faithful build, so both are ray-cast (obb / vplane stay PORTAL-only)
    gid = ob.name.split("_")[0]
    obs = [ob] + [o for o in scene.objects if o.type == "MESH" and o is not ob and re.match(r"^%s_VOUSSOIR" % gid, o.name)]
    vs, polys = [], []
    for o in obs:
        ev, me = _mesh(o)
        try:
            mw = ev.matrix_world
            k = len(vs)
            vs += [mw @ v.co for v in me.vertices]
            polys += [[k + i for i in p.vertices] for p in me.polygons]
        finally:
            ev.to_mesh_clear()
    bvh = BVHTree.FromPolygons(vs, polys)
    a = math.radians(az)
    nrm = Vector((math.cos(a), math.sin(a), 0.0)); u = Vector((-math.sin(a), math.cos(a), 0.0))
    c = Vector((box["c"][0], box["c"][1], 0.0)); z0 = box["zmin"]
    du = 0.1; dz = 0.1; U0 = -15.0; nu = 301; nzr = int(min(20.0, box["zmax"] - z0 + 0.5) / dz) + 1
    rows = []
    for j in range(nzr):
        z = z0 + 0.05 + j * dz
        s = []
        for i in range(nu):
            o = c + u * (U0 + i * du) - nrm * 25.0
            o.z = z
            hit = bvh.ray_cast(o, nrm, 50.0)
            s.append("1" if hit[0] is not None else "0")
        rows.append("".join(s))
    return {"az": az, "c": box["c"], "zmin": z0, "du": du, "dz": dz, "u0": U0, "rows": rows, "objs": [o.name for o in obs]}

for ob in scene.objects:
    nm = ob.name
    try:
        if re.search(r"_AXIS(_MAIN|_DIV)?$", nm) and ob.type in ("CURVE", "MESH"):
            E["axes"][nm] = axis_chains(ob)
        if ob.type != "MESH":
            continue
        if PART.search(nm):
            E["parts"][nm] = part_info(ob)
        if re.search(r"^(P0\d_DECK|S0\d_BODY|B0\d_DECK|G0\d_PORTAL)$", nm):
            E["obb"][nm] = obb(ob)
        if re.search(r"^G0\d_(PORTAL|WING)", nm):
            E["vplane"][nm] = vplane_az(ob)
        if re.search(r"^S0\d_ROOF", nm):
            E["roof"][nm] = roof_bins(ob)
    except Exception as ex:
        E["err"].append("%s: %s" % (nm, ex))

for nm in ("G01_PORTAL", "G02_PORTAL"):
    try:
        ob = bpy.data.objects.get(nm)
        if ob is not None and ob.type == "MESH" and E["vplane"].get(nm) is not None and E["obb"].get(nm):
            E["portal"][nm] = portal_scan(ob, E["vplane"][nm], E["obb"][nm])
    except Exception as ex:
        E["err"].append("scan %s: %s" % (nm, ex))

for ob in scene.objects:
    if not re.match(r"^R\d_V\d\d$", ob.name):
        continue
    try:
        inv = ob.matrix_world.inverted()
        xs = []; areas = {}
        for o in [ob] + list(ob.children_recursive):
            if o.type != "MESH":
                continue
            ev, me = _mesh(o)
            try:
                mw = ev.matrix_world
                for v in me.vertices:
                    xs.append((inv @ (mw @ v.co)).x)
                slots = [s.material.name if s.material else None for s in o.material_slots]
                for p in me.polygons:
                    m = slots[p.material_index] if p.material_index < len(slots) else None
                    if m:
                        areas[m] = areas.get(m, 0.0) + p.area
            finally:
                ev.to_mesh_clear()
        sx = ob.matrix_world.to_3x3().col[0].length
        E["veh"][ob.name] = {"len": (max(xs) - min(xs)) * sx if xs else None, "xmin": min(xs) if xs else None,
                             "xmax": max(xs) if xs else None, "mat": max(areas, key=areas.get) if areas else None}
    except Exception as ex:
        E["err"].append("veh %s: %s" % (ob.name, ex))

for m in bpy.data.materials:
    d = {"base": None, "emis": None}
    try:
        d["base"] = list(m.diffuse_color)[:3]
        if m.use_nodes and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    bc = n.inputs["Base Color"]
                    d["base"] = list(bc.default_value)[:3]
                    if bc.is_linked:
                        fn = bc.links[0].from_node
                        if fn.type == "RGB":
                            d["base"] = list(fn.outputs[0].default_value)[:3]
                        else:
                            d["base_linked"] = fn.type
                    try:
                        if n.inputs["Emission Strength"].default_value > 0:
                            d["emis"] = list(n.inputs["Emission Color"].default_value)[:3]
                    except Exception:
                        pass
                elif n.type == "EMISSION":
                    d["emis"] = list(n.inputs["Color"].default_value)[:3]
    except Exception as ex:
        E["err"].append("mat %s: %s" % (m.name, ex))
    E["mats"][m.name] = d

for r in P["rays"]:
    try:
        res = scene.ray_cast(dg, Vector(r["o"]), Vector(r["d"]))
        hit, loc, nrm, idx, ob = res[0], res[1], res[2], res[3], res[4]
        E["rays"][r["id"]] = {"hit": bool(hit), "obj": ob.name if (hit and ob) else None, "z": loc.z if hit else None,
                              "mats": [s.material.name for s in ob.material_slots if s.material] if (hit and ob) else []}
    except Exception as ex:
        E["rays"][r["id"]] = {"hit": False, "error": str(ex)}
'''


# ------------------------------------------------------------------ small geometry helpers (pure python)
def d2(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angdiff(a, b, period=360.0):
    d = (a - b) % period
    return min(d, period - d)


def az_of(v):
    return math.degrees(math.atan2(v[1], v[0]))


def plan_len(pl):
    return sum(d2(pl[i], pl[i + 1]) for i in range(len(pl) - 1))


def point_at(pl, s):
    """point and unit plan tangent at plan arc length s from pl[0]."""
    acc = 0.0
    for i in range(len(pl) - 1):
        L = d2(pl[i], pl[i + 1])
        if L <= 1e-12:
            continue
        if acc + L >= s or i == len(pl) - 2:
            t = max(0.0, min(1.0, (s - acc) / L))
            a, b = pl[i], pl[i + 1]
            p = [a[k] + t * (b[k] - a[k]) for k in range(3)]
            return p, [(b[0] - a[0]) / L, (b[1] - a[1]) / L]
        acc += L
    return list(pl[-1]), [1.0, 0.0]


def outward(pl, at_end, d=0.5):
    """outward plan tangent at an end (pointing out of the curve).
    Uses the last chord plus a curvature correction from the last three distinct points (exact for sampled circular
    arcs, independent of the sampling density); falls back to the secant over d metres."""
    seq = pl if at_end else pl[::-1]
    pts = [seq[-1]]
    for p in reversed(seq[:-1]):
        if d2(p, pts[-1]) > 1e-4:
            pts.append(p)
        if len(pts) == 3:
            break
    if len(pts) >= 2:
        c, b_ = pts[0], pts[1]
        a2 = math.atan2(c[1] - b_[1], c[0] - b_[0]); l2 = d2(c, b_)
        if len(pts) == 3:
            a_ = pts[2]
            a1 = math.atan2(b_[1] - a_[1], b_[0] - a_[0]); l1 = d2(b_, a_)
            phi = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
            a2 += phi / ((l1 + l2) / 2) * l2 / 2
        return [math.cos(a2), math.sin(a2)]
    q = pl[::-1] if at_end else pl
    e = q[0]
    p, _ = point_at(q, d)
    v = [e[0] - p[0], e[1] - p[1]]
    n = math.hypot(*v) or 1.0
    return [v[0] / n, v[1] / n]


def nearest_on(pl, p):
    """(plan distance, z at foot, unit tangent, cross sign (+1 = p is left of direction), s along)."""
    best = None
    acc = 0.0
    for i in range(len(pl) - 1):
        a, b = pl[i], pl[i + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        L = math.sqrt(L2)
        if L2 <= 1e-12:
            continue
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        fx, fy = a[0] + t * dx, a[1] + t * dy
        dd = math.hypot(p[0] - fx, p[1] - fy)
        if best is None or dd < best[0]:
            cr = dx * (p[1] - a[1]) - dy * (p[0] - a[0])
            best = (dd, a[2] + t * (b[2] - a[2]), [dx / L, dy / L], 1 if cr > 0 else -1, acc + t * L)
        acc += L
    return best


class SegIndex:
    def __init__(self, polylines, cell=10.0):
        self.cell = cell
        self.segs = []
        self.grid = {}
        for pl in polylines:
            for i in range(len(pl) - 1):
                a, b = pl[i], pl[i + 1]
                L = d2(a, b)
                if L < 1e-9 or L > 5000.0 or not all(math.isfinite(x) for x in (a[0], a[1], b[0], b[1])):
                    continue   # degenerate or absurd (stray vertex) segment
                k = len(self.segs)
                self.segs.append((a, b))
                # register the cells the segment passes through (sampled every cell/2); nearest() scans the 3x3
                # neighbourhood, so any point within one cell of the segment finds it. Cost is linear in length.
                n = int(L / (cell / 2)) + 1
                cells = set()
                for t in range(n + 1):
                    x = a[0] + (b[0] - a[0]) * t / n; y = a[1] + (b[1] - a[1]) * t / n
                    cells.add((int(math.floor(x / cell)), int(math.floor(y / cell))))
                for c in cells:
                    self.grid.setdefault(c, []).append(k)

    def nearest(self, p):
        cx, cy = int(math.floor(p[0] / self.cell)), int(math.floor(p[1] / self.cell))
        cand = set()
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                cand.update(self.grid.get((cx + i, cy + j), ()))
        best = None
        for k in cand:
            a, b = self.segs[k]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
            dd = math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
            if best is None or dd < best[0]:
                L = math.sqrt(L2)
                best = (dd, a[2] + t * (b[2] - a[2]), [dx / L, dy / L])
        return best


def lin2srgb(c):
    return [12.92 * x if x <= 0.0031308 else 1.055 * (max(x, 0.0) ** (1 / 2.4)) - 0.055 for x in c[:3]]


def hex2rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


def hsv(c):
    r, g, b = c
    mx, mn = max(c), min(c)
    v = mx
    s = 0 if mx <= 0 else (mx - mn) / mx
    if mx == mn:
        h = 0.0
    elif mx == r:
        h = (60 * ((g - b) / (mx - mn)) + 360) % 360
    elif mx == g:
        h = 60 * ((b - r) / (mx - mn)) + 120
    else:
        h = 60 * ((r - g) / (mx - mn)) + 240
    return h, s, v


def cluster_count(vals, gap):
    v = sorted(vals)
    if not v:
        return 0
    return 1 + sum(1 for i in range(1, len(v)) if v[i] - v[i - 1] > gap)


# ------------------------------------------------------------------ measurement context
class M:
    def __init__(self, S, K):
        self.S, self.K, self.U = S, K, K['units']
        self.X = (S.data or {}).get('extra', {}) or {}
        self._axis = {}
        self.STATE = {}

    # --- axes
    def axis(self, name):
        if name in self._axis:
            return self._axis[name]
        chains = [c for c in (self.X.get('axes', {}).get(name) or []) if len(c) > 1]
        pl = None
        if chains:
            chains = sorted(chains, key=lambda c: -plan_len(c))
            pl = list(chains[0])
            rest = chains[1:]
            changed = True
            while rest and changed:
                changed = False
                for c in list(rest):
                    for cc in (c, c[::-1]):
                        if d2(pl[-1], cc[0]) < 0.05:
                            pl = pl + list(cc[1:]); rest.remove(c); changed = True; break
                        if d2(pl[0], cc[-1]) < 0.05:
                            pl = list(cc[:-1]) + pl; rest.remove(c); changed = True; break
                    if changed:
                        break
        self._axis[name] = pl
        return pl

    def track(self, tid):
        """AXIS polyline oriented start->end according to the answer key."""
        pl = self.axis(f'{tid}_AXIS')
        if not pl:
            return None
        ks = self.U[tid]['geom']['start']
        return pl if d2(pl[0], ks) <= d2(pl[-1], ks) else pl[::-1]

    def turnout(self, did):
        """dict(toe, main_end, div_end points + outward dirs) or None."""
        mn, dv = self.axis(f'{did}_AXIS_MAIN'), self.axis(f'{did}_AXIS_DIV')
        if not mn or not dv:
            return None
        pairs = [(d2(mn[i], dv[j]), i, j) for i in (0, -1) for j in (0, -1)]
        _, i, j = min(pairs)
        mn = mn if i == 0 else mn[::-1]
        dv = dv if j == 0 else dv[::-1]
        return {'main': mn, 'div': dv, 'toe': mn[0], 'toe_out': outward(mn, False), 'main_end': mn[-1],
                'main_end_out': outward(mn, True), 'div_end': dv[-1], 'div_end_out': outward(dv, True)}

    def endpoint(self, tag):
        u, e = tag.split('.')
        if u.startswith('T'):
            pl = self.track(u)
            if not pl:
                return None
            return (pl[0], outward(pl, False)) if e == 'start' else (pl[-1], outward(pl, True))
        t = self.turnout(u)
        if not t:
            return None
        return t[e], t[e + '_out']

    def all_axes(self):
        out = []
        for n in self.X.get('axes', {}):
            pl = self.axis(n)
            if pl:
                out.append(pl)
        return out

    # --- parts
    def part_objs(self, uid, kind):
        r = re.compile(rf'^{uid}_{kind}(_|\.|$)')
        names = [n for n in self.S.coll(uid) if r.search(n)]
        names = [n for n in names if (self.S.ob(n) or {}).get('type') == 'MESH']
        top = [n for n in names if (self.S.ob(n) or {}).get('parent') not in names]
        return sorted(top)

    def parts(self, uid, kind):
        """list of dicts {c, foot} for each countable part (objects if >=2, else islands of the single object)."""
        names = self.part_objs(uid, kind)
        P = self.X.get('parts', {})
        if len(names) >= 2:
            out = []
            for n in names:
                info = P.get(n) or {}
                bb = (self.S.ob(n) or {}).get('bbox_world')
                c = info.get('c') or (Scene.center(bb) if bb else None)
                foot = info.get('foot') or ([c[0], c[1], bb[0][2]] if (c and bb) else c)
                out.append({'c': c, 'foot': foot, 'name': n})
            return out
        if len(names) == 1:
            info = P.get(names[0]) or {}
            isl = info.get('islands')
            if isl:
                return [{'c': i['c'], 'foot': i['foot'], 'name': names[0]} for i in isl]
            bb = (self.S.ob(names[0]) or {}).get('bbox_world')
            c = info.get('c') or (Scene.center(bb) if bb else None)
            return [{'c': c, 'foot': info.get('foot') or c, 'name': names[0]}]
        return []

    def has(self, uid, kind):
        return bool(self.part_objs(uid, kind)) or any(re.match(rf'^{uid}_{kind}$', n) for n in self.S.coll(uid))

    def mat_rgb(self, name, prefer_emis=False, raw=False):
        """sRGB display colour of a material (Blender stores linear values). raw=True returns the stored value
        unconverted (for scripts that wrote hex/255 straight into Base Color)."""
        conv = (lambda c: list(c[:3])) if raw else lin2srgb
        d = self.X.get('mats', {}).get(name)
        if d:
            cands = [c for c in (d.get('emis'), d.get('base')) if c]
            if prefer_emis and cands:
                cands = sorted(cands, key=lambda c: -hsv(lin2srgb(c))[1])
            return conv(cands[0]) if cands else None
        bc = ((self.S.data or {}).get('materials', {}).get(name) or {}).get('base_color')
        return conv(bc) if bc else None

    def obj_rgb(self, objname, prefer_emis=False, raw=False):
        mats = (self.S.ob(objname) or {}).get('materials') or []
        for m in mats:
            c = self.mat_rgb(m, prefer_emis, raw)
            if c:
                return c
        return None

    # --- discrete measurements
    def track_disc(self, tid):
        pl = self.track(tid)
        masts = self.parts(tid, 'MAST')
        side = None
        offs = []
        if pl and masts:
            sides = []
            for m in masts:
                nb = nearest_on(pl, m['foot'] or m['c'])
                sides.append('L' if nb[3] > 0 else 'R')
                offs.append(nb[0])
            side = sides[0] if len(set(sides)) == 1 else 'mixed'
        sl = None
        snames = [n for n in self.S.coll(tid) if re.match(rf'^{tid}_SLEEPERS', n)]
        for n in snames:
            c = self.obj_rgb(n)
            if c:
                # legend timber #5B3A1E / concrete #B9B9B9 (sRGB); the stored colour is read both as linear (-> sRGB)
                # and as already-sRGB (hex/255 written directly), and the interpretation nearest to a legend colour wins
                wood, conc = [0.357, 0.227, 0.118], [0.725, 0.725, 0.725]
                best = None
                for cc in (c, self.obj_rgb(n, raw=True) or c):
                    dw = sum((cc[i] - wood[i]) ** 2 for i in range(3)); dc = sum((cc[i] - conc[i]) ** 2 for i in range(3))
                    if best is None or min(dw, dc) < best[0]:
                        best = (min(dw, dc), dw, dc, cc)
                _, dw, dc, cc = best
                h, s, v = hsv(cc)
                sl = 'wood' if (dw < dc and cc[0] >= cc[2]) else ('concrete' if s < 0.25 else None)
                break
        return {'masts': len(masts), 'mast_side': side, 'sleeper': sl, 'mast_offsets': offs}

    def turnout_disc(self, did):
        t = self.turnout(did)
        if not t:
            return {}
        mdir = [t['main_end'][0] - t['toe'][0], t['main_end'][1] - t['toe'][1]]
        n = math.hypot(*mdir) or 1.0
        mdir = [mdir[0] / n, mdir[1] / n]
        de = [t['div_end'][0] - t['toe'][0], t['div_end'][1] - t['toe'][1]]
        hand = 'L' if mdir[0] * de[1] - mdir[1] * de[0] > 0 else 'R'
        ang = angdiff(az_of(t['div_end_out']), az_of(mdir))
        frog = '1:6' if abs(ang - 9.46) <= 0.5 else ('1:9' if abs(ang - 6.34) <= 0.5 else None)
        ms = None
        mc = self.part_objs(did, 'MACHINE')
        if mc:
            bb = (self.S.ob(mc[0]) or {}).get('bbox_world')
            c = Scene.center(bb) if bb else None
            if c:
                cr = mdir[0] * (c[1] - t['toe'][1]) - mdir[1] * (c[0] - t['toe'][0])
                ms = 'L' if cr > 0 else 'R'
        return {'hand': hand, 'frog': frog, 'angle_deg': ang, 'machine_side': ms}

    def platform_disc(self, pid):
        cols = self.parts(pid, 'COL')
        benches = self.parts(pid, 'BENCH')
        ob = self.X.get('obb', {}).get(f'{pid}_DECK')
        rows = 0
        if cols:
            az = math.radians(ob['az']) if ob else math.radians(self.U[pid]['geom']['heading_deg'])
            nx, ny = -math.sin(az), math.cos(az)
            lat = [c['c'][0] * nx + c['c'][1] * ny for c in cols if c['c']]
            rows = cluster_count(lat, 0.8)
        canopy = {0: 'none', 1: 'single', 2: 'double'}.get(rows)
        return {'canopy': canopy, 'canopy_columns': len(cols), 'benches': len(benches), 'rows': rows}

    def roof_type(self, sid):
        rs = [v for k, v in self.X.get('roof', {}).items() if k.startswith(f'{sid}_ROOF') and v]
        if not rs:
            return None
        bins = [sum(r['bins'][i] for r in rs) for i in range(36)]
        flat = sum(r['flat'] for r in rs); tot = sum(r['total'] for r in rs)
        sl = sum(bins)
        if tot <= 0:
            return None
        if sl < 0.1 * tot:
            return 'flat' if flat > 0.5 * tot else None
        # clusters of significant azimuth bins (circular)
        sig = [b >= 0.06 * sl for b in bins]
        if all(sig):
            return None
        start = sig.index(False)
        n = 0
        prev = False
        for k in range(36):
            cur = sig[(start + k) % 36]
            if cur and not prev:
                n += 1
            prev = cur
        return {4: 'hip', 2: 'gable'}.get(n, f'{n}-slope')

    def building_disc(self, sid):
        op = self.parts(sid, 'OPENING')
        zs = [o['c'][2] for o in op if o['c']]
        floors = cluster_count(zs, 1.0)
        bays = (len(op) // floors) if floors and len(op) % floors == 0 else None
        return {'floors': floors, 'bays': bays, 'openings': len(op), 'roof': self.roof_type(sid),
                'clock_tower': any(re.match(rf'^{sid}_TOWER', n) for n in self.S.coll(sid))}

    def lamp_class(self, objname):
        c = self.obj_rgb(objname, prefer_emis=True)
        if not c:
            return None
        h, s, v = hsv(c)
        if s < 0.25 or v < 0.15:
            return None
        if h < 20 or h >= 330:
            return 'R'
        if h < 75:
            return 'Y'
        if h < 185:
            return 'G'
        return None

    def signal_disc(self, xid):
        lamps = self.part_objs(xid, 'LAMP')
        lamps = sorted(lamps, key=lambda n: -Scene.center((self.S.ob(n) or {}).get('bbox_world') or [[0, 0, 0], [0, 0, 0]])[2])
        cols = [self.lamp_class(n) for n in lamps]
        if len(lamps) == 1:
            isl = (self.X.get('parts', {}).get(lamps[0]) or {}).get('n_islands') or 1
            if isl > 1:
                cols = [None] * isl
        return {'aspects': len(cols), 'colors': cols,
                'ladder': any(re.match(rf'^{xid}_LADDER', n) for n in self.S.coll(xid))}

    def portal_meas(self, gid):
        sc = self.X.get('portal', {}).get(f'{gid}_PORTAL')
        if not sc:
            return {}
        rows = sc['rows']; du, dz, U0 = sc['du'], sc['dz'], sc['u0']
        nu = len(rows[0]) if rows else 0
        i0 = int(round(-U0 / du))

        def miss_interval(r, i):
            if r[i] == '1':
                return None
            a = b = i
            while a > 0 and r[a - 1] == '0':
                a -= 1
            while b < nu - 1 and r[b + 1] == '0':
                b += 1
            if a == 0 or b == nu - 1:
                return None   # not enclosed
            return a, b

        z0 = sc['zmin'] + 0.05
        rz = self.rail_z_at(sc['c'], gid)
        jr = max(0, min(len(rows) - 1, int(round((max(rz, sc['zmin']) + 1.0 - z0) / dz))))
        r = rows[jr]
        # opening column: nearest enclosed miss interval to centre at ~1 m above base
        best = None
        for i in range(nu):
            iv = miss_interval(r, i)
            if iv and (best is None or abs((iv[0] + iv[1]) / 2 - i0) < abs((best[0] + best[1]) / 2 - i0)):
                best = iv
        if not best:
            return {'error': 'no enclosed opening found'}
        ic = (best[0] + best[1]) // 2
        top = None
        widths = []
        for j in range(len(rows)):
            iv = miss_interval(rows[j], ic)
            if iv is None:
                if rows[j][ic] == '1' and j > jr:
                    top = j
                    break
                widths.append(0)
                continue
            widths.append((iv[1] - iv[0] + 1) * du)
        open_w = max(widths) if widths else None
        jrail = max(0, min(len(rows) - 1, int(round((rz + 0.2 - z0) / dz))))
        w_rail = (miss_interval(rows[jrail], ic) or (0, -1))
        w_rail = (w_rail[1] - w_rail[0] + 1) * du
        jm = min(len(rows) - 1, (jrail + top) // 2 if top is not None else jrail + 30)
        hits = [i for i, ch in enumerate(rows[jm]) if ch == '1']
        face_w = (hits[-1] - hits[0] + 1) * du if hits else None
        top_hit = max((j for j in range(len(rows)) if '1' in rows[j]), default=None)
        face_h = (z0 + (top_hit + 0.5) * dz - rz) if top_hit is not None else None
        open_h = (z0 + (top - 0.5) * dz - rz) if top is not None else None
        a = math.radians(sc['az'])
        uc = U0 + ic * du
        cx = sc['c'][0] + uc * (-math.sin(a)); cy = sc['c'][1] + uc * math.cos(a)
        return {'open_w': open_w, 'open_w_base': w_rail, 'open_h': open_h, 'face_w': face_w, 'face_h': face_h,
                'ratio': (w_rail / open_w) if open_w else None, 'center': [cx, cy], 'base_z': sc['zmin'], 'rail_z': rz, 'az': sc['az']}

    def rail_z_at(self, xy, uid):
        pl = self.track(self.U[uid]['placement']['section'])
        if pl:
            nb = nearest_on(pl, xy)
            if nb and nb[0] < 5.0:
                return nb[1]
        return self.U[uid]['geom'].get('rail_z', 0.0)

    def portal_disc(self, gid):
        pm = self.portal_meas(gid)
        shape = None
        if pm.get('ratio') is not None:
            shape = 'semicircular' if pm['ratio'] >= 0.98 else ('horseshoe' if pm['ratio'] <= 0.95 else None)
        vp = self.X.get('vplane', {})
        paz = vp.get(f'{gid}_PORTAL')
        wings = [n for n in self.part_objs(gid, 'WING')]
        ww = None
        if paz is not None and wings:
            angs = []
            for n in wings:
                w = vp.get(n)
                if w is None:
                    angs = None
                    break
                angs.append(angdiff(w, paz, 180.0))
            if angs:
                if all(15 <= x <= 75 for x in angs):
                    ww = 'splayed'
                elif all(x <= 5 for x in angs):
                    ww = 'straight'
        return {'shape': shape, 'voussoirs': len(self.parts(gid, 'VOUSSOIR')), 'wing_walls': ww, 'meas': pm}

    def bridge_disc(self, bid):
        piers = len(self.parts(bid, 'PIER'))
        diag = len(self.parts(bid, 'DIAG'))
        arch = len(self.parts(bid, 'ARCH'))
        typ = 'warren_through' if diag and not arch else ('stone_arch_deck' if arch and not diag else None)
        spans = arch if typ == 'stone_arch_deck' else (piers + 1 if typ == 'warren_through' else None)
        pps = (diag // (spans * 4)) if (typ == 'warren_through' and spans and diag % (spans * 4) == 0) else (0 if typ == 'stone_arch_deck' else None)
        return {'type': typ, 'spans': spans, 'panels_per_span': pps, 'piers': piers, 'diag': diag, 'arch': arch}

    def vehicles(self, rid):
        r = re.compile(rf'^{rid}_V\d\d$')
        return sorted(n for n in self.S.coll(rid) if r.match(n))

    def train_disc(self, rid):
        vs = self.vehicles(rid)
        return {'n_vehicles': len(vs), 'loco_axles': self.axles(rid)}

    def axles(self, rid):
        r = re.compile(rf'^{rid}_V01_AXLE(_|\.|$)')
        names = [n for n in self.S.coll(rid) if r.search(n) and (self.S.ob(n) or {}).get('type') == 'MESH']
        names = [n for n in names if (self.S.ob(n) or {}).get('parent') not in names]
        if len(names) >= 2:
            return len(names)
        if len(names) == 1:
            return (self.X.get('parts', {}).get(names[0]) or {}).get('n_islands') or 1
        return 0

    def veh_len(self, name):
        v = self.X.get('veh', {}).get(name) or {}
        return v.get('len')

    def veh_rgb(self, name, raw=False):
        v = self.X.get('veh', {}).get(name) or {}
        return self.mat_rgb(v['mat'], raw=raw) if v.get('mat') else self.obj_rgb(name, raw=raw)

    def veh_colour_ok(self, name, hexcol, tol=0.08):
        """(ok, shown colour): Base Color read as linear->sRGB, or taken directly (hex/255), either within tol."""
        e = hex2rgb(hexcol)
        c = self.veh_rgb(name)
        for cc in (c, self.veh_rgb(name, raw=True)):
            if cc and max(abs(cc[i] - e[i]) for i in range(3)) <= tol:
                return True, cc
        return False, c

    def measure_unit(self, uid):
        if uid in TRACKS:
            return self.track_disc(uid)
        if uid in TURNOUTS:
            return self.turnout_disc(uid)
        if uid in PLATFORMS:
            return self.platform_disc(uid)
        if uid in BUILDINGS:
            return self.building_disc(uid)
        if uid in SIGNALS:
            return self.signal_disc(uid)
        if uid in PORTALS:
            return self.portal_disc(uid)
        if uid in BRIDGES:
            return self.bridge_disc(uid)
        if uid in TRAINS:
            return self.train_disc(uid)
        return {}


# ------------------------------------------------------------------ item implementations
def fails(lst):
    return bad('; '.join(lst)[:600]) if lst else None


def chk_track_ends(m, tids, tol, ztol, errs):
    for t in tids:
        pl = m.track(t)
        if not pl:
            errs.append(f'{t}_AXIS missing'); continue
        g = m.U[t]['geom']
        for e, p in (('start', pl[0]), ('end', pl[-1])):
            dd = d2(p, g[e]); dz = abs(p[2] - g[e][2])
            if dd > tol or (ztol is not None and dz > ztol):
                errs.append(f'{t}.{e} plan {dd:.3f} z {dz:.3f}')


def chk_signal_pos(m, xs, errs):
    for x in xs:
        mp = m.parts(x, 'MAST')
        if not mp:
            errs.append(f'{x}_MAST missing'); continue
        f = mp[0]['foot']
        dd = d2(f, m.U[x]['geom']['mast_xy'])
        if dd > 0.30:
            errs.append(f'{x} mast {dd:.2f} m off')


def obbx(m, name):
    return m.X.get('obb', {}).get(name)


def disc_compare(m, uid, fields, errs):
    me = m.measure_unit(uid)
    kp = m.U[uid]['params']
    for f in fields:
        if f == 'openings':
            exp = m.U[uid]['derived']['openings']
        elif f == 'rows':
            exp = m.U[uid]['derived']['column_rows']
        elif f == 'diag':
            exp = m.U[uid]['derived']['diag_islands']
        elif f == 'arch':
            exp = m.U[uid]['derived']['arch_islands']
        else:
            exp = kp[f]
        got = me.get(f)
        if isinstance(exp, list):
            okk = got == [str(c).upper() for c in exp]
        else:
            okk = got == exp
        if not okk:
            errs.append(f'{uid}.{f}={got!r} exp {exp!r}')
    return me


TRACK_F = ['masts', 'mast_side', 'sleeper']


def run(ctx):
    R = {}
    K = ctx['answer']
    U = K['units']
    items = ctx['items']
    out = ctx['out']
    ids = [i['id'] for i in items]

    def guard(iid, fn):
        try:
            R[iid] = fn()
        except Exception:
            R[iid] = bad('check exception: ' + traceback.format_exc()[-400:])

    # ---------- file-only items
    def b06():
        req = {'overview.png': (1920, 1080), 'hub.png': (1280, 720), 'terminus.png': (1280, 720)}
        errs = []
        for fn, sz in req.items():
            p = out / 'renders' / fn
            if not p.exists():
                errs.append(f'{fn} missing'); continue
            got = png_size(p)
            if got != sz:
                errs.append(f'{fn} size {got} != {sz}'); continue
            sd = png_std(p)
            if sd is not None and sd <= 5:
                errs.append(f'{fn} blank (std {sd:.2f})')
        return fails(errs) or ok('3 renders at required sizes, non-blank')
    guard('B06', b06)

    man = load_manifest(out)
    REQ = {'track': ['elements', 'z_start', 'z_end', 'masts', 'mast_side', 'sleeper'],
           'turnout': ['hand', 'frog', 'radius', 'angle_deg', 'machine_side'],
           'platform': ['length', 'width', 'height', 'canopy', 'canopy_columns', 'benches'],
           'station_building': ['length', 'depth', 'floors', 'bays', 'roof', 'clock_tower'],
           'signal': ['aspects', 'colors', 'ladder', 'height'],
           'tunnel_portal': ['shape', 'voussoirs', 'wing_walls'],
           'bridge': ['type', 'spans', 'panels_per_span', 'piers'],
           'train': ['n_vehicles', 'loco_axles', 'vehicle_lengths', 'colors']}

    def b07():
        if not isinstance(man, list):
            return bad('manifest.json missing or not a JSON array')
        errs = []
        if len(man) != 32:
            errs.append(f'{len(man)} entries (need 32)')
        mids = [e.get('id') if isinstance(e, dict) else None for e in man]
        if sorted(map(str, mids)) != sorted(ALL_UNITS):
            errs.append(f'ids mismatch: missing {sorted(set(ALL_UNITS) - set(mids))}, extra {sorted(set(map(str, mids)) - set(ALL_UNITS))}')
        for e in man:
            if not isinstance(e, dict):
                errs.append('non-object entry'); continue
            miss = [k for k in ('id', 'collection', 'built', 'params') if k not in e]
            if miss:
                errs.append(f"{e.get('id')}: missing {miss}"); continue
            u = U.get(e['id'])
            if not u:
                continue
            pm = e['params'] if isinstance(e['params'], dict) else {}
            mf = [f for f in REQ[u['type']] if f not in pm]
            if mf:
                errs.append(f"{e['id']}: params missing {mf}")
        return fails(errs) or ok('32 entries, ids and per-type fields complete')
    guard('B07', b07)

    # ---------- scene
    frames = sorted(set(list(range(1, 1441, 6)) + list(range(1, 1441, 12)) +
                        [48, 720, 816, 1392, 1440, 648, 1236, 96, 888, 432, 516, 264, 942, 384, 1104]))
    t11 = U['T11']['geom']
    h = math.radians(t11['start_heading'])
    hp = [t11['start'][0] + 60 * math.cos(h), t11['start'][1] + 60 * math.sin(h)]
    # probes are placed clear of the B02 deck (revised and pre-CO positions) and of the B01 centre pier (see VERIFIER_NOTES.md)
    rays = [{'id': 'river_c', 'o': [464.1, -245.0, 60.0], 'd': [0, 0, -1]},
            {'id': 'river_w', 'o': [454.1, -245.0, 60.0], 'd': [0, 0, -1]},
            {'id': 'river_e', 'o': [474.1, -245.0, 60.0], 'd': [0, 0, -1]},
            {'id': 'river_n', 'o': [464.1, -215.0, 60.0], 'd': [0, 0, -1]},   # 11.3 m off the revised B02 axis, 7.5 m off the pre-CO one
            {'id': 'river_s', 'o': [464.1, -255.0, 60.0], 'd': [0, 0, -1]},
            {'id': 'creek', 'o': [30.0, 150.0, 4.5], 'd': [0, 0, -1]},
            {'id': 'creek_s', 'o': [30.0, 130.0, 4.5], 'd': [0, 0, -1]},
            {'id': 'hill', 'o': [hp[0], hp[1], 3.2 + 30.0], 'd': [0, 0, -1]}]
    params = {'part_re': PART_RE, 'rays': rays}
    extra = EXTRA_PY.replace('__P__', repr(json.dumps(params)))
    S = Scene.load(ctx, frames=frames, anim_regex=r'^R[123]_V\d\d$', extra_py=extra)
    scene_ids = [i for i in ids if i not in ('B06', 'B07', 'G13')]
    if S.err or not S.data:
        for i in scene_ids:
            R[i] = bad(f'scene unavailable: {S.err}')
        STATE['coll_hits'] = 0
        STATE['axis_missing'] = 18
        STATE['scene_err'] = S.err or 'no data'
        return R
    STATE['scene_err'] = None
    m = M(S, K)
    sc = S.data.get('scene', {})

    def b01():
        if sc.get('unit_system') == 'METRIC' and abs(float(sc.get('scale_length', 0)) - 1.0) < 1e-6:
            return ok('METRIC, scale 1.0')
        return bad(f"unit_system={sc.get('unit_system')} scale_length={sc.get('scale_length')}")
    guard('B01', b01)

    def b02():
        miss, empty = [], []
        hits = 0
        for c in ALL_UNITS + ['SITE']:
            if not S.has_coll(c):
                miss.append(c); continue
            if c != 'SITE':
                hits += 1
            if not any((S.ob(n) or {}).get('type') in ('MESH', 'CURVE') for n in S.coll(c)):
                empty.append(c)
        STATE['coll_hits'] = hits
        if miss or empty:
            return bad(f'missing {miss}; no mesh/curve in {empty}')
        return ok('32 unit collections + SITE present, all non-empty')
    guard('B02', b02)

    def b03():
        miss = []
        for t in TRACKS:
            n = f'{t}_AXIS'
            if not (S.ob(n) and n in S.coll(t) and m.axis(n)):
                miss.append(n)
        for d in TURNOUTS:
            for s in ('_AXIS_MAIN', '_AXIS_DIV'):
                n = d + s
                if not (S.ob(n) and n in S.coll(d) and m.axis(n)):
                    miss.append(n)
        STATE['axis_missing'] = len(miss)
        return bad(f'missing/invalid centreline curves: {miss}') if miss else ok('18 centreline curves present')
    STATE['axis_missing'] = 18
    guard('B03', b03)

    def b04():
        req = {}
        for t in TRACKS:
            req[t] = ['MAST', 'SLEEPERS']
        for d in TURNOUTS:
            req[d] = ['MACHINE']
        for p in PLATFORMS:
            req[p] = ['DECK', 'BENCH'] + (['COL'] if U[p]['params']['canopy'] != 'none' else [])
        for s in BUILDINGS:
            req[s] = ['BODY', 'ROOF', 'OPENING'] + (['TOWER'] if U[s]['params']['clock_tower'] else [])
        for x in SIGNALS:
            req[x] = ['MAST', 'LAMP'] + (['LADDER'] if U[x]['params']['ladder'] else [])
        for g in PORTALS:
            req[g] = ['PORTAL', 'VOUSSOIR', 'WING']
        for b in BRIDGES:
            req[b] = ['DECK', 'PIER', 'DIAG' if U[b]['params']['type'] == 'warren_through' else 'ARCH']
        errs = []
        for u, ks in req.items():
            names = S.coll(u)
            for k in ks:
                if not any(re.match(rf'^{u}_{k}', n) for n in names):
                    errs.append(f'{u}_{k}')
        for r in TRAINS:
            names = S.coll(r)
            for v in U[r]['params']['vehicles']:
                if v['id'] not in names:
                    errs.append(v['id'])
            if not any(re.match(rf'^{r}_V01_AXLE', n) for n in names):
                errs.append(f'{r}_V01_AXLE')
        return bad('missing parts: ' + ', '.join(errs)) if errs else ok('all required part prefixes present')
    guard('B04', b04)

    def b05():
        fps, fb = sc.get('fps'), sc.get('fps_base')
        if fps == 24 and abs(float(fb or 0) - 1.0) < 1e-6 and sc.get('frame_start') == 1 and sc.get('frame_end') == 1440:
            return ok('24 fps, 1-1440')
        return bad(f"fps={fps}/{fb} range {sc.get('frame_start')}-{sc.get('frame_end')}")
    guard('B05', b05)

    def b08():
        site = set(S.coll('SITE'))
        errs = []
        terr = [n for n in site if (S.ob(n) or {}).get('type') == 'MESH' and (S.ob(n) or {}).get('bbox_world')
                and (S.ob(n)['bbox_world'][1][0] - S.ob(n)['bbox_world'][0][0]) >= 300
                and (S.ob(n)['bbox_world'][1][1] - S.ob(n)['bbox_world'][0][1]) >= 200]
        if not terr:
            errs.append('no SITE terrain mesh spanning >=300x200 m')
        RY = m.X.get('rays', {})

        def water(r):
            if not r or not r.get('hit') or r.get('obj') not in site:
                return False
            return bool(WATER_RE.search(r['obj'] or '') or any(WATER_RE.search(x) for x in r.get('mats', [])))
        for k in ('river_c', 'river_w', 'river_e', 'river_n', 'river_s'):
            if not water(RY.get(k)):
                errs.append(f'{k}: first hit {RY.get(k, {}).get("obj")} not SITE water')
        for k in ('creek', 'creek_s'):
            cr = RY.get(k)
            if not water(cr) or (cr.get('z') is None or cr['z'] >= 5.0):
                errs.append(f'{k}: hit {cr and cr.get("obj")} z={cr and cr.get("z")}')
        hl = RY.get('hill')
        if not hl or not hl.get('hit') or hl.get('obj') not in site or hl.get('z') is None or hl['z'] < 3.2 + 3.0:
            errs.append(f'hill over T11 ch60: hit {hl and hl.get("obj")} z={hl and hl.get("z")}')
        return fails(errs) or ok('terrain, East River, creek and hill found by ray tests')
    guard('B08', b08)

    # ---------- zone placement / size
    def m01():
        errs = []
        for d in TURNOUTS:
            t = m.turnout(d)
            if not t:
                errs.append(f'{d} axes missing'); continue
            g = U[d]['geom']
            for e in ('toe', 'main_end', 'div_end'):
                dd = d2(t[e], g[e])
                if dd > 0.10:
                    errs.append(f'{d}.{e} {dd:.3f} m')
        chk_track_ends(m, ['T01', 'T02'], 0.10, None, errs)
        for p in ('P01', 'P02'):
            o = obbx(m, f'{p}_DECK')
            if not o:
                errs.append(f'{p}_DECK missing'); continue
            g, kp = U[p]['geom'], U[p]['params']
            dd = d2(o['c'], g['center_xy'])
            if dd > 0.30: errs.append(f'{p} centre {dd:.2f}')
            if not close(o['L'], kp['length']): errs.append(f"{p} L {o['L']:.2f}")
            if not close(o['W'], kp['width']): errs.append(f"{p} W {o['W']:.2f}")
            if abs(o['zmax'] - g['top_z']) > 0.05: errs.append(f"{p} top z {o['zmax']:.3f}")
        o = obbx(m, 'S01_BODY')
        if not o:
            errs.append('S01_BODY missing')
        else:
            dd = d2(o['c'], U['S01']['geom']['footprint_center_xy'])
            if dd > 0.50: errs.append(f'S01 centre {dd:.2f}')
            if not close(o['L'], 48.0): errs.append(f"S01 L {o['L']:.2f}")
            if not close(o['W'], 16.0): errs.append(f"S01 D {o['W']:.2f}")
        chk_signal_pos(m, ['X01', 'X02'], errs)
        return fails(errs) or ok('zone A placement and sizes within tolerance')
    guard('M01', m01)

    def zone_tracks(tids, xs):
        def f():
            errs = []
            chk_track_ends(m, tids, 0.15, 0.05, errs)
            chk_signal_pos(m, xs, errs)
            return fails(errs) or ok(f'{"/".join(tids + xs)} within tolerance')
        return f
    guard('M02', zone_tracks(['T03', 'T04'], ['X03']))
    guard('M04', zone_tracks(['T08', 'T09'], ['X04']))

    def m03():
        errs = []
        chk_track_ends(m, ['T05', 'T06', 'T07'], 0.15, 0.05, errs)
        o = obbx(m, 'B01_DECK')
        if not o:
            errs.append('B01_DECK missing')
        else:
            dd = d2(o['c'], U['B01']['geom']['center_xy'])
            if dd > 0.30: errs.append(f'B01 mid {dd:.2f}')
            if not close(o['L'], 40.0): errs.append(f"B01 L {o['L']:.2f}")
            if not close(o['W'], 6.0): errs.append(f"B01 W {o['W']:.2f}")
        bb = S.bbox(m.part_objs('B01', 'DIAG'))
        if not bb:
            errs.append('B01_DIAG missing')
        else:
            # sheet B01: TRUSS HT 6.00 from top of deck to the top-chord line; members with a section or diagonals that stop
            # under a separate top chord shift the DIAG top by a few decimetres -> +-0.30 m
            dk = obbx(m, 'B01_DECK')
            th = bb[1][2] - (dk['zmax'] if dk else bb[0][2])
            if abs(th - 6.0) > 0.30: errs.append(f'B01 truss height (deck top to DIAG top) {th:.2f}')
        return fails(errs) or ok('zone C within tolerance')
    guard('M03', m03)

    def m05():
        errs = []
        chk_track_ends(m, ['T10', 'T11'], 0.15, 0.05, errs)
        for g in PORTALS:
            pm = m.portal_meas(g)
            if not pm or pm.get('error'):
                errs.append(f'{g}: portal not measurable ({pm.get("error") if pm else "missing"})'); continue
            kp = U[g]['params']
            dd = d2(pm['center'], U[g]['geom']['center_xy'])
            if dd > 0.30: errs.append(f'{g} centre {dd:.2f}')
            for f in ('open_w', 'open_h', 'face_w', 'face_h'):
                okk = pm.get(f) is not None and close(pm[f], kp[f])
                if f == 'face_h' and not okk and pm.get(f) is not None:   # sheet draws a 0.6 m coping above HEADWALL H
                    okk = kp[f] * 0.97 <= pm[f] <= kp[f] + 0.7
                if f == 'open_w' and not okk:   # sheet dimension may be read as max width or width at rail level
                    okk = pm.get('open_w_base') is not None and close(pm['open_w_base'], kp[f])
                if f == 'open_w' and not okk and kp.get('shape') == 'horseshoe' and pm.get(f) is not None:
                    # the G02 sheet's to-scale outline is 1.12 x OPENING W at its widest (5.70 at rail, 6.72 max), so a
                    # build that copies the drawn outline is accepted as well
                    okk = close(pm[f], kp[f] * 1.12)
                if not okk:
                    errs.append(f"{g}.{f}={None if pm.get(f) is None else round(pm[f], 2)} exp {kp[f]}")
        return fails(errs) or ok('zone E within tolerance')
    guard('M05', m05)

    def m06():
        errs = []
        o = obbx(m, 'B02_DECK')
        if not o: errs.append('B02_DECK missing')
        else:
            if not close(o['L'], 48.0): errs.append(f"B02 L {o['L']:.2f}")
            if not close(o['W'], 6.5): errs.append(f"B02 W {o['W']:.2f}")
        o = obbx(m, 'P03_DECK')
        if not o: errs.append('P03_DECK missing')
        else:
            if not close(o['L'], 60.0): errs.append(f"P03 L {o['L']:.2f}")
            if not close(o['W'], 5.0): errs.append(f"P03 W {o['W']:.2f}")
            pl = m.track('T12')
            rz = nearest_on(pl, o['c'])[1] if pl else 4.4
            if abs(o['zmax'] - rz - 0.55) > 0.05: errs.append(f"P03 height {o['zmax'] - rz:.3f}")
        o = obbx(m, 'S02_BODY')
        if not o: errs.append('S02_BODY missing')
        else:
            if not close(o['L'], 22.0): errs.append(f"S02 L {o['L']:.2f}")
            if not close(o['W'], 10.0): errs.append(f"S02 D {o['W']:.2f}")
            if abs((o['zmax'] - o['zmin']) - 4.6) > 0.20: errs.append(f"S02 eave {o['zmax'] - o['zmin']:.2f}")
        mp = m.parts('X05', 'MAST')
        bb = S.coll_bbox('X05')
        if not mp or not bb: errs.append('X05 missing')
        else:
            hh = bb[1][2] - mp[0]['foot'][2]
            if abs(hh - 4.5) > 0.20: errs.append(f'X05 height {hh:.2f}')
        return fails(errs) or ok('zone F part sizes within tolerance')
    guard('M06', m06)

    def m07():
        errs = []
        for r in TRAINS:
            kv = U[r]['params']['vehicles']
            vs = m.vehicles(r)
            if len(vs) != len(kv):
                errs.append(f'{r} {len(vs)} vehicles (exp {len(kv)})')
            for v in kv:
                if v['id'] not in vs:
                    continue
                L = m.veh_len(v['id'])
                if L is None or not close(L, v['length']):
                    errs.append(f"{v['id']} len {L}")
                okc, c = m.veh_colour_ok(v['id'], v['color'])
                if not okc:
                    errs.append(f"{v['id']} colour {None if not c else [round(x, 3) for x in c]} (sRGB) exp {v['color']}")
        return fails(errs) or ok('consists: counts, lengths, colours correct')
    guard('M07', m07)

    def m11():
        errs = []
        for t in TRACKS:
            pl = m.track(t)
            if not pl:
                errs.append(f'{t} AXIS missing'); continue
            kp = U[t]['params']
            L = plan_len(pl)
            for s, z in ((0.0, kp['z_start']), (L / 2, (kp['z_start'] + kp['z_end']) / 2), (L, kp['z_end'])):
                p, _ = point_at(pl, s)
                if abs(p[2] - z) > 0.05:
                    errs.append(f'{t} z@{s:.0f}={p[2]:.3f} exp {z:.3f}')
        return fails(errs) or ok('all profiles within 0.05 m')
    guard('M11', m11)

    # ---------- discrete zone gates
    def zone_disc(spec):
        def f():
            errs = []
            for uid, fields in spec:
                disc_compare(m, uid, fields, errs)
            return errs
        return f

    def g01():
        errs = zone_disc([(d, ['hand', 'frog', 'machine_side']) for d in TURNOUTS] +
                         [('P01', ['canopy', 'canopy_columns', 'benches']), ('P02', ['canopy', 'canopy_columns', 'benches']),
                          ('S01', ['floors', 'bays', 'openings', 'roof', 'clock_tower']),
                          ('X01', ['aspects', 'colors', 'ladder']), ('X02', ['aspects', 'colors', 'ladder']),
                          ('T01', TRACK_F), ('T02', TRACK_F)])()
        for d in TURNOUTS:
            a = m.turnout_disc(d).get('angle_deg')
            if a is None or abs(a - U[d]['params']['angle_deg']) > 0.5:
                errs.append(f'{d} diverging angle {a}')
        return fails(errs) or ok('zone A discrete features all correct')
    guard('G01', g01)

    def g02():
        errs = zone_disc([('T03', TRACK_F), ('T04', TRACK_F), ('X03', ['aspects', 'colors', 'ladder'])])()
        for t in ('T03', 'T04'):
            pl = m.track(t)
            if not pl:
                errs.append(f'{t} AXIS missing'); continue
            L = plan_len(pl)
            hs = []
            s = 0.0
            while s <= L:
                _, tg = point_at(pl, s)
                hs.append(az_of(tg)); s += 2.0
            neg = sum(min(0.0, ((hs[i + 1] - hs[i] + 180) % 360) - 180) for i in range(len(hs) - 1))
            tot = sum(((hs[i + 1] - hs[i] + 180) % 360) - 180 for i in range(len(hs) - 1))
            if neg < -1.0 or tot < 85:
                errs.append(f'{t} turning: total {tot:.1f} deg, right-hand {neg:.1f} deg (arcs must turn left)')
        return fails(errs) or ok('zone B discrete features all correct')
    guard('G02', g02)

    def g03():
        errs = zone_disc([('T05', TRACK_F), ('T06', TRACK_F), ('T07', TRACK_F),
                          ('B01', ['type', 'spans', 'panels_per_span', 'piers', 'diag'])])()
        bb = S.bbox(m.part_objs('B01', 'DIAG'))
        rail = U['B01']['geom']['deck_top_z'] + 0.35
        if not bb or bb[1][2] < rail + 4.0:
            errs.append(f'B01 truss top {bb and round(bb[1][2], 2)} not >= rail+4 ({rail + 4:.2f}) - not a through truss')
        return fails(errs) or ok('zone C discrete features all correct')
    guard('G03', g03)

    guard('G04', lambda: fails(zone_disc([('T08', TRACK_F), ('T09', TRACK_F), ('X04', ['aspects', 'colors', 'ladder'])])())
          or ok('zone D discrete features all correct'))
    guard('G05', lambda: fails(zone_disc([('T10', TRACK_F), ('T11', TRACK_F), ('G01', ['shape', 'voussoirs', 'wing_walls']),
                                          ('G02', ['shape', 'voussoirs', 'wing_walls'])])())
          or ok('zone E discrete features all correct'))
    guard('G06', lambda: fails(zone_disc([('T12', TRACK_F), ('B02', ['type', 'spans', 'piers', 'arch']),
                                          ('P03', ['canopy', 'canopy_columns', 'benches']),
                                          ('S02', ['floors', 'bays', 'roof', 'clock_tower']),
                                          ('X05', ['aspects', 'colors', 'ladder'])])())
          or ok('zone F discrete features all correct'))

    def g07():
        errs = []
        for r in TRAINS:
            a = m.axles(r)
            if a != U[r]['params']['loco_axles']:
                errs.append(f'{r} V01 axles {a} exp {U[r]["params"]["loco_axles"]}')
        L = m.veh_len('R2_V02')
        if 'R2_V02' not in m.vehicles('R2') or L is None or not close(L, 7.0):
            errs.append(f'R2 tender (V02, 7.0 m) not found/len {L}')
        for r in TRAINS:
            kv = U[r]['params']['vehicles']
            locs = []
            for v in kv:
                mm = S.at(1, v['id']) or (S.ob(v['id']) or {}).get('matrix_world')
                locs.append(Scene.loc(mm) if mm else None)
            if None in locs:
                errs.append(f'{r}: vehicle missing at frame 1'); continue
            for i in range(len(kv) - 1):
                gap = math.dist(locs[i], locs[i + 1])
                exp = (kv[i]['length'] + kv[i + 1]['length']) / 2
                if abs(gap - exp) > 1.5:
                    errs.append(f"{kv[i]['id']}->{kv[i + 1]['id']} spacing {gap:.2f} exp {exp:.2f} (order broken)")
        return fails(errs) or ok('axles, tender and consist order correct')
    guard('G07', g07)

    # ---------- manifest consistency
    def m08():
        if not isinstance(man, list):
            return bad('manifest missing')
        errs, skipped = [], []
        FIELDS = {'track': TRACK_F, 'turnout': ['hand', 'frog', 'machine_side'],
                  'platform': ['canopy', 'canopy_columns', 'benches'], 'station_building': ['floors', 'bays', 'roof', 'clock_tower'],
                  'signal': ['aspects', 'colors', 'ladder'], 'tunnel_portal': ['shape', 'voussoirs', 'wing_walls'],
                  'bridge': ['type', 'spans', 'panels_per_span', 'piers'], 'train': ['n_vehicles', 'loco_axles']}
        for e in man:
            if not isinstance(e, dict) or not e.get('built') or e.get('id') not in U:
                continue
            uid = e['id']
            if not any((S.ob(n) or {}).get('type') in ('MESH', 'CURVE') for n in S.coll(uid)):
                errs.append(f'{uid} built=true but collection empty'); continue
            me = m.measure_unit(uid)
            pm = e.get('params') or {}
            for f in FIELDS[U[uid]['type']]:
                got = me.get(f)
                dec = pm.get(f)
                if got is None:
                    skipped.append(f'{uid}.{f}'); continue
                if isinstance(got, list):
                    dec = [str(x).upper() for x in dec] if isinstance(dec, list) else dec
                if isinstance(dec, str) and isinstance(got, str):
                    dec = dec.strip()
                if dec != got:
                    errs.append(f'{uid}.{f}: manifest {dec!r} vs measured {got!r}')
        if errs:
            return bad('; '.join(errs))
        return ok('manifest discrete fields agree with measurements' + (f' (unmeasurable, skipped: {skipped[:12]})' if skipped else ''))
    guard('M08', m08)

    # ---------- animation
    try:
        idx = SegIndex(m.all_axes())
    except Exception:
        idx = None
        STATE['segindex_err'] = traceback.format_exc()[-300:]
    veh_all = {r: [v['id'] for v in U[r]['params']['vehicles']] for r in TRAINS}

    def m09():
        if not S.data.get('anim'):
            return bad('no animation samples')
        if idx is None:
            return bad('centreline index unavailable: ' + STATE.get('segindex_err', ''))
        errs = []
        for f in range(1, 1441, 12):
            for r, vs in veh_all.items():
                for v in vs:
                    mm = S.at(f, v)
                    if not mm:
                        errs.append(f'{v}@{f} missing'); continue
                    p = Scene.loc(mm)
                    nb = idx.nearest(p)
                    if not nb or nb[0] > 0.30:
                        errs.append(f'{v}@{f} off track {nb and round(nb[0], 2)}'); continue
                    if abs(p[2] - nb[1]) > 0.10:
                        errs.append(f'{v}@{f} dz {p[2] - nb[1]:.2f}'); continue
                    xa = Scene.axis(mm, 0)
                    a = angdiff(az_of(xa), az_of(nb[2]), 180.0)
                    if a > 3.0:
                        errs.append(f'{v}@{f} yaw {a:.1f}')
                if len(errs) > 25:
                    break
        return fails(errs) or ok('all vehicles on track at 120 sampled frames')
    guard('M09', m09)

    def train_mid(r, f):
        pts = []
        for v in veh_all[r]:
            mm = S.at(f, v)
            if not mm:
                return None
            p = Scene.loc(mm); xa = Scene.axis(mm, 0)
            n = math.sqrt(sum(c * c for c in xa)) or 1.0
            xa = [c / n for c in xa]
            vi = m.X.get('veh', {}).get(v) or {}
            if vi.get('xmin') is not None:
                lo, hi = vi['xmin'] * n, vi['xmax'] * n   # local extents -> world (col0 carries the scale)
            else:
                L = next(x['length'] for x in U[r]['params']['vehicles'] if x['id'] == v)
                lo, hi = -L / 2, L / 2
            pts.append([p[k] + lo * xa[k] for k in range(3)]); pts.append([p[k] + hi * xa[k] for k in range(3)])
        best = max(((math.dist(a, b), a, b) for a in pts for b in pts), key=lambda x: x[0])
        return [(best[1][k] + best[2][k]) / 2 for k in range(3)]

    def dwell_errs(rows):
        errs = []
        for row in rows:
            r, pf = row['train'], row['platform']
            a = row['arr'] or 1
            d = row['dep'] or 1440
            ref = U[pf]['geom']['axis_point']
            fs = sorted(set([x for x in frames if a <= x <= d] + [a, d]))
            base = {v: Scene.loc(S.at(fs[0], v)) for v in veh_all[r] if S.at(fs[0], v)}
            if len(base) != len(veh_all[r]):
                errs.append(f'{r} not sampled at {fs[0]}'); continue
            mid = train_mid(r, fs[0])
            dd = d2(mid, ref) if mid else None
            if dd is None or dd > 2.0:
                errs.append(f'{r}@{fs[0]} mid {dd and round(dd, 2)} m from {pf}')
            moved = 0.0
            for f in fs:
                for v in veh_all[r]:
                    mm = S.at(f, v)
                    if not mm:
                        moved = 1e9; break
                    moved = max(moved, math.dist(Scene.loc(mm), base[v]))
            if moved > 0.05:
                errs.append(f'{r} {pf} {a}-{d} moved {min(moved, 999):.2f} m')
        return errs

    def m10():
        if not S.data.get('anim'):
            return bad('no animation samples')
        errs = dwell_errs([t for t in K['timetable'] if t['train'] == 'R1'])
        ref = U['P01']['geom']['axis_point']
        for f in (384, 1104):
            mid = train_mid('R1', f)
            if not mid or d2(mid, ref) <= 50:
                errs.append(f'R1@{f} mid {mid and round(d2(mid, ref), 1)} m from P01 (need >50)')
        return fails(errs) or ok('R1 dwells and runs as timetabled')
    guard('M10', m10)

    def g10():
        if not S.data.get('anim'):
            return bad('no animation samples')
        errs = dwell_errs([t for t in K['timetable'] if t['train'] in ('R2', 'R3')])
        for r, f in (('R3', 264), ('R2', 942)):
            mid = train_mid(r, f)
            if not mid:
                errs.append(f'{r}@{f} missing'); continue
            dmin = min(min(d2(mid, U[p]['geom']['axis_point']), d2(mid, U[p]['geom']['center_xy'])) for p in PLATFORMS)
            if dmin <= 30:
                errs.append(f'{r}@{f} within {dmin:.1f} m of a platform')
        return fails(errs) or ok('revised R2/R3 timetable honoured')
    guard('G10', g10)

    # ---------- change order
    def g08():
        errs = []
        pl = m.track('T12')
        if not pl:
            return bad('T12_AXIS missing')
        g = U['T12']['geom']
        dd = d2(pl[-1], g['end'])
        if dd > 0.15: errs.append(f'T12 end {dd:.3f} m off')
        ha = az_of(outward(pl, True))
        if angdiff(ha, -15.0) > 1.0: errs.append(f'T12 end heading {ha:.2f}')
        L = plan_len(pl)
        if abs(L - 254.72) > 0.5: errs.append(f'T12 length {L:.2f}')
        old = K['stale_before_co']['T12_end']
        for n in m.X.get('axes', {}):
            a = m.axis(n)
            if a and nearest_on(a, old)[0] < 5.0:
                errs.append(f'{n} passes within 5 m of old T12 end')
        for n, o in S.objects.items():
            if re.search(r'(?i)buffer|bumper|stop_?block|车挡', n) and o.get('bbox_world'):
                c = Scene.center(o['bbox_world'])
                if d2(c, old) < 5.0:
                    errs.append(f'{n} at old T12 end')
        return fails(errs) or ok('CO-01 alignment applied; no stale alignment')
    guard('G08', g08)

    def g09():
        errs = []
        st = K['stale_before_co']
        o = obbx(m, 'B02_DECK')
        if not o: errs.append('B02_DECK missing')
        else:
            dd = d2(o['c'], U['B02']['geom']['center_xy'])
            if dd > 0.50: errs.append(f'B02 mid {dd:.2f} m off' + (' (matches pre-CO position)' if d2(o['c'], st['B02']) < 2 else ''))
            if angdiff(o['az'], -15.0, 180.0) > 2.0: errs.append(f"B02 axis {o['az']:.1f}")
        for u, nm, tol in (('P03', 'P03_DECK', 0.30), ('S02', 'S02_BODY', 0.50)):
            o = obbx(m, nm)
            if not o:
                errs.append(f'{nm} missing'); continue
            key = 'footprint_center_xy' if u == 'S02' else 'center_xy'
            dd = d2(o['c'], U[u]['geom'][key])
            if dd > tol: errs.append(f'{u} {dd:.2f} m off' + (' (matches pre-CO position)' if u == 'P03' and d2(o['c'], st['P03']) < 2 else ''))
            if angdiff(o['az'], U[u]['geom']['heading_deg'], 180.0) > 2.0: errs.append(f"{u} not parallel ({o['az']:.1f})")
        chk_signal_pos(m, ['X05'], errs)
        return fails(errs) or ok('B02/P03/S02/X05 relocated to revised T12')
    guard('G09', g09)

    # ---------- integration
    def g11():
        errs = []
        for i, j in enumerate(K['interfaces'], 1):
            a, b = m.endpoint(j['a']), m.endpoint(j['b'])
            if not a or not b:
                errs.append(f'J{i:02d} {j["a"]}/{j["b"]} missing'); continue
            dd = d2(a[0], b[0]); dz = abs(a[0][2] - b[0][2])
            da = abs(180.0 - angdiff(az_of(a[1]), az_of(b[1])))
            if dd > 0.05 or dz > 0.03 or da > 1.0:
                errs.append(f'J{i:02d} gap {dd:.3f} dz {dz:.3f} dtan {da:.2f}')
        return fails(errs) or ok('16 joints continuous')
    guard('G11', g11)

    def g12():
        errs = []
        for p in PLATFORMS:
            o = obbx(m, f'{p}_DECK')
            pl = m.track(U[p]['placement']['section'])
            if not o or not pl:
                errs.append(f'{p} deck/axis missing'); continue
            edge = nearest_on(pl, o['c'])[0] - o['W'] / 2
            if abs(edge - 1.75) > 0.05: errs.append(f'{p} edge offset {edge:.3f}')
        for b in BRIDGES:
            o = obbx(m, f'{b}_DECK')
            pl = m.track(U[b]['placement']['section'])
            if not o or not pl:
                errs.append(f'{b} deck/axis missing'); continue
            dz = nearest_on(pl, o['c'])[1] - o['zmax']
            if abs(dz - 0.35) > 0.05: errs.append(f'{b} deck {dz:.3f} below rail')
        pl11 = m.track('T11')
        for g in PORTALS:
            pm = m.portal_meas(g)
            if not pm or pm.get('error') or not pl11:
                errs.append(f'{g} not measurable'); continue
            nb = nearest_on(pl11, pm['center'])
            if nb[0] > 0.20: errs.append(f'{g} opening {nb[0]:.2f} m off CL')
            a = angdiff(pm['az'], az_of(nb[2]), 180.0)
            if a > 2.0: errs.append(f'{g} face normal {a:.1f} deg off tangent')
        for x in SIGNALS:
            mp = m.parts(x, 'MAST')
            pl = m.track(U[x]['placement']['section'])
            if not mp or not pl:
                errs.append(f'{x} mast/axis missing'); continue
            dd = nearest_on(pl, mp[0]['foot'])[0]
            if abs(dd - 2.5) > 0.15: errs.append(f'{x} offset {dd:.2f}')
        bad_m = []
        for t in TRACKS:
            td = m.track_disc(t)
            if not td['masts']:
                bad_m.append(f'{t}:none'); continue
            for o in td['mast_offsets']:
                if abs(o - 3.0) > 0.15:
                    bad_m.append(f'{t}:{o:.2f}')
        if bad_m: errs.append('mast offsets ' + ','.join(bad_m[:10]))
        return fails(errs) or ok('structure interfaces within tolerance')
    guard('G12', g12)

    STATE['extract_err'] = (m.X.get('err') or [])[:20]
    return R


def png_std(p):
    """grey std of a PNG; PIL if available, else None (size check only)."""
    try:
        from PIL import Image, ImageStat
        im = Image.open(p).convert('L')
        im.thumbnail((480, 480))
        return ImageStat.Stat(im).stddev[0]
    except Exception:
        return None


def postprocess(results, ctx):
    items = ctx['items']
    if STATE.get('scene_err'):
        return results   # every scene item already failed with the reason
    hits = STATE.get('coll_hits', 0)
    if hits < 16:
        results = gate_group(results, items, ['B02'],
                             lambda it: it.get('group') in ('contract', 'integration', 'change_order') or str(it.get('group', '')).startswith('zone_'),
                             f'gate: collection contract largely missing ({hits}/32 unit collections)')
    if STATE.get('axis_missing', 0) > 9:
        results = gate_group(results, items, ['B03'], lambda it: it.get('group') in ('integration', 'change_order', 'animation'),
                             f"gate: centreline contract >half missing ({STATE.get('axis_missing')}/18)")
    return results
