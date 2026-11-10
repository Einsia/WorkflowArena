# -*- coding: utf-8 -*-
"""CDC-C-X05 deterministic checks (see review/VERIFIER_NOTES.md, review/rubric-cleanup-20261025.md).
Full verdicts from checks: B01-B06, M01-M11, X01-X03, X05, X06, X08.
Fail-only (checks fail the measurable part, otherwise the judge decides the visual/text remainder): M12 (credentials), X07 (rigs/fingers).
Judge only: X09.  Informational (weight 0): X04.
Project measurements come from one read-only Blender pass over film frames 0..899 of project/scene.blend with
rev1_hold_frames = rev2_trim_frames = 0 (base state); film frame i = scene frame frame_start + i; shot k uses CAM_Sk.
postprocess: group gates (S: B03, P: B06, R: rev1/rev2 part of B01)."""
import json, math, re, shutil, traceback
from pathlib import Path
import numpy as np
import cdcc_lib as L

SR = 48000
VERS = {'base': 900, 'rev1': 912, 'rev2': 903}
STEMS = ['studio', 'taxi', 'radio', 'phone']
CUTS = {'base': [180, 360, 540, 720], 'rev1': [180, 372, 552, 732], 'rev2': [180, 372, 552, 723]}
SHOT = {1: (0, 179), 2: (180, 359), 3: (360, 539), 4: (540, 719), 5: (720, 899)}
REQ_OBJ = ['HOST_A', 'HOST_B', 'DRIVER', 'HOST_A_RIG', 'HOST_B_RIG', 'DRIVER_RIG', 'MIC_A', 'MIC_B', 'CONSOLE', 'CALLER_FADER',
           'ON_AIR_LAMP', 'TAXI', 'RADIO', 'RADIO_KNOB', 'PHONE', 'TRAFFIC_LIGHT'] + [f'CAM_S{i}' for i in range(1, 6)]
RIGS = ['HOST_A_RIG', 'HOST_B_RIG', 'DRIVER_RIG']
REQ_EV = ['line1_start', 'line1_end', 'line2_start', 'line2_end', 'line3_start', 'line3_end', 'line4_start', 'line4_end',
          'knob_down_start', 'knob_down_end', 'phone_at_ear', 'caller_fader_down', 'phone_hang_up', 'knob_up_start', 'knob_up_end', 'light_green']
GROUPS = {'S': ['M01', 'M02', 'M03', 'M04', 'M05', 'X01', 'X02', 'X03', 'X04', 'X05'],
          'P': ['M06', 'M07', 'M08', 'M10', 'M11', 'X06', 'X07'], 'R': ['M09', 'X08']}
WORDS_DEFAULT = {1: 10, 2: 14, 3: 13, 4: 8}
V = L.V


# ---------------------------------------------------------------- B03 band-energy stem contract (method of CDC-C-X06 B04)
def band_db(x):
    fr = 4800
    n = len(x) // fr
    if n < 5:
        return None
    X = np.abs(np.fft.rfft(x[:n * fr].reshape(n, fr) * np.hanning(fr), axis=1)) ** 2
    f = np.fft.rfftfreq(fr, 1 / SR)
    cs = [c for c in (1000 * 2 ** (k / 3) for k in range(-13, 12)) if 45 <= c <= 14500]
    B = np.stack([X[:, (f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))].sum(1) for c in cs], 1)
    return 10 * np.log10(B + 1e-20)


def align(ref, x, maxlag=2048):
    n = min(len(ref), len(x), SR * 10)
    a, b = ref[SR:SR + n - SR], x[SR:SR + n - SR]
    if len(a) < 4096:
        return 0
    c = np.fft.irfft(np.fft.rfft(a, 2 * len(a)) * np.conj(np.fft.rfft(b, 2 * len(a))))
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


def _lp4k(x):
    X = np.fft.rfft(x)
    X[np.fft.rfftfreq(len(x), 1 / SR) > 4000] = 0
    return np.fft.irfft(X, len(x))


def fit_gains(mix, mono_stems, lag):
    names = list(mono_stems)
    n = min(len(v) for v in mono_stems.values())
    S0 = np.stack([mono_stems[k][:n] for k in names], 1)
    m, _ = _aligned(mix, S0[:, 0], lag)
    S = S0[-lag:] if lag < 0 else S0
    k = min(len(m), len(S))
    g, *_ = np.linalg.lstsq(np.stack([_lp4k(S[:k, i]) for i in range(len(names))], 1), _lp4k(m[:k]), rcond=None)
    return dict(zip(names, g.tolist()))


def gain_candidates(tl, names):
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


# ---------------------------------------------------------------- audio measurement helpers
def mono(x):
    return x.mean(axis=1) if x.ndim == 2 else x


def benv(x, lo=300, hi=3400, win=0.02, hop=0.01):
    """speech-band RMS envelope (dBFS) of a mono/stereo signal: (t, e)."""
    return L.env_db(L.bandpass(mono(x), lo, hi)[:, None], win, hop)


def tsel(t, a, b):
    return (t >= a) & (t <= b)


def sustained(mask, n):
    """mask of frames that belong to a run of >= n consecutive True."""
    out = np.zeros_like(mask)
    i = 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            if j - i >= n:
                out[i:j] = True
            i = j
        else:
            i += 1
    return out


def corr(a, b):
    n = min(len(a), len(b))
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    da, db = float(np.sqrt((a * a).sum())), float(np.sqrt((b * b).sum()))
    if da < 1e-9 or db < 1e-9:
        return None
    return float((a * b).sum() / (da * db))


def rms_db(x):
    return 10 * math.log10(max(float((x ** 2).mean()) if len(x) else 0.0, 1e-14))


def lag_search(a, b, lag_lo, lag_hi):
    """best normalized correlation of a[n] with b[n+k] for k in [lag_lo, lag_hi] samples."""
    La = len(a)
    nb = La + lag_hi
    if lag_lo < 0 or len(b) < nb:
        raise ValueError('lag_search: segment too short')
    b = b[:nb]
    N = 1 << int(math.ceil(math.log2(La + nb)))
    c = np.fft.irfft(np.conj(np.fft.rfft(a, N)) * np.fft.rfft(b, N), N)[:lag_hi + 1]
    cs = np.concatenate([[0.0], np.cumsum(b * b)])
    eb = np.sqrt(np.maximum(cs[np.arange(lag_hi + 1) + La] - cs[np.arange(lag_hi + 1)], 1e-20))
    r = c / (np.sqrt((a * a).sum()) + 1e-12) / eb
    r[:lag_lo] = -2
    k = int(np.argmax(r))
    return k, float(r[k])


def switch_check(src, dst, cut, quiet_t0, quiet_t1, quiet_thr=-55.0):
    """perspective switch of one line from stem src to stem dst at time cut. returns (problems, details)."""
    bad, det = [], []
    ts, es = L.env_db(L.bandpass(mono(src), 300, 3400)[:, None], 0.01)
    td, ed = L.env_db(L.bandpass(mono(dst), 300, 3400)[:, None], 0.01)
    ps = float(es[tsel(ts, cut - 1.5, cut)].max(initial=-140))
    pd = float(ed[tsel(td, cut, cut + 1.5)].max(initial=-140))
    if ps < -70:
        return [f'no speech on source stem before {cut:.2f} s (peak {ps:.1f} dBFS)'], det
    if pd < -70:
        return [f'no speech on destination stem after {cut:.2f} s (peak {pd:.1f} dBFS)'], det
    a = np.where(tsel(ts, cut - 1.0, cut + 0.5) & (es > ps - 30))[0]
    b = np.where(tsel(td, cut - 0.5, cut + 1.0) & (ed > pd - 30))[0]
    if not len(a) or not len(b):
        bad.append('line not found near the cut on ' + ('source' if not len(a) else 'destination') + ' stem')
        a = b = None
    if a is not None:
        end_s, on_d = float(ts[a[-1]] + 0.005), float(td[b[0]] - 0.005)
        det.append(f'source end {end_s:.3f} s, destination onset {on_d:.3f} s')
        if end_s > cut + 0.05: bad.append(f'source stem still carries the line at {end_s:.3f} s (> cut+0.05)')
        if on_d < cut - 0.05: bad.append(f'destination stem starts at {on_d:.3f} s (< cut-0.05)')
        if on_d - end_s > 0.40: bad.append(f'gap {on_d - end_s:.3f} s > 0.40')
        if end_s - on_d > 0.05: bad.append(f'overlap {end_s - on_d:.3f} s > 0.05')
    q = L.max_db(src, quiet_t0, quiet_t1)
    det.append(f'source {quiet_t0:.2f}-{quiet_t1:.2f} s max {q:.1f} dBFS')
    if q > quiet_thr: bad.append(f'source stem {quiet_t0:.2f}-{quiet_t1:.2f} s at {q:.1f} dBFS > {quiet_thr}')
    return bad, det


