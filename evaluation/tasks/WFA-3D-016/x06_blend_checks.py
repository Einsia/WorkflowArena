# -*- coding: utf-8 -*-
"""CDC-C-X06: numpy analysis of the per-frame Blender export written by x06_blend_dump.py.
Each item function returns (verdict, detail) and never raises on submission content (callers also guard)."""
import math
import numpy as np

FPS = 30.0
SHOTS = {'S1': (0, 149), 'S2': (150, 269), 'S3': (270, 449), 'S4': (450, 539), 'S5': (540, 659), 'S6': (660, 899)}
PITCH = 0.0127
RP_RING = PITCH / (2 * math.sin(math.pi / 44))   # 88.99 mm
RP_COG = PITCH / (2 * math.sin(math.pi / 16))    # 32.55 mm
WHEEL_R = 0.34
RATIO = 44 / 16
TOL_FRAC = 0.9   # share of sampled frames that must satisfy a per-frame tolerance


def fam(name, base):
    return name == base or name.startswith(base + '.')


class Dump:
    def __init__(self, d):
        self.d = d
        self.us = float(d.get('unit_scale') or 1.0)
        self.F = {int(k): v for k, v in (d.get('frames') or {}).items()}
        self.objects = d.get('objects') or {}

    def frames(self, a, b, key=None):
        return [f for f in sorted(self.F) if a <= f <= b and (key is None or key in self.F[f])]

    def M(self, f, name):
        e = self.F.get(f, {}).get('obj', {}).get(name)
        if not e:
            return None
        m = np.array(e['m'], float).reshape(4, 4)
        m[:3, 3] *= self.us
        return m

    def obj(self, f, name):
        return self.F.get(f, {}).get('obj', {}).get(name)

    def pos(self, f, name):
        m = self.M(f, name)
        return None if m is None else m[:3, 3]

    def members(self, base):
        names = set()
        for F in self.F.values():
            names.update(n for n in F.get('obj', {}) if fam(n, base))
        return sorted(names)

    def mover(self, base, a, b):
        """family member with the largest displacement in [a, b] (exact name on ties / no motion)."""
        best, bd = (base if base in self.members(base) else None), -1.0
        fr = self.frames(a, b)
        for n in self.members(base):
            ps = [self.pos(f, n) for f in fr]
            ps = [p for p in ps if p is not None]
            if len(ps) < 2:
                continue
            dd = float(np.linalg.norm(ps[-1] - ps[0]))
            if dd > bd + 1e-6 or (abs(dd - bd) <= 1e-6 and n == base):
                best, bd = n, dd
        return best

    def links(self, f):
        L = self.F.get(f, {}).get('links')
        if not L:
            return {}
        return {k: np.array(v, float) * self.us for k, v in L.items()}

    def bone(self, f, rig, bn):
        return self.F.get(f, {}).get('bones', {}).get(rig, {}).get(bn)

    def cam(self, f, shot):
        return self.F.get(f, {}).get('cam', {}).get(shot)


def rot(m):
    R = m[:3, :3].copy()
    for i in range(3):
        n = np.linalg.norm(R[:, i])
        if n > 1e-12:
            R[:, i] /= n
    return R


def delta_angle(R1, R2):
    Rd = R2 @ R1.T
    c = np.clip((np.trace(Rd) - 1) / 2, -1, 1)
    th = math.acos(c)
    ax = np.array([Rd[2, 1] - Rd[1, 2], Rd[0, 2] - Rd[2, 0], Rd[1, 0] - Rd[0, 1]])
    n = np.linalg.norm(ax)
    return th, (ax / n if n > 1e-12 else np.zeros(3))


def omega(D, name, parent, ring, a, b, maxgap=2):
    """signed angular speed (rad/s) of `name` relative to `parent`, sign = along the axle of `ring` (common reference).
    returns {f1: w} for consecutive samples f1<f2 (f2-f1<=maxgap) inside [a, b]."""
    out = {}
    fr = D.frames(a, b)
    for f1, f2 in zip(fr, fr[1:]):
        if f2 - f1 > maxgap:
            continue
        m1, m2, p1, p2 = D.M(f1, name), D.M(f2, name), D.M(f1, parent), D.M(f2, parent)
        r1 = D.obj(f1, ring)
        if any(x is None for x in (m1, m2, p1, p2)) or not r1 or 'ax' not in r1:
            continue
        P1, P2 = rot(p1), rot(p2)
        th, ax = delta_angle(P1.T @ rot(m1), P2.T @ rot(m2))
        ref = P1.T @ np.array(r1['ax'], float)
        s = 1.0 if float(ax @ ref) >= 0 else -1.0
        out[f1] = s * th / ((f2 - f1) / FPS)
    return out


def frac_ok(vals, pred):
    vals = list(vals)
    return (sum(1 for v in vals if pred(v)) / len(vals)) if vals else 0.0


def engaged(D, f, disc, rp, links=None):
    """links whose pin centre is within 6 mm of the disc pitch circle (radially) and 8 mm of its plane."""
    o = D.obj(f, disc)
    if not o or 'ax' not in o:
        return None
    c = np.array(o.get('c') or D.pos(f, disc), float) * (D.us if 'c' in o else 1.0)
    a = np.array(o['ax'], float)
    L = links if links is not None else D.links(f)
    res = []
    for k, p in L.items():
        v = p - c
        ax = float(v @ a)
        rad = float(np.linalg.norm(v - ax * a))
        if abs(ax) <= 0.008 and abs(rad - rp) <= 0.006:
            res.append(rad - rp)
    return res


# ---------------------------------------------------------------- camera (M02)
def cam_series(D, shot):
    a, b = SHOTS[shot]
    out = []
    for f in D.frames(a, b):
        c = D.cam(f, shot)
        if c:
            m = np.array(c['m'], float).reshape(4, 4)
            m[:3, 3] *= D.us
            out.append((f, m, c))
    return out


