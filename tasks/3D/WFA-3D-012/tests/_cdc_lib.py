# -*- coding: utf-8 -*-
"""Shared deterministic helpers for CDC-C verifier checks (ffmpeg/numpy/cv2 only; blender optional).
Every helper is defensive: on error it raises, and callers wrap each rubric item individually."""
import csv, json, math, os, pathlib, re, shutil, subprocess
import numpy as np

SR = 48000
FPS = 30


def run(cmd, timeout=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def find_root(out):
    """Directory that contains base/ (normally /workspace/output)."""
    out = pathlib.Path(out)
    if (out / 'base').is_dir():
        return out
    for p in sorted(out.rglob('base')):
        if p.is_dir() and (p / 'output.mp4').exists():
            return p.parent
    return out


def find_file(root, name):
    root = pathlib.Path(root)
    if (root / name).exists():
        return root / name
    c = sorted(root.rglob(name), key=lambda p: len(p.parts))
    return c[0] if c else None


# ---------------- probing ----------------
def ffprobe(p, count=False):
    cmd = ['ffprobe', '-v', 'error']
    if count:
        cmd += ['-count_frames']
    cmd += ['-show_streams', '-show_format', '-of', 'json', str(p)]
    return json.loads(run(cmd, 600).stdout)


def video_contract(p, nframes):
    """Returns (ok, detail) for the H.264/yuv420p/1280x720/SAR1/CFR30/AAC stereo 48k contract."""
    if not p or not pathlib.Path(p).exists():
        return False, 'file missing'
    j = ffprobe(p, count=True)
    vs = [s for s in j.get('streams', []) if s.get('codec_type') == 'video']
    as_ = [s for s in j.get('streams', []) if s.get('codec_type') == 'audio']
    if not vs:
        return False, 'no video stream'
    v = vs[0]
    prob = []
    if v.get('codec_name') != 'h264': prob.append(f"codec={v.get('codec_name')}")
    if v.get('pix_fmt') != 'yuv420p': prob.append(f"pix_fmt={v.get('pix_fmt')}")
    if (v.get('width'), v.get('height')) != (1280, 720): prob.append(f"size={v.get('width')}x{v.get('height')}")
    sar = v.get('sample_aspect_ratio', '1:1')
    if sar not in ('1:1', '0:1', None): prob.append(f'SAR={sar}')
    if v.get('r_frame_rate') != '30/1' or v.get('avg_frame_rate') != '30/1':
        prob.append(f"fps r={v.get('r_frame_rate')} avg={v.get('avg_frame_rate')}")
    n = int(v.get('nb_read_frames') or -1)
    if n != nframes: prob.append(f'frames={n} (need {nframes})')
    if not as_:
        prob.append('no audio')
    else:
        a = as_[0]
        if a.get('codec_name') != 'aac': prob.append(f"acodec={a.get('codec_name')}")
        if int(a.get('channels') or 0) != 2: prob.append(f"channels={a.get('channels')}")
        if str(a.get('sample_rate')) != '48000': prob.append(f"sr={a.get('sample_rate')}")
        try:
            ad = float(a.get('duration') or j['format']['duration'])
            if ad < nframes / FPS - 1.0 / FPS - 1e-3: prob.append(f'audio dur {ad:.3f}s < picture')
        except Exception:
            prob.append('audio duration unknown')
    return (not prob), ('ok' if not prob else '; '.join(prob)) + f' | frames={n}'


def stem_format(p, dur):
    if not p or not pathlib.Path(p).exists():
        return False, f'{p} missing'
    j = ffprobe(p)
    a = [s for s in j.get('streams', []) if s.get('codec_type') == 'audio']
    if not a:
        return False, f'{pathlib.Path(p).name}: no audio'
    a = a[0]
    prob = []
    if not str(a.get('codec_name', '')).startswith('pcm_'): prob.append(f"codec={a.get('codec_name')}")
    if str(a.get('sample_rate')) != '48000': prob.append(f"sr={a.get('sample_rate')}")
    try:
        d = float(a.get('duration') or j['format']['duration'])
    except Exception:
        d = -1
    if abs(d - dur) > 1.0 / FPS + 1e-3: prob.append(f'dur={d:.4f} (need {dur}±1 frame)')
    return (not prob), f"{pathlib.Path(p).name}: " + ('ok' if not prob else '; '.join(prob)) + f' dur={d:.4f}'


# ---------------- audio ----------------
def load_audio(p, ch=1):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:a:0', '-f', 'f32le', '-ac', str(ch), '-ar', str(SR), '-'],
                       capture_output=True, timeout=300)
    a = np.frombuffer(r.stdout, dtype=np.float32)
    if a.size == 0:
        raise RuntimeError(f'cannot decode audio {p}')
    return a.reshape(-1, ch) if ch > 1 else a.copy()


