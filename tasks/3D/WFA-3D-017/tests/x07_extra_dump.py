# -*- coding: utf-8 -*-
"""CDC-C-X07 extra Blender export (2026-10-25). Executed by cxlib.BLEND_DUMP via cfg['extra_py'] inside the same
Blender process, after the revision properties were set to 0/0 (base). Globals available: bpy, sc, OB, R, cfg, guard,
Vector, math, re, os, json, OFF (film frame f = scene frame f + OFF).
Writes R['x07'] = {...}; every block is guarded, errors land in R['errors'] and the consuming check fails with detail.
All frame numbers in the output are FILM frames (base timeline)."""
import time
import numpy as np
from mathutils import Vector

X = {}
R["x07"] = X
EV = cfg.get("events", {}) or {}
FR = cfg.get("frames", {}) or {}
T0 = time.time()
BUDGET = float(cfg.get("budget_s", 900))
W, H = 1280, 720


def ev(k):
    v = EV.get(k)
    return int(v) if v is not None else None


def DG():
    return bpy.context.evaluated_depsgraph_get()


def hier(o):
    return ([o] + list(o.children_recursive)) if o else []


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


GEO = ('MESH', 'CURVE', 'SURFACE', 'FONT', 'META', 'CURVES', 'POINTCLOUD')


def mesh_world(o, dg):
    """world-space evaluated vertex positions (N,3) of a geometry object, or None."""
    if o is None or o.type not in GEO:
        return None
    e = o.evaluated_get(dg)
    try:
        me = e.to_mesh()
    except Exception:
        return None
    if me is None:
        return None
    try:
        n = len(me.vertices)
        a = np.empty(n * 3, np.float32)
        if n:
            me.vertices.foreach_get("co", a)
        M = np.array(e.matrix_world)
        return a.reshape(-1, 3).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
    finally:
        e.to_mesh_clear()


def hier_points(o, dg):
    ps = [p for p in (mesh_world(c, dg) for c in hier(o)) if p is not None and len(p)]
    return np.concatenate(ps) if ps else None


def bbox_world(objs, dg):
    pts = []
    for c in objs:
        if c.type in GEO:
            e = c.evaluated_get(dg)
            pts += [e.matrix_world @ Vector(cc) for cc in e.bound_box]
    if not pts:
        return None
    a = np.array([list(p) for p in pts])
    return a.min(0), a.max(0)


def cam_project(cam, pts, dg):
    """pts (N,3) world -> (x_px, y_px, depth) for a 1280x720 frame (y down)."""
    c = cam.evaluated_get(dg)
    fr = c.data.view_frame(scene=sc)
    z0 = -fr[0].z
    xs = [v.x / z0 for v in fr]
    ys = [v.y / z0 for v in fr]
    Minv = np.array(c.matrix_world.inverted())
    pc = np.asarray(pts, np.float64) @ Minv[:3, :3].T + Minv[:3, 3]
    d = -pc[:, 2]
    with np.errstate(divide='ignore', invalid='ignore'):
        u = (pc[:, 0] / d - min(xs)) / (max(xs) - min(xs))
        v = (pc[:, 1] / d - min(ys)) / (max(ys) - min(ys))
    return u * W, (1 - v) * H, d


def in_frustum(cam, pts, dg):
    if pts is None or not len(pts):
        return np.zeros(0, bool)
    x, y, d = cam_project(cam, pts, dg)
    c = cam.data
    return (d > c.clip_start) & (d < c.clip_end) & (x >= 0) & (x <= W) & (y >= 0) & (y <= H)


def cam_local(cam, p, dg):
    c = cam.evaluated_get(dg)
    return list(c.matrix_world.inverted() @ Vector(p))


# ---------------- light / emission state ----------------
def sock_val(s):
    if s is None:
        return None
    if not s.is_linked:
        return s.default_value
    fn = s.links[0].from_node
    if fn.type == 'VALUE':
        return fn.outputs[0].default_value
    if fn.type == 'RGB':
        return fn.outputs[0].default_value
    return None


def mat_emission(mat):
    tot, cols = 0.0, []
    if not mat or not mat.use_nodes or not mat.node_tree:
        return 0.0, None
    for n in mat.node_tree.nodes:
        if getattr(n, 'mute', False):
            continue
        if n.type == 'EMISSION':
            st, co = n.inputs.get('Strength'), n.inputs.get('Color')
        elif n.type == 'BSDF_PRINCIPLED':
            st, co = n.inputs.get('Emission Strength'), n.inputs.get('Emission Color')
        else:
            continue
        sv = sock_val(st)
        cv = sock_val(co)
        sv = 1.0 if sv is None else float(sv)
        cv = tuple(cv)[:3] if (cv is not None and hasattr(cv, '__len__')) else (1.0, 1.0, 1.0)
        e = sv * lum(cv)
        if e > 1e-9:
            tot += e
            cols.append((e, cv))
    col = None
    if cols:
        w = sum(c[0] for c in cols)
        col = [sum(c[0] * c[1][i] for c in cols) / w for i in range(3)]
    return tot, col


