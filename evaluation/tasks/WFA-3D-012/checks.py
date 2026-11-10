# -*- coding: utf-8 -*-
"""Deterministic checks for CDC-C-X02 (Club Night / Flag Fall). See review/VERIFIER_NOTES.md and
review/rubric-cleanup-20261025.md.
Each item independent; exceptions => fail with detail. Since 2026-10-25 every scored item is decided here except
M14 (qa.md truthfulness vs evidence), the visual remainder of G10 (returned here when its measured part fails) and the
visual narrative item G11. M15 (ASR) has weight 0. Film frame f is measured at Blender scene frame frame_start + f."""
import json, math, pathlib, re, sys, time, traceback
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import _cdc_lib as L
import _cdc_blend as B

REQ_EVENTS = ['w_lift', 'w_place', 'w_press', 'w_glance', 'demo_move_start', 'demo_move_end', 'b_capture_contact', 'knight_rest',
              'b_press', 'line_black_start', 'line_black_end', 'flag_fall', 'line_arbiter_start', 'line_arbiter_end', 'king_tip']
STEMS = ['speech', 'table', 'room']
SH = {'S1': (0, 119), 'S2': (120, 269), 'S3': (270, 389), 'S4': (390, 569), 'S5': (570, 719), 'S6': (720, 899)}
SH_REV = {'S1': (0, 119), 'S2': (120, 269), 'S3': (270, 374), 'S4': (375, 554), 'S5': (555, 704), 'S6': (705, 884)}
CUTS_BASE, CUTS_REV = [120, 270, 390, 570, 720], [120, 270, 375, 555, 705]
PIECES = ['W_KING', 'W_KNIGHT', 'W_PAWN', 'B_KING', 'B_ROOK']
CLOCK_PARTS = ['CLOCK_BUTTON_W', 'CLOCK_BUTTON_B', 'CLOCK_HAND_W', 'CLOCK_HAND_B', 'FLAG_W', 'FLAG_B']
RIGS = {'W': 'PLAYER_W_RIG', 'B': 'PLAYER_B_RIG', 'A': 'ARBITER_RIG'}
MESHES = {'W': 'PLAYER_W', 'B': 'PLAYER_B', 'A': 'ARBITER'}
CAMS = [f'CAM_S{i}' for i in range(1, 7)]
REQ_OBJ = {'PLAYER_W': 'MESH', 'PLAYER_B': 'MESH', 'ARBITER': 'MESH', 'PLAYER_W_RIG': 'ARMATURE', 'PLAYER_B_RIG': 'ARMATURE',
           'ARBITER_RIG': 'ARMATURE', 'BOARD': None, 'DEMO_BOARD': None, 'CLOCK': None,
           **{p: None for p in PIECES}, **{'DEMO_' + p: None for p in PIECES}, **{c: None for c in CLOCK_PARTS},
           **{c: 'CAMERA' for c in CAMS}}
TRACK = ['BOARD', 'DEMO_BOARD', 'CLOCK'] + PIECES + ['DEMO_' + p for p in PIECES] + CLOCK_PARTS + list(RIGS.values()) + list(MESHES.values()) + CAMS
START = {'W_KING': 'g2', 'W_KNIGHT': 'e3', 'W_PAWN': 'f2', 'B_KING': 'f7', 'B_ROOK': 'd5'}
END = {'W_KING': 'g2', 'W_PAWN': 'f2', 'B_KING': 'f7', 'B_ROOK': 'f5'}
SQ, SQ_DEMO = 0.055, 0.15                      # scene.json: board_square_size; demo board 1.2 m / 8
WORDS = {'black': 4, 'arbiter': 3}             # transcript.en.txt as written
HANDISH = re.compile(r'hand|palm|wrist|thumb|index|middle|ring|pinky|little|finger|f_', re.I)
BUDGET_S = 2400
STATE = {}


class _DumpFail(Exception):
    pass


def P(v, d):
    return {'verdict': 'pass' if v else 'fail', 'detail': str(d)[:900]}


def F(d):
    return {'verdict': 'fail', 'detail': str(d)[:900]}


def sqname(i, j):
    return 'abcdefgh'[i] + str(j + 1) if 0 <= i < 8 and 0 <= j < 8 else 'off'


def sq_centre(name):
    return np.array(['abcdefgh'.index(name[0]) - 3.5, int(name[1]) - 1 - 3.5])


BOARD_RENDER_PY = r'''
import bpy, sys, json, math
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
if getattr(bpy.app, "autoexec_fail", False):
    for _t in bpy.data.texts:
        if _t.use_module:
            try:
                exec(compile(_t.as_string(), _t.name, "exec"), {"__name__": _t.name})
            except Exception as _e:
                print("autoexec emulation failed for", _t.name, _e)
argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]; film_f = int(argv[1]); specs = json.loads(argv[2])
sc = bpy.context.scene
sc.frame_set(sc.frame_start + film_f)
for _m in sc.timeline_markers:          # camera-bound markers would override the grader camera
    _m.camera = None
res = {}
for sp in specs:
    bo = bpy.data.objects.get(sp["board"])
    if bo is None:
        continue
    mw = bo.matrix_world; R = mw.to_3x3().normalized(); s = sp["sq"]; side = sp["side"]
    cd = bpy.data.cameras.new("GRADER_TOP_" + bo.name); cd.type = "ORTHO"; cd.ortho_scale = 8 * s * 1.08
    cd.clip_start = 0.005; cd.clip_end = 0.6
    co = bpy.data.objects.new("GRADER_TOP_" + bo.name, cd); sc.collection.objects.link(co)
    rot = R.copy()
    if side < 0:                      # look at the -Z face: flip Z and X, keep +Y up
        rot = R @ Matrix(((-1, 0, 0), (0, 1, 0), (0, 0, -1)))
    co.matrix_world = Matrix.Translation(mw.translation + R @ Vector((0, 0, 0.3 * side))) @ rot.to_4x4()
    sc.camera = co
    sc.render.engine = "CYCLES"; sc.cycles.samples = 8
    sc.cycles.use_denoising = False   # not needed for square medians; Debian Blender 4.3.2 has no OpenImageDenoise
    try: sc.cycles.device = "CPU"
    except Exception: pass
    sc.render.resolution_x = sc.render.resolution_y = 96; sc.render.resolution_percentage = 100
    sc.render.use_compositing = False; sc.render.use_sequencer = False
    sc.render.image_settings.file_format = "OPEN_EXR"; sc.render.image_settings.color_depth = "32"
    sc.render.filepath = f"{out}_{bo.name}.exr"
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(f"{out}_{bo.name}.exr")       # scene-linear radiance, no view transform / clipping
    W_, H_ = img.size; pix = list(img.pixels[:])
    def lum(u, v):
        acc, n = 0.0, 0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x = int(round(u * W_)) + dx; y = int(round(v * H_)) + dy
                if 0 <= x < W_ and 0 <= y < H_:
                    k = 4 * (y * W_ + x); acc += 0.2126 * pix[k] + 0.7152 * pix[k + 1] + 0.0722 * pix[k + 2]; n += 1
        return acc / n if n else None
    px = {}
    for i in range(8):
        for j in range(8):
            loc = (i - 3.5) * s / max(bo.matrix_world.to_scale().x, 1e-9), (j - 3.5) * s / max(bo.matrix_world.to_scale().y, 1e-9)
            w = mw @ Vector((loc[0], loc[1], 0.0))
            uv = world_to_camera_view(sc, co, w)
            px["abcdefgh"[i] + str(j + 1)] = [uv.x, uv.y, lum(uv.x, uv.y) if 0.01 < uv.x < 0.99 and 0.01 < uv.y < 0.99 else None]
    res[bo.name] = {"px": px}
json.dump(res, open(out + ".json", "w"))
print("BOARD_RENDER_OK")
'''


