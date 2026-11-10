# -*- coding: utf-8 -*-
"""CDC-D-X05 deterministic checks (Harbor verifier).

Only items that can be measured reliably from the files are decided here; everything that needs
reading/judgement is left to the review model.  Some items are "fail-only": the check returns
"fail" when a hard, measurable requirement is violated, and otherwise returns nothing so the model
decides the remaining (semantic) part.  Every check is wrapped so that an exception turns that one
item into "fail" with a detail string, never a crash.
"""
import csv, difflib, io, json, re, subprocess, zipfile
from pathlib import Path

REQ = ['presentation.pptx', 'slides.pdf', 'script.md', 'scenario-data.xlsx', 'evidence-index.csv', 'playback-check.md']
CASE_ALIASES = {
    'cb2026': ['counterfactual baseline', 'baseline', 'reference'],
    'highmacro': ['high economic growth', 'high econ', 'highmacro'],
    'lowmacro': ['low economic growth', 'low econ', 'lowmacro'],
    'highogs': ['high oil and gas supply', 'high oil & gas supply', 'high ogs', 'highogs'],
    'lowogs': ['low oil and gas supply', 'low oil & gas supply', 'low ogs', 'lowogs'],
    'highZTC': ['high zero-carbon technology cost', 'high zero carbon technology cost', 'high ztc', 'highztc'],
    'lowZTC': ['low zero-carbon technology cost', 'low zero carbon technology cost', 'low ztc', 'lowztc'],
    'electrnp': ['combination', 'alternative electricity and alternative transportation', 'electrnp'],
    'altelec': ['alternative electricity', 'alt elec', 'altelec'],
    'alttrnp': ['alternative transportation', 'alt trnp', 'alttrnp', 'alt transportation'],
    'higheldmd': ['high electricity demand', 'high elec demand', 'higheldmd', 'high eldmd'],
}
# 2026-10-25: common short forms used by the material/solvers
CASE_ALIASES['highmacro'] += ['highecon', 'high econ growth', 'high economic']
CASE_ALIASES['lowmacro'] += ['lowecon', 'low econ growth', 'low economic']
CASE_ALIASES['highogs'] += ['high oil and gas']
CASE_ALIASES['lowogs'] += ['low oil and gas']
CASE_ALIASES['higheldmd'] += ['high electricity demand']
EMU_PER_PT = 12700


def _norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^0-9a-z ]+', ' ', (s or '').lower())).strip()


def _sh(cmd, timeout=120):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception as e:
        return ''


def _load(ctx):
    out = Path(ctx['out'])
    st = {'out': out, 'prs': None, 'err': None}
    p = out / 'presentation.pptx'
    if p.exists():
        try:
            from pptx import Presentation
            st['prs'] = Presentation(str(p))
            if len(st['prs'].slides) == 0:
                st['err'] = 'pptx has no slides'
        except Exception as e:
            st['err'] = f'python-pptx cannot open: {e}'
    else:
        st['err'] = 'presentation.pptx missing'
    return st


def _title(slide):
    try:
        if slide.shapes.title is not None and slide.shapes.title.has_text_frame:
            return slide.shapes.title.text_frame.text.strip()
    except Exception:
        pass
    return ''


def _iter_shapes(shapes):
    for sh in shapes:
        yield sh
        if sh.shape_type == 6:  # group
            try:
                yield from _iter_shapes(sh.shapes)
            except Exception:
                pass


def _notes(slide):
    try:
        if slide.has_notes_slide:
            return slide.notes_slide.notes_text_frame.text.strip()
    except Exception:
        pass
    return ''


def _script_segments(text, n):
    """Split script.md into per-slide segments by headings mentioning 'Slide <k>'."""
    marks = [(m.start(), int(m.group(1))) for m in re.finditer(r'(?im)^\s*#{1,6}[^\n]*?slide\s*(\d+)[^\n]*$', text)]
    if not marks:
        marks = [(m.start(), int(m.group(1))) for m in re.finditer(r'(?im)^\s*\**\s*slide\s*(\d+)\b[^\n]*$', text)]
    segs = {}
    for i, (pos, k) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        segs.setdefault(k, text[pos:end])
    return segs if len(segs) >= n else None


def _seg_seconds(seg):
    head = seg.split('\n', 1)[0] + '\n' + '\n'.join(l for l in seg.split('\n')[1:6] if re.search(r'(?i)time|duration|timing|\bs\b|sec|min', l))
    m = re.search(r'(?i)(\d+)\s*(?:min|m)\s*(\d+)\s*(?:s|sec)', head)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r'(?<![\d:])(\d{1,2}):(\d{2})(?![\d:])', head)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r'(?i)(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)\b', head)
    if m:
        return float(m.group(1))
    m = re.search(r'(?i)(\d+(?:\.\d+)?)\s*(?:min|mins|minutes)\b', head)
    if m:
        return float(m.group(1)) * 60
    return None


def _strip_md(s):
    s = re.sub(r'(?m)^\s*#{1,6}.*$', ' ', s)
    s = re.sub(r'[*_`>#\[\]()|-]', ' ', s)
    return _norm(s)


def _sim(a, b):
    a, b = _strip_md(a).split(), _strip_md(b).split()
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def _sheet_formulas(xlsx_bytes):
    z = zipfile.ZipFile(io.BytesIO(xlsx_bytes))
    nf = nv = 0
    for n in z.namelist():
        if re.match(r'xl/worksheets/sheet\d*\.xml$', n):
            x = z.read(n).decode('utf-8', 'ignore')
            nf += len(re.findall(r'<f[ >]', x))
            nv += len(re.findall(r'<c [^>]*>', x))
    return nf, nv


# ============================================================================================
# 2026-10-25 rubric cleanup: shared measurement helpers (source tables, numbers, charts, fonts,
# package integrity).  All helpers are defensive; callers are wrapped by guard().
# ============================================================================================
import math, posixpath, random
import xml.etree.ElementTree as ET


# ---------------- minimal read-only xlsx reader (the real verifier image has no openpyxl) ----------------
_XNS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
_XRNS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def _xl_col(s):
    n = 0
    for ch in s:
        n = n * 26 + ord(ch) - 64
    return n


def _xl_num(t):
    t = (t or '').strip()
    if '.' in t or 'E' in t or 'e' in t:
        return float(t)
    return int(t)


class _XlSheet:
    """cells of one worksheet: values as openpyxl(read_only, data_only) returns them for numbers/strings/bools."""

    def __init__(self, title, root, shared):
        self.title = title
        self.cells = {}
        rmax = cmax = 0
        rr = 0
        for row in root.iter(_XNS + 'row'):
            rr = int(row.get('r')) if row.get('r') else rr + 1
            cc = 0
            for c in row.findall(_XNS + 'c'):
                ref = c.get('r')
                if ref:
                    m = re.match(r'([A-Z]+)(\d+)$', ref)
                    cc, r = _xl_col(m.group(1)), int(m.group(2))
                else:
                    cc, r = cc + 1, rr
                t = c.get('t') or 'n'
                v = c.find(_XNS + 'v')
                val = None
                try:
                    if t == 's' and v is not None:
                        val = shared[int(v.text)]
                    elif t == 'inlineStr':
                        is_ = c.find(_XNS + 'is')
                        val = _xl_text(is_) if is_ is not None else None
                    elif t == 'b' and v is not None:
                        val = v.text.strip() in ('1', 'true')
                    elif t in ('str', 'e', 'd') and v is not None:
                        val = v.text
                    elif v is not None and v.text is not None and v.text.strip():
                        val = _xl_num(v.text)
                except Exception:
                    val = v.text if v is not None else None
                if val is not None:
                    self.cells[(r, cc)] = val
                    rmax, cmax = max(rmax, r), max(cmax, cc)
        self.max_row, self.max_column = rmax, cmax

    def iter_rows(self, values_only=True):
        for r in range(1, self.max_row + 1):
            yield tuple(self.cells.get((r, c)) for c in range(1, self.max_column + 1))

    def __getitem__(self, ref):
        m = re.match(r'\$?([A-Z]+)\$?(\d+)$', ref)

        class _Cell:
            value = self.cells.get((int(m.group(2)), _xl_col(m.group(1))))
        return _Cell


def _xl_text(el):
    """text of a shared/inline string item without phonetic runs."""
    out = []
    for ch in el:
        tag = ch.tag
        if tag == _XNS + 't':
            out.append(ch.text or '')
        elif tag == _XNS + 'r':
            out += [t.text or '' for t in ch.findall(_XNS + 't')]
    return ''.join(out)


