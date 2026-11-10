# -*- coding: utf-8 -*-
"""Rich headless-Blender measurement dump + numpy geometry helpers for CDC-3D verifiers (2026-10-25).

Usage from checks.py:
    import _cdc_blend as B
    D = B.rich_dump(blend, cfg, tmp, timeout=1200)      # dict; D['ok'] False + D['error'] on failure (never raises)
    cfg keys (all optional):
      track:        [object names]  -> D['mats'][f][name] = 4x4 matrix_world (per sampled frame)
      frames:       [scene frames] to sample (default: frame_start..frame_end); keys = scene frames
      film_frames:  [film frames f] sampled at scene frame frame_start + f; keys = film frames (D['frame_offset'])
      trim:         value for scene['revision_trim_frames'] (or any 'props' dict below) before sampling
      props:        {scene custom property: value} set before sampling
      rigs:         [armature names] -> static bone table + per-frame world head/tail of bones matching bone_re
      bone_re:      regex (case-insensitive) of bones to sample per frame (default hands/fingers/jaw/head)
      cams:         [camera names] -> per-frame intrinsics (lens, sensor, shift, dof, fstop, type, ortho)
      samples:      {object: n} -> n surface points (object-local, evaluated mesh at first sampled frame)
      bbox_world:   {object: [frames]} -> evaluated world bbox corners at those frames
      shapekey_re:  regex of shape-key names to sample per frame on meshes deformed by / named after the rigs
      chan_re:      regex of pose bones whose local rotation angle (deg, from matrix_basis) is sampled per frame
      mat_re:       regex of pose bones whose world rotation (3x3, columns = bone X,Y,Z axes) is sampled per frame
                    -> D['bmat'][rig][f][bone]
      extra:        python source; may define setup(ctx) and frame(ctx, f); ctx = dict(bpy, sc, dg, D, cfg, np)
                    (anything stored into D is returned)
    Static info always returned: objects (type), parents, scene props, frame range, fps, resolution, engine,
    render (denoise/samples), armature modifiers, fcurve summary per object (+ shape-key datablocks), keyed bones,
    materials, lights, world nodes, fluid / rigid-body / cloth / soft-body / particle physics with cache info.
Film frame f is mapped to scene frame frame_start + f by the callers (see film2scene).
"""
import json, math, pathlib, re, shutil, subprocess, time
import numpy as np

