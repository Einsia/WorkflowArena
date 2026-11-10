# -*- coding: utf-8 -*-
"""Deterministic checks for CDC-C-X01 (The First Bowl). See review/VERIFIER_NOTES.md and
review/rubric-cleanup-20261025.md.
Each item is independent; an exception inside an item => verdict fail with the traceback tail.
Since 2026-10-25 every item is decided here except the visual remainders of B09, G11 and G14 (B09/G11 are returned
only when their measured part fails; G14 is visual only) and M04 (weight 0, informational, never judged).
Film frame f is measured at Blender scene frame frame_start + f."""
import json, math, pathlib, re, sys, time, traceback
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import _cdc_lib as L
import _cdc_blend as B

REQ_EVENTS = ['lid_grip', 'lid_lift', 'ladle_in', 'pour_start', 'pour_end', 'line_door_start', 'line_door_end', 'door_close',
              'line_warn_start', 'line_warn_end', 'lin_touch', 'mei_release', 'line_thanks_start', 'line_thanks_end']
STEMS = ['speech', 'kitchen', 'hall']
CUTS_BASE, CUTS_REV = [180, 390, 540, 720], [180, 381, 531, 711]
SHOTS = {'S1': (0, 179), 'S2': (180, 389), 'S3': (390, 539), 'S4': (540, 719), 'S5': (720, 899)}
REQ_OBJ = {'MEI': 'MESH', 'LIN': 'MESH', 'MEI_RIG': 'ARMATURE', 'LIN_RIG': 'ARMATURE', 'POT': None, 'POT_LID': None,
           'LADLE': None, 'BOWL': None, 'DOOR': None, 'STOVE': None,
           **{f'CAM_S{i}': 'CAMERA' for i in range(1, 6)}}
CAMS = [f'CAM_S{i}' for i in range(1, 6)]
TRACK = ['POT_LID', 'DOOR', 'BOWL', 'POT', 'LADLE', 'MEI', 'LIN', 'MEI_RIG', 'LIN_RIG', 'STOVE'] + CAMS
WORDS = {'door': 3, 'warn': 3, 'thanks': 4}          # words per line as written in input/transcript.en.txt
SPEAKER = {'door': 'lin', 'warn': 'mei', 'thanks': 'lin'}
HANDISH = re.compile(r'hand|palm|wrist|thumb|index|middle|ring|pinky|little|finger|f_', re.I)
BUDGET_S = 2400          # no new re-render is started after this many seconds of checks (verifier timeout 3600 s)
STATE = {}


class _DumpFail(Exception):
    pass


# ------------------------------------------------------------------ Blender-side extra measurements (fluids, support)
EXTRA = r'''
import math, re
def _bvh_from(objs, dg, bpy):
    from mathutils.bvhtree import BVHTree
    V, P = [], []
    for o in objs:
        oe = o.evaluated_get(dg)
        try:
            me = oe.to_mesh()
        except Exception:
            continue
        try:
            if len(me.vertices) <= 8 and any(m.type == "FLUID" for m in o.modifiers):
                continue                                   # unbaked / box-shaped domain: no liquid geometry
            mw = o.matrix_world
            off = len(V)
            V += [tuple(mw @ v.co) for v in me.vertices]
            P += [tuple(off + i for i in p.vertices) for p in me.polygons]
        finally:
            oe.to_mesh_clear()
    if not P:
        return None, 0
    return BVHTree.FromPolygons(V, P), len(V)

def _inside(bvh, p):
    from mathutils import Vector
    hit = bvh.find_nearest(Vector(p))
    if hit[0] is None:
        return False, 1e9
    loc, nor, idx, dist = hit
    return (Vector(p) - loc).dot(nor) < 0, dist

def setup(ctx):
    bpy, D, cfg = ctx["bpy"], ctx["D"], ctx["cfg"]
    D["x01"] = {"liq": {}, "gas": {}, "support": {}}
    ctx["liq_objs"] = [o for o in bpy.data.objects if o.name.startswith("SOUP_DOMAIN") and o.type == "MESH"]
    ctx["gas_objs"] = [o for o in bpy.data.objects if o.name.startswith("STEAM_DOMAIN")
                       and any(m.type == "FLUID" and m.fluid_type == "DOMAIN" and m.domain_settings.domain_type == "GAS"
                               for m in o.modifiers)]
    D["x01"]["liq_objs"] = [o.name for o in ctx["liq_objs"]]
    D["x01"]["gas_objs"] = [o.name for o in ctx["gas_objs"]]
    dg = bpy.context.evaluated_depsgraph_get()
    def local_pts(name):
        o = bpy.data.objects.get(name)
        if o is None or o.type != "MESH":
            return None
        oe = o.evaluated_get(dg); me = oe.to_mesh()
        try:
            return [tuple(v.co) for v in me.vertices]
        finally:
            oe.to_mesh_clear()
    bp = local_pts("BOWL")                     # bowl inner cylinder in BOWL local coords
    if bp:
        xs = [p[0] for p in bp]; ys = [p[1] for p in bp]; zs = [p[2] for p in bp]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        r = 0.5 * min(max(xs) - min(xs), max(ys) - min(ys)) * 0.97
        ctx["bowl"] = (cx, cy, r, min(zs), max(zs))
        D["x01"]["bowl_local"] = ctx["bowl"]
    lp = local_pts("LADLE")                    # ladle head = end of the long axis with the larger lateral spread
    if lp and len(lp) >= 8:
        ext = [max(p[i] for p in lp) - min(p[i] for p in lp) for i in range(3)]
        ax = ext.index(max(ext)); lo = min(p[ax] for p in lp); hi = max(p[ax] for p in lp); L4 = (hi - lo) * 0.3
        ends = []
        oth = [i for i in range(3) if i != ax]
        for sel in ([p for p in lp if p[ax] <= lo + L4], [p for p in lp if p[ax] >= hi - L4]):
            if not sel:
                continue
            spread = sum(max(p[i] for p in sel) - min(p[i] for p in sel) for i in oth)
            c = [sum(p[i] for p in sel) / len(sel) for i in range(3)]
            rad = max(max(p[i] for p in sel) - min(p[i] for p in sel) for i in oth) / 2
            ends.append((spread, c, rad))
        sp, c, rad = max(ends, key=lambda e: e[0])
        ctx["head"] = (c, max(rad, 0.01))
        D["x01"]["head_local"] = ctx["head"]

def frame(ctx, f):
    bpy, D, cfg, dg = ctx["bpy"], ctx["D"], ctx["cfg"], ctx["dg"]
    X = cfg.get("x01", {})
    from mathutils import Vector
    sc = ctx["sc"]
    if "_sets" not in ctx:
        ctx["_sets"] = {k: set(X.get(k, [])) for k in ("support_frames", "liq_frames", "gas_frames")}
    S = ctx["_sets"]
    if f in S["support_frames"] and "BOWL" in bpy.data.objects:
        bo = bpy.data.objects["BOWL"]
        oe = bo.evaluated_get(dg); me = oe.to_mesh()
        try:
            mw = bo.matrix_world
            low = min((mw @ v.co for v in me.vertices), key=lambda q: q.z) if len(me.vertices) else None
        finally:
            oe.to_mesh_clear()
        if low is not None:
            hit, loc, nor, idx, ob, _ = sc.ray_cast(dg, low + Vector((0, 0, -0.0005)), Vector((0, 0, -1)), distance=0.2)
            D["x01"]["support"][f] = [round((low.z - loc.z), 5) if hit else None, ob.name if hit else None]
    if f in S["liq_frames"] and ctx.get("liq_objs"):
        vis = [o for o in ctx["liq_objs"] if not o.hide_render]
        bvh, nv = _bvh_from(vis, dg, bpy)
        rec = {"nv": nv}
        if bvh is not None:
            if "bowl" in ctx and "BOWL" in bpy.data.objects:
                cx, cy, r, z0, z1 = ctx["bowl"]; mw = bpy.data.objects["BOWL"].matrix_world
                n, nz, inside, cells = 12, 8, [], 0
                for i in range(n):
                    for j in range(n):
                        x = cx - r + (i + 0.5) * 2 * r / n; y = cy - r + (j + 0.5) * 2 * r / n
                        if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                            continue
                        for k in range(nz):
                            z = z0 + (k + 0.5) * (z1 - z0) / nz
                            cells += 1
                            pw = mw @ Vector((x, y, z))
                            if _inside(bvh, pw)[0]:
                                inside.append(tuple(pw))
                sx = mw.to_scale(); cellv = (2 * r / n) ** 2 * (z1 - z0) / nz * abs(sx.x * sx.y * sx.z)
                rec["bowl_ml"] = round(len(inside) * cellv * 1e6, 2)
                rec["bowl_cells"] = cells
                if inside:
                    rec["bowl_centroid"] = [round(sum(p[i] for p in inside) / len(inside), 5) for i in range(3)]
                rim = mw @ Vector((cx, cy, z1)); rec["bowl_rim_centre"] = [round(c, 5) for c in rim]
                hz = []
                for i in range(7):
                    for j in range(7):
                        x = cx - 0.7 * r + i * 1.4 * r / 6; y = cy - 0.7 * r + j * 1.4 * r / 6
                        top = mw @ Vector((x, y, z1)) + Vector((0, 0, 0.05))
                        loc, nor, idx, dist = bvh.ray_cast(top, Vector((0, 0, -1)), 0.06 + (z1 - z0) * abs(sx.z))
                        if loc is not None and loc.z <= (mw @ Vector((x, y, z1))).z + 0.01:
                            hz.append(loc.z)
                rec["surf_n"] = len(hz)
                if len(hz) >= 3:
                    rec["surf_range"] = round(max(hz) - min(hz), 5)
            if "head" in ctx and "LADLE" in bpy.data.objects:
                (hc, hr) = ctx["head"]; mw = bpy.data.objects["LADLE"].matrix_world
                cw = mw @ Vector(hc); rec["head_centre"] = [round(c, 5) for c in cw]
                rec["head_in_liquid"] = bool(_inside(bvh, cw)[0])
                cnt, tot = 0, 0
                for i in range(7):
                    for j in range(7):
                        for k in range(7):
                            off = Vector(((i - 3) / 3 * hr, (j - 3) / 3 * hr, (k - 3) / 3 * hr))
                            if off.length > hr:
                                continue
                            tot += 1
                            if _inside(bvh, mw @ (Vector(hc) + off))[0]:
                                cnt += 1
                sx = mw.to_scale()
                rec["head_ml"] = round(cnt / max(tot, 1) * 4 / 3 * math.pi * hr ** 3 * abs(sx.x * sx.y * sx.z) * 1e6, 2)
                if "bowl_rim_centre" in rec:
                    a = cw; b = Vector(rec["bowl_rim_centre"]); dmax = 0
                    for t in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
                        ins, dist = _inside(bvh, a.lerp(b, t))
                        dmax = max(dmax, 0 if ins else dist)
                    rec["stream_gap"] = round(dmax, 5)
        D["x01"]["liq"][f] = rec
    if f in S["gas_frames"] and ctx.get("gas_objs"):
        np = ctx["np"]
        tot, rows = 0.0, {}
        if np is None:
            # Debian Blender 4.3.2 runs on Python 3.13 without numpy, and reading Mantaflow grids of an unbaked domain
            # aborts this build anyway: nothing to measure on the Blender side.
            return
        for o in ctx["gas_objs"]:
            oe = o.evaluated_get(dg)
            md = [m for m in oe.modifiers if m.type == "FLUID"]
            if not md:
                continue
            ds = md[0].domain_settings
            try:
                den = np.array(ds.density_grid[:], dtype=np.float32)
                res = tuple(ds.domain_resolution)
            except Exception as ex:
                rows[o.name] = {"err": str(ex)[:120]}; continue
            s = float(den.sum()) if den.size else 0.0
            e = {"sum": round(s, 5), "res": res, "n": int(den.size)}
            if den.size == res[0] * res[1] * res[2] and s > 0:
                g = den.reshape(res[2], res[1], res[0])
                cz = np.array_split(np.arange(res[2]), 4); cy = np.array_split(np.arange(res[1]), 4); cx = np.array_split(np.arange(res[0]), 4)
                e["coarse"] = [round(float(g[np.ix_(a, b, c)].sum()), 5) for a in cz for b in cy for c in cx]
                try:
                    vel = np.array(ds.velocity_grid[:], dtype=np.float32)
                    if vel.size == 3 * den.size:
                        v = vel.reshape(-1, 3); R = o.matrix_world.to_3x3().normalized()
                        vzw = v[:, 0] * R[2][0] + v[:, 1] * R[2][1] + v[:, 2] * R[2][2]
                        e["vz"] = round(float((vzw * den).sum() / s), 6)
                except Exception:
                    pass
            rows[o.name] = e; tot += s
        D["x01"]["gas"][f] = {"total": round(tot, 5), "doms": rows}
'''