class _XlBook:
    def __init__(self, path):
        with zipfile.ZipFile(str(path)) as z:
            names = set(z.namelist())
            shared = []
            if 'xl/sharedStrings.xml' in names:
                shared = [_xl_text(si) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(_XNS + 'si')]
            rels = {}
            if 'xl/_rels/workbook.xml.rels' in names:
                for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')):
                    tgt = r.get('Target') or ''
                    tgt = tgt.lstrip('/') if tgt.startswith('/') else posixpath.normpath('xl/' + tgt)
                    rels[r.get('Id')] = tgt
            self.worksheets = []
            wb = ET.fromstring(z.read('xl/workbook.xml'))
            for s in wb.iter(_XNS + 'sheet'):
                part = rels.get(s.get(_XRNS + 'id'))
                if part in names:
                    self.worksheets.append(_XlSheet(s.get('name'), ET.fromstring(z.read(part)), shared))
        self.sheetnames = [w.title for w in self.worksheets]

    def __getitem__(self, name):
        for w in self.worksheets:
            if w.title == name:
                return w
        raise KeyError(name)

    def close(self):
        pass


def _load_xlsx(path):
    return _XlBook(path)

_NUM_RX = re.compile(r'(?<![\w.])[-+−–]?\d[\d,]*(?:\.\d+)?|(?<![\w.])[-+−]?\.\d+')
SCALES = (1.0, 1e-3, 1e3, 1e-2, 1e2, 3.412e-3)
DENOMS = ((8, 'ESD000:ga_TotalElectric'), (2, 'QUA000:ga_DeliveredEner'), (1, 'SUP000:fa_Total'))
TABLE_NS = (1, 2, 3, 8, 20)
_SRC = {}


class GraderError(Exception):
    """Problem on the grader side (hidden inputs unreadable): re-raised so that no reward is written."""


def _case_of(text):
    """Map a label to one case key (None if no / ambiguous match)."""
    line = _norm(text)
    if not line:
        return None
    for a in CASE_ALIASES['electrnp']:
        if re.search(r'\b' + re.escape(a) + r'\b', line):
            return 'electrnp'
    hits = []
    for k, al in CASE_ALIASES.items():
        if k == 'electrnp':
            continue
        for a in al:
            if re.search(r'\b' + re.escape(a) + r'\b', line):
                hits.append(k)
                break
    hits = list(dict.fromkeys(hits))
    if len(hits) == 1:
        return hits[0]
    # 'baseline' often appears as a comparison word next to a real case name
    if len(hits) == 2 and 'cb2026' in hits and not re.search(r'counterfactual', line):
        return [h for h in hits if h != 'cb2026'][0]
    return None


def _nums(text):
    """All numbers in a string -> [(value, decimals)]. Thousands commas are removed."""
    out = []
    for m in _NUM_RX.finditer(text or ''):
        raw = m.group(0).replace('−', '-').replace('–', '-')
        neg = raw.startswith('-')
        raw = raw.lstrip('+-')
        if ',' in raw and not re.fullmatch(r'\d{1,3}(,\d{3})+(\.\d+)?', raw):
            raw = raw.replace(',', '')
        raw = raw.replace(',', '')
        try:
            v = float(raw)
        except ValueError:
            continue
        dec = len(raw.split('.', 1)[1]) if '.' in raw else 0
        out.append((-v if neg else v, dec))
    return out


def _tol(dec):
    return 0.5 * 10 ** (-dec) * 1.0001 + 1e-9


def _src_case(ctx, case):
    """{(tableN, rowid): {'label': str, 'y': {year: v}, 'aac': v}} from input/tables/<case>_table<N>.xlsx."""
    if case in _SRC:
        return _SRC[case]
    rows = {}
    base = Path(ctx.get('input') or '') / 'tables'
    for n in TABLE_NS:
        p = base / f'{case}_table{n}.xlsx'
        if not p.exists():
            continue
        for attempt in range(3):
            try:
                wb = _load_xlsx(p)
                break
            except Exception as e:  # grader-side input problem: must surface, never become a solver fail
                if attempt == 2:
                    raise GraderError(f'cannot read source table {p}: {e}')
        ws = wb.worksheets[0]
        ycol, aac = {}, None
        for r in ws.iter_rows(values_only=True):
            r = list(r)
            if not ycol:
                if len(r) > 3 and r[2] == 2025:
                    for j, v in enumerate(r):
                        if isinstance(v, int) and 2000 <= v <= 2100:
                            ycol[j] = v
                    aac = max(ycol) + 1 if ycol else None
                continue
            rid = r[0] if r else None
            if not isinstance(rid, str) or ':' not in rid:
                continue
            y = {yr: float(r[j]) for j, yr in ycol.items() if j < len(r) and isinstance(r[j], (int, float))}
            if not y:
                continue
            a = r[aac] if aac is not None and aac < len(r) and isinstance(r[aac], (int, float)) else None
            rows[(n, rid)] = {'label': str(r[1] or '').strip(), 'y': y, 'aac': a}
        wb.close()
    _SRC[case] = rows
    return rows


def _feat_val(ctx, case, key, kind, year=None):
    """Value of a feature for one case, or None."""
    src = _src_case(ctx, case)
    row = src.get(key)
    if not row:
        return None
    y = row['y']
    try:
        if kind == 'y':
            return y.get(year)
        if kind == 'aac':
            return None if row['aac'] is None else row['aac'] * 100
        if kind == 'growth':
            return (y[2050] / y[2025] - 1) * 100
        if kind == 'cagr':
            return ((y[2050] / y[2025]) ** (1 / 25) - 1) * 100
        if kind == 'mean':
            vals = [y[k] for k in range(2025, 2051) if k in y]
            return sum(vals) / len(vals) if len(vals) == 26 else None
        if kind in ('vsb_pct', 'vsb_diff'):
            b = _src_case(ctx, 'cb2026').get(key)
            if not b:
                return None
            yr = year or 2050
            return (y[yr] / b['y'][yr] - 1) * 100 if kind == 'vsb_pct' else y[yr] - b['y'][yr]
        if kind.startswith('share'):
            yr = year or (2025 if kind.endswith('25') else 2050)
            dk = DENOMS[int(kind.split(':')[1])] if ':' in kind else DENOMS[0]
            d = src.get(dk)
            return y[yr] / d['y'][yr] * 100 if d and d['y'].get(yr) else None
    except (KeyError, ZeroDivisionError, TypeError, ValueError):
        return None
    return None


def _kinds(year):
    if year is None:
        ks = [('y', 2025), ('y', 2050), ('aac', None), ('growth', None), ('cagr', None), ('mean', None),
              ('vsb_pct', None), ('vsb_diff', None)]
        for i in range(len(DENOMS)):
            ks += [('share50:%d' % i, None), ('share25:%d' % i, None)]
        return ks
    ks = [('y', year), ('vsb_pct', year), ('vsb_diff', year)]
    for i in range(len(DENOMS)):
        ks.append(('share:%d' % i, year))
    return ks


def _fit(ctx, obs, year_of=None, min_cov=0.6):
    """obs: [(case, value, decimals, year_or_None)].  Find the source feature (table row, kind, scale) that
    reproduces the most observations within displayed rounding.  Returns (best, matched_idx, total) where best is
    (key, kind, scale, label) or None."""
    if not obs:
        return None, set(), 0
    keys = set()
    for c in {o[0] for o in obs}:
        keys |= set(_src_case(ctx, c).keys())
    best, bestm = None, set()
    years = {o[3] for o in obs}
    for key in sorted(keys):
        for kind, kyear in _kinds(None if years == {None} else 0):
            vals = []
            for (c, v, d, yr) in obs:
                if kyear == 0:  # per-observation year
                    vals.append(_feat_val(ctx, c, key, kind, yr) if yr else None)
                else:
                    vals.append(_feat_val(ctx, c, key, kind, kyear))
            if all(x is None for x in vals):
                continue
            for s in SCALES:
                m = {i for i, ((c, v, d, yr), f) in enumerate(zip(obs, vals))
                     if f is not None and abs(v - s * f) <= _tol(d) + 1e-6 * abs(v)}
                if len(m) > len(bestm):
                    best, bestm = (key, kind if kyear in (0, None) else f'{kind}@{kyear}', s,
                                   _src_case(ctx, 'cb2026').get(key, {}).get('label', '')), m
                    if len(m) == len(obs):
                        return best, bestm, len(obs)
    if best is None or len(bestm) < max(2, min_cov * len(obs)):
        return None, bestm, len(obs)
    return best, bestm, len(obs)


