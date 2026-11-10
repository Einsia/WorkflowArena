# -*- coding: utf-8 -*-
# ---------------- shared helpers (CDC-D pptx tasks; python-pptx/lxml/pypdf, no openpyxl) ----------------
import csv, difflib, io, json, math, posixpath, re, subprocess, zipfile
from pathlib import Path

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    's': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
}
P159 = 'http://schemas.microsoft.com/office/powerpoint/2015/09/main'
P14 = 'http://schemas.microsoft.com/office/powerpoint/2010/main'


def V(v, d):
    return {'verdict': v, 'detail': str(d)[:600]}


def safe(res, iid, fn):
    """run one check; exceptions -> fail with detail; fn returning None -> leave to judge."""
    try:
        r = fn()
        if r is not None:
            res[iid] = r
    except Exception as e:  # noqa
        res[iid] = V('fail', f'check error: {type(e).__name__}: {e}')


def xml(z, name):
    from lxml import etree
    return etree.fromstring(z.read(name))


def rels(z, part):
    d, b = posixpath.split(part)
    rp = posixpath.join(d, '_rels', b + '.rels')
    out = {}
    if rp not in z.namelist():
        return out
    for r in xml(z, rp).findall('rel:Relationship', NS):
        tgt = r.get('Target')
        ext = r.get('TargetMode') == 'External'
        full = tgt if ext else posixpath.normpath(posixpath.join(d, tgt)).lstrip('/')
        if tgt.startswith('/'):
            full = tgt.lstrip('/')
        out[r.get('Id')] = {'type': r.get('Type', '').rsplit('/', 1)[-1], 'target': full, 'external': ext}
    return out


