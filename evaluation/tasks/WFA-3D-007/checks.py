# -*- coding: utf-8 -*-
"""BLD-W07 Star Lake Theme Park — deterministic checks (called by rubric_score.py).

run(ctx) -> {item_id: {"verdict": "pass"|"fail", "detail": str}}
Items NOT returned are left to the judge model: only G14 (deduct-only visual review incl. roof/spire forms).
G01-G05 are fully machine-decided (2026-10-25 cleanup): counts of park-unit features are measured on the evaluated
frame-1 geometry (slices, orthographic facade rasters, loose parts; see _disc_unit), ride counts by name prefix.
All measurements come from ONE Blender export (Scene.load) + the extra_py below
(frame-1 bboxes/matrices, selected vertices, walkable-surface flood fill for G11, swept-envelope sweep for G12).
Conventions follow answer-key.json["conventions"].
"""
import json, math, re, traceback, pathlib, zlib, struct

from _bld_lib import Scene, ok, bad, png_size, load_manifest, gate_group


def close(a, b, rel=0.03, abs_=0.3):
    """rubric size tolerance: ±3 % or ±0.3 m, whichever is larger (_bld_lib.close defaults to 0.1 m)."""
    try:
        return abs(float(a) - float(b)) <= max(abs_, rel * abs(float(b)))
    except Exception:
        return False

RIDES = ['R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08', 'R09', 'R10', 'R11', 'R12']
PARK = ['G01', 'V01', 'F01', 'M01', 'K01', 'K02', 'K03', 'K04', 'K05', 'L01', 'B01', 'B02', 'P01', 'H01']
UNITS = RIDES + PARK
FRAMES = [1, 7, 61, 133, 181, 241, 361, 481, 487, 541, 600, 720]
SAMPLE = [61, 133, 241, 361, 487, 600, 720]
GEOM = ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')
TOL_POS, TOL_ANG, TOL_LIFT = 1.0, 2.0, 0.3
TYPE_OF = {'R01': 'FW', 'R07': 'FW', 'R02': 'CR', 'R09': 'CR', 'R03': 'PS', 'R04': 'DT', 'R05': 'CS', 'R10': 'CS',
           'R06': 'TC', 'R11': 'TC', 'R08': 'FB', 'R12': 'RT', 'G01': 'G', 'V01': 'V', 'F01': 'F', 'M01': 'M',
           'K01': 'K', 'K02': 'K', 'K03': 'K', 'K04': 'K', 'K05': 'K', 'L01': 'L', 'B01': 'B', 'B02': 'B', 'P01': 'P', 'H01': 'H'}
FIELDS = {'FW': 'diameter_m hub_height_m gondolas gondola_type period_s direction',
          'CR': 'diameter_m horses_per_row roof period_s direction bob_per_rev',
          'PS': 'pivot_height_m arm_m hull_length_m seat_rows amplitude_deg period_s',
          'DT': 'tower_height_m faces seats_per_face cycle_s',
          'CS': 'tower_height_m seat_type seats fly_angle_deg period_s direction',
          'TC': 'platter_diameter_m sub_platters cups_per_sub canopy main_period_s sub_period_s',
          'FB': 'pivot_height_m arm_m amplitude_deg period_s seats disc_period_s disc_direction',
          'RT': 'mast_height_m seats cycle_s spin_period_s spin_direction',
          'G': 'width_m arches towers spire', 'V': 'storeys roof bays', 'F': 'basin_diameter_m tiers jets',
          'M': 'height_m tiers clock_faces', 'K': 'roof windows', 'L': 'water_level_m island_radius_m',
          'B': 'deck_width_m form rail_posts_per_side', 'P': 'sides roof', 'H': 'roof bays'}
ZONE_ITEMS = {'M01': 'A', 'M02': 'B', 'M03': 'C', 'M04': 'D', 'M05': 'E'}
SCENE_ITEMS = ['B01', 'B02', 'B03', 'B04', 'B08', 'M01', 'M02', 'M03', 'M04', 'M05', 'M06', 'M07', 'M08', 'M09', 'M10',
               'M11', 'M12', 'G01', 'G02', 'G03', 'G04', 'G05', 'G06', 'G07', 'G08', 'G09', 'G10', 'G11', 'G12', 'G13']

