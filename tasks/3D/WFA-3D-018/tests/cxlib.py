# -*- coding: utf-8 -*-
"""Shared deterministic helpers for CDC-C verifiers (numpy + cv2 + ffmpeg only; blender optional).
Every helper is defensive: it returns None / raises a plain Exception that the caller turns into a 'fail' verdict."""
import csv, json, math, os, pathlib, re, shutil, subprocess
import numpy as np

SR = 48000


def sh(cmd, timeout=600, binary=False):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, text=not binary)
    return r


def pv(d, v, detail):
    return {'verdict': 'pass' if v else 'fail', 'detail': detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False, default=str)[:900]}


def F(detail):
    return {'verdict': 'fail', 'detail': str(detail)[:900]}


def P(detail):
    return {'verdict': 'pass', 'detail': str(detail)[:900]}


# ---------------- probing ----------------
def rate(s):
    try:
        a, b = str(s).split('/')
        return float(a) / float(b) if float(b) else 0.0
    except Exception:
        try:
            return float(s)
        except Exception:
            return 0.0


def probe(path):
    r = sh(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', str(path)], 600)
    return json.loads(r.stdout)


def video_contract(path, fps, n_frames, w=1280, h=720, min_audio=None):
    """Returns (ok, detail dict)."""
    j = probe(path)
    vs = [s for s in j.get('streams', []) if s.get('codec_type') == 'video']
    au = [s for s in j.get('streams', []) if s.get('codec_type') == 'audio']
    d, bad = {}, []
    if not vs:
        return False, {'error': 'no video stream'}
    v = vs[0]
    d.update(codec=v.get('codec_name'), pix=v.get('pix_fmt'), size=[v.get('width'), v.get('height')], sar=v.get('sample_aspect_ratio'),
             r=v.get('r_frame_rate'), avg=v.get('avg_frame_rate'), frames=v.get('nb_read_frames'))
    if v.get('codec_name') != 'h264': bad.append('codec')
    if v.get('pix_fmt') != 'yuv420p': bad.append('pix_fmt')
    if (v.get('width'), v.get('height')) != (w, h): bad.append('size')
    if v.get('sample_aspect_ratio') not in (None, '1:1', '0:1'): bad.append('sar')
    if abs(rate(v.get('r_frame_rate')) - fps) > 1e-3 or abs(rate(v.get('avg_frame_rate')) - fps) > 1e-2: bad.append('fps')
    try:
        nf = int(v.get('nb_read_frames'))
    except Exception:
        nf = -1
    if nf != n_frames: bad.append(f'frames={nf}')
    # constant pts spacing
    try:
        r = sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'frame=pts_time', '-of', 'csv=p=0', str(path)], 600)
        t = np.array([float(x.strip().rstrip(',')) for x in r.stdout.split() if x.strip().rstrip(',') not in ('', 'N/A')])
        if len(t) > 2:
            dt = np.diff(np.sort(t))
            d['pts_dt_dev'] = float(np.max(np.abs(dt - 1.0 / fps)))
            if d['pts_dt_dev'] > 0.5 / fps * 0.5: bad.append('vfr_pts')
    except Exception as e:
        d['pts_err'] = str(e)
    if not au:
        bad.append('no_audio')
    else:
        a = au[0]
        d.update(acodec=a.get('codec_name'), ch=a.get('channels'), asr=a.get('sample_rate'), adur=a.get('duration'))
        if a.get('codec_name') != 'aac': bad.append('acodec')
        if a.get('channels') != 2: bad.append('channels')
        if str(a.get('sample_rate')) != '48000': bad.append('asr')
        need = min_audio if min_audio is not None else n_frames / fps - 0.03
        try:
            if float(a.get('duration') or j['format']['duration']) < need: bad.append('audio_short')
        except Exception:
            bad.append('audio_dur?')
    d['bad'] = bad
    return not bad, d


def frame_count(path):
    try:
        j = probe(path)
        v = [s for s in j['streams'] if s.get('codec_type') == 'video'][0]
        return int(v.get('nb_read_frames'))
    except Exception:
        return -1


def wav_info(path):
    j = json.loads(sh(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(path)], 60).stdout)
    a = [s for s in j.get('streams', []) if s.get('codec_type') == 'audio'][0]
    return {'codec': a.get('codec_name'), 'sr': int(a.get('sample_rate', 0)), 'ch': a.get('channels'), 'dur': float(a.get('duration') or 0)}