DUMP_PY = r'''
import bpy, json, sys, os, re, math, traceback
try:
    import numpy as np
except Exception:
    np = None
argv = sys.argv[sys.argv.index("--") + 1:]
cfg = json.load(open(argv[0])); out = argv[1]
if getattr(bpy.app, "autoexec_fail", False):
    # the file's registered scripts were blocked (no -y support in this Blender build): run them as -y would
    for _t in bpy.data.texts:
        if _t.use_module:
            try:
                exec(compile(_t.as_string(), _t.name, "exec"), {"__name__": _t.name})
            except Exception as _e:
                print("autoexec emulation failed for", _t.name, _e)
sc = bpy.context.scene
D = {"ok": True, "version": bpy.app.version_string, "file": bpy.data.filepath, "warnings": [],
     "autoexec_emulated": bool(getattr(bpy.app, "autoexec_fail", False))}
def W(msg):
    D["warnings"].append(str(msg)[:300])
def r5(x):
    return round(float(x), 5)
def mat(m):
    return [[r5(v) for v in row] for row in m]
def props_of(idb):
    o = {}
    for k in idb.keys():
        try:
            v = idb[k]
            o[k] = v if isinstance(v, (int, float, str, bool)) else str(v)
        except Exception:
            pass
    return o
D["objects"] = {o.name: o.type for o in bpy.data.objects}
D["parents"] = {o.name: [o.parent.name if o.parent else None, o.parent_type, o.parent_bone] for o in bpy.data.objects}
D["scene_props"] = props_of(sc)
D["frame_range"] = [sc.frame_start, sc.frame_end]
D["fps"] = [sc.render.fps, sc.render.fps_base]
D["resolution"] = [sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage,
                   sc.render.pixel_aspect_x, sc.render.pixel_aspect_y]
D["engine"] = sc.render.engine
rd = {}
try:
    rd["cycles_samples"] = sc.cycles.samples; rd["cycles_denoise"] = bool(sc.cycles.use_denoising)
except Exception:
    pass
try:
    import _cycles
    rd["oidn_available"] = bool(getattr(_cycles, "with_openimagedenoise", True))
except Exception:
    pass
try:
    rd["eevee_samples"] = sc.eevee.taa_render_samples
except Exception:
    pass
try:
    rd["compositor_denoise"] = bool(sc.node_tree and any(n.type == "DENOISE" for n in sc.node_tree.nodes))
except Exception:
    pass
D["render"] = rd
D["camera"] = sc.camera.name if sc.camera else None
D["markers"] = [[m.name, m.frame, m.camera.name if m.camera else None] for m in sc.timeline_markers]
D["armature_mods"] = {o.name: [m.object.name for m in o.modifiers if m.type == "ARMATURE" and m.object]
                      for o in bpy.data.objects if o.type == "MESH"}
D["modifiers"] = {o.name: [[m.name, m.type] for m in o.modifiers] for o in bpy.data.objects if len(getattr(o, "modifiers", []))}
D["constraints"] = {o.name: [[c.name, c.type, getattr(getattr(c, "target", None), "name", None)] for c in o.constraints]
                    for o in bpy.data.objects if len(o.constraints)}
D["hide_render"] = {o.name: bool(o.hide_render) for o in bpy.data.objects}
D["collection_children"] = {c.name: [o.name for o in c.all_objects] for c in bpy.data.collections}
# ---- fcurves (object actions, NLA strips, shape-key actions)
def actions_of(idb):
    acts = []
    ad = getattr(idb, "animation_data", None)
    if ad:
        if ad.action: acts.append(ad.action)
        for tr in ad.nla_tracks:
            for st in tr.strips:
                if st.action and st.action not in acts: acts.append(st.action)
    return acts
def fc_summary(idb):
    res = []
    for a in actions_of(idb):
        for fc in a.fcurves:
            kp = fc.keyframe_points
            vals = [p.co[1] for p in kp]
            res.append({"path": fc.data_path, "index": fc.array_index, "n": len(kp),
                        "frames": [r5(p.co[0]) for p in kp][:400], "values": [r5(v) for v in vals][:400],
                        "vmin": r5(min(vals)) if vals else None, "vmax": r5(max(vals)) if vals else None})
    try:
        ad = idb.animation_data
        if ad:
            for dr in ad.drivers:
                res.append({"path": dr.data_path, "index": dr.array_index, "driver": dr.driver.type,
                            "expr": dr.driver.expression[:200], "n": 0})
    except Exception:
        pass
    return res
D["fcurves"] = {}
for o in bpy.data.objects:
    s = fc_summary(o)
    if s: D["fcurves"][o.name] = s
    if o.type == "MESH" and o.data.shape_keys:
        s2 = fc_summary(o.data.shape_keys)
        if s2: D["fcurves"][o.name + "|shape_keys"] = s2
    if o.type in ("CAMERA", "LIGHT") and o.data:
        s3 = fc_summary(o.data)
        if s3: D["fcurves"][o.name + "|data"] = s3
def keyed_bones(o):
    ks = set()
    for f in D["fcurves"].get(o.name, []):
        m = re.match(r'pose\.bones\["(.+?)"\]', f["path"])
        if m and (f.get("n", 0) >= 2 or "driver" in f): ks.add(m.group(1))
    return sorted(ks)
# ---- armatures
D["armatures"] = {}
for o in bpy.data.objects:
    if o.type == "ARMATURE":
        D["armatures"][o.name] = {"bones": {b.name: [b.parent.name if b.parent else None, bool(b.use_deform), r5(b.length)]
                                            for b in o.data.bones},
                                  "keyed": keyed_bones(o),
                                  "constrained": sorted(pb.name for pb in o.pose.bones if len(pb.constraints))}
# ---- shape keys
D["shape_keys"] = {o.name: [k.name for k in o.data.shape_keys.key_blocks] for o in bpy.data.objects
                   if o.type == "MESH" and o.data.shape_keys}
# ---- materials / lights / world
def mat_info(m):
    e = {"name": m.name, "use_nodes": bool(m.use_nodes)}
    if m.use_nodes and m.node_tree:
        nt = m.node_tree
        e["node_types"] = sorted(set(n.type for n in nt.nodes))
        e["n_tex"] = sum(1 for n in nt.nodes if n.type.startswith("TEX_"))
        lk = []
        for n in nt.nodes:
            if n.type == "BSDF_PRINCIPLED":
                lk += [i.name for i in n.inputs if i.is_linked]
        e["principled_linked"] = sorted(set(lk))
    return e
D["materials"] = {}
for o in bpy.data.objects:
    if hasattr(o, "material_slots") and o.material_slots:
        D["materials"][o.name] = [mat_info(s.material) for s in o.material_slots if s.material]
D["lights"] = {o.name: {"type": o.data.type, "energy": r5(o.data.energy),
                        "size": r5(getattr(o.data, "size", 0) or 0), "radius": r5(getattr(o.data, "shadow_soft_size", 0) or 0),
                        "angle": r5(getattr(o.data, "angle", 0) or 0), "color": [r5(c) for c in o.data.color]}
               for o in bpy.data.objects if o.type == "LIGHT"}
try:
    wn = sc.world.node_tree.nodes if sc.world and sc.world.use_nodes else []
    D["world_nodes"] = sorted(set(n.type for n in wn))
except Exception:
    D["world_nodes"] = []
# ---- physics
blenddir = os.path.dirname(bpy.data.filepath)
def absp(p):
    try:
        return os.path.normpath(bpy.path.abspath(p)) if p else ""
    except Exception:
        return p
def pcache(pc):
    if pc is None: return None
    e = {}
    for k in ("frame_start", "frame_end", "is_baked", "use_disk_cache", "use_external", "filepath", "name", "is_outdated"):
        try:
            e[k] = getattr(pc, k)
        except Exception:
            pass
    if e.get("filepath"): e["filepath_abs"] = absp(e["filepath"])
    return e
phys = {}
for o in bpy.data.objects:
    for m in getattr(o, "modifiers", []):
        if m.type == "FLUID":
            e = {"modifier": m.name, "fluid_type": m.fluid_type}
            if m.fluid_type == "DOMAIN":
                ds = m.domain_settings
                e.update(domain_type=ds.domain_type, cache_directory=ds.cache_directory, cache_dir_abs=absp(ds.cache_directory),
                         cache_type=ds.cache_type, cache_frame_start=ds.cache_frame_start, cache_frame_end=ds.cache_frame_end,
                         resolution_max=ds.resolution_max, use_mesh=bool(getattr(ds, "use_mesh", False)))
                try: e["cache_data_format"] = ds.cache_data_format
                except Exception: pass
            elif m.fluid_type == "FLOW":
                fs = m.flow_settings; e.update(flow_type=fs.flow_type, flow_behavior=fs.flow_behavior)
            phys.setdefault(o.name, []).append(e)
        elif m.type in ("CLOTH", "SOFT_BODY"):
            phys.setdefault(o.name, []).append({"modifier": m.name, "type": m.type, "cache": pcache(m.point_cache)})
        elif m.type == "PARTICLE_SYSTEM":
            ps = m.particle_system
            phys.setdefault(o.name, []).append({"modifier": m.name, "type": "PARTICLES", "count": ps.settings.count,
                                                "ptype": ps.settings.type, "physics": ps.settings.physics_type,
                                                "cache": pcache(ps.point_cache)})
    if o.rigid_body:
        rb = o.rigid_body
        phys.setdefault(o.name, []).append({"type": "RIGID_BODY", "rb_type": rb.type, "enabled": bool(rb.enabled),
                                            "kinematic": bool(rb.kinematic), "mass": r5(rb.mass), "shape": rb.collision_shape})
D["physics"] = phys
rbw = sc.rigidbody_world
D["rigidbody_world"] = None if rbw is None else {
    "enabled": bool(rbw.enabled), "time_scale": r5(rbw.time_scale),
    "collection": rbw.collection.name if rbw.collection else None,
    "objects": [o.name for o in rbw.collection.objects] if rbw.collection else [],
    "cache": pcache(rbw.point_cache), "substeps": getattr(rbw, "substeps_per_frame", None)}
D["gravity"] = [r5(x) for x in sc.gravity]; D["use_gravity"] = bool(sc.use_gravity)
# ---- configuration of per-frame sampling
for k, v in (cfg.get("props") or {}).items():
    try: sc[k] = v
    except Exception as ex: W(f"cannot set prop {k}: {ex}")
if cfg.get("trim") is not None:
    if "revision_trim_frames" in sc.keys(): sc["revision_trim_frames"] = int(cfg["trim"])
    else: W("revision_trim_frames missing")
D["frame_offset"] = 0
if cfg.get("film_frames") is not None:
    # keys are film frames f, sampled at scene frame frame_start + f
    D["frame_offset"] = sc.frame_start
    pairs = [(int(f), sc.frame_start + int(f)) for f in cfg["film_frames"]]
else:
    pairs = [(int(f), int(f)) for f in (cfg.get("frames") or list(range(sc.frame_start, sc.frame_end + 1)))]
frames = [k for k, _ in pairs]
D["frames"] = frames
track = [n for n in cfg.get("track", []) if n in bpy.data.objects]
cams = [n for n in cfg.get("cams", []) if n in bpy.data.objects and bpy.data.objects[n].type == "CAMERA"]
rigs = [n for n in cfg.get("rigs", []) if n in bpy.data.objects and bpy.data.objects[n].type == "ARMATURE"]
bre = re.compile(cfg.get("bone_re") or r"hand|palm|finger|thumb|index|middle|ring|pinky|little|f_|jaw|chin|mouth|lip|head|neck|spine|chest|pelvis|hips|foot|toe", re.I)
cre = re.compile(cfg.get("chan_re") or r"jaw|chin|mouth|lip|teeth", re.I)
skre = re.compile(cfg.get("shapekey_re") or r"jaw|mouth|lip|open|viseme|phon|mbp|vrc\.v|_aa|_oh|_ee", re.I)
sel = {}
for rn in rigs:
    o = bpy.data.objects[rn]
    m = [b.name for b in o.data.bones if bre.search(b.name)]
    dm = [n for n in m if o.data.bones[n].use_deform]
    sel[rn] = dm if len(dm) >= 4 else m
D["sampled_bones"] = sel
chans = {rn: [b.name for b in bpy.data.objects[rn].data.bones if cre.search(b.name)] for rn in rigs}
mre = re.compile(cfg["mat_re"], re.I) if cfg.get("mat_re") else None
mats_b = {rn: ([b.name for b in bpy.data.objects[rn].data.bones if mre.search(b.name)] if mre else []) for rn in rigs}
D["bmat"] = {}
D["chan_bones"] = chans
skm = []
for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        drv = set(D["armature_mods"].get(o.name, [])) | ({o.parent.name} if o.parent else set())
        if (drv & set(rigs)) or any(o.name.upper().startswith(r.split("_")[0].upper()) for r in rigs) or cfg.get("all_shapekeys"):
            ks = [k.name for k in o.data.shape_keys.key_blocks[1:] if skre.search(k.name)]
            if ks: skm.append((o.name, ks))
D["sampled_shapekeys"] = {n: ks for n, ks in skm}
D["mats"], D["bones"], D["cams"], D["chan"], D["sk"] = {}, {}, {}, {}, {}
ctx = {"bpy": bpy, "sc": sc, "D": D, "cfg": cfg, "np": np, "W": W}
ex_ns = {}
if cfg.get("extra"):
    try:
        exec(cfg["extra"], ex_ns)
    except Exception:
        W("extra compile error " + traceback.format_exc()[-400:])
try:
    if "setup" in ex_ns: ex_ns["setup"](ctx)
except Exception:
    W("extra setup error " + traceback.format_exc()[-400:])
samples = cfg.get("samples") or {}
bbw = {k: set(v) for k, v in (cfg.get("bbox_world") or {}).items()}
D["samples"], D["bbox_local"], D["bbox_world"] = {}, {}, {}
import random
def surface_samples(o, n, dg):
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    try:
        me.calc_loop_triangles()
        tris = [[tuple(me.vertices[i].co) for i in t.vertices] for t in me.loop_triangles]
        vs = [tuple(v.co) for v in me.vertices]
    finally:
        oe.to_mesh_clear()
    if not tris:
        return [list(map(r5, v)) for v in vs[:n]]
    def area(t):
        a, b, c = t
        u = [b[i] - a[i] for i in range(3)]; v = [c[i] - a[i] for i in range(3)]
        x = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        return 0.5 * math.sqrt(sum(q*q for q in x))
    ar = [area(t) for t in tris]; tot = sum(ar) or 1.0
    rnd = random.Random(12345)
    pts = []
    cum, acc = [], 0.0
    for a in ar:
        acc += a; cum.append(acc)
    import bisect
    for i in range(n):
        k = min(bisect.bisect_left(cum, rnd.random() * acc), len(tris) - 1)
        a, b, c = tris[k]; r1, r2 = rnd.random(), rnd.random()
        if r1 + r2 > 1: r1, r2 = 1 - r1, 1 - r2
        pts.append([r5(a[j] + r1 * (b[j] - a[j]) + r2 * (c[j] - a[j])) for j in range(3)])
    step = max(1, len(vs) // max(1, n // 4))
    pts += [list(map(r5, v)) for v in vs[::step]][: n // 4]
    return pts
t0 = __import__("time").time()
first = True
for f, sf in pairs:
    sc.frame_set(sf)
    ctx["scene_frame"] = sf
    dg = bpy.context.evaluated_depsgraph_get()
    ctx["dg"] = dg
    if first:
        for n, k in samples.items():
            o = bpy.data.objects.get(n)
            if o is not None and o.type in ("MESH", "CURVE", "SURFACE", "META", "FONT"):
                try:
                    D["samples"][n] = surface_samples(o, int(k), dg)
                    oe = o.evaluated_get(dg)
                    D["bbox_local"][n] = [[r5(c) for c in v] for v in oe.bound_box]
                except Exception as ex:
                    W(f"samples {n}: {ex}")
        first = False
    D["mats"][f] = {n: mat(bpy.data.objects[n].matrix_world) for n in track}
    for n, fs in bbw.items():
        if f in fs and n in bpy.data.objects:
            o = bpy.data.objects[n].evaluated_get(dg)
            D["bbox_world"].setdefault(n, {})[f] = [[r5(c) for c in (o.matrix_world @ __import__("mathutils").Vector(v))] for v in o.bound_box]
    for rn in rigs:
        o = bpy.data.objects[rn]; mw = o.matrix_world
        row = {}
        for bn in sel[rn]:
            pb = o.pose.bones.get(bn)
            if pb is None: continue
            h = mw @ pb.head; t = mw @ pb.tail
            row[bn] = [r5(h.x), r5(h.y), r5(h.z), r5(t.x), r5(t.y), r5(t.z)]
        D["bones"].setdefault(rn, {})[f] = row
        ch = {}
        for bn in chans[rn]:
            pb = o.pose.bones.get(bn)
            if pb is None: continue
            q = pb.matrix_basis.to_quaternion()
            ang = math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))
            loc = pb.matrix_basis.translation.length
            ch[bn] = [r5(ang), r5(loc)]
        D["chan"].setdefault(rn, {})[f] = ch
        if mats_b[rn]:
            R3 = mw.to_3x3()
            D["bmat"].setdefault(rn, {})[f] = {bn: [[r5(v) for v in row] for row in (R3 @ o.pose.bones[bn].matrix.to_3x3())]
                                               for bn in mats_b[rn] if bn in o.pose.bones}
    for n, ks in skm:
        kb = bpy.data.objects[n].data.shape_keys.key_blocks
        D["sk"].setdefault(n, {})[f] = {k: r5(kb[k].value) for k in ks}
    for cn in cams:
        c = bpy.data.objects[cn].data
        D["cams"].setdefault(cn, {})[f] = {"type": c.type, "lens": r5(c.lens), "sw": r5(c.sensor_width), "sh": r5(c.sensor_height),
                                           "fit": c.sensor_fit, "shx": r5(c.shift_x), "shy": r5(c.shift_y),
                                           "ortho": r5(c.ortho_scale), "dof": bool(c.dof.use_dof), "fstop": r5(c.dof.aperture_fstop),
                                           "focus": r5(c.dof.focus_distance), "focus_obj": c.dof.focus_object.name if c.dof.focus_object else None}
    if "frame" in ex_ns:
        try:
            ex_ns["frame"](ctx, f)
        except Exception:
            if len(D["warnings"]) < 40: W(f"extra frame {f} error " + traceback.format_exc()[-300:])
D["dump_seconds"] = round(__import__("time").time() - t0, 1)
json.dump(D, open(out, "w"))
print("RICH_DUMP_OK")
'''


