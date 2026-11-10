# -*- coding: utf-8 -*-
"""CDC-A-X08 deterministic checks.

Machine-checked: B1 (deliverables/encoding), B2 (manifest), B3 (per-segment SSIM honesty),
M1/M2 (content family lookup), M3 (intercut order / thread labels), M4 (schema part only:
returns fail when schema invalid, otherwise left to the judge), G1-G7 (exact selection,
gated by per-segment honesty).
"""
import json, subprocess, pathlib

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

ORDER = ['A1', 'B1', 'A2', 'B2', 'A3', 'B3', 'A4']
G_OF = {'A1': 'G1', 'B1': 'G2', 'A2': 'G3', 'B2': 'G4', 'A3': 'G5', 'B3': 'G6', 'A4': 'G7'}
FPS = 30
SW, SH = 360, 202  # max side 360 px for 1280x720
SSIM_TH = 0.95
EXPECTED_FILES = {'solution.mp4', 'solution.json', 'selection-evidence.json'}


def _run(cmd, timeout=600):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def _probe(p):
    r = _run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(p)], 120)
    return json.loads(r.stdout.decode('utf-8', 'replace'))


def _decode_gray(p, timeout=900):
    """Decode all frames as gray SW x SH uint8 array (N, SH, SW). Returns (arr, ok)."""
    cmd = ['ffmpeg', '-v', 'error', '-nostdin', '-i', str(p), '-map', '0:v:0', '-vsync', 'passthrough',
           '-vf', f'scale={SW}:{SH}:flags=area,format=gray', '-f', 'rawvideo', '-pix_fmt', 'gray', '-']
    r = _run(cmd, timeout)
    buf = np.frombuffer(r.stdout, dtype=np.uint8)
    n = buf.size // (SW * SH)
    arr = buf[:n * SW * SH].reshape(n, SH, SW) if n else np.zeros((0, SH, SW), np.uint8)
    return arr, (r.returncode == 0 and not r.stderr.strip())


def _ssim(a, b):
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5, borderType=cv2.BORDER_REFLECT)
    mu_a, mu_b = g(a), g(b)
    saa = g(a * a) - mu_a * mu_a
    sbb = g(b * b) - mu_b * mu_b
    sab = g(a * b) - mu_a * mu_b
    m = ((2 * mu_a * mu_b + C1) * (2 * sab + C2)) / ((mu_a ** 2 + mu_b ** 2 + C1) * (saa + sbb + C2))
    return float(m[5:-5, 5:-5].mean())


