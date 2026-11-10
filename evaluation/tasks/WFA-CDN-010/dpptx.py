# -*- coding: utf-8 -*-
"""Shared deterministic PPTX/PDF/script helpers for CDC-D verifiers (pure zip+lxml, python-pptx, pypdf, ffprobe).

No COM / PowerPoint here: package integrity is a static approximation of "opens without repair".
"""
import csv, io, json, posixpath, re, subprocess, zipfile
from lxml import etree

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'p14': 'http://schemas.microsoft.com/office/powerpoint/2010/main',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'ct': 'http://schemas.openxmlformats.org/package/2006/content-types',
    's': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
}
R_ID = '{%s}id' % NS['r']
R_EMBED = '{%s}embed' % NS['r']
R_LINK = '{%s}link' % NS['r']
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’.,:\-/][A-Za-z0-9]+)*")


# ---------------- package ----------------
def rels_path(part):
    d, f = posixpath.split(part)
    return posixpath.join(d, '_rels', f + '.rels')


def read_rels(z, part):
    rp = rels_path(part)
    out = {}
    if rp not in z.namelist():
        return out
    root = etree.fromstring(z.read(rp))
    for r in root.findall('rel:Relationship', NS):
        mode = r.get('TargetMode', 'Internal')
        tgt = r.get('Target')
        if mode != 'External':
            tgt = posixpath.normpath(posixpath.join(posixpath.dirname(part), tgt)) if not tgt.startswith('/') else tgt.lstrip('/')
        out[r.get('Id')] = {'type': r.get('Type', '').rsplit('/', 1)[-1], 'target': tgt, 'mode': mode}
    return out


def integrity(path):
    """Static checks that commonly trigger PowerPoint's repair prompt. Returns list of issues."""
    issues = []
    try:
        z = zipfile.ZipFile(path)
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
            for rid, r in read_rels(z, src).items():
                if r['mode'] != 'External' and r['target'] not in names:
                    issues.append(f'{n} {rid} -> missing {r["target"]}')
        except Exception as e:
            issues.append(f'bad rels {n}: {e}')
    return issues[:30]