def env_db(x, win):
    n = len(x) // win
    if n == 0:
        return np.array([-200.0])
    y = x[:n * win].reshape(n, win).astype(np.float64)
    return 20 * np.log10(np.sqrt((y ** 2).mean(1)) + 1e-12)


def lowpass(x, fc=4000.0):
    X = np.fft.rfft(x.astype(np.float64))
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    X[f > fc] = 0
    return np.fft.irfft(X, len(x))


def bandpass(x, lo, hi):
    X = np.fft.rfft(x.astype(np.float64))
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def loudness(p, true_peak=False):
    """Integrated LUFS and peak (dBFS or dBTP) via ffmpeg ebur128."""
    r = run(['ffmpeg', '-nostats', '-v', 'info', '-i', str(p), '-map', '0:a:0', '-af',
             'ebur128=peak=' + ('true' if true_peak else 'sample'), '-f', 'null', '-'], 600)
    t = r.stderr
    tail = t[t.rfind('Summary:'):] if 'Summary:' in t else t
    I = float(re.search(r'I:\s*(-?[\d.]+|-inf)\s*LUFS', tail).group(1))
    pk = re.search(r'Peak:\s*(-?[\d.]+|-inf)\s*dBFS', tail)
    return I, (float(pk.group(1)) if pk else None)


def clipped_runs(p, thr=0.999, run_len=3):
    a = load_audio(p, 2)
    m = (np.abs(a) >= thr)
    cnt = 0
    for c in range(m.shape[1]):
        x = m[:, c].astype(np.int8)
        if not x.any():
            continue
        d = np.diff(np.concatenate([[0], x, [0]]))
        s, e = np.where(d == 1)[0], np.where(d == -1)[0]
        cnt += int(((e - s) >= run_len).sum())
    return cnt, float(np.abs(a).max())


def best_lag(ref, sig, maxlag):
    """Lag L (samples) maximising corr(ref[n], sig[n+L])."""
    n = min(len(ref), len(sig))
    a, b = ref[:n], sig[:n]
    N = 1 << int(math.ceil(math.log2(2 * n)))
    c = np.fft.irfft(np.fft.rfft(b, N) * np.conj(np.fft.rfft(a, N)), N)
    lags = np.concatenate([np.arange(0, maxlag + 1), np.arange(-maxlag, 0)])
    vals = np.concatenate([c[:maxlag + 1], c[N - maxlag:]])
    return int(lags[int(np.argmax(vals))])


def shift(x, L, n):
    """y[k] = x[k+L] for k in [0,n)."""
    y = np.zeros(n)
    s0, s1 = max(0, -L), min(n, len(x) - L)
    if s1 > s0:
        y[s0:s1] = x[s0 + L:s1 + L]
    return y


def stems_vs_mix(mix_p, stem_ps, t0=None, t1=None):
    """Fit stem gains to the decoded mix in the <=4 kHz band. Returns dict with fitted gains (linear), residual dB, lag."""
    mix = load_audio(mix_p, 1)
    stems = [load_audio(p, 1) for p in stem_ps]
    n = min([len(mix)] + [len(s) for s in stems])
    mix = mix[:n].astype(np.float64)
    stems = [s[:n].astype(np.float64) for s in stems]
    L = best_lag(np.sum(stems, 0), mix, int(0.05 * SR))
    mixa = shift(mix, L, n)
    a, b = (0, n) if t0 is None else (int(t0 * SR), min(n, int(t1 * SR)))
    ml = lowpass(mixa)[a:b]
    S = np.stack([lowpass(s)[a:b] for s in stems], 1)
    g, *_ = np.linalg.lstsq(S, ml, rcond=None)
    res = ml - S @ g
    rdb = 10 * np.log10(max((res ** 2).mean(), 1e-30) / max((ml ** 2).mean(), 1e-20))
    return {'gains': g.tolist(), 'residual_db': float(rdb), 'lag_samples': L, 'S': S, 'ml': ml}


