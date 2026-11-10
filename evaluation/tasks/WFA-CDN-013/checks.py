# -*- coding: utf-8 -*-
"""CDC-D-X07 确定性检查。见 REVIEW/VERIFIER_NOTES.md。
机测：B01(结构代理) B02 B03 B04 B05 B06 B09 B11 M01 M02(仅否决) M03 M05 M06 M07(仅否决) M10 M15(仅否决)。
v2026-10-25：B05 仅要求承载事实的页；B09 解析继承字号、整页要点数；M03 图表数据对表 11；M05 模板匹配报告页；
M06 点击步骤须对应表 30 上午 burnover 且按时间顺序；M10 抽 10 行核页码与页面文字；M15 越界预筛。
postprocess：任务级门槛（6 件交付缺失或 pptx 不可解析 → 全部判否）；G2 组门槛（B01 否 → G2 全否）。"""
import re, subprocess, traceback, zipfile
import xml.etree.ElementTree as ET
import dlib as L

DELIV = ['presentation.pptx', 'slides.pdf', 'script.md', 'calculations.xlsx', 'evidence-index.csv', 'playback-check.md']
N_SLIDES = 12


def _safe(res, iid, fn):
    try:
        v = fn()
        if v is not None:
            res[iid] = v
    except Exception as e:
        res[iid] = L.F('check error: %s' % traceback.format_exc()[-300:])