def source_objs(names):
    obs = []
    for n in names:
        obs += hier(OB.get(n))
    return obs


def light_state(obs):
    lt, em, lcol, ecol = 0.0, 0.0, None, None
    for o in obs:
        if o.hide_render:
            continue
        if o.type == 'LIGHT':
            e = float(o.data.energy) * lum(o.data.color)
            lt += e
            if e > 0:
                lcol = list(o.data.color)
        elif o.type in GEO:
            for s in o.material_slots:
                v, c = mat_emission(s.material)
                em += v
                if c:
                    ecol = c
    return {"light": lt, "emis": em, "lcol": lcol, "ecol": ecol}


LAMP = source_objs(["LAMP_HEAD"])
if not any(o.type == 'LIGHT' for o in LAMP):
    LAMP += [o for o in source_objs(["STREETLAMP"]) if o.type == 'LIGHT' and o not in LAMP]
BUS = source_objs(["BUS_LIGHTS"])
X["lamp_objects"] = [o.name for o in LAMP][:20]


# ---------------- simulation caches (B04) ----------------
def cache_dir_files(pc, owner):
    try:
        if pc.use_external:
            d = bpy.path.abspath(pc.filepath)
        else:
            bp = bpy.data.filepath
            d = os.path.join(os.path.dirname(bp), "blendcache_" + os.path.splitext(os.path.basename(bp))[0])
        return d, (len(os.listdir(d)) if os.path.isdir(d) else 0)
    except Exception:
        return None, 0


def pc_ok(pc, owner):
    if pc is None:
        return False, "no point cache"
    if not pc.is_baked:
        return False, "not baked"
    if pc.use_disk_cache or pc.use_external:
        d, n = cache_dir_files(pc, owner)
        if n == 0:
            return False, f"disk cache dir empty/missing: {d}"
    return True, "baked"


def has_sim(ng, seen=None):
    seen = seen or set()
    if ng is None or ng.name in seen:
        return False
    seen.add(ng.name)
    for n in ng.nodes:
        if n.bl_idname == 'GeometryNodeSimulationOutput':
            return True
        if getattr(n, 'node_tree', None) is not None and has_sim(n.node_tree, seen):
            return True
    return False


def caches():
    out = []
    for o in OB:
        for ps in getattr(o, 'particle_systems', []):
            st = ps.settings
            if st.type == 'HAIR' or st.physics_type == 'NO':
                continue
            ok, why = pc_ok(ps.point_cache, o)
            out.append({"owner": o.name, "kind": "particles:" + ps.name, "ok": ok, "why": why})
        for md in o.modifiers:
            try:
                if md.type in ('CLOTH', 'SOFT_BODY'):
                    ok, why = pc_ok(md.point_cache, o)
                    out.append({"owner": o.name, "kind": md.type, "ok": ok, "why": why})
                elif md.type == 'DYNAMIC_PAINT' and md.ui_type == 'CANVAS' and md.canvas_settings:
                    for s in md.canvas_settings.canvas_surfaces:
                        if s.surface_format == 'VERTEX':
                            ok, why = pc_ok(s.point_cache, o)
                        else:
                            d = bpy.path.abspath(s.image_output_path)
                            ok = os.path.isdir(d) and len(os.listdir(d)) > 0
                            why = "image sequence present" if ok else f"image sequence dir empty: {d}"
                        out.append({"owner": o.name, "kind": "dynamic_paint:" + s.name, "ok": ok, "why": why})
                elif md.type == 'FLUID' and md.fluid_type == 'DOMAIN':
                    d = bpy.path.abspath(md.domain_settings.cache_directory)
                    n = sum(len(fs) for _, _, fs in os.walk(d)) if os.path.isdir(d) else 0
                    out.append({"owner": o.name, "kind": "fluid", "ok": n > 0, "why": f"{n} files in {d}"})
                elif md.type == 'NODES' and has_sim(md.node_group):
                    tgt = getattr(md, 'bake_target', 'PACKED')
                    if tgt == 'DISK':
                        d = bpy.path.abspath(md.bake_directory)
                        n = sum(len(fs) for _, _, fs in os.walk(d)) if d and os.path.isdir(d) else 0
                        out.append({"owner": o.name, "kind": "gn_sim", "ok": n > 0, "why": f"{n} files in {d}"})
                    else:
                        out.append({"owner": o.name, "kind": "gn_sim", "ok": True, "why": "packed bake target (presence not verifiable)"})
            except Exception as e:
                out.append({"owner": o.name, "kind": md.type, "ok": False, "why": f"inspect error {e}"})
    rbw = sc.rigidbody_world
    if rbw and rbw.collection and len(rbw.collection.objects):
        ok, why = pc_ok(rbw.point_cache, None)
        out.append({"owner": "rigidbody_world", "kind": "rigid_body", "ok": ok, "why": why})
    X["caches"] = out


guard("x07_caches", caches)
NEED_STEP = any(not c["ok"] and (c["kind"].startswith("particles") or c["kind"] in ("CLOTH", "SOFT_BODY", "rigid_body")
                                 or c["kind"].startswith("dynamic_paint") or c["kind"] == "gn_sim") for c in X.get("caches", []))
