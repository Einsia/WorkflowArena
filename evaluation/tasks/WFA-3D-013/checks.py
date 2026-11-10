# -*- coding: utf-8 -*-
"""CDC-C-X03 Attic Storm -- deterministic checks for rubric_score.py (cleanup 2026-10-25,
see review/rubric-cleanup-20261025.md).

Every scored item is decided here except the visual remainders of G01 (photoreal look) and G11 (narrative without
cards / overlays): those two are returned as 'fail' when their measured part fails and left to the judge (contact
sheets) otherwise. An exception inside one item turns only that item into 'fail' with the traceback tail.
Blender: one quick static inspection (B07) and one per-frame rich dump (tests/_cdc_blend.py) of project/scene.blend;
film frame f is measured at scene frame frame_start + f. A dump failure/timeout fails the affected items with the
reason; only a missing/unopenable scene.blend is reported as an open failure.
"""
import csv, json, math, pathlib, re, shutil, subprocess, sys, time, traceback
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import _cdc_blend as B

FPS, NFR, W, H = 24, 672, 1280, 536
DUR = NFR / FPS
SR = 48000
STEMS = ['dialogue', 'storm', 'foley']
LUFS, LUFS_TOL = -23.0, 1.0
EVENTS = ['line_start', 'line_end', 'window_burst', 'flash_peak', 'thunder_1', 'lamp_swing_start', 'mara_rise',
          'curtain_grab', 'window_shut', 'latch_click', 'thunder_far']
CUTS = {'T12': 144, 'T23': 264, 'T34': 408}
SHOTS = {'S1': (0, 143), 'S2': (144, 263), 'S3': (264, 407), 'S4': (408, 551), 'S5': (552, 671)}
SHOT_FR = {'S1': [24, 72, 120], 'S2': [160, 200, 230], 'S3': [300, 340, 380], 'S4': [430, 470, 510], 'S5': [590, 630, 660]}
CAMS = [f'CAM_S{i}' for i in range(1, 6)]
REQ_OBJ = {'MARA': None, 'MARA_RIG': 'ARMATURE', 'PENDANT_LAMP': None, 'LAMP_CORD': None, 'CURTAIN': None,
           'CURTAIN_ROD': None, 'WINDOW_SASH': None, 'WINDOW_LATCH': None, 'DESK': None, 'LAMP_LIGHT': 'LIGHT',
           'LIGHTNING': 'LIGHT', **{c: 'CAMERA' for c in CAMS}}
TRACK = ['PENDANT_LAMP', 'LAMP_LIGHT', 'LIGHTNING', 'WINDOW_SASH', 'WINDOW_LATCH', 'CURTAIN_ROD', 'DESK', 'MARA',
         'MARA_RIG'] + CAMS
HANDISH = re.compile(r'hand|palm|wrist|thumb|index|middle|ring|pinky|little|finger|f_', re.I)
RENDER_W, RENDER_H, RENDER_SPP = 480, 201, 8
BUDGET_S = 2700          # no new re-render is started after this many seconds of checks (verifier timeout 3600 s)
DUMP_TIMEOUT = 1800
STATE = {}


class _DumpFail(Exception):
    pass


# ---------------------------------------------------------------- helpers
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
        and abs(ad - DUR) <= 1.0 / FPS + 1e-3
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


def lowpass(x, fc):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[f > fc] = 0
    return np.fft.irfft(X, len(x))


def gray_frames(p, w=320):
    h = int(round(H * w / W / 2)) * 2
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:v:0', '-vf', f'scale={w}:{h}:flags=area,format=gray',
                        '-vsync', '0', '-f', 'rawvideo', '-'], capture_output=True, timeout=900)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    n = len(a) // (w * h)
    return a[:n * w * h].reshape(n, h, w).astype(np.float32)


def frames_at(p, idxs, w, h, fmt='gray'):
    """Decode the given frame indices (sorted, unique) -> dict idx -> array (gray HxW or rgb HxWx3 uint8)."""
    idxs = sorted(set(int(i) for i in idxs))
    sel = '+'.join(f'eq(n\\,{i})' for i in idxs)
    ch = 3 if fmt == 'rgb24' else 1
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:v:0', '-vf',
                        f"select='{sel}',scale={w}:{h}:flags=area,format={fmt}", '-vsync', '0', '-f', 'rawvideo', '-'],
                       capture_output=True, timeout=900)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    n = a.size // (w * h * ch)
    if n != len(idxs):
        raise RuntimeError(f'decoded {n} of {len(idxs)} requested frames from {p.name}')
    a = a[:n * w * h * ch].reshape((n, h, w, ch) if ch == 3 else (n, h, w))
    return {i: a[k] for k, i in enumerate(idxs)}


def image_gray(p, w, h):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f'scale={w}:{h}:flags=area,format=gray', '-frames:v', '1',
                        '-f', 'rawvideo', '-'], capture_output=True, timeout=120)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    return a[:w * h].reshape(h, w) if a.size >= w * h else None


def full_gray_stream(p, fn, w=W, h=H):
    """Stream full-resolution gray frames to fn(index, bytes)."""
    proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:v:0', '-vf', f'scale={w}:{h},format=gray',
                             '-vsync', '0', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
    n, k = w * h, 0
    try:
        while True:
            buf = proc.stdout.read(n)
            if len(buf) < n:
                break
            fn(k, buf)
            k += 1
    finally:
        proc.stdout.close()
        proc.wait(timeout=60)
    return k


def freeze_runs(p, min_run=6, min_psnr=60.0):
    """Runs of >= min_run consecutive decoded frames that are identical up to encoder noise (each frame within
    PSNR >= min_psnr dB of the previous one, full-resolution gray; H.264 does not reproduce a repeated source frame
    bit-exactly, while render noise or any motion keeps consecutive frames far below 60 dB)."""
    st = {'prev': None, 'run': 1, 'start': 0, 'out': []}

    def same(a, b):
        if a == b:
            return True
        x = np.frombuffer(a, np.uint8).astype(np.int16) - np.frombuffer(b, np.uint8).astype(np.int16)
        mse = float(np.mean(x.astype(np.float64) ** 2))
        return mse <= 1e-10 or 10 * math.log10(255 ** 2 / mse) >= min_psnr

    def fn(k, buf):
        if st['prev'] is not None and same(buf, st['prev']):
            st['run'] += 1
        else:
            if st['run'] >= min_run:
                st['out'].append((st['start'], st['run']))
            st['run'], st['start'] = 1, k
        st['prev'] = buf
    full_gray_stream(p, fn)
    if st['run'] >= min_run:
        st['out'].append((st['start'], st['run']))
    return st['out']


def psnr(a, b):
    m = float(((np.asarray(a, np.float64) - np.asarray(b, np.float64)) ** 2).mean())
    return 99.0 if m <= 1e-10 else 10 * math.log10(255 ** 2 / m)


def _gblur(x, sigma=1.5, r=5):
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(x, r, mode='reflect')
    y = sum(k[i] * p[i:i + x.shape[0], :] for i in range(2 * r + 1))
    y = sum(k[i] * y[:, i:i + x.shape[1]] for i in range(2 * r + 1))
    return y


def ssim(a, b):
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = _gblur(a), _gblur(b)
    va, vb, cab = _gblur(a * a) - ma ** 2, _gblur(b * b) - mb ** 2, _gblur(a * b) - ma * mb
    s = ((2 * ma * mb + C1) * (2 * cab + C2)) / ((ma ** 2 + mb ** 2 + C1) * (va + vb + C2))
    return float(s.mean())


def ncc_render(a, b, w=16):
    """Zero-mean normalised cross-correlation of a re-render and a delivered frame, both area-downsampled to w px wide.
    Robust to path-tracing noise and to small exposure differences, which dominate raw SSIM in this verifier image
    (Debian Blender 4.3.2 has no OpenImageDenoise, so re-renders are not denoised); a correct re-render of the same
    frame measured >= 0.855, a re-render compared with any other sampled frame <= 0.55 (worst case: the exposure-3.8
    S4 frame); the threshold is 0.72."""
    import cv2
    def sm(x):
        x = np.asarray(x, np.float32)
        h = max(2, int(round(x.shape[0] * w / x.shape[1])))
        return cv2.resize(x, (w, h), interpolation=cv2.INTER_AREA)
    a, b = sm(a), sm(b)
    if a.std() < 3 or b.std() < 3:
        return 0.0
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / max(float(np.sqrt((a * a).sum() * (b * b).sum())), 1e-9))

def ssim_render(a, b, sigma=2.0):
    """SSIM after a Gaussian blur (sigma 2 px at 480x270) of both images: the re-render is 8 spp and, in the verifier
    image (Debian Blender 4.3.2, no OpenImageDenoise), not denoised, so raw SSIM is dominated by path-tracing noise;
    after the blur an identical scene scores >= 0.99 while a different shot/framing stays far below."""
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = _gblur(a, sigma), _gblur(b, sigma)
    va, vb, cab = _gblur(a * a, sigma) - ma ** 2, _gblur(b * b, sigma) - mb ** 2, _gblur(a * b, sigma) - ma * mb
    s = ((2 * ma * mb + C1) * (2 * cab + C2)) / ((ma ** 2 + mb ** 2 + C1) * (va + vb + C2))
    return float(s.mean())

def flat_block_index(g):
    """Share of 8x8 luma blocks (mean 24-235) that are flat (variance < 1.0) AND within 0.5 of the mean of all 4
    neighbouring blocks (posterised / flat-shaded regions; smooth gradients and bokeh are not counted)."""
    g = np.asarray(g, np.float64)
    h, w = g.shape
    hb, wb = h // 8, w // 8
    b = g[:hb * 8, :wb * 8].reshape(hb, 8, wb, 8).transpose(0, 2, 1, 3).reshape(hb, wb, 64)
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


def srgb_lab(rgb):
    """uint8 RGB (...,3) -> (L*, a*, b*, linear luminance Y) with D65 white."""
    c = np.asarray(rgb, np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    Mx = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ Mx.T
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[..., 1] - 16
    return L, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2]), xyz[..., 1]


