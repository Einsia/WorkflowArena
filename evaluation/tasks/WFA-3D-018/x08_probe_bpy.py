# WFA-3D-018 project probe (runs inside Blender: blender -b scene.blend --python x08_probe_bpy.py -- cfg.json out.json)
# Modes: "measure" (default) exports everything the deterministic checks need in ONE forward pass over the base timeline;
#        "render" re-renders a few frames at low resolution (M16).
# Base frame f is mapped to scene frame f (+30 for f >= 600 when the file was saved with revision_insert_frames = 30),
# so the project may be saved in either state.
import bpy, json, math, os, re, sys, traceback
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
cfg = json.load(open(argv[0])); OUTF = argv[1]
sc = bpy.context.scene; OB = bpy.data.objects
R = {"errors": []}


def guard(n, fn):
    try:
        fn()
    except Exception:
        R["errors"].append(n + ": " + traceback.format_exc()[-600:])


def V(v):
    return [round(float(x), 5) for x in v]


# ---------------------------------------------------------------- static info
def basic():
    R["version"] = bpy.app.version_string
    R["objects"] = {o.name: {"type": o.type, "parent": o.parent.name if o.parent else None} for o in OB}
    R["frame_range"] = [sc.frame_start, sc.frame_end]
    props = {}
    for k in sc.keys():
        if k.startswith("_"):
            continue
        v = sc[k]
        props[k] = v if isinstance(v, (int, float, str)) else str(v)
    R["scene_props"] = props
    R["engine"] = sc.render.engine
    R["motion_blur"] = bool(sc.render.use_motion_blur)
    den = None
    try:
        den = bool(sc.cycles.use_denoising) if sc.render.engine == "CYCLES" else None
    except Exception:
        pass
    R["denoise"] = den
    R["resolution"] = [sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage]
guard("basic", basic)

RV = R.get("scene_props", {}).get("revision_insert_frames")
try:
    RV = int(RV)
except Exception:
    RV = None
R["rv"] = RV


def smap(f):
    return f + 30 if (RV == 30 and f >= 600) else f


def files():
    bad, urls = [], []
    for coll in (bpy.data.images, bpy.data.sounds, bpy.data.movieclips, bpy.data.libraries, bpy.data.fonts):
        for d in coll:
            fp = getattr(d, "filepath", "") or ""
            if not fp or getattr(d, "packed_file", None) or fp.startswith("<"):
                continue
            if re.match(r"https?://", fp):
                urls.append(fp); continue
            if getattr(d, "source", "FILE") in ("GENERATED", "VIEWER"):
                continue
            ap = bpy.path.abspath(fp)
            if "#" in ap or "<UDIM>" in ap:
                continue
            if not os.path.exists(ap):
                bad.append(fp)
    R["missing_files"] = bad[:30]; R["n_missing"] = len(bad); R["url_refs"] = urls[:10]
guard("files", files)


def looks():
    """X06 project floor: lights, world, material node summary."""
    lights = []
    for o in OB:
        if o.type == "LIGHT":
            d = o.data
            size = getattr(d, "size", 0.0) if d.type == "AREA" else getattr(d, "shadow_soft_size", 0.0)
            lights.append({"name": o.name, "type": d.type, "size": float(size or 0.0), "energy": float(d.energy)})
    R["lights"] = lights
    w = sc.world; wt = []
    if w and w.use_nodes and w.node_tree:
        wt = sorted({n.type for n in w.node_tree.nodes})
    R["world_nodes"] = wt
    mats = {}
    for o in OB:
        if o.type not in ("MESH", "CURVE", "SURFACE", "META", "FONT"):
            continue
        for s in o.material_slots:
            m = s.material
            if not m or m.name in mats:
                continue
            types = [n.type for n in m.node_tree.nodes] if (m.use_nodes and m.node_tree) else []
            mats[m.name] = {"bsdf": any(t.startswith("BSDF") or t in ("SUBSURFACE_SCATTERING",) for t in types),
                            "tex": sum(1 for t in types if t.startswith("TEX_")),
                            "bump": any(t in ("BUMP", "NORMAL_MAP", "DISPLACEMENT") for t in types)}
    R["materials"] = mats
