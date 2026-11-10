# -*- coding: utf-8 -*-
"""CDC-C-X06 deterministic checks (see review/VERIFIER_NOTES.md, review/rubric-cleanup-20261025.md).
Full verdicts: B01-B07, M01-M10, G01-G07 (Blender per-frame export x06_blend_dump.py + numpy x06_blend_checks.py,
stems with numpy, film with ffmpeg).  Fail-only: G08 (engineering clauses; the visual clause goes to the judge).
Judge only: M11, G09, G10 (and G08 when its engineering clauses hold).  postprocess: rubric group gates + task gate flag."""
import json, re, shutil, subprocess, traceback
from pathlib import Path
import numpy as np
import cdcc_lib as L
import x06_blend_checks as XB

SR = 48000
CUTS = [150, 270, 450, 540, 660]
CUTS_REV = [150, 270, 459, 540, 660]
SHOTS = {'S1': (0, 149), 'S2': (150, 269), 'S3': (270, 449), 'S4': (450, 539), 'S5': (540, 659), 'S6': (660, 899)}
SHOP = ['S1', 'S3', 'S5']; STREET = ['S2', 'S4', 'S6']
STEMS = ['foley', 'shop', 'street']
REQ_OBJ = ['MECHANIC', 'COURIER', 'MECHANIC_RIG', 'COURIER_RIG', 'BIKE', 'CHAIN', 'QUICK_LINK', 'OLD_CHAIN', 'CHAINRING', 'CRANK',
           'REAR_COG', 'REAR_WHEEL', 'FRONT_WHEEL', 'REPAIR_STAND', 'PARTS_TRAY', 'WINDOW', 'WATCH', 'HELMET'] + [f'CAM_S{i}' for i in range(1, 7)]
REQ_EV = {'old_chain_off': 'S1', 'watch_check': 'S2', 'chain_hand_contact': 'S3', 'link_join_start': 'S3', 'link_click': 'S3',
          'courier_turn': 'S4', 'crank_grab': 'S5', 'crank_turn_start': 'S5', 'chain_engage': 'S5', 'crank_release': 'S5', 'pedal_start': 'S6'}
BLEND_DERIVED = ['M04', 'M05', 'M06', 'M07', 'M08', 'G01', 'G02', 'G03', 'G04', 'G05', 'G06', 'G07']
EVENT_DERIVED = ['M07', 'G01', 'G02', 'G03', 'G04', 'G05', 'G07']
V = L.V
HERE = Path(__file__).resolve().parent
DUMP_BUDGET_S = 1100      # per-frame export (low-priority frames are skipped beyond this)
DUMP_TIMEOUT_S = 1500
RENDER_TIMEOUT_S = 1500
RENDER_FRAMES = [(75, 'CAM_S1'), (210, 'CAM_S2'), (360, 'CAM_S3'), (495, 'CAM_S4'), (600, 'CAM_S5'), (780, 'CAM_S6')]


