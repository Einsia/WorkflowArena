# -*- coding: utf-8 -*-
"""Static PPTX layout / typography / chart / animation / traceability measurements for CDC-D verifiers
(added 2026-10-25 rubric cleanup). Pure zip + lxml; no PowerPoint.

All functions take the path of a .pptx and return plain data; they never need PowerPoint COM. They are static
approximations of the rendered result:
  * effective font size = explicit run size, else the inherited size (shape lstStyle -> layout placeholder ->
    master placeholder -> master txStyles / presentation defaultTextStyle -> 18 pt), multiplied by
    bodyPr/normAutofit@fontScale; when normAutofit has no stored fontScale but the estimated text height exceeds
    the box, the shrink PowerPoint would apply is estimated (scale = sqrt(available / needed), >= 0.25).
  * text height estimate: characters x 0.5 em average advance per line, line height 1.2 x size, default insets.
  * animation states: entrance-animated shapes are hidden at slide start; exit effects hide; interactive
    (trigger / bookmark) sequences can fire in any order.
"""
import io, json, math, posixpath, re, subprocess, zipfile
from lxml import etree

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'ct': 'http://schemas.openxmlformats.org/package/2006/content-types',
    's': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
}
EMU_PT = 12700.0
EMU_IN = 914400.0
R_ID = '{%s}id' % NS['r']
A = '{%s}' % NS['a']
P = '{%s}' % NS['p']
C = '{%s}' % NS['c']
CAPTION_RE = re.compile(r'^\s*(sources?|fig(ure)?\.?\s*\d*|credits?|image|photo|data\b|adapted|courtesy|note[s:]|'
                        r'table\s*\d|chart\s*data|reproduced|from\b|©)', re.I)
CAPTION_ANY = re.compile(r'\b(source|sources|credit|courtesy|adapted from|reproduced from)\s*[:\-]|\bfig(ure)?\.?\s*\d+\b|'
                         r'\.pdf\b|\bp{1,2}\.\s*\d+|\bpage\s*\d+', re.I)


# ---------------------------------------------------------------- package
def _rels(z, part):
    d, f = posixpath.split(part)
    rp = posixpath.join(d, '_rels', f + '.rels')
    out = {}
    if rp not in z.namelist():
        return out
    for r in etree.fromstring(z.read(rp)).findall('rel:Relationship', NS):
        tgt = r.get('Target') or ''
        ext = r.get('TargetMode') == 'External'
        if not ext:
            tgt = tgt.lstrip('/') if tgt.startswith('/') else posixpath.normpath(posixpath.join(d, tgt))
        out[r.get('Id')] = {'type': (r.get('Type') or '').rsplit('/', 1)[-1], 'target': tgt, 'external': ext}
    return out


def integrity(path):
    """Static checks that commonly trigger PowerPoint's repair prompt (same rules as dpptx.integrity)."""
    issues = []
    try:
        z = zipfile.ZipFile(str(path))
    except Exception as e:
        return [f'not a zip: {e}']
    names = z.namelist()
    if len(names) != len(set(names)):
        issues.append('duplicate zip entries')
    try:
        bad = z.testzip()
        if bad:
            issues.append(f'crc error in {bad}')
    except Exception as e:
        issues.append(f'zip test error {e}')
    if '[Content_Types].xml' not in names:
        return issues + ['missing [Content_Types].xml']
    ct = etree.fromstring(z.read('[Content_Types].xml'))
    defaults = {d.get('Extension', '').lower() for d in ct.findall('ct:Default', NS)}
    overrides = {o.get('PartName', '').lstrip('/') for o in ct.findall('ct:Override', NS)}
    for n in names:
        if n.endswith('/') or n == '[Content_Types].xml':
            continue
        ext = n.rsplit('.', 1)[-1].lower() if '.' in n else ''
        if n not in overrides and ext not in defaults:
            issues.append(f'no content type for {n}')
        if ext in ('xml', 'rels'):
            try:
                etree.fromstring(z.read(n))
            except Exception as e:
                issues.append(f'malformed xml {n}: {str(e)[:80]}')
    for o in overrides:
        if o not in names:
            issues.append(f'override for missing part {o}')
    for n in names:
        if not n.endswith('.rels'):
            continue
        src = n.replace('_rels/', '')[:-5]
        try:
            for rid, r in _rels(z, src).items():
                if not r['external'] and r['target'] not in names:
                    issues.append(f'{n} {rid} -> missing {r["target"]}')
        except Exception as e:
            issues.append(f'bad rels {n}: {e}')
    return issues[:30]


class Pkg:
    def __init__(self, path):
        self.z = zipfile.ZipFile(str(path))
        self.names = set(self.z.namelist())
        self._x = {}
        pres = self.xml('ppt/presentation.xml')
        prels = _rels(self.z, 'ppt/presentation.xml')
        self.slides = [prels[s.get(R_ID)]['target'] for s in pres.findall('p:sldIdLst/p:sldId', NS)]
        sz = pres.find('p:sldSz', NS)
        self.cx, self.cy = int(sz.get('cx')), int(sz.get('cy'))
        self.default_style = pres.find('p:defaultTextStyle', NS)

    def xml(self, part):
        if part not in self._x:
            self._x[part] = etree.fromstring(self.z.read(part))
        return self._x[part]

    def rels(self, part):
        return _rels(self.z, part)

    def layout_master(self, i):
        s = self.slides[i]
        lay = next((r['target'] for r in self.rels(s).values() if r['type'] == 'slideLayout'), None)
        mas = next((r['target'] for r in self.rels(lay).values() if r['type'] == 'slideMaster'), None) if lay else None
        return (lay if lay in self.names else None), (mas if mas in self.names else None)


# ---------------------------------------------------------------- shapes
def _ph(el):
    ph = el.find('./p:nvSpPr/p:nvPr/p:ph', NS)
    if ph is None:
        ph = el.find('./*/p:nvPr/p:ph', NS)
    if ph is None:
        return None
    return {'type': ph.get('type') or 'obj', 'idx': ph.get('idx') or '0'}