def residual_with_gains(fit, gains):
    res = fit['ml'] - fit['S'] @ np.asarray(gains, float)
    return float(10 * np.log10(max((res ** 2).mean(), 1e-30) / max((fit['ml'] ** 2).mean(), 1e-20)))


def find_gains(tl, names):
    """Locate declared master gains for each stem name anywhere in timeline.json. Returns {name: value} or None."""
    found = {}

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                kl = str(k).lower()
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    for nm in names:
                        if nm in kl and ('gain' in kl or 'gain' in path):
                            found.setdefault(nm, []).append((path + '/' + kl, float(v)))
                    if 'gain' in kl:
                        for nm in names:
                            if nm in path.lower():
                                found.setdefault(nm, []).append((path + '/' + kl, float(v)))
                walk(v, path + '/' + kl)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                if isinstance(v, dict):
                    nm_here = ' '.join(str(v.get(k, '')) for k in ('name', 'stem', 'id', 'file', 'track')).lower()
                    for nm in names:
                        if nm in nm_here:
                            for k2, v2 in v.items():
                                if 'gain' in str(k2).lower() and isinstance(v2, (int, float)) and not isinstance(v2, bool):
                                    found.setdefault(nm, []).append((path + f'[{i}]/' + str(k2).lower(), float(v2)))
                walk(v, path + f'[{i}]')
    walk(tl, '')
    if not all(n in found for n in names):
        return None
    return {n: found[n][0] for n in names}


def gains_match(fit, declared, names, tol_db=1.0):
    """declared {name: (key, value)}; value may be dB or linear (key hint 'db'). Returns (ok, detail)."""
    fitted = fit['gains']
    out = []
    for interp in ('auto', 'linear', 'db'):
        ok, det = True, []
        for i, nm in enumerate(names):
            key, v = declared[nm]
            isdb = ('db' in key) if interp == 'auto' else (interp == 'db')
            lin = 10 ** (v / 20) if isdb else v
            if lin <= 0 or fitted[i] <= 0:
                ok = False; det.append(f'{nm}: declared {v} fitted {fitted[i]:.3f}'); continue
            e = 20 * math.log10(fitted[i] / lin)
            det.append(f'{nm}: decl {lin:.3f} fit {fitted[i]:.3f} ({e:+.2f} dB)')
            ok &= abs(e) <= tol_db
        out.append((ok, interp + ': ' + ', '.join(det)))
        if ok:
            return True, out[-1][1]
    return False, ' || '.join(d for _, d in out)


def onset_time(x, thr_db=-50, win_ms=10, start=0.0):
    w = int(SR * win_ms / 1000)
    e = env_db(x[int(start * SR):], w)
    idx = np.where(e > thr_db)[0]
    return None if not idx.size else start + idx[0] * w / SR


def segments(x, thr_db=-45, win_ms=10, min_ms=50, merge_ms=300):
    """Energy VAD -> list of (t0, t1) seconds."""
    w = int(SR * win_ms / 1000)
    e = env_db(x, w) > thr_db
    d = np.diff(np.concatenate([[0], e.astype(np.int8), [0]]))
    s, t = list(np.where(d == 1)[0]), list(np.where(d == -1)[0])
    segs = []
    for a, b in zip(s, t):
        if segs and (a - segs[-1][1]) * win_ms < merge_ms:
            segs[-1][1] = b
        else:
            segs.append([a, b])
    return [(a * w / SR, b * w / SR) for a, b in segs if (b - a) * win_ms >= min_ms]


def transient_at(x, t, tol, rise_db=12.0, prior=0.5, win_ms=5):
    """Is there a window within t±tol whose level is >= rise_db above the floor (median) of the prior `prior` s?"""
    w = int(SR * win_ms / 1000)
    a = max(0, int((t - tol - prior) * SR))
    seg = x[a:int((t + tol) * SR) + w]
    e = env_db(seg, w)
    k0 = int(prior * SR / w)
    if len(e) <= k0:
        return False, 'segment too short'
    floor = float(np.median(e[:k0]))
    pk = float(e[k0:].max())
    return pk - floor >= rise_db, f'peak {pk:.1f} dB vs floor {floor:.1f} dB (+{pk - floor:.1f})'


