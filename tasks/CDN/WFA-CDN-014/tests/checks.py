# -*- coding: utf-8 -*-
"""CDC-D-X08 确定性检查。见 REVIEW/VERIFIER_NOTES.md。
机测（pass/fail）：N05 V01 V02 V03 V04 V07 D01 D02 D04 D05 D06 D07 D08 D09 D10 D12 D15 R03 R04
仅否决（满足时交模型）：N01 V06 D03 D11；postprocess 可判否 D14（playback-check 声称验证但机测失败）
v2026-10-25：见 review/rubric-cleanup-20261025.md。
门槛：GATE0（7 件交付齐全且 pptx 可解析，否则全部判否）；GATE1 结构代理（包结构异常 → G6 全否 + V07 否）。"""
import re, subprocess, traceback, zipfile
import xml.etree.ElementTree as ET
import dlib as L

DELIV = ['presentation.pptx', 'slides.pdf', 'script.md', 'calculations.xlsx', 'event-clip.mp4', 'evidence-index.csv', 'playback-check.md']
DATE = re.compile(r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{1,2}\b|\b\d{1,2}/\d{1,2}\b|\b\d{4}-\d{2}-\d{2}\b', re.I)


def _safe(res, iid, fn):
    try:
        v = fn()
        if v is not None:
            res[iid] = v
    except Exception:
        res[iid] = L.F('check error: %s' % traceback.format_exc()[-300:])


def _near(vals, target, tol):
    return any(abs(v - target) <= tol for v in vals)


def run(ctx):
    out = ctx['out']
    res = {}
    st = {}
    pptx = out / 'presentation.pptx'
    prs = titles = notes = z = None
    try:
        if pptx.exists():
            prs, titles, notes = L.deck_titles_notes(pptx)
            z = zipfile.ZipFile(str(pptx))
    except Exception as e:
        st['parse_err'] = str(e)
    missing = [d for d in DELIV if not (out / d).exists()]
    if missing or prs is None:
        why = 'GATE0: missing %s / pptx parsed=%s' % (missing, prs is not None)
        ctx['_x08_gate0'] = why
        return {it['id']: L.F(why) for it in ctx['items']}

    ok, probs, info = L.pptx_integrity(str(pptx))
    ext = info.get('external_links') or []
    st['gate1'] = ok
    ctx['_x08_gate1'] = (ok, probs)
    nsl = len(prs.slides)
    roots = [(i, sp, ET.fromstring(z.read(sp))) for i, sp in enumerate(L.slide_parts(z), 1)]

    # ---------- G1 ----------
    def n01():
        r = prs.slide_width / prs.slide_height
        if not (9 <= nsl <= 11) or abs(r / (16 / 9) - 1) > 0.01:
            return L.F('slides=%d ratio=%.4f' % (nsl, r))
        return None
    _safe(res, 'N01', n01)

    script = (out / 'script.md').read_text(encoding='utf-8', errors='replace')
    secs = L.split_script(script)

    clip_s = 0.0
    try:
        _j = L.ffprobe(out / 'event-clip.mp4')
        clip_s = float(_j.get('format', {}).get('duration') or 0)
    except Exception:
        clip_s = 0.0

    def n05():
        empty = [i + 1 for i, n in enumerate(notes) if len(n.split()) < 5]
        if empty:
            return L.F('speaker notes empty on slides %s' % empty)
        if len(secs) < nsl or any(i not in secs for i in range(1, nsl + 1)):
            return L.F('script.md: could not find a "Slide N" section for each of the %d slides (found %s)' % (nsl, sorted(secs)))
        sims = [L.jaccard(L.strip_script_markup(secs.get(i, '')), notes[i - 1]) for i in range(1, nsl + 1)]
        bad = [i + 1 for i, s_ in enumerate(sims) if s_ < 0.9]
        if bad:
            return L.F('notes vs script token overlap <0.9 on slides %s (%s)' % (bad, [round(s_, 2) for s_ in sims]))
        # v2026-10-25: both bounds + declared pauses + clip; per-slide declared durations must agree (+-10%)
        words = sum(len(re.findall(r"[A-Za-z0-9][\w'.-]*", L.strip_script_markup(secs[i]))) for i in range(1, nsl + 1))
        pauses = sum(float(x) for x in re.findall(r'pause[^\n\]\)]{0,20}?(\d+(?:\.\d+)?)\s*(?:s\b|sec)', script, re.I))
        extra = (clip_s + pauses) / 60.0
        lo, hi = words / 150.0 + extra, words / 130.0 + extra
        if hi < 11.0 or lo > 13.0:
            return L.F('%d spoken words + %.1f s clip + %.1f s pauses -> %.2f-%.2f min at 150-130 wpm (need overlap with 11-13)'
                       % (words, clip_s, pauses, lo, hi))
        durs = [L.section_duration(secs[i]) for i in range(1, nsl + 1)]
        if any(d is None for d in durs):
            return L.F('no per-slide duration found for slides %s' % [i + 1 for i, d in enumerate(durs) if d is None])
        tot = sum(durs) / 60.0
        if not (0.9 * lo <= tot <= 1.1 * hi):
            return L.F('declared per-slide durations sum %.2f min vs computed %.2f-%.2f min (+-10%%)' % (tot, lo, hi))
        return L.P('%d words, clip %.1f s, pauses %.1f s -> %.2f-%.2f min; declared sum %.2f min; notes = script' % (words, clip_s, pauses, lo, hi, tot))
    _safe(res, 'N05', n05)

    # ---------- G2 ----------
    small, bul = L.font_bullet_scan(prs)

    # v2026-10-25: inherited sizes resolved (layout/master/defaultTextStyle, normAutofit fontScale)
    sizes = L.text_size_scan(prs)

    def v01():
        bad = [(i, round(r['min_pt'], 1), r['text'][:30]) for i, rows in sizes for r in rows
               if r['role'] == 'body' and r['min_pt'] is not None and r['min_pt'] < 19.75]
        return L.V(not bad, 'body text <20 pt: %s' % bad[:5] if bad else 'all body text >=20 pt (resolved sizes incl. autofit)')
    _safe(res, 'V01', v01)

    def v02():
        bad = [(i, round(r['min_pt'], 1), r['text'][:30]) for i, rows in sizes for r in rows
               if r['min_pt'] is not None and r['min_pt'] < 11.75]
        return L.V(not bad, 'text <12 pt: %s' % bad[:5] if bad else 'all caption/source/label text >=12 pt (resolved sizes)')
    _safe(res, 'V02', v02)

    def v03():
        over = [(i, n) for i, n in bul if n > 6]
        return L.V(not over, 'bullet paragraphs per slide (all non-title text frames): %s' % ([n for _, n in bul]))
    _safe(res, 'V03', v03)

    chart_parts = []
    for i, sp, root in roots:
        for c in L.chart_parts_for_slide(z, sp):
            chart_parts.append((i, c))

    UNIT = re.compile(r'kips?|ratio|d/c|\bin\.?(?:²|2)?\b|in²|\bft\b|\bs\b|sec|seconds|%|percent|\btons?\b|\blb|psi|count|number|'
                      r'people|persons|vehicles|minutes?|\bmin\b|hours?|\bdays?\b|date', re.I)

    def v04():
        if not chart_parts:
            return L.F('no native charts')
        A = L.NS['a']
        C = L.NS['c']
        probs_ = []

        def eff_sz(el, base):
            szs = [int(r.get('sz')) for r in el.iter('{%s}defRPr' % A) if r.get('sz')] if el is not None else []
            return min(szs) / 100.0 if szs else base

        for i, c in chart_parts:
            root = ET.fromstring(z.read(c))
            pa = root.find('.//c:plotArea', L.NS)
            if pa is None:
                probs_.append('slide %d no plotArea' % i)
                continue
            # chart-level default text size (c:chartSpace/c:txPr); PowerPoint renders 10 pt when nothing is set
            cs_tx = root.find('c:txPr', L.NS)
            base = eff_sz(cs_tx, 10.0)
            for ax in [ax for ax in pa if ax.tag.rsplit('}', 1)[-1] in ('valAx', 'catAx', 'dateAx')]:
                d = ax.find('c:delete', L.NS)
                if d is not None and d.get('val') in ('1', 'true'):
                    continue
                tag = ax.tag.rsplit('}', 1)[-1]
                t = ax.find('c:title', L.NS)
                ttxt = ' '.join(x.text or '' for x in t.iter('{%s}t' % A)) if t is not None else ''
                if t is None or not ttxt.strip():
                    probs_.append('slide %d %s without title text' % (i, tag))
                elif tag == 'valAx' and not UNIT.search(ttxt):
                    probs_.append('slide %d value-axis title %r has no unit' % (i, ttxt[:30]))
                tick = eff_sz(ax.find('c:txPr', L.NS), base)
                if tick < 12:
                    probs_.append('slide %d %s tick labels %.1f pt' % (i, tag, tick))
            nser = len(list(pa.iter('{%s}ser' % C)))
            if nser > 1 and root.find('.//c:legend', L.NS) is None:
                probs_.append('slide %d %d series without legend' % (i, nser))
            for dl in pa.iter('{%s}dLbls' % C):
                shown = any(x.get('val') in ('1', 'true') for x in dl if x.tag.rsplit('}', 1)[-1] in ('showVal', 'showCatName', 'showSerName', 'showPercent'))
                if shown and eff_sz(dl.find('c:txPr', L.NS), base) < 12:
                    probs_.append('slide %d data labels %.1f pt' % (i, eff_sz(dl.find('c:txPr', L.NS), base)))
        if probs_:
            return L.F('; '.join(probs_[:5]))
        return L.P('%d charts: titled axes (value axes with units), legends for multi-series, tick/data labels >=12 pt (explicit or chart default; 10 pt assumed when unset)' % len(chart_parts))
    _safe(res, 'V04', v04)

    # ---------- G6 ----------
    def d01():
        pages = L.pdf_page_texts(out / 'slides.pdf')
        if len(pages) != nsl:
            return L.F('slides.pdf %d pages vs pptx %d slides' % (len(pages), nsl))
        bad = [i + 1 for i, (t, p) in enumerate(zip(titles, pages)) if not L.title_in_page(t, p)]
        return L.V(not bad, 'title mismatch on slides %s' % bad if bad else 'page count equal; all titles found in order')
    _safe(res, 'D01', d01)

    def d02():
        rows = L.read_csv(out / 'evidence-index.csv')
        if not rows:
            return L.F('empty csv')
        h = rows[0]
        need = {'slide': [r'slide'], 'element': [r'element'], 'claim': [r'claim'], 'printed page': [r'print'],
                'pdf page': [r'pdf'], 'figure/table/section': [r'fig|table|section'], 'transformation': [r'transform']}
        cols = {k: L.find_col(h, v) for k, v in need.items()}
        miss = [k for k, v in cols.items() if v is None]
        if miss:
            return L.F('missing columns %s in header %s' % (miss, h))
        cov = set()
        for r in rows[1:]:
            if cols['slide'] < len(r):
                cov |= L.slide_nums(r[cols['slide']])
        lack = [i for i in range(1, nsl + 1) if i not in cov]
        return L.V(not lack, 'slides without rows: %s' % lack if lack else 'all columns; every slide has >=1 row')
    _safe(res, 'D02', d02)

    def d03():
        empty = [i + 1 for i, n in enumerate(notes) if not n.strip()]
        if empty:
            return L.F('empty speaker notes on slides %s' % empty)
        alltxt = ' '.join(t.text or '' for _, _, r in roots for t in r.iter('{%s}t' % L.NS['a'])) + ' ' + ' '.join(notes)
        if not re.search(r'\bAI\b|artificial intelligence|generative|language model|Claude|GPT', alltxt):
            return L.F('no AI-assistance disclosure in slides or notes')
        if not re.search(r'NTSB|National Transportation Safety Board|HAR-19', alltxt):
            return L.F('source (NTSB report) not credited in slides/notes')
        return None  # 背书暗示交模型
    _safe(res, 'D03', d03)

    def d04():
        good, det = 0, []
        for i, c in chart_parts:
            emb, isext = L.chart_embedded(z, c)
            if not emb:
                det.append('slide %d: %s' % (i, 'linked workbook' if isext else 'no embedded workbook'))
                continue
            x = L.xlsx_scan(z.read(emb))
            s = ' '.join(x['strings']).lower()
            if not x['numbers'] and not x['formula_vals']:
                det.append('slide %d: workbook has no numbers' % i)
            elif not re.search(r'page|\bp\.|pdf', s):
                det.append('slide %d: workbook lacks page refs' % i)
            elif not any(re.match(r'^\s*units?\b', cell, re.I) or
                         re.match(r'^\s*\(?\s*(kips?|ratio(?:\s*\(d/c\))?|d/c|in\.?²|in2|in\.?|ft|s|sec|seconds|lb|psi|%|percent|tons?)\s*\)?\s*$', cell, re.I) or
                         re.search(r'\((kips?|in\.?²|in2|in\.?|ft|s|sec|seconds|lb|psi|%|tons?|ratio|d/c)\)', cell, re.I) or
                         re.search(r'\bratio\b|\bd/c\b', cell, re.I)  # dimensionless quantity named as such
                         for cell in x['strings']):
                det.append('slide %d: workbook has no unit column/header cell (e.g. "Unit", "kips", "Demand (kips)")' % i)
            else:
                good += 1
        return L.V(good >= 2, '%d charts with embedded workbook incl. values/units/pages; issues: %s' % (good, det[:4]))
    _safe(res, 'D04', d04)

    tinfo = [(i, root, L.timing_info(root), L.shape_texts(root)) for i, sp, root in roots]

    STAGES = [('demand', r'demand|underestimat'),
              ('capacity', r'capacity|overestimat|1\.25|\bpc\b|redundan'),
              ('interface', r'reinforc|rebar|sleeve|void|diaphragm|4\.8\s*in|bars?\b'),
              ('cracking', r'crack|distress'),
              ('detensioning', r'de-?tension'),
              ('restressing', r're-?stress|re-?tension'),
              ('failure', r'shear failure|fail|collapse|load path|fell')]

    def stage_of(text):
        t = text.lower()
        best = None
        for k, (nm, pat) in enumerate(STAGES):
            m = re.search(pat, t)
            if m and (best is None or m.start() < best[1]):
                best = (k, m.start())
        return None if best is None else best[0]

    def d07():
        best = None
        for i, root, ti, tx in tinfo:
            cx = [c for c in root.iter('{%s}cxnSp' % L.NS['p'])
                  if c.find('.//a:stCxn', L.NS) is not None or c.find('.//a:endCxn', L.NS) is not None]
            seen, steps = set(), []
            for c in ti['main_clicks']:
                if c['cls'] != 'entr':
                    continue
                tg = [s_ for s_ in c['spids'] if s_ and s_ not in seen and tx.get(s_, ('',))[0] in ('sp', 'grpSp', 'cxnSp')]
                if tg:
                    seen.update(tg)
                    txt = ' '.join(tx.get(s_, ('', '', ''))[1] for s_ in tg)
                    steps.append((tg, txt))
            if len(steps) >= 6 and cx and (best is None or len(steps) > len(best[1])):
                best = (i, steps)
        if best is None:
            return L.F('no slide with >=6 on-click entrance effects on distinct native shapes plus glued connectors (stCxn/endCxn)')
        i, steps = best
        # v2026-10-25: click order must follow the K-MECH stage order
        mapped = [(k + 1, stage_of(t)) for k, (_, t) in enumerate(steps) if t.strip()]
        mapped = [(k, st_) for k, st_ in mapped if st_ is not None]
        seq = [st_ for _, st_ in mapped]
        ordered = all(a_ <= b_ for a_, b_ in zip(seq, seq[1:]))
        names = [STAGES[x][0] for x in seq]
        if len(mapped) < 6 or len(set(seq)) < 5:
            return L.F('slide %d: only %d click steps map to mechanism stages (%d distinct; need >=6 steps, >=5 stages): %s'
                       % (i, len(mapped), len(set(seq)), names))
        return L.V(ordered, 'slide %d: %d click steps in stage order %s%s' % (i, len(mapped), names, '' if ordered else ' (out of mechanism order)'))
    _safe(res, 'D07', d07)

    def d08():
        best = (0, None, [])
        for i, root, ti, tx in tinfo:
            ok_trig = []
            for trig, effs in ti['triggers'].items():
                tgt = set()
                for e in effs:
                    if e['cls'] == 'entr':
                        tgt |= {s for s in e['spids'] if s and s != trig}
                ttxt = tx.get(trig, ('', '', ''))[1]
                if tgt and DATE.search(ttxt):
                    ok_trig.append((trig, ttxt[:30], tuple(sorted(tgt))))
            panels = {t for _, _, t in ok_trig}
            n = min(len(ok_trig), len(panels))
            if n > best[0]:
                best = (n, i, ok_trig)
        if best[0] < 5:
            return L.F('max %d dated trigger shapes revealing separate panels (need 5)%s' % (best[0], ' on slide %d' % best[1] if best[1] else ''))
        return L.P('slide %d: %d dated shapes with OnShapeClick interactive sequences revealing distinct panels' % (best[1], best[0]))
    _safe(res, 'D08', d08)

    def d09():
        found = []
        for i, root, ti, tx in tinfo:
            tm = root.find('p:timing', L.NS)
            for spid, bld in ti['bld_charts']:
                if bld not in ('series', 'category', 'seriesEl', 'categoryEl'):
                    continue
                # v2026-10-25: an effect must actually target the chart by series/category step (graphicEl/a:chart)
                eff = 0
                if tm is not None:
                    for tg in tm.iter('{%s}spTgt' % L.NS['p']):
                        if tg.get('spid') == spid and tg.find('p:graphicEl/a:chart', L.NS) is not None:
                            eff += 1
                if eff:
                    return L.P('slide %d chart spid %s build=%s with %d series/category effect targets' % (i, spid, bld, eff))
                found.append((i, spid, bld))
        if found:
            return L.F('bldChart by series/category listed %s but no timing effect targets the chart elements (graphicEl/a:chart)' % found[:3])
        return L.F('no chart animation built by series/category (bldChart): %s' % [(i, ti['bld_charts']) for i, _, ti, _ in tinfo if ti['bld_charts']][:3])
    _safe(res, 'D09', d09)

    def click_start():
        """v2026-10-25: the embedded video must be started by a click: a play/playFrom/togglePause command that targets
        the video shape inside an on-click interactive sequence, or inside a main-sequence click group that has no
        onBegin (auto) condition."""
        P_ = L.NS['p']
        vids, det, media_node = 0, [], False
        for i, root, ti, tx in tinfo:
            vsp = set()
            for pic in root.iter('{%s}pic' % P_):
                if pic.find('.//a:videoFile', L.NS) is not None or any(e.tag.endswith('}media') for e in pic.iter()):
                    nv = next((e for e in pic.iter() if e.tag.endswith('}cNvPr')), None)
                    if nv is not None:
                        vsp.add(nv.get('id'))
            if not vsp:
                continue
            vids += len(vsp)
            tm = root.find('p:timing', L.NS)
            if tm is None:
                det.append('slide %d: video without timing' % i)
                continue
            parent = {c_: p_ for p_ in tm.iter() for c_ in p_}
            for vn in tm.iter('{%s}video' % P_):
                t_ = vn.find('.//p:spTgt', L.NS)
                if t_ is not None and t_.get('spid') in vsp:
                    media_node = True
            for cmd in tm.iter('{%s}cmd' % P_):
                if not re.search(r'play|togglePause', cmd.get('cmd', '')):
                    continue
                tg = cmd.find('.//p:spTgt', L.NS)
                if tg is None or tg.get('spid') not in vsp:
                    continue
                node, chain = cmd, []
                while node in parent:
                    node = parent[node]
                    if node.tag == '{%s}cTn' % P_:
                        chain.append(node)
                kinds = [c_.get('nodeType') for c_ in chain]
                if 'interactiveSeq' in kinds:
                    return True, 'slide %d: video started by an on-click trigger' % i
                if 'mainSeq' in kinds:
                    k = kinds.index('mainSeq')
                    grp = chain[k - 1] if k >= 1 else None  # click-group cTn directly under mainSeq
                    if grp is not None:
                        conds = grp.findall('p:stCondLst/p:cond', L.NS)
                        auto = any(c_.get('evt') == 'onBegin' for c_ in conds)
                        if not auto and any(c_.get('delay') == 'indefinite' for c_ in conds):
                            return True, 'slide %d: video play command in a main-sequence click group' % i
                det.append('slide %d: play command not click-started (%s)' % (i, '/'.join(x for x in kinds if x)))
        if not vids:
            return False, 'no embedded video shape on any slide'
        if not det and media_node:
            return True, 'no auto-start command; video has a p:video media node (PowerPoint default: plays when clicked)'
        return False, 'video not started by a click: %s' % (det[:3] or 'no play command or media node targeting the video')

    def d10():
        j = L.ffprobe(out / 'event-clip.mp4')
        vs = [s for s in j.get('streams', []) if s.get('codec_type') == 'video']
        if not vs:
            return L.F('event-clip.mp4 has no video stream')
        v = vs[0]
        dur = float(j.get('format', {}).get('duration') or v.get('duration') or 0)
        wh = (v.get('width'), v.get('height'))
        p = []
        if v.get('codec_name') != 'h264':
            p.append('codec %s' % v.get('codec_name'))
        if not (4 <= dur <= 12):
            p.append('duration %.2f s' % dur)
        if wh not in ((1280, 720), (1920, 1080)):
            p.append('size %sx%s' % wh)
        media = [n for n in z.namelist() if n.startswith('ppt/media/') and re.search(r'\.(mp4|m4v|mov)$', n, re.I)]
        ext_media = [e for e in ext if re.search(r'video|media', e)]
        if ext_media:
            p.append('linked (external) media: %s' % ext_media[:2])
        if not media:
            p.append('no embedded mp4 in ppt/media')
        else:
            import tempfile, os
            same = False
            data = (out / 'event-clip.mp4').read_bytes()
            for m in media:
                b = z.read(m)
                if b == data:
                    same = True
                    break
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                    f.write(b)
                try:
                    jj = L.ffprobe(f.name)
                    if abs(float(jj.get('format', {}).get('duration') or 0) - dur) <= 0.2:
                        same = True
                finally:
                    os.unlink(f.name)
            if not same:
                p.append('embedded media differs from event-clip.mp4 (duration)')
        cs = click_start()
        if not cs[0]:
            p.append(cs[1])
        return L.V(not p, '; '.join(p) if p else 'h264 %dx%d %.2fs; embedded identical/same-duration media; %s (full playback in PowerPoint not verifiable)' % (wh[0], wh[1], dur, cs[1]))
    _safe(res, 'D10', d10)

    def d12():
        if not ok:
            return L.F('package problems: %s' % probs)
        if ext:
            return L.F('external links: %s' % ext[:3])
        return L.P('self-contained package: no external non-hyperlink relationships, all parts present (structural proxy)')
    _safe(res, 'D12', d12)

    xl = out / 'calculations.xlsx'
    xs = L.xlsx_scan(xl.read_bytes())
    vals = list(xs['formula_vals'])
    if xs['formulas']:  # real image: no LibreOffice Calc; xlsxwriter caches 0 -> evaluate simple formulas in python
        vals += L.formula_eval_values(xl)
    if xs['formulas'] and xs['formula_no_cache']:
        vals += L.soffice_recalc_values(xl, ctx['tmp'])

    def d15():
        if xs['formulas'] == 0:
            return L.F('no formula cells')
        s = ' '.join(xs['strings']).lower()
        lack = [k for k, pat in (('unit', r'unit'), ('page', r'page|\bp\.|pdf')) if not re.search(pat, s)]
        if lack:
            return L.F('%d formulas but no %s labels' % (xs['formulas'], lack))
        return L.P('%d formula cells; unit/page labels present (heuristic; references to source cells not individually verified)' % xs['formulas'])
    _safe(res, 'D15', d15)

    def r03():
        if xs['formulas'] == 0:
            return L.F('no formula cells')
        if not vals:
            return None
        a, b = _near(vals, 1.62, 0.02), _near(vals, 0.71, 0.02)
        return L.V(a and b, 'formula results contain 1.62:%s 0.71:%s' % (a, b))
    _safe(res, 'R03', r03)

    def r04():
        if xs['formulas'] == 0:
            return L.F('no formula cells')
        if not vals:
            return None
        hit = [(_near(vals, t, 0.002) or _near(vals, t * 1000, 2)) for t in (0.165, 0.264, 0.429)]
        return L.V(all(hit), 'formula results contain 0.165/0.264/0.429 s: %s' % hit)
    _safe(res, 'R04', r04)

    # ---------- v2026-10-25 additions ----------
    INP = ctx.get('input')
    REPORT = (INP / 'report.pdf') if INP else None
    keys = (ctx.get('answer') or {}).get('keys', {})

    def report_numbers():
        if 'repnums' not in st:
            txt = ''
            try:
                txt = subprocess.run(['pdftotext', '-layout', str(REPORT), '-'], capture_output=True, text=True, timeout=120).stdout
            except Exception:
                txt = ''
            nums = set()
            for m in re.finditer(r'(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.,])\d+(?:\.\d+)?', txt):
                try:
                    nums.add(float(m.group().replace(',', '')))
                except Exception:
                    pass
            for v in (keys.get('K-FIG31', {}).get('values') or {}).values():
                nums.add(float(v))
            st['repnums'] = (sorted(nums), bool(txt.strip()))
        return st['repnums']

    def num_ok(v, pool):
        import bisect
        tol = 0.006 if abs(v) < 1.2 else min(1.0, 0.005 * abs(v))
        k = bisect.bisect_left(pool, v - tol)
        return k < len(pool) and pool[k] <= v + tol

    def d05():
        pool, ok_txt = report_numbers()
        if not ok_txt:
            raise RuntimeError('grader could not extract text from input/report.pdf')
        derived = sorted(set(vals))
        allp = sorted(set(pool) | set(derived))
        T6 = set()
        for m in re.finditer(r'(\d,\d{3}|\d{3,4})', keys.get('K-DEMAND', {}).get('facts', '').split('FIGG design')[0]):
            T6.add(float(m.group().replace(',', '')))
        bad, n_ok, det = [], 0, []
        for (i, sl) in enumerate(prs.slides, 1):
            stext = ' '.join(sh.text_frame.text for sh in L._iter_shapes(sl.shapes) if getattr(sh, 'has_text_frame', False) and sh.has_text_frame)
            for sh in L._iter_shapes(sl.shapes):
                if not (getattr(sh, 'has_chart', False) and sh.has_chart):
                    continue
                ch = sh.chart
                cvals = []
                for pl in ch.plots:
                    for se in pl.series:
                        try:
                            cvals += [float(v) for v in se.values if v is not None]
                        except Exception:
                            pass
                if not cvals:
                    bad.append('slide %d chart has no cached values' % i)
                    continue
                miss = [v for v in cvals if not num_ok(v, allp)]
                if miss:
                    bad.append('slide %d values not in report/calculations: %s' % (i, miss[:4]))
                # workbook = chart cache
                try:
                    wb = ch.part.chart_workbook.xlsx_part
                    xx = L.xlsx_scan(wb.blob) if wb is not None else None
                except Exception:
                    xx = None
                if xx is None:
                    bad.append('slide %d chart has no embedded workbook' % i)
                else:
                    wnums = sorted(set(xx['numbers']) | set(xx['formula_vals']))
                    wm = [v for v in cvals if not any(abs(v - w) <= 1e-6 * max(1, abs(v)) for w in wnums)]
                    if wm:
                        bad.append('slide %d chart values missing from its workbook: %s' % (i, wm[:4]))
                if any(any(abs(v - t) <= 1 for t in T6) for v in cvals):
                    try:
                        ttl = ch.chart_title.text_frame.text if ch.has_title else ''
                    except Exception:
                        ttl = ''
                    if not re.search(r'model|maximum|\bmax\b|envelope|average|mean|simple support|fixed pylon', (stext + ' ' + ttl), re.I):
                        bad.append('slide %d plots Table 6 demands without declaring the model/statistic' % i)
                n_ok += 1
        if not n_ok and not bad:
            return L.F('no native charts')
        return L.V(not bad, '; '.join(bad[:4]) if bad else '%d charts: every cached value found in the report text / Fig. 31 labels / calculations.xlsx results; workbooks contain the plotted values' % n_ok)
    _safe(res, 'D05', d05)

    def _cv():
        import cv2
        import numpy as np
        return cv2, np

    def report_images():
        if 'repimgs' not in st:
            cv2, np = _cv()
            d = ctx['tmp'] / 'x08_imgs'
            d.mkdir(exist_ok=True)
            subprocess.run(['pdfimages', '-j', '-p', str(REPORT), str(d / 'im')], capture_output=True, timeout=300)
            ims = []
            for f in sorted(d.iterdir()):
                im = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
                if im is None or im.shape[0] < 120 or im.shape[1] < 160:
                    continue
                m = re.search(r'im-(\d+)-(\d+)', f.name)
                sc = 400.0 / max(im.shape)
                ims.append((int(m.group(1)) if m else 0, int(m.group(2)) if m else 0, cv2.resize(im, (int(im.shape[1] * sc), int(im.shape[0] * sc)), interpolation=cv2.INTER_AREA)))
            st['repimgs'] = ims
        return st['repimgs']

    def best_match(tpl, img, fracs):
        cv2, np = _cv()
        ih, iw = img.shape[:2]
        th, tw = tpl.shape[:2]
        best = -1.0
        for f in fracs:
            w = int(iw * f)
            h = int(th * w / max(1, tw))
            if w < 20 or h < 20 or w > iw or h > ih:
                continue
            t2 = cv2.resize(tpl, (w, h), interpolation=cv2.INTER_AREA)
            if float(t2.std()) < 4:
                continue
            best = max(best, float(cv2.matchTemplate(img, t2, cv2.TM_CCOEFF_NORMED).max()))
        return best

    def d06():
        cv2, np = _cv()
        ims = report_images()
        if not ims:
            raise RuntimeError('grader could not extract images from input/report.pdf')
        found, det = [], []
        fr = np.linspace(0.3, 1.0, 15)
        for i, sl in enumerate(prs.slides, 1):
            boxes = L.shape_boxes(sl)
            for spid, (l, t, r, b, tag, has_txt, sh) in boxes.items():
                if tag != 'pic' or 'PICTURE' not in str(sh.shape_type):
                    continue
                try:
                    im = cv2.imdecode(np.frombuffer(sh.image.blob, np.uint8), cv2.IMREAD_GRAYSCALE)
                except Exception:
                    im = None
                if im is None:
                    continue
                sc = 400.0 / max(im.shape)
                im = cv2.resize(im, (max(1, int(im.shape[1] * sc)), max(1, int(im.shape[0] * sc))), interpolation=cv2.INTER_AREA)
                hit = None
                for pg, num, rim in ims:
                    a1 = best_match(im, rim, fr)       # deck picture is a crop of the report image
                    a2 = best_match(rim, im, fr)       # report image inside a larger deck picture
                    if max(a1, a2) >= 0.65:
                        hit = (pg, num, round(max(a1, a2), 2))
                        break
                if not hit:
                    continue
                ann = sum(1 for s2, (l2, t2, r2, b2, tag2, ht2, sh2) in boxes.items()
                          if s2 != spid and tag2 in ('sp', 'cxnSp', 'grpSp') and L.boxes_overlap((l, t, r, b), (l2, t2, r2, b2), 0)
                          and (r2 - l2) * (b2 - t2) < (r - l) * (b - t))
                if not ann:
                    det.append('slide %d: report image (PDF %d) without native callout on it' % (i, hit[0]))
                    continue
                found.append((i, 'PDF %d' % hit[0], hit[2], ann))
        return L.V(len(found) >= 2, 'report figures with native callouts: %s%s' % (found, '; ' + '; '.join(det[:3]) if det else ''))
    _safe(res, 'D06', d06)

    def d11():
        """fail-only: clip stills must be Figs 9, 10, 11 in this order (template match vs the report's embedded images)
        and their hold times must represent 0.165 s / 0.264 s at 1:1 or at a stated slow-down factor (+-10%)."""
        cv2, np = _cv()
        vid = out / 'event-clip.mp4'
        j = L.ffprobe(vid)
        vs = [s_ for s_ in j.get('streams', []) if s_.get('codec_type') == 'video']
        if not vs:
            return L.F('event-clip.mp4 has no video stream')
        W, H = 320, 180
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(vid), '-vf', 'scale=%d:%d' % (W, H), '-pix_fmt', 'gray',
                              '-f', 'rawvideo', '-vsync', 'passthrough', '-'], capture_output=True, timeout=180).stdout
        n = len(raw) // (W * H)
        if n < 3:
            return L.F('could not decode frames from event-clip.mp4')
        fr = np.frombuffer(raw[:n * W * H], np.uint8).reshape(n, H, W).astype(np.float32)
        ts = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'frame=pts_time,best_effort_timestamp_time',
                             '-of', 'csv=p=0', str(vid)], capture_output=True, text=True, timeout=120).stdout.split()
        times = []
        for x in ts:
            try:
                times.append(float([y for y in x.split(',') if y and y != 'N/A'][0]))
            except Exception:
                pass
        if len(times) != n:
            num, den = (vs[0].get('avg_frame_rate') or '25/1').split('/')
            fps = float(num) / float(den or 1) if float(num) else 25.0
            times = [k / fps for k in range(n)]
        diff = np.abs(fr[1:] - fr[:-1]).mean(axis=(1, 2))
        thr = max(1.5, 4 * float(np.median(diff)))
        ch = [k + 1 for k, d in enumerate(diff) if d > thr]
        # group consecutive change frames (cross-fades) into one transition at the group's midpoint
        trans, grp = [], []
        for k in ch:
            if grp and k != grp[-1] + 1:
                trans.append(grp)
                grp = []
            grp.append(k)
        if grp:
            trans.append(grp)
        segs = []  # (start_time, mid_frame_index) of each stable segment
        starts = [(times[0], 0)] + [(0.5 * (times[g[0]] + times[g[-1]]), g[-1]) for g in trans]
        ends = [g[0] - 1 for g in trans] + [n - 1]
        for (t0, f0), f1 in zip(starts, ends):
            if f1 >= f0:
                segs.append((t0, (f0 + f1) // 2))
        stills = {}
        for pg, num, rim in report_images():
            if pg == 30 and num is not None:
                stills.setdefault(9, rim)
            elif pg == 31:
                stills.setdefault(10 if 10 not in stills else 11, rim)
        if len(stills) < 3:
            raise RuntimeError('grader could not extract Figs 9-11 from report PDF 30-31')
        lab = []
        for t0, mi in segs:
            frame = fr[mi].astype(np.uint8)
            sc = {f: best_match(img, frame, np.linspace(0.3, 1.0, 15)) for f, img in stills.items()}
            f, v = max(sc.items(), key=lambda kv: kv[1])
            lab.append((t0, f if v >= 0.55 else None, round(v, 2)))
        seq = [(t0, f) for t0, f, _ in lab if f is not None]
        # collapse repeats (same still in consecutive segments)
        comp = []
        for t0, f in seq:
            if not comp or comp[-1][1] != f:
                comp.append((t0, f))
        figs = [f for _, f in comp]
        if figs != [9, 10, 11]:
            return L.F('stills identified in clip order %s (need exactly Fig 9 -> Fig 10 -> Fig 11); segments %s' % (figs, lab[:8]))
        d1, d2 = comp[1][0] - comp[0][0], comp[2][0] - comp[1][0]
        k1, k2 = d1 / 0.165, d2 / 0.264
        if abs(k1 / k2 - 1) > 0.10:
            return L.F('hold times %.3f s / %.3f s do not keep the 0.165 : 0.264 s ratio (+-10%%)' % (d1, d2))
        k = (d1 + d2) / 0.429
        if abs(k - 1) <= 0.10:
            return None
        texts = ' '.join(sh.text_frame.text for sl in prs.slides for sh in L._iter_shapes(sl.shapes)
                         if getattr(sh, 'has_text_frame', False) and sh.has_text_frame) + ' ' + ' '.join(notes) + ' ' + script
        stated = []
        for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:[x×]|times)\s*(?:slow|slower|slowed)|slow(?:ed)?(?:[ -]?(?:down|motion))?\s*(?:by|to|of)?\s*'
                             r'(?:a\s*factor\s*of\s*)?(?:about\s*)?(\d+(?:\.\d+)?)\s*(?:[x×]|times)?|factor\s*of\s*(\d+(?:\.\d+)?)|1\s*/\s*(\d+(?:\.\d+)?)\s*speed', texts, re.I):
            for g in m.groups():
                if g:
                    try:
                        stated.append(float(g))
                    except Exception:
                        pass
        if any(f > 0 and abs(k / f - 1) <= 0.10 for f in stated):
            return None
        return L.F('measured slow-down %.2fx (holds %.3f s / %.3f s) but no matching factor stated in slide text, notes or script (found %s)' % (k, d1, d2, stated[:5]))
    _safe(res, 'D11', d11)

    anim = {}
    for i, root, ti, tx in tinfo:
        a_ = set()
        for c in ti['main_clicks']:
            a_ |= {s_ for s_ in c['spids'] if s_}
        trig = set(ti['triggers'])
        for tr, effs in ti['triggers'].items():
            for e in effs:
                a_ |= {s_ for s_ in e['spids'] if s_ and s_ != tr}
        tm = root.find('p:timing', L.NS)
        if tm is not None:
            for c in tm.iter('{%s}cTn' % L.NS['p']):
                if c.get('presetClass') in ('entr', 'exit', 'emph', 'path'):
                    a_ |= {t.get('spid') for t in c.iter('{%s}spTgt' % L.NS['p']) if t.get('spid')}
        anim[i] = (a_ - trig, trig)

    def v06():
        out_ = L.shapes_outside_slide(prs)
        if out_:
            return L.F('shapes extend beyond the slide: %s' % out_[:5])
        bad = []
        for i, sl in enumerate(prs.slides, 1):
            bx = L.shape_boxes(sl)
            a_, trig = anim.get(i, (set(), set()))
            st_txt = [(k, v) for k, v in bx.items() if v[5] and k not in a_ and v[4] in ('sp', 'graphicFrame')]
            for x in range(len(st_txt)):
                for y in range(x + 1, len(st_txt)):
                    (k1, b1), (k2, b2) = st_txt[x], st_txt[y]
                    if L.boxes_overlap(b1[:4], b2[:4], 91440):
                        bad.append((i, b1[6].name, b2[6].name))
        if bad:
            return L.F('always-visible text objects overlap: %s' % bad[:5])
        return None  # text overflow / clipping inside boxes -> judge on rendered pages
    _safe(res, 'V06', v06)

    def v07():
        bad, n_t = [], 0
        for i, sl in enumerate(prs.slides, 1):
            a_, trig = anim.get(i, (set(), set()))
            if not a_:
                continue
            bx = L.shape_boxes(sl)
            root = dict((x[0], x[1]) for x in tinfo).get(i)
            glued = {}
            if root is not None:
                for cx in root.iter('{%s}cxnSp' % L.NS['p']):
                    nv = next((e for e in cx.iter() if e.tag.endswith('}cNvPr')), None)
                    ends = {e.get('id') for e in cx.iter() if e.tag.endswith('}stCxn') or e.tag.endswith('}endCxn')}
                    if nv is not None:
                        glued[nv.get('id')] = ends
            for tgt in a_:
                if tgt not in bx or bx[tgt][4] == 'cxnSp':
                    continue
                n_t += 1
                tb = bx[tgt][:4]
                for k, v in bx.items():
                    if k == tgt or k in a_:
                        continue
                    kind = v[4]
                    if kind == 'cxnSp':
                        if tgt not in glued.get(k, set()) and L.connector_crosses(v[6], v, tb):
                            bad.append((i, bx[tgt][6].name, v[6].name))
                        continue
                    obstacle = (k in trig) or kind == 'graphicFrame' \
                        or (kind in ('sp', 'grpSp') and v[5]) or (kind == 'pic' and any(e.tag.endswith('}videoFile') or e.tag.endswith('}media') for e in v[6]._element.iter()))
                    if obstacle and L.boxes_overlap(tb, v[:4], 91440):
                        bad.append((i, bx[tgt][6].name, v[6].name))
        if not n_t:
            return L.F('no animated shapes found')
        return L.V(not bad, 'revealed shapes cover always-visible objects: %s' % bad[:5] if bad else
                   '%d animated shapes; none covers a trigger, connector, chart/table frame, video or always-visible text' % n_t)
    _safe(res, 'V07', v07)

    if not ok:
        for it in ctx['items']:
            if it.get('group') == 'G6' or it['id'] == 'V07':
                res[it['id']] = L.F('GATE1 structural proxy failed: %s' % probs[:3])
    return res