X["sequential_stepping"] = NEED_STEP


# ---------------- static material / scene facts ----------------
def statics():
    road = OB.get("ROAD")
    info = []
    for o in hier(road):
        for s in getattr(o, 'material_slots', []):
            m = s.material
            if not m or not m.use_nodes:
                continue
            for n in m.node_tree.nodes:
                if n.type in ('BSDF_PRINCIPLED', 'BSDF_GLOSSY', 'BSDF_ANISOTROPIC') and 'Roughness' in n.inputs:
                    info.append({"mat": m.name, "node": n.type, "rough_linked": bool(n.inputs['Roughness'].is_linked)})
    X["road_rough"] = info
    # 2D-overlay red flags: compositor image/movie nodes, rain-named image textures on cards
    flags = []
    nt = sc.node_tree if sc.use_nodes else None
    if nt:
        flags += [f"compositor {n.type} {getattr(getattr(n, 'image', None), 'name', '')}" for n in nt.nodes if n.type in ('IMAGE', 'MOVIECLIP') and not n.mute]
    for o in OB:
        if o.type != 'MESH' or o.name in ("PUDDLE", "ROAD"):
            continue
        if len(o.data.vertices) > 8:
            continue
        for s in o.material_slots:
            m = s.material
            if m and m.use_nodes:
                for n in m.node_tree.nodes:
                    im = getattr(n, 'image', None)
                    if n.type == 'TEX_IMAGE' and im and re.search(r"rain|drop|streak", (im.name + " " + (im.filepath or "")), re.I):
                        flags.append(f"card {o.name} image {im.name}")
    X["overlay_flags"] = flags[:10]
    com = OB.get("COMMUTER")
    if com:
        dg = DG()
        pts = hier_points(com, dg)
        X["commuter_geo"] = {"n_verts": int(len(pts)) if pts is not None else 0,
                             "dims": (list((pts.max(0) - pts.min(0)).round(3)) if pts is not None and len(pts) else None)}


guard("x07_statics", statics)


# ---------------- per-frame task schedule ----------------
tasks = {}


def at(f, fn):
    if f is None:
        return
    tasks.setdefault(int(f), []).append(fn)


fs_, lo_, lon_ = ev("lamp_flicker_start"), ev("lamp_off"), ev("lamp_on")
uo_, fc_, hl_ = ev("umbrella_open"), ev("foot_contact"), ev("headlights_on_face")
ls_, le_ = ev("line_start"), ev("line_end")
S = {k: FR.get(k) for k in ("S1", "S2", "S3", "S4", "S5")}
X["lamp"] = {}
X["bus"] = {}

# lamp state frames: pre-flicker reference, the flicker span, the off span (every 3rd frame), around lamp_on
lamp_frames = set()
if fs_ is not None and lo_ is not None and lon_ is not None:
    lamp_frames |= set(range(max(0, fs_ - 48), fs_ + 1, 4))
    lamp_frames |= set(range(fs_, lo_ + 7))
    lamp_frames |= set(range(lo_ + 7, lon_ - 6, 3))
    lamp_frames |= set(range(lon_ - 6, min(lon_ + 14, 720)))
    if S["S2"]:
        lamp_frames |= set(range(S["S2"][0], min(S["S2"][1], 299) + 1))


def rec_lamp(f):
    def fn():
        X["lamp"][f] = light_state(LAMP)
    return fn


for f in sorted(lamp_frames):
    at(f, rec_lamp(f))

if hl_ is not None:
    for f in range(hl_ - 12, hl_ + 13, 2):
        def fnb(f=f):
            st = light_state(BUS)
            bl = OB.get("BUS_LIGHTS"); cam = OB.get("CAM_S4"); dg = DG()
            if bl and cam:
                st["cam_local"] = cam_local(cam, bl.evaluated_get(dg).matrix_world.translation, dg)
                lights = [o for o in BUS if o.type == 'LIGHT']
                if lights:
                    st["light_cam_local"] = [cam_local(cam, o.evaluated_get(dg).matrix_world.translation, dg) for o in lights[:4]]
            X["bus"][f] = st
        at(f, fnb)


# ---------------- projections for picture ROIs ----------------
X["proj"] = {}


def surface_z(o, dg):
    p = hier_points(o, dg)
    if p is None or not len(p):
        return None
    return float(np.percentile(p[:, 2], 90))


def rect(cam, obj, dg, top_frac=None):
    """2D pixel rect (1280x720, unclipped) of the evaluated vertices of obj's hierarchy that lie in front of the camera."""
    pts = hier_points(obj, dg)
    if pts is None or not len(pts):
        return None
    if top_frac:
        z1, z0 = pts[:, 2].max(), pts[:, 2].min()
        pts = pts[pts[:, 2] >= z1 - top_frac * (z1 - z0)]
    if len(pts) > 20000:
        pts = pts[np.random.default_rng(0).choice(len(pts), 20000, replace=False)]
    x, y, d = cam_project(cam, pts, dg)
    m = d > cam.data.clip_start
    if not m.any():
        return None
    return [float(x[m].min()), float(y[m].min()), float(x[m].max()), float(y[m].max())]


