# -*- coding: utf-8 -*-
"""Shared deterministic helpers for CDC-C-X05 / CDC-C-X06 checks (numpy + ffmpeg/ffprobe only; Blender optional).
Every helper is defensive: on error it raises, callers wrap per item."""
import csv, json, math, re, shutil, subprocess
from pathlib import Path
import numpy as np

SR = 48000
FPS = 30


def sh(cmd, timeout=600, binary=False):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, text=not binary)
    return r


def find(out: Path, rel: str):
    p = out / rel
    if p.exists():
        return p
    hits = sorted(out.glob('*/' + rel)) + sorted(out.glob('*/*/' + rel))
    return hits[0] if hits else None


# ---------------- video ----------------
def vprobe(p):
    r = sh(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', str(p)], 900)
    return json.loads(r.stdout)


def rate(s):
    try:
        a, b = str(s).split('/')
        return float(a) / float(b) if float(b) else 0.0
    except Exception:
        return 0.0


def encoding_contract(p, n_expected):
    """returns (ok, detail, info)."""
    j = vprobe(p)
    vs = [s for s in j.get('streams', []) if s.get('codec_type') == 'video']
    as_ = [s for s in j.get('streams', []) if s.get('codec_type') == 'audio']
    bad = []
    if not vs:
        return False, 'no video stream', {}
    v = vs[0]
    n = int(v.get('nb_read_frames') or 0)
    sar = v.get('sample_aspect_ratio') or '1:1'
    info = {'codec': v.get('codec_name'), 'pix_fmt': v.get('pix_fmt'), 'size': [v.get('width'), v.get('height')], 'sar': sar,
            'r_frame_rate': v.get('r_frame_rate'), 'avg_frame_rate': v.get('avg_frame_rate'), 'frames': n}
    if v.get('codec_name') != 'h264': bad.append('codec')
    if v.get('pix_fmt') != 'yuv420p': bad.append('pix_fmt')
    if (v.get('width'), v.get('height')) != (1280, 720): bad.append('size')
    if sar not in ('1:1', '0:1', 'N/A'): bad.append('sar')
    if abs(rate(v.get('r_frame_rate')) - 30) > 1e-3 or abs(rate(v.get('avg_frame_rate')) - 30) > 0.01: bad.append('fps')
    if n != n_expected: bad.append(f'frames {n}!={n_expected}')
    vdur = n / 30.0
    if not as_:
        bad.append('no audio')
    else:
        a = as_[0]
        info['audio'] = {'codec': a.get('codec_name'), 'channels': a.get('channels'), 'sr': a.get('sample_rate'), 'dur': a.get('duration')}
        if a.get('codec_name') != 'aac': bad.append('audio codec')
        if int(a.get('channels') or 0) != 2: bad.append('audio channels')
        if str(a.get('sample_rate')) != '48000': bad.append('audio sr')
        try:
            ad = float(a.get('duration'))
        except Exception:
            ad = float(j.get('format', {}).get('duration') or 0)
        info['audio_dur'] = ad
        if ad < vdur - 1 / 30.0 - 1e-3: bad.append(f'audio short {ad:.3f}<{vdur:.3f}')
    return (not bad), ('ok' if not bad else 'bad: ' + ', '.join(bad)), info


def gray_frames(p, w=320, h=180, max_frames=1200):
    r = sh(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f'scale={w}:{h}:flags=area,format=gray', '-frames:v', str(max_frames),
            '-f', 'rawvideo', '-'], 900, binary=True)
    a = np.frombuffer(r.stdout, np.uint8)
    n = a.size // (w * h)
    return a[:n * w * h].reshape(n, h, w)


def psnr(a, b):
    m = float(np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2))
    return 99.0 if m < 1e-10 else 10 * math.log10(255 ** 2 / m)


def detect_cuts(F):
    """hard-cut candidates: frame i where mean abs diff to i-1 spikes AND grey histogram changes."""
    if len(F) < 3:
        return [], []
    f = F.astype(np.int16)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))  # d[i-1] = diff(i-1, i)
    hist = np.stack([np.histogram(x, 32, (0, 256))[0] / x.size for x in F])
    hd = 0.5 * np.abs(np.diff(hist, axis=0)).sum(axis=1)
    cuts = []
    for k in range(len(d)):
        lo, hi = max(0, k - 6), min(len(d), k + 7)
        nb = np.concatenate([d[lo:k], d[k + 1:hi]])
        base = float(np.median(nb)) if nb.size else 0.0
        if d[k] > max(10.0, 4.0 * base + 4.0) and hd[k] > 0.12:
            cuts.append(k + 1)
    return cuts, d.tolist()


