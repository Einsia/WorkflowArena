# -*- coding: utf-8 -*-
"""CDC-D 确定性检查辅助库（只用标准库 + python-pptx/pypdf，可选；无 openpyxl）。
所有函数遇异常应由调用方捕获；本库自身尽量不抛异常。"""
import csv, io, json, posixpath, re, subprocess, zipfile
from difflib import SequenceMatcher

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
}
REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
import xml.etree.ElementTree as ET


def V(ok, detail):
    return {'verdict': 'pass' if ok else 'fail', 'detail': str(detail)[:600]}


def F(detail):
    return {'verdict': 'fail', 'detail': str(detail)[:600]}


def P(detail):
    return {'verdict': 'pass', 'detail': str(detail)[:600]}


# ---------------- package / structure ----------------
def _rels_path(part):
    d, b = posixpath.split(part)
    return posixpath.join(d, '_rels', b + '.rels')


def read_rels(z, part):
    rp = _rels_path(part)
    out = []
    if rp not in z.namelist():
        return out
    root = ET.fromstring(z.read(rp))
    for r in root.findall('{%s}Relationship' % REL_NS):
        tgt = r.get('Target', '')
        ext = r.get('TargetMode') == 'External'
        if not ext:
            if tgt.startswith('/'):
                full = tgt.lstrip('/')
            else:
                full = posixpath.normpath(posixpath.join(posixpath.dirname(part), tgt))
        else:
            full = tgt
        out.append({'id': r.get('Id'), 'type': r.get('Type', '').rsplit('/', 1)[-1], 'target': full, 'external': ext})
    return out


def pptx_integrity(path):
    """返回 (ok, problems:list, info)。结构代理：zip 完整、[Content_Types] 覆盖、内部关系目标存在、python-pptx 可读、无外链媒体/图表数据。"""
    probs = []
    info = {}
    try:
        z = zipfile.ZipFile(path)
    except Exception as e:
        return False, ['not a zip: %s' % e], info
    bad = z.testzip()
    if bad:
        probs.append('corrupt zip member %s' % bad)
    names = set(z.namelist())
    if '[Content_Types].xml' not in names:
        probs.append('no [Content_Types].xml')
        return False, probs, info
    ct = ET.fromstring(z.read('[Content_Types].xml'))
    defaults = {e.get('Extension', '').lower() for e in ct if e.tag.endswith('Default')}
    overrides = {e.get('PartName', '').lstrip('/') for e in ct if e.tag.endswith('Override')}
    for n in names:
        if n.endswith('/') or n == '[Content_Types].xml':
            continue
        ext = n.rsplit('.', 1)[-1].lower() if '.' in n else ''
        if n not in overrides and ext not in defaults:
            probs.append('no content type for %s' % n)
    for o in overrides:
        if o not in names:
            probs.append('content-type override for missing part %s' % o)
    ext_links = []
    # walk rels
    for n in list(names):
        if not n.endswith('.rels'):
            continue
        d = posixpath.dirname(posixpath.dirname(n))
        src = posixpath.join(d, posixpath.basename(n)[:-5]) if n != '_rels/.rels' else ''
        if src and src not in names:
            probs.append('rels for missing part %s' % src)
        try:
            root = ET.fromstring(z.read(n))
        except Exception as e:
            probs.append('bad rels xml %s' % n)
            continue
        for r in root.findall('{%s}Relationship' % REL_NS):
            tgt = r.get('Target', '')
            typ = r.get('Type', '').rsplit('/', 1)[-1]
            if r.get('TargetMode') == 'External':
                if typ != 'hyperlink':
                    ext_links.append('%s -> %s (%s)' % (n, tgt, typ))
                continue
            full = tgt.lstrip('/') if tgt.startswith('/') else posixpath.normpath(posixpath.join(d, tgt))
            if full not in names:
                probs.append('broken rel %s -> %s' % (n, tgt))
    # xml well-formedness
    for n in names:
        if n.endswith('.xml') or n.endswith('.rels'):
            try:
                ET.fromstring(z.read(n))
            except Exception:
                probs.append('malformed xml %s' % n)
    info['external_links'] = ext_links
    try:
        from pptx import Presentation
        Presentation(path)
    except ImportError:
        info['python_pptx'] = 'missing'
    except Exception as e:
        probs.append('python-pptx cannot open: %s' % e)
    return (not probs), probs[:12], info


def slide_parts(z):
    """按演示顺序返回 slide part 名列表。"""
    pres = ET.fromstring(z.read('ppt/presentation.xml'))
    rels = {r['id']: r['target'] for r in read_rels(z, 'ppt/presentation.xml')}
    out = []
    lst = pres.find('p:sldIdLst', NS)
    if lst is not None:
        for s in lst:
            rid = s.get('{%s}id' % NS['r'])
            if rid in rels:
                out.append(rels[rid])
    return out


