# -*- coding: utf-8 -*-
"""CDC-D-X01 deterministic checks (door plug briefing). Helpers in dpptx.py.

Machine-decided (pass/fail): N05, V01, V02, V03, V04, V06, V07, D01, D02, D04, D07, D08, D09.
Fail-only (violation => fail, otherwise left to the judge): N01, D03, D05, D06, F01-F08 (F items: the machine trace
is appended to the item's verify text for the judge). Static layout/typography/animation helpers in cdc_layout.py
(added 2026-10-25).
postprocess: GATE0 (all fail), GATE1 static approximation (G6 = 0 and V07 fail),
H06 conditional N/A (+ G3 nominal weight renormalised so G3 stays worth 20 when H06 is N/A).
"""
import json, re, traceback
from pathlib import Path

import dpptx as U
import cdc_layout as L

DELIV = ['presentation.pptx', 'slides.pdf', 'script.md', 'evidence-index.csv', 'playback-check.md']
F = lambda d: {'verdict': 'fail', 'detail': d}
P = lambda d: {'verdict': 'pass', 'detail': d}
STATE = {}


def _safe(R, iid, fn):
    try:
        v = fn()
        if v is not None:
            R[iid] = v
    except Exception as e:
        R[iid] = F(f'check error: {type(e).__name__}: {e}')