def m02(D):
    bad, det = [], []
    S = {k: cam_series(D, k) for k in SHOTS}
    for k, s in S.items():
        if len(s) < 3:
            return 'fail', f'CAM_{k}: no per-frame camera data ({len(s)} samples)'

    def fwd(m):
        return -rot(m)[:, 2]

    def pitch(m):
        return math.degrees(math.asin(np.clip(fwd(m)[2], -1, 1)))

    def locked(s):
        P = np.array([m[:3, 3] for _, m, _ in s]); Ls = [c.get('lens', 0) for _, _, c in s]
        ang = max(math.degrees(delta_angle(rot(s[0][1]), rot(m))[0]) for _, m, _ in s)
        return float(np.max(np.linalg.norm(P - P[0], axis=1))), max(Ls) - min(Ls), ang

    # S1
    s = S['S1']; dp, dl, da = locked(s); z = float(np.mean([m[2, 3] for _, m, _ in s])); pt = float(np.mean([pitch(m) for _, m, _ in s]))
    det.append(f'S1 z={z:.2f} pitch={pt:.1f} move={dp*100:.1f}cm lensΔ={dl:.2f} rotΔ={da:.2f}°')
    if not (1.2 <= z <= 1.9): bad.append(f'S1 height {z:.2f} m not in 1.2-1.9')
    if abs(pt) > 8: bad.append(f'S1 pitch {pt:.1f}°')
    if dp >= 0.01 or dl > 0.01 or da > 0.5: bad.append('S1 not locked-off')
    # S2 handheld, low angle, no zoom
    s = S['S2']; P = np.array([m[:3, 3] for _, m, _ in s]); fr = np.array([f for f, _, _ in s], float)
    pt = float(np.mean([pitch(m) for _, m, _ in s]))
    sm = np.array([P[np.abs(fr - f) <= 7].mean(axis=0) for f in fr])
    shake = float(np.max(np.linalg.norm(P - sm, axis=1))) * 1000
    dl = max(c.get('lens', 0) for _, _, c in s) - min(c.get('lens', 0) for _, _, c in s)
    det.append(f'S2 pitch={pt:.1f}° shake={shake:.1f}mm lensΔ={dl:.2f}')
    if pt < 3: bad.append(f'S2 not low angle (pitch {pt:.1f}° < 3°)')
    if not (2 <= shake <= 60): bad.append(f'S2 handheld shake {shake:.1f} mm not in 2-60')
    if dl > 0.01: bad.append('S2 zooms')
    # S3 locked macro shallow DOF
    s = S['S3']; dp, dl, da = locked(s); c0 = s[0][2]
    det.append(f'S3 move={dp*100:.1f}cm lens={c0.get("lens")} focus={c0.get("focus")} dof={c0.get("dof")} f/{c0.get("fstop")}')
    if dp >= 0.01 or dl > 0.01 or da > 0.5: bad.append('S3 not locked-off')
    if not (c0.get('lens', 0) >= 50 or (c0.get('focus') or 99) * D.us <= 0.6): bad.append('S3 not macro (lens<50 and focus>0.6 m)')
    if not all(c.get('dof') and (c.get('fstop') or 99) <= 4 for _, _, c in s): bad.append('S3 DOF off or f>4')
    # S4 dolly-in towards the courier
    s = S['S4']; cour = 'COURIER'
    d0 = d1 = None
    p0, p1 = D.pos(s[0][0], cour), D.pos(s[-1][0], cour)
    if p0 is not None and p1 is not None:
        d0 = float(np.linalg.norm(s[0][1][:3, 3] - p0)); d1 = float(np.linalg.norm(s[-1][1][:3, 3] - p1))
    dl = max(c.get('lens', 0) for _, _, c in s) - min(c.get('lens', 0) for _, _, c in s)
    det.append(f'S4 dist {d0} -> {d1} lensΔ={dl:.2f}')
    if d0 is None or d0 - d1 < 0.08: bad.append('S4 no dolly-in >=0.08 m towards COURIER')
    if dl > 0.01: bad.append('S4 lens changes')
    if not all(c.get('dof') for _, _, c in s): bad.append('S4 DOF off')
    # S5 locked, chainring centred
    s = S['S5']; dp, dl, da = locked(s)
    pr = [c.get('proj', {}).get('CHAINRING') for _, _, c in s]
    pr = [p for p in pr if p]
    det.append(f'S5 move={dp*100:.1f}cm chainring proj {pr[0] if pr else None}')
    if dp >= 0.01 or dl > 0.01 or da > 0.5: bad.append('S5 not locked-off')
    if not pr or not all(0.3 <= p[0] <= 0.7 and 0.3 <= p[1] <= 0.7 and p[2] > 0 for p in pr): bad.append('S5 CHAINRING centre outside the central 40%')
    # S6 tracking + pull back
    s = S['S6']; P = np.array([m[:3, 3] for _, m, _ in s])
    travel = float(np.linalg.norm(P[-1] - P[0]))
    q0, q1 = D.pos(s[0][0], 'COURIER'), D.pos(s[-1][0], 'COURIER')
    rd = None
    if q0 is not None and q1 is not None:
        rd = float(np.linalg.norm(P[-1] - q1)) / max(float(np.linalg.norm(P[0] - q0)), 1e-6)
    lr = (s[0][2].get('lens') or 1) / max(s[-1][2].get('lens') or 1, 1e-6)
    det.append(f'S6 travel={travel:.2f} m dist ratio={rd} lens ratio={lr:.2f}')
    if travel < 3: bad.append(f'S6 camera travel {travel:.2f} m < 3')
    if not ((rd or 0) >= 1.5 or lr >= 1.5): bad.append('S6 no pull-back (distance x1.5 or focal length /1.5)')
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


# ---------------------------------------------------------------- rigs (M05)
def children_map(D):
    ch = {}
    for n, e in D.objects.items():
        if e.get('parent'):
            ch.setdefault(e['parent'], []).append(n)
    return ch


def descendants(D, name, ch=None):
    ch = ch or children_map(D)
    out, st = [], [name]
    while st:
        x = st.pop()
        for c in ch.get(x, []):
            out.append(c); st.append(c)
    return out


def m05(D):
    bad, det = [], []
    ch = children_map(D)
    for person, rig in (('MECHANIC', 'MECHANIC_RIG'), ('COURIER', 'COURIER_RIG')):
        if D.objects.get(rig, {}).get('type') != 'ARMATURE':
            bad.append(f'{rig} missing or not an armature'); continue
        cands = [n for n, e in D.objects.items() if e.get('type') == 'MESH' and e.get('in_scene') and
                 (fam(n, person) or n in descendants(D, person, ch) or n in descendants(D, rig, ch))]
        drv = [n for n in cands if any(m[0] == 'ARMATURE' and m[1] == rig for m in D.objects[n].get('mods', []))]
        if not drv: bad.append(f'no {person} mesh with an Armature modifier -> {rig}')
        det.append(f'{rig} drives {drv[:4]}')
    ri = (D.d.get('rigs') or {}).get('MECHANIC_RIG')
    if not ri:
        return 'fail', '; '.join(bad + ['MECHANIC_RIG bone data missing'])
    curves_fr = [f for s in ('S1', 'S3', 'S5') for f in D.frames(*SHOTS[s])]
    nv = sum((D.d.get('finger_vcount') or {}).values())
    nbones = sum(len(c['bones']) for c in ri['chains'])
    det.append(f'finger-weighted vertices {nv} for {nbones} finger bones')
    if nbones == 0 or nv < 4 * nbones: bad.append('fingers are not modelled geometry weighted to the finger bones (image-plane hands?)')
    for side in ('L', 'R'):
        chains = [c for c in ri['chains'] if c['side'] == side and len(c['bones']) >= 2]
        if len(chains) < 4:
            bad.append(f'hand {side}: {len(chains)} finger chains with >=2 bones (<4)'); continue
        curves = []
        for c in chains:
            v = []
            for f in curves_fr:
                angs = [D.bone(f, 'MECHANIC_RIG', b) for b in c['bones']]
                if all(a is not None for a in angs):
                    v.append(sum(a['ang'] for a in angs))
            curves.append(np.array(v))
        n = min(len(v) for v in curves)
        if n < 10:
            bad.append(f'hand {side}: too few samples'); continue
        C = np.stack([v[:n] for v in curves])
        rng = C.max(1) - C.min(1)
        with np.errstate(invalid='ignore', divide='ignore'):
            R = np.corrcoef(C)
        R = np.nan_to_num(R, nan=1.0)
        indep = [bool(np.any((np.abs(R[i]) < 0.95) & (np.arange(len(C)) != i))) for i in range(len(C))]
        det.append(f'hand {side}: {len(chains)} chains, rotation range {np.round(rng, 1).tolist()}°, independent {indep}')
        if (rng < 5).any(): bad.append(f'hand {side}: a finger chain rotates <5° over S1/S3/S5')
        if not all(indep): bad.append(f'hand {side}: a finger chain only copies the others (|r|>=0.95 with all)')
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


