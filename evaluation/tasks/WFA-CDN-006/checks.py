# -*- coding: utf-8 -*-
"""CDC-A-X06 deterministic checks.

F1/F2  ffprobe spec + full decode without errors
F3     edl.json structure vs decoded frame counts; output/ has exactly 4 files
F4/F5  per-segment frame count == declared clip count; per-frame SSIM >= 0.95 (gray, 11x11 Gaussian sigma 1.5)
S-*    edl source per slot vs answer-key
E1     only the format part: if it fails -> fail; if it passes, left to the judge (reason content vs answer-key notes)
postprocess: group gate (F1/F4 fail -> all S-A* fail; F2/F5 fail -> all S-B*)
"""
import json, re, subprocess
import numpy as np

FPS = 24
W, H = 640, 360
VERS = {'comedy': ('A', 'F1', 'F4'), 'suspense': ('B', 'F2', 'F5')}
SSIM_MIN = 0.95


def _run(cmd, timeout=600):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _nframes(p, cache):
    k = str(p)
    if k not in cache:
        o = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
                  'stream=nb_read_frames', '-of', 'csv=p=0', k], 300).stdout.strip().split(',')[0]
        cache[k] = int(o) if o.isdigit() else None
    return cache[k]


def _gray_frames(p):
    """Yield gray frames (H, W) uint8 decoded at native size; raise if size differs."""
    proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:v:0', '-vsync', 'passthrough',
                             '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = W * H
    try:
        while True:
            b = proc.stdout.read(n)
            if len(b) < n:
                break
            yield np.frombuffer(b, np.uint8).reshape(H, W)
    finally:
        proc.stdout.close()
        proc.kill()
        proc.wait()


def _ssim(a, b):
    import cv2
    a = a.astype(np.float64); b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    mu1, mu2 = g(a), g(b)
    s1 = g(a * a) - mu1 * mu1
    s2 = g(b * b) - mu2 * mu2
    s12 = g(a * b) - mu1 * mu2
    m = ((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 ** 2 + mu2 ** 2 + C1) * (s1 + s2 + C2))
    return float(m[5:-5, 5:-5].mean())


def _fmt(p):
    if not p.exists():
        return False, 'missing'
    o = _run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(p)], 120).stdout
    try:
        st = json.loads(o)['streams']
    except Exception:
        return False, 'ffprobe failed'
    v = [s for s in st if s.get('codec_type') == 'video']
    a = [s for s in st if s.get('codec_type') == 'audio']
    if len(v) != 1:
        return False, f'{len(v)} video streams'
    s = v[0]
    bad = []
    if s.get('codec_name') != 'h264': bad.append(f"codec={s.get('codec_name')}")
    if s.get('pix_fmt') != 'yuv420p': bad.append(f"pix_fmt={s.get('pix_fmt')}")
    if (s.get('width'), s.get('height')) != (W, H): bad.append(f"size={s.get('width')}x{s.get('height')}")
    if s.get('sample_aspect_ratio') not in ('1:1', None, '0:1'): bad.append(f"sar={s.get('sample_aspect_ratio')}")
    def _rate(x):
        try:
            a, b = str(x).split('/'); return float(a) / float(b)
        except Exception:
            return 0.0
    # r_frame_rate must be exactly 24/1; avg may drift slightly with lossless concat (container timestamps)
    if s.get('r_frame_rate') != '24/1' or abs(_rate(s.get('avg_frame_rate')) - 24) > 0.024:
        bad.append(f"fps r={s.get('r_frame_rate')} avg={s.get('avg_frame_rate')}")
    if a: bad.append('has audio')
    # CFR: all frame pts deltas equal 1/24
    o = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'frame=pts_time,best_effort_timestamp_time',
              '-of', 'csv=p=0', str(p)], 300).stdout
    ts = []
    for line in o.split():
        for x in line.split(','):
            try:
                ts.append(float(x)); break
            except ValueError:
                pass
    if len(ts) > 2:
        d = np.diff(np.array(sorted(ts)))
        if np.abs(d - 1 / FPS).max() > 0.002:
            bad.append(f'non-CFR (dt range {d.min():.4f}..{d.max():.4f})')
    e = _run(['ffmpeg', '-v', 'error', '-i', str(p), '-f', 'null', '-'], 600).stderr.strip()
    if e:
        bad.append('decode errors: ' + e[:200])
    return (not bad), ('ok' if not bad else '; '.join(bad))


