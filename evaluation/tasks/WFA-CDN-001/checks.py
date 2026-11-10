# -*- coding: utf-8 -*-
"""CDC-A-X01 deterministic checks (called by rubric_score.py).

Machine-checked: B1 B2 B3 B4 M1 M2 M3 M4 G1-G5, and M5 (fail when fewer than 4
slots name a hidden near-miss as closest_alternative with a non-empty reason;
otherwise left to the judge, which compares those reasons with the answer-key
near_miss.why notes only).
SSIM: grayscale, long side 360 px, 11x11 Gaussian sigma=1.5, threshold 0.95.
"""
import json, re, subprocess, traceback
from pathlib import Path

N_TOTAL = 1650
SSIM_TH = 0.95
W, H = 360, 202
SLOT_ITEM = {1: 'G1', 2: 'G2', 3: 'G3', 4: 'M2', 5: 'M3', 6: 'G4', 7: 'G5'}


def _run(cmd, timeout=600, binary=False):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, text=not binary)
    return r


def _probe(p):
    r = _run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(p)], 120)
    return json.loads(r.stdout)


def _count_frames(p):
    r = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames',
              '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', str(p)], 300)
    return int(r.stdout.strip().split(',')[0])


def _decode_gray(p):
    import numpy as np
    r = _run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f'scale={W}:{H}:flags=area,format=gray',
              '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], 900, binary=True)
    buf = r.stdout
    n = len(buf) // (W * H)
    return np.frombuffer(buf[:n * W * H], dtype=np.uint8).reshape(n, H, W)


def _ssim(a, b):
    import cv2, numpy as np
    a = a.astype(np.float64); b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    mu_a, mu_b = g(a), g(b)
    saa = g(a * a) - mu_a ** 2
    sbb = g(b * b) - mu_b ** 2
    sab = g(a * b) - mu_a * mu_b
    m = ((2 * mu_a * mu_b + C1) * (2 * sab + C2)) / ((mu_a ** 2 + mu_b ** 2 + C1) * (saa + sbb + C2))
    return float(m[5:-5, 5:-5].mean())


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _rng(x):
    return isinstance(x, list) and len(x) == 2 and all(_is_int(v) for v in x)


