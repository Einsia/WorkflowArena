# -*- coding: utf-8 -*-
"""CDC-A-X07 deterministic checks (all 12 rubric items).

TR (trace): every output frame is compared (gray, longest side 360 px, SSIM 11x11 gaussian sigma=1.5)
with candidate frames. Coarse retrieval uses 64x36 thumbnails to propose (clip, offset) pairs per window;
each proposal is then verified frame-by-frame with full SSIM. A candidate "covers" a window when one
contiguous source range [a, a+L) gives SSIM >= 0.95 on every frame. Overlap disambiguation per rubric:
among covering candidates prefer the edl-claimed one, else the one with the highest minimum SSIM.
"""
import csv, json, os, pathlib, pickle, subprocess
import numpy as np
import cv2

W, H = 360, 202          # longest side 360 (1280x720 -> 360x202.5, even rounding)
TW, TH = 64, 36
THR = 0.95
DUP = 0.995
WINDOWS = [(0, 210), (210, 390), (390, 630), (630, 870), (870, 1080), (1080, 1290)]
KEY = {1: '28', 2: '07', 3: '10', 4: '16', 5: '37', 6: '17'}
SLOT_ITEM = {1: 'M2', 2: 'M3', 6: 'M4', 4: 'M5', 3: 'G1', 5: 'G2'}
FRAMES = {'01': 240, '02': 225, '03': 300, '04': 300, '05': 294, '06': 300, '07': 216, '08': 267, '09': 231,
          '10': 282, '11': 330, '12': 180, '13': 300, '14': 300, '15': 300, '16': 288, '17': 285, '18': 270,
          '19': 180, '20': 195, '21': 300, '22': 204, '23': 300, '24': 300, '25': 270, '26': 285, '27': 180,
          '28': 270, '29': 225, '30': 201, '31': 240, '32': 270, '33': 210, '34': 300, '35': 300, '36': 195,
          '37': 270}
EXPECT_FILES = {'solution.mp4', 'edl.json', 'events.csv'}
GATE = {'fail': False, 'why': ''}
CACHE = pathlib.Path(os.environ['X07_CACHE']) if os.environ.get('X07_CACHE') else None
if CACHE:
    CACHE.mkdir(parents=True, exist_ok=True)


def _run(cmd, timeout=600):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def decode_gray(path, w=W, h=H):
    """Decode to (N,h,w) uint8 gray. Optional disk cache via env X07_CACHE (local smoke tests only)."""
    cf = None
    if CACHE:
        st = pathlib.Path(path).stat()
        cf = CACHE / f"{pathlib.Path(path).stem}_{st.st_size}_{int(st.st_mtime)}_{w}x{h}.npy"
        if cf.exists():
            return np.load(cf)
    p = _run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0', '-vf',
              f'scale={w}:{h}:flags=area,format=gray', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'])
    buf = p.stdout
    n = len(buf) // (w * h)
    a = np.frombuffer(buf[:n * w * h], np.uint8).reshape(n, h, w)
    if cf is not None:
        np.save(str(cf) + '.tmp.npy', a); os.replace(str(cf) + '.tmp.npy', cf)
    return a


_K = None


def _blur(x):
    return cv2.GaussianBlur(x, (11, 11), 1.5, borderType=cv2.BORDER_REPLICATE)


def ssim(a, b):
    a = a.astype(np.float32); b = b.astype(np.float32)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = _blur(a), _blur(b)
    saa = _blur(a * a) - ma * ma
    sbb = _blur(b * b) - mb * mb
    sab = _blur(a * b) - ma * mb
    m = ((2 * ma * mb + C1) * (2 * sab + C2)) / ((ma * ma + mb * mb + C1) * (saa + sbb + C2))
    return float(m[5:-5, 5:-5].mean())


def thumbs(fr):
    t = np.stack([cv2.resize(f, (TW, TH), interpolation=cv2.INTER_AREA) for f in fr]).astype(np.float32)
    t = t.reshape(len(t), -1)
    t -= t.mean(1, keepdims=True)
    t /= (np.linalg.norm(t, axis=1, keepdims=True) + 1e-6)
    return t


def norm_id(s):
    try:
        if isinstance(s, (int, float)):
            s = '%02d' % int(s)
        s = str(s).strip()
        if s.isdigit():
            s = '%02d' % int(s)
        return s if s in FRAMES else None
    except Exception:
        return None