def _xfrm(el):
    tag = etree.QName(el).localname
    if tag == 'graphicFrame':
        x = el.find('p:xfrm', NS)
    elif tag == 'grpSp':
        x = el.find('p:grpSpPr/a:xfrm', NS)
    else:
        x = el.find('p:spPr/a:xfrm', NS)
    if x is None:
        return None
    off, ext = x.find('a:off', NS), x.find('a:ext', NS)
    if off is None or ext is None:
        return None
    r = {'x': int(off.get('x', 0)), 'y': int(off.get('y', 0)), 'cx': int(ext.get('cx', 0)), 'cy': int(ext.get('cy', 0))}
    if tag == 'grpSp':
        co, ce = x.find('a:chOff', NS), x.find('a:chExt', NS)
        r['ch'] = (int(co.get('x', 0)), int(co.get('y', 0)), int(ce.get('cx', 1)) or 1, int(ce.get('cy', 1)) or 1) \
            if co is not None and ce is not None else (r['x'], r['y'], r['cx'] or 1, r['cy'] or 1)
    return r


def _ph_lookup(root, ph):
    """find the placeholder sp in a layout/master tree matching ph (idx first, then type)."""
    if root is None or ph is None:
        return None
    cands = []
    for sp in root.iter(P + 'sp'):
        q = _ph(sp)
        if q is not None:
            cands.append((q, sp))
    t = ph['type']
    norm = {'ctrTitle': 'title', 'subTitle': 'body', 'obj': 'body'}
    if ph['idx'] != '0':
        for q, sp in cands:
            if q['idx'] == ph['idx']:
                return sp
    for q, sp in cands:
        if q['type'] == t:
            return sp
    for q, sp in cands:
        if norm.get(q['type'], q['type']) == norm.get(t, t):
            return sp
    return None


def walk_shapes(pkg, i):
    """Flattened list of shape dicts on slide i with absolute boxes (EMU; group transforms applied)."""
    root = pkg.xml(pkg.slides[i])
    tree = root.find('p:cSld/p:spTree', NS)
    out = []

    def rec(parent, tf, grp):
        for el in parent:
            tag = etree.QName(el).localname if isinstance(el.tag, str) else ''
            if tag not in ('sp', 'pic', 'cxnSp', 'graphicFrame', 'grpSp'):
                if tag == 'AlternateContent':
                    ch = el.find('{http://schemas.openxmlformats.org/markup-compatibility/2006}Choice')
                    if ch is not None:
                        rec(ch, tf, grp)
                continue
            nv = el.find('./*/p:cNvPr', NS)
            spid = nv.get('id') if nv is not None else None
            xf = _xfrm(el)
            box = None
            if xf is not None:
                x, y, cx, cy = xf['x'], xf['y'], xf['cx'], xf['cy']
                box = tf(x, y, cx, cy)
            if tag == 'grpSp':
                if xf is not None:
                    chx, chy, chcx, chcy = xf['ch']
                    bx = box

                    def ntf(x, y, cx, cy, chx=chx, chy=chy, chcx=chcx, chcy=chcy, bx=bx):
                        sx, sy = bx[2] / chcx, bx[3] / chcy
                        return (bx[0] + (x - chx) * sx, bx[1] + (y - chy) * sy, cx * sx, cy * sy)
                else:
                    ntf = tf
                rec(el, ntf, spid if grp is None else grp)
                continue
            d = {'spid': spid, 'name': nv.get('name', '') if nv is not None else '', 'kind': tag, 'el': el,
                 'box': box, 'ph': _ph(el), 'group': grp, 'text': '', 'chart': None, 'table': False}
            if tag == 'sp':
                tb = el.find('p:txBody', NS)
                d['txBody'] = tb
                if tb is not None:
                    d['text'] = '\n'.join(''.join(t.text or '' for t in p.iter(A + 't')) for p in tb.findall('a:p', NS)).strip()
            elif tag == 'graphicFrame':
                if el.find('.//a:tbl', NS) is not None:
                    d['table'] = True
                    d['text'] = ' '.join(t.text or '' for t in el.iter(A + 't')).strip()
                ch = el.find('.//c:chart', NS)
                if ch is not None:
                    r = pkg.rels(pkg.slides[i]).get(ch.get(R_ID))
                    d['chart'] = r['target'] if r and r['target'] in pkg.names else None
            out.append(d)

    rec(tree, lambda x, y, cx, cy: (x, y, cx, cy), None)
    return out


# ---------------------------------------------------------------- font size resolution
def _lvl_sz(lst, lvl):
    if lst is None:
        return None
    e = lst.find('a:lvl%dpPr/a:defRPr' % (lvl + 1), NS)
    if e is not None and e.get('sz'):
        return int(e.get('sz')) / 100.0
    return None


def _inherited_size(pkg, i, shp, lvl, master_tx_cache):
    el = shp['el']
    tb = shp.get('txBody')
    s = _lvl_sz(tb.find('a:lstStyle', NS) if tb is not None else None, lvl)
    if s:
        return s
    lay, mas = pkg.layout_master(i)
    ph = shp['ph']
    if ph is not None:
        for part in (lay, mas):
            if part is None:
                continue
            sp = _ph_lookup(pkg.xml(part), ph)
            if sp is not None:
                b = sp.find('p:txBody', NS)
                s = _lvl_sz(b.find('a:lstStyle', NS) if b is not None else None, lvl)
                if s:
                    return s
        if mas is not None:
            tx = pkg.xml(mas).find('p:txStyles', NS)
            if tx is not None:
                key = 'p:titleStyle' if ph['type'] in ('title', 'ctrTitle') else \
                    ('p:bodyStyle' if ph['type'] in ('body', 'obj', 'subTitle', 'tbl', 'chart', 'dgm', 'media', 'clipArt', 'pic')
                     else 'p:otherStyle')
                s = _lvl_sz(tx.find(key, NS), lvl)
                if s:
                    return s
    s = _lvl_sz(pkg.default_style, lvl)
    if s:
        return s
    if mas is not None:
        tx = pkg.xml(mas).find('p:txStyles', NS)
        if tx is not None:
            s = _lvl_sz(tx.find('p:otherStyle', NS), lvl)
            if s:
                return s
    return 18.0


def _insets(bp):
    def g(k, d):
        try:
            return int(bp.get(k)) if bp is not None and bp.get(k) is not None else d
        except Exception:
            return d
    return g('lIns', 91440), g('tIns', 45720), g('rIns', 91440), g('bIns', 45720)


def _est_height_pt(paras, width_pt, scale=1.0):
    """paras: [(text, size_pt)] -> estimated height in pt."""
    h = 0.0
    for t, sz in paras:
        sz = sz * scale
        n = max(len(t), 1)
        per_line = max(1.0, width_pt / (0.5 * sz))
        lines = max(1, math.ceil(n / per_line)) + t.count('\n')
        h += lines * 1.2 * sz
    return h