def proj_task(key, camname, mirror_of=None):
    def fn():
        dg = DG(); cam = OB.get(camname); out = {}
        if cam is None:
            X["proj"][key] = {"error": f"{camname} missing"}; return
        lamp = OB.get("LAMP_HEAD")
        if mirror_of and lamp:
            bb = bbox_world(hier(lamp), dg)
            if bb is None:
                t = np.array(lamp.evaluated_get(dg).matrix_world.translation)
                bb = (t - 0.1, t + 0.1)
            if bb is not None:
                c = (bb[0] + bb[1]) / 2
                surf = OB.get(mirror_of)
                if mirror_of == "ROAD":
                    rb = bbox_world(hier(surf), dg) if surf else None
                    zs = float(rb[1][2]) if rb is not None else 0.0
                else:
                    zs = surface_z(surf, dg) if surf else None
                if zs is not None:
                    m = c.copy(); m[2] = 2 * zs - c[2]
                    corners = np.array([[x, y, 2 * zs - z] for x in (bb[0][0], bb[1][0]) for y in (bb[0][1], bb[1][1]) for z in (bb[0][2], bb[1][2])])
                    x, y, d = cam_project(cam, np.vstack([m, c, corners]), dg)
                    out.update(mirror=[float(x[0]), float(y[0]), float(d[0])], lamp=[float(x[1]), float(y[1]), float(d[1])],
                               lamp_radius_px=float(max(np.ptp(x[2:]), np.ptp(y[2:])) / 2), surface_z=zs)
                    # projected gravity direction at the mirror point
                    g = cam_project(cam, np.array([c, c - np.array([0, 0, 1.0])]), dg)
                    out["gravity_dir"] = [float(g[0][1] - g[0][0]), float(g[1][1] - g[1][0])]
        for nm in ("COMMUTER", "PUDDLE"):
            o = OB.get(nm)
            if o:
                out[nm] = rect(cam, o, dg)
        o = OB.get("COMMUTER")
        if o:
            out["COMMUTER_head"] = rect(cam, o, dg, top_frac=0.13)
        X["proj"][key] = out
    return fn


def pf(v):
    return None if v is None else int(v)


a1 = min(24, fs_ - 2) if fs_ is not None else 24
b5 = min(lon_ + 12, S["S5"][1]) if (lon_ is not None and S["S5"]) else None
a7 = min(fs_ - 6, S["S1"][1]) if fs_ is not None and S["S1"] else None
b7 = min(lon_ + 12, S["S5"][1] - 4) if (lon_ is not None and S["S5"]) else None
a6 = min(72, fs_ - 2) if fs_ is not None else 72
X["proj_frames"] = {"g01_s1": a1, "g01_s5": b5, "m07_s1": a7, "m07_s5": b7, "g06_s1": a6, "g06_s3": 380}
at(a1, proj_task("g01_s1", "CAM_S1", "ROAD"))
at(b5, proj_task("g01_s5", "CAM_S5", "ROAD"))
if S["S2"]:
    at(S["S2"][0] + 2, proj_task("g02_s2", "CAM_S2", "PUDDLE"))
at(a7, proj_task("m07_s1", "CAM_S1"))
at(b7, proj_task("m07_s5", "CAM_S5"))
at(a6, proj_task("g06_s1", "CAM_S1"))
at(380, proj_task("g06_s3", "CAM_S3"))
if hl_ is not None:
    at(hl_, proj_task("g06_s4", "CAM_S4"))
if fc_ is not None:
    at(fc_, proj_task("g05_s3", "CAM_S3", "PUDDLE"))


# ---------------- rain ----------------
def rain_points(dg):
    o = OB.get("RAIN")
    if o is None:
        return None, None, "RAIN missing"
    e = o.evaluated_get(dg)
    P, V = [], []
    cf = sc.frame_current
    for ps in e.particle_systems:
        if ps.settings.type == 'HAIR':
            continue
        n = len(ps.particles)
        if not n:
            continue
        loc = np.empty(n * 3, np.float32); ps.particles.foreach_get('location', loc)
        vel = np.empty(n * 3, np.float32); ps.particles.foreach_get('velocity', vel)
        bt = np.empty(n, np.float32); ps.particles.foreach_get('birth_time', bt)
        dt = np.empty(n, np.float32); ps.particles.foreach_get('die_time', dt)
        alive = (bt <= cf) & (dt > cf)
        P.append(loc.reshape(-1, 3)[alive]); V.append(vel.reshape(-1, 3)[alive])
    if P:
        return np.concatenate(P).astype(np.float64), np.concatenate(V).astype(np.float64), "particles"
    pts = []
    for inst in dg.object_instances:
        if inst.is_instance and inst.parent is not None and inst.parent.original.name == "RAIN":
            pts.append(list(inst.matrix_world.translation))
    if pts:
        return np.array(pts), None, "instances"
    pts = mesh_world(o, dg)
    if pts is not None and len(pts):
        return pts, None, "mesh_vertices"
    return None, None, "no drops found (no particles, instances or vertices)"


