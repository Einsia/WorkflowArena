# -*- coding: utf-8 -*-
"""CDC-C-X08 deterministic checks (see review/VERIFIER_NOTES.md and review/rubric-cleanup-20261025.md).
All items except B08 (credits completeness), X06 (photoreal look), X08 (narrative legibility) and M18 (truthful QA) are
decided here; those four go to the LLM judge (text files + contact sheets) only after their deterministic floors pass.
Project measurements come from ONE forward pass of tests/x08_probe_bpy.py inside Blender (blender -b); the project may be
saved with revision_insert_frames 0 or 30 (the probe maps base frames to scene frames)."""
import json, math, os, pathlib, re, shutil, traceback
import numpy as np
import cxlib as L

FPS = 30
STEMS = ('speech', 'lane', 'gate')
SHOTS = {'base': {'S1': (0, 149), 'S2': (150, 299), 'S3': (300, 449), 'S4': (450, 599), 'S5': (600, 719), 'S6': (720, 899)},
         'revision': {'S1': (0, 149), 'S2': (150, 299), 'S3': (300, 449), 'S4': (450, 599), 'S5': (600, 749), 'S6': (750, 929)}}
EV_SHOT = {'tray_push': 'S1', 'bag_enter_tunnel': 'S1', 'pass_scan': 'S2', 'flaps_open': 'S2', 'passenger_through': 'S2',
           'stop_press': 'S3', 'belt_stop': 'S3', 'tray_bump': 'S3', 'line_screener_start': 'S3', 'line_screener_end': 'S3',
           'officer_halt': 'S4', 'line_officer_start': 'S4', 'line_officer_end': 'S4', 'passenger_stop': 'S4',
           'bag_grip': 'S5', 'bag_place': 'S5', 'passenger_arrive': 'S6'}
NAMES = ['PASSENGER', 'SCREENER', 'OFFICER', 'PASSENGER_RIG', 'SCREENER_RIG', 'OFFICER_RIG', 'BAG', 'TRAY_A', 'TRAY_B', 'CONVEYOR',
         'XRAY_TUNNEL', 'MONITOR', 'BELT_STOP_BUTTON', 'RADIO_HANDSET', 'SEARCH_TABLE', 'TURNSTILE_GATE2', 'BOARDING_PASS', 'PARTITION']
CAMS = ['CAM_S1', 'CAM_S2', 'CAM_S3', 'CAM_S4', 'CAM_S5', 'CAM_S6A', 'CAM_S6B']
RIGS = {'PASSENGER_RIG': 'PASSENGER', 'SCREENER_RIG': 'SCREENER', 'OFFICER_RIG': 'OFFICER'}
CHAR_RIG = {v: k for k, v in RIGS.items()}
PRJ_DEP = ['M09', 'M10', 'M11', 'M12', 'M13', 'M14', 'M15', 'M16', 'M17', 'X01', 'X02', 'X03', 'X04', 'X05', 'X06', 'X07', 'X09']
LAYOUT = {'CONVEYOR': (9.8, 3.0), 'XRAY_TUNNEL': (9.6, 3.0), 'SEARCH_TABLE': (11.6, 6.0), 'TURNSTILE_GATE2': (3.4, 3.0),
          'MONITOR': (9.6, 1.9)}
DOORS = ((0.6, 1.8), (6.2, 7.4))
WALL_X = 6.0
WORDS = {'screener': 9, 'officer': 4}
PROBE_TIMEOUT = 2400
RENDER_TIMEOUT = 1800
RERENDER_FRAMES = (75, 225, 375, 525, 660, 780, 860)


class GraderEnvError(RuntimeError):
    """grader environment problem (not a submission problem): must surface as _checks_error, never as a fail."""


