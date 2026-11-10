# -*- coding: utf-8 -*-
"""CDC-A-X03 deterministic checks (called by rubric_score.py).

Machine-checked: B1 B2 B3 B4 M1-M7 G1-G7 G8, plus a frame-range pre-check for M8
(M8 is only returned when it fails deterministically; otherwise left to the judge model).
postprocess(): group gate B4 -> a dishonest slot k forces M<k>/G<k> to fail.
"""
import json, re, subprocess, traceback
from fractions import Fraction

import numpy as np

FPS = 24
W, H = 1280, 720
SW, SH = 360, 202          # max side 360 px (1280x720 -> 360x202.5, even height)
SSIM_T = 0.95
FILES = {'solution.mp4', 'solution.json', 'selection-evidence.json'}
# provenance frame counts (fallback when ffprobe on input fails)
FRAMES = {'01': 190, '02': 216, '03': 197, '04': 214, '05': 258, '06': 167, '07': 164, '08': 197, '09': 190,
          '10': 158, '11': 180, '12': 196, '13': 211, '14': 192, '15': 192, '16': 199, '17': 193, '18': 170,
          '19': 286, '20': 196, '21': 190, '22': 204, '23': 192, '24': 164, '25': 258, '26': 286, '27': 216,
          '28': 193, '29': 218, '30': 152, '31': 216, '32': 216, '33': 230, '34': 187, '35': 216, '36': 167,
          '37': 216, '38': 199, '39': 168, '40': 204, '41': 182, '42': 182, '43': 216, '44': 218, '45': 216}


def _run(cmd, timeout=600, text=True):
    return subprocess.run(cmd, capture_output=True, text=text, timeout=timeout)


def _clip_frames(ctx, sid):
    p = ctx['input'] / f'{sid}.mp4'
    try:
        o = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=nb_frames',
                  '-of', 'csv=p=0', str(p)], 60).stdout.strip()
        n = int(o)
        if n > 0:
            return n
    except Exception:
        pass
    return FRAMES.get(sid)


def _decode_gray(path, timeout=900):
    """Decode all frames as gray SWxSH uint8 array (N,SH,SW). None on failure."""
    buf = b''
    for vs in (['-vsync', 'passthrough'], ['-fps_mode', 'passthrough']):  # ffmpeg 4.x .. 8.x
        r = _run(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(path), '-map', '0:v:0', *vs,
                  '-vf', f'scale={SW}:{SH}:flags=area,format=gray', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                 timeout, text=False)
        buf = r.stdout
        if buf or b'nrecognized option' not in (r.stderr or b''):
            break
    fs = SW * SH
    n = len(buf) // fs
    if n == 0:
        return None
    return np.frombuffer(buf[:n * fs], np.uint8).reshape(n, SH, SW)


def _ssim(a, b):
    import cv2
    a = a.astype(np.float32); b = b.astype(np.float32)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    mu1, mu2 = g(a), g(b)
    s1 = g(a * a) - mu1 * mu1
    s2 = g(b * b) - mu2 * mu2
    s12 = g(a * b) - mu1 * mu2
    m = ((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 * mu1 + mu2 * mu2 + C1) * (s1 + s2 + C2))
    return float(m.mean())


def _sid(x):
    if isinstance(x, str) and re.fullmatch(r'\d{2}', x):
        return x
    return None


