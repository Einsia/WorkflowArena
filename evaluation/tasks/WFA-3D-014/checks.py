# -*- coding: utf-8 -*-
"""CDC-C-X04 Night Shift / Rack C -- deterministic checks for rubric_score.py (rewritten 2026-10-25).

Every scored item is decided here except the visual remainders of M13 / G08 (returned by checks only when their measured
part fails) and G10 (narrative readability from the contact sheets, judge only). See review/rubric-cleanup-20261025.md.
Film frame f is measured at Blender scene frame frame_start + f. An exception inside an item => fail with the reason.
Blender: one short static inspection (B04) + one per-frame inspection (all frame-mapped items) + <=6 tiny re-renders.
"""
import csv, json, math, os, pathlib, re, shutil, subprocess, sys, time, traceback
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import _cdc_blend as B

FPS, NFR, W, H = 30, 900, 1280, 720
DUR = NFR / FPS
SR = 48000
STEMS = ['speech', 'fx', 'amb']
LUFS, LUFS_TOL = -20.0, 2.0
EVENTS = ['upright_contact', 'forklift_stop', 'pallet_tip', 'first_box_release', 'first_floor_hit', 'last_box_rest',
          'picker_behind_line', 'radio_raise', 'line_dispatch_start', 'line_dispatch_end', 'line_picker_start', 'line_picker_end']
BOXES = [f'BOX_{i:02d}' for i in range(1, 13)]
UPRIGHTS = [f'UPRIGHT_C{i}' for i in range(1, 6)]
CAMS = ['CAM_S1', 'CAM_S2', 'CAM_S3', 'CAM_S4']
REQ_OBJ = ['DRIVER', 'PICKER', 'DRIVER_RIG', 'PICKER_RIG', 'FORKLIFT', 'RACK_C'] + UPRIGHTS + \
          ['PALLET_TOP'] + BOXES + ['CART', 'RADIO', 'SAFETY_LINE'] + CAMS
CUTS_BASE = [180, 330, 540, 720]
CUTS_REV = [180, 320, 540, 720]
SHOTS = {'S1': (0, 179), 'S2': (180, 329), 'S3': (330, 539), 'S4': (540, 719), 'S5': (720, 899)}
SHOT_CAM = {'S1': 'CAM_S1', 'S2': 'CAM_S2', 'S3': 'CAM_S3', 'S4': 'CAM_S4', 'S5': 'CAM_S1'}
SCENE = {'carton': [0.4, 0.4, 0.6], 'pallet': [0.144, 0.8, 1.2], 'beam_top': 4.5, 'upright_x': [0.0, 2.8, 5.6, 8.4, 11.2],
         'guard': 2.15, 'PICKER': 1.65, 'DRIVER': 1.78, 'line_x': 17.0}
TRACK = BOXES + ['PALLET_TOP', 'FORKLIFT', 'RADIO', 'RACK_C', 'SAFETY_LINE', 'CART', 'PICKER', 'DRIVER',
                 'PICKER_RIG', 'DRIVER_RIG'] + UPRIGHTS + CAMS
BONE_RE = r'hand|palm|wrist|finger|thumb|index|middle|ring|pinky|little|f_|head|neck|spine|chest|pelvis|hips|hip|root|torso|foot|toe|heel|ankle'
HANDISH = re.compile(r'hand|palm|wrist|thumb|index|middle|ring|pinky|little|finger|f_', re.I)
BUDGET_S = 2700          # no new Blender job is started after this many seconds of checks (verifier timeout 3600 s)
RENDER_W, RENDER_H, RENDER_SPP = 480, 270, 8
SUPPORT_TOL = 0.05       # support contact distance: 1 cm + Bullet's default 4 cm collision margin of mesh/convex shapes
STATE = {}


class _DumpFail(Exception):
    pass


class _GraderError(Exception):
    """verifier-environment problem: propagates out of run() so that no reward is written"""
    pass


# ---------------------------------------------------------------- Blender-side measurements (run inside the dump)
EXTRA = r'''
import math
BOXES = ["BOX_%02d" % i for i in range(1, 13)]
UPR = ["UPRIGHT_C%d" % i for i in range(1, 6)]
DEFORM = {"ARMATURE", "CLOTH", "SOFT_BODY", "HOOK", "LATTICE", "MESH_DEFORM", "SURFACE_DEFORM", "WAVE", "DISPLACE",
          "SIMPLE_DEFORM", "NODES", "SHRINKWRAP", "CAST", "SMOOTH", "LAPLACIANDEFORM", "CORRECTIVE_SMOOTH"}
def r5(x):
    return round(float(x), 5)
def _family(bpy, name, skip_chars=True):
    o = bpy.data.objects.get(name)
    if o is None:
        return []
    out = [o] + list(o.children_recursive)
    res = []
    for q in out:
        if q.type not in ("MESH", "CURVE", "SURFACE", "META", "FONT"):
            continue
        if skip_chars and (q.name in ("DRIVER", "PICKER", "RADIO") or any(m.type == "ARMATURE" for m in q.modifiers)):
            continue
        if q.name in BOXES and name not in BOXES:
            continue
        res.append(q)
    return res
def _world_mesh(o, dg):
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    try:
        mw = oe.matrix_world.copy()
        V = [mw @ v.co for v in me.vertices]
        P = [tuple(p.vertices) for p in me.polygons]
        N = [(mw.to_3x3() @ p.normal).normalized() for p in me.polygons]
        C = [mw @ p.center for p in me.polygons]
    finally:
        oe.to_mesh_clear()
    return V, P, N, C
def _deforming(o):
    return any(m.type in DEFORM for m in getattr(o, "modifiers", [])) or bool(getattr(getattr(o, "data", None), "shape_keys", None))
def _bvh(ctx, key, objs):
    from mathutils.bvhtree import BVHTree
    dg = ctx["dg"]
    sig = tuple((o.name, tuple(round(v, 6) for row in o.matrix_world for v in row)) for o in objs)
    if any(_deforming(o) for o in objs):
        sig = (sig, ctx["scene_frame"])
    cache = ctx.setdefault("_bvh", {})
    if key in cache and cache[key][0] == sig:
        return cache[key][1]
    V, P = [], []
    for o in objs:
        try:
            v, p, n, c = _world_mesh(o, dg)
        except Exception:
            continue
        off = len(V); V += v; P += [tuple(off + i for i in q) for q in p]
    t = BVHTree.FromPolygons(V, P) if P else None
    cache[key] = (sig, t)
    return t
def _inside(bvh, p):
    from mathutils import Vector
    loc, nor, idx, dist = bvh.find_nearest(p)
    if loc is None or (p - loc).dot(nor) >= 0:
        return 0.0
    for d in (Vector((0, 0, 1)), Vector((0, 0, -1))):
        n, q = 0, p.copy()
        for _ in range(40):
            h = bvh.ray_cast(q, d, 1000.0)
            if h[0] is None:
                break
            n += 1; q = h[0] + d * 1e-4
        if n % 2 == 0:
            return 0.0
    return dist
def _edge_local(o, dg, step=0.02, cap=80000):
    oe = o.evaluated_get(dg); me = oe.to_mesh()
    try:
        pts = [v.co.copy() for v in me.vertices]
        for e in me.edges:
            a, b = me.vertices[e.vertices[0]].co, me.vertices[e.vertices[1]].co
            k = int((b - a).length / step)
            if k > 1:
                pts += [a.lerp(b, i / k) for i in range(1, k)]
            if len(pts) > cap:
                break
    finally:
        oe.to_mesh_clear()
    return pts
def _tpts(ctx, objs):
    """World-space edge samples of the support objects (pure mathutils: this code runs inside `blender -b`, whose
    Python 3.13 has no numpy in the verifier image)."""
    cache = ctx.setdefault("_tl", {})
    out = []
    for o in objs:
        if o.name not in cache:
            try:
                cache[o.name] = _edge_local(o, ctx["dg"])
            except Exception:
                cache[o.name] = []
        M = o.matrix_world
        out += [M @ p for p in cache[o.name]]
    return out
def _box_side(ctx, n, tp, margin):
    """(box BVH, target points near the box) for reverse-direction distance / penetration tests"""
    from mathutils.bvhtree import BVHTree
    V, P_, N_, C_ = _world_mesh(ctx["bpy"].data.objects[n], ctx["dg"])
    if not P_ or not tp:
        return None, []
    lo = [min(v[i] for v in V) - margin for i in range(3)]
    hi = [max(v[i] for v in V) + margin for i in range(3)]
    sel = [p for p in tp if all(lo[i] <= p[i] <= hi[i] for i in range(3))]
    return BVHTree.FromPolygons(V, P_), sel
def setup(ctx):
    bpy, D, cfg = ctx["bpy"], ctx["D"], ctx["cfg"]
    from mathutils import Vector
    X = D["x04"] = {"cam": {}, "kin": {}, "sup": {}, "pen": {}, "fu": {}, "sway": {}, "static": {}}
    C = cfg.get("x04", {})
    ctx["_sets"] = {k: set(C.get(k, [])) for k in ("sup_frames", "pen_frames", "contact_frames", "sway_frames")}
    dg = bpy.context.evaluated_depsgraph_get()
    loc = {}
    for n in BOXES:
        o = bpy.data.objects.get(n)
        if o is None or o.type != "MESH":
            continue
        oe = o.evaluated_get(dg); me = oe.to_mesh()
        try:
            vs = [v.co.copy() for v in me.vertices]
            pts = vs[:: max(1, len(vs) // 200)]
            ed = []
            for e in me.edges:
                a, b = me.vertices[e.vertices[0]].co, me.vertices[e.vertices[1]].co
                k = max(1, int((b - a).length / 0.04))
                ed += [a.lerp(b, i / k) for i in range(1, k)]
            pts += ed[:: max(1, len(ed) // 300)]
            pc = [p.center.copy() for p in me.polygons]
            pts += pc[:: max(1, len(pc) // 100)]
        finally:
            oe.to_mesh_clear()
        loc[n] = pts
    ctx["box_local"] = loc
    X["static"]["box_samples"] = {n: len(v) for n, v in loc.items()}
    se = ctx["sc"].sequence_editor
    X["static"]["scene_strips"] = len([s for s in (se.sequences_all if se else []) if s.type == "SCENE"])
def _static(ctx):
    bpy, D, sc, dg = ctx["bpy"], ctx["D"], ctx["sc"], ctx["dg"]
    S = D["x04"]["static"]
    # rack: up-facing polygon centres (beam tops) in world z
    zs = []
    for o in _family(bpy, "RACK_C"):
        try:
            V, P, N, Cc = _world_mesh(o, dg)
        except Exception:
            continue
        zs += [c.z for c, nn in zip(Cc, N) if nn.z > 0.9]
    S["rack_up_z"] = sorted(set(round(z, 3) for z in zs))[:400]
    ux = {}
    for n in UPR:
        fam = _family(bpy, n)
        xs = []
        for o in fam:
            try:
                xs += [v.x for v in _world_mesh(o, dg)[0]]
            except Exception:
                pass
        if xs:
            ux[n] = [r5(min(xs)), r5(max(xs))]
    S["upright_x"] = ux
    zf = []
    for o in _family(bpy, "FORKLIFT"):
        try:
            zf += [v.z for v in _world_mesh(o, dg)[0]]
        except Exception:
            pass
    S["forklift_top"] = r5(max(zf)) if zf else None
    dims, cl = {}, []
    car = sorted([0.4, 0.4, 0.6])
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        d = sorted(o.dimensions)
        if o.name in BOXES or o.name == "PALLET_TOP":
            dims[o.name] = [r5(v) for v in d]
        elif all(abs(a - b) <= 0.05 * b for a, b in zip(d, car)):
            cl.append(o.name)
    S["dims"] = dims; S["carton_like"] = cl[:200]
    hts = {}
    for ch, rig in (("PICKER", "PICKER_RIG"), ("DRIVER", "DRIVER_RIG")):
        a = bpy.data.objects.get(rig); m = bpy.data.objects.get(ch)
        e = {}
        if a is not None and a.type == "ARMATURE":
            old = a.data.pose_position
            try:
                a.data.pose_position = "REST"
                bpy.context.view_layer.update()
                dg2 = bpy.context.evaluated_depsgraph_get()
                mw = a.matrix_world
                z = [(mw @ b.head_local).z for b in a.data.bones] + [(mw @ b.tail_local).z for b in a.data.bones]
                if z:
                    e["rig_rest_extent"] = r5(max(z) - min(z))
                if m is not None and m.type == "MESH":
                    vz = [v.z for v in _world_mesh(m, dg2)[0]]
                    if vz:
                        e["mesh_rest_extent"] = r5(max(vz) - min(vz))
            finally:
                a.data.pose_position = old
                bpy.context.view_layer.update()
        hts[ch] = e
    S["heights"] = hts
def frame(ctx, f):
    bpy, D, cfg, dg, sc = ctx["bpy"], ctx["D"], ctx["cfg"], ctx["dg"], ctx["sc"]
    from mathutils import Vector
    X = D["x04"]; C = cfg.get("x04", {}); S = ctx["_sets"]; OB = bpy.data.objects
    if "static_done" not in ctx:
        ctx["static_done"] = True
        try:
            _static(ctx)
        except Exception as ex:
            X["static"]["error"] = repr(ex)[:300]
            dg = ctx["dg"] = bpy.context.evaluated_depsgraph_get()
        if sc.frame_current != ctx["scene_frame"]:
            sc.frame_set(ctx["scene_frame"])
        dg = ctx["dg"] = bpy.context.evaluated_depsgraph_get()
    X["cam"][f] = sc.camera.name if sc.camera else None
    kin = [n for n in BOXES if OB.get(n) is not None and OB[n].rigid_body and OB[n].rigid_body.kinematic]
    if kin:
        X["kin"][f] = kin
    bl = ctx.get("box_local", {})
    if f in S["sup_frames"] or f in S["pen_frames"]:
        pts = {n: [OB[n].matrix_world @ p for p in v] for n, v in bl.items()}
        if f in S["sup_frames"]:
            objs = list({o.name: o for o in _family(bpy, "PALLET_TOP") + _family(bpy, "RACK_C") + sum((_family(bpy, u) for u in UPR), [])}.values())
            t = _bvh(ctx, "sup", objs)
            tp = _tpts(ctx, objs)
            if t is not None:
                row = {}
                for n, ps in pts.items():
                    if not ps:
                        continue
                    dmin = min(t.find_nearest(p)[3] for p in ps)          # box samples -> support surfaces
                    bb, sel = _box_side(ctx, n, tp, 0.03)
                    if bb is not None and len(sel):                        # support edges/vertices -> box faces
                        dmin = min(dmin, min(bb.find_nearest(Vector(tuple(q)))[3] for q in sel))
                    row[n] = r5(dmin)
                X["sup"][f] = row
        if f in S["pen_frames"]:
            objs = list({o.name: o for o in _family(bpy, "RACK_C") + sum((_family(bpy, u) for u in UPR), []) + _family(bpy, "FORKLIFT")}.values())
            t = _bvh(ctx, "pen", objs)
            tp = _tpts(ctx, objs)
            if t is not None:
                row = {}
                for n, ps in pts.items():
                    if not ps:
                        continue
                    dep = max([0.0] + [_inside(t, p) for p in ps])
                    bb, sel = _box_side(ctx, n, tp, 0.0)
                    if bb is not None and len(sel):
                        dep = max([dep] + [_inside(bb, Vector(tuple(q))) for q in sel])
                    row[n] = r5(dep)
                X["pen"][f] = row
    if f in S["contact_frames"]:
        fk = []
        for o in _family(bpy, "FORKLIFT"):
            try:
                fk += _world_mesh(o, dg)[0]
            except Exception:
                pass
        fk = fk[:: max(1, len(fk) // 6000)]
        tf = _bvh(ctx, "fork_%d" % f, _family(bpy, "FORKLIFT"))
        row = {}
        for u in UPR:
            fam = _family(bpy, u)
            tu = _bvh(ctx, "upr_" + u, fam)
            if tu is None:
                continue
            d = min([tu.find_nearest(p)[3] for p in fk] or [1e9])
            if tf is not None:
                uv = []
                for o in fam:
                    uv += _world_mesh(o, dg)[0]
                d = min([d] + [tf.find_nearest(p)[3] for p in uv[:: max(1, len(uv) // 3000)]])
            row[u] = r5(d)
        X["fu"][f] = row
    if f in S["sway_frames"]:
        row = {}
        for u in UPR + ["RACK_C"]:
            vv = []
            for o in _family(bpy, u):
                try:
                    vv += _world_mesh(o, dg)[0]
                except Exception:
                    pass
            if vv:
                st = ctx.setdefault("_sway_step", {}).setdefault(u, max(1, len(vv) // 150))
                row[u] = [[r5(p.x), r5(p.y), r5(p.z)] for p in vv[::st]]
        X["sway"][f] = row
    if f == C.get("last") and C.get("roll_frames"):
        k = "roll_T23_frames"
        if k in sc.keys():
            old = sc[k]
            try:
                sc[k] = -10
                R = {}
                for g in C["roll_frames"]:
                    sc.frame_set(D["frame_offset"] + g)
                    R[g] = {n: [[r5(v) for v in row] for row in OB[n].matrix_world] for n in C.get("roll_track", []) if n in OB}
                X["roll"] = R
            finally:
                sc[k] = old
                sc.frame_set(D["frame_offset"] + f)
        else:
            X["roll_missing"] = True
'''