def slide_size(z):
    pres = ET.fromstring(z.read('ppt/presentation.xml'))
    s = pres.find('p:sldSz', NS)
    return int(s.get('cx')), int(s.get('cy'))


def shapes_by_id(sroot):
    d = {}
    for el in sroot.iter():
        if el.tag.endswith('}cNvPr'):
            d[el.get('id')] = el
    return d


def shape_texts(sroot):
    """spid -> 文本（sp/grpSp 内全部 a:t）。"""
    out = {}
    for sp in sroot.iter():
        tag = sp.tag.rsplit('}', 1)[-1]
        if tag in ('sp', 'grpSp', 'cxnSp', 'pic', 'graphicFrame'):
            nv = None
            for el in sp.iter():
                if el.tag.endswith('}cNvPr'):
                    nv = el
                    break
            if nv is None:
                continue
            txt = ' '.join(t.text or '' for t in sp.iter('{%s}t' % NS['a']))
            out.setdefault(nv.get('id'), (tag, txt, nv.get('name', '')))
    return out


def _ctn_attr(par):
    c = par.find('p:cTn', NS)
    return c


def timing_info(sroot):
    """解析 p:timing。返回 dict:
    main_clicks: [ {spids:set, classes:set} ] 主序列中每个 clickEffect 节点
    triggers: {trigger_spid: [ {spids, classes} ]}  交互序列
    media_cmds: 列表（playFrom 等）
    """
    res = {'main_clicks': [], 'triggers': {}, 'media_cmds': [], 'bld_charts': [], 'chart_anim_targets': 0}
    tm = sroot.find('p:timing', NS)
    if tm is None:
        return res
    for ctn in tm.iter('{%s}cTn' % NS['p']):
        nt = ctn.get('nodeType')
        if nt == 'mainSeq':
            for eff in ctn.iter('{%s}cTn' % NS['p']):
                if eff.get('nodeType') == 'clickEffect':
                    sp = {t.get('spid') for t in eff.iter('{%s}spTgt' % NS['p'])}
                    res['main_clicks'].append({'spids': sp, 'cls': eff.get('presetClass'), 'grpId': eff.get('grpId')})
        elif nt == 'interactiveSeq':
            trig = None
            st = ctn.find('p:stCondLst', NS)
            if st is not None:
                for cond in st.findall('p:cond', NS):
                    if cond.get('evt') == 'onClick':
                        t = cond.find('.//p:spTgt', NS)
                        if t is not None:
                            trig = t.get('spid')
            effs = []
            for eff in ctn.iter('{%s}cTn' % NS['p']):
                if eff.get('presetClass'):
                    effs.append({'spids': {t.get('spid') for t in eff.iter('{%s}spTgt' % NS['p'])}, 'cls': eff.get('presetClass')})
            if trig:
                res['triggers'].setdefault(trig, []).extend(effs)
    for cmd in tm.iter('{%s}cmd' % NS['p']):
        res['media_cmds'].append(cmd.get('cmd', ''))
    for bg in tm.iter('{%s}bldGraphic' % NS['p']):
        for bc in bg.iter('{%s}bldChart' % NS['a']):
            res['bld_charts'].append((bg.get('spid'), bc.get('bld', 'allAtOnce')))
    res['chart_anim_targets'] = sum(1 for _ in tm.iter('{%s}chart' % NS['a']))
    return res


def chart_parts_for_slide(z, spart):
    return [r['target'] for r in read_rels(z, spart) if r['type'] == 'chart' and not r['external']]


def chart_embedded(z, cpart):
    """返回 embedded workbook part 名（或 None）及是否外链。"""
    try:
        root = ET.fromstring(z.read(cpart))
    except Exception:
        return None, False
    ed = root.find('c:externalData', NS)
    if ed is None:
        return None, False
    rid = ed.get('{%s}id' % NS['r'])
    for r in read_rels(z, cpart):
        if r['id'] == rid:
            if r['external']:
                return None, True
            return (r['target'] if r['target'] in z.namelist() else None), False
    return None, False