def run(ctx):
    out, inp, ans = Path(ctx['out']), Path(ctx['input']), ctx.get('answer') or {}
    R = {}
    keyslots = {s['slot']: s for s in ans.get('slots', [])}
    mp4 = out / 'assembly.mp4'
    sel_p = out / 'selection.json'

    # ---- B4 ----
    try:
        files = sorted(p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()) if out.exists() else []
        ok = files == ['assembly.mp4', 'selection.json']
        R['B4'] = {'verdict': 'pass' if ok else 'fail', 'detail': f'files={files}'}
    except Exception as e:
        R['B4'] = {'verdict': 'fail', 'detail': f'error {e}'}

    # ---- B1 ----
    nframes = None
    b1_ok = False
    try:
        if not mp4.exists():
            raise ValueError('assembly.mp4 missing')
        j = _probe(mp4)
        st = j.get('streams', [])
        v = [s for s in st if s.get('codec_type') == 'video']
        a = [s for s in st if s.get('codec_type') == 'audio']
        probs = []
        if len(v) != 1:
            probs.append(f'{len(v)} video streams')
        else:
            v = v[0]
            if v.get('codec_name') != 'h264': probs.append(f"codec={v.get('codec_name')}")
            if v.get('pix_fmt') != 'yuv420p': probs.append(f"pix_fmt={v.get('pix_fmt')}")
            if (v.get('width'), v.get('height')) != (1280, 720): probs.append(f"size={v.get('width')}x{v.get('height')}")
            if v.get('sample_aspect_ratio', '1:1') not in ('1:1',): probs.append(f"sar={v.get('sample_aspect_ratio')}")
            if v.get('r_frame_rate') != '30/1' or v.get('avg_frame_rate') not in ('30/1',):
                probs.append(f"fps r={v.get('r_frame_rate')} avg={v.get('avg_frame_rate')}")
        if a:
            probs.append(f'{len(a)} audio streams')
        dec = _run(['ffmpeg', '-v', 'error', '-i', str(mp4), '-map', '0:v:0', '-f', 'null', '-'], 600)
        if dec.returncode != 0 or dec.stderr.strip():
            probs.append('decode errors: ' + dec.stderr.strip()[:200])
        # CFR: check pts deltas
        pk = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'frame=best_effort_timestamp_time',
                   '-of', 'csv=p=0', str(mp4)], 300).stdout.split()
        ts = []
        for t in pk:
            try: ts.append(float(t.strip(',')))
            except ValueError: pass
        try:
            nframes = _count_frames(mp4)
        except Exception:
            nframes = None
        if not nframes or len(ts) != nframes:
            probs.append(f'frame timestamps {len(ts)} vs decoded {nframes}')
        if len(ts) > 1:
            d = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
            if max(abs(x - 1 / 30) for x in d) > 0.004:
                probs.append('non-constant frame timing')
        b1_ok = not probs
        R['B1'] = {'verdict': 'pass' if b1_ok else 'fail', 'detail': '; '.join(probs) or f'ok, {nframes} frames'}
    except Exception as e:
        R['B1'] = {'verdict': 'fail', 'detail': f'{e}'}

    # ---- parse selection ----
    slots = None
    try:
        sel = json.loads(sel_p.read_text(encoding='utf-8'))
        slots = sel['slots']
        if not isinstance(slots, list):
            raise ValueError('slots not a list')
    except Exception as e:
        for k in ['B2', 'B3', 'M1', 'M2', 'M3', 'M4', 'M5', 'G1', 'G2', 'G3', 'G4', 'G5']:
            R[k] = {'verdict': 'fail', 'detail': f'selection.json unparsable: {e}'}
        return R

    # ---- B2 ----
    clip_len = {}
    def clen(sid):
        if sid not in clip_len:
            try: clip_len[sid] = _count_frames(inp / f'{sid}.mp4')
            except Exception: clip_len[sid] = None
        return clip_len[sid]
    probs = []
    try:
        if len(slots) != 7: probs.append(f'{len(slots)} slots')
        srcs = []
        for i, s in enumerate(slots):
            if not isinstance(s, dict): probs.append(f'#{i} not object'); continue
            if s.get('slot') != i + 1: probs.append(f'#{i} slot={s.get("slot")}')
            sid = s.get('source')
            if not (isinstance(sid, str) and re.fullmatch(r'\d\d', sid) and 1 <= int(sid) <= 40):
                probs.append(f'#{i} bad source {sid!r}'); continue
            srcs.append(sid)
            sf, of = s.get('source_frames'), s.get('output_frames')
            if not (_rng(sf) and _rng(of)): probs.append(f'#{i} bad ranges'); continue
            if not (sf[0] < sf[1] and of[0] < of[1]): probs.append(f'#{i} empty/reversed range')
            if sf[1] - sf[0] != of[1] - of[0]: probs.append(f'#{i} b-a != d-c')
            n = clen(sid)
            if n is None or sf[0] < 0 or sf[1] > n: probs.append(f'#{i} source_frames {sf} outside clip ({n})')
            if 'closest_alternative' not in s or 'reason' not in s: probs.append(f'#{i} missing closest_alternative/reason')
        if len(set(srcs)) != len(srcs): probs.append('duplicate sources')
        R['B2'] = {'verdict': 'pass' if not probs else 'fail', 'detail': '; '.join(probs) or 'ok'}
    except Exception as e:
        R['B2'] = {'verdict': 'fail', 'detail': f'error {e}'}

    good = [s for s in slots if isinstance(s, dict) and _rng(s.get('output_frames')) and _rng(s.get('source_frames'))]

    # ---- B3 ----
    try:
        ofs = [s.get('output_frames') for s in slots if isinstance(s, dict)]
        ok = len(ofs) == len(slots) and len(ofs) > 0 and all(_rng(x) for x in ofs)
        if ok:
            ok = ofs[0][0] == 0 and all(ofs[i][1] == ofs[i + 1][0] for i in range(len(ofs) - 1)) \
                 and ofs[-1][1] == N_TOTAL and nframes == N_TOTAL
        R['B3'] = {'verdict': 'pass' if ok else 'fail', 'detail': f'output_frames={ofs}, decoded={nframes}'}
    except Exception as e:
        R['B3'] = {'verdict': 'fail', 'detail': f'error {e}'}

    # ---- per-segment SSIM ----
    seg_ok = {}
    seg_detail = {}
    try:
        outf = _decode_gray(mp4) if mp4.exists() else None
        for s in slots:
            k = s.get('slot') if isinstance(s, dict) else None
            try:
                if outf is None: raise ValueError('no assembly')
                sf, of, sid = s['source_frames'], s['output_frames'], s['source']
                if not (_rng(sf) and _rng(of)) or sf[1] - sf[0] != of[1] - of[0] or sf[1] <= sf[0]:
                    raise ValueError('bad ranges')
                if of[0] < 0 or of[1] > len(outf): raise ValueError(f'output_frames {of} beyond {len(outf)} frames')
                srcf = _decode_gray(inp / f'{sid}.mp4')
                if sf[0] < 0 or sf[1] > len(srcf): raise ValueError(f'source_frames {sf} beyond clip ({len(srcf)})')
                worst, wi = 1.0, None
                for t in range(sf[1] - sf[0]):
                    v = _ssim(outf[of[0] + t], srcf[sf[0] + t])
                    if v < worst: worst, wi = v, t
                    if v < SSIM_TH: break
                seg_ok[k] = worst >= SSIM_TH
                seg_detail[k] = f'min SSIM {worst:.4f}' + (f' at seg frame {wi}' if wi is not None else '')
            except Exception as e:
                seg_ok[k] = False
                seg_detail[k] = f'error {e}'
    except Exception as e:
        seg_detail['_'] = f'decode error {e}'

    # ---- M1 ----
    try:
        ofs = [s.get('output_frames') for s in slots if isinstance(s, dict)]
        cover = all(_rng(x) for x in ofs) and ofs and ofs[0][0] == 0 and \
            all(ofs[i][1] == ofs[i + 1][0] for i in range(len(ofs) - 1)) and ofs[-1][1] == nframes
        ok = len(slots) == 7 and cover and all(seg_ok.get(i + 1) for i in range(7))
        R['M1'] = {'verdict': 'pass' if ok else 'fail',
                   'detail': f'segments cover all frames={bool(cover)}; ' + '; '.join(f's{k}:{v}' for k, v in seg_detail.items())}
    except Exception as e:
        R['M1'] = {'verdict': 'fail', 'detail': f'error {e}'}

    # ---- selection items + M4 ----
    correct = []
    for slot, item in SLOT_ITEM.items():
        try:
            s = slots[slot - 1]
            ks = keyslots[slot]
            hit = s.get('source') == ks['correct_source']
            if hit: correct.append(slot)
            ok = hit and seg_ok.get(slot, False) and s.get('slot') == slot
            R[item] = {'verdict': 'pass' if ok else 'fail',
                       'detail': f"source={s.get('source')} key={ks['correct_source']}; {seg_detail.get(slot, '')}"}
        except Exception as e:
            R[item] = {'verdict': 'fail', 'detail': f'error {e}'}
    try:
        bad = []
        for slot in correct:
            mk = keyslots[slot]['must_keep_source_frames']
            sf = slots[slot - 1].get('source_frames')
            if not (_rng(sf) and sf[0] <= mk[0] and sf[1] >= mk[1]):
                bad.append(f's{slot} {sf} !⊇ {mk}')
        ok = len(correct) >= 2 and not bad
        R['M4'] = {'verdict': 'pass' if ok else 'fail', 'detail': f'correct slots={correct}; ' + ('; '.join(bad) or 'all cover must-keep')}
    except Exception as e:
        R['M4'] = {'verdict': 'fail', 'detail': f'error {e}'}

    # ---- M5 (membership only; if >=4 hits leave reason-truth to the judge) ----
    try:
        hits = []
        for slot, ks in keyslots.items():
            s = slots[slot - 1] if slot - 1 < len(slots) else {}
            alt = str(s.get('closest_alternative', '')).strip() if isinstance(s, dict) else ''
            m = re.search(r'\d+', alt)
            alt = f'{int(m.group()):02d}' if m else alt
            reason = s.get('reason') if isinstance(s, dict) else None
            if alt in {n['id'] for n in ks.get('near_miss', [])} and isinstance(reason, str) and reason.strip():
                hits.append(slot)
        if len(hits) < 4:
            R['M5'] = {'verdict': 'fail', 'detail': f'near-miss membership hits with non-empty reason {hits} (<4)'}
    except Exception as e:
        R['M5'] = {'verdict': 'fail', 'detail': f'error {e}'}
    return R


def postprocess(results, ctx):
    b1 = results.get('B1', {})
    if b1.get('verdict') == 'fail' and ('missing' in b1.get('detail', '') or 'decode errors' in b1.get('detail', '')):
        results['_task_gate'] = {'verdict': 'fail', 'detail': 'critical B1: assembly.mp4 missing/undecodable -> task acceptance failed (continuous score still reported)'}
    return results