class Deck:
    def __init__(self, path):
        self.path = path
        self.z = zipfile.ZipFile(path)
        self.names = set(self.z.namelist())
        pres = etree.fromstring(self.z.read('ppt/presentation.xml'))
        prels = read_rels(self.z, 'ppt/presentation.xml')
        self.slides = []
        for s in pres.findall('p:sldIdLst/p:sldId', NS):
            self.slides.append(prels[s.get(R_ID)]['target'])
        sz = pres.find('p:sldSz', NS)
        self.cx, self.cy = int(sz.get('cx')), int(sz.get('cy'))
        self._x = {}

    def xml(self, part):
        if part not in self._x:
            self._x[part] = etree.fromstring(self.z.read(part))
        return self._x[part]

    def rels(self, part):
        return read_rels(self.z, part)

    def external_links(self):
        out = []
        for n in self.names:
            if n.endswith('.rels'):
                src = n.replace('_rels/', '')[:-5]
                for rid, r in read_rels(self.z, src).items():
                    if r['mode'] == 'External' and r['type'] != 'hyperlink':
                        out.append(f'{src}:{r["type"]}->{r["target"]}')
        return out

    # ---- shapes
    def shape_boxes(self, i):
        """spid -> dict(kind, name, box(x,y,cx,cy), text) for top-level and grouped shapes (group offsets ignored)."""
        root = self.xml(self.slides[i])
        out = {}
        for el in root.iter('{%s}sp' % NS['p'], '{%s}pic' % NS['p'], '{%s}cxnSp' % NS['p'], '{%s}graphicFrame' % NS['p']):
            c = el.find('.//p:cNvPr', NS)
            if c is None:
                continue
            off = el.find('.//a:xfrm/a:off', NS) if el.tag != '{%s}graphicFrame' % NS['p'] else el.find('p:xfrm/a:off', NS)
            ext = el.find('.//a:xfrm/a:ext', NS) if el.tag != '{%s}graphicFrame' % NS['p'] else el.find('p:xfrm/a:ext', NS)
            box = None
            if off is not None and ext is not None:
                box = (int(off.get('x')), int(off.get('y')), int(ext.get('cx')), int(ext.get('cy')))
            txt = ' '.join(t.text or '' for t in el.iter('{%s}t' % NS['a'])).strip()
            ph = el.find('.//p:nvPr/p:ph', NS)
            out[c.get('id')] = {'kind': etree.QName(el).localname, 'name': c.get('name'), 'box': box, 'text': txt,
                                'ph': None if ph is None else (ph.get('type') or 'body'), 'el': el}
        return out

    def connectors(self, i):
        root = self.xml(self.slides[i])
        res = []
        for el in root.iter('{%s}cxnSp' % NS['p']):
            st = el.find('.//a:stCxn', NS)
            en = el.find('.//a:endCxn', NS)
            res.append((None if st is None else st.get('id'), None if en is None else en.get('id')))
        return res

    def pictures(self, i):
        root = self.xml(self.slides[i])
        rels = self.rels(self.slides[i])
        out = []
        for el in root.iter('{%s}pic' % NS['p']):
            if el.find('.//a:videoFile', NS) is not None or el.find('.//a:audioFile', NS) is not None:
                continue
            b = el.find('.//a:blip', NS)
            if b is not None and b.get(R_EMBED) in rels:
                out.append(el.find('.//p:cNvPr', NS).get('id'))
        return out

    def text_frames(self, i):
        """list of (spid, is_title, [non-empty paragraph texts]) for sp text bodies."""
        root = self.xml(self.slides[i])
        out = []
        for el in root.iter('{%s}sp' % NS['p']):
            tb = el.find('p:txBody', NS)
            if tb is None:
                continue
            ph = el.find('.//p:nvPr/p:ph', NS)
            is_title = ph is not None and ph.get('type') in ('title', 'ctrTitle')
            paras = []
            for p in tb.findall('a:p', NS):
                t = ''.join(x.text or '' for x in p.iter('{%s}t' % NS['a'])).strip()
                if t:
                    paras.append(t)
            out.append((el.find('.//p:cNvPr', NS).get('id'), is_title, paras))
        return out

    def title(self, i):
        for _, is_t, paras in self.text_frames(i):
            if is_t and paras:
                return ' '.join(paras)
        return ''

    def slide_text(self, i):
        return ' '.join(' '.join(p) for _, _, p in self.text_frames(i))

    def notes(self, i):
        for rid, r in self.rels(self.slides[i]).items():
            if r['type'] == 'notesSlide' and r['target'] in self.names:
                root = self.xml(r['target'])
                parts = []
                for sp in root.iter('{%s}sp' % NS['p']):
                    ph = sp.find('.//p:nvPr/p:ph', NS)
                    if ph is not None and ph.get('type') == 'body':
                        for p in sp.iter('{%s}p' % NS['a']):
                            parts.append(''.join(x.text or '' for x in p.iter('{%s}t' % NS['a'])))
                return '\n'.join(parts).strip()
        return ''

    # ---- charts
    def charts(self):
        """list of dict(slide, part, wb_bytes or None, wb_err)."""
        out = []
        for i, s in enumerate(self.slides):
            rels = self.rels(s)
            root = self.xml(s)
            for ch in root.iter('{%s}chart' % NS['c']):
                rid = ch.get(R_ID)
                if rid not in rels:
                    continue
                part = rels[rid]['target']
                d = {'slide': i + 1, 'part': part, 'wb': None, 'err': None}
                if part not in self.names:
                    d['err'] = 'chart part missing'
                    out.append(d)
                    continue
                crels = self.rels(part)
                cx = self.xml(part)
                ext = cx.find('c:externalData', NS)
                if ext is None:
                    d['err'] = 'no externalData (no embedded workbook)'
                else:
                    r = crels.get(ext.get(R_ID))
                    if not r:
                        d['err'] = 'externalData rel missing'
                    elif r['mode'] == 'External':
                        d['err'] = f'workbook linked externally: {r["target"]}'
                    elif r['target'] not in self.names:
                        d['err'] = 'embedded workbook part missing'
                    else:
                        d['wb'] = self.z.read(r['target'])
                out.append(d)
        return out

    # ---- media
    def media(self, i):
        """audio/video on slide i: list of dict(spid, kind, linked, target, bookmarks[(name, sec)])."""
        s = self.slides[i]
        root = self.xml(s)
        rels = self.rels(s)
        out = []
        for el in root.iter('{%s}pic' % NS['p']):
            af = el.find('.//a:audioFile', NS)
            vf = el.find('.//a:videoFile', NS)
            f = af if af is not None else vf
            if f is None:
                continue
            m = el.find('.//p14:media', NS)
            tgt, linked = None, False
            rid = m.get(R_EMBED) if m is not None else None
            if rid and rid in rels:
                tgt = rels[rid]['target']
                linked = rels[rid]['mode'] == 'External'
            else:
                r = rels.get(f.get(R_LINK)) or {}
                tgt = r.get('target')
                linked = r.get('mode') == 'External'
            bm = []
            if m is not None:
                for b in m.iter('{%s}bmk' % NS['p14']):
                    try:
                        bm.append((b.get('name'), int(b.get('time')) / 1000.0))
                    except Exception:
                        pass
            out.append({'spid': el.find('.//p:cNvPr', NS).get('id'), 'kind': 'audio' if af is not None else 'video',
                        'linked': linked, 'target': tgt, 'bookmarks': bm})
        return out

    # ---- timing
    def timing(self, i):
        """Return dict(main=[effects], inter=[{trigger_spid, bookmark, evt, effects:[...]}]).
        effect = dict(node, cls, spid)."""
        root = self.xml(self.slides[i])
        tm = root.find('p:timing', NS)
        res = {'main': [], 'inter': [], 'media_auto': [], 'media_calls': []}
        if tm is None:
            return res

        def effects(node):
            out = []
            for ctn in node.iter('{%s}cTn' % NS['p']):
                cls = ctn.get('presetClass')
                if cls is None:
                    continue
                tg = ctn.find('.//p:spTgt', NS)
                out.append({'node': ctn.get('nodeType'), 'cls': cls, 'spid': None if tg is None else tg.get('spid'), 'el': ctn})
            return out

        for ctn in tm.iter('{%s}cTn' % NS['p']):
            nt = ctn.get('nodeType')
            if nt == 'mainSeq':
                res['main'] = effects(ctn)
                # media autoplay: mediacall effect inside the first top-level par that is not click-started
                pars = ctn.findall('p:childTnLst/p:par', NS)
                for k, par in enumerate(pars):
                    conds = par.findall('p:cTn/p:stCondLst/p:cond', NS)
                    auto = any(c.get('evt') == 'onBegin' for c in conds) or (conds and all(c.get('delay') not in (None, 'indefinite') for c in conds))
                    for e in effects(par):
                        if e['cls'] == 'mediacall':
                            res['media_calls'].append(e['spid'])
                            if k == 0 and (auto or e['node'] in ('withEffect', 'afterEffect') and auto):
                                res['media_auto'].append(e['spid'])
            elif nt == 'interactiveSeq':
                trig, bmk, evt = None, None, None
                for c in ctn.findall('p:stCondLst/p:cond', NS) + ctn.findall('p:stCondLst//p:cond', NS):
                    if c.get('evt') in ('onClick', 'onMediaBookmark', 'onBegin'):
                        evt = c.get('evt')
                        for t in c.iter():
                            if t.get('spid') is not None:
                                trig = t.get('spid')
                            if t.get('bmkName') is not None:
                                bmk = t.get('bmkName')
                        break
                res['inter'].append({'trigger': trig, 'bookmark': bmk, 'evt': evt, 'effects': effects(ctn)})
        # also catch AlternateContent-wrapped bookmark conds (bmkName anywhere under seq)
        for it in res['inter']:
            if it['bookmark'] is None:
                for e in [it]:
                    pass
        return res


