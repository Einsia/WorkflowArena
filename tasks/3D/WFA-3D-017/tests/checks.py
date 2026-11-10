# -*- coding: utf-8 -*-
"""CDC-C-X07 deterministic checks (see review/VERIFIER_NOTES.md and review/rubric-cleanup-20261025.md).
Policy (2026-10-25): every item is decided here with pass/fail, except X07-B07, X07-M18, X07-G07 and X07-G08, which
return only a deterministic fail floor and otherwise go to the LLM judge (text files / contact sheets).
Blender-dependent items need `blender` in the grader image; if it is missing they are marked 'error' (no reward)."""
import json, math, os, pathlib, traceback
import numpy as np
import cxlib as L

FPS = 24
VERS = ('base', 'revision1', 'revision2')
STEMS = ('speech', 'rain', 'fx')
REQ_EV = ['lamp_flicker_start', 'lamp_off', 'umbrella_open', 'foot_contact', 'headlights_on_face', 'line_start', 'line_end', 'lamp_on']
EV_SHOT = {'lamp_flicker_start': 'S1', 'lamp_off': 'S2', 'umbrella_open': 'S3', 'foot_contact': 'S3', 'headlights_on_face': 'S4',
           'line_start': 'S4', 'line_end': 'S4', 'lamp_on': 'S5'}
NAMES = ['COMMUTER', 'COMMUTER_RIG', 'UMBRELLA', 'PHONE', 'STREETLAMP', 'LAMP_HEAD', 'PUDDLE', 'ROAD', 'KERB', 'BUS_STOP', 'NEON_SIGN',
         'RAIN', 'BUS_LIGHTS', 'CAM_S1', 'CAM_S2', 'CAM_S3', 'CAM_S4', 'CAM_S5']