def onsets(x, rise_db=12.0, win_ms=5, prior_ms=200, refractory_ms=60):
    w = int(SR * win_ms / 1000)
    e = env_db(x, w)
    k = int(prior_ms / win_ms)
    res, last = [], -1e9
    for i in range(k, len(e)):
        bg = np.median(e[i - k:i])
        if e[i] - bg >= rise_db and e[i] > -70 and (i - last) * win_ms >= refractory_ms:
            res.append(i * w / SR); last = i
    return res


# ---------------- video ----------------
def gray_frames(p, w=320, h=180, every=1):
    vf = f'scale={w}:{h}:flags=area,format=gray'
    if every > 1:
        vf = f"select='not(mod(n\\,{every}))'," + vf
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:v:0', '-vf', vf, '-vsync', '0', '-f', 'rawvideo', '-'],
                       capture_output=True, timeout=900)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    n = a.size // (w * h)
    if n == 0:
        raise RuntimeError(f'cannot decode video {p}')
    return a[:n * w * h].reshape(n, h, w)


def detect_cuts(fr):
    """Hard-cut detector on gray frames. Returns (cuts, diffs, freezes, soft) where cut index c = first frame of new shot."""
    f = fr.astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    # histogram distance as second cue
    hs = np.stack([np.histogram(x, 32, (0, 256))[0] for x in fr]).astype(np.float32)
    hs /= hs.sum(1, keepdims=True)
    hd = 0.5 * np.abs(np.diff(hs, axis=0)).sum(1)
    med = float(np.median(d)) if d.size else 0
    thr = max(12.0, 6 * med)
    cuts = [i + 1 for i in range(len(d)) if (d[i] > thr) and (d[i] >= 3 * max(d[i - 1] if i > 0 else 0, d[i + 1] if i + 1 < len(d) else 0)) or (hd[i] > 0.5 and d[i] > max(8.0, 4 * med))]
    cuts = sorted(set(cuts))
    # soft/gradual transitions: sustained elevated diffs (>=3 consecutive frames > 3*med and > 4)
    soft = []
    run = 0
    for i in range(len(d)):
        if d[i] > max(4.0, 3 * med) and (i + 1) not in cuts:
            run += 1
            if run == 4:
                soft.append(i - 2)
        else:
            run = 0
    # freezes: >= 6 identical consecutive frames => >=5 consecutive near-zero diffs
    fz, run = [], 0
    for i in range(len(d)):
        if d[i] < 0.02:
            run += 1
            if run == 5:
                fz.append(i - 4)
        else:
            run = 0
    return cuts, d, fz, soft


def hard_cut_ok(d, c):
    """No blend frame at cut c: the neighbouring diffs are small compared with the cut diff."""
    i = c - 1
    nb = [d[j] for j in (i - 2, i - 1, i + 1, i + 2) if 0 <= j < len(d)]
    return all(x < 0.35 * d[i] for x in nb)


def psnr(a, b):
    m = np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2)
    return 99.0 if m < 1e-10 else float(10 * np.log10(255.0 ** 2 / m))


def ssim_render(a, b, sigma=2.0):
    """SSIM between a verifier re-render and a delivered frame after a Gaussian blur (sigma 2 px at 480x270) of both:
    the re-render is 8 spp and, in the verifier image (Debian Blender 4.3.2, no OpenImageDenoise), not denoised, so raw
    SSIM mostly measures path-tracing noise (measured 0.61-0.91 for an identical scene); after the blur an identical scene
    scores >= 0.99 while a different shot/framing still scores far lower."""
    import cv2
    g = lambda x: cv2.GaussianBlur(np.asarray(x, np.float64), (0, 0), sigma)
    return ssim(g(a), g(b))


def ssim(a, b):
    import cv2
    a = a.astype(np.float64); b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    ma, mb = g(a), g(b)
    va, vb, cab = g(a * a) - ma ** 2, g(b * b) - mb ** 2, g(a * b) - ma * mb
    s = ((2 * ma * mb + C1) * (2 * cab + C2)) / ((ma ** 2 + mb ** 2 + C1) * (va + vb + C2))
    return float(s.mean())