def freeze_runs(F, min_len, thr_psnr=55.0):
    runs, cur = [], 1
    for i in range(1, len(F)):
        if psnr(F[i], F[i - 1]) >= thr_psnr:
            cur += 1
        else:
            if cur >= min_len: runs.append((i - cur, i - 1))
            cur = 1
    if cur >= min_len: runs.append((len(F) - cur, len(F) - 1))
    return runs


def cut_structure(F, expected, tol=1):
    cuts, d = detect_cuts(F)
    found, miss = [], []
    for c in expected:
        hit = [x for x in cuts if abs(x - c) <= tol]
        (found if hit else miss).append(c)
    extra = [x for x in cuts if all(abs(x - c) > tol for c in expected)]
    blend = []
    for c in expected:
        hit = [x for x in cuts if abs(x - c) <= tol]
        if hit:
            k = hit[0] - 1
            if 0 < k < len(d) - 1 and (d[k - 1] > 0.5 * d[k] or d[k + 1] > 0.5 * d[k]):
                blend.append(hit[0])
    return {'cuts': cuts, 'missing': miss, 'extra': extra, 'blendlike': blend}


# ---------------- audio ----------------
def audio(p, sr=SR):
    r = sh(['ffmpeg', '-v', 'error', '-i', str(p), '-vn', '-ac', '2', '-ar', str(sr), '-f', 'f32le', '-'], 600, binary=True)
    a = np.frombuffer(r.stdout, np.float32)
    if a.size < 2:
        raise ValueError(f'cannot decode audio {p.name}')
    return a[:a.size // 2 * 2].reshape(-1, 2).astype(np.float64)


def wav_info(p):
    j = json.loads(sh(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(p)], 60).stdout)
    s = [x for x in j.get('streams', []) if x.get('codec_type') == 'audio']
    return s[0] if s else {}