def P(v, d):
    return {'verdict': 'pass' if v else 'fail', 'detail': str(d)[:900]}


def F(d):
    return {'verdict': 'fail', 'detail': str(d)[:900]}


def _cache_cover(dom_entries, proj, frames_needed):
    """Fluid cache on disk inside project/: files whose names carry frame numbers covering >= 80% of frames_needed."""
    det = []
    for name, e in dom_entries:
        if not e.get('cache_dir_abs'):
            det.append(f'{name}: no cache directory'); continue
        cd = pathlib.Path(e['cache_dir_abs'])
        try:
            inside = cd.resolve().is_relative_to(proj.resolve())
        except Exception:
            inside = False
        if not cd.is_dir():
            det.append(f'{name}: cache dir {cd} not found'); continue
        nums, nfiles = set(), 0
        for p in cd.rglob('*'):
            if p.is_file():
                nfiles += 1
                for m in re.finditer(r'(?<!\d)(\d{3,6})(?!\d)', p.name):
                    nums.add(int(m.group(1)))
        need = set(frames_needed)
        cov = len(need & nums) / max(len(need), 1)
        det.append(f'{name}: cache {cd.name} inside project={inside} files={nfiles} frame coverage={cov:.0%}')
        if inside and cov >= 0.8:
            return True, det
    return False, det


def _steam_cache_evidence(d, proj, cache_root, lid_lift, fs):
    """Deterministic stand-in for the Mantaflow density measurement when the grids cannot be evaluated in the verifier
    image (Debian Blender 4.3.2 aborts in PyImport_AppendInittab on any FLUID evaluation, baked or not). Uses the VDB
    files Mantaflow itself wrote: they must exist inside project/ for the frames around lid_lift (both before and after),
    carry the density and velocity grids, and the field must change from frame to frame after the lid is lifted.
    Returns {'ok': bool, 'det': [..]}."""
    doms = [(n, e) for n, lst in (d.get('physics') or {}).items() if n.startswith('STEAM_DOMAIN') for e in lst
            if e.get('fluid_type') == 'DOMAIN' and e.get('domain_type') == 'GAS']
    if not doms:
        return {'ok': False, 'det': ['no STEAM_DOMAIN* gas fluid domain']}
    det, ok = [], False
    for name, e in doms:
        cd = e.get('cache_dir_abs')
        if not cd:
            det.append(f'{name}: no cache directory'); continue
        try:
            inside = pathlib.Path(cd).resolve().is_relative_to(proj.resolve())
        except Exception:
            inside = False
        frames = list(range(max(0, lid_lift - 15), lid_lift)) + list(range(lid_lift + 1, min(899, lid_lift + 15) + 1))
        ser = _vdb_series(cd, [fs + f for f in frames])
        got = {f - fs for f in ser}
        need = set(frames)
        cov = len(need & got) / max(len(need), 1)
        det.append(f'{name}: cache {pathlib.Path(cd).name} inside project={inside} vdb frames {len(got)}/{len(need)} around lid_lift')
        if not inside or cov < 0.8:
            continue
        grids = [set(s['grids']) for s in ser.values()]
        if not all({'density', 'velocity'} <= g for g in grids):
            det.append(f'{name}: VDB files lack density/velocity grids ({sorted(set().union(*grids))})')
            continue
        after = [ser[fs + f]['md5'] for f in sorted(f for f in frames if f > lid_lift) if fs + f in ser]
        if len(set(after)) < max(2, int(0.8 * len(after))):
            det.append(f'{name}: VDB payload identical across post-lift frames (frozen/static cache)')
            continue
        det.append(f'{name}: {len(set(after))}/{len(after)} post-lift VDB payloads distinct')
        ok = True
        break
    return {'ok': ok, 'det': det}


def _vdb_stats(path):
    """Header-level statistics of one OpenVDB file written by Mantaflow: total byte length and an MD5 of the payload,
    plus the file's grid names. Used when Mantaflow cannot be evaluated in the verifier image (Debian Blender 4.3.2
    aborts in PyImport_AppendInittab as soon as a FLUID modifier is evaluated): a baked steam cache then still proves
    that per-frame density/velocity fields were computed and shipped, and that the field evolves."""
    import hashlib
    b = pathlib.Path(path).read_bytes()
    names = sorted({m.group(1).decode('ascii', 'ignore') for m in re.finditer(rb'[\x00-\x20](density|velocity|flame|temperature|shadow)[\x00-\x20]', b)})
    return {'bytes': len(b), 'md5': hashlib.md5(b).hexdigest(), 'grids': names}


def _vdb_series(cache_dir, frames_needed, limit=240):
    """Per-frame VDB statistics for the frames_needed that exist in cache_dir/data (capped at `limit` files)."""
    d = pathlib.Path(cache_dir) / 'data'
    if not d.is_dir():
        return {}
    want = set(frames_needed)
    out = {}
    for p in sorted(d.glob('*.vdb')):
        m = re.search(r'(?<!\d)(\d{3,6})(?!\d)', p.name)
        if not m or int(m.group(1)) not in want:
            continue
        out[int(m.group(1))] = _vdb_stats(p)
        if len(out) >= limit:
            break
    return out