# ----------------------------------------------------------------------------------------------
# extra_py: executed inside Blender by _bld_extract.py. HELPERS are pure python/numpy (unit-testable
# outside Blender, see REVIEW/smoke/make_fake.py); DRIVER uses bpy.
# ----------------------------------------------------------------------------------------------
EXTRA_HELPERS = r'''
import math as _m
try:
    import numpy as np
except Exception:
    np = None

def _flood(tris, start, targets, step=0.25, zmin=-0.05, zmax=2.0, nz_min=0.7, max_dz=0.3, reach_r=0.6):
    """tris: [((x,y,z),(x,y,z),(x,y,z)), ...] world coords. Rasterize up-facing triangles in [zmin,zmax] to a
    step grid (cell = max surface z), 8-neighbour flood from start with |dz|<=max_dz."""
    cells = {}
    used = 0
    for a, b, c in tris:
        if min(a[2], b[2], c[2]) < zmin or max(a[2], b[2], c[2]) > zmax:
            continue
        ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
        vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
        nx, ny, nzv = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        nl = _m.sqrt(nx*nx+ny*ny+nzv*nzv)
        if nl < 1e-12 or abs(nzv)/nl < nz_min:
            continue
        det = ux*vy - uy*vx
        if abs(det) < 1e-12:
            continue
        used += 1
        i0 = int(_m.floor(min(a[0], b[0], c[0])/step)); i1 = int(_m.floor(max(a[0], b[0], c[0])/step))
        j0 = int(_m.floor(min(a[1], b[1], c[1])/step)); j1 = int(_m.floor(max(a[1], b[1], c[1])/step))
        for i in range(i0, i1+1):
            px = (i+0.5)*step - a[0]
            for j in range(j0, j1+1):
                py = (j+0.5)*step - a[1]
                s = (px*vy - py*vx)/det
                t = (ux*py - uy*px)/det
                if s < -1e-9 or t < -1e-9 or s+t > 1+1e-9:
                    continue
                z = a[2] + s*uz + t*vz
                k = (i, j)
                if k not in cells or z > cells[k]:
                    cells[k] = z
    def near(pt, r):
        ci, cj = int(_m.floor(pt[0]/step)), int(_m.floor(pt[1]/step))
        rr = int(_m.ceil(r/step))
        out = []
        for i in range(ci-rr, ci+rr+1):
            for j in range(cj-rr, cj+rr+1):
                if (i, j) in cells and ((i+0.5)*step-pt[0])**2+((j+0.5)*step-pt[1])**2 <= (r+step)**2:
                    out.append((i, j))
        return out
    seeds = near(start, 1.0)
    seen = set(seeds)
    stack = list(seeds)
    while stack:
        i, j = stack.pop()
        z = cells[(i, j)]
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                k = (i+di, j+dj)
                if k in cells and k not in seen and abs(cells[k]-z) <= max_dz:
                    seen.add(k); stack.append(k)
    reached = {}
    for name, pt in targets.items():
        reached[name] = (pt is not None) and any(k in seen for k in near(pt, reach_r))
    return {'n_cells': len(cells), 'n_tris_used': used, 'start_ok': bool(seeds), 'n_reached_cells': len(seen),
            'reached': reached}

def _dist_to_path(P, p):
    """P: Nx2 numpy array; p: path dict (segment x1,y1,x2,y2,w | ring cx,cy,r,w). Horizontal distance to polygon (0 inside)."""
    if p['kind'] == 'ring':
        d = np.hypot(P[:, 0]-p['cx'], P[:, 1]-p['cy'])
        return np.maximum(np.abs(d - p['r']) - p['w']/2.0, 0.0)
    ax, ay, bx, by = p['x1'], p['y1'], p['x2'], p['y2']
    L = _m.hypot(bx-ax, by-ay)
    ux, uy = (bx-ax)/L, (by-ay)/L
    s = (P[:, 0]-ax)*ux + (P[:, 1]-ay)*uy - L/2.0
    n = -(P[:, 0]-ax)*uy + (P[:, 1]-ay)*ux
    dx = np.maximum(np.abs(s) - L/2.0, 0.0)
    dy = np.maximum(np.abs(n) - p['w']/2.0, 0.0)
    return np.hypot(dx, dy)

def _min_pair(A, B):
    best = 1e9
    try:
        from mathutils import kdtree as _kd
        t = _kd.KDTree(len(B))
        for i, q in enumerate(B):
            t.insert((float(q[0]), float(q[1]), 0.0), i)
        t.balance()
        for q in A:
            co, idx, d = t.find((float(q[0]), float(q[1]), 0.0))
            if d < best:
                best = d
        return best
    except Exception:
        pass
    for s in range(0, len(A), 2000):
        a = A[s:s+2000]
        d = np.sqrt(((a[:, None, :]-B[None, :, :])**2).sum(-1)).min()
        best = min(best, float(d))
    return best

def _g12_summarize(swept, cfg):
    """swept: {rid: Nx3 array of swept world points (all sampled frames)}; cfg['rides'][rid] = {cx,cy,R,H};
    cfg['paths'] = [path dicts with optional 'own' ride id]."""
    out = {'rides': {}, 'pairs': [], 'min_gap': None}
    xy = {}
    for rid, P in swept.items():
        c = cfg['rides'][rid]
        if isinstance(P, dict):     # precomputed running stats (Blender sweep): max_r/max_z/min_z/n_pts + xy keys
            if not P.get('n_pts'):
                out['rides'][rid] = {'n_pts': 0}
                continue
            Q = np.asarray(P['xy'], dtype=np.float64)*0.1
            rmax, zmax, zmin, npts = P['max_r'], P['max_z'], P['min_z'], P['n_pts']
        else:
            if P is None or len(P) == 0:
                out['rides'][rid] = {'n_pts': 0}
                continue
            r = np.hypot(P[:, 0]-c['cx'], P[:, 1]-c['cy'])
            keys = np.unique(np.round(P[:, :2]/0.1).astype(np.int64), axis=0)
            Q = keys.astype(np.float64)*0.1
            rmax, zmax, zmin, npts = float(r.max()), float(P[:, 2].max()), float(P[:, 2].min()), len(P)
        xy[rid] = Q
        pm, pid = 1e9, None
        for p in cfg['paths']:
            if p.get('own') == rid:
                continue
            d = float(_dist_to_path(Q, p).min())
            if d < pm:
                pm, pid = d, p['id']
        out['rides'][rid] = {'n_pts': int(npts), 'max_r': round(float(rmax), 3), 'max_z': round(float(zmax), 3),
                             'min_z': round(float(zmin), 3), 'path_min': round(pm, 3), 'path_min_id': pid}
    ids = sorted(xy)
    gmin = None
    for i in range(len(ids)):
        for j in range(i+1, len(ids)):
            a, b = ids[i], ids[j]
            ca, cb = cfg['rides'][a], cfg['rides'][b]
            lb = _m.hypot(ca['cx']-cb['cx'], ca['cy']-cb['cy']) - out['rides'][a]['max_r'] - out['rides'][b]['max_r']
            if lb >= 4.0:
                d, how = lb, 'bound'
            else:
                d, how = _min_pair(xy[a], xy[b]), 'exact'
            out['pairs'].append({'a': a, 'b': b, 'd': round(float(d), 3), 'how': how})
            gmin = d if gmin is None else min(gmin, d)
    out['min_gap'] = None if gmin is None else round(float(gmin), 3)
    return out

# ---- discrete-feature measurement helpers (G01-G05, M12): pure numpy, operate on world triangles of one unit ----
def _to_local(V, x, y, rot):
    """columns: u (along facade / across bridge), n (along rot_deg: facade normal / bridge axis), z."""
    a = _m.radians(rot)
    nx, ny = _m.cos(a), _m.sin(a)
    dx, dy = V[:, 0] - x, V[:, 1] - y
    return np.stack([-dx * ny + dy * nx, dx * nx + dy * ny, V[:, 2]], 1)

def _slice(L, T, axis, val):
    """segments (k,2,3) where the plane L[:,axis]==val cuts the triangles T."""
    d = L[:, axis] - (val + 1.3e-6)
    D = d[T]
    m = (D.min(1) < 0) & (D.max(1) > 0)
    if not m.any():
        return np.zeros((0, 2, 3))
    Ti, Dm = T[m], D[m]
    P = np.full((len(Ti), 3, 3), np.nan)
    for k, (a, b) in enumerate(((0, 1), (1, 2), (2, 0))):
        da, db = Dm[:, a], Dm[:, b]
        c = (da * db) < 0
        if c.any():
            t = da[c] / (da[c] - db[c])
            Va, Vb = L[Ti[c, a]], L[Ti[c, b]]
            P[np.nonzero(c)[0], k] = Va + (Vb - Va) * t[:, None]
    valid = ~np.isnan(P[:, :, 0])
    ok = valid.sum(1) == 2
    order = np.argsort(~valid, axis=1, kind='stable')[:, :2]
    S = np.take_along_axis(P, order[:, :, None], axis=1)
    return S[ok]

def _seg_pts(S, step=0.025):
    if len(S) == 0:
        return np.zeros((0, 3))
    ln = np.linalg.norm(S[:, 1] - S[:, 0], axis=1)
    n = np.minimum(np.ceil(ln / step).astype(np.int64) + 1, 4000)
    idx = np.repeat(np.arange(len(S)), n)
    off = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)
    t = (off / np.maximum(np.repeat(n, n) - 1, 1))[:, None]
    return S[idx, 0] + (S[idx, 1] - S[idx, 0]) * t

def _merge(lo, hi, gap):
    if len(lo) == 0:
        return []
    o = np.argsort(lo)
    out = [[float(lo[o[0]]), float(hi[o[0]])]]
    for i in o[1:]:
        if lo[i] <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], float(hi[i]))
        else:
            out.append([float(lo[i]), float(hi[i])])
    return out

def _proj(S, axis, gap=0.05):
    if len(S) == 0:
        return []
    t = S[:, :, axis]
    return _merge(t.min(1), t.max(1), gap)

def _cells_comps(cells, conn8=True):
    """cells: set of (i,j); returns list of lists of cells (connected components)."""
    seen, comps = set(), []
    nb = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (conn8 or a == 0 or b == 0)]
    for c in cells:
        if c in seen:
            continue
        st, comp = [c], []
        seen.add(c)
        while st:
            i, j = st.pop()
            comp.append((i, j))
            for a, b in nb:
                k = (i + a, j + b)
                if k in cells and k not in seen:
                    seen.add(k); st.append(k)
        comps.append(comp)
    return comps

def _blobs2d(P, cell=0.05):
    """P: points (k,>=2) in a plane (x,y); 8-connected blobs on a cell grid -> list of (cx, cy, wx, wy)."""
    if len(P) == 0:
        return []
    ij = np.unique(np.floor(P[:, :2] / cell).astype(np.int64), axis=0)
    cells = set(map(tuple, ij.tolist()))
    out = []
    for comp in _cells_comps(cells):
        a = np.array(comp, dtype=float)
        lo, hi = a.min(0) * cell, (a.max(0) + 1) * cell
        out.append((float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2), float(hi[0] - lo[0]), float(hi[1] - lo[1])))
    return out

def _part_boxes(L, Pv):
    if len(Pv) == 0:
        return np.zeros((0, 3)), np.zeros((0, 3))
    o = np.argsort(Pv, kind='stable')
    ps = Pv[o]
    st = np.nonzero(np.r_[True, ps[1:] != ps[:-1]])[0]
    lo = np.minimum.reduceat(L[o], st, axis=0)
    hi = np.maximum.reduceat(L[o], st, axis=0)
    return lo, hi

def _dedupe(cs, r):
    out = []
    for c in cs:
        if all(_m.hypot(c[0] - d[0], c[1] - d[1]) > r for d in out):
            out.append(c)
    return out

def _raster(L, T, Mt, Pt, band, ur, zr, cell=0.1, nmin=0.5, view='front'):
    """Orthographic raster of the triangles whose depth coordinate lies inside band.
    view 'front': image axes (u in ur, z in zr), depth = n (largest n = frontmost);
    view 'top':   image axes (u in ur, n in zr), depth = z (topmost).
    returns dict(depth, mat, part) grids [iu, iv] (-inf / -1 = empty)."""
    ia, ib, idp = (0, 2, 1) if view == 'front' else (0, 1, 2)
    ra, rb = ur, zr          # image axes; band = depth range (n for 'front', z for 'top')
    na = max(1, int(_m.ceil((ra[1] - ra[0]) / cell)))
    nb = max(1, int(_m.ceil((rb[1] - rb[0]) / cell)))
    D = np.full((na, nb), -np.inf)
    MA = np.full((na, nb), -1, dtype=np.int64)
    PA = np.full((na, nb), -1, dtype=np.int64)
    if len(T) == 0:
        return {'depth': D, 'mat': MA, 'part': PA, 'cell': cell, 'ra': ra, 'rb': rb}
    tri = L[T]
    nr = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nl = np.linalg.norm(nr, axis=1)
    dp = tri[:, :, idp]
    A, B = tri[:, :, ia], tri[:, :, ib]
    keep = ((nl > 1e-12) & (np.abs(nr[:, idp]) >= nmin * np.maximum(nl, 1e-30)) & (dp.min(1) >= band[0]) & (dp.max(1) <= band[1])
            & (A.max(1) > ra[0]) & (A.min(1) < ra[1]) & (B.max(1) > rb[0]) & (B.min(1) < rb[1]))
    for t in np.nonzero(keep)[0]:
        a, b, d = A[t], B[t], dp[t]
        i0 = max(0, int(_m.floor((a.min() - ra[0]) / cell))); i1 = min(na - 1, int(_m.floor((a.max() - ra[0]) / cell)))
        j0 = max(0, int(_m.floor((b.min() - rb[0]) / cell))); j1 = min(nb - 1, int(_m.floor((b.max() - rb[0]) / cell)))
        if i1 < i0 or j1 < j0:
            continue
        ca = ra[0] + (np.arange(i0, i1 + 1) + 0.5) * cell
        cb = rb[0] + (np.arange(j0, j1 + 1) + 0.5) * cell
        PA_, PB_ = np.meshgrid(ca, cb, indexing='ij')
        ux, uy = a[1] - a[0], b[1] - b[0]
        vx, vy = a[2] - a[0], b[2] - b[0]
        det = ux * vy - uy * vx
        if abs(det) < 1e-12:
            continue
        px, py = PA_ - a[0], PB_ - b[0]
        s = (px * vy - py * vx) / det
        w = (ux * py - uy * px) / det
        ins = (s >= -1e-9) & (w >= -1e-9) & (s + w <= 1 + 1e-9)
        if not ins.any():
            continue
        z = d[0] + s * (d[1] - d[0]) + w * (d[2] - d[0])
        sub = D[i0:i1 + 1, j0:j1 + 1]
        upd = ins & (z > sub)
        if upd.any():
            sub[upd] = z[upd]
            MA[i0:i1 + 1, j0:j1 + 1][upd] = Mt[t]
            PA[i0:i1 + 1, j0:j1 + 1][upd] = Pt[t]
    return {'depth': D, 'mat': MA, 'part': PA, 'cell': cell, 'ra': ra, 'rb': rb}

def _mask_comps(mask, R, conn8=False):
    ii, jj = np.nonzero(mask)
    cells = set(zip(ii.tolist(), jj.tolist()))
    out = []
    c = R['cell']
    for comp in _cells_comps(cells, conn8):
        a = np.array(comp, dtype=float)
        lo, hi = a.min(0), a.max(0) + 1
        out.append((round(R['ra'][0] + (lo[0] + hi[0]) / 2 * c, 3), round(R['rb'][0] + (lo[1] + hi[1]) / 2 * c, 3),
                    round((hi[0] - lo[0]) * c, 3), round((hi[1] - lo[1]) * c, 3), len(comp)))
    return out

def _features(R, wr=(0.3, 3.5), hr=(0.3, 3.0), bmin=None):
    """facade features under 4 hypotheses: different material / different loose part / recess-protrusion / through-hole.
    returns {variant: [(uc, zc, w, h), ...]} filtered by size (w in wr, h in hr) and bottom >= bmin."""
    D, MA, PA = R['depth'], R['mat'], R['part']
    full = D > -np.inf
    out = {}
    if full.sum() < 4:
        return {'mat': [], 'part': [], 'depth': [], 'hole': []}
    def dom(G):
        v, c = np.unique(G[full], return_counts=True)
        return v[c.argmax()]
    masks = {'mat': full & (MA != dom(MA)), 'part': full & (PA != dom(PA)),
             'depth': full & (np.abs(D - np.median(D[full])) > 0.04)}
    # holes: empty cells not connected to the raster border
    em = ~full
    hole = np.zeros_like(em)
    for comp in _cells_comps(set(zip(*[x.tolist() for x in np.nonzero(em)])), False):
        a = np.array(comp)
        if a[:, 0].min() > 0 and a[:, 1].min() > 0 and a[:, 0].max() < em.shape[0] - 1 and a[:, 1].max() < em.shape[1] - 1:
            hole[a[:, 0], a[:, 1]] = True
    masks['hole'] = hole
    for k, mk in masks.items():
        cs = []
        for (uc, zc, w, h, n) in _mask_comps(mk, R):
            if wr[0] <= w <= wr[1] and hr[0] <= h <= hr[1] and (bmin is None or zc - h / 2 >= bmin):
                cs.append((uc, zc, w, h))
        out[k] = cs
    return out

def _label_runs(R, min_cells=4):
    """number of same-label connected regions (stripes) for material and part labels."""
    full = R['depth'] > -np.inf
    out = {}
    for k in ('mat', 'part'):
        G = R[k]
        n = 0
        for v in np.unique(G[full]):
            ii, jj = np.nonzero(full & (G == v))
            for comp in _cells_comps(set(zip(ii.tolist(), jj.tolist())), False):
                if len(comp) >= min_cells:
                    n += 1
        out[k] = n
    return out

def _profile(L, T, axis_s, s_lo, s_hi, step=0.1, zmax=4.0):
    """top surface along the centre line (u=0) as h(s) on a grid; returns (grid, h)."""
    S = _slice(L, T, 0, 0.0)
    P = _seg_pts(S, 0.03)
    g = np.arange(s_lo, s_hi + 1e-9, step)
    h = np.full(len(g), np.nan)
    if len(P):
        P = P[P[:, 2] <= zmax]
        k = np.floor((P[:, axis_s] - s_lo) / step + 0.5).astype(np.int64)
        m = (k >= 0) & (k < len(g))
        hh = np.full(len(g), -np.inf)
        np.maximum.at(hh, k[m], P[m, 2])
        h = np.where(np.isfinite(hh), hh, np.nan)
    ok = ~np.isnan(h)
    if ok.sum() >= 2:
        h = np.interp(g, g[ok], h[ok])
    return g, h

def _facade_windows(L, T, Mt, Pt, length, depth, eave, side_d=None, bmin=0.25, wr=(0.3, 3.5), hr=(0.3, 3.0)):
    d = depth / 2.0 if side_d is None else side_d
    R = _raster(L, T, Mt, Pt, (d - 0.6, d + 0.6), (-length / 2 + 0.05, length / 2 - 0.05), (0.05, eave - 0.05), 0.1, 0.5, 'front')
    return _features(R, wr, hr, bmin)

def _disc_unit(uid, L0, T, Mt, Pt, Pv, u):
    """measure the discrete features of one park unit. L0: world vertices; u: cfg (x, y, rot, kind, params)."""
    k = u['kind']; P = u['p']; x, y, rot = u['x'], u['y'], u['rot']
    r = {}
    if k == 'G':
        L = _to_local(L0, x, y, rot)
        iv = _proj(_slice(L, T, 2, 2.0), 0, 0.05)
        gaps = [round(iv[i + 1][0] - iv[i][1], 3) for i in range(len(iv) - 1)]
        r['arch_gaps'] = gaps
        r['arches'] = sum(1 for g in gaps if g >= 0.8)
        zt = 0.75 * P['tower_height_m']
        iv2 = _proj(_slice(L, T, 2, zt), 0, 0.3)
        r['tower_widths'] = [round(b - a, 2) for a, b in iv2]
        r['towers'] = sum(1 for a, b in iv2 if b - a >= 1.0)
    elif k == 'F':
        L = _to_local(L0, x, y, 0.0)
        tri = L[T]
        nr = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nl = np.linalg.norm(nr, axis=1)
        cen = tri.mean(1)
        rr = np.hypot(cen[:, 0], cen[:, 1])
        Rb = P['basin_diameter_m'] / 2
        sel = (nl > 1e-12) & (np.abs(nr[:, 2]) > 0.9 * np.maximum(nl, 1e-30)) & (rr <= 0.65 * Rb) & (cen[:, 2] >= P['basin_wall_m'] + 0.15)
        zs, ar = cen[sel, 2], np.abs(nr[sel, 2]) / 2
        o = np.argsort(zs)
        cl = []
        for z, a in zip(zs[o], ar[o]):
            if cl and z - cl[-1][1] <= 0.3:
                cl[-1][1] = z; cl[-1][2] += a
            else:
                cl.append([z, z, a])
        lv = [(round(c[0], 2), round(c[2], 2)) for c in cl if c[2] >= 1.0]
        r['tier_levels'] = lv
        r['tiers'] = len(lv)
        lo, hi = _part_boxes(L, Pv)
        c = (lo + hi) / 2
        sz = (hi - lo).max(1)
        rc = np.hypot(c[:, 0], c[:, 1])
        jm = (rc >= 0.55 * Rb) & (rc <= Rb - 0.15) & (sz <= 1.5) & (c[:, 2] <= 4.0)
        js = _dedupe([(float(a), float(b)) for a, b in c[jm][:, :2]], 0.3)
        r['jets'] = len(js)
    elif k == 'M':
        L = _to_local(L0, x, y, 0.0)
        H = P['height_m']
        ext = []
        for z in np.arange(0.3, H - 5.4, 0.2):
            Q = _seg_pts(_slice(L, T, 2, float(z)), 0.05)
            Q = Q[(np.abs(Q[:, 0]) <= 4.0) & (np.abs(Q[:, 1]) <= 4.0)] if len(Q) else Q
            ext.append((float(z), float(min(np.ptp(Q[:, 0]), np.ptp(Q[:, 1]))) if len(Q) > 2 else 0.0))
        pl = []
        for z, e in ext:
            if e <= 0.2:
                continue
            if pl and abs(e - pl[-1][2]) <= 0.15 and z - pl[-1][1] <= 0.21:
                pl[-1][1] = z
            else:
                pl.append([z, z, e])
        tiers = [p for p in pl if p[1] - p[0] + 0.2 >= 1.0]
        r['tier_sizes'] = [(round(p[0], 1), round(p[1], 1), round(p[2], 2)) for p in tiers]
        r['tiers'] = len(tiers)
        clocks = {}
        if tiers:
            z0, z1, e = tiers[-1]
            for sd in (0, 90, 180, 270):
                Ls = _to_local(L0, x, y, float(sd))
                R = _raster(Ls, T, Mt, Pt, (e / 2 - 0.6, e / 2 + 0.6), (-e / 2 - 0.3, e / 2 + 0.3), (z0 - 0.3, z1 + 0.3), 0.08, 0.5, 'front')
                f = _features(R, (1.0, 3.8), (1.0, 3.8), None)
                clocks[str(sd)] = {kk: len(v) for kk, v in f.items()}
        r['clocks'] = clocks
    elif k == 'P':
        L = _to_local(L0, x, y, 0.0)
        Q = _seg_pts(_slice(L, T, 2, P['platform_height_m'] - 0.1), 0.03)
        sides = None
        if len(Q):
            Q = Q[np.hypot(Q[:, 0], Q[:, 1]) <= P['diameter_m']]
        if len(Q) > 20:
            th = (np.degrees(np.arctan2(Q[:, 1], Q[:, 0])) % 360).astype(np.int64) % 360
            rm = np.full(360, -1.0)
            np.maximum.at(rm, th, np.hypot(Q[:, 0], Q[:, 1]))
            ok = rm >= 0
            if ok.sum() >= 36:
                idx = np.arange(360)
                rm = np.interp(idx, np.r_[idx[ok] - 360, idx[ok], idx[ok] + 360], np.r_[rm[ok], rm[ok], rm[ok]])
                r['outline_r'] = [round(float(rm.min()), 2), round(float(rm.max()), 2)]
                if rm.max() - rm.min() < 0.1:
                    sides = 0
                else:
                    hi_ = rm > (rm.max() + rm.min()) / 2
                    sides = int(np.sum(hi_ & ~np.roll(hi_, 1)))
                    if hi_.all():
                        sides = 0
        r['sides'] = sides
        zc = P['platform_height_m'] + 1.5
        bl = _blobs2d(_seg_pts(_slice(L, T, 2, zc), 0.02), 0.05)
        cols = [b for b in bl if 1.0 <= _m.hypot(b[0], b[1]) <= P['diameter_m'] / 2 + 0.5 and max(b[2], b[3]) <= 1.2]
        r['columns'] = len(cols)
        r['blobs_at_column_height'] = len(bl)
    elif k == 'B':
        L = _to_local(L0, x, y, rot)          # n = bridge axis (s), u = across (t)
        half = P['span_m'] / 2
        g, h = _profile(L, T, 1, -half - 0.6, half + 0.6, 0.1)
        if np.isnan(h).all():
            r['err'] = 'no deck at the bridge centre line'
            return r
        inside = np.abs(g) <= half
        ends = [float(np.interp(-half + 0.15, g, h)), float(np.interp(half - 0.15, g, h))]
        r['deck_end_z'] = [round(e, 3) for e in ends]
        r['rise'] = round(float(np.nanmax(h[inside]) - np.mean(ends)), 3)
        Lw = L.copy()
        Lw[:, 2] = L[:, 2] - np.interp(L[:, 1], g, h)
        Q = _seg_pts(_slice(Lw, T, 2, 0.45), 0.02)
        w2 = P['deck_width_m'] / 2
        posts = {}
        for nm, sg in (('L', -1), ('R', 1)):
            q = Q[(sg * Q[:, 0] >= w2 - 0.6) & (sg * Q[:, 0] <= w2 + 0.8) & (np.abs(Q[:, 1]) <= half + 0.5)] if len(Q) else Q
            iv = _merge(q[:, 1], q[:, 1], 0.05) if len(q) else []
            posts[nm] = {'n': sum(1 for a, b in iv if b - a <= 0.8), 'wide': sum(1 for a, b in iv if b - a > 0.8)}
        r['posts'] = posts
        Q2 = _seg_pts(_slice(L, T, 2, -0.7), 0.05)
        iv = _merge(Q2[:, 1], Q2[:, 1], 0.3) if len(Q2) else []
        r['piers'] = sum(1 for a, b in iv if abs((a + b) / 2) < half - 0.8)
    if k in ('V', 'H', 'K'):
        L = _to_local(L0, x, y, rot)
        Lf, Dp, ev = P['length_m'], P['width_m'], P['eave_height_m']
        f = _facade_windows(L, T, Mt, Pt, Lf, Dp, ev)
        r['windows'] = {kk: len(v) for kk, v in f.items()}
        rows = {}
        for kk, v in f.items():
            zs = sorted(c[1] for c in v)
            rw = []
            for z in zs:
                if rw and z - rw[-1][-1] <= 1.0:
                    rw[-1].append(z)
                else:
                    rw.append([z])
            rows[kk] = [len(a) for a in rw]
        r['window_rows'] = rows
        sides = {}
        for sd in (0, 90, 180, 270):
            Ls = _to_local(L0, x, y, rot + sd)
            dd, ll = (Dp, Lf) if sd in (0, 180) else (Lf, Dp)
            fs = _facade_windows(Ls, T, Mt, Pt, ll, dd, ev, None, None, (0.3, 6.0), (0.3, 4.5))
            sides[str(sd)] = max(len(v) for v in fs.values())
        r['side_features'] = sides
        if k == 'H':
            low = T[(L[T][:, :, 2].max(1) <= 1.5)]
            r['terrace_depth'] = round(float(L[np.unique(low), 1].max() - Dp / 2), 3) if len(low) else None
        if k == 'K' and P.get('roof') == 'awning':
            d = Dp / 2
            st = {}
            Rf = _raster(L, T, Mt, Pt, (d - 0.3, d + 3.0), (-Lf / 2 - 1.0, Lf / 2 + 1.0), (ev - 0.75, ev - 0.05), 0.05, 0.05, 'front')
            for kk, v in _label_runs(Rf).items():
                st['front_' + kk] = v
            Rt = _raster(L, T, Mt, Pt, (ev - 1.2, ev + 0.3), (-Lf / 2 - 1.0, Lf / 2 + 1.0), (d + 0.05, d + 3.0), 0.05, 0.05, 'top')
            for kk, v in _label_runs(Rt).items():
                st['top_' + kk] = v
            r['stripes'] = st
    return r
'''