def ebur(p):
    o = sh(['ffmpeg', '-hide_banner', '-nostats', '-i', str(p), '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], 600).stderr
    m = re.findall(r'I:\s+(-?[\d.]+|-inf) LUFS', o)
    pk = re.findall(r'Peak:\s+(-?[\d.]+|-inf) dBFS', o)
    I = float(m[-1]) if m and m[-1] != '-inf' else -99.0
    TP = float(pk[-1]) if pk and pk[-1] != '-inf' else -99.0
    return I, TP


def clip_run(x, thr=0.999, run=3):
    for ch in range(x.shape[1]):
        m = np.abs(x[:, ch]) >= thr
        if not m.any(): continue
        c = np.convolve(m.astype(np.int8), np.ones(run, np.int8), 'valid')
        if (c >= run).any():
            return True
    return False


def db(v, floor=1e-12):
    return 10 * math.log10(max(float(v), floor))


def env_db(x, win_s=0.01, hop_s=None, sr=SR):
    """windowed RMS dBFS envelope (max over channels). returns (t, e)."""
    hop_s = hop_s or win_s
    w, h = int(win_s * sr), int(hop_s * sr)
    m = x if x.ndim == 2 else x[:, None]
    n = max(0, (len(m) - w) // h + 1)
    if n == 0:
        return np.zeros(0), np.zeros(0)
    idx = np.arange(n) * h
    e2 = np.cumsum(np.vstack([np.zeros((1, m.shape[1])), m ** 2]), axis=0)
    p = (e2[idx + w] - e2[idx]) / w
    e = 10 * np.log10(np.maximum(p.max(axis=1), 1e-14))
    return (idx + w / 2) / sr, e


def max_db(x, t0, t1, win_s=0.01, sr=SR):
    a, b = int(max(0, t0) * sr), int(max(0, t1) * sr)
    seg = x[a:b]
    if len(seg) < int(win_s * sr):
        return -140.0
    return float(env_db(seg, win_s, sr=sr)[1].max())


def find_gains(tl):
    """collect numeric values under keys containing 'gain' from timeline.json."""
    out = []
    def walk(o, path=''):
        if isinstance(o, dict):
            for k, v in o.items():
                kp = f'{path}.{k}'
                if 'gain' in str(k).lower() and isinstance(v, (int, float)) and not isinstance(v, bool):
                    out.append((kp, float(v)))
                elif 'gain' in str(k).lower() and isinstance(v, dict):
                    for k2, v2 in v.items():
                        if isinstance(v2, (int, float)) and not isinstance(v2, bool):
                            out.append((f'{kp}.{k2}', float(v2)))
                    walk(v, kp)
                else:
                    walk(v, kp)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f'{path}[{i}]')
    walk(tl)
    return out


def best_align_resid(mix, s, max_lag):
    n = min(len(mix), len(s))
    mix, s = mix[:n], s[:n]
    best = (1e9, 0)
    for lag in range(-max_lag, max_lag + 1, 1 if max_lag <= 48 else 4):
        if lag >= 0:
            a, b = mix[lag:], s[:n - lag]
        else:
            a, b = mix[:n + lag], s[-lag:]
        r = db(np.sum((a - b) ** 2)) - db(np.sum(a ** 2))
        if r < best[0]:
            best = (r, lag)
    if max_lag > 48:  # refine
        l0 = best[1]
        for lag in range(l0 - 4, l0 + 5):
            if abs(lag) > max_lag: continue
            a, b = (mix[lag:], s[:n - lag]) if lag >= 0 else (mix[:n + lag], s[-lag:])
            r = db(np.sum((a - b) ** 2)) - db(np.sum(a ** 2))
            if r < best[0]:
                best = (r, lag)
    return best


def stem_sum_residual(mix, stems: dict, tl, max_lag=240):
    """try declared gain interpretations (master linear / master dB / per-stem linear|dB / unity); return best (resid_db, how)."""
    gains = find_gains(tl)
    names = list(stems)
    cands = [('unity', {k: 1.0 for k in names})]
    master = [g for g in gains if 'master' in g[0].lower()]
    for kp, g in master[:3]:
        cands.append((f'{kp} linear', {k: g for k in names}))
        cands.append((f'{kp} dB', {k: 10 ** (g / 20) for k in names}))
    per = {}
    for k in names:
        hit = [g for g in gains if re.search(r'\b' + k + r'\b', g[0].lower().replace('.', ' ').replace('[', ' ').replace('_', ' '))]
        if hit:
            per[k] = hit[0][1]
    if per:
        mg = master[0][1] if master else None
        for unit in ('lin', 'db'):
            for mu in ([None] if mg is None else [None, 'lin', 'db']):
                gd = {}
                for k in names:
                    v = per.get(k, 1.0 if unit == 'lin' else 0.0)
                    gd[k] = v if unit == 'lin' else 10 ** (v / 20)
                    if mu == 'lin': gd[k] *= mg
                    if mu == 'db': gd[k] *= 10 ** (mg / 20)
                cands.append((f'per-stem {unit} master {mu}', gd))
    L = min([len(mix)] + [len(v) for v in stems.values()])
    mono_mix = mix[:L].mean(axis=1)
    best = None
    for how, gd in cands:
        s = sum(stems[k][:L] * gd[k] for k in names)
        r, lag = best_align_resid(mono_mix, s.mean(axis=1), max_lag)
        # stereo residual at that lag
        if lag >= 0:
            a, b = mix[lag:L], s[:L - lag]
        else:
            a, b = mix[:L + lag], s[-lag:L]
        rs = db(np.sum((a - b) ** 2)) - db(np.sum(a ** 2))
        if best is None or rs < best[0]:
            best = (rs, f'{how}; lag={lag} samples')
    return best


def band_energy(x, sr, bands, frames_mask_db=30.0, nfft=2048):
    """Welch-like PSD over active frames (frame RMS within frames_mask_db of max). x mono."""
    hop = nfft // 2
    n = (len(x) - nfft) // hop + 1
    if n <= 0:
        raise ValueError('segment too short')
    win = np.hanning(nfft)
    fr = np.stack([x[i * hop:i * hop + nfft] for i in range(n)])
    rms = 10 * np.log10(np.maximum((fr ** 2).mean(axis=1), 1e-14))
    act = fr[rms >= rms.max() - frames_mask_db]
    P = (np.abs(np.fft.rfft(act * win, axis=1)) ** 2).mean(axis=0)
    f = np.fft.rfftfreq(nfft, 1 / sr)
    return {b: float(P[(f >= b[0]) & (f < b[1])].sum()) for b in bands}


def read_events(p):
    txt = p.read_text(encoding='utf-8-sig', errors='replace')
    lines = txt.splitlines()
    header = lines[0].strip() if lines else ''
    ev = {}
    bad = []
    for row in csv.reader(lines[1:]):
        if not row or not row[0].strip():
            continue
        k = row[0].strip()
        if k in ev:
            continue
        try:
            fv = row[1].strip()
            if not re.fullmatch(r'-?\d+', fv):
                bad.append(k); ev[k] = None; continue
            ev[k] = int(fv)
        except Exception:
            bad.append(k); ev[k] = None
    return header, ev, bad


# ---------------- blender ----------------
BLEND_INSPECT = r'''
import bpy, json
d = {"version": bpy.app.version_string, "file_version": list(bpy.data.version), "objects": {}, "scenes": {}}
for o in bpy.data.objects:
    d["objects"][o.name] = {"type": o.type, "arm_mods": [m.object.name for m in getattr(o, "modifiers", []) if m.type == "ARMATURE" and m.object]}
for s in bpy.data.scenes:
    d["scenes"][s.name] = {k: (s[k] if isinstance(s[k], (int, float, str)) else str(s[k])) for k in s.keys() if not k.startswith("_")}
d["active_scene"] = bpy.context.scene.name
print("CDCCJSON" + json.dumps(d))
'''


def blend_inspect(blend: Path, tmp: Path):
    """returns dict or None if blender unavailable; raises on failure to open."""
    if not shutil.which('blender'):
        return None
    f = tmp / 'cdcc_inspect.py'
    f.write_text(BLEND_INSPECT)
    r = sh(['blender', '-b', '--factory-startup', str(blend), '--python', str(f)], 900)
    m = re.search(r'CDCCJSON(\{.*\})', r.stdout or '')
    if not m:
        raise RuntimeError('blender could not open/inspect: ' + ((r.stdout or '') + (r.stderr or ''))[-600:])
    return json.loads(m.group(1))


def V(verdict, detail):
    return {'verdict': verdict, 'detail': str(detail)[:1500]}


# ---------------- X05 per-frame project export (added 2026-10-25) ----------------
# One read-only Blender pass over film frames 0..N-1 (scene frame = frame_start + i) with both revision properties set to 0
# (base state).  Modifiers are muted (only object/bone/shape-key/material/light data are read), so the pass is cheap.
# Output: JSON with per-frame object transforms, camera data, shot-camera projections, rig head/hand/mouth signals.
X05_EXPORT = r'''
import bpy, json, sys, math, re
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0]; NFR = int(argv[1]) if len(argv) > 1 else 900
SHOTS = [(0, 179, "CAM_S1"), (180, 359, "CAM_S2"), (360, 539, "CAM_S3"), (540, 719, "CAM_S4"), (720, 899, "CAM_S5")]
RIGS = ["HOST_A_RIG", "HOST_B_RIG", "DRIVER_RIG"]
CHAR = {"HOST_A_RIG": "HOST_A", "HOST_B_RIG": "HOST_B", "DRIVER_RIG": "DRIVER"}
TRACK = ["MIC_A", "MIC_B", "CONSOLE", "CALLER_FADER", "ON_AIR_LAMP", "TAXI", "RADIO", "RADIO_KNOB", "PHONE", "TRAFFIC_LIGHT",
         "HOST_A", "HOST_B", "DRIVER"] + RIGS
CAMS = ["CAM_S%d" % i for i in range(1, 6)]
OB = bpy.data.objects
sc = bpy.context.scene
D = {"file_version": list(bpy.data.version), "app_version": bpy.app.version_string, "scene": sc.name,
     "frame_start": sc.frame_start, "frame_end": sc.frame_end, "fps": sc.render.fps / (sc.render.fps_base or 1),
     "saved_props": {}, "notes": [], "types": {n: OB[n].type for n in TRACK + CAMS if n in OB}}
for k in ("rev1_hold_frames", "rev2_trim_frames"):
    if k in sc.keys():
        v = sc[k]
        D["saved_props"][k] = v if isinstance(v, (int, float)) else str(v)
        try:
            sc[k] = type(v)(0) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0
        except Exception as e:
            D["notes"].append("cannot set %s: %s" % (k, e))
D["deformed"] = {r: sorted(o.name for o in OB if o.type == "MESH" and any(
    m.type == "ARMATURE" and m.object is not None and m.object.name == r for m in o.modifiers)) for r in RIGS}
for o in OB:
    for m in getattr(o, "modifiers", []):
        try:
            m.show_viewport = False
        except Exception:
            pass
try:
    sc.render.use_simplify = True; sc.render.simplify_subdivision = 0
except Exception:
    pass

def low(s): return s.lower()
HEAD_RE = re.compile(r"(^|[^a-z])head($|[^a-z])|(^|[^a-z])spine\.006$")
JAW_RE = re.compile(r"jaw|mouth|lip|chin|teeth|tongue")
FACE_RE = re.compile(r"eye|nose|brow|cheek|lip|teeth|jaw|chin|mouth")
HAND_RE = re.compile(r"hand|palm|finger|thumb|index|middle|ring|pinky|little|f_")
FING_RE = re.compile(r"finger|thumb|index|middle|ring|pinky|little|f_(index|middle|ring|pinky)")
KEY_RE = re.compile(r"jaw|mouth|viseme|lip|open|vrc\.v_|phon|^(aa|ah|ao|ee|eh|ih|iy|oh|ou|uw|mbp|fv|th|oo|a|e|i|o|u)$")
def side(n):
    n = low(n)
    if re.search(r"(\.|_|-| )l($|\.|_|\d)|left", n): return "L"
    if re.search(r"(\.|_|-| )r($|\.|_|\d)|right", n): return "R"
    return "?"
def pick(bones, rx, limit):
    c = [b for b in bones if rx.search(low(b.name))]
    d = [b for b in c if b.bone.use_deform]
    c = d or c
    c.sort(key=lambda b: (len(b.name), b.name))
    return c[:limit]

RINFO = {}
for r in RIGS:
    o = OB.get(r)
    if o is None or o.type != "ARMATURE":
        continue
    pbs = list(o.pose.bones)
    heads = pick(pbs, HEAD_RE, 1)
    jaws = pick(pbs, JAW_RE, 12)
    hands = pick(pbs, HAND_RE, 80)
    face = pick(pbs, FACE_RE, 40)
    fingers = [b for b in pbs if FING_RE.search(low(b.name))]
    # finger chains: finger bones whose parent is not a finger bone, length = longest finger-only descent
    fset = set(b.name for b in fingers)
    def depth(b):
        ch = [c for c in b.children if c.name in fset]
        return 1 + max([depth(c) for c in ch], default=0)
    chains = {"L": 0, "R": 0, "?": 0}
    for b in fingers:
        if b.parent is None or b.parent.name not in fset:
            if depth(b) >= 3:
                chains[side(b.name)] += 1
    defb = [b for b in pbs if b.bone.use_deform][:250] or pbs[:250]
    meshes = set(D["deformed"].get(r, []))
    cn = CHAR[r]
    for m in OB:
        if m.type == "MESH" and (m.parent == o or m.name == cn or m.name.startswith(cn + "_") or m.name.startswith(cn + ".")):
            meshes.add(m.name)
    keys = []
    for mn in sorted(meshes):
        me = OB[mn].data
        sk = getattr(me, "shape_keys", None)
        if sk is None:
            continue
        for i, kb in enumerate(sk.key_blocks):
            if i == 0: continue
            if KEY_RE.search(low(kb.name)):
                keys.append((mn, sk.name, kb.name))
    jobj = [m.name for m in OB if m.type in ("MESH", "EMPTY") and JAW_RE.search(low(m.name)) and
            (m.name.startswith(cn) or m.parent == o or (m.parent is not None and m.parent.name.startswith(cn)))][:6]
    RINFO[r] = dict(obj=o, head=heads[0] if heads else None, jaws=jaws, hands=hands, face=face, fingers=fingers,
                    defb=defb, keys=keys[:24], jobj=jobj, cn=cn)
    D.setdefault("rigs", {})[r] = {"head": heads[0].name if heads else None, "jaws": [b.name for b in jaws],
                                    "n_hand": len(hands), "finger_chains": chains, "n_finger": len(fingers),
                                    "shape_keys": ["%s:%s" % (a, c) for a, b, c in keys[:24]], "jaw_objects": jobj,
                                    "meshes": sorted(meshes), "n_bones": len(pbs)}

def qang(m3):
    q = m3.to_quaternion(); q.normalize()
    return 2.0 * math.degrees(math.acos(min(1.0, abs(q.w))))
def local_delta(pb):
    M = pb.matrix; Mr = pb.bone.matrix_local
    if pb.parent is not None:
        M = pb.parent.matrix.inverted_safe() @ M; Mr = pb.parent.bone.matrix_local.inverted_safe() @ Mr
    dl = Mr.inverted_safe() @ M
    return qang(dl.to_3x3()), dl.to_translation().length
def seg_dist(p, a, b):
    ab = b - a; L2 = ab.length_squared
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, (p - a).dot(ab) / L2))
    return (a + ab * t - p).length
def rgb_of(sock):
    if sock is None: return None
    if not sock.is_linked:
        v = sock.default_value
        try: return [float(v[0]), float(v[1]), float(v[2])]
        except Exception: return [float(v)] * 3
    fn = sock.links[0].from_node
    if fn.type == "RGB": v = fn.outputs[0].default_value; return [float(v[0]), float(v[1]), float(v[2])]
    return None
def val_of(sock):
    if sock is None: return None
    if not sock.is_linked: return float(sock.default_value)
    fn = sock.links[0].from_node
    if fn.type == "VALUE": return float(fn.outputs[0].default_value)
    return None
def mat_emis(mat):
    tot = [0.0, 0.0, 0.0]
    if mat is None or not mat.use_nodes or mat.node_tree is None: return tot
    for n in mat.node_tree.nodes:
        if n.mute: continue
        if n.type == "EMISSION": c, s = rgb_of(n.inputs.get("Color")), val_of(n.inputs.get("Strength"))
        elif n.type == "BSDF_PRINCIPLED": c, s = rgb_of(n.inputs.get("Emission Color")), val_of(n.inputs.get("Emission Strength"))
        else: continue
        if c is None or s is None: continue
        for i in range(3): tot[i] += max(0.0, c[i]) * max(0.0, s)
    return tot
def hier(name):
    o = OB.get(name)
    if o is None: return []
    return [o] + list(o.children_recursive)
def emis(name, dg):
    tot = [0.0, 0.0, 0.0]
    for o in hier(name):
        oe = o.evaluated_get(dg)
        if o.hide_render or oe.hide_render: continue
        if o.type == "LIGHT":
            c = oe.data.color; e = float(oe.data.energy)
            for i in range(3): tot[i] += float(c[i]) * e
        for sl in o.material_slots:
            if sl.material is None: continue
            em = mat_emis(sl.material.evaluated_get(dg))
            for i in range(3): tot[i] += em[i]
    return [round(x, 5) for x in tot]

def mlist(M, nd=5): return [round(M[i][j], nd) for i in range(4) for j in range(4)]
F = []
prev = {}
fmin, fmax = {}, {}
TLH = [o.name for o in hier("TRAFFIC_LIGHT")][:9]
f0 = sc.frame_start
for i in range(NFR):
    sc.frame_set(f0 + i)
    dg = bpy.context.evaluated_depsgraph_get()
    fr = {"i": i, "cam": sc.camera.name if sc.camera else None, "obj": {}, "cams": {}, "rig": {}}
    for n in TRACK:
        o = OB.get(n)
        if o is None: continue
        fr["obj"][n] = mlist(o.evaluated_get(dg).matrix_world)
    if "RADIO" in OB and "RADIO_KNOB" in OB:
        R = OB["RADIO"].evaluated_get(dg).matrix_world; K = OB["RADIO_KNOB"].evaluated_get(dg).matrix_world
        q = (R.inverted_safe() @ K).to_quaternion(); fr["knob_rel_q"] = [round(q.w, 6), round(q.x, 6), round(q.y, 6), round(q.z, 6)]
    for c in CAMS:
        o = OB.get(c)
        if o is None or o.type != "CAMERA": continue
        oe = o.evaluated_get(dg); cd = oe.data
        fr["cams"][c] = {"m": mlist(oe.matrix_world), "lens": round(cd.lens, 4), "dof": bool(cd.dof.use_dof),
                         "fstop": round(cd.dof.aperture_fstop, 4), "type": cd.type}
    shot = [s for s in SHOTS if s[0] <= i <= s[1]]
    camn = shot[0][2] if shot else None
    cam = OB.get(camn) if camn else None
    camE = cam.evaluated_get(dg) if cam is not None and cam.type == "CAMERA" else None
    pts = {}
    for n in ("RADIO", "ON_AIR_LAMP", "TRAFFIC_LIGHT", "RADIO_KNOB", "PHONE", "HOST_B"):
        if n in OB: pts[n] = OB[n].evaluated_get(dg).matrix_world.to_translation()
    for n in TLH[1:]:
        pts["TL:" + n] = OB[n].evaluated_get(dg).matrix_world.to_translation()
    for r, inf in RINFO.items():
        o = inf["obj"].evaluated_get(dg); W = o.matrix_world; pb = o.pose.bones
        rr = {}
        hb = inf["head"]
        if hb is not None:
            b = pb[hb.name]; a = W @ b.head; t = W @ b.tail
            rr["head"] = [round(x, 5) for x in list(a) + list(t)]
            pts["HEAD:" + r] = (a + t) * 0.5
            fr_vec = None
            jw = [pb[j.name] for j in inf["jaws"] if "jaw" in low(j.name)]
            if jw:
                v = (W @ jw[0].tail) - (W @ jw[0].head); fr_vec = Vector((v.x, v.y, 0.0))
            else:
                fc = [pb[f.name] for f in inf["face"] if f.name != hb.name]
                if fc:
                    cen = sum(((W @ f.head) for f in fc), Vector((0, 0, 0))) / len(fc)
                    v = cen - a; fr_vec = Vector((v.x, v.y, 0.0))
            if fr_vec is not None and fr_vec.length > 1e-6:
                rr["front"] = [round(x, 5) for x in fr_vec.normalized()]
            for pn in ("PHONE",):
                if pn in pts: rr["d_head_" + pn] = round(seg_dist(pts[pn], a, t), 5)
        segs = [(W @ pb[h.name].head, W @ pb[h.name].tail, side(h.name)) for h in inf["hands"]]
        for pn in ("RADIO_KNOB", "PHONE"):
            if pn in pts and segs:
                rr["d_hand_" + pn] = round(min(seg_dist(pts[pn], a, b) for a, b, s in segs), 5)
        if "CALLER_FADER" in OB and segs:
            p = OB["CALLER_FADER"].evaluated_get(dg).matrix_world.to_translation()
            rr["d_hand_CALLER_FADER"] = round(min(seg_dist(p, a, b) for a, b, s in segs), 5)
        mouth = {}
        for j in inf["jaws"]:
            ang, tr = local_delta(pb[j.name])
            mouth["bone_rot:" + j.name] = round(ang, 4); mouth["bone_loc:" + j.name] = round(tr * 100, 4)
        for mn, kn, kb in inf["keys"]:
            try:
                k = bpy.data.shape_keys[kn].evaluated_get(dg)
                mouth["key:%s:%s" % (mn, kb)] = round(float(k.key_blocks[kb].value), 5)
            except Exception:
                mouth["key:%s:%s" % (mn, kb)] = round(float(bpy.data.shape_keys[kn].key_blocks[kb].value), 5)
        for jn in inf["jobj"]:
            ml = OB[jn].evaluated_get(dg).matrix_local
            mouth["obj_rot:" + jn] = round(qang(ml.to_3x3()), 4); mouth["obj_loc:" + jn] = round(ml.to_translation().length * 100, 4)
        rr["mouth"] = mouth
        cur = [W @ pb[b.name].head for b in inf["defb"]] + [W @ pb[b.name].tail for b in inf["defb"]]
        if r in prev and len(prev[r]) == len(cur):
            rr["motion"] = round(max((x - y).length for x, y in zip(cur, prev[r])), 6)
        prev[r] = cur
        for b in inf["fingers"]:
            ang, _ = local_delta(pb[b.name]); k = r + ":" + b.name
            fmin[k] = min(fmin.get(k, 1e9), ang); fmax[k] = max(fmax.get(k, -1e9), ang)
        rr["root"] = [round(x, 5) for x in W.to_translation()]
        hip = [b for b in inf["defb"] if re.search(r"hip|pelvis|spine$|spine\.000|^def-spine$|root", low(b.name))]
        if hip:
            rr["root"] = [round(x, 5) for x in (W @ pb[hip[0].name].head)]
        fr["rig"][r] = rr
    if camE is not None:
        Mi = camE.matrix_world.inverted_safe()
        fr["proj"] = {}
        for n, p in pts.items():
            v = world_to_camera_view(sc, camE, p); cs = Mi @ p
            fr["proj"][n] = [round(v.x, 5), round(v.y, 5), round(v.z, 5), round(cs.x, 5), round(cs.y, 5), round(cs.z, 5)]
    fr["tl_emis"] = emis("TRAFFIC_LIGHT", dg)
    if i % 30 == 0 or 0 <= i <= 179:
        fr["lamp_emis"] = emis("ON_AIR_LAMP", dg)
    F.append(fr)
D["frames"] = F
D["finger_range"] = {k: round(fmax[k] - fmin[k], 3) for k in fmin}
json.dump(D, open(OUT, "w"))
print("X05EXPORT_OK")
'''


def blend_export(blend: Path, tmp: Path, nfr=900, timeout=1500):
    """per-frame base-state export; returns dict. Raises RuntimeError if Blender cannot open/run on the file."""
    f = tmp / 'x05_export.py'
    f.write_text(X05_EXPORT)
    o = tmp / 'x05_export.json'
    if o.exists():
        o.unlink()
    r = sh(['blender', '-b', '--factory-startup', str(blend), '--python', str(f), '--', str(o), str(nfr)], timeout)
    if not o.exists():
        raise RuntimeError('per-frame export failed: ' + ((r.stdout or '') + (r.stderr or ''))[-800:])
    return json.loads(o.read_text())


# Re-render (M10): base state, Cycles CPU, 320x180, few samples, explicit shot camera.
X05_RENDER = r'''
import bpy, sys, json
argv = sys.argv[sys.argv.index("--") + 1:]
outdir = argv[0]; frames = [int(x) for x in argv[1].split(",")]
sc = bpy.context.scene
for k in ("rev1_hold_frames", "rev2_trim_frames"):
    if k in sc.keys() and isinstance(sc[k], (int, float)):
        sc[k] = type(sc[k])(0)
r = sc.render
r.engine = "CYCLES"
try: sc.cycles.device = "CPU"
except Exception: pass
sc.cycles.samples = 16
try: sc.cycles.use_adaptive_sampling = True
except Exception: pass
try: sc.cycles.time_limit = 45.0
except Exception: pass
try: sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception:
    try: sc.cycles.use_denoising = False
    except Exception: pass
r.resolution_x, r.resolution_y, r.resolution_percentage = 320, 180, 100
r.use_motion_blur = False
r.use_simplify = True; r.simplify_subdivision_render = min(r.simplify_subdivision_render, 2)
r.image_settings.file_format = "PNG"; r.image_settings.color_mode = "RGB"; r.image_settings.color_depth = "8"
SHOTS = [(0, 179, "CAM_S1"), (180, 359, "CAM_S2"), (360, 539, "CAM_S3"), (540, 719, "CAM_S4"), (720, 899, "CAM_S5")]
done = {}
for i in frames:
    sc.frame_set(sc.frame_start + i)
    cn = [s[2] for s in SHOTS if s[0] <= i <= s[1]][0]
    if cn in bpy.data.objects and bpy.data.objects[cn].type == "CAMERA":
        sc.camera = bpy.data.objects[cn]
    r.filepath = "%s/f%04d.png" % (outdir, i)
    try:
        bpy.ops.render.render(write_still=True); done[i] = "ok"
    except Exception as e:
        done[i] = "error: %s" % e
print("X05RENDER" + json.dumps(done))
'''


def blend_render(blend: Path, tmp: Path, frames, timeout=1500):
    d = tmp / 'x05_render'
    d.mkdir(parents=True, exist_ok=True)
    f = tmp / 'x05_render.py'
    f.write_text(X05_RENDER)
    try:
        r = sh(['blender', '-b', '--factory-startup', str(blend), '--python', str(f), '--', str(d), ','.join(str(x) for x in frames)], timeout)
        log = ((r.stdout or '') + (r.stderr or ''))[-600:]
    except subprocess.TimeoutExpired:
        log = f'render timed out after {timeout} s'
    return {i: (d / f'f{i:04d}.png') for i in frames if (d / f'f{i:04d}.png').exists()}, log


# ---------------- X05 audio/picture helpers (added 2026-10-25) ----------------
def bandpass(x, lo, hi, sr=SR):
    """zero-phase FFT band-pass of a mono signal with raised-cosine skirts (lo*0.7..lo, hi..hi*1.3) so that
    the time-domain ringing stays in the 10 ms range (a brick-wall filter smears energy over hundreds of ms)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / sr)
    H = np.ones_like(f)
    a = 0.7 * lo
    H[f <= a] = 0
    m = (f > a) & (f < lo)
    H[m] = 0.5 - 0.5 * np.cos(np.pi * (f[m] - a) / (lo - a))
    b = 1.3 * hi
    H[f >= b] = 0
    m = (f > hi) & (f < b)
    H[m] = 0.5 + 0.5 * np.cos(np.pi * (f[m] - hi) / (b - hi))
    return np.fft.irfft(X * H, len(x))


def kweight_ms(x, sr=SR):
    """K-weighted (BS.1770 magnitude response, applied in the FFT domain) signal per channel."""
    f = np.fft.rfftfreq(len(x), 1 / sr)
    def biquad_mag(b, a):
        z = np.exp(-2j * np.pi * f / sr)
        return np.abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))
    H = biquad_mag([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]) * \
        biquad_mag([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])
    m = x if x.ndim == 2 else x[:, None]
    return np.stack([np.fft.irfft(np.fft.rfft(m[:, c]) * H, len(m)) for c in range(m.shape[1])], 1)


def st_loudness(xk, t_end, win=0.4, sr=SR):
    """short-term loudness (LUFS) of a K-weighted stereo signal over the 400 ms window ending at t_end."""
    b = int(round(t_end * sr)); a = b - int(win * sr)
    if a < 0 or b > len(xk) or b <= a:
        return -99.0
    ms = float((xk[a:b] ** 2).mean(axis=0).sum())
    return -0.691 + 10 * math.log10(max(ms, 1e-14))


def ssim(a, b):
    """global-window-free SSIM (8x8 box windows) on float grey images 0..255."""
    a = a.astype(np.float64); b = b.astype(np.float64)
    def box(x, k=8):
        c = np.cumsum(np.cumsum(np.pad(x, ((1, 0), (1, 0))), 0), 1)
        return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = box(a), box(b)
    va, vb, cab = box(a * a) - ma ** 2, box(b * b) - mb ** 2, box(a * b) - ma * mb
    s = ((2 * ma * mb + C1) * (2 * cab + C2)) / ((ma ** 2 + mb ** 2 + C1) * (va + vb + C2))
    return float(s.mean())


def blur3(x):
    p = np.pad(x.astype(np.float64), 1, mode='edge')
    return sum(p[i:i + x.shape[0], j:j + x.shape[1]] for i in range(3) for j in range(3)) / 9.0


def rgb_frames(p, w, h, first, count):
    r = sh(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f'select=between(n\\,{first}\\,{first + count - 1}),scale={w}:{h}:flags=area,format=rgb24',
            '-vsync', '0', '-f', 'rawvideo', '-'], 600, binary=True)
    a = np.frombuffer(r.stdout, np.uint8)
    n = a.size // (w * h * 3)
    return a[:n * w * h * 3].reshape(n, h, w, 3)


def read_png_gray(p, w, h):
    r = sh(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f'scale={w}:{h}:flags=area,format=gray', '-frames:v', '1', '-f', 'rawvideo', '-'], 60, binary=True)
    a = np.frombuffer(r.stdout, np.uint8)
    if a.size < w * h:
        raise ValueError(f'cannot decode {p.name}')
    return a[:w * h].reshape(h, w)


def frame_gray(p, idx, w, h):
    r = sh(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f'select=eq(n\\,{idx}),scale={w}:{h}:flags=area,format=gray', '-vsync', '0',
            '-frames:v', '1', '-f', 'rawvideo', '-'], 300, binary=True)
    a = np.frombuffer(r.stdout, np.uint8)
    if a.size < w * h:
        raise ValueError(f'cannot decode frame {idx} of {p.name}')
    return a[:w * h].reshape(h, w)