def _anchor(pkg, i, s, bp):
    if bp is not None and bp.get('anchor'):
        return bp.get('anchor')
    if s['ph'] is not None:
        lay, mas = pkg.layout_master(i)
        for part in (lay, mas):
            if part is None:
                continue
            sp = _ph_lookup(pkg.xml(part), s['ph'])
            if sp is not None:
                b = sp.find('p:txBody/a:bodyPr', NS)
                if b is not None and b.get('anchor'):
                    return b.get('anchor')
    return 't'


def _algn(tb):
    p = tb.find('a:p/a:pPr', NS)
    return p.get('algn') if p is not None and p.get('algn') else 'l'


def text_shapes(pkg, i):
    """Per text-bearing shape on slide i: dict(spid, name, ph, box, role, paras=[(text, eff_size)], runs=[(text, eff_size)],
    est_h_pt, avail_h_pt, autofit, font_scale, bullets)."""
    out = []
    shapes = walk_shapes(pkg, i)
    cxn_ids = set()
    for s in shapes:
        if s['kind'] == 'cxnSp':
            for k in ('a:stCxn', 'a:endCxn'):
                e = s['el'].find('.//' + k, NS)
                if e is not None:
                    cxn_ids.add(e.get('id'))
    for s in shapes:
        if s['kind'] == 'graphicFrame' and s['table']:
            runs = []
            for tc in s['el'].iter(A + 'tc'):
                for r in tc.iter(A + 'r'):
                    t = ''.join(x.text or '' for x in r.iter(A + 't'))
                    if not t.strip():
                        continue
                    rp = r.find('a:rPr', NS)
                    sz = int(rp.get('sz')) / 100.0 if rp is not None and rp.get('sz') else (_lvl_sz(pkg.default_style, 0) or 18.0)
                    runs.append((t, sz))
            if runs:
                out.append({'spid': s['spid'], 'name': s['name'], 'ph': None, 'box': s['box'], 'role': 'table', 'runs': runs,
                            'paras': runs, 'est_h_pt': None, 'avail_h_pt': None, 'autofit': None, 'font_scale': 1.0,
                            'bullets': 0, 'text': s['text'], 'diagram_node': False, 'group': s['group']})
            continue
        if s['kind'] != 'sp' or s.get('txBody') is None or not s['text']:
            continue
        tb = s['txBody']
        bp = tb.find('a:bodyPr', NS)
        autofit, fscale = None, 1.0
        if bp is not None:
            if bp.find('a:normAutofit', NS) is not None:
                autofit = 'norm'
                fs = bp.find('a:normAutofit', NS).get('fontScale')
                if fs:
                    try:
                        fscale = int(fs) / 100000.0
                    except Exception:
                        pass
            elif bp.find('a:spAutoFit', NS) is not None:
                autofit = 'shape'
        ph = s['ph']
        ptype = ph['type'] if ph else None
        paras, runs, bullets = [], [], 0
        mtx = {}
        for p in tb.findall('a:p', NS):
            ppr = p.find('a:pPr', NS)
            lvl = int(ppr.get('lvl', 0)) if ppr is not None and str(ppr.get('lvl', '0')).isdigit() else 0
            inh = None
            ptext, psz = '', []
            for r in p:
                ln = etree.QName(r).localname
                if ln not in ('r', 'fld'):
                    if ln == 'br':
                        ptext += '\n'
                    continue
                t = ''.join(x.text or '' for x in r.iter(A + 't'))
                if not t:
                    continue
                rp = r.find('a:rPr', NS)
                if rp is not None and rp.get('sz'):
                    sz = int(rp.get('sz')) / 100.0
                else:
                    if inh is None:
                        inh = _inherited_size(pkg, i, s, lvl, mtx)
                    sz = inh
                ptext += t
                if t.strip():
                    runs.append((t, sz))
                    psz.append(sz)
            if ptext.strip():
                paras.append((ptext, max(psz) if psz else 18.0))
                bu_none = ppr is not None and ppr.find('a:buNone', NS) is not None
                bu_exp = ppr is not None and (ppr.find('a:buChar', NS) is not None or ppr.find('a:buAutoNum', NS) is not None)
                if bu_exp or (ptype in ('body', 'obj') and not bu_none):
                    bullets += 1
        box = s['box']
        est = avail = None
        if box:
            l, t_, r_, b_ = _insets(bp)
            wpt = max(1.0, (box[2] - l - r_) / EMU_PT)
            avail = max(1.0, (box[3] - t_ - b_) / EMU_PT)
            est = _est_height_pt(paras, wpt, fscale)
            if autofit == 'norm' and fscale == 1.0 and est > avail:
                fscale = max(0.25, math.sqrt(avail / est))
                est = _est_height_pt(paras, wpt, fscale)
        role = 'title' if ptype in ('title', 'ctrTitle') else ('footer' if ptype in ('dt', 'ftr', 'sldNum', 'hdr') else None)
        if role is None:
            first = s['text'].strip().split('\n')[0]
            small = box is not None and box[3] / EMU_IN < 0.6 and len(s['text'].split()) <= 30
            if CAPTION_RE.search(first) or (small and CAPTION_ANY.search(s['text'])):
                role = 'caption'
            elif ptype == 'subTitle':
                role = 'subtitle'
            else:
                role = 'body'
        out.append({'spid': s['spid'], 'name': s['name'], 'ph': ptype, 'box': box, 'role': role,
                    'runs': [(t, sz * fscale) for t, sz in runs], 'paras': paras, 'est_h_pt': est, 'avail_h_pt': avail,
                    'autofit': autofit, 'font_scale': fscale, 'bullets': bullets, 'text': s['text'],
                    'diagram_node': s['spid'] in cxn_ids, 'group': s['group'], 'insets': _insets(bp),
                    'anchor': _anchor(pkg, i, s, bp), 'algn': _algn(tb)})
    return out


def font_violations(path, body_min, caption_min):
    """-> (body_viol, small_viol, n_runs). body_viol: runs of body text (body/object placeholders, subtitles and
    ordinary text boxes that are not captions/source lines) below body_min; small_viol: runs of captions/source lines,
    titles and table cells below caption_min. Date/footer/slide-number placeholders and chart-internal text ignored."""
    pkg = Pkg(path)
    bv, sv, n = [], [], 0
    for i in range(len(pkg.slides)):
        for t in text_shapes(pkg, i):
            if t['role'] == 'footer':
                continue
            for txt, sz in t['runs']:
                n += 1
                lab = f'slide {i + 1} "{t["name"]}" ({t["role"]}) {sz:.1f}pt "{txt.strip()[:30]}"' + \
                    (f' [autofit x{t["font_scale"]:.2f}]' if t['font_scale'] != 1.0 else '')
                if t['role'] in ('body', 'subtitle'):
                    if sz < body_min - 0.05:
                        bv.append(lab)
                elif sz < caption_min - 0.05:
                    sv.append(lab)
    return bv, sv, n