def _edl_check(out, inp, cache):
    """Return (ok, detail, parsed_segments_by_version or None)."""
    p = out / 'edl.json'
    try:
        j = json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        return False, f'edl.json unreadable: {e}', None
    bad, segs_by = [], {}
    files = sorted(x.name for x in out.iterdir())
    if sorted(files) != sorted(['comedy.mp4', 'suspense.mp4', 'edl.json', 'selection-evidence.json']):
        bad.append(f'output/ files = {files}')
    for ver, (L, _, _) in VERS.items():
        try:
            segs = j[ver]['segments']
            assert isinstance(segs, list)
        except Exception:
            bad.append(f'{ver}: no segments list'); continue
        segs_by[ver] = segs
        if len(segs) != 5:
            bad.append(f'{ver}: {len(segs)} segments')
        t, srcs = 0, []
        for k, s in enumerate(segs):
            try:
                if s.get('slot') != f'{L}{k + 1}': bad.append(f'{ver}[{k}] slot={s.get("slot")}')
                src = s.get('source')
                srcs.append(src)
                if not (isinstance(src, str) and re.fullmatch(r'\d\d', src) and (inp / f'{src}.mp4').exists()):
                    bad.append(f'{ver}[{k}] bad source {src!r}'); continue
                n = _nframes(inp / f'{src}.mp4', cache)
                of, sf, sec = s['output_frames'], s['source_frames'], s['output']
                if list(of) != [t, t + n]: bad.append(f'{ver}[{k}] output_frames {of} != {[t, t + n]}')
                if list(sf) != [0, n]: bad.append(f'{ver}[{k}] source_frames {sf} != [0,{n}]')
                if abs(float(sec[0]) - of[0] / FPS) > 0.001 or abs(float(sec[1]) - of[1] / FPS) > 0.001:
                    bad.append(f'{ver}[{k}] seconds {sec} != frames/24')
                t = int(of[1])
            except Exception as e:
                bad.append(f'{ver}[{k}] malformed: {e}')
        if len(set(srcs)) != len(srcs): bad.append(f'{ver}: repeated sources {srcs}')
        nv = _nframes(out / f'{ver}.mp4', cache) if (out / f'{ver}.mp4').exists() else None
        if nv != t: bad.append(f'{ver}: final end {t} != decoded {nv}')
    return (not bad), ('ok' if not bad else '; '.join(bad)[:1500]), segs_by


def _honest(video, inp, segs, cache):
    if not video.exists():
        return False, 'missing video'
    if not segs or len(segs) != 5:
        return False, 'edl segments missing/invalid'
    plan = []
    try:
        for s in segs:
            src = s['source']
            a, b = int(s['output_frames'][0]), int(s['output_frames'][1])
            n = _nframes(inp / f'{src}.mp4', cache)
            if n is None or b - a != n:
                return False, f'segment {s.get("slot")} length {b - a} != clip {src} frames {n}'
            plan.append((a, b, src))
    except Exception as e:
        return False, f'edl malformed: {e}'
    plan.sort()
    if plan[0][0] != 0 or any(plan[i][1] != plan[i + 1][0] for i in range(len(plan) - 1)):
        return False, 'segments not contiguous from 0'
    total = _nframes(video, cache)
    if total != plan[-1][1]:
        return False, f'video frames {total} != edl end {plan[-1][1]}'
    vid = _gray_frames(video)
    worst = (1.0, None)
    for a, b, src in plan:
        ref = _gray_frames(inp / f'{src}.mp4')
        for i in range(a, b):
            fv = next(vid, None); fr = next(ref, None)
            if fv is None or fr is None:
                return False, f'ran out of frames at output frame {i} (src {src})'
            v = _ssim(fv, fr)
            if v < worst[0]:
                worst = (v, (i, src))
            if v < SSIM_MIN:
                return False, f'SSIM {v:.3f} < {SSIM_MIN} at output frame {i} (clip {src} frame {i - a})'
    return True, f'all frames SSIM>={SSIM_MIN}; min {worst[0]:.4f} at {worst[1]}'


