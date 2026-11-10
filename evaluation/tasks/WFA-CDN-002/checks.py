# -*- coding: utf-8 -*-
"""CDC-A-X02 deterministic checks (B1-B4, M1-M6, G1-G3). G4: schema/range pre-check here
(fail on violation); if it passes, the reason content is left to the judge.

Picture fidelity (M4) uses Y-plane PSNR with cv2/numpy only; sound checks (M5/M6) use mono float
cross-correlation on decoded 48 kHz audio. Expected layout is always derived from the chosen clips'
frame counts (not from the solver's EDL), so fidelity is graded independently of selection correctness.
"""
import json, pathlib, subprocess
import numpy as np

FPS = 24
SR = 48000
SPF = SR // FPS  # 2000 samples per frame
J = 24
W, H = 1280, 544
FSZ = W * H
# Candidate frame counts (from provenance.json); ffprobe of /workspace/input is used if available.
CLIP_FRAMES = {'01': 168, '02': 264, '03': 204, '04': 180, '05': 212, '06': 168, '07': 192, '08': 192, '09': 240,
               '10': 183, '11': 144, '12': 216, '13': 196, '14': 224, '15': 208, '16': 252, '17': 232, '18': 269,
               '19': 223, '20': 264, '21': 254, '22': 184, '23': 240, '24': 268, '25': 197, '26': 240, '27': 200,
               '28': 234, '29': 216, '30': 232, '31': 276, '32': 216, '33': 216, '34': 240, '35': 216, '36': 176,
               '37': 228, '38': 240, '39': 216, '40': 240, '41': 240, '42': 230}
EXPECTED_FILES = {'sequence.mp4', 'edl.json', 'selection-evidence.json'}
SEL_ITEMS = {'G1': 1, 'M1': 2, 'M2': 3, 'G2': 4, 'M3': 5, 'G3': 6}


def P(v, d=''):
    return {'verdict': 'pass', 'detail': str(d)[:1500]}


def F(d):
    return {'verdict': 'fail', 'detail': str(d)[:1500]}


def run_(cmd, timeout=600, binary=False):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, text=not binary)
    return r


def ffprobe_json(path, extra):
    r = run_(['ffprobe', '-v', 'error'] + extra + ['-of', 'json', str(path)], 300)
    return json.loads(r.stdout or '{}')


# ---------------- media helpers ----------------
def decode_y(path, start=None, count=None):
    """Return uint8 array (n, H, W) of luma, optionally frames [start, start+count)."""
    vf = 'format=gray'
    if start is not None:
        vf = f'select=between(n\\,{start}\\,{start + count - 1}),' + vf
    r = run_(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0', '-vf', vf, '-vsync', '0',
              '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], 600, binary=True)
    buf = r.stdout
    n = len(buf) // FSZ
    return np.frombuffer(buf[:n * FSZ], np.uint8).reshape(n, H, W)


def decode_audio(path):
    r = run_(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0', '-ac', '1', '-ar', str(SR),
              '-f', 'f32le', '-'], 600, binary=True)
    return np.frombuffer(r.stdout, np.float32).astype(np.float64)


def psnr(a, b):
    d = a.astype(np.float32) - b.astype(np.float32)
    m = float(np.mean(d * d))
    return 99.0 if m < 1e-10 else 10 * np.log10(255.0 ** 2 / m)


def rms_db(x):
    if len(x) == 0:
        return -200.0
    r = float(np.sqrt(np.mean(x * x)))
    return 20 * np.log10(max(r, 1e-10))