def blender_ok():
    return shutil.which('blender') is not None


# Debian's Blender 4.3.2 (verifier image) is built against Python 3.13; its Mantaflow solver calls
# PyImport_AppendInittab after Py_Initialize, which Python >= 3.12 turns into a fatal abort as soon as any FLUID
# modifier is evaluated (file load, frame_set, render). When that happens the dump/render is retried with every
# FLUID modifier disabled from a load_post handler, so the rest of the scene can still be graded.
MANTAFLOW_CRASH = 'PyImport_AppendInittab'
FLUID_OFF_PY = r'''
import bpy
from bpy.app.handlers import persistent
@persistent
def _cdc_fluid_off(*_a):
    for o in bpy.data.objects:
        for m in getattr(o, "modifiers", []):
            if m.type == "FLUID":
                m.show_viewport = False; m.show_render = False
bpy.app.handlers.load_post.append(_cdc_fluid_off)
'''


def fluid_off_args(tmp):
    s = pathlib.Path(tmp) / 'cdc_fluid_off.py'
    s.write_text(FLUID_OFF_PY)
    return ['--python', str(s)]


def rich_dump(blend, cfg, tmp, timeout=1200, tag='main'):
    """Run DUMP_PY in Blender (background, autoexec enabled so solver drivers/handlers run).
    Returns the dump dict (D['ok'] True) or {'ok': False, 'error': str, 'opened': bool|None}. Never raises."""
    tmp = pathlib.Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    s, c, o = tmp / 'cdc_rich_dump.py', tmp / f'cdc_rich_cfg_{tag}.json', tmp / f'cdc_rich_{tag}.json'
    s.write_text(DUMP_PY)
    c.write_text(json.dumps(cfg))
    if o.exists():
        o.unlink()
    t0 = time.time()
    fluid_off = False
    for attempt in (0, 1):
        pre = fluid_off_args(tmp) if fluid_off else []
        try:
            r = subprocess.run(['blender', '-b', '-y'] + pre + [str(blend), '--python-exit-code', '1', '--python', str(s), '--', str(c), str(o)],
                               capture_output=True, text=True, timeout=max(1, timeout - (time.time() - t0)))
            txt = (r.stdout + r.stderr)[-2000:]
        except subprocess.TimeoutExpired:
            return {'ok': False, 'opened': None, 'error': f'blender dump timed out after {timeout} s'}
        except Exception as e:
            return {'ok': False, 'opened': None, 'error': f'blender run error: {e}'}
        if o.exists() or fluid_off or MANTAFLOW_CRASH not in (r.stdout + r.stderr):
            break
        fluid_off = True
    if o.exists():
        try:
            D = json.loads(o.read_text())
        except Exception as e:
            return {'ok': False, 'opened': True, 'error': f'dump unreadable: {e}'}
        D['mats'] = {int(f): v for f, v in D.get('mats', {}).items()}
        for k in ('cams', 'sk'):
            D[k] = {n: {int(f): v for f, v in d.items()} for n, d in D.get(k, {}).items()}
        for k in ('bones', 'chan', 'bmat'):
            D[k] = {n: {int(f): v for f, v in d.items()} for n, d in D.get(k, {}).items()}
        for n, d in list(D.get('bbox_world', {}).items()):
            D['bbox_world'][n] = {int(f): v for f, v in d.items()}
        D['wall_seconds'] = round(time.time() - t0, 1)
        if fluid_off:
            D['mantaflow_disabled'] = True
            D.setdefault('warnings', []).append('Blender aborted while evaluating a Mantaflow (FLUID) modifier (Debian Blender '
                                                '4.3.2 / Python 3.13 Mantaflow init crash); dump re-run with all FLUID modifiers disabled')
        return D
    opened = not re.search(r'(Unable to open|Error: Cannot read file|cannot read file|not a blend file|File format is not supported)', txt, re.I)
    return {'ok': False, 'opened': True if opened else False, 'error': txt}