def xlsx_scan(data):
    """解 xlsx 字节：返回 {'formulas': n, 'formula_vals': [float...], 'strings': [..], 'numbers': [..], 'sheets': n}."""
    out = {'formulas': 0, 'formula_vals': [], 'strings': [], 'numbers': [], 'sheets': 0, 'formula_no_cache': 0}
    z = zipfile.ZipFile(io.BytesIO(data))
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    sst = []
    if 'xl/sharedStrings.xml' in z.namelist():
        r = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in r.findall('m:si', ns):
            sst.append(''.join(t.text or '' for t in si.iter('{%s}t' % ns['m'])))
    for n in z.namelist():
        if not re.match(r'xl/worksheets/sheet\d*\.xml$', n):
            continue
        out['sheets'] += 1
        r = ET.fromstring(z.read(n))
        for c in r.iter('{%s}c' % ns['m']):
            f = c.find('m:f', ns)
            v = c.find('m:v', ns)
            t = c.get('t')
            if f is not None and (f.text or f.get('t') == 'shared' or f.get('ref')):
                out['formulas'] += 1
                if v is not None and v.text not in (None, '') and t not in ('s', 'str', 'e', 'b'):
                    try:
                        out['formula_vals'].append(float(v.text))
                    except Exception:
                        pass
                elif v is None or v.text in (None, ''):
                    out['formula_no_cache'] += 1
            if t == 's' and v is not None:
                try:
                    out['strings'].append(sst[int(v.text)])
                except Exception:
                    pass
            elif t == 'inlineStr':
                out['strings'].append(''.join(x.text or '' for x in c.iter('{%s}t' % ns['m'])))
            elif t == 'str' and v is not None:
                out['strings'].append(v.text or '')
            elif v is not None and t in (None, 'n'):
                try:
                    out['numbers'].append(float(v.text))
                except Exception:
                    pass
    return out


def soffice_recalc_values(xlsx_path, tmp):
    """用 soffice 转 csv（所有表）取值，供公式无缓存值时近似。返回数值列表。"""
    vals = []
    try:
        od = tmp / 'recalc'
        od.mkdir(exist_ok=True)
        subprocess.run(['soffice', '--headless', '--convert-to',
                        'csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,-1',
                        '--outdir', str(od), str(xlsx_path)], capture_output=True, timeout=180)
        for c in od.glob('*.csv'):
            for row in csv.reader(io.StringIO(c.read_text(errors='replace'))):
                for x in row:
                    try:
                        vals.append(float(x.replace(',', '')))
                    except Exception:
                        pass
    except Exception:
        pass
    return vals


def _fe_col(c):
    n = 0
    for ch in c:
        n = n * 26 + ord(ch) - 64
    return n


def _fe_ncol(n):
    s = ''
    while n:
        n, m = divmod(n - 1, 26)
        s = chr(65 + m) + s
    return s


def _fe_flat(a):
    o = []
    for x in a:
        if isinstance(x, (list, tuple)):
            o += _fe_flat(x)
        else:
            o.append(x)
    return o