def xcorr(out_seg, src_seg, maxlag):
    """Best normalized correlation of out_seg vs src_seg over lags in [-maxlag, maxlag].
    lag > 0 means output is delayed relative to source. Returns (corr, lag)."""
    n = min(len(out_seg), len(src_seg))
    if n < 200:
        return 0.0, 0
    a = out_seg[:n] - 0.0
    b = src_seg[:n] - 0.0
    L = 1
    while L < 2 * n:
        L *= 2
    c = np.fft.irfft(np.fft.rfft(a, L) * np.conj(np.fft.rfft(b, L)), L)
    lags = np.concatenate([np.arange(0, maxlag + 1), np.arange(-maxlag, 0)])
    vals = np.concatenate([c[:maxlag + 1], c[L - maxlag:]])
    k = int(np.argmax(vals))
    lag = int(lags[k])
    # normalized over overlap at that lag
    if lag >= 0:
        x, y = a[lag:], b[:n - lag]
    else:
        x, y = a[:n + lag], b[-lag:]
    den = np.sqrt(np.sum(x * x) * np.sum(y * y))
    return (float(np.sum(x * y) / den) if den > 0 else 0.0), lag


def ncorr0(x, y):
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    den = np.sqrt(np.sum(x * x) * np.sum(y * y))
    return float(abs(np.sum(x * y)) / den) if den > 0 else 0.0