def run(ctx):
    out, tmp = pathlib.Path(ctx['out']), pathlib.Path(ctx['tmp'])
    tmp.mkdir(parents=True, exist_ok=True)
    R, S = {}, {}
    ctx['_x08'] = S

    def guard(ids, fn):
        try:
            fn()
        except GraderEnvError:
            raise
        except Exception as e:
            for i in ids:
                R.setdefault(i, L.F(f'check error: {type(e).__name__}: {e} | {traceback.format_exc()[-300:]}'))

    vid = {v: out / v / 'output.mp4' for v in ('base', 'revision')}
    have = {v: p.exists() for v, p in vid.items()}
    EV = None
    try: EV = L.read_events(out / 'base' / 'events.csv')
    except Exception: pass
    def ev(k):
        try: return EV[1][k]
        except Exception: return None

    def b01():
        if not have['base']: R['B01'] = L.F('base/output.mp4 missing'); return
        ok, d = L.video_contract(vid['base'], FPS, 900, min_audio=29.97); R['B01'] = L.pv(None, ok, d)
    guard(['B01'], b01)

    def b02():
        if not have['revision']: R['B02'] = L.F('revision/output.mp4 missing'); return
        ok, d = L.video_contract(vid['revision'], FPS, 930, min_audio=30.97)
        for s in STEMS:
            p = out / 'revision' / 'stems' / f'{s}.wav'
            try:
                du = L.wav_info(p)['dur']
                if abs(du - 31.0) > 0.01: ok = False; d[f'{s}_dur'] = du
            except Exception:
                ok = False; d[f'{s}'] = 'missing/unreadable'
        R['B02'] = L.pv(None, ok, d)
    guard(['B02'], b02)

    def b03():
        ds, ok = {}, True
        for v in ('base', 'revision'):
            if not have[v]: ok = False; ds[v] = 'missing'; continue
            o, d = L.master_check(vid[v], clip_run=1); ok &= o; ds[v] = d
        R['B03'] = L.pv(None, ok, ds)
    guard(['B03'], b03)

    def b04():
        bad = []; sp = {s: out / 'base' / 'stems' / f'{s}.wav' for s in STEMS}
        for s, p in sp.items():
            if not p.exists(): bad.append(f'{s}.wav missing'); continue
            i = L.wav_info(p)
            if not str(i['codec']).startswith('pcm_') or i['sr'] != 48000 or abs(i['dur'] - 30.0) > 1.0 / FPS: bad.append(f'{s}: {i}')
        if not have['base']: bad.append('base film missing')
        if not bad:
            cands = []
            try: cands = L.find_gain_sets(json.loads((out / 'base' / 'timeline.json').read_text(encoding='utf-8-sig')), STEMS)
            except Exception: pass
            best = None
            for g in (cands or [{s: 1.0 for s in STEMS}]):
                r = L.stem_sum_bandcheck(vid['base'], sp, g)
                if r is None: continue
                ok = r['median'] <= 0.75 and r['p95'] <= 3.0 and r['max_gain_err_db'] <= 1.0
                if best is None or (ok, -r['median']) > (best[0], -best[1]['median']): best = (ok, r, g)
            if best is None: bad.append('band comparison impossible (silent/short)')
            else:
                ok, r, g = best
                msg = (f"band diff median {r['median']:.2f} dB (<=0.75), p95 {r['p95']:.2f} dB (<=3), lag {r['lag']}; "
                       f"declared gains {g}, fitted {r['fitted']}, err dB {r['gain_err_db']} (<=1); declared sets {len(cands)}")
                if ok: R['B04'] = L.P(msg)
                else: bad.append(msg)
        if bad: R['B04'] = L.F('; '.join(bad))
    guard(['B04'], b04)

    def b05():
        bad = []
        if EV is None: bad.append('base/events.csv missing')
        else:
            hdr, e, rows = EV
            if hdr != ['event_id', 'frame', 'description']: bad.append(f'header {hdr}')
            if rows: bad.append(f'non-integer frames {rows[:3]}')
            miss = [k for k in EV_SHOT if k not in e]
            if miss: bad.append(f'missing {miss}')
            for k, s in EV_SHOT.items():
                if k in e:
                    a, b = SHOTS['base'][s]
                    if not (a <= e[k] <= b): bad.append(f'{k}={e[k]} not in {s}')
            if 'passenger_arrive' in e and e['passenger_arrive'] < 810: bad.append('passenger_arrive < 810')
        for v, hc in (('base', 810), ('revision', 840)):
            p = out / v / 'timeline.json'
            try:
                t = p.read_text(encoding='utf-8-sig'); j = json.loads(t)
                nums = []
                def walk(o):
                    if isinstance(o, dict): [walk(x) for x in o.values()]
                    elif isinstance(o, list): [walk(x) for x in o]
                    elif isinstance(o, (int, float)) and not isinstance(o, bool): nums.append(o)
                walk(j)
                if hc not in nums and hc / FPS not in nums: bad.append(f'{v} timeline lacks hidden cut {hc}')
                if 'gain' not in t.lower(): bad.append(f'{v} timeline lacks master gains')
                if not all(c in t for c in ('S1', 'S6')): bad.append(f'{v} timeline lacks shot ids')
            except Exception as ex:
                bad.append(f'{v}/timeline.json unreadable ({type(ex).__name__})')
        R['B05'] = L.F('; '.join(bad[:12])) if bad else L.P('events header/ids/shots OK; timelines parse with hidden cut and gains')
    guard(['B05'], b05)

    def b08():   # deterministic floor; completeness of credits.md is judged from the text
        h = L.scan_credentials(out); bad = []
        if h: bad.append(f'credential-like strings in {h[:5]}')
        if not any(out.rglob('credits.md')): bad.append('credits.md missing')
        if bad: R['B08'] = L.F('; '.join(bad))
    guard(['B08'], b08)

    def m18():   # floor; truthfulness vs the delivered evidence is judged from the text
        if not any(out.rglob('qa.md')): R['M18'] = L.F('qa.md missing')
    guard(['M18'], m18)

    G = {}
    for v in ('base', 'revision'):
        if have[v]:
            try: G[v] = L.gray_frames(vid[v])
            except Exception: pass
    if 'base' not in G or len(G['base']) < 10:
        R.setdefault('X08', L.F('base film missing or undecodable'))

    def b07():
        if 'base' not in G or len(G['base']) != 900: R['B07'] = L.F('base film missing or not 900 frames'); return
        g = G['base']; cuts, sc = L.detect_cuts(g); bad = []
        exp = [150, 300, 450, 600, 720]
        for c in exp:
            near = [x for x in cuts if abs(x - c) <= 1]
            if not near: bad.append(f'no hard cut at {c}')
            elif max(sc[near[0] - 1], sc[min(near[0] + 1, len(sc) - 1)]) > 0.5 * sc[near[0]]: bad.append(f'blend frames at {near[0]}')
        extra = [x for x in cuts if all(abs(x - c) > 1 for c in exp) and not (780 <= x <= 840)]
        if extra: bad.append(f'extra cuts {extra[:8]}')
        fz = L.freezes(g, 50.0); fz3 = [f for f in fz if f + 1 in fz]
        if fz3: bad.append(f'>=3 identical frames at {fz3[:6]}')
        S['cuts_base'] = cuts
        R['B07'] = L.F('; '.join(bad)) if bad else L.P(f'cuts {cuts}')
        S['x05a'] = not any(abs(x - 810) <= 1 for x in cuts)
        if not S['x05a']: R['X05'] = L.F('(a) hidden cut at 810 detected as a cut (content detector)')
    guard(['B07'], b07)

    def x05c():   # optical-flow direction across the hidden cut
        if 'base' not in G or len(G['base']) < 812: R.setdefault('X05', L.F('base film missing or short')); return
        import cv2
        g = G['base']
        fl = [float(cv2.calcOpticalFlowFarneback(g[i], g[i + 1], None, 0.5, 4, 21, 3, 5, 1.2, 0)[..., 0].mean()) for i in (808, 809, 810)]
        S['x05c'] = [round(x, 3) for x in fl]
        if not (all(x > 0 for x in fl) or all(x < 0 for x in fl)):
            R.setdefault('X05', L.F(f'(c) horizontal optical-flow means 808->811 change sign {S["x05c"]}'))
    guard(['X05'], x05c)

    A = {}
    def st(v, s):
        if (v, s) not in A: A[(v, s)] = L.decode_audio(out / v / 'stems' / f'{s}.wav')
        return A[(v, s)]

    def envs(v, s, w=0.01):
        return L.env_db(st(v, s), L.SR, w, w)

    def first_above(t, e, thr, a, b):
        i = np.where((t >= a) & (t <= b) & (e > thr))[0]
        return float(t[i[0]]) if i.size else None

    def last_above(t, e, thr, a, b):
        i = np.where((t >= a) & (t <= b) & (e > thr))[0]
        return float(t[i[-1]]) if i.size else None

    def onset(v, s, a, b, seg):
        t, e = envs(v, s); med = L.win_med(t, e, *seg)
        if med is None: return None, None
        return first_above(t, e, med - 20, a, b), med

    def m01():
        t, e = envs('base', 'gate'); bad = []
        on, med = onset('base', 'gate', 3.5, 5.5, (4.45, 9.9))
        if on is None or abs(on - 4.40) > 0.05: bad.append(f'gate onset {on}')
        pre = e[t < 4.35]
        if pre.size and pre.max() >= -60: bad.append(f'gate before 4.35 s max {pre.max():.1f} dBFS')
        rt = None
        if on is not None and med is not None:
            t10 = first_above(t, e, med - 20, on - 0.05, on + 1)
            t90 = first_above(t, e, med + 20 * math.log10(0.9), on - 0.05, on + 1)
            rt = None if t10 is None or t90 is None else t90 - t10
            if rt is None or rt > 0.3: bad.append(f'rise time {rt} (> 0.3 s or never reached)')
            ok, ratio = L.click_check(st('base', 'gate'), L.SR, on, w=0.02)
            if not ok: bad.append(f'click at gate onset (diff ratio {ratio} > 3)')
        tl, el = envs('base', 'lane'); end = last_above(tl, el, -60, 0, 9.9)
        if end is None or not (4.97 <= end <= 5.10): bad.append(f'lane end {end}')
        R['M01'] = L.F('; '.join(bad)) if bad else L.P(f'gate onset {on:.3f}s rise {rt:.3f}s click-free, lane end {end:.3f}s')
    guard(['M01'], m01)

    def m02():
        t, e = envs('base', 'gate'); bad = []
        on, _ = onset('base', 'gate', 23.0, 24.0, (23.55, 26.0))
        if on is None or abs(on - 23.50) > 0.05: bad.append(f'gate re-onset {on}')
        w = e[(t >= 20.10) & (t <= 23.45)]
        if w.size and w.max() >= -60: bad.append(f'gate in 20.10-23.45 max {w.max():.1f}')
        tl, el = envs('base', 'lane'); end = last_above(tl, el, -60, 20.0, 26.3)
        if end is None or not (23.97 <= end <= 24.10): bad.append(f'lane exit {end}')
        w = el[(tl >= 24.10) & (tl <= 26.30)]
        if w.size and w.max() >= -60: bad.append(f'lane in 24.10-26.30 max {w.max():.1f}')
        R['M02'] = L.F('; '.join(bad)) if bad else L.P('J-cut T56 timings OK')
    guard(['M02'], m02)

    def m03():
        bad = []
        tg, eg = envs('base', 'gate'); tl, el = envs('base', 'lane')
        E = {'gate': (tg, eg), 'lane': (tl, el)}
        for c, outg, inn in ((10, 'gate', 'lane'), (15, 'lane', 'gate'), (20, 'gate', 'lane')):
            x = last_above(*E[outg], -50, c - 1, c + 1); y = first_above(*E[inn], -50, c - 1, c + 1)
            if x is None or abs(x - c) > 0.10: bad.append(f'{outg} exit at {c}: {x}')
            if y is None or abs(y - c) > 0.10: bad.append(f'{inn} entry at {c}: {y}')
        for (a, b, off, ex) in ((0, 5, 'gate', (4.40, 5.0)), (5, 10, 'lane', None), (10, 15, 'gate', None), (15, 20, 'lane', None), (20, 24, 'gate', (23.5, 24.0))):
            t, e = E[off]; m = (t >= a + 0.1) & (t <= b - 0.1) & (e > -50)
            if ex: m &= ~((t >= ex[0]) & (t <= ex[1]))
            if m.sum() * 0.01 > 0.15: bad.append(f'{off} audible in {a}-{b}s for {m.sum() * 0.01:.2f}s')
        R['M03'] = L.F('; '.join(bad)) if bad else L.P('sound cuts with picture at 10/15/20 s')
    guard(['M03'], m03)

    def m04():
        bad = []
        tg, eg = envs('base', 'gate'); tl, el = envs('base', 'lane')
        k = np.ones(5) / 5; sg, sl = np.convolve(eg, k, 'same'), np.convolve(el, k, 'same')
        w = (tg >= 26.3) & (tg <= 27.7); x = np.where(w & (sl - sg >= 0))[0]
        cross = float(tg[x[0]]) if x.size else None
        if cross is None or not (26.5 <= cross <= 27.5): bad.append(f'crossover {cross}')
        gp, lp = L.win_med(tg, eg, 25.8, 26.3), L.win_med(tl, el, 27.7, 28.2)
        if gp is not None and lp is not None:
            g3 = first_above(tg, -sg, -(gp - 3), 26.0, 28.0); g20 = first_above(tg, -sg, -(gp - 20), 26.0, 28.5)
            l20 = first_above(tl, sl, lp - 20, 26.0, 28.0); l3 = first_above(tl, sl, lp - 3, 26.0, 28.5)
            fo = None if g3 is None or g20 is None else g20 - g3; fi = None if l20 is None or l3 is None else l3 - l20
            if fo is None or not (0.1 <= fo <= 1.5): bad.append(f'gate fade {fo}')
            if fi is None or not (0.1 <= fi <= 1.5): bad.append(f'lane fade {fi}')
        else: bad.append('no reference levels')
        # click test only at the hidden-cut seam: footsteps/door sounds elsewhere in 26-28 s are required action sound
        mix = L.decode_audio(vid['base']) if have['base'] else None
        for nm, y in (('gate', st('base', 'gate')), ('lane', st('base', 'lane')), ('mix', mix)):
            if y is None: continue
            ok, ratio = L.click_check(y, L.SR, 27.0, w=0.02)
            if not ok: bad.append(f'{nm} click at 27.0 s ±20 ms (diff ratio {ratio} > 3)')
        g = eg[tg >= 28.0]
        if g.size and g.max() >= -50: bad.append(f'gate after 28 s max {g.max():.1f}')
        R['M04'] = L.F('; '.join(bad)) if bad else L.P(f'crossover {cross:.2f}s; no click at the seam')
    guard(['M04'], m04)

    # ---------- speech (energy VAD + YIN f0; no ASR is available in the grader image)
    SP = {}
    def speech_segments():
        if 'segs' in SP: return SP['segs']
        x = st('base', 'speech'); t, e = L.env_db(x, L.SR, 0.1, 0.01)
        thr = max(-60.0, float(e.max()) - 35.0)
        act = e > thr; segs = []; i = 0
        while i < len(act):
            if act[i]:
                j = i
                while j + 1 < len(act) and act[j + 1]: j += 1
                segs.append([float(t[i]) - 0.05, float(t[j]) + 0.05]); i = j + 1
            else: i += 1
        mg = []
        for s in segs:
            if mg and s[0] - mg[-1][1] < 0.35: mg[-1][1] = s[1]
            else: mg.append(s)
        SP['segs'] = [s for s in mg if s[1] - s[0] >= 0.15]; SP['thr'] = thr
        return SP['segs']

    def line_span(who):
        a, b = ev(f'line_{who}_start'), ev(f'line_{who}_end')
        if a is None or b is None: return None, None, None
        tol = 6 / FPS; segs = [s for s in speech_segments() if s[1] > a / FPS - tol and s[0] < b / FPS + tol]
        if not segs: return (a, b), None, None
        return (a, b), segs[0][0], segs[-1][1]

    def f0_track(a, b):
        """YIN f0 (70-400 Hz, 40 ms frames, 10 ms hop) on the speech stem between a and b seconds; nan = unvoiced."""
        from scipy.signal import resample_poly
        x = st('base', 'speech')[max(0, int(a * L.SR)):int(b * L.SR)]
        y = resample_poly(x, 1, 3); sr = 16000; n = 640; hop = 160; tmax = sr // 70; tmin = sr // 400
        if len(y) < n + tmax: return np.array([]), np.array([])
        k = 1 + (len(y) - n - tmax) // hop; ts, f0 = [], []
        rms_all = np.sqrt(np.mean(y ** 2)) + 1e-12
        for i in range(k):
            s = y[i * hop:i * hop + n + tmax]; w = s[:n]; ts.append(a + (i * hop + n / 2) / sr)
            if np.sqrt(np.mean(w ** 2)) < 0.1 * rms_all: f0.append(np.nan); continue
            d = np.array([np.sum((w - s[tau:tau + n]) ** 2) for tau in range(1, tmax + 1)])
            cm = d * np.arange(1, tmax + 1) / (np.cumsum(d) + 1e-12)
            rng = cm[tmin - 1:]; below = np.where(rng < 0.15)[0]
            j = int(below[0]) if below.size else int(np.argmin(rng))
            while j + 1 < len(rng) and rng[j + 1] < rng[j]: j += 1
            f0.append(sr / (j + tmin) if rng[j] < 0.3 else np.nan)
        return np.array(ts), np.array(f0)

    def voiced_fraction(a, b):
        t, f = f0_track(a, b)
        return float(np.mean(~np.isnan(f))) if f.size else 0.0

    def m05():
        bad = []; info = {}
        segs = speech_segments()
        if not segs: R['M05'] = L.F('speech stem silent'); return
        spans = []
        for who, shot in (('screener', 'S3'), ('officer', 'S4')):
            dec, on, off = line_span(who)
            if dec is None: bad.append(f'line_{who}_start/end not declared'); continue
            spans.append((dec[0] / FPS - 6 / FPS, dec[1] / FPS + 6 / FPS))
            if on is None: bad.append(f'no speech in declared {who} span {dec}'); continue
            info[who] = [round(on, 3), round(off, 3)]
            if abs(on * FPS - dec[0]) > 6: bad.append(f'{who} onset {on * FPS:.1f}f vs declared {dec[0]}')
            if abs(off * FPS - dec[1]) > 6: bad.append(f'{who} offset {off * FPS:.1f}f vs declared {dec[1]}')
            a, b = SHOTS['base'][shot]
            if not (a / FPS <= on and off <= (b + 1) / FPS): bad.append(f'{who} speech {on:.2f}-{off:.2f}s not inside {shot}')
            vf = voiced_fraction(on, off); info[f'{who}_voiced'] = round(vf, 2)
            if vf < 0.3: bad.append(f'{who} line not speech-like (voiced fraction {vf:.2f} < 0.30)')
        stray = [s for s in segs if not any(s[1] > a and s[0] < b for a, b in spans)]
        if stray: bad.append(f'speech outside the two declared lines at {[[round(a, 2), round(b, 2)] for a, b in stray[:4]]}')
        R['M05'] = L.F('; '.join(bad)) if bad else L.P(f'VAD {info} (thr {SP["thr"]:.1f} dBFS)')
    guard(['M05'], m05)

    def m06():
        bad = []; info = {}
        for who in ('screener', 'officer'):
            dec, on, off = line_span(who)
            if on is None: bad.append(f'{who} line not found'); continue
            t, f = f0_track(on, off); v = f[~np.isnan(f)]
            if v.size < 10: bad.append(f'{who}: too few voiced frames ({v.size})'); continue
            stn = 12 * np.log2(v / np.median(v)); stn = stn[np.abs(stn) < 9]   # drop octave errors
            sd = float(np.std(stn)); rate = WORDS[who] / max(off - on, 1e-3)
            info[who] = {'f0_med': round(float(np.median(v)), 1), 'f0_sd_st': round(sd, 2), 'words_per_s': round(rate, 2)}
            if sd < 1.5: bad.append(f'{who} f0 SD {sd:.2f} st < 1.5 (monotone)')
            if not (1.8 <= rate <= 4.5): bad.append(f'{who} rate {rate:.2f} words/s not in 1.8-4.5')
        R['M06'] = L.F('; '.join(bad) + f' {info}') if bad else L.P(info)
    guard(['M06'], m06)

    def m08():
        bad = []; info = {}
        for s, k, tol in (('gate', 'pass_scan', 3), ('lane', 'tray_bump', 2), ('lane', 'bag_place', 2)):
            f = ev(k)
            if f is None: bad.append(f'{k} missing'); continue
            ok, r = L.transient_at(st('base', s), L.SR, f / FPS, tol / FPS, 8.0, 0.1); info[k] = r
            if not ok: bad.append(f'{s} transient at {k} rise {r} dB')
        R['M08'] = L.F('; '.join(bad)) if bad else L.P(f'transient rises (dB) {info}')
    guard(['M08'], m08)

    def m17_video():
        bad = []
        if 'revision' not in G or 'base' not in G: S['m17v'] = ['base or revision film missing']; R['M17'] = L.F('films missing'); return
        b, r = G['base'], G['revision']
        if len(r) != 930 or len(b) != 900: bad.append(f'revision frames {len(r)} / base {len(b)}')
        else:
            lo = [f for f in range(600) if L.psnr(r[f], b[f]) < 30]
            if lo: bad.append(f'rev != base at {lo[:5]} (n={len(lo)})')
            hi = [f for f in range(600, 900, 3) if L.ssim(r[f + 30], b[f]) < 0.85]
            if hi: bad.append(f'rev[f+30] SSIM<0.85 at {hi[:5]} (n={len(hi)})')
            fz = [f for f in range(601, 630) if L.psnr(r[f], r[f - 1]) > 50]
            if fz: bad.append(f'freeze in insert {fz[:5]}')
            md = [float(np.mean(np.abs(r[f + 1].astype(np.int16) - r[f].astype(np.int16)))) for f in range(615, 645)]
            j = md[14]; ref = float(np.median(md[:14] + md[15:]))   # md[14] = 629->630
            if j > 3 * ref + 1.0: bad.append(f'picture jump at 629->630 (mean diff {j:.2f} vs median {ref:.2f})')
        try:
            ab = L.decode_audio(vid['base']); ar = L.decode_audio(vid['revision']); sr = L.SR
            n = int(19.9 * sr); c = np.corrcoef(ab[:n], ar[:n])[0, 1]
            if c < 0.99: bad.append(f'audio before 20s corr {c:.3f}')
            a0, a1 = int(20.5 * sr), int(29.5 * sr)
            best = max(((float(np.corrcoef(ab[a0:a1], ar[a0 + int(round(lag * sr)):a1 + int(round(lag * sr))])[0, 1]), lag)
                        for lag in np.arange(0.97, 1.031, 0.005)), key=lambda z: z[0])
            if best[0] < 0.9 or abs(best[1] - 1.0) > 0.02: bad.append(f'audio after 20s offset {best[1]:.3f}s corr {best[0]:.3f}')
        except Exception as ex: bad.append(f'audio compare error {ex}')
        try:
            on, _ = onset('revision', 'gate', 24.0, 25.0, (24.55, 27.0))
            if on is None or abs(on - 24.50) > 0.05: bad.append(f'revision gate onset {on}')
        except Exception as ex: bad.append(f'revision gate stem error {ex}')
        S['m17v'] = bad
        if bad: R['M17'] = L.F('; '.join(bad[:10]))
    guard(['M17'], m17_video)

    G640 = {}
    def x06():
        if not have['base']: R['X06'] = L.F('no base film'); return
        g = L.gray_frames(vid['base'], 640, 360); G640['base'] = g; idx = {}
        for s, (a, b) in SHOTS['base'].items():
            vals = [L.flat_block_index(g[f], bs=16, std_thr=0.2, dark=8) for f in np.linspace(a + 3, b - 3, 5).astype(int) if f < len(g)]
            idx[s] = round(float(np.mean(vals)), 3) if vals else None
        S['flat'] = idx
        if any(v is None or v > 0.15 for v in idx.values()): R['X06'] = L.F(f'flat-block index per shot {idx} (> 0.15)')
    guard(['X06'], x06)

    # ---------- project ----------
    def project():
        blend = L.find_blend(out)
        rd = out / 'project' / 'README.md'
        readme_ok = rd.exists() and 'blender' in rd.read_text(encoding='utf-8', errors='ignore').lower()
        if not blend or not readme_ok:
            S['blend'] = 'missing'
            R['B06'] = L.F('project/scene.blend missing' if not blend else 'README.md without blender export command'); return
        if not shutil.which('blender'):
            raise GraderEnvError('blender not on PATH in the grader image; project items cannot be graded')
        e = (EV[1] if EV else {})
        def evd(k, dflt):
            v = e.get(k); return v if isinstance(v, int) else dflt
        ps, sp, tb = evd('pass_scan', 200), evd('stop_press', 340), evd('tray_bump', 360)
        gr, pl, pa = evd('bag_grip', 620), evd('bag_place', 700), evd('passenger_arrive', 860)
        cl = lambda a, b: list(range(max(0, a), min(899, b) + 1))
        cfg = {'rigs': RIGS,
               'cams': {'CAM_S1': [0, 149], 'CAM_S2': [150, 299], 'CAM_S3': [300, 449], 'CAM_S4': [450, 599], 'CAM_S5': [600, 719],
                        'CAM_S6A': [795, 809], 'CAM_S6B': [810, 899]},
               'track': ['PASSENGER', 'SCREENER', 'OFFICER', 'BAG', 'TRAY_A', 'TRAY_B', 'MONITOR', 'BELT_STOP_BUTTON', 'CONVEYOR',
                         'XRAY_TUNNEL', 'SEARCH_TABLE', 'TURNSTILE_GATE2', 'PARTITION'],
               'frames': list(range(0, 900)),
               'req': {'vbox': {'BAG': cl(580, 899), 'SEARCH_TABLE': [600, 899]},
                       'contact_bag': cl(gr - 3, pl + 3), 'contact_button': cl(sp - 10, sp + 10), 'button_disp': cl(sp - 10, sp + 20),
                       'gate': cl(ps - 5, 449), 'gate_pen': cl(ps, ps + 120)[::2],
                       'tray': sorted(set(list(range(0, 450, 3)) + list(range(450, 900, 9)) + cl(tb - 3, tb + 3))),
                       'proj': {'CAM_S6B': {'frames': [pa], 'objects': ['PASSENGER', 'SCREENER', 'OFFICER', 'BAG']}},
                       'monitor_proj': [300, 375, 449]},
               'mouth': {'SCREENER_RIG': ['SCREENER', 300, 449], 'OFFICER_RIG': ['OFFICER', 450, 599]},
               'revision_pass': True}
        D = run_probe(blend, cfg, tmp, PROBE_TIMEOUT)
        S['blend'] = {k: D.get(k) for k in ('version', 'rv', 'frame_range', 'engine', 'errors', '_rc', '_error')}
        if '_error' in D or 'objects' not in D:
            R['B06'] = L.F(f'blender could not open/inspect scene.blend: {str(D)[:400]}'); return
        ob = D['objects']; bad = []
        miss = [n for n in NAMES + CAMS if n not in ob]
        if miss: bad.append(f'missing {miss}')
        bt = [n for n in NAMES if n.endswith('_RIG') and n in ob and ob[n]['type'] != 'ARMATURE'] + [c for c in CAMS if c in ob and ob[c]['type'] != 'CAMERA']
        if bt: bad.append(f'bad types {bt}')
        rv = (D.get('scene_props') or {}).get('revision_insert_frames')
        exp = {0: [0, 899], 30: [0, 929]}.get(D.get('rv'))
        if exp is None: bad.append(f'scene property revision_insert_frames={rv} (must exist with value 0 or 30)')
        elif D.get('frame_range') != exp: bad.append(f'frame range {D.get("frame_range")} does not match revision_insert_frames={rv} (expected {exp})')
        if D.get('_rc') not in (0, None): bad.append(f'blender rc {D.get("_rc")}')
        perr = [x for x in D.get('errors', []) if x.startswith(('basic', 'measure'))]
        if perr: bad.append(f'project could not be evaluated: {perr[0][-300:]}')
        R['B06'] = L.F('; '.join(bad)) if bad else L.P(f'opens; 18 names + 7 cameras; revision_insert_frames={rv}, frame range {D.get("frame_range")}')
        if bad: return
        if D.get('url_refs'): R['B08'] = L.F(f'URL media refs {D["url_refs"]}')
        measure_project(D, R, S, ev, st, G, G640, out, tmp, blend)
    guard(['B06'], project)

    def m07():   # after the project pass: uses the measured belt stop when available
        bs = S.get('belt_stop_measured'); src = 'measured'
        if bs is None: bs = ev('belt_stop'); src = 'declared'
        if bs is None: R['M07'] = L.F('belt_stop neither declared nor measured'); return
        from scipy.ndimage import median_filter
        t, e = L.band_env(st('base', 'lane'), L.SR, 40, 500, 0.1, 0.05)
        e = median_filter(e, 11, mode='nearest'); b = bs / FPS; bad = []
        if b + 0.6 > 14.85: R['M07'] = L.F(f'belt stop {b:.2f}s ({src}) leaves no measurable window in S3'); return
        pre = L.win_med(t, e, b - 1.0, b - 0.1); post = L.win_med(t, e, b + 0.6, min(b + 1.0, 14.95))
        if pre is None or post is None: R['M07'] = L.F('lane stem too short'); return
        rest = e[(t >= b + 0.6) & (t <= 14.9)]
        if pre - post < 6: bad.append(f'40-500 Hz drop {pre - post:.1f} dB < 6 within 0.6 s of the stop')
        if rest.size and rest.max() > post + 3: bad.append(f'band recovers {rest.max() - post:.1f} dB above the stopped level (> 3)')
        for nm, a0, a1 in (('S1', 0.5, 4.4), ('S3', 10.2, b - 0.1)):
            m = (t >= a0) & (t <= a1)
            if m.sum() < 4:
                if nm == 'S1': bad.append('S1 window empty')
                continue
            if np.median(e[m]) < post + 6: bad.append(f'{nm} belt-running band {np.median(e[m]):.1f} dB not >= stopped level + 6 ({post + 6:.1f})')
            if np.std(e[m]) > 3: bad.append(f'{nm} belt sound not steady (SD {np.std(e[m]):.1f} dB > 3)')
        R['M07'] = L.F('; '.join(bad)) if bad else L.P(f'belt stop {b:.2f}s ({src}); drop {pre - post:.1f} dB; no recovery')
    guard(['M07'], m07)

    def x07_lip():
        if 'lip' not in S or 'X07' in R: return
        bad = list(S['lip_floor'])
        for rn, who in (('SCREENER_RIG', 'screener'), ('OFFICER_RIG', 'officer')):
            mo = (S['lip'] or {}).get(rn); a, b = ev(f'line_{who}_start'), ev(f'line_{who}_end')
            if not mo or a is None or b is None: bad.append(f'{rn}: no mouth curve or undeclared line'); continue
            cur = np.array(mo['curve'], dtype=float); a0 = mo['start']
            if not (a0 <= a < b <= a0 + len(cur) - 1): bad.append(f'{who} line {a}-{b} outside its shot'); continue
            sp_ = st('base', 'speech'); spf = int(L.SR / FPS)
            env = np.array([np.sqrt(np.mean(sp_[f * spf:(f + 1) * spf] ** 2) + 1e-12) for f in range(a, b + 1)])
            m = cur[a - a0:b - a0 + 1]; best = (-1.0, None)
            for lag in range(-2, 3):
                x = m[max(0, lag):len(m) + min(0, lag)]; y = env[max(0, -lag):len(env) - max(0, lag)]
                if len(x) > 5 and np.std(x) > 1e-6 and np.std(y) > 1e-9:
                    r = float(np.corrcoef(x, y)[0, 1])
                    if r > best[0]: best = (r, lag)
            S[f'lip_{who}'] = [round(best[0], 3), best[1], mo.get('sources')]
            if best[0] < 0.5: bad.append(f'{who} mouth/speech r {best[0]:.2f} < 0.5 within lag <= 2 frames (67 ms); sources {mo.get("sources")}')
        R['X07'] = L.F('; '.join(bad)) if bad else L.P(f'rigs bound, finger chains keyed; lip r/lag screener {S.get("lip_screener")} officer {S.get("lip_officer")}')
    guard(['X07'], x07_lip)
    if R.get('B06', {}).get('verdict') != 'pass':   # project items are not measurable: decide here instead of the judge
        for i in PRJ_DEP:
            R.setdefault(i, L.F('not measured: PRJ gate (B06 failed)'))
    return R