def formula_eval_values(xlsx_path):
    """Pure-python values of simple arithmetic formula cells (+-*/^, %, cell refs/ranges incl. other sheets, SUM AVERAGE
    ROUND ABS MIN MAX). The real verifier image has no LibreOffice Calc (soffice cannot load .xlsx there) and the
    agent image writes workbooks with xlsxwriter, which caches 0 for formulas; this gives the formula results directly.
    Unsupported formulas are skipped. Returns a list of floats."""
    m_ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    r_ns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
    try:
        z = zipfile.ZipFile(str(xlsx_path))
        names = set(z.namelist())
        ss = []
        if 'xl/sharedStrings.xml' in names:
            ss = [''.join(t.text or '' for t in si.iter(m_ns + 't'))
                  for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(m_ns + 'si')]
        rels = {}
        if 'xl/_rels/workbook.xml.rels' in names:
            for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')):
                tg = r.get('Target') or ''
                rels[r.get('Id')] = tg.lstrip('/') if tg.startswith('/') else posixpath.normpath('xl/' + tg)
        sheets = {}
        order = []
        for s in ET.fromstring(z.read('xl/workbook.xml')).iter(m_ns + 'sheet'):
            part = rels.get(s.get(r_ns + 'id'))
            if part not in names:
                continue
            cells = {}
            for c in ET.fromstring(z.read(part)).iter(m_ns + 'c'):
                ref, t = c.get('r'), c.get('t')
                f, v = c.find(m_ns + 'f'), c.find(m_ns + 'v')
                val = None
                if t == 's' and v is not None:
                    try:
                        val = ss[int(v.text)]
                    except Exception:
                        val = None
                elif t == 'inlineStr':
                    val = ''.join(x.text or '' for x in c.iter(m_ns + 't'))
                elif v is not None and v.text not in (None, ''):
                    try:
                        val = float(v.text) if t not in ('str', 'e', 'b') else v.text
                    except ValueError:
                        val = v.text
                if ref:
                    cells[ref] = (val, f.text if f is not None and f.text else None)
            sheets[s.get('name')] = cells
            order.append(s.get('name'))
    except Exception:
        return []

    def cell(sh, ref, depth):
        cells = sheets.get(sh) if sh in sheets else sheets.get(sh.strip("'"))
        if cells is None or depth > 30:
            raise ValueError('ref')
        ref = ref.replace('$', '')
        if ref not in cells:
            return 0.0
        v, f = cells[ref]
        if f:
            return formula(sh, f, depth + 1)
        if isinstance(v, float):
            return v
        if isinstance(v, str):
            return float(v)
        return 0.0

    def formula(sheet, f, depth):
        def rng(sh, a, b):
            ca, ra = re.match(r'([A-Z]+)(\d+)', a.replace('$', '')).groups()
            cb, rb = re.match(r'([A-Z]+)(\d+)', b.replace('$', '')).groups()
            out = []
            cells = sheets.get(sh) or {}
            for r in range(int(ra), int(rb) + 1):
                for c in range(_fe_col(ca), _fe_col(cb) + 1):
                    k = _fe_ncol(c) + str(r)
                    if k in cells and (cells[k][1] or isinstance(cells[k][0], float)):
                        out.append(cell(sh, k, depth))
            return out

        env = {'SUM': lambda *a: sum(_fe_flat(a)), 'AVERAGE': lambda *a: sum(_fe_flat(a)) / len(_fe_flat(a)),
               'ROUND': lambda x, n=0: round(x, int(n)), 'ABS': abs, 'MIN': lambda *a: min(_fe_flat(a)),
               'MAX': lambda *a: max(_fe_flat(a)), 'RNG': rng, 'CELL': lambda sh, r: cell(sh, r, depth)}
        expr = f.lstrip('=')
        sref = r"(?:'([^']+)'|([A-Za-z_][\w\.]*))!"
        expr = re.sub(sref + r"(\$?[A-Z]+\$?\d+):(\$?[A-Z]+\$?\d+)",
                      lambda m: "RNG(%s,'%s','%s')" % (json.dumps(m.group(1) or m.group(2)), m.group(3), m.group(4)), expr)
        expr = re.sub(sref + r"(\$?[A-Z]+\$?\d+)",
                      lambda m: "CELL(%s,'%s')" % (json.dumps(m.group(1) or m.group(2)), m.group(3)), expr)
        expr = re.sub(r"(?<![\w'\"])(\$?[A-Z]{1,3}\$?\d+):(\$?[A-Z]{1,3}\$?\d+)",
                      lambda m: "RNG(%s,'%s','%s')" % (json.dumps(sheet), m.group(1), m.group(2)), expr)
        expr = re.sub(r"(?<![\w'\"])(\$?[A-Z]{1,3}\$?\d+)(?![\w(])",
                      lambda m: "CELL(%s,'%s')" % (json.dumps(sheet), m.group(1)), expr)
        expr = expr.replace('^', '**')
        expr = re.sub(r'(\d+(?:\.\d+)?)%', r'(\1/100)', expr)
        bare = re.sub(r'"[^"]*"|\'[^\']*\'', '0', expr)
        if any(w not in env for w in re.findall(r'[A-Za-z_]\w*', bare)) or re.search(r'[<>&{}\[\];:@]', bare):
            raise ValueError('unsupported ' + f)
        return float(eval(expr, {'__builtins__': {}}, env))

    vals = []
    for sh in order:
        for ref, (v, f) in sheets[sh].items():
            if f:
                try:
                    vals.append(formula(sh, f, 0))
                except Exception:
                    pass
    return vals


# ---------------- text helpers ----------------
def toks(s):
    return set(re.findall(r"[a-z0-9]+(?:[.:'][a-z0-9]+)*", (s or '').lower()))


def jaccard(a, b):
    A, B = toks(a), toks(b)
    if not A and not B:
        return 1.0
    return len(A & B) / max(1, len(A | B))


def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', (s or '').lower())).strip()


def title_in_page(title, page_text):
    t = norm(title)
    p = norm(page_text)
    if not t:
        return False
    if t in p:
        return True
    tw = t.split()
    pw = set(p.split())
    rec = sum(1 for w in tw if w in pw) / max(1, len(tw))
    if rec >= 0.8:
        return True
    return SequenceMatcher(None, t, p[:len(t) * 2 + 40]).ratio() >= 0.8


def pdf_page_texts(path):
    try:
        from pypdf import PdfReader
        rd = PdfReader(str(path))
        return [(pg.extract_text() or '') for pg in rd.pages]
    except Exception:
        out = subprocess.run(['pdftotext', '-layout', str(path), '-'], capture_output=True, text=True, timeout=120).stdout
        pages = out.split('\f')
        if pages and not pages[-1].strip():
            pages = pages[:-1]
        return pages