def run(ctx):
    out, tmp = pathlib.Path(ctx['out']), pathlib.Path(ctx['tmp'])
    FR = ctx['rubric']['frames']
    R, S = {}, {}          # results, shared state for postprocess
    ctx['_x07'] = S

    def guard(ids, fn):
        try:
            fn()
        except Exception as e:
            for i in ids:
                R.setdefault(i, L.F(f'check error: {type(e).__name__}: {e} | {traceback.format_exc()[-300:]}'))

    vid = {v: out / v / 'output.mp4' for v in VERS}
    have = {v: vid[v].exists() for v in VERS}
    EV = {}
    for v in VERS:
        try:
            EV[v] = L.read_events(out / v / 'events.csv')
        except Exception:
            EV[v] = None

    # ---------- B01 / B02 ----------
    def b01():
        if not have['base']:
            S['base_frames'] = -1
            R['X07-B01'] = L.F('base/output.mp4 missing'); return
        ok, d = L.video_contract(vid['base'], FPS, 720)
        try: S['base_frames'] = int(d.get('frames'))
        except Exception: S['base_frames'] = -1
        R['X07-B01'] = L.pv(None, ok, d)
    guard(['X07-B01'], b01)

    def b02():
        ds, ok = {}, True
        for v, n in (('revision1', 732), ('revision2', 726)):
            if not have[v]:
                ok = False; ds[v] = 'missing'; continue
            o, d = L.video_contract(vid[v], FPS, n); ok &= o; ds[v] = d
        R['X07-B02'] = L.pv(None, ok, ds)
    guard(['X07-B02'], b02)

    # ---------- B03 ----------
    def b03():
        ds, ok = {}, True
        for v in VERS:
            if not have[v]:
                ok = False; ds[v] = 'missing'; continue
            o, d = L.master_check(vid[v]); ok &= o; ds[v] = d
        R['X07-B03'] = L.pv(None, ok, ds)
    guard(['X07-B03'], b03)

    # ---------- B04 ----------
    stem_ok = {}
    def b04():
        bad = []
        for v in VERS:
            for f in ('output.mp4', 'timeline.json', 'events.csv'):
                if not (out / v / f).exists(): bad.append(f'{v}/{f}')
            dur = None
            try: dur = L.frame_count(vid[v]) / FPS if have[v] else None
            except Exception: pass
            ok_v = True
            for s in STEMS:
                p = out / v / 'stems' / f'{s}.wav'
                if not p.exists():
                    bad.append(f'{v}/stems/{s}.wav'); ok_v = False; continue
                try:
                    i = L.wav_info(p)
                    if not str(i['codec']).startswith('pcm_') or i['sr'] != 48000: bad.append(f'{v}/{s}: {i}')
                    if dur and abs(i['dur'] - dur) > 1.0 / FPS + 1e-3: bad.append(f'{v}/{s} len {i["dur"]:.3f} vs {dur:.3f}')
                except Exception as e:
                    bad.append(f'{v}/{s}: {e}'); ok_v = False
            stem_ok[v] = ok_v
            if v == 'base' and dur is None: pass
        for v in VERS:
            p = out / v / 'timeline.json'
            if p.exists():
                try: json.loads(p.read_text(encoding='utf-8-sig'))
                except Exception: bad.append(f'{v}/timeline.json not JSON')
        if not (out / 'project' / 'scene.blend').exists(): bad.append('project/scene.blend')
        rd = out / 'project' / 'README.md'
        if not rd.exists() or 'blender' not in rd.read_text(encoding='utf-8', errors='ignore').lower(): bad.append('project/README.md without blender command')
        S['stems_present_base'] = stem_ok.get('base', False)
        if bad:
            R['X07-B04'] = L.F('; '.join(bad[:15]))
    guard(['X07-B04'], b04)

    # ---------- B06 events ----------
    def b06():
        bad = []
        for v in VERS:
            if EV[v] is None:
                bad.append(f'{v}: events.csv missing'); continue
            hdr, ev, rows = EV[v]
            if hdr != ['event_id', 'frame', 'description']: bad.append(f'{v}: header {hdr}')
            if rows: bad.append(f'{v}: non-integer frames {rows[:3]}')
            miss = [k for k in REQ_EV if k not in ev]
            if miss: bad.append(f'{v}: missing {miss}'); continue
            fr = FR[v]
            for k, s in EV_SHOT.items():
                a, b = fr[s]
                if not (a <= ev[k] <= b): bad.append(f'{v}: {k}={ev[k]} not in {s} {fr[s]}')
            o = [ev[k] for k in REQ_EV]
            # headlights_on_face vs line_start: the instruction's synopsis and S4 row give opposite orders -> either is accepted
            if not (o[0] < o[1] < o[2] < o[3] < min(o[4], o[5]) and o[5] < o[6] < o[7] and o[4] < o[7]): bad.append(f'{v}: order {o}')
        R['X07-B06'] = L.F('; '.join(bad[:12])) if bad else L.P('header, 8 ids, shot membership and order OK in 3 versions')
    guard(['X07-B06'], b06)

    def ev(v, k):
        try: return EV[v][1][k]
        except Exception: return None

    # ---------- B07 (fail-only) ----------
    def b07():
        bad = []
        for f in ('credits.md', 'qa.md'):
            if not any(out.rglob(f)): bad.append(f'{f} missing')
        h = L.scan_credentials(out)
        if h: bad.append(f'credential-like strings in {h[:5]}')
        if bad: R['X07-B07'] = L.F('; '.join(bad))
    guard(['X07-B07'], b07)

    # ---------- picture ----------
    G = {}
    for v in VERS:
        if have[v]:
            try: G[v] = L.gray_frames(vid[v])
            except Exception: pass

    def excl_windows(v):
        w = []
        e = lambda k: ev(v, k)
        if e('lamp_flicker_start') is not None and e('lamp_off') is not None: w.append((e('lamp_flicker_start'), e('lamp_off') + 2))
        if e('lamp_on') is not None: w.append((e('lamp_on') - 2, e('lamp_on') + 2))
        if e('headlights_on_face') is not None: w.append((e('headlights_on_face') - 12, e('headlights_on_face') + 12))
        return w

    def structure(v, cuts_exp, diss):
        g = G[v]; cuts, sc = L.detect_cuts(g)
        bad = []
        ex = excl_windows(v) + [(diss[0] - 6, diss[1] + 6)]
        for c in cuts_exp:
            near = [x for x in cuts if abs(x - c) <= 1]
            if not near: bad.append(f'no hard cut at {c} (score {sc[c]:.3f})')
            else:
                x = near[0]
                nb_ = [y for y in (x - 1, min(x + 1, len(sc) - 1)) if not any(a <= y <= b for a, b in excl_windows(v))]
                if nb_ and max(sc[y] for y in nb_) > 0.5 * sc[x]: bad.append(f'blend frames around cut {x}')
        extra = [x for x in cuts if all(abs(x - c) > 1 for c in cuts_exp) and not any(a <= x <= b for a, b in ex)]
        if extra: bad.append(f'extra cuts {extra[:8]}')
        A, B = g[max(0, diss[0] - 6)].astype(np.float64), g[min(len(g) - 1, diss[1] + 6)].astype(np.float64)
        D = A - B; den = (D * D).sum() + 1e-9
        al = [float(((g[f] - B) * D).sum() / den) for f in range(diss[0] - 6, min(len(g), diss[1] + 7))]
        nb = sum(1 for a in al if 0.05 < a < 0.95) if np.abs(D).mean() >= 3 else 0
        if nb < 16: bad.append(f'dissolve blended frames {nb} < 16')
        fz = L.freezes(g)
        if fz: bad.append(f'repeated frames at {fz[:8]}')
        return bad, {'cuts': cuts[:20], 'dissolve_blended': nb}

    def m01():
        if 'base' not in G or len(G['base']) != 720:
            R['X07-M01'] = L.F('base film missing or not 720 frames'); return
        bad, d = structure('base', [144, 456, 600], FR['base']['T23_dissolve'])
        R['X07-M01'] = L.F('; '.join(bad) + f' | {d}') if bad else L.P(d)
    guard(['X07-M01'], m01)

    # ---------- audio ----------
    A = {}
    def stem(v, s):
        k = (v, s)
        if k not in A:
            A[k] = L.decode_audio(out / v / 'stems' / f'{s}.wav')
        return A[k]

    def bus_env(v):
        return L.band_env(stem(v, 'fx'), L.SR, 30, 400, 0.1, 0.05, medfilt=31)

    def bridge(v):
        B = FR[v]['bridge_onset_s']; t, e = bus_env(v)
        mask = np.ones_like(t, bool)
        fc = ev(v, 'foot_contact')
        if fc is not None: mask &= ~((t >= fc / FPS - 0.1) & (t <= fc / FPS + 0.75))
        for k in ('umbrella_open',):
            if ev(v, k) is not None: mask &= ~(np.abs(t - ev(v, k) / FPS) <= 0.25)
        w = (t >= B - 1.1) & (t <= B - 0.1) & mask
        if w.sum() < 10: w = (t >= B - 1.6) & (t <= B - 0.1) & mask
        N0 = max(float(np.median(e[w])) if w.any() else -70.0, -70.0)
        on = None
        idx = np.where(t >= B - 0.5)[0]
        for i in idx:
            if i + 6 <= len(e) and (e[i:i + 6] > N0 + 6).all(): on = float(t[i]); break
        m1 = L.win_med(t, e, B + 0.1, B + 1.0); m2 = L.win_med(t, e, B + 1.0, B + 2.0)
        ok = on is not None and abs(on - B) <= 0.08 and m1 is not None and m1 - N0 >= 10 and m2 is not None and m2 >= m1 - 6
        return ok, {'onset': on, 'target': B, 'N0': round(N0, 1), 'm1': m1 and round(m1, 1), 'm2': m2 and round(m2, 1)}

    def tail(v):
        C, E = FR[v]['T45_s'], FR[v]['tail_end_s']; t, e = bus_env(v)
        mask = np.ones_like(t, bool)
        lo = ev(v, 'lamp_on')
        if lo is not None: mask &= ~((t >= lo / FPS - 0.1) & (t <= lo / FPS + 0.5))
        ref = L.win_med(t, e, C, C + 1.0, mask)
        if ref is None: return False, {'error': 'no ref'}
        sus = True; a = C
        while a + 0.3 <= E - 0.2:
            m = L.win_med(t, e, a, a + 0.3, mask)
            if m is not None and m < ref - 10: sus = False
            a += 0.3
        thr = max(ref - 20, -70); end = None
        above = (e > thr) & mask
        for i in range(len(t) - 4, -1, -1):
            if t[i] >= C and above[i:i + 4].all(): end = float(t[i + 3]); break
        after = L.win_med(t, e, E + 0.12, t[-1], mask)
        ok = sus and end is not None and abs(end - E) <= 0.08 and (after is None or after <= ref - 20 or after < -60)
        return ok, {'end': end, 'target': E, 'ref': round(ref, 1), 'sustained': sus, 'after': after and round(after, 1)}

    def m02():
        ok, d = bridge('base'); R['X07-M02'] = L.pv(None, ok, d)
    guard(['X07-M02'], m02)

    def m03():
        ok, d = tail('base'); R['X07-M03'] = L.pv(None, ok, d)
    guard(['X07-M03'], m03)

    def m04():
        x = stem('base', 'rain'); t, e = L.env_db(x, L.SR, 0.05, 0.05)
        bad = []
        if e.size == 0 or e.min() < -50: bad.append(f'rain RMS min {e.min() if e.size else None:.1f} dBFS at {t[np.argmin(e)] if e.size else None:.2f}s')
        mix = L.decode_audio(vid['base'])
        for nm, y in (('rain', x), ('mix', mix)):
            for c in (6.0, 12.0, 19.0, 25.0):
                ok, r = L.click_check(y, L.SR, c)
                if not ok: bad.append(f'click {nm}@{c}s ratio {r}')
        R['X07-M04'] = L.F('; '.join(bad)) if bad else L.P('rain bed >= -50 dBFS throughout; no clicks at cuts')
    guard(['X07-M04'], m04)

    def m10():   # fail-only (project emission part not measured here)
        fs, fo, fn = ev('base', 'lamp_flicker_start'), ev('base', 'lamp_off'), ev('base', 'lamp_on')
        if None in (fs, fo, fn): R['X07-M10'] = L.F('lamp events missing'); return
        x = stem('base', 'fx'); n, hp = 4096, 1024
        k = 1 + (len(x) - n) // hp; wnd = np.hanning(n); fr = np.fft.rfftfreq(n, 1 / L.SR)
        sel = (fr >= 50) & (fr <= 4000)
        Sdb = np.array([10 * np.log10(np.abs(np.fft.rfft(x[i * hp:i * hp + n] * wnd)) ** 2 + 1e-14) for i in range(k)])[:, sel]
        t = (np.arange(k) * hp + n / 2) / L.SR
        pre = (t >= fs / FPS - 2) & (t < fs / FPS)
        if not pre.any(): R['X07-M10'] = L.F('no pre-flicker window'); return
        avg = Sdb[pre].mean(0)
        pad = np.pad(avg, 15, mode='edge'); base = np.median(np.lib.stride_tricks.sliding_window_view(pad, 31), axis=1)[:len(avg)]
        prom = avg - base; pk = np.where(prom >= 6)[0]
        if pk.size == 0: R['X07-M10'] = L.F('no narrow-band lamp hum (>=6 dB prominence) before flicker'); return
        lev = 10 * np.log10((10 ** (Sdb[:, pk] / 10)).sum(1))
        Lpre = float(np.median(lev[pre]))
        off = (t >= (fo + 3) / FPS) & (t <= (fn - 1) / FPS)
        on = (t >= (fn + 3) / FPS) & (t <= (fn + 3) / FPS + 0.3)
        Loff = float(np.median(lev[off])) if off.any() else None
        Lon = float(np.median(lev[on])) if on.any() else None
        ok = Loff is not None and Loff <= Lpre - 10 and Lon is not None and Lon >= Lpre - 6
        d = {'hum_bins_hz': [round(float(f)) for f in fr[sel][pk][:6]], 'pre': round(Lpre, 1), 'off': Loff and round(Loff, 1), 'on': Lon and round(Lon, 1)}
        if not ok: R['X07-M10'] = L.F(d)
        else: S['m10_audio'] = d          # project emission part decided in project()
    guard(['X07-M10'], m10)

    def m11():
        uo = ev('base', 'umbrella_open')
        if uo is None: R['X07-M11'] = L.F('umbrella_open missing'); return
        u = uo / FPS; x = stem('base', 'rain') + stem('base', 'fx')
        t, e = L.band_env(x, L.SR, 1000, 6000, 0.05, 0.025)
        # spectral flux 10 ms
        n, hp = 480, 480; k = 1 + (len(x) - n) // hp; fr = np.fft.rfftfreq(n, 1 / L.SR); sel = (fr >= 1000) & (fr <= 6000)
        M = np.array([np.abs(np.fft.rfft(x[i * hp:i * hp + n] * np.hanning(n)))[sel] for i in range(k)])
        fl = np.r_[0, np.maximum(np.diff(M, axis=0), 0).sum(1)]; tf = (np.arange(k) * hp + n / 2) / L.SR
        med = np.median(fl); mad = np.median(np.abs(fl - med)) + 1e-12
        pk = np.where((fl[1:-1] > fl[:-2]) & (fl[1:-1] >= fl[2:]) & (fl[1:-1] > med + 3 * mad))[0] + 1
        def dens(a, b): return ((tf[pk] >= a) & (tf[pk] <= b)).sum() / max(b - a, 1e-3)
        def step(c):
            a, b = L.win_med(t, e, c + 0.3, c + 1.5), L.win_med(t, e, c - 1.2, c - 0.1)
            dp = dens(c + 0.3, c + 1.5)
            return (a - b) if a is not None and b is not None else -99, (dp / max(dens(c - 1.2, c - 0.1), 1.0)) if dp >= 2.0 else 0.0
        lv, dr = step(u)
        ok = lv >= 3 or dr >= 1.5
        taus = np.arange(u - 1.5, u + 1.51, 0.05)
        sv = [step(c) for c in taus]
        key = 0 if lv >= 3 else 1
        best = float(taus[int(np.argmax([s[key] for s in sv]))])
        ok = ok and abs(best - u) <= 0.5
        R['X07-M11'] = L.pv(None, ok, {'level_db': round(lv, 2), 'transient_ratio': round(dr, 2), 'change_at': round(best, 2), 'umbrella_open_s': round(u, 2)})
    guard(['X07-M11'], m11)

    # ---------- M05 line timing (energy VAD on the speech stem; no ASR in the grader) ----------
    def m05():
        bad, info = [], {}
        for v in VERS:
            ls, le = ev(v, 'line_start'), ev(v, 'line_end')
            if ls is None or le is None: bad.append(f'{v}: line_start/line_end missing'); continue
            p = out / v / 'stems' / 'speech.wav'
            if not p.exists(): bad.append(f'{v}: speech stem missing'); continue
            t, e = L.env_db(stem(v, 'speech'), L.SR, 0.1, 0.01)
            i = np.where(e > -40)[0]
            if not i.size: bad.append(f'{v}: no speech above -40 dBFS'); continue
            on, off = float(t[i[0]] - 0.05), float(t[i[-1]] + 0.05)
            a, b = FR[v]['S4']; dur = off - on
            info[v] = {'on_f': round(on * FPS, 1), 'off_f': round(off * FPS, 1), 'decl': [ls, le], 'dur_s': round(dur, 2)}
            if abs(on * FPS - ls) > 6 or abs(off * FPS - le) > 6: bad.append(f'{v}: VAD {on * FPS:.1f}-{off * FPS:.1f} f vs declared {ls}-{le} (>6 f)')
            if on * FPS < a - 0.5 or off * FPS > b + 1.5: bad.append(f'{v}: phrase {on * FPS:.1f}-{off * FPS:.1f} f not inside S4 {a}-{b}')
            if not 1.8 <= dur <= 4.5: bad.append(f'{v}: phrase length {dur:.2f} s not in 1.8-4.5 s')
        R['X07-M05'] = L.F('; '.join(bad)) if bad else L.P(info)
    guard(['X07-M05'], m05)

    # ---------- M16 + sound gate ----------
    def m16():
        bad, res = [], {}
        for v in VERS:
            sp = {s: out / v / 'stems' / f'{s}.wav' for s in STEMS}
            if not have[v] or not all(p.exists() for p in sp.values()):
                bad.append(f'{v}: film/stems missing'); res[v] = None; continue
            cands = []
            try: cands = L.find_gain_sets(json.loads((out / v / 'timeline.json').read_text(encoding='utf-8-sig')), STEMS)
            except Exception: pass
            best = None
            for g in cands + [{s: 1.0 for s in STEMS}]:
                r = L.stem_sum_bandcheck(vid[v], sp, g)
                if r and (best is None or r['median'] < best[0]['median']): best = (r, g)
            if best is None:
                bad.append(f'{v}: band comparison impossible (silent/short)'); res[v] = None; continue
            r, g = best
            ok = r['median'] <= 0.75 and r['p95'] <= 3.0
            res[v] = {'median': round(r['median'], 2), 'p95': round(r['p95'], 2), 'ok': ok}
            if not ok: bad.append(f"{v}: band diff median {r['median']:.2f} dB (<=0.75), p95 {r['p95']:.2f} dB (<=3), lag {r['lag']}; gains {g}; declared sets {len(cands)}")
        S['residual'] = res
        R['X07-M16'] = L.F('; '.join(bad)) if bad else L.P(res)
    guard(['X07-M16'], m16)

    # ---------- revisions (fail-only) ----------
    def onset_speech(v):
        t, e = L.env_db(stem(v, 'speech'), L.SR, 0.1, 0.01)
        i = np.where(e > -40)[0]
        return float(t[i[0]] - 0.05) if i.size else None

    def m08():
        bad = []
        if not all(v in G for v in ('base', 'revision1')): R['X07-M08'] = L.F('films missing'); return
        b, r = G['base'], G['revision1']
        if len(r) != 732: bad.append(f'rev1 frames {len(r)}')
        else:
            lo = [f for f in range(0, 276) if L.psnr(r[f], b[f]) < 28]
            if lo: bad.append(f'rev1 differs from base at {lo[:5]}')
            hi = [f for f in range(300, 720) if L.psnr(r[f + 12], b[f]) < 28]
            if len(hi) > 0: bad.append(f'rev1[f+12]!=base[f] at {hi[:5]} (n={len(hi)})')
            fz = [f for f in L.freezes(r[275:289]) if f > 0]
            fz = [275 + f for f in fz]
            if fz: bad.append(f'freeze in S2 extension {fz}')
            if L.ssim(r[281], b[275]) < 0.6: bad.append('extension not same set-up as S2')
        e0, e1 = EV['base'], EV['revision1']
        if e0 and e1:
            for k in ('umbrella_open', 'foot_contact', 'headlights_on_face', 'line_start', 'line_end', 'lamp_on'):
                if k in e0[1] and k in e1[1] and abs(e1[1][k] - e0[1][k] - 12) > 1: bad.append(f'event {k} not +12')
        try:
            ab = L.decode_audio(vid['base']); ar = L.decode_audio(vid['revision1']); sr = L.SR
            n = int(11.5 * sr); c = np.corrcoef(ab[:n], ar[:n])[0, 1]
            if c < 0.99: bad.append(f'audio <11.5s corr {c:.3f}')
            a0, a1 = int(12.5 * sr), min(len(ab), int(30 * sr), len(ar) - int(0.5 * sr))
            c2 = np.corrcoef(ab[a0:a1], ar[a0 + int(0.5 * sr):a1 + int(0.5 * sr)])[0, 1]
            if c2 < 0.95: bad.append(f'audio after 12.5s not delayed 0.5s (corr {c2:.3f})')
        except Exception as ex:
            bad.append(f'audio compare error {ex}')
        ok, d = bridge('revision1')
        if not (d.get('onset') and 18.42 <= d['onset'] <= 18.58): bad.append(f'rev1 bridge {d}')
        ok, d = tail('revision1')
        if not (d.get('end') and 26.92 <= d['end'] <= 27.08): bad.append(f'rev1 tail {d}')
        cuts, _ = L.detect_cuts(r)
        for c in (144, 468, 612):
            if not any(abs(x - c) <= 1 for x in cuts): bad.append(f'rev1 no cut at {c}')
        R['X07-M08'] = L.F('; '.join(bad[:10])) if bad else L.P('rev1: 732 frames, 0-275 = base, extension moving, +12 shift in picture/events/audio, bridge/tail/cuts OK')
    guard(['X07-M08'], m08)

    def m09():
        bad = []
        if not all(v in G for v in ('revision1', 'revision2')): R['X07-M09'] = L.F('films missing'); return
        r1, r2 = G['revision1'], G['revision2']
        if len(r2) != 726: bad.append(f'rev2 frames {len(r2)}')
        else:
            lo = [f for f in range(0, 468) if L.psnr(r2[f], r1[f]) < 28]
            if lo: bad.append(f'rev2 != rev1 before 468 at {lo[:5]}')
            if len(r1) >= 732:
                hi = [f for f in range(468, 726) if L.psnr(r2[f], r1[f + 6]) < 28]
                if hi: bad.append(f'rev2[f]!=rev1[f+6] at {hi[:5]} (n={len(hi)})')
            cuts, _ = L.detect_cuts(r2)
            for c in (468, 606):
                if not any(abs(x - c) <= 1 for x in cuts): bad.append(f'rev2 no cut at {c}')
        try:
            o1, o2 = onset_speech('revision1'), onset_speech('revision2')
            if o1 is None or o2 is None or abs((o1 - o2) - 0.25) > 0.02: bad.append(f'speech onset r1 {o1} r2 {o2}')
        except Exception as ex: bad.append(f'speech err {ex}')
        for s in ('fx', 'rain'):
            ok, rr = L.click_check(stem('revision2', s), L.SR, 19.5)
            if not ok: bad.append(f'click {s}@19.5 ({rr})')
        ok, d = tail('revision2')
        if not (d.get('end') and 26.67 <= d['end'] <= 26.83): bad.append(f'rev2 tail {d}')
        ok, d = bridge('revision2')
        if not (d.get('onset') and 18.42 <= d['onset'] <= 18.58): bad.append(f'rev2 bridge {d}')
        e1, e2 = EV['revision1'], EV['revision2']
        if e1 and e2:
            for k in ('headlights_on_face', 'line_start', 'line_end', 'lamp_on'):
                if k in e1[1] and k in e2[1] and e1[1][k] >= 474 and abs(e1[1][k] - e2[1][k] - 6) > 1: bad.append(f'event {k} not -6')
        R['X07-M09'] = L.F('; '.join(bad[:10])) if bad else L.P('rev2: 726 frames, = rev1 before 468, rev2[f]=rev1[f+6], cuts 468/606, line -0.25 s, bridge/tail OK, no click')
    guard(['X07-M09'], m09)

    # ---------- G05 / G07 / G09 (fail-only) ----------
    def g05():
        fc = ev('base', 'foot_contact')
        if fc is None: R['X07-G05'] = L.F('foot_contact missing'); return
        ok, r = L.transient_at(stem('base', 'fx'), L.SR, fc / FPS, 2 / FPS, 10.0, 0.2)
        if not ok: R['X07-G05'] = L.F(f'no fx transient >=10 dB at foot_contact±2f (rise {r} dB)')
        else: S['g05_audio'] = f'fx transient +{r} dB at foot_contact'      # geometry part decided in project()
    guard(['X07-G05'], g05)

    def g07():
        if not have['base']: R['X07-G07'] = L.F('no base film'); return
        g = L.gray_frames(vid['base'], 640, 360); fr = FR['base']; idx = {}
        for s in ('S1', 'S2', 'S3', 'S4', 'S5'):
            a, b = fr[s]; vals = [L.flat_block_index(g[f], bs=16, std_thr=0.2, dark=8) for f in np.linspace(a + 3, b - 3, 5).astype(int) if f < len(g)]
            idx[s] = round(float(np.mean(vals)), 3) if vals else None
        S['flat'] = idx
        if any(v is None or v > 0.15 for v in idx.values()): R['X07-G07'] = L.F(f'flat-block index per shot {idx}')
    guard(['X07-G07'], g07)

    def g09():
        if 'base' not in G: R['X07-G09'] = L.F('base film missing/undecodable'); return
        g = G['base']; m = g.reshape(len(g), -1).mean(1)
        ex = excl_windows('base') + [(143, 145), (270, 305), (455, 457), (599, 601)]
        bad = [f for f in range(1, len(m)) if abs(m[f] - m[f - 1]) / max(m[f - 1], 1.0) > 0.04 and not any(a <= f <= b for a, b in ex)]
        R['X07-G09'] = L.F(f'luma jumps >4% at frames {bad[:10]}') if bad else L.P('no in-shot global luma jump >4% outside the declared light-change windows')
    guard(['X07-G09'], g09)

    # ---------- project (.blend) ----------
    BLEND_IDS = ('X07-B05', 'X07-M06', 'X07-M07', 'X07-M10', 'X07-M12', 'X07-M13', 'X07-M14', 'X07-M15', 'X07-M17',
                 'X07-G01', 'X07-G02', 'X07-G03', 'X07-G04', 'X07-G05', 'X07-G06')

    def project():
        blend = L.find_blend(out)
        if not blend:
            S['blend'] = 'missing'
            for i in BLEND_IDS + ('X07-B04',):
                R.setdefault(i, L.F('project/scene.blend missing'))
            return
        tf = sorted(set([72, 660] + list(range(288, 456, 6)) + list(range(456, 600, 6))))
        evb = (EV.get('base') or (None, {}, None))[1] or {}
        cfg = {'rigs': {'COMMUTER_RIG': 'COMMUTER'},
               'cams': {'CAM_S1': [0, 143], 'CAM_S2': [144, 287], 'CAM_S3': [288, 455], 'CAM_S4': [456, 599], 'CAM_S5': [600, 719]},
               'track': ['COMMUTER', 'PUDDLE', 'STREETLAMP', 'BUS_STOP'], 'track_frames': tf,
               'mouth': {'COMMUTER_RIG': ['COMMUTER', 456, 599]},
               # base state: the instruction defines base = rev props 0/0; the file may have been saved in any state
               'set_props': {'rev_s2_hold_frames': 0, 'rev_s4_trim_frames': 0},
               'film_frames': True,
               'extra_py': str(pathlib.Path(__file__).with_name('x07_extra_dump.py')),
               'events': {k: evb.get(k) for k in REQ_EV}, 'frames': FR['base'], 'budget_s': 900}
        D = L.blender_dump(blend, cfg, tmp, timeout=1500)
        if D is None:
            S['blend'] = 'no-blender'
            for i in BLEND_IDS + ('X07-B04',):
                R[i] = {'verdict': 'error', 'detail': 'grader image has no `blender`; .blend measurements impossible'}
            return
        S['blend'] = D
        if '_error' in D or 'objects' not in D:
            for i in BLEND_IDS + ('X07-B04',):
                R[i] = L.F(f'blender could not open/inspect scene.blend: {str(D)[:400]}')
            return
        X = D.get('x07') or {}
        errs = [e for e in D.get('errors', []) if e.startswith(('x07', 'extra', 'set_props'))]
        S['dump_errors'] = errs[:5]
        # B04 blend part (+ simulation caches)
        if 'X07-B04' not in R:
            cch = X.get('caches')
            badc = [c for c in (cch or []) if not c['ok']]
            if D.get('n_missing', 0) or D.get('_rc') not in (0, None):
                R['X07-B04'] = L.F(f'missing files {D.get("missing_files")}, rc {D.get("_rc")}')
            elif cch is None:
                R['X07-B04'] = L.F(f'simulation cache inspection failed: {errs[:1]}')
            elif badc:
                R['X07-B04'] = L.F(f'simulation caches not shipped: {badc[:5]}')
            else:
                R['X07-B04'] = L.P(f'all deliverables present; stems 48k PCM; scene.blend opens, no missing files; {len(cch)} simulation caches baked')
        if D.get('url_refs'): R['X07-B07'] = L.F(f'URL media refs {D["url_refs"]}')
        ob = D['objects']; miss = [n for n in NAMES if n not in ob]
        typ = [n for n in NAMES if n in ob and ((n == 'COMMUTER_RIG' and ob[n]['type'] != 'ARMATURE') or (n.startswith('CAM_') and ob[n]['type'] != 'CAMERA'))]
        props = [p for p in ('rev_s2_hold_frames', 'rev_s4_trim_frames') if p not in D.get('scene_props', {})]
        S['props_missing'] = props
        R['X07-B05'] = L.pv(None, not miss and not typ and not props, {'missing': miss, 'bad_type': typ, 'props_missing': props})
        rig = (D.get('rigs') or {}).get('COMMUTER_RIG', {})
        S['char_bound'] = bool(rig.get('char_bound'))
        hands = rig.get('hands', [])
        # M13: rig binding, finger chains moving in S3-S4 (sampled pose), real 3D character geometry
        bad = []
        if not rig.get('char_bound'): bad.append('COMMUTER not deformed by COMMUTER_RIG')
        elif (rig.get('vg_cover') or 0) < 0.9: bad.append(f'vertex-group cover {rig.get("vg_cover")}')
        mv = ((X.get('props_summary') or {}).get('finger_bones_moving_S3S4') or {})
        if not any(h['chains'] >= 4 and mv.get(h['hand'], 0) >= 4 for h in hands):
            bad.append(f'no hand with >=4 finger chains of >=3 bones and >=4 finger bones moving in S3-S4: chains {hands}, moving {mv}')
        cg = X.get('commuter_geo') or {}
        if not cg.get('n_verts') or cg['n_verts'] < 500 or not cg.get('dims') or min(cg['dims']) < 0.1:
            bad.append(f'COMMUTER is not a 3D character mesh (verts {cg.get("n_verts")}, dims {cg.get("dims")})')
        R['X07-M13'] = L.F('; '.join(bad)) if bad else L.P({'vg_cover': rig.get('vg_cover'), 'hands': hands, 'moving': mv, 'geo': cg})
        # M06 cameras
        cams = D.get('cams') or {}; tr = D.get('tracks') or {}
        def P(c): return np.array([r[1] for r in c]), np.array([r[2] for r in c]), np.array([r[3] for r in c])
        bad, info = [], {}
        try:
            if any(cams.get(c) is None for c in ('CAM_S1', 'CAM_S2', 'CAM_S3', 'CAM_S4')): raise ValueError('camera missing')
            def ang(fw): return math.degrees(max(math.acos(max(-1, min(1, float(np.dot(fw[0], f) / (np.linalg.norm(fw[0]) * np.linalg.norm(f)))))) for f in fw))
            p, fw, ln = P(cams['CAM_S1']); pit = L.cam_pitch_deg(fw.mean(0))
            info['S1'] = [round(pit, 1), round(float(p[:, 2].mean()), 2)]
            r0 = cams['CAM_S1'][0]
            if not (pit <= -10 and p[:, 2].mean() >= 3 and np.ptp(p, 0).max() < 0.01 and ang(fw) < 0.2 and (not r0[4] or r0[5] >= 5.6)): bad.append(f'S1 {info["S1"]}')
            if np.ptp(ln) / ln.mean() >= 0.01: bad.append('S1 focal change')
            p, fw, ln = P(cams['CAM_S2']); pit = L.cam_pitch_deg(fw.mean(0)); r0 = cams['CAM_S2'][0]
            pz = tr.get('PUDDLE')[0][1][2] if tr.get('PUDDLE') else 0.0
            info['S2'] = [round(pit, 1), round(float(p[:, 2].mean() - pz), 3)]
            if not (-45 <= pit <= 10 and p[:, 2].mean() - pz <= 0.5 and np.ptp(p, 0).max() < 0.01 and ang(fw) < 0.2 and r0[4] and r0[5] <= 4): bad.append(f'S2 {info["S2"]} dof {r0[4:6]}')
            if np.ptp(ln) / ln.mean() >= 0.01: bad.append('S2 focal change')
            p, fw, ln = P(cams['CAM_S3']); disp = p[-1] - p[0]; dh = disp.copy(); dh[2] = 0
            ax = fw.mean(0); ax[2] = 0; ax /= (np.linalg.norm(ax) + 1e-9)
            perp = np.linalg.norm(dh - np.dot(dh, ax) * ax)
            ch = tr.get('COMMUTER'); cdir = None
            if ch:
                cs = [r for r in ch if 288 <= r[0] <= 455]
                if len(cs) >= 2: cdir = np.array(cs[-1][1]) - np.array(cs[0][1]); cdir[2] = 0
            same = cdir is not None and np.dot(cdir, dh) > 0
            info['S3'] = [round(float(p[:, 2].mean()), 2), round(float(np.linalg.norm(dh)), 2), round(float(perp / (np.linalg.norm(dh) + 1e-9)), 2), bool(same)]
            if not (1.2 <= p[:, 2].mean() <= 1.9 and np.linalg.norm(dh) >= 0.4 and perp >= 0.7 * np.linalg.norm(dh) and same): bad.append(f'S3 {info["S3"]}')
            if np.ptp(ln) / ln.mean() >= 0.01: bad.append('S3 focal change')
            p, fw, ln = P(cams['CAM_S4']); pit = L.cam_pitch_deg(fw.mean(0)); r0 = cams['CAM_S4'][0]
            dd = None
            if ch:
                cs = {r[0]: np.array(r[1]) for r in ch if 456 <= r[0] <= 599}
                if cs:
                    f0, f1 = min(cs), max(cs); cr = {r[0]: np.array(r[1]) for r in cams['CAM_S4']}
                    dd = float(np.linalg.norm(cr[f0] - cs[f0]) - np.linalg.norm(cr[f1] - cs[f1]))
            info['S4'] = [round(pit, 1), dd and round(dd, 3), r0[4:6]]
            if not (2 <= pit <= 25 and dd is not None and dd >= 0.08 and r0[4] and r0[5] <= 4): bad.append(f'S4 {info["S4"]}')
            if np.ptp(ln) / ln.mean() >= 0.01: bad.append('S4 focal change')
        except Exception as e:
            bad.append(f'camera export error {e}')
        R['X07-M06'] = L.F('; '.join(bad) + ' | proxy: COMMUTER bbox centre for root/head') if bad else L.P(info)

        # ----- shared film data for picture measurements -----
        e = lambda k: evb.get(k)
        fs, lo, lon, uo, fc, hl, ls, le = (e(k) for k in REQ_EV[:2] + ['lamp_on', 'umbrella_open', 'foot_contact', 'headlights_on_face', 'line_start', 'line_end'])
        PJ = X.get('proj') or {}; PF = X.get('proj_frames') or {}
        Fb = FR['base']
        lamp = {int(k): v for k, v in (X.get('lamp') or {}).items()}

        def lamp_norm():
            """normalised lamp state per frame: max over animated components (light energy, emission) of value/on-level."""
            if not lamp or fs is None: return {}
            pre = [f for f in lamp if fs - 48 <= f < fs]
            if not pre: return {}
            comps = []
            for c in ('light', 'emis'):
                on = float(np.median([lamp[f][c] for f in pre]))
                if on > 1e-9: comps.append((c, on))
            if not comps: return {}
            return {f: max(lamp[f][c] / on for c, on in comps) for f in lamp}
        LS = lamp_norm()
        S['lamp_state'] = {k: round(v, 3) for k, v in sorted(LS.items())[::6]}

        need = set()
        a1, b5 = PF.get('g01_s1'), PF.get('g01_s5')
        for f in (a1, b5, PF.get('g06_s1'), 380):
            if f is not None: need.add(int(f))
        if lon is not None: need.add(max(Fb['S5'][0], lon - 3))
        if lo is not None: need |= set(range(Fb['S2'][0], min(lo + 13, Fb['T23_dissolve'][0])))
        if hl is not None: need |= set(range(max(Fb['S4'][0], hl - 12), min(Fb['S4'][1], hl + 12) + 1))
        a7, b7 = PF.get('m07_s1'), PF.get('m07_s5')
        win7 = {}
        if a7 is not None and b7 is not None and fs is not None and lon is not None:
            hi1 = min(fs - 1, Fb['S1'][1]); lo5 = max(lon + 1, Fb['S5'][0])
            win7['a'] = [f for f in range(a7 - 4, a7 + 5) if Fb['S1'][0] <= f <= hi1]
            win7['b'] = [f for f in range(b7 - 4, b7 + 5) if lo5 <= f <= Fb['S5'][1]]
            need |= set(win7['a']) | set(win7['b'])
        RGB = {}
        try:
            if have['base']: RGB = L.frames_at(vid['base'], sorted(need), 640, 360)
        except Exception as ex:
            S['rgb_error'] = str(ex)

        def Y(img): return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722

        def rect_mask(rc, shape, dil=0, s=0.5):
            h, w = shape; m = np.zeros(shape, bool)
            if not rc: return m
            x0, y0, x1, y1 = [int(round(v * s)) for v in rc]
            x0, y0 = max(0, x0 - dil), max(0, y0 - dil); x1, y1 = min(w, x1 + dil + 1), min(h, y1 + dil + 1)
            if x1 > x0 and y1 > y0: m[y0:y1, x0:x1] = True
            return m

        # ----- M07 return set-up (camera/object part + masked SSIM) -----
        try:
            bad = []
            p1, f1, l1 = P(cams['CAM_S1']); p5, f5, l5 = P(cams['CAM_S5'])
            dp = float(np.linalg.norm(p1.mean(0) - p5.mean(0)))
            da = math.degrees(math.acos(max(-1, min(1, float(np.dot(f1.mean(0), f5.mean(0)) / (np.linalg.norm(f1.mean(0)) * np.linalg.norm(f5.mean(0))))))))
            if dp > 0.02 or da > 1 or abs(l1.mean() - l5.mean()) > 1: bad.append(f'CAM_S5 vs CAM_S1 {dp:.3f} m {da:.2f} deg lens {l1.mean():.1f}/{l5.mean():.1f}')
            for n in ('STREETLAMP', 'PUDDLE', 'BUS_STOP'):
                rr = {r[0]: np.array(r[1]) for r in (tr.get(n) or [])}
                if 72 in rr and 660 in rr and np.linalg.norm(rr[72] - rr[660]) >= 0.01: bad.append(f'{n} moved')
            ss = None
            wa, wb = [RGB[f] for f in win7.get('a', []) if f in RGB], [RGB[f] for f in win7.get('b', []) if f in RGB]
            if len(wa) < 5 or len(wb) < 5:
                bad.append(f'cannot build 9-frame lit medians for S1/S5 (frames {win7})')
            else:
                A = Y(np.median(np.stack(wa), 0)); B = Y(np.median(np.stack(wb), 0))
                m = rect_mask((PJ.get('m07_s1') or {}).get('COMMUTER'), A.shape, 4) | rect_mask((PJ.get('m07_s5') or {}).get('COMMUTER'), A.shape, 4)
                ss = ssim_masked(A, B, ~m)
                if ss is None or ss < 0.70: bad.append(f'masked SSIM S1 vs S5 {ss}')
            R['X07-M07'] = L.F('; '.join(bad)) if bad else L.P(f'CAM_S5 = CAM_S1 ({dp:.3f} m, {da:.2f} deg); set static; masked SSIM {ss:.3f}')
        except Exception as ex:
            R['X07-M07'] = L.F(f'return set-up measure error {ex}')

        # ----- M12 lip sync (rev props forced to 0/0 before sampling) -----
        try:
            mo = (D.get('mouth') or {}).get('COMMUTER_RIG')
            if not mo or ls is None or le is None:
                R['X07-M12'] = L.F(f'no mouth curve / line events (mouth {bool(mo)})')
            else:
                cur = np.array(mo['curve']); a0 = mo['start']
                sp = stem('base', 'speech'); spf = int(L.SR / FPS)
                env = np.array([np.sqrt(np.mean(sp[f * spf:(f + 1) * spf] ** 2) + 1e-12) for f in range(ls, le + 1)])
                m = cur[max(0, ls - a0):max(0, le - a0 + 1)]
                best = -1
                for lag in range(-2, 3):
                    a = m[max(0, lag):len(m) + min(0, lag)]; b = env[max(0, -lag):len(env) - max(0, lag)]
                    n = min(len(a), len(b)); a, b = a[:n], b[:n]
                    if n > 5 and np.std(a) > 1e-6 and np.std(b) > 1e-9: best = max(best, float(np.corrcoef(a, b)[0, 1]))
                R['X07-M12'] = (L.F if best < 0.4 else L.P)(f'mouth/speech correlation {best:.2f} (need >=0.4, lag <=2 f); sources {mo.get("sources")}')
        except Exception as ex:
            R['X07-M12'] = L.F(f'lip-sync measure error {ex}')

        # ----- M10 project part: LAMP_HEAD energy follows lamp_off / lamp_on -----
        def lamp_off_ok():
            if not LS or lo is None or lon is None: return False, f'no lamp energy curve (objects {X.get("lamp_objects")})'
            offs = [f for f in LS if lo + 1 <= f <= lon - 1]
            on_after = LS.get(lon + 1)
            drop = next((f for f in range(lo - 6, lo + 7) if all(LS.get(g, 1) <= 0.05 for g in range(f, lo + 7) if g in LS)), None)
            d = {'off_span_max': round(max(LS[f] for f in offs), 3) if offs else None, 'at_lamp_on+1': on_after and round(on_after, 3),
                 'at_lamp_on-2': LS.get(lon - 2) and round(LS[lon - 2], 3), 'final_drop_frame': drop, 'lamp_off': lo}
            ok = bool(offs) and max(LS[f] for f in offs) <= 0.05 and on_after is not None and on_after >= 0.8 and \
                LS.get(lon - 2, 0) <= 0.05 and drop is not None and abs(drop - lo) <= 1
            return ok, d
        try:
            ok, d = lamp_off_ok()
            if 'X07-M10' not in R:
                R['X07-M10'] = L.pv(None, ok, {'audio': S.get('m10_audio'), 'emission': d})
        except Exception as ex:
            R.setdefault('X07-M10', L.F(f'lamp curve error {ex}'))

        # ----- M14 umbrella / phone handling -----
        try:
            ps = X.get('props_summary') or {}
            bad = []
            dims = {int(k): v for k, v in (ps.get('umbrella_mid_dim') or {}).items()}
            if uo is None or not dims: bad.append(f'no umbrella size samples (umbrella_open {uo})')
            else:
                bef = [v for f, v in dims.items() if f <= uo - 6]; aft = [v for f, v in dims.items() if f >= uo + 6]
                if not bef or not aft: bad.append('umbrella samples missing before/after umbrella_open')
                else:
                    op = float(np.median(aft))
                    if max(bef) >= 0.5 * op: bad.append(f'umbrella not closed before open: {max(bef):.3f} vs open {op:.3f} m')
                    if min(aft) < 0.8 * op: bad.append(f'umbrella does not stay open (min {min(aft):.3f} vs {op:.3f} m)')
            hd = ps.get('umbrella_hand_dist_max')
            if not ps.get('umbrella_hand_link') and (hd is None or hd[0] > 0.06): bad.append(f'umbrella not hand-held in S3-S4 (max hand dist {hd}, no hand-bone parent/constraint)')
            if ps.get('phone_hand_dist_max') is None or ps['phone_hand_dist_max'] > 0.05: bad.append(f'phone-hand distance during line {ps.get("phone_hand_dist_max")} (<=0.05)')
            if ps.get('phone_head_dist_max') is None or ps['phone_head_dist_max'] > 0.25: bad.append(f'phone-head distance during line {ps.get("phone_head_dist_max")} (<=0.25)')
            for nm in ('UMBRELLA', 'PHONE'):
                j = ps.get(nm + '_max_jump')
                if j and j[0] >= 0.15: bad.append(f'{nm} jumps {j[0]:.2f} m at frame {j[1]}')
            R['X07-M14'] = L.F('; '.join(bad)) if bad else L.P({k: ps.get(k) for k in ('umbrella_hand_link', 'umbrella_hand_dist_max', 'phone_hand_dist_max', 'phone_head_dist_max', 'UMBRELLA_max_jump', 'PHONE_max_jump')})
        except Exception as ex:
            R['X07-M14'] = L.F(f'prop measure error {ex}')

        # ----- rain (G03, M15) -----
        rain = X.get('rain') or {}
        r72, r660 = rain.get('72') or {}, rain.get('660') or {}

        def rain_resid(frames, gdir=None):
            g = G.get('base')
            if g is None: return None
            fr_ = [f for f in frames if 2 <= f < len(g) - 2]
            if not fr_: return None
            fracs, J = [], np.zeros(3)
            for f in fr_:
                med = np.median(g[f - 2:f + 3].astype(np.float32), 0)
                rs = np.clip(g[f].astype(np.float32) - med, 0, None)
                fracs.append(float((rs > 6).mean()))
                gy, gx = np.gradient(rs)
                J += [float((gx * gx).sum()), float((gy * gy).sum()), float((gx * gy).sum())]
            jxx, jyy, jxy = J
            tr_ = jxx + jyy + 1e-12
            l1 = tr_ / 2 + math.sqrt(((jxx - jyy) / 2) ** 2 + jxy ** 2); l2 = tr_ - l1
            coh = (l1 - l2) / tr_
            th = 0.5 * math.atan2(2 * jxy, jxx - jyy)          # dominant gradient direction
            streak = (-math.sin(th), math.cos(th))              # streaks run perpendicular to it
            angle = None
            if gdir and (gdir[0] or gdir[1]):
                gn = math.hypot(*gdir); c = abs(streak[0] * gdir[0] + streak[1] * gdir[1]) / gn
                angle = math.degrees(math.acos(min(1, c)))
            return {'frac_med': float(np.median(fracs)), 'coherence': round(coh, 3), 'angle_to_gravity': angle and round(angle, 1)}
        try:
            bad = []
            n72 = r72.get('drops_frustum_est'); sp_ = r72.get('fall_speed_med')
            if n72 is None or n72 < 2000: bad.append(f'drops in CAM_S1 frustum at 72: {n72} ({r72.get("kind")}) < 2000')
            if sp_ is None or not 4 <= sp_ <= 12: bad.append(f'median fall speed {sp_} m/s not in 4-12')
            if X.get('overlay_flags'): bad.append(f'2D rain overlay suspects {X["overlay_flags"]}')
            gdir = (PJ.get('g01_s1') or {}).get('gravity_dir')
            lit1 = list(range(4, (fs - 2) if fs else 140, max(1, ((fs or 140) - 6) // 10)))[:12]
            rr = rain_resid(lit1, gdir)
            if rr is None or rr['frac_med'] < 0.0005: bad.append(f'no moving rain detail in S1 picture {rr}')
            elif rr['coherence'] < 0.2 or rr['angle_to_gravity'] is None or rr['angle_to_gravity'] > 25: bad.append(f'rain in picture not gravity-aligned streaks {rr}')
            R['X07-G03'] = L.F('; '.join(bad)) if bad else L.P({'n72': n72, 'kind': r72.get('kind'), 'speed': round(sp_, 2), 'picture': rr})
        except Exception as ex:
            R['X07-G03'] = L.F(f'rain measure error {ex}')
        try:
            bad = []
            n72 = r72.get('drops_frustum_est'); n660 = r660.get('drops_frustum_est')
            ratio = (n660 / n72) if (n72 and n660 is not None) else None
            if ratio is None or not 0.10 <= ratio <= 0.70 or not n660: bad.append(f'S5/S1 drops in frustum {n660}/{n72} = {ratio} (need 0.10-0.70)')
            rr = rain_resid(list(range(Fb['S5'][0] + 4, Fb['S5'][1] - 3, 10)))
            if rr is None or rr['frac_med'] < 0.0002: bad.append(f'no rain visible in S5 picture {rr}')
            R['X07-M15'] = L.F('; '.join(bad)) if bad else L.P(f'S5/S1 rain {n660}/{n72} = {ratio:.2f}; picture {rr}')
        except Exception as ex:
            R['X07-M15'] = L.F(f'rain ratio error {ex}')

        # ----- G01 wet-road highlight -----
        def highlight(img, pj):
            if not pj or 'mirror' not in pj: return False, {'error': 'no mirror projection (LAMP_HEAD/ROAD/camera missing)'}
            Yi = Y(img.astype(np.float64)); h, w = Yi.shape
            px, py = pj['mirror'][0] * 0.5, pj['mirror'][1] * 0.5
            if pj['mirror'][2] <= 0 or not (0 <= px < w and 0 <= py < h): return False, {'error': f'mirror point outside frame ({px:.0f},{py:.0f})'}
            yy, xx = np.mgrid[0:h, 0:w]
            roi = (np.abs(yy - py) <= 15) & (np.abs(xx - px) <= 7.5)
            rr_ = np.hypot(yy - py, xx - px); ring = (rr_ >= 40) & (rr_ <= 100)
            ref = max(float(np.median(Yi[ring])), 1.0); rm = float(Yi[roi].mean())
            import cv2
            win = (np.abs(yy - py) <= 45) & (np.abs(xx - px) <= 45)
            thr = ref + 0.5 * (float(Yi[win].max()) - ref)
            mk = ((Yi >= thr) & win).astype(np.uint8)
            n, lab = cv2.connectedComponents(mk)
            cand = lab[roi & (mk > 0)]
            el, angle = None, None
            if cand.size:
                k = np.bincount(cand).argmax(); ys_, xs_ = np.where(lab == k)
                if len(xs_) >= 5:
                    C = np.cov(np.vstack([xs_, ys_])); ev_, evec = np.linalg.eigh(C)
                    el = float(math.sqrt(max(ev_[1], 1e-9) / max(ev_[0], 1e-3)))
                    ma = evec[:, 1]; dv = np.array([pj['lamp'][0] * 0.5 - px, pj['lamp'][1] * 0.5 - py])
                    if np.linalg.norm(dv) > 5: angle = float(math.degrees(math.acos(min(1, abs(ma @ dv) / np.linalg.norm(dv)))))
            d = {'P': [round(px), round(py)], 'roi_mean': round(rm, 1), 'ring_median': round(ref, 1), 'ratio': round(rm / ref, 2), 'elongation': el and round(el, 2), 'angle_to_lamp': angle and round(angle, 1)}
            ok = rm >= 1.5 * ref and el is not None and el >= 1.5 and (angle is None or angle <= 30)
            return ok, d
        try:
            bad, info = [], {}
            if a1 is None or a1 not in RGB: bad.append(f'S1 lit frame {a1} not decoded')
            else:
                ok, d = highlight(RGB[a1], PJ.get('g01_s1')); info['S1'] = d
                if not ok: bad.append(f'S1@{a1} {d}')
            if b5 is None or b5 not in RGB: bad.append(f'S5 lit frame {b5} not decoded')
            else:
                ok, d = highlight(RGB[b5], PJ.get('g01_s5')); info['S5'] = d
                if not ok: bad.append(f'S5@{b5} {d}')
                fpre = max(Fb['S5'][0], lon - 3) if lon is not None else None
                if ok and fpre is not None and fpre < lon and fpre in RGB:
                    _, d0 = highlight(RGB[fpre], PJ.get('g01_s5'))
                    ex0 = (d0.get('roi_mean') or 0) - (d0.get('ring_median') or 0); ex1 = d['roi_mean'] - d['ring_median']
                    if d0.get('roi_mean') is None or ex0 > 0.5 * ex1: bad.append(f'S5 highlight already present before lamp_on (excess {ex0:.1f} vs lit {ex1:.1f})')
            rough = X.get('road_rough') or []
            if not any(r['rough_linked'] for r in rough): bad.append(f'ROAD roughness is constant (not linked to a texture/mask): {rough[:3]}')
            R['X07-G01'] = L.F('; '.join(bad)) if bad else L.P(info)
        except Exception as ex:
            R['X07-G01'] = L.F(f'highlight measure error {ex}')

        # ----- G02 puddle reflection follows the lamp -----
        try:
            bad, info = [], {}
            pj = PJ.get('g02_s2') or {}
            s2a = Fb['S2'][0]; s2z = Fb['T23_dissolve'][0] - 1
            if 'mirror' not in pj or lo is None or not LS: raise ValueError(f'missing projection / lamp_off / lamp curve ({list(pj)}, {lo}, {bool(LS)})')
            qx, qy = pj['mirror'][0] * 0.5, pj['mirror'][1] * 0.5
            rad = max(10.0, 1.5 * pj.get('lamp_radius_px', 0))
            h, w = 360, 640
            if pj['mirror'][2] <= 0 or not (-rad < qx < w + rad and -rad < qy < h + rad): raise ValueError(f'lamp reflection point outside S2 frame ({qx:.0f},{qy:.0f})')
            yy, xx = np.mgrid[0:h, 0:w]; roi = np.hypot(yy - qy, xx - qx) <= rad
            pm = rect_mask(pj.get('PUDDLE'), (h, w)) if pj.get('PUDDLE') else np.ones((h, w), bool)
            if pm.sum() < 100: pm = np.ones((h, w), bool)
            rv = {f: float(Y(RGB[f].astype(np.float64))[roi].mean()) for f in range(s2a, s2z + 1) if f in RGB}
            pmed = {f: float(np.median(Y(RGB[f].astype(np.float64))[pm])) for f in rv}
            lit = [f for f in rv if f <= lo and LS.get(f, 0) >= 0.5]
            aft = [f for f in rv if lo + 3 <= f <= min(lo + 12, s2z)]
            if len(lit) < 2 or not aft: raise ValueError(f'not enough lit S2 frames ({len(lit)}) or post-off frames ({len(aft)})')
            Lit = float(np.median([rv[f] for f in lit])); Pm = float(np.median([pmed[f] for f in lit]))
            Aft = float(np.median([rv[f] for f in aft])); PmA = float(np.median([pmed[f] for f in aft]))
            exL = Lit - Pm                                  # reflection excess over the puddle median
            info.update(reflection_lit=round(Lit, 1), puddle_median=round(Pm, 1), reflection_after=round(Aft, 1), puddle_median_after=round(PmA, 1))
            if Lit < 2 * max(Pm, 1.0): bad.append(f'lit reflection {Lit:.1f} < 2x puddle median {Pm:.1f}')
            if Aft - PmA > 0.5 * exL: bad.append(f'reflection excess after lamp_off {Aft - PmA:.1f} > 50% of lit excess {exL:.1f}')
            # final drop = first frame from which the reflection (film) / lamp energy (project) stays low through lamp_off+6
            dfilm = next((f for f in range(lo - 6, lo + 7) if f in rv and all(rv[g] - pmed[g] < 0.5 * exL for g in range(f, lo + 7) if g in rv)), None)
            demis = next((f for f in range(lo - 6, lo + 7) if f in LS and all(LS[g] <= 0.05 for g in range(f, lo + 7) if g in LS)), None)
            info.update(drop_film=dfilm, drop_emission=demis, lamp_off=lo)
            if dfilm is None or demis is None or abs(dfilm - demis) > 1 or abs(dfilm - lo) > 2: bad.append(f'reflection drop frame {dfilm} vs emission {demis} vs declared {lo}')
            br = [RGB[f][pm].reshape(-1, 3).mean(0) for f in range(lo + 6, min(lo + 13, s2z + 1)) if f in RGB]
            if br:
                c = np.mean(br, 0); info['BR_after'] = round(float(c[2] / max(c[0], 1e-3)), 2)
                if c[2] / max(c[0], 1e-3) < 1.2: bad.append(f'puddle not cyan after lamp_off (B/R {info["BR_after"]})')
            else: bad.append('no S2 frames after lamp_off+6 before the dissolve')
            R['X07-G02'] = L.F('; '.join(bad) + f' | {info}') if bad else L.P(info)
        except Exception as ex:
            R['X07-G02'] = L.F(f'puddle reflection: {ex}')

        # ----- G04 rain ripples -----
        try:
            bad = []; pu = X.get('puddle') or {}
            if pu.get('topology_changes'): bad.append(f'PUDDLE topology changes over time ({pu["topology_changes"]} samples)')
            if (pu.get('max_abs_dev_m') or 0) < 0.0005: bad.append(f'PUDDLE surface static over frames 150-280 (max dev {pu.get("max_abs_dev_m")} m)')
            elif pu.get('max_lag_corr') is None or pu['max_lag_corr'] >= 0.9: bad.append(f'ripple field repeats (max 0.5-2 s lag corr {pu.get("max_lag_corr")})')
            g = G.get('base'); act = None
            if g is not None:
                pj = PJ.get('g02_s2') or {}
                m = rect_mask(pj.get('PUDDLE'), g.shape[1:], 0, 0.25) if pj.get('PUDDLE') else np.ones(g.shape[1:], bool)
                if m.sum() < 50: m = np.ones(g.shape[1:], bool)
                fr_ = list(range(max(146, Fb['S2'][0] + 2), Fb['T23_dissolve'][0]))
                vals = []
                for f in fr_:
                    a, b = g[f - 1][m].astype(np.float32), g[f][m].astype(np.float32)
                    a = a * (b.mean() / max(a.mean(), 1e-3))
                    vals.append(float((np.abs(b - a) > 4).mean()))
                act = float(np.mean(np.array(vals) >= 0.002)) if vals else 0.0
                if act < 0.8: bad.append(f'S2 puddle shows local change in only {act:.0%} of frame pairs (need 80%)')
            R['X07-G04'] = L.F('; '.join(bad)) if bad else L.P({'max_dev_m': pu.get('max_abs_dev_m'), 'max_lag_corr': pu.get('max_lag_corr'), 'film_active_pairs': act})
        except Exception as ex:
            R['X07-G04'] = L.F(f'ripple measure error {ex}')

        # ----- G05 puddle step -----
        try:
            if 'X07-G05' not in R:
                fsum = X.get('feet_summary') or {}; bad = []
                c = fsum.get('contact')
                if not c: bad.append(f'no foot/shoe vertex over the PUDDLE at foot_contact±2 ({fsum.get("error", "")})')
                else:
                    if not -0.10 <= c['gap_m'] <= 0.04: bad.append(f'foot-water gap {c["gap_m"]} m (need <=0.04)')
                    if fsum.get('pre6_min_height_m') is None or fsum['pre6_min_height_m'] < 0.03: bad.append(f'foot 6 frames before only {fsum.get("pre6_min_height_m")} m above water (need >=0.03)')
                    if fsum.get('splash_after_max', 0) <= fsum.get('splash_before', 0): bad.append(f'no new splash elements within 0.3 m ({fsum.get("splash_before")} -> {fsum.get("splash_after_max")})')
                    vb, va = fsum.get('puddle_var_before'), fsum.get('puddle_var_after')
                    if va is None or va <= 1e-10 or (vb or 0) * 3 > va: bad.append(f'puddle displacement variance near the step {vb} -> {va} (need x3)')
                R['X07-G05'] = L.F('; '.join(bad)) if bad else L.P({'audio': S.get('g05_audio'), **{k: fsum.get(k) for k in ('contact', 'pre6_min_height_m', 'splash_before', 'splash_after_max', 'puddle_var_before', 'puddle_var_after')}})
        except Exception as ex:
            R['X07-G05'] = L.F(f'foot contact measure error {ex}')

        # ----- G06 lighting continuity -----
        try:
            bad, info = [], {}
            if not LS or fs is None or lo is None: raise ValueError('no lamp curve / events')
            seq = [LS[f] for f in sorted(LS) if fs <= f <= lo]
            jumps, low = 0, False
            for v_ in seq:
                if v_ <= 0.2: low = True
                elif v_ >= 0.8 and low: jumps += 1; low = False
            info['flicker_off_on'] = jumps
            if jumps < 2: bad.append(f'only {jumps} off->on lamp jumps between flicker start and lamp_off')
            ok, d = lamp_off_ok(); info['off_span'] = d
            if not ok: bad.append(f'lamp not off lamp_off..lamp_on / not back on: {d}')
            pre = [lamp[f] for f in lamp if fs - 48 <= f < fs]
            col = next((p_.get('lcol') or p_.get('ecol') for p_ in pre if p_.get('lcol') or p_.get('ecol')), None)
            info['lamp_colour'] = col
            if not col or col[0] / max(col[2], 1e-3) < 1.3: bad.append(f'lamp colour not warm (R/B {col})')
            def region_rgb(f, key, sub='COMMUTER'):
                rc = (PJ.get(key) or {}).get(sub)
                if f not in RGB or not rc: return None
                m = rect_mask(rc, (360, 640))
                return RGB[f][m].reshape(-1, 3).astype(np.float64).mean(0) if m.sum() >= 20 else None
            c1 = region_rgb(PF.get('g06_s1'), 'g06_s1')
            if c1 is None or c1[0] / max(c1[2], 1e-3) < 1.05: bad.append(f'S1 character region not warm-lit (RGB {None if c1 is None else c1.round(1).tolist()})')
            c3 = region_rgb(380, 'g06_s3')
            if c3 is None or c3[2] / max(c3[0], 1e-3) < 1.1 or c3[1] / max(c3[0], 1e-3) < 1.0: bad.append(f'S3@380 character region not cyan-lit (RGB {None if c3 is None else c3.round(1).tolist()})')
            if hl is None: bad.append('headlights_on_face missing')
            else:
                rc = (PJ.get('g06_s4') or {}).get('COMMUTER_head')
                m = rect_mask(rc, (360, 640)) if rc else None
                bef = [Y(RGB[f].astype(np.float64))[m].mean() for f in range(hl - 12, hl) if f in RGB and m is not None and m.sum() >= 20]
                aft = [Y(RGB[f].astype(np.float64))[m].mean() for f in range(hl + 1, hl + 13) if f in RGB and m is not None and m.sum() >= 20]
                if len(bef) < 3 or len(aft) < 3: bad.append(f'face ROI frames before/after headlights {len(bef)}/{len(aft)} (<3)')
                else:
                    rat = float(np.mean(aft) / max(np.mean(bef), 1.0)); info['face_ratio'] = round(rat, 2)
                    if rat < 1.5: bad.append(f'face brightening after headlights_on_face x{rat:.2f} (<1.5)')
                bus = {int(k): v for k, v in (X.get('bus') or {}).items()}
                bl = bus.get(hl) or bus.get(hl + 1) or {}
                locs = bl.get('light_cam_local') or ([bl['cam_local']] if bl.get('cam_local') else [])
                if not locs or not all(p_[0] < 0 for p_ in locs): bad.append(f'BUS_LIGHTS not on frame left of CAM_S4 (camera-local {locs})')
                if not any((v.get('light', 0) + v.get('emis', 0)) > 0 for f, v in bus.items() if hl <= f <= hl + 12): bad.append('BUS_LIGHTS emit nothing after headlights_on_face')
            R['X07-G06'] = L.F('; '.join(bad) + f' | {info}') if bad else L.P(info)
        except Exception as ex:
            R['X07-G06'] = L.F(f'lighting continuity: {ex}')

        # ----- M17 re-render from the project -----
        try:
            R['X07-M17'] = rerender(blend)
        except Exception as ex:
            R['X07-M17'] = L.F(f're-render error {type(ex).__name__}: {ex}')

    def rerender(blend):
        import cv2, shutil
        exe = shutil.which('blender')
        rp = pathlib.Path(__file__).with_name('x07_render.py')
        jobs = [('base', {'rev_s2_hold_frames': 0, 'rev_s4_trim_frames': 0}, [72, 216, 372, 528, 660]),
                ('revision2', {'rev_s2_hold_frames': 12, 'rev_s4_trim_frames': 6}, [500])]
        res, bad = {}, []
        t_start = __import__('time').time()
        for v, props, frames in jobs:
            g = G.get(v)
            if g is None: bad.append(f'{v} film missing'); continue
            best = {}
            for eng in (None, 'CYCLES'):
                todo = [f for f in frames if best.get(f, -1) < 0.70]
                if not todo or (eng == 'CYCLES' and res.get(f'{v}_engine') == 'CYCLES'): break
                left = 900 - (__import__('time').time() - t_start)
                if left < 60: bad.append('re-render time budget (900 s) exhausted'); break
                d = pathlib.Path(tmp) / f'rr_{v}_{eng or "auth"}'; d.mkdir(parents=True, exist_ok=True)
                cfgp = d / 'cfg.json'; outp = d / 'out.json'
                cfgp.write_text(json.dumps({'props': props, 'frames': todo, 'w': 320, 'h': 180, 'samples': 16, 'dir': str(d), 'out': str(outp), 'engine': eng}))
                try:
                    L.sh([exe, '-b', str(blend), '--python', str(rp), '--', str(cfgp)], int(left))
                except Exception as ex:
                    bad.append(f'{v} render {eng}: {type(ex).__name__}'); continue
                o = json.loads(outp.read_text()) if outp.exists() else {'frames': {}, 'errors': ['no output']}
                res[f'{v}_engine'] = o.get('engine')
                for f in todo:
                    fp = o['frames'].get(str(f), 'ERR missing')
                    if fp.startswith('ERR') or f >= len(g): res[f'{v}@{f}:{eng}'] = fp[:80]; continue
                    im = cv2.imread(fp, cv2.IMREAD_GRAYSCALE)
                    if im is None: continue
                    im = cv2.resize(im, (320, 180), interpolation=cv2.INTER_AREA)
                    a = cv2.GaussianBlur(im.astype(np.float64), (0, 0), 1.0); b = cv2.GaussianBlur(g[f].astype(np.float64), (0, 0), 1.0)
                    best[f] = max(best.get(f, -1), L.ssim(a, b))
            for f in frames:
                res[f'{v}@{f}'] = round(best.get(f, -1), 3)
                if best.get(f, -1) < 0.70: bad.append(f'{v} frame {f}: SSIM {best.get(f)}')
        return L.F('; '.join(bad[:8]) + f' | {res}') if bad else L.P(res)

    guard(list(BLEND_IDS) + ['X07-B04'], project)
    return R


def ssim_masked(a, b, keep):
    """mean SSIM map (7x7 gaussian) over pixels where keep is True."""
    import cv2
    a = a.astype(np.float64); b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    k, s = (7, 7), 1.5
    mu1, mu2 = cv2.GaussianBlur(a, k, s), cv2.GaussianBlur(b, k, s)
    s11 = cv2.GaussianBlur(a * a, k, s) - mu1 ** 2
    s22 = cv2.GaussianBlur(b * b, k, s) - mu2 ** 2
    s12 = cv2.GaussianBlur(a * b, k, s) - mu1 * mu2
    m = ((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 ** 2 + mu2 ** 2 + C1) * (s11 + s22 + C2))
    return float(m[keep].mean()) if keep.any() else None


GATES = {'edit': lambda S, R: S.get('base_frames', 720) != 720,
         'sound': lambda S, R: (not S.get('stems_present_base', True)) or (S.get('residual') is not None and (lambda b: b is None or b['median'] > 1.5 or b['p95'] > 6.0)(S['residual'].get('base'))),
         'revision': lambda S, R: S.get('blend') == 'missing' or bool(S.get('props_missing')),
         'character': lambda S, R: S.get('blend') == 'missing' or (isinstance(S.get('blend'), dict) and 'objects' in S['blend'] and not S.get('char_bound')),
         # 2026-10-25: only the deterministic flat-shading floor fires the pbr gate (a judge verdict on G07 does not)
         'pbr': lambda S, R: R.get('X07-G07', {}).get('verdict') == 'fail' and R.get('X07-G07', {}).get('source') == 'checks' and not R['X07-G07'].get('gate')}


def postprocess(res, ctx):
    S = ctx.get('_x07', {})
    items = {i['id']: i for i in ctx['items']}
    for g, fn in GATES.items():
        try:
            hit = fn(S, res)
        except Exception:
            hit = False
        if hit:
            for iid, it in items.items():
                if it.get('group') == g and res.get(iid, {}).get('verdict') not in ('fail', 'error'):
                    pre = res.get(iid, {})
                    res[iid] = dict(pre, verdict='fail', detail=f'group gate "{g}" triggered (pre-gate: {pre.get("verdict")} {str(pre.get("detail", pre.get("reason", "")))[:300]})', gate=g)
    return res