# ---------------- xlsx (no openpyxl) ----------------
def xlsx_first_sheet(b):
    """Return list of cells dict(ref, v, f, t) for first worksheet of xlsx bytes."""
    z = zipfile.ZipFile(io.BytesIO(b))
    wb = etree.fromstring(z.read('xl/workbook.xml'))
    first = wb.find('s:sheets/s:sheet', NS)
    rels = read_rels(z, 'xl/workbook.xml')
    part = rels[first.get(R_ID)]['target']
    ss = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in etree.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS):
            ss.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['s'])))
    sh = etree.fromstring(z.read(part))
    cells = []
    for c in sh.iter('{%s}c' % NS['s']):
        v = c.find('s:v', NS)
        f = c.find('s:f', NS)
        t = c.get('t')
        val = v.text if v is not None else None
        if t == 's' and val is not None:
            try:
                val = ss[int(val)]
            except Exception:
                pass
        elif t == 'inlineStr':
            val = ''.join(x.text or '' for x in c.iter('{%s}t' % NS['s']))
        cells.append({'ref': c.get('r'), 'v': val, 'f': None if f is None else (f.text or 'shared'), 't': t})
    return cells


def is_num(s):
    try:
        float(str(s).replace(',', ''))
        return True
    except Exception:
        return False


PAGE_RE = re.compile(r'(\bp{1,2}\.?\s*\d+|\bpages?\s*\d+|\bpdf\s*(p|page)?\.?\s*\d+|\bpage\b|\bsource\b)', re.I)