def _reduce_raw_gas(gas):
    """Gas grids dumped raw by the Blender side (no numpy there): total, 4x4x4 coarse sums and the density-weighted
    vertical velocity, computed here with numpy. Replaces the 'raw' entries in place."""
    for f, g in list(gas.items()):
        if not isinstance(g, dict) or not g.get('raw'):
            continue
        tot, rows = 0.0, {}
        for name, e in (g.get('doms') or {}).items():
            if 'den' not in e:
                rows[name] = {k: v for k, v in e.items() if k != 'raw'}; continue
            res = e.get('res') or [0, 0, 0]
            den = np.asarray(e['den'], np.float32)
            s_ = float(den.sum()) if den.size else 0.0
            row = {'sum': round(s_, 5), 'res': tuple(res), 'n': int(den.size)}
            if den.size == res[0] * res[1] * res[2] and s_ > 0:
                g3 = den.reshape(res[2], res[1], res[0])
                cz = np.array_split(np.arange(res[2]), 4); cy = np.array_split(np.arange(res[1]), 4)
                cx = np.array_split(np.arange(res[0]), 4)
                row['coarse'] = [round(float(g3[np.ix_(a, b, c)].sum()), 5) for a in cz for b in cy for c in cx]
                vel = np.asarray(e.get('vel') or [], np.float32)
                if vel.size == 3 * den.size:
                    R = np.asarray(e.get('rot') or [[1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
                    v = vel.reshape(-1, 3)
                    vzw = v[:, 0] * R[2][0] + v[:, 1] * R[2][1] + v[:, 2] * R[2][2]
                    row['vz'] = round(float((vzw * den).sum() / s_), 6)
            rows[name] = row; tot += s_
        gas[f] = {'total': round(tot, 5), 'doms': rows}


def run(ctx):
    R = {}
    t_start = time.time()
    root = L.find_root(ctx['out'])
    base, rev, proj = root / 'base', root / 'revision', root / 'project'
    bmp, rmp = base / 'output.mp4', rev / 'output.mp4'
    tmp = ctx['tmp']

    def item(iid, fn):
        try:
            v = fn()
            if v is not None:
                R[iid] = v
        except _DumpFail as e:
            R[iid] = F(str(e))
        except Exception as e:
            R[iid] = F(f'check error: {type(e).__name__}: {e} | {traceback.format_exc()[-300:]}')

    # ---------- B01/B02 ----------
    item('B01', lambda: P(*L.video_contract(bmp if bmp.exists() else None, 900)))
    item('B02', lambda: P(*L.video_contract(rmp if rmp.exists() else None, 891)))

    # ---------- B03 ----------
    def b03():
        det, ok = [], True
        for nm, p in (('base', bmp), ('revision', rmp)):
            if not p.exists():
                return F(f'{nm} master missing')
            I, pk = L.loudness(p, true_peak=False)
            nclip, amax = L.clipped_runs(p)
            o = (abs(I + 18) <= 2) and pk is not None and pk <= -1.0 and nclip == 0
            ok &= o
            det.append(f'{nm}: I={I} LUFS peak={pk} dBFS clipped_runs={nclip}')
        return P(ok, '; '.join(det))
    item('B03', b03)

    # ---------- B04 ----------
    def b04():
        det, ok = [], True
        for nm, d, dur in (('base', base, 30.0), ('revision', rev, 29.7)):
            for s in STEMS:
                o, t = L.stem_format(d / 'stems' / f'{s}.wav', dur)
                ok &= o; det.append(f'{nm}/{t}')
        return P(ok, '; '.join(det))
    item('B04', b04)

    # ---------- B05 / events ----------
    ev = {}
    evp = base / 'events.csv'

    def b05():
        if not evp.exists():
            STATE['events_bad'] = True
            return F('base/events.csv missing')
        try:
            hdr_ok, e, dup, bad = L.read_events(evp)
        except Exception as ex:
            STATE['events_bad'] = True
            return F(f'unparseable: {ex}')
        ev.update(e)
        miss = [k for k in REQ_EVENTS if k not in e]
        dupr = [k for k in dup if k in REQ_EVENTS]
        rng = [k for k in REQ_EVENTS if k in e and not (0 <= e[k] <= 899)]
        badr = [k for k in bad if k in REQ_EVENTS]
        ok = hdr_ok and not miss and not dupr and not rng and not badr
        return P(ok, f'header_ok={hdr_ok} missing={miss} duplicate={dupr} out_of_range={rng} non_integer={badr}')
    item('B05', b05)

    # ---------- B06 timeline structure (deterministic) ----------
    def tl_check(tl, starts, nfr):
        prob, nums = [], []

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
        shot_nums = [v for p, v in nums if re.search(r'shot|/s[1-5]\b|clip|range', p)]
        fr_or_s = lambda v, s: abs(v - s) <= 1 or abs(v * 30 - s) <= 1
        ok_shots = all(any(fr_or_s(v, s) for v in shot_nums) for s in starts[1:]) and \
            any(fr_or_s(v, nfr - 1) or fr_or_s(v, nfr) for v in shot_nums)
        if not ok_shots:
            prob.append(f'shot ranges starting {starts} and ending at {nfr} (frames or seconds) not found under a shot/clip/range key')
        txt = json.dumps(tl).lower()
        tr_paths = set(re.match(r'(.*?transition[^/\[]*(\[\d+\]|/[^/\[]+))', p).group(1) for p, v in nums
                       if re.match(r'(.*?transition[^/\[]*(\[\d+\]|/[^/\[]+))', p))
        n_tr = max(len(set(re.findall(r'"(t12|t23|t34|t45)"', txt))), len(tr_paths))
        if n_tr < 4:
            prob.append(f'4 transitions not found (found {n_tr}; expected a "transitions" list/dict or ids T12..T45)')
        for s in STEMS:
            if not any(s in p and re.search(r'in|out|start|end|region|offset|src|dst', p.split(s, 1)[-1] + p) for p, v in nums):
                prob.append(f'no numeric audio region (in/out) for stem {s}')
        if L.find_gains(tl, STEMS) is None:
            prob.append('master gains for speech/kitchen/hall not locatable (numeric key containing "gain" with the stem name)')
        return prob

    def b06():
        prob = []
        for nm, d, starts, nfr in (('base', base, [0, 180, 390, 540, 720], 900), ('revision', rev, [0, 180, 381, 531, 711], 891)):
            p = d / 'timeline.json'
            if not p.exists():
                return F(f'{nm}/timeline.json missing')
            try:
                tl = L.load_json(p)
            except Exception as ex:
                return F(f'{nm}/timeline.json unparseable: {ex}')
            prob += [f'{nm}: {x}' for x in tl_check(tl, starts, nfr)]
        return P(not prob, '; '.join(prob) if prob else 'both timelines: 5 shot ranges, 4 transitions, stem regions and gains present')
    item('B06', b06)

    # ---------- B08 (deterministic) ----------
    def b08():
        cr, qa = L.find_file(root, 'credits.md'), L.find_file(root, 'qa.md')
        prob = []
        if not cr:
            prob.append('credits.md missing')
        else:
            t = cr.read_text(encoding='utf-8', errors='ignore').lower()
            if 'blender' not in t:
                prob.append('credits.md does not name Blender')
            if not re.search(r'espeak|sox|text[- ]to[- ]speech|tts|synthes|recorded|voice|speech', t):
                prob.append('credits.md does not say how the lines were produced')
        if not qa:
            prob.append('qa.md missing')
        elif not qa.read_text(encoding='utf-8', errors='ignore').strip():
            prob.append('qa.md empty')
        hits = L.scan_text_tree(root)
        if hits:
            prob += hits[:5]
        return P(not prob, '; '.join(prob) if prob else 'credits names Blender and the speech method; qa.md present; no credentials/URL media')
    item('B08', b08)

    # ---------- M17 ----------
    def m17():
        if not ev:
            return F('events.csv missing/unparseable')
        miss = [k for k in REQ_EVENTS if k not in ev]
        if miss:
            return F(f'missing events {miss}')
        inr = lambda k, a, b: a <= ev[k] <= b
        conds = {
            'lid_grip<lid_lift<180': ev['lid_grip'] < ev['lid_lift'] < 180,
            'ladle_in<pour_start<pour_end in 180-389': ev['ladle_in'] < ev['pour_start'] < ev['pour_end'] and all(inr(k, 180, 389) for k in ('ladle_in', 'pour_start', 'pour_end')),
            'door_close in 390-539': inr('door_close', 390, 539),
            'line_warn in 540-719': inr('line_warn_start', 540, 719) and inr('line_warn_end', 540, 719),
            'lin_touch<mei_release, mei_release 720-899': ev['lin_touch'] < ev['mei_release'] and inr('mei_release', 720, 899),
            'line_thanks in 720-899': inr('line_thanks_start', 720, 899) and inr('line_thanks_end', 720, 899),
            'line start<end': all(ev[f'line_{n}_start'] < ev[f'line_{n}_end'] for n in ('door', 'warn', 'thanks')),
        }
        bad = [k for k, v in conds.items() if not v]
        return P(not bad, 'failed: ' + ', '.join(bad) if bad else 'all ordering/membership rules hold')
    item('M17', m17)

    # ---------- M01 / M12 (picture) ----------
    frames = {}

    def get_frames(nm, p):
        if nm not in frames:
            frames[nm] = L.gray_frames(p, 320, 180)
        return frames[nm]

    def edit_check(fr, expect, nframes, p):
        cuts, d, _fz, soft = L.detect_cuts(fr)
        prob = []
        if len(fr) != nframes: prob.append(f'decoded {len(fr)} frames')
        for c in expect:
            m = [x for x in cuts if abs(x - c) <= 1]
            if not m: prob.append(f'no cut at {c}±1')
            elif not L.hard_cut_ok(d, m[0]): prob.append(f'blend frames around cut {m[0]}')
        extra = [x for x in cuts if all(abs(x - c) > 1 for c in expect)]
        if extra: prob.append(f'extra cuts at {extra[:10]}')
        fz = L.freeze_runs(p, 6)
        if fz: prob.append(f'freeze (>=6 frames identical up to codec rounding) at (start, length) {fz[:5]}')
        soft = [k for k in soft if any(abs(k - c) <= 6 for c in expect)]
        if soft: prob.append(f'gradual transition/dissolve-like change near {soft[:5]}')
        return not prob, f"cuts={cuts[:12]}; " + ('; '.join(prob) if prob else 'ok')

    def m01():
        if not bmp.exists():
            return F('base/output.mp4 missing')
        return P(*edit_check(get_frames('base', bmp), CUTS_BASE, 900, bmp))
    item('M01', m01)

    def m12():
        if not (bmp.exists() and rmp.exists()):
            return F('base or revision master missing')
        b, r = get_frames('base', bmp), get_frames('rev', rmp)
        if len(r) != 891 or len(b) != 900:
            return F(f'frame counts base={len(b)} rev={len(r)}')
        p1 = [L.psnr(r[f], b[f]) for f in range(0, 381)]
        p2 = [L.psnr(r[f], b[f + 9]) for f in range(381, 891)]
        bad1 = [f for f, v in zip(range(0, 381), p1) if v < 30]
        bad2 = [f for f, v in zip(range(381, 891), p2) if v < 30]
        cuts, d, fz, soft = L.detect_cuts(r)
        cm = all(any(abs(x - c) <= 1 for x in cuts) for c in [381, 531, 711]) and all(any(abs(x - c) <= 1 for c in CUTS_REV) for x in cuts)
        ok = not bad1 and not bad2 and cm
        return P(ok, f'min PSNR rev0-380={min(p1):.1f} (bad n={len(bad1)} first {bad1[:3]}); rev381-890 vs base+9 min={min(p2):.1f} (bad n={len(bad2)} first {bad2[:3]}); rev cuts={cuts[:10]}. PSNR on 320x180 luma.')
    item('M12', m12)

    # ---------- audio ----------
    au = {}

    def A(ver, s):
        k = (ver, s)
        if k not in au:
            au[k] = L.load_audio((base if ver == 'base' else rev) / 'stems' / f'{s}.wav', 1)
        return au[k]

    def jcut(x, t_on):
        on = L.onset_time(x, -50, 10)
        prob = []
        if on is None:
            return False, 'hall stem never exceeds -50 dBFS'
        if abs(on - t_on) > 0.05: prob.append(f'onset {on:.3f}s (need {t_on}±0.05)')
        pre = x[:int((t_on - 0.05) * L.SR)]
        pre_db = float(L.env_db(pre, 480).max()) if len(pre) > 480 else -200
        if pre_db >= -60: prob.append(f'pre-onset level {pre_db:.1f} dBFS (need < -60)')
        return not prob, f'onset={on:.3f}s pre={pre_db:.1f}dBFS; ' + ('; '.join(prob) if prob else 'ok')

    item('M02', lambda: P(*jcut(A('base', 'hall'), 12.0)))

    def line_seg(n):
        """Measured (t0, t1) of line n: energy VAD (-45 dBFS, 10 ms, gaps <300 ms merged), segment nearest the
        declared start extended by segments starting before the declared end + 0.3 s."""
        segs = L.segments(A('base', 'speech'), -45, 10, 50, 300)
        ds, de = ev[f'line_{n}_start'] / 30, ev[f'line_{n}_end'] / 30
        if not segs:
            return None
        sg = min(segs, key=lambda s: abs(s[0] - ds))
        e1 = max([s[1] for s in segs if s[0] >= sg[0] and s[0] <= de + 0.3] + [sg[1]])
        return sg[0], e1

    def line_match(names, need_inside):
        if not ev or any(f'line_{n}_{e}' not in ev for n in names for e in ('start', 'end')):
            return F('events.csv missing line events')
        det, ok = [], True
        for n in names:
            ds, de = ev[f'line_{n}_start'] / 30, ev[f'line_{n}_end'] / 30
            m = line_seg(n)
            if m is None:
                return F('no speech detected in speech stem')
            s0, e1 = m
            o = abs(s0 - ds) <= 0.2 and abs(e1 - de) <= 0.2
            a, b = need_inside[n]
            ok &= o and (a <= ev[f'line_{n}_start'] <= b if n != 'door' else True)
            det.append(f'{n}: measured {s0:.2f}-{e1:.2f}s declared {ds:.2f}-{de:.2f}s')
        return ok, det

    def m03():
        if not ev or 'line_door_start' not in ev or 'line_door_end' not in ev:
            return F('events.csv missing line_door_*')
        r = line_match(['door'], {'door': (0, 899)})
        if isinstance(r, dict):
            return r
        ok, det = r
        segs = L.segments(A('base', 'speech'))
        ds = ev['line_door_start']
        sg = min(segs, key=lambda s: abs(s[0] - ds / 30))
        ok_start = 360 <= ds <= 389 and abs(sg[0] * 30 - ds) <= 6
        ok_end = 390 <= ev['line_door_end'] <= 539
        return P(ok_start and ok_end, f'declared start {ds}, end {ev["line_door_end"]}; measured onset frame {sg[0]*30:.1f}; ' + '; '.join(det))
    item('M03', m03)

    def m05():
        r = line_match(['warn', 'thanks'], {'warn': (540, 719), 'thanks': (720, 899)})
        if isinstance(r, dict):
            return r
        ok, det = r
        ok &= 540 <= ev['line_warn_start'] and ev['line_warn_end'] <= 719 and 720 <= ev['line_thanks_start'] and ev['line_thanks_end'] <= 899
        return P(ok, '; '.join(det) + ' (tolerance 6 frames = 0.2 s; energy VAD -45 dBFS)')
    item('M05', m05)

    # ---------- M06 voices (numpy F0) ----------
    def f0_track(x):
        """Autocorrelation F0 (Hz) per 40 ms frame / 10 ms hop, 70-400 Hz; voiced = normalised peak > 0.5."""
        w, h = int(0.04 * L.SR), int(0.01 * L.SR)
        lo, hi = int(L.SR / 400), int(L.SR / 70)
        out, thr = [], 10 ** (-40 / 20)
        for i in range(0, len(x) - w, h):
            fr = x[i:i + w].astype(np.float64)
            if np.sqrt((fr ** 2).mean()) < thr:
                continue
            fr = fr - fr.mean()
            ac = np.fft.irfft(np.abs(np.fft.rfft(fr, 2 * w)) ** 2)[:w]
            if ac[0] <= 0:
                continue
            ac = ac / ac[0]
            k = lo + int(np.argmax(ac[lo:hi]))
            if ac[k] > 0.5:
                for div in (3, 2):                      # octave-error guard: prefer a comparable shorter lag
                    k2 = int(round(k / div))
                    if k2 >= lo:
                        j = max(lo, k2 - 2) + int(np.argmax(ac[max(lo, k2 - 2):k2 + 3]))
                        if ac[j] > 0.9 * ac[k]:
                            k = j
                            break
                out.append(L.SR / k)
        out = np.array(out)
        if len(out):                                  # fold residual octave errors onto the median octave
            m = float(np.median(out))
            out = np.where(out > 1.6 * m, out / 2, np.where(out < m / 1.6, out * 2, out))
        return out

    def m06():
        if not ev or any(f'line_{n}_{e}' not in ev for n in WORDS for e in ('start', 'end')):
            return F('events.csv missing line events')
        x = A('base', 'speech')
        det, ok, med = [], True, {}
        for n in WORDS:
            m = line_seg(n)
            if m is None:
                return F('no speech detected in speech stem')
            t0, t1 = m
            dur = max(t1 - t0, 1e-3)
            wps = WORDS[n] / dur
            f0 = f0_track(x[int(t0 * L.SR):int(t1 * L.SR)])
            if len(f0) < 10:
                ok = False; det.append(f'{n}: <10 voiced frames'); continue
            st = 12 * np.log2(f0 / 100.0)
            sd, md = float(np.std(st)), float(np.median(st))
            med.setdefault(SPEAKER[n], []).append(md)
            ok &= 2.0 <= wps <= 4.5 and sd >= 1.5
            det.append(f'{n}: {wps:.2f} words/s over {dur:.2f}s, median F0 {100 * 2 ** (md / 12):.0f} Hz, F0 SD {sd:.2f} st')
        if 'mei' in med and 'lin' in med:
            diff = abs(np.median(med['mei']) - np.median(med['lin']))
            ok &= diff >= 2.0
            det.append(f'Mei vs Lin median F0 difference {diff:.2f} st (need >=2)')
        else:
            ok = False
        return P(ok, '; '.join(det))
    item('M06', m06)

    def kitchen_cont(x, pts, same_room_pt):
        det, ok = [], True
        for t in pts:
            seg = x[int((t - 0.5) * L.SR):int((t + 0.5) * L.SR)]
            e = L.env_db(seg, 960)  # 20 ms
            gap = (e < -70).any()
            pre, post = e[:25], e[25:]
            step = abs(float(np.percentile(post, 10)) - float(np.percentile(pre, 10)))
            lim = 3 if t == same_room_pt else 20
            o = (not gap) and step < lim + (0 if lim == 3 else 1e-9)
            ok &= o
            det.append(f'{t:.1f}s gap={bool(gap)} step={step:.1f}dB (lim {lim})')
        return ok, det

    def m10():
        ok1, d1 = kitchen_cont(A('base', 'kitchen'), [13.0, 18.0, 24.0], 24.0)
        ok2, d2 = kitchen_cont(A('rev', 'kitchen'), [12.7, 17.7, 23.7], 23.7)
        return P(ok1 and ok2, 'base: ' + ', '.join(d1) + ' | rev: ' + ', '.join(d2))
    item('M10', m10)

    def m11():
        det, ok = [], True
        for nm, d in (('base', base), ('revision', rev)):
            fit = L.stems_vs_mix(d / 'output.mp4', [d / 'stems' / f'{s}.wav' for s in STEMS])
            tl = L.load_json(d / 'timeline.json')
            dec = L.find_gains(tl, STEMS)
            rd = fit['residual_db']
            if dec is None:
                ok = False
                det.append(f'{nm}: fitted residual {rd:.1f} dB; declared master gains not locatable in timeline.json')
                continue
            gm, gd = L.gains_match(fit, dec, STEMS)
            ok &= (rd <= -25) and gm
            det.append(f'{nm}: residual(fitted) {rd:.1f} dB lag {fit["lag_samples"]}; {gd}')
        return P(ok, '; '.join(det))
    item('M11', m11)

    def m16():
        if 'lid_lift' not in ev:
            return F('events.csv missing lid_lift')
        x = A('base', 'kitchen')
        t = ev['lid_lift'] / 30
        tr, td = L.transient_at(x, t, 0.1, 12.0, 0.5, 5)
        bb = L.bandpass(x, 1000, 6000)
        pre = bb[max(0, int((t - 1) * L.SR)):int(t * L.SR)]
        post = bb[int(t * L.SR):int((t + 1) * L.SR)]
        inc = 10 * math.log10((post ** 2).mean() / max((pre ** 2).mean(), 1e-20)) if pre.size and post.size else -99
        return P(tr and inc >= 3, f'transient@lid_lift±3f: {td}; 1-6 kHz after/before = {inc:+.1f} dB')
    item('M16', m16)

    # ---------- B09 (music measured; on-screen overlays left to the judge) ----------
    def music_runs(x):
        """Start times of 3 s windows in which >=80% of 100 ms frames are tonal (strongest 80-4000 Hz peak of the
        2-frame-averaged spectrum >=15 dB above the median of the bins within +-1/3 octave) and >=3 pitch classes each
        dominate >=10% of the frames (melody/harmony, not a hum, whistle or band-limited noise)."""
        n, hop = 8192, 4800
        win = np.hanning(n)
        f = np.fft.rfftfreq(n, 1 / L.SR)
        band = np.where((f >= 80) & (f <= 4000))[0]
        specs = []
        for i in range(0, len(x) - n, hop):
            fr = x[i:i + n]
            specs.append(None if np.sqrt((fr ** 2).mean()) < 10 ** (-55 / 20) else np.abs(np.fft.rfft(fr * win)) ** 2)
        tonal, pcs = [], []
        for j, S in enumerate(specs):
            if S is None:
                tonal.append(False); pcs.append(-1); continue
            if j + 1 < len(specs) and specs[j + 1] is not None:
                S = S + specs[j + 1]
            k = band[int(np.argmax(S[band]))]
            lo, hi = int(k / 2 ** (1 / 3)), int(k * 2 ** (1 / 3)) + 1
            loc = S[max(1, lo):hi]
            tonal.append(bool(S[k] >= 10 ** 1.5 * np.median(loc)))
            pcs.append(int(round(12 * math.log2(f[k] / 440.0))) % 12)
        tonal, pcs = np.array(tonal, bool), np.array(pcs)
        kk = int(3.0 * L.SR / hop)
        hits = []
        for s0 in range(0, max(1, len(tonal) - kk + 1)):
            t = tonal[s0:s0 + kk]
            if t.size and t.mean() >= 0.8:
                vals, cnt = np.unique(pcs[s0:s0 + kk][t], return_counts=True)
                if (cnt >= 0.1 * kk).sum() >= 3:
                    hits.append(round(s0 * hop / L.SR, 1))
        return hits

    def b09():
        det = []
        for ver in ('base', 'rev'):
            for s in ('kitchen', 'hall'):
                h = music_runs(A(ver, s))
                if h:
                    det.append(f'{ver}/{s}: musical (tonal, >=3 pitch classes) 3 s windows starting at {h[:5]} s')
        return F('; '.join(det)) if det else None   # no music -> visual overlay part decided by the judge
    item('B09', b09)

    # ---------- blender-based ----------
    blend = proj / 'scene.blend'
    D = None

    def get_dump():
        nonlocal D
        if D is not None:
            return D
        if not blend.exists():
            D = {'ok': False, 'opened': False, 'error': 'project/scene.blend missing'}
            STATE['blend_open_fail'] = True
            return D
        if not B.blender_ok():
            raise RuntimeError('blender not on PATH in the verifier image (grader problem)')
        evs = {k: v for k, v in ev.items() if isinstance(v, int)}
        g = lambda k, dflt: int(min(899, max(0, evs.get(k, dflt))))
        liq = set(range(180, 900, 3))
        liq |= set(range(max(180, g('ladle_in', 200) - 5), min(899, g('pour_end', 380) + 6)))
        liq |= set(range(max(180, g('lin_touch', 730) - 3), min(899, g('mei_release', 760) + 4)))
        gas = set(range(max(0, g('lid_lift', 150) - 20), min(899, g('lid_lift', 150) + 21))) | set(range(180, 390, 10)) | set(range(720, 900, 10))
        cfg = {'film_frames': list(range(0, 900)), 'track': TRACK, 'rigs': ['MEI_RIG', 'LIN_RIG'], 'cams': CAMS,
               'samples': {'POT_LID': 1500, 'BOWL': 1500, 'LADLE': 1200, 'POT': 800},
               'bbox_world': {'LIN': sorted(set(range(540, 720, 10)) | {0, 719, 720}), 'MEI': [0, 719, 720]},
               'extra': EXTRA,
               'x01': {'liq_frames': sorted(liq), 'gas_frames': sorted(gas), 'support_frames': list(range(180, 900))}}
        D = B.rich_dump(blend, cfg, tmp, timeout=1500, tag='base')
        X = D.get('x01') if D.get('ok') else None
        if isinstance(X, dict):
            for k in ('liq', 'gas', 'support'):
                X[k] = {int(f): v for f, v in (X.get(k) or {}).items()}
            _reduce_raw_gas(X.get('gas') or {})
        if not D.get('ok') and D.get('opened') is False:
            STATE['blend_open_fail'] = True
        STATE['dump_warnings'] = (D.get('warnings') or [])[:10]
        STATE['dump_seconds'] = D.get('wall_seconds')
        return D

    def need_dump():
        d = get_dump()
        if not d.get('ok'):
            raise _DumpFail('Blender inspection of project/scene.blend failed: ' + str(d.get('error'))[-300:])
        return d

    def b07():
        readme = L.find_file(proj, 'README.md')
        rtxt = readme.read_text(encoding='utf-8', errors='ignore') if readme else ''
        d = get_dump()
        if not d.get('ok'):
            if d.get('opened') is False:
                return F('scene.blend missing or failed to open headless: ' + str(d.get('error'))[-400:])
            return F('Blender inspection failed (not a file-open error; GG1 not applied): ' + str(d.get('error'))[-400:])
        obj = d['objects']
        prob = []
        for n, t in REQ_OBJ.items():
            if n not in obj: prob.append(f'{n} missing')
            elif t and obj[n] != t: prob.append(f'{n} type {obj[n]}')
        for pre in ('SOUP_DOMAIN', 'STEAM_DOMAIN'):
            if not any(k.startswith(pre) for k in obj): prob.append(f'no {pre}*')
        if 'revision_trim_frames' not in d['scene_props']: prob.append('scene prop revision_trim_frames missing')
        if not readme:
            prob.append('README.md missing')
        elif not any(re.search(r'\bblender\b', ln, re.I) and re.search(r'(^|\s)(-b|--background)(\s|$)', ln) for ln in rtxt.splitlines()):
            prob.append('README has no `blender ... -b/--background ...` command line')
        return P(not prob, f"Blender {d.get('version')}; frame_start={d['frame_range'][0]}; " + ('; '.join(prob) if prob else 'all named objects/types present'))
    item('B07', b07)

    # helpers on the dump -------------------------------------------------
    def has(d, *names):
        miss = [n for n in names if n not in d['objects']]
        if miss:
            raise _DumpFail(f'required objects missing: {miss}')

    def mw(d, n, f):
        return B.M(d, n, f)

    def pts_world(d, n, f, k=None):
        s = d['samples'].get(n)
        if not s:
            raise _DumpFail(f'{n}: no mesh geometry to sample')
        p = np.array(s, float)
        if k:
            p = p[::max(1, len(p) // k)]
        return B.xf(mw(d, n, f), p)

    def hand_segs(d, rig, f, side=None):
        names = [b for b in d['sampled_bones'].get(rig, []) if HANDISH.search(b) and (side is None or B.side_of(b) == side)]
        return B.bone_segs(d, rig, f, set(names))

    def hand_dist(d, rig, obj, f, side=None, pts=None):
        ks, segs = hand_segs(d, rig, f, side)
        if not len(segs):
            return np.inf, None
        P_ = pts if pts is not None else pts_world(d, obj, f)
        dd = B.seg_point_dist(segs, P_)
        i = int(np.argmin(dd))
        return float(dd[i]), ks[i]

    def knob_local(d):
        if 'POT_LID' not in d['samples']:
            raise _DumpFail('POT_LID: no mesh geometry to sample')
        p = np.array(d['samples']['POT_LID'], float)
        c = np.array(d['bbox_local']['POT_LID'], float).mean(0)
        top = p[:, 2].max()
        sel = p[(p[:, 2] >= top - 0.03) & (np.hypot(p[:, 0] - c[0], p[:, 1] - c[1]) <= 0.03)]
        if len(sel) < 5:
            hp = p[np.argmax(p[:, 2])]
            sel = p[np.linalg.norm(p - hp, axis=1) <= 0.04]
        return sel

    def visible(d, cam, f, P_):
        uvz = B.project(d, cam, f, P_)
        inside = (uvz[:, 2] > 0) & (uvz[:, 0] >= 0) & (uvz[:, 0] <= 1) & (uvz[:, 1] >= 0) & (uvz[:, 1] <= 1)
        return bool(inside.any()), uvz

    def evreq(*ks):
        miss = [k for k in ks if k not in ev]
        if miss:
            raise _DumpFail(f'events.csv missing {miss}')
        return [ev[k] for k in ks]

    # ---------- M08 camera grammar ----------
    def m08():
        d = need_dump(); has(d, *CAMS)
        prob, det = [], []

        def series(cam, a, b):
            fs = list(range(a, b + 1))
            ms = [mw(d, cam, f) for f in fs]
            pos = np.array([m[:3, 3] for m in ms])
            pit = np.array([B.cam_pitch(m) for m in ms])
            ci = [d['cams'][cam][f] for f in fs]
            return ms, pos, pit, ci, np.array([c['lens'] for c in ci])
        ms, pos, pit, ci, lens = series('CAM_S1', 0, 179)
        disp = float(np.linalg.norm(pos - pos[0], axis=1).max())
        dofok = all((not c['dof']) or c['fstop'] >= 5.6 for c in ci)
        if not (1.1 <= pos[:, 2].mean() <= 1.9 and np.abs(pit).max() <= 10 and disp < 0.01 and np.ptp(lens) < 0.01 and dofok): prob.append('S1')
        det.append(f'S1 h={pos[:,2].mean():.2f}m pitch {pit.min():.1f}..{pit.max():.1f} disp {disp*100:.1f}cm lens_range {np.ptp(lens):.3f} deep_focus={dofok}')
        ms, pos, pit, ci, lens = series('CAM_S2', 180, 389)
        disp = float(np.linalg.norm(pos - pos[0], axis=1).max())
        dof2 = all(c['dof'] and c['fstop'] <= 4 for c in ci)
        if not (pit.max() <= -30 and disp < 0.01 and dof2): prob.append('S2')
        det.append(f'S2 pitch max {pit.max():.1f} disp {disp*100:.1f}cm dof f<=4={dof2}')
        ms, pos, pit, ci, lens = series('CAM_S3', 390, 539)
        k = 15
        ker = np.ones(k) / k
        smooth = lambda a: np.stack([np.convolve(np.pad(a[:, i], (k // 2, k // 2), mode='edge'), ker, 'valid') for i in range(3)], 1)
        jit = float(np.linalg.norm(pos - smooth(pos), axis=1).max())
        fw = np.array([B.cam_forward(m) for m in ms]); fsm = smooth(fw)
        rj = float(np.degrees(np.arccos(np.clip((fw * fsm).sum(1) / np.linalg.norm(fsm, axis=1), -1, 1))).max())
        if not (1.1 <= pos[:, 2].mean() <= 1.9 and np.abs(pit).max() <= 10 and np.ptp(lens) < 0.01 and (jit >= 0.001 or rj >= 0.1) and jit <= 0.06): prob.append('S3')
        det.append(f'S3 h={pos[:,2].mean():.2f}m pitch {pit.min():.1f}..{pit.max():.1f} jitter {jit*1000:.1f}mm/{rj:.2f}deg lens_range {np.ptp(lens):.3f}')
        ms, pos, pit, ci, lens = series('CAM_S4', 540, 719)
        has(d, 'MEI', 'LIN')
        target = mw(d, 'MEI_RIG' if 'MEI_RIG' in d['objects'] else 'MEI', 540)[:3, 3]
        dist = np.linalg.norm(pos - target, axis=1)
        dolly = float(dist[0] - dist[-1])
        areas, sides = [], []
        for f, bb in sorted(d['bbox_world'].get('LIN', {}).items()):
            if 540 <= f <= 719:
                box, area, vis = B.proj_box(B.project(d, 'CAM_S4', f, np.array(bb)))
                areas.append(area)
                if box:
                    sides.append((max(box[0], 0) + min(box[2], 1)) / 2)
        ma = float(np.median(areas)) if areas else 0.0
        mside = float(np.median(sides)) if sides else 0.5
        if not (dolly >= 0.08 and np.ptp(lens) < 0.01 and all(c['dof'] for c in ci) and 0.05 <= ma <= 0.45 and (mside <= 0.4 or mside >= 0.6)): prob.append('S4')
        det.append(f'S4 dolly toward MEI {dolly*100:.1f}cm, LIN bbox area {ma:.2f} centre_u {mside:.2f}, lens_range {np.ptp(lens):.3f}, dof={all(c["dof"] for c in ci)}')
        ms, pos, pit, ci, lens = series('CAM_S5', 720, 899)
        disp = float(np.linalg.norm(pos - pos[0], axis=1).max())
        mono = bool(np.all(np.diff(pit) >= -0.05))
        if not (disp < 0.02 and mono and (pit[-1] - pit[0]) >= 3 and all(c['dof'] for c in ci)): prob.append('S5')
        det.append(f'S5 disp {disp*100:.1f}cm tilt {pit[0]:.1f}->{pit[-1]:.1f} monotone={mono} dof={all(c["dof"] for c in ci)}')
        return P(not prob, ('failed: ' + ','.join(prob) + ' | ' if prob else '') + '; '.join(det))
    item('M08', m08)

    # ---------- M15 rigs ----------
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

    def mouth_anim(d, rig, char):
        arm = d['armatures'].get(rig, {})
        bones = [b for b in arm.get('keyed', []) if re.search(r'jaw|chin|mouth|lip', b, re.I)]
        sk = []
        for k, lst in d['fcurves'].items():
            if k.endswith('|shape_keys'):
                o = k.split('|')[0]
                if o.upper().startswith(char) or rig in d['armature_mods'].get(o, []):
                    sk += [e['path'] for e in lst if re.search(r'jaw|mouth|lip|open|viseme|phon|mbp|_aa|_oh|_ee', e['path'], re.I)
                           and (e.get('n', 0) >= 2 or 'driver' in e)]
        return bones, sk

    def m15():
        d = need_dump(); has(d, 'MEI', 'LIN', 'MEI_RIG', 'LIN_RIG')
        prob, det = [], []
        for ch, rig in (('MEI', 'MEI_RIG'), ('LIN', 'LIN_RIG')):
            par = d['parents'].get(ch, [None, None, None])
            driven = rig in d['armature_mods'].get(ch, []) or (par[0] == rig and par[1] == 'ARMATURE')
            if not driven: prob.append(f'{ch} not deformed by {rig}')
            cnt, sig = finger_count(d, rig)
            if min(cnt.get('L', 0), cnt.get('R', 0)) < 4: prob.append(f'{rig} keyed finger chains per hand {cnt} (need >=4 each)')
            if min(sig.get('L', 0), sig.get('R', 0)) < 2: prob.append(f'{rig} fingers not individually animated (distinct finger curves per hand {sig})')
            bones, sk = mouth_anim(d, rig, ch)
            if not bones and not sk: prob.append(f'{ch}: no keyed jaw/lip bone or mouth shape key')
            bb = np.array(d['bbox_world'].get(ch, {}).get(0) or [[0, 0, 0]] * 8, float)
            ext = bb.max(0) - bb.min(0)
            if ext.min() < 0.1: prob.append(f'{ch} mesh is flat/too small (bbox {np.round(ext, 2).tolist()} m)')
            det.append(f'{ch}: driven={driven} fingers={cnt} distinct={sig} jaw_bones={bones[:3]} mouth_keys={len(sk)}')
        return P(not prob, ('; '.join(prob) + ' | ' if prob else '') + '; '.join(det))
    item('M15', m15)

    # ---------- M07 lip sync ----------
    def m07():
        d = need_dump(); has(d, 'MEI_RIG', 'LIN_RIG')
        x = A('base', 'speech')
        hop = L.SR // 30
        nf = len(x) // hop
        env = np.sqrt((x[:nf * hop].astype(np.float64).reshape(nf, hop) ** 2).mean(1))
        det, ok = [], True
        for ch, rig, (a, b) in (('LIN', 'LIN_RIG', SHOTS['S3']), ('MEI', 'MEI_RIG', SHOTS['S4'])):
            chans = {}
            for f in range(a, b + 1):
                for bn, (ang, loc) in d['chan'].get(rig, {}).get(f, {}).items():
                    chans.setdefault('bone:' + bn + ':rot', []).append(ang)
                    chans.setdefault('bone:' + bn + ':loc', []).append(loc)
            for o, per in d['sk'].items():
                if o.upper().startswith(ch) or rig in d['armature_mods'].get(o, []):
                    for f in range(a, b + 1):
                        for k, v in per.get(f, {}).items():
                            chans.setdefault('sk:' + o + ':' + k, []).append(v)
            e = env[a:b + 1]
            best = (-2.0, None, None)
            for nm, s in chans.items():
                s = np.array(s, float)
                if len(s) != len(e) or np.ptp(s) < 1e-6:
                    continue
                for lag in range(-2, 3):          # +-2 frames = +-67 ms (<= 80 ms)
                    u, v = (s[lag:], e[:len(e) - lag]) if lag >= 0 else (s[:lag], e[-lag:])
                    if np.std(u) < 1e-9 or np.std(v) < 1e-12:
                        continue
                    r = float(np.corrcoef(u, v)[0, 1])
                    if r > best[0]:
                        best = (r, nm, lag)
            ok &= best[0] >= 0.4
            det.append(f'{ch} frames {a}-{b}: best r={best[0]:.2f} channel={best[1]} lag={best[2]} frames ({len(chans)} mouth channels)')
        return P(ok, '; '.join(det))
    item('M07', m07)

    # ---------- M09 door ----------
    def m09():
        if 'door_close' not in ev:
            return F('door_close not declared')
        d = need_dump(); has(d, 'DOOR')
        sp = {f: B.rot_angle(B.rot_of(mw(d, 'DOOR', f - 1)), B.rot_of(mw(d, 'DOOR', f))) for f in range(1, 900)}
        moving = [f for f, a in sp.items() if a > 0.05 and 300 <= f <= 600]
        if not moving:
            return F('DOOR does not rotate in frames 300-600')
        stop = max(moving)
        dc = ev['door_close']
        okd = abs(stop - dc) <= 2
        tr, td = L.transient_at(A('base', 'hall'), dc / 30, 2 / 30, 12.0, 0.5, 5)
        return P(okd and tr, f'DOOR rotation stops at frame {stop} (declared door_close {dc}); hall transient: {td}')
    item('M09', m09)

    # ---------- G01 lid grip ----------
    def lid_leave_frame(d):
        lid = np.array(d['samples']['POT_LID'], float)[::10]
        for f in range(180, 390):
            if not visible(d, 'CAM_S2', f, B.xf(mw(d, 'POT_LID', f), lid))[0]:
                return f
        return 389

    def g01():
        lg, = evreq('lid_grip')
        d = need_dump(); has(d, 'POT_LID', 'MEI_RIG', 'CAM_S2')
        kl = knob_local(d)
        prob = []
        dg, bn = hand_dist(d, 'MEI_RIG', 'POT_LID', lg, pts=B.xf(mw(d, 'POT_LID', lg), kl))
        if dg > 0.015: prob.append(f'at lid_grip {lg} nearest MEI hand bone {bn} is {dg*100:.1f} cm from the knob (need <=1.5)')
        p0 = mw(d, 'POT_LID', 0)[:3, 3]
        mv = max([float(np.linalg.norm(mw(d, 'POT_LID', f)[:3, 3] - p0)) for f in range(0, max(1, lg))] + [0])
        if mv >= 0.002: prob.append(f'lid moves {mv*1000:.1f} mm before lid_grip')
        end = lid_leave_frame(d)
        worst = (0, None)
        for f in range(lg, end):
            dd, _ = hand_dist(d, 'MEI_RIG', 'POT_LID', f, pts=B.xf(mw(d, 'POT_LID', f), kl))
            if dd > worst[0]:
                worst = (dd, f)
        if worst[0] > 0.02: prob.append(f'hand-knob distance {worst[0]*100:.1f} cm at frame {worst[1]} (need <=2 cm until the lid leaves CAM_S2 at {end})')
        return P(not prob, '; '.join(prob) if prob else f'grip {dg*100:.1f} cm at {lg}; lid static before; max hand-knob {worst[0]*100:.1f} cm until frame {end}')
    item('G01', g01)

    # ---------- G02 lift + steam ----------
    def gas_total(d, f):
        g = d.get('x01', {}).get('gas', {}).get(f)
        return None if g is None else g.get('total', 0.0)

    def g02():
        ll, = evreq('lid_lift')
        d = need_dump(); has(d, 'POT_LID', 'POT')
        lid = np.array(d['samples']['POT_LID'], float)[::5]
        pot = np.array(d['samples']['POT'], float)[::5]
        gap = lambda f: B.xf(mw(d, 'POT_LID', f), lid)[:, 2].min() - B.xf(mw(d, 'POT', f), pot)[:, 2].max()
        g0 = gap(0)
        first = next((f for f in range(0, 900) if gap(f) - g0 > 0.005), None)
        prob = []
        if first is None or abs(first - ll) > 2: prob.append(f'lid first >5 mm off the rim at frame {first} (declared lid_lift {ll}, need ±2)')
        z = [mw(d, 'POT_LID', f)[2, 3] for f in range(175, 186)]
        if not all(b - a > 0 for a, b in zip(z, z[1:])): prob.append('lid not rising through every frame 175-185')
        pre = [x for x in (gas_total(d, f) for f in range(max(0, ll - 15), ll)) if x is not None]
        post = [x for x in (gas_total(d, f) for f in range(ll + 1, min(899, ll + 15) + 1)) if x is not None]
        if not d.get('x01', {}).get('gas_objs'):
            prob.append('no STEAM_DOMAIN* gas fluid domain')
        elif not post or max(post) <= 0:
            # Mantaflow cannot be evaluated in this verifier image: fall back to the shipped VDB cache
            st = _steam_cache_evidence(d, proj, proj, ll, d.get('frame_offset', 0))
            if st.get('ok'):
                return P(not prob, '; '.join(prob + st['det']) if prob else f'lid off rim first at {first}; rising 175-185; ' + '; '.join(st['det']))
            prob.append('no steam density readable after lid_lift (cache missing/not baked)'
                        + (' (FLUID modifiers had to be disabled: this Blender build aborts when Mantaflow is evaluated)' if d.get('mantaflow_disabled') else '')
                        + (('; cache: ' + '; '.join(st['det'])) if st.get('det') else ''))
        else:
            ratio = max(post) / max(float(np.mean(pre)) if pre else 0.0, 1e-9)
            if ratio < 3: prob.append(f'steam density after/before lid_lift = {ratio:.2f} (need >=3)')
        return P(not prob, '; '.join(prob) if prob else f'lid off rim first at {first}; rising 175-185; steam density after/before >= 3x')
    item('G02', g02)

    # ---------- G03 T12 match on action ----------
    def g03():
        d = need_dump(); has(d, 'POT_LID', 'CAM_S1', 'CAM_S2')
        t = {f: mw(d, 'POT_LID', f)[:3, 3] for f in (178, 179, 180, 181)}
        vb, va = t[179] - t[178], t[181] - t[180]
        nb, na = np.linalg.norm(vb), np.linalg.norm(va)
        if nb < 1e-5 or na < 1e-5:
            return F(f'lid not moving at the cut (|v|={nb*1000:.2f}/{na*1000:.2f} mm/frame)')
        prob = []
        ang = math.degrees(math.acos(max(-1, min(1, float(vb @ va) / (nb * na)))))
        ratio = na / nb
        jump = float(np.linalg.norm(t[180] - t[179] - (vb + va) / 2))
        if ang > 45: prob.append(f'velocity direction change {ang:.0f} deg')
        if not 0.5 <= ratio <= 2: prob.append(f'speed ratio {ratio:.2f}')
        if jump >= 0.03: prob.append(f'extra jump {jump*100:.1f} cm')
        lid = np.array(d['samples']['POT_LID'], float)[::10]
        c = lid.mean(0, keepdims=True)
        v1 = [B.project(d, 'CAM_S1', f, B.xf(mw(d, 'POT_LID', f), c))[0][1] for f in (178, 179)]
        v2 = [B.project(d, 'CAM_S2', f, B.xf(mw(d, 'POT_LID', f), c))[0][1] for f in (180, 181)]
        if not v1[1] > v1[0]: prob.append('lid not moving screen-up in CAM_S1 at 178->179')
        if not v2[1] > v2[0]: prob.append('lid not moving screen-up in CAM_S2 at 180->181')
        if not visible(d, 'CAM_S2', 180, B.xf(mw(d, 'POT_LID', 180), lid))[0]: prob.append('lid not visible in CAM_S2 at 180')
        return P(not prob, '; '.join(prob) if prob else f'angle {ang:.0f} deg, speed ratio {ratio:.2f}, extra jump {jump*100:.2f} cm, screen-up in both cameras, visible at 180')
    item('G03', g03)

    # ---------- G04 / G05 / G13 soup ----------
    def liq(d, f):
        return d.get('x01', {}).get('liq', {}).get(f)

    def mei_side(d):
        return 'R' if any(B.side_of(b) == 'R' and HANDISH.search(b) for b in d['sampled_bones'].get('MEI_RIG', [])) else None

    def g04():
        li, ps, pe = evreq('ladle_in', 'pour_start', 'pour_end')
        d = need_dump(); has(d, 'LADLE', 'MEI_RIG')
        prob = []
        side = mei_side(d)
        worst = (0, None)
        for f in range(li, pe + 1):
            dd, _ = hand_dist(d, 'MEI_RIG', 'LADLE', f, side)
            if dd > worst[0]:
                worst = (dd, f)
        if worst[0] > 0.02: prob.append(f'MEI {"right " if side else ""}hand {worst[0]*100:.1f} cm from LADLE at frame {worst[1]} (need <=2 cm ladle_in..pour_end)')
        if not d.get('x01', {}).get('liq_objs'):
            return F('; '.join(prob + ['no SOUP_DOMAIN* liquid geometry']))
        r = liq(d, li) or {}
        if not r.get('head_in_liquid'): prob.append(f'ladle head not inside the liquid at ladle_in {li}')
        fr = [f for f in range(li + 1, ps + 1) if liq(d, f) is not None]
        full = [f for f in fr if (liq(d, f).get('head_ml') or 0) >= 1.0]
        if not fr or len(full) < 0.5 * len(fr): prob.append(f'liquid (>=1 mL) in the ladle head in {len(full)}/{len(fr)} sampled frames ladle_in..pour_start (need >=50%)')
        return P(not prob, '; '.join(prob) if prob else f'held (max {worst[0]*100:.1f} cm); head in liquid at ladle_in; filled in {len(full)}/{len(fr)} frames')
    item('G04', g04)

    def g05():
        ps, pe = evreq('pour_start', 'pour_end')
        d = need_dump(); has(d, 'LADLE', 'BOWL')
        if not d.get('x01', {}).get('liq_objs'):
            return F('no SOUP_DOMAIN* liquid geometry')
        fr = [f for f in range(ps, pe + 1) if liq(d, f) is not None]
        if not fr:
            return F('no sampled liquid frames in the pour window')
        conn = [f for f in fr if liq(d, f).get('stream_gap', 1) <= 0.015]
        vols = [liq(d, f).get('bowl_ml', 0) for f in fr]
        runmax, mono = 0, True
        for v in vols:
            if v < 0.95 * runmax - 5.0:              # 5% or 5 mL (grid-sampling resolution ~1.3 mL/cell)
                mono = False
            runmax = max(runmax, v)
        v_end = vols[-1]
        ladle0 = (liq(d, ps) or {}).get('head_ml', 0)
        prob = []
        if len(conn) < 0.7 * len(fr): prob.append(f'stream ladle->bowl connected in {len(conn)}/{len(fr)} frames (need >=70%)')
        if not mono: prob.append(f'bowl volume drops >5% (and >5 mL) below its running maximum during the pour ({vols[:6]}...)')
        if v_end < 30 or v_end < 0.5 * ladle0: prob.append(f'bowl {v_end:.0f} mL at pour_end (need >=30 and >=50% of ladle {ladle0:.0f} mL at pour_start)')
        return P(not prob, '; '.join(prob) if prob else f'stream {len(conn)}/{len(fr)} frames; bowl {vols[0]:.0f}->{v_end:.0f} mL; ladle at pour_start {ladle0:.0f} mL')
    item('G05', g05)

    def g13():
        pe, lt, mr = evreq('pour_end', 'lin_touch', 'mei_release')
        d = need_dump(); has(d, 'BOWL')
        if not d.get('x01', {}).get('liq_objs'):
            return F('no SOUP_DOMAIN* liquid geometry')
        fr = [f for f in range(pe, 900) if liq(d, f) is not None]
        v0 = (liq(d, pe) or {}).get('bowl_ml', 0)
        prob, far, lost = [], [], []
        for f in fr:
            r = liq(d, f)
            if r.get('bowl_ml', 0) < 0.5 * v0 or 'bowl_centroid' not in r:
                lost.append(f); continue
            c, rc = np.array(r['bowl_centroid']), np.array(r['bowl_rim_centre'])
            if np.hypot(*(c - rc)[:2]) > 0.03:
                far.append(f)
        if v0 <= 0: prob.append('no liquid in the bowl at pour_end')
        if lost: prob.append(f'bowl liquid below 50% of the pour_end volume at frames {lost[:5]}')
        if far: prob.append(f'bowl liquid centroid >3 cm from the bowl axis at {far[:5]}')
        rng = [liq(d, f).get('surf_range', 0) for f in range(lt, mr + 1) if liq(d, f) is not None]
        if not rng or max(rng) < 0.002: prob.append(f'liquid surface height range max {max(rng) * 1000 if rng else 0:.1f} mm during the handover (need >=2 mm)')
        return P(not prob, '; '.join(prob) if prob else f'liquid follows the bowl in {len(fr)} sampled frames; surface range max {max(rng)*1000:.1f} mm')
    item('G13', g13)

    # ---------- G06 / G07 bowl support + handover ----------
    def contact_series(d, rig, a, b):
        return {f: hand_dist(d, rig, 'BOWL', f, pts=pts_world(d, 'BOWL', f, 600))[0] for f in range(a, b + 1)}

    def g06():
        pe, = evreq('pour_end')
        d = need_dump(); has(d, 'BOWL', 'MEI_RIG', 'LIN_RIG')
        cm, cl = contact_series(d, 'MEI_RIG', pe, 899), contact_series(d, 'LIN_RIG', pe, 899)
        sup = d.get('x01', {}).get('support', {})
        bad = []
        for f in range(pe, 900):
            s = sup.get(f, [None, None])
            rest = s[0] is not None and s[0] <= 0.005
            if not (min(cm[f], cl[f]) <= 0.02 or rest):
                bad.append(f)
        return P(not bad, f'unsupported frames {bad[:8]} (n={len(bad)}; no hand bone <=2 cm and no surface <=5 mm below)' if bad else f'BOWL held (<=2 cm) or resting (<=5 mm) in every frame {pe}-899')
    item('G06', g06)

    def g07():
        lt, mr = evreq('lin_touch', 'mei_release')
        d = need_dump(); has(d, 'BOWL', 'MEI_RIG', 'LIN_RIG')
        a = max(180, min(lt, mr) - 60)
        cm, cl = contact_series(d, 'MEI_RIG', a, 899), contact_series(d, 'LIN_RIG', a, 899)
        lt_m = next((f for f in range(a, 900) if cl[f] <= 0.015), None)
        mei_c = [f for f in range(a, 900) if cm[f] <= 0.015]
        mr_m = max(mei_c) if mei_c else None
        both = [f for f in range(a, 900) if cl[f] <= 0.015 and cm[f] <= 0.015]
        prob = []
        if lt_m is None or abs(lt_m - lt) > 3: prob.append(f'measured lin_touch {lt_m} vs declared {lt}')
        if mr_m is None or abs(mr_m - mr) > 3: prob.append(f'measured mei_release {mr_m} vs declared {mr}')
        if len(both) < 4: prob.append(f'both hands on the bowl {len(both)} frames (need >=4)')
        if mr_m is None or not 720 <= mr_m <= 899: prob.append('measured mei_release not in S5')
        return P(not prob, ('; '.join(prob) + ' | ' if prob else '') + f'measured lin_touch={lt_m} mei_release={mr_m} overlap={len(both)} frames')
    item('G07', g07)

    # ---------- G08 T45 ----------
    def g08():
        d = need_dump(); has(d, 'BOWL', 'CAM_S4', 'CAM_S5', 'MEI_RIG', 'LIN_RIG')
        t = {f: mw(d, 'BOWL', f)[:3, 3] for f in (718, 719, 720, 721)}
        vb, va = t[719] - t[718], t[721] - t[720]
        jump = float(np.linalg.norm(t[720] - t[719] - (vb + va) / 2))
        spd = float(np.linalg.norm(t[720] - t[719])) * 30
        prob = []
        if jump >= 0.03: prob.append(f'BOWL extra jump {jump*100:.1f} cm at 719->720')
        if spd < 0.01: prob.append(f'BOWL speed at the cut {spd*100:.2f} cm/s (need >=1)')

        def hand_c(rig, f):
            ks, segs = hand_segs(d, rig, f)
            if not len(segs):
                ks, segs = B.bone_segs(d, rig, f)
            return segs[:, :3].mean(0, keepdims=True) if len(segs) else mw(d, rig, f)[:3, 3][None]
        s4 = B.project(d, 'CAM_S4', 719, hand_c('MEI_RIG', 719))[0][0] - B.project(d, 'CAM_S4', 719, hand_c('LIN_RIG', 719))[0][0]
        s5 = B.project(d, 'CAM_S5', 720, hand_c('MEI_RIG', 720))[0][0] - B.project(d, 'CAM_S5', 720, hand_c('LIN_RIG', 720))[0][0]
        if s4 == 0 or np.sign(s4) != np.sign(s5): prob.append(f'MEI/LIN left-right relation flips (CAM_S4 du={s4:+.2f}, CAM_S5 du={s5:+.2f})')
        return P(not prob, '; '.join(prob) if prob else f'extra jump {jump*100:.2f} cm, speed {spd*100:.1f} cm/s, MEI-LIN du S4 {s4:+.2f} / S5 {s5:+.2f}')
    item('G08', g08)

    # ---------- G09 / G10 sims ----------
    def g09():
        d = need_dump()
        doms = [(n, e) for n, lst in d['physics'].items() if n.startswith('STEAM_DOMAIN') for e in lst
                if e.get('fluid_type') == 'DOMAIN' and e.get('domain_type') == 'GAS']
        if not doms:
            return F('no STEAM_DOMAIN* gas fluid domain')
        fs = d.get('frame_offset', 0)
        ok_c, cdet = _cache_cover(doms, proj, [fs + f for f in range(180, 390)] + [fs + f for f in range(720, 900)])
        prob = [] if ok_c else ['steam cache not shipped inside project/ for S2+S5: ' + '; '.join(cdet)]
        gas = d.get('x01', {}).get('gas', {})
        det2 = []
        for s in ('S2', 'S5'):
            a, b = SHOTS[s]
            fr = [f for f in sorted(gas) if a <= f <= b]
            tot = [gas[f]['total'] for f in fr]
            if not tot or min(tot) <= 0:
                # no evaluable grids in this verifier image: judge the shipped VDB cache instead (see _steam_cache_evidence)
                st = _steam_cache_evidence(d, proj, proj, (a + b) // 2, fs)
                if st.get('ok'):
                    det2.append(f'{s}: VDB cache evidence ok')
                    continue
                prob.append(f'{s}: steam density zero/unreadable in sampled frames'
                            + (' (FLUID modifiers had to be disabled: this Blender build aborts when Mantaflow is evaluated)' if d.get('mantaflow_disabled') else '')
                            + (('; cache: ' + '; '.join(st['det'])) if st.get('det') else '')); continue
            co = []
            for f in fr:
                c = [v['coarse'] for v in gas[f]['doms'].values() if 'coarse' in v]
                co.append(np.array(c[0] if c else [], float))
            ch = [float(np.corrcoef(u, v)[0, 1]) < 0.995 or abs(u.sum() - v.sum()) > 0.02 * max(u.sum(), 1e-9)
                  for u, v in zip(co, co[1:]) if len(u) and len(u) == len(v) and np.std(u) > 0 and np.std(v) > 0]
            if not ch or np.mean(ch) < 0.8: prob.append(f'{s}: steam field not evolving between sampled frames')
            vz = [v.get('vz') for f in fr for v in gas[f]['doms'].values() if v.get('vz') is not None]
            if not vz or np.median(vz) <= 0: prob.append(f'{s}: density-weighted vertical velocity not upward ({np.median(vz) if vz else None})')
        return P(not prob, '; '.join(prob) if prob else '; '.join(cdet + det2) + '; steam present, evolving and rising in S2 and S5')
    item('G09', g09)

    def g10():
        d = need_dump()
        doms = [(n, e) for n, lst in d['physics'].items() if n.startswith('SOUP_DOMAIN') for e in lst
                if e.get('fluid_type') == 'DOMAIN' and e.get('domain_type') == 'LIQUID']
        if not doms:
            return F('no SOUP_DOMAIN* liquid fluid domain')
        fs = d.get('frame_offset', 0)
        ok_c, cdet = _cache_cover(doms, proj, [fs + f for f in range(180, 390)])
        prob = [] if ok_c else ['soup cache not shipped inside project/ for S2: ' + '; '.join(cdet)]
        L_ = d.get('x01', {}).get('liq', {})
        fr = [f for f in sorted(L_) if 180 <= f <= 389]
        have = [f for f in fr if L_[f].get('nv', 0) > 0]
        if len(have) < 0.9 * max(len(fr), 1): prob.append(f'liquid geometry present in {len(have)}/{len(fr)} sampled S2 frames')
        nv = [L_[f]['nv'] for f in have]
        if len(set(nv)) < 2: prob.append('liquid mesh vertex count never changes in S2 (rigid object, not a simulated surface)')
        if prob and d.get('mantaflow_disabled'): prob.append('FLUID modifiers had to be disabled: this Blender build aborts when Mantaflow is evaluated')
        return P(not prob, '; '.join(prob) if prob else '; '.join(cdet) + f'; liquid mesh in {len(have)}/{len(fr)} S2 frames, {len(set(nv))} distinct vertex counts')
    item('G10', g10)

    # ---------- G12 finger wrap ----------
    def fingers_near(d, rig, f, P_, side=None, thr=0.02):
        groups = B.finger_groups(d['armatures'].get(rig, {}).get('bones', {}))
        row = d['bones'].get(rig, {}).get(f, {})
        best = 0
        for s in (('L', 'R') if side is None else (side,)):
            n = 0
            for key, names in groups[s].items():
                segs = np.array([row[b] for b in names if b in row], float).reshape(-1, 6)
                if len(segs) and B.seg_point_dist(segs, P_).min() <= thr:
                    n += 1
            best = max(best, n)
        return best

    def g12():
        lg, li, pe, lt, mr = evreq('lid_grip', 'ladle_in', 'pour_end', 'lin_touch', 'mei_release')
        d = need_dump(); has(d, 'POT_LID', 'LADLE', 'BOWL', 'MEI_RIG', 'LIN_RIG')
        kl = knob_local(d)
        fl, fh = (li + pe) // 2, (lt + mr) // 2
        res = {f'lid@{lg}': fingers_near(d, 'MEI_RIG', lg, B.xf(mw(d, 'POT_LID', lg), kl)),
               f'ladle@{fl}': fingers_near(d, 'MEI_RIG', fl, pts_world(d, 'LADLE', fl), mei_side(d)),
               f'bowl/MEI@{fh}': fingers_near(d, 'MEI_RIG', fh, pts_world(d, 'BOWL', fh)),
               f'bowl/LIN@{fh}': fingers_near(d, 'LIN_RIG', fh, pts_world(d, 'BOWL', fh))}
        bad = {k: v for k, v in res.items() if v < 3}
        return P(not bad, f'fingers (distinct finger chains) within 2 cm of the held object, need >=3 per grip: {res}')
    item('G12', g12)

    # ---------- G11 (flat index, materials, lights, denoise measured; look -> judge) ----------
    def g11():
        prob = []
        if not bmp.exists():
            return F('base/output.mp4 missing')
        g = L.gray_frames(bmp, 1280, 720, every=15)
        idx = {s: [] for s in SHOTS}
        for k, fr in enumerate(g):
            for s, (a, b) in SHOTS.items():
                if a <= k * 15 <= b:
                    idx[s].append(L.flat_block_index(fr))
        med = {s: round(float(np.median(v)), 3) for s, v in idx.items() if v}
        STATE['flat_index'] = med
        bad = {s: v for s, v in med.items() if v > 0.35}
        if len(bad) >= 3: prob.append(f'flat-block index > 0.35 in {len(bad)} of 5 shots {bad}')
        d = get_dump()
        if d.get('ok'):
            hero = ['MEI', 'LIN', 'POT', 'POT_LID', 'BOWL', 'LADLE', 'STOVE']
            nob = [h for h in hero if h in d['objects'] and not any(
                any(t.startswith('BSDF') or t == 'GROUP' for t in m.get('node_types', [])) for m in d['materials'].get(h, []))]
            if nob: prob.append(f'hero objects without a node-based BSDF material: {nob}')
            var = [h for h in hero if any(m.get('n_tex', 0) > 0 or m.get('principled_linked') for m in d['materials'].get(h, []))]
            if len(var) < 3: prob.append(f'surface variation (texture or linked BSDF input) on only {var} (need >=3 hero objects)')
            soft = [n for n, l in d['lights'].items() if l['type'] == 'AREA' or l['size'] > 0.02 or l['radius'] > 0.02 or (l['type'] == 'SUN' and l['angle'] > 0.005)]
            if not soft and not any(t in d.get('world_nodes', []) for t in ('TEX_ENVIRONMENT', 'TEX_SKY')):
                prob.append('no soft light source (area/sized light or environment/sky world)')
            if d.get('engine') == 'CYCLES' and d['render'].get('oidn_available', True) and not (d['render'].get('cycles_denoise') or d['render'].get('compositor_denoise')):
                prob.append('Cycles render without denoising')
        else:
            if not prob:
                STATE['g11_no_gate'] = True   # an inspection failure alone is not evidence of a non-photoreal look
            prob.append('Blender inspection failed: ' + str(d.get('error'))[-200:])
        return F('; '.join(prob)) if prob else None   # measured parts pass -> look decided by the judge
    item('G11', g11)

    # ---------- M13 / M14 re-renders ----------
    def offset():
        d = get_dump()
        return int(d.get('frame_offset', 0) or 0) if d.get('ok') else 0

    def m13():
        prob, det = [], []
        ok, dd = jcut(A('rev', 'hall'), 11.70)
        if not ok: prob.append('rev hall: ' + dd)
        det.append('rev hall ' + dd)
        bm, rm = L.load_audio(bmp, 1), L.load_audio(rmp, 1)
        n = int(11.65 * L.SR)
        a, b = L.lowpass(bm[:n]), L.lowpass(rm[:n])
        lag = L.best_lag(a, b, int(0.02 * L.SR))
        b2 = L.shift(b, lag, n)
        g = float(np.dot(a, b2) / max(np.dot(b2, b2), 1e-20))
        res = 10 * math.log10(max(((a - g * b2) ** 2).mean(), 1e-30) / max((a ** 2).mean(), 1e-20))
        det.append(f'pre-11.65s residual {res:.1f} dB')
        if res > -25: prob.append(f'pre-11.65 s audio differs ({res:.1f} dB)')
        sb, sr_ = A('base', 'speech'), A('rev', 'speech')
        a0 = int(11.7 * L.SR)
        lag2 = L.best_lag(sb[a0:], sr_[a0 - int(0.5 * L.SR):], int(0.5 * L.SR))
        sh = (lag2 - int(0.5 * L.SR)) / L.SR
        det.append(f'speech shift {sh:+.4f}s')
        if abs(sh + 0.300) > 0.010: prob.append(f'speech shift {sh:+.3f}s (need -0.300±0.010)')
        if prob:
            return F('; '.join(prob))
        if not blend.exists():
            return F('; '.join(det) + '; project/scene.blend missing')
        if time.time() - t_start > BUDGET_S:
            return F('; '.join(det) + '; grader time budget exhausted before the trim=9 re-render')
        rr, note = L.blend_render(blend, offset() + 400, tmp, 9, 'CAM_S3')
        if rr is None:
            return F('; '.join(det) + f'; re-render of revision frame 400 with revision_trim_frames=9 failed ({note})')
        s = L.ssim_render(rr, L.frame_at(rmp, 400, L.RENDER_W, L.RENDER_H))
        return P(s >= 0.75, '; '.join(det) + f'; re-render rev frame 400 SSIM={s:.3f} at {L.RENDER_W}x{L.RENDER_H} {note}')
    item('M13', m13)

    def m14():
        if not blend.exists():
            return F('project/scene.blend missing')
        if not bmp.exists():
            return F('base/output.mp4 missing')
        det, ok, measured_fail = [], True, False
        for f, cam in ((90, 'CAM_S1'), (270, 'CAM_S2'), (465, 'CAM_S3'), (630, 'CAM_S4'), (810, 'CAM_S5')):
            if time.time() - t_start > BUDGET_S:
                return F('; '.join(det + [f'grader time budget exhausted before frame {f}']))
            rr, note = L.blend_render(blend, offset() + f, tmp, 0, cam)
            if rr is None:
                return F('; '.join(det + [f'frame {f} re-render failed ({note})']))
            s = L.ssim_render(rr, L.frame_at(bmp, f, L.RENDER_W, L.RENDER_H))
            if s < 0.75:
                ok, measured_fail = False, True
            det.append(f'f{f} SSIM={s:.3f}{" " + note if note else ""}')
        STATE['m14_measured_fail'] = measured_fail
        return P(ok, '; '.join(det) + f' ({L.RENDER_W}x{L.RENDER_H}, {L.RENDER_SPP} spp re-render)')
    item('M14', m14)

    STATE['root'] = str(root)
    STATE['seconds'] = round(time.time() - t_start, 1)
    R['_x01_state'] = {'verdict': 'na', 'detail': json.dumps({k: STATE.get(k) for k in ('flat_index', 'dump_seconds', 'dump_warnings', 'seconds')})[:900]}
    return R


GROUPS_GG1 = {'project', 'camera', 'contact', 'sim'}
GG4_ITEMS = ['M03', 'M05', 'M09', 'M16', 'M17', 'G01', 'G02', 'G04', 'G05', 'G06', 'G07', 'G13']


def postprocess(res, ctx):
    items = {i['id']: i for i in ctx['items']}

    def zero(iid, why):
        r = res.get(iid, {})
        if r.get('verdict') not in ('fail', 'na'):
            res[iid] = dict(r, verdict='fail', detail=f'[{why}] ' + str(r.get('detail', r.get('reason', '')))[:300], gated=True)

    if STATE.get('blend_open_fail'):
        for iid, it in items.items():
            if it.get('group') in GROUPS_GG1:
                zero(iid, 'GG1 scene.blend missing/unopenable')
    if STATE.get('m14_measured_fail'):
        for iid, it in items.items():
            if it.get('group') == 'contact':
                zero(iid, 'GG2 M14 re-render SSIM below 0.75')
    if res.get('G11', {}).get('verdict') == 'fail' and not STATE.get('g11_no_gate'):
        for iid, it in items.items():
            if it.get('group') in ('look', 'sim') and iid != 'G11':
                zero(iid, 'GG3 G11 failed (not photoreal)')
    if STATE.get('events_bad'):
        for iid in GG4_ITEMS:
            zero(iid, 'GG4 events.csv missing/unparseable')
    return res