def decode_audio(path, sr=SR, mono=True):
    # 2026-10-25: ffmpeg's mono->stereo upmix attenuates by 3 dB, so mono files are decoded as mono (exact samples);
    # stereo (or more) is decoded to stereo and averaged.
    try:
        j = json.loads(sh(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=channels', '-of', 'json', str(path)], 60).stdout)
        ch = int(j['streams'][0]['channels'])
    except Exception:
        ch = 2
    nc = 1 if ch == 1 else 2
    r = sh(['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-f', 'f32le', '-acodec', 'pcm_f32le', '-ar', str(sr), '-ac', str(nc), '-'], 600, binary=True)
    x = np.frombuffer(r.stdout, dtype='<f4').reshape(-1, nc).astype(np.float64)
    if x.size == 0:
        raise ValueError(f'cannot decode audio {path}')
    if mono:
        return x.mean(1)
    return np.repeat(x, 2, axis=1) if nc == 1 else x


def ebur128_I(path):
    r = sh(['ffmpeg', '-nostats', '-i', str(path), '-vn', '-af', 'ebur128', '-f', 'null', '-'], 600)
    m = re.findall(r'I:\s*(-?[\d.]+|-inf)\s*LUFS', r.stderr)
    return float(m[-1]) if m and m[-1] != '-inf' else None


def master_check(path, lo=-22, hi=-18, peak=0.891, clip_run=3):
    I = ebur128_I(path)
    x = decode_audio(path, mono=False)
    pk = float(np.max(np.abs(x)))
    a = (np.abs(x) >= 0.999).any(1).astype(np.int8)
    best = 0
    if a.any():
        d = np.diff(np.concatenate([[0], a, [0]]))
        s, e = np.where(d == 1)[0], np.where(d == -1)[0]
        best = int((e - s).max())
    ok = I is not None and lo <= I <= hi and pk <= peak and best < clip_run
    return ok, {'I': I, 'peak': round(pk, 4), 'clip_run': best, 'n_clip': int(a.sum())}


def gray_frames(path, w=320, h=180):
    r = sh(['ffmpeg', '-v', 'error', '-i', str(path), '-vf', f'scale={w}:{h},format=gray', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], 900, binary=True)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    n = a.size // (w * h)
    return a[:n * w * h].reshape(n, h, w)


def rgb_frames(path, w=320, h=180):
    r = sh(['ffmpeg', '-v', 'error', '-i', str(path), '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], 900, binary=True)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    n = a.size // (w * h * 3)
    return a[:n * w * h * 3].reshape(n, h, w, 3)


def psnr(a, b):
    m = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return 99.0 if m < 1e-10 else 10 * math.log10(255 ** 2 / m)


def ssim(a, b):
    import cv2
    a = a.astype(np.float64); b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    k = (7, 7); s = 1.5
    mu1, mu2 = cv2.GaussianBlur(a, k, s), cv2.GaussianBlur(b, k, s)
    s11 = cv2.GaussianBlur(a * a, k, s) - mu1 ** 2
    s22 = cv2.GaussianBlur(b * b, k, s) - mu2 ** 2
    s12 = cv2.GaussianBlur(a * b, k, s) - mu1 * mu2
    m = ((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 ** 2 + mu2 ** 2 + C1) * (s11 + s22 + C2))
    return float(m.mean())


def hist_diff(a, b):
    import cv2
    ha = cv2.calcHist([a], [0], None, [32], [0, 256]).ravel(); hb = cv2.calcHist([b], [0], None, [32], [0, 256]).ravel()
    ha /= ha.sum() + 1e-9; hb /= hb.sum() + 1e-9
    return float(0.5 * np.abs(ha - hb).sum())


def cut_scores(G):
    """per transition f-1 -> f: combined content score (mean abs diff/255 + histogram diff)."""
    sc = np.zeros(len(G))
    for f in range(1, len(G)):
        sc[f] = np.mean(np.abs(G[f].astype(np.int16) - G[f - 1].astype(np.int16))) / 255.0 + hist_diff(G[f], G[f - 1])
    return sc


def detect_cuts(G, rel=4.0, absmin=0.12):
    """Hard-cut candidates: score > absmin and > rel × local median (±12 frames)."""
    sc = cut_scores(G)
    cuts = []
    for f in range(1, len(G)):
        lo, hi = max(1, f - 12), min(len(G), f + 13)
        med = np.median(np.delete(sc[lo:hi], f - lo)) if hi - lo > 1 else 0
        if sc[f] > absmin and sc[f] > rel * max(med, 0.005):
            cuts.append(f)
    return cuts, sc


def freezes(G, thr=55.0, run=1):
    """indices f where frame f equals f-1 (PSNR>thr)."""
    return [f for f in range(1, len(G)) if psnr(G[f], G[f - 1]) > thr]


def flat_block_index(g, bs=16, std_thr=0.5, dark=3):
    h, w = g.shape
    h2, w2 = h // bs * bs, w // bs * bs
    b = g[:h2, :w2].astype(np.float64).reshape(h2 // bs, bs, w2 // bs, bs).swapaxes(1, 2).reshape(-1, bs * bs)
    sd, mu = b.std(1), b.mean(1)
    keep = mu >= dark
    if keep.sum() == 0:
        return 0.0
    return float(((sd < std_thr) & keep).sum() / keep.sum())


# ---------------- audio envelopes ----------------
def env_db(x, sr=SR, win=0.01, hop=0.01):
    n, hp = int(win * sr), int(hop * sr)
    if len(x) < n:
        return np.array([]), np.array([])
    k = 1 + (len(x) - n) // hp
    idx = np.arange(k) * hp
    e = np.array([np.sqrt(np.mean(x[i:i + n] ** 2) + 1e-20) for i in idx])
    return (idx + n / 2) / sr, 20 * np.log10(e + 1e-12)


def band_env(x, sr, lo, hi, win=0.1, hop=0.05, medfilt=0):
    """STFT band envelope in dBFS; optional median filter along frequency (removes narrow-band tones)."""
    n, hp = int(win * sr), int(hop * sr)
    k = 1 + (len(x) - n) // hp
    wnd = np.hanning(n)
    fr = np.fft.rfftfreq(n, 1 / sr)
    top = np.searchsorted(fr, hi) + (medfilt or 0) + 2
    out = np.zeros(k)
    sel = (fr[:top] >= lo) & (fr[:top] <= hi)
    for i in range(k):
        seg = x[i * hp:i * hp + n] * wnd
        S = np.abs(np.fft.rfft(seg))[:top] ** 2
        if medfilt:
            pad = np.pad(S, medfilt // 2, mode='edge')
            S = np.median(np.lib.stride_tricks.sliding_window_view(pad, medfilt), axis=1)[:top]
        out[i] = S[sel].sum() * 2 / (np.sum(wnd ** 2) * n)
    t = (np.arange(k) * hp + n / 2) / sr
    return t, 10 * np.log10(out + 1e-14)


def win_med(t, e, a, b, mask=None):
    m = (t >= a) & (t <= b)
    if mask is not None:
        m &= mask
    return float(np.median(e[m])) if m.any() else None


def click_check(x, sr, t, w=0.005, ref=1.0, k=3.0):
    """No click at time t: max |diff| within ±w is ≤ k × 99.9 percentile of |diff| in surrounding ±ref s."""
    d = np.abs(np.diff(x))
    i0, i1 = max(0, int((t - w) * sr)), min(len(d), int((t + w) * sr))
    r0, r1 = max(0, int((t - ref) * sr)), min(len(d), int((t + ref) * sr))
    if i1 <= i0 or r1 <= r0:
        return True, None
    p = np.percentile(d[r0:r1], 99.9)
    m = d[i0:i1].max()
    return bool(m <= k * p + 1e-9), round(float(m / (p + 1e-12)), 2)


def transient_at(x, sr, t, tol, rise_db=10.0, pre=0.2):
    te, e = env_db(x, sr, 0.01, 0.005)
    m = (te >= t - tol) & (te <= t + tol)
    if not m.any():
        return False, None
    i = np.where(m)[0][np.argmax(e[m])]
    pm = (te >= te[i] - pre - 0.01) & (te < te[i] - 0.01)
    base = np.median(e[pm]) if pm.any() else -120
    return bool(e[i] - base >= rise_db), round(float(e[i] - base), 1)


# ---------------- deliverable text ----------------
def read_events(path):
    txt = pathlib.Path(path).read_text(encoding='utf-8-sig')
    rows = list(csv.reader(txt.splitlines()))
    hdr = [c.strip() for c in rows[0]] if rows else []
    ev, bad = {}, []
    for r in rows[1:]:
        if not r or not ''.join(r).strip():
            continue
        try:
            ev[r[0].strip()] = int(r[1].strip())
        except Exception:
            bad.append(r[:2])
    return hdr, ev, bad


def find_gain_sets(tl, stems):
    """Collect candidate {stem: linear gain} maps from a free-form timeline.json."""
    out = []

    def lin(k, v):
        try:
            v = float(v)
        except Exception:
            return None
        return 10 ** (v / 20) if ('db' in k.lower() or v < 0) else v

    def walk(o, path=''):
        if isinstance(o, dict):
            # form 1: {"speech": 1.0, "rain": 0.8, ...} under a key containing gain
            keys = {k.lower(): k for k in o}
            if 'gain' in path.lower() or any('gain' in k for k in keys):
                g = {}
                for s in stems:
                    for k in o:
                        if s in k.lower():
                            v = o[k]
                            if isinstance(v, dict):
                                for kk, vv in v.items():
                                    if 'gain' in kk.lower() and lin(kk, vv) is not None:
                                        g[s] = lin(kk, vv)
                            elif lin(path + k, v) is not None:
                                g[s] = lin(path + k, v)
                if len(g) == len(stems):
                    out.append(g)
            # form 2: per-stem objects carrying a gain field
            for k, v in o.items():
                walk(v, path + '/' + str(k))
        elif isinstance(o, list):
            g = {}
            for it in o:
                if isinstance(it, dict):
                    nm = ' '.join(str(it.get(k, '')) for k in ('name', 'stem', 'id', 'file', 'track')).lower()
                    for s in stems:
                        if s in nm:
                            for kk, vv in it.items():
                                if 'gain' in kk.lower() and lin(kk, vv) is not None:
                                    g[s] = lin(kk, vv)
                walk(it, path)
            if len(g) == len(stems):
                out.append(g)
    walk(tl)
    uniq = []
    for g in out:
        if g not in uniq:
            uniq.append(g)
    return uniq


def band_db(x):
    """1/3-octave band energies (dB), 100 ms frames, ~50 Hz-14 kHz."""
    fr = 4800
    n = len(x) // fr
    if n < 5:
        return None
    X = np.abs(np.fft.rfft(x[:n * fr].reshape(n, fr) * np.hanning(fr), axis=1)) ** 2
    f = np.fft.rfftfreq(fr, 1 / SR)
    cs = [1000 * 2 ** (k / 3) for k in range(-13, 12)]
    cs = [c for c in cs if 45 <= c <= 14500]
    B = np.stack([X[:, (f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))].sum(1) for c in cs], 1)
    return 10 * np.log10(B + 1e-20)


def align_lag(ref, x, maxlag=2048):
    """lag such that ref[lag:] ~ x (positive) or ref ~ x[-lag:] (negative); cross-correlation over <=10 s."""
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


def _apply_lag(mix, x, lag):
    if lag > 0:
        mix = mix[lag:]
    elif lag < 0:
        x = x[-lag:]
    n = min(len(mix), len(x))
    return mix[:n], x[:n]


def band_compare(mix, summ):
    """median / p95 |band dB diff| between decoded mix and stem sum (bands within 40 dB of frame max)."""
    lag = align_lag(mix, summ)
    m, s = _apply_lag(mix, summ, lag)
    A, B = band_db(m), band_db(s)
    if A is None:
        return None
    mask = (A >= A.max(1, keepdims=True) - 40) & (A.max(1, keepdims=True) > -80)
    d = np.abs(A - B)[mask]
    if d.size == 0:
        return None
    return dict(lag=lag, median=float(np.median(d)), p95=float(np.percentile(d, 95)))


def lowpass(x, fc=4000.0):
    X = np.fft.rfft(x)
    X[np.fft.rfftfreq(len(x), 1 / SR) > fc] = 0
    return np.fft.irfft(X, len(x))


def fit_stem_gains(mix, stems, lag):
    """least-squares stem gains vs mix in the <=4 kHz band (AAC-robust), after alignment by lag."""
    names = list(stems)
    n = min(len(v) for v in stems.values())
    cols = []
    for k in names:
        m, s = _apply_lag(mix, stems[k][:n], lag)
        cols.append(s)
    L = min(len(c) for c in cols)
    m = _apply_lag(mix, stems[names[0]][:n], lag)[0][:L]
    S = np.stack([lowpass(c[:L]) for c in cols], 1)
    g, *_ = np.linalg.lstsq(S, lowpass(m), rcond=None)
    return dict(zip(names, (float(v) for v in g)))


def stem_sum_bandcheck(mix_path, stem_paths, gains):
    """decoded mix vs Σ g·stem: band comparison + fitted gains. Returns dict."""
    mx = decode_audio(mix_path)
    st = {k: decode_audio(p) for k, p in stem_paths.items()}
    n = min(len(v) for v in st.values())
    summ = sum(gains[k] * st[k][:n] for k in st)
    c = band_compare(mx, summ)
    if c is None:
        return None
    fit = fit_stem_gains(mx, st, c['lag'])
    err = {k: (20 * math.log10(fit[k] / gains[k]) if fit[k] > 0 and gains[k] > 0 else float('inf')) for k in st}
    c.update(fitted={k: round(v, 4) for k, v in fit.items()}, gain_err_db={k: round(v, 2) for k, v in err.items()},
             max_gain_err_db=max(abs(v) for v in err.values()))
    return c


def scan_credentials(root):
    pat = re.compile(r'(sk-[A-Za-z0-9_\-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[bpa]-[A-Za-z0-9\-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
    hits = []
    for p in pathlib.Path(root).rglob('*'):
        if p.is_file() and p.suffix.lower() in ('.md', '.txt', '.json', '.csv', '.py', '.sh', '.yaml', '.yml', '.toml', '.cfg', '.ini', '.env'):
            try:
                if pat.search(p.read_text(encoding='utf-8', errors='ignore')):
                    hits.append(str(p.relative_to(root)))
            except Exception:
                pass
    return hits


# ---------------- blender ----------------
BLEND_DUMP = r'''
import bpy, json, math, os, re, sys, traceback
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
cfg = json.load(open(argv[0])); OUTF = argv[1]
sc = bpy.context.scene; OB = bpy.data.objects; R = {"errors": []}
def guard(n, fn):
    try: fn()
    except Exception as e: R["errors"].append(n + ": " + traceback.format_exc()[-500:])
def basic():
    R["version"] = bpy.app.version_string
    R["objects"] = {o.name: {"type": o.type, "parent": o.parent.name if o.parent else None,
                     "arm_mods": [m.object.name if m.object else None for m in o.modifiers if m.type == "ARMATURE"]} for o in OB}
    R["frame_range"] = [sc.frame_start, sc.frame_end]
    R["scene_props"] = {k: (sc[k] if isinstance(sc[k], (int, float, str)) else str(sc[k])) for k in sc.keys() if not k.startswith("_")}
    R["engine"] = sc.render.engine; R["motion_blur"] = bool(sc.render.use_motion_blur)
guard("basic", basic)
def files():
    bad, urls = [], []
    for coll in (bpy.data.images, bpy.data.sounds, bpy.data.movieclips, bpy.data.libraries, bpy.data.fonts):
        for d in coll:
            fp = getattr(d, "filepath", "") or ""
            if not fp or getattr(d, "packed_file", None) or fp.startswith("<"): continue
            if re.match(r"https?://", fp): urls.append(fp); continue
            if getattr(d, "source", "FILE") in ("GENERATED", "VIEWER"): continue
            ap = bpy.path.abspath(fp)
            if "#" in ap or "<UDIM>" in ap: continue
            if not os.path.exists(ap): bad.append(fp)
    R["missing_files"] = bad[:30]; R["n_missing"] = len(bad); R["url_refs"] = urls[:10]
guard("files", files)
def rigs():
    out = {}
    for rn, mn in cfg.get("rigs", {}).items():
        r = OB.get(rn); d = {"exists": bool(r), "is_armature": bool(r and r.type == "ARMATURE")}
        meshes = [o for o in OB if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == r for m in o.modifiers)] if r else []
        d["bound_meshes"] = [o.name for o in meshes]
        m = OB.get(mn); d["char_bound"] = False; d["vg_cover"] = None
        if m:
            cands = [m] + [c for c in m.children_recursive if c.type == "MESH"]
            for c in cands:
                if c.type == "MESH" and any(md.type == "ARMATURE" and md.object == r for md in c.modifiers):
                    d["char_bound"] = True
                    names = {g.index for g in c.vertex_groups if r and g.name in r.data.bones}
                    n = len(c.data.vertices); cov = sum(1 for v in c.data.vertices if any(g.group in names and g.weight > 0 for g in v.groups))
                    d["vg_cover"] = max(d["vg_cover"] or 0, cov / max(n, 1))
        hands = []; keyed = set()
        if r and r.type == "ARMATURE":
            def chain_len(b):
                n = 1
                while len(b.children) == 1: b = b.children[0]; n += 1
                return n if not b.children else 0
            for b in r.data.bones:
                ch = [c for c in b.children if chain_len(c) >= 3]
                if len(ch) >= 4: hands.append({"hand": b.name, "chains": len(ch), "bones": [x.name for c in ch for x in [c] + list(c.children_recursive)]})
            act = r.animation_data.action if r.animation_data else None
            if act:
                for fc in act.fcurves:
                    mm = re.match(r'pose\.bones\["(.+?)"\]', fc.data_path)
                    if mm and len(fc.keyframe_points) >= 2:
                        vals = [k.co[1] for k in fc.keyframe_points]
                        if max(vals) - min(vals) > 1e-4: keyed.add(mm.group(1))
        d["hands"] = [{"hand": h["hand"], "chains": h["chains"], "keyed_finger_bones": len(set(h["bones"]) & keyed)} for h in hands]
        out[rn] = d
    R["rigs"] = out
guard("rigs", rigs)
def cams():
    tr = {}
    for cn, (a, b) in cfg.get("cams", {}).items():
        c = OB.get(cn)
        if not c or c.type != "CAMERA": tr[cn] = None; continue
        rows = []
        for f in range(a, b + 1):
            sc.frame_set(f); m = c.matrix_world.copy(); fw = (m.to_3x3() @ Vector((0, 0, -1))).normalized(); d = c.data
            fd = d.dof.focus_distance
            if d.dof.focus_object: fd = (d.dof.focus_object.matrix_world.translation - m.translation).length
            rows.append([f, list(m.translation), list(fw), d.lens, bool(d.dof.use_dof), d.dof.aperture_fstop, fd])
        tr[cn] = rows
    R["cams"] = tr
guard("cams", cams)
def tracks():
    tr = {}
    fr = cfg.get("track_frames", [])
    for n in cfg.get("track", []):
        o = OB.get(n)
        if not o: tr[n] = None; continue
        rows = []
        for f in fr:
            sc.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg)
            pts = [e.matrix_world @ Vector(cc) for cc in e.bound_box]
            rows.append([f, list(sum(pts, Vector()) / 8), list(e.matrix_world.translation)])
        tr[n] = rows
    R["tracks"] = tr
guard("tracks", tracks)
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
            sc.frame_set(f); v = sum(kb.value for kb in mk)
            for pb in jaw[:2]:
                q = pb.matrix_basis.to_quaternion(); v += 2 * math.acos(max(-1, min(1, abs(q.w))))
            cur.append(v)
        out[rn] = {"start": a, "curve": cur, "sources": [kb.name for kb in mk][:10] + [pb.name for pb in jaw][:4]}
    R["mouth"] = out
guard("mouth", mouth)
json.dump(R, open(OUTF, "w"), default=str)
print("BLENDDUMP_OK")
'''


def find_blend(out):
    p = pathlib.Path(out) / 'project' / 'scene.blend'
    return p if p.exists() else None


def blender_dump(blend, cfg, tmp, timeout=1500):
    """Run blender -b to dump scene data. Returns dict, or None if blender unavailable; {'_error':..} on failure."""
    exe = shutil.which('blender')
    if not exe:
        return None
    tmp = pathlib.Path(tmp)
    sp = tmp / 'cx_blend_dump.py'; sp.write_text(BLEND_DUMP)
    cp = tmp / 'cx_blend_cfg.json'; cp.write_text(json.dumps(cfg))
    op = tmp / 'cx_blend_out.json'
    if op.exists():
        op.unlink()
    try:
        r = sh([exe, '-b', str(blend), '--python', str(sp), '--', str(cp), str(op)], timeout)
        log = (r.stdout or '')[-1500:] + (r.stderr or '')[-800:]
        if op.exists():
            d = json.loads(op.read_text())
            d['_rc'] = r.returncode
            d['_log_tail'] = log[-600:]
            return d
        return {'_error': 'no dump produced', '_rc': r.returncode, '_log_tail': log}
    except Exception as e:
        return {'_error': f'{type(e).__name__}: {e}'}


def cam_pitch_deg(fw):
    return math.degrees(math.asin(max(-1, min(1, fw[2]))))


def cam_yaw_deg(fw):
    return math.degrees(math.atan2(fw[1], fw[0]))