def run(ctx):
    out = ctx['out']
    res = {}
    pptx = out / 'presentation.pptx'
    st = {}

    def b01():
        if not pptx.exists():
            return L.F('presentation.pptx missing')
        ok, probs, info = L.pptx_integrity(str(pptx))
        st['integrity'] = ok
        if not ok:
            return L.F('package problems (PowerPoint would likely repair/refuse): %s' % probs)
        if info.get('external_links'):
            st['integrity'] = False
            return L.F('external (linked) parts break offline copy: %s' % info['external_links'][:3])
        return L.P('structural proxy only (Linux; no PowerPoint): zip/content-types/relationships/xml well-formed, python-pptx opens, no external links')
    _safe(res, 'B01', b01)

    prs = titles = notes = None
    z = None
    try:
        if pptx.exists():
            prs, titles, notes = L.deck_titles_notes(pptx)
            z = zipfile.ZipFile(str(pptx))
    except Exception as e:
        st['parse_err'] = str(e)
    st['parsed'] = prs is not None

    def b02():
        if prs is None:
            return L.F('pptx missing or unparseable')
        n = len(prs.slides)
        r = prs.slide_width / prs.slide_height
        ok = n == N_SLIDES and abs(r / (16 / 9) - 1) <= 0.01
        return L.V(ok, 'slides=%d ratio=%.4f' % (n, r))
    _safe(res, 'B02', b02)

    def b03():
        pdf = out / 'slides.pdf'
        if not pdf.exists():
            return L.F('slides.pdf missing')
        pages = L.pdf_page_texts(pdf)
        if len(pages) != N_SLIDES:
            return L.F('slides.pdf has %d pages' % len(pages))
        if titles is None:
            return L.F('pptx unparseable; cannot match titles')
        if len(titles) != len(pages):
            return L.F('pptx %d slides vs pdf %d pages' % (len(titles), len(pages)))
        bad = [i + 1 for i, (t, p) in enumerate(zip(titles, pages)) if not L.title_in_page(t, p)]
        return L.V(not bad, 'pages=12; title mismatch on slides %s' % bad if bad else 'pages=12; all titles found in order')
    _safe(res, 'B03', b03)

    def b04():
        sp = out / 'script.md'
        if not sp.exists():
            return L.F('script.md missing')
        txt = sp.read_text(encoding='utf-8', errors='replace')
        secs = L.split_script(txt)
        if notes is not None:
            empty = [i + 1 for i, n in enumerate(notes) if len(n.split()) < 5]
            if len(empty) >= 2:
                return L.F('speaker notes empty/near-empty on slides %s' % empty)
        if not re.search(r'click', txt, re.I):
            return L.F('no click events marked in script.md')
        if len(secs) < N_SLIDES or notes is None:
            return None  # 格式无法稳妥解析 → 交模型
        sims = []
        for i in range(1, N_SLIDES + 1):
            sims.append(L.jaccard(L.strip_script_markup(secs.get(i, '')), notes[i - 1] if i - 1 < len(notes) else ''))
        good = sum(1 for s in sims if s >= 0.8)
        durs = [L.section_duration(secs[i]) for i in range(1, N_SLIDES + 1)]
        if good < 11:
            return L.F('notes vs script token Jaccard >=0.8 on only %d/12 slides (%s)' % (good, [round(s, 2) for s in sims]))
        if any(d is None for d in durs):
            return None
        tot = sum(durs) / 60
        return L.V(12 <= tot <= 15, 'notes match %d/12; per-slide durations sum %.2f min' % (good, tot))
    _safe(res, 'B04', b04)

    def b05():
        p = out / 'evidence-index.csv'
        if not p.exists():
            return L.F('evidence-index.csv missing')
        rows = L.read_csv(p)
        if not rows:
            return L.F('empty csv')
        h = rows[0]
        need = {'slide': [r'slide'], 'element': [r'element'], 'claim': [r'claim'], 'report': [r'report|source|document'],
                'printed page': [r'print'], 'pdf page': [r'pdf'], 'table/figure': [r'table|figure|fig'],
                'transformation': [r'transform']}
        cols = {k: L.find_col(h, v) for k, v in need.items()}
        miss = [k for k, v in cols.items() if v is None]
        st['ev_rows'] = rows
        st['ev_cols'] = cols
        if miss:
            return L.F('missing columns %s in header %s' % (miss, h))
        cov = set()
        for r in rows[1:]:
            if cols['slide'] < len(r):
                cov |= L.slide_nums(r[cols['slide']])
        # v2026-10-25: only fact-bearing slides need a row (digit in slide text/notes, or a chart/table/picture)
        fact = []
        if prs is not None:
            for i, s in enumerate(prs.slides, 1):
                txt = ' '.join(sh.text_frame.text for sh in L._iter_shapes(s.shapes) if getattr(sh, 'has_text_frame', False) and sh.has_text_frame)
                nt = notes[i - 1] if notes is not None and i - 1 < len(notes) else ''
                objs = any(getattr(sh, 'has_chart', False) or getattr(sh, 'has_table', False) or 'PICTURE' in str(sh.shape_type)
                           for sh in L._iter_shapes(s.shapes))
                if objs or re.search(r'\d', re.sub(r'\bslides?\s*\d+', ' ', txt + ' ' + nt, flags=re.I)):
                    fact.append(i)
        else:
            fact = list(range(1, N_SLIDES + 1))
        lack = [i for i in fact if i not in cov]
        return L.V(not lack, '8 columns present; fact-bearing slides without rows: %s' % lack if lack
                   else '8 columns; every fact-bearing slide (%d) has >=1 row' % len(fact))
    _safe(res, 'B05', b05)

    def b06():
        p = out / 'calculations.xlsx'
        if not p.exists():
            return L.F('calculations.xlsx missing')
        x = L.xlsx_scan(p.read_bytes())
        if x['formulas'] == 0:
            return L.F('no formula cells (pasted values only)')
        s = ' '.join(x['strings']).lower()
        lack = [k for k, pat in (('unit', r'unit'), ('page', r'page|\bp\.'), ('report', r'report|tn ?2252|tn ?2135|source'))
                if not re.search(pat, s)]
        if lack:
            return L.F('%d formulas but no %s labels found' % (x['formulas'], lack))
        return L.P('%d live formula cells; unit/page/report labels present (heuristic, completeness of "every derived quantity" not verified)' % x['formulas'])
    _safe(res, 'B06', b06)

    def b09():
        if prs is None:
            return L.F('pptx unparseable')
        # v2026-10-25: inherited sizes resolved (layout/master/defaultTextStyle, normAutofit); bullets summed per slide
        ok, det = L.font_rule_check(prs, 20.0, 12.0, 6)
        return L.V(ok, det)
    _safe(res, 'B09', b09)

    def b11():
        rows = st.get('ev_rows')
        cols = st.get('ev_cols')
        if rows is None:
            p = out / 'evidence-index.csv'
            if not p.exists():
                return L.F('evidence-index.csv missing')
            rows = L.read_csv(p)
            cols = {'report': L.find_col(rows[0], [r'report|source|document'])}
        rc = cols.get('report')
        if rc is None:
            return L.F('no report column')
        a = b = 0
        for r in rows[1:]:
            c = (r[rc] if rc < len(r) else '').lower()
            if re.search(r'2252|main|nettra|notification|evacuation', c):
                a += 1
            if re.search(r'2135|companion|progression|timeline', c):
                b += 1
        return L.V(a >= 5 and b >= 5, 'rows citing TN 2252/main=%d, TN 2135/companion=%d' % (a, b))
    _safe(res, 'B11', b11)

    # ---------- native objects ----------
    def m01():
        if z is None:
            return L.F('pptx missing/unparseable')
        ok_n, det = 0, []
        for i, spart in enumerate(L.slide_parts(z), 1):
            for c in L.chart_parts_for_slide(z, spart):
                emb, ext = L.chart_embedded(z, c)
                if emb and emb.lower().endswith(('.xlsx', '.xlsm')):
                    ok_n += 1
                    st.setdefault('emb', []).append(emb)
                else:
                    det.append('slide %d %s: %s' % (i, c, 'external link' if ext else 'no embedded workbook'))
        return L.V(ok_n >= 3, '%d native charts with embedded workbook; issues: %s' % (ok_n, det[:4]))
    _safe(res, 'M01', m01)

    def m02():
        embs = st.get('emb') or []
        if not embs:
            return L.F('no embedded chart workbooks')
        bad = []
        for e in embs:
            try:
                x = L.xlsx_scan(z.read(e))
            except Exception as ex:
                bad.append('%s unreadable' % e)
                continue
            s = ' '.join(x['strings']).lower()
            if not re.search(r'page|\bp\.', s) or not re.search(r'report|tn ?2252|tn ?2135|source', s):
                bad.append('%s lacks page/report labels' % e.rsplit('/', 1)[-1])
        if bad:
            return L.F('; '.join(bad[:4]))
        return None  # 单位/公式覆盖交模型
    _safe(res, 'M02', m02)

    def slide_roots():
        out_ = []
        for i, sp in enumerate(L.slide_parts(z), 1):
            out_.append((i, sp, ET.fromstring(z.read(sp))))
        return out_


    TIME = re.compile(r'\b([01]?\d|2[0-3]):([0-5]\d)\b')
    ans = ctx.get('answer') or {}
    BURN = []  # (id, road, community, cat, minutes or None (Nov 9 => None))
    for row in ans.get('burnovers_TN2252_Table30_p125-126_PDF163-164', []):
        t = None if 'Nov 9' in str(row[4]) else L.hhmm(str(row[4]))
        BURN.append((int(row[0]), str(row[1]), str(row[2]), row[3], t))

    def _road_keys(road):
        # 'Clark Rd / American Way' -> ['american way']; 'Skyway (upper)' -> ['skyway'] ...
        parts = [re.sub(r'\b(rd|road|ln|lane|way|cir|circle)\b\.?', '', x.lower()).strip(' .()')
                 for x in re.split(r'/', re.sub(r'\(.*?\)', '', road))]
        return [x for x in parts if len(x) >= 4]

    def burn_ids(text):
        """Burnover ids identified by a label: '#N' (or 'burnover N'), else unique road-name match."""
        t = text.lower()
        ids = {int(x) for x in re.findall(r'(?:#|no\.?\s*|burnover\s+)(\d{1,2})\b', t)}
        ids = {i for i in ids if any(b[0] == i for b in BURN)}
        if ids:
            return ids
        hit = set()
        for bid, road, *_ in BURN:
            keys = _road_keys(road)
            if keys and all(k in t for k in keys):
                hit.add(bid)
        return hit

    def m06():
        if z is None:
            return L.F('pptx missing/unparseable')
        best = None
        for i, sp, root in slide_roots():
            has_pic = any(True for _ in root.iter('{%s}pic' % L.NS['p']))
            ti = L.timing_info(root)
            texts = L.shape_texts(root)
            seq = []
            seen = set()
            for c in ti['main_clicks']:
                if c['cls'] != 'entr':
                    continue
                tg = [s for s in c['spids'] if s and s not in seen]
                if tg:
                    seen.update(tg)
                    seq.append(tg)
            if has_pic and len(seq) >= 4 and (best is None or len(seq) > best[1]):
                best = (i, len(seq), seq, texts)
        if best is None:
            return L.F('no map slide (with picture) has >=4 on-click entrance effects on distinct shapes')
        i, n, seq, texts = best
        # v2026-10-25: every revealed step must identify a Nov-8-morning burnover (Table 30 '#N' or road) and the
        # steps must be in chronological order (label time if given, else Table 30 time)
        steps, unmapped = [], []
        for k, tg in enumerate(seq, 1):
            tt = ' '.join(texts.get(s, ('', '', ''))[1] for s in tg)
            ids = burn_ids(tt)
            morning = [b for b in BURN if b[0] in ids and b[4] is not None and b[4] <= 12 * 60]
            if not morning:
                unmapped.append((k, tt[:40]))
                continue
            lt = L.hhmm(tt)
            key_t = min(b[4] for b in morning)
            steps.append((k, sorted(b[0] for b in morning), lt if lt is not None else key_t))
        if len(steps) < 4:
            return L.F('slide %d: only %d of %d click steps identify a Nov-8-morning Table 30 burnover (ID or road); unmapped %s'
                       % (i, len(steps), n, unmapped[:4]))
        tv = [t for _, _, t in steps]
        ok = all(a <= b for a, b in zip(tv, tv[1:]))
        return L.V(ok, 'slide %d: %d click steps map to morning burnovers %s at %s%s' % (
            i, len(steps), [x[1] for x in steps], ['%02d:%02d' % divmod(t, 60) for t in tv],
            '' if ok else ' (not chronological)'))
    _safe(res, 'M06', m06)

    def m07():
        if z is None:
            return L.F('pptx missing/unparseable')
        for i, sp, root in slide_roots():
            txt = ' '.join(t.text or '' for t in root.iter('{%s}t' % L.NS['a'])).lower()
            nsp = sum(1 for _ in root.iter('{%s}sp' % L.NS['p']))
            if nsp >= 6 and re.search(r'observ', txt) and re.search(r'infer', txt) and re.search(r'unsupport|not support|counterfactual', txt):
                return None  # 有候选原生形状图 → 内容交模型
        return L.F('no slide with >=6 native shapes containing observed/inference/unsupported categories')
    _safe(res, 'M07', m07)

    # ---------- v2026-10-25 additions ----------
    T11 = ans.get('table11_TN2252_p56_PDF94_subset') or {}

    def zone_key(name):
        n = (name or '').lower().strip()
        for k, pat in (('Pulga', r'pulga'), ('Concow', r'concow'), ('Lower Pentz', r'(?:lower|l\.?)\s*pentz'),
                       ('Lower Clark', r'(?:lower|l\.?)\s*clark'), ('Old Magalia', r'old\s*magalia')):
            if re.search(pat, n):
                return k
        m = re.search(r'(?:zone|zn|z|paradise|par\.?)\s*#?\s*(\d{1,2})\b', n) or re.fullmatch(r'\s*(\d{1,2})\s*', n)
        if m:
            k = 'Paradise %d' % int(m.group(1))
            return k
        return None

    def zone_candidates(k):
        row = T11.get(k)
        if not row:
            return None
        ff = L.hhmm(str(row[0]))
        times = []
        for x in row[1:]:
            times += L.all_hhmm(str(x)) if x else []
        c = set()
        if ff is not None:
            c.add(ff)
            for t in times:
                c.add(ff - t)
                c.add(t - ff)
        c.update(times)
        return c

    def val_ok(v, cands):
        reps = [v, v * 60.0, v * 1440.0]  # minutes / hours / Excel day fraction
        return any(abs(r - c) <= 1.01 for r in reps for c in cands)

    def deck_charts():
        out_ = []
        for i, s in enumerate(prs.slides, 1):
            for sh in L._iter_shapes(s.shapes):
                if getattr(sh, 'has_chart', False) and sh.has_chart:
                    out_.append((i, s, sh.chart))
        return out_

    def m03():
        if prs is None:
            return L.F('pptx unparseable')
        best = None
        for i, s, ch in deck_charts():
            try:
                cats = [str(c) for c in ch.plots[0].categories]
            except Exception:
                cats = []
            series = []
            for pl in ch.plots:
                for se in pl.series:
                    try:
                        series.append((se.name or '', list(se.values)))
                    except Exception:
                        pass
            per = {}  # zone -> list of values
            if sum(1 for c in cats if zone_key(c) in T11) >= 4:
                for j, c in enumerate(cats):
                    k = zone_key(c)
                    if k in T11:
                        per.setdefault(k, []).extend(v[j] for _, v in series if j < len(v) and v[j] is not None)
            elif sum(1 for nm, _ in series if zone_key(nm) in T11) >= 4:
                for nm, v in series:
                    k = zone_key(nm)
                    if k in T11:
                        per.setdefault(k, []).extend(x for x in v if x is not None)
            if not per:
                continue
            good = [k for k, vs in per.items() if vs and all(val_ok(float(x), zone_candidates(k)) for x in vs)]
            bad = [(k, vs[:3]) for k, vs in per.items() if vs and k not in good]
            cand = (len(good), i, s, ch, good, bad)
            if best is None or cand[0] > best[0]:
                best = cand
        if best is None:
            return L.F('no chart whose categories or series are Table 11 zones (Pulga, Concow, Zone N, Lower Pentz ...)')
        n, i, s, ch, good, bad = best
        if bad:
            return L.F('slide %d chart: values do not match Table 11 (first fire vs request/CodeRED, +-1 min) for %s' % (i, bad[:4]))
        if n < 8:
            return L.F('slide %d chart: only %d Table 11 zones checkable (need >=8): %s' % (i, n, good))
        txt = ' '.join(sh.text_frame.text for sh in L._iter_shapes(s.shapes) if getattr(sh, 'has_text_frame', False) and sh.has_text_frame)
        for part in ('chart_title', 'category_axis', 'value_axis'):
            try:
                if part == 'chart_title':
                    txt += ' ' + (ch.chart_title.text_frame.text if ch.has_title else '')
                else:
                    a = getattr(ch, part)
                    txt += ' ' + (a.axis_title.text_frame.text if a.has_title else '')
            except Exception:
                pass
        tl = txt.lower()
        basis = re.search(r'codered|\brequest', tl)
        sign = re.search(r'positive|negative|\bsign\b|minus|[<>]\s*0|ahead of|before (?:the )?fire|after (?:the )?fire|'
                         r'fire (?:arrival|data) (?:minus|−|-)|(?:minus|−|-)\s*(?:notification|request|codered)', tl)
        if not basis or not sign:
            return L.F('slide %d: chart data match %d zones, but slide does not state %s' % (
                i, n, ' and '.join(x for x, ok in (('the time basis (IC request / CodeRED)', basis), ('the sign convention', sign)) if not ok)))
        return L.P('slide %d chart: %d zones match Table 11 to +-1 min; time basis and sign convention stated' % (i, n))
    _safe(res, 'M03', m03)

    INP = ctx.get('input')
    PDFS = {'main': (INP / 'main-report.pdf') if INP else None, 'companion': (INP / 'companion-report.pdf') if INP else None}

    def rep_of(cell):
        c = (cell or '').lower()
        if re.search(r'2252|main|nettra|notification|evacuation', c):
            return 'main'
        if re.search(r'2135|companion|progression|timeline', c):
            return 'companion'
        return None

    ROMAN = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}

    def roman(sv):
        sv = sv.lower()
        if not sv or any(ch not in ROMAN for ch in sv):
            return None
        tot = 0
        for a_, b_ in zip(sv, sv[1:] + ' '):
            va, vb = ROMAN[a_], ROMAN.get(b_, 0)
            tot += -va if vb > va else va
        return tot

    def ev_rows_parsed():
        rows = st.get('ev_rows')
        cols = st.get('ev_cols') or {}
        if not rows or any(cols.get(k) is None for k in ('slide', 'claim', 'report', 'printed page', 'pdf page')):
            return None
        outr = []
        for r in rows[1:]:
            g = lambda k: (r[cols[k]] if cols.get(k) is not None and cols[k] < len(r) else '').strip()
            rep = rep_of(g('report'))
            pm = re.search(r'\d+', g('pdf page'))
            pr = re.sub(r'^(?:p\.?|page)\s*', '', g('printed page').lower()).strip()
            if not rep or not pm:
                continue
            outr.append({'slide': g('slide'), 'element': g('element') if cols.get('element') is not None else '', 'claim': g('claim'),
                         'rep': rep, 'pdf': int(pm.group()), 'printed': pr,
                         'fig': g('table/figure') if cols.get('table/figure') is not None else '',
                         'trans': g('transformation') if cols.get('transformation') is not None else ''})
        return outr

    STOP = set('about after again against along also among because before being between both could during each from have '
               'their there these those through under until which while would other than then them they this that with were '
               'where when what into only over such some more most very will shall should zone zones fire fires report'.split())

    def m10():
        rows = ev_rows_parsed()
        if rows is None:
            return L.F('evidence-index.csv missing or lacks slide/claim/report/printed page/PDF page columns')
        if len(rows) < 5:
            return L.F('only %d evidence rows with a recognisable report and PDF page' % len(rows))
        import random
        samp = sorted(random.Random(2252).sample(range(len(rows)), min(10, len(rows))))
        good, det = 0, []
        cache = {}
        for j in samp:
            r = rows[j]
            pdf = PDFS.get(r['rep'])
            if pdf is None or not pdf.exists():
                return L.F('input report %s not available to the grader' % r['rep'])
            off_ok = True
            if r['printed'].isdigit():
                off_ok = r['pdf'] == int(r['printed']) + (38 if r['rep'] == 'main' else 30)
            elif roman(r['printed']) is not None and r['rep'] == 'main':
                off_ok = r['pdf'] == roman(r['printed']) + 2
            key = (r['rep'], r['pdf'])
            if key not in cache:
                cache[key] = L.pdf_page_text(pdf, r['pdf'])
            pg = cache[key]
            pgn = re.sub(r'(?<=\d),(?=\d{3})', '', pg).lower()
            claim = re.sub(r'(?<=\d),(?=\d{3})', '', r['claim']).lower()
            nums = [x for x in re.findall(r'\d{1,2}:\d{2}|\d+(?:\.\d+)?', claim) if len(x) >= 3 and x not in ('2018',)]
            num_hit = any(re.search(r'(?<![\d.])%s(?![\d])' % re.escape(x), pgn) for x in nums)
            words = [w for w in re.findall(r'[a-z]{5,}', claim) if w not in STOP]
            wr = (sum(1 for w in set(words) if w in pgn) / len(set(words))) if len(set(words)) >= 3 else 0
            ok = off_ok and bool(pg.strip()) and (num_hit or wr >= 0.6)
            good += ok
            if not ok:
                det.append('row%d %s PDF %d printed %s: offset_ok=%s num_hit=%s words=%.2f' % (
                    j + 2, r['rep'], r['pdf'], r['printed'] or '-', off_ok, num_hit, wr))
        n = len(samp)
        need = 9 if n >= 10 else n
        return L.V(good >= need, '%d/%d sampled rows resolve (printed/PDF offset and claim found on the PDF page)%s' % (
            good, n, '; ' + '; '.join(det[:4]) if det else ''))
    _safe(res, 'M10', m10)

    def m05():
        if prs is None:
            return L.F('pptx unparseable')
        pics = []
        for i, s in enumerate(prs.slides, 1):
            for sh in L._iter_shapes(s.shapes):
                if 'PICTURE' in str(sh.shape_type):
                    try:
                        pics.append((i, s, sh, sh.image.blob))
                    except Exception:
                        pass
        if len(pics) < 3:
            return L.F('only %d picture shapes in deck (<3 map crops possible)' % len(pics))
        try:
            import cv2
            import numpy as np
        except Exception as e:
            raise RuntimeError('grader image lacks opencv/numpy: %s' % e)
        mp = ans.get('map_pages') or {}
        known = {'main': set(), 'companion': set()}
        for rk, dk in (('TN2252', 'main'), ('TN2135', 'companion')):
            for v in (mp.get(rk) or {}).values():
                m = re.search(r'PDF\s*(\d+)', str(v))
                if m:
                    known[dk].add(int(m.group(1)))
        rows = ev_rows_parsed() or []
        pages_cache = {}

        def page_img(rep, pg):
            k = (rep, pg)
            if k not in pages_cache:
                im = None
                try:
                    pref = ctx['tmp'] / ('m05_%s_%d' % (rep, pg))
                    subprocess.run(['pdftoppm', '-r', '40', '-gray', '-png', '-f', str(pg), '-l', str(pg), '-singlefile',
                                    str(PDFS[rep]), str(pref)], capture_output=True, timeout=60)
                    im = cv2.imread(str(pref) + '.png', cv2.IMREAD_GRAYSCALE)
                except Exception:
                    im = None
                pages_cache[k] = im
            return pages_cache[k]

        def match(tpl, page):
            ph, pw = page.shape[:2]
            th, tw = tpl.shape[:2]
            best = (-1, 0)
            for frac in np.linspace(0.12, 1.0, 23):
                w = int(pw * frac)
                h = int(th * w / max(1, tw))
                if w < 24 or h < 24 or h > ph or w > pw:
                    continue
                t2 = cv2.resize(tpl, (w, h), interpolation=cv2.INTER_AREA)
                if float(t2.std()) < 4:
                    continue
                r = cv2.matchTemplate(page, t2, cv2.TM_CCOEFF_NORMED)
                mv = float(r.max())
                if mv > best[0]:
                    best = (mv, (w * h) / float(pw * ph))
            return best

        found, det = [], []
        for i, s, sh, blob in pics:
            tpl = cv2.imdecode(np.frombuffer(blob, np.uint8), cv2.IMREAD_GRAYSCALE)
            if tpl is None:
                det.append('slide %d %s: undecodable image' % (i, sh.name))
                continue
            cand = []
            for r in rows:
                if i in L.slide_nums(r['slide']):
                    cand += [(r['rep'], r['pdf'] + d) for d in (0, -1, 1)]
            cand += [(rep, pg) for rep, pgs in known.items() for pg in sorted(pgs)]
            hit = None
            for rep, pg in dict.fromkeys(cand):
                if not PDFS.get(rep) or not PDFS[rep].exists():
                    continue
                page = page_img(rep, pg)
                if page is None:
                    continue
                score, area = match(tpl, page)
                if score >= 0.6:
                    hit = (rep, pg, round(score, 2), area)
                    break
            if hit is None:
                det.append('slide %d %s: no match on cited/known map pages' % (i, sh.name))
                continue
            if hit[3] >= 0.85:
                det.append('slide %d %s: full-page image (%s PDF %d), not a crop' % (i, sh.name, hit[0], hit[1]))
                continue
            # native annotation shapes placed on the picture
            pl, pt, pw_, ph_ = sh.left or 0, sh.top or 0, sh.width or 0, sh.height or 0
            ann = 0
            for o in L._iter_shapes(s.shapes):
                if o is sh or 'PICTURE' in str(o.shape_type):
                    continue
                try:
                    if None in (o.left, o.top, o.width, o.height):
                        continue
                    if o.left < pl + pw_ and o.left + o.width > pl and o.top < pt + ph_ and o.top + o.height > pt \
                            and (o.width < pw_ or o.height < ph_):
                        ann += 1
                except Exception:
                    pass
            if ann == 0:
                det.append('slide %d %s: matches %s PDF %d but has no native annotation on it' % (i, sh.name, hit[0], hit[1]))
                continue
            found.append((i, hit[0], hit[1], hit[2], ann))
        reps = {f[1] for f in found}
        ok = len(found) >= 3 and reps >= {'main', 'companion'}
        return L.V(ok, 'annotated report-map crops: %s%s' % (
            [('slide %d' % f[0], f[1], 'PDF %d' % f[2], 'ncc %.2f' % f[3], '%d annot.' % f[4]) for f in found],
            '; issues: ' + '; '.join(det[:4]) if det else ''))
    _safe(res, 'M05', m05)

    def m15():
        if prs is None:
            return L.F('pptx unparseable')
        bad = L.shapes_outside_slide(prs)
        if bad:
            return L.F('shapes extend beyond the slide: %s' % bad[:6])
        return None  # visual overflow / occlusion by revealed shapes -> judge on rendered pages
    _safe(res, 'M15', m15)

    st_missing = [d for d in DELIV if not (out / d).exists()]
    ctx['_x07_gate'] = {'missing': st_missing, 'parsed': st.get('parsed')}
    if st_missing or not st.get('parsed'):
        # 任务级门槛：直接全部判否，避免无谓调用评审模型
        why = 'task gate: missing %s / pptx parsed=%s' % (st_missing, st.get('parsed'))
        for it in ctx['items']:
            res[it['id']] = dict(res.get(it['id'], {}), verdict='fail', detail=why, gated=True)
    return res


def postprocess(results, ctx):
    g = ctx.get('_x07_gate') or {}
    items = ctx['items']
    if g.get('missing') or not g.get('parsed'):
        why = 'task gate: missing %s / pptx parsed=%s' % (g.get('missing'), g.get('parsed'))
        for it in items:
            r = results.get(it['id'], {})
            results[it['id']] = dict(r, verdict='fail', detail=why, gated=True)
        return results
    if results.get('B01', {}).get('verdict') != 'pass':
        for it in items:
            if it.get('group') == 'G2' and it['id'] != 'B01':
                r = results.get(it['id'], {})
                if r.get('verdict') != 'fail':
                    results[it['id']] = dict(r, verdict='fail', detail='G2 gate: B01 failed', gated=True)
    return results