# ======================================================================== Blender probe
def run_probe(blend, cfg, tmp, timeout):
    tmp = pathlib.Path(tmp); script = pathlib.Path(__file__).resolve().parent / 'x08_probe_bpy.py'
    cp = tmp / f'x08_cfg_{cfg.get("mode", "measure")}.json'; cp.write_text(json.dumps(cfg))
    op = tmp / f'x08_out_{cfg.get("mode", "measure")}.json'
    if op.exists(): op.unlink()
    try:
        r = L.sh([shutil.which('blender'), '-b', str(blend), '--python', str(script), '--', str(cp), str(op)], timeout)
        log = (r.stdout or '')[-1500:] + (r.stderr or '')[-800:]
        if op.exists():
            d = json.loads(op.read_text()); d['_rc'] = r.returncode; d['_log_tail'] = log[-600:]
            return d
        return {'_error': 'no probe output produced', '_rc': r.returncode, '_log_tail': log}
    except Exception as e:
        return {'_error': f'{type(e).__name__}: {e}'}


# ======================================================================== project measurements
def _unit(v):
    v = np.asarray(v, float); n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v * 0


def _ang(a, b):
    a, b = _unit(a), _unit(b)
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(a, b))))))


def _ang2(a, b):   # horizontal angle between two xy vectors
    return _ang(np.append(np.asarray(a, float)[:2], 0), np.append(np.asarray(b, float)[:2], 0))