def loose_parts(o, dg):
    e = o.evaluated_get(dg)
    me = e.to_mesh()
    try:
        n = len(me.vertices)
        if n == 0 or n > 400000:
            return None
        ed = np.empty(len(me.edges) * 2, np.int32)
        if len(me.edges):
            me.edges.foreach_get("vertices", ed)
        par = list(range(n))

        def find(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for a, b in ed.reshape(-1, 2):
            ra, rb = find(int(a)), find(int(b))
            if ra != rb:
                par[ra] = rb
        return len(set(find(i) for i in range(n)))
    finally:
        e.to_mesh_clear()


X["rain"] = {}


def rain_task(f, camname, keep_pts=False):
    def fn():
        dg = DG(); cam = OB.get(camname)
        P, V, kind = rain_points(dg)
        d = {"kind": kind}
        if P is None or cam is None:
            X["rain"][f] = d; return
        m = in_frustum(cam, P, dg)
        d["n_total"] = int(len(P)); d["n_frustum"] = int(m.sum())
        if kind == "mesh_vertices":
            lp = loose_parts(OB["RAIN"], dg)
            if lp:
                d["loose_parts"] = lp
                d["drops_frustum_est"] = int(round(m.sum() * lp / max(len(P), 1)))
        else:
            d["drops_frustum_est"] = int(m.sum())
        if V is not None and m.any():
            d["fall_speed_med"] = float(np.median(-V[m][:, 2])); d["speed_med"] = float(np.median(np.linalg.norm(V[m], axis=1)))
        if keep_pts:
            d["_pts"] = P[m][:20000]
        X["rain"][f] = d
    return fn


at(72, rain_task(72, "CAM_S1", keep_pts=True))
at(73, rain_task(73, "CAM_S1", keep_pts=True))
at(660, rain_task(660, "CAM_S5"))


def rain_speed_match():
    r0, r1 = X["rain"].get(72, {}), X["rain"].get(73, {})
    for d in (r0, r1):
        d.pop("_pts_keep", None)
    p0, p1 = r0.pop("_pts", None), r1.pop("_pts", None)
    if "fall_speed_med" in r0 or p0 is None or p1 is None or not len(p0) or not len(p1):
        return
    from mathutils.kdtree import KDTree
    kd = KDTree(len(p1))
    for i, p in enumerate(p1):
        kd.insert((p[0], p[1], 0.0), i)
    kd.balance()
    dz = []
    for p in p0[:5000]:
        best = None
        for (co, i, dist) in kd.find_n((p[0], p[1], 0.0), 4):
            z = p1[i][2] - p[2]
            if dist < 0.05 and z < 0 and (best is None or dist < best[0]):
                best = (dist, z)
        if best:
            dz.append(-best[1])
    if len(dz) >= 20:
        r0["fall_speed_med"] = float(np.median(dz) * sc.render.fps / sc.render.fps_base)
        r0["fall_speed_method"] = "nearest-neighbour match 72->73"


# ---------------- puddle ripple field (G04) ----------------
X["puddle"] = {}
PUD_IDX = {}


def pud_task(f):
    def fn():
        o = OB.get("PUDDLE")
        if not o:
            return
        p = mesh_world(o, DG())
        if p is None or not len(p):
            return
        if "idx" not in PUD_IDX:
            rng = np.random.default_rng(0)
            PUD_IDX["n"] = len(p)
            PUD_IDX["idx"] = np.sort(rng.choice(len(p), min(len(p), 3000), replace=False))
        if len(p) != PUD_IDX["n"]:
            X["puddle"].setdefault("topology_changes", 0)
            X["puddle"]["topology_changes"] += 1
            return
        X["puddle"].setdefault("_z", {})[f] = p[PUD_IDX["idx"], 2]
    return fn


for f in range(150, 281, 2):
    at(f, pud_task(f))


def pud_summary():
    zz = X["puddle"].pop("_z", {})
    if len(zz) < 10:
        X["puddle"]["n_samples"] = len(zz); return
    fr = sorted(zz)
    Z = np.array([zz[f] for f in fr])
    D = Z - Z.mean(0)
    X["puddle"]["n_samples"] = len(fr)
    X["puddle"]["max_abs_dev_m"] = float(np.abs(D).max())
    X["puddle"]["rms_dev_m"] = float(np.sqrt((D ** 2).mean()))
    step = fr[1] - fr[0]
    cors = []
    for lag_f in range(12, 49, step):
        k = lag_f // step
        if k >= len(fr) - 3:
            break
        a, b = D[:-k].ravel(), D[k:].ravel()
        if a.std() > 1e-12 and b.std() > 1e-12:
            cors.append((lag_f, float(np.corrcoef(a, b)[0, 1])))
    X["puddle"]["lag_corr"] = cors
    X["puddle"]["max_lag_corr"] = max((c for _, c in cors), default=None)


# ---------------- feet / splash (G05) ----------------
FOOT_RE = re.compile(r"foot|toe|shoe|boot|heel|ball", re.I)
X["feet"] = {}


def foot_points(dg):
    """world positions of vertices belonging to feet/shoes (by vertex group weight or object name)."""
    rig = OB.get("COMMUTER_RIG")
    objs = set(hier(OB.get("COMMUTER")))
    if rig:
        objs |= {o for o in OB if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)}
        objs |= {o for o in hier(rig) if o.type == 'MESH'}
    out = []
    for o in sorted(objs, key=lambda o: o.name):      # stable order -> vertex indices comparable across frames
        if o.type != 'MESH':
            continue
        if FOOT_RE.search(o.name) or (o.parent_type == 'BONE' and FOOT_RE.search(o.parent_bone or "")):
            p = mesh_world(o, dg)
            if p is not None:
                out.append(p)
            continue
        gi = {g.index for g in o.vertex_groups if FOOT_RE.search(g.name)}
        if not gi:
            continue
        e = o.evaluated_get(dg); me = e.to_mesh()
        try:
            idx = [v.index for v in me.vertices if any(g.group in gi and g.weight >= 0.3 for g in v.groups)]
            if idx:
                a = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", a)
                M = np.array(e.matrix_world)
                out.append(a.reshape(-1, 3)[idx].astype(np.float64) @ M[:3, :3].T + M[:3, 3])
        finally:
            e.to_mesh_clear()
    return np.concatenate(out) if out else None