class Deck:
    def __init__(self, path):
        self.path = Path(path)
        self.z = zipfile.ZipFile(str(path))
        pres = xml(self.z, 'ppt/presentation.xml')
        prel = rels(self.z, 'ppt/presentation.xml')
        self.slides = []
        for sid in pres.findall('p:sldIdLst/p:sldId', NS):
            self.slides.append(prel[sid.get('{%s}id' % NS['r'])]['target'])
        sz = pres.find('p:sldSz', NS)
        self.cx, self.cy = int(sz.get('cx')), int(sz.get('cy'))
        self._x = {}

    def sx(self, i):  # slide xml (0-based)
        if i not in self._x:
            self._x[i] = xml(self.z, self.slides[i])
        return self._x[i]

    def srels(self, i):
        return rels(self.z, self.slides[i])

    # ---- text ----
    def shape_texts(self, i):
        """list of (kind, ph_type, name, [paragraph texts], [explicit run sizes pt], fontScale)"""
        out = []
        root = self.sx(i)
        for sp in root.iter('{%s}sp' % NS['p']):
            tb = sp.find('p:txBody', NS)
            if tb is None:
                continue
            ph = sp.find('.//p:nvPr/p:ph', NS)
            phtype = (ph.get('type') or 'body') if ph is not None else None
            name = sp.find('.//p:cNvPr', NS).get('name', '')
            paras = [''.join(t.text or '' for t in p.iter('{%s}t' % NS['a'])) for p in tb.findall('a:p', NS)]
            fs = 1.0
            na = tb.find('a:bodyPr/a:normAutofit', NS)
            if na is not None and na.get('fontScale'):
                fs = int(na.get('fontScale')) / 100000.0
            sizes = []
            for p in tb.findall('a:p', NS):
                for rr in p.findall('a:r', NS):
                    t = ''.join(x.text or '' for x in rr.iter('{%s}t' % NS['a'])).strip()
                    rp = rr.find('a:rPr', NS)
                    if t and rp is not None and rp.get('sz'):
                        sizes.append(int(rp.get('sz')) / 100.0 * fs)
            out.append(('sp', phtype, name, paras, sizes, fs))
        for tc in root.iter('{%s}tc' % NS['a']):
            tb = tc.find('a:txBody', NS)
            if tb is None:
                continue
            paras = [''.join(t.text or '' for t in p.iter('{%s}t' % NS['a'])) for p in tb.findall('a:p', NS)]
            sizes = []
            for rr in tb.iter('{%s}r' % NS['a']):
                t = ''.join(x.text or '' for x in rr.iter('{%s}t' % NS['a'])).strip()
                rp = rr.find('a:rPr', NS)
                if t and rp is not None and rp.get('sz'):
                    sizes.append(int(rp.get('sz')) / 100.0)
            out.append(('tc', None, 'table', paras, sizes, 1.0))
        return out

    def slide_text(self, i):
        return '\n'.join(p for s in self.shape_texts(i) for p in s[3] if p.strip())

    def title(self, i):
        for k, ph, name, paras, _, _ in self.shape_texts(i):
            if ph in ('title', 'ctrTitle'):
                return ' '.join(p for p in paras if p.strip())
        return ''

    def notes(self, i):
        for r in self.srels(i).values():
            if r['type'] == 'notesSlide' and r['target'] in self.z.namelist():
                root = xml(self.z, r['target'])
                out = []
                for sp in root.iter('{%s}sp' % NS['p']):
                    ph = sp.find('.//p:nvPr/p:ph', NS)
                    if ph is not None and ph.get('type') == 'body':
                        tb = sp.find('p:txBody', NS)
                        out += [''.join(t.text or '' for t in p.iter('{%s}t' % NS['a'])) for p in tb.findall('a:p', NS)]
                return '\n'.join(out)
        return ''

    # ---- charts ----
    def charts(self, i):
        """[(chart_part, graphicFrame_name)]"""
        res = []
        sr = self.srels(i)
        for gf in self.sx(i).iter('{%s}graphicFrame' % NS['p']):
            ch = gf.find('.//c:chart', NS)
            if ch is not None:
                rid = ch.get('{%s}id' % NS['r'])
                if rid in sr:
                    res.append((sr[rid]['target'], gf.find('.//p:cNvPr', NS).get('name', '')))
        return res

    def chart_info(self, part):
        root = xml(self.z, part)
        cr = rels(self.z, part)
        kinds = []
        for pa in root.findall('.//c:plotArea', NS):
            for el in pa:
                ln = el.tag.split('}')[-1]
                if ln.endswith('Chart'):
                    if ln in ('barChart', 'bar3DChart'):
                        bd = el.find('c:barDir', NS)
                        ln = ln + ':' + (bd.get('val') if bd is not None else 'col')
                    kinds.append(ln)
        ext = root.find('c:externalData', NS)
        emb = None
        ext_external = False
        if ext is not None:
            r = cr.get(ext.get('{%s}id' % NS['r']))
            if r:
                ext_external = r['external']
                emb = None if r['external'] else r['target']
        series = []
        for ser in root.iter('{%s}ser' % NS['c']):
            for tagname in ('val', 'yVal'):
                v = ser.find('c:%s' % tagname, NS)
                if v is None:
                    continue
                f = v.find('.//c:f', NS)
                pts = [(int(pt.get('idx')), pt.findtext('c:v', namespaces=NS)) for pt in v.findall('.//c:numCache/c:pt', NS)]
                series.append({'ref': f.text if f is not None else None, 'cache': pts})
        texts = [t.text for t in root.iter('{%s}t' % NS['a']) if t.text] + \
                [v.text for v in root.iter('{%s}v' % NS['c']) if v.text and v.getparent().getparent().tag.endswith('strCache')]
        return {'kinds': kinds, 'embedded': emb, 'external': ext_external, 'series': series, 'texts': texts}

    def all_charts(self):
        out = []
        for i in range(len(self.slides)):
            for part, nm in self.charts(i):
                info = self.chart_info(part)
                info.update(slide=i + 1, part=part, name=nm)
                out.append(info)
        return out

    def external_rels(self, allow=('hyperlink',)):
        bad = []
        for n in self.z.namelist():
            if n.endswith('.rels'):
                try:
                    root = xml(self.z, n)
                except Exception:
                    continue
                for r in root.findall('rel:Relationship', NS):
                    t = r.get('Type', '').rsplit('/', 1)[-1]
                    if r.get('TargetMode') == 'External' and t not in allow:
                        bad.append(f'{n}:{t}->{r.get("Target")}')
        return bad

    def missing_internal_targets(self):
        miss = []
        names = set(self.z.namelist())
        for n in names:
            if n.endswith('.rels'):
                base = posixpath.dirname(posixpath.dirname(n))
                try:
                    root = xml(self.z, n)
                except Exception:
                    continue
                for r in root.findall('rel:Relationship', NS):
                    if r.get('TargetMode') == 'External':
                        continue
                    tg = r.get('Target')
                    full = tg.lstrip('/') if tg.startswith('/') else posixpath.normpath(posixpath.join(base, tg))
                    if full not in names and not full.endswith('/'):
                        miss.append(f'{n}->{tg}')
        return miss

    # ---- timing / transitions ----
    def transition(self, i):
        """returns dict(name, dur_s, adv_s or None, adv_click)"""
        root = self.sx(i)
        tr = None
        ac = root.find('mc:AlternateContent', NS)
        if ac is not None:
            ch = ac.find('mc:Choice', NS)
            if ch is not None:
                tr = ch.find('p:transition', NS)
            if tr is None:
                fb = ac.find('mc:Fallback', NS)
                if fb is not None:
                    tr = fb.find('p:transition', NS)
        if tr is None:
            tr = root.find('p:transition', NS)
        if tr is None:
            return None
        name = None
        for el in tr:
            ln = el.tag.split('}')[-1]
            if ln not in ('sndAc', 'extLst'):
                name = ln
                break
        dur = tr.get('{%s}dur' % P14)
        if dur is not None:
            dur_s = int(dur) / 1000.0
        else:
            dur_s = {'fast': 0.5, 'med': 0.75, 'slow': 1.0}.get(tr.get('spd', 'fast'), 0.5) if name else 0.0
        adv = tr.get('advTm')
        morph = tr.find('{%s}morph' % P159) is not None
        return {'name': name, 'dur_s': dur_s, 'adv_s': int(adv) / 1000.0 if adv is not None else None,
                'adv_click': tr.get('advClick', '1') != '0', 'morph': morph}

    def timing_effects(self, i):
        """[(nodeType, presetClass, spid)] for every effect cTn"""
        root = self.sx(i)
        out = []
        tm = root.find('p:timing', NS)
        if tm is None:
            return out, False
        inter = any(c.get('nodeType') == 'interactiveSeq' for c in tm.iter('{%s}cTn' % NS['p']))
        for c in tm.iter('{%s}cTn' % NS['p']):
            if c.get('presetClass'):
                spids = {t.get('spid') for t in c.iter('{%s}spTgt' % NS['p'])}
                out.append((c.get('nodeType'), c.get('presetClass'), ','.join(sorted(x for x in spids if x))))
        return out, inter

    def timing_end(self, i):
        """rough end time (s) of the auto-run timing tree."""
        root = self.sx(i)
        tm = root.find('p:timing', NS)
        if tm is None:
            return 0.0

        def num(x):
            try:
                return int(x) / 1000.0
            except Exception:
                return 0.0

        def end(ctn):
            delay = 0.0
            st = ctn.find('p:stCondLst', NS)
            if st is not None:
                ds = [num(c.get('delay')) for c in st.findall('p:cond', NS) if c.get('delay') not in (None, 'indefinite')]
                delay = max(ds) if ds else 0.0
            kids = []
            cl = ctn.find('p:childTnLst', NS)
            if cl is not None:
                for k in cl:
                    kc = k.find('.//p:cTn', NS) if k.tag.split('}')[-1] != 'cTn' else k
                    if kc is not None:
                        kids.append((k.tag.split('}')[-1], kc))
            d = ctn.get('dur')
            own = num(d) if d not in (None, 'indefinite') else 0.0
            if not kids:
                return delay + own
            if ctn.getparent().tag.endswith('seq'):
                tot = sum(end(kc) for _, kc in kids)
            else:
                tot = max(end(kc) for _, kc in kids)
            return delay + max(own, tot)

        top = tm.find('p:tnLst/p:par/p:cTn', NS)
        return end(top) if top is not None else 0.0

    def show_props(self):
        if 'ppt/presProps.xml' not in self.z.namelist():
            return {}
        root = xml(self.z, 'ppt/presProps.xml')
        sp = root.find('p:showPr', NS)
        if sp is None:
            return {}
        return {'loop': sp.get('loop') in ('1', 'true'), 'kiosk': sp.find('p:kiosk', NS) is not None,
                'browse': sp.find('p:browse', NS) is not None, 'useTimings': sp.get('useTimings', '1') not in ('0', 'false')}

    def shapes_by_name(self, i):
        out = {}
        root = self.sx(i)
        tree = root.find('p:cSld/p:spTree', NS)
        for el in tree:
            nv = el.find('.//p:cNvPr', NS)
            if nv is None:
                continue
            off = el.find('.//a:off', NS)
            ext = el.find('.//a:ext', NS)
            txt = ''.join(t.text or '' for t in el.iter('{%s}t' % NS['a']))
            geo = (off.get('x'), off.get('y'), ext.get('cx') if ext is not None else None, ext.get('cy') if ext is not None else None) if off is not None else None
            chart = None
            c = el.find('.//c:chart', NS)
            if c is not None:
                r = self.srels(i).get(c.get('{%s}id' % NS['r']))
                if r:
                    try:
                        chart = json.dumps([s['cache'] for s in self.chart_info(r['target'])['series']])
                    except Exception:
                        chart = None
            out[nv.get('name', '')] = (el.tag.split('}')[-1], geo, txt, chart)
        return out

    def pictures(self, i):
        return len(list(self.sx(i).iter('{%s}pic' % NS['p']))) + \
            len([b for b in self.sx(i).iter('{%s}blipFill' % NS['a'])])


