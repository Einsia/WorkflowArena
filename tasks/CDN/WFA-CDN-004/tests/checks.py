# -*- coding: utf-8 -*-
"""CDC-A-X04 deterministic checks (B1-B4, S1-S6, T1-T6). P01 (weight 0, integrity gate)
is not graded here: rubric_score.py marks weight-0 items 'na' and never sends them to the judge.

B3 SSIM: gray, longest side 360 px (640x360 -> 360x202), 11x11 Gaussian window sigma=1.5,
every output frame c+i vs declared candidate frame a+i, threshold 0.95.
T gating: S pass + declared source_frame in hidden window + |mapped output frame - accent| <= 1
+ declared output_frame consistent with mapping + that slot's B3 frames all pass.
"""
import csv, json, pathlib, subprocess

W, H = 360, 202
SSIM_TH = 0.95


def _ff(cmd, timeout=600):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def _count_frames(p):
    try:
        r = _ff(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
                 'stream=nb_read_frames', '-of', 'csv=p=0', str(p)], 300)
        return int(r.stdout.decode().strip().split(',')[0])
    except Exception:
        return None


def _decode(p, a=None, b=None):
    """Decode frames [a,b) (or all) as gray 360x202 uint8 array (n,H,W)."""
    import numpy as np
    vf = []
    if a is not None:
        vf.append(f'trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS')
    vf.append(f'scale={W}:{H}:flags=area,format=gray')
    r = _ff(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:v:0', '-vf', ','.join(vf), '-vsync', 'passthrough',
             '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], 900)
    buf = np.frombuffer(r.stdout, dtype=np.uint8)
    n = buf.size // (W * H)
    return buf[:n * W * H].reshape(n, H, W)


def _ssim(x, y):
    import cv2
    import numpy as np
    x = x.astype(np.float64); y = y.astype(np.float64)
    C1 = (0.01 * 255) ** 2; C2 = (0.03 * 255) ** 2
    g = lambda z: cv2.GaussianBlur(z, (11, 11), 1.5)
    mx, my = g(x), g(y)
    sxx = g(x * x) - mx * mx; syy = g(y * y) - my * my; sxy = g(x * y) - mx * my
    m = ((2 * mx * my + C1) * (2 * sxy + C2)) / ((mx * mx + my * my + C1) * (sxx + syy + C2))
    return float(m[5:-5, 5:-5].mean())


def run(ctx):
    out = pathlib.Path(ctx['out']); inp = pathlib.Path(ctx['input'])
    ak = ctx.get('answer') or {}
    res = {}

    def put(k, ok, detail):
        res[k] = {'verdict': 'pass' if ok else 'fail', 'detail': str(detail)[:900]}

    try:
        beats = json.loads((inp / 'beats.json').read_text(encoding='utf-8'))
    except Exception:
        beats = ak.get('beats')
    slots_b = {s['slot']: s for s in beats['slots']}
    total = beats['total_frames']
    keys = {s['slot']: s for s in ak.get('slots', [])}
    mp4 = out / 'solution.mp4'

    # ---- B1 ----
    try:
        files = sorted(p.name for p in out.iterdir()) if out.exists() else []
        probs = []
        if files != sorted(['solution.mp4', 'solution.json', 'events.csv']):
            probs.append(f'output files={files}')
        if mp4.exists():
            j = json.loads(_ff(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(mp4)], 120).stdout or b'{}')
            st = j.get('streams', [])
            vs = [s for s in st if s.get('codec_type') == 'video']
            if any(s.get('codec_type') == 'audio' for s in st):
                probs.append('has audio stream')
            if len(vs) != 1:
                probs.append(f'{len(vs)} video streams')
            else:
                v = vs[0]
                exp = {'codec_name': 'h264', 'pix_fmt': 'yuv420p', 'width': 1280, 'height': 720, 'r_frame_rate': '30/1'}
                for k2, e in exp.items():
                    if v.get(k2) != e:
                        probs.append(f'{k2}={v.get(k2)}')
                if v.get('sample_aspect_ratio') not in (None, '1:1', '0:1', 'N/A'):
                    probs.append(f"SAR={v.get('sample_aspect_ratio')}")
                if v.get('avg_frame_rate') not in ('30/1', None, '0/0'):
                    probs.append(f"avg_frame_rate={v.get('avg_frame_rate')} (not CFR 30)")
            dec = _ff(['ffmpeg', '-v', 'error', '-i', str(mp4), '-map', '0:v:0', '-f', 'null', '-'], 900)
            if dec.returncode != 0 or dec.stderr.strip():
                probs.append('decode errors: ' + dec.stderr.decode(errors='replace').strip()[:200])
            n = _count_frames(mp4)
            if n != total:
                probs.append(f'decoded frames={n} (want {total})')
        else:
            probs.append('solution.mp4 missing')
        put('B1', not probs, '; '.join(probs) or 'all format specs OK')
    except Exception as e:
        put('B1', False, f'error: {e}')

    # ---- B2 ----
    segs = None
    seg_ok = {}
    try:
        sj = json.loads((out / 'solution.json').read_text(encoding='utf-8'))
        segs = sj['segments']
        probs = []
        if not isinstance(segs, list) or len(segs) != 6:
            probs.append('segments is not a list of 6')
        srcs = []
        for i, sg in enumerate(segs or [], 1):
            try:
                src = str(sg['source']); a, b = [int(x) for x in sg['source_frames']]; c, d = [int(x) for x in sg['output_frames']]
                if int(sg['slot']) != i:
                    probs.append(f'seg{i}: slot={sg["slot"]}')
                srcs.append(src)
                clip = inp / 'clips' / f'{src}.mp4'
                if not clip.exists():
                    probs.append(f'slot{i}: invalid source {src}'); continue
                sb = slots_b[i]
                if [c, d] != [sb['start_frame'], sb['end_frame']]:
                    probs.append(f'slot{i}: output_frames {[c, d]} != {[sb["start_frame"], sb["end_frame"]]}')
                if b - a != d - c:
                    probs.append(f'slot{i}: b-a={b - a} != d-c={d - c}')
                nf = _count_frames(clip)
                if not (0 <= a < b <= (nf or 0)):
                    probs.append(f'slot{i}: source_frames {[a, b]} outside [0,{nf}]')
                else:
                    seg_ok[i] = (src, a, b, c, d)
            except Exception as e:
                probs.append(f'seg{i}: malformed ({e})')
        if len(set(srcs)) != len(srcs):
            probs.append(f'duplicate sources {srcs}')
        put('B2', not probs, '; '.join(probs) or 'contract OK')
    except Exception as e:
        put('B2', False, f'solution.json unreadable: {e}')

    # ---- B3 ----
    slot_b3 = {}
    try:
        if not mp4.exists() or not segs:
            raise RuntimeError('missing solution.mp4 or solution.json')
        outf = _decode(mp4)
        probs = []
        covered = 0
        for i in range(1, 7):
            if i not in seg_ok:
                slot_b3[i] = False; probs.append(f'slot{i}: no valid segment'); continue
            src, a, b, c, d = seg_ok[i]
            sf = _decode(inp / 'clips' / f'{src}.mp4', a, b)
            bad = 0; worst = 1.0
            for k in range(d - c):
                if c + k >= len(outf) or k >= len(sf):
                    bad += 1; worst = 0.0; continue
                s = _ssim(outf[c + k], sf[k]); worst = min(worst, s)
                if s < SSIM_TH:
                    bad += 1
            slot_b3[i] = bad == 0
            covered += (d - c)
            if bad:
                probs.append(f'slot{i}: {bad} frames SSIM<{SSIM_TH} (min {worst:.3f})')
        if covered != total:
            probs.append(f'segments cover {covered} frames, want {total}')
        put('B3', not probs and len(outf) == total, '; '.join(probs) or f'all {total} frames SSIM>={SSIM_TH}')
    except Exception as e:
        put('B3', False, f'error: {e}')

    # ---- B4 ----
    ev = {}
    try:
        rows = list(csv.reader((out / 'events.csv').read_text(encoding='utf-8-sig').splitlines()))
        probs = []
        if not rows or [x.strip() for x in rows[0]] != ['slot', 'source', 'source_frame', 'output_frame']:
            probs.append(f'header={rows[0] if rows else None}')
        body = [r for r in rows[1:] if any(x.strip() for x in r)]
        if len(body) != 6:
            probs.append(f'{len(body)} data rows')
        for r in body:
            try:
                s, src, sf, of = int(r[0]), r[1].strip(), int(r[2]), int(r[3])
                if s in ev:
                    probs.append(f'duplicate slot {s}')
                ev[s] = (src, sf, of)
                if s not in seg_ok:
                    probs.append(f'slot{s}: no valid segment'); continue
                gsrc, a, b, c, d = seg_ok[s]
                if src != gsrc:
                    probs.append(f'slot{s}: source {src} != {gsrc}')
                if not (a <= sf < b):
                    probs.append(f'slot{s}: source_frame {sf} not in [{a},{b})')
                if of - c != sf - a:
                    probs.append(f'slot{s}: output_frame {of} inconsistent (want {c + sf - a})')
            except Exception as e:
                probs.append(f'row {r}: {e}')
        if sorted(ev) != list(range(1, 7)):
            probs.append(f'slots {sorted(ev)}')
        put('B4', not probs, '; '.join(probs) or 'events.csv OK')
    except Exception as e:
        put('B4', False, f'events.csv unreadable: {e}')

    # ---- S / T ----
    for i in range(1, 7):
        key = keys.get(i, {})
        want = str(key.get('correct_source'))
        try:
            got = str(segs[i - 1]['source']) if segs and len(segs) >= i else None
        except Exception:
            got = None
        s_ok = got == want
        put(f'S{i}', s_ok, f'chosen={got} key={want}')
        try:
            probs = []
            if not s_ok:
                probs.append('S fails')
            if i not in seg_ok:
                probs.append('no valid segment')
            if i not in ev:
                probs.append('no events row')
            if not probs:
                src, a, b, c, d = seg_ok[i]
                esrc, sf, of = ev[i]
                lo, hi = key['change_window_source_frames']
                acc = slots_b[i]['accent_frame']
                mapped = c + sf - a
                if esrc != src:
                    probs.append(f'events source {esrc} != {src}')
                if not (lo <= sf <= hi):
                    probs.append(f'source_frame {sf} not in [{lo},{hi}]')
                if not (a <= sf < b):
                    probs.append(f'source_frame {sf} outside segment')
                if of != mapped:
                    probs.append(f'declared output_frame {of} != mapped {mapped}')
                if abs(mapped - acc) > 1:
                    probs.append(f'change lands at {mapped}, accent {acc}')
                if not slot_b3.get(i):
                    probs.append('B3 frame check failed for this slot')
            put(f'T{i}', not probs, '; '.join(probs) or 'change point on beat')
        except Exception as e:
            put(f'T{i}', False, f'error: {e}')
    return res