D14_TOPICS = [('D08', r'trigger'), ('D09', r'chart (?:build|animation)|build[s]? by (?:series|category)'),
              ('D10', r'video|clip|media|playback'), ('D07', r'mechanism|click sequence|on-click'),
              ('D12', r'offline|external|linked'), ('D04', r'edit data|embedded workbook|chartdata')]


def d14_contradiction(results, ctx):
    """v2026-10-25: playback-check.md claims a property as verified that the grader measured as failing."""
    p = ctx['out'] / 'playback-check.md'
    if not p.exists():
        return None
    hits = []
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        l = line.lower()
        if not re.search(r'verified|confirmed|works|working|tested|plays|checked|passed|\bok\b|✓|✔', l):
            continue
        if re.search(r"\bnot\b|cannot|can't|could not|unable|unverified|untested|n/a|no access|without powerpoint", l):
            continue
        for iid, pat in D14_TOPICS:
            if re.search(pat, l) and results.get(iid, {}).get('verdict') == 'fail' and results.get(iid, {}).get('source') == 'checks':
                hits.append('%s claimed (%r) but checks failed %s' % (iid, line.strip()[:60], iid))
    return hits


def postprocess(results, ctx):
    try:
        hits = d14_contradiction(results, ctx) if not ctx.get('_x08_gate0') else None
    except Exception:
        raise
    if hits:
        results['D14'] = dict(results.get('D14', {}), verdict='fail', detail='; '.join(hits[:3]), source='checks')
    g1 = ctx.get('_x08_gate1')
    if g1 and not g1[0]:
        for it in ctx['items']:
            if it.get('group') == 'G6' or it['id'] == 'V07':
                results[it['id']] = dict(results.get(it['id'], {}), verdict='fail', detail='GATE1 structural proxy failed', gated=True)
    return results