def _load_json(p):
    try:
        return json.loads(p.read_text(encoding='utf-8')), None
    except Exception as e:
        return None, f'{p.name}: {e}'


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def run(ctx):
    out = pathlib.Path(ctx['out'])
    inp = pathlib.Path(ctx['input'])
    ans = ctx.get('answer') or {}
    csm = ans.get('clip_shot_map', {})
    beats_key = ans.get('beats', {})
    R = {}
    state = ctx.setdefault('_x08', {'honest': {}})

    def clip_frames(sid):
        if sid in csm and _is_int(csm[sid].get('frames')):
            return csm[sid]['frames']
        try:
            st = [s for s in _probe(inp / f'{sid}.mp4')['streams'] if s.get('codec_type') == 'video'][0]
            return int(st['nb_frames'])
        except Exception:
            return None

    valid_ids = {f'{i:02d}' for i in range(1, 47)}
    vid = out / 'solution.mp4'

    # ---------- B1 deliverables + encoding ----------
    dec_count = None
    try:
        files = sorted(p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()) if out.exists() else []
        probs = []
        if set(files) != EXPECTED_FILES:
            probs.append(f'output files = {files}')
        if vid.exists():
            j = _probe(vid)
            vs = [s for s in j.get('streams', []) if s.get('codec_type') == 'video']
            aus = [s for s in j.get('streams', []) if s.get('codec_type') == 'audio']
            if len(vs) != 1:
                probs.append(f'{len(vs)} video streams')
            else:
                s = vs[0]
                for k, want in (('codec_name', 'h264'), ('pix_fmt', 'yuv420p'), ('width', 1280), ('height', 720),
                                ('r_frame_rate', '30/1'), ('avg_frame_rate', '30/1')):
                    if s.get(k) != want:
                        probs.append(f'{k}={s.get(k)} (want {want})')
                if s.get('sample_aspect_ratio') not in ('1:1', None, 'N/A', '0:1'):
                    probs.append(f"SAR={s.get('sample_aspect_ratio')}")
            if aus:
                probs.append(f'{len(aus)} audio stream(s)')
            # full decode + frame count + CFR via pts
            r = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'frame=best_effort_timestamp', '-of', 'csv=p=0', str(vid)], 600)
            pts = [int(x.strip().split(',')[0]) for x in r.stdout.decode().splitlines() if x.strip() and x.strip().split(',')[0].lstrip('-').isdigit()]
            dec_count = len(pts)
            if r.returncode != 0 or r.stderr.strip():
                probs.append('decode errors: ' + r.stderr.decode('utf-8', 'replace')[:200])
            if dec_count == 0:
                probs.append('0 decoded frames')
            else:
                d = np.diff(np.array(sorted(pts)))
                if d.size and (d.min() != d.max() or d.min() <= 0):
                    probs.append(f'non-constant pts step (min {d.min()}, max {d.max()})')
        else:
            probs.append('solution.mp4 missing')
        R['B1'] = {'verdict': 'fail' if probs else 'pass',
                   'detail': '; '.join(probs) if probs else f'ok, {dec_count} frames decoded'}
    except Exception as e:
        R['B1'] = {'verdict': 'fail', 'detail': f'error: {e}'}

    # ---------- parse manifest ----------
    segs = None
    man, err = _load_json(out / 'solution.json') if (out / 'solution.json').exists() else (None, 'solution.json missing')
    if man is not None:
        segs = man.get('segments') if isinstance(man, dict) else None
        if not isinstance(segs, list) or not all(isinstance(s, dict) for s in segs):
            err, segs = 'segments not a list of objects', None

    # ---------- B2 manifest consistency ----------
    try:
        probs = []
        if segs is None:
            probs.append(err or 'no segments')
        else:
            if len(segs) != 7:
                probs.append(f'{len(segs)} segments')
            srcs = [s.get('source') for s in segs]
            if not all(isinstance(x, str) and x in valid_ids for x in srcs):
                probs.append(f'invalid source ids {srcs}')
            elif len(set(srcs)) != len(srcs):
                probs.append(f'duplicate sources {srcs}')
            cur = 0
            for i, s in enumerate(segs):
                th, bt = s.get('thread'), s.get('beat')
                if th not in ('A', 'B') or not isinstance(bt, str) or bt not in ORDER:
                    probs.append(f'seg{i}: thread/beat {th}/{bt}')
                of, sf, o, sr = s.get('output_frames'), s.get('source_frames'), s.get('output'), s.get('source_range')
                if not (isinstance(of, list) and len(of) == 2 and all(_is_int(x) for x in of)):
                    probs.append(f'seg{i}: output_frames {of}'); continue
                if of[0] != cur or of[1] <= of[0]:
                    probs.append(f'seg{i}: output_frames {of} not contiguous from {cur}')
                cur = of[1]
                n = clip_frames(s.get('source')) if s.get('source') in valid_ids else None
                if not (isinstance(sf, list) and len(sf) == 2 and sf == [0, n]):
                    probs.append(f'seg{i}: source_frames {sf} != [0,{n}]')
                if n is not None and of[1] - of[0] != n:
                    probs.append(f'seg{i}: output length {of[1]-of[0]} != clip frames {n}')
                try:
                    if abs(float(o[0]) - of[0] / FPS) > 0.001 or abs(float(o[1]) - of[1] / FPS) > 0.001:
                        probs.append(f'seg{i}: output seconds {o} != frames/30')
                except Exception:
                    probs.append(f'seg{i}: output {o}')
                try:
                    if n is None or abs(float(sr[0])) > 0.001 or abs(float(sr[1]) - n / FPS) > 0.001:
                        probs.append(f'seg{i}: source_range {sr}')
                except Exception:
                    probs.append(f'seg{i}: source_range {sr}')
            if dec_count is None or cur != dec_count:
                probs.append(f'last end {cur} != decoded count {dec_count}')
        R['B2'] = {'verdict': 'fail' if probs else 'pass', 'detail': '; '.join(probs)[:1500] if probs else 'ok'}
    except Exception as e:
        R['B2'] = {'verdict': 'fail', 'detail': f'error: {e}'}

    # ---------- B3 honesty (per-segment SSIM) ----------
    honest = state['honest']  # beat -> bool
    try:
        if segs is None or not vid.exists() or cv2 is None:
            R['B3'] = {'verdict': 'fail', 'detail': err or ('cv2 unavailable' if cv2 is None else 'no video/manifest')}
        else:
            outv, _ = _decode_gray(vid)
            det = []
            allok = len(segs) == 7
            for i, s in enumerate(segs):
                bt, sid, of = s.get('beat'), s.get('source'), s.get('output_frames')
                ok, why = False, ''
                try:
                    if sid not in valid_ids:
                        raise ValueError(f'bad source {sid}')
                    if not (isinstance(of, list) and len(of) == 2 and all(_is_int(x) for x in of)):
                        raise ValueError(f'bad output_frames {of}')
                    src, _ = _decode_gray(inp / f'{sid}.mp4')
                    a, b = of
                    if b - a != len(src):
                        raise ValueError(f'len {b-a} != clip decoded {len(src)}')
                    if b > len(outv) or a < 0:
                        raise ValueError(f'range {of} outside video ({len(outv)})')
                    mn, mi = 1.0, 0
                    for k in range(len(src)):
                        v = _ssim(outv[a + k], src[k])
                        if v < mn:
                            mn, mi = v, k
                        if v < SSIM_TH:
                            break
                    ok = mn >= SSIM_TH
                    why = f'min SSIM {mn:.4f} @ {mi}'
                except Exception as e:
                    why = str(e)
                if isinstance(bt, str) and bt in ORDER:
                    honest[bt] = honest.get(bt, True) and ok if bt in honest else ok
                allok = allok and ok
                det.append(f'{bt}/{sid}: {"ok" if ok else "FAIL"} {why}')
            R['B3'] = {'verdict': 'pass' if allok else 'fail', 'detail': '; '.join(det)[:1500]}
    except Exception as e:
        R['B3'] = {'verdict': 'fail', 'detail': f'error: {e}'}

    # ---------- M1/M2/M3/G lookups ----------
    try:
        chosen = {}
        if segs:
            for s in segs:
                bt = s.get('beat')
                if isinstance(bt, str) and bt in ORDER and bt not in chosen:
                    chosen[bt] = s.get('source')
        for mid, bl in (('M1', ['A1', 'A2', 'A3', 'A4']), ('M2', ['B1', 'B2', 'B3'])):
            bad = [f'{b}={chosen.get(b)}' for b in bl if chosen.get(b) not in beats_key.get(b, {}).get('content_family', [])]
            R[mid] = {'verdict': 'fail' if bad else 'pass', 'detail': ('outside family: ' + ', '.join(bad)) if bad else 'all in family'}
        probs = []
        if not segs:
            probs.append('no segments')
        else:
            labels = [s.get('beat') for s in segs]
            if labels != ORDER:
                probs.append(f'order {labels}')
            for s in segs:
                if not (isinstance(s.get('beat'), str) and s.get('thread') == s['beat'][:1]):
                    probs.append(f"thread/beat mismatch {s.get('thread')}/{s.get('beat')}")
        R['M3'] = {'verdict': 'fail' if probs else 'pass', 'detail': '; '.join(probs) if probs else 'ok'}
        for bt in ORDER:
            g = G_OF[bt]
            key = beats_key.get(bt, {}).get('source')
            c = chosen.get(bt)
            if c != key:
                R[g] = {'verdict': 'fail', 'detail': f'{bt}: chose {c}, key {key}'}
            elif not honest.get(bt, False):
                R[g] = {'verdict': 'fail', 'detail': f'{bt}: correct id {c} but segment fails honesty (B3 gate)'}
            else:
                R[g] = {'verdict': 'pass', 'detail': f'{bt}: {c} correct, honest'}
    except Exception as e:
        for k in ['M1', 'M2', 'M3'] + list(G_OF.values()):
            R.setdefault(k, {'verdict': 'fail', 'detail': f'error: {e}'})

    # ---------- M4 schema (content left to judge) ----------
    try:
        probs = []
        chosen_ev = {}
        for sg in (segs or []):
            if isinstance(sg, dict) and isinstance(sg.get('beat'), str) and sg['beat'] not in chosen_ev:
                chosen_ev[sg['beat']] = sg.get('source')
        p = out / 'selection-evidence.json'
        ev, e2 = _load_json(p) if p.exists() else (None, 'selection-evidence.json missing')
        if ev is None:
            probs.append(e2)
        elif not isinstance(ev, list) or len(ev) != 7:
            probs.append('not an array of 7')
        else:
            for i, o in enumerate(ev):
                if not isinstance(o, dict):
                    probs.append(f'item{i} not object'); continue
                sid, sf, rs = o.get('source'), o.get('source_frames'), o.get('reason')
                if o.get('beat') not in ORDER:
                    probs.append(f'item{i} beat {o.get("beat")}')
                elif sid != chosen_ev.get(o.get('beat')):
                    probs.append(f'item{i} source {sid} != solution.json source {chosen_ev.get(o.get("beat"))} for {o.get("beat")}')
                n = clip_frames(sid) if sid in valid_ids else None
                if n is None:
                    probs.append(f'item{i} source {sid}')
                elif not (isinstance(sf, list) and len(sf) == 2 and all(_is_int(x) for x in sf)
                          and 0 <= sf[0] and sf[1] <= n and sf[1] - sf[0] >= 12):
                    probs.append(f'item{i} source_frames {sf} (clip {n})')
                if not (isinstance(rs, str) and rs.strip()):
                    probs.append(f'item{i} empty reason')
            if len({o.get('beat') for o in ev if isinstance(o, dict)}) != 7:
                probs.append('beats not distinct')
        if probs:
            R['M4'] = {'verdict': 'fail', 'detail': 'schema: ' + '; '.join(map(str, probs))[:1200]}
        # schema valid -> content judged by model (not returned)
    except Exception as e:
        R['M4'] = {'verdict': 'fail', 'detail': f'error: {e}'}

    R['_slots_correct'] = {'verdict': 'info', 'detail': f"{sum(1 for g in G_OF.values() if R.get(g, {}).get('verdict') == 'pass')}/7"}
    return R


def postprocess(results, ctx):
    # group gate: G item for a beat whose segment fails honesty -> 0 (already enforced in run; re-assert)
    honest = ctx.get('_x08', {}).get('honest', {})
    for bt, g in G_OF.items():
        if g in results and results[g].get('verdict') == 'pass' and not honest.get(bt, False):
            results[g] = dict(results[g], verdict='fail', detail=results[g].get('detail', '') + ' [honesty gate]')
    return results