EXCL_SPLASH = None


def splash_points(dg):
    global EXCL_SPLASH
    if EXCL_SPLASH is None:
        ex = set()
        for n in ("RAIN", "COMMUTER", "COMMUTER_RIG", "UMBRELLA", "PHONE", "PUDDLE", "ROAD", "KERB"):
            ex |= {o.name for o in hier(OB.get(n))}
        EXCL_SPLASH = ex
    pts = []
    cf = sc.frame_current
    for o in OB:
        if o.name in EXCL_SPLASH:
            continue
        e = o.evaluated_get(dg)
        for ps in getattr(e, 'particle_systems', []):
            if ps.settings.type == 'HAIR' or not len(ps.particles):
                continue
            n = len(ps.particles)
            loc = np.empty(n * 3, np.float32); ps.particles.foreach_get('location', loc)
            bt = np.empty(n, np.float32); ps.particles.foreach_get('birth_time', bt)
            dt = np.empty(n, np.float32); ps.particles.foreach_get('die_time', dt)
            pts.append(loc.reshape(-1, 3)[(bt <= cf) & (dt > cf)].astype(np.float64))
        if o.type == 'MESH' and re.search(r"splash|spray|droplet|fluid|water", o.name, re.I):
            p = mesh_world(o, dg)
            if p is not None:
                pts.append(p)
    for inst in dg.object_instances:
        if inst.is_instance and inst.parent is not None and inst.parent.original.name not in EXCL_SPLASH:
            pts.append(np.array([list(inst.matrix_world.translation)]))
    return np.concatenate(pts) if pts else np.zeros((0, 3))


def foot_task(f):
    def fn():
        dg = DG()
        fp = foot_points(dg)
        pud = OB.get("PUDDLE")
        d = {}
        if fp is not None and len(fp):
            d["_fp"] = fp
        if pud:
            pp = mesh_world(pud, dg)
            if pp is not None and len(pp):
                d["_pud"] = pp
        d["_spl"] = splash_points(dg)
        X["feet"][f] = d
    return fn


if fc_ is not None:
    for f in range(fc_ - 8, fc_ + 5):
        at(f, foot_task(f))


