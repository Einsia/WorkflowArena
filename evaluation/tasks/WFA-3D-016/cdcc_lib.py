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
d = {"version": bpy.app.version_string, "objects": {}, "scenes": {}}
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