# ---------------------------------------------------------------- chain (M06)
def loop_ok(P, pitch):
    n = len(P)
    if n < 3:
        return False, 'too few'
    Dm = np.linalg.norm(P[:, None] - P[None], axis=2)
    A = (Dm <= 1.5 * pitch) & ~np.eye(n, dtype=bool)
    deg = A.sum(1)
    seen, st = {0}, [0]
    while st:
        i = st.pop()
        for j in np.nonzero(A[i])[0]:
            if j not in seen:
                seen.add(int(j)); st.append(int(j))
    return bool(deg.min() >= 2 and len(seen) == n), f'min degree {int(deg.min())}, component {len(seen)}/{n}'


def chain_nodes(D, f):
    L = D.links(f)
    P = list(L.values())
    q = D.pos(f, 'QUICK_LINK')
    if q is not None:
        P.append(q)
    return np.array(P) if P else np.zeros((0, 3))


def m06(D):
    fr = D.frames(540, 659, 'links')
    if not fr:
        return 'fail', 'no chain-link data in S5'
    f0 = fr[0]
    src = D.F[f0].get('link_src'); counts = D.F[f0].get('link_counts')
    P = chain_nodes(D, f0)
    n = len(P)
    bad = []
    if n - 1 < 100: bad.append(f'only {n - 1} discrete link objects/instances (+QUICK_LINK) (<100)')
    if abs(n - 106) > 2: bad.append(f'link count {n} (incl. QUICK_LINK) not 106±2')
    if n < 3:
        return 'fail', '; '.join(bad) + f' src={src} counts={counts}'
    Dm = np.linalg.norm(P[:, None] - P[None], axis=2) + np.eye(n) * 1e9
    pitch = float(np.median(Dm.min(1)))
    if abs(pitch - PITCH) > 0.05 * PITCH: bad.append(f'pitch {pitch*1000:.2f} mm not 12.7±5%')
    broken = []
    for f in fr:
        ok, why = loop_ok(chain_nodes(D, f), pitch)
        if not ok: broken.append((f, why))
    if broken: bad.append(f'loop open in {len(broken)} S5 frames, e.g. {broken[:2]}')
    return ('fail' if bad else 'pass'), '; '.join(bad) + f' | n={n} pitch={pitch*1000:.2f}mm src={src} {counts} frames={len(fr)}'


# ---------------------------------------------------------------- courier (M07)
def side_bone(ri, side):
    return (ri.get('wrist') or {}).get(side)


def m07(D, ev):
    ri = (D.d.get('rigs') or {}).get('COURIER_RIG')
    if not ri:
        return 'fail', 'COURIER_RIG bone data missing'
    bad, det = [], []
    wc, ct = ev.get('watch_check'), ev.get('courier_turn')
    for k, s in (('watch_check', 'S2'), ('courier_turn', 'S4')):
        a, b = SHOTS[s]
        if ev.get(k) is None or not (a + 6 <= ev[k] <= b - 6): bad.append(f'{k} not >=6 frames inside {s}')
    if bad:
        return 'fail', '; '.join(bad)
    wl, wr = side_bone(ri, 'L'), side_bone(ri, 'R')
    if not wl:
        return 'fail', 'no left wrist/hand bone on COURIER_RIG'

    def bh(f, bn):
        b = D.bone(f, 'COURIER_RIG', bn)
        return None if b is None else np.array(b['h'], float) * D.us
    win = [f for f in D.frames(wc - 6, wc + 6) if bh(f, wl) is not None]
    pre = [f for f in D.frames(150, wc) if bh(f, wl) is not None]
    if not win or not pre:
        return 'fail', 'no wrist samples around watch_check'
    rise = max(bh(f, wl)[2] for f in win) - min(bh(f, wl)[2] for f in pre)
    det.append(f'left wrist rise {rise:.3f} m')
    if rise < 0.15: bad.append(f'left wrist rises {rise:.3f} m < 0.15 within watch_check±6')
    wp = D.pos(wc, 'WATCH') if wc in D.F else None
    fw = min(D.F, key=lambda f: abs(f - wc))
    wp = D.pos(fw, 'WATCH')
    pj = (D.cam(fw, 'S2') or {}).get('proj', {}).get('WATCH')
    if wp is None: bad.append('WATCH missing')
    else:
        dl = float(np.linalg.norm(wp - bh(fw, wl)))
        dr = float(np.linalg.norm(wp - bh(fw, wr))) if wr and bh(fw, wr) is not None else 9.0
        det.append(f'WATCH-left wrist {dl:.3f} m, -right {dr:.3f} m, proj {pj}')
        if not (dl <= 0.12 and dl < dr): bad.append('WATCH not on the left wrist')
    if not pj or not (0 <= pj[0] <= 1 and 0 <= pj[1] <= 1 and pj[2] > 0): bad.append('WATCH not inside CAM_S2 frame at watch_check')
    hd = ri.get('head')
    if not hd:
        bad.append('no head bone')
    else:
        def heading(f):
            b = D.bone(f, 'COURIER_RIG', hd)
            if b is None: return None
            x = np.array(b['x'], float)
            return math.atan2(x[1], x[0])
        hs = [(f, heading(f)) for f in D.frames(ct - 6, ct + 6)]
        hs = [(f, h) for f, h in hs if h is not None]
        if len(hs) < 2:
            bad.append('no head samples around courier_turn')
        else:
            u = np.unwrap([h for _, h in hs])
            yaw = math.degrees(float(u.max() - u.min()))
            det.append(f'head yaw change {yaw:.1f}°')
            if yaw < 30: bad.append(f'head yaw {yaw:.1f}° < 30 within courier_turn±6')
            eyes = ri.get('eyes') or []
            if eyes:
                def facing(f):
                    h = D.bone(f, 'COURIER_RIG', hd); es = [D.bone(f, 'COURIER_RIG', e) for e in eyes]
                    if h is None or any(e is None for e in es): return None
                    v = np.mean([np.array(e['h'], float) for e in es], axis=0) - np.array(h['h'], float)
                    v[2] = 0
                    return v / max(np.linalg.norm(v), 1e-9), np.array(h['h'], float) * D.us
                f0, f1 = hs[0][0], hs[-1][0]
                a0, a1 = facing(f0), facing(f1)
                wpos = D.pos(f1, 'WINDOW')
                if a0 and a1 and wpos is not None:
                    tw = wpos - a1[1]; tw[2] = 0; tw /= max(np.linalg.norm(tw), 1e-9)
                    g0, g1 = math.degrees(math.acos(np.clip(a0[0] @ tw, -1, 1))), math.degrees(math.acos(np.clip(a1[0] @ tw, -1, 1)))
                    det.append(f'angle to WINDOW {g0:.0f}° -> {g1:.0f}° (eye bones)')
                    if g1 >= g0: bad.append('head does not turn towards the shop (WINDOW)')
            else:
                det.append('no eye bones: turn direction not checked')
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