def bullets_per_slide(path):
    """[(slide_no, n_bullets, detail)] where bullets = non-empty paragraphs of body/object placeholders without buNone
    plus paragraphs with explicit buChar/buAutoNum in any text shape; captions/source lines and connector-linked
    diagram nodes excluded."""
    pkg = Pkg(path)
    res = []
    for i in range(len(pkg.slides)):
        tot, parts = 0, []
        for t in text_shapes(pkg, i):
            if t['role'] in ('caption', 'title', 'footer', 'table') or t['diagram_node']:
                continue
            if t['bullets']:
                tot += t['bullets']
                parts.append(f'{t["name"]}:{t["bullets"]}')
        res.append((i + 1, tot, ', '.join(parts)))
    return res


# ---------------------------------------------------------------- geometry
def _inter(a, b):
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0


def _text_area(t):
    """estimated rendered text rectangle of a text shape (EMU): height from the text estimate (can exceed the box when
    the text overflows), width from the longest line, placed by vertical anchor and paragraph alignment."""
    b = t['box']
    if b is None:
        return None
    if t['est_h_pt'] is None:
        return b
    li, ti, ri, bi = t.get('insets') or (91440, 45720, 91440, 45720)
    h = t['est_h_pt'] * EMU_PT + ti + bi
    if t['autofit'] == 'shape':
        h = max(b[3], h)
    an = t.get('anchor') or 't'
    y = b[1] if an == 't' or t['autofit'] == 'shape' else (b[1] + (b[3] - h) / 2 if an == 'ctr' else b[1] + b[3] - h)
    longest = max((len(x) * 0.5 * sz * t['font_scale'] for tx, sz in t['paras'] for x in tx.split('\n')), default=0)
    w = min(b[2], longest * EMU_PT + li + ri)
    al = t.get('algn') or 'l'
    x = b[0] if al in ('l', 'just', 'dist') else (b[0] + (b[2] - w) / 2 if al == 'ctr' else b[0] + b[2] - w)
    return (x, y, w, h)


def layout_issues(path, slides=None, exclude_animated=True):
    """Static-render problems: text overflow (estimated text height > 1.25 x available + 6 pt without autofit),
    shapes beyond the slide edge (> 1 % of slide size), and overlapping text (estimated text areas of two
    text shapes / tables intersect by > 5 % of the smaller one). With exclude_animated, overlap pairs in which
    either shape is the target of an animation are left to the animation-state check."""
    pkg = Pkg(path)
    issues = []
    for i in range(len(pkg.slides)):
        if slides and i + 1 not in slides:
            continue
        anim = animated_spids(pkg, i) if exclude_animated else set()
        ts = text_shapes(pkg, i)
        for el in walk_shapes(pkg, i):
            b = el['box']
            if not b or el['group'] is not None:
                continue
            tolx, toly = 0.01 * pkg.cx, 0.01 * pkg.cy
            if b[0] < -tolx or b[1] < -toly or b[0] + b[2] > pkg.cx + tolx or b[1] + b[3] > pkg.cy + toly:
                issues.append(f'slide {i + 1}: "{el["name"]}" extends beyond the slide')
        for t in ts:
            if t['est_h_pt'] is not None and t['autofit'] != 'shape' and t['est_h_pt'] > 1.25 * t['avail_h_pt'] + 6:
                issues.append(f'slide {i + 1}: "{t["name"]}" text overflows (needs ~{t["est_h_pt"]:.0f}pt, box {t["avail_h_pt"]:.0f}pt)')
            if t['est_h_pt'] is not None and t['autofit'] == 'shape' and t['box'] and \
                    t['box'][1] + t['est_h_pt'] * EMU_PT > pkg.cy * 1.01 + 6 * EMU_PT:
                issues.append(f'slide {i + 1}: "{t["name"]}" auto-grown text box runs off the slide')
        for k in range(len(ts)):
            for m in range(k + 1, len(ts)):
                a, b = ts[k], ts[m]
                if exclude_animated and (a['spid'] in anim or b['spid'] in anim):
                    continue
                if _text_overlap(a, b):
                    issues.append(f'slide {i + 1}: text of "{a["name"]}" and "{b["name"]}" overlap')
    return issues


def _text_overlap(a, b, frac=0.05):
    ra, rb = _text_area(a), _text_area(b)
    if not ra or not rb:
        return False
    ov = _inter(ra, rb)
    small = min(ra[2] * ra[3], rb[2] * rb[3]) or 1
    return ov > frac * small


# ---------------------------------------------------------------- animation
def _effects(node):
    out = []
    for ctn in node.iter(P + 'cTn'):
        cls = ctn.get('presetClass')
        if cls is None:
            continue
        sp = {t.get('spid') for t in ctn.iter(P + 'spTgt') if t.get('spid')}
        for s in sp:
            out.append({'cls': cls, 'node': ctn.get('nodeType'), 'spid': s})
    return out


def timeline(pkg, i):
    """dict(main=[ [effects of click-group k] ...], auto_first=bool, inter=[{'trigger', 'evt', 'effects'}])."""
    root = pkg.xml(pkg.slides[i])
    tm = root.find('p:timing', NS)
    res = {'main': [], 'inter': [], 'entry_visible_anim': set()}
    if tm is None:
        return res
    for ctn in tm.iter(P + 'cTn'):
        nt = ctn.get('nodeType')
        if nt == 'mainSeq':
            for par in ctn.findall('p:childTnLst/p:par', NS):
                res['main'].append(_effects(par))
        elif nt == 'interactiveSeq':
            trig, evt = None, None
            for c in ctn.iter(P + 'cond'):
                if c.get('evt') in ('onClick', 'onMediaBookmark', 'onBegin'):
                    evt = c.get('evt')
                    for t in c.iter():
                        if t.get('spid') is not None:
                            trig = t.get('spid')
                    break
            res['inter'].append({'trigger': trig, 'evt': evt, 'effects': _effects(ctn)})
    return res


def animated_spids(pkg, i):
    tl = timeline(pkg, i)
    s = {e['spid'] for g in tl['main'] for e in g if e['cls'] in ('entr', 'exit', 'path')}
    s |= {e['spid'] for it in tl['inter'] for e in it['effects'] if e['cls'] in ('entr', 'exit', 'path')}
    return s