def measure_project(D, R, S, ev, st, G, G640, out, tmp, blend):
    cams = D.get('cams') or {}; tr = D.get('tracks') or {}; sk = D.get('skel') or {}; me = D.get('meas') or {}
    T = {n: {r[0]: np.array(r[1]) for r in (rows or [])} for n, rows in tr.items()}
    SKF = {rn: {f: p for f, p in (sk.get(rn) or []) if p} for rn in RIGS}
    PEL = {}
    for ch, rn in CHAR_RIG.items():   # pelvis bone if the rig has one, else the character's evaluated bbox centre
        p = {f: np.array(q['pelvis']) for f, q in SKF.get(rn, {}).items() if q.get('pelvis')}
        PEL[ch] = (p, 'pelvis bone', 0.10) if len(p) > 100 else (T.get(ch) or {}, 'mesh bbox centre', 0.15)

    def speed(pos, f, half=2):   # horizontal m/s, central difference over +-half frames
        a, b = pos.get(f - half), pos.get(f + half)
        if a is None or b is None: return None
        return float(np.linalg.norm((b - a)[:2])) * FPS / (2 * half)

    def head_forward(rn):
        """f -> horizontal unit forward of the head bone; the head axis is calibrated against the walking direction."""
        rows = SKF.get(rn) or {}; pel = PEL[RIGS[rn]][0]
        cand = [(k, s) for k in range(3) for s in (1, -1)]; score = {c: [] for c in cand}
        for f in rows:
            v = speed(pel, f)
            if v is None or v < 0.4 or 'head_ax' not in rows[f]: continue
            vel = _unit((pel[f + 2] - pel[f - 2])[:2])
            for k, s in cand:
                score[(k, s)].append(float(np.dot(_unit(np.array(rows[f]['head_ax'][k][:2]) * s), vel)))
        best = max(cand, key=lambda c: np.mean(score[c]) if score[c] else -9)
        if score[best] and np.mean(score[best]) >= 0.5:
            k, s = best
            return (lambda f: _unit(np.array(rows[f]['head_ax'][k][:2]) * s) if f in rows and 'head_ax' in rows[f] else None), f'head axis {"+" if s > 0 else "-"}{"XYZ"[k]} (walk-calibrated)'
        return (lambda f: _unit(-np.array(rows[f]['rig_ax'][1][:2])) if f in rows else None), 'rig -Y (no walking frames to calibrate)'

    def hpos(rn, f):
        r = (SKF.get(rn) or {}).get(f) or {}
        return np.array(r['head']) if r.get('head') else None

    def arr(c): return np.array([r[1] for r in c]), np.array([r[2] for r in c]), np.array([r[3] for r in c])
    def tpos(n, f): return T.get(n, {}).get(f)

    # ---------------- M09 camera parameters
    bad, info = [], {}
    try:
        p, fw, ln = arr(cams['CAM_S1']); r0 = cams['CAM_S1'][0]; pit = L.cam_pitch_deg(fw.mean(0)); info['S1'] = round(pit, 1)
        if not (pit <= -8 and np.ptp(p, 0).max() < 0.01 and max(_ang(fw[0], f) for f in fw) < 0.5 and (not r0[4] or r0[5] >= 5.6)): bad.append(f'S1 pitch {pit:.1f} move {np.ptp(p,0).max():.3f} dof {r0[4:6]}')
        p, fw, ln = arr(cams['CAM_S2']); y = np.unwrap(np.radians([L.cam_yaw_deg(f) for f in fw])); dy = math.degrees(y[-1] - y[0])
        pa, pb = PEL['PASSENGER'][0].get(150), PEL['PASSENGER'][0].get(299); same = None
        if pa is not None and pb is not None:
            ba = math.atan2(pa[1] - p[0][1], pa[0] - p[0][0]); bb = math.atan2(pb[1] - p[-1][1], pb[0] - p[-1][0])
            same = (math.remainder(bb - ba, 2 * math.pi)) * dy > 0
        info['S2'] = [round(dy, 1), round(float(np.linalg.norm(p[-1] - p[0])), 3), round(float(p[:, 2].mean()), 2), float(ln.mean()), same]
        if not (np.ptp(p, 0).max() < 0.3 and abs(dy) >= 15 and same and 1.2 <= p[:, 2].mean() <= 1.9 and 28 <= ln.min() and ln.max() <= 75 and np.ptp(ln) < 0.01 * ln.mean()): bad.append(f'S2 [yaw deg, travel, height, lens, follows] {info["S2"]}')
        p, fw, ln = arr(cams['CAM_S4']); tt = np.arange(len(p)); res = p - np.array([np.polyval(np.polyfit(tt, p[:, i], 1), tt) for i in range(3)]).T
        jit = float(np.sqrt((np.linalg.norm(res, axis=1) ** 2).mean()) * 1000); info['S4'] = [round(float(p[:, 2].mean()), 2), round(jit, 1), round(float(np.linalg.norm(p[-1] - p[0])), 3)]
        if not (1.2 <= p[:, 2].mean() <= 1.9 and 1 <= jit <= 60 and np.linalg.norm(p[-1] - p[0]) < 0.5): bad.append(f'S4 [height, jitter mm, net] {info["S4"]}')
        p, fw, ln = arr(cams['CAM_S5']); pit = L.cam_pitch_deg(fw.mean(0))
        dd = float(np.dot(p[-1] - p[0], _unit(fw.mean(0))))   # camera travel along its mean view direction
        info['S5'] = [round(pit, 1), round(float(p[:, 2].mean()), 2), round(dd, 3)]
        if not ((pit >= 4 or p[:, 2].mean() <= 0.9) and dd >= 0.08 and np.ptp(ln) < 0.01 * ln.mean()): bad.append(f'S5 [pitch, height, dolly-in m] {info["S5"]}')
        fw6 = np.array([r[2] for r in cams['CAM_S6B'] if r[0] >= 840])
        av = max(_ang(fw6[i], fw6[i + 1]) for i in range(len(fw6) - 1)); info['S6B_settle'] = round(av, 3)
        if av >= 0.5: bad.append(f'S6B angular speed after 840 {av:.2f} deg/frame')
    except Exception as ex: bad.append(f'camera export error {type(ex).__name__}: {ex}')
    R['M09'] = L.F('; '.join(bad)) if bad else L.P(info)

    # ---------------- M10 rack focus
    try:
        c = cams['CAM_S3']; p, fw, ln = arr(c); r0 = c[0]; fd = np.array([r[6] for r in c])
        mon = tpos('MONITOR', 300); btn = tpos('BELT_STOP_BUTTON', 300); bad = []
        dm, dbn = float(np.linalg.norm(p[0] - mon)), float(np.linalg.norm(p[0] - btn))
        if not (r0[4] and r0[5] <= 4): bad.append(f'dof {r0[4:6]}')
        if abs(dm - dbn) / max(dm, dbn) < 0.15: bad.append('monitor/button distances differ <15%')
        if abs(fd[0] - dm) > 0.25 * dm: bad.append(f'early focus {fd[0]:.2f} vs monitor {dm:.2f}')
        if abs(fd[-1] - dbn) > 0.25 * dbn: bad.append(f'late focus {fd[-1]:.2f} vs button {dbn:.2f}')
        if (np.sign(dbn - dm) * np.diff(fd) < -1e-4).any(): bad.append('focus pull not monotone')
        if np.ptp(p, 0).max() >= 0.01: bad.append('camera not fixed')
        R['M10'] = L.F('; '.join(bad)) if bad else L.P(f'focus {fd[0]:.2f}->{fd[-1]:.2f} m (monitor {dm:.2f}, button {dbn:.2f})')
    except Exception as ex: R['M10'] = L.F(f'rack-focus export error {type(ex).__name__}: {ex}')

    # ---------------- X04 button contact + belt stop (measured belt stop also feeds M07, M12-M15)
    try:
        bad = []; belt = {}; sp = ev('stop_press'); bs = ev('belt_stop')
        cb = {r['f']: r.get('tip') for r in me.get('contact_button', [])}
        win = [f for f in sorted(cb) if sp is not None and abs(f - sp) <= 2 and cb[f] is not None]
        tipmin = min((cb[f] for f in win), default=None)
        if tipmin is None or tipmin > 0.015: bad.append(f'fingertip-button distance at stop_press±2 {tipmin} m (> 0.015 or no finger bones)')
        cont = next((f for f in sorted(cb) if cb[f] is not None and cb[f] <= 0.015), None)
        travel = max((d for f, d in me.get('button_disp', [])), default=0.0)
        if travel < 0.002: bad.append(f'button cap travel {travel * 1000:.1f} mm (< 2)')
        pos = T.get('TRAY_A') or {}
        v = {f: float(np.linalg.norm(pos[f + 1] - pos[f])) for f in pos if f + 1 in pos}
        vs = {f: float(np.mean([v[g] for g in range(f - 1, f + 2) if g in v])) for f in v}
        c0 = cont if cont is not None else sp
        if c0 is None: bad.append('no contact frame / stop_press')
        else:
            pre = [vs[f] for f in range(c0 - 60, c0 - 4) if f in vs]
            steady = float(np.median(pre)) if pre else 0.0; belt['steady_m_per_frame'] = round(steady, 5)
            if steady < 0.0005: bad.append(f'TRAY_A not moving before contact ({steady:.5f} m/frame)')
            else:
                if any(abs(x - steady) > 0.15 * steady for x in pre): bad.append(f'belt speed before stop varies >15% ({min(pre):.4f}-{max(pre):.4f} m/frame)')
                dec = next((f for f in range(c0 - 2, c0 + 40) if f in vs and vs[f] < 0.9 * steady), None)
                stop = None if dec is None else next((f for f in range(dec, c0 + 80) if all(g in v and v[g] < 0.05 * steady for g in range(f, f + 5))), None)
                belt.update(contact=cont, decel=dec, stop=stop)
                if dec is None or not (0 <= dec - c0 <= 10): bad.append(f'decel onset {dec} not 0-10 frames after contact {c0}')
                if stop is None or dec is None or not (2 <= stop - dec <= 20): bad.append(f'full stop {stop} not 2-20 frames after decel onset {dec}')
                if stop is not None:
                    S['belt_stop_measured'] = stop
                    if bs is None or abs(stop - bs) > 3: bad.append(f'declared belt_stop {bs} vs measured {stop} (> 3 frames)')
        R['X04'] = L.F('; '.join(bad)) if bad else L.P(f'tip {tipmin:.3f} m, cap travel {travel * 1000:.1f} mm, belt {belt}')
    except Exception as ex: R['X04'] = L.F(f'button/belt measurement error {type(ex).__name__}: {ex}')

    # ---------------- X01 continuity of the shared world timeline
    try:
        bad = []; info = {}
        movers = [(ch, PEL[ch][0], PEL[ch][2], PEL[ch][1]) for ch in ('PASSENGER', 'SCREENER', 'OFFICER')] + \
                 [(n, T.get(n) or {}, 0.10, 'object bbox centre') for n in ('BAG', 'TRAY_A', 'TRAY_B')]
        for n, pos, lim, src in movers:
            fr = sorted(pos)
            if len(fr) < 900: bad.append(f'{n} not tracked'); continue
            P_ = np.array([pos[f] for f in fr]); stp = np.linalg.norm(np.diff(P_, axis=0), axis=1)
            j = np.where(stp > lim)[0]
            if j.size: bad.append(f'{n} ({src}) jumps {stp[j[0]]:.2f} m at {fr[j[0]]}->{fr[j[0] + 1]} (> {lim})')
            w = np.linalg.norm(P_[30:] - P_[:-30], axis=1)
            if (w > 2.5).any(): bad.append(f'{n} faster than 2.5 m/s over 1 s at frame {fr[int(np.argmax(w))]}')
            if n in CHAR_RIG:
                x = P_[:, 0] - WALL_X
                for i in np.where(np.sign(x[1:]) != np.sign(x[:-1]))[0]:
                    yy = float(P_[i, 1] + (P_[i + 1, 1] - P_[i, 1]) * (abs(x[i]) / max(abs(x[i]) + abs(x[i + 1]), 1e-9)))
                    if not any(a <= yy <= b for a, b in DOORS): bad.append(f'{n} crosses the partition at y={yy:.2f} (frame {fr[i]}) outside both doors')
        bag = T.get('BAG') or {}; bet = ev('bag_enter_tunnel') or 130
        sv = [float(np.linalg.norm(bag[f + 1] - bag[f])) for f in range(max(0, bet - 20), 149) if f in bag and f + 1 in bag]
        sv = [x for x in sv if x > 0.0005]
        if len(sv) < 5 or 149 not in bag or 300 not in bag: bad.append('BAG not riding the belt in S1 (no S1 belt speed)')
        else:
            vS1 = float(np.median(sv)); pred = vS1 * 151; act = float(np.linalg.norm(bag[300] - bag[149]))
            info['belt'] = [round(vS1, 5), round(pred, 3), round(act, 3)]
            if abs(act / pred - 1) > 0.3: bad.append(f'BAG 149->300 moved {act:.2f} m vs S1 belt prediction {pred:.2f} m (> 30% off)')
        R['X01'] = L.F('; '.join(bad[:8])) if bad else L.P(f'no jumps; belt continuity [v, pred, actual] {info.get("belt")}; partition only via doors; position source {[PEL[c][1] for c in PEL]}')
    except Exception as ex: R['X01'] = L.F(f'track measurement error {type(ex).__name__}: {ex}')

    # ---------------- X02 halt reaction
    pstop = {}
    try:
        bad = []; info = {}; oh = ev('officer_halt'); pst = ev('passenger_stop')
        orows = SKF.get('OFFICER_RIG') or {}; pp = PEL['PASSENGER'][0]; op = PEL['OFFICER'][0]
        def raised(f):
            for h in ((orows.get(f) or {}).get('hands') or {}).values():
                w, e_, s_ = np.array(h['wrist']), np.array(h['elbow']), np.array(h['shoulder']); fa = w - e_
                if np.linalg.norm(fa) > 1e-6 and (math.degrees(math.asin(max(-1, min(1, fa[2] / np.linalg.norm(fa))))) >= 45 or w[2] > s_[2]): return True
            return False
        if not any((orows.get(f) or {}).get('hands') for f in orows): bad.append('officer hand/forearm bones not found')
        onset = next((f for f in range(441, 600) if raised(f) and not raised(f - 1)), None); info['raise'] = onset
        if onset is None:
            bad.append('no officer forearm raise found in S4')
            if oh is not None:   # M14 still needs the measured passenger stop
                ms = next((f for f in range(oh, 585) if all((speed(pp, g) is not None and speed(pp, g) < 0.1) for g in range(f, f + 15))), None)
                if ms is not None: pstop['measured'] = ms
        else:
            if oh is None or abs(onset - oh) > 3 or not (450 <= onset <= 599): bad.append(f'raise onset {onset} vs declared officer_halt {oh} (> 3 frames or outside S4)')
            pre = [x for x in (speed(pp, f) for f in range(onset - 10, onset)) if x is not None]
            info['pre_speed'] = round(float(np.mean(pre)), 2) if pre else None
            if not pre or np.mean(pre) < 0.4: bad.append(f'passenger speed before the raise {info["pre_speed"]} m/s (< 0.4)')
            def slow(g):
                s_ = speed(pp, g); return s_ is not None and s_ < 0.1
            stop = next((f for f in range(onset + 6, onset + 46) if all(slow(g) for g in range(f, f + 15))), None); info['stop'] = stop
            if stop is None: bad.append('passenger does not stop (< 0.1 m/s for 15 frames) 6-45 frames after the raise')
            else:
                pstop['measured'] = stop
                if pst is None or abs(stop - pst) > 4: bad.append(f'declared passenger_stop {pst} vs measured {stop} (> 4 frames)')
            pf, psrc = head_forward('PASSENGER_RIG'); of, osrc = head_forward('OFFICER_RIG')
            run_, best = 0, 0
            for f in range(onset, onset + 61):
                fv, a, b = pf(f), hpos('PASSENGER_RIG', f), hpos('OFFICER_RIG', f)
                ok = fv is not None and a is not None and b is not None and _ang2(fv, b - a) <= 35
                run_ = run_ + 1 if ok else 0; best = max(best, run_)
            info['head_turn_frames'] = best; info['axes'] = [psrc, osrc]
            if best < 10: bad.append(f'passenger head within 35° of the officer for only {best} consecutive frames (< 10)')
            fv, a, b = of(onset), hpos('OFFICER_RIG', onset), hpos('PASSENGER_RIG', onset)
            oa = None if fv is None or a is None or b is None else _ang2(fv, b - a)
            info['officer_facing'] = None if oa is None else round(oa, 1)
            if oa is None or oa > 35: bad.append(f'officer head angle to the passenger at the raise {info["officer_facing"]}° (> 35)')
            ds = [float(np.linalg.norm((pp[f] - op[f])[:2])) for f in range(450, 600) if f in pp and f in op]
            info['min_pelvis_dist'] = round(min(ds), 3) if ds else None
            if not ds or min(ds) < 0.35: bad.append(f'pelvis distance {info["min_pelvis_dist"]} m < 0.35 (collision)')
        R['X02'] = L.F('; '.join(bad)) if bad else L.P(info)
    except Exception as ex: R['X02'] = L.F(f'halt measurement error {type(ex).__name__}: {ex}')

    # ---------------- X03 bag lift hand contact
    try:
        bad = []; info = {}; gr, pl = ev('bag_grip'), ev('bag_place')
        rows = {r['f']: r for r in me.get('contact_bag', [])}
        span = list(range(gr, pl + 1)) if gr is not None and pl is not None and pl > gr else []
        if not span: bad.append('bag_grip/bag_place not declared (or place <= grip)')
        else:
            hd = lambda f: [rows.get(f, {}).get(s) for s in ('L', 'R')]
            one = [f for f in span if min([x for x in hd(f) if x is not None] or [9]) <= 0.04]
            both = [f for f in span if all(x is not None and x <= 0.04 for x in hd(f))]
            info.update(one_hand=f'{len(one)}/{len(span)}', both_hands=f'{len(both)}/{len(span)}')
            if len(one) < len(span): bad.append(f'no hand within 4 cm of the BAG on {len(span) - len(one)}/{len(span)} frames (first {next(f for f in span if f not in one)})')
            if len(both) < 0.8 * len(span): bad.append(f'both hands on the BAG on {len(both)}/{len(span)} frames (< 80%)')
            vb = {f: b for f, b in (me.get('vbox') or {}).get('BAG', []) if b}
            z0 = vb.get(gr, [0] * 6)[4]; lift = max((vb[f][4] - z0 for f in span if f in vb), default=0.0); info['lift'] = round(lift, 3)
            if lift < 0.10: bad.append(f'BAG lift {lift:.3f} m < 0.10')
            bag = T.get('BAG') or {}
            drift = [(f, float(np.linalg.norm(bag[f + 1] - bag[f]))) for f in range(600, 899) if f in bag and f + 1 in bag and not (gr <= f < pl)]
            drift = [(f, d) for f, d in drift if d >= 0.005]
            if drift: bad.append(f'BAG moves {drift[0][1] * 1000:.1f} mm/frame at frame {drift[0][0]} outside the lift (>= 5)')
            tbx = dict((f, b) for f, b in (me.get('vbox') or {}).get('SEARCH_TABLE', []) if b)
            top = tbx.get(899, tbx.get(600))
            if not top: bad.append('SEARCH_TABLE geometry not measurable')
            else:
                gaps = [vb[f][4] - top[5] for f in range(pl, 900) if f in vb]
                offt = [f for f in range(pl, 900) if f in vb and not (top[0] <= (vb[f][0] + vb[f][1]) / 2 <= top[1] and top[2] <= (vb[f][2] + vb[f][3]) / 2 <= top[3])]
                info['table_gap'] = [round(min(gaps), 4), round(max(gaps), 4)] if gaps else None
                if not gaps or max(abs(g) for g in gaps) > 0.015: bad.append(f'BAG bottom vs table top {info["table_gap"]} m after bag_place (|gap| > 0.015)')
                if offt: bad.append(f'BAG not over SEARCH_TABLE at frame {offt[0]}')
        R['X03'] = L.F('; '.join(bad)) if bad else L.P(info)
    except Exception as ex: R['X03'] = L.F(f'bag contact measurement error {type(ex).__name__}: {ex}')

    # ---------------- M11 e-gate passage
    try:
        bad = []; info = {}; ps = ev('pass_scan')
        gd = {f: d for f, d in me.get('gate', [])}
        if ps is None or not gd: bad.append('pass_scan undeclared or TURNSTILE_GATE2 not measurable')
        else:
            onset = next((f for f in sorted(gd) if f > ps - 5 and gd[f] > 0.02), None)
            opened = next((f for f in sorted(gd) if gd[f] >= 0.15), None)
            pp = PEL['PASSENGER'][0]
            cross = next((f for f in range(ps - 5, 449) if f in pp and f + 1 in pp and pp[f][1] < 3.0 <= pp[f + 1][1]), None)
            closed = next((f for f in sorted(gd) if cross is not None and f > cross and gd[f] < 0.03), None)
            pens = [d for f, d in me.get('gate_pen', []) if d is not None]; pen = max(pens) if pens else None
            info = dict(onset=onset, open=opened, cross=cross, closed=closed, max_pen=pen)
            if onset is None or not (3 <= onset - ps <= 36): bad.append(f'flap opening onset {onset} not 3-36 frames after pass_scan {ps}')
            if opened is None: bad.append('flaps never open (>= 0.15 m flap displacement)')
            if cross is None: bad.append('passenger never crosses the gate line y=3.0 after pass_scan (before 449)')
            elif gd.get(cross, 0) < 0.15: bad.append(f'gate not open when the passenger crosses (frame {cross}, displacement {gd.get(cross)})')
            if closed is None: bad.append('flaps do not close after the passage (by frame 449)')
            if pen is None or pen > 0.02: bad.append(f'passenger/gate interpenetration {pen} m (> 0.02)')
        R['M11'] = L.F('; '.join(bad)) if bad else L.P(info)
    except Exception as ex: R['M11'] = L.F(f'gate measurement error {type(ex).__name__}: {ex}')

    # ---------------- M12 rigid bodies on the belt
    try:
        bad = []; info = {}; ph = D.get('physics') or {}; rb = ph.get('objects') or {}
        files = [p for p in (out / 'project').rglob('*') if p.is_file()]
        disk = [p for p in files if p.suffix == '.bphys']
        coll = set(ph.get('collection') or [])
        sim = bool(ph.get('world') and {'TRAY_A', 'TRAY_B'} <= coll and all((rb.get(n) or {}).get('rigid_body') for n in ('TRAY_A', 'TRAY_B')) and (ph.get('baked') or disk))
        rbscript = any(re.search(r'rigid_?body', p.read_text(encoding='utf-8', errors='ignore')) for p in files if p.suffix == '.py')
        baked_keys = all((rb.get(n) or {}).get('n_keys', 0) >= 100 for n in ('TRAY_A', 'TRAY_B')) and rbscript
        info['sim'] = {'world': ph.get('world'), 'baked': ph.get('baked'), 'bphys_files': len(disk), 'in_world': sorted(coll & {'TRAY_A', 'TRAY_B', 'BAG'}), 'baked_to_keys+script': baked_keys}
        if not (sim or baked_keys): bad.append(f'no shipped rigid-body cache/bake for TRAY_A/TRAY_B {info["sim"]}')
        trows = me.get('tray', []); tb = ev('tray_bump'); bs = S.get('belt_stop_measured') or ev('belt_stop'); gr = ev('bag_grip'); tp = ev('tray_push')
        gaps = [r['gap_ab'] for r in trows if tb is not None and abs(r['f'] - tb) <= 3 and r.get('gap_ab') is not None]
        info['bump_gap'] = min(gaps) if gaps else None
        if not gaps or min(gaps) > 0.01: bad.append(f'tray gap at tray_bump±3 {info["bump_gap"]} m (> 0.01)')
        pen = max([max(r.get('pen_ab') or 0, r.get('pen_conv') or 0) for r in trows] or [0]); info['max_pen'] = pen
        if pen > 0.01: bad.append(f'tray interpenetration {pen:.3f} m (> 0.01)')
        def inside(b, c, m=0.05): return c[0] - m <= (b[0] + b[1]) / 2 <= c[1] + m and c[2] - m <= (b[2] + b[3]) / 2 <= c[3] + m
        offb = [r['f'] for r in trows if bs is not None and r['f'] >= bs and r.get('C') and any(not inside(b, r['C']) for b in (r.get('A'), r.get('B')) if b)]
        if offb: bad.append(f'tray off the belt after the stop (frame {offb[0]})')
        bag = T.get('BAG') or {}
        outt = [r['f'] for r in trows if tp is not None and gr is not None and tp <= r['f'] < gr and r.get('A') and r['f'] in bag and not (
            r['A'][0] - 0.02 <= bag[r['f']][0] <= r['A'][1] + 0.02 and r['A'][2] - 0.02 <= bag[r['f']][1] <= r['A'][3] + 0.02)]
        if outt: bad.append(f'BAG leaves TRAY_A before bag_grip (frame {outt[0]})')
        R['M12'] = L.F('; '.join(bad)) if bad else L.P(info)
    except Exception as ex: R['M12'] = L.F(f'rigid-body measurement error {type(ex).__name__}: {ex}')

    # ---------------- M13 layout and screen direction
    try:
        bad = []; info = {}
        for n, (x, y) in LAYOUT.items():
            p = tpos(n, 0)
            if p is None: bad.append(f'{n} not found'); continue
            d = float(np.hypot(p[0] - x, p[1] - y)); info[n] = round(d, 2)
            if d > 0.5: bad.append(f'{n} centre {np.round(p[:2], 2).tolist()} is {d:.2f} m from scene.json {[x, y]}')
        pt = tpos('PARTITION', 0)
        if pt is None or abs(pt[0] - WALL_X) > 0.5: bad.append(f'PARTITION centre x {None if pt is None else round(float(pt[0]), 2)} vs 6.0')
        bag = T.get('BAG') or {}; bs = S.get('belt_stop_measured') or ev('belt_stop') or 449
        for cn, a, b in (('CAM_S1', 0, 149), ('CAM_S3', 300, bs)):
            rows = {r[0]: np.array(r[7]) for r in (cams.get(cn) or [])}
            sg = [float(np.dot(bag[f + 1] - bag[f], rows[f])) for f in range(a, b) if f in rows and f in bag and f + 1 in bag and np.linalg.norm(bag[f + 1] - bag[f]) > 0.001]
            info[cn] = f'{sum(1 for s in sg if s > 0)}/{len(sg)} L->R'
            if len(sg) < 5 or sum(1 for s in sg if s > 0) < 0.9 * len(sg): bad.append(f'{cn}: BAG belt motion not screen left->right ({info[cn]} moving frames)')
        c6 = {r[0]: np.array(r[2]) for r in (cams.get('CAM_S6A') or [])}
        a0, a1 = (_ang2(c6[795], [1, 0]), _ang2(c6[803], [1, 0])) if 795 in c6 and 803 in c6 else (None, None)
        info['S6A_to_east_deg'] = None if a0 is None else [round(a0, 1), round(a1, 1)]
        if a0 is None or not a1 < a0: bad.append(f'CAM_S6A whip does not turn toward +x (the partition, east): angle to +x at 795/803 {info["S6A_to_east_deg"]}')
        R['M13'] = L.F('; '.join(bad)) if bad else L.P(info)
    except Exception as ex: R['M13'] = L.F(f'layout measurement error {type(ex).__name__}: {ex}')

    # ---------------- M14 causal chain
    try:
        bad = []
        need = ['stop_press', 'belt_stop', 'line_screener_end', 'officer_halt', 'passenger_stop', 'bag_grip', 'bag_place', 'passenger_arrive']
        E = {k: ev(k) for k in need}
        if any(v is None for v in E.values()): bad.append(f'undeclared {[k for k, v in E.items() if v is None]}')
        else:
            ch = ['stop_press', 'belt_stop', 'line_screener_end', 'officer_halt', 'passenger_stop']
            for a, b in zip(ch, ch[1:]):
                if not E[a] < E[b]: bad.append(f'{a} {E[a]} !< {b} {E[b]}')
            if not E['bag_grip'] > E['belt_stop']: bad.append('bag_grip not after belt_stop')
            if not E['passenger_arrive'] > E['bag_place']: bad.append('passenger_arrive not after bag_place')
            mb, mp = S.get('belt_stop_measured'), pstop.get('measured')
            if mb is None or abs(mb - E['belt_stop']) > 4: bad.append(f'measured belt stop {mb} vs declared {E["belt_stop"]}')
            if mp is None or abs(mp - E['passenger_stop']) > 4: bad.append(f'measured passenger stop {mp} vs declared {E["passenger_stop"]}')
        R['M14'] = L.F('; '.join(bad)) if bad else L.P(f'declared order OK; measured belt stop {S.get("belt_stop_measured")}, passenger stop {pstop.get("measured")}')
    except Exception as ex: R['M14'] = L.F(f'causal-chain error {type(ex).__name__}: {ex}')

    # ---------------- M15 X-ray monitor (film ROI = CAM_S3 projection of MONITOR)
    try:
        bad = []; g = G640.get('base')
        pr = [p for f, p in me.get('monitor_proj', []) if p]
        bs = S.get('belt_stop_measured') or ev('belt_stop')
        if g is None or len(g) < 450: bad.append('base film missing')
        elif not pr or bs is None: bad.append('MONITOR projection or belt stop unavailable')
        else:
            x0 = max(0.0, min(p[0] for p in pr)); x1 = min(1.0, max(p[1] for p in pr)); y0 = max(0.0, min(p[2] for p in pr)); y1 = min(1.0, max(p[3] for p in pr))
            H, W = g.shape[1:]; c0, c1 = int(x0 * W), int(math.ceil(x1 * W)); r0, r1 = int((1 - y1) * H), int(math.ceil((1 - y0) * H))
            if min(p[4] for p in pr) <= 0 or c1 - c0 < 4 or r1 - r0 < 4: bad.append(f'MONITOR not visible in CAM_S3 (roi {[c0, c1, r0, r1]})')
            else:
                roi = g[300:450, r0:r1, c0:c1].astype(np.int16); d = np.abs(np.diff(roi, axis=0)).mean(axis=(1, 2))   # d[i]: (300+i)->(301+i)
                pre = d[1:max(2, bs - 302)]; post = d[min(len(d) - 2, bs + 5 - 300):len(d) - 1]
                sd = float(roi[5].std()); pm = float(np.mean(pre)); qm = float(np.mean(post)) if post.size else 0.0
                S['m15'] = dict(roi=[c0, c1, r0, r1], diff_pre=round(pm, 3), diff_post=round(qm, 3), std=round(sd, 1))
                if sd < 5: bad.append(f'monitor image uniform (std {sd:.1f} < 5)')
                if pm < 0.5: bad.append(f'monitor image not updating before the belt stop (mean frame diff {pm:.2f} < 0.5)')
                if pm < 2 * qm: bad.append(f'monitor image not holding after the belt stop (pre {pm:.2f} < 2 x post {qm:.2f})')
        R['M15'] = L.F('; '.join(bad)) if bad else L.P(S.get('m15'))
    except Exception as ex: R['M15'] = L.F(f'monitor measurement error {type(ex).__name__}: {ex}')

    # ---------------- X05 (b) whip; pass needs (a) and (c) from the film as well
    try:
        def yawv(c, a, b):
            rows = [r for r in c if a <= r[0] <= b]; y = np.unwrap(np.radians([L.cam_yaw_deg(r[2]) for r in rows]))
            return np.degrees(np.diff(y))
        va, vb = yawv(cams['CAM_S6A'], 803, 809), yawv(cams['CAM_S6B'], 810, 816)
        ok = len(va) and len(vb) and (np.abs(va) >= 6).all() and (np.abs(vb) >= 6).all() and np.sign(va).min() == np.sign(va).max() == np.sign(vb).min() == np.sign(vb).max()
        if not ok or not D.get('motion_blur'): R['X05'] = L.F(f'(b) whip yaw speeds S6A {np.round(va,1).tolist()} S6B {np.round(vb,1).tolist()} motion_blur {D.get("motion_blur")}')
        elif 'X05' not in R and S.get('x05a') and S.get('x05c'):
            R['X05'] = L.P(f'(a) 810 not detected as a cut; (b) yaw S6A {np.round(va,1).tolist()} S6B {np.round(vb,1).tolist()} motion blur on; (c) flow {S.get("x05c")}')
    except Exception as ex: R.setdefault('X05', L.F(f'whip export error {type(ex).__name__}: {ex}'))

    # ---------------- X06 project floor (the look itself is judged from the contact sheets)
    try:
        bad = []
        eng = D.get('engine'); lights = D.get('lights') or []; mats = D.get('materials') or {}
        if eng not in ('CYCLES', 'BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'): bad.append(f'render engine {eng}')
        if eng == 'CYCLES' and D.get('denoise') is False: bad.append('Cycles denoising off')
        soft = [l for l in lights if l['type'] == 'AREA' or l['size'] >= 0.05] or (['world'] if set(D.get('world_nodes') or []) & {'TEX_ENVIRONMENT', 'TEX_SKY'} else [])
        if not soft: bad.append('no soft light source (area light, light radius >= 5 cm, or HDRI/sky world)')
        nb = sum(1 for m in mats.values() if m['bsdf']); nt = sum(1 for m in mats.values() if m['tex'] or m['bump'])
        if not mats or nb < 0.6 * len(mats): bad.append(f'only {nb}/{len(mats)} materials use a BSDF shader')
        if nt < 5: bad.append(f'only {nt} materials with image/procedural texture or bump nodes (< 5)')
        if bad: R['X06'] = L.F('project floor: ' + '; '.join(bad))
    except Exception as ex: R['X06'] = L.F(f'material export error {type(ex).__name__}: {ex}')

    # ---------------- X07 rig floor (lip sync is computed in run() after this)
    try:
        fl = []
        for rn, d in (D.get('rigs') or {}).items():
            if not d.get('char_bound'): fl.append(f'{rn} does not deform its character mesh')
            if not any(h['chains'] >= 4 and h['keyed_finger_bones'] >= 4 for h in d.get('hands', [])): fl.append(f'{rn}: no hand with >= 4 finger chains (>= 3 bones) and >= 4 keyed finger bones')
        S['lip_floor'] = fl; S['lip'] = D.get('mouth') or {}
    except Exception as ex: R['X07'] = L.F(f'rig export error {type(ex).__name__}: {ex}')

    # ---------------- X09 convergence
    try:
        bad = []; info = {}; pa = ev('passenger_arrive')
        for ch in ('PASSENGER', 'OFFICER'):
            pos = PEL[ch][0]; fr = [f for f in range(720, 900) if f in pos]
            xs = [f for f in fr[:-1] if pos[f][0] < WALL_X <= pos[f + 1][0]]
            if not xs: bad.append(f'{ch} does not enter the lane (x crosses 6.0) during S6'); continue
            y = float(pos[xs[0]][1]); info[f'{ch}_door_y'] = round(y, 2)
            if not (DOORS[1][0] <= y <= DOORS[1][1]): bad.append(f'{ch} enters the lane at y={y:.2f}, not through the north door [6.2, 7.4]')
            end = pa if (ch == 'PASSENGER' and pa) else 899
            steps = [float(np.linalg.norm((pos[g + 1] - pos[g])[:2])) for g in range(720, end) if g in pos and g + 1 in pos]
            mv = [s for s in steps if s * FPS > 0.1]; spd = sum(mv) / max(len(mv), 1) * FPS; info[f'{ch}_speed'] = round(spd, 2)
            if not (0.4 <= spd <= 2.0): bad.append(f'{ch} mean walking speed {spd:.2f} m/s not 0.4-2.0')
        tbx = dict((f, b) for f, b in (me.get('vbox') or {}).get('SEARCH_TABLE', []) if b).get(899)
        pp = PEL['PASSENGER'][0]
        if pa is None or pa not in pp or not tbx: bad.append('passenger_arrive undeclared or SEARCH_TABLE not measurable')
        else:
            p = pp[pa]; dx = max(tbx[0] - p[0], 0, p[0] - tbx[1]); dy = max(tbx[2] - p[1], 0, p[1] - tbx[3]); dist = float(np.hypot(dx, dy))
            info['table_dist'] = round(dist, 2)
            if dist > 1.2: bad.append(f'passenger {dist:.2f} m from the table edge at passenger_arrive (> 1.2)')
            hf, src = head_forward('PASSENGER_RIG'); hp = hpos('PASSENGER_RIG', pa); bagp = tpos('BAG', pa)
            if hf(pa) is None or hp is None or bagp is None: bad.append('passenger head / BAG not measurable at passenger_arrive')
            else:
                a = _ang2(hf(pa), bagp - hp); info['head_to_bag_deg'] = round(a, 1)
                if a > 35: bad.append(f'passenger head {a:.0f}° from the BAG direction (> 35; {src})')
            prj = next((r for r in me.get('proj', []) if r.get('cam') == 'CAM_S6B' and r['f'] == pa), None)
            if not prj or pa < 810: bad.append('CAM_S6B not active / not projected at passenger_arrive')
            else:
                for n in ('PASSENGER', 'SCREENER', 'OFFICER', 'BAG'):
                    q = prj.get(n)
                    if not q or q[4] <= 0: bad.append(f'{n} not in front of CAM_S6B'); continue
                    ar = max(1e-9, (q[1] - q[0]) * (q[3] - q[2]))
                    ins = max(0, min(q[1], 1) - max(q[0], 0)) * max(0, min(q[3], 1) - max(q[2], 0)) / ar
                    info[f'{n}_in_frame'] = round(ins, 2)
                    if ins < 0.5: bad.append(f'{n} only {ins:.0%} inside the CAM_S6B frame (< 50%)')
        bag = T.get('BAG') or {}
        if 719 in bag:
            dm = max(float(np.linalg.norm(bag[f] - bag[719])) for f in range(810, 900) if f in bag); info['bag_shift'] = round(dm, 3)
            if dm > 0.02: bad.append(f'BAG in S6B differs from the end of S5 by {dm:.3f} m (> 0.02)')
        R['X09'] = L.F('; '.join(bad)) if bad else L.P(info)
    except Exception as ex: R['X09'] = L.F(f'convergence measurement error {type(ex).__name__}: {ex}')

    # ---------------- M17 project part: revision state continuity at 599/600 and 629/630
    try:
        bad = list(S.get('m17v') or [])
        rvd = D.get('revision') or {}
        rows = {r['f']: r for r in rvd.get('rows', [])}
        note = ''
        if rvd.get('error') or not rows: bad.append(f'revision state not evaluable: {rvd.get("error") or (D.get("errors") or [""])[-1][-200:]}')
        else:
            live = rvd.get('saved_rv') == 30
            if not live:   # saved in base state: did setting the property to 30 shift the scene (rev 700 ~ base 670)?
                d_shift = [float(np.linalg.norm(np.array(rows[700][k]) - T[k][670])) for k in ('BAG', 'SCREENER') if k in rows.get(700, {}) and 670 in T.get(k, {})]
                d_same = [float(np.linalg.norm(np.array(rows[700][k]) - T[k][700])) for k in ('BAG', 'SCREENER') if k in rows.get(700, {}) and 700 in T.get(k, {})]
                live = bool(d_shift and d_same and np.mean(d_same) > 0.005 and np.mean(d_shift) < np.mean(d_same))
            if live:
                keys = [k for k in rows.get(600, {}) if k not in ('f', 'CAM_S4')]
                for a in (599, 629):
                    for k in keys:
                        if not all(k in rows.get(f, {}) for f in range(a - 2, a + 4)): continue
                        stp = lambda f: float(np.linalg.norm(np.array(rows[f + 1][k]) - np.array(rows[f][k])))
                        j = stp(a); nb = [stp(f) for f in (a - 2, a - 1, a + 1, a + 2)]
                        if j > 0.03 + 2 * float(np.median(nb)): bad.append(f'revision jump {k} {j:.3f} m at {a}->{a + 1}')
                note = 'project revision continuity measured'
            else:
                note = 'setting revision_insert_frames=30 does not change the evaluated scene (scripted revision); insert continuity judged from the film only'
        R['M17'] = L.F('; '.join(bad[:10])) if bad else L.P(f'film/audio propagation OK; {note}')
    except Exception as ex: R['M17'] = L.F(f'revision measurement error {type(ex).__name__}: {ex}')

    # ---------------- M16 re-render
    try:
        bad = []
        if 'base' not in G or len(G['base']) != 900: R['M16'] = L.F('base film missing'); return
        rdir = pathlib.Path(tmp) / 'x08_rr'; rdir.mkdir(exist_ok=True)
        for p in rdir.glob('*.png'): p.unlink()
        RD = run_probe(blend, {'mode': 'render', 'render': {'dir': str(rdir), 'frames': list(RERENDER_FRAMES), 'samples': 16, 'time_limit': 90}}, tmp, RENDER_TIMEOUT)
        import cv2
        vals = {}
        for f in RERENDER_FRAMES:
            p = rdir / f'rr_{f:04d}.png'
            im = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) if p.exists() else None
            if im is None: bad.append(f'frame {f} not re-rendered ({str(RD.get("_error") or RD.get("errors"))[:200]})'); continue
            im = cv2.resize(im, (320, 180), interpolation=cv2.INTER_AREA)
            vals[f] = round(L.ssim(cv2.GaussianBlur(im, (0, 0), 1.5), cv2.GaussianBlur(G['base'][f], (0, 0), 1.5)), 3)
        S['m16'] = vals
        low = {f: v for f, v in vals.items() if v < 0.75}
        if low: bad.append(f'SSIM < 0.75 at {low}')
        R['M16'] = L.F('; '.join(bad)) if bad else L.P(f'SSIM per frame {vals}')
    except Exception as ex: R['M16'] = L.F(f're-render error {type(ex).__name__}: {ex}')


def postprocess(res, ctx):
    items = {i['id']: i for i in ctx['items']}
    def failed(i): return res.get(i, {}).get('verdict') not in ('pass', 'na')
    def gate(ids, why):
        for i in ids:
            if i in items and res.get(i, {}).get('verdict') != 'fail':
                pre = res.get(i, {})
                res[i] = dict(pre, verdict='fail', detail=f'group gate {why} triggered (pre-gate: {pre.get("verdict")} {str(pre.get("detail", pre.get("reason", "")))[:300]})', gate=why)
    if failed('B04'):
        gate([i for i, it in items.items() if (it.get('group') == 'AUD' and i not in ('B03', 'B04')) or it.get('group') == 'SPEECH'], 'AUD (B04)')
    if failed('B06'):
        gate(PRJ_DEP, 'PRJ (B06)')
    if failed('B02'):
        gate(['M17'], 'REV (B02)')
    return res