# ---------------- xlsx (no openpyxl) ----------------
def col2n(c):
    n = 0
    for ch in c:
        n = n * 26 + ord(ch) - 64
    return n


class Workbook:
    def __init__(self, data):
        self.z = zipfile.ZipFile(io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else str(data))
        ss = []
        if 'xl/sharedStrings.xml' in self.z.namelist():
            for si in xml(self.z, 'xl/sharedStrings.xml').findall('s:si', NS):
                ss.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['s'])))
        wb = xml(self.z, 'xl/workbook.xml')
        wr = rels(self.z, 'xl/workbook.xml')
        self.sheets = []  # (name, {ref: (value, formula)})
        for s in wb.findall('s:sheets/s:sheet', NS):
            part = wr[s.get('{%s}id' % NS['r'])]['target']
            cells = {}
            root = xml(self.z, part)
            for c in root.iter('{%s}c' % NS['s']):
                ref = c.get('r')
                t = c.get('t')
                f = c.find('s:f', NS)
                v = c.find('s:v', NS)
                isv = c.find('s:is', NS)
                val = None
                if t == 's' and v is not None:
                    val = ss[int(v.text)]
                elif t == 'inlineStr' and isv is not None:
                    val = ''.join(x.text or '' for x in isv.iter('{%s}t' % NS['s']))
                elif v is not None and v.text is not None:
                    try:
                        val = float(v.text) if t not in ('str', 'e', 'b') else v.text
                    except ValueError:
                        val = v.text
                cells[ref] = (val, (f.text if f is not None else None), f is not None)
            self.sheets.append((s.get('name'), cells))

    def sheet(self, name):
        for n, c in self.sheets:
            if n == name or n.strip("'") == name.strip("'"):
                return c
        return None

    def strings(self):
        return [str(v) for _, cells in self.sheets for (v, f, isf) in cells.values() if isinstance(v, str)]

    def numbers(self, sheet_idx=None):
        sh = self.sheets if sheet_idx is None else self.sheets[sheet_idx:sheet_idx + 1]
        return [v for _, cells in sh for (v, f, isf) in cells.values() if isinstance(v, float)]

    def formulas(self):
        return [(n, r, f) for n, cells in self.sheets for r, (v, f, isf) in cells.items() if isf]

    # -- tiny evaluator for simple arithmetic formulas --
    def eval_cell(self, sheet, ref, depth=0):
        cells = self.sheet(sheet)
        if cells is None or depth > 30:
            raise ValueError('ref')
        ref = ref.replace('$', '')
        if ref not in cells:
            return 0.0
        v, f, isf = cells[ref]
        if isf and f:
            return self.eval_formula(sheet, f, depth + 1)
        if isinstance(v, float):
            return v
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                raise ValueError('text cell %s' % ref)
        return 0.0

    def eval_formula(self, sheet, f, depth=0):
        f = f.lstrip('=')

        def rng(sh, a, b):
            ca, ra = re.match(r'([A-Z]+)(\d+)', a.replace('$', '')).groups()
            cb, rb = re.match(r'([A-Z]+)(\d+)', b.replace('$', '')).groups()
            vals = []
            for r in range(int(ra), int(rb) + 1):
                for c in range(col2n(ca), col2n(cb) + 1):
                    s = ''
                    n = c
                    while n:
                        n, m = divmod(n - 1, 26)
                        s = chr(65 + m) + s
                    cells = self.sheet(sh)
                    if cells and (s + str(r)) in cells:
                        vals.append(self.eval_cell(sh, s + str(r), depth))
            return vals

        env = {'SUM': lambda *a: sum(_flat(a)), 'AVERAGE': lambda *a: (sum(_flat(a)) / len(_flat(a))),
               'ROUND': lambda x, n=0: round(x, int(n)), 'ABS': abs, 'MIN': lambda *a: min(_flat(a)),
               'MAX': lambda *a: max(_flat(a)), 'RNG': rng, 'CELL': lambda sh, r: self.eval_cell(sh, r, depth)}
        expr = f
        sref = r"(?:'([^']+)'|([A-Za-z_][\w\.]*))!"
        expr = re.sub(sref + r"(\$?[A-Z]+\$?\d+):(\$?[A-Z]+\$?\d+)",
                      lambda m: f"RNG({json.dumps(m.group(1) or m.group(2))},'{m.group(3)}','{m.group(4)}')", expr)
        expr = re.sub(sref + r"(\$?[A-Z]+\$?\d+)",
                      lambda m: f"CELL({json.dumps(m.group(1) or m.group(2))},'{m.group(3)}')", expr)
        expr = re.sub(r"(?<![\w'\"])(\$?[A-Z]{1,3}\$?\d+):(\$?[A-Z]{1,3}\$?\d+)",
                      lambda m: f"RNG({json.dumps(sheet)},'{m.group(1)}','{m.group(2)}')", expr)
        expr = re.sub(r"(?<![\w'\"])(\$?[A-Z]{1,3}\$?\d+)(?![\w(])",
                      lambda m: f"CELL({json.dumps(sheet)},'{m.group(1)}')", expr)
        expr = expr.replace('^', '**')
        expr = re.sub(r'(\d+(?:\.\d+)?)%', r'(\1/100)', expr)
        if re.search(r'[A-Z]{2,}\(', expr) and not all(fn in env for fn in re.findall(r'([A-Z]{2,})\(', expr)):
            raise ValueError('unsupported function in ' + f)
        if re.search(r'[<>&{}]|;', expr):
            raise ValueError('unsupported syntax ' + f)
        return float(eval(expr, {'__builtins__': {}}, env))

    def formula_values(self):
        """[(sheet, ref, formula, value or None)]; value from evaluator, else cached."""
        out = []
        for n, r, f in self.formulas():
            val = None
            try:
                val = self.eval_formula(n, f or '')
            except Exception:
                c = self.sheet(n)[r][0]
                val = c if isinstance(c, float) else None
            out.append((n, r, f, val))
        return out