# ---------------------------------------------------------------- world (M08)
def m08(D):
    bad, det = [], []
    fr = D.frames(0, 149, 's1_vis')
    if len(fr) < 5:
        return 'fail', f'no S1 visibility samples ({len(fr)})'
    share = sum(1 for f in fr if D.F[f]['s1_vis'][1]) / len(fr)
    det.append(f'COURIER visible through WINDOW in {share*100:.0f}% of {len(fr)} sampled S1 frames')
    if share < 0.6: bad.append('courier visible through WINDOW in <60% of S1 frames')
    ri = (D.d.get('rigs') or {}).get('COURIER_RIG') or {}
    hb = ri.get('hips')

    def root(f):
        b = D.bone(f, 'COURIER_RIG', hb) if hb else None
        return np.array(b['h'], float) * D.us if b else D.pos(f, 'COURIER_RIG')
    a = [f for f in D.frames(140, 149) if root(f) is not None]
    b = [f for f in D.frames(150, 159) if root(f) is not None]
    if not a or not b:
        bad.append('no COURIER_RIG samples at the S1/S2 boundary')
    else:
        dd = float(np.linalg.norm(root(a[-1]) - root(b[0])))
        det.append(f'courier root {hb} moves {dd:.2f} m from frame {a[-1]} to {b[0]}')
        if dd > 0.6: bad.append(f'courier jumps {dd:.2f} m between S1 and S2')
    miss = [n for n in ('COURIER', 'COURIER_RIG', 'MECHANIC', 'MECHANIC_RIG', 'WINDOW', 'BIKE', 'CAM_S1', 'CAM_S2')
            if not D.objects.get(n, {}).get('in_scene')]
    if miss: bad.append(f'not in the same scene as CAM_S1: {miss}')
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