def run(ctx):
    R = {}
    t_start = time.time()
    root = L.find_root(ctx['out'])
    base, rev, proj = root / 'base', root / 'revision', root / 'project'
    bmp, rmp = base / 'output.mp4', rev / 'output.mp4'
    tmp = ctx['tmp']

    def item(iid, fn):
        try:
            v = fn()
            if v is not None:
                R[iid] = v
        except _DumpFail as e:
            R[iid] = F(str(e))
        except Exception as e:
            R[iid] = F(f'check error: {type(e).__name__}: {e} | {traceback.format_exc()[-300:]}')

    item('B01', lambda: P(*L.video_contract(bmp if bmp.exists() else None, 900)))
    item('B02', lambda: P(*L.video_contract(rmp if rmp.exists() else None, 885)))

    def b03():
        det, ok = [], True
        for nm, p in (('base', bmp), ('revision', rmp)):
            if not p.exists():
                return F(f'{nm} master missing')
            I, tp = L.loudness(p, true_peak=True)
            nclip, _ = L.clipped_runs(p)
            ok &= abs(I + 23) <= 2 and tp is not None and tp <= -1.0 and nclip == 0
            det.append(f'{nm}: I={I} LUFS TP={tp} dBTP clipped_runs={nclip}')
        return P(ok, '; '.join(det))
    item('B03', b03)

    def b04():
        det, ok = [], True
        for s in STEMS:
            o, t = L.stem_format(base / 'stems' / f'{s}.wav', 30.0)
            ok &= o; det.append(t)
        if not ok:
            return F('; '.join(det))
        fit = L.stems_vs_mix(bmp, [base / 'stems' / f'{s}.wav' for s in STEMS])
        rd = fit['residual_db']
        det.append(f"residual {rd:.1f} dB lag {fit['lag_samples']} smp")
        if rd > -25 or abs(fit['lag_samples']) > 0.005 * L.SR:
            return F('; '.join(det))
        dec = L.find_gains(L.load_json(base / 'timeline.json'), STEMS)
        if dec is None:
            return F('; '.join(det) + '; declared master gains not locatable in base/timeline.json')
        gm, gd = L.gains_match(fit, dec, STEMS)
        return P(gm, '; '.join(det) + '; ' + gd)
    item('B04', b04)

    ev = {}
    evp = base / 'events.csv'

    def b05():
        if not evp.exists():
            return F('base/events.csv missing')
        hdr_ok, e, dup, bad = L.read_events(evp)
        ev.update(e)
        miss = [k for k in REQ_EVENTS if k not in e]
        dupr = [k for k in dup if k in REQ_EVENTS]
        rng = [k for k in REQ_EVENTS if k in e and not (0 <= e[k] <= 899)]
        badr = [k for k in bad if k in REQ_EVENTS]
        return P(hdr_ok and not (miss or dupr or rng or badr), f'header_ok={hdr_ok} missing={miss} duplicate={dupr} out_of_range={rng} non_integer={badr}')
    item('B05', b05)

    def b08():
        prob = []
        cr, qa = L.find_file(root, 'credits.md'), L.find_file(root, 'qa.md')
        if not cr:
            prob.append('credits.md missing')
        elif not re.search(r'espeak|sox|text[- ]to[- ]speech|tts|synthes|recorded|voice|speech', cr.read_text(encoding='utf-8', errors='ignore'), re.I):
            prob.append('credits.md does not say how the spoken lines were produced')
        if not qa:
            prob.append('qa.md missing')
        prob += L.scan_text_tree(root)[:5]
        return P(not prob, '; '.join(prob) if prob else 'credits/qa present, speech method stated, no credentials/URL media')
    item('B08', b08)

    def evreq(*ks):
        miss = [k for k in ks if k not in ev]
        if miss:
            raise _DumpFail(f'events.csv missing {miss}')
        return [ev[k] for k in ks]

    def m13():
        miss = [k for k in REQ_EVENTS if k not in ev]
        if miss:
            return F(f'events missing {miss}')
        e = ev
        inS = lambda k, s: SH[s][0] <= e[k] <= SH[s][1]
        conds = {
            'w_lift<w_place<w_press': e['w_lift'] < e['w_place'] < e['w_press'],
            'w_* in S2': all(inS(k, 'S2') for k in ('w_lift', 'w_place', 'w_press', 'w_glance')),
            'demo_move_start>w_press': e['demo_move_start'] > e['w_press'],
            'demo_* in S3': inS('demo_move_start', 'S3') and inS('demo_move_end', 'S3'),
            'capture/rest/b_press in S4, contact<rest': all(inS(k, 'S4') for k in ('b_capture_contact', 'knight_rest', 'b_press')) and e['b_capture_contact'] < e['knight_rest'],
            'flag_fall in S5': inS('flag_fall', 'S5'),
            'line_arbiter_start>=flag_fall+3': e['line_arbiter_start'] >= e['flag_fall'] + 3,
            'king_tip in S6': inS('king_tip', 'S6'),
        }
        bad = [k for k, v in conds.items() if not v]
        return P(not bad, 'failed: ' + ', '.join(bad) if bad else 'all rules hold')
    item('M13', m13)

    # ---------------- picture
    frames = {}

    def get_frames(nm, p):
        if nm not in frames:
            frames[nm] = L.gray_frames(p, 320, 180)
        return frames[nm]

    def cut_match(cuts, d, c):
        m = [x for x in cuts if abs(x - c) <= 1]
        if m:
            return m[0]
        med = float(np.median(d)) if len(d) else 0
        for x in (c, c - 1, c + 1):               # dim scenes: accept a clear local peak at the expected cut
            i = x - 1
            if 2 <= i < len(d) - 2:
                nb = max(d[i - 2], d[i - 1], d[i + 1], d[i + 2])
                if d[i] >= 3 * nb and d[i] > max(3.0, 3 * med):
                    return x
        return None

    def b07():
        if not bmp.exists():
            return F('base/output.mp4 missing')
        fr = get_frames('base', bmp)
        cuts, d, _fz, soft = L.detect_cuts(fr)
        prob = []
        for c in CUTS_BASE:
            m = cut_match(cuts, d, c)
            if m is None: prob.append(f'no cut at {c}±1')
            elif not L.hard_cut_ok(d, m): prob.append(f'blend frames at {m}')
        extra = [x for x in cuts if all(abs(x - c) > 1 for c in CUTS_BASE)]
        if extra: prob.append(f'extra cuts {extra[:10]}')
        fz = L.freeze_runs(bmp, 6)
        if fz: prob.append(f'freeze (>=6 frames identical up to codec rounding) at (start, length) {fz[:5]}')
        soft = [k for k in soft if any(abs(k - c) <= 6 for c in CUTS_BASE)]
        if soft: prob.append(f'gradual transition near {soft[:5]}')
        return P(not prob, f'cuts={cuts[:12]}; ' + ('; '.join(prob) if prob else 'ok'))
    item('B07', b07)

    # ---------------- audio
    au = {}

    def A(ver, s):
        if (ver, s) not in au:
            au[(ver, s)] = L.load_audio((base if ver == 'base' else rev) / 'stems' / f'{s}.wav', 1)
        return au[(ver, s)]

    def line_meas(name):
        segs = L.segments(A('base', 'speech'), -45, 10, 50, 300)
        ds, de = ev[f'line_{name}_start'] / 30, ev[f'line_{name}_end'] / 30
        if not segs:
            raise _DumpFail('no speech in the speech stem')
        sg = min(segs, key=lambda s: abs(s[0] - ds))
        e1 = max([s[1] for s in segs if sg[0] <= s[0] <= de + 0.3] + [sg[1]])
        return sg[0], e1, ds, de

    def m01():
        evreq('line_black_start', 'line_black_end', 'line_arbiter_start', 'line_arbiter_end')
        prob, det = [], []
        for n in ('black', 'arbiter'):
            a, b, ds, de = line_meas(n)
            wps = WORDS[n] / max(b - a, 1e-3)
            det.append(f'{n}: measured {a:.2f}-{b:.2f}s declared {ds:.2f}-{de:.2f}s, {wps:.1f} words/s')
            if abs(a - ds) > 0.2 or abs(b - de) > 0.2:
                prob.append(f'{n} timing off by >6 frames')
            if not 1.5 <= wps <= 5.0:
                prob.append(f'{n} speech rate {wps:.1f} words/s outside 1.5-5')
        return P(not prob, '; '.join(prob + det))
    item('M01', m01)

    def m02():
        x = A('base', 'speech')
        start = 20.0
        if 'line_black_start' in ev and 'line_black_end' in ev:
            try:
                start = max(20.0, line_meas('black')[1] + 0.1)
            except _DumpFail:
                pass
        on = L.onset_time(x, -50, 10, start=start)
        if on is None:
            return F(f'no arbiter onset after {start:.2f} s')
        prob = []
        if abs(on - 23.40) > 0.05: prob.append(f'arbiter onset {on:.3f}s (need 23.40±0.05)')
        if 'line_arbiter_start' not in ev or abs(ev['line_arbiter_start'] - 702) > 2: prob.append(f"declared line_arbiter_start={ev.get('line_arbiter_start')} (need 702±2)")
        seg = x[int(start * L.SR):int(23.35 * L.SR)]
        if seg.size > 480:
            mx = float(L.env_db(seg, 480).max())
            if mx >= -50: prob.append(f'speech level {mx:.1f} dBFS between black line end and 23.35 s')
        return P(not prob, f'onset {on:.3f}s (searched from {start:.2f}s); ' + ('; '.join(prob) if prob else 'ok'))
    item('M02', m02)

    def m03():
        evreq('line_black_start', 'line_black_end')
        a, b, ds, de = line_meas('black')
        ok = 13.0 <= a <= 19.0 and 19.15 < b < 23.35
        return P(ok, f'black line measured {a:.2f}-{b:.2f}s (onset in 13-19, end in 19.15-23.35)')
    item('M03', m03)

    def fx():
        return A('base', 'table') + A('base', 'room')     # foley may sit in either stem

    def m08():
        evreq('w_place', 'w_press', 'b_press', 'b_capture_contact', 'knight_rest')
        x = fx()
        det, ok = [], True
        for k in ('w_place', 'w_press', 'b_press'):
            o, d = L.transient_at(x, ev[k] / 30, 2 / 30, 12.0, 0.2, 5)
            ok &= o; det.append(f'{k}: {d}')
        on = L.onsets(x)
        a, b = ev['b_capture_contact'] / 30, ev['knight_rest'] / 30
        n = len([t for t in on if a <= t <= b])
        ok &= n >= 2
        det.append(f'{n} transients between capture and rest')
        return P(ok, '; '.join(det) + ' (table+room stems)')
    item('M08', m08)

    def m09():
        on = [t for t in L.onsets(fx(), 10.0, 5, 200, 60) if 19.0 <= t <= 24.0]
        best = 0
        for i in range(len(on)):
            for j in range(i + 3, len(on)):
                iv = np.diff(on[i:j + 1])
                if iv.min() >= 0.1 and iv.max() <= 1.2 and iv.std() / iv.mean() <= 0.2:
                    best = max(best, j - i + 1)
        return P(best >= 4, f'{len(on)} onsets in S5 (table+room); longest periodic run {best}')
    item('M09', m09)

    def tl_rev_ok():
        tl = L.load_json(rev / 'timeline.json')
        nums = []

        def walk(o, path=''):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, path + '/' + str(k).lower())
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    walk(v, path + f'[{i}]')
            elif isinstance(o, (int, float)) and not isinstance(o, bool):
                nums.append(float(o))
        walk(tl)
        has = lambda fr: any(abs(v - fr) <= 1 or abs(v * 30 - fr) <= 1 for v in nums)
        need = [375, 555, 705]
        old = [390, 570, 720]
        ok = all(has(x) for x in need) and (has(884) or has(885)) and not all(has(x) for x in old)
        return ok, f'revision timeline: shot starts 375/555/705 present={all(has(x) for x in need)}, end 884/885 present={has(884) or has(885)}, old 390/570/720 all present={all(has(x) for x in old)}'

    def m11():
        if not (bmp.exists() and rmp.exists()):
            return F('master missing')
        prob, det = [], []
        b, r = get_frames('base', bmp), get_frames('rev', rmp)
        if len(r) != 885:
            prob.append(f'rev frames {len(r)}')
        else:
            p1 = [L.psnr(r[f], b[f]) for f in range(0, 375, 10)]
            p2 = [L.psnr(r[f], b[f + 15]) for f in range(375, 885, 10) if f + 15 < len(b)]
            det.append(f'PSNR min {min(p1):.1f}/{min(p2):.1f}')
            if min(p1) < 30 or min(p2) < 30: prob.append(f'picture PSNR {min(p1):.1f}/{min(p2):.1f} < 30')
        bm, rm = L.load_audio(bmp, 1), L.load_audio(rmp, 1)
        n = int(12.5 * L.SR)
        x, y = L.lowpass(bm[:n]), L.lowpass(rm[:n])
        lag = L.best_lag(x, y, int(0.02 * L.SR)); y2 = L.shift(y, lag, n)
        g = float(np.dot(x, y2) / max(np.dot(y2, y2), 1e-20))
        res = 10 * math.log10(max(((x - g * y2) ** 2).mean(), 1e-30) / max((x ** 2).mean(), 1e-20))
        det.append(f'pre-12.5s residual {res:.1f} dB')
        if res > -25: prob.append(f'pre-12.5 s audio differs ({res:.1f} dB)')
        a0 = int(13.0 * L.SR)
        lag2 = L.best_lag(bm[a0:], rm[a0 - int(1.0 * L.SR):], int(1.0 * L.SR))
        sh = (lag2 - int(1.0 * L.SR)) / L.SR
        det.append(f'post shift {sh:+.4f}s')
        if abs(sh + 0.5) > 0.01: prob.append(f'post-12.5 s shift {sh:+.3f}s (need -0.500±0.01)')
        if not (rev / 'timeline.json').exists():
            prob.append('revision/timeline.json missing')
        else:
            ok_tl, dtl = tl_rev_ok()
            det.append(dtl)
            if not ok_tl: prob.append('revision timeline.json not consistent with the ripple delete')
        return P(not prob, '; '.join(prob + det))
    item('M11', m11)

    # ---------------- blender
    blend = proj / 'scene.blend'
    DUMPS = {}

    def get_dump(trim=None):
        if trim in DUMPS:
            return DUMPS[trim]
        if not blend.exists():
            DUMPS[trim] = {'ok': False, 'opened': False, 'error': 'project/scene.blend missing'}
            return DUMPS[trim]
        if not B.blender_ok():
            raise RuntimeError('blender not on PATH in the verifier image (grader problem)')
        n = 900 if trim is None else 885
        cfg = {'film_frames': list(range(0, n)), 'track': TRACK, 'rigs': list(RIGS.values()), 'cams': CAMS, 'mat_re': r'head',
               'samples': {k: 400 for k in ['BOARD', 'DEMO_BOARD', 'CLOCK'] + PIECES + CLOCK_PARTS},
               'bbox_world': {m: [0] for m in MESHES.values()}}
        if trim is not None:
            cfg['props'] = {'revision_trim_frames': int(trim)}
            cfg = {k: v for k, v in cfg.items() if k in ('film_frames', 'track', 'props', 'samples')}
        D = B.rich_dump(blend, cfg, tmp, timeout=1500 if trim is None else 900, tag=f'trim{trim}')
        DUMPS[trim] = D
        if trim is None:
            STATE['dump_seconds'] = D.get('wall_seconds')
            STATE['dump_warnings'] = (D.get('warnings') or [])[:8]
        return D

    def need(trim=None):
        d = get_dump(trim)
        if not d.get('ok'):
            raise _DumpFail(('revision (revision_trim_frames=15) ' if trim else '') + 'Blender inspection of project/scene.blend failed: ' + str(d.get('error'))[-300:])
        return d

    def has(d, *names):
        miss = [n for n in names if n not in d['objects']]
        if miss:
            raise _DumpFail(f'required objects missing: {miss}')

    mw = lambda d, n, f: B.M(d, n, f)

    def centroid_w(d, n, f):
        s = d['samples'].get(n)
        if s:
            return B.xf(mw(d, n, f), np.array(s, float)).mean(0)
        return mw(d, n, f)[:3, 3]

    def pts_w(d, n, f):
        s = d['samples'].get(n)
        if not s:
            return mw(d, n, f)[:3, 3][None]
        return B.xf(mw(d, n, f), np.array(s, float))

    def b06():
        d = get_dump()
        if not d.get('ok'):
            if d.get('opened') is False:
                return F('scene.blend missing or failed to open headless: ' + str(d.get('error'))[-400:])
            return dict(F('Blender inspection failed (not a file-open error; PROJ group gate not applied): ' + str(d.get('error'))[-400:]), nogate=True)
        obj = d['objects']
        prob = [f'{n} missing' for n in REQ_OBJ if n not in obj] + [f'{n} type {obj[n]}' for n, t in REQ_OBJ.items() if t and n in obj and obj[n] != t]
        if 'revision_trim_frames' not in d['scene_props']: prob.append('revision_trim_frames missing')
        return P(not prob, '; '.join(prob[:15]) if prob else f"all named objects present (frame_start={d['frame_range'][0]})")
    item('B06', b06)

    # -- chess geometry: board-local coordinates; square size fitted to the known start position
    def local_xy(d, board, piece, f):
        m = mw(d, board, f)
        p = np.linalg.inv(m) @ np.append(centroid_w(d, piece, f), 1.0)
        sc = np.linalg.norm(m[:3, :3], axis=0)
        return p[:2] * sc[:2], p[2] * sc[2]          # metres along the board axes

    def fit_square(d, board, prefix, f, nominal):
        P_ = np.array([local_xy(d, board, prefix + p, f)[0] for p in START])
        Q = np.array([sq_centre(START[p]) for p in START])
        s = float((P_ * Q).sum() / (Q * Q).sum())
        return s, P_, Q

    def which(d, board, piece, f, s):
        xy, z = local_xy(d, board, piece, f)
        x, y = xy[0] / s + 4, xy[1] / s + 4
        i, j = int(math.floor(x)), int(math.floor(y))
        return sqname(i, j), max(abs(x - (i + 0.5)), abs(y - (j + 0.5))), z

    def m04():
        d = need(); has(d, 'BOARD', *PIECES)
        s, P_, Q = fit_square(d, 'BOARD', '', 0, SQ)
        prob = []
        if not abs(s - SQ) / SQ <= 0.15: prob.append(f'fitted square size {s:.4f} m vs {SQ} (>15%)')
        bb = np.array(d['bbox_local'].get('BOARD') or [], float)
        if bb.size:
            ext = (bb.max(0) - bb.min(0))[:2] * np.linalg.norm(mw(d, 'BOARD', 0)[:3, :3], axis=0)[:2]
            if ext.min() < 8 * s * 0.95 or ext.max() > 8 * s + 0.08 + 0.05 * 8 * s:
                prob.append(f'BOARD outline {np.round(ext, 3).tolist()} m inconsistent with 8 x {s:.4f} m + border <= 4 cm/side')
        Rb = B.rot_of(mw(d, 'BOARD', 0))
        for p, sq in START.items():
            nm, off, _ = which(d, 'BOARD', p, 0, s)
            zang = math.degrees(math.acos(np.clip(np.dot(Rb[:, 2], B.rot_of(mw(d, p, 0))[:, 2]), -1, 1)))
            if nm != sq or off > 0.3: prob.append(f'{p} on {nm} (off {off:.2f}) need {sq}')
            if zang > 15: prob.append(f'{p} tilted {zang:.0f}°')
        others = [n for n in d['objects'] if n not in PIECES and re.match(r'^(W|B)_(KING|QUEEN|ROOK|BISHOP|KNIGHT|PAWN)', n)]
        for n in others:
            if n in d['mats'].get(0, {}):
                nm, _, z = which(d, 'BOARD', n, 0, s)
                if nm != 'off' and abs(z) < 0.1: prob.append(f'extra piece {n} on {nm}')
        return P(not prob, '; '.join(prob) if prob else f'frame-0 position matches the FEN (fitted square {s:.4f} m)')
    item('M04', m04)

    def m05():
        bp, kt = evreq('b_press', 'king_tip')
        d = need(); has(d, 'BOARD', *PIECES)
        s, _, _ = fit_square(d, 'BOARD', '', 0, SQ)
        fr = [f for f in range(bp + 1, kt) if f in d['mats']]
        if not fr:
            return F('empty b_press..king_tip window')
        prob = []
        for f in fr[::3] + [fr[-1]]:
            for p, sq in END.items():
                nm, off, _ = which(d, 'BOARD', p, f, s)
                if nm != sq or off > 0.3: prob.append(f'f{f} {p} on {nm} need {sq}')
            nm, _, _ = which(d, 'BOARD', 'W_KNIGHT', f, s)
            if nm != 'off': prob.append(f'f{f} W_KNIGHT on {nm}')
        for p in END:
            mv = np.linalg.norm(mw(d, p, fr[-1])[:3, 3] - mw(d, p, fr[0])[:3, 3])
            if mv > 0.005: prob.append(f'{p} moved {mv*100:.1f} cm')
        return P(not prob, '; '.join(sorted(set(prob))[:10]) if prob else 'final position correct and static')
    item('M05', m05)

    def m06():
        ds_, de_ = evreq('demo_move_start', 'demo_move_end')
        d = need(); has(d, 'DEMO_BOARD', *['DEMO_' + p for p in PIECES])
        f0, f1 = max(0, ds_ - 1), min(899, de_ + 1)
        s, _, _ = fit_square(d, 'DEMO_BOARD', 'DEMO_', f0, SQ_DEMO)
        prob = []
        if not 0.05 <= s <= 0.2: prob.append(f'demo square size {s:.3f} m implausible')
        for f, tgt in ((f0, START), (f1, {**START, 'W_KNIGHT': 'f5'})):
            for p, sq in tgt.items():
                nm, off, _ = which(d, 'DEMO_BOARD', 'DEMO_' + p, f, s)
                if nm != sq or off > 0.3: prob.append(f'f{f} DEMO_{p} on {nm} need {sq}')
        R_ = B.rot_of(mw(d, 'DEMO_BOARD', f0))
        nz = math.degrees(math.asin(min(1, abs(R_[2, 2]))))
        yz = math.degrees(math.acos(np.clip(R_[2, 1], -1, 1)))
        if nz > 15: prob.append(f'demo board normal {nz:.0f}° from horizontal')
        if yz > 15: prob.append(f'local +Y {yz:.0f}° from world up (1st rank not at bottom)')
        return P(not prob, '; '.join(prob[:10]) if prob else f'demo board mirrors the move (square {s:.3f} m), vertical, rank 1 at bottom')
    item('M06', m06)

    def clock_local(d, n, f):
        """Point of part n (sample centroid) in CLOCK local coordinates (metres)."""
        m = mw(d, 'CLOCK', f)
        p = np.linalg.inv(m) @ np.append(centroid_w(d, n, f), 1.0)
        return p[:3] * np.linalg.norm(m[:3, :3], axis=0)

    def m07():
        wp, bp = evreq('w_press', 'b_press')
        d = need(); has(d, 'CLOCK', 'CLOCK_BUTTON_W', 'CLOCK_BUTTON_B')
        fs = sorted(d['mats'])
        det, ok = [], True
        exp = {'CLOCK_BUTTON_W': [(wp, -1), (bp, +1)], 'CLOCK_BUTTON_B': [(wp, +1), (bp, -1)]}
        for b, want in exp.items():
            h = np.array([clock_local(d, b, f)[2] for f in fs])
            if np.ptp(h) < 0.001:
                ok = False; det.append(f'{b} does not move'); continue
            st = (h > (h.max() + h.min()) / 2).astype(int)
            ch = [(fs[i + 1], int(st[i + 1] - st[i])) for i in range(len(st) - 1) if st[i + 1] != st[i]]
            good = len(ch) == len(want) and all(abs(c[0] - w[0]) <= 2 and c[1] == w[1] for c, w in zip(ch, want))
            ok &= good
            det.append(f'{b}: transitions {ch[:6]} expected {want}')
        return P(ok, '; '.join(det) + ' (heights in CLOCK local coordinates)')
    item('M07', m07)

    def hand_series(d, name):
        fs = sorted(d['mats'])
        Rh = {f: B.rot_of(mw(d, 'CLOCK', f)).T @ B.rot_of(mw(d, name, f)) for f in fs}
        step = {}
        for f in fs[1:]:
            if f - 1 in Rh:
                Rr = Rh[f - 1].T @ Rh[f]
                ax = np.array([Rr[2, 1] - Rr[1, 2], Rr[0, 2] - Rr[2, 0], Rr[1, 0] - Rr[0, 1]])
                nrm = np.linalg.norm(ax)
                step[f] = (B.rot_angle(Rh[f - 1], Rh[f]), ax / nrm if nrm > 1e-12 else np.zeros(3))
        return fs, Rh, step

    def clock_logic(d, wp, bp, ff, end):
        det, ok = [], True

        def moving(name, a, b):
            fs, Rh, step = hand_series(d, name)
            fr = [f for f in range(a + 3, b - 2) if f in step]
            if not fr:
                return False, f'{name} [{a},{b}) empty window'
            tot = B.rot_angle(Rh[fr[0] - 1], Rh[fr[-1]])
            axes = [step[f][1] for f in fr if step[f][0] > 1e-4]
            if tot < 0.2 or not axes:
                return False, f'{name} [{a},{b}) turns only {tot:.3f}°'
            mono = all(np.dot(x, axes[0]) > 0 for x in axes)
            return mono, f'{name} [{a},{b}) turns {tot:.2f}° monotone={mono}'

        def still(name, a, b):
            fs, Rh, step = hand_series(d, name)
            fr = [f for f in range(a + 2, b - 2) if f in Rh]
            if len(fr) < 2:
                return True, f'{name} [{a},{b}) empty'
            mx = max(B.rot_angle(Rh[fr[0]], Rh[f]) for f in fr)
            return mx < 0.2, f'{name} [{a},{b}) max drift {mx:.3f}°'
        for fn, args in ((moving, ('CLOCK_HAND_W', 0, wp)), (still, ('CLOCK_HAND_W', wp, bp)), (moving, ('CLOCK_HAND_W', bp, ff + 1)),
                         (still, ('CLOCK_HAND_B', 0, wp)), (moving, ('CLOCK_HAND_B', wp, bp)), (still, ('CLOCK_HAND_B', bp, end))):
            o, dd = fn(*args)
            ok &= o; det.append(dd)
        return ok, det

    def g01():
        wp, bp, ff = evreq('w_press', 'b_press', 'flag_fall')
        d = need(); has(d, 'CLOCK', 'CLOCK_HAND_W', 'CLOCK_HAND_B')
        ok, det = clock_logic(d, wp, bp, ff, 900)
        return P(ok, '; '.join(det))
    item('G01', g01)

    def flag_rel(d, n, f):
        return B.rot_of(mw(d, 'CLOCK', f)).T @ B.rot_of(mw(d, n, f))

    def flag_logic(d, ff, last, s5, cam):
        prob, det = [], []
        a_before = flag_rel(d, 'FLAG_W', max(0, ff - 3))
        drop = B.rot_angle(a_before, flag_rel(d, 'FLAG_W', min(last, ff + 3)))
        end = B.rot_angle(a_before, flag_rel(d, 'FLAG_W', last))
        bmax = max(B.rot_angle(flag_rel(d, 'FLAG_B', 0), flag_rel(d, 'FLAG_B', f)) for f in range(0, last + 1, 5))
        lift = B.rot_angle(flag_rel(d, 'FLAG_W', max(0, ff - 63)), a_before)
        fs, Rh, step = hand_series(d, 'CLOCK_HAND_W')
        hand_turn = B.rot_angle(Rh[max(0, ff - 63)], Rh[max(0, ff - 3)])
        if drop < 45: prob.append(f'FLAG_W drops only {drop:.0f}° within flag_fall±3')
        if end < 45: prob.append(f'FLAG_W not down at the end ({end:.0f}°)')
        if bmax >= 45: prob.append(f'FLAG_B rotates {bmax:.0f}°')
        if lift < 5 or hand_turn < 0.05: prob.append(f'FLAG_W not lifted before the fall (lift {lift:.1f}° while CLOCK_HAND_W turned {hand_turn:.2f}°)')
        if not (s5[0] <= ff <= s5[1]): prob.append(f'flag_fall {ff} outside S5 {s5}')
        if cam:
            uvz = B.project(d, cam, ff, centroid_w(d, 'FLAG_W', ff)[None])[0]
            if not (uvz[2] > 0 and 0 <= uvz[0] <= 1 and 0 <= uvz[1] <= 1): prob.append(f'FLAG_W outside the {cam} frame at flag_fall (u={uvz[0]:.2f}, v={uvz[1]:.2f})')
        det.append(f'lift {lift:.1f}°, drop {drop:.0f}°, end {end:.0f}°, FLAG_B max {bmax:.0f}°')
        return prob, det

    def g02():
        ff, = evreq('flag_fall')
        d = need(); has(d, 'CLOCK', 'FLAG_W', 'FLAG_B', 'CLOCK_HAND_W', 'CAM_S5')
        prob, det = flag_logic(d, ff, 899, SH['S5'], 'CAM_S5')
        return P(not prob, '; '.join(prob + det))
    item('G02', g02)

    # -- rigs / hands / heads
    def bones_of(d, rig, f, pat=HANDISH, side=None):
        names = [b for b in d['sampled_bones'].get(rig, []) if pat.search(b) and (side is None or B.side_of(b) == side)]
        return B.bone_segs(d, rig, f, set(names))

    def head_pt(d, rig, f):
        row = d['bones'].get(rig, {}).get(f, {})
        hs = [b for b in row if re.search(r'head', b, re.I) and not re.search(r'target|ctrl|mch', b, re.I)]
        if hs:
            b = sorted(hs, key=lambda x: (not x.startswith('DEF'), len(x)))[0]
            return np.array(row[b][3:6]) * 0.5 + np.array(row[b][0:3]) * 0.5, b
        if row:
            b = max(row, key=lambda k: row[k][5])
            return np.array(row[b][3:6]), b
        return mw(d, rig, f)[:3, 3] + np.array([0, 0, 1.6]), None

    def hand_side_near(d, rig, f, P_):
        best = (np.inf, None)
        for side in ('L', 'R'):
            ks, segs = bones_of(d, rig, f, side=side)
            if len(segs):
                dd = float(B.seg_point_dist(segs, P_).min())
                if dd < best[0]:
                    best = (dd, side)
        if best[1] is None:            # sides not named: armature-local x sign of the nearest hand bone
            ks, segs = bones_of(d, rig, f)
            if not len(segs):
                return np.inf, None
            dd = B.seg_point_dist(segs, P_)
            i = int(np.argmin(dd))
            loc = np.linalg.inv(mw(d, rig, f)) @ np.append(segs[i, 3:6], 1)
            best = (float(dd[i]), 'L' if loc[0] > 0 else 'R')
        return best

    def m10():
        d = need(); has(d, *CAMS, *RIGS.values())
        prob, det = [], []

        def series(cam, a, b):
            fs = list(range(a, b + 1))
            ms = [mw(d, cam, f) for f in fs]
            return fs, ms, np.array([m[:3, 3] for m in ms]), np.array([B.cam_pitch(m) for m in ms]), [d['cams'][cam][f] for f in fs]

        def inframe(cam, f, p):
            u = B.project(d, cam, f, np.asarray(p)[None])[0]
            return u[2] > 0 and 0 <= u[0] <= 1 and 0 <= u[1] <= 1, u
        fs, ms, pos, pit, ci = series('CAM_S1', *SH['S1'])
        disp = float(np.linalg.norm(pos - pos[0], axis=1).max())
        heads = all(inframe('CAM_S1', f, head_pt(d, r, f)[0])[0] for f in (fs[0], fs[len(fs) // 2], fs[-1]) for r in RIGS.values())
        if not (pit.max() <= -8 and disp < 0.01 and heads): prob.append('S1')
        det.append(f'S1 pitch max {pit.max():.1f} disp {disp*100:.1f}cm heads_in_frame={heads}')
        for s, cam, fg, other in (('S2', 'CAM_S2', 'B', 'W'), ('S4', 'CAM_S4', 'W', 'B')):
            fs, ms, pos, pit, ci = series(cam, *SH[s])
            fm = fs[len(fs) // 2]
            hf, ho = head_pt(d, RIGS[fg], fm)[0], head_pt(d, RIGS[other], fm)[0]
            _, uf = inframe(cam, fm, hf)
            nearer = np.linalg.norm(hf - pos[len(fs) // 2]) < np.linalg.norm(ho - pos[len(fs) // 2])
            outer = uf[2] > 0 and (uf[0] < 0.4 or uf[0] > 0.6)
            dof = all(c['dof'] and c['fstop'] <= 5.6 for c in ci)
            if not (nearer and outer and dof): prob.append(s)
            det.append(f'{s} foreground {fg} head u={uf[0]:.2f} nearer={nearer} dof f<=5.6={dof}')
        fs, ms, pos, pit, ci = series('CAM_S3', *SH['S3'])
        fwd = B.cam_forward(ms[0])
        dv = pos[-1] - pos[0]
        lat = float(np.linalg.norm(dv - np.dot(dv, fwd) * fwd))
        if lat < 0.1: prob.append('S3')
        det.append(f'S3 lateral truck {lat*100:.1f}cm')
        fs, ms, pos, pit, ci = series('CAM_S5', *SH['S5'])
        fm = fs[len(fs) // 2]
        cl = np.vstack([pts_w(d, n, fm) for n in ['CLOCK'] + [c for c in CLOCK_PARTS if c in d['objects']]])
        box, area, vis = B.proj_box(B.project(d, 'CAM_S5', fm, cl))
        wfrac = (min(box[2], 1) - max(box[0], 0)) if box else 0
        dof5 = all(c['dof'] for c in ci)
        if not (wfrac >= 0.35 and dof5): prob.append('S5')
        det.append(f'S5 CLOCK width {wfrac:.2f} of frame, dof={dof5}')
        fs, ms, pos, pit, ci = series('CAM_S6', *SH['S6'])
        hw = [head_pt(d, RIGS['W'], f)[0] for f in (fs[0], fs[-1])]
        hb = [head_pt(d, RIGS['B'], f)[0] for f in (fs[0], fs[-1])]
        inb = all(inframe('CAM_S6', f, h)[0] for f, h in zip((fs[0], fs[-1]), hw)) and all(inframe('CAM_S6', f, h)[0] for f, h in zip((fs[0], fs[-1]), hb))
        axis = hb[0] - hw[0]
        ang = math.degrees(math.acos(abs(np.dot(axis / np.linalg.norm(axis), B.cam_forward(ms[0])))))
        mid0, mid1 = (hw[0] + hb[0]) / 2, (hw[1] + hb[1]) / 2
        dolly = float(np.linalg.norm(mid0 - pos[0]) - np.linalg.norm(mid1 - pos[-1]))
        lens = np.array([c['lens'] for c in ci])
        if not (inb and 60 <= ang <= 120 and dolly >= 0.05 and np.ptp(lens) < 0.01): prob.append('S6')
        det.append(f'S6 heads in frame={inb} axis angle {ang:.0f}° dolly {dolly*100:.1f}cm lens_range {np.ptp(lens):.3f}')
        return P(not prob, ('failed: ' + ','.join(prob) + ' | ' if prob else '') + '; '.join(det))
    item('M10', m10)

    def g03():
        wpl, wpr, bcc, bp = evreq('w_place', 'w_press', 'b_capture_contact', 'b_press')
        d = need(); has(d, 'W_KNIGHT', 'B_ROOK', 'CLOCK_BUTTON_W', 'CLOCK_BUTTON_B', RIGS['W'], RIGS['B'])
        rook = [centroid_w(d, 'B_ROOK', f) for f in range(bcc, bp + 1)]
        b_place = next((bcc + i for i in range(1, len(rook)) if np.linalg.norm(rook[i] - rook[i - 1]) < 0.0005), bp)
        prob, det = [], []
        for col, place, press, piece, own, other in (('W', wpl, wpr, 'W_KNIGHT', 'CLOCK_BUTTON_W', 'CLOCK_BUTTON_B'),
                                                     ('B', b_place, bp, 'B_ROOK', 'CLOCK_BUTTON_B', 'CLOCK_BUTTON_W')):
            rig = RIGS[col]
            d1, s1 = hand_side_near(d, rig, place, pts_w(d, piece, place))
            d2, s2 = hand_side_near(d, rig, press, pts_w(d, own, press))
            d3, _ = hand_side_near(d, rig, press, pts_w(d, other, press))
            ok = s1 is not None and s1 == s2 and d2 <= 0.05 and d2 <= d3
            if not ok: prob.append(f'{col}: moved with {s1} hand ({d1*100:.1f} cm) at frame {place}, pressed with {s2} hand ({d2*100:.1f} cm to own button, {d3*100:.1f} cm to the other) at {press}')
            det.append(f'{col} place@{place} {s1} / press@{press} {s2} {d2*100:.1f}cm')
        return P(not prob, '; '.join(prob + det))
    item('G03', g03)

    def g04():
        wg, = evreq('w_glance')
        d = need(); has(d, RIGS['W'], RIGS['B'], 'CAM_S1', 'CAM_S2', 'CAM_S4', 'CAM_S6')
        prob, det = [], []
        signs = {}
        for s in ('S1', 'S2', 'S4', 'S6'):
            cam = f'CAM_{s}'
            vals = []
            for f in range(SH[s][0], SH[s][1] + 1, 5):
                hw, hb = head_pt(d, RIGS['W'], f)[0], head_pt(d, RIGS['B'], f)[0]
                a = (hb - hw)[:2]; c = (mw(d, cam, f)[:3, 3] - hw)[:2]
                vals.append(np.sign(a[0] * c[1] - a[1] * c[0]))
            signs[s] = set(vals)
        allv = set().union(*signs.values())
        if len(allv - {0}) != 1: prob.append(f'cameras on both sides of the players\' axis {dict((k, sorted(v)) for k, v in signs.items())}')
        f2, f4 = (SH['S2'][0] + SH['S2'][1]) // 2, (SH['S4'][0] + SH['S4'][1]) // 2
        u = lambda cam, f, p: B.project(d, cam, f, p[None])[0][0]
        g2 = np.sign(u('CAM_S2', f2, head_pt(d, RIGS['B'], f2)[0]) - u('CAM_S2', f2, head_pt(d, RIGS['W'], f2)[0]))
        g4 = np.sign(u('CAM_S4', f4, head_pt(d, RIGS['W'], f4)[0]) - u('CAM_S4', f4, head_pt(d, RIGS['B'], f4)[0]))
        if g2 == g4 or g2 == 0: prob.append(f'eyeline screen directions not opposite (S2 {g2:+.0f}, S4 {g4:+.0f})')
        # head forward: the head bone's local axis (+-X or +-Z, world rotation from the dump) whose horizontal projection
        # points most toward Black's head at frame 0 (players face each other); the same local axis is read at w_glance
        hb_name = head_pt(d, RIGS['W'], 0)[1]
        bm = d.get('bmat', {}).get(RIGS['W'], {})
        if hb_name is None or hb_name not in bm.get(0, {}) or hb_name not in bm.get(wg, {}):
            prob.append('no head bone rotation on PLAYER_W_RIG')
        else:
            def axes(f):
                M3 = B.rot_of(np.array(bm[f][hb_name], float))
                return {'+x': M3[:, 0], '-x': -M3[:, 0], '+z': M3[:, 2], '-z': -M3[:, 2]}
            tgt0 = head_pt(d, RIGS['B'], 0)[0] - head_pt(d, RIGS['W'], 0)[0]
            ax0 = axes(0)
            key = max(ax0, key=lambda k: np.dot(ax0[k][:2], tgt0[:2]) / ((np.linalg.norm(ax0[k][:2]) * np.linalg.norm(tgt0[:2])) or 1))
            fwd = axes(wg)[key]
            tg = head_pt(d, RIGS['B'], wg)[0] - head_pt(d, RIGS['W'], wg)[0]
            ang = math.degrees(math.acos(np.clip(np.dot(fwd, tg) / np.linalg.norm(tg), -1, 1)))
            det.append(f'White head forward vs direction to Black at w_glance: {ang:.0f}° (axis {key} of {hb_name})')
            if ang > 25: prob.append(f'White not looking at Black at w_glance ({ang:.0f}° > 25°)')
        det.append(f'camera sides {dict((k, sorted(v)) for k, v in signs.items())}; eyeline S2 {g2:+.0f} / S4 {g4:+.0f}')
        return P(not prob, '; '.join(prob + det))
    item('G04', g04)

    def tilt(d, n, f, board='BOARD'):
        return math.degrees(math.acos(np.clip(np.dot(B.rot_of(mw(d, n, f))[:, 2], B.rot_of(mw(d, board, f))[:, 2]), -1, 1)))

    def rigid_ok(d, n):
        e = [x for x in d['physics'].get(n, []) if x.get('type') == 'RIGID_BODY']
        w = d.get('rigidbody_world') or {}
        cache = (w.get('cache') or {})
        in_world = n in (w.get('objects') or [])
        baked = bool(cache.get('is_baked')) or (bool(cache.get('use_disk_cache')) and any(proj.rglob('blendcache_*/*')))
        ok = bool(e) and e[0].get('rb_type') == 'ACTIVE' and e[0].get('enabled', True) and in_world and baked
        return ok, f'{n}: rigid body {e[0].get("rb_type") if e else None}, in world={in_world}, cache baked/shipped={baked}'

    def g06():
        bcc, kr = evreq('b_capture_contact', 'knight_rest')
        d = need(); has(d, 'W_KNIGHT', 'BOARD', 'CAM_S4')
        prob = []
        ok, dr = rigid_ok(d, 'W_KNIGHT')
        if not ok: prob.append(dr)
        s, _, _ = fit_square(d, 'BOARD', '', 0, SQ)
        t = tilt(d, 'W_KNIGHT', min(899, kr + 3))
        if t <= 60: prob.append(f'knight tilt {t:.0f}° at knight_rest+3 (need >60)')
        nm, _, z = which(d, 'BOARD', 'W_KNIGHT', min(899, kr + 3), s)
        xy, _ = local_xy(d, 'BOARD', 'W_KNIGHT', min(899, kr + 3))
        if nm != 'off': prob.append(f'knight rests on {nm} (must be off the 64 squares)')
        if not (-0.1 <= z <= 0.08 and np.abs(xy).max() <= 0.8): prob.append(f'knight not resting on the table near the board (board-local z {z:.3f} m, xy {np.round(xy, 2).tolist()})')
        cen = {f: centroid_w(d, 'W_KNIGHT', f) for f in range(bcc, min(899, kr + 14) + 1)}
        jumps = [float(np.linalg.norm(cen[f] - cen[f - 1])) for f in range(bcc + 1, min(899, kr + 14) + 1)]
        if jumps and max(jumps) > 0.03: prob.append(f'single-frame jump {max(jumps)*100:.1f} cm')
        rest = None
        for f0 in range(kr - 3, kr + 4):
            sp = [float(np.linalg.norm(cen.get(f + 1, cen[f]) - cen[f])) for f in range(f0, f0 + 10) if f in cen]
            if len(sp) == 10 and max(sp) < 0.001:
                rest = f0; break
        if rest is None: prob.append('knight not at rest (<1 mm/frame for 10 frames) starting within knight_rest±3')
        fv = min(SH['S4'][1], kr + 5)
        uvz = B.project(d, 'CAM_S4', fv, cen.get(fv, centroid_w(d, 'W_KNIGHT', fv))[None])[0]
        if not (uvz[2] > 0 and 0 <= uvz[0] <= 1 and 0 <= uvz[1] <= 1): prob.append(f'resting knight outside CAM_S4 frame at {fv}')
        return P(not prob, '; '.join(prob) if prob else f'{dr}; tilt {t:.0f}°, off-board rest from {rest}, max jump {max(jumps)*100:.1f} cm, visible in S4')
    item('G06', g06)

    def g07():
        kt, = evreq('king_tip')
        d = need(); has(d, 'W_KING', 'BOARD', RIGS['W'], 'CAM_S6')
        prob = []
        ok, dr = rigid_ok(d, 'W_KING')
        if not ok: prob.append(dr)
        dmin = min(hand_side_near(d, RIGS['W'], f, pts_w(d, 'W_KING', f))[0] for f in range(max(0, kt - 3), min(899, kt + 3) + 1))
        if dmin > 0.03: prob.append(f'White hand/finger bone {dmin*100:.1f} cm from W_KING around king_tip (need <=3)')
        fe = min(899, kt + 60)
        t = max(tilt(d, 'W_KING', f) for f in range(kt, fe + 1))
        if t <= 60: prob.append(f'king tilt max {t:.0f}° after king_tip (need >60)')
        s, _, _ = fit_square(d, 'BOARD', '', 0, SQ)
        xy, z = local_xy(d, 'BOARD', 'W_KING', 899)
        cen = [centroid_w(d, 'W_KING', f) for f in (897, 898, 899)]
        still = max(np.linalg.norm(cen[1] - cen[0]), np.linalg.norm(cen[2] - cen[1])) < 0.001
        if not (np.abs(xy).max() <= 4 * s + 0.02 and -0.02 <= z <= 0.06 and still): prob.append(f'king not resting on the board at the end (xy {np.round(xy, 3).tolist()}, z {z:.3f}, still={still})')
        uvz = B.project(d, 'CAM_S6', fe, centroid_w(d, 'W_KING', fe)[None])[0]
        if not (uvz[2] > 0 and 0 <= uvz[0] <= 1 and 0 <= uvz[1] <= 1): prob.append('fallen king outside the CAM_S6 frame')
        return P(not prob, '; '.join(prob) if prob else f'{dr}; finger {dmin*100:.1f} cm at king_tip; tilt {t:.0f}°; rests on the board; visible in S6')
    item('G07', g07)

    def finger_count(d, rig):
        arm = d['armatures'].get(rig)
        if not arm:
            return {}, {}, {}
        bones, keyed = arm['bones'], set(arm['keyed'])
        fc = {}
        for e in d['fcurves'].get(rig, []):
            m = re.match(r'pose\.bones\["(.+?)"\]', e['path'])
            if m and e.get('n', 0) >= 2:
                fc.setdefault(m.group(1), []).append((e['path'].split('.')[-1], e['index'], tuple(e['frames'][:60]), tuple(e['values'][:60])))
        groups = B.finger_groups(bones)
        res, sig, struct = {}, {}, {}
        for side in ('L', 'R'):
            names = {k: v for k, v in groups[side].items() if sum(1 for b in v if b in keyed) >= 3}
            struct[side] = sum(1 for v in groups[side].values() if len(v) >= 3)
            topo = 0
            for h in [b for b in bones if re.search(r'hand|palm', b, re.I) and B.side_of(b) == side]:
                for path in B.chains_under(bones, h):
                    if len(path) >= 3:
                        struct[side] = max(struct[side], 0)
                    if sum(1 for b in path if b in keyed) >= 3:
                        topo += 1
            res[side] = max(len(names), topo)
            sig[side] = len(set(tuple(sorted(sum((fc.get(b, []) for b in v if b in keyed), []))) for v in names.values()))
        return res, sig, struct

    def g08():
        d = need(); has(d, *RIGS.values(), *MESHES.values())
        prob, det = [], []
        for k in RIGS:
            rig, me = RIGS[k], MESHES[k]
            par = d['parents'].get(me, [None, None, None])
            driven = rig in d['armature_mods'].get(me, []) or (par[0] == rig and par[1] == 'ARMATURE')
            if not driven: prob.append(f'{me} not deformed by {rig}')
            cnt, sig, struct = finger_count(d, rig)
            act = max(('L', 'R'), key=lambda s: cnt.get(s, 0))
            if cnt.get(act, 0) < 4: prob.append(f'{rig}: keyed finger chains per hand {cnt} (need >=4 on the acting hand)')
            if sig.get(act, 0) < 2: prob.append(f'{rig}: fingers of the acting hand not individually animated ({sig})')
            if min(struct.get('L', 0), struct.get('R', 0)) < 4: prob.append(f'{rig}: finger chains (>=3 bones) per hand {struct} (need >=4 on both hands)')
            bb = np.array(d['bbox_world'].get(me, {}).get(0) or [[0, 0, 0]] * 8, float)
            ext = bb.max(0) - bb.min(0)
            if ext.min() < 0.1: prob.append(f'{me} mesh flat/too small {np.round(ext, 2).tolist()}')
            det.append(f'{k}: driven={driven} keyed chains={cnt} distinct={sig} chains={struct}')
        return P(not prob, '; '.join(prob + det))
    item('G08', g08)

    def g09():
        d = need(); has(d, RIGS['B'], RIGS['A'])
        x = A('base', 'speech')
        hop = L.SR // 30
        nf = len(x) // hop
        env = np.sqrt((x[:nf * hop].astype(np.float64).reshape(nf, hop) ** 2).mean(1))
        det, ok = [], True
        for k, (a, b) in (('B', SH['S4']), ('A', SH['S6'])):
            rig, me = RIGS[k], MESHES[k]
            chans = {}
            for f in range(a, b + 1):
                for bn, (ang, loc) in d['chan'].get(rig, {}).get(f, {}).items():
                    chans.setdefault(f'bone:{bn}:rot', []).append(ang)
                    chans.setdefault(f'bone:{bn}:loc', []).append(loc)
            for o, per in d['sk'].items():
                if o.upper().startswith(me) or rig in d['armature_mods'].get(o, []):
                    for f in range(a, b + 1):
                        for kk, v in per.get(f, {}).items():
                            chans.setdefault(f'sk:{o}:{kk}', []).append(v)
            e = env[a:b + 1]
            best = (-2.0, None, None)
            for nm, s in chans.items():
                s = np.array(s, float)
                if len(s) != len(e) or np.ptp(s) < 1e-6:
                    continue
                for lag in range(-2, 3):
                    u, v = (s[lag:], e[:len(e) - lag]) if lag >= 0 else (s[:lag], e[-lag:])
                    if np.std(u) < 1e-9 or np.std(v) < 1e-12:
                        continue
                    r = float(np.corrcoef(u, v)[0, 1])
                    if r > best[0]:
                        best = (r, nm, lag)
            ok &= best[0] >= 0.4
            det.append(f'{me} frames {a}-{b}: best r={best[0]:.2f} channel={best[1]} lag={best[2]} ({len(chans)} mouth channels)')
        return P(ok, '; '.join(det))
    item('G09', g09)

    def g12():
        dme, = evreq('demo_move_end')
        wp, bp, ff = evreq('w_press', 'b_press', 'flag_fall')
        prob, det = [], []
        if dme > 368: prob.append(f'demo_move_end={dme} > 368')
        d = need(15); has(d, 'CLOCK', 'CLOCK_HAND_W', 'CLOCK_HAND_B', 'FLAG_W', 'FLAG_B', 'DEMO_BOARD', 'DEMO_W_KNIGHT')
        sh = lambda e: e if e < 375 else e - 15
        ok, dd = clock_logic(d, sh(wp), sh(bp), sh(ff), 885)
        if not ok: prob.append('revision clock logic: ' + '; '.join(dd))
        p2, d2 = flag_logic(d, sh(ff), 884, SH_REV['S5'], None)
        if p2: prob.append('revision flag: ' + '; '.join(p2))
        s, _, _ = fit_square(d, 'DEMO_BOARD', 'DEMO_', 0, SQ_DEMO)
        on_f5 = [f for f in range(min(dme + 1, 374), 375) if which(d, 'DEMO_BOARD', 'DEMO_W_KNIGHT', f, s)[0] == 'f5']
        if len(on_f5) < 6: prob.append(f'revision: DEMO_W_KNIGHT on f5 in only {len(on_f5)} frames of the trimmed S3 (need >=6)')
        det.append(f'revision dump (revision_trim_frames=15): clock/flag logic ok={ok and not p2}, demo knight on f5 {len(on_f5)} frames')
        return P(not prob, '; '.join(prob + det))
    item('G12', g12)

    def g05():
        d = need(); has(d, 'BOARD', 'DEMO_BOARD', RIGS['W'])
        if time.time() - t_start > BUDGET_S:
            return F('grader time budget exhausted before the board top-view render')
        sB, _, _ = fit_square(d, 'BOARD', '', 0, SQ)
        sD, _, _ = fit_square(d, 'DEMO_BOARD', 'DEMO_', 0, SQ_DEMO)
        zs = np.mean([local_xy(d, 'DEMO_BOARD', 'DEMO_' + p, 0)[1] for p in PIECES])
        specs = [{'board': 'BOARD', 'sq': sB, 'side': 1}, {'board': 'DEMO_BOARD', 'sq': sD, 'side': 1 if zs >= 0 else -1}]
        sp = pathlib.Path(tmp) / 'cdc_board_render.py'
        sp.write_text(BOARD_RENDER_PY)
        out = str(pathlib.Path(tmp) / 'cdc_board')
        try:
            L.run(['blender', '-b', '-y', str(blend), '--python', str(sp), '--', out, '0', json.dumps(specs)], 300)
        except Exception as e:
            return F(f'board top-view render failed: {type(e).__name__}')
        jp = pathlib.Path(out + '.json')
        if not jp.exists():
            return F('board top-view render failed (no output)')
        res = json.loads(jp.read_text())
        prob, det = [], []
        occupied = set(START.values())
        for bn in ('BOARD', 'DEMO_BOARD'):
            r = res.get(bn)
            if not r:
                prob.append(f'{bn}: no render'); continue
            light, dark = [], []
            for sqn, (u, v, val) in r['px'].items():
                if sqn in occupied or val is None:
                    continue
                i, j = 'abcdefgh'.index(sqn[0]), int(sqn[1]) - 1
                (light if (i + j) % 2 == 1 else dark).append(val)
            if len(light) < 10 or len(dark) < 10:
                prob.append(f'{bn}: squares not visible in the top view'); continue
            ml, md = float(np.median(light)), float(np.median(dark))
            det.append(f'{bn}: h1-colour squares {ml:.4g} vs a1-colour {md:.4g} (linear)')
            if ml < 1.15 * md: prob.append(f'{bn}: h1 is not a light square (median linear luminance {ml:.4g} vs {md:.4g})')
        hw = head_pt(d, RIGS['W'], 0)[0]
        mb = mw(d, 'BOARD', 0)
        yW = float((np.linalg.inv(mb) @ np.append(hw, 1))[1])
        if yW >= 0: prob.append(f'White sits on the BOARD local +Y side (head y={yW:.2f})')
        return P(not prob, '; '.join(prob + det))
    item('G05', g05)

    def g10():
        prob = []
        if not bmp.exists():
            return F('base/output.mp4 missing')
        g = L.gray_frames(bmp, 1280, 720, every=15)
        idx = {s: [] for s in SH}
        for k, fr in enumerate(g):
            for s, (a, b) in SH.items():
                if a <= k * 15 <= b:
                    idx[s].append(L.flat_block_index(fr))
        med = {s: round(float(np.median(v)), 3) for s, v in idx.items() if v}
        STATE['flat_index'] = med
        bad = {s: v for s, v in med.items() if v > 0.35}
        if len(bad) >= 4: prob.append(f'flat-block index > 0.35 in {len(bad)} of 6 shots {bad}')
        d = get_dump()
        if d.get('ok'):
            hero = ['BOARD', 'W_KNIGHT', 'B_ROOK', 'W_KING', 'PLAYER_W', 'PLAYER_B', 'ARBITER']
            nob = [h for h in hero if h in d['objects'] and not any(any(t.startswith('BSDF') or t == 'GROUP' for t in m.get('node_types', [])) for m in d['materials'].get(h, []))]
            if nob: prob.append(f'hero objects without a node-based BSDF material: {nob}')
            var = [h for h in hero if any(m.get('n_tex', 0) > 0 or m.get('principled_linked') for m in d['materials'].get(h, []))]
            if len(var) < 3: prob.append(f'surface variation (texture or linked BSDF input) on only {var} (need >=3 hero objects)')
            soft = [n for n, l in d['lights'].items() if l['type'] == 'AREA' or l['size'] > 0.02 or l['radius'] > 0.02 or (l['type'] == 'SUN' and l['angle'] > 0.005)]
            if not soft and not any(t in d.get('world_nodes', []) for t in ('TEX_ENVIRONMENT', 'TEX_SKY')):
                prob.append('no soft light source (area/sized light or environment/sky world)')
            if d.get('engine') == 'CYCLES' and d['render'].get('oidn_available', True) and not (d['render'].get('cycles_denoise') or d['render'].get('compositor_denoise')):
                prob.append('Cycles render without denoising')
        else:
            if not prob:
                STATE['g10_nogate'] = True
            prob.append('Blender inspection failed: ' + str(d.get('error'))[-200:])
        return F('; '.join(prob)) if prob else None       # measured parts pass -> look/Staunton pieces judged visually
    item('G10', g10)

    def offset():
        d = get_dump()
        return int(d.get('frame_offset', 0) or 0) if d.get('ok') else 0

    def m12():
        if not blend.exists():
            return F('project/scene.blend missing')
        if not bmp.exists():
            return F('base/output.mp4 missing')
        det, ok = [], True
        for f, cam in ((60, 'CAM_S1'), (200, 'CAM_S2'), (330, 'CAM_S3'), (480, 'CAM_S4'), (650, 'CAM_S5'), (820, 'CAM_S6')):
            if time.time() - t_start > BUDGET_S:
                return F('; '.join(det + [f'grader time budget exhausted before frame {f}']))
            rr, note = L.blend_render(blend, offset() + f, tmp, 0, cam)
            if rr is None:
                return F('; '.join(det + [f'frame {f} re-render failed ({note})']))
            s = L.ssim_render(rr, L.frame_at(bmp, f, L.RENDER_W, L.RENDER_H)); ok &= s >= 0.75
            det.append(f'f{f} SSIM={s:.3f}{" " + note if note else ""}')
        return P(ok, '; '.join(det) + f' ({L.RENDER_W}x{L.RENDER_H}, {L.RENDER_SPP} spp re-render)')
    item('M12', m12)

    STATE['seconds'] = round(time.time() - t_start, 1)
    R['_x02_state'] = {'verdict': 'na', 'detail': json.dumps({k: STATE.get(k) for k in ('flat_index', 'dump_seconds', 'dump_warnings', 'seconds')})[:900]}
    return R


def postprocess(res, ctx):
    """Group gate: a failed critical item zeroes its whole group (not when the failure is a grader-side Blender
    inspection failure, nor G10 failing only because the inspection failed)."""
    items = ctx['items']
    for it in items:
        r0 = res.get(it['id'], {})
        if it.get('critical') and r0.get('verdict') == 'fail' and not r0.get('nogate') and not (it['id'] == 'G10' and STATE.get('g10_nogate')):
            for o in items:
                if o['group'] == it['group'] and o['id'] != it['id']:
                    r = res.get(o['id'], {})
                    if r.get('verdict') not in ('fail', 'na'):
                        res[o['id']] = dict(r, verdict='fail', gated=True,
                                            detail=f"[group gate: critical {it['id']} failed] " + str(r.get('detail', r.get('reason', '')))[:300])
    return res