def _flat(a):
    o = []
    for x in a:
        if isinstance(x, (list, tuple)):
            o += _flat(x)
        else:
            o.append(x)
    return o


def find_formula_value(wbs, targets, tol):
    """wbs: [(label, Workbook)]; targets: list of acceptable values. returns (hit, n_formulas, n_unevaluated)."""
    nf = nu = 0
    for lab, wb in wbs:
        for n, r, f, v in wb.formula_values():
            nf += 1
            if v is None:
                nu += 1
                continue
            for t in targets:
                if abs(v - t) <= tol:
                    return (f'{lab}!{n}!{r} ={f} -> {v:.6g}', nf, nu)
    return (None, nf, nu)


def embedded_workbooks(deck):
    out = []
    for ch in deck.all_charts():
        if ch['embedded'] and ch['embedded'] in deck.z.namelist() and ch['embedded'].lower().endswith(('.xlsx', '.xlsm')):
            try:
                out.append((f"slide{ch['slide']}:{posixpath.basename(ch['embedded'])}", Workbook(deck.z.read(ch['embedded'])), ch))
            except Exception as e:
                out.append((f"slide{ch['slide']}:{posixpath.basename(ch['embedded'])}", None, ch))
    return out


def chart_vs_workbook(deck):
    """returns list of mismatches between numCache and embedded workbook cells."""
    mism, checked = [], 0
    for ch in deck.all_charts():
        if not ch['embedded'] or ch['embedded'] not in deck.z.namelist():
            mism.append(f"slide{ch['slide']} {ch['name']}: no embedded workbook")
            continue
        wb = Workbook(deck.z.read(ch['embedded']))
        for s in ch['series']:
            if not s['ref']:
                continue
            m = re.match(r"^(?:'([^']+)'|([^!]+))!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?$", s['ref'].strip())
            if not m:
                continue
            sh = m.group(1) or m.group(2)
            c1, r1 = col2n(m.group(3)), int(m.group(4))
            c2, r2 = (col2n(m.group(5)), int(m.group(6))) if m.group(5) else (c1, r1)
            refs = []
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    s_ = ''
                    n = c
                    while n:
                        n, k = divmod(n - 1, 26)
                        s_ = chr(65 + k) + s_
                    refs.append(s_ + str(r))
            for idx, val in s['cache']:
                if idx >= len(refs) or val is None:
                    continue
                try:
                    wv = wb.eval_cell(sh, refs[idx])
                except Exception:
                    continue
                checked += 1
                if abs(float(val) - wv) > max(1e-6, 1e-6 * abs(wv)):
                    mism.append(f"slide{ch['slide']} {sh}!{refs[idx]} plotted={val} workbook={wv:.6g}")
    return mism, checked


def words(s):
    return re.findall(r"[A-Za-z0-9][\w'’.,%°±–\-/]*", s or '')


def pdf_pagecount(p):
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(p)).pages)
    except Exception:
        o = subprocess.run(['pdfinfo', str(p)], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r'Pages:\s+(\d+)', o)
        return int(m.group(1)) if m else None