def run(ctx):
    out = Path(ctx['out'])
    R = {}
    missing = [f for f in DELIV if not (out / f).is_file()]
    STATE['missing'] = missing
    pp = out / 'presentation.pptx'
    deck = None
    if pp.is_file():
        try:
            from pptx import Presentation
            Presentation(str(pp))
            deck = U.Deck(pp)
        except Exception as e:
            STATE['parse_error'] = str(e)[:300]
    STATE['integrity'] = U.integrity(pp) if pp.is_file() else ['missing pptx']
    STATE['deck'] = deck
    STATE['script'] = (out / 'script.md').read_text(encoding='utf-8', errors='replace') if (out / 'script.md').is_file() else ''
    if deck is None:
        return R  # GATE0 handled in postprocess
    n = len(deck.slides)
    script = U.parse_script(STATE['script'])

    # ---- N01 (fail-only)
    def n01():
        bad = []
        if not 8 <= n <= 10:
            bad.append(f'{n} slides')
        r = deck.cx / deck.cy
        if abs(r / (16 / 9) - 1) > 0.01:
            bad.append(f'aspect {r:.3f}')
        for i in range(1, n):
            content = [k for k, v in deck.shape_boxes(i).items() if v['ph'] not in ('title', 'ctrTitle', 'sldNum', 'dt', 'ftr')
                       and (v['text'] or v['kind'] in ('pic', 'graphicFrame', 'cxnSp'))]
            if not content:
                bad.append(f'slide {i + 1} has no content besides title')
        return F('; '.join(bad)) if bad else None
    _safe(R, 'N01', n01)

    # ---- N05 word count / timing / notes = script
    def n05():
        if not script:
            return F('script.md has no per-slide "Slide N" sections')
        words = sum(v['words'] for v in script.values())
        pause_min = sum(v['pauses_s'] for v in script.values()) / 60
        lo, hi = words / 150 + pause_min, words / 130 + pause_min
        bad = []
        if hi < 11 or lo > 13:
            bad.append(f'words={words}, pauses={pause_min:.2f} min -> {lo:.2f}-{hi:.2f} min, no overlap with 11-13')
        decl = [v['declared_s'] for v in script.values()]
        if any(d is None for d in decl):
            bad.append(f'per-slide timing missing for slides {[k for k, v in script.items() if v["declared_s"] is None]}')
        else:
            tot = sum(decl) / 60
            if not 11 * 0.9 <= tot <= 13 * 1.1:
                bad.append(f'declared per-slide sum {tot:.2f} min outside 11-13 min ±10%')
        low = []
        for i in range(n):
            s = script.get(i + 1)
            ov = U.overlap(deck.notes(i), s['text'] if s else '')
            if ov < 0.9:
                low.append(f'{i + 1}:{ov:.2f}')
        if low:
            bad.append('notes vs script token overlap <0.90 on slides ' + ', '.join(low))
        if bad:
            return F('; '.join(bad))
        return P(f'words={words}, pauses={pause_min:.2f} min, est {lo:.2f}-{hi:.2f} min; declared {sum(decl) / 60:.2f} min; notes match')
    _safe(R, 'N05', n05)

    # ---- V03 <=6 bullets per slide (summed over the slide's body placeholders and bulleted text boxes)
    def v03():
        bad = [f'slide {k}: {nb} bullets ({d})' for k, nb, d in L.bullets_per_slide(pp) if nb > 6]
        return F('; '.join(bad[:8])) if bad else P('every slide has <=6 bullet paragraphs (body placeholders + bulleted text boxes; '
                                                   'captions/source lines and connector-linked diagram nodes excluded)')
    _safe(R, 'V03', v03)

    # ---- V01 / V02 effective font sizes (explicit or inherited size x autofit scale)
    def v01():
        bv, _, nr = L.font_violations(pp, 20, 12)
        return F(f'{len(bv)} body run(s) <20 pt: ' + '; '.join(bv[:6])) if bv else P(f'all body text runs >=20 pt ({nr} runs checked)')
    _safe(R, 'V01', v01)

    def v02():
        _, sv, nr = L.font_violations(pp, 20, 12)
        return F(f'{len(sv)} caption/source/title/table run(s) <12 pt: ' + '; '.join(sv[:6])) if sv else \
            P('all captions, source lines, titles and table cells >=12 pt')
    _safe(R, 'V02', v02)

    # ---- V04 chart axes / legend
    def v04():
        iss, nc = L.chart_axis_issues(pp)
        if not nc:
            return F('no native charts')
        return F('; '.join(iss[:6])) if iss else P(f'{nc} chart(s): every visible axis titled, value axes carry units, legends on multi-series charts')
    _safe(R, 'V04', v04)

    # ---- V06 static layout: overflow / off-slide / overlapping text (non-animated shapes)
    def v06():
        iss = L.layout_issues(pp, exclude_animated=True)
        return F('; '.join(iss[:6])) if iss else P('no estimated text overflow, no shape beyond the slide edge, no overlapping text areas')
    _safe(R, 'V06', v06)

    # ---- V07 animation states: animated text vs co-visible text, animated text covering a figure/chart
    def v07():
        iss, nchk = L.animation_occlusion(pp)
        return F('; '.join(iss[:6])) if iss else P(f'no overlap in any reachable animation state ({nchk} animated pairs checked)')
    _safe(R, 'V07', v07)

    # ---- D01 PDF matches deck
    def d01():
        pdf = out / 'slides.pdf'
        if not pdf.is_file():
            return F('slides.pdf missing')
        pc = U.pdf_page_count(pdf)
        if pc != n:
            return F(f'pdf pages {pc} != slides {n}')
        pages = U.pdf_pages_text(pdf) or []
        miss = []
        for i in range(n):
            ref = U.norm_words(deck.title(i) or deck.slide_text(i))
            if not ref:
                continue
            got = U.norm_words(pages[i] if i < len(pages) else '')
            if len(ref & got) / len(ref) < 0.6:
                miss.append(i + 1)
        if miss:
            return F(f'title text not found on corresponding PDF page(s) {miss}')
        return P(f'{n} pages, titles match page-by-page')
    _safe(R, 'D01', d01)

    # ---- D02 evidence-index columns + >=1 row per slide
    def d02():
        p = out / 'evidence-index.csv'
        if not p.is_file():
            return F('evidence-index.csv missing')
        h, rows = U.read_csv(p)
        cols = {'slide': U.find_col(h, ('slide',)), 'element': U.find_col(h, ('element',), ('object',)),
                'claim': U.find_col(h, ('claim',), ('fact',)), 'source': U.find_col(h, ('source', 'file'), ('file',), ('source',)),
                'printed': U.find_col(h, ('printed',)), 'pdf_page': U.find_col(h, ('pdf', 'page'), ('pdf',)),
                'fig': U.find_col(h, ('figure',), ('table',), ('section',), ('fig',)), 'transform': U.find_col(h, ('transform',))}
        miss = [k for k, v in cols.items() if v is None]
        if miss:
            return F(f'missing columns {miss}; header={h}')
        seen = set()
        for r in rows:
            if cols['slide'] < len(r):
                for m in re.findall(r'\d+', r[cols['slide']]):
                    seen.add(int(m))
        lack = [i for i in range(1, n + 1) if i not in seen]
        if lack:
            return F(f'no evidence rows for slides {lack}')
        return P(f'{len(rows)} rows, all 8 columns, every slide covered')
    _safe(R, 'D02', d02)

    # ---- D03 (fail-only): notes on every slide + AI disclosure
    def d03():
        empty = [i + 1 for i in range(n) if not deck.notes(i).strip()]
        alltxt = ' '.join(deck.slide_text(i) + ' ' + deck.notes(i) for i in range(n))
        bad = []
        if empty:
            bad.append(f'empty notes on slides {empty}')
        if not re.search(r'\bAI\b|artificial intelligence|language model|\bLLM\b', alltxt, re.I):
            bad.append('no AI-assistance disclosure found in slides/notes')
        return F('; '.join(bad)) if bad else None
    _safe(R, 'D03', d03)

    # ---- D04 native charts + embedded workbook content
    def d04():
        chs = deck.charts()
        ok, notes = [], []
        for c in chs:
            if c['wb'] is None:
                notes.append(f'slide {c["slide"]}: {c["err"]}')
                continue
            try:
                cells = U.xlsx_first_sheet(c['wb'])
            except Exception as e:
                notes.append(f'slide {c["slide"]}: workbook unreadable {e}')
                continue
            nums = [x for x in cells if x['t'] not in ('s', 'inlineStr', 'str') and U.is_num(x['v'])]
            txt = ' '.join(str(x['v']) for x in cells if x['v'] is not None and not U.is_num(x['v']))
            has_page = bool(U.PAGE_RE.search(txt))
            has_unit = bool(re.search(r'\b(ft|feet|psi|lb|lbs|g|days?|min|minutes?|s|sec|seconds?|hours?|cycles?|instances?|airplanes?|aircraft|count|number|%|percent|knots?|kt|UTC|PST|year|occupants|people|persons)\b|\(.*\)', txt, re.I))
            if len(nums) >= 2 and has_page and has_unit:
                ok.append(c['slide'])
            else:
                notes.append(f'slide {c["slide"]}: nums={len(nums)} page_ref={has_page} unit={has_unit}')
        if len(ok) >= 2:
            return P(f'{len(ok)} native charts with embedded workbooks listing values/units/pages (slides {ok}); COM Activate not run')
        return F(f'{len(chs)} chart(s), {len(ok)} qualifying; ' + '; '.join(notes[:6]))
    _safe(R, 'D04', d04)

    # ---- D06 (fail-only): >=2 pictures + native callouts
    def d06():
        pics = sum(len(deck.pictures(i)) for i in range(n))
        if pics < 2:
            return F(f'only {pics} raster picture(s) in deck')
        return None
    _safe(R, 'D06', d06)

    # ---- D07 causal chain: connectors + >=5 on-click entrance effects on distinct shapes
    def d07():
        best = None
        for i in range(n):
            tm = deck.timing(i)
            sp = deck.shape_boxes(i)
            clicks = {e['spid'] for e in tm['main'] if e['cls'] == 'entr' and e['node'] == 'clickEffect' and e['spid'] in sp}
            cx = deck.connectors(i)
            glued = [c for c in cx if c[0] or c[1]]
            cand = (len(clicks), len(glued), i + 1)
            if best is None or cand > best:
                best = cand
            if len(clicks) >= 5 and glued:
                return P(f'slide {i + 1}: {len(clicks)} on-click entrance effects on distinct shapes, {len(glued)} glued connectors (slideshow execution not run)')
        return F(f'no slide with >=5 on-click entrance effects + glued connectors; best (clicks, glued connectors, slide)={best}')
    _safe(R, 'D07', d07)

    # ---- D08 triggers: >=3 interactive sequences triggered by distinct shape clicks revealing a separate shape
    def d08():
        best = (0, None)
        for i in range(n):
            tm = deck.timing(i)
            sp = deck.shape_boxes(i)
            trig = set()
            for it in tm['inter']:
                if it['evt'] != 'onClick' or not it['trigger'] or it['trigger'] not in sp:
                    continue
                rev = [e for e in it['effects'] if e['cls'] == 'entr' and e['spid'] and e['spid'] != it['trigger'] and e['spid'] in sp
                       and sp[e['spid']]['kind'] == 'sp' and sp[e['spid']]['text']]
                if rev:
                    trig.add(it['trigger'])
            if len(trig) > best[0]:
                best = (len(trig), i + 1)
        if best[0] >= 3:
            return P(f'slide {best[1]}: {best[0]} shape-click triggers each revealing a separate editable text shape (slideshow click not run)')
        return F(f'max shape-click triggers revealing editable text on one slide = {best[0]} (slide {best[1]})')
    _safe(R, 'D08', d08)

    # ---- D09 self-contained (no external links, internal parts present, embedded workbooks)
    def d09():
        ext = deck.external_links()
        miss = [x for x in STATE['integrity'] if 'missing' in x]
        chs = [c for c in deck.charts() if c['wb'] is None]
        bad = []
        if ext:
            bad.append(f'external links: {ext[:5]}')
        if miss:
            bad.append(f'missing parts: {miss[:5]}')
        if chs:
            bad.append(f'charts without embedded workbook: {[c["slide"] for c in chs]}')
        return F('; '.join(bad)) if bad else P('no external media/OLE/workbook links; all internal targets present (static check)')
    _safe(R, 'D09', d09)

    # ---- D05 (fail-only) plotted values: workbook = plotted values; every value printed in the material / answer key
    # or a live workbook formula. Basis/stage correctness is judged from the chart_data evidence.
    def d05():
        mat = L.material(ctx['input'])
        iss, nv, nc = L.plotted_value_issues(pp, mat, L.number_set(json.dumps(ctx.get('answer') or {}, ensure_ascii=False)))
        if not nc:
            return F('no native charts')
        return F('; '.join(iss[:6])) if iss else None
    _safe(R, 'D05', d05)

    # ---- F01-F08 (fail-only + trace for the judge)
    def fid():
        groups = {f'F0{k}': [k] for k in range(1, 8)}
        groups['F08'] = list(range(8, n + 1))
        return L.fidelity(ctx, pp, groups, out / 'evidence-index.csv')
    try:
        R.update(fid())
    except Exception as e:
        for k in range(1, 9):
            R[f'F0{k}'] = F(f'check error: {type(e).__name__}: {e}')
    return R