guard("looks", looks)


def physics():
    rw = sc.rigidbody_world
    d = {"world": bool(rw)}
    if rw:
        pc = rw.point_cache
        d.update(enabled=bool(rw.enabled), collection=[o.name for o in rw.collection.objects] if rw.collection else [],
                 baked=bool(pc.is_baked), cache_range=[pc.frame_start, pc.frame_end], disk=bool(pc.use_disk_cache),
                 info=str(pc.info), outdated=bool(getattr(pc, "is_outdated", False)))
    rb = {}
    for n in ("TRAY_A", "TRAY_B", "BAG"):
        o = OB.get(n)
        if not o:
            continue
        nk = 0
        ad = o.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                if fc.data_path in ("location", "rotation_euler", "rotation_quaternion"):
                    nk = max(nk, len(fc.keyframe_points))
        rb[n] = {"rigid_body": o.rigid_body.type if o.rigid_body else None, "n_keys": nk}
    d["objects"] = rb
    R["physics"] = d
guard("physics", physics)


# ---------------------------------------------------------------- rig analysis
SIDE_L = re.compile(r"(\.|_|-|\b)(l|left)$|left", re.I)
SIDE_R = re.compile(r"(\.|_|-|\b)(r|right)$|right", re.I)
RIGINFO = {}


def chain_len(b):
    n = 1
    while len(b.children) == 1:
        b = b.children[0]; n += 1
    return n if not b.children else 0


def chain_bones(b):
    out = [b]
    while len(b.children) == 1:
        b = b.children[0]; out.append(b)
    return out


def rigs():
    out = {}
    for rn, mn in cfg.get("rigs", {}).items():
        r = OB.get(rn); d = {"exists": bool(r), "is_armature": bool(r and r.type == "ARMATURE")}
        m = OB.get(mn); d["char_bound"] = False; d["vg_cover"] = None
        if m and r:
            cands = [m] + [c for c in m.children_recursive if c.type == "MESH"]
            for c in cands:
                if c.type == "MESH" and any(md.type == "ARMATURE" and md.object == r for md in c.modifiers):
                    d["char_bound"] = True
                    names = {g.index for g in c.vertex_groups if g.name in r.data.bones}
                    n = len(c.data.vertices)
                    cov = sum(1 for v in c.data.vertices if any(g.group in names and g.weight > 0 for g in v.groups))
                    d["vg_cover"] = max(d["vg_cover"] or 0, cov / max(n, 1))
        hands = []; keyed = set(); info = {}
        if r and r.type == "ARMATURE":
            bones = r.data.bones
            for b in bones:
                ch = [c for c in b.children if chain_len(c) >= 3]
                if len(ch) >= 4:
                    hands.append((b, ch))
            act = r.animation_data.action if r.animation_data else None
            if act:
                for fc in act.fcurves:
                    mm = re.match(r'pose\.bones\["(.+?)"\]', fc.data_path)
                    if mm and len(fc.keyframe_points) >= 2:
                        vals = [k.co[1] for k in fc.keyframe_points]
                        if max(vals) - min(vals) > 1e-4:
                            keyed.add(mm.group(1))

            def deform_score(h):
                return sum(1 for c in h[1] for x in chain_bones(c) if x.use_deform)
            hands.sort(key=lambda h: -deform_score(h))   # Rigify keeps ORG/MCH copies; prefer deforming hands
            sel = {}
            for b, ch in hands:
                nm = b.name
                if SIDE_L.search(nm) and not SIDE_R.search(nm):
                    side = "L"
                elif SIDE_R.search(nm):
                    side = "R"
                else:
                    side = "L" if b.head_local.x > 0 else "R"
                if side in sel:
                    continue
                anc = []
                p = b.parent
                while p is not None and len(anc) < 4:
                    anc.append(p); p = p.parent
                fore = [a for a in anc if re.search(r"fore|lowerarm|lower_arm|elbow", a.name, re.I)]
                elbow = fore[-1] if fore else (anc[0] if anc else b)
                upper = [a for a in anc if re.search(r"upper|uparm|arm", a.name, re.I) and a not in fore]
                shoulder = upper[0] if upper else (anc[1] if len(anc) > 1 else elbow)
                sel[side] = {"hand": nm, "elbow": elbow.name, "shoulder": shoulder.name,
                             "fingers": [x.name for c in ch for x in chain_bones(c)], "tips": [chain_bones(c)[-1].name for c in ch]}

            def pick(rx, excl=r"end|top|tail|ik|pole|target|mch|ctrl|org"):
                c = [b for b in bones if re.search(rx, b.name, re.I) and not re.search(excl, b.name, re.I)]
                c.sort(key=lambda b: (not b.use_deform, len(b.name)))
                return c[0] if c else None
            pel = pick(r"pelvis") or pick(r"hips?\b|hip$|^hips") or pick(r"root") or next((b for b in bones if b.parent is None), None)
            head = pick(r"(^|[^a-z])head($|[^a-z])") or (max(bones, key=lambda b: b.head_local.z) if len(bones) else None)
            info = {"pelvis": pel.name if pel else None, "head": head.name if head else None, "hands": sel}
        d["hands"] = [{"hand": b.name, "chains": len(ch), "keyed_finger_bones": len({x.name for c in ch for x in chain_bones(c)} & keyed)} for b, ch in hands]
        d["key_bones"] = info
        RIGINFO[rn] = info
        out[rn] = d
    R["rigs"] = out