RENDER_PY = r'''
import bpy, sys
argv = sys.argv[sys.argv.index("--") + 1:]
sf = int(argv[0]); out = argv[1]; roll = int(argv[2]); cam = argv[3]
W, H, spp, force_cycles = int(argv[4]), int(argv[5]), int(argv[6]), argv[7] == "1"
if getattr(bpy.app, "autoexec_fail", False):
    for _t in bpy.data.texts:
        if _t.use_module:
            try:
                exec(compile(_t.as_string(), _t.name, "exec"), {"__name__": _t.name})
            except Exception as _e:
                print("autoexec emulation failed for", _t.name, _e)
sc = bpy.context.scene
if "roll_T23_frames" in sc.keys():
    sc["roll_T23_frames"] = roll
for m in sc.timeline_markers:
    m.camera = None
if cam in bpy.data.objects:
    sc.camera = bpy.data.objects[cam]
sc.frame_set(sf)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
if force_cycles:
    sc.render.engine = "CYCLES"
if sc.render.engine == "CYCLES":
    sc.cycles.samples = spp
    try:
        import _cycles   # Debian's Blender 4.3.2 has no OpenImageDenoise: enabling denoise there aborts the render
        sc.cycles.use_denoising = bool(getattr(_cycles, "with_openimagedenoise", True))
    except Exception: pass
    try: sc.cycles.device = "CPU"
    except Exception: pass
elif hasattr(sc, "eevee"):
    try: sc.eevee.taa_render_samples = spp
    except Exception: pass
sc.render.use_compositing = False
sc.render.use_sequencer = False
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("RENDER_OK")
'''


# ---------------------------------------------------------------- generic helpers
def _sh(cmd, timeout=600, err=False):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.stderr if err else p.stdout
    except Exception as e:
        return f'<error {e}>'


def P(v, d):
    return {'verdict': 'pass' if v else 'fail', 'detail': str(d)[:900]}


def F(d):
    return {'verdict': 'fail', 'detail': str(d)[:900]}


def vprobe(p):
    o = _sh(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', str(p)], 600)
    try:
        return json.loads(o)
    except Exception:
        return {}


def video_contract(p):
    if not p.exists():
        return False, f'{p.name} missing'
    j = vprobe(p)
    vs = [s for s in j.get('streams', []) if s.get('codec_type') == 'video']
    if not vs:
        return False, 'no video stream'
    v = vs[0]
    sar = v.get('sample_aspect_ratio') or '1:1'
    got = dict(codec=v.get('codec_name'), pix=v.get('pix_fmt'), w=v.get('width'), h=v.get('height'), sar=sar,
               r=v.get('r_frame_rate'), avg=v.get('avg_frame_rate'), n=v.get('nb_read_frames'))
    ok = (got['codec'] == 'h264' and got['pix'] == 'yuv420p' and got['w'] == W and got['h'] == H
          and sar in ('1:1', '0:1', 'N/A') and got['r'] == f'{FPS}/1' and got['avg'] == f'{FPS}/1'
          and str(got['n']) == str(NFR))
    return ok, got


def audio_contract(p):
    j = vprobe(p)
    a = [s for s in j.get('streams', []) if s.get('codec_type') == 'audio']
    if not a:
        return False, 'no audio stream'
    a = a[0]
    try:
        ad = float(a.get('duration') or j['format']['duration'])
    except Exception:
        ad = -1
    ok = a.get('codec_name') == 'aac' and int(a.get('channels') or 0) == 2 and str(a.get('sample_rate')) == str(SR) \
        and ad >= DUR - 1.0 / FPS - 1e-3
    return ok, dict(codec=a.get('codec_name'), ch=a.get('channels'), sr=a.get('sample_rate'), dur=ad)


def decode_audio(p, mono=True):
    cmd = ['ffmpeg', '-v', 'error', '-i', str(p), '-vn', '-f', 'f32le', '-acodec', 'pcm_f32le', '-ar', str(SR)]
    cmd += ['-ac', '1'] if mono else []
    cmd += ['-']
    r = subprocess.run(cmd, capture_output=True, timeout=300)
    x = np.frombuffer(r.stdout, dtype=np.float32)
    if not mono:
        x = x[:len(x) // 2 * 2].reshape(-1, 2)
    return x.astype(np.float64)


def stem_info(p):
    j = json.loads(_sh(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(p)], 60) or '{}')
    a = [s for s in j.get('streams', []) if s.get('codec_type') == 'audio']
    if not a:
        return dict(codec=None, sr=None, dur=-1)
    a = a[0]
    return dict(codec=a.get('codec_name'), sr=a.get('sample_rate'), dur=float(a.get('duration') or j['format']['duration']))


def loud(p):
    o = _sh(['ffmpeg', '-hide_banner', '-nostats', '-i', str(p), '-af', 'ebur128=peak=true', '-f', 'null', '-'], 600, err=True)
    i = re.findall(r'I:\s+(-?[\d.]+) LUFS', o)
    pk = re.findall(r'Peak:\s+(-?[\d.inf]+) dBFS', o)
    return (float(i[-1]) if i else None), (float(pk[-1]) if pk else None)


def clip_run(x, n=3):
    m = (np.abs(x) >= 0.999)
    if m.ndim > 1:
        m = m.any(axis=1)
    if not m.any():
        return 0
    d = np.diff(np.concatenate([[0], m.astype(np.int8), [0]]))
    s, e = np.where(d == 1)[0], np.where(d == -1)[0]
    return int((e - s).max())


def read_json(p):
    try:
        return json.loads(p.read_text(encoding='utf-8-sig'))
    except Exception:
        return None


def read_events(p):
    """-> (header_ok, {id: frame}, problems)"""
    txt = p.read_text(encoding='utf-8-sig')
    rows = list(csv.reader(txt.splitlines()))
    if not rows:
        return False, {}, ['empty']
    hdr = [c.strip() for c in rows[0]]
    ev, prob = {}, []
    for r in rows[1:]:
        if not r or not ''.join(r).strip():
            continue
        k = r[0].strip()
        try:
            fv = float(r[1])
            if fv != int(fv):
                prob.append(f'{k} non-integer frame {r[1]}')
            ev.setdefault(k, int(fv))
        except Exception:
            prob.append(f'{k} bad frame {r[1:2]}')
    return hdr == ['event_id', 'frame', 'description'], ev, prob


def find_gains(tl, names):
    """search timeline.json for per-stem gains; returns list of candidate dicts {stem: linear}"""
    found = []

    def num(v):
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v), None
        if isinstance(v, dict):
            for k, x in v.items():
                if isinstance(x, (int, float)) and not isinstance(x, bool) and re.search(r'gain|db|level', k, re.I):
                    return float(x), ('db' if re.search(r'db', k, re.I) else 'lin' if re.search(r'lin', k, re.I) else None)
        return None, None

    def walk(o, ctxdb=None):
        if isinstance(o, dict):
            keys = {re.sub(r'\.wav$', '', str(k).split('/')[-1]).lower(): v for k, v in o.items()}
            if all(n in keys for n in names):
                vals = {n: num(keys[n]) for n in names}
                if all(v[0] is not None for v in vals.values()):
                    found.append((vals, ctxdb))
            for k, v in o.items():
                walk(v, 'db' if re.search(r'db', str(k), re.I) else ('lin' if re.search(r'lin', str(k), re.I) else ctxdb))
        elif isinstance(o, list):
            d = {}
            for it in o:
                if isinstance(it, dict):
                    nm = next((str(it[k]) for k in ('stem', 'name', 'id', 'file', 'track') if k in it), None)
                    if nm:
                        nm = re.sub(r'\.wav$', '', nm.split('/')[-1]).lower()
                        v = num(it)
                        if v[0] is not None:
                            d[nm] = v
            if all(n in d for n in names):
                found.append(({n: d[n] for n in names}, ctxdb))
            for it in o:
                walk(it, ctxdb)
    walk(tl)
    cands = []
    for vals, ctxdb in found:
        hint = {u for _, u in vals.values() if u} or ({ctxdb} if ctxdb else set())
        if hint != {'lin'}:
            cands.append({n: 10 ** (v[0] / 20) for n, v in vals.items()})
        if hint != {'db'}:
            cands.append({n: v[0] for n, v in vals.items()})
    return cands


def band_db(x):
    fr = 4800
    n = len(x) // fr
    if n < 5:
        return None
    X = np.abs(np.fft.rfft(x[:n * fr].reshape(n, fr) * np.hanning(fr), axis=1)) ** 2
    f = np.fft.rfftfreq(fr, 1 / SR)
    cs = [1000 * 2 ** (k / 3) for k in range(-13, 12)]
    cs = [c for c in cs if 45 <= c <= 14500]
    Bd = np.stack([X[:, (f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))].sum(1) for c in cs], 1)
    return 10 * np.log10(Bd + 1e-20)


def align(ref, x, maxlag=2048):
    n = min(len(ref), len(x), SR * 10)
    a, b = ref[SR:SR + n - SR], x[SR:SR + n - SR]
    if len(a) < 4096:
        return 0
    A = np.fft.rfft(a, 2 * len(a))
    Bf = np.fft.rfft(b, 2 * len(a))
    c = np.fft.irfft(A * np.conj(Bf))
    lags = np.concatenate([np.arange(0, maxlag + 1), np.arange(-maxlag, 0)])
    vals = np.concatenate([c[:maxlag + 1], c[-maxlag:]])
    return int(lags[int(np.argmax(vals))])


def band_compare(mix, summ):
    lag = align(mix, summ)
    if lag > 0:
        mix = mix[lag:]
    elif lag < 0:
        summ = summ[-lag:]
    n = min(len(mix), len(summ))
    A, Bb = band_db(mix[:n]), band_db(summ[:n])
    if A is None:
        return None
    mask = (A >= A.max(1, keepdims=True) - 40) & (A.max(1, keepdims=True) > -80)
    d = np.abs(A - Bb)[mask]
    if d.size == 0:
        return None
    return dict(lag=lag, median=float(np.median(d)), p95=float(np.percentile(d, 95)))


def rms_env(x, win):
    n = len(x) // win
    return 20 * np.log10(np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(1)) + 1e-12)


def fft_band(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def gray_frames(p, w=320):
    h = int(round(H * w / W / 2)) * 2
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                       capture_output=True, timeout=900)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    n = len(a) // (w * h)
    return a[:n * w * h].reshape(n, h, w).astype(np.float32)


def psnr(a, b):
    m = float(((a.astype(np.float64) - b) ** 2).mean())
    return 99.0 if m <= 1e-10 else 10 * math.log10(255 ** 2 / m)


def detect_cuts(fr):
    """Hard cuts on gray frames (index c = first frame of the new shot) and the frame-difference series."""
    f = fr.astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    hs = np.stack([np.histogram(x, 32, (0, 256))[0] for x in fr]).astype(np.float32)
    hs /= np.maximum(hs.sum(1, keepdims=True), 1)
    hd = 0.5 * np.abs(np.diff(hs, axis=0)).sum(1)
    med = float(np.median(d)) if d.size else 0
    thr = max(12.0, 6 * med)
    nbm = lambda i: max(d[i - 1] if i > 0 else 0, d[i + 1] if i + 1 < len(d) else 0)
    # a cut is an isolated spike of the frame difference (fast motion gives runs of similar large differences)
    cuts = [i + 1 for i in range(len(d)) if ((d[i] > thr) and (d[i] >= 3 * nbm(i)))
            or (hd[i] > 0.5 and d[i] > max(8.0, 4 * med) and d[i] >= 2 * nbm(i))]
    return sorted(set(cuts)), d