def feet_summary():
    F = X["feet"]
    if fc_ is None or not F:
        return
    out = {}
    ref = F.get(fc_ - 8, {})
    pud = ref.get("_pud")
    if pud is None:
        out["error"] = "PUDDLE has no geometry"; X["feet_summary"] = out; return
    top = float(np.percentile(pud[:, 2], 90))
    lo, hi = pud[:, :2].min(0), pud[:, :2].max(0)
    out["puddle_top"] = top; out["puddle_xy"] = [lo.tolist(), hi.tolist()]
    best = None
    for f in range(fc_ - 2, fc_ + 3):
        fp = F.get(f, {}).get("_fp")
        if fp is None:
            continue
        inside = (fp[:, 0] >= lo[0] - 0.03) & (fp[:, 0] <= hi[0] + 0.03) & (fp[:, 1] >= lo[1] - 0.03) & (fp[:, 1] <= hi[1] + 0.03)
        if inside.any():
            i = np.argmin(np.where(inside, fp[:, 2], np.inf))
            gap = float(fp[i, 2] - top)
            if best is None or gap < best[1]:
                best = (f, gap, fp[i].copy())
    if best is None:
        out["contact"] = None
    else:
        f, gap, p = best
        out["contact"] = {"frame": f, "gap_m": round(gap, 4), "xy": [float(p[0]), float(p[1])]}
        # the stepping foot: vertices near the contact vertex at the contact frame, followed back 6 frames
        cur = F.get(f, {}).get("_fp"); pre = F.get(fc_ - 6, {}).get("_fp")
        if pre is not None and cur is not None and len(pre) == len(cur):
            sel = (np.linalg.norm(cur[:, :2] - p[:2], axis=1) <= 0.08) & (cur[:, 2] <= p[2] + 0.03)
            out["pre6_min_height_m"] = round(float(pre[sel, 2].min() - top), 4) if sel.any() else None
        elif pre is not None:
            out["pre6_note"] = "foot vertex count changed between frames"
        def nspl(fr):
            s = F.get(fr, {}).get("_spl")
            if s is None or not len(s):
                return 0
            m = (np.linalg.norm(s[:, :2] - p[:2], axis=1) <= 0.30) & (s[:, 2] >= top + 0.02) & (s[:, 2] <= top + 1.0)
            return int(m.sum())
        out["splash_before"] = nspl(fc_ - 2)
        out["splash_after_max"] = max(nspl(fr) for fr in range(fc_, fc_ + 5))
        def pvar(fr):
            q = F.get(fr, {}).get("_pud")
            if q is None:
                return None
            m = np.linalg.norm(q[:, :2] - p[:2], axis=1) <= 0.30
            return float(q[m, 2].var()) if m.sum() >= 3 else None
        out["puddle_var_before"] = pvar(fc_ - 2)
        out["puddle_var_after"] = max([v for v in (pvar(fr) for fr in range(fc_ + 1, fc_ + 5)) if v is not None], default=None)
    X["feet_summary"] = out


# ---------------- props / hands / fingers (M13, M14) ----------------
HAND_RE = re.compile(r"hand|wrist|palm", re.I)
X["props"] = {}


def hand_bones(rig):
    names = set()
    for b in rig.data.bones:
        if HAND_RE.search(b.name):
            names.add(b.name); names |= {c.name for c in b.children_recursive}
    for h in (R.get("rigs", {}).get("COMMUTER_RIG", {}) or {}).get("hands", []):
        b = rig.data.bones.get(h["hand"])
        if b:
            names.add(b.name); names |= {c.name for c in b.children_recursive}
    return sorted(names)


def head_bone(rig):
    c = [b.name for b in rig.data.bones if re.search(r"head", b.name, re.I) and not re.search(r"fore|top|end", b.name, re.I)]
    return c[0] if c else None


RIG = OB.get("COMMUTER_RIG") if (OB.get("COMMUTER_RIG") and OB["COMMUTER_RIG"].type == 'ARMATURE') else None
HB = hand_bones(RIG) if RIG else []
HEAD = head_bone(RIG) if RIG else None
X["hand_bones"] = HB[:40]; X["head_bone"] = HEAD
FINGERS = []
for h in (R.get("rigs", {}).get("COMMUTER_RIG", {}) or {}).get("hands", []) if RIG else []:
    b = RIG.data.bones.get(h["hand"])
    if b:
        FINGERS.append((b.name, [c.name for c in b.children_recursive]))


def bone_pts(dg, names):
    e = RIG.evaluated_get(dg); M = e.matrix_world; out = []
    for n in names:
        pb = e.pose.bones.get(n)
        if pb:
            h, t = M @ pb.head, M @ pb.tail
            out += [list(h), list(t), list((h + t) / 2)]
    return np.array(out) if out else None


def prop_task(f, detail):
    def fn():
        dg = DG(); d = {}
        for nm in ("UMBRELLA", "PHONE"):
            o = OB.get(nm)
            if not o:
                continue
            e = o.evaluated_get(dg)
            d[nm + "_loc"] = list(e.matrix_world.translation)
            if detail:
                pts = hier_points(o, dg)
                if pts is not None and len(pts):
                    if nm == "UMBRELLA":
                        Minv = np.array(e.matrix_world.inverted())
                        loc = pts @ Minv[:3, :3].T + Minv[:3, 3]
                        dims = sorted((loc.max(0) - loc.min(0)).tolist())
                        sc_ = np.array(e.matrix_world.to_scale())
                        d["UMBRELLA_dims_local"] = dims
                        d["UMBRELLA_mid_dim_world"] = float(sorted(((loc.max(0) - loc.min(0)) * np.abs(sc_)).tolist())[1])
                    if RIG and HB:
                        bp = bone_pts(dg, HB)
                        if bp is not None:
                            dd = min(float(np.sqrt(((pts[i:i + 2000, None, :] - bp[None, :, :]) ** 2).sum(-1)).min())
                                     for i in range(0, len(pts), 2000))
                            d[nm + "_hand_dist"] = dd
                    if nm == "PHONE" and RIG and HEAD:
                        hp = bone_pts(dg, [HEAD])
                        if hp is not None:
                            d["PHONE_head_dist"] = float(np.linalg.norm(pts.mean(0) - hp[2]))
        if FINGERS and detail:
            e = RIG.evaluated_get(dg)
            d["_fingers"] = {n: list(e.pose.bones[n].matrix_basis.to_quaternion()) + list(e.pose.bones[n].matrix_basis.translation)
                             for _, bs in FINGERS for n in bs if n in e.pose.bones}
        X["props"][f] = d
    return fn