def main_steps(pkg, i):
    """flattened main-sequence effects as (step, cls, spid): a new step starts with every top-level click group and with
    every clickEffect / afterEffect; withEffect shares the step of the effect before it."""
    tl = timeline(pkg, i)
    out, step = [], -1
    for g in tl['main']:
        step += 1
        first = True
        for e in g:
            if not first and e['node'] in ('clickEffect', 'afterEffect'):
                step += 1
            first = False
            out.append((step, e['cls'], e['spid']))
    return out, tl


def co_visible(pkg, i):
    """function(spidA, spidB) -> True if both can be visible at the same time in some animation state.
    Main-sequence effects are ordered by step (see main_steps); interactive (trigger/bookmark) sequences can fire at
    any time and in any order; a shape with no entrance effect is visible from slide entry until its first exit."""
    flat, tl = main_steps(pkg, i)
    ev = {}
    for k, cls, sp in flat:
        ev.setdefault(sp, []).append(('main', k, cls))
    for j, it in enumerate(tl['inter']):
        for e in it['effects']:
            ev.setdefault(e['spid'], []).append(('int', j, e['cls']))

    def ivs(s):
        es = ev.get(s, [])
        em = sorted(k for q, k, c in es if q == 'main' and c == 'entr')
        xm = sorted(k for q, k, c in es if q == 'main' and c == 'exit')
        ei = {k for q, k, c in es if q == 'int' and c == 'entr'}
        xi = {k for q, k, c in es if q == 'int' and c == 'exit'}
        out = []
        if not em and not ei:
            out.append(('main', -1, min(xm) if xm else math.inf))
        for k in em:
            nx = [e for e in xm if e > k]
            out.append(('main', k, min(nx) if nx else math.inf))
        for j in ei:
            out.append(('int', j, None))
        return out, xi

    def f(a, b):
        va, xa = ivs(a)
        vb, xb = ivs(b)
        for qa, ka, ha in va:
            for qb, kb, hb in vb:
                if qa == qb == 'main':
                    if max(ka, kb) < min(ha, hb):
                        return True
                elif qa == 'int' and qb == 'main':
                    if ka not in xb:
                        return True
                elif qa == 'main' and qb == 'int':
                    if kb not in xa:
                        return True
                elif ka not in xb and kb not in xa:
                    return True
        return False
    return f


def animation_occlusion(path, slides=None, picture_cover=0.30):
    """Problems visible in some animation state: (1) an animated text shape and any other text shape whose
    estimated text areas intersect while co-visible; (2) an animated text shape covering > picture_cover of a
    picture / chart frame it is co-visible with."""
    pkg = Pkg(path)
    issues, checked = [], 0
    for i in range(len(pkg.slides)):
        if slides and i + 1 not in slides:
            continue
        anim = animated_spids(pkg, i)
        if not anim:
            continue
        cov = co_visible(pkg, i)
        ts = text_shapes(pkg, i)
        for k in range(len(ts)):
            for m in range(k + 1, len(ts)):
                a, b = ts[k], ts[m]
                if a['spid'] not in anim and b['spid'] not in anim:
                    continue
                checked += 1
                if cov(a['spid'], b['spid']) and _text_overlap(a, b):
                    issues.append(f'slide {i + 1}: animated text "{a["name"]}" / "{b["name"]}" overlap when both visible')
        figs = [s for s in walk_shapes(pkg, i) if s['kind'] == 'pic' or s['chart']]
        for t in ts:
            if t['spid'] not in anim:
                continue
            ra = _text_area(t)
            for fg in figs:
                if not fg['box'] or not ra:
                    continue
                checked += 1
                area = fg['box'][2] * fg['box'][3] or 1
                if cov(t['spid'], fg['spid']) and _inter(ra, fg['box']) > picture_cover * area:
                    issues.append(f'slide {i + 1}: animated text "{t["name"]}" covers {100 * _inter(ra, fg["box"]) / area:.0f}% of "{fg["name"]}"')
    return issues, checked


# ---------------------------------------------------------------- charts
UNIT_RE = re.compile(r'\(|\[|%|°|‰|\$|/|\bper\b|\b(ft|feet|psi|lbs?|kg|g|m|km|mm|cm|m³|m3|m²|m2|mJ|J|bar|kPa|days?|hours?|h|'
                     r'min|minutes?|s|sec|seconds?|years?|count|number|no\.|cases|deaths|people|persons|patients|instances|'
                     r'airplanes|aircraft|flights|cycles|occupants|rate|percent|share|USD|dollars|°C|°F|degrees?|celsius|'
                     r'fahrenheit|anomaly|wt)\b', re.I)

UNIT_STRICT = re.compile(r'%|°|‰|\$|\b(ft|feet|psi|lbs?|kg|g|m|km|mm|cm|µm|um|m³|m3|m²|m2|g/m³|g/m3|mJ|J|bar|kPa|days?|hours?|h|'
                         r'min|minutes?|s|sec|seconds?|years?|count|cases|deaths|people|persons|patients|instances|airplanes|'
                         r'aircraft|flights|cycles|occupants|percent|USD|dollars|°C|°F|degrees?|celsius|fahrenheit|wt%?|'
                         r'per 100,?000|per 10,?000|fatalities|injuries|injured|workers|employees|pieces|buildings)\b', re.I)


def _title_text(t):
    if t is None:
        return ''
    s = ' '.join(x.text or '' for x in t.iter(A + 't'))
    s += ' ' + ' '.join(x.text or '' for x in t.iter(C + 'v'))
    return s.strip()


def chart_parts(path):
    pkg = Pkg(path)
    out = []
    for i in range(len(pkg.slides)):
        for s in walk_shapes(pkg, i):
            if s['chart']:
                out.append((i + 1, s['name'], s['chart'], pkg))
    return out