# ---------------------------------------------------------------- foley helpers
def env(x, sr, win=0.005, hop=0.001):
    w, h = int(win * sr), int(hop * sr)
    n = max(0, (len(x) - w) // h + 1)
    if n == 0:
        return np.zeros(0), np.zeros(0)
    c = np.concatenate([[0.0], np.cumsum(x.astype(np.float64) ** 2)])
    idx = np.arange(n) * h
    e = 10 * np.log10(np.maximum((c[idx + w] - c[idx]) / w, 1e-14))
    return (idx + w / 2) / sr, e


def transient_at(foley, sr, t_c, tol, t_range):
    """loudest short transient near t_c (±tol s); compares with all other onsets in t_range.
    returns (ok, detail)."""
    t, e = env(foley, sr)
    if not len(e):
        return False, 'foley empty'

    sel = (t >= t_range[0]) & (t <= t_range[1])
    sub_t, sub_e = t[sel], e[sel]
    if len(sub_e) < 200:
        return False, 'foley too short for S3'
    win = (sub_t >= t_c - tol) & (sub_t <= t_c + tol + 0.03)
    if not win.any():
        return False, 'no samples at link_click'
    j = int(np.argmax(np.where(win, sub_e, -999)))
    pk = float(sub_e[j]); tp = float(sub_t[j])
    bg = float(np.percentile(sub_e[max(0, j - 150):max(1, j - 10)], 20))
    k0 = j
    while k0 > 0 and sub_e[k0 - 1] >= pk - 10: k0 -= 1
    k1 = j
    while k1 < len(sub_e) - 1 and sub_e[k1 + 1] >= pk - 10: k1 += 1
    dur = (k1 - k0) * 0.001 + 0.005
    det = f'click peak {pk:.1f} dBFS at {tp:.3f}s, rise {pk - bg:.1f} dB, duration {dur*1000:.0f} ms'
    if pk - bg < 12 or not (t_c - tol <= tp <= t_c + tol + 0.03):
        return False, 'no >=12 dB transient within link_click±2 frames; ' + det
    if dur >= 0.06:
        return False, 'link_click transient not short (>=60 ms); ' + det
    # other onsets in S3 (outside ±6 frames) must be >=1 dB weaker
    rivals = []
    for i in range(150, len(sub_e)):
        if abs(sub_t[i] - tp) <= 0.2:
            continue
        b2 = float(np.percentile(sub_e[max(0, i - 150):i - 10], 20))
        if sub_e[i] - b2 >= 12 and sub_e[i] >= sub_e[max(0, i - 3):i + 4].max() and sub_e[i] > pk - 1:
            rivals.append((round(float(sub_t[i]), 3), round(float(sub_e[i]), 1)))
    if rivals:
        return False, f'other S3 transients as strong as the click: {rivals[:4]}; ' + det
    return True, det


def tick_ratio(foley, sr, t0, t1, wheel_rps):
    """periodic-tick analysis of a window: returns (peak_corr, ticks_per_rev) or (None, None)."""
    seg = foley[int(t0 * sr):int(t1 * sr)]
    if len(seg) < int(0.2 * sr) or wheel_rps < 0.05:
        return None, None
    X = np.fft.rfft(seg)
    X[np.fft.rfftfreq(len(seg), 1 / sr) < 1000] = 0
    y = np.abs(np.fft.irfft(X, len(seg)))
    h = int(sr / 4000)
    k = np.ones(h * 4) / (h * 4)
    y = np.convolve(y, k, 'same')[::h]
    y = y - y.mean()
    if float(np.sqrt(np.mean(y ** 2))) < 1e-7:
        return 0.0, None
    fs = 4000.0
    ac = np.correlate(y, y, 'full')[len(y) - 1:]
    ac = ac / max(ac[0], 1e-20)
    lo = max(int(fs / (100 * wheel_rps)), 3)
    hi = min(int(fs / (10 * wheel_rps)), len(ac) // 2)
    if hi <= lo + 2:
        return None, None
    seg_ac = ac[lo:hi]
    peaks = [i for i in range(1, len(seg_ac) - 1) if seg_ac[i] >= seg_ac[i - 1] and seg_ac[i] >= seg_ac[i + 1]]
    if not peaks:
        return 0.0, None
    mx = max(seg_ac[i] for i in peaks)
    first = min(i for i in peaks if seg_ac[i] >= 0.85 * mx)
    lag = (lo + first) / fs
    return float(mx), (1 / lag) / wheel_rps


# ---------------------------------------------------------------- contact (G01, G02)
def tips(D, f):
    return D.F.get(f, {}).get('tips') or {}


def g01(D, ev, foley, sr):
    bad, det = [], []
    lj, lc = ev.get('link_join_start'), ev.get('link_click')
    if lj is None or lc is None:
        return 'fail', 'link events missing'
    if not (3 <= lc - lj <= 90): bad.append(f'link_click - link_join_start = {lc - lj} not in [3, 90]')
    T = tips(D, lc)
    if not T:
        return 'fail', '; '.join(bad + [f'no fingertip data at link_click {lc}'])
    for side in ('L', 'R'):
        ds = [min(v['d_ql'], v['d_adj']) * D.us for v in T.values() if v['side'] == side]
        dm = min(ds) if ds else 9
        det.append(f'{side} fingertip-QUICK_LINK {dm*100:.1f} cm')
        if dm > 0.025: bad.append(f'hand {side}: no fingertip within 2.5 cm of QUICK_LINK/adjacent links at link_click')
    # seating: distances between QUICK_LINK parts and the two adjacent links become constant
    fr = [f for f in D.frames(lj, 449, 'ql') if 'links' in D.F[f]]
    if len(fr) < 4:
        bad.append('no QUICK_LINK samples after link_join_start')
    else:
        fe = fr[-1]
        L = D.links(fe)
        Q = {n: np.array(m, float).reshape(4, 4)[:3, 3] * D.us for n, m in D.F[fe]['ql'].items()}
        if not L or not Q:
            bad.append('QUICK_LINK or links missing')
        else:
            qc = np.mean(list(Q.values()), axis=0)
            adj = sorted(L, key=lambda k: np.linalg.norm(L[k] - qc))[:2]

            def cfg(f):
                Lf = D.links(f)
                Qf = {n: np.array(m, float).reshape(4, 4)[:3, 3] * D.us for n, m in D.F[f]['ql'].items()}
                if any(k not in Lf for k in adj) or set(Qf) != set(Q):
                    return None
                pts = [Qf[n] for n in sorted(Qf)] + [Lf[k] for k in adj]
                return np.array([np.linalg.norm(pts[i] - pts[j]) for i in range(len(pts)) for j in range(i + 1, len(pts))])
            ref = cfg(fe)
            C = {f: cfg(f) for f in fr}
            dev = {f: (float(np.max(np.abs(c - ref))) if c is not None else 9.0) for f, c in C.items()}
            seat = None
            for f in fr:
                if all(dev[g] <= 0.0005 for g in fr if g >= f):
                    seat = f; break
            sep = dev[fr[0]]
            det.append(f'QUICK_LINK parts {sorted(Q)}; separation at link_join_start {sep*1000:.1f} mm; seated from frame {seat}')
            if sep <= 0.002: bad.append('QUICK_LINK already seated at link_join_start (no separated -> seated change)')
            if seat is None or abs(seat - lc) > 3: bad.append(f'QUICK_LINK seats at {seat}, not within 3 frames of link_click {lc}')
    if foley is None:
        bad.append('foley stem missing')
    else:
        ok, d = transient_at(foley, sr, lc / FPS, 2 / FPS, (270 / FPS, 450 / FPS))
        det.append(d)
        if not ok: bad.append('foley click: ' + d.split(';')[0])
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


def g02(D, ev):
    bad, det = [], []
    c = ev.get('chain_hand_contact')
    if c is None:
        return 'fail', 'chain_hand_contact missing'
    T = tips(D, c)
    if not T:
        return 'fail', f'no fingertip data at chain_hand_contact {c}'
    tn = min(T, key=lambda k: T[k]['d_chain'])
    d0 = T[tn]['d_chain'] * D.us
    det.append(f'closest fingertip {tn} {d0*100:.1f} cm from CHAIN at {c}')
    if d0 > 0.02: bad.append(f'no finger within 2 cm of CHAIN at chain_hand_contact ({d0*100:.1f} cm)')
    L0 = D.links(c)
    if not L0:
        return 'fail', '; '.join(bad + ['no chain-link data at contact'])
    tp0 = np.array(T[tn]['p'], float) * D.us
    near = sorted(L0, key=lambda k: np.linalg.norm(L0[k] - tp0))[:5]
    pre = [f for f in D.frames(c - 10, c - 1, 'links')]
    if len(pre) < 5:
        bad.append('too few samples before contact')
    else:
        mv = max(float(np.linalg.norm(D.links(f)[k] - L0[k])) for f in pre for k in near if k in D.links(f))
        det.append(f'chain end moves {mv*1000:.1f} mm in the 10 frames before contact')
        if mv > 0.002: bad.append('chain end not still before contact')
    post = [f for f in D.frames(c + 1, min(c + 15, 449), 'tips') if 'links' in D.F[f] and tn in tips(D, f)]
    if not post:
        bad.append('no samples after contact')
    else:
        f1 = post[-1]
        L1 = D.links(f1)
        dl = np.mean([L1[k] - L0[k] for k in near if k in L1], axis=0)
        dt = np.array(tips(D, f1)[tn]['p'], float) * D.us - tp0
        nl, nt = float(np.linalg.norm(dl)), float(np.linalg.norm(dt))
        cos = float(dl @ dt / max(nl * nt, 1e-12))
        det.append(f'after contact (to {f1}): chain {nl*1000:.0f} mm, fingertip {nt*1000:.0f} mm, cos {cos:.2f}')
        if nl < 0.005 or nt < 0.005 or cos < 0.5 or not (0.5 <= nl / max(nt, 1e-9) <= 2):
            bad.append('chain not driven by the hand after contact (same direction, ratio 0.5-2)')
    pen = [(f, D.F[f]['pen']) for f in D.frames(270, 449, 'pen')]
    if not pen:
        bad.append('no interpenetration samples (finger-weighted vertices missing?)')
    else:
        pm = max(pen, key=lambda x: x[1])
        det.append(f'max finger penetration {pm[1]*D.us*1000:.1f} mm at {pm[0]} ({len(pen)} samples)')
        if pm[1] * D.us > 0.006: bad.append('finger/chain/cog interpenetration > 6 mm')
    e0 = [engaged(D, f, 'CHAINRING', RP_RING) for f in D.frames(270, 275, 'links')[:1]]
    e1 = [(engaged(D, f, 'CHAINRING', RP_RING), engaged(D, f, 'REAR_COG', RP_COG)) for f in D.frames(440, 449, 'links')[-1:]]
    c0 = [engaged(D, f, 'REAR_COG', RP_COG) for f in D.frames(270, 275, 'links')[:1]]
    if not e0 or not e1 or e0[0] is None or e1[0][0] is None or e1[0][1] is None:
        bad.append('cannot evaluate chain on cog/chainring')
    else:
        on_start = len(e0[0]) >= 4 and len(c0[0] or []) >= 4
        on_end = len(e1[0][0]) >= 4 and len(e1[0][1]) >= 4
        det.append(f'links on chainring/cog: start {len(e0[0])}/{len(c0[0] or [])}, end {len(e1[0][0])}/{len(e1[0][1])}')
        if on_start or not on_end: bad.append('CHAIN does not go from off the bike to engaged on REAR_COG and CHAINRING in S3')
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


# ---------------------------------------------------------------- mechanics (G03-G05)
def drive_window(ev):
    return ev['chain_engage'] + 2, ev['crank_release'] - 2


def g03(D, ev):
    a, b = drive_window(ev)
    w = omega(D, 'CHAINRING', 'BIKE', 'CHAINRING', a, b, maxgap=1)
    fr = [f for f in sorted(w) if abs(w[f]) > 0.5 and 'links' in D.F.get(f, {}) and 'links' in D.F.get(f + 1, {})]
    if len(fr) < 5:
        return 'fail', f'chainring not turning / no samples in drive window {a}-{b} ({len(fr)})'
    ratios = []
    for f in fr:
        L1, L2 = D.links(f), D.links(f + 1)
        B1, B2 = rot(D.M(f, 'BIKE')), rot(D.M(f + 1, 'BIKE'))
        t1, t2 = D.pos(f, 'BIKE'), D.pos(f + 1, 'BIKE')
        sp = [np.linalg.norm(B2.T @ (L2[k] - t2) - B1.T @ (L1[k] - t1)) * FPS for k in L1 if k in L2]
        if not sp:
            continue
        ratios.append(float(np.median(sp)) / (abs(w[f]) * RP_RING))
    ok_share = frac_ok(ratios, lambda r: abs(r - 1) <= 0.12)
    fm = fr[len(fr) // 2]
    eg = engaged(D, fm, 'CHAINRING', RP_RING) or []
    near = frac_ok(eg, lambda x: abs(x) <= 0.004)
    det = (f'link speed / pitch-line speed median {np.median(ratios) if ratios else None:.3f}, {ok_share*100:.0f}% of {len(ratios)} frames within 12%; '
           f'{len(eg)} links on the chainring at {fm}, {near*100:.0f}% within 4 mm of the pitch circle (r={RP_RING*1000:.2f} mm)')
    bad = []
    if ok_share < TOL_FRAC: bad.append('chain slips (link speed vs chainring pitch-line speed >12%)')
    if len(eg) < 8 or near < 0.8: bad.append('links do not sit on the chainring pitch circle')
    return ('fail' if bad else 'pass'), '; '.join(bad + [det])


def g04(D, ev):
    bad, det = [], []
    if ev['chain_engage'] - ev['crank_turn_start'] > 15: bad.append('chain_engage - crank_turn_start > 15 frames')
    a, b = drive_window(ev)
    wr = omega(D, 'CHAINRING', 'BIKE', 'CHAINRING', 540, 659, 1)
    wc = omega(D, 'REAR_COG', 'BIKE', 'CHAINRING', 540, 659, 1)
    ww = omega(D, 'REAR_WHEEL', 'BIKE', 'CHAINRING', 540, 659, 1)
    fr = [f for f in range(a, b + 1) if f in wr and f in wc and f in ww and abs(wr[f]) > 0.5]
    if len(fr) < 5:
        return 'fail', '; '.join(bad + [f'no driving samples ({len(fr)})'])
    rc = [wc[f] / wr[f] for f in fr]
    rw = [ww[f] / wc[f] if abs(wc[f]) > 1e-6 else 0 for f in fr]
    s1 = frac_ok(rc, lambda r: abs(r / RATIO - 1) <= 0.10)
    s2 = frac_ok(rw, lambda r: abs(r - 1) <= 0.05)
    det.append(f'cog/chainring median {np.median(rc):.3f} ({s1*100:.0f}% within 2.75±10%), wheel/cog median {np.median(rw):.3f} ({s2*100:.0f}% within 5%)')
    if s1 < TOL_FRAC: bad.append('gear ratio not 2.75±10% (same rotation sense)')
    if s2 < TOL_FRAC: bad.append('REAR_WHEEL not locked to REAR_COG while driving')
    ce = ev['chain_engage']
    before = [abs(ww[f]) for f in sorted(ww) if f <= ce - 3]
    start = next((f for f in sorted(ww) if abs(ww[f]) >= 0.3), None)
    det.append(f'rear wheel starts at {start} (chain_engage {ce}); max |w| before {max(before) if before else None}')
    if before and max(before) >= 0.3: bad.append('rear wheel turns before chain_engage')
    if start is None or abs(start - ce) > 2: bad.append('rear wheel does not start within chain_engage±2')
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


def g05(D, ev, foley, sr):
    bad, det = [], []
    rl = ev['crank_release']
    if 659 - rl < 15: bad.append('fewer than 15 frames after crank_release in S5')
    ww = omega(D, 'REAR_WHEEL', 'BIKE', 'CHAINRING', rl - 3, 659, 1)
    wk = omega(D, 'CRANK', 'BIKE', 'CHAINRING', rl - 3, 659, 1)
    fr = [f for f in sorted(ww) if f >= rl]
    if len(fr) < 10 or (rl - 1) not in ww:
        return 'fail', '; '.join(bad + ['no wheel samples after crank_release'])
    w0 = abs(ww[rl - 1]); k0 = abs(wk.get(rl - 1, 0))
    vals = [abs(ww[f]) for f in fr]
    coast = [f for f in fr if abs(ww[f]) > 0.3]
    det.append(f'wheel |w| at release {w0:.2f} rad/s, turning for {len(coast)} frames after release')
    if len(coast) < 15: bad.append('rear wheel coasts < 0.5 s')
    mono = all(vals[i + 1] <= vals[i] * 1.03 + 0.05 for i in range(len(vals) - 1))
    jump = max([vals[i] - vals[i + 1] for i in range(len(vals) - 1)] + [0]) > 0.25 * max(w0, 1e-6)
    if not mono or jump: bad.append('wheel speed does not decay monotonically / stops abruptly')
    fe = coast[-1] if coast else fr[-1]
    kn = abs(wk.get(fe, 0)) / max(k0, 1e-6); wn = abs(ww[fe]) / max(w0, 1e-6)
    det.append(f'normalised speed at {fe}: crank {kn:.2f} wheel {wn:.2f}')
    if k0 < 0.5 or not (kn < wn) or (abs(wk.get(fe, 0)) > 1e-3 and abs(ww[fe]) / abs(wk[fe]) <= RATIO * 1.1):
        bad.append('crank is dragged along by the wheel (no freewheel)')
    if foley is None:
        bad.append('foley stem missing')
    else:
        rs, cs = [], []
        t = (rl + 3) / FPS
        t_end = (fe + 1) / FPS
        while t + 0.25 <= t_end + 1e-9:
            fm = int(round((t + 0.125) * FPS))
            fm = min(ww, key=lambda f: abs(f - fm))
            pk, r = tick_ratio(foley, sr, t, t + 0.25, abs(ww[fm]) / (2 * math.pi))
            if pk is not None:
                rs.append(r); cs.append(pk)
            t += 0.25
        valid = [r for r, c in zip(rs, cs) if r is not None and c >= 0.3]
        det.append(f'coast windows: ticks/rev {[None if r is None else round(r, 1) for r in rs]} corr {[round(c, 2) for c in cs]}')
        if len(rs) < 2 or len(valid) < len(rs) or len(valid) < 2:
            bad.append('no periodic ratchet ticks in every 0.25 s coast window')
        else:
            cv = float(np.std(valid) / max(np.mean(valid), 1e-9))
            det.append(f'ratio CV {cv*100:.0f}%')
            if not all(18 <= r <= 72 for r in valid) or cv > 0.25:
                bad.append('tick rate / wheel speed not within 18-72 with CV<=25%')
        a, b = drive_window(ev)
        wd = omega(D, 'REAR_WHEEL', 'BIKE', 'CHAINRING', a, b, 1)
        t = (ev['chain_engage'] + 3) / FPS
        hits = []
        while t + 0.25 <= (rl - 3) / FPS:
            fm = int(round((t + 0.125) * FPS))
            if wd:
                fm = min(wd, key=lambda f: abs(f - fm))
                seg = foley[int(t * sr):int((t + 0.25) * sr)]
                lvl = 20 * math.log10(max(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0, 1e-9))
                if lvl > -60:
                    pk, r = tick_ratio(foley, sr, t, t + 0.25, abs(wd[fm]) / (2 * math.pi))
                    if pk is not None and pk >= 0.5 and r is not None and 18 <= r <= 72:
                        hits.append(round(t, 2))
            t += 0.25
        if hits: bad.append(f'ratchet-like periodic ticks while driving at {hits[:4]} s')
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


# ---------------------------------------------------------------- match cut / ride (G06, G07)
def g06(D, res):
    W, H = res
    c5 = (D.cam(659, 'S5') or {}).get('rim', {}).get('CHAINRING')
    r6 = (D.cam(660, 'S6') or {}).get('rim', {})
    if not c5 or not r6:
        return 'fail', 'no chainring projection at 659/660'

    def diam(r):
        P = np.array([[p[0] * W, p[1] * H] for p in r['rim']])
        return max(float(np.linalg.norm(P[i] - P[(i + 8) % 16])) for i in range(8))
    name6 = max(r6, key=lambda n: diam(r6[n]) if 0 <= r6[n]['centre'][0] <= 1 and r6[n]['centre'][2] > 0 else -1)
    c6 = r6[name6]
    bad, det = [], []
    if any(p[2] <= 0 for p in c5['rim'] + c6['rim']):
        return 'fail', 'chainring behind camera'
    dx = (c6['centre'][0] - c5['centre'][0]); dy = (c6['centre'][1] - c5['centre'][1]) * H / W
    dc = math.hypot(dx, dy)
    d5, d6 = diam(c5), diam(c6)
    det.append(f'centre shift {dc*100:.1f}% width, diameter {d5:.0f}px -> {d6:.0f}px ({name6})')
    if dc > 0.08: bad.append('chainring centre moves >8% of frame width across the cut')
    if not (0.67 <= d6 / max(d5, 1e-6) <= 1.5): bad.append('projected diameter ratio not 0.67-1.5')
    if d6 < 0.3 * H: bad.append('chainring not dominant at the S6 opening (<30% frame height)')

    def spin(fa, fb, shot, name):
        A = (D.cam(fa, shot) or {}).get('rim', {}).get(name); B = (D.cam(fb, shot) or {}).get('rim', {}).get(name)
        if not A or not B:
            return None
        def ang(r):
            return math.atan2((r['rim'][0][1] - r['centre'][1]) * H, (r['rim'][0][0] - r['centre'][0]) * W)
        d = ang(B) - ang(A)
        return (d + math.pi) % (2 * math.pi) - math.pi
    s5 = spin(658, 659, 'S5', 'CHAINRING'); s6 = spin(660, 661, 'S6', name6)
    det.append(f'screen spin per frame S5 {None if s5 is None else round(math.degrees(s5), 2)}°, S6 {None if s6 is None else round(math.degrees(s6), 2)}°')
    if s5 is None or s6 is None or abs(s5) < math.radians(0.3) or abs(s6) < math.radians(0.3):
        bad.append('chainring not rotating on screen on both sides of the cut')
    elif s5 * s6 < 0 or not (0.5 <= abs(s6) / abs(s5) <= 2.0):
        bad.append('on-screen rotation sense differs or speed ratio not 0.5-2')
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


def g07(D, ev):
    bad, det = [], []
    ps = ev['pedal_start']
    bike = D.mover('BIKE', 660, 899)
    if bike is None:
        return 'fail', 'no BIKE in S6'
    ob, o0 = D.objects.get(bike, {}), D.objects.get('BIKE', {})
    ch = children_map(D)
    same = bike == 'BIKE' or (ob.get('data') and ob.get('data') == o0.get('data')) or (
        sorted(D.objects[c].get('data') or '' for c in ch.get(bike, [])) == sorted(D.objects[c].get('data') or '' for c in ch.get('BIKE', [])) and ch.get('BIKE'))
    det.append(f'S6 bike {bike}')
    if not same: bad.append(f'S6 bike {bike} is not BIKE or a linked copy of it')
    ring, crank = D.mover('CHAINRING', 660, 899), D.mover('CRANK', 660, 899)
    rw, fw = D.mover('REAR_WHEEL', 660, 899), D.mover('FRONT_WHEEL', 660, 899)
    fr = D.frames(ps + 3, 899)
    rows = []
    for f1, f2 in zip(fr, fr[1:]):
        if f2 - f1 > 2:
            continue
        p1, p2 = D.pos(f1, bike), D.pos(f2, bike)
        if p1 is None or p2 is None:
            continue
        dt = (f2 - f1) / FPS
        v = (p2 - p1) / dt; v[2] = 0
        rows.append((f1, f2, v))
    rows = [r for r in rows if np.linalg.norm(r[2]) > 0.3]
    if len(rows) < 5:
        return 'fail', '; '.join(bad + det + ['bike does not move after pedal_start'])
    fwd = np.mean([r[2] / np.linalg.norm(r[2]) for r in rows], axis=0); fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 0, 1.0])
    f_mid = rows[len(rows) // 2][0]
    pc, pw = D.pos(f_mid, ring), D.pos(f_mid, rw)
    lat = float((pc - pw) @ right) if pc is not None and pw is not None else None
    det.append(f'chainring lateral offset from rear-wheel plane {lat}')
    if lat is None or lat <= 0.01: bad.append('drive side not on the right of the riding bike')
    cad, roll_r, roll_f = [], [], []
    for f1, f2, v in rows:
        sp = float(np.linalg.norm(v)); dt = (f2 - f1) / FPS
        B1, B2 = rot(D.M(f1, bike)), rot(D.M(f2, bike))
        def wrel(n):
            m1, m2 = D.M(f1, n), D.M(f2, n)
            if m1 is None or m2 is None: return None
            th, _ = delta_angle(B1.T @ rot(m1), B2.T @ rot(m2))
            return th / dt
        def wworld(n):
            m1, m2 = D.M(f1, n), D.M(f2, n)
            if m1 is None or m2 is None: return None
            th, ax = delta_angle(rot(m1), rot(m2))
            return th / dt * float(ax @ np.cross([0, 0, 1.0], fwd))
        wc = wrel(crank)
        if wc is not None:
            cad.append(wc / (2 * math.pi) * RATIO * 0.68 * math.pi / sp)
        for n, acc in ((rw, roll_r), (fw, roll_f)):
            w = wworld(n)
            if w is not None:
                acc.append(w * WHEEL_R / sp)
    s_c = frac_ok(cad, lambda r: abs(r - 1) <= 0.20)
    s_r = frac_ok(roll_r, lambda r: abs(r - 1) <= 0.15)
    s_f = frac_ok(roll_f, lambda r: abs(r - 1) <= 0.15)
    det.append(f'cadence model/ground speed median {np.median(cad) if cad else None}, {s_c*100:.0f}% within 20%; '
               f'rolling rear {np.median(roll_r) if roll_r else None} ({s_r*100:.0f}%), front {np.median(roll_f) if roll_f else None} ({s_f*100:.0f}%) within 15%')
    if s_c < TOL_FRAC: bad.append('crank cadence x 2.75 x wheel circumference does not match ground speed ±20%')
    if s_r < TOL_FRAC or s_f < TOL_FRAC: bad.append('wheels skate (rolling speed vs ground speed outside ±15% or wrong direction)')
    # courier exits frame right
    xs = []
    for f in D.frames(660, 899):
        bp = (D.cam(f, 'S6') or {}).get('bbproj', {}).get('COURIER')
        if bp:
            xs.append((f, float(np.mean([p[0] for p in bp])), min(p[2] for p in bp)))
    if not xs:
        bad.append('no COURIER projection in CAM_S6')
    else:
        inside = [f for f, x, z in xs if 0 <= x <= 1 and z > 0]
        fl, xl, zl = xs[-1]
        det.append(f'COURIER centre x at {fl}: {xl:.2f}')
        if not inside or not (xl > 1.0 and zl > 0): bad.append('courier does not exit frame right by the end of S6')
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


# ---------------------------------------------------------------- render engineering (G08 clause)
def g08_engineering(D):
    bad, det = [], []
    used = set()
    for n, e in D.objects.items():
        if e.get('in_scene') and e.get('type') in ('MESH', 'CURVE', 'SURFACE', 'FONT'):
            used.update(e.get('materials') or [])
    M = D.d.get('materials') or {}
    um = [M[m] for m in used if m in M]
    if not um:
        return 'fail', 'no materials on scene geometry'
    nb = sum(1 for m in um if m['bsdf'])
    nt = sum(1 for m in um if m['tex_inputs'])
    det.append(f'{len(um)} materials: {nb} with a BSDF, {nt} with textured/procedural inputs')
    if nb < 0.9 * len(um): bad.append('more than 10% of materials have no BSDF (flat/emission shading)')
    if nt < 4: bad.append('fewer than 4 materials with surface variation (textures/procedurals on colour/roughness/normal)')
    lights = [e['light'] for e in D.objects.values() if e.get('in_scene') and e.get('light')]
    soft = [l for l in lights if l['energy'] > 0 and (l['type'] == 'AREA' or (l['type'] == 'SUN' and l['angle'] > 0.009) or
                                                      (l['type'] in ('POINT', 'SPOT') and max(l['soft'], l['size']) >= 0.05))]
    w = D.d.get('world') or {}
    sky = any(t in (w.get('nodes') or []) for t in ('TEX_SKY', 'TEX_ENVIRONMENT')) and (w.get('strength') or 0) > 0
    det.append(f'{len(soft)} soft lights, sky/HDRI {sky}')
    if not soft and not sky: bad.append('no area/soft light or sky/HDRI world')
    r = D.d.get('render') or {}
    den = r.get('engine') != 'CYCLES' or r.get('cycles_denoise') or r.get('comp_denoise')
    det.append(f"engine {r.get('engine')} denoise {r.get('cycles_denoise')}/{r.get('comp_denoise')}")
    if not den: bad.append('Cycles without denoising')
    return ('fail' if bad else 'pass'), '; '.join(bad + det)


# ---------------------------------------------------------------- SSIM (M04, M09)
def _box(x, k=7):
    c = np.cumsum(np.cumsum(np.pad(x, ((1, 0), (1, 0))), 0), 1)
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def ssim(a, b):
    a = a.astype(np.float64); b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = _box(a), _box(b)
    va = _box(a * a) - ma ** 2; vb = _box(b * b) - mb ** 2; cv = _box(a * b) - ma * mb
    s = ((2 * ma * mb + C1) * (2 * cv + C2)) / ((ma ** 2 + mb ** 2 + C1) * (va + vb + C2))
    return float(s.mean())