EXTRA_DRIVER = r'''
# Real-image fix (2026-10-25): the Debian Blender 4.3.2 of workflowarena-original-cdc-tools runs on the system
# python3.13 WITHOUT numpy. This driver therefore only uses pure Python inside Blender: f1 / verts / g11 are
# computed here; the numpy-heavy G12 sweep and the discrete-feature measurement (DISC) only COLLECT raw arrays
# here (written as binary blobs next to the extract JSON, index in EXTRA['_raw']); checks._post_raw() runs the
# unchanged numpy helpers (EXTRA_HELPERS) on them in the verifier's python3 (numpy 1.26) after Scene.load.
import json as _json
import re
import sys as _sys, os as _os, array as _arr
CFG = _json.loads(__CFG__)
_argv = _sys.argv[_sys.argv.index('--') + 1:] if '--' in _sys.argv else []
_RAWDIR = (_argv[0] if _argv else '/tmp/bld_extract.json') + '.raw'
_os.makedirs(_RAWDIR, exist_ok=True)
_RAWN = [0]
def _dump(a):
    k = 'b%06d.bin' % _RAWN[0]; _RAWN[0] += 1
    with open(_os.path.join(_RAWDIR, k), 'wb') as fh:
        a.tofile(fh)
    return [k, a.typecode, len(a)]
def _buf(tc, n):
    return _arr.array(tc, bytes(_arr.array(tc).itemsize * n))
def _coll(cn):
    c = bpy.data.collections.get(cn)
    return list(c.all_objects) if c else []
def _mat(m):
    return [[round(m[i][j], 6) for j in range(4)] for i in range(4)]
def _W(mw):
    return [[float(mw[i][j]) for j in range(4)] for i in range(4)]
def _xf(pts, M):
    (a0, a1, a2, a3), (b0, b1, b2, b3), (c0, c1, c2, c3) = M[0], M[1], M[2]
    return [(a0*x + a1*y + a2*z + a3, b0*x + b1*y + b2*z + b3, c0*x + c1*y + c2*z + c3) for (x, y, z) in pts]
def _co(me):
    n = len(me.vertices)
    a = _buf('f', n * 3)
    me.vertices.foreach_get('co', a)
    return [(a[3*i], a[3*i+1], a[3*i+2]) for i in range(n)]
def _ebb(ev, mw):
    # exact world AABB of the evaluated geometry (modifiers / GN / curves); None for empty geometry
    me = ev.to_mesh()
    try:
        if len(me.vertices) == 0:
            return None
        w = _xf(_co(me), _W(mw))
        return [[round(min(p[k] for p in w), 5) for k in range(3)], [round(max(p[k] for p in w), 5) for k in range(3)]]
    finally:
        ev.to_mesh_clear()
scene.frame_set(1)
_dg = bpy.context.evaluated_depsgraph_get()
F1 = {}
for ob in scene.objects:
    try:
        ev = ob.evaluated_get(_dg)
        mw = ev.matrix_world
        d = {'mw': _mat(mw)}
        if ob.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            try:
                d['bb'] = _ebb(ev, mw)
            except Exception:
                pts = [mw @ Vector(c) for c in ev.bound_box]
                d['bb'] = [[round(min(p[i] for p in pts), 5) for i in range(3)], [round(max(p[i] for p in pts), 5) for i in range(3)]]
        F1[ob.name] = d
    except Exception as e:
        F1[ob.name] = {'err': str(e)[:200]}
EXTRA['f1'] = F1

def _local(ob, cap, boundary=False):
    # frame-1 local vertices, subsampled to ~cap (boundary-edge vertices kept first when boundary=True)
    ev = ob.evaluated_get(_dg)
    me = ev.to_mesh()
    bidx = None
    try:
        n = len(me.vertices)
        if n == 0:
            return [], []
        a = _co(me)
        if boundary and n > cap:
            ne = len(me.edges)
            ek = _buf('i', len(me.loops))
            me.loops.foreach_get('edge_index', ek)
            fc = [0] * ne
            for k in ek:
                fc[k] += 1
            ev_ = _buf('i', ne * 2)
            me.edges.foreach_get('vertices', ev_)
            bs = set()
            for e in range(ne):
                if fc[e] == 1:
                    bs.add(ev_[2*e]); bs.add(ev_[2*e+1])
            bidx = sorted(bs)
    finally:
        ev.to_mesh_clear()
    if n > cap:
        idx = set()
        if bidx:
            idx.update(bidx[::max(1, len(bidx) // (cap // 2))])
        idx.update(range(0, n, max(1, n // cap)))
        for k in range(3):
            col = [p[k] for p in a]
            idx.add(col.index(min(col))); idx.add(col.index(max(col)))
        a = [a[i] for i in sorted(idx)]
    return a, []

def _world(a, mw):
    return _xf(a, _W(mw))

# --- vertices for lake / bridges / selected paths (frame 1) ---
VX = {}
_vobs = []
_l01 = set(o.name for o in _coll('L01'))
for cn in ('L01', 'B01', 'B02'):
    _vobs += _coll(cn)
for nm in ('PATH_E02', 'PATH_E08', 'PATH_E09'):
    o = bpy.data.objects.get(nm)
    if o is not None:
        _vobs.append(o)
for ob in _vobs:
    if ob.type not in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT') or ob.name in VX:
        continue
    try:
        a, _t = _local(ob, 6000, boundary=ob.name in _l01)
        VX[ob.name] = [[round(c, 3) for c in p] for p in _world(a, ob.evaluated_get(_dg).matrix_world)]
    except Exception as e:
        VX[ob.name] = 'err ' + str(e)[:120]
EXTRA['verts'] = VX

# --- G11 walkable flood fill (frame 1) ---
try:
    tris = []
    wob = [o for o in _coll('SITE') if re.match(r'^(PATH_|SPUR_)', o.name)]
    for cn in ('B01', 'B02', 'L01'):
        wob += _coll(cn)
    for ob in wob:
        if ob.type not in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            continue
        ev = ob.evaluated_get(_dg)
        me = ev.to_mesh()
        try:
            me.calc_loop_triangles()
            mw = ev.matrix_world
            V = [tuple(mw @ v.co) for v in me.vertices]
            for t in me.loop_triangles:
                i, j, k = t.vertices
                tris.append((V[i], V[j], V[k]))
        finally:
            ev.to_mesh_clear()
    targets = {}
    for rid in CFG['rides']:
        o = bpy.data.objects.get(rid + '_ENTRY')
        targets[rid] = tuple(o.matrix_world.translation)[:2] if o else None
    targets['island'] = (0.0, 20.0)
    EXTRA['g11'] = _flood(tris, CFG['start'], targets)
except Exception:
    import traceback as _tb
    EXTRA['g11'] = {'error': _tb.format_exc()[-600:]}

RAW = {'dir': _RAWDIR}
# --- G12 swept envelopes: collect frame-1 local vertices + per-frame world matrices (sweep is done by _post_raw) ---
try:
    G12R = {}
    for rid in CFG['rides']:
        names, blobs = [], []
        for ob in _coll(rid):
            if ob.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT') and not ob.hide_render:
                try:
                    a, _t = _local(ob, 3000)
                    if len(a):
                        names.append(ob.name)
                        blobs.append(_dump(_arr.array('d', [c for p in a for c in p])))
                except Exception:
                    pass
        G12R[rid] = {'names': names, 'local': blobs, 'mats': []}
    nfr = 0
    for f in range(1, 721, 6):
        scene.frame_set(f)
        dg2 = bpy.context.evaluated_depsgraph_get()
        nfr += 1
        for rid, R in G12R.items():
            if R['names']:
                R['mats'].append([_W(bpy.data.objects[nm].evaluated_get(dg2).matrix_world) for nm in R['names']])
    scene.frame_set(1)
    RAW['g12'] = {'rides': G12R, 'frames': nfr}
except Exception:
    import traceback as _tb
    RAW['g12'] = {'error': _tb.format_exc()[-600:]}

# --- discrete features of park units (G01-G05, M12): evaluated world triangles at frame 1, incl. instanced geometry ---
try:
    _own = {}
    for cn in CFG['units']:
        c = bpy.data.collections.get(cn)
        if c:
            for o in c.all_objects:
                _own.setdefault(o.name, cn)
    scene.frame_set(1)
    _dg3 = bpy.context.evaluated_depsgraph_get()
    _acc = {cn: [] for cn in CFG['units']}
    _derr = []
    for oi in _dg3.object_instances:
        try:
            owner = oi.parent if oi.is_instance else oi.object
            on = owner.original.name if owner is not None else None
            cn = _own.get(on)
            if cn is None or owner.original.hide_render:
                continue
            ob = oi.object
            if ob.type not in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
                continue
            M = _W(oi.matrix_world)
            mats = [(sl.material.name if sl.material else '') for sl in ob.material_slots]
            me = ob.to_mesh()
            try:
                n = len(me.vertices)
                if n == 0:
                    continue
                co = _buf('f', n*3)
                me.vertices.foreach_get('co', co)
                me.calc_loop_triangles()
                nt = len(me.loop_triangles)
                tv = _buf('i', nt*3)
                me.loop_triangles.foreach_get('vertices', tv)
                mi = _buf('i', nt)
                me.loop_triangles.foreach_get('material_index', mi)
                ne = len(me.edges)
                evv = _buf('i', ne*2)
                me.edges.foreach_get('vertices', evv)
                if not mats:
                    mats = [(mm_.name if mm_ else '') for mm_ in me.materials]
            finally:
                ob.to_mesh_clear()
            _acc[cn].append({'M': M, 'mats': mats, 'n': n, 'co': _dump(co), 'tv': _dump(tv), 'mi': _dump(mi),
                             'ev': _dump(evv)})
        except Exception as e:
            _derr.append(str(e)[:120])
    RAW['disc'] = {'acc': _acc, 'errors': _derr}
except Exception:
    import traceback as _tb
    RAW['disc'] = {'error': _tb.format_exc()[-600:]}
scene.frame_set(1)
EXTRA['_raw'] = RAW
'''