def load_edl(out):
    try:
        j = json.loads((out / 'edl.json').read_text(encoding='utf-8'))
        seg = j['segments']
        return seg if isinstance(seg, list) else None
    except Exception:
        return None


def run(ctx):
    out = pathlib.Path(ctx['out']); inp = pathlib.Path(ctx['input'])
    R = {}

    def put(k, ok, d):
        R[k] = {'verdict': 'pass' if ok else 'fail', 'detail': str(d)[:900]}

    files = sorted(str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()) if out.exists() else []
    vid = out / 'solution.mp4'
    edl = load_edl(out)

    # ---------- B1 ----------
    try:
        probs = []
        if set(files) != EXPECT_FILES:
            probs.append(f'files={files}')
        if vid.exists():
            j = json.loads(_run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(vid)], 120).stdout or b'{}')
            st = j.get('streams', [])
            v = [s for s in st if s.get('codec_type') == 'video']
            if any(s.get('codec_type') == 'audio' for s in st):
                probs.append('has audio stream')
            if len(v) != 1:
                probs.append(f'{len(v)} video streams')
            else:
                v = v[0]
                for k, e in (('codec_name', 'h264'), ('pix_fmt', 'yuv420p'), ('width', 1280), ('height', 720),
                             ('r_frame_rate', '30/1')):
                    if v.get(k) != e:
                        probs.append(f'{k}={v.get(k)}')
                # CFR: judged on packet timestamps (avg_frame_rate is skewed by container duration/edit lists)
                pk = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'packet=pts_time',
                           '-of', 'csv=p=0', str(vid)], 120).stdout.decode('utf-8', 'replace').split()
                ts = sorted(float(x.strip(',')) for x in pk if x.strip(',') not in ('', 'N/A'))
                dd = np.diff(np.array(ts)) if len(ts) > 1 else np.array([])
                if len(dd) == 0 or np.abs(dd - 1 / 30).max() > 2e-3:
                    probs.append(f"not 30 fps CFR by timestamps (deltas {sorted(set(np.round(dd, 4).tolist()))[:5]}, avg_frame_rate={v.get('avg_frame_rate')})")
                if v.get('sample_aspect_ratio', '1:1') not in ('1:1', None):
                    probs.append(f"sar={v.get('sample_aspect_ratio')}")
            dec = _run(['ffmpeg', '-v', 'error', '-i', str(vid), '-f', 'null', '-'], 600)
            if dec.returncode != 0 or dec.stderr.strip():
                probs.append('decode errors: ' + dec.stderr.decode('utf-8', 'replace')[:200])
        else:
            probs.append('solution.mp4 missing')
        missing = [f for f in EXPECT_FILES if not (out / f).exists()]
        undec = any(x.startswith('decode errors') or x.endswith('video streams') for x in probs)
        GATE['fail'] = bool(missing or undec)
        GATE['why'] = f'missing={missing} undecodable={undec}'
        put('B1', not probs, '; '.join(probs) or 'ok')
    except Exception as e:
        GATE['fail'] = True; GATE['why'] = f'B1 error {e}'
        put('B1', False, f'error {e}')

    # ---------- decode output ----------
    of = None
    try:
        if vid.exists():
            of = decode_gray(vid)
    except Exception:
        of = None
    nout = 0 if of is None else len(of)

    # ---------- B2 ----------
    try:
        probs = []
        if nout != 1290:
            probs.append(f'decoded frames={nout}')
        if edl is None or len(edl) != 6:
            probs.append('edl missing/invalid or not 6 segments')
        else:
            for i, s in enumerate(edl):
                if s.get('window') != i + 1 or [int(x) for x in s.get('output_frames')] != list(WINDOWS[i]) \
                        or any(not isinstance(x, int) for x in s.get('output_frames')):
                    probs.append(f"seg{i}: window={s.get('window')} output_frames={s.get('output_frames')}")
        put('B2', not probs, '; '.join(probs) or 'ok')
    except Exception as e:
        put('B2', False, f'error {e}')

    # ---------- B3 ----------
    claimed = {}
    try:
        probs = []
        if edl is None or len(edl) != 6:
            probs.append('edl missing/invalid or not 6 segments')
        else:
            ids = []
            for i, s in enumerate(edl):
                sid = norm_id(s.get('source'))
                ids.append(sid)
                sf, of_ = s.get('source_frames'), s.get('output_frames')
                if sid is None:
                    probs.append(f"seg{i}: bad source {s.get('source')!r}"); continue
                if not (isinstance(sf, list) and len(sf) == 2 and all(isinstance(x, int) for x in sf)):
                    probs.append(f'seg{i}: bad source_frames {sf}'); continue
                a, b = sf
                if not (0 <= a < b <= FRAMES[sid]):
                    probs.append(f'seg{i}: {sid} {sf} outside [0,{FRAMES[sid]}]')
                try:
                    if b - a != int(of_[1]) - int(of_[0]):
                        probs.append(f'seg{i}: length mismatch {sf} vs {of_}')
                except Exception:
                    probs.append(f'seg{i}: bad output_frames {of_}')
                w = s.get('window')
                if isinstance(w, int):
                    claimed[w] = (sid, a, b)
            if len(set(ids)) != 6 or None in ids:
                probs.append(f'sources not 6 distinct legal ids: {ids}')
        put('B3', not probs, '; '.join(probs) or 'ok')
    except Exception as e:
        put('B3', False, f'error {e}')

    # ---------- B4 ----------
    E = None
    try:
        probs = []
        p = out / 'events.csv'
        if not p.exists():
            probs.append('events.csv missing')
        else:
            rows = list(csv.reader(p.read_text(encoding='utf-8-sig').splitlines()))
            rows = [r for r in rows if any(c.strip() for c in r)]
            if not rows or [c.strip() for c in rows[0]] != ['line_time_s', 'output_frame']:
                probs.append(f'header={rows[:1]}')
            hits = []
            for r in rows[1:]:
                try:
                    if abs(float(r[0]) - 24.5) < 1e-6:
                        hits.append(r[1].strip())
                except Exception:
                    pass
            if len(hits) != 1:
                probs.append(f'{len(hits)} rows with line_time_s=24.5')
            else:
                try:
                    E = int(hits[0])
                    if not (0 <= E < 1290):
                        probs.append(f'output_frame {E} out of range')
                except ValueError:
                    probs.append(f'output_frame not integer: {hits[0]!r}')
                    E = None
        put('B4', not probs, '; '.join(probs) or 'ok')
    except Exception as e:
        put('B4', False, f'error {e}')

    if of is None or nout == 0:
        for k in ('M1', 'M2', 'M3', 'M4', 'M5', 'G1', 'G2', 'G3'):
            put(k, False, 'solution.mp4 missing or undecodable')
        return R

    # ---------- candidates: thumbnails for all, 360-px frames lazily ----------
    cth, _full = {}, {}
    for cid in FRAMES:
        fp = inp / 'clips' / f'{cid}.mp4'
        try:
            fr = decode_gray(fp, TW, TH)
            if len(fr):
                cth[cid] = thumbs(fr)
        except Exception:
            pass

    def full(cid):
        if cid not in _full:
            _full[cid] = decode_gray(inp / 'clips' / f'{cid}.mp4')
        return _full[cid]

    oth = thumbs(of)
    skey = None
    sscache = {}
    if CACHE:
        import hashlib
        skey = CACHE / ('ssim_' + hashlib.md5(of[::50].tobytes()).hexdigest() + '.pkl')
        if skey.exists():
            try:
                sscache = pickle.loads(skey.read_bytes())
            except Exception:
                sscache = {}
    new = [0]

    def _save(force=False):
        if skey is not None and (force or new[0] >= 200):
            skey.write_bytes(pickle.dumps(sscache)); new[0] = 0

    def S(cid, k, oi):
        key = (cid, k, oi)
        if key not in sscache:
            sscache[key] = ssim(of[oi], full(cid)[k]); new[0] += 1; _save()
        return sscache[key]

    def Sdup(cid, k):
        key = ('dup', cid, k)
        if key not in sscache:
            f = full(cid)
            sscache[key] = ssim(f[k], f[k + 1]); new[0] += 1; _save()
        return sscache[key]

    def eval_range(cid, a, c, L, early=True):
        """SSIM of output c+i vs cid frame a+i. Returns list (may stop early when < THR)."""
        vals = []
        n = len(cth[cid])
        for i in range(L):
            if c + i >= nout or a + i >= n:
                vals.append(0.0); break
            v = S(cid, a + i, c + i)
            vals.append(v)
            if early and v < THR:
                break
        return vals

    # ---------- trace per window ----------
    trace = {}
    for w, (c, d) in enumerate(WINDOWS, 1):
        L = d - c
        if c >= nout:
            trace[w] = None; continue
        props = []
        cl = claimed.get(w)
        if cl and cl[0] in cth and 0 <= cl[1] and cl[1] + L <= len(cth[cl[0]]):
            props.append((cl[0], cl[1]))
        ot = oth[c:min(d, nout)]
        scored = []
        for cid, t in cth.items():
            sim = ot @ t.T                      # (L, Nc)
            best = sim.argmax(1); bv = sim.max(1)
            if np.median(bv) < 0.9:
                continue
            offs = best - np.arange(len(best))
            vals, cnt = np.unique(offs, return_counts=True)
            scored.append((float(np.median(bv)), cid, [int(o) for o in vals[np.argsort(-cnt)][:2]]))
        for _, cid, offs in sorted(scored, reverse=True):
            for o in offs:
                for dd in (0, -1, 1, -2, 2):
                    a = o + dd
                    if 0 <= a and a + L <= len(cth[cid]):
                        props.append((cid, a))
        props = list(dict.fromkeys(props))
        covers = []
        for cid, a in props:
            vals = eval_range(cid, a, c, L)
            if len(vals) == L and min(vals) >= THR:
                covers.append((cid, a, min(vals)))
                if cl and cid == cl[0]:
                    break       # rubric: prefer the edl-claimed candidate when it covers the window
        if not covers:
            trace[w] = None
        else:
            pc = [x for x in covers if cl and x[0] == cl[0]]
            trace[w] = pc[0] if pc else max(covers, key=lambda x: x[2])

    # ---------- slots ----------
    for w, item in SLOT_ITEM.items():
        t = trace.get(w)
        if t is None:
            put(item, False, f'window {w}: no candidate covers the window with one contiguous range (SSIM>={THR})')
        else:
            put(item, t[0] == KEY[w], f'window {w}: traced source {t[0]} start {t[1]} (min SSIM {t[2]:.3f}); key {KEY[w]}')

    # ---------- M1 ----------
    try:
        probs = []
        if len(claimed) != 6:
            probs.append('edl does not describe 6 windows')
        for w, (c, d) in enumerate(WINDOWS, 1):
            if w not in claimed:
                continue
            cid, a, b = claimed[w]
            L = d - c
            if cid not in cth or b - a != L or a < 0 or b > len(cth[cid]):
                probs.append(f'w{w}: invalid claim {claimed[w]}'); continue
            vals = eval_range(cid, a, c, L)
            if len(vals) < L or min(vals) < THR:
                probs.append(f'w{w}: output {c + len(vals) - 1} vs {cid}#{a + len(vals) - 1} SSIM {vals[-1]:.3f}')
                continue
            ndup = 0
            for i in range(L - 1):
                src_dup = Sdup(cid, a + i) >= DUP
                if src_dup:
                    continue
                if S(cid, a + i, c + i + 1) > S(cid, a + i + 1, c + i + 1) + 1e-3:
                    ndup += 1
                    if ndup == 1:
                        probs.append(f'w{w}: output {c + i + 1} looks like a duplicate of source {a + i}')
        put('M1', not probs, '; '.join(probs) or 'all 1290 frames match claimed source ranges')
    except Exception as e:
        put('M1', False, f'error {e}')

    # ---------- G3 ----------
    try:
        t = trace.get(4)
        probs = []
        if t is None or t[0] != '16':
            probs.append(f'window 4 traced source {t[0] if t else None} != 16')
        else:
            a = t[1]
            if not (12 <= a <= 42):
                probs.append(f'source start a={a} not in [12,42] (onset 132 lands at output {630 + 132 - a})')
            if E is None:
                probs.append('no valid events.csv frame')
            else:
                src = E - 630 + a
                if not (720 <= E <= 750):
                    probs.append(f'declared frame {E} not in 720-750')
                if not (120 <= src <= 150):
                    probs.append(f'declared frame maps to source {src} not in 120-150')
        put('G3', not probs, '; '.join(probs) or f'a={t[1]}, declared {E} -> source {E - 630 + t[1]}')
    except Exception as e:
        put('G3', False, f'error {e}')
    _save(True)
    return R


def postprocess(results, ctx):
    """Missing/undecodable deliverables (B1 gate) = whole-task fail; other B1 spec misses only cost B1."""
    if GATE['fail']:
        for k, v in results.items():
            if not k.startswith('_') and k != 'B1' and v.get('verdict') == 'pass':
                v['verdict'] = 'fail'
                v['detail'] = f"B1 gate failed ({GATE['why']}); " + str(v.get('detail', ''))
    return results