def pdf_texts(p):
    try:
        o = subprocess.run(['pdftotext', '-layout', str(p), '-'], capture_output=True, text=True, timeout=120).stdout
        return o.split('\f')
    except Exception:
        return []


def norm(s):
    s = re.sub(r'[*_#>`\[\]()|]', ' ', (s or '').lower())
    return re.sub(r'\s+', ' ', s).strip()


def bullets_per_body(deck, i):
    """max non-empty paragraph count in any body/object placeholder or text box with >1 paragraph (excludes titles, tables)."""
    worst = (0, '')
    for kind, ph, name, paras, sizes, fs in deck.shape_texts(i):
        if kind != 'sp' or ph in ('title', 'ctrTitle', 'sldNum', 'dt', 'ftr', 'subTitle'):
            continue
        n = len([p for p in paras if p.strip()])
        if n > worst[0]:
            worst = (n, name)
    return worst


def min_font(deck, i):
    m = (999, '')
    for kind, ph, name, paras, sizes, fs in deck.shape_texts(i):
        if ph in ('sldNum', 'dt', 'ftr'):
            continue
        for s in sizes:
            if s < m[0]:
                m = (s, name)
    return m


# ======================= CDC-D-X03 task-specific checks =======================
# 2026-10-25: static layout / typography / chart-axis / animation / traceability measurements come from cdc_layout.py
import cdc_layout as L
REQUIRED = ['presentation.pptx', 'slides.pdf', 'script.md', 'evidence-index.csv', 'playback-check.md']
DUR_LINE = re.compile(r'duration|estimated|est\.|time|timing|⏱', re.I)
CLICK = re.compile(r'\[\s*click[^\]]*\]|\(\s*click[^)]*\)|<\s*click[^>]*>|\bclick\s*\d*\s*[:→\-]', re.I)


def parse_dur(text):
    t = text
    m = re.search(r'(\d{1,2}):(\d{2})(?!\d)', t)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:min|mins|minutes?|m)\b(?:\s*(?:and\s*)?(\d+)\s*(?:s|sec|secs|seconds?)\b)?', t, re.I)
    if m:
        return float(m.group(1)) * 60 + (int(m.group(2)) if m.group(2) else 0)
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds?)\b', t, re.I)
    if m:
        return float(m.group(1))
    return None


def parse_script(txt):
    """-> list of dict(n, body, dur) in order, or None"""
    hs = list(re.finditer(r'^[ \t]*(?:#{1,6}[ \t]*(?:\*\*)?|\*\*)[ \t]*slide[ \t]+(\d+)\b(.*)$', txt, re.I | re.M))
    if not hs:
        hs = [h for h in re.finditer(r'^[ \t]*slide[ \t]+(\d+)\b(.*)$', txt, re.I | re.M) if len(words(h.group(2))) <= 10]
    if not hs:
        return None
    secs = []
    for k, h in enumerate(hs):
        end = hs[k + 1].start() if k + 1 < len(hs) else len(txt)
        body = txt[h.end():end]
        head = h.group(2)
        durs = []
        if parse_dur(head) is not None and DUR_LINE.search(head + ' duration'):
            durs.append(parse_dur(head))
        keep = []
        for ln in body.splitlines():
            if DUR_LINE.search(ln) and parse_dur(ln) is not None and len(words(ln)) <= 12:
                durs.append(parse_dur(ln))
                continue
            keep.append(ln)
        secs.append({'n': int(h.group(1)), 'body': CLICK.sub(' ', '\n'.join(keep)), 'durs': durs})
    return secs


def sim(a, b):
    wa, wb = norm(CLICK.sub(' ', a)).split(), norm(CLICK.sub(' ', b)).split()
    if not wa or not wb:
        return 0.0
    sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
    match = sum(bl.size for bl in sm.get_matching_blocks())
    return max(sm.ratio(), match / max(1, min(len(wa), len(wb))) if min(len(wa), len(wb)) / max(len(wa), len(wb)) > 0.8 else 0)