def _post_raw(ex, A):
    # Real-image fix (2026-10-25): second stage of the extraction, run in the verifier's python3 (numpy available).
    # Reproduces the former in-Blender numpy code of the G12 sweep and the DISC measurement on the raw arrays
    # collected by EXTRA_DRIVER; results land in ex['g12'] / ex['disc'] exactly as before.
    R = ex.pop('_raw', None)
    if not isinstance(R, dict):
        return
    import os as _os
    import numpy as np
    CFG = g12_cfg(A)
    HG = {}
    exec(EXTRA_HELPERS, HG)
    try:
        from scipy.spatial import cKDTree as _KD

        def _min_pair(A_, B_):   # nearest-neighbour min distance (was mathutils.kdtree inside Blender)
            A_ = np.asarray(A_, dtype=np.float64)[:, :2]; B_ = np.asarray(B_, dtype=np.float64)[:, :2]
            if not len(A_) or not len(B_):
                return 1e9
            return float(_KD(B_).query(A_, k=1)[0].min())
        HG['_min_pair'] = _min_pair
    except Exception:
        pass
    D = R.get('dir') or ''

    def ld(b):
        k, tc, n = b
        a = np.fromfile(_os.path.join(D, k), dtype={'d': np.float64, 'f': np.float32, 'i': np.int32}[tc])
        if len(a) != n:
            raise ValueError('raw blob %s: %d of %d values' % (k, len(a), n))
        return a

    def _world(a, M):
        M = np.array(M, dtype=np.float64)
        return a @ M[:3, :3].T + M[:3, 3]

    # ---- G12
    try:
        g = R.get('g12') or {}
        if 'error' in g:
            raise RuntimeError(g['error'])
        rides = g['rides']
        LOC = {rid: [ld(b).reshape(-1, 3) for b in r['local']] for rid, r in rides.items()}
        ST = {rid: {'max_r': -1.0, 'max_z': -1e9, 'min_z': 1e9, 'n_pts': 0, 'xy': [], 'nxy': 0} for rid in CFG['rides']}
        for fi in range(g['frames']):
            for rid, L in LOC.items():
                if not L:
                    continue
                Ms = rides[rid]['mats'][fi]
                P = np.concatenate([_world(a, Ms[k]) for k, a in enumerate(L)])
                c = CFG['rides'][rid]
                s = ST[rid]
                s['max_r'] = max(s['max_r'], float(np.hypot(P[:, 0]-c['cx'], P[:, 1]-c['cy']).max()))
                s['max_z'] = max(s['max_z'], float(P[:, 2].max()))
                s['min_z'] = min(s['min_z'], float(P[:, 2].min()))
                s['n_pts'] += len(P)
                k = np.unique(np.round(P[:, :2] / 0.1).astype(np.int64), axis=0)
                s['xy'].append(k); s['nxy'] += len(k)
                if s['nxy'] > 1500000:
                    s['xy'] = [np.unique(np.concatenate(s['xy']), axis=0)]; s['nxy'] = len(s['xy'][0])
        swept = {}
        for rid, s in ST.items():
            if not s['n_pts']:
                swept[rid] = None
                continue
            s['xy'] = np.unique(np.concatenate(s['xy']), axis=0)
            swept[rid] = s
        out = HG['_g12_summarize'](swept, CFG)
        out['frames'] = g['frames']
        ex['g12'] = out
    except Exception:
        ex['g12'] = {'error': traceback.format_exc()[-600:]}

    # ---- DISC
    def _parts_of(nv, E):
        par = list(range(nv))

        def f(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        for a, b in E.tolist():
            ra, rb = f(a), f(b)
            if ra != rb:
                par[ra] = rb
        return np.array([f(i) for i in range(nv)], dtype=np.int64)
    DISC = {}
    try:
        dr = R.get('disc') or {}
        if 'error' in dr:
            raise RuntimeError(dr['error'])
        _derr = list(dr.get('errors') or [])
        _acc = {}
        for cn, lst in dr['acc'].items():
            L = []
            for e in lst:
                try:
                    n = e['n']
                    L.append((_world(ld(e['co']).astype(np.float64).reshape(n, 3), e['M']),
                              ld(e['tv']).reshape(-1, 3).astype(np.int64), ld(e['mi']), e['mats'], ld(e['ev']).reshape(-1, 2)))
                except Exception as x:
                    _derr.append(str(x)[:120])
            _acc[cn] = L
        for cn, lst in _acc.items():
            if not lst:
                DISC[cn] = {'err': 'no evaluated geometry'}
                continue
            try:
                Vs, Ts, Ms, Ps, Pvs = [], [], [], [], []
                off = poff = 0
                mname = {}
                for (Wv, Tt, mi, mats, E) in lst:
                    n = len(Wv)
                    pv = _parts_of(n, E) if n <= 200000 else np.zeros(n, dtype=np.int64)
                    pv = np.unique(pv, return_inverse=True)[1].reshape(-1)
                    lab = np.array([mname.setdefault(mats[i] if i < len(mats) else '', len(mname)) for i in range(max(len(mats), 1))])
                    Vs.append(Wv); Ts.append(Tt + off)
                    Ms.append(lab[np.clip(mi, 0, len(lab) - 1)])
                    Pvs.append(pv + poff); Ps.append(pv[Tt[:, 0]] + poff if len(Tt) else np.zeros(0, dtype=np.int64))
                    off += n; poff += int(pv.max()) + 1
                DISC[cn] = HG['_disc_unit'](cn, np.concatenate(Vs), np.concatenate(Ts), np.concatenate(Ms), np.concatenate(Ps),
                                            np.concatenate(Pvs), CFG['units'][cn])
            except Exception:
                DISC[cn] = {'err': traceback.format_exc()[-500:]}
        if _derr:
            DISC['_errors'] = _derr[:20]
    except Exception:
        DISC['_error'] = traceback.format_exc()[-600:]
    ex['disc'] = DISC


DISC_UNITS = ['G01', 'V01', 'F01', 'M01', 'K01', 'K02', 'K03', 'K04', 'B01', 'B02', 'P01', 'H01']


def g12_cfg(A):
    rides = {}
    paths = []
    for rid in RIDES:
        u = A['units'][rid]
        rides[rid] = {'cx': u['position']['x'], 'cy': u['position']['y'], 'R': u['envelope_R_m'], 'H': u['envelope_H_m']}
        s = u['spur']
        paths.append({'id': 'SPUR_' + rid, 'kind': 'segment', 'x1': s['x1'], 'y1': s['y1'], 'x2': s['x2'], 'y2': s['y2'],
                      'w': s['width'], 'own': rid})
    for p in A['paths']:
        if p['kind'] == 'ring':
            paths.append({'id': p['id'], 'kind': 'ring', 'cx': p['cx'], 'cy': p['cy'], 'r': p['r'], 'w': p['width']})
        else:
            paths.append({'id': p['id'], 'kind': 'segment', 'x1': p['x1'], 'y1': p['y1'], 'x2': p['x2'], 'y2': p['y2'], 'w': p['width']})
    paths.append({'id': 'B01_deck', 'kind': 'segment', 'x1': 0, 'y1': -6, 'x2': 0, 'y2': 10, 'w': A['units']['B01']['params']['deck_width_m']})
    paths.append({'id': 'B02_deck', 'kind': 'segment', 'x1': 0, 'y1': 30, 'x2': 0, 'y2': 46, 'w': A['units']['B02']['params']['deck_width_m']})
    units = {}
    for uid in DISC_UNITS:
        u = A['units'][uid]
        units[uid] = {'x': u['position']['x'], 'y': u['position']['y'], 'rot': u['position']['rot_deg'], 'kind': u['kind'],
                      'p': u['params']}
    return {'rides': rides, 'paths': paths, 'start': [0.0, -119.0], 'units': units}


def build_extra(A):
    cfg = json.dumps(g12_cfg(A))
    return EXTRA_HELPERS + '\n' + EXTRA_DRIVER.replace('__CFG__', repr(cfg))


# ----------------------------------------------------------------------------------------------
# small linear algebra (pure python)
# ----------------------------------------------------------------------------------------------
def rot(m):
    return [[m[i][j] for j in range(3)] for i in range(3)]


def tr(R):
    return [[R[j][i] for j in range(3)] for i in range(3)]


def mm(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mv(A, v):
    return [sum(A[i][k] * v[k] for k in range(3)) for i in range(3)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    n = norm(a)
    return [x / n for x in a] if n > 1e-12 else a


def ortho(R):
    """normalise columns (removes object scale)."""
    cols = [unit([R[0][j], R[1][j], R[2][j]]) for j in range(3)]
    return [[cols[j][i] for j in range(3)] for i in range(3)]


def ang_about(Rrel, axis):
    axis = unit(axis)
    u = cross(axis, [0, 0, 1])
    if norm(u) < 1e-6:
        u = cross(axis, [1, 0, 0])
    u = unit(u)
    v = mv(Rrel, u)
    v = [v[i] - axis[i] * dot(v, axis) for i in range(3)]
    return math.degrees(math.atan2(dot(axis, cross(u, v)), dot(u, v)))


def wrap(d):
    return (d + 180.0) % 360.0 - 180.0


def solve3(A, b):
    det = (A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1]) - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
           + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]))
    if abs(det) < 1e-12:
        return None
    out = []
    for c in range(3):
        M = [row[:] for row in A]
        for r in range(3):
            M[r][c] = b[r]
        d = (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
             + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
        out.append(d / det)
    return out


def fixed_axis(m1, mf, near):
    """Rotation axis (point, dir) of rigid motion mf*m1^-1; point = closest axis point to `near`."""
    R1, Rf = ortho(rot(m1)), ortho(rot(mf))
    R = mm(Rf, tr(R1))
    t1 = [m1[i][3] for i in range(3)]
    tf = [mf[i][3] for i in range(3)]
    t = [tf[i] - mv(R, t1)[i] for i in range(3)]
    ax = [R[2][1] - R[1][2], R[0][2] - R[2][0], R[1][0] - R[0][1]]
    if norm(ax) < 1e-4:
        return None
    a = unit(ax)
    # (I-R)p = t  and  a.p = a.near  -> normal equations
    IR = [[(1.0 if i == j else 0.0) - R[i][j] for j in range(3)] for i in range(3)]
    rows = IR + [a]
    rhs = t + [dot(a, near)]
    AtA = [[sum(rows[k][i] * rows[k][j] for k in range(4)) for j in range(3)] for i in range(3)]
    Atb = [sum(rows[k][i] * rhs[k] for k in range(4)) for i in range(3)]
    p = solve3(AtA, Atb)
    return (p, a) if p else None


def dist_line(q, p, a):
    d = [q[i] - p[i] for i in range(3)]
    c = cross(d, unit(a))
    return norm(c)


# ----------------------------------------------------------------------------------------------
# PNG statistics without numpy
# ----------------------------------------------------------------------------------------------
def png_std(path):
    try:
        from PIL import Image, ImageStat
        im = Image.open(path).convert('L')
        return ImageStat.Stat(im).stddev[0]
    except ImportError:
        pass
    data = open(path, 'rb').read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    pos, idat, hdr = 8, [], None
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            hdr = struct.unpack('>IIBBBBB', body)
        elif typ == b'IDAT':
            idat.append(body)
        pos += 12 + ln
    w, h, bd, ct, _, _, il = hdr
    if il:
        return None
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    bpp = max(1, ch * bd // 8)
    stride = (w * ch * bd + 7) // 8
    raw = zlib.decompress(b''.join(idat))
    prev = bytearray(stride)
    vals = []
    step_r = max(1, h // 120)
    step_c = max(1, w // 160)
    for y in range(h):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                line[i] = (line[i] + ((line[i - bpp] if i >= bpp else 0) + prev[i]) // 2) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        prev = line
        if y % step_r:
            continue
        sz = bd // 8 if bd >= 8 else 1
        for x in range(0, w, step_c):
            o = x * ch * sz
            px = [line[o + k * sz] for k in range(min(ch, 3))]
            vals.append(sum(px) / len(px))
    n = len(vals)
    m = sum(vals) / n
    return math.sqrt(sum((v - m) ** 2 for v in vals) / n)


# ----------------------------------------------------------------------------------------------
class World:
    def __init__(self, S, A, ctx):
        self.S, self.A, self.ctx = S, A, ctx
        d = S.data or {}
        self.ex = d.get('extra') or {}
        self.f1 = self.ex.get('f1') or {}
        self.anim = d.get('anim') or {}
        self.animset = set(d.get('anim_objects') or [])
        self.U = A['units']
        self.meas = {}          # unit -> measured params (for M10)
        self._cache = {}

    # ---- object access ----
    def has(self, n):
        return n in self.S.objects

    def typ(self, n):
        return (self.S.objects.get(n) or {}).get('type')

    def bb(self, n):
        f = self.f1.get(n) or {}
        if 'bb' in f:
            return f['bb']
        o = self.S.objects.get(n) or {}
        return o.get('bbox_world') if o.get('type') in GEOM else None

    def mw(self, n, f=1):
        a = self.anim.get(str(f), {})
        if n in a:
            return a[n]
        if (self.f1.get(n) or {}).get('mw'):
            return self.f1[n]['mw']
        return (self.S.objects.get(n) or {}).get('matrix_world')

    def loc(self, n, f=1):
        m = self.mw(n, f)
        return [m[0][3], m[1][3], m[2][3]] if m else None

    def geoms(self, cn, renderable=True):
        out = []
        for n in self.S.coll(cn):
            o = self.S.objects.get(n) or {}
            if o.get('type') in GEOM and not (renderable and o.get('hide_render')):
                out.append(n)
        return out

    def union(self, names):
        bs = [self.bb(n) for n in names if self.bb(n)]
        if not bs:
            return None
        return [[min(b[0][i] for b in bs) for i in range(3)], [max(b[1][i] for b in bs) for i in range(3)]]

    def inst_in(self, cn):
        """instanced geometry (collection / geometry-nodes instances) whose instancer belongs to collection cn."""
        objs = set(self.S.coll(cn))
        return [i for i in ((self.S.data or {}).get('instances') or []) if i.get('instancer') in objs]

    def disc(self, uid):
        d = (self.ex.get('disc') or {}).get(uid)
        return d if isinstance(d, dict) else {'err': 'no discrete-feature data (%s)' % str((self.ex.get('disc') or {}).get('_error', ''))[-120:]}

    def statics(self, cn):
        return [n for n in self.geoms(cn) if n not in self.animset]

    def named(self, uid, kind):
        r = re.compile('^%s_%s\\d+$' % (uid, kind))
        return sorted(n for n in self.S.coll(uid) if r.match(n))

    # ---- ride frame ----
    def facing(self, rid):
        return self.U[rid]['position']['rot_deg']

    def fdir(self, rid, extra=0.0):
        a = math.radians(self.facing(rid) + extra)
        return [math.cos(a), math.sin(a), 0.0]

    def ride_center(self, rid):
        """candidate centers: MAIN frame-1 bbox centre, static-part bbox centre."""
        c = []
        b = self.bb(rid + '_MAIN')
        if b:
            c.append(Scene.center(b))
        s = self.union(self.statics(rid))
        if s:
            c.append(Scene.center(s))
        return c

    def best_center(self, rid, target=None):
        cs = self.ride_center(rid)
        if not cs:
            return None
        if target is None:
            return cs[0]
        return min(cs, key=lambda c: math.hypot(c[0] - target[0], c[1] - target[1]))

    def entry_az(self, rid):
        e = self.loc(rid + '_ENTRY')
        c = self.best_center(rid)
        if not e or not c:
            return None
        return math.degrees(math.atan2(e[1] - c[1], e[0] - c[0])) % 360

    # ---- kinematics ----
    def rrel(self, n, f):
        m1, mf = self.mw(n, 1), self.mw(n, f)
        return mm(ortho(rot(mf)), tr(ortho(rot(m1))))

    def main_angle(self, rid, f):
        k = TYPE_OF[rid]
        R = self.rrel(rid + '_MAIN', f)
        if k == 'FW':
            return ang_about(R, self.fdir(rid))
        return ang_about(R, [0, 0, 1])

    def swing(self, rid, f, n=None):
        R = self.rrel(n or rid + '_MAIN', f)
        d = mv(R, [0, 0, -1])
        ax = self.fdir(rid) if TYPE_OF[rid] == 'PS' else self.fdir(rid, 90)
        return math.degrees(math.atan2(dot(d, ax), -d[2]))

    def sub_rel(self, rid, f, sub=None, axis_world=(0, 0, 1)):
        mn, sn = rid + '_MAIN', sub or rid + '_SUB01'
        L1 = mm(tr(ortho(rot(self.mw(mn, 1)))), ortho(rot(self.mw(sn, 1))))
        Lf = mm(tr(ortho(rot(self.mw(mn, f)))), ortho(rot(self.mw(sn, f))))
        Sp = mm(Lf, tr(L1))
        a = mv(tr(ortho(rot(self.mw(mn, 1)))), list(axis_world))
        return ang_about(Sp, a)

    def lift(self, rid, f):
        n = rid + '_MAIN'
        b = self.bb(n)
        return b[0][2] + (self.mw(n, f)[2][3] - self.mw(n, 1)[2][3])

    def pivot(self, rid, f):
        n = rid + '_MAIN'
        b = self.bb(n)
        near = Scene.center(b) if b else self.loc(n)
        return fixed_axis(self.mw(n, 1), self.mw(n, f), near)


def need(W, names):
    miss = [n for n in names if not W.has(n)]
    if miss:
        raise KeyError('missing objects: ' + ', '.join(miss[:8]))


def angle_ok(meas, exp, tol=TOL_ANG):
    return abs(wrap(meas - exp)) <= tol


def boxsz(b):
    return Scene.size(b)


# ----------------------------------------------------------------------------------------------
# unit-level measurement (zones)
# ----------------------------------------------------------------------------------------------
def any_box(W, uid, pred):
    names = W.geoms(uid)
    boxes = [(n, W.bb(n)) for n in names if W.bb(n)]
    cb = W.union(names)
    if cb:
        boxes.append(('<collection>', cb))
    for n, b in boxes:
        try:
            if pred(b):
                return n, b
        except Exception:
            pass
    return None, None


def fp_match(L, Wd):
    def p(b):
        s = boxsz(b)
        a, c = sorted([s[0], s[1]]), sorted([L, Wd])
        return close(a[0], c[0]) and close(a[1], c[1])
    return p


def check_park(W, uid):
    """returns (ok, detail). Hypothesis-based: some object (or the whole collection) matches each dimension."""
    u = W.U[uid]
    P = u['params']
    pos = (u['position']['x'], u['position']['y'])
    names = W.geoms(uid)
    if not names:
        return False, f'{uid}: no renderable geometry'
    cb = W.union(names)
    k = u['kind']
    errs = []
    center = Scene.center(cb)
    meas = {}
    if k in ('V', 'K', 'H'):
        n, b = any_box(W, uid, fp_match(P['length_m'], P['width_m']))
        if not n:
            errs.append('footprint %sx%s not found (coll %s)' % (P['length_m'], P['width_m'], [round(x, 2) for x in boxsz(cb)[:2]]))
        else:
            center = Scene.center(b)
        n2, b2 = any_box(W, uid, lambda b: close(b[1][2], P['eave_height_m']))
        if not n2:
            errs.append('no part with top at eave %.2f' % P['eave_height_m'])
    elif k == 'G':
        n, b = any_box(W, uid, lambda b: close(max(boxsz(b)[:2]), P['width_m']))
        if not n:
            errs.append('no part with width %.1f' % P['width_m'])
        else:
            meas['width_m'] = max(boxsz(b)[:2])
        n2, _ = any_box(W, uid, lambda b: close(b[1][2], P['tower_height_m']))
        if not n2:
            errs.append('no part with top at tower height %.1f' % P['tower_height_m'])
    elif k == 'F':
        n, b = any_box(W, uid, lambda b: close(boxsz(b)[0], P['basin_diameter_m']) and close(boxsz(b)[1], P['basin_diameter_m']))
        if not n:
            errs.append('basin diameter %.1f not found' % P['basin_diameter_m'])
        else:
            meas['basin_diameter_m'] = max(boxsz(b)[:2])
    elif k == 'M':
        if not close(cb[1][2], P['height_m']):
            errs.append('height %.2f vs %.1f' % (cb[1][2], P['height_m']))
        meas['height_m'] = cb[1][2]
        n, b = any_box(W, uid, lambda b: close(boxsz(b)[0], P['base_m']) and close(boxsz(b)[1], P['base_m']))
        if not n:
            errs.append('base %.1f square not found' % P['base_m'])
    elif k == 'P':
        n, b = any_box(W, uid, lambda b: close(max(boxsz(b)[:2]), P['diameter_m']))
        if not n:
            errs.append('diameter %.1f not found' % P['diameter_m'])
        if not close(cb[1][2], P['height_m']):
            errs.append('total height %.2f vs %.1f' % (cb[1][2], P['height_m']))
    elif k == 'B':
        span = P['span_m']
        if uid == 'B01':
            n, b = any_box(W, uid, lambda b: close(boxsz(b)[1], span) and close(boxsz(b)[0], P['deck_width_m']))
        else:   # B02 width judged in G10 only
            n, b = any_box(W, uid, lambda b: close(boxsz(b)[1], span))
        if not n:
            errs.append('deck span %.0f%s not found' % (span, ' x %.1f' % P['deck_width_m'] if uid == 'B01' else ''))
        else:
            center = Scene.center(b)
    elif k == 'L':
        r = lake_measure(W)
        if r.get('err'):
            errs.append(r['err'])
        else:
            meas.update(r['meas'])
            center = r['center']
            if r['max_err'] > 0.5:
                errs.append('water outline radial error %.2f m > 0.5' % r['max_err'])
            if abs(r['level'] - P['water_level_m']) > 0.05:
                errs.append('water level %.3f vs %.2f' % (r['level'], P['water_level_m']))
    dpos = math.hypot(center[0] - pos[0], center[1] - pos[1])
    if dpos > TOL_POS:
        errs.append('plan centre (%.2f,%.2f) off by %.2f m' % (center[0], center[1], dpos))
    meas.update({'x': center[0], 'y': center[1]})
    W.meas.setdefault(uid, {}).update(meas)
    return (not errs), f'{uid}: ' + ('; '.join(errs) if errs else 'ok')


def lake_measure(W):
    P = W.U['L01']['params']
    a, b0 = P['semi_axis_x_m'], P['semi_axis_y_m']
    cx, cy = W.U['L01']['position']['x'], W.U['L01']['position']['y']
    VX = W.ex.get('verts') or {}
    best = None
    for n in W.geoms('L01'):
        bb = W.bb(n)
        if not bb:
            continue
        s = boxsz(bb)
        if s[2] < 0.3 and -0.7 <= bb[1][2] <= -0.1 and s[0] > 1.5 * a and s[1] > 1.5 * b0:
            if best is None or s[0] * s[1] > boxsz(W.bb(best))[0] * boxsz(W.bb(best))[1]:
                best = n
    if not best:
        return {'err': 'no flat water mesh (z≈-0.4, ~80x52) found in L01'}
    V = VX.get(best)
    if not isinstance(V, list) or not V:
        return {'err': f'no vertices exported for water object {best}'}
    bb = W.bb(best)
    level = bb[1][2]
    max_err = 0.0
    for k in range(16):
        th = math.radians(k * 22.5)
        cand = []
        for v in V:
            dx, dy = v[0] - cx, v[1] - cy
            r = math.hypot(dx, dy)
            if r < 1e-6:
                continue
            ph = math.atan2(dy, dx)
            if abs(wrap(math.degrees(ph - th))) <= 4.0:
                cand.append((r, ph))
        if not cand:
            return {'err': 'water outline: no vertex near direction %d°' % (k * 22.5)}
        r, ph = max(cand)
        re_ = 1.0 / math.sqrt((math.cos(ph) / a) ** 2 + (math.sin(ph) / b0) ** 2)
        max_err = max(max_err, abs(r - re_))
    return {'max_err': max_err, 'level': level, 'center': Scene.center(bb), 'meas': {'water_level_m': level}}


def check_ride(W, rid, judge_pos=True):
    u = W.U[rid]
    P = u['params']
    k = u['kind']
    pos = (u['position']['x'], u['position']['y'])
    mn = rid + '_MAIN'
    need(W, [mn])
    errs = []
    meas = W.meas.setdefault(rid, {})
    cs = W.ride_center(rid)
    c = W.best_center(rid, pos)
    meas['x'], meas['y'] = c[0], c[1]
    if judge_pos:
        d = min(math.hypot(q[0] - pos[0], q[1] - pos[1]) for q in cs)
        if d > TOL_POS:
            errs.append('centre off pad by %.2f m' % d)
    bm = W.bb(mn)
    sm = boxsz(bm)
    statics = W.union(W.statics(rid))
    if k == 'FW':
        perp = sm[1] if abs(math.cos(math.radians(W.facing(rid)))) > 0.5 else sm[0]
        dia = max(perp, sm[2])
        meas['diameter_m'] = dia
        if not close(dia, P['diameter_m']):
            errs.append('wheel dia %.2f vs %.1f' % (dia, P['diameter_m']))
        hz = [W.mw(mn, 1)[2][3]]
        fa = W.pivot(rid, 241)
        if fa:
            hz.append(fa[0][2])
        hz.append(Scene.center(bm)[2])
        hub = min(hz, key=lambda z: abs(z - P['hub_height_m']))
        meas['hub_height_m'] = hub
        if not close(hub, P['hub_height_m']):
            errs.append('hub z %s vs %.1f' % ([round(z, 2) for z in hz], P['hub_height_m']))
    elif k in ('CR', 'TC'):
        dia = max(sm[0], sm[1])
        key = 'diameter_m' if k == 'CR' else 'platter_diameter_m'
        meas[key] = dia
        if not close(dia, P[key]):
            errs.append('MAIN plan dia %.2f vs %.1f' % (dia, P[key]))
        if k == 'CR':
            top = W.union(W.geoms(rid))[1][2]
            if top > u['envelope_H_m'] + 0.05:
                errs.append('total height %.2f > envelope H %.1f' % (top, u['envelope_H_m']))
    elif k == 'PS':
        fa = W.pivot(rid, 61)
        if not fa:
            errs.append('cannot locate swing pivot (MAIN not animated?)')
        else:
            pz = fa[0][2]
            meas['pivot_height_m'] = pz
            arm = pz - bm[0][2]
            meas['arm_m'] = arm
            if not close(pz, P['pivot_height_m']):
                errs.append('pivot z %.2f vs %.1f' % (pz, P['pivot_height_m']))
            if not close(arm, P['arm_m']):
                errs.append('arm %.2f vs %.1f' % (arm, P['arm_m']))
        hl = sm[0] if abs(math.cos(math.radians(W.facing(rid)))) > 0.5 else sm[1]
        meas['hull_length_m'] = hl
        if not close(hl, P['hull_length_m']):
            errs.append('hull length %.2f vs %.1f' % (hl, P['hull_length_m']))
    elif k == 'CS':
        th = statics[1][2] if statics else None
        meas['tower_height_m'] = th
        if th is None or not close(th, P['tower_height_m']):
            errs.append('static tower top %s vs %.1f' % (th, P['tower_height_m']))
        seats = W.named(rid, 'SEAT')
        if not seats:
            errs.append('no SEAT objects')
        else:
            rs = [math.hypot(Scene.center(W.bb(s))[0] - c[0], Scene.center(W.bb(s))[1] - c[1]) for s in seats if W.bb(s)]
            exp = P['canopy_radius_m'] + P['chain_m'] * math.sin(math.radians(P['fly_angle_deg']))
            rm = sum(rs) / len(rs) if rs else 0
            if not close(rm, exp):
                errs.append('seat circle r %.2f vs %.2f' % (rm, exp))
    elif k == 'FB':
        fa = W.pivot(rid, 61)
        sub = rid + '_SUB01'
        if not fa or not W.bb(sub):
            errs.append('cannot locate pivot or disc SUB01')
        else:
            pz = fa[0][2]
            meas['pivot_height_m'] = pz
            sb = W.bb(sub)
            arms = [pz - sb[0][2], pz - sb[1][2], pz - Scene.center(sb)[2]]
            arm = min(arms, key=lambda x: abs(x - P['arm_m']))
            meas['arm_m'] = arm
            if not close(pz, P['pivot_height_m']):
                errs.append('pivot z %.2f vs %.1f' % (pz, P['pivot_height_m']))
            if not close(arm, P['arm_m']):
                errs.append('arm %.2f vs %.1f' % (arm, P['arm_m']))
            dd = max(boxsz(sb)[:2])
            if not close(dd, P['disc_diameter_m']):
                errs.append('disc dia %.2f vs %.1f' % (dd, P['disc_diameter_m']))
    elif k in ('DT', 'RT'):
        key = 'tower_height_m' if k == 'DT' else 'mast_height_m'
        th = statics[1][2] if statics else None
        meas[key] = th
        if th is None or not close(th, P[key]):
            errs.append('static tower top %s vs %.1f' % (th, P[key]))
        if k == 'DT':
            if abs(bm[0][2] - P['z_bottom_m']) > TOL_LIFT:
                errs.append('frame-1 gondola bottom %.2f vs %.1f' % (bm[0][2], P['z_bottom_m']))
        else:
            cd = max(sm[0], sm[1])
            if not close(cd, P['cabin_diameter_m']):
                errs.append('cabin dia %.2f vs %.1f' % (cd, P['cabin_diameter_m']))
    return (not errs), f'{rid}: ' + ('; '.join(errs) if errs else 'ok')


def zone_check(W, zone):
    z = next(x for x in W.A['zones'] if x['id'] == zone)
    msgs, good = [], True
    for uid in z['units']:
        if uid == 'K05':
            continue
        try:
            if uid in RIDES:
                o, m = check_ride(W, uid, judge_pos=uid not in ('R04', 'R10'))
            else:
                o, m = check_park(W, uid)
        except Exception as e:
            o, m = False, f'{uid}: error {e}'
        good &= o
        msgs.append(m)
    return (ok if good else bad)(' | '.join(msgs))


# ----------------------------------------------------------------------------------------------
# kinematics per ride (G06-G08)
# ----------------------------------------------------------------------------------------------
def kin_ride(W, rid, frames=SAMPLE):
    k = TYPE_OF[rid]
    ms = W.A['motion_samples'][rid]
    P = W.U[rid]['params']
    mn = rid + '_MAIN'
    need(W, [mn])
    errs = []
    for f in frames:
        e = ms[str(f)]
        if k in ('FW', 'CR', 'CS', 'TC'):
            a = W.main_angle(rid, f)
            if not angle_ok(a, e['main_angle_deg']):
                errs.append('f%d angle %.1f vs %.1f' % (f, a, wrap(e['main_angle_deg'])))
        if k == 'TC':
            s = W.sub_rel(rid, f)
            if not angle_ok(s, e['sub_rel_angle_deg']):
                errs.append('f%d sub %.1f vs %.1f' % (f, s, wrap(e['sub_rel_angle_deg'])))
        if k in ('PS', 'FB'):
            s = W.swing(rid, f)
            if abs(s - e['swing_angle_deg']) > TOL_ANG:
                errs.append('f%d swing %.1f vs %.1f' % (f, s, e['swing_angle_deg']))
        if k == 'FB':
            d = W.sub_rel(rid, f)
            if not angle_ok(d, e['disc_angle_deg']):
                errs.append('f%d disc %.1f vs %.1f' % (f, d, wrap(e['disc_angle_deg'])))
        if k == 'DT':
            z = W.lift(rid, f)
            if abs(z - e['gondola_z_m']) > TOL_LIFT:
                errs.append('f%d z %.2f vs %.2f' % (f, z, e['gondola_z_m']))
        if k == 'RT':
            z = W.lift(rid, f)
            if abs(z - e['cabin_z_m']) > TOL_LIFT:
                errs.append('f%d z %.2f vs %.2f' % (f, z, e['cabin_z_m']))
            a = W.main_angle(rid, f)
            if not angle_ok(a, e['spin_angle_deg']):
                errs.append('f%d spin %.1f vs %.1f' % (f, a, wrap(e['spin_angle_deg'])))
    if k == 'CR':
        h = rid + '_HORSE01'
        need(W, [h])
        A = P['bob_amp_m']
        dz = {f: W.mw(h, f)[2][3] - W.mw(h, 1)[2][3] for f in frames}
        fits = []
        for sgn in (1, -1):
            fits.append(max(abs(dz[f] - sgn * A * math.sin(math.radians(ms[str(f)]['horse_bob_phase_deg']))) for f in frames))
        if min(fits) > 0.1:
            errs.append('HORSE01 bob mismatch (max err %.2f m)' % min(fits))
    if k == 'CS':
        fa = P['fly_angle_deg']
        s1 = rid + '_SEAT01'
        need(W, [s1])
        c = W.best_center(rid, (W.U[rid]['position']['x'], W.U[rid]['position']['y']))
        for f in (1, 361):
            m = W.mw(s1, f)
            zc = unit([m[0][2], m[1][2], m[2][2]])
            tilt = math.degrees(math.acos(max(-1, min(1, zc[2]))))
            r = math.hypot(m[0][3] - c[0], m[1][3] - c[1])
            x = (r - P['canopy_radius_m']) / P['chain_m']
            pa = math.degrees(math.asin(max(-1, min(1, x))))
            if abs(tilt - fa) > TOL_ANG and abs(pa - fa) > TOL_ANG:
                errs.append('f%d seat fly angle tilt %.1f / radial %.1f vs %.0f' % (f, tilt, pa, fa))
    return (not errs), f'{rid}: ' + ('; '.join(errs[:6]) if errs else 'ok')


def direction(W, rid, what='main'):
    """sign of motion at frame 7 -> 'ccw'/'cw' (ccw positive per conventions)."""
    if what == 'main':
        a = W.main_angle(rid, 7)
    else:
        a = W.sub_rel(rid, 7)
    if abs(a) < 0.2:
        return None
    return 'ccw' if a > 0 else 'cw'


def kin_group(W, rids):
    msgs, good = [], True
    for rid in rids:
        try:
            if rid == 'R07':    # only direction and start pose; period judged in G10
                d = direction(W, rid)
                st = start_pose(W, rid)
                o = d == 'cw' and st[0]
                m = f'R07: direction {d}, start {st[1]}'
            else:
                o, m = kin_ride(W, rid)
        except Exception as e:
            o, m = False, f'{rid}: error {e}'
        good &= o
        msgs.append(m)
    return (ok if good else bad)(' | '.join(msgs))


def start_pose(W, rid):
    k = TYPE_OF[rid]
    P = W.U[rid]['params']
    mn = rid + '_MAIN'
    pos = (W.U[rid]['position']['x'], W.U[rid]['position']['y'])
    if k == 'FW':
        cars = W.named(rid, 'CAR')
        if not cars:
            return False, 'no CAR objects'
        zs = {c: W.mw(c, 1)[2][3] for c in cars}
        lo = min(zs.values())
        return (zs.get(rid + '_CAR01', 1e9) <= lo + 1e-3), 'CAR01 z %.2f, min %.2f' % (zs.get(rid + '_CAR01', float('nan')), lo)
    if k in ('CS', 'TC'):
        n = rid + ('_SEAT01' if k == 'CS' else '_SUB01')
        if not W.has(n):
            return False, f'{n} missing'
        c = W.best_center(rid, pos)
        b = W.bb(n)
        q = Scene.center(b) if b else W.loc(n)
        az = math.degrees(math.atan2(q[1] - c[1], q[0] - c[0]))
        return angle_ok(az, W.facing(rid)), '%s azimuth %.1f vs facing %.0f' % (n, az % 360, W.facing(rid))
    if k in ('DT', 'RT'):
        z = W.bb(mn)[0][2]
        return abs(z - P['z_bottom_m']) <= TOL_LIFT, 'MAIN bottom z %.2f vs %.1f' % (z, P['z_bottom_m'])
    if k in ('PS', 'FB'):
        fa = W.pivot(rid, 61)
        if not fa:
            return False, 'pivot not found'
        p = fa[0]
        tgt = W.bb(mn) if k == 'PS' else W.bb(rid + '_SUB01')
        if not tgt:
            return False, 'bob object missing'
        q = Scene.center(tgt)
        ax = W.fdir(rid) if k == 'PS' else W.fdir(rid, 90)
        off = (q[0] - p[0]) * ax[0] + (q[1] - p[1]) * ax[1]
        ang = math.degrees(math.atan2(off, p[2] - q[2]))
        return abs(ang) <= TOL_ANG, 'arm tilt %.1f°' % ang
    if k == 'CR':
        return True, 'no geometric zero reference (bob phase judged in G06/G08)'
    return True, ''


# ----------------------------------------------------------------------------------------------
# items
# ----------------------------------------------------------------------------------------------
def c_B01(W):
    s = (W.S.data or {}).get('scene') or {}
    e = []
    if s.get('unit_system') != 'METRIC':
        e.append('unit system %s' % s.get('unit_system'))
    if abs((s.get('scale_length') or 0) - 1.0) > 1e-6:
        e.append('scale %s' % s.get('scale_length'))
    if s.get('frame_start') != 1 or s.get('frame_end') != 720:
        e.append('frames %s-%s' % (s.get('frame_start'), s.get('frame_end')))
    if s.get('fps') != 24 or abs((s.get('fps_base') or 0) - 1.0) > 1e-6:
        e.append('fps %s/%s' % (s.get('fps'), s.get('fps_base')))
    return bad('; '.join(e)) if e else ok('metric, scale 1, 1-720, 24 fps (Blender %s)' % W.S.data.get('blender_version'))


def c_B02(W):
    e = []
    for uid in UNITS + ['SITE']:
        if not W.S.has_coll(uid):
            e.append(f'missing collection {uid}')
        elif uid not in ('K05', 'SITE') and not W.geoms(uid) and not W.inst_in(uid):
            e.append(f'{uid} has no renderable geometry')
    return bad('; '.join(e[:12])) if e else ok('26 unit collections + SITE, all built units have geometry')


def c_B03(W):
    e = []
    for rid in RIDES:
        for n in (rid + '_MAIN', rid + '_ENTRY'):
            if not W.has(n):
                e.append(f'{n} missing')
            elif n not in W.S.coll(rid):
                e.append(f'{n} not in {rid}')
        if W.has(rid + '_ENTRY') and W.typ(rid + '_ENTRY') != 'EMPTY':
            e.append(f'{rid}_ENTRY not EMPTY')
    for rid, kind in [('R01', 'CAR'), ('R07', 'CAR'), ('R02', 'HORSE'), ('R09', 'HORSE'), ('R05', 'SEAT'), ('R10', 'SEAT'),
                      ('R06', 'SUB'), ('R11', 'SUB'), ('R08', 'SUB')]:
        n = f'{rid}_{kind}01'
        if not W.has(n) or n not in W.S.coll(rid):
            e.append(f'{n} missing/not in {rid}')
    return bad('; '.join(e[:12])) if e else ok('all MAIN/ENTRY/CAR01/HORSE01/SEAT01/SUB01 present in own collections')


def ground_name(W):
    best, area = None, 0
    for n in W.geoms('SITE'):
        if re.match(r'^(PATH_|SPUR_)', n):
            continue
        b = W.bb(n)
        if not b:
            continue
        s = boxsz(b)
        if s[0] * s[1] > area and s[2] < 3.0:
            best, area = n, s[0] * s[1]
    return best, area


def c_B04(W):
    e = []
    site = set(W.S.coll('SITE'))
    for i in range(1, 12):
        n = 'PATH_E%02d' % i
        if n not in site:
            e.append(f'{n} not in SITE')
    for rid in RIDES:
        if 'SPUR_' + rid not in site:
            e.append(f'SPUR_{rid} not in SITE')
    g, area = ground_name(W)
    named = [n for n in W.geoms('SITE') if re.search(r'(?i)ground|terrain|grass|lawn|land|地面', n)]
    if not named and area < 150 * 150:
        e.append('no ground object in SITE (largest non-path plane %.0f m²)' % area)
    return bad('; '.join(e[:12])) if e else ok('ground (%s), PATH_E01-E11, 12 SPUR_* in SITE' % (named[0] if named else g))


def c_render(W, names):
    e, info = [], []
    for nm in names:
        p = pathlib.Path(W.ctx['out']) / 'renders' / nm
        if not p.exists():
            e.append(f'{nm} missing')
            continue
        sz = png_size(p)
        if sz != (1920, 1080):
            e.append(f'{nm} size {sz}')
            continue
        try:
            sd = png_std(p)
        except Exception as ex:
            sd = None
            e.append(f'{nm} decode error {ex}')
            continue
        if sd is None or sd <= 10:
            e.append(f'{nm} blank (std {sd})')
        else:
            info.append(f'{nm} std {sd:.1f}')
    return bad('; '.join(e)) if e else ok('; '.join(info))


def c_B07(W, man):
    if man is None:
        return bad('manifest.json missing or unparsable')
    if not isinstance(man, list):
        return bad('manifest is not an array')
    e = []
    ids = [m.get('id') for m in man if isinstance(m, dict)]
    if len(man) != 26 or sorted(ids) != sorted(UNITS):
        e.append('entries %d, ids mismatch: missing %s extra %s' % (len(man), sorted(set(UNITS) - set(ids)), sorted(set(ids) - set(UNITS))))
    for m in man:
        if not isinstance(m, dict) or m.get('id') not in TYPE_OF:
            continue
        uid = m['id']
        if m.get('collection') != uid:
            e.append(f'{uid} collection {m.get("collection")}')
        if m.get('type') != TYPE_OF[uid]:
            e.append(f'{uid} type {m.get("type")}')
        if m.get('built') is False:
            continue
        p = m.get('params')
        if not isinstance(p, dict):
            e.append(f'{uid} no params')
            continue
        req = FIELDS[TYPE_OF[uid]].split() + ['x', 'y', 'rot_deg']
        if TYPE_OF[uid] == 'K' and str(p.get('roof', '')).lower() == 'awning':
            req.append('awning_stripes')
        miss = [f for f in req if f not in p]
        if miss:
            e.append(f'{uid} missing {miss}')
    return bad('; '.join(e[:10])) if e else ok('26 entries, ids/collections/types/fields complete')


def c_B08(W):
    e = []
    for uid in UNITS:
        if uid == 'K05':
            continue
        b = W.union(W.geoms(uid))
        if not b:
            e.append(f'{uid} empty')
            continue
        if b[0][0] < -150 or b[1][0] > 150 or b[0][1] < -135 or b[1][1] > 140:
            e.append(f'{uid} outside site XY {[round(v, 1) for v in b[0][:2] + b[1][:2]]}')
        if not (-1.7 <= b[0][2] <= 0.3):
            e.append(f'{uid} lowest z {b[0][2]:.2f}')
    return bad('; '.join(e[:10])) if e else ok('all unit bboxes inside site, grounded at frame 1')


def c_M06(W):
    e = []
    for p in W.A['paths']:
        n = 'PATH_' + p['id']
        if not W.has(n) or not W.bb(n):
            e.append(f'{n} missing')
            continue
        b = W.bb(n)
        if not (0.0 <= b[1][2] <= 0.10):
            e.append(f'{n} top z {b[1][2]:.3f}')
        if p['kind'] == 'ring':
            V = (W.ex.get('verts') or {}).get(n)
            if not isinstance(V, list) or not V:
                e.append(f'{n} no vertices')
                continue
            rs = [math.hypot(v[0] - p['cx'], v[1] - p['cy']) for v in V]
            ri, ro = p['r'] - p['width'] / 2, p['r'] + p['width'] / 2
            if abs(min(rs) - ri) > 0.2 or abs(max(rs) - ro) > 0.2:
                e.append(f'{n} radii {min(rs):.2f}/{max(rs):.2f} vs {ri}/{ro}')
            continue
        vert = abs(p['x1'] - p['x2']) < 1e-6
        ax, cr = (1, 0) if vert else (0, 1)
        lo, hi = sorted([p['y1'], p['y2']] if vert else [p['x1'], p['x2']])
        c0 = p['x1'] if vert else p['y1']
        if abs(b[0][ax] - lo) > 0.5 or abs(b[1][ax] - hi) > 0.5:
            e.append(f'{n} ends {b[0][ax]:.2f}..{b[1][ax]:.2f} vs {lo}..{hi}')
        w = b[1][cr] - b[0][cr]
        if p['id'] != 'E09' and abs(w - p['width']) > 0.2:
            e.append(f'{n} width {w:.2f} vs {p["width"]}')
        if abs((b[0][cr] + b[1][cr]) / 2 - c0) > 0.2:
            e.append(f'{n} centreline offset {(b[0][cr] + b[1][cr]) / 2 - c0:.2f}')
    return bad('; '.join(e[:10])) if e else ok('PATH_E01-E11 centrelines/widths/levels match (E09 width excluded)')


def entry_spur(W, rid):
    u = W.U[rid]
    e = []
    en = rid + '_ENTRY'
    if not W.has(en):
        return [f'{en} missing']
    q = W.loc(en)
    ke = u['entry']
    if math.hypot(q[0] - ke['x'], q[1] - ke['y']) > 0.5 or abs(q[2] - ke['z']) > 0.1:
        e.append('%s at (%.2f,%.2f,%.2f) vs (%.1f,%.1f,%.2f)' % (en, q[0], q[1], q[2], ke['x'], ke['y'], ke['z']))
    sn = 'SPUR_' + rid
    b = W.bb(sn)
    if not b:
        return e + [f'{sn} missing']
    s = u['spur']
    vert = abs(s['x1'] - s['x2']) < 1e-6
    ax, cr = (1, 0) if vert else (0, 1)
    lo, hi = sorted([s['y1'], s['y2']] if vert else [s['x1'], s['x2']])
    c0 = s['x1'] if vert else s['y1']
    if abs(b[0][ax] - lo) > 0.5 or abs(b[1][ax] - hi) > 0.5:
        e.append(f'{sn} ends {b[0][ax]:.2f}..{b[1][ax]:.2f} vs {lo}..{hi}')
    w = b[1][cr] - b[0][cr]
    if abs(w - s['width']) > 0.2 or abs((b[0][cr] + b[1][cr]) / 2 - c0) > 0.3:
        e.append(f'{sn} width {w:.2f} / centre {(b[0][cr] + b[1][cr]) / 2:.2f} vs {s["width"]} / {c0}')
    return e


def c_M07(W):
    e = []
    for rid in RIDES:
        if rid in ('R04', 'R10'):
            continue
        e += entry_spur(W, rid)
    return bad('; '.join(e[:10])) if e else ok('10 ENTRY empties and spurs match answer key')


def c_M08(W):
    e = []
    for rid in RIDES:
        mn = rid + '_MAIN'
        if not W.has(mn):
            e.append(f'{mn} missing')
            continue
        ms = [W.mw(mn, f) for f in (1, 241, 481, 720)]
        flat = [[round(x, 4) for r in m for x in r] for m in ms]
        if all(fl == flat[0] for fl in flat):
            e.append(f'{rid} MAIN static at 1/241/481/720')
            continue
        o, d = start_pose(W, rid)
        if not o:
            e.append(f'{rid} start: {d}')
    return bad('; '.join(e[:10])) if e else ok('12 MAIN animated; frame-1 start poses correct')


def c_M09(W):
    e = []
    for rid in ('R01', 'R07'):
        P = W.U[rid]['params']
        cars = W.named(rid, 'CAR')
        if len(cars) != P['gondolas']:
            e.append(f'{rid} CAR count {len(cars)} vs {P["gondolas"]}')
            continue
        fa = W.pivot(rid, 241)
        hub = fa if fa else (W.loc(rid + '_MAIN'), W.fdir(rid))
        r = P['diameter_m'] / 2
        ds = [dist_line(W.loc(c, 1), hub[0], hub[1]) for c in cars]
        if max(abs(d - r) for d in ds) > 0.5:
            e.append(f'{rid} CAR to axis {min(ds):.2f}..{max(ds):.2f} vs {r}')
        # uniform spacing
        a = unit(hub[1])
        u0 = unit(cross(a, [0, 0, 1]))
        v0 = cross(a, u0)
        angs = sorted(math.degrees(math.atan2(dot([W.loc(c)[i] - hub[0][i] for i in range(3)], v0),
                                              dot([W.loc(c)[i] - hub[0][i] for i in range(3)], u0))) % 360 for c in cars)
        gaps = [(angs[(i + 1) % len(angs)] - angs[i]) % 360 for i in range(len(angs))]
        if max(abs(g - 360.0 / len(cars)) for g in gaps) > 3.0:
            e.append(f'{rid} CARs not evenly spaced (gaps {min(gaps):.1f}..{max(gaps):.1f})')
        worst = 0
        for f in (1, 181, 361, 541):
            for c in cars:
                m = W.mw(c, f)
                zc = unit([m[0][2], m[1][2], m[2][2]])
                worst = max(worst, math.degrees(math.acos(max(-1, min(1, zc[2])))))
        if worst > 5:
            e.append(f'{rid} gondola tilt up to {worst:.1f}°')
    return bad('; '.join(e)) if e else ok('R01 32 / R07 15 gondolas on rim, evenly spaced, upright at 1/181/361/541')


def predict(kind, period, direction, f):
    t = (f - 1) / 24.0
    s = 1 if direction == 'ccw' else -1
    return s * 360.0 * t / period


def c_M10(W, man):
    if man is None or not isinstance(man, list):
        return bad('manifest.json missing or unparsable')
    by = {m.get('id'): m for m in man if isinstance(m, dict)}
    e = []
    for uid in UNITS:
        m = by.get(uid)
        if not m:
            e.append(f'{uid} not declared')
            continue
        built_meas = bool(W.geoms(uid))
        if bool(m.get('built', True)) != built_meas:
            e.append(f'{uid} built={m.get("built")} but scene has {"" if built_meas else "no "}geometry')
            continue
        if not built_meas:
            continue
        p = m.get('params') or {}
        me = W.meas.get(uid, {})
        try:
            for key in ('x', 'y'):
                if key in me and key in p and abs(float(p[key]) - me[key]) > TOL_POS:
                    e.append(f'{uid}.{key} {p[key]} vs measured {me[key]:.2f}')
            if uid in RIDES:
                az = W.entry_az(uid)
                if az is not None and 'rot_deg' in p and not angle_ok(float(p['rot_deg']), az):
                    e.append(f'{uid}.rot_deg {p["rot_deg"]} vs measured {az:.1f}')
            for key, val in me.items():
                if key in ('x', 'y') or key not in p or val is None:
                    continue
                if not close(float(p[key]), val) and not (key.endswith('level_m') and abs(float(p[key]) - val) <= 0.05):
                    e.append(f'{uid}.{key} {p[key]} vs measured {val:.2f}')
            k = TYPE_OF[uid]
            if k == 'FW' and 'gondolas' in p and int(p['gondolas']) != len(W.named(uid, 'CAR')):
                e.append(f'{uid}.gondolas {p["gondolas"]} vs {len(W.named(uid, "CAR"))} CAR objects')
            if k == 'CR' and isinstance(p.get('horses_per_row'), list) and sum(p['horses_per_row']) != len(W.named(uid, 'HORSE')):
                e.append(f'{uid}.horses_per_row sum {sum(p["horses_per_row"])} vs {len(W.named(uid, "HORSE"))} HORSE objects')
            if k == 'CS' and 'seats' in p:
                n = len(W.named(uid, 'SEAT'))
                if int(p['seats']) not in (n, 2 * n):
                    e.append(f'{uid}.seats {p["seats"]} vs {n} SEAT objects')
            if k == 'TC' and 'sub_platters' in p and int(p['sub_platters']) != len(W.named(uid, 'SUB')):
                e.append(f'{uid}.sub_platters {p["sub_platters"]} vs {len(W.named(uid, "SUB"))} SUB objects')
            # motion declarations vs measured motion
            if k in ('FW', 'CR', 'CS') and 'period_s' in p and 'direction' in p:
                bad_f = [f for f in SAMPLE if not angle_ok(W.main_angle(uid, f), predict(k, float(p['period_s']), p['direction'], f), 3.0)]
                if bad_f:
                    e.append(f'{uid} period/direction {p["period_s"]}/{p["direction"]} inconsistent with motion (frames {bad_f[:3]})')
            if k == 'TC' and 'main_period_s' in p:
                md = direction(W, uid)
                sd = direction(W, uid, 'sub')
                bf = [f for f in SAMPLE if not angle_ok(W.main_angle(uid, f), predict(k, float(p['main_period_s']), md, f), 3.0)
                      or not angle_ok(W.sub_rel(uid, f), predict(k, float(p['sub_period_s']), sd, f), 3.0)]
                if bf:
                    e.append(f'{uid} main/sub periods inconsistent with motion (frames {bf[:3]})')
            if k in ('PS', 'FB') and 'period_s' in p and 'amplitude_deg' in p:
                bf = [f for f in SAMPLE if abs(W.swing(uid, f) - float(p['amplitude_deg']) * math.sin(2 * math.pi * (f - 1) / 24.0 / float(p['period_s']))) > 3.0]
                if bf:
                    e.append(f'{uid} amplitude/period inconsistent with swing (frames {bf[:3]})')
            if k == 'FB' and 'disc_period_s' in p:
                bf = [f for f in SAMPLE if not angle_ok(W.sub_rel(uid, f), predict(k, float(p['disc_period_s']), p.get('disc_direction'), f), 3.0)]
                if bf:
                    e.append(f'{uid} disc period/direction inconsistent (frames {bf[:3]})')
            if k == 'RT' and 'spin_period_s' in p:
                bf = [f for f in SAMPLE if not angle_ok(W.main_angle(uid, f), predict(k, float(p['spin_period_s']), p.get('spin_direction'), f), 3.0)]
                if bf:
                    e.append(f'{uid} spin period/direction inconsistent (frames {bf[:3]})')
            if k == 'CS' and 'fly_angle_deg' in p:
                s1 = uid + '_SEAT01'
                if W.has(s1):
                    m1 = W.mw(s1, 1)
                    zc = unit([m1[0][2], m1[1][2], m1[2][2]])
                    tilt = math.degrees(math.acos(max(-1, min(1, zc[2]))))
                    c = W.best_center(uid, (W.U[uid]['position']['x'], W.U[uid]['position']['y']))
                    r = math.hypot(m1[0][3] - c[0], m1[1][3] - c[1])
                    P = W.U[uid]['params']
                    pa = math.degrees(math.asin(max(-1, min(1, (r - P['canopy_radius_m']) / P['chain_m']))))
                    if abs(float(p['fly_angle_deg']) - tilt) > 2 and abs(float(p['fly_angle_deg']) - pa) > 2:
                        e.append(f'{uid}.fly_angle_deg {p["fly_angle_deg"]} vs measured {tilt:.1f}/{pa:.1f}')
        except Exception as ex:
            e.append(f'{uid} compare error {ex}')
    return bad('; '.join(e[:10])) if e else ok('manifest consistent with all measured quantities')


def island_obj(W):
    isl = None
    for n in W.geoms('L01'):
        b = W.bb(n)
        if not b:
            continue
        c = Scene.center(b)
        s = boxsz(b)
        if math.hypot(c[0], c[1] - 20) < 1.0 and 15 < s[0] < 25 and 15 < s[1] < 25:
            isl = (n, b)
            if abs(s[0] / 2 - 10) <= 0.3 and abs(s[1] / 2 - 10) <= 0.3 and abs(b[1][2] - 0.05) <= 0.05:
                break
    return isl


def c_M11(W):
    e = []
    isl = island_obj(W)
    if not isl:
        e.append('island mesh (r≈10 at (0,20)) not found in L01')
    else:
        b = isl[1]
        s = boxsz(b)
        if abs(s[0] / 2 - 10) > 0.3 or abs(s[1] / 2 - 10) > 0.3 or abs(b[1][2] - 0.05) > 0.05:
            e.append('island %s r %.2f/%.2f top %.3f' % (isl[0], s[0] / 2, s[1] / 2, b[1][2]))
        W.meas.setdefault('L01', {})['island_radius_m'] = (s[0] + s[1]) / 4
    for uid, (y0, y1) in (('B01', (-6, 10)), ('B02', (30, 46))):
        n, b = any_box(W, uid, lambda b: abs(b[0][1] - y0) <= 0.3 and abs(b[1][1] - y1) <= 0.3 and abs(Scene.center(b)[0]) <= 0.3)
        if not n:
            cb = W.union(W.geoms(uid))
            e.append(f'{uid} deck y-range {[round(cb[0][1], 2), round(cb[1][1], 2)] if cb else None} vs [{y0},{y1}]')
    return bad('; '.join(e)) if e else ok('island r10 top +0.05; B01 y[-6,10], B02 y[30,46], axis x=0')


FEAT = re.compile(r'(?i)(window|win_|_win|door|counter|serv|shop|hatch|awning|entr|portal|facade|front|terrace|deck|arch|窗|门|平台)')


def facade_dir(W, uid):
    u = W.U[uid]
    P = u['params']
    names = W.geoms(uid)
    if not names:
        return None, 'no geometry'
    n, body = any_box(W, uid, fp_match(P['length_m'], P['width_m'])) if 'length_m' in P else (None, None)
    bc = Scene.center(body) if body else Scene.center(W.union(names))
    feats = [x for x in names if FEAT.search(x) and x != n]
    if feats:
        fc = Scene.center(W.union(feats))
        off = (fc[0] - bc[0], fc[1] - bc[1])
        if math.hypot(*off) > 0.2:
            return math.degrees(math.atan2(off[1], off[0])) % 360, 'named features %s' % feats[:3]
    cc = Scene.center(W.union(names))
    off = (cc[0] - bc[0], cc[1] - bc[1])
    if body and math.hypot(*off) > 0.3:
        return math.degrees(math.atan2(off[1], off[0])) % 360, 'protrusion offset'
    return None, 'undetermined'


def c_M12(W):
    e = []
    for rid in RIDES:
        if rid in ('R04', 'R10'):
            continue
        az = W.entry_az(rid)
        if az is None:
            e.append(f'{rid} MAIN/ENTRY missing')
        elif not angle_ok(az, W.facing(rid)):
            e.append(f'{rid} entry azimuth {az:.1f} vs {W.facing(rid)}')
    undetermined = []
    g = W.union(W.geoms('G01'))
    if g:
        s = boxsz(g)
        if s[0] < s[1]:
            e.append('G01 long axis not along X (south facade normal 270)')
    else:
        e.append('G01 empty')
    for uid in ('V01', 'H01', 'K01', 'K02', 'K03', 'K04'):
        d, how = facade_dir(W, uid)
        if d is None:
            sf = W.disc(uid).get('side_features') or {}
            if sf:
                best = max(sf.values())
                tops = [sd for sd, v in sf.items() if v == best]
                if best > 0 and len(tops) == 1:
                    d, how = (W.U[uid]['position']['rot_deg'] + float(tops[0])) % 360, 'facade features per side %s' % sf
        if d is None:
            undetermined.append(f'{uid}:{how}')
            continue
        if not angle_ok(d, W.U[uid]['position']['rot_deg'], 10.0):
            e.append(f'{uid} facade {d:.0f}° ({how}) vs {W.U[uid]["position"]["rot_deg"]}')
    if undetermined:
        e.append('main facade not identifiable (no door/window/terrace feature distinguishes one side): ' + ', '.join(undetermined))
    if e:
        return bad('; '.join(e[:10]))
    return ok('ride entries aligned ≤2°; building facades within 10°')


def rows_of(W, rid):
    hs = W.named(rid, 'HORSE')
    c = W.best_center(rid, (W.U[rid]['position']['x'], W.U[rid]['position']['y']))
    rs = sorted((math.hypot(Scene.center(W.bb(h))[0] - c[0], Scene.center(W.bb(h))[1] - c[1]) for h in hs if W.bb(h)), reverse=True)
    rows, cur = [], []
    for r in rs:
        if cur and cur[-1] - r > 0.5:
            rows.append(cur)
            cur = []
        cur.append(r)
    if cur:
        rows.append(cur)
    return [len(x) for x in rows]


def count_seats(W, rid):
    return len(W.named(rid, 'SEAT'))


def g_discrete(W, rids):
    """ride part of G03-G05 (counts by name prefix, horse rows, directions, first swing) -> list of errors."""
    e = []
    for rid in rids:
        P = W.U[rid]['params']
        k = TYPE_OF[rid]
        try:
            if k == 'FW':
                n = len(W.named(rid, 'CAR'))
                if n != P['gondolas']:
                    e.append(f'{rid} {n} CARs vs {P["gondolas"]}')
                d = direction(W, rid)
                if d != P['direction']:
                    e.append(f'{rid} direction {d} vs {P["direction"]}')
            elif k == 'CR':
                rw = rows_of(W, rid)
                if rw != P['horses_per_row']:
                    e.append(f'{rid} horse rows {rw} vs {P["horses_per_row"]}')
                d = direction(W, rid)
                if d != P['direction']:
                    e.append(f'{rid} direction {d} vs {P["direction"]}')
                o, m = kin_ride(W, rid, frames=[61, 133, 241])
                if not o and 'HORSE01' in m:
                    e.append(f'{rid} bob count/phase wrong')
            elif k == 'CS':
                n = count_seats(W, rid)
                if P['seats'] not in ((n, 2 * n) if P['seat_type'] == 'double' else (n,)):
                    e.append(f'{rid} {n} SEAT objects vs {P["seats"]} {P["seat_type"]} seats')
                d = direction(W, rid)
                if d != P['direction']:
                    e.append(f'{rid} direction {d} vs {P["direction"]}')
            elif k == 'TC':
                n = len(W.named(rid, 'SUB'))
                if n != P['sub_platters']:
                    e.append(f'{rid} {n} SUB vs {P["sub_platters"]}')
                d, sd = direction(W, rid), direction(W, rid, 'sub')
                if d != P['main_direction'] or sd != P['sub_direction']:
                    e.append(f'{rid} main/sub {d}/{sd} vs {P["main_direction"]}/{P["sub_direction"]}')
            elif k == 'PS':
                if W.swing(rid, 7) <= 0:
                    e.append(f'{rid} first swing not toward +X')
            elif k == 'FB':
                m = W.mw(rid + '_MAIN', 61)
                d = mv(W.rrel(rid + '_MAIN', 61), [0, 0, -1])
                if W.swing(rid, 7) <= 0 or abs(dot(d, W.fdir(rid))) > 0.1:
                    e.append(f'{rid} swing plane/first swing not YZ/+Y')
                if direction(W, rid, 'sub') != P['disc_direction']:
                    e.append(f'{rid} disc direction {direction(W, rid, "sub")} vs {P["disc_direction"]}')
            elif k == 'RT':
                if direction(W, rid) != P['spin_direction']:
                    e.append(f'{rid} spin {direction(W, rid)} vs {P["spin_direction"]}')
        except Exception as ex:
            e.append(f'{rid} error {ex}')
    return e


VARS = ('mat', 'part', 'depth', 'hole')


def _var_eq(d, n):
    """d: {variant: count}; returns the first variant whose count == n, else None."""
    for v in VARS:
        if (d or {}).get(v) == n:
            return v
    return None


def park_discrete(W, uid):
    """machine checks of the discrete sheet features of one park unit -> list of errors (empty = pass)."""
    P = W.U[uid]['params']
    k = W.U[uid]['kind']
    d = W.disc(uid)
    if d.get('err'):
        return [f'{uid}: not measurable ({str(d["err"])[-160:]})']
    e = []
    meas = W.meas.setdefault(uid, {})
    if k == 'G':
        if d.get('arches') != P['arches']:
            e.append('%s: %s through-openings at z=2.0 (gaps %s) vs %d arches' % (uid, d.get('arches'), d.get('arch_gaps'), P['arches']))
        else:
            meas['arches'] = P['arches']
        if d.get('towers') != P['towers']:
            e.append('%s: %s towers at z=%.1f (widths %s) vs %d' % (uid, d.get('towers'), 0.75 * P['tower_height_m'], d.get('tower_widths'), P['towers']))
        else:
            meas['towers'] = P['towers']
    elif k == 'F':
        if d.get('tiers') != P['tiers']:
            e.append('%s: %s basin tiers (levels z/area %s) vs %d' % (uid, d.get('tiers'), d.get('tier_levels'), P['tiers']))
        else:
            meas['tiers'] = P['tiers']
        if d.get('jets') != P['jets']:
            e.append('%s: %s ring jets vs %d' % (uid, d.get('jets'), P['jets']))
        else:
            meas['jets'] = P['jets']
    elif k == 'M':
        if d.get('tiers') != P['tiers']:
            e.append('%s: %s tapering tiers (z0,z1,size %s) vs %d' % (uid, d.get('tiers'), d.get('tier_sizes'), P['tiers']))
        else:
            meas['tiers'] = P['tiers']
        cl = d.get('clocks') or {}
        good = None
        for v in VARS:
            c = {sd: (cl.get(sd) or {}).get(v, 0) for sd in ('0', '90', '180', '270')}
            if c['90'] >= 1 and c['270'] >= 1 and c['0'] == 0 and c['180'] == 0:
                good = v
                break
        if P['clock_faces'] != 2 or not good:
            e.append('%s: clock faces on top tier by side E/N/W/S %s, expected one on N and S only' % (
                uid, {sd: cl.get(sd) for sd in ('0', '90', '180', '270')}))
        else:
            meas['clock_faces'] = 2
    elif k == 'B':
        posts = d.get('posts') or {}
        n = P['rail_posts_per_side']
        if not all((posts.get(sd) or {}).get('n') == n for sd in ('L', 'R')):
            e.append('%s: rail posts per side %s vs %d' % (uid, {sd: (posts.get(sd) or {}).get('n') for sd in ('L', 'R')}, n))
        else:
            meas['rail_posts_per_side'] = n
        rise = d.get('rise')
        if P['form'] == 'arch':
            if rise is None or not close(rise, P['rise_m']):
                e.append('%s: arch rise %s vs %.1f' % (uid, rise, P['rise_m']))
        else:
            if rise is None or rise > 0.15:
                e.append('%s: deck not flat (rise %s) for %s' % (uid, rise, P['form']))
            if d.get('piers') != P.get('piers'):
                e.append('%s: %s piers vs %s' % (uid, d.get('piers'), P.get('piers')))
    elif k == 'P':
        if d.get('sides') != P['sides']:
            e.append('%s: platform outline %s-sided (r %s) vs %d' % (uid, d.get('sides'), d.get('outline_r'), P['sides']))
        else:
            meas['sides'] = P['sides']
        if d.get('columns') != P['columns']:
            e.append('%s: %s columns vs %d' % (uid, d.get('columns'), P['columns']))
    if k in ('V', 'H', 'K'):
        w = d.get('windows') or {}
        rows = d.get('window_rows') or {}
        if k == 'V':
            exp = [P['bays']] * P['storeys']
            v = next((v for v in VARS if rows.get(v) == exp), None)
            if not v:
                e.append('%s: main-facade window rows %s vs %s' % (uid, rows, exp))
            else:
                meas['bays'], meas['storeys'] = P['bays'], P['storeys']
        else:
            exp = P['bays'] if k == 'H' else P['windows']
            if not _var_eq(w, exp):
                e.append('%s: main-facade windows %s vs %d' % (uid, w, exp))
            else:
                meas['bays' if k == 'H' else 'windows'] = exp
        if k == 'H':
            td = d.get('terrace_depth')
            if td is None or not close(td, P['terrace_depth_m']):
                e.append('%s: lakeside terrace depth %s vs %.1f' % (uid, td, P['terrace_depth_m']))
        if k == 'K' and P.get('roof') == 'awning':
            st = d.get('stripes') or {}
            if P['awning_stripes'] not in st.values():
                e.append('%s: awning stripes %s vs %d' % (uid, st, P['awning_stripes']))
            else:
                meas['awning_stripes'] = P['awning_stripes']
    return e


def g_park(W, uids):
    e = []
    for uid in uids:
        try:
            e += park_discrete(W, uid)
        except Exception as ex:
            e.append(f'{uid} error {ex}')
    return bad('; '.join(e[:8])) if e else ok('discrete features of %s match the sheets' % ', '.join(uids))


def g_zone(W, rids, parks):
    e = g_discrete(W, rids)
    for uid in parks:
        try:
            e += park_discrete(W, uid)
        except Exception as ex:
            e.append(f'{uid} error {ex}')
    return bad('; '.join(e[:8])) if e else ok('counts/directions of %s match the sheets' % ', '.join(rids + parks))


def c_G09(W):
    e = []
    for rid, pad in (('R04', 'PN2'), ('R10', 'PE4')):
        p = W.A['pads'][pad]
        if not W.has(rid + '_MAIN'):
            e.append(f'{rid}_MAIN missing')
            continue
        cs = W.ride_center(rid)
        d = min(math.hypot(c[0] - p['x'], c[1] - p['y']) for c in cs)
        if d > TOL_POS:
            e.append(f'{rid} centre {d:.2f} m from {pad}')
        az = W.entry_az(rid)
        if az is None or not angle_ok(az, p['facing_deg']):
            e.append(f'{rid} +X azimuth {az} vs {p["facing_deg"]}')
        e += entry_spur(W, rid)
    g, _ = ground_name(W)
    for n in W.geoms('SITE'):
        if n == g:
            continue
        b = W.bb(n)
        if b and b[0][0] < 62.5 and b[1][0] > 59.5 and b[0][1] < -24.5 and b[1][1] > -27.5 and b[1][2] > 0.02:
            s = boxsz(b)
            # walkway-like = PATH_/SPUR_ object or a strip (narrow side <= 3.5 m) at path level; ride pads / lawns are not
            if re.match(r'^(PATH_|SPUR_)', n) or (min(s[0], s[1]) <= 3.5 and b[1][2] <= 0.3):
                e.append(f'stale walkway {n} in old R04 spur zone')
    return bad('; '.join(e[:10])) if e else ok('R04@PN2, R10@PE4, entries/spurs rebuilt, no stale spur')


def c_G10(W, man):
    e = []
    try:
        for f, exp in ((241, -100.0), (481, -200.0), (487, -202.5)):
            a = W.main_angle('R07', f)
            if not angle_ok(a, exp):
                e.append(f'R07 f{f} angle {a:.1f} vs {exp}')
    except Exception as ex:
        e.append(f'R07 error {ex}')
    n, b = any_box(W, 'B02', lambda b: close(boxsz(b)[1], 16.0) and abs(boxsz(b)[0] - 5.0) <= 0.1)
    if not n:
        e.append('B02 deck 5.0 m wide not found')
    pb = W.bb('PATH_E09')
    if not pb or abs(boxsz(pb)[0] - 5.0) > 0.1:
        e.append('PATH_E09 width %s' % (round(boxsz(pb)[0], 3) if pb else None))
    if not W.S.has_coll('K05'):
        e.append('K05 collection missing')
    elif W.geoms('K05', renderable=False):
        e.append('K05 not empty')
    k5 = next((m for m in (man or []) if isinstance(m, dict) and m.get('id') == 'K05'), None)
    if not k5 or k5.get('built') is not False:
        e.append('manifest K05 built != false')
    return bad('; '.join(e)) if e else ok('R07 36 s, B02/E09 5.0 m, K05 cancelled')


def c_G11(W):
    g = W.ex.get('g11') or {}
    if not g or g.get('error'):
        return bad('flood fill unavailable: %s' % str(g.get('error'))[:300])
    e = []
    if not g.get('start_ok'):
        e.append('no walkable surface at gate passage (0,-119)')
    for rid in RIDES:
        q = W.loc(rid + '_ENTRY') if W.has(rid + '_ENTRY') else None
        ke = W.U[rid]['entry']
        if q is None or math.hypot(q[0] - ke['x'], q[1] - ke['y']) > 0.5:
            e.append(f'{rid}_ENTRY missing/off key')
        elif not g['reached'].get(rid):
            e.append(f'{rid} entry unreachable')
    if not g['reached'].get('island'):
        e.append('island centre unreachable')
    return bad('; '.join(e[:10])) if e else ok('gate connects to 12 entries + island (%d cells)' % g.get('n_reached_cells', 0))


def c_G12(W):
    g = W.ex.get('g12') or {}
    if not g or g.get('error'):
        return bad('sweep unavailable: %s' % str(g.get('error'))[:300])
    e = []
    for rid in RIDES:
        r = g['rides'].get(rid) or {}
        u = W.U[rid]
        if not r.get('n_pts'):
            e.append(f'{rid} no geometry swept')
            continue
        if r['max_r'] > u['envelope_R_m'] + 0.05:
            e.append(f'{rid} radius {r["max_r"]} > R {u["envelope_R_m"]}')
        if r['max_z'] > u['envelope_H_m'] + 0.05:
            e.append(f'{rid} height {r["max_z"]} > H {u["envelope_H_m"]}')
        if r['path_min'] < 1.5:
            e.append(f'{rid} {r["path_min"]} m to {r["path_min_id"]}')
    for p in g.get('pairs', []):
        if p['d'] < 3.0:
            e.append(f'{p["a"]}-{p["b"]} gap {p["d"]}')
    return bad('; '.join(e[:10])) if e else ok('envelopes respected over %s frames; min ride gap %s m' % (g.get('frames'), g.get('min_gap')))


def c_G13(W):
    VX = W.ex.get('verts') or {}
    e = []

    def pts(names):
        out = []
        for n in names:
            v = VX.get(n)
            if isinstance(v, list):
                out += v
        return out
    isl_top = None
    io = island_obj(W)
    if io:
        isl_top = io[1][1][2]
    else:   # fallback: median of near-surface vertices on the island disc (ignores lamps / trees / edging)
        isl = sorted(v[2] for v in pts(W.geoms('L01')) if math.hypot(v[0], v[1] - 20) <= 9.5 and -0.3 < v[2] < 0.5)
        isl_top = isl[len(isl) // 2] if isl else None
    for uid, w, ends in (('B01', 3.5, ((-6.0, 'PATH_E08', -1), (10.0, 'island', 1))),
                         ('B02', 5.0, ((30.0, 'island', -1), (46.0, 'PATH_E09', 1)))):
        # deck object = part spanning the bridge (y-extent ≈ 16 m, x-extent ≈ deck width); fallback: all parts that are
        # not posts/rails/lamps
        dn, _ = any_box(W, uid, lambda b: close(boxsz(b)[1], 16.0) and abs(boxsz(b)[0] - w) <= 0.5)
        if dn and dn != '<collection>':
            src = [dn]
        else:
            src = [n for n in W.geoms(uid) if not re.search(r'(?i)post|rail|balust|lamp|light|pier|abut|pile|column', n)]
        D = [v for v in pts(src) if abs(v[0]) <= w / 2 + 0.05 and v[2] >= -0.2]
        if not D:
            e.append(f'{uid} no deck vertices')
            continue
        for yend, other, sgn in ends:
            # deck end coordinate and deck top within 0.3 m of the end (rubric says 1 m; an arch deck rises ~0.3 m
            # within 1 m of its head, so 0.3 m is used to avoid false fails on the arch form required by the sheet)
            if sgn < 0:
                dend = min(v[1] for v in D)
                top = max(v[2] for v in D if v[1] <= dend + 0.3)
            else:
                dend = max(v[1] for v in D)
                top = max(v[2] for v in D if v[1] >= dend - 0.3)
            if other == 'island':
                oz = isl_top
                oend = 10.0 if sgn > 0 else 30.0
            else:
                O = VX.get(other)
                if not isinstance(O, list) or not O:
                    e.append(f'{other} vertices missing')
                    continue
                oz = max(v[2] for v in O)
                oend = max(v[1] for v in O) if sgn < 0 else min(v[1] for v in O)
            if oz is None:
                e.append(f'{uid} island surface not found')
                continue
            if abs(top - oz) > 0.05:
                e.append(f'{uid} end y{yend:.0f} deck top {top:.3f} vs {other} {oz:.3f}')
            gap = (dend - oend) if sgn < 0 else (oend - dend)
            if gap > 0.3:
                e.append(f'{uid} end y{yend:.0f} gap {gap:.2f} m to {other}')
    return bad('; '.join(e)) if e else ok('bridge heads flush (≤0.05) and gap ≤0.3 at all four ends')


# ----------------------------------------------------------------------------------------------
def run(ctx):
    res = {}
    A = ctx['answer']
    man = load_manifest(ctx['out'])
    # file-only items
    for iid, fn in (('B05', lambda: c_render(W0, ['overview.png'])), ('B06', lambda: c_render(W0, ['wing_east.png', 'lake.png'])),
                    ('B07', lambda: c_B07(W0, man))):
        try:
            W0 = type('W0', (), {'ctx': ctx})()
            res[iid] = fn()
        except Exception:
            res[iid] = bad('check error: ' + traceback.format_exc()[-300:])
    try:
        S = Scene.load(ctx, frames=FRAMES, extra_py=build_extra(A))
        if S.data and isinstance(S.data.get('extra'), dict):
            _post_raw(S.data['extra'], A)
    except Exception as ex:
        S = Scene(None, f'scene load error: {ex}')
    if S.err or not S.data:
        for iid in SCENE_ITEMS:
            res[iid] = bad(f'scene unavailable: {S.err}')
        return res
    W = World(S, A, ctx)
    plan = [('B01', c_B01), ('B02', c_B02), ('B03', c_B03), ('B04', c_B04), ('B08', c_B08),
            ('M01', lambda W: zone_check(W, 'A')), ('M02', lambda W: zone_check(W, 'B')), ('M03', lambda W: zone_check(W, 'C')),
            ('M04', lambda W: zone_check(W, 'D')), ('M05', lambda W: zone_check(W, 'E')),
            ('M06', c_M06), ('M07', c_M07), ('M08', c_M08), ('M09', c_M09), ('M11', c_M11), ('M12', c_M12),
            ('G01', lambda W: g_park(W, ['G01', 'V01', 'F01', 'M01', 'K01', 'K02'])),
            ('G02', lambda W: g_park(W, ['B01', 'B02', 'P01', 'H01'])),
            ('G03', lambda W: g_zone(W, ['R01', 'R02', 'R03', 'R10'], ['K03'])),
            ('G04', lambda W: g_zone(W, ['R05', 'R06', 'R07', 'R08'], ['K04'])),
            ('G05', lambda W: g_zone(W, ['R09', 'R11', 'R12'], [])),
            ('M10', lambda W: c_M10(W, man)),     # after M01-M05 / G01-G05: compares manifest with their measurements
            ('G06', lambda W: kin_group(W, ['R01', 'R02', 'R03', 'R10'])), ('G07', lambda W: kin_group(W, ['R05', 'R06', 'R07', 'R08'])),
            ('G08', lambda W: kin_group(W, ['R09', 'R04', 'R11', 'R12'])),
            ('G09', c_G09), ('G10', lambda W: c_G10(W, man)), ('G11', c_G11), ('G12', c_G12), ('G13', c_G13)]
    for iid, fn in plan:
        try:
            r = fn(W)
        except Exception:
            r = bad('check error: ' + traceback.format_exc()[-400:])
        if r is not None:
            res[iid] = r
    if man is None:
        res['M10'] = bad('manifest.json missing or unparsable (rubric: M10 = 0)')
    return res


def postprocess(results, ctx):
    items = ctx['items']
    failing = [i for i in ('B01', 'B02') if results.get(i, {}).get('verdict') == 'fail']
    if failing:
        for it in items:
            iid = it['id']
            if iid in ('B01', 'B02', 'B05', 'B06', 'B07'):
                continue
            raw = results.get(iid, {}).get('verdict', 'ungraded')
            results[iid] = {'verdict': 'fail', 'source': 'gate',
                            'detail': f'scene gate: {"/".join(failing)} failed (raw verdict: {raw})'}
    return results