def hard_cut_ok(d, c):
    i = c - 1
    nb = [d[j] for j in (i - 2, i - 1, i + 1, i + 2) if 0 <= j < len(d)]
    return all(x < 0.35 * d[i] for x in nb)


def freeze_runs(p, min_run=8, w=1280, h=720, tol=2):
    """Runs of >= min_run consecutive decoded frames identical up to codec rounding (no full-resolution luma pixel
    changes by more than `tol` levels; an H.264-encoded duplicate frame differs by <= 2) (streamed): [(start, n)]."""
    proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:v:0', '-vf', f'scale={w}:{h},format=gray',
                             '-vsync', '0', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
    n = w * h
    prev, k, run, start, out = None, 0, 1, 0, []
    try:
        while True:
            buf = proc.stdout.read(n)
            if len(buf) < n:
                break
            if prev is not None and (buf == prev or int(np.abs(np.frombuffer(buf, np.uint8).astype(np.int16) - np.frombuffer(prev, np.uint8)).max()) <= tol):
                run += 1
            else:
                if run >= min_run:
                    out.append((start, run))
                run, start = 1, k
            prev, k = buf, k + 1
        if run >= min_run:
            out.append((start, run))
    finally:
        proc.stdout.close()
        proc.wait(timeout=60)
    return out


def frame_at(p, f, w=640, h=360):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f"select='eq(n\\,{f})',scale={w}:{h}:flags=area,format=gray",
                        '-vsync', '0', '-frames:v', '1', '-f', 'rawvideo', '-'], capture_output=True, timeout=300)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    if a.size < w * h:
        raise RuntimeError(f'frame {f} of {p.name} not decodable')
    return a[:w * h].reshape(h, w)


def ssim(a, b):
    import cv2
    a = a.astype(np.float64); b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    ma, mb = g(a), g(b)
    va, vb, cab = g(a * a) - ma ** 2, g(b * b) - mb ** 2, g(a * b) - ma * mb
    s = ((2 * ma * mb + C1) * (2 * cab + C2)) / ((ma ** 2 + mb ** 2 + C1) * (va + vb + C2))
    return float(s.mean())


def ssim_render(a, b, sigma=2.0):
    """SSIM between a verifier re-render and a delivered frame after a Gaussian blur (sigma 2 px at 480x270) of both:
    the re-render is 8 spp and, in the verifier image (Debian Blender 4.3.2, no OpenImageDenoise), not denoised, so raw
    SSIM mostly measures path-tracing noise; after the blur an identical scene scores >= 0.99 while a different shot or
    framing stays far below."""
    import cv2
    g = lambda x: cv2.GaussianBlur(np.asarray(x, np.float64), (0, 0), sigma)
    return ssim(g(a), g(b))

def flat_block_index(g):
    """Share of 8x8 luma blocks that are flat (variance < 1) AND equal in mean (< 0.5) to all 4 neighbours (posterised /
    flat-shaded regions; gradients and bokeh are not counted). Blocks with mean < 24 or > 235 are excluded."""
    h, w = g.shape
    hb, wb = h // 8, w // 8
    b = g[:hb * 8, :wb * 8].astype(np.float64).reshape(hb, 8, wb, 8).transpose(0, 2, 1, 3).reshape(hb, wb, 64)
    m, v = b.mean(2), b.var(2)
    keep = (m >= 24) & (m <= 235)
    nb = np.zeros_like(m)
    for sh, ax in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
        nb = np.maximum(nb, np.abs(m - np.roll(m, sh, ax)))
    flat = (v < 1.0) & (nb < 0.5) & keep
    flat[0, :] = flat[-1, :] = False
    flat[:, 0] = flat[:, -1] = False
    return float(flat.sum() / max(keep[1:-1, 1:-1].sum(), 1))


def blend_render(blend, sf, tmp, roll, cam, timeout=240):
    """Render scene frame sf through camera `cam` (marker bindings cleared) at 480x270, 8 spp. Solver engine first;
    retried once with Cycles if no image was written. -> (gray uint8 array or None, note)."""
    import cv2
    tmp = pathlib.Path(tmp)
    s = tmp / 'x04_render.py'
    s.write_text(RENDER_PY)
    note = []
    for force in ('0', '1'):
        o = tmp / f'x04_render_{roll}_{sf}_{cam}_{force}.png'
        try:
            subprocess.run(['blender', '-b', '-y', str(blend), '--python', str(s), '--', str(sf), str(o), str(roll), cam,
                            str(RENDER_W), str(RENDER_H), str(RENDER_SPP), force], capture_output=True, timeout=timeout)
        except Exception as e:
            note.append(f'render {"cycles " if force == "1" else ""}error/timeout: {type(e).__name__}')
            if force == '0':
                continue
            return None, '; '.join(note)
        if o.exists():
            g = cv2.imread(str(o), cv2.IMREAD_GRAYSCALE)
            if g is not None:
                if force == '1':
                    note.append('solver engine produced no image; re-rendered with Cycles')
                return cv2.resize(g, (RENDER_W, RENDER_H), interpolation=cv2.INTER_AREA), '; '.join(note)
        note.append('no image written' + (' (cycles retry)' if force == '1' else ''))
    return None, '; '.join(note)


def segments(act, step, gap):
    idx = np.where(act)[0]
    if not idx.size:
        return []
    segs, s0 = [], idx[0]
    for a, b in zip(idx[:-1], idx[1:]):
        if (b - a) * step > gap:
            segs.append((float(s0 * step), float((a + 1) * step))); s0 = b
    segs.append((float(s0 * step), float((idx[-1] + 1) * step)))
    return segs


def band_ratio(x, a, b, bands):
    y = x[int(a * SR):int(b * SR)]
    if len(y) < 2048:
        return None
    fr = 2048
    n = len(y) // fr
    Y = (np.abs(np.fft.rfft(y[:n * fr].reshape(n, fr) * np.hanning(fr), axis=1)) ** 2).mean(0)
    f = np.fft.rfftfreq(fr, 1 / SR)
    return [10 * math.log10(Y[(f >= lo) & (f < hi)].sum() + 1e-20) for lo, hi in bands]