LEAVE_RE = re.compile(r'(on leave|leave|vacation|holiday|\bPTO\b|time off|day off|days off|off work|absent|not at work|away)', re.I)
DOORM_RE = re.compile(r'(experienced|senior|most.{0,20}door|door (team|crew)? ?member|door[- ]team)', re.I)


def _leave_cited():
    deck = STATE.get('deck')
    texts = [STATE.get('script', '')]
    if deck is not None:
        for i in range(len(deck.slides)):
            texts += [deck.slide_text(i), deck.notes(i)]
    blob = '\n'.join(texts)
    for m in LEAVE_RE.finditer(blob):
        win = blob[max(0, m.start() - 250): m.end() + 250]
        if DOORM_RE.search(win) and re.search(r'door', win, re.I):
            return True
    return False


def postprocess(res, ctx):
    items = ctx['items']
    # GATE0
    if STATE.get('missing') or STATE.get('deck') is None:
        why = f"GATE0: missing {STATE.get('missing')} / pptx parse error {STATE.get('parse_error')}"
        for i in items:
            res[i['id']] = {'verdict': 'fail', 'detail': why, 'source': 'gate'}
        res['_gate'] = {'verdict': 'fail', 'detail': why}
        return res
    # GATE1 (static approximation of PowerPoint repair prompt)
    iss = STATE.get('integrity') or []
    if iss:
        why = 'GATE1 (static package integrity, approximates repair prompt): ' + '; '.join(iss[:6])
        for i in items:
            if i['group'] == 'G6' or i['id'] == 'V07':
                res[i['id']] = {'verdict': 'fail', 'detail': why, 'source': 'gate'}
        res['_gate1'] = {'verdict': 'fail', 'detail': why}
    # H06 conditional
    try:
        cited = _leave_cited()
    except Exception:
        cited = True
        res['_h06_error'] = {'verdict': 'error', 'detail': traceback.format_exc()[-600:]}
    h = res.get('H06', {})
    if not cited and h.get('verdict') not in ('pass',):
        res['H06'] = {'verdict': 'na', 'detail': 'conditional: experienced door member leave not cited in slides/notes/script', 'source': 'checks-postprocess'}
    elif cited and h.get('verdict') == 'na':
        res['H06'] = dict(h, verdict='fail', detail='leave fact appears to be cited (regex) but judge returned N/A; conditional item applies')
    # group-normalised scoring: G3 keeps nominal weight 20 when H06 is N/A
    g3 = [i for i in items if i['group'] == 'G3']
    app = [i for i in g3 if res.get(i['id'], {}).get('verdict') != 'na']
    if app:
        w = 20.0 / len(app)
        for i in g3:
            i['weight'] = round(w, 6)
    return res