def deck_titles_notes(path):
    from pptx import Presentation
    from pptx.enum.shapes import PP_PLACEHOLDER
    prs = Presentation(str(path))
    titles, notes, bodies = [], [], []
    for s in prs.slides:
        t = ''
        for sh in s.placeholders:
            try:
                if sh.placeholder_format.type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE):
                    t = sh.text_frame.text
                    break
            except Exception:
                pass
        if not t:
            # 退化：最上方含文字的形状
            cands = [sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.strip() and sh.top is not None]
            if cands:
                t = sorted(cands, key=lambda x: (x.top, x.left))[0].text_frame.text
        titles.append(t.strip())
        notes.append(s.notes_slide.notes_text_frame.text if s.has_notes_slide else '')
        bodies.append(s)
    return prs, titles, notes


def font_bullet_scan(prs):
    """返回 (small_runs: [(slide, size_pt, text)], bullets_per_slide: [(slide, n)])。只看 sp 文本框（不含表格/图表）。
    要点数：整页所有非标题文本框中项目符号段落数之和（v2026-10-25：原为单个文本框的最大值）。"""
    from pptx.enum.shapes import PP_PLACEHOLDER
    small, bul = [], []
    for i, s in enumerate(prs.slides, 1):
        mx = 0
        for sh in _iter_shapes(s.shapes):
            if not getattr(sh, 'has_text_frame', False) or not sh.has_text_frame:
                continue
            is_title = False
            try:
                if sh.is_placeholder and sh.placeholder_format.type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE):
                    is_title = True
            except Exception:
                pass
            paras = [p for p in sh.text_frame.paragraphs if ''.join(r.text for r in p.runs).strip()]
            if not is_title:
                bulletish = [p for p in paras if _is_bullet(p, sh)]
                mx += len(bulletish)  # v2026-10-25: per-slide total over all non-title frames (was max per frame)
            for p in paras:
                for r in p.runs:
                    if r.font.size is not None and r.text.strip() and r.font.size.pt < 12:
                        small.append((i, r.font.size.pt, r.text[:40]))
        bul.append((i, mx))
    return small, bul


def _is_bullet(p, sh):
    pPr = p._p.find('{%s}pPr' % NS['a'])
    if pPr is not None:
        if pPr.find('{%s}buNone' % NS['a']) is not None:
            return False
        if pPr.find('{%s}buChar' % NS['a']) is not None or pPr.find('{%s}buAutoNum' % NS['a']) is not None:
            return True
    # 正文占位符默认有项目符号
    try:
        return bool(sh.is_placeholder and sh.placeholder_format.idx not in (0,))
    except Exception:
        return False


def _iter_shapes(shapes):
    for sh in shapes:
        if sh.shape_type is not None and 'GROUP' in str(sh.shape_type):
            yield from _iter_shapes(sh.shapes)
        else:
            yield sh


# ---------------- script.md ----------------
DUR_RE = re.compile(r'(?:(\d{1,2}):(\d{2}))|(?:(\d+(?:\.\d+)?)\s*(?:s\b|sec|secs|seconds))|(?:(\d+(?:\.\d+)?)\s*(?:min|mins|minutes)\b)', re.I)


def split_script(text):
    """按 'Slide N' 标题切分。返回 {n: section_text}。"""
    secs = {}
    hdr = re.compile(r'^\s*(?:#{1,6}\s*|\*\*\s*)?slide\s*(\d{1,2})\b.*$', re.I | re.M)
    ms = list(hdr.finditer(text))
    for k, m in enumerate(ms):
        n = int(m.group(1))
        end = ms[k + 1].start() if k + 1 < len(ms) else len(text)
        secs.setdefault(n, text[m.start():end])
    return secs


def section_duration(sec):
    """在章节文本中找时长声明（含 duration/time/est 关键词的行或标题行）。返回秒或 None。"""
    lines = sec.splitlines()
    cand = [lines[0]] + [l for l in lines[1:] if re.search(r'duration|time|est|timing|length|⏱', l, re.I)]
    for l in cand:
        for m in DUR_RE.finditer(l):
            if m.group(1):
                return int(m.group(1)) * 60 + int(m.group(2))
            if m.group(3):
                return float(m.group(3))
            if m.group(4):
                return float(m.group(4)) * 60
    return None