def beeper(x, uc_t=None):
    """Reverse-alarm analysis of the fx stem. Peak frequency = strongest 500-3000 Hz bin of the mean spectrum over
    3.0-6.0 s; band-pass +-15 %; 10 ms RMS envelope; onsets = rising crossings of the mid level between the 10th and
    95th percentile (3-8 s) with an 80 ms refractory period, kept only if >= 20 % of the 300-8000 Hz energy in the
    50 ms after the onset lies in the beeper band (rejects broadband impacts)."""
    seg = x[int(3.0 * SR):int(6.0 * SR)]
    if len(seg) < 8192:
        return None, 'fx stem shorter than 6 s'
    n = 8192
    fr = seg[:len(seg) // n * n].reshape(-1, n)
    S = (np.abs(np.fft.rfft(fr * np.hanning(n), axis=1)) ** 2).mean(0)
    f = np.fft.rfftfreq(n, 1 / SR)
    band = (f >= 500) & (f <= 3000)
    k = np.where(band)[0][int(np.argmax(S[band]))]
    fpk = float(f[k])
    prom = 10 * math.log10(S[k] / max(float(np.median(S[band])), 1e-30))
    Xf = np.fft.rfft(x); ff = np.fft.rfftfreq(len(x), 1 / SR)
    r = np.abs(ff - fpk) / fpk
    Xf *= np.where(r <= 0.08, 1.0, np.where(r <= 0.15, 0.5 + 0.5 * np.cos(np.pi * (r - 0.08) / 0.07), 0.0))   # +-15 %, cosine-tapered
    bp = np.fft.irfft(Xf, len(x))
    wide = fft_band(x, 300, 8000)
    win = int(0.01 * SR)
    env = rms_env(bp, win)
    w38 = env[300:800]
    lo, hi = float(np.percentile(w38, 10)), float(np.percentile(w38, 95))
    thr = (lo + hi) / 2
    on, last, armed = [], -1e9, True
    for i in range(1, len(env)):
        if env[i] < thr - 3:
            armed = True                     # hysteresis: re-arm only after the envelope fell 3 dB below the threshold
        if armed and env[i - 1] < thr <= env[i] and (i - last) * 0.01 >= 0.08 and env[i:i + 5].max() >= thr + 6:
            armed = False
            a = i * win
            eb = float((bp[a:a + int(0.05 * SR)] ** 2).sum()); ew = float((wide[a:a + int(0.05 * SR)] ** 2).sum())
            if ew > 0 and eb / ew >= 0.2:
                w1 = int(0.001 * SR); s0 = max(0, a - int(0.03 * SR))
                e1 = rms_env(bp[s0:a + int(0.05 * SR)], w1)
                j = int(np.argmax(e1 >= e1.max() - 12)) if len(e1) else int(0.03 * SR / w1)
                on.append(round((s0 + j * w1) / SR, 4)); last = i      # refined to 1 ms: first ms within 12 dB of the beep peak
    return dict(fpk=fpk, prom=prom, contrast=hi - lo, onsets=on, bp=bp), ''


# ---------------------------------------------------------------- run
def run(ctx):
    R = {}
    t_start = time.time()
    out = ctx['out']
    base, rev, proj = out / 'base', out / 'revision', out / 'project'
    bmp, rmp = base / 'output.mp4', rev / 'output.mp4'
    tmp = pathlib.Path(ctx['tmp'])
    blend = proj / 'scene.blend'
    STATE.clear()

    def item(iid, fn):
        try:
            v = fn()
            if v is not None:
                R[iid] = v
        except _DumpFail as e:
            R[iid] = F(str(e))
        except _GraderError:
            raise
        except Exception as e:
            R[iid] = F(f'check error: {type(e).__name__}: {e} | {traceback.format_exc()[-300:]}')

    # ---------- B01 / B02 / B03 ----------
    def b01():
        if not bmp.exists():
            return F('base/output.mp4 missing')
        ok, d = video_contract(bmp)
        ok2, d2 = audio_contract(bmp)
        return P(ok and ok2, dict(video=d, audio=d2))
    item('B01', b01)

    def b02():
        det, ok = {}, True
        for nm in ('base', 'revision'):
            p = out / nm / 'output.mp4'
            if not p.exists():
                ok = False; det[nm] = 'missing'; continue
            i, tp = loud(p)
            cr = clip_run(decode_audio(p, mono=False))
            o = i is not None and tp is not None and abs(i - LUFS) <= LUFS_TOL and tp <= -1.0 and cr < 3
            det[nm] = dict(I=i, TP=tp, clip_run=cr); ok &= o
        return P(ok, det)
    item('B02', b02)

    def b03():
        tl = read_json(base / 'timeline.json') if (base / 'timeline.json').exists() else None
        sts = {}
        for s in STEMS:
            p = base / 'stems' / f'{s}.wav'
            if not p.exists():
                return F(f'stems/{s}.wav missing')
            inf = stem_info(p)
            if not (str(inf['codec']).startswith('pcm_') and str(inf['sr']) == str(SR) and abs(inf['dur'] - DUR) <= 1 / FPS + 1e-3):
                return F(f'stem {s} spec wrong: {inf}')
            sts[s] = decode_audio(p)
        if not bmp.exists() or tl is None:
            return F('base/output.mp4 or base/timeline.json missing/unparseable')
        cands = find_gains(tl, STEMS)
        if not cands:
            return F('no per-stem master gains found in timeline.json')
        mix = decode_audio(bmp)
        best = None
        n = min(len(v) for v in sts.values())
        for g in cands:
            c = band_compare(mix, sum(g[s] * sts[s][:n] for s in STEMS))
            if c and (best is None or c['median'] < best[1]['median']):
                best = (g, c)
        if best is None:
            return F('band comparison impossible (silent/short)')
        g, c = best
        return P(c['median'] <= 0.75 and c['p95'] <= 3.0, dict(gains_lin={k: round(v, 4) for k, v in g.items()},
                                                               lag=c['lag'], median=round(c['median'], 3), p95=round(c['p95'], 3)))
    item('B03', b03)

    # ---------- B05 / events ----------
    ev = {}

    def b05():
        p = base / 'events.csv'
        if not p.exists():
            return F('base/events.csv missing')
        hok, e, prob = read_events(p)
        ev.update(e)
        rows = list(csv.reader(p.read_text(encoding='utf-8-sig').splitlines()))[1:]
        cnt = {}
        for r in rows:
            if r and r[0].strip():
                cnt[r[0].strip()] = cnt.get(r[0].strip(), 0) + 1
        miss = [k for k in EVENTS if k not in e]
        dup = [k for k in EVENTS if cnt.get(k, 0) > 1]
        bad = [k for k in EVENTS if k in e and not 0 <= e[k] <= NFR - 1]
        pb = [x for x in prob if any(x.startswith(k + ' ') for k in EVENTS)]
        return P(hok and not miss and not dup and not bad and not pb, dict(header_ok=hok, missing=miss, duplicated=dup, out_of_range=bad, parse=pb[:5]))
    item('B05', b05)

    def evreq(*ks):
        miss = [k for k in ks if k not in ev]
        if miss:
            raise _DumpFail(f'events.csv missing {miss}')
        return [ev[k] for k in ks]

    # ---------- picture analysis (shared by B06, B07, M01, M12, M13) ----------
    frames = {}

    def get_frames(nm):
        if nm not in frames:
            p = bmp if nm == 'base' else rmp
            frames[nm] = gray_frames(p) if p.exists() else None
            if frames[nm] is not None and len(frames[nm]) == 0:
                frames[nm] = None
        return frames[nm]

    cutinfo = {}

    def get_cuts(nm):
        if nm not in cutinfo:
            fr = get_frames(nm)
            cutinfo[nm] = detect_cuts(fr) if fr is not None and len(fr) > 2 else ([], np.zeros(0))
        return cutinfo[nm]

    # ---------- B06 timeline structure + declared cuts vs detected cuts ----------
    def tl_numbers(tl):
        nums = []

        def walk(o, path=''):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, path + '/' + str(k).lower())
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    walk(v, path + f'[{i}]')
            elif isinstance(o, (int, float)) and not isinstance(o, bool):
                nums.append((path, float(o)))
        walk(tl)
        return nums

    def tl_check(nm, tl, starts, nfr):
        prob = []
        nums = tl_numbers(tl)
        shot_nums = [v for p, v in nums if re.search(r'shot|/s[1-5]\b|clip|range|start|end|in\b|out\b|frame', p)]
        near = lambda v, s: abs(v - s) <= 1 or abs(v * FPS - s) <= 1
        for s in starts[1:]:
            if not any(near(v, s) or near(v, s - 1) for v in shot_nums):
                prob.append(f'shot boundary {s} not declared')
        if not any(near(v, nfr - 1) or near(v, nfr) for v in shot_nums):
            prob.append(f'film end {nfr} not declared')
        key = 'rev' if nm == 'revision' else nm
        cuts, _ = get_cuts(key)
        if get_frames(key) is not None:
            und = [c for c in cuts if not any(near(v, c) or near(v, c - 1) for v in shot_nums)]
            if und:
                prob.append(f'detected cuts {und[:6]} not declared as shot boundaries')
            nodet = [s for s in starts[1:] if not any(abs(c - s) <= 1 for c in cuts)]
            if nodet:
                prob.append(f'declared boundaries {nodet} have no detected cut in the video')
        else:
            prob.append('video missing/undecodable: cannot compare declared and detected cuts')
        txt = json.dumps(tl)
        low = txt.lower()
        tr_paths = set(m.group(1) for p, v in nums for m in [re.match(r'(.*?transition[^/\[]*(\[\d+\]|/[^/\[]+))', p)] if m)
        n_tr = max(len(set(re.findall(r'"(t12|t23|t34|t45)"', low))), len(tr_paths),
                   len(tl.get('transitions', [])) if isinstance(tl, dict) and isinstance(tl.get('transitions'), (list, dict)) else 0)
        if n_tr < 4:
            prob.append(f'4 transitions not found (found {n_tr})')
        for c in CAMS:
            if c not in txt:
                prob.append(f'camera {c} not mentioned')
        if txt.count('CAM_S1') < 2:
            prob.append('CAM_S1 not declared for both S1 and S5')
        for s in STEMS:
            if not any(s in p and re.search(r'in|out|start|end|region|offset|src|dst', p.split(s, 1)[-1] + p) for p, v in nums):
                prob.append(f'no numeric audio in/out for stem {s}')
        if not find_gains(tl, STEMS):
            prob.append('no per-stem master gains')
        return [f'{nm}: {x}' for x in prob]

    def b06():
        prob = []
        for nm, d, starts in (('base', base, [0] + CUTS_BASE), ('revision', rev, [0] + CUTS_REV)):
            p = d / 'timeline.json'
            tl = read_json(p) if p.exists() else None
            if tl is None:
                prob.append(f'{nm}/timeline.json missing or unparseable'); continue
            prob += tl_check(nm, tl, starts, NFR)
        return P(not prob, '; '.join(prob) if prob else 'both timelines: 5 shot ranges matching the detected cuts, cameras, 4 transitions, stem in/out and gains')
    item('B06', b06)

    # ---------- B08 ----------
    def b08():
        prob = []
        cr = sorted(out.rglob('credits.md')); qa = sorted(out.rglob('qa.md'))
        if not cr:
            prob.append('credits.md missing')
        else:
            t = cr[0].read_text(encoding='utf-8', errors='ignore').lower()
            if 'blender' not in t:
                prob.append('credits.md does not name Blender')
            if not re.search(r'espeak|sox|text[- ]to[- ]speech|tts|synthes|recorded|voice|speech', t):
                prob.append('credits.md does not say how the lines were produced')
        if not qa:
            prob.append('qa.md missing')
        elif not qa[0].read_text(encoding='utf-8', errors='ignore').strip():
            prob.append('qa.md empty')
        pat = re.compile(r'(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|api[_-]?key\s*[:=]\s*\S{8,}|bearer\s+[A-Za-z0-9._-]{20,}|'
                         r'-----BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|'
                         r'elevenlabs|play\.ht|azure.*speech|polly|texttospeech\.googleapis|openai\.com/v1/audio|'
                         r'https?://\S+\.(png|jpe?g|exr|hdr|wav|mp3|mp4|mov|blend|fbx|obj|glb|gltf|tif)\b)', re.I)
        for f in out.rglob('*'):
            if f.is_file() and f.suffix.lower() in {'.md', '.txt', '.json', '.csv', '.py', '.sh', '.toml', '.yaml', '.yml'} and f.stat().st_size < 2_000_000:
                m = pat.search(f.read_text(encoding='utf-8', errors='ignore'))
                if m:
                    prob.append(f'{f.relative_to(out)}: credential/online-service trace {m.group(0)[:40]!r}')
        return P(not prob, '; '.join(prob[:8]) if prob else 'credits names Blender and the speech method; qa.md present; no credentials/online-TTS/URL media')
    item('B08', b08)

    # ---------- speech: M04, M05, M06 ----------
    sp = {}

    def speech_segs():
        if 'segs' in sp:
            return sp
        p = base / 'stems' / 'speech.wav'
        if not p.exists():
            raise _DumpFail('speech stem missing')
        need = ('line_dispatch_start', 'line_dispatch_end', 'line_picker_start', 'line_picker_end')
        if any(k not in ev for k in need):
            raise _DumpFail('line_* events not declared')
        x = decode_audio(p)
        e = rms_env(x, int(0.02 * SR))
        thr = max(float(e.max()) - 35, -60)
        segs = segments(e > thr, 0.02, 0.5)  # gaps <= 0.5 s merged (natural pauses)
        ds, de = ev['line_dispatch_start'] / FPS, ev['line_dispatch_end'] / FPS
        ps, pe = ev['line_picker_start'] / FPS, ev['line_picker_end'] / FPS

        def pick(a, b):
            best, ov = None, 0
            for s in segs:
                o = min(b, s[1]) - max(a, s[0])
                if o > ov:
                    best, ov = s, o
            return best
        dseg, pseg = pick(ds, de), pick(ps, pe)
        note = ''
        if dseg is not None and dseg == pseg and de < ps:
            # both lines merged into one segment (reply within 0.5 s): split at the quietest 20 ms between the declarations
            lo = max(int(dseg[0] / 0.02) + 1, int((de - 0.3) / 0.02)); hi = min(int(pseg[1] / 0.02) - 1, int((ps + 0.3) / 0.02) + 1)
            quiet = e[lo:hi] <= thr
            best, run, st_ = (0, None), 0, None
            for j, q in enumerate(quiet):
                if q:
                    st_ = j if run == 0 else st_; run += 1
                    if run > best[0]:
                        best = (run, st_)
                else:
                    run = 0
            if best[1] is not None:
                a0, a1 = lo + best[1], lo + best[1] + best[0]
            else:
                a0 = lo + int(np.argmin(e[lo:hi])); a1 = a0 + 1
            dseg, pseg = (dseg[0], a0 * 0.02), (a1 * 0.02, pseg[1])
            note = f'lines merged by the 0.5 s gap rule; split at the pause {a0 * 0.02:.2f}-{a1 * 0.02:.2f} s'
        sp.update(x=x, segs=segs, dseg=dseg, pseg=pseg, ds=ds, de=de, ps=ps, pe=pe, note=note)
        return sp

    def m04():
        s = speech_segs()
        if s['dseg'] is None:
            return F(f"no speech activity overlapping declared dispatcher line {s['ds']:.2f}-{s['de']:.2f}s")
        on, off = s['dseg']
        ok = 18.0 <= on <= 23.5 and off >= 24.4 and abs(on - s['ds']) <= 6 / FPS and abs(off - s['de']) <= 6 / FPS
        return P(ok, dict(measured=[round(on, 2), round(off, 2)], declared=[round(s['ds'], 2), round(s['de'], 2)],
                          note=(s['note'] + '; ' if s['note'] else '') + 'energy segments, gaps <=0.5 s merged (a >0.5 s gap at 24.0 s splits the line)'))
    item('M04', m04)

    def m05():
        s = speech_segs()
        if s['pseg'] is None:
            return F('no speech activity overlapping the declared picker line')
        on, off = s['pseg']
        prob = []
        if on < 24.0 or off > DUR + 1e-6:
            prob.append('picker line not inside S5')
        if s['dseg'] is not None and on < s['dseg'][1]:
            prob.append('picker line starts before the dispatcher line ends')
        if abs(on - s['ps']) > 6 / FPS or abs(off - s['pe']) > 6 / FPS:
            prob.append(f"declared {s['ps']:.2f}-{s['pe']:.2f}s vs measured {on:.2f}-{off:.2f}s")
        return P(not prob, '; '.join(prob) if prob else f"picker line measured {on:.2f}-{off:.2f}s (declared {s['ps']:.2f}-{s['pe']:.2f}s); {s['note']}")
    item('M05', m05)

    def m06():
        s = speech_segs()
        if s['dseg'] is None or s['pseg'] is None:
            return F('dispatcher or picker line not found in the speech stem')
        bands = [(300, 3400), (4000, 8000), (20, 200)]
        bd = band_ratio(s['x'], *s['dseg'], bands)
        bp = band_ratio(s['x'], *s['pseg'], bands)
        if not bd or not bp:
            return F('line segment too short for a spectrum')
        hd, ld, hp = bd[1] - bd[0], bd[2] - bd[0], bp[1] - bp[0]
        return P(hd <= -15 and ld <= -10 and hp - hd >= 8,
                 dict(dispatch_hf_dB=round(hd, 1), dispatch_lf_dB=round(ld, 1), picker_hf_dB=round(hp, 1)))
    item('M06', m06)

    # ---------- M07 reverse alarm ----------
    fxd = {}

    def fx_beeps():
        if 'r' in fxd:
            return fxd['r']
        p = base / 'stems' / 'fx.wav'
        if not p.exists():
            raise _DumpFail('fx stem missing')
        x = decode_audio(p)
        r, why = beeper(x)
        if r is None:
            raise _DumpFail(why)
        fxd['r'] = r
        return r

    def m07():
        r = fx_beeps()
        prob = []
        if r['prom'] < 10:
            prob.append(f"no tonal beeper: 500-3000 Hz peak {r['fpk']:.0f} Hz only {r['prom']:.1f} dB above the band median (need >=10)")
        if r['contrast'] < 10:
            prob.append(f"beeper band envelope on/off contrast {r['contrast']:.1f} dB (need >=10)")
        on = [t for t in r['onsets'] if 4.0 <= t <= 8.0]
        iv = np.diff(on)
        det = f"peak {r['fpk']:.0f} Hz (+{r['prom']:.1f} dB); onsets 4-8 s: {[round(t, 2) for t in on][:14]}"
        if len(iv) < 3:
            prob.append(f'only {len(on)} beep onsets in 4.0-8.0 s (need >=4)')
        else:
            cv = float(iv.std() / iv.mean())
            med = float(np.median(iv))
            span = [b - a for a, b in zip(on, on[1:]) if a < 6.0 <= b]
            det += f'; interval median {med:.3f}s CV {cv:.1%}'
            if cv > 0.15:
                prob.append(f'onset-interval CV {cv:.1%} > 15%')
            if not span:
                prob.append('no beep interval spans 6.0 s (alarm not continuous across T12)')
            elif abs(span[0] / med - 1) > 0.15:
                prob.append(f'interval across 6.0 s = {span[0]:.3f}s vs median {med:.3f}s (phase reset)')
            else:
                det += f'; interval across 6.0 s {span[0]:.3f}s'
        return P(not prob, ('; '.join(prob) + ' | ' if prob else '') + det)
    item('M07', m07)

    # ---------- M08 transients on fx (spectral flux, hop 256) ----------
    def m08():
        p = base / 'stems' / 'fx.wav'
        if not p.exists():
            return F('fx stem missing')
        if any(k not in ev for k in ('upright_contact', 'first_floor_hit')):
            return F('upright_contact/first_floor_hit not declared')
        x = decode_audio(p)
        hop, n = 256, 1024
        m = (len(x) - n) // hop
        idx = np.arange(n)[None, :] + hop * np.arange(m)[:, None]
        S = np.log1p(np.abs(np.fft.rfft(x[idx] * np.hanning(n), axis=1)) * 100)
        flux = np.concatenate([[0], np.maximum(S[1:] - S[:-1], 0).sum(1)])
        tt = (np.arange(m) * hop + n / 2) / SR
        det, ok = {}, True
        for k in ('upright_contact', 'first_floor_hit'):
            t0 = ev[k] / FPS
            w = flux[(tt >= t0 - 0.067) & (tt <= t0 + 0.067)]
            pre = flux[(tt >= t0 - 0.567) & (tt < t0 - 0.067)]
            if not w.size or not pre.size:
                ok = False; det[k] = 'window out of range'; continue
            r = 20 * math.log10((float(w.max()) + 1e-9) / (float(np.median(pre)) + 1e-9))
            det[k] = round(r, 1)
            ok &= r >= 12
        return P(ok, dict(flux_peak_over_prior_median_dB=det))
    item('M08', m08)

    # ---------- B07 / M13 (picture) ----------
    def b07():
        if not rmp.exists():
            return F('revision/output.mp4 missing')
        ok, d = video_contract(rmp)
        if not ok:
            return F(f'revision contract: {d}')
        fr, rf = get_frames('base'), get_frames('rev')
        if fr is None:
            return F('base/output.mp4 missing/undecodable')
        n = min(len(fr), len(rf))
        bad = [i for i in list(range(0, 319)) + list(range(331, n)) if psnr(fr[i], rf[i]) < 35]
        return P(not bad and n == NFR, dict(revision=d, frames_below_35dB=len(bad), first=bad[:5], note='PSNR on 320px luma'))
    item('B07', b07)

    def m13():
        fr = get_frames('base')
        if fr is None:
            return F('base/output.mp4 missing/undecodable')
        lum = fr.mean((1, 2))
        nearc = set(j for c in CUTS_BASE for j in range(c - 2, c + 3))
        hh, ww = fr.shape[1] // 4, fr.shape[2] // 4
        cell = fr[:, :hh * 4, :ww * 4].reshape(len(fr), 4, hh, 4, ww).mean((2, 4)).reshape(len(fr), 16)
        fl = []
        for i in range(1, len(lum) - 1):
            if i in nearc or abs(lum[i] - (lum[i - 1] + lum[i + 1]) / 2) <= max(0.03 * (lum[i - 1] + lum[i + 1]) / 2, 1.0):
                continue
            nb = (cell[i - 1] + cell[i + 1]) / 2
            r = cell[i] - nb
            big = np.abs(r) > np.maximum(0.03 * nb, 1.0)
            if max(int((big & (r > 0)).sum()), int((big & (r < 0)).sum())) >= 12:   # frame-wide (>=12 of 16 cells, same sign)
                u, v = fr[i] - fr[i].mean(), (fr[i - 1] + fr[i + 1]) / 2
                v = v - v.mean()
                cc = float((u * v).sum() / max(math.sqrt(float((u * u).sum()) * float((v * v).sum())), 1e-9))
                if cc >= 0.9:                                  # same picture structure, only brightness jumps
                    fl.append(i)
        if fl:
            return F(f'luminance flicker (frame-wide jump >3% vs the mean of both neighbours in >=12 of 16 cells, picture structure unchanged r>=0.9) at frames {fl[:8]}')
        return None   # measured part passes -> geometry/ghost remainder decided by the judge from the contact sheets
    item('M13', m13)

    # ---------- Blender: static inspection (B04) ----------
    D0 = {}

    def b04():
        rd = proj / 'README.md'
        if not blend.exists():
            STATE['b04_gate'] = 'project/scene.blend missing'
            return F('project/scene.blend missing')
        if not B.blender_ok():
            raise _GraderError('blender not on PATH in the verifier image (grader problem)')
        d = B.rich_dump(blend, {'film_frames': [0]}, tmp, timeout=300, tag='static')
        D0.update(d)
        prob = []
        if not d.get('ok'):
            if d.get('opened') is False:
                STATE['b04_gate'] = 'scene.blend cannot be opened'
                return F('Blender cannot open project/scene.blend: ' + str(d.get('error'))[-400:])
            return F('Blender static inspection failed (not a file-open error; group gate not applied): ' + str(d.get('error'))[-400:])
        miss = [n for n in REQ_OBJ if n not in d['objects']]
        if miss:
            prob.append(f'missing objects {miss}')
        if 'roll_T23_frames' not in d.get('scene_props', {}):
            prob.append('scene property roll_T23_frames missing')
        if prob:
            STATE['b04_gate'] = '; '.join(prob)
        rtxt = rd.read_text(encoding='utf-8', errors='ignore') if rd.exists() else ''
        if not rd.exists():
            prob.append('project/README.md missing')
        elif not any(re.search(r'\bblender\b|\$\{?BLENDER\}?', ln, re.I) and re.search(r'(^|\s)(-b|--background)(\s|$)', ln)
                     for ln in rtxt.splitlines()):
            prob.append('README has no command line with `blender` and `-b`/`--background`')
        return P(not prob, f"Blender {d.get('version')}; frame_start={d['frame_range'][0]}; roll_T23_frames="
                           f"{d.get('scene_props', {}).get('roll_T23_frames')}; " + ('; '.join(prob) if prob else 'all required objects present'))
    item('B04', b04)

    # ---------- Blender: per-frame inspection ----------
    Dm = {}

    def need_dump():
        if Dm:
            if not Dm.get('ok'):
                raise _DumpFail(Dm['why'])
            return Dm
        if not blend.exists():
            Dm.update(ok=False, why='project/scene.blend missing')
            raise _DumpFail(Dm['why'])
        if D0 and not D0.get('ok'):
            Dm.update(ok=False, why='Blender inspection of project/scene.blend failed: ' + str(D0.get('error'))[-300:])
            raise _DumpFail(Dm['why'])
        left = BUDGET_S - (time.time() - t_start)
        if left < 120:
            Dm.update(ok=False, why='grader time budget exhausted before the Blender per-frame inspection')
            raise _DumpFail(Dm['why'])
        uc = ev.get('upright_contact')
        s0 = uc if isinstance(uc, int) and 0 <= uc < 330 else 180
        x4 = {'sup_frames': list(range(s0, 546)), 'pen_frames': list(range(330, 900, 5)), 'last': 899,
              'roll_frames': sorted(set(range(0, 900, 10)) | set(range(170, 191)) | set(range(310, 341)) | {899}),
              'roll_track': BOXES + ['PALLET_TOP', 'FORKLIFT']}
        if isinstance(uc, int) and 15 <= uc <= 880:
            x4['contact_frames'] = [uc - 15, uc]
            x4['sway_frames'] = list(range(uc - 1, uc + 16)) + [899]
        cut_fr = [179, 180, 329, 330, 539, 540, 719, 720]
        cfg = {'film_frames': list(range(0, 900)), 'track': TRACK, 'rigs': ['PICKER_RIG', 'DRIVER_RIG'], 'bone_re': BONE_RE,
               'cams': CAMS, 'samples': dict({n: 24 for n in BOXES}, PALLET_TOP=24, FORKLIFT=60, RADIO=300),
               'bbox_world': {'FORKLIFT': sorted(set(range(174, 186)) | set(cut_fr)), 'PALLET_TOP': cut_fr,
                              'PICKER': [719, 720], 'SAFETY_LINE': [0]},
               'extra': EXTRA, 'x04': x4}
        d = B.rich_dump(blend, cfg, tmp, timeout=int(min(1800, left - 60)), tag='main')
        if not d.get('ok'):
            Dm.update(ok=False, why='Blender per-frame inspection of project/scene.blend failed: ' + str(d.get('error'))[-300:])
            raise _DumpFail(Dm['why'])
        X = d.get('x04') or {}
        for k in ('cam', 'kin', 'sup', 'pen', 'fu', 'sway', 'roll'):
            if isinstance(X.get(k), dict):
                X[k] = {int(f): v for f, v in X[k].items()}
        d['x04'] = X
        d['why'] = ''
        Dm.update(d)
        STATE['dump_seconds'] = d.get('wall_seconds')
        STATE['dump_warnings'] = (d.get('warnings') or [])[:8]
        return Dm

    def has(d, *names):
        miss = [n for n in names if n not in d['objects']]
        if miss:
            raise _DumpFail(f'required objects missing: {miss}')

    def mw(d, n, f):
        return B.M(d, n, f)

    def pos(d, n, a, b):
        return np.array([mw(d, n, f)[:3, 3] for f in range(a, b + 1)])

    def corners(d, n):
        bl = d.get('bbox_local', {}).get(n)
        if not bl:
            raise _DumpFail(f'{n}: no evaluated mesh bounds')
        return np.array(bl, float)

    def minz(d, n, f):
        return float(B.xf(mw(d, n, f), corners(d, n))[:, 2].min())

    def cuboid_pts(c, k=5):
        mn, mx = c.min(0), c.max(0)
        g = np.linspace(0, 1, k)
        pts = []
        for ax in range(3):
            o1, o2 = [a for a in range(3) if a != ax]
            for side in (0, 1):
                for u in g:
                    for v in g:
                        p = np.zeros(3); p[ax] = (mn if side == 0 else mx)[ax]
                        p[o1] = mn[o1] + u * (mx[o1] - mn[o1]); p[o2] = mn[o2] + v * (mx[o2] - mn[o2])
                        pts.append(p)
        return np.array(pts)

    def box_box(d, f, a, b, pa):
        """distance (>=0) and penetration depth of world points pa (of box a) w.r.t. cuboid b."""
        Mb = mw(d, b, f)
        cb = corners(d, b); mn, mx = cb.min(0), cb.max(0)
        inv = np.linalg.inv(Mb)
        q = pa @ inv[:3, :3].T + inv[:3, 3]
        cl = np.clip(q, mn, mx)
        wd = (cl - q) @ Mb[:3, :3].T
        dist = float(np.sqrt((wd ** 2).sum(1)).min())
        inside = np.all((q > mn) & (q < mx), axis=1)
        dep = 0.0
        if inside.any():
            sc_ = np.linalg.norm(Mb[:3, :3], axis=0)
            qi = q[inside]
            dep = float((np.minimum(qi - mn, mx - qi) * sc_).min(1).max())
        return dist, dep

    def cam_series(d, cam, a, b):
        fs = list(range(a, b + 1))
        ms = [mw(d, cam, f) for f in fs]
        return ms, np.array([m[:3, 3] for m in ms]), np.array([B.cam_pitch(m) for m in ms]), [d['cams'][cam][f] for f in fs]

    def hfov(d, ci):
        if ci.get('type') == 'ORTHO':
            return 0.0
        rx, ry, pct, pax, pay = d.get('resolution') or [1280, 720, 100, 1, 1]
        Wd, Hd = rx * pax, ry * pay
        fit = ci.get('fit', 'AUTO')
        horiz = (Wd >= Hd) if fit == 'AUTO' else (fit == 'HORIZONTAL')
        if horiz:
            return math.degrees(2 * math.atan(ci['sw'] / 2 / ci['lens']))
        sens = ci['sh'] if fit == 'VERTICAL' else ci['sw']
        return math.degrees(2 * math.atan(math.tan(math.atan(sens / 2 / ci['lens'])) * Wd / Hd))

    def locked(ms, pos_):
        disp = float(np.linalg.norm(pos_ - pos_[0], axis=1).max())
        rot = max(B.rot_angle(B.rot_of(ms[0]), B.rot_of(m)) for m in ms)
        return disp, rot

    # ---------- M02 camera grammar ----------
    def m02():
        d = need_dump(); has(d, *CAMS)
        prob, det = [], []
        guard = (d['x04'].get('static') or {}).get('forklift_top') or SCENE['guard']
        for nm, (a, b) in (('S1', SHOTS['S1']), ('S5', SHOTS['S5'])):
            ms, p_, pit, ci = cam_series(d, 'CAM_S1', a, b)
            fov = min(hfov(d, c) for c in ci)
            disp, rot = locked(ms, p_)
            if not (pit.max() <= -15 and p_[:, 2].min() >= 3 and fov >= 55 and disp < 0.01 and rot < 0.2):
                prob.append(nm)
            det.append(f'{nm} pitch<={pit.max():.1f} h>={p_[:, 2].min():.2f}m HFOV {fov:.0f} drift {disp * 100:.1f}cm/{rot:.2f}deg')
        ms, p_, pit, ci = cam_series(d, 'CAM_S2', *SHOTS['S2'])
        truck = float(np.linalg.norm((p_ - p_[0])[:, :2], axis=1).max())
        lens = np.array([c['lens'] for c in ci])
        if not (p_[:, 2].max() < guard and pit.min() >= 0 and truck >= 0.3 and np.ptp(lens) < 0.01):
            prob.append('S2')
        det.append(f'S2 h<={p_[:, 2].max():.2f}m (guard {guard:.2f}) pitch>={pit.min():.1f} truck {truck:.2f}m lens range {np.ptp(lens):.3f}')
        ms, p_, pit, ci = cam_series(d, 'CAM_S3', *SHOTS['S3'])
        fov = max(hfov(d, c) for c in ci)
        disp, rot = locked(ms, p_)
        if not (pit.min() >= 20 and disp < 0.01 and rot < 0.2 and fov <= 30):
            prob.append('S3')
        det.append(f'S3 pitch>={pit.min():.1f} HFOV {fov:.0f} drift {disp * 100:.1f}cm/{rot:.2f}deg')
        ms, p_, pit, ci = cam_series(d, 'CAM_S4', *SHOTS['S4'])
        yaw = np.unwrap(np.radians([math.degrees(math.atan2(B.cam_forward(m)[1], B.cam_forward(m)[0])) for m in ms]))
        pan = float(np.degrees(np.ptp(yaw)))
        trav = float(np.linalg.norm(p_ - p_[0], axis=1).max())
        if not (p_[:, 2].min() >= 1.2 and p_[:, 2].max() <= 1.9 and pan >= 8 and trav < 0.3):
            prob.append('S4')
        det.append(f'S4 h {p_[:, 2].min():.2f}-{p_[:, 2].max():.2f}m pan {pan:.1f}deg travel {trav:.2f}m')
        return P(not prob, ('failed: ' + ','.join(prob) + ' | ' if prob else '') + '; '.join(det))
    item('M02', m02)

    # ---------- M03 no jump cuts ----------
    def m03():
        d = need_dump(); has(d, *CAMS)
        pairs = [(180, 'CAM_S1', 'CAM_S2', ['FORKLIFT', 'PALLET_TOP']), (330, 'CAM_S2', 'CAM_S3', ['FORKLIFT', 'PALLET_TOP']),
                 (540, 'CAM_S3', 'CAM_S4', ['FORKLIFT', 'PALLET_TOP']), (720, 'CAM_S4', 'CAM_S1', ['PICKER'])]
        prob, det = [], []
        for c, ca, cb, subs in pairs:
            ang = math.degrees(math.acos(max(-1, min(1, float(B.cam_forward(mw(d, ca, c - 1)) @ B.cam_forward(mw(d, cb, c)))))))
            best = 1.0
            for s in subs:
                bw = d.get('bbox_world', {}).get(s, {})
                if c - 1 in bw and c in bw:
                    ba, _, va = B.proj_box(B.project(d, ca, c - 1, np.array(bw[c - 1])))
                    bb, _, vb = B.proj_box(B.project(d, cb, c, np.array(bw[c])))
                    if ba and bb and va and vb:
                        ha, hb = ba[3] - ba[1], bb[3] - bb[1]
                        if min(ha, hb) > 1e-6:
                            best = max(best, max(ha, hb) / min(ha, hb))
            ok = ang >= 20 or best >= 1.4
            if not ok:
                prob.append(f'{c}')
            det.append(f'cut {c} {ca}->{cb}: axis {ang:.0f}deg, subject scale x{best:.2f}')
        return P(not prob, ('jump cut at ' + ','.join(prob) + ' | ' if prob else '') + '; '.join(det))
    item('M03', m03)

    # ---------- M01 shot structure ----------
    def moving(d, a, b):
        """True if any tracked object / sampled bone / camera changes between film frames a and b."""
        for n in d['mats'].get(a, {}):
            if n in d['mats'].get(b, {}) and np.abs(np.array(d['mats'][a][n]) - np.array(d['mats'][b][n])).max() > 1e-4:
                return True
        for rig, per in d.get('bones', {}).items():
            ra, rb = per.get(a, {}), per.get(b, {})
            for k in ra:
                if k in rb and max(abs(u - v) for u, v in zip(ra[k], rb[k])) > 1e-4:
                    return True
        return False

    def m01():
        fr = get_frames('base')
        if fr is None:
            return F('base/output.mp4 missing/undecodable')
        cuts, dd = get_cuts('base')
        prob = []
        if len(fr) != NFR:
            prob.append(f'decoded {len(fr)} frames')
        for c in CUTS_BASE:
            m = [x for x in cuts if abs(x - c) <= 1]
            if not m:
                prob.append(f'no hard cut at {c}±1')
            elif not hard_cut_ok(dd, m[0]):
                prob.append(f'blended frames around cut {m[0]}')
        extra = [x for x in cuts if all(abs(x - c) > 1 for c in CUTS_BASE)]
        if extra:
            prob.append(f'extra cuts at {extra[:10]}')
        fz = freeze_runs(bmp, 8)
        if fz:
            try:
                d = need_dump()
                mv = [(s, n) for s, n in fz if moving(d, s, s + n - 1)]
                if mv:
                    prob.append(f'freeze: >=8 frames identical up to codec rounding while the project moves at (start, length) {mv[:5]}')
            except _DumpFail as e:
                prob.append(f'>=8 frames identical up to codec rounding at {fz[:5]} and project motion cannot be checked ({e})')
        return P(not prob, f'cuts={cuts[:12]}; ' + ('; '.join(prob) if prob else 'five shots, hard cuts at 180/330/540/720, no extra cut, no freeze'))
    item('M01', m01)

    # ---------- M09 picker behind the safety line ----------
    def pelvis_x(d, rig, f):
        row = d['bones'].get(rig, {}).get(f, {})
        for pat in (r'pelvis|hips', r'(^|[^a-z])hip($|[^a-z])', r'spine(\.0+|_0+|\.001)?$', r'spine', r'root|torso'):
            ks = sorted(k for k in row if re.search(pat, k, re.I) and not re.search(r'thigh|shin|leg', k, re.I))
            if ks:
                if pat in (r'pelvis|hips', r'(^|[^a-z])hip($|[^a-z])'):
                    return float(np.mean([row[k][0] for k in ks])), ks[0]
                return float(row[ks[0]][0]), ks[0]
        if row:
            return float(np.mean([v[0] for v in row.values()])), 'bone centroid'
        return float(mw(d, rig, f)[0, 3]), 'rig origin'

    def m09():
        pb, = evreq('picker_behind_line')
        d = need_dump(); has(d, 'PICKER_RIG', 'SAFETY_LINE')
        bw = d['bbox_world'].get('SAFETY_LINE', {}).get(0)
        lx = float(np.array(bw).mean(0)[0]) if bw else SCENE['line_x']
        prob = []
        if not 540 <= pb <= 719:
            prob.append(f'picker_behind_line {pb} not in S4')
        x_at, bn = pelvis_x(d, 'PICKER_RIG', min(pb, 899))
        x_pre, _ = pelvis_x(d, 'PICKER_RIG', max(0, pb - 30))
        later = [pelvis_x(d, 'PICKER_RIG', f)[0] for f in range(min(pb, 899), 900)]
        if x_at < lx + 0.2:
            prob.append(f'pelvis x {x_at:.2f} at {pb} < line+0.2 ({lx + 0.2:.2f})')
        if x_pre >= lx:
            prob.append(f'pelvis already on the safe side 1 s earlier (x {x_pre:.2f})')
        if later and min(later) < lx:
            prob.append(f'pelvis back on the unsafe side later (min x {min(later):.2f})')
        slide = []
        row0 = d['bones'].get('PICKER_RIG', {}).get(540, {})
        feet = [k for k in row0 if re.search(r'foot|ankle', k, re.I) and not re.search(r'ik|pole|target|ctrl|mch', k, re.I)]
        by_side = {}
        for k in sorted(feet):
            by_side.setdefault(B.side_of(k) or k, k)
        for s, k in by_side.items():
            z = np.array([d['bones']['PICKER_RIG'][f][k][2] for f in range(540, 900)])
            xy = np.array([d['bones']['PICKER_RIG'][f][k][:2] for f in range(540, 900)])
            low = z <= z.min() + 0.01
            i = 0
            while i < len(z):
                if low[i]:
                    j = i
                    while j + 1 < len(z) and low[j + 1]:
                        j += 1
                    if j - i + 1 >= 3:
                        drift = float(np.linalg.norm(xy[i:j + 1] - xy[i], axis=1).max())
                        if drift >= 0.05:
                            slide.append((k, 540 + i, round(drift * 100, 1)))
                    i = j + 1
                else:
                    i += 1
        if not by_side:
            prob.append('no foot bones in PICKER_RIG')
        if slide:
            prob.append(f'planted foot slides >=5 cm (bone, frame, cm): {slide[:4]}')
        return P(not prob, ('; '.join(prob) + ' | ' if prob else '') + f'line x {lx:.2f}; pelvis ({bn}) x {x_pre:.2f} at {pb - 30}, {x_at:.2f} at {pb}, min later {min(later) if later else float("nan"):.2f}; feet {list(by_side.values())}')
    item('M09', m09)

    # ---------- M10 interpenetration ----------
    def m10():
        d = need_dump(); has(d, *BOXES)
        pen = d['x04'].get('pen', {})
        if not pen:
            return F('no penetration samples (RACK_C/FORKLIFT geometry not readable)')
        worst = (0.0, None, None)
        loc = {n: cuboid_pts(corners(d, n)) for n in BOXES}
        for f in range(330, 900, 5):
            for n in BOXES:
                pw = B.xf(mw(d, n, f), loc[n])
                fl = max(0.0, -float(pw[:, 2].min()))
                if fl > worst[0]:
                    worst = (fl, n, f'floor@{f}')
                rk = float((pen.get(f) or {}).get(n, 0.0))
                if rk > worst[0]:
                    worst = (rk, n, f'rack/forklift@{f}')
                for m in BOXES:
                    if m != n:
                        dep = box_box(d, f, n, m, pw)[1]
                        if dep > worst[0]:
                            worst = (dep, n, f'{m}@{f}')
        return P(worst[0] <= 0.02, f'max penetration {worst[0] * 100:.1f} cm ({worst[1]} vs {worst[2]}); sampled every 5 frames 330-895; floor z=0')
    item('M10', m10)

    # ---------- M11 rigs, fingers, radio grip ----------
    def finger_count(d, rig):
        arm = d['armatures'].get(rig)
        if not arm:
            return {}, {}
        bones, keyed = arm['bones'], set(arm['keyed'])
        fc = {}
        for e in d['fcurves'].get(rig, []):
            m = re.match(r'pose\.bones\["(.+?)"\]', e['path'])
            if m and e.get('n', 0) >= 2:
                fc.setdefault(m.group(1), []).append((e['path'].split('.')[-1], e['index'], tuple(e['frames'][:60]), tuple(e['values'][:60])))
        groups = B.finger_groups(bones)
        res, sig = {}, {}
        for side in ('L', 'R'):
            names = {k: v for k, v in groups[side].items() if sum(1 for b in v if b in keyed) >= 3}
            topo = 0
            for h in [b for b in bones if re.search(r'hand|palm', b, re.I) and B.side_of(b) == side]:
                for path in B.chains_under(bones, h):
                    if sum(1 for b in path if b in keyed) >= 3:
                        topo += 1
            res[side] = max(len(names), topo)
            sig[side] = len(set(tuple(sorted(sum((fc.get(b, []) for b in v if b in keyed), []))) for v in names.values()))
        return res, sig

    def m11():
        rr, = evreq('radio_raise')
        d = need_dump(); has(d, 'DRIVER', 'PICKER', 'DRIVER_RIG', 'PICKER_RIG', 'RADIO')
        prob, det = [], []
        for ch, rig in (('DRIVER', 'DRIVER_RIG'), ('PICKER', 'PICKER_RIG')):
            par = d['parents'].get(ch, [None, None, None])
            driven = rig in d['armature_mods'].get(ch, []) or (par[0] == rig and par[1] == 'ARMATURE')
            if not driven:
                prob.append(f'{ch} not deformed by {rig}')
            cnt, sig = finger_count(d, rig)
            if min(cnt.get('L', 0), cnt.get('R', 0)) < 4:
                prob.append(f'{rig} keyed finger chains per hand {cnt} (need >=4 chains of >=3 keyed bones on each hand)')
            if min(sig.get('L', 0), sig.get('R', 0)) < 2:
                prob.append(f'{rig} fingers not independently animated (distinct finger curves per hand {sig})')
            det.append(f'{ch}: driven={driven} chains={cnt} distinct={sig}')
        if not 720 <= rr <= 899:
            prob.append(f'radio_raise {rr} not in S5')
        rs = np.array(d['samples'].get('RADIO') or [], float)
        if not len(rs):
            raise _DumpFail('RADIO: no mesh geometry')
        hand = [b for b in d['sampled_bones'].get('PICKER_RIG', []) if HANDISH.search(b)]
        head = [b for b in d['sampled_bones'].get('PICKER_RIG', []) if re.search(r'(^|[^a-z])head', b, re.I)]
        if not hand or not head:
            raise _DumpFail(f'PICKER_RIG hand bones {hand[:3]} / head bones {head[:3]} not found')

        def hd(f):
            ks, segs = B.bone_segs(d, 'PICKER_RIG', f, set(hand))
            return float(B.seg_point_dist(segs, B.xf(mw(d, 'RADIO', f), rs)).min()) if len(segs) else np.inf
        rr = min(max(rr, 2), 897)
        dg = min(hd(f) for f in range(rr - 2, rr + 3))
        if dg > 0.05:
            prob.append(f'nearest PICKER hand/finger bone {dg * 100:.1f} cm from RADIO at radio_raise±2 (need <=5)')
        c = rs.mean(0, keepdims=True)
        reach = None
        for f in range(rr, 900):
            ks, segs = B.bone_segs(d, 'PICKER_RIG', f, set(head))
            if len(segs) and B.seg_point_dist(segs, B.xf(mw(d, 'RADIO', f), c)).min() <= 0.30:
                reach = f; break
        if reach is None:
            prob.append('RADIO never comes within 30 cm of the PICKER head after radio_raise')
        else:
            par = d['parents'].get('RADIO', [None, None, None])
            cons = [x for x in d.get('constraints', {}).get('RADIO', []) if x[2] == 'PICKER_RIG']
            far = [f for f in range(rr, reach + 1) if hd(f) > 0.05]
            follows = par[0] == 'PICKER_RIG' or bool(cons) or not far
            if not follows:
                prob.append(f'RADIO does not follow the hand (>5 cm from it at frames {far[:4]})')
            det.append(f'radio grip {dg * 100:.1f} cm at {rr}±2; reaches head at {reach}; parent={par[0]} constraints={len(cons)}')
        return P(not prob, ('; '.join(prob) + ' | ' if prob else '') + '; '.join(det))
    item('M11', m11)

    # ---------- M14 metric scale ----------
    def m14():
        d = need_dump()
        S = d['x04'].get('static') or {}
        if 'dims' not in S:
            raise _DumpFail('static scale measurement failed: ' + str(S.get('error')))
        prob = []
        within = lambda a, b, t=0.05: abs(a - b) <= t * b
        for n in BOXES:
            v = S['dims'].get(n)
            if v is None or not all(within(a, b) for a, b in zip(v, SCENE['carton'])):
                prob.append(f'{n} dims {v}')
        v = S['dims'].get('PALLET_TOP')
        if v is None or not all(within(a, b) for a, b in zip(v, SCENE['pallet'])):
            prob.append(f'PALLET_TOP dims {v}')
        zt = [z for z in S.get('rack_up_z', []) if 4.0 <= z <= 5.0]
        bt = max(zt) if zt else None
        if bt is None or abs(bt - SCENE['beam_top']) > 0.1:
            prob.append(f'RACK_C top beam top z {bt} (need 4.5±0.1; up-facing faces at {S.get("rack_up_z", [])[:8]})')
        for n, x0 in zip(UPRIGHTS, SCENE['upright_x']):
            r = S.get('upright_x', {}).get(n)
            if r is None or abs((r[0] + r[1]) / 2 - x0) > 0.1:
                prob.append(f'{n} centre x {None if r is None else round((r[0] + r[1]) / 2, 3)} (need {x0}±0.1)')
        gt = S.get('forklift_top')
        if gt is None or not within(gt, SCENE['guard']):
            prob.append(f'FORKLIFT top (overhead guard) z {gt} (need 2.15±5%)')
        for ch in ('PICKER', 'DRIVER'):
            h = S.get('heights', {}).get(ch, {})
            ok = any(within(h[k], SCENE[ch]) for k in ('mesh_rest_extent', 'rig_rest_extent') if h.get(k))
            if not ok:
                prob.append(f'{ch} rest-pose height {h} (need {SCENE[ch]}±5% from mesh or rig extent)')
        return P(not prob, '; '.join(prob[:8]) if prob else f'cartons, pallet, beam top {bt:.3f}, uprights, guard {gt:.2f} m and character heights {S.get("heights")} within tolerance')
    item('M14', m14)

    # ---------- G01 one continuous world ----------
    def g01():
        d = need_dump(); has(d, *BOXES, 'PALLET_TOP', 'FORKLIFT')
        prob = []
        for n in BOXES + ['PALLET_TOP', 'FORKLIFT']:
            p_ = pos(d, n, 0, 899)
            for c in CUTS_BASE:
                if n == 'FORKLIFT' and c == 180:
                    continue                         # forklift continuity at T12 is scored by G03
                dj = float(np.linalg.norm(p_[c] - p_[c - 1]))
                nb = [float(np.linalg.norm(p_[i + 1] - p_[i])) for i in range(max(0, c - 6), min(899, c + 5)) if i != c - 1]
                ref = float(np.mean(nb)) if nb else 0.0
                if dj > max(0.01, 2 * ref):
                    prob.append(f'{n} jumps {dj * 100:.1f} cm at {c - 1}->{c} (neighbour motion {ref * 100:.2f} cm/frame)')
        hide = [n for n in BOXES + ['PALLET_TOP', 'FORKLIFT'] for e in d['fcurves'].get(n, []) if re.search(r'hide_render|hide_viewport|visible', e['path'])]
        if hide:
            prob.append(f'visibility animated on {sorted(set(hide))}')
        cl = (d['x04'].get('static') or {}).get('carton_like', [])
        stand = [n for n in cl if n not in BOXES and any(re.search(r'location|rotation|scale|hide|visible', e['path']) for e in d['fcurves'].get(n, []))]
        if stand:
            prob.append(f'animated carton-sized stand-ins (transform/visibility keys) {stand[:6]}')
        return P(not prob, '; '.join(prob[:6]) if prob else 'BOX_01-12, PALLET_TOP, FORKLIFT continuous across all cuts; no visibility animation, no animated carton stand-ins')
    item('G01', g01)

    # ---------- G02 gravity & scale ----------
    def g02():
        rel, hit_d = evreq('first_box_release', 'first_floor_hit')
        d = need_dump(); has(d, *BOXES)
        prob, det = [], []
        g = d.get('gravity') or [0, 0, 0]
        gz = -float(g[2])
        rbw = d.get('rigidbody_world') or {}
        if not d.get('use_gravity', True) or abs(gz - 9.81) > 0.05 * 9.81:
            prob.append(f'scene gravity {g} (use_gravity={d.get("use_gravity")})')
        ts = rbw.get('time_scale')
        if ts is None or abs(ts - 1.0) > 0.05:
            prob.append(f'rigid-body time scale {ts}')
        mz = {n: np.array([minz(d, n, f) for f in range(0, 900)]) for n in BOXES}
        hits = {n: int(np.argmax(z < 0.02)) for n, z in mz.items() if (z < 0.02).any()}
        if not hits:
            return F('; '.join(prob + ['no BOX reaches the floor (min z < 2 cm)']))
        first = min(hits.values())
        if not (330 <= rel <= 539 and 330 <= hit_d <= 539):
            prob.append(f'declared first_box_release {rel} / first_floor_hit {hit_d} not both in S3')
        if abs(hit_d - first) > 3:
            prob.append(f'declared first_floor_hit {hit_d} vs first measured touchdown {first}')
        sup = d['x04'].get('sup', {})
        loc = {n: cuboid_pts(corners(d, n)) for n in BOXES}
        timing = 'waived (no carton falls >= 0.5 m)'
        tried = []
        for n in sorted(hits, key=lambda k: hits[k]):
            hf = hits[n]
            start, how = None, ''
            for f in range(hf - 1, max(0, min(sup) if sup else 330) - 1, -1):
                ds = (sup.get(f) or {}).get(n)
                pw = B.xf(mw(d, n, f), loc[n])
                still = [m for m in BOXES if m != n and np.linalg.norm(mw(d, m, f)[:3, 3] - mw(d, m, f - 1)[:3, 3]) <= 0.005]
                db = min([box_box(d, f, n, m, pw)[0] for m in still] or [1e9])     # only cartons that are (nearly) at rest support
                if (ds is not None and ds <= SUPPORT_TOL) or db <= SUPPORT_TOL:
                    start, how = f, f'last support contact <={SUPPORT_TOL * 100:.0f} cm'
                    break
            if start is None:
                f = hf - 1
                while f > 0 and mz[n][f - 1] > mz[n][f] + 1e-4:
                    f -= 1
                start, how = f, 'start of the final descent (no support contact found)'
            h = float(mz[n][start])
            tried.append(f'{n}:{start}->{hf} h={h:.2f}')
            if h < 0.5:
                continue
            t = (hf - start) / FPS
            ratio = t / math.sqrt(2 * h / 9.81)
            timing = f'{n}: fall {start}->{hf} ({how}), h={h:.2f} m, t={t:.2f}s = {ratio:.2f}x sqrt(2h/g)'
            if not 0.75 <= ratio <= 1.35:
                prob.append(f'fall time ratio {ratio:.2f} outside [0.75, 1.35]')
            break
        det.append(timing + ('' if 'waived' not in timing else f' tried {tried[:6]}'))
        return P(not prob, ('; '.join(prob) + ' | ' if prob else '') + f'gravity {gz:.2f}, time scale {ts}, first touchdown {first}; ' + '; '.join(det))
    item('G02', g02)

    # ---------- G03 match on action at T12 ----------
    def g03():
        d = need_dump(); has(d, 'FORKLIFT', 'CAM_S1', 'CAM_S2')
        p_ = {f: mw(d, 'FORKLIFT', f)[:3, 3] for f in range(174, 186)}
        steps = {f: float(np.linalg.norm(p_[f + 1] - p_[f])) for f in range(174, 185)}
        ref = float(np.mean([steps[f] for f in range(175, 185) if f != 179]))
        prob = []
        if ref < 1e-4:
            return F(f'FORKLIFT not moving around the T12 cut (mean {ref * 1000:.2f} mm/frame)')
        ratio = steps[179] / ref
        if not 0.5 <= ratio <= 2.0:
            prob.append(f'179->180 displacement {ratio:.2f}x the 175-185 mean')
        sb = float(np.mean([steps[f] for f in range(175, 179)])); sa = float(np.mean([steps[f] for f in range(180, 184)]))
        chg = abs(sa - sb) / max(sb, 1e-9)
        if chg >= 0.25:
            prob.append(f'speed change {chg:.0%} across the cut')
        v = p_[180] - p_[179]
        if np.linalg.norm(v) < 1e-6:
            v = p_[181] - p_[178]
        x1 = float((B.rot_of(mw(d, 'CAM_S1', 179)).T @ v)[0]); x2 = float((B.rot_of(mw(d, 'CAM_S2', 180)).T @ v)[0])
        if x1 == 0 or np.sign(x1) != np.sign(x2):
            prob.append(f'screen-horizontal direction flips (CAM_S1 {x1:+.3f}, CAM_S2 {x2:+.3f})')
        bw = d['bbox_world'].get('FORKLIFT', {})
        low = []
        for cam, fr_ in (('CAM_S1', range(175, 180)), ('CAM_S2', range(180, 185))):
            for f in fr_:
                uvz = B.project(d, cam, f, np.array(bw[f]))
                box, area, vis = B.proj_box(uvz)
                full = (box[2] - box[0]) * (box[3] - box[1]) if box else 0
                share = area / full if full > 0 else 0
                if share < 0.3:
                    low.append((cam, f, round(share, 2)))
        if low:
            prob.append(f'FORKLIFT bbox <30% in frame at {low[:4]}')
        return P(not prob, ('; '.join(prob) + ' | ' if prob else '') + f'displacement ratio {ratio:.2f}, speed change {chg:.0%}, screen x CAM_S1 {x1:+.3f} / CAM_S2 {x2:+.3f}')
    item('G03', g03)

    # ---------- G04 S1/S5 same set-up ----------
    def shot_cams(tl):
        res = []

        def walk(o):
            if isinstance(o, dict):
                cam = next((v for v in o.values() if isinstance(v, str) and re.fullmatch(r'CAM_S[1-4]', v)), None)
                st = next((v for k, v in o.items() if isinstance(v, (int, float)) and not isinstance(v, bool) and re.search(r'start|in|from|first|begin', k, re.I)), None)
                if st is None:
                    rg = next((v for k, v in o.items() if isinstance(v, list) and len(v) == 2 and all(isinstance(q, (int, float)) for q in v)), None)
                    st = rg[0] if rg else None
                if cam and st is not None:
                    res.append((float(st) * FPS if float(st) <= 30 else float(st), cam))   # <=30: seconds
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(tl)
        return res

    def g04():
        d = need_dump(); has(d, 'CAM_S1', *BOXES)
        prob, det = [], []
        act = d['x04'].get('cam', {})
        used = set(v for v in act.values() if v)
        if len(used) > 1:
            bad = [f for f in list(range(1, 179)) + list(range(721, 899)) if act.get(f) != 'CAM_S1']
            if bad:
                prob.append(f'active camera is not CAM_S1 at film frames {bad[:4]} (S1/S5)')
            det.append('active camera from the file (markers/scene)')
        else:
            tl = read_json(base / 'timeline.json') if (base / 'timeline.json').exists() else None
            sc_ = shot_cams(tl) if tl is not None else []
            s5 = [c for st, c in sc_ if abs(st - 720) <= 1]
            if not s5 or s5[0] != 'CAM_S1':
                prob.append(f'file does not switch cameras and timeline.json does not declare CAM_S1 for the shot starting at 720 ({sc_[:6]})')
            det.append('S5 camera from timeline.json (file does not switch cameras)')
        ms, p_, pit, ci = cam_series(d, 'CAM_S1', 0, 179)
        ms2, p2, pit2, ci2 = cam_series(d, 'CAM_S1', 720, 899)
        allm, allp = ms + ms2, np.vstack([p_, p2])
        disp, rot = locked(allm, allp)
        lens = [c['lens'] for c in ci + ci2]
        if disp >= 0.01 or rot >= 0.2 or max(lens) - min(lens) > 1e-3:
            prob.append(f'CAM_S1 differs between S1 and S5 ({disp * 100:.1f} cm, {rot:.2f} deg, lens {min(lens):.2f}-{max(lens):.2f})')
        if not bmp.exists():
            return F('; '.join(prob + ['base/output.mp4 missing']))
        a, b = frame_at(bmp, 90).astype(np.float64), frame_at(bmp, 810).astype(np.float64)
        hb, wb = 360 // 16, 640 // 16
        ba = a[:hb * 16, :wb * 16].reshape(hb, 16, wb, 16); bb = b[:hb * 16, :wb * 16].reshape(hb, 16, wb, 16)
        mse = ((ba - bb) ** 2).mean((1, 3))
        ps = np.where(mse <= 1e-10, 99.0, 10 * np.log10(255.0 ** 2 / np.maximum(mse, 1e-10)))
        med = float(np.median(ps))
        if med < 26:
            prob.append(f'frame 90 vs 810 median block PSNR {med:.1f} dB < 26')
        onfl = []
        for n in BOXES:
            c8 = B.xf(mw(d, n, 810), corners(d, n))
            if c8[:, 2].min() < 0.05:
                box, area, vis = B.proj_box(B.project(d, 'CAM_S1', 810, c8))
                full = (box[2] - box[0]) * (box[3] - box[1]) if box else 0
                if full > 0 and area / full >= 0.4:
                    onfl.append(n)
        if len(onfl) < 2:
            prob.append(f'only {len(onfl)} fallen cartons >=40% inside the CAM_S1 frame at 810')
        return P(not prob, ('; '.join(prob) + ' | ' if prob else '') + f"{'; '.join(det)}; CAM_S1 drift {disp * 100:.2f} cm/{rot:.3f} deg; median block PSNR {med:.1f} dB; fallen cartons in view {onfl}")
    item('G04', g04)

    # ---------- G05 collapse settles ----------
    def g05():
        lr, = evreq('last_box_rest')
        d = need_dump(); has(d, *BOXES)
        prob = []
        if not 330 <= lr < 720:
            prob.append(f'last_box_rest {lr} not in S3/S4')
        fast = []
        for n in BOXES:
            a = pos(d, n, min(lr, 899), 899)
            if len(a) > 1:
                v = np.linalg.norm(np.diff(a, axis=0), axis=1)
                if v.max() > 0.002:
                    fast.append((n, round(float(v.max()) * 1000, 1)))
        if fast:
            prob.append(f'boxes moving >2 mm/frame after last_box_rest: {fast[:4]}')
        floor = [n for n in BOXES if minz(d, n, 899) < 0.05]
        if len(floor) < 2:
            prob.append(f'only {len(floor)} boxes on the floor at frame 899')
        return P(not prob, '; '.join(prob) if prob else f'all cartons <=2 mm/frame from {lr}; {len(floor)} on the floor')
    item('G05', g05)

    # ---------- G06 contact & causality ----------
    def g06():
        uc, tip, stop = evreq('upright_contact', 'pallet_tip', 'forklift_stop')
        d = need_dump(); has(d, 'FORKLIFT', *UPRIGHTS)
        prob = []
        if not 180 <= uc < 330:
            prob.append(f'upright_contact {uc} not in S2')
        if not tip > uc:
            prob.append('pallet_tip not after upright_contact')
        if not 0 <= stop - uc <= FPS:
            prob.append('forklift_stop not within 1 s after contact')
        fu = d['x04'].get('fu', {})
        if uc not in fu or uc - 15 not in fu or not fu[uc]:
            return F('; '.join(prob + ['forklift-upright distances not measurable']))
        up = min(fu[uc], key=fu[uc].get)
        dc, dp = fu[uc][up], fu[uc - 15].get(up, 0)
        if dc > 0.02:
            prob.append(f'nearest upright {up} is {dc * 100:.1f} cm from FORKLIFT at contact (need <=2)')
        if dp < 0.10:
            prob.append(f'{up} already {dp * 100:.1f} cm from FORKLIFT 15 frames before contact (need >=10)')
        sw = d['x04'].get('sway', {})
        ref = sw.get(uc - 1, {})

        def disp(name, f):
            a, b = ref.get(name), sw.get(f, {}).get(name)
            if not a or not b or len(a) != len(b):
                return None
            return float(np.linalg.norm(np.array(b) - np.array(a), axis=1).max())
        sway = max([x for x in (disp(n, f) for n in (up, 'RACK_C') for f in range(uc, uc + 16)) if x is not None] or [0])
        drift = [x for x in (disp(up, 899), disp('RACK_C', 899)) if x is not None]
        if sway < 0.005:
            prob.append(f'{up}/RACK_C sway {sway * 1000:.1f} mm within 0.5 s of contact (need >=5)')
        if drift and max(drift) > 0.03:
            prob.append(f'permanent drift {max(drift) * 100:.1f} cm at 899 (max 3)')
        mv = []
        for n in BOXES + ['PALLET_TOP']:
            if n in d['objects']:
                a = pos(d, n, 0, uc)
                dm = float(np.linalg.norm(a - a[0], axis=1).max())
                if dm >= 0.005:
                    mv.append((n, round(dm * 1000, 1)))
        if mv:
            prob.append(f'objects moved before contact (mm): {mv[:4]}')
        return P(not prob, ('; '.join(prob) + ' | ' if prob else '') + f'{up}: {dc * 100:.1f} cm at {uc}, {dp * 100:.1f} cm at {uc - 15}; sway {sway * 1000:.1f} mm; drift {max(drift or [0]) * 100:.1f} cm')
    item('G06', g06)

    # ---------- G07 sound perspective ----------
    def g07():
        r = fx_beeps()
        d = need_dump(); has(d, 'FORKLIFT', 'CAM_S1', 'CAM_S2')
        bp = r['bp']
        on = r['onsets']

        def per(ts):
            lv, el = [], []
            for t in ts:
                a = int(t * SR)
                seg = bp[a:a + int(0.05 * SR)]
                if len(seg) < 240:
                    continue
                lv.append(float(rms_env(seg, 240).max()))
                e1 = float((bp[a:a + int(0.03 * SR)] ** 2).sum()); e2 = float((bp[a + int(0.1 * SR):a + int(0.3 * SR)] ** 2).sum())
                el.append(10 * math.log10(max(e1, 1e-20) / max(e2, 1e-20)))
            return (float(np.median(lv)) if lv else None), (float(np.median(el)) if el else None)
        s1 = [t for t in on if 3.0 <= t <= 5.8]
        s2 = [t for t in on if 6.2 <= t <= 8.0]
        if len(s2) < 2:
            s2 = [t for t in on if 6.0 <= t <= 11.0]
        if not s1 or not s2:
            return F(f'beeps found S1 {len(s1)} / S2 {len(s2)} (need >=1 each)')
        L1, E1 = per(s1); L2, E2 = per(s2)
        c = corners(d, 'FORKLIFT')
        cen, half = (c.min(0) + c.max(0)) / 2, (c.max(0) - c.min(0)) / 2
        p_ = pos(d, 'FORKLIFT', 0, 329)
        v = p_[170] - p_[10]
        Rm = B.rot_of(mw(d, 'FORKLIFT', 0))
        if np.linalg.norm(v) > 1e-3:
            k = int(np.argmax(np.abs(Rm.T @ v)))
            sgn = np.sign((Rm.T @ v)[k])
        else:
            k, sgn = 0, -1.0
        rear = cen.copy(); rear[k] += sgn * half[k]
        dist = lambda cam, a, b: float(np.mean([np.linalg.norm(mw(d, cam, f)[:3, 3] - B.xf(mw(d, 'FORKLIFT', f), rear[None])[0]) for f in range(a, b + 1)]))
        d1, d2 = dist('CAM_S1', 0, 179), dist('CAM_S2', 180, 329)
        det = f'cam-rear distance S1 {d1:.2f} m, S2 {d2:.2f} m; beep level S1 {L1:.1f} / S2 {L2:.1f} dB; early/late S1 {E1:.1f} / S2 {E2:.1f} dB'
        if d2 <= 0.5 * d1:
            ok = (L2 - L1 >= 3) and (E1 <= E2 - 2)
        else:
            ok = L2 - L1 >= -1
            det += ' (distance condition not met: level must not drop by >1 dB)'
        return P(ok, det)
    item('G07', g07)

    # ---------- G08 photoreal (measured part) ----------
    def g08():
        prob = []
        if not bmp.exists():
            return F('base/output.mp4 missing')
        idx = {}
        for s, fs in (('S1', [30, 90, 150]), ('S2', [200, 250, 300]), ('S3', [360, 430, 500]), ('S4', [570, 630, 690]), ('S5', [750, 810, 870])):
            idx[s] = round(float(np.median([flat_block_index(frame_at(bmp, f, 1280, 720)) for f in fs])), 3)
        STATE['flat_index'] = idx
        bad = {s: v for s, v in idx.items() if v > 0.35}
        if len(bad) >= 3:
            prob.append(f'flat-block index > 0.35 in {len(bad)} of 5 shots {bad}')
            STATE['g08_flat'] = True
        try:
            d = need_dump()
            hero = ['FORKLIFT', 'RACK_C', 'PALLET_TOP', 'DRIVER', 'PICKER', 'CART'] + BOXES[:1]
            nob = [h for h in hero if h in d['objects'] and not any(
                any(t.startswith('BSDF') or t == 'GROUP' for t in m.get('node_types', [])) for m in d['materials'].get(h, []))]
            if nob:
                prob.append(f'objects without a node-based BSDF material: {nob}')
            var = [h for h in hero if any(m.get('n_tex', 0) > 0 or m.get('principled_linked') for m in d['materials'].get(h, []))]
            if len(var) < 3:
                prob.append(f'surface variation (texture or linked BSDF input) on only {var} (need >=3 of {hero})')
            soft = [n for n, l in d['lights'].items() if l['type'] == 'AREA' or l['size'] > 0.02 or l['radius'] > 0.02 or (l['type'] == 'SUN' and l['angle'] > 0.005)]
            if not soft and not any(t in d.get('world_nodes', []) for t in ('TEX_ENVIRONMENT', 'TEX_SKY')):
                prob.append('no soft light source (area/sized light or environment/sky world)')
            if d.get('engine') == 'CYCLES' and d['render'].get('oidn_available', True) and not (d['render'].get('cycles_denoise') or d['render'].get('compositor_denoise')):
                prob.append('Cycles render without denoising')
        except _DumpFail as e:
            prob.append(str(e))
        return F('; '.join(prob)) if prob else None   # measured parts pass -> photoreal look decided by the judge
    item('G08', g08)

    # ---------- G09 rigid-body simulation ----------
    def g09():
        uc, lr = evreq('upright_contact', 'last_box_rest')
        d = need_dump(); has(d, *BOXES)
        prob = []
        fs = int(d.get('frame_offset', 0) or 0)
        rbw = d.get('rigidbody_world') or {}
        if not rbw:
            return F('no rigid body world')
        members = set(rbw.get('objects') or [])
        notact = [n for n in BOXES if not any(e.get('type') == 'RIGID_BODY' and e.get('rb_type') == 'ACTIVE' and e.get('enabled', True)
                                              for e in d['physics'].get(n, [])) or n not in members]
        if notact:
            prob.append(f'not active rigid bodies in the rigid-body world: {notact}')
        kin = d['x04'].get('kin', {})
        km = []
        for n in BOXES:
            for f in range(max(uc, 1), 900):
                if n in kin.get(f, []):
                    a, b = mw(d, n, f - 1), mw(d, n, f)
                    if np.linalg.norm(b[:3, 3] - a[:3, 3]) > 0.001 or B.rot_angle(B.rot_of(a), B.rot_of(b)) > 0.1:
                        km.append((n, f)); break
        if km:
            prob.append(f'kinematic (animated) boxes moving after upright_contact: {km[:4]}')
        keyed = sorted(set(n for n in BOXES for e in d['fcurves'].get(n, []) if re.match(r'(delta_)?(location|rotation_euler|rotation_quaternion|scale)$', e['path'])
                           and any(fr > fs + uc for fr in e.get('frames', []))))
        if keyed:
            prob.append(f'transform keyframes after upright_contact on {keyed[:6]}')
        cache = rbw.get('cache') or {}
        disk = list(proj.rglob('*.bphys'))
        if not (cache.get('is_baked') or disk):
            prob.append('rigid-body cache not baked in the .blend and no .bphys files in project/')
        if cache and not (cache.get('frame_start', 0) <= fs + uc and cache.get('frame_end', 0) >= fs + min(lr, 899)):
            prob.append(f"rigid-body cache range {cache.get('frame_start')}-{cache.get('frame_end')} does not cover scene frames {fs + uc}-{fs + min(lr, 899)}")
        om, bounce, slide = 0.0, [], []
        for n in BOXES:
            for f in range(max(uc, 1), 900):
                om = max(om, B.rot_angle(B.rot_of(mw(d, n, f - 1)), B.rot_of(mw(d, n, f))) * FPS)
            z = np.array([minz(d, n, f) for f in range(uc, 900)])
            xy = pos(d, n, uc, 899)[:, :2]
            hit = np.where(z < 0.02)[0]
            if hit.size:
                h0 = hit[0]
                zmin = np.minimum.accumulate(z[h0:])
                if (z[h0:] - zmin).max() >= 0.01:
                    bounce.append(n)
                cont = z < 0.02
                tr = sum(float(np.linalg.norm(xy[i + 1] - xy[i])) for i in range(h0, len(z) - 1) if cont[i] and cont[i + 1])
                if tr >= 0.05:
                    slide.append(n)
        if om < 90:
            prob.append(f'peak carton angular speed {om:.0f} deg/s (need >=90)')
        if not bounce and not slide:
            prob.append('no carton bounces (>=1 cm) or slides (>=5 cm) after touching the floor')
        return P(not prob, ('; '.join(prob) + ' | ' if prob else '') + f'cache baked={cache.get("is_baked")} range {cache.get("frame_start")}-{cache.get("frame_end")} bphys={len(disk)}; peak {om:.0f} deg/s; bounce {bounce[:3]} slide {slide[:3]}')
    item('G09', g09)

    # ---------- M15 / M12 re-renders ----------
    def offset():
        if Dm.get('ok'):
            return int(Dm.get('frame_offset') or 0)
        if D0.get('ok'):
            return int((D0.get('frame_range') or [0])[0] or 0)
        return 0

    def m15():
        if not blend.exists():
            return F('project/scene.blend missing')
        if not bmp.exists():
            return F('base/output.mp4 missing')
        if D0 and not D0.get('ok'):
            return F('Blender cannot inspect project/scene.blend: ' + str(D0.get('error'))[-200:])
        det, ok = [], True
        for f, cam in ((90, 'CAM_S1'), (255, 'CAM_S2'), (435, 'CAM_S3'), (630, 'CAM_S4'), (810, 'CAM_S1')):
            if time.time() - t_start > BUDGET_S:
                return F('; '.join(det + [f'grader time budget exhausted before frame {f}']))
            rr, note = blend_render(blend, offset() + f, tmp, 0, cam)
            if rr is None:
                return F('; '.join(det + [f'frame {f} re-render failed ({note})']))
            s = ssim_render(rr, frame_at(bmp, f, RENDER_W, RENDER_H))
            ok &= s >= 0.75
            det.append(f'f{f} {cam} SSIM={s:.3f}{" " + note if note else ""}')
        return P(ok, '; '.join(det) + f' ({RENDER_W}x{RENDER_H}, {RENDER_SPP} spp re-render, marker bindings cleared)')
    item('M15', m15)

    def m12():
        if not rmp.exists() or not bmp.exists():
            return F('base or revision output.mp4 missing')
        prob, det = [], []
        rf = get_frames('rev')
        cuts, dd = get_cuts('rev')
        for c in CUTS_REV:
            if not any(abs(x - c) <= 1 for x in cuts):
                prob.append(f'no revision cut at {c}±1')
        extra = [x for x in cuts if all(abs(x - c) > 1 for c in CUTS_REV)]
        if extra:
            prob.append(f'extra revision cuts at {extra[:6]}')
        a, b = decode_audio(bmp), decode_audio(rmp)
        m = min(len(a), len(b))
        res = 10 * math.log10(float(((a[:m] - b[:m]) ** 2).mean()) / max(float((a[:m] ** 2).mean()), 1e-20) + 1e-20)
        det.append(f'audio null {res:.1f} dB')
        if res > -50:
            c = band_compare(a, b)
            if c is None or c['median'] > 0.25:
                prob.append(f'revision audio differs (null {res:.1f} dB, band {c})')
        try:
            d = need_dump()
            X = d['x04']
            if X.get('roll_missing'):
                prob.append('roll_T23_frames property missing')
            else:
                rl = X.get('roll') or {}
                worst = 0.0
                for f, row in rl.items():
                    for n, mm in row.items():
                        if f in d['mats'] and n in d['mats'][f]:
                            worst = max(worst, float(np.abs(np.array(mm)[:3, 3] - np.array(d['mats'][f][n])[:3, 3]).max()))
                det.append(f'roll -10 vs 0: max BOX/PALLET_TOP/FORKLIFT translation difference {worst * 1000:.2f} mm over {len(rl)} frames')
                if not rl or worst > 0.001:
                    prob.append('object world transforms change with roll_T23_frames=-10' if rl else 'roll comparison not measured')
        except _DumpFail as e:
            prob.append(str(e))
        if prob:
            return F('; '.join(prob + det))
        if time.time() - t_start > BUDGET_S:
            return F('; '.join(det) + '; grader time budget exhausted before the roll=-10 re-render')
        rr, note = blend_render(blend, offset() + 325, tmp, -10, 'CAM_S3')
        if rr is None:
            return F('; '.join(det) + f'; re-render of revision frame 325 (CAM_S3, roll -10) failed ({note})')
        s = ssim_render(rr, frame_at(rmp, 325, RENDER_W, RENDER_H))
        return P(s >= 0.75, '; '.join(det) + f'; revision frame 325 vs CAM_S3 re-render at world frame 325: SSIM={s:.3f} {note}')
    item('M12', m12)

    STATE['seconds'] = round(time.time() - t_start, 1)
    R['_x04_state'] = {'verdict': 'na', 'detail': json.dumps({k: STATE.get(k) for k in ('flat_index', 'dump_seconds', 'dump_warnings', 'seconds', 'b04_gate')})[:900]}
    return R


def postprocess(results, ctx):
    items = {i['id']: i for i in ctx['items']}

    def zero(iid, why):
        r = results.get(iid, {})
        if r.get('verdict') not in ('fail', 'na'):
            results[iid] = dict(r, verdict='fail', detail=f'[{why}] ' + str(r.get('detail', r.get('reason', '')))[:300], gated=True)
    # B04 structural failure (scene.blend missing / unopenable / required objects or roll property missing) ->
    # world3d and edit groups fail. README-only failures and inspection time-outs do not trigger the gate.
    if STATE.get('b04_gate') and results.get('B04', {}).get('verdict') == 'fail':
        for iid, it in items.items():
            if it.get('group') in ('world3d', 'edit'):
                zero(iid, 'group gate: B04 ' + str(STATE['b04_gate'])[:80])
    # measured flat/cartoon picture (G08 flat-block index) -> craft group fails
    if STATE.get('g08_flat') and results.get('G08', {}).get('source') == 'checks':
        for iid, it in items.items():
            if it.get('group') == 'craft' and iid != 'G08':
                zero(iid, 'craft gate: G08 flat-block index failed')
    return results