def click_check(stems, cut, order=24):
    """click = a transient that a short-term linear predictor (order 24, fitted on the +-60 ms neighbourhood) cannot explain:
    max |prediction residual| within +-10 ms of the cut more than 12 dB above the max residual in the rest of +-60 ms."""
    x = mono(sum(stems[k] for k in STEMS if k in stems))
    i0, W, Cn = int(cut * SR), 2880, 480
    a, b = i0 - W - order, i0 + W
    if a < 0 or b > len(x):
        return False, 'cut too close to the file edge for click analysis'
    seg = x[a:b]
    if float(np.abs(seg).max()) < 1e-4:
        return False, 'silent around the cut'
    M = np.lib.stride_tricks.sliding_window_view(seg, order + 1)[:, ::-1]   # row n: seg[n+order], seg[n+order-1], ...
    y, X = M[:, 0], M[:, 1:]
    pos = np.arange(len(y)) + order + a                                        # absolute sample index of y
    ctr = np.abs(pos - i0) <= Cn
    coef, *_ = np.linalg.lstsq(X[~ctr], y[~ctr], rcond=None)
    e = np.abs(y - X @ coef)
    pc, pn = float(e[ctr].max()), float(e[~ctr].max())
    ratio = 20 * math.log10((pc + 1e-12) / (pn + 1e-12))
    return ratio > 12, f'cut ±10 ms LPC residual peak {pc:.4f} vs neighbourhood {pn:.4f} ({ratio:+.1f} dB)'


def onset_l3(taxi, lo, hi, quiet0, quiet1):
    """driver speech onset on the taxi stem: first sustained (>=50 ms) speech-band activity 15 dB over the cabin floor."""
    t, e = benv(taxi)
    w = tsel(t, lo - 1.0, hi + 6.0)
    if not w.any():
        return None, None, 'stem too short'
    floor = float(np.percentile(e[w], 10))
    peak = float(e[tsel(t, lo, hi + 6.0)].max(initial=-140))
    thr = max(floor + 15, peak - 35)
    act = sustained(e > thr, 5)
    idx = np.where(act & tsel(t, lo, hi))[0]
    on = float(t[idx[0]] - 0.01) if len(idx) else None
    pre = bool((act & tsel(t, quiet0, quiet1)).any())
    return on, pre, f'floor {floor:.1f} dB, threshold {thr:.1f} dB'


def frame_env(x, n0, n1, lo=100, hi=4000):
    """linear RMS per film frame n0..n1 (inclusive) of a band-passed mono stem."""
    y = L.bandpass(mono(x), lo, hi)
    hop = SR // 30
    out = []
    for f in range(n0, n1 + 1):
        s = y[f * hop:(f + 1) * hop]
        out.append(float(np.sqrt((s * s).mean())) if len(s) else 0.0)
    return np.array(out)


def lipsync(P, rig, n0, n1, env):
    """max Pearson r over mouth channels of rig and lags -2..2 frames (|lag| <= 67 ms) vs env (frames n0..n1)."""
    fr = P['frames']
    keys = set()
    for f in range(n0, n1 + 1):
        keys |= set(((fr[f]['rig'].get(rig) or {}).get('mouth') or {}).keys())
    best, which = None, None
    for k in sorted(keys):
        sig = np.array([((fr[f]['rig'].get(rig) or {}).get('mouth') or {}).get(k, 0.0) for f in range(n0, n1 + 1)], float)
        if np.ptp(sig) < 1e-6:
            continue
        for lag in range(-2, 3):
            if lag >= 0:
                r = corr(sig[lag:], env[:len(env) - lag] if lag else env)
            else:
                r = corr(sig[:lag], env[-lag:])
            if r is not None and (best is None or r > best):
                best, which = r, f'{k} lag {lag}'
    return best, which


# ---------------------------------------------------------------- picture / project helpers
def mtrans(m):
    return np.array([m[3], m[7], m[11]])


def mfwd(m):
    return -np.array([m[2], m[6], m[10]])


def qang(q1, q2):
    d = abs(sum(a * b for a, b in zip(q1, q2)))
    return 2 * math.degrees(math.acos(min(1.0, d)))


def inframe(p):
    return p is not None and p[2] > 0 and 0 <= p[0] <= 1 and 0 <= p[1] <= 1


def proj(P, f, name):
    return ((P['frames'][f].get('proj') or {}).get(name))


def ild_rule(ild, x):
    if abs(x - 0.5) >= 0.10:
        return ild * (x - 0.5) > 0 and abs(ild) >= 1.5
    return abs(ild) <= 3.0


def ild_windows(stem, t0, t1, min_len=0.25):
    """per 0.5 s window: (ta, tb, ILD R-L dB in 200-4000 Hz, level dB); windows below peak-30 / -70 dBFS dropped."""
    if t1 - t0 < min_len:
        return []
    l = L.bandpass(stem[:, 0], 200, 4000); r = L.bandpass(stem[:, 1], 200, 4000)
    out, ta = [], t0
    while ta < t1 - 1e-6:
        tb = min(ta + 0.5, t1)
        if tb - ta >= min_len:
            a, b = int(ta * SR), int(tb * SR)
            el, er = rms_db(l[a:b]), rms_db(r[a:b])
            out.append((ta, tb, er - el, max(el, er)))
        ta += 0.5
    if not out:
        return []
    pk = max(w[3] for w in out)
    return [w for w in out if w[3] >= max(-70.0, pk - 30)]