guard("rigs", rigs)


def bone_world(r, name, tail=False):
    pb = r.pose.bones.get(name)
    if pb is None:
        return None
    return r.matrix_world @ (pb.tail if tail else pb.head)


def rig_points(rn):
    """per-frame skeleton sample: pelvis, head position + head axes, rig axes, per hand wrist/elbow/shoulder."""
    r = OB.get(rn); info = RIGINFO.get(rn) or {}
    if not r or r.type != "ARMATURE":
        return None
    d = {}
    if info.get("pelvis"):
        d["pelvis"] = V(bone_world(r, info["pelvis"]))
    if info.get("head") and r.pose.bones.get(info["head"]):
        M = r.matrix_world @ r.pose.bones[info["head"]].matrix
        d["head"] = V(M.translation)
        d["head_ax"] = [V(M.col[i].xyz.normalized()) for i in range(3)]
    d["rig_ax"] = [V(r.matrix_world.col[i].xyz.normalized()) for i in range(3)]
    hs = {}
    for side, h in (info.get("hands") or {}).items():
        hs[side] = {"wrist": V(bone_world(r, h["hand"])), "elbow": V(bone_world(r, h["elbow"])),
                    "shoulder": V(bone_world(r, h["shoulder"]))}
    d["hands"] = hs
    return d


def hand_points(rn):
    """world points of each hand (palm + all finger heads/tails) and fingertips."""
    r = OB.get(rn); info = RIGINFO.get(rn) or {}
    out = {}
    if not r:
        return out
    for side, h in (info.get("hands") or {}).items():
        pts = [bone_world(r, h["hand"]), bone_world(r, h["hand"], True)]
        for b in h["fingers"]:
            pts += [bone_world(r, b), bone_world(r, b, True)]
        tips = [bone_world(r, b, True) for b in h["tips"]]
        out[side] = ([p for p in pts if p is not None], [p for p in tips if p is not None])
    return out


# ---------------------------------------------------------------- mesh helpers (evaluated, world space)
def family(name):
    o = OB.get(name)
    if not o:
        return []
    return [x for x in [o] + list(o.children_recursive) if x.type in ("MESH", "CURVE", "SURFACE", "META", "FONT")]


def world_mesh(objs, dg, maxv=None):
    verts, polys = [], []
    for o in objs:
        e = o.evaluated_get(dg)
        try:
            me = e.to_mesh()
        except Exception:
            continue
        if me is None:
            continue
        mw = e.matrix_world.copy(); base = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        polys += [[base + i for i in p.vertices] for p in me.polygons]
        e.to_mesh_clear()
    if maxv and len(verts) > maxv:
        step = len(verts) / maxv
        sub = [verts[int(i * step)] for i in range(maxv)]
    else:
        sub = verts
    return verts, polys, sub