# ---------------------------------------------------------------- numpy geometry helpers
def M(D, name, f):
    return np.array(D['mats'][f][name], float)


def xf(m, pts):
    """Transform (N,3) local points by a 4x4 matrix."""
    p = np.asarray(pts, float)
    return p @ m[:3, :3].T + m[:3, 3]


def rot_of(m):
    r = np.array(m, float)[:3, :3].copy()
    for i in range(3):
        n = np.linalg.norm(r[:, i])
        if n > 0:
            r[:, i] /= n
    return r


def rot_angle(r1, r2):
    R = r1.T @ r2
    c = max(-1.0, min(1.0, (np.trace(R) - 1) / 2))
    return math.degrees(math.acos(c))


def cam_forward(m):
    f = -rot_of(m)[:, 2]
    return f / (np.linalg.norm(f) or 1)


def cam_pitch(m):
    """Elevation of the viewing axis in degrees (negative = looking down)."""
    return math.degrees(math.asin(max(-1.0, min(1.0, cam_forward(m)[2]))))


def project(D, cam, f, pts):
    """World points -> (N,3) [u, v, depth] in Blender camera-view convention (u,v in [0,1] inside frame, v up)."""
    m = M(D, cam, f)
    ci = D['cams'][cam][f]
    rx, ry, pct, pax, pay = (D.get('resolution') or [1280, 720, 100, 1, 1])
    W, H = rx * pax, ry * pay
    R = rot_of(m)
    p = (np.asarray(pts, float).reshape(-1, 3) - m[:3, 3]) @ R          # camera-local (x right, y up, -z forward)
    z = -p[:, 2]
    fit = ci.get('fit', 'AUTO')
    horiz = (W >= H) if fit == 'AUTO' else (fit == 'HORIZONTAL')
    if ci.get('type') == 'ORTHO':
        size = ci['ortho']
        sx, sy = (size, size * H / W) if horiz else (size * W / H, size)
        u = 0.5 + p[:, 0] / sx - ci['shx'] * (1 if horiz else H / W)
        v = 0.5 + p[:, 1] / sy - ci['shy'] * (W / H if horiz else 1)
        return np.column_stack([u, v, z])
    sens = ci['sh'] if fit == 'VERTICAL' else ci['sw']
    zz = np.where(np.abs(z) < 1e-9, 1e-9, z)
    if horiz:
        fx = ci['lens'] / sens
        fy = fx * W / H
        u = 0.5 + fx * p[:, 0] / zz - ci['shx']
        v = 0.5 + fy * p[:, 1] / zz - ci['shy'] * W / H
    else:
        fy = ci['lens'] / sens
        fx = fy * H / W
        u = 0.5 + fx * p[:, 0] / zz - ci['shx'] * H / W
        v = 0.5 + fy * p[:, 1] / zz - ci['shy']
    return np.column_stack([u, v, z])