def strip_script_markup(sec):
    lines = sec.splitlines()[1:]
    keep = []
    for l in lines:
        if re.search(r'^\s*(?:\*\*)?(?:duration|est\.?|estimated|timing|time)\b', l, re.I):
            continue
        keep.append(l)
    t = '\n'.join(keep)
    t = re.sub(r'\[[^\]]*\]', ' ', t)
    t = re.sub(r'\([^)]*(?:click|trigger|duration|sec|min)[^)]*\)', ' ', t, flags=re.I)
    t = re.sub(r'[#*_>`]', ' ', t)
    return t


def find_col(header, pats):
    h = [norm(x) for x in header]
    for i, x in enumerate(h):
        if all(re.search(p, x) for p in pats):
            return i
    return None


def read_csv(path):
    raw = path.read_bytes().decode('utf-8-sig', errors='replace')
    try:
        dialect = csv.Sniffer().sniff(raw[:4000], delimiters=',;\t')
    except Exception:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(raw), dialect))
    rows = [r for r in rows if any(c.strip() for c in r)]
    return rows


def slide_nums(cell):
    return {int(x) for x in re.findall(r'\d+', cell or '')}


def ffprobe(path):
    o = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                       capture_output=True, text=True, timeout=60).stdout
    return json.loads(o)


# ---------------- v2026-10-25 additions (rubric cleanup) ----------------
def _lvl_sz(lst, lvl):
    """a:lstStyle / p:txStyles child -> sz (pt) for level lvl (1-based) or None."""
    if lst is None:
        return None
    el = lst.find('{%s}lvl%dpPr' % (NS['a'], lvl))
    if el is None:
        return None
    d = el.find('{%s}defRPr' % NS['a'])
    if d is not None and d.get('sz'):
        return int(d.get('sz')) / 100.0
    return None


def _ph_sz(ph_shape, lvl):
    try:
        tb = ph_shape._element.find('.//{%s}txBody' % NS['p'])
        if tb is None:
            return None
        return _lvl_sz(tb.find('{%s}lstStyle' % NS['a']), lvl)
    except Exception:
        return None


def _font_scale(sh):
    try:
        bp = sh.text_frame._txBody.find('{%s}bodyPr' % NS['a'])
        na = bp.find('{%s}normAutofit' % NS['a']) if bp is not None else None
        if na is not None and na.get('fontScale'):
            return int(na.get('fontScale')) / 100000.0
    except Exception:
        pass
    return 1.0


def resolve_run_size(prs, slide, sh, para, run):
    """Effective font size (pt) of a run: run rPr -> paragraph defRPr -> shape lstStyle -> layout/master placeholder
    lstStyle -> master txStyles (title/body/other) -> presentation defaultTextStyle -> 18 pt. normAutofit fontScale
    is applied. Never raises (returns None only if nothing at all can be resolved)."""
    from pptx.enum.shapes import PP_PLACEHOLDER
    try:
        lvl = min(9, (para.level or 0) + 1)
    except Exception:
        lvl = 1
    scale = _font_scale(sh)
    try:
        if run is not None and run.font.size is not None:
            return run.font.size.pt * scale
    except Exception:
        pass
    try:
        pPr = para._p.find('{%s}pPr' % NS['a'])
        d = pPr.find('{%s}defRPr' % NS['a']) if pPr is not None else None
        if d is not None and d.get('sz'):
            return int(d.get('sz')) / 100.0 * scale
    except Exception:
        pass
    try:
        s = _lvl_sz(sh.text_frame._txBody.find('{%s}lstStyle' % NS['a']), lvl)
        if s:
            return s * scale
    except Exception:
        pass
    kind = 'other'
    try:
        if sh.is_placeholder:
            pf = sh.placeholder_format
            kind = 'title' if pf.type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE) else 'body'
            if pf.type in (PP_PLACEHOLDER.DATE, PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.SLIDE_NUMBER):
                kind = 'other'
            lay = slide.slide_layout
            cand = []
            for p2 in lay.placeholders:
                try:
                    if p2.placeholder_format.idx == pf.idx:
                        cand.append(p2)
                except Exception:
                    pass
            for c in cand:
                s = _ph_sz(c, lvl)
                if s:
                    return s * scale
            for p2 in lay.slide_master.placeholders:
                try:
                    if p2.placeholder_format.type == pf.type or (kind == 'body' and 'BODY' in str(p2.placeholder_format.type)):
                        s = _ph_sz(p2, lvl)
                        if s:
                            return s * scale
                except Exception:
                    pass
    except Exception:
        pass
    try:
        m = slide.slide_layout.slide_master._element
        ts = m.find('{%s}txStyles' % NS['p'])
        if ts is not None and kind in ('title', 'body'):
            s = _lvl_sz(ts.find('{%s}%sStyle' % (NS['p'], kind)), lvl)
            if s:
                return s * scale
    except Exception:
        pass
    try:
        dts = prs.part._element.find('{%s}defaultTextStyle' % NS['p'])
        s = _lvl_sz(dts, lvl)
        if s:
            return s * scale
    except Exception:
        pass
    try:
        m = slide.slide_layout.slide_master._element
        ts = m.find('{%s}txStyles' % NS['p'])
        s = _lvl_sz(ts.find('{%s}otherStyle' % NS['p']), lvl) if ts is not None else None
        if s:
            return s * scale
    except Exception:
        pass
    return 18.0 * scale