def bvh_of(objs, dg):
    v, p, _ = world_mesh(objs, dg)
    if not v or not p:
        return None, v
    return BVHTree.FromPolygons(v, p, all_triangles=False), v


def vbox(v):
    if not v:
        return None
    xs = [a.x for a in v]; ys = [a.y for a in v]; zs = [a.z for a in v]
    return [round(min(xs), 5), round(max(xs), 5), round(min(ys), 5), round(max(ys), 5), round(min(zs), 5), round(max(zs), 5)]


def penetration(bvh_b, pts):
    """max depth of points inside closed mesh B (inside = behind the face normal at the nearest surface point)."""
    worst = 0.0
    for p in pts:
        loc, nrm, idx, dist = bvh_b.find_nearest(p)
        if loc is None:
            continue
        if (p - loc).dot(nrm) < 0:
            worst = max(worst, dist)
    return worst


def overlap_depth(ba, bb, va, vb):
    """surfaces intersect -> penetration estimated as the smallest overlap extent of the two world AABBs."""
    if not ba.overlap(bb):
        return 0.0
    a, b = vbox(va), vbox(vb)
    return max(0.0, min(min(a[2 * i + 1], b[2 * i + 1]) - max(a[2 * i], b[2 * i]) for i in range(3)))


def min_dist(bvh_b, pts):
    best = 1e9
    for p in pts:
        loc, nrm, idx, dist = bvh_b.find_nearest(p)
        if loc is not None:
            best = min(best, dist)
    return best


def proj(cam, pts):
    from bpy_extras.object_utils import world_to_camera_view
    c = [world_to_camera_view(sc, cam, p) for p in pts]
    if not c:
        return None
    xs = [a.x for a in c]; ys = [a.y for a in c]; zs = [a.z for a in c]
    return [round(min(xs), 4), round(max(xs), 4), round(min(ys), 4), round(max(ys), 4), round(min(zs), 4)]