def _orient(cells):
    """Return (case_rows_map, cells_used, transposed).  Supports cases as rows (normal) or as columns."""
    def hits(cs):
        h = {}
        for ri, row in enumerate(cs):
            for cell in row[:2]:
                k = _case_of(cell)
                if k and k not in h:
                    h[k] = ri
                    break
        return h
    h1 = hits(cells)
    width = max((len(r) for r in cells), default=0)
    tcells = [[(r[j] if j < len(r) else '') for r in cells] for j in range(width)]
    h2 = hits(tcells)
    if len(h2) > len(h1):
        return h2, tcells, True
    return h1, cells, False


def _best_table(tables):
    best = None
    for i, sh, cells in tables:
        h, cs, tr = _orient(cells)
        sc = len(h)
        if best is None or sc > best[0]:
            best = (sc, i, sh, cs, h, tr)
    return best


def _table_columns(cs, h):
    """For a case-row-oriented table: [(col_index, header_text, [(case, value, decimals)])]."""
    case_ri = set(h.values())
    hdr_rows = [r for ri, r in enumerate(cs) if ri not in case_ri and ri < min(case_ri or {0})]
    width = max(len(r) for r in cs)
    cols = []
    for j in range(1, width):
        head = ' '.join(r[j] for r in hdr_rows if j < len(r))
        obs = []
        for k, ri in h.items():
            row = cs[ri]
            if j >= len(row):
                continue
            ns = _nums(row[j])
            if row[j].strip() and ns and _case_of(row[j]) is None:
                v, d = ns[0]
                obs.append((k, v, d))
        if obs:
            cols.append((j, head, obs))
    return cols


def _col_year(head):
    """2025 / 2050 / None (unknown) from a header; '2025' used as price basis is ignored."""
    t = re.sub(r'(?i)\b2025\s*(?:\$|¢|c\b|cents?|dollars?|usd|us\$|real|constant)', ' ', head or '')
    t = re.sub(r'(?i)(?:\$|dollars?|cents?|usd)\s*(?:of\s*)?2025\b', ' ', t)
    has25, has50 = bool(re.search(r'\b2025\b', t)), bool(re.search(r'\b2050\b', t))
    if re.search(r'(?i)chang|growth|cagr|%/y|per year|/yr|vs\.?|Δ|delta|diff|relative|share', t):
        return None
    if has25 and not has50:
        return 2025
    if has50 and not has25:
        return 2050
    return None


def _table_fit(ctx, cs, h):
    """Fit every numeric column of the native table to a source feature.  Returns list of dicts."""
    res = []
    for j, head, obs in _table_columns(cs, h):
        yr = _col_year(head)
        o4 = [(c, v, d, None) for c, v, d in obs]
        best, m, n = _fit(ctx, o4)
        if best and yr and best[1] in ('y@2025', 'y@2050') and best[1] != f'y@{yr}':
            pass  # header year label disagrees with the fitted year; reported below as a mismatch hint
        res.append({'col': j, 'head': head, 'obs': obs, 'best': best, 'matched': m, 'n': n, 'year': yr})
    return res


# ---------------- charts ----------------
_C = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
_A = 'http://schemas.openxmlformats.org/drawingml/2006/main'


def _year_of(x):
    try:
        f = float(str(x).strip())
        if f.is_integer() and 1990 <= f <= 2060:
            return int(f)
    except (TypeError, ValueError):
        pass
    m = re.fullmatch(r'\s*(\d{4})\s*', str(x))
    return int(m.group(1)) if m and 1990 <= int(m.group(1)) <= 2060 else None


def _chart_series(ch):
    """[{name, cats, vals, fmt, el, plot_el, idx}] for every series of a chart."""
    out = []
    for pl in ch.plots:
        try:
            cats = [str(c) for c in pl.categories]
        except Exception:
            cats = []
        for se in pl.series:
            try:
                vals = list(se.values)
            except Exception:
                vals = []
            fc = se._element.findall('.//{%s}val//{%s}formatCode' % (_C, _C))
            out.append({'name': (se.name or '').strip(), 'cats': cats, 'vals': vals,
                        'fmt': fc[0].text if fc and fc[0].text else 'General', 'el': se._element,
                        'plot_el': pl._element, 'idx': len(out)})
    return out


def _chart_points(ch, title=''):
    """Case-mapped points: [(case, year_or_None, value, series_index)].  Also returns orientation."""
    pts, orient = [], None
    sers = _chart_series(ch)
    for s in sers:
        sc = _case_of(s['name'])
        cat_cases = [_case_of(c) for c in s['cats']]
        cat_years = [_year_of(c) for c in s['cats']]
        if sc and any(cat_years):
            orient = 'series=case'
            for v, yr in zip(s['vals'], cat_years):
                if v is not None and yr:
                    pts.append((sc, yr, float(v), s['idx']))
        elif sum(1 for c in cat_cases if c) >= 2:
            orient = 'cat=case'
            yr = _year_of(re.findall(r'\b(20[2-5]\d)\b', s['name'])[0]) if re.findall(r'\b(20[2-5]\d)\b', s['name']) else None
            for v, c in zip(s['vals'], cat_cases):
                if v is not None and c:
                    pts.append((c, yr, float(v), s['idx']))
        elif sc:
            orient = 'series=case'
            for v in s['vals']:
                if v is not None:
                    pts.append((sc, None, float(v), s['idx']))
    return pts, sers, orient


def _chart_title(ch):
    try:
        return ch.chart_title.text_frame.text if ch.has_title else ''
    except Exception:
        return ''


def _axis_title(ax):
    try:
        return ax.axis_title.text_frame.text if ax.has_title else ''
    except Exception:
        return ''