def chart_axis_issues(path, need_period=False, date_basis_re=None):
    """For each native chart: every non-deleted axis needs a title; the value-axis title must carry a unit;
    >= 2 series need a non-deleted legend; with need_period the chart text must contain a 'YYYY–YYYY' period;
    with date_basis_re a date/category axis whose labels are dates must state its basis (regex on its title)."""
    issues, n = [], 0
    for sl, name, part, pkg in chart_parts(path):
        n += 1
        root = pkg.xml(part)
        pa = root.find('.//c:plotArea', NS)
        if pa is None:
            issues.append(f'slide {sl} "{name}": chart has no plot area')
            continue
        lab = f'slide {sl} "{name}"'
        nser = len(pa.findall('.//c:ser', NS))
        for ax in pa:
            ln = etree.QName(ax).localname
            if ln not in ('valAx', 'catAx', 'dateAx', 'serAx'):
                continue
            d = ax.find('c:delete', NS)
            if d is not None and d.get('val') in ('1', 'true'):
                continue
            tt = _title_text(ax.find('c:title', NS))
            if not tt:
                issues.append(f'{lab}: {ln} has no axis title')
                continue
            if ln == 'valAx' and not UNIT_RE.search(tt):
                issues.append(f'{lab}: value-axis title "{tt[:40]}" states no unit')
            if ln in ('catAx', 'dateAx') and date_basis_re is not None:
                cats = ' '.join(v.text or '' for v in ax.getparent().iter(C + 'v'))
                is_date = ln == 'dateAx' or re.search(r'\b(jan|feb|mar|\d{1,2}[/-]\d{1,2}|\d{4}-\d{2}-\d{2})', cats, re.I)
                if is_date and not re.search(date_basis_re, tt, re.I):
                    issues.append(f'{lab}: date axis title "{tt[:40]}" does not state its date basis')
        if nser >= 2:
            lg = root.find('.//c:chart/c:legend', NS)
            if lg is None or (lg.find('c:delete', NS) is not None and lg.find('c:delete', NS).get('val') in ('1', 'true')):
                issues.append(f'{lab}: {nser} series but no legend')
        if need_period:
            txt = ' '.join(x.text or '' for x in root.iter(A + 't')) + ' ' + \
                ' '.join(v.text or '' for v in root.iter(C + 'v') if v.getparent().getparent() is not None and
                         etree.QName(v.getparent().getparent()).localname == 'strCache')
            if not re.search(r'(1[89]|20)\d{2}\s*[–\-—]\s*(1[89]|20)?\d{2}', txt):
                issues.append(f'{lab}: no reference period (YYYY–YYYY) stated in chart title/axis/series text')
    return issues, n


def chart_series(path):
    """[(slide, name, part, [(series_name, [values], ref)])] from c:numCache."""
    out = []
    for sl, name, part, pkg in chart_parts(path):
        root = pkg.xml(part)
        ss = []
        for ser in root.iter(C + 'ser'):
            nm = ' '.join(v.text or '' for v in ser.findall('c:tx//c:v', NS)) or ' '.join(t.text or '' for t in ser.findall('c:tx//a:t', NS))
            for tag in ('val', 'yVal', 'xVal'):
                v = ser.find('c:' + tag, NS)
                if v is None:
                    continue
                if tag == 'xVal' and v.find('.//c:numCache', NS) is None:
                    continue
                f = v.find('.//c:f', NS)
                vals = []
                for pt in v.findall('.//c:numCache/c:pt', NS):
                    try:
                        vals.append((int(pt.get('idx')), float(pt.findtext('c:v', namespaces=NS))))
                    except Exception:
                        pass
                ss.append((nm, vals, f.text if f is not None else None))
        out.append((sl, name, part, ss))
    return out


# ---------------------------------------------------------------- material numbers / traceability
NUM_RE = re.compile(r'(?<![\w.])[-+−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.,])[-+−]?\d+(?:\.\d+)?')


def nums_in(text):
    out = []
    for m in NUM_RE.finditer(text or ''):
        s = m.group(0).replace(',', '').replace('−', '-').lstrip('+')
        try:
            out.append((m.group(0), float(s), m.start()))
        except ValueError:
            pass
    return out


_MAT = {}


def material(input_dir):
    """cached Material for an input directory."""
    k = str(input_dir)
    if k not in _MAT:
        _MAT[k] = Material(input_dir)
    return _MAT[k]


class Material:
    """Numbers and text of the input material, per file and page (pdftotext -layout; html tags stripped)."""

    def __init__(self, input_dir):
        from pathlib import Path
        self.pages = {}  # file -> [page text]
        for p in sorted(Path(input_dir).glob('*')):
            if p.suffix.lower() == '.pdf':
                try:
                    o = subprocess.run(['pdftotext', '-layout', str(p), '-'], capture_output=True, text=True, timeout=180).stdout
                except Exception:
                    o = ''
                pg = o.split('\f')
                if pg and not pg[-1].strip():
                    pg = pg[:-1]
                self.pages[p.name] = pg
            elif p.suffix.lower() in ('.html', '.htm', '.txt', '.md'):
                t = p.read_text(encoding='utf-8', errors='replace')
                t = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', t, flags=re.S | re.I)
                self.pages[p.name] = [re.sub(r'&nbsp;|&#160;', ' ', re.sub(r'<[^>]+>', ' ', t))]
        self.vals = {}
        for f, pg in self.pages.items():
            for k, t in enumerate(pg):
                for raw, v, _ in nums_in(t):
                    self.vals.setdefault(round(v, 6), []).append((f, k + 1))
        self._sorted = sorted(self.vals)

    def find_rounded(self, v):
        """v is a printed number rounded to v's own precision (e.g. 15.4 for 15,375,959 in millions, 83.5 for 83.47);
        also tried in thousands / millions and as percent <-> share."""
        import bisect
        t = fmt(v)
        dp = len(t.split('.')[1]) if '.' in t and 'e' not in t else 0
        hits = []
        for scale in (1, 1e3, 1e6, 100, 0.01):
            c = v * scale
            tol = 0.5 * 10 ** -dp * scale + 1e-9 * abs(c)
            lo = bisect.bisect_left(self._sorted, c - tol)
            for k in range(lo, len(self._sorted)):
                x = self._sorted[k]
                if x > c + tol:
                    break
                hits += self.vals[x]
        return hits

    def find(self, v, rel=1e-6):
        """locations of a printed number equal to v (also v*100 / v/100 for share <-> percent)."""
        import bisect
        hits = []
        for c in (v, v * 100, v / 100):
            tol = max(1e-9, rel * abs(c))
            lo = bisect.bisect_left(self._sorted, round(c - tol, 6))
            for k in range(lo, len(self._sorted)):
                x = self._sorted[k]
                if x > c + tol:
                    break
                hits += self.vals[x]
        return hits

    def on_page(self, fname, page, raw):
        pg = self.pages.get(fname)
        if not pg:
            return False
        txts = pg if len(pg) == 1 else ([pg[page - 1]] if 1 <= page <= len(pg) else [])
        s = raw.replace(',', '')
        return any(s in t.replace(',', '') for t in txts)