def run(ctx):
    out, tmp = Path(ctx['out']), Path(ctx['tmp'])
    tmp.mkdir(parents=True, exist_ok=True)
    R, S = {}, {}
    ctx['_x05'] = S

    def guard(iid, fn):
        try:
            v = fn()
            if v is not None:
                R[iid] = v
        except Exception as e:
            R[iid] = V('fail', f'check error: {type(e).__name__}: {e} | {traceback.format_exc()[-300:]}')

    vid = {k: L.find(out, f'{k}/output.mp4') for k in VERS}

    # ---- B01 encoding contract
    def b01():
        bad, det = [], []
        for k, n in VERS.items():
            if not vid[k]:
                bad.append(f'{k}: missing'); S[f'{k}_ok'] = False; continue
            ok, d, _ = L.encoding_contract(vid[k], n)
            S[f'{k}_ok'] = ok
            det.append(f'{k}: {d}')
            if not ok: bad.append(k)
        return V('fail' if bad else 'pass', '; '.join(det + (['FAIL ' + ','.join(bad)] if bad else [])))
    guard('B01', b01)

    # ---- B02 master loudness
    mixes = {}
    def b02():
        det, bad = [], False
        for k in VERS:
            if not vid[k]:
                return V('fail', f'{k}/output.mp4 missing')
            I, TP = L.ebur(vid[k])
            x = L.audio(vid[k]); mixes[k] = x
            clip = L.clip_run(x)
            ok = -22.0 <= I <= -18.0 and TP <= -0.9 and not clip
            bad |= not ok
            det.append(f'{k}: I={I} LUFS TP={TP} dBTP clip_run={clip}')
        return V('fail' if bad else 'pass', '; '.join(det))
    guard('B02', b02)

    # ---- B03 stems (band-energy comparison + fitted gains; AAC makes a waveform residual unreachable)
    stems = {}
    def b03():
        det, bad = [], []
        for k, n in VERS.items():
            d = vid[k]
            if not d:
                bad.append(f'{k} missing'); continue
            st = {}
            for s in STEMS:
                p = d.parent / 'stems' / f'{s}.wav'
                if not p.exists():
                    bad.append(f'{k}/stems/{s}.wav missing'); continue
                wi = L.wav_info(p)
                if str(wi.get('sample_rate')) != '48000' or int(wi.get('channels') or 0) != 2 or not str(wi.get('codec_name', '')).startswith('pcm'):
                    bad.append(f'{k}/{s}: {wi.get("codec_name")} {wi.get("sample_rate")} ch{wi.get("channels")}')
                a = L.audio(p)
                if abs(len(a) / SR - n / 30) > 1 / 30 + 1e-4:
                    bad.append(f'{k}/{s}: len {len(a)/SR:.3f}s vs {n/30:.3f}s')
                st[s] = a
            stems[k] = st
            if len(st) < 4:
                continue
            try:
                tl = json.loads((d.parent / 'timeline.json').read_text(encoding='utf-8'))
            except Exception:
                tl = {}; bad.append(f'{k}/timeline.json unreadable')
            mix = mixes.get(k)
            if mix is None:
                mix = L.audio(d); mixes[k] = mix
            mn = {s: mono(v) for s, v in st.items()}
            mm = mono(mix)
            nn = min([len(mm)] + [len(v) for v in mn.values()])
            best = None
            for how, gd in gain_candidates(tl, STEMS):
                c = band_compare(mm[:nn], sum(gd[s] * mn[s][:nn] for s in STEMS))
                if c and (best is None or c['median'] < best[2]['median']):
                    best = (how, gd, c)
            if best is None:
                bad.append(f'{k}: band comparison impossible (silent/short)'); continue
            how, gd, c = best
            if not (c['median'] <= 0.75 and c['p95'] <= 3.0):
                bad.append(f"{k}: band diff median {c['median']:.2f} / p95 {c['p95']:.2f} dB > 0.75 / 3")
            fg = fit_gains(mm[:nn], {s: mn[s][:nn] for s in STEMS}, c['lag'])
            gdiff = {}
            for s in STEMS:
                if fg[s] <= 0 or gd[s] <= 0:
                    gdiff[s] = None; bad.append(f'{k}/{s}: fitted gain {fg[s]:.3f} / declared {gd[s]:.3f} non-positive')
                else:
                    gdiff[s] = round(float(20 * np.log10(gd[s] / fg[s])), 2)
                    if abs(gdiff[s]) > 1.0: bad.append(f'{k}/{s}: declared vs fitted {gdiff[s]:+.2f} dB > 1')
            det.append(f"{k}: band median {c['median']:.2f} p95 {c['p95']:.2f} dB lag {c['lag']} ({how}); declared-fitted dB {gdiff}")
        return V('fail' if bad else 'pass', '; '.join(det + bad))
    guard('B03', b03)

    # ---- B05 events
    ev = {}
    def b05():
        p = L.find(out, 'base/events.csv')
        if not p:
            return V('fail', 'base/events.csv missing')
        header, e, badint = L.read_events(p)
        ev.update({k: v for k, v in e.items() if v is not None})
        prob = []
        if header != 'event_id,frame,description': prob.append(f'header {header!r}')
        miss = [k for k in REQ_EV if k not in ev]
        if miss: prob.append(f'missing {miss}')
        if badint: prob.append(f'non-integer {badint}')
        if prob:
            return V('fail', '; '.join(prob))
        g = ev
        S1, S2, S4, S5 = (0, 179), (180, 359), (540, 719), (720, 899)
        def inn(k, s): return s[0] <= g[k] <= s[1]
        rules = [
            ('all in 0..899', all(0 <= g[k] <= 899 for k in REQ_EV)),
            ('line1 in S1', inn('line1_start', S1) and inn('line1_end', S1)),
            ('line2_start in S1', inn('line2_start', S1)), ('line2_end in S2', inn('line2_end', S2)),
            ('knob_down/phone_at_ear in S2', all(inn(k, S2) for k in ['knob_down_start', 'knob_down_end', 'phone_at_ear'])),
            ('knob_down_end<phone_at_ear<=line3_start', g['knob_down_end'] < g['phone_at_ear'] <= g['line3_start']),
            ('line3_start=342+-2', abs(g['line3_start'] - 342) <= 2),
            ('line3_end, caller_fader_down, line4_start in S4', all(inn(k, S4) for k in ['line3_end', 'caller_fader_down', 'line4_start'])),
            ('line3_end<caller_fader_down<line4_start', g['line3_end'] < g['caller_fader_down'] < g['line4_start']),
            ('S5 events', all(inn(k, S5) for k in ['line4_end', 'phone_hang_up', 'knob_up_start', 'knob_up_end', 'light_green'])),
            ('phone_hang_up<knob_up_start', g['phone_hang_up'] < g['knob_up_start']),
            ('starts<=ends', all(g[f'line{i}_start'] < g[f'line{i}_end'] for i in range(1, 5)) and g['knob_down_start'] <= g['knob_down_end'] and g['knob_up_start'] <= g['knob_up_end']),
        ]
        fails = [n for n, ok in rules if not ok]
        return V('fail' if fails else 'pass', ('violations: ' + '; '.join(fails)) if fails else f'all rules ok {g}')
    guard('B05', b05)
    EVOK = all(0 <= ev.get(k, -1) <= 899 for k in REQ_EV)

    # ---- B06 project + per-frame export
    blend = L.find(out, 'project/scene.blend')
    P = {'d': None, 'err': None}
    has_blender = bool(shutil.which('blender'))

    def b06():
        prob = []
        if not blend: return V('fail', 'project/scene.blend missing')
        rd = L.find(out, 'project/README.md')
        if not rd or not re.search(r'blender\b.*(-b|--background)', rd.read_text(encoding='utf-8', errors='replace'), re.I):
            prob.append('README.md missing or without a blender -b export command')
        for f in ('credits.md', 'qa.md'):
            if not (out / f).exists() and not list(out.rglob(f)):
                prob.append(f'{f} missing')
        if not has_blender:
            return V('error', 'grader image has no blender: cannot inspect project/scene.blend')
        try:
            d = L.blend_inspect(blend, tmp)
        except Exception as e:
            return V('fail', f'{e}; ' + '; '.join(prob))
        miss = [n for n in REQ_OBJ if n not in d['objects']]
        if miss: prob.append(f'missing objects {miss}')
        notarm = [r for r in RIGS if r in d['objects'] and d['objects'][r].get('type') != 'ARMATURE']
        if notarm: prob.append(f'not armatures: {notarm}')
        props = set().union(*[set(v) for v in d['scenes'].values()]) if d['scenes'] else set()
        for k in ('rev1_hold_frames', 'rev2_trim_frames'):
            if k not in props: prob.append(f'scene property {k} missing')
        fv = d.get('file_version') or [0, 0, 0]
        if tuple(fv[:2]) != (4, 3): prob.append(f'file saved with Blender {".".join(map(str, fv))}, not 4.3')
        return V('fail' if prob else 'pass', '; '.join(prob) if prob else f'saved with {".".join(map(str, fv))}; all objects/props present; rigs are armatures')
    guard('B06', b06)

    if blend and has_blender:
        try:
            P['d'] = L.blend_export(blend, tmp, 900)
            if len(P['d'].get('frames', [])) < 900:
                P['err'] = f"export returned {len(P['d'].get('frames', []))} frames"; P['d'] = None
        except Exception as e:
            P['err'] = f'{type(e).__name__}: {e}'
    elif not blend:
        P['err'] = 'project/scene.blend missing'
    else:
        P['err'] = 'NOBLENDER'

    def need_p():
        if P['d'] is not None:
            return P['d'], None
        if P['err'] == 'NOBLENDER':
            return None, V('error', 'grader image has no blender: project measurement impossible')
        return None, V('fail', f'project data unavailable: {P["err"]}')

    def need_ev():
        return None if EVOK else V('fail', 'events.csv missing/incomplete/out of range (B05) - declared frames needed')

    def stem(ver, s):
        st = stems.get(ver) or {}
        if s not in st:
            raise LookupError(f'{ver}/stems/{s}.wav missing')
        return st[s]

    # ---- B04 picture structure (+ freeze cross-check with project animation)
    F = {}
    def b04():
        if not vid['base']:
            return V('fail', 'base missing')
        F['base'] = L.gray_frames(vid['base'])
        cs = L.cut_structure(F['base'], CUTS['base'])
        if cs['missing'] or cs['extra'] or cs['blendlike']:
            return V('fail', f'cut detection {cs}')
        fr = L.freeze_runs(F['base'], 15)
        if not fr:
            return V('pass', f'hard cuts at {cs["cuts"]}; no freeze candidate (>=15 frames PSNR>=55)')
        d, err = need_p()
        if err is not None:
            return V(err['verdict'], f'freeze candidates {fr} and {err["detail"]}')
        frames = d['frames']; bad = []
        for a, b in fr:
            b = min(b, 899)
            if a > 899: continue
            k = [k for k, (s0, s1) in SHOT.items() if s0 <= a <= s1][0]
            cam = f'CAM_S{k}'
            mov = []
            ms = [frames[f]['cams'].get(cam) for f in range(a, b + 1)]
            if all(ms) and (max(float(np.abs(np.array(m['m']) - np.array(ms[0]['m'])).max()) for m in ms) > 1e-4 or
                            max(abs(m['lens'] - ms[0]['lens']) for m in ms) > 1e-4):
                mov.append(cam)
            for r in RIGS:
                vis = any(inframe(proj(d, f, f'HEAD:{r}')) for f in range(a, b + 1))
                motion = sum((frames[f]['rig'].get(r) or {}).get('motion', 0.0) for f in range(a + 1, b + 1))
                mouth = [((frames[f]['rig'].get(r) or {}).get('mouth') or {}) for f in range(a, b + 1)]
                mch = max((abs(m.get(kk, 0) - mouth[0].get(kk, 0)) for m in mouth for kk in m), default=0)
                if vis and (motion > 1e-4 or mch > 1e-4):
                    mov.append(r)
            if not mov:
                bad.append(f'frames {a}-{b} frozen and neither {cam} nor a visible character is animated')
        if bad:
            return V('fail', '; '.join(bad))
        return V('pass', f'hard cuts at {cs["cuts"]}; static-picture runs {fr} have camera/character animation in the project')
    guard('B04', b04)

    # ---- M01 speech timing on the summed stems
    def m01():
        e0 = need_ev()
        if e0: return e0
        st = stems.get('base') or {}
        if len(st) < 4: return V('fail', 'base stems missing')
        t, e = benv(sum(st[s] for s in STEMS))
        floor = float(np.percentile(e, 10))
        bad, det = [], []
        for i in range(1, 5):
            s, en = ev[f'line{i}_start'] / 30, ev[f'line{i}_end'] / 30
            pk = float(e[tsel(t, s, en)].max(initial=-140))
            thr = max(floor + 15, pk - 35)
            act = e > thr
            def any_act(a, b): return bool((act & tsel(t, a, b)).any())
            prev_end = ev[f'line{i-1}_end'] / 30 if i > 1 else -9
            next_st = ev[f'line{i+1}_start'] / 30 if i < 4 else 99
            ok_on = any_act(s - 0.2, s + 0.2) and (prev_end > s - 0.5 or not any_act(s - 0.45, s - 0.2))
            ok_off = any_act(en - 0.2, en + 0.2) and (next_st < en + 0.5 or not any_act(en + 0.2, en + 0.45))
            det.append(f'L{i} {s:.2f}-{en:.2f}s thr {thr:.1f} on {"ok" if ok_on else "BAD"} off {"ok" if ok_off else "BAD"}')
            if not ok_on: bad.append(f'L{i} measured onset not within 6 frames of declared {ev[f"line{i}_start"]}')
            if not ok_off: bad.append(f'L{i} measured offset not within 6 frames of declared {ev[f"line{i}_end"]}')
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('M01', m01)

    # ---- M02 J-cut onset + driver mouth in 342-359
    def m02():
        on, pre, how = onset_l3(stem('base', 'taxi'), 10.9, 12.5, 11.00, 11.35)
        bad = []
        if on is None or abs(on - 11.40) > 0.05: bad.append(f'taxi-stem speech onset {on} s (expected 11.40±0.05)')
        if pre: bad.append('speech activity on taxi stem in 11.00-11.35 s')
        d, err = need_p()
        if err is not None: return V(err['verdict'], '; '.join(bad + [err['detail']]))
        unseen = []
        for f in range(342, 360):
            p = proj(d, f, 'HEAD:DRIVER_RIG')
            rr = d['frames'][f]['rig'].get('DRIVER_RIG') or {}
            cam = d['frames'][f]['cams'].get('CAM_S2')
            away = False
            if rr.get('front') and rr.get('head') and cam:
                h = np.array(rr['head'][:3]); v = mtrans(cam['m']) - h; v[2] = 0
                fv = np.array(rr['front'])
                if np.linalg.norm(v) > 1e-6:
                    away = math.degrees(math.acos(max(-1.0, min(1.0, float(fv @ v) / float(np.linalg.norm(v)))))) > 100
            unseen.append((p is not None and not inframe(p)) or away)
        pic = 'mouth unseen (off-frame/facing away) in all frames' if all(unseen) else None
        if pic is None:
            r, which = lipsync(d, 'DRIVER_RIG', 342, 359, frame_env(stem('base', 'taxi'), 342, 359))
            if r is not None and r >= 0.5:
                pic = f'lip-synced r={r:.2f} ({which})'
            else:
                bad.append(f'DRIVER mouth visible in {sum(not u for u in unseen)}/18 frames of 342-359 and not lip-synced (r={r})')
        return V('fail' if bad else 'pass', '; '.join(bad) + f' | onset {on} ({how}); picture: {pic}')
    guard('M02', m02)

    # ---- M03 / M04 / M05 perspective switches
    def m0345(src, dst, cut, q0, q1, extra=None):
        st = stems.get('base') or {}
        if any(k not in st for k in STEMS): return V('fail', 'base stems missing')
        bad, det = switch_check(st[src], st[dst], cut, q0, q1)
        clk, cd = click_check(st, cut)
        det.append(cd)
        if clk: bad.append('click at the cut (transient > 12 dB above the neighbourhood after linear prediction)')
        if extra: extra(st, bad, det)
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('M03', lambda: m0345('studio', 'radio', 6.0, 6.10, 12.0))
    guard('M04', lambda: m0345('studio', 'radio', 24.0, 24.10, 30.0))

    def m05_extra(st, bad, det):
        q = L.max_db(st['phone'], 0.0, 17.95)
        det.append(f'phone before 17.95 s max {q:.1f} dBFS')
        if q > -50: bad.append(f'phone stem active before 17.95 s ({q:.1f} dBFS)')
        if not EVOK:
            bad.append('line3_end not declared'); return
        t, e = L.env_db(L.bandpass(mono(st['phone']), 300, 3400)[:, None], 0.01)
        pk = float(e[tsel(t, 18.0, 30)].max(initial=-140))
        idx = np.where(tsel(t, 18.0, ev['line3_end'] / 30 + 0.5) & (e > pk - 30))[0]
        last = float(t[idx[-1]]) if len(idx) else None
        det.append(f'phone L3 last activity {last} s vs line3_end {ev["line3_end"] / 30:.2f} s')
        if last is None or last < ev['line3_end'] / 30 - 0.2: bad.append('phone stem does not carry L3 to the declared line3_end')
    guard('M05', lambda: m0345('taxi', 'phone', 18.0, 18.20, 24.0, m05_extra))

    # ---- M06 radio knob causality
    def m06():
        e0 = need_ev()
        if e0: return e0
        d, err = need_p()
        if err is not None: return err
        fr = d['frames']
        if 'knob_rel_q' not in fr[0]: return V('fail', 'RADIO or RADIO_KNOB missing in project')
        q = [f['knob_rel_q'] for f in fr]
        bad, det = [], []
        wins = [(ev['knob_down_start'], ev['knob_down_end'], 'down'), (ev['knob_up_start'], ev['knob_up_end'], 'up')]
        for a, b, nm in wins:
            ang = [qang(q[f], q[a]) for f in range(a, b + 1)]
            mono_ok = all(ang[i + 1] >= ang[i] - 0.5 for i in range(len(ang) - 1))
            det.append(f'{nm}: turn {ang[-1]:.1f} deg monotonic={mono_ok}')
            if ang[-1] < 30 or not mono_ok: bad.append(f'knob {nm} turn {ang[-1]:.1f} deg (need monotonic >=30)')
            dh = [(fr[f]['rig'].get('DRIVER_RIG') or {}).get('d_hand_RADIO_KNOB') for f in range(max(0, a - 2), min(899, a + 2) + 1)]
            dh = [x for x in dh if x is not None]
            dm = min(dh) if dh else None
            det.append(f'{nm}: DRIVER hand-knob {dm} m')
            if dm is None or dm > 0.06: bad.append(f'DRIVER hand not within 6 cm of knob at {nm} start ({dm})')
        (a1, b1, _), (a2, b2, _) = wins
        for s0, s1 in [(0, a1 - 2), (b1 + 2, a2 - 2), (b2 + 2, 899)]:
            if s1 <= s0: continue
            mv = max(qang(q[f], q[s0]) for f in range(s0, s1 + 1))
            if mv > 3: bad.append(f'knob moves {mv:.1f} deg in frames {s0}-{s1} (outside the declared turns)')
        xk = L.kweight_ms(stem('base', 'radio'))
        def stmax(t0, t1):  # max short-term loudness over 400 ms windows ending in [t0, t1] (50 ms steps)
            return max(L.st_loudness(xk, t) for t in np.arange(t0, t1 + 1e-6, 0.05))
        lb, la = stmax(a1 / 30 - 0.5, (a1 - 3) / 30), stmax(b1 / 30 + 0.5, b1 / 30 + 1.0)
        ub, ua = stmax(a2 / 30 - 0.5, (a2 - 3) / 30), stmax(b2 / 30 + 0.5, b2 / 30 + 1.0)
        det.append(f'radio short-term loudness before/after: down {lb:.1f}->{la:.1f}, up {ub:.1f}->{ua:.1f} LUFS')
        if la > lb - 6: bad.append(f'radio stem not >=6 LU lower after knob_down_end ({lb:.1f} -> {la:.1f})')
        if ua < ub + 6: bad.append(f'radio stem not >=6 LU higher after knob_up_end ({ub:.1f} -> {ua:.1f})')
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('M06', m06)

    # ---- M07 phone at ear, fader
    def m07():
        e0 = need_ev()
        if e0: return e0
        bad, det = [], []
        t0 = (ev['caller_fader_down'] + 3) / 30
        q = L.max_db(stem('base', 'phone'), t0, 30.0)
        det.append(f'phone from caller_fader_down+3 max {q:.1f} dBFS')
        if q > -60: bad.append(f'phone stem {q:.1f} dBFS after caller_fader_down+3 (> -60)')
        d, err = need_p()
        if err is not None: return V(err['verdict'], '; '.join(bad + [err['detail']]))
        fr = d['frames']
        rng = range(ev['phone_at_ear'], min(ev['line3_end'], 539) + 1)
        dh = [(fr[f]['rig'].get('DRIVER_RIG') or {}).get('d_head_PHONE') for f in rng]
        dd = [(fr[f]['rig'].get('DRIVER_RIG') or {}).get('d_hand_PHONE') for f in rng]
        if not len(rng) or any(x is None for x in dh + dd):
            bad.append('DRIVER head/hand bones or PHONE not found')
        else:
            det.append(f'phone-head max {max(dh):.3f} m, phone-hand max {max(dd):.3f} m over frames {rng.start}-{rng.stop - 1}')
            if max(dh) > 0.12: bad.append(f'PHONE {max(dh):.3f} m from DRIVER head bone (> 0.12)')
            if max(dd) > 0.06: bad.append(f'PHONE {max(dd):.3f} m from DRIVER hand (> 0.06)')
        cf = ev['caller_fader_down']
        a, b = max(0, cf - 3), min(899, cf + 3)
        if 'CALLER_FADER' not in fr[a]['obj']:
            bad.append('CALLER_FADER missing')
        else:
            mv = float(np.linalg.norm(mtrans(fr[b]['obj']['CALLER_FADER']) - mtrans(fr[a]['obj']['CALLER_FADER'])))
            hb = [(fr[f]['rig'].get('HOST_B_RIG') or {}).get('d_hand_CALLER_FADER') for f in range(a, cf + 1)]
            hb = [x for x in hb if x is not None]
            det.append(f'fader travel {mv * 100:.2f} cm; HOST_B hand-fader {min(hb) if hb else None} m')
            if mv < 0.01: bad.append(f'CALLER_FADER moves {mv * 100:.2f} cm in caller_fader_down±3 (< 1 cm)')
            if not hb or min(hb) > 0.05: bad.append('HOST_B hand not within 5 cm of CALLER_FADER at the pull')
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('M07', m07)

    # ---- M08 camera data
    def m08():
        d, err = need_p()
        if err is not None: return err
        fr = d['frames']; bad, det = [], []
        def series(k):
            c = f'CAM_S{k}'; a, b = SHOT[k]
            s = [fr[f]['cams'].get(c) for f in range(a, b + 1)]
            return None if any(x is None for x in s) else s
        cams = {k: series(k) for k in SHOT}
        miss = [k for k, s in cams.items() if s is None]
        if miss: return V('fail', f'cameras missing: {["CAM_S%d" % k for k in miss]}')
        def lens_const(s): return max(x['lens'] for x in s) - min(x['lens'] for x in s) <= 0.01
        def pos(s): return np.array([mtrans(x['m']) for x in s])
        def travel(s): p = pos(s); return float(np.linalg.norm(p - p[0], axis=1).max())
        def unit(v): return v / (np.linalg.norm(v) + 1e-12)
        s1 = cams[1]
        pitch = [math.degrees(math.asin(max(-1.0, min(1.0, float(unit(mfwd(x['m']))[2]))))) for x in s1]
        det.append(f'S1 pitch {min(pitch):.1f}..{max(pitch):.1f} deg, travel {travel(s1) * 100:.2f} cm, lens {s1[0]["lens"]}')
        if max(abs(p) for p in pitch) > 10: bad.append('S1 not eye level (pitch > 10 deg)')
        if travel(s1) >= 0.01: bad.append('S1 camera moves >= 1 cm')
        if not lens_const(s1) or not 28 <= s1[0]['lens'] <= 70: bad.append('S1 lens not constant 28-70 mm')
        ker = np.ones(15) / 15
        def smooth(a): return np.stack([np.convolve(np.pad(a[:, i], 7, mode='edge'), ker, 'valid') for i in range(a.shape[1])], 1)
        for k in (2, 5):
            s = cams[k]; p = pos(s)
            res = p - smooth(p)
            amp = float(np.linalg.norm(res, axis=1).max()) * 1000
            fw = np.array([unit(mfwd(x['m'])) for x in s]); fsm = smooth(fw)
            fsm = fsm / (np.linalg.norm(fsm, axis=1, keepdims=True) + 1e-12)
            rot = float(np.degrees(np.arccos(np.clip((fw * fsm).sum(1), -1, 1))).max())
            sig = res if amp >= 1 else fw - fsm
            ser = sig[:, int(np.argmax(sig.std(0)))]
            z = ser - ser.mean()
            ac = np.correlate(z, z, 'full')[len(z) - 1:]
            ac = ac / ac[0] if ac[0] > 0 else np.zeros_like(ac)
            neg = np.where(ac[:61] < 0)[0]          # periodic = the autocorrelation comes back up after its first zero crossing
            share = float(ac[neg[0]:61].max()) if len(neg) else 0.0
            lens = [x['lens'] for x in s]
            shake = (1 <= amp <= 60) or (amp < 1 and 0.05 <= rot <= 3)
            det.append(f'S{k} shake {amp:.1f} mm / {rot:.2f} deg, autocorr return peak (<=60 f) {share:.2f}, lens {min(lens)}-{max(lens)}')
            if not shake: bad.append(f'S{k} no handheld shake (pos residual {amp:.1f} mm, rot {rot:.2f} deg)')
            elif share >= 0.6: bad.append(f'S{k} shake is periodic (autocorrelation returns to {share:.2f} >= 0.6 within 60 frames)')
            if not (24 <= min(lens) and max(lens) <= 70): bad.append(f'S{k} lens outside 24-70 mm')
        for k in (3, 4):
            s = cams[k]
            if not lens_const(s): bad.append(f'S{k} lens changes')
            if not all(x['dof'] and x['fstop'] <= 4 for x in s): bad.append(f'S{k} depth of field off or f-stop > 4')
        det.append(f'S3 travel {travel(cams[3]) * 100:.2f} cm')
        if travel(cams[3]) >= 0.01: bad.append('S3 camera moves >= 1 cm')
        h0 = (fr[540]['rig'].get('HOST_B_RIG') or {}).get('head'); h1 = (fr[719]['rig'].get('HOST_B_RIG') or {}).get('head')
        if not h0 or not h1:
            bad.append('HOST_B head bone not found for S4 dolly')
        else:
            d0 = float(np.linalg.norm(np.array(h0[:3]) - mtrans(cams[4][0]['m'])))
            d1 = float(np.linalg.norm(np.array(h1[:3]) - mtrans(cams[4][-1]['m'])))
            det.append(f'S4 camera-HOST_B head {d0:.3f} -> {d1:.3f} m')
            if d0 - d1 < 0.08: bad.append(f'S4 dolly-in toward HOST_B {d0 - d1:.3f} m (< 0.08)')
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('M08', m08)

    # ---- M09 rev1
    def m09():
        if not vid['rev1'] or 'base' not in F:
            return V('fail', 'rev1 or base missing')
        F['rev1'] = L.gray_frames(vid['rev1'])
        A, B = F['base'], F['rev1']
        bad, det = [], []
        if len(B) != 912: bad.append(f'rev1 frames {len(B)}')
        p1 = [round(L.psnr(A[i], B[i]), 1) for i in range(0, 342, 19) if i < len(A) and i < len(B)]
        p2 = [round(L.psnr(A[i], B[i + 12]), 1) for i in (360, 450, 630, 810) if i + 12 < len(B) and i < len(A)]
        if min(p1, default=0) < 30: bad.append(f'0-341 PSNR min {min(p1, default=0)}')
        if min(p2, default=0) < 30: bad.append(f'shifted PSNR {p2}')
        cs = L.cut_structure(B, CUTS['rev1'])
        if 372 in cs['missing']: bad.append(f'no cut at 372: {cs["cuts"]}')
        b0, b1 = stems.get('base') or {}, stems.get('rev1') or {}
        if any(s not in b0 or s not in b1 for s in STEMS):
            bad.append('base/rev1 stems missing')
        else:
            for s in STEMS:
                n = int(11.38 * SR)
                x0, x1 = mono(b0[s])[:n], mono(b1[s])[:n]
                if not (rms_db(x0) < -80 and rms_db(x1) < -80):
                    c = corr(x0, x1)
                    if c is None or c < 0.99: bad.append(f'{s}: before 11.38 s corr {c} < 0.99')
                a = L.bandpass(mono(b0[s]), 200, 4000)[int(12.4 * SR):int(29.5 * SR)]
                if rms_db(a) < -60: continue
                bb = L.bandpass(mono(b1[s]), 200, 4000)[int(12.35 * SR):]
                k, r = lag_search(a, bb, 0, int(0.65 * SR))
                lag = k / SR - 0.05
                det.append(f'{s} lag {lag:.4f} s r {r:.2f}')
                if abs(lag - 0.400) > 0.010 or r < 0.5: bad.append(f'{s}: after 12.4 s lag {lag:.3f} s (r {r:.2f}), expected +0.400±0.010')
            on, _, how = onset_l3(b1['taxi'], 11.3, 12.9, 11.40, 11.75)
            det.append(f'rev1 L3 onset {on}')
            if on is None or abs(on - 11.80) > 0.05: bad.append(f'rev1 L3 onset {on} s (expected 11.80±0.05)')
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('M09', m09)

    # ---- M10 re-render from the project
    def m10():
        if not blend: return V('fail', 'project/scene.blend missing')
        if not has_blender: return V('error', 'grader image has no blender')
        if not vid['base']: return V('fail', 'base missing')
        frames = [90, 270, 450, 630, 810]
        got, log = L.blend_render(blend, tmp, frames)
        if not got: return V('fail', f'project did not render: {log[-300:]}')
        ss = {}
        for f in frames:
            if f not in got:
                ss[f] = None; continue
            a = L.blur3(L.read_png_gray(got[f], 320, 180)); b = L.blur3(L.frame_gray(vid['base'], f, 320, 180))
            ss[f] = round(L.ssim(a, b), 3)
        okn = sum(1 for v in ss.values() if v is not None and v >= 0.75)
        return V('pass' if okn >= 4 else 'fail', f'SSIM (320x180 grey, 3x3 blur) per frame {ss}; {okn}/5 >= 0.75 (need 4)')
    guard('M10', m10)

    # ---- M11 identity and prop states
    def m11():
        e0 = need_ev()
        if e0: return e0
        d, err = need_p()
        if err is not None: return err
        fr = d['frames']; bad, det = [], []
        roots = [np.array(fr[f]['rig']['HOST_B_RIG']['root']) for f in list(range(0, 180)) + list(range(540, 720)) if 'HOST_B_RIG' in fr[f]['rig']]
        if not roots: bad.append('HOST_B_RIG missing')
        else:
            dev = float(max(np.linalg.norm(r - roots[0]) for r in roots))
            det.append(f'HOST_B seat drift {dev:.3f} m')
            if dev > 0.15: bad.append(f'HOST_B moves {dev:.2f} m between/within S1 and S4')
        lamp_in = sum(inframe(proj(d, f, 'ON_AIR_LAMP')) for f in range(0, 180))
        lit = [sum(fr[f]['lamp_emis']) for f in range(0, 180) if 'lamp_emis' in fr[f]]
        det.append(f'ON AIR lamp in frame {lamp_in}/180, emissive {sum(1 for x in lit if x > 0)}/{len(lit)}')
        if lamp_in < 162: bad.append('ON_AIR_LAMP not in CAM_S1 frame for >=90% of S1')
        if not lit or sum(1 for x in lit if x > 0) < 0.9 * len(lit): bad.append('ON_AIR_LAMP not self-emissive in S1')
        for k in (2, 5):
            a, b = SHOT[k]
            n = sum(inframe(proj(d, f, 'RADIO')) for f in range(a, b + 1))
            det.append(f'RADIO in CAM_S{k} {n}/180')
            if n < 135: bad.append(f'RADIO in frame in only {n}/180 frames of S{k}')
        g = ev['light_green']
        red = list(range(720, g)); grn = list(range(min(g + 3, 899), 900))
        def st(f):
            r, gg, _ = fr[f]['tl_emis']
            return 'R' if r > gg and r > 0 else ('G' if gg > r and gg > 0 else '?')
        okr = sum(st(f) == 'R' for f in red); okg = sum(st(f) == 'G' for f in grn)
        how = 'material/light emission'
        if not (okr >= 0.9 * len(red) and okg >= 0.9 * len(grn)) and vid['base']:
            px = L.rgb_frames(vid['base'], 320, 180, 720, 180)
            def pst(f):
                if f - 720 >= len(px): return '?'
                im = px[f - 720].astype(int); vals = []
                for n_, p in (fr[f].get('proj') or {}).items():
                    if (n_ == 'TRAFFIC_LIGHT' or n_.startswith('TL:')) and inframe(p):
                        x, y = int(p[0] * 319), int((1 - p[1]) * 179)
                        box = im[max(0, y - 4):y + 5, max(0, x - 4):x + 5].reshape(-1, 3)
                        top = box[np.argsort(box.sum(1))[-10:]]
                        vals.append(float((top[:, 0] - top[:, 1]).mean()))
                if not vals: return '?'
                v = max(vals, key=abs)
                return 'R' if v > 20 else ('G' if v < -20 else '?')
            okr2 = sum(pst(f) == 'R' for f in red); okg2 = sum(pst(f) == 'G' for f in grn)
            if okr2 + okg2 > okr + okg:
                okr, okg, how = okr2, okg2, 'rendered pixels at the projected light'
        det.append(f'traffic light red {okr}/{len(red)} before, green {okg}/{len(grn)} from +3 ({how})')
        if okr < 0.9 * len(red) or okg < 0.9 * len(grn): bad.append('TRAFFIC_LIGHT not red before / green from light_green+3')
        if 'TAXI' not in fr[0]['obj']: bad.append('TAXI missing')
        else:
            p = {f: mtrans(fr[f]['obj']['TAXI']) for f in range(720, 900)}
            pre = max(float(np.linalg.norm(p[f] - p[720])) for f in range(720, g + 1))
            mv = [f for f in range(g, 900) if np.linalg.norm(p[f] - p[g]) > 0.01]
            det.append(f'TAXI drift before green {pre:.3f} m, starts moving at {mv[0] if mv else None}')
            if pre > 0.01: bad.append('TAXI moves before light_green')
            if not mv or mv[0] > g + 30: bad.append('TAXI does not start moving within 1 s of light_green')
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('M11', m11)

    # ---- M12 credentials (fail-only; credits/qa/timeline content is judged from the text files)
    def m12():
        pat = re.compile(r'sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY|'
                         r'(api[_-]?key|secret|password|token)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{12,}', re.I)
        hits = []
        for p in out.rglob('*'):
            if p.is_file() and p.suffix.lower() in ('.md', '.txt', '.json', '.csv', '.py', '.sh', '.yaml', '.yml', '.toml', '.cfg', '.ini', '.env') \
                    and p.stat().st_size < 2_000_000:
                m = pat.search(p.read_text(encoding='utf-8', errors='replace'))
                if m: hits.append(f'{p.relative_to(out)}: {m.group(0)[:12]}...')
        return V('fail', f'credential-like strings: {hits[:5]}') if hits else None
    guard('M12', m12)

    # ---- X01 phone-line timbre (unchanged)
    def x01():
        st = stems.get('base') or {}
        if 'phone' not in st or 'radio' not in st:
            return V('fail', 'base phone/radio stems missing')
        ph = st['phone'].mean(axis=1); ra = st['radio'].mean(axis=1)
        t1 = (ev.get('line3_end', 630) + 1) / 30
        seg = ph[int(18.0 * 48000):int(t1 * 48000)]
        if len(seg) < 4800 or L.max_db(st['phone'], 18.0, t1) < -60:
            seg = ph[int(12.0 * 48000):int(t1 * 48000)]
        B = [(20, 200), (300, 3400), (5000, 20000), (3400, 8000), (80, 20000)]
        e = L.band_energy(seg, 48000, B)
        lo = L.db(e[(300, 3400)]) - L.db(e[(20, 200)]); hi = L.db(e[(300, 3400)]) - L.db(e[(5000, 20000)])
        rsegs = []
        a2 = ev.get('line2_end', 300); a4 = ev.get('line4_end', 880)
        rsegs.append(ra[int(6.0 * 48000):int((a2 + 1) / 30 * 48000)])
        rsegs.append(ra[int(24.0 * 48000):int((a4 + 1) / 30 * 48000)])
        rs = np.concatenate([s for s in rsegs if len(s) > 4096])
        er = L.band_energy(rs, 48000, B)
        rel_r = L.db(er[(3400, 8000)]) - L.db(er[(80, 20000)]); rel_p = L.db(e[(3400, 8000)]) - L.db(e[(80, 20000)])
        ok = lo >= 15 and hi >= 15 and rel_r - rel_p >= 6
        return V('pass' if ok else 'fail', f'phone: 300-3400 vs <200 = {lo:.1f} dB, vs >5k = {hi:.1f} dB; radio-phone rel 3.4-8k = {rel_r - rel_p:.1f} dB')
    guard('X01', x01)

    def win_proj(d, a, b, name, shot):
        s0, s1 = SHOT[shot]
        ps = [proj(d, f, name) for f in range(max(s0, int(a * 30)), min(int(math.ceil(b * 30)) - 1, s1) + 1)]
        return [p for p in ps if p is not None and p[2] > 0]

    def ild_eval(d, stm, t0, t1, name, label, shot):
        res = []
        for ta, tb, ild, lv in ild_windows(stm, t0, t1):
            ps = win_proj(d, ta, tb, name, shot)
            if not ps: continue
            res.append(ild_rule(ild, float(np.mean([p[0] for p in ps]))))
        if not res:
            return False, f'{label}: no evaluable window'
        return sum(res) / len(res) >= 0.8, f'{label}: {sum(res)}/{len(res)} windows agree'

    # ---- X02 on-screen radio placement
    def x02():
        d, err = need_p()
        if err is not None: return err
        ra = stem('base', 'radio')
        ok2, d2 = ild_eval(d, ra, 6.0, 12.0, 'RADIO', 'S2', 2)
        ok5, d5 = ild_eval(d, ra, 24.0, 30.0, 'RADIO', 'S5', 5)
        return V('pass' if ok2 and ok5 else 'fail', f'{d2}; {d5} (ILD R-L 200-4000 Hz vs RADIO screen x; >=80% needed)')
    guard('X02', x02)

    # ---- X03 speaker placement
    def x03():
        e0 = need_ev()
        if e0: return e0
        d, err = need_p()
        if err is not None: return err
        sto, tx = stem('base', 'studio'), stem('base', 'taxi')
        res = [ild_eval(d, sto, ev['line1_start'] / 30, min(ev['line1_end'] / 30, 6.0), 'HEAD:HOST_A_RIG', 'S1 L1/HOST_A', 1),
               ild_eval(d, sto, ev['line2_start'] / 30, 6.0, 'HEAD:HOST_B_RIG', 'S1 L2/HOST_B', 1),
               ild_eval(d, tx, 12.0, min(ev['line3_end'] / 30, 18.0), 'HEAD:DRIVER_RIG', 'S3 L3/DRIVER', 3)]
        f0 = ev['line4_start']
        offn = sum(1 for f in range(f0, 720) if not inframe(proj(d, f, 'HEAD:HOST_A_RIG')))
        tot = max(1, 720 - f0)
        agree = []
        for ta, tb, ild, lv in ild_windows(sto, f0 / 30, 24.0):
            ps = [proj(d, f, 'HEAD:HOST_A_RIG') for f in range(max(540, int(ta * 30)), min(int(math.ceil(tb * 30)) - 1, 719) + 1)]
            ps = [p for p in ps if p is not None]
            if not ps: continue
            xs = float(np.mean([p[3] for p in ps])); zs = float(np.mean([p[5] for p in ps]))
            az = math.degrees(math.atan2(xs, -zs))
            agree.append(abs(ild) >= 1.5 and (abs(az) <= 10 or ild * xs > 0))
        ok4 = offn >= 0.9 * tot and bool(agree) and sum(agree) / len(agree) >= 0.8
        res.append((ok4, f'S4 L4/HOST_A off-frame {offn}/{tot}, {sum(agree)}/{len(agree)} windows point to HOST_A side'))
        return V('pass' if all(r[0] for r in res) else 'fail', '; '.join(r[1] for r in res))
    guard('X03', x03)

    # ---- X04 informational (weight 0): not returned

    # ---- X05 voices: f0 variation and articulation rate
    def x05():
        e0 = need_ev()
        if e0: return e0
        st = stems.get('base') or {}
        if len(st) < 4: return V('fail', 'base stems missing')
        words = dict(WORDS_DEFAULT)
        try:
            tp = Path(str(ctx.get('input') or '')) / 'transcript.en.txt'
            if not tp.exists(): tp = Path(ctx['tests']) / 'public_input' / 'transcript.en.txt'
            for ln in tp.read_text(encoding='utf-8').splitlines():
                m = re.match(r'\s*L(\d)\s+[A-Z_]+:\s*(.*)', ln)
                if m: words[int(m.group(1))] = len(re.findall(r"[A-Za-z0-9']+", m.group(2)))
        except Exception:
            pass
        x = mono(sum(st[s] for s in STEMS))
        t, e = benv(x)
        floor = float(np.percentile(e, 10))
        y = L.bandpass(x, 60, 1000)
        bad, det = [], []
        for i in range(1, 5):
            s, en = ev[f'line{i}_start'] / 30, ev[f'line{i}_end'] / 30
            w = tsel(t, s - 0.1, en + 0.1)
            pk = float(e[w].max(initial=-140)); thr = max(floor + 15, pk - 35)
            idx = np.where((e > thr) & w)[0]
            dur = 0.0
            if len(idx):
                gaps = np.diff(t[idx])
                dur = 0.01 + float(sum(g for g in gaps if g < 0.20)) + 0.01 * sum(1 for g in gaps if g >= 0.20)
            rate = words[i] / dur if dur > 0 else 0.0
            f0s = []
            lo, hi = SR // 400, SR // 60
            for tc in t[idx]:
                a = int((tc - 0.02) * SR); seg = y[max(0, a):a + 1920]
                if len(seg) < 1920: continue
                seg = seg - seg.mean()
                ac = np.fft.irfft(np.abs(np.fft.rfft(seg, 4096)) ** 2)[:1920]
                if ac[0] <= 0: continue
                ac = ac / ac[0]
                k = lo + int(np.argmax(ac[lo:hi]))
                if ac[k] >= 0.5:
                    f0s.append(SR / k)
            if len(f0s) < 20:
                bad.append(f'L{i}: only {len(f0s)} voiced frames'); det.append(f'L{i} rate {rate:.2f} w/s'); continue
            stn = 12 * np.log2(np.array(f0s) / np.median(f0s))
            stn = stn[np.abs(stn) <= 12]
            sd = float(stn.std())
            det.append(f'L{i}: {words[i]} words / {dur:.2f} s active = {rate:.2f} w/s; f0 median {np.median(f0s):.0f} Hz SD {sd:.2f} st')
            if sd < 1.5: bad.append(f'L{i} f0 SD {sd:.2f} st < 1.5')
            if not 1.8 <= rate <= 4.5: bad.append(f'L{i} articulation rate {rate:.2f} w/s outside 1.8-4.5')
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('X05', x05)

    # ---- X06 lip sync
    def x06():
        e0 = need_ev()
        if e0: return e0
        d, err = need_p()
        if err is not None: return err
        sto, tx, ph = stem('base', 'studio'), stem('base', 'taxi'), stem('base', 'phone')
        bad, det = [], []
        def spk(rig, n0, n1, st, label, need_vis=False):
            if n1 - n0 < 10: det.append(f'{label}: skipped (<10 frames)'); return
            if need_vis:
                vis = [f for f in range(n0, n1 + 1) if inframe(proj(d, f, f'HEAD:{rig}'))]
                if len(vis) < 10: det.append(f'{label}: not in vision, skipped'); return
                n0, n1 = vis[0], vis[-1]
            r, w = lipsync(d, rig, n0, n1, frame_env(st, n0, n1))
            det.append(f'{label}: r={None if r is None else round(r, 2)} ({w})')
            if r is None or r < 0.5: bad.append(f'{label} lip sync r={r} < 0.5')
        def non(rig, n0, n1, env, label):
            r, w = lipsync(d, rig, n0, n1, env)
            det.append(f'{label}: r={None if r is None else round(r, 2)} ({w})')
            if r is not None and r >= 0.3: bad.append(f'{label} non-speaker mouths with the speech (r={r:.2f} >= 0.3)')
        a1, b1 = ev['line1_start'], min(ev['line1_end'], 179)
        spk('HOST_A_RIG', a1, b1, sto, 'HOST_A L1 (S1)')
        spk('HOST_B_RIG', ev['line2_start'], 179, sto, 'HOST_B L2 in S1', need_vis=True)
        spk('DRIVER_RIG', 360, min(ev['line3_end'], 539), tx, 'DRIVER L3 (S3)')
        non('HOST_B_RIG', a1, b1, frame_env(sto, a1, b1), 'HOST_B during L1')
        non('HOST_B_RIG', 540, 719, frame_env(sto, 540, 719) + frame_env(ph, 540, 719), 'HOST_B in S4')
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('X06', x06)

    # ---- X07 rigs and fingers (fail-only; photoreal look is judged from the contact sheets)
    def x07():
        d, err = need_p()
        if err is not None: return err
        bad = []
        rg = d.get('rigs') or {}
        for r in RIGS:
            ri = rg.get(r)
            if not ri: bad.append(f'{r} missing or not an armature'); continue
            if not (d.get('deformed') or {}).get(r): bad.append(f'{r} deforms no mesh (no Armature modifier)')
            fc = ri.get('finger_chains', {})
            if fc.get('L', 0) < 4 or fc.get('R', 0) < 4: bad.append(f'{r} finger chains (>=3 bones) per hand {fc} (< 4)')
        fr = d.get('finger_range') or {}
        for r in ('DRIVER_RIG', 'HOST_B_RIG'):
            mx = max([v for k, v in fr.items() if k.startswith(r + ':')], default=0)
            if mx < 5: bad.append(f'{r} fingers not animated (max finger rotation range {mx:.1f} deg)')
        return V('fail', '; '.join(bad)) if bad else None
    guard('X07', x07)

    # ---- X08 rev2
    def x08():
        if not vid['rev2'] or 'rev1' not in F:
            return V('fail', 'rev2 or rev1 missing')
        C = L.gray_frames(vid['rev2']); B = F['rev1']
        bad, det = [], []
        if len(C) != 903: bad.append(f'rev2 frames {len(C)}')
        p1 = [round(L.psnr(B[i], C[i]), 1) for i in range(0, 723, 37) if i < len(C)]
        p2 = [round(L.psnr(B[i + 9], C[i]), 1) for i in (723, 780, 840, 900) if i < len(C) and i + 9 < len(B)]
        if min(p1, default=0) < 30: bad.append(f'0-722 PSNR min {min(p1, default=0)}')
        if min(p2, default=0) < 30: bad.append(f'S5 shift PSNR {p2}')
        cs = L.cut_structure(C, CUTS['rev2'])
        if 723 in cs['missing']: bad.append(f'no cut at 723: {cs["cuts"]}')
        if not EVOK:
            bad.append('events.csv incomplete: rev2 L4 start unknown')
            return V('fail', '; '.join(bad))
        r1, r2 = stems.get('rev1') or {}, stems.get('rev2') or {}
        if any(s not in r1 or s not in r2 for s in STEMS):
            bad.append('rev1/rev2 stems missing'); return V('fail', '; '.join(bad))
        t4 = (ev['line4_start'] + 3) / 30
        for s in STEMS:
            n = int((t4 - 0.02) * SR)
            x1, x2 = mono(r1[s])[:n], mono(r2[s])[:n]
            if not (rms_db(x1) < -80 and rms_db(x2) < -80):
                c = corr(x1, x2)
                if c is None or c < 0.99: bad.append(f'{s}: before rev2 L4 ({t4:.2f} s) corr {c} < 0.99')
            a = L.bandpass(mono(r2[s]), 200, 4000)[int((t4 + 0.1) * SR):int(29.6 * SR)]
            if rms_db(a) < -60: continue
            bb = L.bandpass(mono(r1[s]), 200, 4000)[int((t4 + 0.05) * SR):]
            k, r = lag_search(a, bb, 0, int(0.45 * SR))
            lag = k / SR - 0.05
            det.append(f'{s} rev2 earlier by {lag:.4f} s r {r:.2f}')
            if abs(lag - 0.300) > 0.010 or r < 0.5: bad.append(f'{s}: from L4 on rev2 is earlier by {lag:.3f} s (r {r:.2f}), expected 0.300±0.010')
        sb, sd = switch_check(r2['studio'], r2['radio'], 24.10, 24.20, len(r2['studio']) / SR)
        bad += [f'T45 switch: {x}' for x in sb]; det += sd
        q0 = (ev['caller_fader_down'] + 12 + 3) / 30
        q = L.max_db(r2['phone'], q0, t4)
        det.append(f'rev2 phone {q0:.2f}-{t4:.2f} s max {q:.1f} dBFS')
        if q > -60: bad.append(f'rev2 phone line not closed before L4 ({q:.1f} dBFS > -60)')
        tp, ep = L.env_db(L.bandpass(mono(r2['phone']), 300, 3400)[:, None], 0.01)
        ts_, es_ = L.env_db(L.bandpass(mono(r2['studio']), 300, 3400)[:, None], 0.01)
        pp = float(ep.max(initial=-140)); ps = float(es_[tsel(ts_, t4 - 0.5, 24.1)].max(initial=-140))
        ip = np.where(ep > pp - 30)[0]; is_ = np.where(tsel(ts_, t4 - 0.5, 24.1) & (es_ > ps - 30))[0]
        if len(ip) and len(is_):
            lastp, on4 = float(tp[ip[-1]]), float(ts_[is_[0]])
            det.append(f'rev2 L3 (phone) ends {lastp:.2f} s, L4 starts {on4:.2f} s')
            if lastp >= on4: bad.append('rev2: L3 on the phone overlaps L4')
        return V('fail' if bad else 'pass', '; '.join(bad + det))
    guard('X08', x08)
    return R


def postprocess(res, ctx):
    S = ctx.get('_x05', {})
    gates = {'S': res.get('B03', {}).get('verdict') == 'pass',
             'P': res.get('B06', {}).get('verdict') == 'pass',
             'R': bool(S.get('rev1_ok')) and bool(S.get('rev2_ok'))}
    if 'rev1_ok' not in S:  # B01 errored -> fall back to B01 verdict
        gates['R'] = res.get('B01', {}).get('verdict') == 'pass'
    for g, ok in gates.items():
        if ok: continue
        for iid in GROUPS[g]:
            if iid in res and res[iid].get('verdict') not in ('na', 'error'):
                res[iid] = dict(res[iid], verdict='fail', detail=f'group gate {g} failed; ' + str(res[iid].get('detail') or res[iid].get('reason', '')))
    # task gate (reported in aux only; the continuous score is unchanged)
    res['_task_gate'] = {'verdict': 'pass' if S.get('base_ok') else 'fail',
                         'detail': 'acceptance gate: base/output.mp4 present and meets the encoding contract'}
    return res