def frame_at(p, f, w=640, h=360):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f"select='eq(n\\,{f})',scale={w}:{h}:flags=area,format=gray",
                        '-vsync', '0', '-frames:v', '1', '-f', 'rawvideo', '-'], capture_output=True, timeout=300)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    if a.size < w * h:
        raise RuntimeError(f'frame {f} not decodable')
    return a[:w * h].reshape(h, w)


def flat_block_index(g):
    """Share of 8x8 luma blocks that are flat (variance < 1.0) AND equal in mean (<0.5) to all 4 neighbours, i.e.
    posterised / flat-shaded regions; smooth gradients and bokeh (neighbour means differ) are not counted.
    Blocks with mean < 24 or > 235 (night darks / highlights) are excluded."""
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
    k = keep[1:-1, 1:-1].sum()
    return float(flat.sum() / max(k, 1))


def freeze_runs(p, min_run=6, w=1280, h=720, tol=2):
    """Freezes: runs of >= min_run consecutive decoded frames that are identical up to codec rounding (no full-resolution
    luma pixel differs by more than `tol` levels from the previous frame; an H.264-encoded duplicate frame differs by
    <= 2 levels, any real motion or render noise by far more). Streamed. Returns list of (start_frame, run_length)."""
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


# ---------------- events / json ----------------
def read_events(p):
    """Returns (header_ok, events{id: frame}, problems)."""
    with open(p, newline='', encoding='utf-8-sig') as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise ValueError('empty csv')
    hdr = [c.strip() for c in rows[0]]
    ev, dup, bad = {}, [], []
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        k = r[0].strip()
        try:
            v = float(r[1])
            if v != int(v):
                raise ValueError
            v = int(v)
        except Exception:
            bad.append(k); continue
        if k in ev:
            dup.append(k)
        ev[k] = v
    return hdr == ['event_id', 'frame', 'description'], ev, dup, bad


def load_json(p):
    return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))


# ---------------- blender ----------------
def blender_ok():
    return shutil.which('blender') is not None


BLEND_DUMP = r'''
import bpy, json, sys, os
argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]; track = json.loads(argv[1]); trim = int(argv[2]) if len(argv) > 2 else None
sc = bpy.context.scene
d = {"opened": True, "file": bpy.data.filepath, "version": bpy.app.version_string,
     "objects": {o.name: o.type for o in bpy.data.objects},
     "parents": {o.name: (o.parent.name if o.parent else None) for o in bpy.data.objects},
     "scene_props": {k: (sc[k] if isinstance(sc[k], (int, float, str)) else str(sc[k])) for k in sc.keys()},
     "frame_range": [sc.frame_start, sc.frame_end], "fps": sc.render.fps,
     "armature_mods": {o.name: [m.object.name for m in o.modifiers if m.type == "ARMATURE" and m.object] for o in bpy.data.objects if o.type == "MESH"},
     "bbox": {}, "mats": {}}
if trim is not None and trim >= 0 and "revision_trim_frames" in sc.keys():
    sc["revision_trim_frames"] = trim
for n in track:
    o = bpy.data.objects.get(n)
    if o is not None and o.type == "MESH":
        d["bbox"][n] = [list(c) for c in o.bound_box]
d["mats"] = {}
f0, f1 = sc.frame_start, sc.frame_end
f0 = min(f0, 0); f1 = max(f1, int(argv[3]) if len(argv) > 3 else f1)
for f in range(f0, f1 + 1):
    sc.frame_set(f)
    row = {}
    for n in track:
        o = bpy.data.objects.get(n)
        if o is not None:
            row[n] = [list(r) for r in o.matrix_world]
    d["mats"][f] = row
json.dump(d, open(out, "w"))
print("DUMP_OK")
'''