def blend_frames(frames, ia, ib, rng, thr_r2=0.70):
    """Count frames in rng that are a linear mix of frames ia and ib (fit on 4x-downscaled, blurred gray).
    Returns (list of blend frame indices, list of (i, r2, share_of_b)).
    thr_r2 0.70: this verifier image's Blender has no OpenImageDenoise, so a dissolve rendered at a moderate sample
    count carries per-frame noise that lowers r2 to ~0.79 mid-dissolve; 0.70 still rejects frames outside a dissolve
    (measured 0.0-0.6 there)."""
    def small(x):
        h, w = x.shape[0] // 4 * 4, x.shape[1] // 4 * 4
        return _gblur(x[:h, :w].reshape(h // 4, 4, w // 4, 4).mean((1, 3)), 1.0, 3)
    A, Bb = small(frames[ia]).ravel(), small(frames[ib]).ravel()
    X = np.stack([A, Bb, np.ones_like(A)], 1)
    out, info = [], []
    for i in rng:
        y = small(frames[i]).ravel()
        c, res, *_ = np.linalg.lstsq(X, y, rcond=None)
        ss = float(((y - y.mean()) ** 2).sum()) + 1e-9
        r2 = 1 - float(((X @ c - y) ** 2).sum()) / ss
        sb = c[1] / (c[0] + c[1]) if abs(c[0] + c[1]) > 1e-6 else 0.0
        info.append((i, round(r2, 3), round(float(sb), 3)))
        if r2 >= thr_r2 and 0.05 < sb < 0.95 and c[0] > -0.05 and c[1] > -0.05:
            out.append(i)
    return out, info


def numbers_in(o, out=None):
    out = [] if out is None else out
    if isinstance(o, dict):
        for v in o.values():
            numbers_in(v, out)
    elif isinstance(o, list):
        for v in o:
            numbers_in(v, out)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        out.append(float(o))
    elif isinstance(o, str):
        m = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(s|f|fr|frames?)?\s*', o)
        if m:
            out.append(float(m.group(1)) if m.group(2) != 's' else float(m.group(1)))
    return out


def has_number(nums, frame, tol=1.0):
    """frame value present as a frame number or as seconds (x24)."""
    return any(abs(v - frame) <= tol + 1e-6 or (v <= 30 and abs(v * FPS - frame) <= tol + 1e-3) for v in nums)


def corr_lag(a, b, maxlag=3):
    a, b = np.asarray(a, float), np.asarray(b, float)
    best = (0.0, 0)
    for lag in range(-maxlag, maxlag + 1):
        u, v = (a[lag:], b[:len(b) - lag]) if lag >= 0 else (a[:lag], b[-lag:])
        if len(u) < 8 or np.std(u) < 1e-12 or np.std(v) < 1e-12:
            continue
        r = float(np.corrcoef(u, v)[0, 1])
        if abs(r) > abs(best[0]):
            best = (r, lag)
    return best


def detrend(x):
    x = np.asarray(x, float)
    t = np.arange(len(x))
    if len(x) < 3:
        return x - x.mean()
    p = np.polyfit(t, x, 1)
    return x - np.polyval(p, t)


# ---------------------------------------------------------------- Blender-side extra measurements
EXTRA = r'''
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
SKIP_COLL = {"CURTAIN", "CURTAIN_ROD", "MARA", "PENDANT_LAMP", "LAMP_CORD", "DESK", "WINDOW_LATCH"}
def _mesh_world(o, dg):
    e = o.evaluated_get(dg)
    m = e.to_mesh()
    try:
        mw = e.matrix_world
        vs = [mw @ v.co for v in m.vertices]
        m.calc_loop_triangles()
        tris = [tuple(t.vertices) for t in m.loop_triangles]
    finally:
        e.to_mesh_clear()
    return vs, tris
def _bvh(o, dg):
    vs, tris = _mesh_world(o, dg)
    return BVHTree.FromPolygons(vs, tris) if tris else None
def _wbox(o, dg):
    e = o.evaluated_get(dg)
    return [e.matrix_world @ Vector(c) for c in e.bound_box]
def _depth(bvh, p, flip):
    r = bvh.find_nearest(p, 0.5)
    if r is None or r[0] is None:
        return 0.0
    loc, nrm, idx, dist = r
    if dist is None or dist < 1e-6:
        return 0.0
    d = p - loc
    s = d.dot(nrm) * flip
    if s < 0 and abs(d.dot(nrm)) >= 0.9 * dist:
        return dist
    return 0.0
def _orient(bv, ctx):
    # +1 if the room reference point (DESK, else MARA, at the first sampled frame) is on the front side of the
    # collider's nearest face, -1 if the mesh normals point away from the room (then the sides are swapped)
    ref = ctx.get("_ref")
    if ref is None:
        return 1.0
    r = bv.find_nearest(ref)
    if r is None or r[0] is None:
        return 1.0
    return 1.0 if (ref - r[0]).dot(r[1]) >= 0 else -1.0
def setup(ctx):
    bpy, sc, D, cfg = ctx["bpy"], ctx["sc"], ctx["D"], ctx["cfg"]
    X = D["x03"] = {"lamp_c": {}, "lamp_box": {}, "cord_top": {}, "lights": {}, "cur_speed": {}, "rod_dist": {},
                    "cur_pen": {}, "cur_pts": {}, "finger_pen": {}, "colliders": [], "flip": {}}
    OB = bpy.data.objects
    try:
        se = sc.sequence_editor
        X["strips"] = [[s.name, s.type, s.channel, s.frame_final_start, s.frame_final_end] for s in se.sequences_all] if se else []
    except Exception as e:
        X["strips"] = []; X["strips_err"] = str(e)[:200]
    ext = []
    for coll in (bpy.data.images, bpy.data.sounds, bpy.data.movieclips, bpy.data.libraries):
        for it in coll:
            fp = getattr(it, "filepath", "") or ""
            ext.append([it.name, fp, bool(getattr(it, "packed_file", None))])
    X["ext_files"] = ext[:200]
    cur = OB.get("CURTAIN")
    X["cur_ok"] = bool(cur and cur.type == "MESH")
    ctx["_pin"] = []
    if X["cur_ok"]:
        X["cur_verts"] = len(cur.data.vertices)
        pin = None
        for m in cur.modifiers:
            if m.type == "CLOTH":
                pin = m.settings.vertex_group_mass or None
        idx = []
        if pin and pin in cur.vertex_groups:
            gi = cur.vertex_groups[pin].index
            idx = [v.index for v in cur.data.vertices if any(g.group == gi and g.weight >= 0.5 for g in v.groups)]
        X["pin_group"] = pin; X["pin_n"] = len(idx)
        ctx["_pin"] = idx
    ctx["_prev"] = None; ctx["_first"] = True
    xc = cfg.get("x03", {})
    ctx["_curf"] = set(xc.get("cur_frames", [])); ctx["_fingf"] = set(xc.get("finger_frames", []))
def _init_first(ctx, dg):
    bpy, D = ctx["bpy"], ctx["D"]; X = D["x03"]; OB = bpy.data.objects
    ctx["_first"] = False
    sash = OB.get("WINDOW_SASH")
    cols = []
    if sash is not None and sash.type == "MESH":
        bb = _wbox(sash, dg); c = sum(bb, Vector()) / 8
        cols.append("WINDOW_SASH")
        rig_mesh = set(n for n, ms in D.get("armature_mods", {}).items() if ms)
        cand = []
        for o in OB:
            if o.type != "MESH" or o.name in SKIP_COLL or o.name in cols or o.name in rig_mesh:
                continue
            if o.parent is not None and o.parent.type == "ARMATURE":
                continue
            try:
                b2 = _wbox(o, dg)
            except Exception:
                continue
            lo = [min(v[k] for v in b2) - 0.2 for k in range(3)]; hi = [max(v[k] for v in b2) + 0.2 for k in range(3)]
            if all(lo[k] <= c[k] <= hi[k] for k in range(3)):
                vol = (hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2])
                cand.append((vol, o.name))
        cols += [n for _, n in sorted(cand, reverse=True)[:5]]
    X["colliders"] = cols
    refo = OB.get("DESK") or OB.get("MARA")
    ctx["_ref"] = refo.matrix_world.translation.copy() if refo is not None else None
    cur = OB.get("CURTAIN")
    if X["cur_ok"]:
        n = len(cur.evaluated_get(dg).data.vertices)
        ctx["_sub"] = list(range(0, n, max(1, n // 1500)))
def frame(ctx, f):
    bpy, D, dg = ctx["bpy"], ctx["D"], ctx["dg"]; X = D["x03"]; OB = bpy.data.objects
    if ctx["_first"]:
        _init_first(ctx, dg)
    # lights (all LIGHT objects): energy, hide_render, world location
    X["lights"][f] = {o.name: [round(float(o.data.energy), 5), bool(o.hide_render)] + [round(float(v), 5) for v in o.matrix_world.translation]
                      for o in OB if o.type == "LIGHT"}
    lamp = OB.get("PENDANT_LAMP")
    if lamp is not None:
        objs = [lamp] if lamp.type in ("MESH", "CURVE", "SURFACE", "META", "FONT") else [c for c in lamp.children_recursive if c.type == "MESH"]
        bb = []
        for o in objs:
            bb += _wbox(o, dg)
        if bb:
            X["lamp_c"][f] = [round(float(v), 5) for v in (sum(bb, Vector()) / len(bb))]
            X["lamp_box"][f] = [[min(v[k] for v in bb) for k in range(3)], [max(v[k] for v in bb) for k in range(3)]]
        else:
            X["lamp_c"][f] = [float(v) for v in lamp.matrix_world.translation]
    cord = OB.get("LAMP_CORD")
    if cord is not None and cord.type in ("MESH", "CURVE", "SURFACE"):
        vs, _ = _mesh_world(cord, dg)
        if vs:
            top = max(vs, key=lambda v: v.z)
            X["cord_top"][f] = [round(float(v), 5) for v in top]
    cur = OB.get("CURTAIN")
    if X["cur_ok"]:
        e = cur.evaluated_get(dg); m = e.to_mesh(); mw = e.matrix_world
        try:
            sub = ctx.get("_sub") or []
            vs = m.vertices
            pts = [mw @ vs[i].co for i in sub if i < len(vs)]
            if not ctx["_pin"] or max(ctx["_pin"]) >= len(vs):
                if "_top" not in ctx:
                    allp = [mw @ v.co for v in vs]
                    zmax = max(p.z for p in allp); zmin = min(p.z for p in allp)
                    ctx["_top"] = [i for i, p in enumerate(allp) if p.z >= zmax - max(0.02, 0.02 * (zmax - zmin))]
                    X["top_band_n"] = len(ctx["_top"])
                top_idx = ctx["_top"]
            else:
                top_idx = ctx["_pin"]
            toppts = [mw @ vs[i].co for i in top_idx[::max(1, len(top_idx) // 300)] if i < len(vs)]
            nvert = len(vs)
        finally:
            e.to_mesh_clear()
        prev = ctx["_prev"]
        X["cur_speed"][f] = (sum((a - b).length for a, b in zip(pts, prev)) / max(1, len(pts))) if prev is not None and len(prev) == len(pts) else None
        ctx["_prev"] = pts
        if f in ctx["_curf"]:
            X["cur_pts"][f] = [[round(p.x, 4), round(p.y, 4), round(p.z, 4)] for p in pts[::max(1, len(pts) // 600)]]
        if f % 4 == 0:
            rod = OB.get("CURTAIN_ROD")
            if rod is not None and rod.type in ("MESH", "CURVE"):
                bv = _bvh(rod, dg)
                if bv is not None and toppts:
                    ds = []
                    for p in toppts:
                        r = bv.find_nearest(p)
                        ds.append(r[3] if r and r[3] is not None else 9.0)
                    X["rod_dist"][f] = max(ds)
            pen = {}
            for cn in X["colliders"]:
                co = OB.get(cn)
                bv = _bvh(co, dg) if co is not None else None
                if bv is None:
                    continue
                if cn not in X["flip"]:
                    X["flip"][cn] = _orient(bv, ctx)
                fl = X["flip"][cn]
                dmax = 0.0
                for p in pts:
                    dd = _depth(bv, p, fl)
                    if dd > dmax:
                        dmax = dd
                pen[cn] = round(dmax, 4)
            X["cur_pen"][f] = pen
    if f in ctx["_fingf"]:
        rig, sash = OB.get("MARA_RIG"), OB.get("WINDOW_SASH")
        if rig is not None and rig.type == "ARMATURE" and sash is not None and sash.type == "MESH":
            bv = _bvh(sash, dg)
            if "WINDOW_SASH" not in X["flip"] and bv is not None:
                X["flip"]["WINDOW_SASH"] = _orient(bv, ctx)
            fl = X["flip"].get("WINDOW_SASH", 1.0)
            best = [0.0, None]
            if bv is not None:
                mw = rig.matrix_world
                import re as _re
                for pb in rig.pose.bones:
                    if not _re.search(r"thumb|index|middle|ring|pinky|little|finger|f_", pb.name, _re.I):
                        continue
                    h, t = mw @ pb.head, mw @ pb.tail
                    for k in (0.0, 0.5, 1.0):
                        dd = _depth(bv, h.lerp(t, k), fl)
                        if dd > best[0]:
                            best = [round(dd, 4), pb.name]
            X["finger_pen"][f] = best
'''


# ---------------------------------------------------------------- re-render (G10)
RENDER_PY = r'''
import bpy, sys
argv = sys.argv[sys.argv.index("--") + 1:]
f = int(argv[0]); out = argv[1]; fallback = argv[2]
Wr, Hr, spp, force_cycles = int(argv[3]), int(argv[4]), int(argv[5]), argv[6] == "1"
if getattr(bpy.app, "autoexec_fail", False):
    for _t in bpy.data.texts:
        if _t.use_module:
            try:
                exec(compile(_t.as_string(), _t.name, "exec"), {"__name__": _t.name})
            except Exception as _e:
                print("autoexec emulation failed for", _t.name, _e)
sc = bpy.context.scene
sc.frame_set(f)
has_bound = any(m.camera for m in sc.timeline_markers)
if not has_bound and fallback and fallback in bpy.data.objects:
    sc.camera = bpy.data.objects[fallback]
sc.frame_set(f)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = Wr, Hr, 100
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


def blend_render(blend, frame, tmp, cam, timeout=200):
    tmp = pathlib.Path(tmp)
    s = tmp / 'x03_render.py'
    s.write_text(RENDER_PY)
    note = []
    for force in ('0', '1'):
        o = tmp / f'x03_render_{frame}_{force}.png'
        if o.exists():
            o.unlink()
        try:
            subprocess.run(['blender', '-b', '-y', str(blend), '--python', str(s), '--', str(frame), str(o), cam,
                            str(RENDER_W), str(RENDER_H), str(RENDER_SPP), force], capture_output=True, timeout=timeout)
        except Exception as e:
            note.append(f'render {"cycles " if force == "1" else ""}error/timeout: {type(e).__name__}')
            if force == '0':
                continue
            return None, '; '.join(note)
        if o.exists():
            g = image_gray(o, RENDER_W, RENDER_H)
            if g is not None:
                if force == '1':
                    note.append('solver engine produced no image; re-rendered with Cycles')
                return g, '; '.join(note)
        note.append('no image written' + (' (cycles retry)' if force == '1' else ''))
    return None, '; '.join(note)


# ---------------------------------------------------------------- run
def run(ctx):
    R = {}
    STATE.clear()
    t_start = time.time()
    out = ctx['out']
    base, rev, proj = out / 'base', out / 'revision', out / 'project'
    bmp, rmp = base / 'output.mp4', rev / 'output.mp4'
    tmp = pathlib.Path(ctx['tmp'])
    blend = proj / 'scene.blend'

    def item(iid, fn):
        try:
            v = fn()
            if v is not None:
                R[iid] = v
        except _DumpFail as e:
            R[iid] = F(str(e))
        except Exception as e:
            R[iid] = F(f'check error: {type(e).__name__}: {e} | {traceback.format_exc()[-300:]}')

    # ---------- B01-B04 ----------
    item('B01', lambda: P(*video_contract(bmp)))

    def b02():
        if not bmp.exists():
            return F('base/output.mp4 missing')
        return P(*audio_contract(bmp))
    item('B02', b02)

    def b03():
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
    item('B03', b03)

    def b04():
        ok, d = video_contract(rmp)
        tl = read_json(rev / 'timeline.json') if (rev / 'timeline.json').exists() else None
        return P(ok and tl is not None, dict(video=d, timeline_json=tl is not None))
    item('B04', b04)

    # ---------- B05 ----------
    stems = {}

    def stem(s):
        if s not in stems:
            p = base / 'stems' / f'{s}.wav'
            stems[s] = decode_audio(p) if p.exists() else None
        return stems[s]

    def b05():
        det = {}
        tl = read_json(base / 'timeline.json') if (base / 'timeline.json').exists() else None
        sts = {}
        for s in STEMS:
            p = base / 'stems' / f'{s}.wav'
            if not p.exists():
                return F(f'stems/{s}.wav missing')
            inf = stem_info(p)
            det[s] = inf
            if not (str(inf['codec']).startswith('pcm_') and str(inf['sr']) == str(SR) and abs(inf['dur'] - DUR) <= 1 / FPS + 1e-3):
                return F(f'stem {s} spec wrong: {inf}')
            sts[s] = stem(s)
        if not bmp.exists() or tl is None:
            return F('base/output.mp4 or base/timeline.json missing/unparseable')
        cands = find_gains(tl, STEMS)
        if not cands:
            return F('no per-stem master gains found in timeline.json')
        mix = decode_audio(bmp)
        best = None
        n = min(len(v) for v in sts.values())
        for g in cands:
            summ = sum(g[s] * sts[s][:n] for s in STEMS)
            c = band_compare(mix, summ)
            if c and (best is None or c['median'] < best[1]['median']):
                best = (g, c)
        if best is None:
            return F('band comparison impossible (silent/short)')
        g, c = best
        STATE['gains'] = g
        return P(c['median'] <= 0.75 and c['p95'] <= 3.0, dict(gains_lin={k: round(v, 4) for k, v in g.items()}, **c))
    item('B05', b05)

    # ---------- B06 events ----------
    ev = {}

    def b06():
        p = base / 'events.csv'
        if not p.exists():
            return F('base/events.csv missing')
        hok, e, prob = read_events(p)
        ev.update({k: v for k, v in e.items() if k in EVENTS})
        miss = [k for k in EVENTS if k not in e]
        bad = [k for k in EVENTS if k in e and not 0 <= e[k] <= NFR - 1]
        rules = []
        if not miss:
            chk = [('line_start<line_end', e['line_start'] < e['line_end']),
                   ('window_burst in S2 [144,264)', 144 <= e['window_burst'] < 264),
                   ('flash_peak 258-270', 258 <= e['flash_peak'] <= 270),
                   ('thunder_1>flash_peak', e['thunder_1'] > e['flash_peak']),
                   ('lamp_swing_start>=window_burst', e['lamp_swing_start'] >= e['window_burst']),
                   ('curtain_grab<window_shut<=latch_click', e['curtain_grab'] < e['window_shut'] <= e['latch_click']),
                   ('thunder_far 540-671', 540 <= e['thunder_far'] <= 671)]
            rules = [n for n, v in chk if not v]
        ok = hok and not miss and not bad and not rules and not [x for x in prob if any(x.startswith(k + ' ') for k in EVENTS)]
        return P(ok, dict(header_ok=hok, missing=miss, out_of_range=bad, failed_rules=rules, parse=prob[:5]))
    item('B06', b06)

    def evreq(*ks):
        miss = [k for k in ks if k not in ev]
        if miss:
            raise _DumpFail(f'events.csv does not declare {miss}')
        return [int(min(NFR - 1, max(0, ev[k]))) for k in ks]

    # ---------- dialogue envelope: M02 / M03 ----------
    DLG = {}

    def m02():
        x = stem('dialogue')
        if x is None:
            return F('dialogue stem missing')
        win = int(0.02 * SR)
        e = rms_env(x, win)
        t = (np.arange(len(e)) + 0.5) * 0.02
        act = e > -40
        if not act.any():
            return F('dialogue stem never above -40 dBFS')
        on = float(t[np.argmax(act)]) - 0.01
        idx = np.where(act)[0]
        segs, s0 = [], idx[0]
        for a, b in zip(idx[:-1], idx[1:]):
            if (b - a) * 0.02 > 0.4:
                segs.append((s0, a)); s0 = b
        segs.append((s0, idx[-1]))
        segs_t = [(float(t[a]) - 0.01, float(t[b]) + 0.01) for a, b in segs]
        first_end = segs_t[0][1]
        DLG.update(on=on, off=first_end)
        after = e[(t > first_end + 0.04) & (t < 11.0)]
        others = segs_t[1:]
        ok = on < 6.0 and abs(first_end - 6.5) <= 2 / FPS + 1e-3 and (after.size == 0 or after.max() <= -50) and not others
        return P(ok, dict(onset_s=round(on, 3), offset_s=round(first_end, 3), max_after_dBFS=round(float(after.max()), 1) if after.size else None,
                          extra_segments=[(round(a, 2), round(b, 2)) for a, b in others][:5]))
    item('M02', m02)

    def m03():
        if 'on' not in DLG:
            return F('dialogue line not measurable (see M02)')
        if 'line_start' not in ev or 'line_end' not in ev:
            return F('line_start/line_end not declared in events.csv')
        ds, de = ev['line_start'] / FPS, ev['line_end'] / FPS
        ok = abs(ds - DLG['on']) <= 4 / FPS + 1e-3 and abs(de - DLG['off']) <= 4 / FPS + 1e-3
        return P(ok, f'declared {ds:.3f}-{de:.3f} s vs measured {DLG["on"]:.3f}-{DLG["off"]:.3f} s (tolerance 4 frames = 0.167 s)')
    item('M03', m03)

    # ---------- M10 thunder ----------
    def m10():
        x = stem('storm')
        if x is None:
            return F('storm stem missing')
        t1f, tff, fpf = evreq('thunder_1', 'thunder_far', 'flash_peak')
        lf = lowpass(x, 200)
        e = rms_env(lf, int(0.05 * SR))
        tt = (np.arange(len(e)) + 0.5) * 0.05

        def seg(a, b):
            return e[(tt >= a) & (tt < b)]
        t1, tf, fp = t1f / FPS, tff / FPS, fpf / FPS
        pre = seg(max(0, t1 - 1.5), t1 - 0.5)
        basel = float(np.median(pre)) if pre.size else float(np.median(e))
        m = (tt >= t1 - 0.5) & (tt < t1 + 0.5)
        pk1 = float(e[(tt >= t1) & (tt < t1 + 3.0)].max()) if ((tt >= t1) & (tt < t1 + 3.0)).any() else -200
        above = np.where(m & (e >= max(basel + 6, pk1 - 20)))[0]
        onset = float(tt[above[0]] - 0.025) if above.size else None
        th1 = seg(t1, min(DUR, t1 + 3.0))
        peak1 = float(th1.max()) if th1.size else -200
        rise = peak1 - basel
        lag = t1 - fp
        thf = seg(tf, min(DUR, tf + 2.5))
        peakf = float(thf.max()) if thf.size else -200
        rng1 = float(th1.max() - th1.min()) if th1.size else 0
        rngf = float(thf.max() - thf.min()) if thf.size else 0
        a, b = int(tf * SR), int(min(DUR, tf + 2.5) * SR)
        lfshare = 0.0
        if b - a > 8192 and a - (b - a) >= 0:
            def bands(y):            # Welch PSD (4096-pt Hann, 50% overlap) summed into 1/3-octave bands 20 Hz-20 kHz
                n = 4096
                segs = np.stack([y[i:i + n] for i in range(0, len(y) - n + 1, n // 2)])
                ps = (np.abs(np.fft.rfft(segs * np.hanning(n), axis=1)) ** 2).mean(0)
                f = np.fft.rfftfreq(n, 1 / SR)
                cs = [1000 * 2 ** (k / 3) for k in range(-17, 14)]
                return np.array(cs), np.array([ps[(f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))].sum() for c in cs])
            cs, Bw = bands(x[a:b])
            _, Bp = bands(x[a - (b - a):a])
            inc = np.clip(Bw - Bp, 0, None)
            lfshare = float(inc[cs < 300].sum() / max(inc.sum(), 1e-20))
        onset_ok = onset is not None and abs(onset - t1) <= 3 / FPS + 0.026
        ok = (onset_ok and rise >= 10 and 0.15 <= lag <= 10 and 540 <= tff <= 671 and lfshare >= 0.7
              and peak1 - peakf >= 6 and rng1 >= 10 and rngf >= 10)
        return P(ok, dict(lf_onset_s=None if onset is None else round(onset, 3), thunder_1_s=round(t1, 3), lf_rise_dB=round(rise, 1),
                          lag_s=round(lag, 2), far_lf_share_of_increase=round(lfshare, 2), peak1_minus_far_dB=round(peak1 - peakf, 1),
                          env_range_1=round(rng1, 1), env_range_far=round(rngf, 1)))
    item('M10', m10)

    # ---------- G11 measured part (fail-only; picture remainder -> judge) ----------
    def g11():
        a, b = stem('storm'), stem('foley')
        if a is None or b is None:
            return F('storm/foley stem missing')
        n = min(len(a), len(b))
        tot = a[:n] + b[:n]

        def r(t0, t1):
            y = tot[int(t0 * SR):int(t1 * SR)]
            return 10 * math.log10(float((y ** 2).mean()) + 1e-20) if y.size else -200
        d = r(6, 23) - r(23.5, 28)
        if d < 4:
            return F(f'S5 storm+foley RMS only {d:.1f} dB below S2-S4 (<4 dB)')
        STATE['g11_drop_db'] = round(d, 1)
        return None
    item('G11', g11)

    # ---------- picture ----------
    PIC = {}

    def base_frames():
        if 'fr' not in PIC:
            if not bmp.exists():
                raise _DumpFail('base/output.mp4 missing')
            fr = gray_frames(bmp)
            if len(fr) < NFR:
                raise _DumpFail(f'base/output.mp4: only {len(fr)} decoded frames')
            PIC['fr'] = fr
        return PIC['fr']

    def rev_frames():
        if 'rf' not in PIC:
            if not rmp.exists():
                raise _DumpFail('revision/output.mp4 missing')
            rf = gray_frames(rmp)
            if len(rf) < NFR:
                raise _DumpFail(f'revision/output.mp4: only {len(rf)} decoded frames')
            PIC['rf'] = rf
        return PIC['rf']

    def cut_profile(fr):
        d = np.abs(np.diff(fr, axis=0)).mean((1, 2))      # d[i] = |f[i+1]-f[i]|
        return d, float(np.median(d)) + 1e-3

    def m01_pic():
        fr = base_frames()
        d, med = cut_profile(fr)
        prob, det = [], []
        found = {}
        for nm, c in (('T12', 144), ('T34', 408)):
            i = int(np.argmax(d[c - 3:c + 1])) + c - 3          # transition into frame i+1 (c-2..c+1)
            if d[i] < max(6 * med, 4.0):
                prob.append(f'no hard cut near frame {c} (max diff {d[i]:.1f}, median {med:.2f})'); continue
            found[nm] = i + 1
            nb = [d[j] for j in (i - 2, i - 1, i + 1, i + 2) if 0 <= j < len(d)]
            if not all(x < 0.35 * d[i] for x in nb):
                prob.append(f'{nm} at {i + 1} is not a clean hard cut (neighbouring diffs {np.round(nb, 1).tolist()} vs {d[i]:.1f})')
        STATE['cuts'] = found
        # other hard cuts (outside the edit points, the flash window 250-285 and the dissolve 534-570)
        thr = max(12.0, 6 * med)
        others = []
        for i in range(len(d)):
            f1 = i + 1
            if abs(f1 - 144) <= 3 or abs(f1 - 408) <= 3 or 250 <= f1 <= 285 or 534 <= f1 <= 570:
                continue
            if d[i] > thr and d[i] >= 3 * max(d[i - 1] if i > 0 else 0, d[i + 1] if i + 1 < len(d) else 0):
                others.append(f1)
        if others:
            prob.append(f'extra cuts at frames {others[:6]}')
        bl, info = blend_frames(fr, 538, 566, range(539, 566))
        STATE['base_blend'] = bl
        if len(bl) < 16:
            prob.append(f'T45: only {len(bl)} blend frames in 539-565 (need >=16)')
        det.append(f'T45 blend frames {len(bl)} ({bl[0] if bl else None}-{bl[-1] if bl else None})')
        fz = freeze_runs(bmp, 6)
        if fz:
            prob.append(f'freeze (>=6 consecutive frames within PSNR 60 dB of each other) at (start, length) {fz[:4]}')
        return prob, det + [f'hard cuts {found}']

    # ---------- Blender ----------
    SD, MD = {}, {}

    def static_dump():
        if 'd' in SD:
            return SD['d']
        if not blend.exists():
            SD['d'] = {'ok': False, 'opened': False, 'error': 'project/scene.blend missing'}
        elif not B.blender_ok():
            raise RuntimeError('blender not on PATH in the verifier image (grader problem)')
        else:
            SD['d'] = B.rich_dump(blend, {'film_frames': [0]}, tmp, timeout=600, tag='x03static')
        if not SD['d'].get('ok') and SD['d'].get('opened') is False:
            STATE['blend_open_fail'] = True
        return SD['d']

    def main_dump():
        if 'd' in MD:
            return MD['d']
        s = static_dump()
        if not s.get('ok'):
            MD['d'] = s
            return s
        cur_fr, fing_fr = set(), set(range(408, 552, 2))
        if 'curtain_grab' in ev:
            g = int(min(NFR - 1, max(0, ev['curtain_grab'])))
            cur_fr |= set(range(max(0, g - 2), min(NFR, g + 3)))
        if 'window_shut' in ev:
            w = int(min(NFR - 1, max(0, ev['window_shut'])))
            fing_fr |= set(range(max(0, w - 2), min(NFR, w + 3)))
        cfg = {'film_frames': list(range(NFR)), 'track': TRACK, 'rigs': ['MARA_RIG'], 'cams': CAMS,
               'samples': {'WINDOW_SASH': 800},
               'bbox_world': {'MARA': [0, 72, 143, 264, 336, 407, 480, 540, 600, 671]},
               'extra': EXTRA, 'x03': {'cur_frames': sorted(cur_fr), 'finger_frames': sorted(fing_fr)}}
        d = B.rich_dump(blend, cfg, tmp, timeout=DUMP_TIMEOUT, tag='x03main')
        if d.get('ok'):
            X = d.get('x03')
            if not isinstance(X, dict):
                d = {'ok': False, 'opened': True, 'error': 'x03 extra hook produced no data: ' + str(d.get('warnings'))[-300:]}
            else:
                for k in ('lamp_c', 'lamp_box', 'cord_top', 'lights', 'cur_speed', 'rod_dist', 'cur_pen', 'cur_pts', 'finger_pen'):
                    X[k] = {int(f): v for f, v in (X.get(k) or {}).items()}
        STATE['dump_seconds'] = d.get('wall_seconds')
        STATE['dump_warnings'] = (d.get('warnings') or [])[:6]
        MD['d'] = d
        return d

    def need_dump():
        d = main_dump()
        if not d.get('ok'):
            raise _DumpFail('Blender per-frame inspection of project/scene.blend failed: ' + str(d.get('error'))[-300:])
        return d

    def has(d, *names):
        miss = [n for n in names if n not in d['objects']]
        if miss:
            raise _DumpFail(f'required objects missing: {miss}')

    def mw(d, n, f):
        return B.M(d, n, f)

    def b07():
        d = static_dump()
        if not d.get('ok'):
            if d.get('opened') is False:
                return F('scene.blend missing or failed to open headless: ' + str(d.get('error'))[-400:])
            return F('Blender static inspection failed (not a file-open error): ' + str(d.get('error'))[-400:])
        objs = d['objects']
        miss = [n for n in REQ_OBJ if n not in objs]
        wrong = [f'{n}:{objs[n]}' for n, t in REQ_OBJ.items() if n in objs and t and objs[n] != t]
        prop = 'dissolve_frames' in d.get('scene_props', {})
        return P(not miss and not wrong and prop, dict(version=d.get('version'), frame_start=d['frame_range'][0], missing=miss,
                                                       wrong_type=wrong, dissolve_frames=d.get('scene_props', {}).get('dissolve_frames')))
    item('B07', b07)

    # ---------- B08 ----------
    def b08():
        prob = []
        cr = [p for p in out.rglob('credits.md')]
        qa = [p for p in out.rglob('qa.md')]
        if not cr: prob.append('credits.md missing')
        if not qa: prob.append('qa.md missing')
        elif not qa[0].read_text(encoding='utf-8', errors='ignore').strip(): prob.append('qa.md empty')
        if cr:
            t = cr[0].read_text(encoding='utf-8', errors='ignore')
            if not re.search(r'espeak|festival|flite|piper|mimic|coqui|\btts\b|text[- ]to[- ]speech|synthes|record|microphone|'
                             r'voice[- ]?(actor|talent|over)|voiced|spoken by|sox|formant|vocoder|speech', t, re.I):
                prob.append('credits.md does not say how the spoken line was produced')
        pat = re.compile(r'(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|api[_-]?key\s*[:=]\s*["\']?[A-Za-z0-9_\-]{12,}|bearer\s+[A-Za-z0-9._-]{20,}|'
                         r'api\.elevenlabs\.io|play\.ht/api|\.tts\.speech\.microsoft\.com|polly\.[a-z0-9-]+\.amazonaws\.com|'
                         r'texttospeech\.googleapis|openai\.com/v1/audio|https?://\S+\.(?:wav|mp3|flac|ogg|png|jpe?g|exr|hdr|tif+|mp4|mov|blend|fbx|obj|glb|gltf|abc|usd[a-z]?)\b)', re.I)
        hits = []
        for f in out.rglob('*'):
            if f.is_file() and f.suffix.lower() in {'.md', '.txt', '.json', '.csv', '.py', '.sh', '.toml', '.yaml', '.yml'} and f.stat().st_size < 2_000_000:
                m = pat.search(f.read_text(encoding='utf-8', errors='ignore'))
                if m:
                    hits.append(f'{f.relative_to(out)}: {m.group(0)[:50]}')
        if hits:
            prob.append(f'credential / online-service / URL-media traces: {hits[:5]}')
        note = ''
        if blend.exists():
            d = main_dump()
            if d.get('ok'):
                urls = [e for e in d['x03'].get('ext_files', []) if '://' in str(e[1])]
                if urls:
                    prob.append(f'scene.blend references media by URL: {urls[:3]}')
            else:
                note = ' (scene.blend media paths not inspected: Blender inspection failed)'
        return P(not prob, ('; '.join(prob) if prob else 'credits/qa present; line production stated; no traces') + note)
    item('B08', b08)

    # ---------- geometry helpers ----------
    def offset(d=None):
        s = static_dump()
        return int(s['frame_range'][0]) if s.get('ok') else 0

    def sash_frame0(d):
        bl = np.array(d['bbox_local'].get('WINDOW_SASH') or [[0, 0, 0]], float)
        c = B.xf(mw(d, 'WINDOW_SASH', 0), bl).mean(0)
        return c

    def inward(d):
        """unit horizontal vector from the closed sash (frame 0) toward the room (DESK, else MARA)."""
        c = sash_frame0(d)
        ref = 'DESK' if 'DESK' in d['objects'] else 'MARA'
        t = mw(d, ref, 0)[:3, 3]
        v = t - c
        v[2] = 0
        n = np.linalg.norm(v)
        if n < 1e-6:
            raise _DumpFail('cannot orient the window plane (DESK at the window position)')
        return c, v / n

    def eye_z(d, f):
        bones = d['bones'].get('MARA_RIG', {}).get(f, {})
        hb = [b for b in bones if re.search(r'head', b, re.I) and not re.search(r'fore|tip|end|top', b, re.I)]
        if hb:
            h = np.array(bones[sorted(hb, key=len)[0]], float)
            return 0.5 * (h[2] + h[5])
        bw = d['bbox_world'].get('MARA', {})
        if bw:
            k = min(bw, key=lambda x: abs(x - f))
            return float(np.array(bw[k], float)[:, 2].max()) - 0.1
        raise _DumpFail('MARA eye height not measurable (no head bone, no MARA mesh)')

    def subject(d, f):
        bones = d['bones'].get('MARA_RIG', {}).get(f, {})
        hb = [b for b in bones if re.search(r'head', b, re.I) and not re.search(r'fore|tip|end|top', b, re.I)]
        if hb:
            h = np.array(bones[sorted(hb, key=len)[0]], float)
            return 0.5 * (h[:3] + h[3:])
        bw = d['bbox_world'].get('MARA', {})
        if bw:
            k = min(bw, key=lambda x: abs(x - f))
            return np.array(bw[k], float).mean(0)
        return mw(d, 'MARA', f)[:3, 3]

    # ---------- M01 ----------
    def m01():
        prob, det = m01_pic()
        d = static_dump()
        if d.get('ok'):
            mk = sorted([m for m in d.get('markers', []) if m[2]], key=lambda m: m[1])
            if mk:
                fs = int(d['frame_range'][0])
                want = {72: 'CAM_S1', 200: 'CAM_S2', 330: 'CAM_S3', 480: 'CAM_S4', 620: 'CAM_S5'}
                got = {}
                for f in want:
                    act = [m for m in mk if m[1] <= fs + f]
                    got[f] = act[-1][2] if act else None
                bad = {f: g for f, g in got.items() if g != want[f]}
                if bad:
                    prob.append(f'camera-bound markers do not select CAM_S1..S5 in shot order: {bad}')
                det.append('camera markers ok' if not bad else '')
            else:
                det.append('no camera-bound markers (per-shot camera checked by the G10 re-render)')
        return P(not prob, '; '.join(prob + det))
    item('M01', m01)

    # ---------- M11 ----------
    def m11():
        fr, rf = base_frames(), rev_frames()
        prob, det = [], []
        if len(rf) != len(fr):
            return F(f'revision frame count {len(rf)} != base {len(fr)}')
        bad = [i for i in list(range(0, 526)) + list(range(579, len(fr))) if psnr(fr[i], rf[i]) < 35]
        if bad:
            prob.append(f'{len(bad)} frames outside 526-578 differ from base (PSNR<35), first {bad[:5]}')
        bl, info = blend_frames(rf, 526, 577, range(527, 577))
        mid = [(i, sb) for i, r2, sb in info if r2 >= 0.7 and 0.1 <= sb <= 0.9]
        cen = None
        if len(mid) >= 4:                      # frame where a linear fit of the mix share crosses 0.5
            k_, c_ = np.polyfit([i for i, _ in mid], [sb for _, sb in mid], 1)
            cen = float((0.5 - c_) / k_) if k_ > 1e-6 else None
        det.append(f'revision blend frames {len(bl)} centre {None if cen is None else round(cen, 1)}')
        if len(bl) < 40 or cen is None or abs(cen - 552) > 2:  # nominal centre of 528-575 is 551.5
            prob.append(f'revision dissolve: {len(bl)} blend frames (need >=40), centre {cen} (need 552±2)')
        full = frames_at(rmp, range(528, 576), W, H)
        mv = [psnr(full[i], full[i + 1]) < 50 for i in range(528, 575)]
        share = float(np.mean(mv))
        det.append(f'moving pairs in 528-575 {share:.0%}')
        if share < 0.8:
            prob.append(f'dissolve handles frozen: only {share:.0%} of consecutive pairs in 528-575 have PSNR<50 dB')
        a, b = decode_audio(bmp), decode_audio(rmp)
        n = min(len(a), len(b))
        res = 10 * math.log10(float(((a[:n] - b[:n]) ** 2).mean()) / max(float((a[:n] ** 2).mean()), 1e-20) + 1e-20)
        det.append(f'audio null {res:.1f} dB')
        if res > -50:
            c = band_compare(a, b)
            if c is None or c['median'] > 0.25:
                prob.append(f'revision audio differs from base (null {res:.1f} dB, band {c})')
        d = static_dump()
        if not d.get('ok'):
            prob.append('scene.blend not inspectable: ' + str(d.get('error'))[-150:])
        else:
            dfv = d['scene_props'].get('dissolve_frames')
            try:
                dfi = int(float(dfv))
            except Exception:
                dfi = None
            if dfi not in (24, 48):
                prob.append(f'scene["dissolve_frames"] = {dfv!r} (need 24 or 48)')
            md = main_dump()
            if md.get('ok') and dfi:
                tr = [s for s in md['x03'].get('strips', []) if s[1] in ('CROSS', 'GAMMA_CROSS', 'WIPE')]
                wrong = [s for s in tr if abs((s[4] - s[3]) - dfi) > 1]
                if wrong:
                    prob.append(f'sequencer transition length differs from dissolve_frames={dfi}: {wrong[:2]}')
                det.append(f'sequencer transitions {[(s[0], s[4] - s[3]) for s in tr][:3]}')
        return P(not prob, '; '.join(prob + det))
    item('M11', m11)

    # ---------- M12 ----------
    def m12():
        prob = []
        tb, tr = read_json(base / 'timeline.json'), read_json(rev / 'timeline.json')
        if tb is None or tr is None:
            return F('base/ or revision/timeline.json missing or unparseable')
        try:
            base_frames()
            cuts = STATE.get('cuts') or {}
        except _DumpFail:
            cuts = {}
        nb, nr = numbers_in(tb), numbers_in(tr)
        tgt = {'T12': cuts.get('T12', 144), 'T23': STATE.get('t23_cut', 264), 'T34': cuts.get('T34', 408)}
        for nm, nums in (('base', nb), ('revision', nr)):
            miss = [f'{k}@{v}' for k, v in tgt.items() if not has_number(nums, v)]
            if miss:
                prob.append(f'{nm} timeline lacks shot boundaries {miss} (frames or seconds, ±1 frame)')
        for nm, nums, (a, b) in (('base', nb, (540, 563)), ('revision', nr, (528, 575))):
            if not has_number(nums, a) or not (has_number(nums, b) or has_number(nums, b + 1)):
                prob.append(f'{nm} timeline lacks dissolve range {a}-{b} (±1 frame; end inclusive or exclusive)')
        gb, gr = find_gains(tb, STEMS), find_gains(tr, STEMS)
        ref = STATE.get('gains') or (gb[0] if gb else None)
        if ref is None or not gr:
            prob.append('master gains not found in both timelines')
        else:
            ok = any(all(abs(20 * math.log10(max(g[s], 1e-9) / max(ref[s], 1e-9))) <= 0.5 for s in STEMS) for g in gr if all(g[s] > 0 for s in STEMS))
            if not ok:
                prob.append(f'revision master gains differ from the base gains {ref} by >0.5 dB')
        return P(not prob, '; '.join(prob) if prob else f'timeline ranges match the film (cuts {tgt}); revision gains = base gains')

    # ---------- G07 (needs T23 cut, used by M12) ----------
    def g07():
        fr = base_frames()
        prob = []
        lum = fr.mean((1, 2))
        pre = float(lum[234:258].mean())
        mid = float(lum[262:267].mean())
        if mid < 2.5 * pre:
            prob.append(f'flash frames 262-266 mean Y {mid:.1f} < 2.5x pre-flash {pre:.1f}')

        def zn(x):
            x = x - x.mean(); return x / (np.linalg.norm(x) + 1e-9)
        A, Bb = zn(fr[250]), zn(fr[280])
        lab = [int((zn(fr[i]) * Bb).sum() > (zn(fr[i]) * A).sum()) for i in range(250, 281)]
        cut = 250 + lab.index(1) if 1 in lab else None
        STATE['t23_cut'] = cut if cut is not None else 264
        if cut is None or abs(cut - 264) > 1:
            prob.append(f'T23 cut measured at {cut} (need 264±1; first frame closer to S3 frame 280 than to S2 frame 250)')
        full = frames_at(bmp, range(255, 275), W, H)
        cards = [i for i in range(255, 275) if (full[i] >= 250).mean() >= 0.99 and full[i].std() < 2]
        if cards:
            prob.append(f'uniform white card frames {cards[:5]} (>=99% pixels >=250 and Y std <2)')
        d = need_dump(); has(d, 'LIGHTNING')
        e = np.array([d['x03']['lights'].get(f, {}).get('LIGHTNING', [0])[0] for f in range(NFR)], float)
        pk = int(np.argmax(e))
        if np.ptp(e) <= 0:
            prob.append('LIGHTNING energy is not animated')
        elif not 258 <= pk <= 270:
            prob.append(f'LIGHTNING energy peaks at film frame {pk} (need 258-270)')
        return P(not prob, '; '.join(prob) if prob else f'cut at {cut}; flash {mid:.0f}/{pre:.0f} Y; LIGHTNING energy peak at {pk}')
    item('G07', g07)
    item('M12', m12)

    # ---------- M06 cloth ----------
    def m06():
        d = need_dump(); has(d, 'CURTAIN', 'CURTAIN_ROD')
        X = d['x03']
        prob = []
        mods = [m for m in d['modifiers'].get('CURTAIN', []) if m[1] == 'CLOTH']
        if not mods:
            prob.append('CURTAIN has no Cloth modifier')
        cache = next((e.get('cache') for e in d['physics'].get('CURTAIN', []) if e.get('type') == 'CLOTH'), None) or {}
        files = [p for p in proj.rglob('*') if p.is_file() and (p.suffix.lower() == '.bphys' or 'blendcache' in str(p.parent).lower())]
        if not (cache.get('is_baked') or files):
            prob.append('cloth cache neither baked into scene.blend nor shipped as .bphys/blendcache files in project/')
        nv = X.get('cur_verts', 0)
        if nv < 400:
            prob.append(f'CURTAIN has {nv} vertices (<400)')
        rd = {f: v for f, v in X['rod_dist'].items() if v is not None}
        if not rd:
            prob.append('top-edge to CURTAIN_ROD distance not measurable')
        else:
            fmax = max(rd, key=rd.get)
            if rd[fmax] > 0.05:
                prob.append(f'top edge {rd[fmax]*100:.1f} cm from the rod at film frame {fmax} (>5 cm)')
        top = f"pin group {X.get('pin_group')} ({X.get('pin_n')} verts)" if X.get('pin_n') else f"top band {X.get('top_band_n')} verts"
        return P(not prob, '; '.join(prob) if prob else f'cloth cache ok (baked={cache.get("is_baked")}, files={len(files)}), {nv} verts, '
                 f'{top} max {max(rd.values())*100:.1f} cm from rod (every 4th frame)')
    item('M06', m06)

    def m07():
        wb, ws = evreq('window_burst', 'window_shut')
        d = need_dump()
        cs = d['x03']['cur_speed']
        v = np.array([cs.get(f) if cs.get(f) is not None else np.nan for f in range(NFR)], float)
        h = FPS // 2
        if np.all(np.isnan(v)):
            return F('CURTAIN vertex motion not measurable')
        bef, aft = np.nanmean(v[max(1, wb - h):max(2, wb)]), np.nanmean(v[wb:wb + h])
        s3 = np.nanmean(v[264:408])
        last = np.nanmean(v[max(ws, NFR - FPS):NFR])
        ok = aft >= 3 * bef and last <= 0.4 * s3
        return P(bool(ok), dict(before=round(float(bef), 5), after=round(float(aft), 5), s3=round(float(s3), 5), last_1s=round(float(last), 5)))
    item('M07', m07)

    # ---------- M08 sash / latch ----------
    def m08():
        wb, ws, lcf = evreq('window_burst', 'window_shut', 'latch_click')
        d = need_dump(); has(d, 'WINDOW_SASH', 'WINDOW_LATCH')
        R0 = B.rot_of(mw(d, 'WINDOW_SASH', 0))
        ang = np.array([B.rot_angle(R0, B.rot_of(mw(d, 'WINDOW_SASH', f))) for f in range(NFR)])
        mv = np.where(ang > 1.0)[0]
        start = int(mv[0]) if mv.size else None
        prob = []
        if start is None or abs(start - wb) > 3:
            prob.append(f'sash starts moving at {start}, declared window_burst {wb}')
        if ang.max() < 25:
            prob.append(f'max sash angle {ang.max():.1f} < 25')
        if ang[ws:].max() > 3:
            prob.append(f'sash not within 3 deg of its initial angle after window_shut (max {ang[ws:].max():.1f})')
        c0, nin = inward(d)
        imax = int(np.argmax(ang))
        bl = np.array(d['bbox_local'].get('WINDOW_SASH') or [[0, 0, 0]], float)
        cm = B.xf(mw(d, 'WINDOW_SASH', imax), bl).mean(0)
        inn = float((cm - c0) @ nin)
        if inn <= 0.01:
            prob.append(f'sash does not open inward (centre moves {inn*100:.1f} cm toward the room at max opening)')
        L0 = mw(d, 'WINDOW_LATCH', lcf)
        dl = max(float(np.abs(mw(d, 'WINDOW_LATCH', f) - L0).max()) for f in range(lcf, NFR))
        if dl > 1e-3:
            prob.append(f'latch moves after latch_click (max matrix delta {dl:.4f})')
        x = stem('foley')
        if x is None:
            prob.append('foley stem missing')
        else:
            e5 = rms_env(x, int(0.005 * SR))
            t0 = lcf / FPS
            i0, i1 = int((t0 - 2 / FPS) / 0.005), int((t0 + 2 / FPS) / 0.005) + 1
            pre = e5[max(0, i0 - 40):max(1, i0)]
            pk = float(e5[max(0, i0):i1].max()) if i1 > max(0, i0) else -240
            if not pre.size or pk - float(np.median(pre)) < 10:
                prob.append(f'no foley transient >=10 dB at latch_click (peak-median {pk - (float(np.median(pre)) if pre.size else 0):.1f})')
        return P(not prob, prob or dict(max_angle=round(float(ang.max()), 1), start=start, inward_cm=round(inn * 100, 1)))
    item('M08', m08)

    # ---------- M04 lip sync ----------
    def m04():
        d = need_dump(); has(d, 'MARA_RIG')
        if 'on' not in DLG:
            return F('dialogue line not measurable (see M02)')
        x = stem('dialogue')
        hop = SR // FPS
        nf = len(x) // hop
        env = np.sqrt((x[:nf * hop].reshape(nf, hop) ** 2).mean(1))
        a = max(0, int(DLG['on'] * FPS) - 6)
        b = min(NFR - 1, nf - 1, int(math.ceil(DLG['off'] * FPS)) + 6)
        chans = {}
        for f in range(a, b + 1):
            for bn, (ag, lc) in d['chan'].get('MARA_RIG', {}).get(f, {}).items():
                chans.setdefault('bone:' + bn + ':rot', []).append(ag)
                chans.setdefault('bone:' + bn + ':loc', []).append(lc)
        for o, per in d['sk'].items():
            for f in range(a, b + 1):
                for k, v in per.get(f, {}).items():
                    chans.setdefault('sk:' + o + ':' + k, []).append(v)
        e = env[a:b + 1]
        best = (-2.0, None, None)
        for nm, s in chans.items():
            s = np.array(s, float)
            if len(s) != len(e) or np.ptp(s) < 1e-6:
                continue
            for lag in range(-2, 3):          # +-2 frames = +-83 ms
                u, v = (s[lag:], e[:len(e) - lag]) if lag >= 0 else (s[:lag], e[-lag:])
                if np.std(u) < 1e-9 or np.std(v) < 1e-12:
                    continue
                r = float(np.corrcoef(u, v)[0, 1])
                if r > best[0]:
                    best = (r, nm, lag)
        return P(best[0] >= 0.4, f'frames {a}-{b}: best r={best[0]:.2f} channel={best[1]} lag={best[2]} frames ({len(chans)} mouth channels sampled)')
    item('M04', m04)

    # ---------- M05 camera grammar ----------
    def m05():
        d = need_dump(); has(d, *CAMS)
        prob, det = [], []

        def series(cam, a, b):
            fs = list(range(a, b + 1))
            ms = [mw(d, cam, f) for f in fs]
            pos = np.array([m[:3, 3] for m in ms])
            pit = np.array([B.cam_pitch(m) for m in ms])
            ci = [d['cams'][cam][f] for f in fs]
            eq = np.array([c['lens'] * (24.0 / c['sh'] if c.get('fit') == 'VERTICAL' else 36.0 / c['sw']) for c in ci])
            return fs, ms, pos, pit, ci, eq

        def dolly(fs, ms, pos):
            fw = B.cam_forward(ms[0])
            along = float((pos[-1] - pos[0]) @ fw)
            ds = float(np.linalg.norm(pos[0] - subject(d, fs[0])) - np.linalg.norm(pos[-1] - subject(d, fs[-1])))
            return along, ds
        k = 15
        ker = np.ones(k) / k
        smooth = lambda a_: np.stack([np.convolve(np.pad(a_[:, i], (k // 2, k // 2), mode='edge'), ker, 'valid') for i in range(a_.shape[1])], 1)
        # S1
        fs, ms, pos, pit, ci, eq = series('CAM_S1', 0, 143)
        dz = np.array([pos[i, 2] - eye_z(d, f) for i, f in enumerate(fs)])
        al, ds = dolly(fs, ms, pos)
        ok = np.abs(dz).max() <= 0.4 and np.abs(pit).max() <= 10 and max(al, ds) >= 0.05 and np.ptp(eq) < 0.01 and 35 <= eq.mean() <= 60
        if not ok: prob.append('S1')
        det.append(f'S1 cam-eye {dz.min():+.2f}..{dz.max():+.2f} m pitch {pit.min():.1f}..{pit.max():.1f} dolly-in {max(al, ds)*100:.1f} cm eq {eq.min():.1f}-{eq.max():.1f} mm')
        # S2
        fs, ms, pos, pit, ci, eq = series('CAM_S2', 144, 263)
        jr = pos - smooth(pos)
        jit = float(np.linalg.norm(jr, axis=1).max())
        fw = np.array([B.cam_forward(m) for m in ms]); fsm = smooth(fw)
        rj = float(np.degrees(np.arccos(np.clip((fw * fsm).sum(1) / np.linalg.norm(fsm, axis=1), -1, 1))).max())
        sig = jr if jit >= 0.002 else (fw - fsm)          # the jitter channel that carries the shake
        sig = sig - sig.mean(0)
        S = (np.abs(np.fft.rfft(sig * np.hanning(len(sig))[:, None], axis=0)) ** 2).sum(1)
        S[0] = 0
        top3 = max(float(S[max(0, i - 1):i + 2].sum()) for i in range(len(S))) / max(float(S.sum()), 1e-20)
        okj = (0.002 <= jit <= 0.06) or (rj >= 0.15 and jit <= 0.06)
        if not (okj and top3 < 0.8): prob.append('S2')
        det.append(f'S2 jitter {jit*1000:.1f} mm / {rj:.2f} deg, strongest-3-bin share {top3:.2f}')
        # S3
        fs, ms, pos, pit, ci, eq = series('CAM_S3', 264, 407)
        dz = np.array([pos[i, 2] - eye_z(d, f) for i, f in enumerate(fs)])
        disp = float(np.linalg.norm(pos - pos[0], axis=1).max())
        ok = np.median(dz) < 0 and pit.min() >= 5 and eq.max() <= 32 and disp < 0.01
        if not ok: prob.append('S3')
        det.append(f'S3 cam-eye median {np.median(dz):+.2f} m pitch min {pit.min():.1f} eq max {eq.max():.1f} mm disp {disp*100:.1f} cm')
        # S4
        fs, ms, pos, pit, ci, eq = series('CAM_S4', 408, 539)
        disp = float(np.linalg.norm(pos - pos[0], axis=1).max())
        dof = all(c['dof'] and c['fstop'] <= 5.6 for c in ci)
        if not (disp < 0.01 and dof): prob.append('S4')
        det.append(f'S4 disp {disp*100:.1f} cm dof on & f<=5.6 {dof}')
        # S5
        fs, ms, pos, pit, ci, eq = series('CAM_S5', 540, 671)
        al, ds = dolly(fs, ms, pos)
        ok = pit.max() <= -10 and min(al, ds) <= -0.15 and np.ptp(eq) < 0.01
        if not ok: prob.append('S5')
        det.append(f'S5 pitch max {pit.max():.1f} pull-back {-min(al, ds)*100:.1f} cm eq range {np.ptp(eq):.3f}')
        return P(not prob, ('failed: ' + ','.join(prob) + ' | ' if prob else '') + '; '.join(det))
    item('M05', m05)

    # ---------- M09 hands ----------
    def keyed_in(d, rig, a, b):
        fs = offset()
        ks = set()
        for e in d['fcurves'].get(rig, []):
            m = re.match(r'pose\.bones\["(.+?)"\]', e['path'])
            if not m or e.get('n', 0) < 2 or e.get('vmax') is None or e['vmax'] - e['vmin'] < 1e-6:
                continue
            fr_ = e.get('frames') or []
            if fr_ and min(fr_) <= fs + b and max(fr_) >= fs + a:
                ks.add(m.group(1))
        return ks

    def m09():
        cg, ws = evreq('curtain_grab', 'window_shut')
        d = need_dump(); has(d, 'MARA_RIG', 'CURTAIN', 'WINDOW_SASH', 'CAM_S4')
        X = d['x03']
        prob, det = [], []
        handnames = [b for b in d['sampled_bones'].get('MARA_RIG', []) if HANDISH.search(b)]
        if not handnames:
            return F('MARA_RIG has no hand/finger bones')

        def mind(f, pts):
            ks, segs = B.bone_segs(d, 'MARA_RIG', f, set(handnames))
            if not len(segs) or pts is None or not len(pts):
                return np.inf
            return float(B.seg_point_dist(segs, pts).min())
        dc = min([mind(f, np.array(X['cur_pts'][f], float)) for f in range(cg - 2, cg + 3) if f in X['cur_pts']] or [np.inf])
        sl = np.array(d['samples'].get('WINDOW_SASH') or [], float)
        dsash = min([mind(f, B.xf(mw(d, 'WINDOW_SASH', f), sl)) for f in range(max(0, ws - 2), min(NFR, ws + 3))] or [np.inf])
        if dc > 0.05: prob.append(f'no hand/finger bone within 5 cm of CURTAIN at curtain_grab±2 (min {dc*100:.1f} cm)')
        if dsash > 0.05: prob.append(f'no hand/finger bone within 5 cm of WINDOW_SASH at window_shut±2 (min {dsash*100:.1f} cm)')
        det.append(f'curtain {dc*100:.1f} cm, sash {dsash*100:.1f} cm')
        arm = d['armatures'].get('MARA_RIG', {})
        bones = arm.get('bones', {})
        keyed = keyed_in(d, 'MARA_RIG', 408, 551)
        groups = B.finger_groups(bones)
        vis, chains = {}, {}
        for side in ('L', 'R'):
            hb = [b for b in bones if re.search(r'hand|palm|wrist', b, re.I) and B.side_of(b) == side]
            fb = [b for k_, v in groups[side].items() for b in v]
            pts_b = [b for b in hb + fb if b in d['bones'].get('MARA_RIG', {}).get(408, {})]
            if not pts_b:
                continue
            seen = False
            for f in range(408, 552, 8):
                row = d['bones']['MARA_RIG'][f]
                P_ = np.array([row[b][:3] for b in pts_b], float)
                uvz = B.project(d, 'CAM_S4', f, P_)
                if ((uvz[:, 2] > 0) & (uvz[:, 0] >= 0) & (uvz[:, 0] <= 1) & (uvz[:, 1] >= 0) & (uvz[:, 1] <= 1)).any():
                    seen = True; break
            vis[side] = seen
            n_name = sum(1 for v in groups[side].values() if sum(1 for b in v if b in keyed) >= 3)
            topo = 0
            for h in hb:
                for path in B.chains_under(bones, h):
                    if sum(1 for b in path if b in keyed) >= 3:
                        topo += 1
            chains[side] = max(n_name, topo)
        visible = [s for s, v in vis.items() if v]
        if not visible:
            prob.append(f'no MARA hand visible in CAM_S4 during S4 (hand sides found: {list(vis)})')
        for s in visible:
            if chains.get(s, 0) < 4:
                prob.append(f'visible hand {s}: {chains.get(s, 0)} finger chains (>=3 bones) keyed in S4 (need >=4)')
        det.append(f'visible hands {visible}, keyed chains {chains}')
        fp = [v for f, v in X['finger_pen'].items()]
        worst = max(fp, key=lambda v: v[0]) if fp else [0.0, None]
        if worst[0] > 0.02:
            prob.append(f'finger {worst[1]} penetrates WINDOW_SASH by {worst[0]*100:.1f} cm (>2 cm)')
        det.append(f'max finger penetration {worst[0]*100:.1f} cm')
        return P(not prob, '; '.join(prob + det))
    item('M09', m09)

    # ---------- G01 measured part ----------
    def g01():
        prob = []
        if not bmp.exists():
            return F('base/output.mp4 missing')
        allf = sorted(f for v in SHOT_FR.values() for f in v)
        full = frames_at(bmp, allf, W, H)
        idx = {s: round(float(np.median([flat_block_index(full[f]) for f in fs])), 3) for s, fs in SHOT_FR.items()}
        STATE['flat_index'] = idx
        bad = {s: v for s, v in idx.items() if v > 0.35}
        if len(bad) >= 3:
            prob.append(f'flat-block index > 0.35 in {len(bad)} of 5 shots {bad}')
        d = main_dump()
        if d.get('ok'):
            hero = ['MARA', 'CURTAIN', 'DESK', 'PENDANT_LAMP', 'WINDOW_SASH']
            nob = [h for h in hero if h in d['objects'] and d['objects'][h] == 'MESH' and not any(
                any(t.startswith('BSDF') or t == 'GROUP' for t in m.get('node_types', [])) for m in d['materials'].get(h, []))]
            if nob: prob.append(f'objects without a node-based BSDF material: {nob}')
            var = [n for n, ms in d['materials'].items() if any(m.get('n_tex', 0) > 0 or m.get('principled_linked') for m in ms)]
            if len(var) < 3: prob.append(f'surface variation (texture or linked BSDF input) on only {var} (need >=3 objects)')
            if d.get('engine') == 'CYCLES' and d['render'].get('oidn_available', True) and not (d['render'].get('cycles_denoise') or d['render'].get('compositor_denoise')):
                prob.append('Cycles render without denoising')
        else:
            if not prob:
                STATE['g01_no_gate'] = True
            prob.append('Blender inspection failed: ' + str(d.get('error'))[-200:])
        if prob:
            if not STATE.get('g01_no_gate'):
                STATE['g01_measured_fail'] = True
            return F('; '.join(prob))
        return None     # measured part passes -> the judge decides the look from the contact sheets
    item('G01', g01)

    # ---------- G02 lights ----------
    def g02():
        d = need_dump()
        c0, nin = inward(d)
        Ls = d['x03']['lights']
        prob, extra = [], {}
        for f in range(0, NFR, 2):
            for n, (en, hid, x, y, z) in Ls.get(f, {}).items():
                if n in ('LAMP_LIGHT', 'LIGHTNING'):
                    continue
                s = float((np.array([x, y, z]) - c0) @ nin)
                if en > 0 and not hid and s > -0.05:
                    extra.setdefault(n, f)
        if extra:
            prob.append(f'extra interior lights renderable with energy > 0 (first film frame): {extra}')
        lam = [Ls.get(f, {}).get('LAMP_LIGHT') for f in range(NFR)]
        lam = [v for v in lam if v]
        if lam:
            e = np.array([v[0] for v in lam]); hid = [v[1] for v in lam]
            if any(hid) or e.min() < 0.25 * max(e.max(), 1e-9):
                prob.append(f'LAMP_LIGHT switched off/hidden in part of the film (energy {e.min():.1f}..{e.max():.1f}, hidden frames {sum(hid)})')
        else:
            prob.append('LAMP_LIGHT missing')
        for n, lst in d['fcurves'].items():
            o = n.split('|')[0]
            if d['objects'].get(o) == 'LIGHT' and o not in ('LIGHTNING', 'LAMP_LIGHT') and any(e['path'] in ('hide_render', 'hide_viewport', 'energy') for e in lst):
                s = float((mw(d, o, 0)[:3, 3] - c0) @ nin) if o in d['mats'][0] else 0.0
                if s > -0.05:
                    prob.append(f'{o}: animated visibility/energy (per-shot light)')
        return P(not prob, '; '.join(prob) if prob else f'only LAMP_LIGHT/LIGHTNING light the interior; lights: {sorted(d["lights"])}')
    item('G02', g02)

    # ---------- G03 / G05 lamp ----------
    def lamp_series(d):
        X = d['x03']
        if not X['lamp_c'] or not X['cord_top']:
            raise _DumpFail('PENDANT_LAMP / LAMP_CORD positions not measurable (LAMP_CORD must be a mesh or curve)')
        lc = np.array([X['lamp_c'][f] for f in range(NFR)], float)
        ct = np.array([X['cord_top'][f] for f in range(NFR)], float)
        return lc, ct

    def g03():
        s0, = evreq('lamp_swing_start')
        d = need_dump(); has(d, 'PENDANT_LAMP', 'LAMP_LIGHT', 'LAMP_CORD')
        lc, ct = lamp_series(d)
        li = np.array([mw(d, 'LAMP_LIGHT', f)[:3, 3] for f in range(NFR)])
        lb = d['x03']['lamp_box']
        dist = np.linalg.norm(lc - li, axis=1)
        inside = np.array([bool(lb.get(f)) and all(lb[f][0][k] - 0.02 <= li[f][k] <= lb[f][1][k] + 0.02 for k in range(3)) for f in range(NFR)])
        ride_ok = bool(np.all((dist <= 0.05) | inside))
        v = lc - ct
        v = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
        s0 = max(1, s0)
        rest = np.median(v[:s0], axis=0); rest /= max(np.linalg.norm(rest), 1e-9)
        ang = np.degrees(np.arccos(np.clip(v @ rest, -1, 1)))
        before = float(ang[:s0].max())
        after = float(ang[s0:].max()) if s0 < NFR else 0.0
        drift = float(np.linalg.norm(ct - ct[0], axis=1).max())
        STATE['lamp'] = dict(lc=lc, ct=ct, li=li)
        return P(ride_ok and before < 2 and after >= 8 and drift <= 0.02,
                 dict(light_to_lamp_max_m=round(float(dist.max()), 3), light_inside_lamp_bbox_all=bool(inside.all()),
                      swing_before_deg=round(before, 2), swing_after_peak_deg=round(after, 2), pivot_drift_m=round(drift, 4)))
    item('G03', g03)

    def g05():
        s0, ws = evreq('lamp_swing_start', 'window_shut')
        d = need_dump(); has(d, 'PENDANT_LAMP', 'LAMP_CORD', 'LAMP_LIGHT')
        lc, ct = lamp_series(d)
        li = np.array([mw(d, 'LAMP_LIGHT', f)[:3, 3] for f in range(NFR)])
        s0 = max(1, s0)
        hv = (lc - ct)[:, :2]
        hv = hv - hv[:s0].mean(0)
        seg = hv[s0:] - hv[s0:].mean(0)
        if np.abs(seg).max() < 1e-4:
            return F('the lamp does not swing')
        u = np.linalg.svd(seg, full_matrices=False)[2][0]
        s = hv @ u

        def upz(x):
            return np.where((x[:-1] < 0) & (x[1:] >= 0))[0]

        def per(x):
            z = upz(x)
            return (float(np.median(np.diff(z))) / FPS, len(z)) if len(z) >= 3 else (None, len(z))
        T, nz = per(s[ws:])
        src = 'after window_shut'
        if T is None:
            T, nz = per(s[264:]); src = 'S3-S5'
        Ls = [float(np.median(np.linalg.norm(lc - ct, axis=1))), float(np.median(np.linalg.norm(li - ct, axis=1)))]
        T0s = [2 * math.pi * math.sqrt(max(L_, 1e-6) / 9.81) for L_ in Ls]
        ratios = [T / t0 for t0 in T0s] if T else []
        okT = any(0.67 <= r <= 1.5 for r in ratios)
        a = s[ws:]
        zc = np.where(np.sign(a[:-1]) != np.sign(a[1:]))[0]
        bounds = [0] + list(zc + 1) + [len(a)]
        hc = [(float(np.sign(a[b0])), float(np.abs(a[b0:b1]).max())) for b0, b1 in zip(bounds[:-1], bounds[1:]) if b1 > b0]
        hc = hc[1:-1] if len(hc) > 2 else hc           # drop partial half-cycles at the ends
        pk = [p for _, p in hc]
        mono = True                                    # compared per side, so a constant centre offset does not matter
        for side in (1.0, -1.0):
            q = [p for sg, p in hc if sg == side]
            mono &= all(b <= a_ * 1.05 + 1e-4 for a_, b in zip(q, q[1:]))
        end_amp = float(np.abs(s[-24:]).max())
        s3_amp = float(np.abs(s[264:408]).max())
        ok = okT and mono and end_amp < s3_amp
        return P(ok, dict(period_s=None if T is None else round(T, 3), period_from=src, upward_crossings=nz,
                          T0_s=[round(t, 3) for t in T0s], ratio=[round(r, 2) for r in ratios], amp_nonincreasing=mono,
                          half_cycle_peaks_m=[round(p, 3) for p in pk[:8]], end_amp_m=round(end_amp, 3), s3_peak_m=round(s3_amp, 3)))
    item('G05', g05)

    # ---------- G04 shadows follow the lamp ----------
    def g04():
        s0, = evreq('lamp_swing_start')
        d = need_dump(); has(d, 'LAMP_LIGHT', 'CAM_S3', 'CAM_S5')
        fr = base_frames()
        hh, ww = fr.shape[1], fr.shape[2]
        xs, ys = np.arange(ww)[None, :], np.arange(hh)[:, None]
        res, prob = {}, []
        for shot, cam, a, b in (('S3', 'CAM_S3', max(280, s0), 407), ('S5', 'CAM_S5', 570, 665)):
            if b - a < 24:
                prob.append(f'{shot}: fewer than 24 swing frames ({a}-{b})'); continue
            fs = list(range(a, b + 1))
            uv = np.array([B.project(d, cam, f, mw(d, 'LAMP_LIGHT', f)[:3, 3][None])[0] for f in fs])
            cx = np.array([(fr[f] * xs).sum() / max(fr[f].sum(), 1e-9) / ww for f in fs])
            cy = np.array([(fr[f] * ys).sum() / max(fr[f].sum(), 1e-9) / hh for f in fs])
            best = None
            for k, cen in ((0, cx), (1, cy)):
                bu = detrend(uv[:, k])
                if np.ptp(bu) < 0.005:
                    continue
                r, lag = corr_lag(bu, detrend(cen))
                if best is None or abs(r) > abs(best[0]):
                    best = (r, lag, 'xy'[k], float(np.ptp(bu)))
            if best is None:
                res[shot] = 'bulb motion < 0.5% of frame'
                if shot == 'S3':
                    prob.append('S3: projected bulb displacement < 0.5% of the frame (swing not visible)')
                continue
            res[shot] = f'|r|={abs(best[0]):.2f} lag {best[1]} axis {best[2]} bulb range {best[3]:.3f}'
            if abs(best[0]) < 0.5:
                prob.append(f'{shot}: |r|={abs(best[0]):.2f} < 0.5')
        return P(not prob, '; '.join(prob) + (' | ' if prob else '') + str(res))
    item('G04', g04)

    # ---------- G06 lightning direction + colour ----------
    def g06():
        fp, = evreq('flash_peak')
        d = need_dump(); has(d, 'LIGHTNING', 'WINDOW_SASH')
        c0, nin = inward(d)
        typ = d['lights'].get('LIGHTNING', {}).get('type')
        prob, det = [], []
        fl = range(max(0, fp - 6), min(NFR, fp + 7))
        if typ == 'SUN':
            angs = []
            for f in fl:
                dirv = B.cam_forward(mw(d, 'LIGHTNING', f))       # light shines along its local -Z
                angs.append(math.degrees(math.acos(max(-1, min(1, float(dirv @ nin))))))
            if max(angs) >= 80:
                prob.append(f'SUN LIGHTNING direction {max(angs):.0f}° from the inward window normal (need <80°)')
            det.append(f'SUN direction {min(angs):.0f}-{max(angs):.0f}° from inward normal')
        else:
            ss = [float((mw(d, 'LIGHTNING', f)[:3, 3] - c0) @ nin) for f in fl]
            if max(ss) > -0.3:
                prob.append(f'LIGHTNING ({typ}) only {-max(ss):.2f} m outside the window plane (need >=0.3 m)')
            det.append(f'{typ} {-max(ss):.2f} m outside the window plane')
        others = [n for n in d['lights'] if n not in ('LIGHTNING', 'LAMP_LIGHT')]
        Ls = d['x03']['lights']
        flashers = [n for n in others if len({round(Ls.get(f, {}).get(n, [0])[0], 3) for f in range(230, 300)}) > 1]
        if flashers:
            prob.append(f'other lights flash with the lightning: {flashers}')
        fr = base_frames()
        lum = fr.mean((1, 2))
        s2f = 255 + int(np.argmax(lum[255:264]))
        s3f = 264 + int(np.argmax(lum[264:276]))
        rgb = frames_at(bmp, {s2f, s3f, 234, 330}, 640, 268, 'rgb24')
        for shot, ff, rf_ in (('S2', s2f, 234), ('S3', s3f, 330)):
            Lf, af, bf, Yf = srgb_lab(rgb[ff]); Lr, ar, br, Yr = srgb_lab(rgb[rf_])
            dY = Yf - Yr
            m_fl = dY >= np.percentile(dY, 90)
            clip = (rgb[rf_] >= 250).all(-1)
            m_lp = (Yr >= np.percentile(Yr[~clip], 80) if (~clip).any() else Yr > 0) & ~clip
            db = float(np.median(br[m_lp]) - np.median(bf[m_fl])) if m_lp.any() and m_fl.any() else -99
            det.append(f'{shot} flash frame {ff} vs {rf_}: b*(lamp-lit) - b*(flash-lit) = {db:.1f}')
            if db < 5:
                prob.append(f'{shot}: flash-lit pixels not cooler than lamp-lit pixels (Δb* {db:.1f} < 5)')
        return P(not prob, '; '.join(prob + det))
    item('G06', g06)

    # ---------- G08 exposure / colour continuity ----------
    def g08():
        if not bmp.exists():
            return F('base/output.mp4 missing')
        shots = ['S1', 'S3', 'S4', 'S5']
        rgb = frames_at(bmp, [f for s in shots for f in SHOT_FR[s]], 640, 268, 'rgb24')
        res, prob = {}, []
        for s in shots:
            bs, ys = [], []
            for f in SHOT_FR[s]:
                L_, a_, b_, Y = srgb_lab(rgb[f])
                clip = (rgb[f] >= 250).all(-1)
                if (~clip).sum() < 100:
                    continue
                m = (Y >= np.percentile(Y[~clip], 80)) & ~clip
                bs.append(float(np.median(b_[m]))); ys.append(float(np.median(Y[m])))
            if not bs:
                prob.append(f'{s}: frames fully clipped'); continue
            res[s] = (round(float(np.median(bs)), 1), float(np.median(ys)))
        cold = {s: v[0] for s, v in res.items() if v[0] < 8}
        if cold:
            prob.append(f'brightest 20% not warm (b* < 8) in {cold}')
        if len(res) >= 2:
            yv = [v[1] for v in res.values()]
            ev_ = math.log2(max(yv) / max(min(yv), 1e-9))
            if ev_ > 1.0:
                prob.append(f'brightest-20% median luminance differs by {ev_:.2f} EV across shots (>1.0)')
        else:
            ev_ = None
        return P(not prob, '; '.join(prob) + (' | ' if prob else '') + str({s: dict(b=v[0], Y=round(v[1], 4)) for s, v in res.items()})
                 + (f' spread {ev_:.2f} EV' if ev_ is not None else ''))
    item('G08', g08)

    # ---------- G09 cloth penetration ----------
    def g09():
        d = need_dump(); has(d, 'CURTAIN', 'WINDOW_SASH')
        X = d['x03']
        cp = X['cur_pen']
        if not cp:
            return F('CURTAIN penetration not measurable (CURTAIN not a mesh)')
        worst = (0.0, None, None)
        for f, pen in cp.items():
            for n, v in pen.items():
                if v > worst[0]:
                    worst = (v, n, f)
        flips = {k: v for k, v in X['flip'].items() if v < 0}
        return P(worst[0] <= 0.02, f'max CURTAIN penetration {worst[0]*100:.1f} cm into {worst[1]} at film frame {worst[2]} '
                 f'(every 4th frame; colliders {X["colliders"]}; meshes whose normals face away from the room: {list(flips)})')
    item('G09', g09)

    # ---------- G10 re-render ----------
    def g10():
        if not blend.exists():
            return F('project/scene.blend missing')
        if not bmp.exists():
            return F('base/output.mp4 missing')
        s = static_dump()
        if not s.get('ok'):
            return F('scene.blend not inspectable: ' + str(s.get('error'))[-200:])
        fs = offset()
        film = frames_at(bmp, [72, 200, 330, 480, 620], RENDER_W, RENDER_H)
        det, ok = [], True
        for f, cam in ((72, 'CAM_S1'), (200, 'CAM_S2'), (330, 'CAM_S3'), (480, 'CAM_S4'), (620, 'CAM_S5')):
            if time.time() - t_start > BUDGET_S:
                return F('; '.join(det + [f'grader time budget exhausted before frame {f}']))
            rr, note = blend_render(blend, fs + f, tmp, cam)
            if rr is None:
                return F('; '.join(det + [f'frame {f} re-render failed ({note})']))
            sv = ncc_render(rr, film[f])
            ok &= sv >= 0.72
            det.append(f'f{f} ncc={sv:.3f}{" " + note if note else ""}')
        return P(ok, '; '.join(det) + f' ({RENDER_W}x{RENDER_H}, {RENDER_SPP} spp re-render vs film)')
    item('G10', g10)

    STATE['seconds'] = round(time.time() - t_start, 1)
    R['_x03_state'] = {'verdict': 'na', 'detail': json.dumps({k: STATE.get(k) for k in ('flat_index', 'dump_seconds', 'dump_warnings', 'seconds', 'cuts', 't23_cut', 'g11_drop_db')}, default=str)[:900]}
    return R


GATES = {'G01': ['G02', 'G03', 'G04', 'G05', 'G06', 'G08'], 'M06': ['M07', 'G09']}


def postprocess(results, ctx):
    for g, deps in GATES.items():
        r = results.get(g, {})
        measured = r.get('source') == 'checks' and r.get('verdict') == 'fail' and (g != 'G01' or STATE.get('g01_measured_fail'))
        if measured:
            for dpd in deps:
                if dpd in results and results[dpd].get('verdict') not in ('na', 'fail'):
                    results[dpd] = dict(results[dpd], verdict='fail', gated=True,
                                        detail=f'group gate: {g} failed (measured); ' + str(results[dpd].get('detail', results[dpd].get('reason', '')))[:300])
    return results