def _evidence(out, inp, segs_by, cache):
    try:
        ev = json.loads((out / 'selection-evidence.json').read_text(encoding='utf-8'))
    except Exception as e:
        return False, f'unreadable: {e}'
    if not isinstance(ev, list) or len(ev) != 10:
        return False, f'expected array of 10, got {type(ev).__name__} len {len(ev) if isinstance(ev, list) else "-"}'
    want = {}
    for ver, segs in (segs_by or {}).items():
        for s in segs:
            if isinstance(s, dict):
                want[(ver, s.get('slot'))] = s.get('source')
    bad, seen = [], set()
    for k, e in enumerate(ev):
        try:
            key = (e['version'], e['slot'])
            if key in seen: bad.append(f'dup {key}')
            seen.add(key)
            if want and want.get(key) != e['source']: bad.append(f'{key} source {e["source"]} != edl {want.get(key)}')
            a, b = int(e['source_frames'][0]), int(e['source_frames'][1])
            n = _nframes(inp / f'{e["source"]}.mp4', cache) if (inp / f'{e["source"]}.mp4').exists() else None
            if n is None: bad.append(f'[{k}] unknown source')
            elif not (0 <= a and b <= n and b - a >= 12): bad.append(f'[{k}] source_frames {[a, b]} invalid (clip {n})')
            if not (isinstance(e.get('reason'), str) and len(e['reason'].strip()) >= 10): bad.append(f'[{k}] empty reason')
        except Exception as ex:
            bad.append(f'[{k}] malformed: {ex}')
    exp = {(v, f'{L}{i}') for v, (L, _, _) in VERS.items() for i in range(1, 6)}
    if seen != exp: bad.append('version x slot set incomplete')
    return (not bad), ('format ok' if not bad else '; '.join(bad)[:1200])


def run(ctx):
    out, inp, ans = ctx['out'], ctx['input'], ctx.get('answer') or {}
    cache, res = {}, {}

    def put(i, ok, d):
        res[i] = {'verdict': 'pass' if ok else 'fail', 'detail': d}

    for ver, (L, fid, hid) in VERS.items():
        try:
            put(fid, *_fmt(out / f'{ver}.mp4'))
        except Exception as e:
            put(fid, False, f'error: {e}')
    segs_by = None
    try:
        ok, d, segs_by = _edl_check(out, inp, cache)
        put('F3', ok, d)
    except Exception as e:
        put('F3', False, f'error: {e}')
    for ver, (L, fid, hid) in VERS.items():
        try:
            put(hid, *_honest(out / f'{ver}.mp4', inp, (segs_by or {}).get(ver), cache))
        except Exception as e:
            put(hid, False, f'error: {e}')
    # slot selection
    key = {}
    for ver, v in (ans.get('versions') or {}).items():
        for s in v.get('segments', []):
            key[s['slot']] = s['source']
    for ver, (L, _, _) in VERS.items():
        segs = (segs_by or {}).get(ver) or []
        for i in range(1, 6):
            slot = f'{L}{i}'
            got = None
            try:
                got = next((s.get('source') for s in segs if isinstance(s, dict) and s.get('slot') == slot), None)
                if got is None and len(segs) >= i and isinstance(segs[i - 1], dict):
                    got = segs[i - 1].get('source')
            except Exception:
                pass
            if slot in key:
                put(f'S-{slot}', got == key[slot], f'chosen {got!r}, key {key[slot]}')
    try:
        ok, d = _evidence(out, inp, segs_by, cache)
        if not ok:
            put('E1', False, d)  # format part failed; reason content left to the judge otherwise
    except Exception as e:
        put('E1', False, f'error: {e}')
    return res


def postprocess(results, ctx):
    for ver, (L, fid, hid) in VERS.items():
        failed = [g for g in (fid, hid) if results.get(g, {}).get('verdict') != 'pass']
        if failed:
            for i in range(1, 6):
                k = f'S-{L}{i}'
                if k in results and results[k].get('verdict') == 'pass':
                    results[k] = dict(results[k], verdict='fail', detail=results[k].get('detail', '') + f' | gated: {"/".join(failed)} failed')
    return results