def _wb_strings_numbers(blob):
    """(strings, numbers) of an embedded xlsx (all sheets), parsed from the zip without openpyxl."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = z.namelist()
    shared = []
    if 'xl/sharedStrings.xml' in names:
        root = ET.fromstring(z.read('xl/sharedStrings.xml'))
        ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
        for si in root.findall(ns + 'si'):
            shared.append(''.join(t.text or '' for t in si.iter(ns + 't')))
    strs, nums = [], []
    for n in names:
        if not re.match(r'xl/worksheets/sheet\d*\.xml$', n):
            continue
        root = ET.fromstring(z.read(n))
        ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
        for c in root.iter(ns + 'c'):
            t = c.get('t')
            v = c.find(ns + 'v')
            if t == 's' and v is not None:
                try:
                    strs.append(shared[int(v.text)])
                except Exception:
                    pass
            elif t == 'inlineStr':
                strs.append(''.join(x.text or '' for x in c.iter(ns + 't')))
            elif t == 'str' and v is not None:
                strs.append(v.text or '')
            elif v is not None and v.text is not None:
                try:
                    nums.append(float(v.text))
                except ValueError:
                    strs.append(v.text)
    return strs, nums


def _fill_of(el):
    """Colour id of the first solid fill / line fill under a c:spPr child of el, or None."""
    sp = el.find('{%s}spPr' % _C)
    if sp is None:
        return None
    for path in ('{%s}solidFill' % _A, '{%s}ln/{%s}solidFill' % (_A, _A)):
        f = sp.find(path)
        if f is not None and len(f):
            c = f[0]
            return '%s:%s' % (c.tag.rsplit('}', 1)[-1], c.get('val'))
    return None


def _fmt_display(v, fmt):
    """Approximate the displayed number for an Excel number format (decimals only)."""
    f = (fmt or 'General').split(';')[0]
    if f.lower() == 'general':
        return None
    m = re.search(r'0\.(0+)', f)
    d = len(m.group(1)) if m else 0
    if '%' in f:
        v = v * 100
    return round(v, d), d


# ---------------- fonts ----------------
def _lvl_sz(lst, lvl):
    if lst is None:
        return None
    e = lst.find('{%s}lvl%dpPr' % (_A, lvl + 1))
    if e is not None:
        d = e.find('{%s}defRPr' % _A)
        if d is not None and d.get('sz'):
            return int(d.get('sz')) / 100.0
    return None


def _eff_size(run, para, sh, prs):
    """Effective run size in pt (explicit -> shape lstStyle -> layout/master placeholder -> master txStyles /
    presentation defaultTextStyle -> 18 pt), times normAutofit fontScale."""
    lvl = para.level or 0
    size = run.font.size.pt if run.font.size is not None else None
    txb = sh.text_frame._txBody
    if size is None:
        size = _lvl_sz(txb.find('{%s}lstStyle' % _A), lvl)
    if size is None and getattr(sh, 'is_placeholder', False):
        try:
            base = sh._base_placeholder
            depth = 0
            while base is not None and size is None and depth < 3:
                if base.has_text_frame:
                    size = _lvl_sz(base.text_frame._txBody.find('{%s}lstStyle' % _A), lvl)
                base = getattr(base, '_base_placeholder', None)
                depth += 1
        except Exception:
            pass
        if size is None:
            try:
                pht = str(sh.placeholder_format.type)
                master = sh.part.slide.slide_layout.slide_master if hasattr(sh.part, 'slide') else None
            except Exception:
                pht, master = '', None
            try:
                master = sh.part.slide_layout.slide_master
            except Exception:
                pass
            if master is not None:
                ts = master._element.find('{http://schemas.openxmlformats.org/presentationml/2006/main}txStyles')
                if ts is not None:
                    tag = 'titleStyle' if 'TITLE' in pht else ('bodyStyle' if ('BODY' in pht or 'OBJECT' in pht) else 'otherStyle')
                    size = _lvl_sz(ts.find('{http://schemas.openxmlformats.org/presentationml/2006/main}%s' % tag), lvl)
    if size is None:
        try:
            dts = prs.part._element.find('{http://schemas.openxmlformats.org/presentationml/2006/main}defaultTextStyle')
            size = _lvl_sz(dts, lvl)
        except Exception:
            size = None
    if size is None:
        size = 18.0
    bp = txb.find('{%s}bodyPr' % _A)
    if bp is not None:
        na = bp.find('{%s}normAutofit' % _A)
        if na is not None and na.get('fontScale'):
            size = size * int(na.get('fontScale')) / 100000.0
    return size


_CAPTION_RX = re.compile(r'(?i)^\s*(sources?|notes?|data|credit|prepared|ai[- ]assisted|figure|fig\.|chart)\b')


def _frame_kind(sh, prs, title_id):
    """'title' | 'body' | 'caption' | 'label' for a text-bearing shape."""
    if title_id is not None and sh.shape_id == title_id:
        return 'title'
    paras = [p for p in sh.text_frame.paragraphs if p.text.strip()]
    if not paras:
        return 'empty'
    txt = ' '.join(p.text for p in paras)
    words = len(txt.split())
    if _CAPTION_RX.match(paras[0].text):
        return 'caption'
    ph = ''
    if getattr(sh, 'is_placeholder', False):
        try:
            ph = str(sh.placeholder_format.type)
        except Exception:
            ph = ''
    if 'TITLE' in ph:
        return 'title'
    if 'FOOTER' in ph or 'SLIDE_NUMBER' in ph or 'DATE' in ph:
        return 'caption'
    sizes = [_eff_size(r, p, sh, prs) for p in paras for r in p.runs if r.text.strip()]
    if sizes and max(sizes) < 16:
        return 'caption'
    if 'BODY' in ph or 'OBJECT' in ph:
        return 'body'
    if words >= 15 or (len(paras) >= 2 and words / len(paras) >= 5):
        return 'body'
    return 'label'


# ---------------- package integrity (GATE1 proxy; adapted from cdc-d-x07/x08 tests/dlib.py) ----------------
_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'


def pptx_integrity(path):
    """(ok, problems, external_links): zip intact, content types cover all parts, internal relationship targets
    exist, XML well-formed, python-pptx opens.  External non-hyperlink relationships are reported separately."""
    probs, ext = [], []
    try:
        z = zipfile.ZipFile(path)
    except Exception as e:
        return False, ['not a zip: %s' % e], ext
    try:
        bad = z.testzip()
    except Exception as e:
        bad = str(e)
    if bad:
        probs.append('corrupt zip member %s' % bad)
    names = set(z.namelist())
    if '[Content_Types].xml' not in names:
        return False, probs + ['no [Content_Types].xml'], ext
    try:
        ct = ET.fromstring(z.read('[Content_Types].xml'))
    except Exception:
        return False, probs + ['malformed [Content_Types].xml'], ext
    defaults = {e.get('Extension', '').lower() for e in ct if e.tag.endswith('Default')}
    overrides = {e.get('PartName', '').lstrip('/') for e in ct if e.tag.endswith('Override')}
    for n in names:
        if n.endswith('/') or n == '[Content_Types].xml':
            continue
        ext_ = n.rsplit('.', 1)[-1].lower() if '.' in n else ''
        if n not in overrides and ext_ not in defaults:
            probs.append('no content type for %s' % n)
    for o in overrides:
        if o not in names:
            probs.append('content-type override for missing part %s' % o)
    for n in names:
        if not n.endswith('.rels'):
            continue
        d = posixpath.dirname(posixpath.dirname(n))
        src = posixpath.join(d, posixpath.basename(n)[:-5]) if n != '_rels/.rels' else ''
        if src and src not in names:
            probs.append('rels for missing part %s' % src)
        try:
            root = ET.fromstring(z.read(n))
        except Exception:
            probs.append('bad rels xml %s' % n)
            continue
        for r in root.findall('{%s}Relationship' % _REL_NS):
            tgt = r.get('Target', '')
            typ = r.get('Type', '').rsplit('/', 1)[-1]
            if r.get('TargetMode') == 'External':
                if typ != 'hyperlink':
                    ext.append('%s -> %s (%s)' % (n, tgt, typ))
                continue
            full = tgt.lstrip('/') if tgt.startswith('/') else posixpath.normpath(posixpath.join(d, tgt))
            if full not in names:
                probs.append('broken rel %s -> %s' % (n, tgt))
    for n in names:
        if n.endswith('.xml') or n.endswith('.rels'):
            try:
                ET.fromstring(z.read(n))
            except Exception:
                probs.append('malformed xml %s' % n)
    try:
        from pptx import Presentation
        Presentation(path)
    except Exception as e:
        probs.append('python-pptx cannot open: %s' % e)
    return (not probs), probs[:12], ext


def run(ctx):
    R = {}

    def guard(iid, fn):
        try:
            v = fn()
            if v:
                R[iid] = {'verdict': v[0], 'detail': v[1]}
        except GraderError:
            raise
        except Exception as e:
            R[iid] = {'verdict': 'fail', 'detail': f'check error: {type(e).__name__}: {e}'}

    st = _load(ctx)
    out = st['out']
    prs = st['prs']
    slides = list(prs.slides) if prs is not None else []

    # D01 deliverables
    def d01():
        miss = [f for f in REQ if not (out / f).exists()]
        if miss or st['err']:
            return 'fail', f'missing={miss} pptx_err={st["err"]}'
        return 'pass', f'all six deliverables present; {len(slides)} slides parsed'
    guard('D01', d01)
    if prs is None or not slides:
        return R

    # N01 slide count + 16:9 (fail-only; empty-divider part left to model)
    def n01():
        w, h = prs.slide_width, prs.slide_height
        ratio = w / h if h else 0
        n = len(slides)
        bad = []
        if not 9 <= n <= 11:
            bad.append(f'{n} slides (need 9-11)')
        if abs(ratio - 16 / 9) > 0.01:
            bad.append(f'aspect {ratio:.3f} not 16:9')
        if bad:
            return 'fail', '; '.join(bad)
        return None
    guard('N01', n01)

    # D07 notes on every slide
    def d07():
        empty = [i + 1 for i, s in enumerate(slides) if not _notes(s)]
        return ('fail', f'slides without notes: {empty}') if empty else ('pass', 'every slide has speaker notes')
    guard('D07', d07)

    # N03 notes vs script similarity + timing total
    def n03():
        sp = out / 'script.md'
        if not sp.exists():
            return 'fail', 'script.md missing'
        text = sp.read_text(encoding='utf-8', errors='ignore')
        segs = _script_segments(text, len(slides))
        if not segs:
            return None  # cannot segment reliably -> model
        sims, secs = [], []
        for i, s in enumerate(slides, 1):
            seg = segs.get(i, '')
            nt = _notes(s)
            r = _sim(nt, seg)
            # notes may be the spoken text only, while the segment also has a timing line: use containment too
            na, sa = _strip_md(nt), _strip_md(seg)
            if na and na in sa:
                r = max(r, 0.99)
            sims.append(round(r, 3))
            secs.append(_seg_seconds(seg))
        low = [i + 1 for i, r in enumerate(sims) if r < 0.9]
        if low:
            return 'fail', f'notes vs script similarity <0.9 on slides {low}; sims={sims}'
        if all(x is not None for x in secs):
            tot = sum(secs)
            if 660 <= tot <= 780:
                return 'pass', f'notes match script (min sim {min(sims)}); per-slide timings total {tot:.0f}s'
            return 'fail', f'per-slide timings total {tot:.0f}s outside 11-13 min; parsed={secs}'
        return None  # timings not parseable -> model
    guard('N03', n03)

    # V01 font sizes (2026-10-25: effective sizes incl. inheritance; body >= 20 pt, everything else >= 12 pt)
    def v01():
        small, body_small = [], []
        for i, s in enumerate(slides, 1):
            t = s.shapes.title
            tid = t.shape_id if t is not None else None
            for sh in _iter_shapes(s.shapes):
                if getattr(sh, 'has_table', False) and sh.has_table:
                    for row in sh.table.rows:
                        for c in row.cells:
                            for p in c.text_frame.paragraphs:
                                for r in p.runs:
                                    if r.text.strip() and r.font.size is not None and r.font.size.pt < 11.95:
                                        small.append((i, 'table', round(r.font.size.pt, 1), r.text[:30]))
                    continue
                if not (getattr(sh, 'has_text_frame', False) and sh.has_text_frame):
                    continue
                kind = _frame_kind(sh, prs, tid)
                if kind in ('title', 'empty'):
                    continue
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        if not r.text.strip():
                            continue
                        sz = _eff_size(r, p, sh, prs)
                        if sz < 11.95:
                            small.append((i, kind, round(sz, 1), r.text[:30]))
                        elif kind == 'body' and sz < 19.95:
                            body_small.append((i, round(sz, 1), r.text[:30]))
        if small or body_small:
            return 'fail', f'{len(small)} runs below 12 pt e.g. {small[:4]}; {len(body_small)} body runs below 20 pt e.g. {body_small[:4]}'
        return 'pass', 'body text >= 20 pt and captions/labels/table cells >= 12 pt (effective sizes)'
    guard('V01', v01)

    # V02 <= 6 bullets per slide (2026-10-25: summed over all body text frames of the slide, not per frame;
    # titles, captions/source lines and single-line labels/callouts are not bullets)
    def v02():
        worst = []
        for i, s in enumerate(slides, 1):
            t = s.shapes.title
            tid = t.shape_id if t is not None else None
            n = 0
            for sh in _iter_shapes(s.shapes):
                if getattr(sh, 'has_text_frame', False) and sh.has_text_frame:
                    kind = _frame_kind(sh, prs, tid)
                    if kind == 'body' or (kind == 'label' and len([p for p in sh.text_frame.paragraphs if p.text.strip()]) >= 2):
                        n += sum(1 for p in sh.text_frame.paragraphs if p.text.strip())
            if n > 6:
                worst.append((i, n))
        return ('fail', f'slides with >6 bullet paragraphs (slide, count): {worst[:6]}') if worst else ('pass', 'no slide has more than 6 bullet paragraphs (summed over its body text frames)')
    guard('V02', v02)

    # tables
    tables = []
    for i, s in enumerate(slides, 1):
        for sh in _iter_shapes(s.shapes):
            if getattr(sh, 'has_table', False) and sh.has_table:
                cells = [[c.text.strip() for c in r.cells] for r in sh.table.rows]
                tables.append((i, sh, cells))

    def case_rows(cells):
        hit = {}
        for row in cells:
            line = _norm(' '.join(row[:2]))
            for k, al in CASE_ALIASES.items():
                if k in hit:
                    continue
                for a in al:
                    if re.search(r'\b' + re.escape(a) + r'\b', line):
                        # avoid matching "alternative electricity"/"alternative transportation" inside the combination row
                        if k in ('altelec', 'alttrnp') and ('combination' in line or 'electricity and' in line):
                            continue
                        hit[k] = (row, a)
                        break
        return hit

    _tb = _best_table(tables) if tables else None   # (n_cases, slide, shape, cells(case rows), {case: row_idx}, transposed)

    def _has2025(cells):
        """A 2025 reference column/row/value -- not merely a '2025 $' / '2025 cents' price-basis label."""
        rx = re.compile(r'(?i)\b2025\b(?!\s*(?:\$|¢|c\b|c/|cents?|dollars?|usd|us\$|real|constant|\)?\s*(?:\$|¢|cents?|dollars?)))')
        for r in cells:
            for c in r:
                t = re.sub(r'(?i)(?:\$|dollars?|cents?|usd)\s*(?:of\s*)?2025\b', ' ', c)
                t = re.sub(r'(?i)\b(?:real|constant)\s+2025\b', ' ', t)
                if rx.search(t):
                    return True
        return False

    def d02():
        if not tables:
            return 'fail', 'no native table (a:tbl) in the deck'
        nh, i, sh, cells, h, tr = _tb
        nr, nc = len(cells), max(len(r) for r in cells)
        has2025 = _has2025(cells)
        if nr >= 12 and nc >= 6 and nh >= 11 and has2025:
            return 'pass', f'slide {i}: native table with 11 cases x {nc - 1} indicator columns{" (transposed)" if tr else ""}, 2025 reference present'
        if nr < 12 or nc < 6:
            return 'fail', f'best native table slide {i} has {nr} case-rows x {nc} columns (need header + 11 cases, >=5 indicators)'
        if not has2025:
            return 'fail', f'slide {i} table has no 2025 reference column/row/value ("2025" only appears as a price-basis label)'
        return None  # case naming unusual -> model
    guard('D02', d02)

    def c01():
        if not tables:
            return 'fail', 'no native table'
        nh, i, sh, cells, h, tr = _tb
        hit = case_rows(cells)
        if len(hit) == 11:
            if hit['cb2026'][1] == 'reference':
                return None  # baseline only under the old name -> model checks the rename note
            return 'pass', 'all 11 case names found in native table rows'
        return None  # unusual naming -> model
    guard('C01', c01)

    # charts
    charts = []
    for i, s in enumerate(slides, 1):
        for sh in _iter_shapes(s.shapes):
            if getattr(sh, 'has_chart', False) and sh.has_chart:
                charts.append((i, sh.chart))

    def chart_wb(ch):
        try:
            for rel in ch.part.rels.values():
                if rel.reltype.endswith('/package') and not rel.is_external:
                    return rel.target_part.blob
        except Exception:
            pass
        return None

    def d03():
        withwb = [(i, chart_wb(c) is not None) for i, c in charts]
        ok = sum(1 for _, w in withwb if w)
        if ok >= 3:
            return 'pass', f'{len(charts)} native charts, {ok} with embedded workbook'
        return 'fail', f'{len(charts)} native charts, only {ok} with embedded workbook (need >=3)'
    guard('D03', d03)


    # D08 scenario-data.xlsx live formulas (fail-only when no / very few formulas)
    def d08():
        p = out / 'scenario-data.xlsx'
        if not p.exists():
            return 'fail', 'scenario-data.xlsx missing'
        try:
            nf, nv = _sheet_formulas(p.read_bytes())
        except Exception as e:
            return 'fail', f'not a readable xlsx: {e}'
        if nf == 0:
            return 'fail', f'no live formulas (<f>) in any worksheet ({nv} cells)'
        return None
    guard('D08', d08)

    # D09 evidence-index.csv schema (fail-only)
    def d09():
        p = out / 'evidence-index.csv'
        if not p.exists():
            return 'fail', 'evidence-index.csv missing'
        raw = p.read_text(encoding='utf-8-sig', errors='ignore')
        rows = list(csv.reader(io.StringIO(raw)))
        if not rows:
            return 'fail', 'empty csv'
        hdr = _norm(' | '.join(rows[0]))
        need = {'slide': r'slide', 'element': r'element|object|shape', 'claim': r'claim|fact|statement',
                'source file': r'source|file|document', 'location': r'page|sheet|cell|location|loc',
                'transformation': r'transform|method|operation|derivation'}
        miss = [k for k, rx in need.items() if not re.search(rx, hdr)]
        if miss:
            return 'fail', f'header lacks fields {miss}: {rows[0]}'
        if len(rows) - 1 < len(slides) - 2:
            return 'fail', f'only {len(rows) - 1} rows for {len(slides)} slides'
        return None
    guard('D09', d09)

    # D10 slides.pdf vs pptx
    def d10():
        p = out / 'slides.pdf'
        if not p.exists():
            return 'fail', 'slides.pdf missing'
        txt = _sh(['pdftotext', '-layout', str(p), '-'])
        pages = txt.split('\f')
        if pages and not pages[-1].strip():
            pages = pages[:-1]
        try:
            from pypdf import PdfReader
            npg = len(PdfReader(str(p)).pages)
        except Exception:
            npg = len(pages)
        if npg != len(slides):
            return 'fail', f'PDF has {npg} pages, PPTX has {len(slides)} slides'
        miss = []
        for i, s in enumerate(slides):
            t = _norm(_title(s))
            pg = _norm(pages[i]) if i < len(pages) else ''
            if not t:
                continue
            words = t.split()
            found = sum(1 for w in words if w in pg.split()) / len(words)
            if found < 0.8:
                miss.append((i + 1, round(found, 2)))
        if miss:
            return 'fail', f'page/slide title mismatch (slide, fraction of title words on same PDF page): {miss}'
        return 'pass', f'{npg} pages = {len(slides)} slides; every slide title found on the same PDF page'
    guard('D10', d10)

    # ---------------------------------------------------------------- 2026-10-25 additions
    UNIT_RX = re.compile(r'(?i)kwh|twh|gwh|mwh|quad|btu|¢|cents?\b|\$|dollars?|%|percent|\bgw\b|tonnes?|\bmmt\b|billion|trillion|index')
    MONEY_RX = re.compile(r'(?i)price|¢|cents?\b|\$|dollars?|\bcosts?\b|tariff')
    BASIS_RX = re.compile(r'(?i)\b2025\b|nominal|\breal\b|constant')

    def _chart_texts(ch):
        t = [_chart_title(ch)]
        for ax in ('value_axis', 'category_axis'):
            try:
                t.append(_axis_title(getattr(ch, ax)))
            except Exception:
                pass
        t += [s['name'] for s in _chart_series(ch)]
        return ' | '.join(x for x in t if x)

    def v05():
        bad = []
        for i, c in charts:
            for s in _chart_series(c):
                if re.fullmatch(r'(?i)\s*series\s*\d*\s*', s['name']) or not s['name']:
                    bad.append((i, 'default/empty series name %r' % s['name']))
            title = _chart_title(c)
            try:
                vt = _axis_title(c.value_axis)
                has_axis = True
            except Exception:
                vt, has_axis = '', False
            lab = vt if has_axis else title
            if not UNIT_RX.search(vt or '') and not UNIT_RX.search(title or ''):
                bad.append((i, 'no unit in value-axis title %r / chart title %r' % (vt, title)))
            elif MONEY_RX.search(_chart_texts(c)) and not (BASIS_RX.search(vt or '') or BASIS_RX.search(title or '')):
                bad.append((i, 'money chart without price basis (2025 $/real/nominal) in axis/chart title %r / %r' % (vt, title)))
        if not charts:
            return 'fail', 'no native charts'
        return ('fail', f'{bad[:6]}') if bad else ('pass', f'{len(charts)} charts: named series, unit (and price basis for money) in value-axis or chart title')
    guard('V05', v05)

    # D04 chart workbooks carry values + unit + price basis + source location (deterministic; COM Activate dropped)
    LOC_RX = re.compile(r'(?i)table\s*\d|_table\d|\.xlsx|\.pdf|sheet|\bcell\b|\brow\s*\d|\b[A-Z]{1,2}\d{1,4}\b|\bpage\b|\bp\.?\s*\d|figure-data|outlook|case-desc')
    WB_UNIT_RX = re.compile(r'(?i)kwh|twh|quad|btu|¢|cents?\b|\$|dollars?|%|percent|\bunit')

    def d04():
        if not charts:
            return 'fail', 'no native charts'
        bad = []
        for i, c in charts:
            blob = chart_wb(c)
            if blob is None:
                bad.append((i, 'no embedded workbook'))
                continue
            try:
                strs, nums = _wb_strings_numbers(blob)
            except Exception as e:
                bad.append((i, f'embedded workbook unreadable: {e}'))
                continue
            text = ' | '.join(strs)
            miss = []
            plotted = [float(v) for s in _chart_series(c) for v in s['vals'] if v is not None]
            lost = [v for v in plotted if not any(abs(v - n) <= 1e-6 * max(1, abs(v)) for n in nums)]
            if lost:
                miss.append(f'{len(lost)} plotted values not in workbook')
            if not WB_UNIT_RX.search(text):
                miss.append('no unit label')
            if not LOC_RX.search(text):
                miss.append('no source file/sheet/cell/page')
            if MONEY_RX.search(_chart_texts(c)) and not BASIS_RX.search(text):
                miss.append('money values without price basis')
            if miss:
                bad.append((i, ', '.join(miss)))
        return ('fail', f'chart workbooks: {bad[:6]}') if bad else ('pass', f'{len(charts)} chart workbooks list plotted values, units, source location (and basis for money)')
    guard('D04', d04)

    # F01 every native-table value matches the source tables (column-wise fit to one source row/feature)
    fit_cache = {}

    def table_fit():
        if 'v' not in fit_cache:
            if not _tb or _tb[0] < 2:
                fit_cache['v'] = None
            else:
                fit_cache['v'] = _table_fit(ctx, _tb[3], _tb[4])
        return fit_cache['v']

    def f01():
        if not tables:
            return 'fail', 'no native table'
        tf = table_fit()
        if tf is None:
            return None
        nh, i, sh, cells, h, tr = _tb
        wrong, unmapped, ok = [], [], []
        for col in tf:
            if col['best'] is None:
                unmapped.append(col['head'][:30] or f"col{col['col']}")
                continue
            key, kind, sc, lab = col['best']
            for k, (c, v, d) in enumerate(col['obs']):
                if k not in col['matched']:
                    ref = None
                    kk, yr = (kind.split('@') + [None])[:2]
                    fv = _feat_val(ctx, c, key, kk, int(yr) if yr else None)
                    ref = None if fv is None else round(fv * sc, max(d, 1))
                    wrong.append(f"{c}/{col['head'][:20] or col['col']}: {v} vs source {ref}")
            ok.append(f"{col['head'][:25] or col['col']}<-{lab.strip()[:25]}[{kind}x{sc:g}]")
        # 2025 reference rows (not a case row) must equal the baseline 2025 value of the same source row
        case_ri = set(h.values())
        for ri, row in enumerate(cells):
            if ri in case_ri or not re.search(r'\b2025\b', ' '.join(row[:2])):
                continue
            for col in tf:
                if col['best'] is None or not col['best'][1].startswith('y@'):
                    continue
                j = col['col']
                ns = _nums(row[j]) if j < len(row) else []
                if not ns:
                    continue
                v, d = ns[0]
                fv = _feat_val(ctx, 'cb2026', col['best'][0], 'y', 2025)
                if fv is None or abs(v - col['best'][2] * fv) > _tol(d) + 1e-6 * abs(v):
                    wrong.append(f"2025 row/{col['head'][:20]}: {v} vs source {None if fv is None else round(fv * col['best'][2], max(d, 1))}")
        if wrong:
            return 'fail', f'slide {i}: {len(wrong)} table cells do not match the source tables: {wrong[:6]}'
        if unmapped:
            return None  # some columns could not be tied to a source row -> model
        if not ok:
            return None
        return 'pass', f'slide {i}: every numeric cell matches its source row within displayed rounding: {ok[:8]}'
    guard('F01', f01)

    # chart point -> source fit (per series)
    def series_fit(c):
        pts, sers, orient = _chart_points(c)
        out = []
        for s in sers:
            sp = [p for p in pts if p[3] == s['idx']]
            if not sp:
                out.append((s, None, set(), 0, []))
                continue
            obs = []
            for (case, yr, v, _) in sp:
                vs = ('%.10g' % v)
                d = len(vs.split('.', 1)[1]) if '.' in vs and 'e' not in vs else 0
                obs.append((case, v, min(d, 4), yr))
            best, m, n = _fit(ctx, obs)
            out.append((s, best, m, n, obs))
        return out

    def _figdata_numbers():
        """numeric rows and columns (>=3 numbers) of figure-data.xlsx"""
        if 'fd' not in fit_cache:
            nums = []
            p = Path(ctx.get('input') or '') / 'figure-data.xlsx'
            try:
                wb = _load_xlsx(p)
                for ws in wb.worksheets:
                    grid = [list(r) for r in ws.iter_rows(values_only=True)]
                    width = max((len(r) for r in grid), default=0)
                    lines = grid + [[r[j] if j < len(r) else None for r in grid] for j in range(width)]
                    for ln in lines:  # every row and every column of every sheet
                        v = [float(x) for x in ln if isinstance(x, (int, float)) and not isinstance(x, bool)]
                        if len(v) >= 3:
                            nums.append(v)
                wb.close()
            except Exception:
                pass
            fit_cache['fd'] = nums
        return fit_cache['fd']

    def f02():
        if not charts:
            return 'fail', 'no native charts'
        wrong, unmapped, ok = [], [], 0
        for i, c in charts:
            for (s, best, m, n, obs) in series_fit(c):
                vals = [float(v) for v in s['vals'] if v is not None]
                if not vals:
                    continue
                if best is not None:
                    bad = [obs[k] for k in range(n) if k not in m]
                    if bad:
                        wrong.append(f"slide {i} series {s['name']!r}: {len(bad)} of {n} points do not match {best[3].strip()[:30]} e.g. {bad[:2]}")
                    else:
                        ok += 1
                    continue
                # not case-mapped (e.g. baseline-only or figure-data series): baseline fit, else figure-data values
                obs_b = []
                for v, cat in zip(s['vals'], s['cats'] or [None] * len(s['vals'])):
                    if v is None:
                        continue
                    vs = '%.10g' % v
                    d = len(vs.split('.', 1)[1]) if '.' in vs and 'e' not in vs else 0
                    obs_b.append(('cb2026', float(v), min(d, 4), _year_of(cat)))
                bb, mb, nb = _fit(ctx, obs_b) if all(o[3] for o in obs_b) else (None, set(), len(obs_b))
                if bb is not None and len(mb) == nb:
                    ok += 1
                    continue
                # figure-data.xlsx: all points (>=3) must come from ONE row or column of one sheet
                fd = _figdata_numbers()
                if len(obs_b) >= 3 and any(all(any(abs(v - x) <= max(_tol(d), 1e-6 * abs(v)) for x in ln) for (_, v, d, _) in obs_b) for ln in fd):
                    ok += 1
                    continue
                unmapped.append(f"slide {i} series {s['name']!r}")
        if wrong:
            return 'fail', f'{wrong[:4]}'
        if unmapped:
            return None
        return 'pass', f'{ok} chart series reproduce source-table (or figure-data) values within stored precision'
    guard('F02', f02)

    # D05 table-chart agreement as displayed
    def d05():
        if not tables or not charts:
            return 'fail', 'needs a native table and native charts'
        tf = table_fit()
        if tf is None:
            return None
        cols = [c for c in tf if c['best'] is not None]
        shared, bad = 0, []
        for i, c in charts:
            for (s, best, m, n, obs) in series_fit(c):
                if best is None:
                    continue
                for col in cols:
                    tk, tkind, tsc, lab = col['best']
                    if tk != best[0]:
                        continue
                    # same source quantity in the same year/derivation?
                    same_kind = (tkind == best[1]) or (best[1] == 'y' and tkind.startswith('y@'))
                    if not same_kind:
                        continue
                    tvals = {cs: (v, d) for cs, v, d in col['obs']}
                    for k, (case, v, d, yr) in enumerate(obs):
                        if case not in tvals:
                            continue
                        if best[1] == 'y' and tkind.startswith('y@') and yr != int(tkind.split('@')[1]):
                            continue
                        tv, td = tvals[case]
                        shared += 1
                        if abs(best[2] - tsc) > 1e-12:
                            bad.append(f'{case}: chart unit scale x{best[2]:g} vs table x{tsc:g}')
                            continue
                        disp = _fmt_display(v, s['fmt'])
                        if disp is not None:
                            dv, dd = disp
                            if dd != td or abs(dv - tv) > 1e-9 + _tol(td) * 0.01:
                                bad.append(f'{case}: chart shows {dv} ({s["fmt"]}) vs table {tv}')
                        elif abs(v - tv) > _tol(td) + 1e-9:
                            bad.append(f'{case}: chart {v} vs table {tv}')
        if bad:
            return 'fail', f'{len(bad)} of {shared} shared values disagree: {bad[:5]}'
        if shared == 0:
            return 'pass', 'no value appears both in the native table and in a chart'
        return 'pass', f'{shared} values shared by table and charts agree as displayed'
    guard('D05', d05)

    # D06 price chart: >=4 cases, all-sector average price (Table 8) 2025-2050, values = source years
    def d06():
        if not charts:
            return 'fail', 'no native charts'
        notes = []
        for i, c in charts:
            pts, sers, orient = _chart_points(c)
            cases = {p[0] for p in pts}
            if len(cases) < 4:
                continue
            years = sorted({p[1] for p in pts if p[1]})
            nominal = bool(re.search(r'(?i)nominal', _chart_texts(c)))
            rk = (8, 'ESD000:nom_AllSectorsAv' if nominal else 'ESD000:ja_AllSectorsAve')
            badp = []
            if years:
                if years[0] != 2025 or years[-1] != 2050:
                    notes.append(f'slide {i}: years {years[0]}-{years[-1]} (need 2025-2050)')
                    continue
                for (case, yr, v, _) in pts:
                    if yr is None:
                        continue
                    vs = '%.10g' % v
                    d = min(len(vs.split('.', 1)[1]) if '.' in vs and 'e' not in vs else 0, 4)
                    for sc in (1.0, 1e-2):
                        f = _feat_val(ctx, case, rk, 'y', yr)
                        if f is not None and abs(v - sc * f) <= _tol(d) + 1e-6 * abs(v):
                            break
                    else:
                        badp.append((case, yr, v, None if _feat_val(ctx, case, rk, 'y', yr) is None else round(_feat_val(ctx, case, rk, 'y', yr), 2)))
                if not badp:
                    return 'pass', f'slide {i}: {len(cases)} cases, {len(years)} source years 2025-2050, every point = Table 8 {"nominal" if nominal else "2025-cent"} all-sector average price'
                notes.append(f'slide {i}: points not in Table 8 average price row: {badp[:4]}')
            else:
                # period-average bars: mean of the 26 annual values 2025-2050
                for (case, yr, v, _) in pts:
                    f = _feat_val(ctx, case, rk, 'mean')
                    if f is None or not any(abs(v - sc * f) <= 0.051 * sc for sc in (1.0, 1e-2)):
                        badp.append((case, v))
                if not badp:
                    return 'pass', f'slide {i}: {len(cases)} cases, 2025-2050 mean of the Table 8 all-sector average price'
        return 'fail', f'no chart with >=4 cases plotting the Table 8 all-sector average price 2025-2050; {notes[:3]}'
    guard('D06', d06)

    # V06 same colour per case across charts, same order and name as in the native table
    def v06():
        if not charts:
            return 'fail', 'no native charts'
        colour = {}   # case -> set(colour ids)
        owner = {}    # colour id -> set(cases)
        names = {}    # case -> set(normalised labels)
        bad = []
        trow = {}
        if _tb:
            nh, i_t, sh_t, cells, h, tr = _tb
            for k, ri in h.items():
                trow[k] = ri
                names.setdefault(k, set()).add(_norm(re.sub(r'\(.*?\)', '', cells[ri][0] or cells[ri][1])))
        for i, c in charts:
            sers = _chart_series(c)
            order = []
            for s in sers:
                sc = _case_of(s['name'])
                cat_cases = [_case_of(x) for x in s['cats']]
                if sc:
                    col = _fill_of(s['el']) or 'auto:%d' % s['idx']
                    colour.setdefault(sc, set()).add(col)
                    owner.setdefault(col, set()).add(sc)
                    names.setdefault(sc, set()).add(_norm(re.sub(r'\(.*?\)', '', s['name'])))
                    order.append(sc)
                elif sum(1 for x in cat_cases if x) >= 2:
                    dpts = {int(dp.find('{%s}idx' % _C).get('val')): dp for dp in s['el'].findall('{%s}dPt' % _C)
                            if dp.find('{%s}idx' % _C) is not None}
                    vary = s['plot_el'].find('{%s}varyColors' % _C)
                    for j, cc in enumerate(cat_cases):
                        if not cc:
                            continue
                        if j in dpts and _fill_of(dpts[j]):
                            col = _fill_of(dpts[j])
                        elif vary is not None and vary.get('val') in ('1', 'true') and len(sers) == 1:
                            col = 'auto:%d' % j
                        else:
                            col = _fill_of(s['el']) or 'auto:%d' % s['idx']
                        colour.setdefault(cc, set()).add(col)
                        if len(sers) == 1:
                            owner.setdefault(col, set()).add(cc)
                        names.setdefault(cc, set()).add(_norm(re.sub(r'\(.*?\)', '', s['cats'][j])))
                        if cc not in order:
                            order.append(cc)
            if trow and order:
                ranks = [trow[k] for k in order if k in trow]
                if ranks != sorted(ranks):
                    bad.append(f'slide {i}: case order {order} differs from table order')
        for k, cs in colour.items():
            if len(cs) > 1:
                bad.append(f'{k} drawn in {len(cs)} colours {sorted(cs)}')
        for col, ks in owner.items():
            if len(ks) > 1:
                bad.append(f'colour {col} shared by {sorted(ks)}')
        for k, ns in names.items():
            ns = {n for n in ns if n}
            if len(ns) > 1:
                bad.append(f'{k} named differently: {sorted(ns)}')
        if not colour:
            return None  # no case-coded chart -> model
        return ('fail', f'{bad[:6]}') if bad else ('pass', f'{len(colour)} cases: one colour each across charts, unique colours, table order and names reused')
    guard('V06', v06)

    # V03 (fail-only) every shape inside the slide; native table frame (sum of row heights) inside the slide
    def v03():
        W, H = prs.slide_width, prs.slide_height
        tolr = 12700  # 1 pt
        out_ = []
        for i, s in enumerate(slides, 1):
            for sh in s.shapes:
                try:
                    x, y, w, h = sh.left, sh.top, sh.width, sh.height
                except Exception:
                    continue
                if x is None or w is None:
                    continue
                if getattr(sh, 'has_table', False) and sh.has_table:
                    h = max(h, sum(r.height for r in sh.table.rows))
                if x < -tolr or y < -tolr or x + w > W + tolr or y + h > H + tolr:
                    out_.append((i, sh.name))
        return ('fail', f'shapes extending beyond the slide (slide, shape): {out_[:6]}') if out_ else None
    guard('V03', v03)

    # C07 (pass-only) no data-centre server electricity figure anywhere -> condition not triggered -> pass
    def c07():
        blob = []
        for s in slides:
            for sh in _iter_shapes(s.shapes):
                if getattr(sh, 'has_text_frame', False) and sh.has_text_frame:
                    blob.append(sh.text_frame.text)
                if getattr(sh, 'has_table', False) and sh.has_table:
                    blob += [c.text for r in sh.table.rows for c in r.cells]
            blob.append(_notes(s))
        for i, c in charts:
            blob.append(_chart_texts(c))
        sp = out / 'script.md'
        if sp.exists():
            blob.append(sp.read_text(encoding='utf-8', errors='ignore'))
        text = '\n'.join(blob)
        if re.search(r'(?i)data[- ]?cent(er|re)s?|servers?', text):
            return None  # data centres mentioned -> model decides whether a server figure is given and flagged
        return 'pass', 'no data-centre / server electricity mentioned anywhere (condition not triggered)'
    guard('C07', c07)

    # F07 10 sampled evidence-index rows resolve to the cited page or cell
    def f07():
        p = out / 'evidence-index.csv'
        if not p.exists():
            return 'fail', 'evidence-index.csv missing'
        rows = list(csv.reader(io.StringIO(p.read_text(encoding='utf-8-sig', errors='ignore'))))
        if len(rows) < 2:
            return 'fail', 'evidence-index.csv has no data rows'
        hdr = [_norm(x) for x in rows[0]]

        def col(rx):
            for j, x in enumerate(hdr):
                if re.search(rx, x):
                    return j
            return None
        jc, jf = col(r'claim|fact|statement|value'), col(r'source|file|document')
        jl, jt = col(r'page|sheet|cell|loc'), col(r'transform|method|operation|derivation')
        if jc is None or jf is None:
            return 'fail', f'cannot find claim/source columns in header {rows[0]}'
        data = [r for r in rows[1:] if any(x.strip() for x in r)]
        rnd = random.Random(20261025)
        sample = data if len(data) <= 10 else rnd.sample(data, 10)
        inp = Path(ctx.get('input') or '')
        pdf_cache = {}

        def pdf_page(fp, n):
            k = (str(fp), n)
            if k not in pdf_cache:
                pdf_cache[k] = _sh(['pdftotext', '-layout', '-f', str(n), '-l', str(n), str(fp), '-'], 60)
            return pdf_cache[k]

        def locate(name):
            name = name.strip().replace('\\', '/')
            for cand in (inp / name, inp / name.replace('input/', '', 1), inp / 'tables' / Path(name).name, inp / Path(name).name):
                if cand.is_file():
                    return cand
            m = re.search(r'([\w.-]+\.(?:pdf|xlsx))', name, re.I)
            if m:
                for cand in (inp / m.group(1), inp / 'tables' / m.group(1)):
                    if cand.is_file():
                        return cand
            return None

        def nums_ok(claim_nums, hay_nums):
            for v, d in claim_nums:
                if any(abs(v - h) <= _tol(d) + 1e-6 * abs(v) for h in hay_nums):
                    return True
            return False

        def words_ok(claim, hay):
            cw, hw = _norm(claim).split(), _norm(hay)
            if any(' '.join(cw[k:k + 5]) in hw for k in range(max(0, len(cw) - 4))):
                return True  # a 5-word phrase of the claim is on the page
            ws = [w for w in cw if len(w) >= 5]
            hs = set(hw.split())
            return len(ws) >= 3 and sum(1 for w in ws if w in hs) / len(ws) >= 0.75

        fails = []
        for r in sample:
            g = lambda j: (r[j] if j is not None and j < len(r) else '')
            claim, srcf, loc, tr = g(jc), g(jf), g(jl), g(jt)
            fp = locate(srcf) or locate(loc)
            cn = [(v, d) for v, d in _nums(claim) if not (d == 0 and 1990 <= v <= 2060)]
            derived = bool(re.search(r'(?i)recalc|calc|conver|deriv|comput|ratio|differen|growth|sum|formula|arithmetic', tr))
            if fp is None:
                fails.append(f'{srcf!r}: file not in input/')
                continue
            if fp.suffix.lower() == '.pdf':
                pages = [int(x) for x in re.findall(r'(?i)(?:p(?:age|df)?\.?\s*|pp\.?\s*)(\d{1,3})', loc + ' ' + srcf)]
                if not pages:
                    pages = [int(x) for x in re.findall(r'\b(\d{1,3})\b', loc)]
                if not pages:
                    fails.append(f'{srcf}: no page in {loc!r}')
                    continue
                off = 4 if 'case' in fp.name else 3
                cand = sorted({q for pg in pages[:3] for q in (pg, pg + off) if q > 0})
                hay = '\n'.join(pdf_page(fp, q) for q in cand)
                hn = [v for v, d in _nums(hay)]
                if (cn and nums_ok(cn, hn)) or words_ok(claim, hay) or (derived and hay.strip()):
                    continue
                fails.append(f'{fp.name} p{pages[:3]}: claim {claim[:40]!r} not found')
            else:
                try:
                    wb = _load_xlsx(fp)
                except Exception as e:
                    fails.append(f'{fp.name}: unreadable ({e})')
                    continue
                sheet = None
                for sn in wb.sheetnames:
                    if sn.lower() in (loc + ' ' + srcf).lower():
                        sheet = sn
                ws = wb[sheet] if sheet else wb.worksheets[0]
                refs = re.findall(r'\b([A-Z]{1,3})\$?(\d{1,5})\b', loc)
                mrow = re.search(r'(?i)row\s*(\d+)', loc)
                mcol = re.findall(r'(?i)col(?:umn)?\s*([A-Z]{1,3})\b', loc)
                if mrow and mcol:
                    refs += [(cc.upper(), mrow.group(1)) for cc in mcol]
                vals = []
                for cl, rw in refs[:6]:
                    try:
                        v = ws[f'{cl}{rw}'].value
                    except Exception:
                        v = None
                    if v is not None:
                        vals.append(v)
                wb.close()
                if not vals:
                    fails.append(f'{fp.name}: cell(s) {loc!r} empty or unparseable')
                    continue
                hn = [float(v) for v in vals if isinstance(v, (int, float))]
                ht = ' '.join(str(v) for v in vals)
                if (cn and nums_ok(cn, hn)) or words_ok(claim, ht) or (derived and hn) or not cn:
                    continue
                fails.append(f'{fp.name}!{loc}: claim numbers {cn[:3]} vs cell values {hn[:3]}')
        if fails:
            return 'fail', f'{len(fails)} of {len(sample)} sampled rows do not resolve: {fails[:4]}'
        return 'pass', f'{len(sample)} sampled evidence rows resolve to the cited page/cell'
    guard('F07', f07)

    return R


def postprocess(results, ctx):
    """GATE0: six deliverables + parseable PPTX, else every item is a fail.  GATE1 (structural proxy): G6 = fail."""
    out = Path(ctx['out'])
    miss = [f for f in REQ if not (out / f).exists()]
    ok = not miss
    if ok:
        try:
            from pptx import Presentation
            ok = len(Presentation(str(out / 'presentation.pptx')).slides) > 0
        except Exception:
            ok = False
    if not ok:
        for it in ctx['items']:
            results[it['id']] = {'verdict': 'fail', 'detail': f'GATE0 failed (missing={miss} or PPTX unparseable)', 'source': 'gate'}
        results['_gate0'] = {'verdict': 'fail', 'detail': f'missing={miss}'}
        return results
    # GATE1 structural proxy (2026-10-25): PowerPoint's repair prompt cannot be tested on Linux; a package that is
    # structurally broken (content types, relationships, malformed XML) or depends on external files fails every G6
    # (native objects & delivery) item, as stated in the instruction ("A file that PowerPoint must repair fails all
    # native-object and delivery checks").
    try:
        ok1, probs, ext = pptx_integrity(str(out / 'presentation.pptx'))
    except Exception as e:  # grader bug must surface, but keep the reason
        ok1, probs, ext = False, [f'integrity check error: {e}'], []
    if not ok1 or ext:
        why = f'GATE1 structural proxy failed: {(probs + ext)[:3]}'
        for it in ctx['items']:
            if it.get('group') == 'G6':
                results[it['id']] = {'verdict': 'fail', 'detail': why, 'source': 'gate'}
        results['_gate1'] = {'verdict': 'fail', 'detail': why}
    return results