def blend_dump(blend, track, tmp, trim=None, last_frame=899, timeout=900):
    """Run blender headless; returns dict or {'opened': False, 'error': ...}. Returns None if blender is unavailable."""
    if not blender_ok():
        return None
    tmp = pathlib.Path(tmp)
    s = tmp / 'cdc_blend_dump.py'
    s.write_text(BLEND_DUMP)
    o = tmp / f'cdc_blend_dump_{trim}.json'
    if o.exists():
        o.unlink()
    args = ['blender', '-b', '-y', str(blend), '--python-exit-code', '1', '--python', str(s), '--', str(o), json.dumps(track)]
    args += [str(trim if trim is not None else -1)]
    args += [str(last_frame)]
    try:
        r = run(args, timeout)
    except Exception as e:
        return {'opened': None, 'error': f'blender run error: {e}'}
    if o.exists():
        d = json.loads(o.read_text())
        d['mats'] = {int(k): v for k, v in d['mats'].items()}
        if trim is not None and trim < 0:
            pass
        return d
    txt = (r.stdout + r.stderr)[-1500:]
    opened = not re.search(r'(Unable to open|Error: Cannot read file|not a blend file|File format is not supported)', txt, re.I)
    return {'opened': False if not opened else None, 'error': txt}


RENDER_PY = r'''
import bpy, sys
if getattr(bpy.app, "autoexec_fail", False):
    # the file's registered scripts were blocked (no -y support in this Blender build): run them as -y would
    for _t in bpy.data.texts:
        if _t.use_module:
            try:
                exec(compile(_t.as_string(), _t.name, "exec"), {"__name__": _t.name})
            except Exception as _e:
                print("autoexec emulation failed for", _t.name, _e)
argv = sys.argv[sys.argv.index("--") + 1:]
f = int(argv[0]); out = argv[1]; trim = int(argv[2]); fallback = argv[3] if len(argv) > 3 else ""
W, H, spp, force_cycles = int(argv[4]), int(argv[5]), int(argv[6]), argv[7] == "1"
sc = bpy.context.scene
if "revision_trim_frames" in sc.keys():
    sc["revision_trim_frames"] = trim
sc.frame_set(f)
has_bound = any(m.camera for m in sc.timeline_markers)
if not has_bound and fallback and fallback in bpy.data.objects:
    sc.camera = bpy.data.objects[fallback]
sc.frame_set(f)
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

RENDER_W, RENDER_H, RENDER_SPP = 480, 270, 8


def blend_render(blend, frame, tmp, trim=0, fallback_cam='', timeout=200):
    """Render one scene frame (480x270, 8 spp; solver engine, retried once with Cycles if that produced no image)
    -> (gray uint8 array at RENDER_W x RENDER_H or None, note)."""
    import cv2
    tmp = pathlib.Path(tmp)
    s = tmp / 'cdc_render.py'
    s.write_text(RENDER_PY)
    note = []
    for force in ('0', '1'):
        o = tmp / f'cdc_render_{trim}_{frame}_{force}.png'
        try:
            run(['blender', '-b', '-y', str(blend), '--python', str(s), '--', str(frame), str(o), str(trim), fallback_cam,
                 str(RENDER_W), str(RENDER_H), str(RENDER_SPP), force], timeout)
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


def M(dump, name, f):
    return np.array(dump['mats'][f][name], float)


def rot_of(m):
    r = m[:3, :3].copy()
    for i in range(3):
        n = np.linalg.norm(r[:, i])
        if n > 0:
            r[:, i] /= n
    return r


def rel_angle(r1, r2):
    """Angle (deg) and axis of rotation from r1 to r2."""
    R = r1.T @ r2
    c = max(-1.0, min(1.0, (np.trace(R) - 1) / 2))
    ax = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    n = np.linalg.norm(ax)
    return math.degrees(math.acos(c)), (ax / n if n > 1e-12 else np.zeros(3))


CRED_RE = re.compile(r'(sk-[A-Za-z0-9]{16,}|api[_-]?key\s*[:=]\s*\S{8,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|xox[bp]-[A-Za-z0-9-]{10,})', re.I)
URL_MEDIA_RE = re.compile(r'https?://\S+\.(png|jpe?g|exr|hdr|wav|mp3|mp4|mov|blend|fbx|obj|glb|gltf|tif)\b', re.I)


def scan_text_tree(root, exts=('.md', '.txt', '.json', '.py', '.csv', '.yaml', '.yml', '.toml', '.sh')):
    hits = []
    for p in pathlib.Path(root).rglob('*'):
        if p.is_file() and p.suffix.lower() in exts and p.stat().st_size < 5_000_000:
            try:
                t = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            for rx, tag in ((CRED_RE, 'credential'), (URL_MEDIA_RE, 'url-media')):
                m = rx.search(t)
                if m:
                    hits.append(f'{tag} in {p.name}: {m.group(0)[:40]}')
    return hits