CAPTION_RE = re.compile(r'^\s*(?:sources?|credit|credits|note|notes|caption|fig(?:ure)?\.?|map|data|adapted|after|from)\b', re.I)


def text_size_scan(prs):
    """Per slide: list of text shapes with role and resolved sizes.
    role: 'title' (title placeholder), 'body' (body/object placeholder, plus the slide's main other text shape: the
    non-placeholder text box with the most words when it has >=20 words and does not start like a source/caption line), 'minor'
    (everything else: captions, source lines, labels, callouts). Returns [(slide_no, [ {role, words, min_pt, text} ])]."""
    from pptx.enum.shapes import PP_PLACEHOLDER
    out = []
    for i, s in enumerate(prs.slides, 1):
        rows = []
        for sh in _iter_shapes(s.shapes):
            if not getattr(sh, 'has_text_frame', False) or not sh.has_text_frame:
                continue
            txt = sh.text_frame.text.strip()
            if not txt:
                continue
            role = 'minor'
            try:
                if sh.is_placeholder:
                    t = sh.placeholder_format.type
                    if t in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE):
                        role = 'title'
                    elif t in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT) and not CAPTION_RE.match(txt):
                        role = 'body'
            except Exception:
                pass
            sizes = []
            for p in sh.text_frame.paragraphs:
                runs = [r for r in p.runs if r.text.strip()]
                for r in runs:
                    sz = resolve_run_size(prs, s, sh, p, r)
                    if sz:
                        sizes.append(sz)
            rows.append({'role': role, 'words': len(txt.split()), 'min_pt': min(sizes) if sizes else None,
                         'text': txt[:50], 'shape': sh})
        cands = [r for r in rows if r['role'] == 'minor' and r['words'] >= 20 and not CAPTION_RE.match(r['text'])]
        if cands:
            max(cands, key=lambda r: r['words'])['role'] = 'body'
        for r in rows:
            r.pop('shape', None)
        out.append((i, rows))
    return out


def font_rule_check(prs, body_min=20.0, minor_min=12.0, max_bullets=6):
    """Deterministic font / bullet rule. Returns (ok, detail)."""
    small, bul = font_bullet_scan(prs)
    over = [(i, n) for i, n in bul if n > max_bullets]
    bad_body, bad_minor = [], []
    for i, rows in text_size_scan(prs):
        for r in rows:
            if r['min_pt'] is None:
                continue
            if r['role'] == 'body' and r['min_pt'] < body_min - 0.25:
                bad_body.append((i, round(r['min_pt'], 1), r['text'][:30]))
            elif r['role'] == 'minor' and r['min_pt'] < minor_min - 0.25:
                bad_minor.append((i, round(r['min_pt'], 1), r['text'][:30]))
    probs = []
    if bad_body:
        probs.append('body text <%g pt: %s' % (body_min, bad_body[:4]))
    if bad_minor:
        probs.append('caption/label text <%g pt: %s' % (minor_min, bad_minor[:4]))
    if over:
        probs.append('>%d bullets on slides %s' % (max_bullets, over))
    if probs:
        return False, '; '.join(probs)
    return True, 'resolved sizes: body >=%g pt, other text >=%g pt; bullets per slide %s' % (body_min, minor_min, [n for _, n in bul])


def shapes_outside_slide(prs, tol_emu=12700):
    """List (slide, name) of shapes whose bbox extends beyond the slide (incl. tables: frame size)."""
    W, H = prs.slide_width, prs.slide_height
    bad = []
    for i, s in enumerate(prs.slides, 1):
        for sh in s.shapes:
            try:
                l, t, w, h = sh.left, sh.top, sh.width, sh.height
                if None in (l, t, w, h):
                    continue
                if getattr(sh, 'has_table', False) and sh.has_table:
                    h = max(h, sum(r.height for r in sh.table.rows))
                if l < -tol_emu or t < -tol_emu or l + w > W + tol_emu or t + h > H + tol_emu:
                    bad.append((i, sh.name))
            except Exception:
                pass
    return bad