def run_blender(blend, mode, outj, args, timeout):
    """runs x06_blend_dump.py; returns (dict|None, problem)."""
    if not shutil.which('blender'):
        return None, 'blender not available in the grader image'
    try:
        r = subprocess.run(['blender', '-b', '--factory-startup', str(blend), '--python', str(HERE / 'x06_blend_dump.py'), '--',
                            mode, str(outj), json.dumps(args)], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f'blender {mode} exceeded {timeout} s'
    if not Path(outj).exists():
        return None, f'blender could not open/process scene.blend: {((r.stdout or "") + (r.stderr or ""))[-500:]}'
    try:
        d = json.loads(Path(outj).read_text())
    except Exception as e:
        return None, f'blender {mode} output unreadable: {e}'
    if d.get('fatal'):
        return None, f'blender {mode} failed on this scene: {d["fatal"][-500:]}'
    return d, ''


def gray_at(src, frames, w=640, h=360):
    """grey frames (by decoded index) of a video, or of a still image when frames is None."""
    if frames is None:
        vf = f'scale={w}:{h}:flags=area,format=gray'
        cmd = ['ffmpeg', '-v', 'error', '-i', str(src), '-vf', vf, '-frames:v', '1', '-f', 'rawvideo', '-']
    else:
        sel = '+'.join(f'eq(n,{f})' for f in frames)
        vf = f"select='{sel}',scale={w}:{h}:flags=area,format=gray"
        cmd = ['ffmpeg', '-v', 'error', '-i', str(src), '-vf', vf, '-vsync', '0', '-f', 'rawvideo', '-']
    a = np.frombuffer(subprocess.run(cmd, capture_output=True, timeout=600).stdout, np.uint8)
    n = a.size // (w * h)
    return a[:n * w * h].reshape(n, h, w)


def freeze_runs_native(p, min_pairs=5, thr=3, max_px=0.0001):
    """M01 freeze: frame pairs at native resolution where at most 0.01% of pixels change by more than 3 grey levels
    (identical up to codec noise); returns the longest run of such consecutive pairs and its start."""
    w, h = 1280, 720
    proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', 'scale=1280:720,format=gray', '-f', 'rawvideo', '-'],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    prev, i, run, best, start, bstart = None, 0, 0, 0, 0, 0
    try:
        while True:
            buf = proc.stdout.read(w * h)
            if len(buf) < w * h:
                break
            cur = np.frombuffer(buf, np.uint8).reshape(h, w)
            if prev is not None:
                ch = np.count_nonzero(np.abs(cur.astype(np.int16) - prev) > thr) / (w * h)
                if ch <= max_px:
                    if run == 0: start = i - 1
                    run += 1
                    if run > best: best, bstart = run, start
                else:
                    run = 0
            prev = cur.astype(np.int16)
            i += 1
    finally:
        proc.stdout.close(); proc.wait()
    return best, bstart


# ---- B04 band-energy comparison (same method as CDC-C-X03 B05; copied, not imported) ----
def band_db(x):
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


def _aligned(mix, summ, lag):
    if lag > 0:
        mix = mix[lag:]
    elif lag < 0:
        summ = summ[-lag:]
    n = min(len(mix), len(summ))
    return mix[:n], summ[:n]


def band_compare(mix, summ):
    lag = align(mix, summ)
    mix, summ = _aligned(mix, summ, lag)
    A, B = band_db(mix), band_db(summ)
    if A is None:
        return None
    mask = (A >= A.max(1, keepdims=True) - 40) & (A.max(1, keepdims=True) > -80)
    d = np.abs(A - B)[mask]
    if d.size == 0:
        return None
    return dict(lag=lag, median=float(np.median(d)), p95=float(np.percentile(d, 95)))


def region_band_compare(x, ref, spans=((0.0, 14.9), (15.4, None))):
    """M10 AAC mix: band_compare restricted to non-revised spans (single lag from whole-file alignment)."""
    lag = align(ref, x)
    ref, x = _aligned(ref, x, lag)
    ds = []
    for a, b in spans:
        i, j = int(a * SR), len(x) if b is None else int(b * SR)
        A, B = band_db(ref[i:j]), band_db(x[i:j])
        if A is None:
            continue
        mask = (A >= A.max(1, keepdims=True) - 40) & (A.max(1, keepdims=True) > -80)
        ds.append(np.abs(A - B)[mask])
    d = np.concatenate(ds) if ds else np.array([])
    if d.size == 0:
        return None
    return dict(lag=lag, median=float(np.median(d)), p95=float(np.percentile(d, 95)))


def _lp4k(x):
    X = np.fft.rfft(x)
    X[np.fft.rfftfreq(len(x), 1 / SR) > 4000] = 0
    return np.fft.irfft(X, len(x))


def fit_gains(mix, mono_stems, lag):
    """least-squares stem gains vs decoded mix in the <=4 kHz band (AAC is near-transparent there)."""
    names = list(mono_stems)
    n = min(len(v) for v in mono_stems.values())
    S0 = np.stack([mono_stems[k][:n] for k in names], 1)
    m, _ = _aligned(mix, S0[:, 0], lag)
    S = S0[-lag:] if lag < 0 else S0
    k = min(len(m), len(S))
    ml = _lp4k(m[:k])
    Sl = np.stack([_lp4k(S[:k, i]) for i in range(len(names))], 1)
    g, *_ = np.linalg.lstsq(Sl, ml, rcond=None)
    return dict(zip(names, g.tolist()))


def gain_candidates(tl, names):
    """declared-gain interpretations (same heuristics as before): unity / master lin|dB / per-stem lin|dB x master."""
    gains = L.find_gains(tl)
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
    return cands


def run(ctx):
    out, tmp = Path(ctx['out']), Path(ctx['tmp'])
    R, S = {}, {}
    ctx['_x06'] = S

    def guard(iid, fn):
        try:
            v = fn()
            if v is not None:
                R[iid] = v
        except Exception as e:
            R[iid] = V('fail', f'check error: {type(e).__name__}: {e} | {traceback.format_exc()[-300:]}')

    # 2026-10-24 policy: G09/G10 (blind review) are judged by the model; nothing left pending.

    vb, vr = L.find(out, 'base/output.mp4'), L.find(out, 'revision/output.mp4')
    S['rev_present'] = bool(vr)

    def enc(p, tag):
        if not p: return V('fail', f'{tag}/output.mp4 missing')
        ok, d, _ = L.encoding_contract(p, 900)
        return V('pass' if ok else 'fail', d)
    guard('B01', lambda: enc(vb, 'base'))
    guard('B02', lambda: enc(vr, 'revision'))

    mixes = {}
    def b03():
        det, bad = [], False
        for tag, p in (('base', vb), ('revision', vr)):
            if not p: return V('fail', f'{tag} missing')
            I, _ = L.ebur(p)
            x = L.audio(p); mixes[tag] = x
            pk = 20 * np.log10(max(float(np.abs(x).max()), 1e-9))
            clip = L.clip_run(x)
            ok = -20.0 <= I <= -16.0 and pk <= -1.0 and not clip
            bad |= not ok
            det.append(f'{tag}: I={I} LUFS sample_peak={pk:.2f} dBFS clip_run={clip}')
        return V('fail' if bad else 'pass', '; '.join(det))
    guard('B03', b03)

    stems = {}
    def load_stems(tag, p):
        st, bad = {}, []
        for s in STEMS:
            q = p.parent / 'stems' / f'{s}.wav'
            if not q.exists(): bad.append(f'{tag}/stems/{s}.wav missing'); continue
            wi = L.wav_info(q)
            if str(wi.get('sample_rate')) != '48000' or not str(wi.get('codec_name', '')).startswith('pcm'):
                bad.append(f'{tag}/{s}: {wi.get("codec_name")} {wi.get("sample_rate")}')
            a = L.audio(q)
            if abs(len(a) / SR - 30.0) > 0.05: bad.append(f'{tag}/{s}: {len(a)/SR:.3f}s')
            st[s] = a
        stems[tag] = st
        return bad

    def b04():
        if not vb: return V('fail', 'base missing')
        bad = load_stems('base', vb)
        if len(stems['base']) < 3: return V('fail', '; '.join(bad))
        try:
            tl = json.loads((vb.parent / 'timeline.json').read_text(encoding='utf-8'))
        except Exception:
            tl = {}; bad.append('timeline.json unreadable')
        mix = mixes.get('base')
        if mix is None: mix = L.audio(vb); mixes['base'] = mix
        mono = {k: v.mean(axis=1) for k, v in stems['base'].items()}
        mm = mix.mean(axis=1)
        n = min([len(mm)] + [len(v) for v in mono.values()])
        best = None
        for how, gd in gain_candidates(tl, STEMS):
            summ = sum(gd[k] * mono[k][:n] for k in STEMS)
            c = band_compare(mm[:n], summ)
            if c and (best is None or c['median'] < best[2]['median']):
                best = (how, gd, c)
        if best is None: return V('fail', 'band comparison impossible (silent/short); ' + '; '.join(bad))
        how, gd, c = best
        if not (c['median'] <= 0.75 and c['p95'] <= 3.0):
            bad.append(f"band diff median {c['median']:.2f} / p95 {c['p95']:.2f} dB > 0.75 / 3")
        fg = fit_gains(mm[:n], {k: mono[k][:n] for k in STEMS}, c['lag'])
        gdiff = {}
        for k in STEMS:
            if fg[k] <= 0 or gd[k] <= 0:
                gdiff[k] = None; bad.append(f'{k}: fitted gain {fg[k]:.3f} / declared {gd[k]:.3f} non-positive')
            else:
                gdiff[k] = round(float(20 * np.log10(gd[k] / fg[k])), 2)
                if abs(gdiff[k]) > 1.0: bad.append(f'{k}: declared vs fitted {gdiff[k]:+.2f} dB > 1')
        return V('fail' if bad else 'pass',
                 f"band median {c['median']:.2f} dB p95 {c['p95']:.2f} dB lag {c['lag']} ({how}); "
                 f"declared-fitted dB {gdiff}; " + '; '.join(bad))
    guard('B04', b04)

    ev = {}
    def b05():
        p = L.find(out, 'base/events.csv')
        if not p: S['b05'] = False; return V('fail', 'base/events.csv missing')
        header, e, badint = L.read_events(p)
        ev.update({k: v for k, v in e.items() if v is not None})
        prob = []
        if header != 'event_id,frame,description': prob.append(f'header {header!r}')
        miss = [k for k in REQ_EV if k not in ev]
        if miss: prob.append(f'missing {miss}')
        if badint: prob.append(f'non-integer {badint}')
        if not prob:
            g = ev
            for k, s in REQ_EV.items():
                a, b = SHOTS[s]
                if not (0 <= g[k] <= 899 and a <= g[k] <= b): prob.append(f'{k}={g[k]} not in {s} {a}-{b}')
            if not (g['chain_hand_contact'] < g['link_join_start'] < g['link_click']): prob.append('order chain_hand_contact<link_join_start<link_click')
            if not (g['crank_grab'] <= g['crank_turn_start'] <= g['chain_engage'] < g['crank_release']): prob.append('order crank_grab<=crank_turn_start<=chain_engage<crank_release')
        S['b05'] = not prob
        return V('fail' if prob else 'pass', '; '.join(prob) if prob else f'ok {dict(ev)}')
    guard('B05', b05)

    BL = {}
    def b06():
        bl = L.find(out, 'project/scene.blend')
        prob = []
        if not bl: return V('fail', 'project/scene.blend missing')
        rd = L.find(out, 'project/README.md')
        if not rd or not re.search(r'blender\b.*(-b|--background)', rd.read_text(encoding='utf-8', errors='replace'), re.I):
            prob.append('README.md missing or without a blender -b export command')
        d, why = run_blender(bl, 'dump', tmp / 'x06_dump.json', {'events': dict(ev), 'budget': DUMP_BUDGET_S, 'hard': DUMP_TIMEOUT_S - 150}, DUMP_TIMEOUT_S)
        if d is None:
            if 'not available' in why:
                BL['error'] = why
                return {'verdict': 'error', 'detail': why}
            BL['problem'] = why
            return V('fail', '; '.join([why] + prob))
        BL['path'], BL['dump'] = bl, d
        objs = d.get('objects') or {}
        miss = [n for n in REQ_OBJ if n not in objs]
        if miss: prob.append(f'missing objects {miss}')
        for r in ('MECHANIC_RIG', 'COURIER_RIG'):
            if r in objs and objs[r].get('type') != 'ARMATURE': prob.append(f'{r} is {objs[r].get("type")}, not ARMATURE')
        if not d.get('has_roll'): prob.append('scene property roll_T34_frames missing')
        fv = d.get('file_version') or [0, 0, 0]
        if tuple(fv[:2]) != (4, 3): prob.append(f'scene.blend saved with Blender {fv}')
        if not str(d.get('version', '')).startswith('4.3'): prob.append(f'grader Blender {d.get("version")}')
        return V('fail' if prob else 'pass', '; '.join(prob) if prob else
                 f'opened in {d["version"]} (file {fv}); objects/property present; export {d.get("elapsed")} s, '
                 f'{len(d.get("frames") or {})} frames, skipped {d.get("n_truncated")}, errors {len(d.get("errors") or [])}')
    guard('B06', b06)

    F = {}
    def m01():
        if not vb: return V('fail', 'base missing')
        F['base'] = L.gray_frames(vb)
        cs = L.cut_structure(F['base'], CUTS)
        S['cuts'] = cs['cuts']
        if cs['missing'] or cs['extra'] or cs['blendlike']:
            return V('fail', f'cut detection {cs}')
        # freeze: >=6 consecutive frames (5 pairs) identical at native resolution up to codec noise
        best, st = freeze_runs_native(vb)
        if best >= 5:
            return V('fail', f'freeze: {best + 1} consecutive near-identical frames from frame {st} (<=0.01% pixels change >3 levels)')
        return V('pass', f'hard cuts at {cs["cuts"]}; longest near-identical run {best + 1} frames (<6)')
    guard('M01', m01)

    def segs(names, margin):
        return [((SHOTS[n][0] + margin) / 30, (SHOTS[n][1] + 1 - margin) / 30) for n in names]

    def holes(x, t0, t1):
        t, e = L.env_db(x[int(t0 * SR):int(t1 * SR)], 0.05, 0.01)
        if not len(e): return 0
        med = float(np.median(e)); run = best = 0
        for v in e:
            run = run + 1 if v < med - 20 else 0
            best = max(best, run)
        return (best - 1) * 0.01 + 0.05 if best else 0

    def spectrum(x, spans):
        y = np.concatenate([x[int(a * SR):int(b * SR)].mean(axis=1) for a, b in spans])
        nf = 8192; hop = 4096; n = (len(y) - nf) // hop + 1
        if n <= 0: raise ValueError('too short')
        P = np.zeros(nf // 2 + 1); w = np.hanning(nf)
        for i in range(n): P += np.abs(np.fft.rfft(y[i * hop:i * hop + nf] * w)) ** 2
        f = np.fft.rfftfreq(nf, 1 / SR)
        sel = (f >= 20) & (f <= 20000)
        cen = float((f[sel] * P[sel]).sum() / max(P[sel].sum(), 1e-20))
        centres = [1000 * 2 ** (k / 3) for k in range(-13, 13)]
        bands = np.array([P[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() for c in centres])
        bands = bands / max(bands.sum(), 1e-20)
        return cen, 10 * np.log10(np.maximum(bands, 1e-12))

    def m03():
        st = stems.get('base') or {}
        if 'shop' not in st or 'street' not in st: return V('fail', 'base shop/street stems missing')
        bad, det = [], []
        for stem, own, other in (('shop', SHOP, STREET), ('street', STREET, SHOP)):
            x = st[stem]
            for a, b in segs(other, 2):
                m = L.max_db(x, a, b, 0.05)
                if m > -50: bad.append(f'{stem} leaks {m:.1f} dBFS in {a:.2f}-{b:.2f}s')
            for a, b in segs(own, 2):
                m = L.max_db(x, a, b, 0.05)
                if m <= -50: bad.append(f'{stem} silent in own {a:.2f}-{b:.2f}s')
                h = holes(x, a, b)
                if h >= 0.1: bad.append(f'{stem} hole {h:.2f}s in {a:.2f}-{b:.2f}s')
        c1, b1 = spectrum(st['shop'], segs(SHOP, 2)); c2, b2 = spectrum(st['street'], segs(STREET, 2))
        cr = abs(c1 - c2) / max(min(c1, c2), 1e-9); dist = float(np.sqrt(np.mean((b1 - b2) ** 2)))
        det.append(f'centroid shop {c1:.0f} Hz street {c2:.0f} Hz diff {cr*100:.0f}%; 1/3-oct dist {dist:.1f} dB')
        if cr < 0.30 and dist < 6: bad.append('ambiences not spectrally distinct')
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('M03', m03)

    def m09():
        if not vr or 'base' not in F: return V('fail', 'revision or base missing')
        B = F['base']; Rv = L.gray_frames(vr)
        bad = []
        if len(Rv) != 900 or len(B) != 900: return V('fail', f'frame counts base {len(B)} rev {len(Rv)}')
        low = [(i, round(L.psnr(B[i], Rv[i]), 1)) for i in list(range(0, 450)) + list(range(459, 900)) if L.psnr(B[i], Rv[i]) < 32]
        if low: bad.append(f'{len(low)} frames PSNR<32, e.g. {low[:5]}')
        for i in range(450, 459):
            d449 = float(np.abs(Rv[i].astype(np.int16) - B[449]).mean()); d450 = float(np.abs(Rv[i].astype(np.int16) - B[450]).mean())
            if d449 >= d450: bad.append(f'rev frame {i} closer to base S4 than S3'); break
        moving = [i for i in range(451, 459) if float(np.abs(Rv[i].astype(np.int16) - Rv[i - 1]).mean()) > 0.05]
        if len(moving) < 4: bad.append('rev frames 450-458 are (near) frozen')
        cs = L.cut_structure(Rv, CUTS_REV)
        S['rev_cuts'] = cs['cuts']
        if 459 in cs['missing'] or any(abs(c - 450) <= 1 for c in cs['cuts']): bad.append(f'rev cuts {cs["cuts"]}')
        if bad: return V('fail', '; '.join(bad))
        S['m09_picture'] = True
        return None  # completed after the re-render (rerender())
    guard('M09', m09)

    def m10():
        if not vr: return V('fail', 'revision missing')
        bad = load_stems('revision', vr)
        sb, sr = stems.get('base') or {}, stems['revision']
        if len(sr) < 3 or len(sb) < 3: return V('fail', 'stems missing: ' + '; '.join(bad))
        f2 = 2 / 30
        chk = [('shop', 15.0, 15.25, '>', 'rev shop sounding 15.00-15.25'), ('shop', 15.30 + f2, 18.0 - f2, '<=', 'rev shop out after 15.30'),
               ('street', 15.0 + f2, 15.30 - f2, '<=', 'rev street silent before 15.30'), ('street', 15.30 + f2, 15.6, '>', 'rev street in at 15.30')]
        for s, a, b, op, lab in chk:
            m = L.max_db(sr[s], a, b, 0.05)
            if not (m > -50 if op == '>' else m <= -50): bad.append(f'{lab}: {m:.1f} dBFS')
        def region_diff(x, y):
            n = min(len(x), len(y)); num = den = 0.0
            for a, b in ((0.0, 14.9), (15.4, n / SR)):
                i, j = int(a * SR), int(b * SR)
                num += float(np.sum((x[i:j] - y[i:j]) ** 2)); den += float(np.sum(y[i:j] ** 2))
            return L.db(num) - L.db(den) if den > 1e-8 else (-200 if num < 1e-10 else 0)
        det = []
        for s in STEMS:
            r = region_diff(sr[s], sb[s]); det.append(f'{s} {r:.1f}')
            if r > -40: bad.append(f'{s} stem differs from base outside T34 ({r:.1f} dB)')
        for tag, p in (('base', vb), ('revision', vr)):
            if tag not in mixes and p: mixes[tag] = L.audio(p)
        if 'base' in mixes and 'revision' in mixes:
            c = region_band_compare(mixes['revision'].mean(axis=1), mixes['base'].mean(axis=1))
            if c is None: bad.append('mix band comparison impossible (silent/short)')
            else:
                det.append(f"mix band median {c['median']:.2f} p95 {c['p95']:.2f} lag {c['lag']}")
                if not (c['median'] <= 0.75 and c['p95'] <= 3.0):
                    bad.append(f"mix differs from base outside T34 (band median {c['median']:.2f} / p95 {c['p95']:.2f} dB > 0.75 / 3)")
        return V('fail' if bad else 'pass', '; '.join(bad) + ' | diff dB: ' + ', '.join(det))
    guard('M10', m10)

    def b07():
        def ints(o):
            if isinstance(o, dict): return [x for v in o.values() for x in ints(v)]
            if isinstance(o, list): return [x for v in o for x in ints(v)]
            if isinstance(o, (int, float)) and not isinstance(o, bool) and float(o).is_integer(): return [int(o)]
            return []
        bad = []
        for tag, p, key, exp in (('base', vb, 'cuts', CUTS), ('revision', vr, 'rev_cuts', CUTS_REV)):
            if not p: return V('fail', f'{tag} missing')
            try: vals = set(ints(json.loads((p.parent / 'timeline.json').read_text(encoding='utf-8'))))
            except Exception as e: return V('fail', f'{tag}/timeline.json unreadable: {e}')
            cuts = S.get(key) or exp  # detected cuts (M01/M09); nominal when detection did not run
            for c in cuts:
                if not any(abs(c - v) <= 1 or abs(c - 1 - v) <= 1 for v in vals): bad.append(f'{tag}: cut at {c} not declared')
            if tag == 'revision' and not ({458, 459} & vals): bad.append('revision T34 (459) not declared')
            if tag == 'base' and 459 in vals and 450 not in vals: bad.append('base declares T34 at 459')
        return V('fail' if bad else 'pass', '; '.join(bad) or f'declared edit points match detected cuts {S.get("cuts")} / {S.get("rev_cuts")}')
    guard('B07', b07)

    # ---------------- Blender-derived items (per-frame export) ----------------
    BLEND_ITEMS = ['M02', 'M04', 'M05', 'M06', 'M07', 'M08', 'G01', 'G02', 'G03', 'G04', 'G05', 'G06', 'G07', 'G08']
    if 'dump' not in BL:
        why = BL.get('error') or BL.get('problem') or 'scene.blend missing or not exported'
        for iid in BLEND_ITEMS:
            R[iid] = {'verdict': 'error', 'detail': why} if 'error' in BL else V('fail', f'no Blender export: {why}')
        if 'M09' not in R and S.get('m09_picture'):
            R['M09'] = {'verdict': 'error', 'detail': why} if 'error' in BL else V('fail', f're-render impossible: {why}')
        return R
    D = XB.Dump(BL['dump'])
    evok = bool(S.get('b05'))
    fol = stems.get('base', {}).get('foley')
    fol = fol.mean(axis=1) if fol is not None else None
    res_wh = (1280, 720)

    def item(iid, fn, needs_events=False):
        def g():
            if needs_events and not evok:
                return V('fail', 'events.csv invalid (B05 failed); declared frames unavailable')
            v, d = fn()
            return V(v, d)
        guard(iid, g)
    item('M02', lambda: XB.m02(D))
    item('M05', lambda: XB.m05(D))
    item('M06', lambda: XB.m06(D))
    item('M07', lambda: XB.m07(D, ev), True)
    item('M08', lambda: XB.m08(D))
    item('G01', lambda: XB.g01(D, ev, fol, SR), True)
    item('G02', lambda: XB.g02(D, ev), True)
    item('G03', lambda: XB.g03(D, ev), True)
    item('G04', lambda: XB.g04(D, ev), True)
    item('G05', lambda: XB.g05(D, ev, fol, SR), True)
    item('G06', lambda: XB.g06(D, res_wh))
    item('G07', lambda: XB.g07(D, ev), True)

    def g08():
        v, d = XB.g08_engineering(D)
        return V('fail', 'engineering clause: ' + d) if v == 'fail' else None  # visual clause -> judge
    guard('G08', g08)

    def rerender():
        jobs = [{'roll': 0, 'frames': [list(x) for x in RENDER_FRAMES]}]
        if S.get('m09_picture'): jobs.append({'roll': 9, 'frames': [[454, 'CAM_S3']]})
        rd = tmp / 'rr'; rd.mkdir(exist_ok=True)
        args = {'jobs': jobs, 'dir': str(rd), 'w': 640, 'h': 360, 'samples': 16, 'engine': 'CYCLES'}
        d, why = None, ''
        if (BL['dump'].get('engine') or '') != 'CYCLES':
            d, why = run_blender(BL['path'], 'render', tmp / 'x06_render_scene.json', dict(args, engine='SCENE'), 600)
            if d is not None and len(d.get('files') or {}) < sum(len(j['frames']) for j in jobs): d = None
        if d is None:
            d, why = run_blender(BL['path'], 'render', tmp / 'x06_render.json', args, RENDER_TIMEOUT_S)
        if d is None:
            R['M04'] = V('fail', f're-render failed: {why}')
            if S.get('m09_picture'): R['M09'] = V('fail', f're-render failed: {why}')
            return
        files = d.get('files') or {}
        film = gray_at(vb, [f for f, _ in RENDER_FRAMES]) if vb else np.zeros((0, 360, 640), np.uint8)
        sc, bad = [], []
        for k, (f, cam) in enumerate(RENDER_FRAMES):
            p = files.get(f'0:{f}')
            if not p or k >= len(film): bad.append(f'frame {f}: no render'); continue
            img = gray_at(p, None)
            if not len(img): bad.append(f'frame {f}: render unreadable'); continue
            v = XB.ssim(img[0], film[k]); sc.append((f, round(v, 3)))
            if v < 0.70: bad.append(f'frame {f} SSIM {v:.3f} < 0.70')
        R['M04'] = V('fail' if bad else 'pass', '; '.join(bad) + f' | SSIM {sc} ({d.get("engine_used")}, {d.get("elapsed")} s)')
        if S.get('m09_picture'):
            p = files.get('9:454')
            rv = gray_at(vr, [454])
            if not p or not len(rv):
                R['M09'] = V('fail', 'picture clauses hold; re-render of frame 454 with roll_T34_frames=9 failed')
            else:
                v = XB.ssim(gray_at(p, None)[0], rv[0])
                R['M09'] = V('pass' if v >= 0.70 else 'fail', f'picture clauses hold; frame 454 re-render (roll 9) SSIM {v:.3f}')
    try:
        rerender()
    except Exception as e:
        R['M04'] = V('fail', f'check error: {type(e).__name__}: {e} | {traceback.format_exc()[-300:]}')
        if S.get('m09_picture') and 'M09' not in R: R['M09'] = R['M04']
    return R


def postprocess(res, ctx):
    S = ctx.get('_x06', {})
    def gate(ids, why):
        for iid in ids:
            if iid in res and res[iid].get('verdict') != 'error':
                res[iid] = dict(res[iid], verdict='fail', detail=f'gate: {why}; ' + str(res[iid].get('detail') or res[iid].get('reason', '')))
    if res.get('B06', {}).get('verdict') == 'fail': gate(BLEND_DERIVED, 'B06 failed')
    if res.get('G08', {}).get('verdict') == 'fail': gate(['G09', 'G10'], 'G08 failed')
    if not S.get('rev_present') or res.get('B02', {}).get('verdict') != 'pass': gate(['M09', 'M10'], 'revision missing or B02 failed')
    if res.get('B05', {}).get('verdict') != 'pass': gate(EVENT_DERIVED, 'B05 failed')
    # task gate (acceptance flag only; the continuous score is reported unchanged)
    b01 = res.get('B01', {})
    res['_task_gate'] = {'verdict': 'pass' if b01.get('verdict') == 'pass' else 'fail',
                         'detail': 'base/output.mp4 present and decodable (B01)' if b01.get('verdict') == 'pass' else
                         'base/output.mp4 missing, undecodable or off-contract: ' + str(b01.get('detail', ''))[:200]}
    return res