def proj_box(uvz):
    """Clipped 2D bbox [u0,v0,u1,v1] of projected points in front of the camera, area fraction and visibility."""
    q = uvz[uvz[:, 2] > 1e-4]
    if not len(q):
        return None, 0.0, False
    u0, v0, u1, v1 = q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()
    cu0, cv0, cu1, cv1 = max(u0, 0), max(v0, 0), min(u1, 1), min(v1, 1)
    area = max(0.0, cu1 - cu0) * max(0.0, cv1 - cv0)
    return [u0, v0, u1, v1], float(area), bool(cu1 > cu0 and cv1 > cv0)


def seg_point_dist(segs, pts):
    """Min distance from each segment (S,6: head,tail) to a point set (N,3). Returns (S,) array."""
    segs = np.asarray(segs, float).reshape(-1, 6)
    P = np.asarray(pts, float).reshape(-1, 3)
    if not len(segs) or not len(P):
        return np.full(len(segs), np.inf)
    a, b = segs[:, None, :3], segs[:, None, 3:]
    ab = b - a
    t = np.clip(((P[None] - a) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-12), 0, 1)
    c = a + t[..., None] * ab
    return np.sqrt(((P[None] - c) ** 2).sum(-1)).min(1)


def bone_segs(D, rig, f, names=None):
    row = D.get('bones', {}).get(rig, {}).get(f, {})
    ks = [k for k in row if names is None or k in names]
    return ks, np.array([row[k] for k in ks], float).reshape(-1, 6)