def hhmm(s):
    m = re.search(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', s or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def all_hhmm(s):
    return [int(a) * 60 + int(b) for a, b in re.findall(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', s or '')]


def pdf_page_text(pdf, page):
    """pdftotext of one 1-based page ('' on any error)."""
    try:
        return subprocess.run(['pdftotext', '-layout', '-f', str(page), '-l', str(page), str(pdf), '-'],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ''


def shape_boxes(slide):
    """spid(str) -> (left, top, right, bottom, kind, has_text, shape) in slide EMU, group children transformed."""
    out = {}

    def walk(shapes, tf):
        for sh in shapes:
            try:
                l, t, w, h = sh.left, sh.top, sh.width, sh.height
            except Exception:
                continue
            if None in (l, t, w, h):
                continue
            ox, oy, sx, sy = tf
            L_, T_ = ox + l * sx, oy + t * sy
            box = (L_, T_, L_ + w * sx, T_ + h * sy)
            kind = str(sh.shape_type)
            tag = sh._element.tag.rsplit('}', 1)[-1]
            txt = sh.text_frame.text.strip() if getattr(sh, 'has_text_frame', False) and sh.has_text_frame else ''
            out[str(sh.shape_id)] = box + (tag, bool(txt), sh)
            if tag == 'grpSp':
                try:
                    x = sh._element.grpSpPr.find('{%s}xfrm' % NS['a'])
                    co, ce = x.find('{%s}chOff' % NS['a']), x.find('{%s}chExt' % NS['a'])
                    cx, cy = int(co.get('x')), int(co.get('y'))
                    cw, ch = int(ce.get('cx')) or 1, int(ce.get('cy')) or 1
                    nsx, nsy = w * sx / cw, h * sy / ch
                    walk(sh.shapes, (L_ - cx * nsx, T_ - cy * nsy, nsx, nsy))
                except Exception:
                    walk(sh.shapes, tf)
    walk(slide.shapes, (0, 0, 1.0, 1.0))
    return out


def _iv(a0, a1, b0, b1, eps):
    la, lb = a1 - a0, b1 - b0
    if la < eps or lb < eps:
        (p0, p1), (q0, q1) = ((a0, a1), (b0, b1)) if la < lb else ((b0, b1), (a0, a1))
        return q0 + eps < p0 and p1 < q1 - eps
    return min(a1, b1) - max(a0, b0) > eps


def boxes_overlap(a, b, eps=45720):
    """Meaningful overlap of two (l, t, r, b) boxes; degenerate (line) boxes must lie strictly inside the other."""
    return _iv(a[0], a[2], b[0], b[2], eps) and _iv(a[1], a[3], b[1], b[3], eps)


def _seg_hits_rect(p0, p1, rect, eps):
    """Liang-Barsky: does segment p0-p1 pass through rect shrunk by eps?"""
    l, t, r, b = rect[0] + eps, rect[1] + eps, rect[2] - eps, rect[3] - eps
    if l >= r or t >= b:
        return False
    x0, y0 = p0
    dx, dy = p1[0] - x0, p1[1] - y0
    u0, u1 = 0.0, 1.0
    for pp, q in ((-dx, x0 - l), (dx, r - x0), (-dy, y0 - t), (dy, b - y0)):
        if pp == 0:
            if q < 0:
                return False
        else:
            u = q / float(pp)
            if pp < 0:
                u0 = max(u0, u)
            else:
                u1 = min(u1, u)
            if u0 > u1:
                return False
    return True


def connector_path(sh, box):
    """Approximate path of a connector in slide EMU: straight = diagonal of its box (honouring flips);
    bent/curved = elbow through the box's horizontal middle."""
    l, t, r, b = box[:4]
    try:
        x = sh._element.spPr.find('{%s}xfrm' % NS['a'])
        fh, fv = x.get('flipH') in ('1', 'true'), x.get('flipV') in ('1', 'true')
        geom = sh._element.spPr.find('{%s}prstGeom' % NS['a']).get('prst', 'line')
    except Exception:
        fh = fv = False
        geom = 'line'
    x0, x1 = (r, l) if fh else (l, r)
    y0, y1 = (b, t) if fv else (t, b)
    if geom.startswith('bent') or geom.startswith('curved'):
        xm = (x0 + x1) / 2.0
        return [((x0, y0), (xm, y0)), ((xm, y0), (xm, y1)), ((xm, y1), (x1, y1))]
    return [((x0, y0), (x1, y1))]


def connector_crosses(sh, box, rect, eps=91440):
    return any(_seg_hits_rect(a, b, rect, eps) for a, b in connector_path(sh, box))