def resolve_input_file(cell, names):
    """match an evidence-index source cell to an input filename (substring / stem / fuzzy)."""
    c = (cell or '').strip().lower()
    if not c:
        return None
    for n in names:
        if n.lower() in c:
            return n
    for n in sorted(names, key=len, reverse=True):
        stem = n.rsplit('.', 1)[0].lower()
        if stem in c or stem.replace('-', ' ') in c or stem.replace('-', '_') in c:
            return n
    return None


REF_BEFORE = re.compile(r'(slide|slides|p|pp|page|pages|fig|figure|figures|table|tables|section|sections|§|finding|findings|'
                        r'recommendation|recommendations|rec|footnote|fn|appendix|chapter|step|version|v|powerpoint|python|'
                        r'pptx|office|row|item|no|#)\.?\s*[-–#]?\s*$', re.I)
SKIP_LINE = re.compile(r'powerpoint|libreoffice|python|python-pptx|\bAI\b|artificial intelligence|language model|\bLLM\b|'
                       r'claude|gpt|openai|anthropic|version|software|font|pt\b|click|trigger|bookmark|animation', re.I)


def slide_numbers(text):
    """significant numeric tokens of a text (>= 2 digits or a decimal), skipping references (slide/page/figure ...),
    lines about software/AI/animation and list markers."""
    out = []
    for line in (text or '').splitlines():
        if SKIP_LINE.search(line):
            continue
        for raw, v, pos in nums_in(line):
            digits = re.sub(r'\D', '', raw)
            if len(digits) < 2 and '.' not in raw:
                continue
            if REF_BEFORE.search(line[max(0, pos - 14):pos]):
                continue
            if re.match(r'^\s*\d+[.)]\s', line[pos:pos + len(raw) + 2]) and line[:pos].strip() == '':
                continue
            out.append((raw, v))
    return out


def evidence_rows(csv_path):
    import csv as _csv
    raw = csv_path.read_bytes().decode('utf-8-sig', errors='replace')
    try:
        dialect = _csv.Sniffer().sniff(raw[:4000], delimiters=',;\t')
    except Exception:
        dialect = _csv.excel
    rows = [r for r in _csv.reader(io.StringIO(raw), dialect) if any(c.strip() for c in r)]
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _col(h, *alts):
    hl = [x.strip().lower() for x in h]
    for alt in alts:
        for j, x in enumerate(hl):
            if all(k in x for k in alt):
                return j
    return None


DERIVED_RE = re.compile(r'recalc|conver|calc|deriv|arith|comput|sum|differen|ratio|round|aggregat|subtract|divid|multipl|'
                        r'percent|rate|offset|interval|formula|read from fig|read-off|estimate', re.I)


# ---------------------------------------------------------------- slide text / notes
def slide_text(pkg, i):
    return '\n'.join(s['text'] for s in walk_shapes(pkg, i) if s['text'])


def notes_text(pkg, i):
    for r in pkg.rels(pkg.slides[i]).values():
        if r['type'] == 'notesSlide' and r['target'] in pkg.names:
            root = pkg.xml(r['target'])
            parts = []
            for sp in root.iter(P + 'sp'):
                ph = sp.find('.//p:nvPr/p:ph', NS)
                if ph is not None and ph.get('type') == 'body':
                    for p in sp.iter(A + 'p'):
                        parts.append(''.join(x.text or '' for x in p.iter(A + 't')))
            return '\n'.join(parts).strip()
    return ''


# ---------------------------------------------------------------- workbooks
def _col2n(c):
    n = 0
    for ch in c:
        n = n * 26 + ord(ch) - 64
    return n


def _n2col(n):
    s = ''
    while n:
        n, m = divmod(n - 1, 26)
        s = chr(65 + m) + s
    return s


def workbook_cells(data):
    """{sheet_name: {ref: (value, formula_or_None)}}; value float for numbers, str for strings; sheets in order."""
    z = zipfile.ZipFile(io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else str(data))
    S = '{%s}' % NS['s']
    ss = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in etree.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS):
            ss.append(''.join(t.text or '' for t in si.iter(S + 't')))
    wb = etree.fromstring(z.read('xl/workbook.xml'))
    wr = _rels(z, 'xl/workbook.xml')
    out = {}
    for sh in wb.findall('s:sheets/s:sheet', NS):
        part = wr.get(sh.get(R_ID), {}).get('target')
        cells = {}
        if part and part in z.namelist():
            for c in etree.fromstring(z.read(part)).iter(S + 'c'):
                t, v, f, isv = c.get('t'), c.find('s:v', NS), c.find('s:f', NS), c.find('s:is', NS)
                val = None
                if t == 's' and v is not None and v.text and v.text.isdigit() and int(v.text) < len(ss):
                    val = ss[int(v.text)]
                elif t == 'inlineStr' and isv is not None:
                    val = ''.join(x.text or '' for x in isv.iter(S + 't'))
                elif v is not None and v.text is not None:
                    try:
                        val = float(v.text) if t not in ('str', 'e', 'b') else v.text
                    except ValueError:
                        val = v.text
                cells[c.get('r')] = (val, (f.text or 'shared') if f is not None else None)
        out[sh.get('name')] = cells
    return out


def chart_workbook(pkg, part):
    """(bytes or None, error)"""
    root = pkg.xml(part)
    ext = root.find('c:externalData', NS)
    if ext is None:
        return None, 'no externalData (no embedded workbook)'
    r = pkg.rels(part).get(ext.get(R_ID))
    if not r:
        return None, 'externalData relationship missing'
    if r['external']:
        return None, f'workbook linked externally: {r["target"]}'
    if r['target'] not in pkg.names:
        return None, 'embedded workbook part missing'
    return pkg.z.read(r['target']), None


def _ref_cells(ref):
    m = re.match(r"^(?:'([^']+)'|([^!]+))!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?$", (ref or '').strip())
    if not m:
        return None, []
    sh = m.group(1) or m.group(2)
    c1, r1 = _col2n(m.group(3)), int(m.group(4))
    c2, r2 = (_col2n(m.group(5)), int(m.group(6))) if m.group(5) else (c1, r1)
    return sh, [_n2col(c) + str(r) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]


def number_set(text):
    return sorted({round(v, 9) for _, v, _ in nums_in((text or '').replace('−', '-'))})


def in_numbers(v, nums, rel=1e-6):
    import bisect
    for c in (v, v * 100, v / 100):
        tol = max(1e-9, rel * abs(c))
        k = bisect.bisect_left(nums, c - tol)
        if k < len(nums) and nums[k] <= c + tol:
            return True
    return False


def fmt(v):
    return ('%.10g' % v)