# ---------------- main ----------------
def run(ctx):
    out = pathlib.Path(ctx['out'])
    inp = pathlib.Path(ctx['input'])
    ans = ctx.get('answer') or {}
    correct = ans.get('correct_sources') or ['42', '41', '05', '18', '02', '31']
    res = {}
    seq = out / 'sequence.mp4'
    st = {}

    # ---- B1 ----
    try:
        files = {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()} if out.exists() else set()
        probs = []
        if files != EXPECTED_FILES:
            probs.append(f'output files = {sorted(files)}')
        edl = ev = None
        try:
            edl = json.loads((out / 'edl.json').read_text(encoding='utf-8'))
        except Exception as e:
            probs.append(f'edl.json unparsable: {e}')
        try:
            ev = json.loads((out / 'selection-evidence.json').read_text(encoding='utf-8'))
        except Exception as e:
            probs.append(f'selection-evidence.json unparsable: {e}')
        if seq.exists():
            r = run_(['ffmpeg', '-v', 'error', '-i', str(seq), '-f', 'null', '-'], 900)
            if r.returncode != 0 or r.stderr.strip():
                probs.append('decode errors: ' + r.stderr.strip()[:300])
        else:
            probs.append('sequence.mp4 missing')
        res['B1'] = F('; '.join(probs)) if probs else P(1, 'three files present, mp4 decodes cleanly, JSON parses')
        st['edl'] = edl
    except Exception as e:
        res['B1'] = F(f'check error: {e}')

    # ---- probe ----
    vstreams, astreams, nframes, vdur, adur = [], [], None, None, None
    if seq.exists():
        try:
            j = ffprobe_json(seq, ['-show_streams', '-show_format'])
            vstreams = [s for s in j.get('streams', []) if s.get('codec_type') == 'video']
            astreams = [s for s in j.get('streams', []) if s.get('codec_type') == 'audio']
        except Exception:
            pass

    # ---- B2 ----
    try:
        if not vstreams:
            res['B2'] = F('no video stream')
        else:
            v = vstreams[0]
            probs = []
            if v.get('codec_name') != 'h264': probs.append(f"codec={v.get('codec_name')}")
            if v.get('pix_fmt') != 'yuv420p': probs.append(f"pix_fmt={v.get('pix_fmt')}")
            if (v.get('width'), v.get('height')) != (W, H): probs.append(f"size={v.get('width')}x{v.get('height')}")
            if v.get('sample_aspect_ratio') not in ('1:1', None, 'N/A'): probs.append(f"SAR={v.get('sample_aspect_ratio')}")
            if v.get('r_frame_rate') != '24/1': probs.append(f"r_frame_rate={v.get('r_frame_rate')}")
            fj = ffprobe_json(seq, ['-select_streams', 'v:0', '-show_entries', 'frame=pts_time,best_effort_timestamp_time'])
            ts = []
            for fr in fj.get('frames', []):
                t = fr.get('pts_time', fr.get('best_effort_timestamp_time'))
                if t not in (None, 'N/A'):
                    ts.append(float(t))
            nframes = len(fj.get('frames', []))
            if len(ts) >= 2:
                d = np.diff(np.array(ts))
                bad = int(np.sum(np.abs(d - 1 / 24) > 0.002))
                if bad: probs.append(f'{bad} non-1/24 s pts steps (min {d.min():.4f}, max {d.max():.4f})')
            else:
                probs.append('could not read frame timestamps')
            vdur = (ts[-1] - ts[0] + 1 / 24) if ts else None
            res['B2'] = F('; '.join(probs)) if probs else P(1, f'h264 yuv420p 1280x544 SAR1:1 24/1, {nframes} frames constant 1/24 s steps')
    except Exception as e:
        res['B2'] = F(f'check error: {e}')
    st['nframes'] = nframes

    # ---- B3 ----
    try:
        if len(astreams) != 1:
            res['B3'] = F(f'{len(astreams)} audio streams')
        else:
            a = astreams[0]
            probs = []
            if a.get('codec_name') != 'aac' or a.get('profile') != 'LC': probs.append(f"codec={a.get('codec_name')}/{a.get('profile')}")
            if int(a.get('channels') or 0) != 2: probs.append(f"channels={a.get('channels')}")
            if str(a.get('sample_rate')) != '48000': probs.append(f"sr={a.get('sample_rate')}")
            try:
                adur = float(a.get('duration'))
            except Exception:
                adur = None
            if vdur is None and vstreams:
                try: vdur = float(vstreams[0].get('duration'))
                except Exception: pass
            if adur is None or vdur is None:
                probs.append('durations unreadable')
            elif abs(adur - vdur) > 1 / 24 + 1e-3:
                probs.append(f'audio {adur:.4f}s vs video {vdur:.4f}s')
            res['B3'] = F('; '.join(probs)) if probs else P(1, f'AAC-LC stereo 48k, a={adur:.4f}s v={vdur:.4f}s')
    except Exception as e:
        res['B3'] = F(f'check error: {e}')

    # ---- clip frame counts ----
    def clip_n(s):
        p = inp / f'{s}.mp4'
        if p.exists():
            try:
                j = ffprobe_json(p, ['-select_streams', 'v:0', '-show_entries', 'stream=nb_frames'])
                return int(j['streams'][0]['nb_frames'])
            except Exception:
                pass
        return CLIP_FRAMES.get(s)

    # ---- EDL / selection ----
    edl = st.get('edl')
    segs = None
    sources = None
    try:
        segs = edl.get('segments') if isinstance(edl, dict) else None
        if isinstance(segs, list):
            sources = [str(s.get('source')) if isinstance(s, dict) else None for s in segs]
    except Exception:
        segs = None
    for item, slot in SEL_ITEMS.items():
        try:
            if not sources or len(sources) < slot:
                res[item] = F('edl.json missing/unparsable or lacks this slot')
                continue
            seg = segs[slot - 1]
            src = sources[slot - 1]
            if seg.get('slot') != slot:
                res[item] = F(f'segment {slot} has slot={seg.get("slot")}')
            elif src == correct[slot - 1]:
                res[item] = P(1, f'slot {slot} source {src}')
            else:
                res[item] = F(f'slot {slot} source {src} != {correct[slot - 1]}')
        except Exception as e:
            res[item] = F(f'check error: {e}')

    # ---- B4 ----
    try:
        probs = []
        if not isinstance(segs, list) or len(segs) != 6:
            probs.append('segments missing or not 6')
        else:
            ids = []
            for k, s in enumerate(segs):
                if s.get('slot') != k + 1: probs.append(f'seg{k} slot={s.get("slot")}')
                src = s.get('source')
                if not (isinstance(src, str) and src in CLIP_FRAMES): probs.append(f'seg{k} bad source {src!r}')
                ids.append(src)
            if len(set(ids)) != 6: probs.append(f'sources not distinct {ids}')
            for kind in ('picture', 'sound'):
                pos = 0
                for k, s in enumerate(segs):
                    try:
                        o = s[kind]['output_frames']; sf = s[kind]['source_frames']
                        if not all(isinstance(x, int) and not isinstance(x, bool) for x in o + sf) or len(o) != 2 or len(sf) != 2:
                            probs.append(f'{kind} seg{k + 1} non-integer/bad intervals'); break
                        if o[0] != pos: probs.append(f'{kind} seg{k + 1} starts {o[0]} expected {pos}')
                        if o[1] <= o[0] or sf[1] <= sf[0]: probs.append(f'{kind} seg{k + 1} empty/inverted')
                        if (o[1] - o[0]) != (sf[1] - sf[0]): probs.append(f'{kind} seg{k + 1} output/source length mismatch')
                        n = clip_n(s.get('source'))
                        if n is None or sf[0] < 0 or sf[1] > n: probs.append(f'{kind} seg{k + 1} source_frames {sf} outside [0,{n})')
                        pos = o[1]
                    except Exception as e:
                        probs.append(f'{kind} seg{k + 1} malformed: {e}'); break
            try:
                last = segs[-1]['picture']['output_frames'][1]
                if nframes is None:
                    probs.append('decoded frame count unavailable')
                elif last != nframes:
                    probs.append(f'last picture end {last} != decoded frames {nframes}')
            except Exception:
                pass
        res['B4'] = F('; '.join(probs[:12])) if probs else P(1, f'EDL contract ok, {nframes} frames')
    except Exception as e:
        res['B4'] = F(f'check error: {e}')

    # ---- expected layout from chosen clips ----
    layout = None
    try:
        if sources and len(sources) == 6 and all(s in CLIP_FRAMES for s in sources) and len(set(sources)) == 6:
            Ns = [clip_n(s) for s in sources]
            layout, p = [], 0
            for k, n in enumerate(Ns):
                ps = (J, n) if k == 5 else (0, n)
                layout.append({'src': sources[k], 'N': n, 'po': (p, p + ps[1] - ps[0]), 'ps': ps})
                p += ps[1] - ps[0]
    except Exception:
        layout = None

    # ---- M4 picture fidelity ----
    try:
        if layout is None:
            res['M4'] = F('edl.json unparsable or sources invalid -> M4 = 0 (group gate)')
        elif not seq.exists() or not vstreams:
            res['M4'] = F('no video')
        else:
            probs, notes = [], []
            total = layout[-1]['po'][1]
            if nframes is not None and nframes != total:
                probs.append(f'decoded frames {nframes} != expected {total}')
            # check EDL picture lengths agree with expected segment lengths
            for k, L in enumerate(layout):
                try:
                    o = segs[k]['picture']['output_frames']
                    if (o[1] - o[0]) != (L['po'][1] - L['po'][0]):
                        probs.append(f'slot{k + 1} EDL picture length {o[1] - o[0]} != expected {L["po"][1] - L["po"][0]}')
                except Exception:
                    probs.append(f'slot{k + 1} EDL picture malformed')
            pipe = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(seq), '-map', '0:v:0', '-vsync', '0',
                                     '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL)

            def read_frames(cnt):
                buf = pipe.stdout.read(cnt * FSZ) or b''
                n = len(buf) // FSZ
                return np.frombuffer(buf[:n * FSZ], np.uint8).reshape(n, H, W)
            for k, L in enumerate(layout):
                src = decode_y(inp / f"{L['src']}.mp4")
                a, b = L['po']
                o = read_frames(b - a)
                if len(o) != b - a:
                    probs.append(f'slot{k + 1}: got {len(o)} output frames for [{a},{b})'); continue
                s0 = L['ps'][0]
                if len(src) < L['ps'][1]:
                    probs.append(f'slot{k + 1}: source decode short'); continue
                ps_all = [psnr(o[i], src[s0 + i]) for i in range(len(o))]
                lowc = sum(1 for x in ps_all if x < 35)
                if lowc:
                    probs.append(f'slot{k + 1}: {lowc} frames PSNR<35 (min {min(ps_all):.1f} dB)')
                for tag, oi, si in (('first', 0, s0), ('last', len(o) - 1, L['ps'][1] - 1)):
                    allp = np.array([psnr(o[oi], src[j]) for j in range(len(src))])
                    best = int(np.argmax(allp))
                    if allp[si] < 35 or (best != si and allp[best] - allp[si] > 0.5):
                        probs.append(f'slot{k + 1} {tag} frame: expected src {si} {allp[si]:.1f} dB, best src {best} {allp[best]:.1f} dB')
                notes.append(f'slot{k + 1}({L["src"]}) min {min(ps_all):.1f} dB')
                del src, o
            try:
                pipe.kill()
            except Exception:
                pass
            res['M4'] = F('; '.join(probs[:12])) if probs else P(1, '; '.join(notes))
    except Exception as e:
        res['M4'] = F(f'check error: {e}')

    # ---- sound ----
    try:
        if not astreams:
            res['M5'] = F('no audio track (group gate)')
            res['M6'] = F('no audio track (group gate)')
        elif layout is None:
            res['M5'] = F('edl.json unparsable or sources invalid')
            res['M6'] = F('edl.json unparsable or sources invalid')
        else:
            A = decode_audio(seq)
            srcA = {L['src']: decode_audio(inp / f"{L['src']}.mp4") for L in layout}
            fs = lambda f: int(f) * SPF

            def win(x, f0, f1):
                return x[max(fs(f0), 0):max(fs(f1), 0)]

            def rms_ok(o, s):
                sd = rms_db(s)
                if sd < -50:
                    return True, f'src {sd:.1f} dBFS exempt'
                od = rms_db(o)
                return od >= sd + 20 * np.log10(0.8), f'out {od:.1f} vs src {sd:.1f} dB'

            # M6 slots 1-5
            probs, notes = [], []
            for k in range(5):
                L = layout[k]
                n = L['N']; sa = srcA[L['src']]
                send = n - J if k == 4 else n
                p0 = L['po'][0]
                o = win(A, p0, p0 + send); s = win(sa, 0, send)
                c, lag = xcorr(o, s, 2000)
                if c < 0.8 or abs(lag) > 2000:
                    probs.append(f'slot{k + 1} corr {c:.3f} lag {lag}')
                ok1, d1 = rms_ok(win(A, p0, p0 + 6), win(sa, 0, 6))
                ok2, d2 = rms_ok(win(A, p0 + send - 6, p0 + send), win(sa, send - 6, send))
                if not ok1: probs.append(f'slot{k + 1} head {d1}')
                if not ok2: probs.append(f'slot{k + 1} tail {d2}')
                notes.append(f'slot{k + 1} r={c:.3f} lag={lag}')
            res['M6'] = F('; '.join(probs)) if probs else P(1, '; '.join(notes))

            # M5 J-cut
            probs = []
            L5, L6 = layout[4], layout[5]
            P5end = L5['po'][1]; N5 = L5['N']; N6 = L6['N']; P6end = L6['po'][1]
            s5, s6 = srcA[L5['src']], srcA[L6['src']]
            c6, lag6 = xcorr(win(A, P5end - J, P6end), win(s6, 0, N6), 1000)
            if c6 < 0.8: probs.append(f'slot6 sound corr {c6:.3f} lag {lag6}')
            c5, lag5 = xcorr(win(A, P5end - 2 * J, P5end - J), win(s5, N5 - 2 * J, N5 - J), 1000)
            if c5 < 0.8: probs.append(f'slot5 pre-cut corr {c5:.3f} lag {lag5}')
            # residual of slot5's last 24 frames under slot6 sound (best over small lags)
            r5, _ = xcorr(win(A, P5end - J, P5end), win(s5, N5 - J, N5), 1000)
            if r5 >= 0.3: probs.append(f'slot5 tail residue corr {r5:.3f} >= 0.3')
            ok, d = rms_ok(win(A, P5end - J, P5end - J + 6), win(s6, 0, 6))
            if not ok: probs.append(f'slot6 sound head fade? {d}')
            ok, d = rms_ok(win(A, P5end - J - 6, P5end - J), win(s5, N5 - J - 6, N5 - J))
            if not ok: probs.append(f'slot5 sound tail fade? {d}')
            # EDL agreement
            try:
                e5, e6 = segs[4], segs[5]
                exp5p = [L5['po'][0], P5end]; exp6p = [P5end, P6end]
                if list(e5['picture']['output_frames']) != exp5p or list(e5['picture']['source_frames']) != [0, N5]:
                    probs.append(f'EDL slot5 picture {e5["picture"]} != out {exp5p} src [0,{N5}]')
                if list(e6['picture']['output_frames']) != exp6p or list(e6['picture']['source_frames']) != [J, N6]:
                    probs.append(f'EDL slot6 picture {e6["picture"]} != out {exp6p} src [{J},{N6}]')
                if list(e5['sound']['output_frames']) != [L5['po'][0], P5end - J] or list(e5['sound']['source_frames']) != [0, N5 - J]:
                    probs.append(f'EDL slot5 sound {e5["sound"]} != out [{L5["po"][0]},{P5end - J}] src [0,{N5 - J}]')
                if list(e6['sound']['output_frames']) != [P5end - J, P6end] or list(e6['sound']['source_frames']) != [0, N6]:
                    probs.append(f'EDL slot6 sound {e6["sound"]} != out [{P5end - J},{P6end}] src [0,{N6}]')
            except Exception as e:
                probs.append(f'EDL slot5/6 malformed: {e}')
            res['M5'] = F('; '.join(probs)) if probs else P(1, f'slot6 r={c6:.3f} lag={lag6}; slot5 pre-cut r={c5:.3f}; residue r={r5:.3f}')
    except Exception as e:
        res.setdefault('M5', F(f'check error: {e}'))
        res.setdefault('M6', F(f'check error: {e}'))

    # ---- G4 pre-check (schema/range part; content part is left to the judge) ----
    try:
        probs = []
        try:
            ev = json.loads((out / 'selection-evidence.json').read_text(encoding='utf-8'))
        except Exception as e:
            ev = None
            probs.append(f'selection-evidence.json missing/unparsable: {e}')
        if ev is not None:
            if not isinstance(ev, list) or len(ev) != 6:
                probs.append(f'evidence is not an array of 6 objects ({type(ev).__name__}, len={len(ev) if isinstance(ev, list) else "-"})')
            else:
                by_slot = {e.get('slot'): e for e in ev if isinstance(e, dict)}
                for slot in range(1, 7):
                    e = by_slot.get(slot)
                    if e is None:
                        probs.append(f'slot {slot}: no evidence entry'); continue
                    src = e.get('source')
                    esrc = sources[slot - 1] if sources and len(sources) >= slot else None
                    if src != esrc:
                        probs.append(f'slot {slot}: source {src!r} != edl source {esrc!r}')
                    sf = e.get('source_frames')
                    if not (isinstance(sf, list) and len(sf) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in sf)):
                        probs.append(f'slot {slot}: bad source_frames {sf!r}')
                    else:
                        n = clip_n(src) if isinstance(src, str) else None
                        if n is None or sf[0] < 0 or sf[1] > n:
                            probs.append(f'slot {slot}: source_frames {sf} outside [0,{n})')
                        if sf[1] - sf[0] < 12:
                            probs.append(f'slot {slot}: source_frames {sf} span < 12')
                    r = e.get('reason')
                    if not (isinstance(r, str) and r.strip()):
                        probs.append(f'slot {slot}: empty reason')
        if probs:
            res['G4'] = F('evidence schema: ' + '; '.join(probs[:12]))
        # otherwise G4 is left to the judge (reasons of slots 1, 4, 6 vs answer-key distractors)
    except Exception as e:
        res['G4'] = F(f'check error: {e}')
    return res


def postprocess(results, ctx):
    # Group gates are already enforced in run(): no audio -> B3/M5/M6 fail; unparsable EDL -> M4 fail.
    # B1 whole-task gate: continuous score still reported; flag acceptance failure in aux.
    b1 = results.get('B1', {}).get('verdict')
    results['_acceptance'] = {'verdict': 'info', 'detail': 'pass' if b1 == 'pass' else 'acceptance failure (B1)'}
    sel = sum(1 for k in SEL_ITEMS if results.get(k, {}).get('verdict') == 'pass')
    results['_correct_slots'] = {'verdict': 'info', 'detail': f'{sel}/6'}
    return results