s3, s4 = S["S3"], S["S4"]
if s3 and s4:
    pf_ = set(range(s3[0], s4[1] + 1))
    det = set(range(s3[0], s4[1] + 1, 3))
    if uo_ is not None:
        det |= set(range(uo_ - 12, uo_ + 13, 2))
    if ls_ is not None and le_ is not None:
        det |= set(range(ls_, le_ + 1, 2))
    for f in sorted(pf_):
        at(f, prop_task(f, f in det))


def props_summary():
    P = X["props"]
    if not P:
        return
    out = {}
    fr = sorted(P)
    for nm in ("UMBRELLA", "PHONE"):
        jumps = []
        for a, b in zip(fr[:-1], fr[1:]):
            if b != a + 1 or (s4 and a < s4[0] <= b):
                continue
            pa, pb = P[a].get(nm + "_loc"), P[b].get(nm + "_loc")
            if pa and pb:
                jumps.append((float(np.linalg.norm(np.array(pb) - np.array(pa))), b))
        out[nm + "_max_jump"] = max(jumps) if jumps else None
    dims = {f: P[f]["UMBRELLA_mid_dim_world"] for f in fr if "UMBRELLA_mid_dim_world" in P[f]}
    out["umbrella_mid_dim"] = {str(f): round(v, 3) for f, v in sorted(dims.items())}
    hd = {f: P[f]["UMBRELLA_hand_dist"] for f in fr if "UMBRELLA_hand_dist" in P[f]}
    out["umbrella_hand_dist_max"] = (max(hd.values()), max(hd, key=hd.get)) if hd else None
    if ls_ is not None and le_ is not None:
        ph = [P[f].get("PHONE_hand_dist") for f in fr if ls_ <= f <= le_ and "PHONE_hand_dist" in P[f]]
        phh = [P[f].get("PHONE_head_dist") for f in fr if ls_ <= f <= le_ and "PHONE_head_dist" in P[f]]
        out["phone_hand_dist_max"] = max(ph) if ph else None
        out["phone_head_dist_max"] = max(phh) if phh else None
    # parenting of the umbrella to a hand bone
    u = OB.get("UMBRELLA"); par = None
    if u and RIG:
        if u.parent == RIG and u.parent_type == 'BONE' and u.parent_bone in HB:
            par = "parent_bone " + u.parent_bone
        for c in u.constraints:
            if c.type in ('CHILD_OF', 'COPY_TRANSFORMS', 'ARMATURE') and not c.mute and getattr(c, 'target', None) == RIG and getattr(c, 'subtarget', '') in HB:
                par = f"{c.type} {c.subtarget}"
    out["umbrella_hand_link"] = par
    # finger motion in S3-S4 (sampled pose, includes NLA/drivers)
    fing = {f: P[f]["_fingers"] for f in fr if "_fingers" in P[f]}
    for f in fing:
        P[f].pop("_fingers", None)
    moved = {}
    for hand, bones in FINGERS:
        n = 0
        for b in bones:
            vals = np.array([fing[f][b] for f in fing if b in fing[f]])
            if len(vals) >= 2 and np.ptp(vals, 0).max() > 1e-3:
                n += 1
        moved[hand] = n
    out["finger_bones_moving_S3S4"] = moved
    X["props_summary"] = out
    for f in fr:
        for k in list(P[f]):
            if k.startswith("_"):
                P[f].pop(k, None)
    X["props"] = {}   # raw per-frame data not needed downstream


# ---------------- execute schedule (ascending) ----------------
def run_schedule():
    if not tasks:
        return
    need = sorted(tasks)
    frames = list(range(need[0], need[-1] + 1)) if NEED_STEP else need
    if NEED_STEP:
        sc.frame_set(sc.frame_start)
        frames = list(range(0, need[-1] + 1))
    done = 0
    for f in frames:
        if time.time() - T0 > BUDGET:
            X["timeout_at_frame"] = f
            break
        sc.frame_set(f + OFF)
        for fn in tasks.get(f, []):
            try:
                fn()
            except Exception:
                R["errors"].append(f"x07 task @{f}: " + traceback.format_exc()[-400:])
        done += 1
    X["frames_visited"] = done
    X["elapsed_s"] = round(time.time() - T0, 1)


guard("x07_schedule", run_schedule)
guard("x07_rain_speed", rain_speed_match)
guard("x07_puddle", pud_summary)
guard("x07_feet", feet_summary)
guard("x07_props", props_summary)
for f in list(X.get("feet", {})):
    X["feet"][f] = {}
X.pop("feet", None)
for d in X.get("rain", {}).values():
    d.pop("_pts", None)
X["lamp"] = {str(k): v for k, v in X["lamp"].items()}
X["bus"] = {str(k): v for k, v in X["bus"].items()}
X["rain"] = {str(k): v for k, v in X["rain"].items()}