def run(ctx):
    out = Path(ctx['out'])
    res = {}
    ctx['_gate0'] = None
    missing = [f for f in REQUIRED if not (out / f).is_file()]
    deck = None
    try:
        if (out / 'presentation.pptx').is_file():
            from pptx import Presentation
            Presentation(str(out / 'presentation.pptx'))
            deck = Deck(out / 'presentation.pptx')
    except Exception as e:
        missing.append(f'presentation.pptx unreadable: {e}')
    if missing:
        ctx['_gate0'] = 'GATE0 failed: ' + '; '.join(missing)
    if deck is None:
        return res
    n = len(deck.slides)

    # V01 slide count + 16:9
    def v01():
        ratio = deck.cx / deck.cy
        ok = 14 <= n <= 18 and abs(ratio - 16 / 9) < 0.01
        return V('pass' if ok else 'fail', f'{n} slides, size {deck.cx}x{deck.cy} EMU ratio {ratio:.4f}')
    safe(res, 'V01', v01)

    pp = out / 'presentation.pptx'

    # V02 <=6 bullets per slide (summed over body placeholders and bulleted text boxes)
    def v02():
        bad = [f'slide {k}: {nb} bullets ({d})' for k, nb, d in L.bullets_per_slide(pp) if nb > 6]
        return V('fail', '; '.join(bad[:8])) if bad else V('pass', 'every slide has <=6 bullet paragraphs (body placeholders + '
                                                                  'bulleted text boxes; captions/source lines and diagram nodes excluded)')
    safe(res, 'V02', v02)

    # V03 effective font sizes (explicit or inherited x autofit scale): body >=20 pt, captions/source/titles/tables >=12 pt
    def v03():
        bv, sv, nr = L.font_violations(pp, 20, 12)
        if bv or sv:
            return V('fail', f'{len(bv)} body run(s) <20 pt, {len(sv)} caption/source/title/table run(s) <12 pt: ' + '; '.join((bv + sv)[:5]))
        return V('pass', f'body >=20 pt and captions/source lines/titles/tables >=12 pt at effective size ({nr} runs)')
    safe(res, 'V03', v03)

    # V04 chart axes: titles, unit on value axis, legend for >=2 series, date axis states its basis
    def v04():
        iss, nc = L.chart_axis_issues(pp, date_basis_re=r'onset|report|confirm|notif|symptom|diagnos|week|announce|publication|as of')
        if not nc:
            return V('fail', 'no native charts')
        return V('fail', '; '.join(iss[:6])) if iss else V('pass', f'{nc} charts: axes titled, value-axis units, legends, date basis stated')
    safe(res, 'V04', v04)

    # V05 static layout
    def v05():
        iss = L.layout_issues(pp, exclude_animated=True)
        return V('fail', '; '.join(iss[:6])) if iss else V('pass', 'no estimated text overflow, no shape beyond the slide edge, no overlapping text')
    safe(res, 'V05', v05)

    charts = []
    try:
        charts = deck.all_charts()
    except Exception:
        pass

    # D01 >=4 native charts incl line + column
    def d01():
        kinds = [k for c in charts for k in c['kinds']]
        line = any(k.startswith(('lineChart', 'line3DChart')) for k in kinds)
        col = any(k in ('barChart:col', 'bar3DChart:col') for k in kinds)
        ok = len(charts) >= 4 and line and col
        return V('pass' if ok else 'fail', f'{len(charts)} native charts; kinds={sorted(set(kinds))}')
    safe(res, 'D01', d01)

    wbs = []
    try:
        wbs = embedded_workbooks(deck)
    except Exception:
        pass
    good_wbs = [(l, w) for l, w, c in wbs if w is not None]

    # D02 (approximation of ChartData.Activate): every chart has an embedded, parseable workbook whose first sheet holds plotted values
    def d02():
        if not charts:
            return V('fail', 'no native charts')
        probs = []
        for c in charts:
            if c['external'] or not c['embedded'] or c['embedded'] not in deck.z.namelist():
                probs.append(f"slide{c['slide']} {c['name']}: no embedded workbook (linked={c['external']})")
                continue
            try:
                wb = Workbook(deck.z.read(c['embedded']))
            except Exception as e:
                probs.append(f"slide{c['slide']}: embedded workbook unreadable {e}")
                continue
            first = wb.numbers(0)
            vals = [float(v) for s in c['series'] for _, v in s['cache'] if v is not None]
            miss = [v for v in vals if not any(abs(v - x) <= 1e-6 * max(1, abs(v)) for x in first)]
            fvals = [fv for _, _, _, fv in wb.formula_values() if fv is not None]
            miss = [v for v in miss if not any(abs(v - x) <= 1e-6 * max(1, abs(v)) for x in fvals)]
            if not wb.sheets[0][1]:
                probs.append(f"slide{c['slide']}: first sheet empty")
            elif miss:
                probs.append(f"slide{c['slide']}: plotted values not in first sheet {miss[:4]}")
        if probs:
            return V('fail', '; '.join(probs[:6]))
        return V('pass', f'{len(charts)} charts each have an embedded workbook whose first sheet contains the plotted values '
                         '(static approximation of ChartData.Activate(); PowerPoint COM not available)')
    safe(res, 'D02', d02)

    # D03 workbook lists source file + page (fail-only)
    def d03():
        bad = []
        for l, w, c in wbs:
            if w is None:
                bad.append(l + ' unreadable')
                continue
            s = ' '.join(w.strings())
            miss = [k for k, ok in (('file', re.search(r'report|sitrep|situation report', s, re.I)),
                                    ('page', re.search(r'\bp(?:age|p)?\.?\s*\d+|\bpage', s, re.I)),
                                    ('unit', L.UNIT_STRICT.search(s))) if not ok]
            if miss:
                bad.append(f'{l} (no {"/".join(miss)})')
        if not wbs:
            return V('fail', 'no embedded chart workbooks')
        if bad:
            return V('fail', 'embedded workbook(s) without source file / page / unit text: ' + ', '.join(bad[:6]))
        return V('pass', f'{len(wbs)} embedded workbooks name the source file, a page and a unit')
    safe(res, 'D03', d03)

    # D04 derived values live formulas (fail-only: no formula in any embedded workbook)
    def d04():
        if good_wbs and not any(w.formulas() for _, w in good_wbs):
            return V('fail', 'no embedded chart workbook contains any formula; derived values cannot be live')
        if not good_wbs:
            return V('fail', 'no embedded chart workbooks')
        return None
    safe(res, 'D04', d04)

    # D05 plotted values == workbook (fail-only on mismatch)
    def d05():
        mism, checked = chart_vs_workbook(deck)
        if mism:
            return V('fail', f'{len(mism)} mismatches: ' + '; '.join(mism[:5]))
        return None
    safe(res, 'D05', d05)

    # B01 / B06 / B04 workbook formula values
    def fcheck(targets, tol, label, need_text=None):
        def f():
            hit, nf, nu = find_formula_value(good_wbs, targets, tol)
            if hit:
                if need_text:
                    alltext = ' '.join(deck.slide_text(i) + ' ' + deck.notes(i) for i in range(n))
                    if not re.search(need_text, alltext):
                        return None
                return V('pass', f'{label}: formula {hit}')
            if nu == 0:
                return V('fail', f'{label}: no embedded-workbook formula evaluates to {targets} (±{tol}); {nf} formulas checked')
            return None
        return f
    def multi(specs, label, pass_ok=True):
        def f():
            nf_all = nu_all = 0
            for targets, tol in specs:
                hit, nf, nu = find_formula_value(good_wbs, targets, tol)
                nf_all, nu_all = nf, nu
                if hit:
                    return V('pass', f'{label}: formula {hit}') if pass_ok else None
            if good_wbs and nu_all == 0:
                return V('fail', f'{label}: no embedded-workbook formula evaluates to the expected value; {nf_all} formulas checked')
            if not good_wbs:
                return V('fail', f'{label}: no embedded chart workbooks')
            return None
        return f
    # B01 crude CFR 2114/55924 = 3.78%: live workbook formula (3.78 / 0.0378, or ROUND -> 3.8 when the formula uses
    # 2114 and 55924 directly or via cells), or the formula written out in notes / evidence index / slides
    def b01():
        hit, nf, nu = find_formula_value(good_wbs, [0.0378, 3.78], 0.00011)
        if not hit:
            hit, _, _ = find_formula_value(good_wbs, [3.78], 0.011)
        if not hit:
            for l, w in good_wbs:
                for sh, ref, f, v in w.formula_values():
                    if v is not None and (abs(v - 3.8) <= 0.05 or abs(v - 0.038) <= 0.0005):
                        refs = re.findall(r'\$?([A-Z]{1,3})\$?(\d+)', f or '')
                        vals = []
                        for c_, r_ in refs:
                            try:
                                vals.append(w.eval_cell(sh, c_ + r_))
                            except Exception:
                                pass
                        if ('2114' in (f or '') or 2114 in vals) and ('55924' in (f or '') or 55924 in vals):
                            hit = f'{l}!{sh}!{ref} ={f} -> {v:.4g}'
        if hit:
            return V('pass', f'crude CFR formula {hit}')
        txt = ' '.join(deck.slide_text(i) + ' ' + deck.notes(i) for i in range(n))
        if (out / 'evidence-index.csv').is_file():
            txt += ' ' + (out / 'evidence-index.csv').read_text(encoding='utf-8', errors='replace')
        t2 = txt.replace(',', '')
        if re.search(r'2114\s*(?:/|÷|divided by)\s*55924', t2) and re.search(r'3\.78?\s*%|0\.0378', t2):
            return V('pass', 'crude CFR formula 2114/55,924 = 3.78% written out in notes/evidence index/slides')
        return V('fail', 'no live workbook formula and no written formula 2114/55,924 giving 3.78% (3.8%)')
    safe(res, 'B01', b01)
    # B06 (2478-409)/2478 = 83.5%: formula absent -> fail; present -> labelling judged by model
    safe(res, 'B06', multi([([0.835], 0.0011), ([83.5], 0.11)], 'daily-new decline', pass_ok=False))

    def b04():
        alltxt = ' '.join(deck.slide_text(i) + ' ' + deck.notes(i) for i in range(n)) + ' ' + \
            ' '.join(t for c in charts for t in c['texts'])
        if not re.search(r'per\s*100[,\s]?000|/\s*100[,\s]?000|per\s*100\s*k|per\s*10[,\s]?000|/\s*10\s*万|10\s*万', alltxt, re.I):
            return V('pass', 'conditional: no population rate (per 100,000 / per 10,000) shown')
        hit, nf, nu = find_formula_value(good_wbs, [104.8], 0.1)
        hit2, _, _ = find_formula_value(good_wbs, [1.17], 0.01)
        h = hit or hit2
        if h:
            alltext = ' '.join(deck.slide_text(i) for i in range(n))
            if re.search(r'104\.8|1\.17', alltext):
                return V('pass', f'per-100k rate formula {h}; value shown on slide')
        return None  # other provinces / rates may be valid -> judge
    safe(res, 'B04', b04)

    # D08 / D09 click build on one slide
    def build():
        best = (0, 0)
        for i in range(n):
            eff, inter = deck.timing_effects(i)
            sp = {s for nt, pc, s in eff if nt == 'clickEffect' and pc == 'entr' and s}
            if len(sp) > best[0]:
                best = (len(sp), i + 1)
        return best
    def d08():
        k, sl = build()
        if k >= 3:
            return V('pass', f'slide {sl}: {k} on-click entrance effects on distinct shapes')
        return V('fail', f'max on-click entrance effects on distinct shapes on any slide = {k}')
    safe(res, 'D08', d08)
    def d09():
        k, sl = build()
        if k < 3:
            return V('fail', f'no slide with >=3 on-click entrance effects (max {k})')
        tl = L.timeline(L.Pkg(pp), sl - 1)
        root = deck.sx(sl - 1)
        tm = root.find('p:timing', NS)
        # click groups of the main sequence: a group whose start condition is not 'indefinite' runs on entry
        groups = []
        if tm is not None:
            for c in tm.iter('{%s}cTn' % NS['p']):
                if c.get('nodeType') == 'mainSeq':
                    for par in c.findall('p:childTnLst/p:par', NS):
                        cond = par.find('p:cTn/p:stCondLst/p:cond', NS)
                        groups.append(cond is not None and cond.get('delay') == 'indefinite')
        first_ent, probs = {}, []
        for g, (effs, is_click) in enumerate(zip(tl['main'], groups)):
            for e in effs:
                if e['cls'] == 'entr' and e['spid'] not in first_ent:
                    first_ent[e['spid']] = (g, is_click)
                if e['cls'] == 'exit' and e['spid'] in first_ent and g < len(tl['main']) - 1:
                    probs.append(f'shape {e["spid"]} exits at step {g + 1} before the build ends')
        on_entry = [s_ for s_, (g, c) in first_ent.items() if not c]
        clicks = [g for s_, (g, c) in first_ent.items() if c]
        per_click = sorted(set(clicks))
        if on_entry:
            probs.append(f'shapes {on_entry} are revealed automatically on slide entry')
        if len(per_click) < 3:
            probs.append(f'only {len(per_click)} distinct click steps reveal a new shape')
        if probs:
            return V('fail', f'slide {sl}: ' + '; '.join(probs[:4]))
        return V('pass', f'slide {sl}: {len(per_click)} successive clicks each reveal new shape(s); none visible on entry (static timing analysis)')
    safe(res, 'D09', d09)

    # V06 no occlusion in any click state of the curve-turn (build) slide
    def v06():
        k, sl = build()
        if k < 1:
            return V('fail', 'no click-build slide to check')
        iss, nchk = L.animation_occlusion(pp, slides=[sl])
        return V('fail', '; '.join(iss[:6])) if iss else V('pass', f'slide {sl}: no overlap in any click state ({nchk} animated pairs checked)')
    safe(res, 'V06', v06)

    # D11 pdf pages + notes vs script
    def d11():
        pc = pdf_pagecount(out / 'slides.pdf') if (out / 'slides.pdf').is_file() else None
        if pc != n:
            return V('fail', f'slides.pdf pages={pc} vs pptx slides={n}')
        if not (out / 'script.md').is_file():
            return V('fail', 'script.md missing')
        secs = parse_script((out / 'script.md').read_text(encoding='utf-8', errors='replace'))
        if not secs or len(secs) != n:
            return None
        sims = [(s['n'], sim(s['body'], deck.notes(s['n'] - 1) if 1 <= s['n'] <= n else '')) for s in secs]
        low = [x for x in sims if x[1] < 0.9]
        if not low:
            return V('pass', f'pdf pages={n}; notes~script min similarity {min(x[1] for x in sims):.2f}')
        if any(x[1] < 0.6 for x in low):
            return V('fail', 'notes vs script low similarity: ' + ', '.join(f's{a}={b:.2f}' for a, b in low[:6]))
        return None
    safe(res, 'D11', d11)

    # D13 no external links, embedded chart data
    def d13():
        bad = deck.external_rels()
        nolink = [c for c in charts if c['external'] or not c['embedded']]
        if bad or nolink:
            return V('fail', f'external rels {bad[:4]}; charts without embedded data {len(nolink)}')
        miss = deck.missing_internal_targets()
        if miss:
            return V('fail', 'broken internal relationships: ' + '; '.join(miss[:4]))
        return V('pass', 'no external (non-hyperlink) relationships; all chart data embedded; all internal parts present '
                         '(static check; PowerPoint reopen not possible on Linux)')
    safe(res, 'D13', d13)

    # D14 AI disclosure (fail-only)
    def d14():
        txt = ' '.join(deck.slide_text(i) for i in range(n))
        if not re.search(r'\bAI\b|artificial intelligence|A\.I\.|language model|LLM', txt):
            return V('fail', 'no AI-production disclosure in slide text')
        return None
    safe(res, 'D14', d14)

    # N06 script timing
    def n06():
        p = out / 'script.md'
        if not p.is_file():
            return V('fail', 'script.md missing')
        secs = parse_script(p.read_text(encoding='utf-8', errors='replace'))
        if not secs or any(len(s['durs']) != 1 for s in secs):
            return None
        T = sum(s['durs'][0] for s in secs) / 60.0
        W = sum(len(words(s['body'])) for s in secs)
        ok = 12 <= T <= 15 and 0.75 * W / 160 <= T <= 1.25 * W / 130
        return V('pass' if ok else 'fail', f'declared total {T:.2f} min over {len(secs)} slides; script words W={W}; '
                                           f'bounds [{0.75 * W / 160:.2f}, {1.25 * W / 130:.2f}]')
    safe(res, 'N06', n06)

    # F01-F14 (fail-only + machine trace appended to verify for the judge)
    try:
        res.update(L.fidelity(ctx, pp, {f'F{k:02d}': [k] for k in range(1, 15)}, out / 'evidence-index.csv'))
    except Exception as e:
        for k in range(1, 15):
            res[f'F{k:02d}'] = V('fail', f'check error: {type(e).__name__}: {e}')

    # group gates (static approximations): GATE-PPT package integrity, GATE-CHART embedded workbooks parseable
    ctx['_gate_ppt'] = L.integrity(pp)
    bad_ch = [f"slide{c['slide']} {c['name']}" for c in charts if c['external'] or not c['embedded'] or c['embedded'] not in deck.z.namelist()]
    bad_ch += [l for l, w, c in wbs if w is None]
    ctx['_gate_chart'] = bad_ch
    return res


def postprocess(results, ctx):
    g = ctx.get('_gate0')
    if g:
        for it in ctx['items']:
            results[it['id']] = {'verdict': 'fail', 'detail': g, 'source': 'checks'}
        results['_gate0'] = {'verdict': 'fail', 'detail': g}
        return results
    iss = ctx.get('_gate_ppt') or []
    if iss:
        why = 'GATE-PPT (static package integrity, approximates the PowerPoint repair prompt): ' + '; '.join(iss[:6])
        for it in ctx['items']:
            if it.get('group') == 'G6' or it['id'] in ('V03', 'V05', 'V06'):
                results[it['id']] = {'verdict': 'fail', 'detail': why, 'source': 'gate'}
        results['_gate_ppt'] = {'verdict': 'fail', 'detail': why}
    bad = ctx.get('_gate_chart') or []
    if bad:
        why = 'GATE-CHART (static approximation of ChartData.Activate: chart without a parseable embedded workbook): ' + ', '.join(bad[:6])
        for iid in ('D02', 'D03', 'D04', 'D05', 'D06', 'D07'):
            results[iid] = {'verdict': 'fail', 'detail': why, 'source': 'gate'}
        results['_gate_chart'] = {'verdict': 'fail', 'detail': why}
    return results