def plotted_value_issues(path, material, answer_nums, print_rounding=False):
    """Every plotted value (c:numCache) must (a) equal the corresponding embedded-workbook cell and (b) be a number
    printed in the input material, a number of the answer key, or a live formula cell of the workbook (derived).
    -> (issues, n_values, n_charts)."""
    pkg = Pkg(path)
    issues, nv, nc = [], 0, 0
    for sl, name, part, ss in chart_series(path):
        nc += 1
        data, err = chart_workbook(pkg, part)
        cells = None
        if data is not None:
            try:
                cells = workbook_cells(data)
            except Exception as e:
                err = f'embedded workbook unreadable: {e}'
        if cells is None:
            issues.append(f'slide {sl} "{name}": {err}')
        for snm, vals, ref in ss:
            sh, refs = _ref_cells(ref) if ref else (None, [])
            for idx, v in vals:
                nv += 1
                cell = None
                if cells is not None and sh is not None and idx < len(refs):
                    cell = (cells.get(sh) or cells.get(sh.strip("'")) or {}).get(refs[idx])
                    if cell is not None and isinstance(cell[0], float) and abs(cell[0] - v) > max(1e-9, 1e-6 * abs(v)):
                        issues.append(f'slide {sl} "{name}" {snm}[{idx}]: plotted {fmt(v)} != workbook {sh}!{refs[idx]} {fmt(cell[0])}')
                        continue
                if material.find(v) or in_numbers(v, answer_nums) or (print_rounding and material.find_rounded(v)):
                    continue
                if cell is not None and cell[1]:
                    continue
                issues.append(f'slide {sl} "{name}" {snm}[{idx}]={fmt(v)}: not printed in the material, not in the answer key '
                              f'and not a live formula in the embedded workbook')
    return issues, nv, nc


# ---------------------------------------------------------------- per-slide fidelity (F items)
def slide_fact_texts(pkg, i):
    """texts and numeric values that carry facts on slide i: slide text (incl. groups, tables), notes, chart values."""
    texts = [slide_text(pkg, i), notes_text(pkg, i)]
    vals = []
    for s in walk_shapes(pkg, i):
        if s['chart']:
            root = pkg.xml(s['chart'])
            texts.append(' '.join(t.text or '' for t in root.iter(A + 't')))
            for pt in root.iter(C + 'pt'):
                par = pt.getparent()
                if par is not None and etree.QName(par).localname == 'numCache':
                    try:
                        vals.append(float(pt.findtext('c:v', namespaces=NS)))
                    except Exception:
                        pass
    return texts, vals


def trace_slide(pkg, i, material, ev_header, ev_rows, answer_nums, extra_nums=()):
    texts, vals = slide_fact_texts(pkg, i)
    slide_no = i + 1
    cs = _col(ev_header, ('slide',))
    cf = _col(ev_header, ('source', 'file'), ('file',), ('source',), ('document',))
    cp = _col(ev_header, ('pdf', 'page'), ('pdf',), ('page',))
    ct = _col(ev_header, ('transform',))
    mine = [r for r in ev_rows if cs is not None and cs < len(r) and slide_no in [int(x) for x in re.findall(r'\d+', r[cs])]]
    names = list(material.pages)
    toks = []
    for t in texts:
        toks += slide_numbers(t)
    toks += [(fmt(v), v) for v in vals]
    res = {'untraced': [], 'counts': {}, 'n': 0, 'rows': len(mine)}
    seen = set()
    for raw, v in toks:
        key = round(v, 9)
        if key in seen:
            continue
        seen.add(key)
        res['n'] += 1
        st = None
        for r in mine:
            fn = resolve_input_file(r[cf], names) if cf is not None and cf < len(r) else None
            pg = re.findall(r'\d+', r[cp]) if cp is not None and cp < len(r) else []
            if fn and pg and material.on_page(fn, int(pg[0]), raw):
                st = 'cited'
                break
        if st is None and material.find(v):
            st = 'material'
        if st is None and in_numbers(v, answer_nums):
            st = 'answer'
        if st is None and extra_nums and in_numbers(v, extra_nums):
            st = 'derived'
        if st is None:
            for r in mine:
                if (ct is None or ct >= len(r) or DERIVED_RE.search(r[ct])) and in_numbers(v, number_set(' '.join(r))):
                    st = 'derived'
                    break
        st = st or 'untraced'
        res['counts'][st] = res['counts'].get(st, 0) + 1
        if st == 'untraced':
            res['untraced'].append(raw)
    return res


def fidelity(ctx, path, item_slides, ev_path, inject=True, extra_derived=()):
    """item_slides: {item_id: [slide numbers]}. Fails an item when a slide carries a number that is neither printed
    in the input material, nor in the answer key, nor declared as a derived value in an evidence-index row of that
    slide (or one of extra_derived, e.g. live formula values of a calculations workbook); otherwise leaves the item to
    the judge and appends the machine trace to the item's verify text."""
    from pathlib import Path
    pkg = Pkg(path)
    mat = material(ctx['input'])
    answer_nums = number_set(json.dumps(ctx.get('answer') or {}, ensure_ascii=False))
    extra = sorted({round(float(x), 9) for x in extra_derived if isinstance(x, (int, float))})
    h, rows = evidence_rows(Path(ev_path)) if Path(ev_path).is_file() else ([], [])
    items = {it['id']: it for it in ctx.get('items') or []}
    out = {}
    n = len(pkg.slides)
    for iid, sl in item_slides.items():
        sl = [s for s in sl if 1 <= s <= n]
        if not sl:
            out[iid] = {'verdict': 'na', 'detail': 'slide(s) not present in the deck'}
            continue
        bad, summ = [], []
        for s in sl:
            r = trace_slide(pkg, s - 1, mat, h, rows, answer_nums, extra)
            if r['untraced']:
                bad.append(f'slide {s}: {r["untraced"][:8]}')
            summ.append(f'slide {s}: {r["n"]} numbers ' + ', '.join(f'{k} {v}' for k, v in sorted(r['counts'].items())) +
                        f'; {r["rows"]} evidence-index rows')
        if bad:
            out[iid] = {'verdict': 'fail', 'detail': 'numbers not found in the material, the answer key or a derived '
                                                    'evidence-index row of the slide: ' + '; '.join(bad)}
        elif inject and iid in items:
            items[iid]['verify'] = (items[iid].get('verify') or '') + ' [checks.py trace at grading time: ' + ' | '.join(summ) + \
                ' -- every number is printed in the input PDFs (cited = found on the evidence-index page), in the answer key, ' \
                'or declared as derived in evidence-index.csv]'
    return out