def run(ctx):
    out, ans = ctx['out'], ctx.get('answer') or {}
    res = {}
    st = ctx.setdefault('x03', {'honest': {}})
    mp4, sj, ej = out / 'solution.mp4', out / 'solution.json', out / 'selection-evidence.json'

    # ---------- B1 ----------
    decoded = None
    try:
        if not mp4.exists():
            res['B1'] = {'verdict': 'fail', 'detail': 'solution.mp4 missing'}
        else:
            j = json.loads(_run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(mp4)], 60).stdout or '{}')
            ss = j.get('streams', [])
            v = [s for s in ss if s.get('codec_type') == 'video']
            a = [s for s in ss if s.get('codec_type') == 'audio']
            probs = []
            if len(v) != 1:
                probs.append(f'{len(v)} video streams')
            else:
                s = v[0]
                if s.get('codec_name') != 'h264': probs.append(f"codec {s.get('codec_name')}")
                if s.get('pix_fmt') != 'yuv420p': probs.append(f"pix_fmt {s.get('pix_fmt')}")
                if (s.get('width'), s.get('height')) != (W, H): probs.append(f"size {s.get('width')}x{s.get('height')}")
                if s.get('sample_aspect_ratio') not in ('1:1', None): probs.append(f"SAR {s.get('sample_aspect_ratio')}")
                # r_frame_rate must be exactly 24/1; avg_frame_rate within 0.1 % (a stream-copy concat,
                # which the task explicitly allows, leaves sub-ms pts jitter at the joins, e.g. 23.9996)
                try:
                    if Fraction(s.get('r_frame_rate', '0/1')) != FPS: probs.append(f"r_frame_rate {s.get('r_frame_rate')}")
                except Exception:
                    probs.append(f"r_frame_rate {s.get('r_frame_rate')}")
                try:
                    if abs(float(Fraction(s.get('avg_frame_rate', '0/1'))) - FPS) > 0.024:
                        probs.append(f"avg_frame_rate {s.get('avg_frame_rate')}")
                except Exception:
                    probs.append(f"avg_frame_rate {s.get('avg_frame_rate')}")
                # constant frame spacing from packet pts: every step within 2 ms of 1/24 s
                pk = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'packet=pts',
                           '-of', 'csv=p=0', str(mp4)], 120).stdout.split()
                pts = sorted(int(x.strip(',')) for x in pk if re.fullmatch(r'-?\d+', x.strip(',')))
                try:
                    tb = float(Fraction(s.get('time_base', '1/12288')))
                    d = np.diff(pts) * tb if len(pts) > 1 else np.zeros(0)
                    bad = d[np.abs(d - 1.0 / FPS) > 0.002]
                    if bad.size: probs.append(f'non-constant frame spacing: {bad.size} steps off 1/24 s, e.g. {bad[:3].round(4).tolist()}')
                except Exception as e:
                    probs.append(f'pts check error {e}')
            if a: probs.append(f'{len(a)} audio streams')
            decoded = _decode_gray(mp4)
            if decoded is None: probs.append('does not decode')
            res['B1'] = {'verdict': 'fail' if probs else 'pass',
                         'detail': '; '.join(probs) or f'ok, {len(decoded)} frames decoded'}
    except Exception:
        res['B1'] = {'verdict': 'fail', 'detail': 'error: ' + traceback.format_exc()[-300:]}
    nd = len(decoded) if decoded is not None else None
    st['decoded'] = nd

    # ---------- B2 ----------
    segs = None
    try:
        if not sj.exists():
            raise ValueError('solution.json missing')
        doc = json.loads(sj.read_text(encoding='utf-8'))
        segs = doc.get('segments') if isinstance(doc, dict) else None
        if not isinstance(segs, list):
            raise ValueError('no segments list')
        probs = []
        if len(segs) != 7: probs.append(f'{len(segs)} segments')
        prev, seen = 0, set()
        for i, s in enumerate(segs):
            if not isinstance(s, dict):
                probs.append(f'seg{i} not object'); continue
            sid = _sid(s.get('source'))
            if s.get('slot') != i + 1: probs.append(f'seg{i} slot={s.get("slot")}')
            if sid is None or sid not in FRAMES: probs.append(f'seg{i} bad source {s.get("source")!r}')
            elif sid in seen: probs.append(f'seg{i} duplicate source {sid}')
            seen.add(sid)
            of, sf, sec = s.get('output_frames'), s.get('source_frames'), s.get('output')
            ok = isinstance(of, list) and len(of) == 2 and all(type(x) is int for x in of)
            if not ok:
                probs.append(f'seg{i} output_frames {of!r}'); continue
            if of[0] != prev or of[1] <= of[0]: probs.append(f'seg{i} output_frames {of} not contiguous from {prev}')
            prev = of[1]
            if sid in FRAMES and sf != [0, _clip_frames(ctx, sid)]:
                probs.append(f'seg{i} source_frames {sf!r} != [0,{_clip_frames(ctx, sid)}]')
            try:
                if not (len(sec) == 2 and all(abs(float(sec[k]) - of[k] / FPS) <= 0.001 for k in (0, 1))):
                    probs.append(f'seg{i} output seconds {sec!r}')
            except Exception:
                probs.append(f'seg{i} output seconds {sec!r}')
        if nd is None: probs.append('solution.mp4 not decodable, cannot check final end')
        elif prev != nd: probs.append(f'final end {prev} != decoded {nd}')
        res['B2'] = {'verdict': 'fail' if probs else 'pass', 'detail': '; '.join(probs)[:800] or 'ok'}
    except Exception as e:
        res['B2'] = {'verdict': 'fail', 'detail': f'error: {e}'}

    # slot -> source map (lenient: by slot field)
    pick = {}
    if isinstance(segs, list):
        for s in segs:
            if isinstance(s, dict) and isinstance(s.get('slot'), int) and 1 <= s['slot'] <= 7:
                sid = _sid(s.get('source'))
                if sid and s['slot'] not in pick:
                    pick[s['slot']] = (sid, s.get('output_frames'))
    st['pick'] = pick

    # ---------- B3 / M8 pre-check ----------
    try:
        names = {p.name for p in out.iterdir()}
        nfiles = sum(1 for p in out.rglob('*') if p.is_file())
        probs = []
        if names != FILES or nfiles != 3: probs.append(f'output entries {sorted(names)} ({nfiles} files)')
        ev = json.loads(ej.read_text(encoding='utf-8')) if ej.exists() else None
        frame_probs = []
        if not isinstance(ev, list) or len(ev) != 7:
            probs.append('selection-evidence.json not a 7-element array')
            frame_probs.append('evidence missing/malformed')
        else:
            for i, e in enumerate(ev):
                if not isinstance(e, dict):
                    probs.append(f'ev{i} not object'); frame_probs.append(f'ev{i}'); continue
                slot = e.get('slot')
                src = str(e.get('source')).zfill(2) if e.get('source') is not None else None
                if slot != i + 1: probs.append(f'ev{i} slot {slot}')
                if slot not in pick or pick[slot][0] != src: probs.append(f'ev{i} source {src} != solution.json')
                fr = e.get('frames')
                n = _clip_frames(ctx, src) if src in FRAMES else None
                if not (isinstance(fr, list) and len(fr) == 2 and all(type(x) is int for x in fr) and n
                        and all(0 <= x < n for x in fr)):
                    probs.append(f'ev{i} frames {fr!r} not inside clip {src} (n={n})'); frame_probs.append(f'ev{i} frames')
                if not (isinstance(e.get('reason'), str) and e['reason'].strip()):
                    frame_probs.append(f'ev{i} empty reason')
        res['B3'] = {'verdict': 'fail' if probs else 'pass', 'detail': '; '.join(probs)[:800] or 'ok'}
        if frame_probs:
            res['M8'] = {'verdict': 'fail', 'detail': 'deterministic: ' + '; '.join(frame_probs)[:500]}
    except Exception as e:
        res['B3'] = {'verdict': 'fail', 'detail': f'error: {e}'}

    # ---------- B4 (per-slot honesty, every-frame SSIM) ----------
    honest = st['honest']
    try:
        probs = []
        for k in range(1, 8):
            if k not in pick:
                honest[k] = False; probs.append(f'slot{k}: no segment'); continue
            sid, of = pick[k]
            n = _clip_frames(ctx, sid)
            if decoded is None or not (isinstance(of, list) and len(of) == 2 and all(type(x) is int for x in of)):
                honest[k] = False; probs.append(f'slot{k}: no decodable range'); continue
            a, b = of
            if b - a != n:
                honest[k] = False; probs.append(f'slot{k}: length {b - a} != clip {sid} {n}'); continue
            if a < 0 or b > nd:
                honest[k] = False; probs.append(f'slot{k}: range {of} beyond decoded {nd}'); continue
            src = _decode_gray(ctx['input'] / f'{sid}.mp4')
            if src is None or len(src) != n:
                honest[k] = False; probs.append(f'slot{k}: cannot decode input {sid}'); continue
            vals = [_ssim(decoded[a + t], src[t]) for t in range(n)]
            mn = min(vals)
            honest[k] = mn >= SSIM_T
            if not honest[k]:
                probs.append(f'slot{k} ({sid}): min SSIM {mn:.3f} at frame {int(np.argmin(vals))}')
            else:
                st.setdefault('minssim', {})[k] = round(mn, 4)
        res['B4'] = {'verdict': 'pass' if all(honest.get(k) for k in range(1, 8)) else 'fail',
                     'detail': ('; '.join(probs) or f"min SSIM per slot {st.get('minssim')}")[:800]}
    except Exception:
        res['B4'] = {'verdict': 'fail', 'detail': 'error: ' + traceback.format_exc()[-300:]}

    # ---------- M1-M7 / G1-G7 / G8 ----------
    key = ans.get('correct_sources') or ['37', '21', '44', '20', '26', '25', '17']
    mir = ans.get('mirror_pairs_with_key') or {}
    lab = ans.get('orientation_label') or {}
    for k in range(1, 8):
        kid = key[k - 1]
        ok_m = {kid, mir.get(kid)} - {None}
        sid = pick.get(k, (None,))[0]
        res[f'M{k}'] = {'verdict': 'pass' if sid in ok_m else 'fail', 'detail': f'slot{k} chose {sid}, accepted {sorted(ok_m)}'}
        res[f'G{k}'] = {'verdict': 'pass' if sid == kid else 'fail', 'detail': f'slot{k} chose {sid}, key {kid}'}
    chosen = [pick.get(k, (None,))[0] for k in range(1, 8)]
    good = len(set(chosen)) == 7 and None not in chosen and all(str(lab.get(c, '')).startswith('axis-consistent') for c in chosen)
    res['G8'] = {'verdict': 'pass' if good else 'fail',
                 'detail': ', '.join(f'{c}:{lab.get(c, "?")[:14]}' for c in chosen)}
    return res


def postprocess(results, ctx):
    honest = (ctx.get('x03') or {}).get('honest') or {}
    for k in range(1, 8):
        if not honest.get(k, False):
            for p in ('M', 'G'):
                r = results.get(f'{p}{k}')
                if r and r.get('verdict') == 'pass':
                    r['verdict'] = 'fail'
                    r['detail'] = (r.get('detail', '') + ' | zeroed by B4 group gate (slot not honest)').strip()
    return results