SIDE_R = re.compile(r'(\.|_|-|\b)(r|right)(\.|_|-|\d|$)|right|^r_|_r$|\.r$', re.I)
SIDE_L = re.compile(r'(\.|_|-|\b)(l|left)(\.|_|-|\d|$)|left|^l_|_l$|\.l$', re.I)
FINGER_RE = re.compile(r'thumb|index|middle|ring|pinky|little|finger|f_', re.I)
HAND_RE = re.compile(r'hand|palm|wrist', re.I)


def side_of(name):
    n = name.replace('DEF-', '').replace('ORG-', '').replace('MCH-', '')
    r, l = bool(SIDE_R.search(n)), bool(SIDE_L.search(n))
    return 'R' if r and not l else 'L' if l and not r else None


def finger_groups(bones):
    """bones: {name: [parent, deform, length]}. Returns {side: {finger_key: [bone names]}} from name tokens,
    plus topology chains (maximal descending paths of >=3 bones under a hand bone)."""
    out = {'R': {}, 'L': {}}
    for n in bones:
        if not FINGER_RE.search(n) or HAND_RE.search(n) and not FINGER_RE.search(n):
            continue
        s = side_of(n)
        if s is None:
            continue
        base = re.sub(r'^(DEF|ORG|MCH|CTRL|CTL|FK|IK)[-_.]', '', n, flags=re.I)
        tok = FINGER_RE.search(base).group(0).lower()
        m = re.search(r'(thumb|index|middle|ring|pinky|little)', base, re.I)
        key = (m.group(1).lower() if m else tok)
        if key in ('finger', 'f_'):
            m2 = re.search(r'(finger|f_)[_\.]?([a-z]+|\d)', base, re.I)
            key = (m2.group(0).lower() if m2 else base.lower())
        out[s].setdefault(key, []).append(n)
    return out


def chains_under(bones, root):
    kids = {}
    for n, (p, _, _) in bones.items():
        kids.setdefault(p, []).append(n)
    paths = []

    def walk(n, path):
        ch = kids.get(n, [])
        if not ch:
            paths.append(path)
        for c in ch:
            walk(c, path + [c])
    for c in kids.get(root, []):
        walk(c, [c])
    return paths