# ---------------- script.md ----------------
SLIDE_HDR = re.compile(r'^\s*(?:#{1,6}\s*|\*\*\s*|\[)?\s*slide\s*(\d{1,2})\b.*$', re.I | re.M)
DUR_RE = re.compile(r'(?:(\d+)\s*:\s*(\d{2})(?!\d))|(?:(\d+(?:\.\d+)?)\s*(?:min(?:ute)?s?|m)\b(?:\s*(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)\b)?)|(?:(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)\b)', re.I)
PAUSE_RE = re.compile(r'\[[^\]]*pause[^\]]*?(\d+(?:\.\d+)?)\s*(s|sec|secs|seconds|second)\b[^\]]*\]', re.I)
META_LINE = re.compile(r'^\s*[-*_>]*\s*\**\s*(duration|timing|time|estimated|est\.?|target|length|speaking time|word count|words)\b[^\n]*$', re.I | re.M)


def _dur(m):
    if m.group(1):
        return int(m.group(1)) * 60 + int(m.group(2))
    if m.group(3):
        return float(m.group(3)) * 60 + (float(m.group(4)) if m.group(4) else 0)
    return float(m.group(5))


def parse_script(text):
    """-> {slide_no: dict(text, words, pauses_s, declared_s or None)} ; empty dict if no slide headings found."""
    hs = list(SLIDE_HDR.finditer(text))
    out = {}
    for k, h in enumerate(hs):
        n = int(h.group(1))
        body = text[h.end(): hs[k + 1].start() if k + 1 < len(hs) else len(text)]
        hdr = h.group(0)
        declared = None
        m = DUR_RE.search(hdr)
        if m:
            declared = _dur(m)
        else:
            for ml in META_LINE.finditer(body):
                mm = DUR_RE.search(ml.group(0))
                if mm and not re.search(r'\bwords?\b\s*[:=]', ml.group(0), re.I):
                    declared = _dur(mm)
                    break
        pauses = sum(float(p.group(1)) for p in PAUSE_RE.finditer(body))
        spoken = clean_spoken(body)
        if n in out:  # duplicated heading -> merge
            out[n]['text'] += '\n' + spoken
            continue
        out[n] = {'text': spoken, 'pauses_s': pauses, 'declared_s': declared}
    for v in out.values():
        v['words'] = len(WORD_RE.findall(v['text']))
    return out


def clean_spoken(t):
    t = META_LINE.sub(' ', t)
    t = re.sub(r'\[[^\]]*\]', ' ', t)          # [CLICK], [pause 2 s], [trigger: ...]
    t = re.sub(r'\{[^}]*\}', ' ', t)
    t = re.sub(r'<[^>]*>', ' ', t)
    t = re.sub(r'^\s*(#+|\|.*\||[-*]{3,}).*$', ' ', t, flags=re.M)
    t = re.sub(r'[*_`>]', ' ', t)
    return t


def tokens(t):
    return [w.lower().strip('.,:') for w in WORD_RE.findall(clean_spoken(t))]


def overlap(a, b):
    from collections import Counter
    ca, cb = Counter(tokens(a)), Counter(tokens(b))
    if not ca and not cb:
        return 1.0
    inter = sum((ca & cb).values())
    return inter / max(sum(ca.values()), sum(cb.values()), 1)


# ---------------- csv ----------------
def read_csv(p):
    raw = p.read_bytes().decode('utf-8-sig', errors='replace')
    try:
        dialect = csv.Sniffer().sniff(raw[:4000], delimiters=',;\t')
    except Exception:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(raw), dialect))
    rows = [r for r in rows if any(c.strip() for c in r)]
    return (rows[0], rows[1:]) if rows else ([], [])


def find_col(header, *alts):
    h = [x.strip().lower() for x in header]
    for alt in alts:
        for j, x in enumerate(h):
            if all(k in x for k in alt):
                return j
    return None


# ---------------- misc ----------------
def pdf_pages_text(p):
    try:
        o = subprocess.run(['pdftotext', '-layout', str(p), '-'], capture_output=True, text=True, timeout=180).stdout
        pages = o.split('\f')
        if pages and not pages[-1].strip():
            pages = pages[:-1]
        return pages
    except Exception:
        return None


def pdf_page_count(p):
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(p)).pages)
    except Exception:
        o = subprocess.run(['pdfinfo', str(p)], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r'Pages:\s+(\d+)', o)
        return int(m.group(1)) if m else None


def media_duration(deck, part, tmp):
    try:
        f = tmp / ('m_' + part.replace('/', '_'))
        f.write_bytes(deck.z.read(part))
        o = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(f)],
                           capture_output=True, text=True, timeout=60).stdout
        return float(json.loads(o)['format']['duration'])
    except Exception:
        return None


def boxes_overlap(a, b):
    if not a or not b:
        return False
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def norm_words(t):
    return set(w.lower() for w in re.findall(r'[A-Za-z0-9]{3,}', t or ''))