def sub_pts(v, n):
    return v[::max(1, len(v) // n)] if v else []


# ---------------------------------------------------------------- per-frame pass (frames ascending: rigid-body safe)
def measure():
    frames = sorted(set(int(f) for f in cfg.get("frames", range(0, 900))))
    cams_cfg = cfg.get("cams", {}); track = cfg.get("track", []); rig_names = list(cfg.get("rigs", {}).keys())
    req = cfg.get("req", {})

    def fs(key):
        return set(int(f) for f in req.get(key, []))
    F_vbox = {n: set(int(f) for f in fr) for n, fr in req.get("vbox", {}).items()}
    F_contact = fs("contact_bag"); F_button = fs("contact_button"); F_btn_disp = fs("button_disp")
    F_gate = fs("gate"); F_gate_pen = fs("gate_pen"); F_tray = fs("tray"); F_proj = req.get("proj", {}); F_mon = fs("monitor_proj")
    tracks = {n: ([] if OB.get(n) else None) for n in track}
    camrows = {c: ([] if (OB.get(c) and OB[c].type == "CAMERA") else None) for c in cams_cfg}
    skel = {rn: [] for rn in rig_names}
    meas = {"vbox": {n: [] for n in F_vbox}, "contact_bag": [], "contact_button": [], "button_disp": [], "gate": [],
            "gate_pen": [], "tray": [], "proj": [], "monitor_proj": []}
    ref = {}
    for f in frames:
        sc.frame_set(smap(f))
        dg = bpy.context.evaluated_depsgraph_get()
        for n in track:
            o = OB.get(n)
            if not o:
                continue
            e = o.evaluated_get(dg)
            pts = [e.matrix_world @ Vector(cc) for cc in e.bound_box]
            tracks[n].append([f, V(sum(pts, Vector()) / 8), V(e.matrix_world.translation)])
        for cn, (a, b) in cams_cfg.items():
            if camrows.get(cn) is None or not (a <= f <= b):
                continue
            c = OB[cn]; m = c.matrix_world.copy(); M3 = m.to_3x3()
            fw = (M3 @ Vector((0, 0, -1))).normalized(); rt = (M3 @ Vector((1, 0, 0))).normalized()
            d = c.data; fd = d.dof.focus_distance
            if d.dof.focus_object:
                fd = (d.dof.focus_object.matrix_world.translation - m.translation).length
            camrows[cn].append([f, V(m.translation), V(fw), float(d.lens), bool(d.dof.use_dof), float(d.dof.aperture_fstop), float(fd), V(rt)])
        for rn in rig_names:
            try:
                p = rig_points(rn)
            except Exception:
                p = None
            skel[rn].append([f, p])
        for n, fr in F_vbox.items():
            if f in fr:
                v, _, _ = world_mesh(family(n), dg)
                meas["vbox"][n].append([f, vbox(v)])
        if f in F_contact:  # X03: screener hands vs BAG surface
            bvh, v = bvh_of(family("BAG"), dg)
            row = {"f": f, "bag_box": vbox(v)}
            if bvh:
                for side, (pts, tips) in hand_points("SCREENER_RIG").items():
                    row[side] = round(min_dist(bvh, pts), 4) if pts else None
            meas["contact_bag"].append(row)
        if f in F_button:  # X04: fingertips vs button surface
            bvh, v = bvh_of(family("BELT_STOP_BUTTON"), dg); row = {"f": f}
            if bvh:
                ds = [min_dist(bvh, tips) for side, (pts, tips) in hand_points("SCREENER_RIG").items() if tips]
                row["tip"] = round(min(ds), 4) if ds else None
            meas["contact_button"].append(row)
        for key, fam, F_ in (("button_disp", "BELT_STOP_BUTTON", F_btn_disp), ("gate", "TURNSTILE_GATE2", F_gate)):
            if f in F_:  # max vertex displacement relative to the first requested frame
                v, _, _ = world_mesh(family(fam), dg)
                if key not in ref or len(ref[key]) != len(v):
                    ref[key] = v; dmax = 0.0
                else:
                    dmax = max(((a - b).length for a, b in zip(v, ref[key])), default=0.0)
                meas[key].append([f, round(dmax, 5)])
        if f in F_gate_pen:  # M11: passenger vs gate interpenetration
            bvh, _ = bvh_of(family("TURNSTILE_GATE2"), dg)
            _, _, sub = world_mesh(family("PASSENGER"), dg, 3000)
            meas["gate_pen"].append([f, round(penetration(bvh, sub), 4) if bvh else None])
        if f in F_tray:  # M12: tray gap / penetration
            ba, va = bvh_of(family("TRAY_A"), dg); bb, vb = bvh_of(family("TRAY_B"), dg); bc, vc = bvh_of(family("CONVEYOR"), dg)
            sa, sb = sub_pts(va, 1500), sub_pts(vb, 1500)
            row = {"f": f, "A": vbox(va), "B": vbox(vb), "C": vbox(vc)}
            if ba and bb:
                row["gap_ab"] = round(min(min_dist(bb, sa), min_dist(ba, sb)), 4)
                row["pen_ab"] = round(max(penetration(bb, sa), penetration(ba, sb), overlap_depth(ba, bb, va, vb)), 4)
            if bc:
                row["pen_conv"] = round(max([penetration(bc, sa), penetration(bc, sb)] + [overlap_depth(x, bc, v, vc) for x, v in ((ba, va), (bb, vb)) if x]), 4)
            meas["tray"].append(row)
        for cn, spec in F_proj.items():
            if f in set(int(x) for x in spec.get("frames", [])) and OB.get(cn):
                row = {"f": f, "cam": cn}
                for n in spec.get("objects", []):
                    v, _, _ = world_mesh(family(n), dg)
                    row[n] = proj(OB[cn], sub_pts(v, 3000)) if v else None
                meas["proj"].append(row)
        if f in F_mon and OB.get("CAM_S3"):
            v, _, _ = world_mesh(family("MONITOR"), dg)
            meas["monitor_proj"].append([f, proj(OB["CAM_S3"], sub_pts(v, 3000)) if v else None])
    R["tracks"] = tracks; R["cams"] = camrows; R["skel"] = skel; R["meas"] = meas


def mouth():
    out = {}
    for rn, (mn, a, b) in cfg.get("mouth", {}).items():
        r = OB.get(rn); m = OB.get(mn)
        meshes = [o for o in ([m] + list(m.children_recursive) if m else []) if o.type == "MESH"]
        meshes += [o for o in OB if o.type == "MESH" and r and any(md.type == "ARMATURE" and md.object == r for md in o.modifiers)]
        keys = [kb for o in set(meshes) if o.data.shape_keys for kb in o.data.shape_keys.key_blocks[1:]]
        mk = [kb for kb in keys if re.search(r"mouth|jaw|lip|vis|open|aa|oh|ee|mbp|viseme", kb.name, re.I)] or keys
        jaw = [pb for pb in (r.pose.bones if r and r.type == "ARMATURE" else []) if re.search(r"jaw|chin|mouth|lip", pb.name, re.I)]
        cur = []
        for f in range(a, b + 1):
            sc.frame_set(smap(f)); v = sum(kb.value for kb in mk)
            for pb in jaw[:2]:
                q = pb.matrix_basis.to_quaternion(); v += 2 * math.acos(max(-1, min(1, abs(q.w))))
            cur.append(v)
        out[rn] = {"start": a, "curve": cur, "sources": [kb.name for kb in mk][:10] + [pb.name for pb in jaw][:4]}
    R["mouth"] = out


def revision_pass():
    """M17: revision state around the insert (scene frames 596-633, plus 700/800/900). If the file was saved in base
    state, set the property to 30 (frame_end 929) first; checks.py decides whether that changed the evaluated scene."""
    names = cfg.get("track", []); rig_names = list(cfg.get("rigs", {}).keys())
    res = {"saved_rv": RV}
    if RV != 30:
        if "revision_insert_frames" not in sc.keys():
            res["error"] = "no revision_insert_frames property"; R["revision"] = res; return
        sc["revision_insert_frames"] = 30
        sc.frame_end = 929
        try:
            sc.update_tag(); bpy.context.view_layer.update()
        except Exception:
            pass
    rows = []
    for f in list(range(596, 634)) + [700, 800, 900]:
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); row = {"f": f}
        for n in names:
            o = OB.get(n)
            if o:
                e = o.evaluated_get(dg); pts = [e.matrix_world @ Vector(cc) for cc in e.bound_box]
                row[n] = V(sum(pts, Vector()) / 8)
        for rn in rig_names:
            p = rig_points(rn)
            if p and p.get("pelvis"):
                row[rn] = p["pelvis"]
        for cn in ("CAM_S4", "CAM_S5"):
            c = OB.get(cn)
            if c:
                row[cn] = V(c.matrix_world.translation)
        rows.append(row)
    res["rows"] = rows
    R["revision"] = res


def render():
    import time
    rr = cfg.get("render", {})
    out_dir = rr["dir"]
    try:
        if sc.render.engine != "CYCLES":
            sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = int(rr.get("samples", 16))
        try:
            sc.cycles.time_limit = float(rr.get("time_limit", 90))
        except Exception:
            pass
        try:
            sc.cycles.use_denoising = True
        except Exception:
            pass
    except Exception:
        R["errors"].append("render setup: " + traceback.format_exc()[-300:])
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 320, 180, 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"
    sc.render.use_motion_blur = False
    done = {}
    for f in rr.get("frames", []):
        t0 = time.time()
        sc.frame_set(smap(int(f)))
        sc.render.filepath = os.path.join(out_dir, "rr_%04d.png" % int(f))
        try:
            bpy.ops.render.render(write_still=True)
            done[str(f)] = round(time.time() - t0, 1)
        except Exception:
            R["errors"].append("render %s: " % f + traceback.format_exc()[-300:])
    R["rendered"] = done


mode = cfg.get("mode", "measure")
if mode == "render":
    guard("render", render)
else:
    guard("measure", measure)
    guard("mouth", mouth)
    if cfg.get("revision_pass"):
        guard("revision", revision_pass)
json.dump(R, open(OUTF, "w"), default=str)
print("X08PROBE_OK")
