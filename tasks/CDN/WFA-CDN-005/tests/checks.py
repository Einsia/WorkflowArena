# -*- coding: utf-8 -*-
"""CDC-A-X05 deterministic checks. All 15 rubric decisions are machine-checkable.

B1 deliverables / decode; B2 ffprobe spec + pts cadence; B3 decoded frame count;
B4 manifest contract; B5 per-segment frame-for-frame SSIM (gray, 11x11 gaussian sigma 1.5, >=0.95);
M1-M4/G1-G3 source vs answer key (zeroed when that slot's segment fails B5);
M5 edge gap >=12 frames to internal cuts of the chosen candidate; M6/G4 must_cover coverage.
"""
from fractions import Fraction
import json, subprocess
import numpy as np

W, H, FPS, TOTAL, GAP = 640, 360, 24, 1248, 12
SEL = {1: 'M1', 2: 'M2', 3: 'M3', 4: 'G1', 5: 'M4', 6: 'G2', 7: 'G3'}


def _run(cmd, timeout=600):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def _ffprobe_json(args, p):
    r = _run(['ffprobe', '-v', 'error'] + args + ['-of', 'json', str(p)], 300)
    return json.loads(r.stdout.decode('utf-8', 'replace') or '{}')


def _frames_gray(p):
    r = _run(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:v:0', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], 900)
    buf = np.frombuffer(r.stdout, np.uint8)
    n = buf.size // (W * H)
    return buf[:n * W * H].reshape(n, H, W)


def _ssim(a, b):
    import cv2
    a = a.astype(np.float64); b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    mu1, mu2 = g(a), g(b)
    s11 = g(a * a) - mu1 * mu1; s22 = g(b * b) - mu2 * mu2; s12 = g(a * b) - mu1 * mu2
    m = ((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 * mu1 + mu2 * mu2 + C1) * (s11 + s22 + C2))
    return float(m[5:-5, 5:-5].mean())


def _cand_frames(inp, sid):
    p = inp / f'{sid}.mp4'
    try:
        j = _ffprobe_json(['-select_streams', 'v:0', '-show_entries', 'stream=nb_frames'], p)
        return int(j['streams'][0]['nb_frames'])
    except Exception:
        return None


def run(ctx):
    out, inp, ans = ctx['out'], ctx['input'], ctx.get('answer') or {}
    R = {}
    F = lambda d: {'verdict': 'fail', 'detail': d}
    P = lambda d: {'verdict': 'pass', 'detail': d}
    mp4, js = out / 'solution.mp4', out / 'solution.json'

    # ---- B1
    segs, man, decoded = None, None, None
    try:
        files = sorted(x.name for x in out.iterdir()) if out.exists() else []
        try:
            man = json.loads(js.read_text(encoding='utf-8'))
        except Exception as e:
            man = None
            jerr = str(e)[:200]
        dec_ok = False
        if mp4.exists():
            r = _run(['ffmpeg', '-v', 'error', '-i', str(mp4), '-f', 'null', '-'], 600)
            dec_ok = r.returncode == 0 and not r.stderr.strip()
            derr = r.stderr.decode('utf-8', 'replace')[:300]
        if files != ['solution.json', 'solution.mp4']:
            R['B1'] = F(f'output files = {files}')
        elif man is None:
            R['B1'] = F(f'json parse error: {jerr}')
        elif not dec_ok:
            R['B1'] = F(f'mp4 decode error: {derr}')
        else:
            R['B1'] = P('exactly two files; mp4 decodes cleanly; json parses')
    except Exception as e:
        R['B1'] = F(f'error: {e}')

    # ---- B2 / B3
    nread = None
    if not mp4.exists():
        R['B2'] = F('solution.mp4 missing'); R['B3'] = F('solution.mp4 missing')
    else:
        try:
            j = _ffprobe_json(['-show_streams'], mp4)
            st = j.get('streams', [])
            v = [s for s in st if s.get('codec_type') == 'video']
            a = [s for s in st if s.get('codec_type') == 'audio']
            bad = []
            if len(v) != 1:
                bad.append(f'{len(v)} video streams')
            else:
                s = v[0]
                if s.get('codec_name') != 'h264': bad.append(f"codec={s.get('codec_name')}")
                if s.get('pix_fmt') != 'yuv420p': bad.append(f"pix_fmt={s.get('pix_fmt')}")
                if (s.get('width'), s.get('height')) != (W, H): bad.append(f"size={s.get('width')}x{s.get('height')}")
                if s.get('sample_aspect_ratio', '1:1') not in ('1:1', None): bad.append(f"sar={s.get('sample_aspect_ratio')}")
                if s.get('r_frame_rate') != '24/1': bad.append(f"r_frame_rate={s.get('r_frame_rate')}")
                # avg_frame_rate within 0.1 % (a stream-copy concat of 24 fps parts can report ~23.998);
                # constant cadence is enforced by the pts check below
                try:
                    avg_ok = abs(float(Fraction(str(s.get('avg_frame_rate', '0/1')))) - FPS) <= 0.024
                except (ValueError, ZeroDivisionError):
                    avg_ok = False
                if not avg_ok: bad.append(f"avg_frame_rate={s.get('avg_frame_rate')}")
            if a: bad.append(f'{len(a)} audio streams')
            if len(v) == 1 and not bad:
                fj = _ffprobe_json(['-select_streams', 'v:0', '-show_entries', 'frame=best_effort_timestamp_time'], mp4)
                ts = [float(f['best_effort_timestamp_time']) for f in fj.get('frames', []) if f.get('best_effort_timestamp_time') not in (None, 'N/A')]
                d = np.diff(np.array(ts)) if len(ts) > 1 else np.array([])
                if len(ts) < 2 or np.abs(d - 1 / FPS).max() > 0.002:
                    bad.append('non-constant pts cadence' + (f' (min {d.min():.4f} max {d.max():.4f})' if d.size else ''))
            R['B2'] = F('; '.join(bad)) if bad else P('h264 yuv420p 640x360 SAR1:1 24/1 CFR, no audio')
        except Exception as e:
            R['B2'] = F(f'error: {e}')
        try:
            j = _ffprobe_json(['-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames'], mp4)
            nread = int(j['streams'][0]['nb_read_frames'])
            last = None
            try:
                last = int(man['segments'][-1]['output_frames'][1])
            except Exception:
                pass
            # B3 = decoded length only; the manifest end is checked by B4 (no double count)
            if nread == TOTAL:
                R['B3'] = P(f'nb_read_frames={nread} (manifest end={last}, checked in B4)')
            else:
                R['B3'] = F(f'nb_read_frames={nread}, required {TOTAL}')
        except Exception as e:
            R['B3'] = F(f'error: {e}')

    # ---- B4 manifest
    b4 = []
    try:
        if not isinstance(man, dict) or not isinstance(man.get('segments'), list):
            b4.append('no segments list')
        else:
            segs = man['segments']
            if len(segs) != 7: b4.append(f'{len(segs)} segments')
            srcs, expect_c = [], 0
            for i, sg in enumerate(segs):
                try:
                    k, sid = sg['slot'], sg['source']
                    a, b = sg['source_frames']; c, d = sg['output_frames']
                    if not all(type(x) is int for x in (a, b, c, d)): b4.append(f'seg{i}: non-integer frames'); continue
                    if k != i + 1: b4.append(f'seg{i}: slot={k}')
                    if not (isinstance(sid, str) and len(sid) == 2 and sid.isdigit() and 1 <= int(sid) <= 45):
                        b4.append(f'seg{i}: bad source {sid!r}'); continue
                    srcs.append(sid)
                    if c != expect_c: b4.append(f'seg{i}: output start {c} != {expect_c}')
                    expect_c = d
                    if d - c != b - a: b4.append(f'seg{i}: d-c != b-a')
                    n = _cand_frames(inp, sid)
                    if not (0 <= a < b <= (n if n is not None else 10 ** 9)): b4.append(f'seg{i}: range [{a},{b}) vs {n} frames')
                except Exception as e:
                    b4.append(f'seg{i}: malformed ({e})')
            if len(set(srcs)) != len(srcs): b4.append('duplicate sources')
            if segs and expect_c != TOTAL: b4.append(f'last output end {expect_c} != {TOTAL}')
    except Exception as e:
        b4.append(f'error: {e}')
    R['B4'] = F('; '.join(b4)[:600]) if b4 else P('7 segments, contract satisfied')
    good_segs = segs if (segs and len(segs) == 7 and not b4) else None

    # ---- B5 honest splice (per segment)
    seg_ok = {k: False for k in range(1, 8)}
    try:
        if not mp4.exists() or not isinstance(segs, list):
            R['B5'] = F('missing video or manifest')
        else:
            O = _frames_gray(mp4)
            notes = []
            for i, sg in enumerate(segs[:7]):
                try:
                    k, sid = int(sg['slot']), sg['source']
                    a, b = map(int, sg['source_frames']); c, d = map(int, sg['output_frames'])
                    if d - c != b - a or a < 0 or c < 0 or d > len(O):
                        notes.append(f'slot{k}: bad ranges'); continue
                    S = _frames_gray(inp / f'{sid}.mp4')
                    if b > len(S):
                        notes.append(f'slot{k}: source has {len(S)} frames'); continue
                    worst, wi = 1.0, None
                    for t in range(b - a):
                        s = _ssim(O[c + t], S[a + t])
                        if s < worst: worst, wi = s, t
                        if s < 0.95: break
                    if worst >= 0.95:
                        seg_ok[k] = True
                    else:
                        notes.append(f'slot{k}: SSIM {worst:.3f} at seg frame {wi}')
                except Exception as e:
                    notes.append(f'seg{i}: error {e}')
            R['B5'] = P('all 7 segments frame-for-frame SSIM>=0.95') if all(seg_ok.values()) and len(segs) == 7 and not notes else F('; '.join(notes)[:600] or 'segment count != 7')
    except Exception as e:
        R['B5'] = F(f'error: {e}')

    # ---- selection items
    key = {s['slot']: s for s in ans.get('slots', [])}
    chosen = {}
    if isinstance(segs, list):
        for i, sg in enumerate(segs[:7]):
            try:
                chosen[i + 1] = (str(sg['source']), int(sg['source_frames'][0]), int(sg['source_frames'][1]))
            except Exception:
                pass
    for k, iid in SEL.items():
        want = key.get(k, {}).get('correct_source')
        got = chosen.get(k)
        if got is None:
            R[iid] = F(f'slot {k}: no valid segment')
        elif got[0] != want:
            R[iid] = F(f'slot {k}: chose {got[0]}, key {want}')
        elif not seg_ok[k]:
            R[iid] = F(f'slot {k}: correct source but segment failed B5 (group gate)')
        else:
            R[iid] = P(f'slot {k}: {got[0]}')

    # ---- M5 edge gap
    cuts = ans.get('internal_cuts_by_clip', {})
    if len(chosen) != 7:
        R['M5'] = F('manifest does not give 7 readable segments')
    else:
        bad = []
        for k, (sid, a, b) in chosen.items():
            for cut in cuts.get(sid, []):
                if a < cut < b and (cut - a < GAP or b - cut < GAP):
                    bad.append(f'slot{k} src{sid} [{a},{b}) cut {cut}')
        R['M5'] = F('; '.join(bad)) if bad else P('all in/out points >=12 frames from internal cuts')

    # ---- M6 / G4 coverage
    for iid, slots, need in (('M6', (1, 2, 3, 5), 2), ('G4', (4, 6, 7), 1)):
        correct = [k for k in slots if chosen.get(k) and chosen[k][0] == key.get(k, {}).get('correct_source')]
        miss = []
        for k in correct:
            lo, hi = key[k]['must_cover_clip_frames']
            _, a, b = chosen[k]
            if not (a <= lo and b >= hi): miss.append(f'slot{k} [{a},{b}) vs must_cover [{lo},{hi}]')
        if len(correct) < need:
            R[iid] = F(f'only {len(correct)} correct among slots {slots} (need {need})')
        elif miss:
            R[iid] = F('; '.join(miss))
        else:
            R[iid] = P(f'correct slots {correct} all cover must_cover')
    return R
