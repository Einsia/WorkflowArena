# -*- coding: utf-8 -*-
"""CDC-D-X02 deterministic checks (corn mill dust explosion briefing). Helpers in dpptx.py.

Machine-decided (pass/fail): N00, N04, V01, V02, V03, V04, V05, D01, D03, D04, D05, D07, D07b, D11.
Fail-only (violation => fail, else left to the judge): N01, D02, D06, D08, D09, D10, F01-F06 (F items: the sampled
slide is fixed here and the machine trace is appended to the item's verify text for the judge).
Static layout/typography/animation/traceability helpers in cdc_layout.py (added 2026-10-25).
postprocess: GATE-W (all fail), GATE-P static approximation (package integrity issues => G6 = 0).
"""
import json, random, re, subprocess
from pathlib import Path

import dpptx as U
import cdc_layout as L

DELIV = ['presentation.pptx', 'slides.pdf', 'script.md', 'evidence-index.csv', 'events.csv']
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
    out, inp, tmp = Path(ctx['out']), Path(ctx['input']), Path(ctx['tmp'])
    R = {}
    # Workaround: rubric_score.load_items() picks the first list whose dicts carry 'criterion_zh'; in this
    # rubric.json that is 'gates' (3 entries) rather than 'items' (55). Replace the list in place so that both
    # judging and scoring in rubric_score.main() use the real items. Idempotent if the scorer is fixed.
    items, rub = ctx.get('items'), ctx.get('rubric') or {}
    if isinstance(items, list) and isinstance(rub.get('items'), list) and items is not rub['items'] \
            and all(str(i.get('id', '')).startswith('GATE') for i in items):
        items[:] = rub['items']
    STATE['missing'] = [f for f in DELIV if not (out / f).is_file()]
    pp = out / 'presentation.pptx'
    deck = None
    if pp.is_file():
        try:
            from pptx import Presentation
            Presentation(str(pp))
            deck = U.Deck(pp)
        except Exception as e:
            STATE['parse_error'] = str(e)[:300]
    STATE['deck'] = deck
    STATE['integrity'] = U.integrity(pp) if pp.is_file() else ['missing pptx']
    if deck is None:
        return R
    n = len(deck.slides)
    stext = (out / 'script.md').read_text(encoding='utf-8', errors='replace') if (out / 'script.md').is_file() else ''
    script = U.parse_script(stext)

    # media on all slides: [(slide_idx, media dict, duration)]
    media = []
    for i in range(n):
        for m in deck.media(i):
            d = None if (m['linked'] or not m['target'] or m['target'] not in deck.names) else U.media_duration(deck, m['target'], tmp)
            media.append((i, m, d))
    narr = [x for x in media if x[1]['kind'] == 'audio'] or media
    STATE['narr'] = narr

    lpkg = L.Pkg(pp)

    def _top_text(i):
        """fallback title: top-most text shape starting in the top 20 % of the slide (decks built on blank layouts)."""
        c = [t for t in L.text_shapes(lpkg, i) if t['box'] and t['box'][1] < 0.2 * lpkg.cy and t['role'] != 'footer']
        return min(c, key=lambda t: t['box'][1])['text'] if c else ''

    # ---- N01 (fail-only)
    def n01():
        bad = []
        if not 14 <= n <= 18:
            bad.append(f'{n} slides')
        r = deck.cx / deck.cy
        if abs(r / (16 / 9) - 1) > 0.01:
            bad.append(f'aspect {r:.3f}')
        nt = [i + 1 for i in range(n) if not deck.title(i).strip() and not _top_text(i)]
        if nt:
            bad.append(f'no title (title placeholder or a text shape in the top 20 % of the slide) on slides {nt}')
        return F('; '.join(bad)) if bad else None
    _safe(R, 'N01', n01)

    # ---- N00 notes on every slide + per-slide duration in script
    def n00():
        bad = []
        empty = [i + 1 for i in range(n) if not deck.notes(i).strip()]
        if empty:
            bad.append(f'empty notes on slides {empty}')
        if not script:
            bad.append('script.md has no "Slide N" sections')
        else:
            nod = [k for k in range(1, n + 1) if k not in script or script[k]['declared_s'] is None]
            if nod:
                bad.append(f'no per-slide duration for slides {nod}')
        return F('; '.join(bad)) if bad else P('notes on all slides; every script section declares a duration')
    _safe(R, 'N00', n00)

    # ---- N04 notes=script, 12-15 min, per-slide durations
    def n04():
        if not script:
            return F('script.md has no "Slide N" sections')
        bad = []
        low = []
        for i in range(n):
            s = script.get(i + 1)
            ov = U.overlap(deck.notes(i), s['text'] if s else '')
            if ov < 0.9:
                low.append(f'{i + 1}:{ov:.2f}')
        if low:
            bad.append('notes vs script similarity <0.90 on slides ' + ', '.join(low))
        words = sum(v['words'] for v in script.values())
        a_slide = {}
        for i, m, d in narr:
            a_slide[i + 1] = a_slide.get(i + 1, 0) + (d or 0)
        a_min = sum(a_slide.values()) / 60
        lo, hi = words / 150 + a_min, words / 130 + a_min
        if hi < 12 or lo > 15:
            bad.append(f'words={words}+audio {a_min:.2f} min -> {lo:.2f}-{hi:.2f} min, no overlap with 12-15')
        dev = []
        for k, v in script.items():
            if v['declared_s'] is None:
                dev.append(f'{k}:none')
                continue
            est = v['words'] / 140 * 60 + a_slide.get(k, 0)
            tol = max(0.25 * est, 10)
            if abs(v['declared_s'] - est) > tol:
                dev.append(f'{k}:decl {v["declared_s"]:.0f}s vs est {est:.0f}s')
        if dev:
            bad.append('per-slide duration mismatch ' + ', '.join(dev[:8]))
        return F('; '.join(bad)) if bad else P(f'words={words}, audio={a_min:.2f} min, est {lo:.2f}-{hi:.2f} min; per-slide durations within tolerance; notes match')
    _safe(R, 'N04', n04)

    # ---- V01 <=6 bullets per slide (summed over body placeholders and bulleted text boxes, all levels)
    def v01():
        bad = [f'slide {k}: {nb} bullets ({d})' for k, nb, d in L.bullets_per_slide(pp) if nb > 6]
        return F('; '.join(bad[:8])) if bad else P('every slide has <=6 bullet paragraphs (body placeholders + bulleted text boxes, '
                                                   'all levels; captions/source lines and connector-linked diagram nodes excluded)')
    _safe(R, 'V01', v01)

    # ---- V02 effective font sizes, V03 static layout, V04 animation states, V05 chart axes
    def v02():
        bv, sv, nr = L.font_violations(pp, 20, 12)
        if bv or sv:
            return F(f'{len(bv)} body run(s) <20 pt, {len(sv)} caption/source/title/table run(s) <12 pt: ' + '; '.join((bv + sv)[:6]))
        return P(f'body >=20 pt and captions/source lines/titles/tables >=12 pt at effective size ({nr} runs)')
    _safe(R, 'V02', v02)

    def v03():
        iss = L.layout_issues(pp, exclude_animated=True)
        return F('; '.join(iss[:6])) if iss else P('no estimated text overflow, no shape beyond the slide edge, no overlapping text areas')
    _safe(R, 'V03', v03)

    def v04():
        iss, nchk = L.animation_occlusion(pp)
        return F('; '.join(iss[:6])) if iss else P(f'no overlap in any reachable animation state ({nchk} animated pairs checked)')
    _safe(R, 'V04', v04)

    def v05():
        iss, nc = L.chart_axis_issues(pp)
        if not nc:
            return F('no native charts')
        return F('; '.join(iss[:6])) if iss else P(f'{nc} chart(s): every visible axis titled, value axes carry units, legends on multi-series charts')
    _safe(R, 'V05', v05)

    # ---- D01 pdf pages + csv/script parseable with columns
    def d01():
        bad = []
        pc = U.pdf_page_count(out / 'slides.pdf') if (out / 'slides.pdf').is_file() else None
        if pc != n:
            bad.append(f'pdf pages {pc} != slides {n}')
        if not script:
            bad.append('script.md not parseable per slide')
        h, rows = U.read_csv(out / 'evidence-index.csv') if (out / 'evidence-index.csv').is_file() else ([], [])
        need = {'slide': [('slide',)], 'element': [('element',), ('object',)], 'claim': [('claim',), ('fact',)],
                'source': [('source', 'file'), ('file',), ('source',)], 'pdf page': [('pdf', 'page'), ('pdf',)],
                'figure/table/appendix': [('figure',), ('table',), ('appendix',), ('fig',)], 'transformation': [('transform',)]}
        miss = [k for k, alts in need.items() if U.find_col(h, *alts) is None]
        if miss or not rows:
            bad.append(f'evidence-index.csv missing columns {miss} or no rows')
        h2, rows2 = U.read_csv(out / 'events.csv') if (out / 'events.csv').is_file() else ([], [])
        need2 = {'slide': [('slide',)], 'bookmark name': [('bookmark', 'name'), ('name',), ('bookmark',)],
                 'time': [('time',)], 'sentence': [('sentence',), ('spoken',), ('text',)], 'object': [('object',), ('shape',), ('trigger',), ('annotation',)]}
        miss2 = [k for k, alts in need2.items() if U.find_col(h2, *alts) is None]
        if miss2 or not rows2:
            bad.append(f'events.csv missing columns {miss2} or no rows')
        return F('; '.join(bad)) if bad else P(f'{n} pages = slides; script/evidence-index/events parse with all columns')
    _safe(R, 'D01', d01)

    # ---- D02 (fail-only) AI disclosure on slides
    def d02():
        txt = ' '.join(deck.slide_text(i) for i in range(n))
        if not re.search(r'\bAI\b|artificial intelligence|language model|\bLLM\b', txt, re.I):
            return F('no AI-production statement found in slide text')
        return None
    _safe(R, 'D02', d02)

    # ---- D03 embedded narration 30-60 s, labelled, autostart
    def d03():
        if not narr:
            return F('no embedded audio/video media found')
        notes = []
        for i, m, d in narr:
            why = []
            if m['linked'] or not m['target']:
                why.append('linked/not embedded')
            if d is None or not 30 <= d <= 60:
                why.append(f'duration {d}')
            tm = deck.timing(i)
            if m['spid'] not in tm['media_auto']:
                why.append('no automatic (onBegin/after-previous) play on slide entry')
            if not re.search(r'presenter|\bTTS\b|text[- ]to[- ]speech|synthes|AI[- ]generated|computer[- ]generated|recorded by|narrat', deck.slide_text(i), re.I):
                why.append('no presenter-made/narration label on slide')
            if not why:
                return P(f'slide {i + 1}: embedded {m["kind"]} {d:.1f}s, auto-start, labelled (slideshow state & offline copy not run)')
            notes.append(f'slide {i + 1}: ' + ', '.join(why))
        return F('; '.join(notes))
    _safe(R, 'D03', d03)

    # ---- D04 bookmarks vs events.csv
    bm_all = [(i, m, b) for i, m, d in narr for b in m['bookmarks']]

    def d04():
        if len(bm_all) < 3:
            return F(f'{len(bm_all)} media bookmark(s) in PPTX')
        h, rows = U.read_csv(out / 'events.csv')
        cn = U.find_col(h, ('bookmark', 'name'), ('name',), ('bookmark',))
        ct = U.find_col(h, ('time',))
        if cn is None or ct is None:
            return F(f'events.csv lacks bookmark name/time columns: {h}')
        decl = {}
        for r in rows:
            try:
                decl[r[cn].strip()] = float(re.findall(r'-?\d+(?:\.\d+)?', r[ct])[0])
            except Exception:
                pass
        bad = []
        for i, m, (name, t) in bm_all:
            if name not in decl:
                bad.append(f'{name}: not in events.csv')
            elif abs(decl[name] - t) > 0.05:
                bad.append(f'{name}: pptx {t:.3f}s vs csv {decl[name]:.2f}s')
        return F('; '.join(bad)) if bad else P(f'{len(bm_all)} bookmarks, names and times match events.csv within 0.05 s')
    _safe(R, 'D04', d04)

    # ---- D05 bookmark triggers -> separate editable annotation over a picture
    def d05():
        good, notes = set(), []
        for i in {x[0] for x in narr}:
            tm = deck.timing(i)
            sp = deck.shape_boxes(i)
            pics = [sp[p]['box'] for p in deck.pictures(i) if p in sp]
            names = {b[0] for ii, m, d in narr if ii == i for b in m['bookmarks']}
            used = set()
            for it in tm['inter']:
                if it['evt'] != 'onMediaBookmark':
                    continue
                bn = it['bookmark']
                rev = [e['spid'] for e in it['effects'] if e['cls'] == 'entr' and e['spid'] in sp and sp[e['spid']]['kind'] in ('sp', 'cxnSp')]
                rev = [s for s in rev if s not in used]
                if not rev:
                    notes.append(f'bookmark {bn}: no editable entrance target')
                    continue
                over = [s for s in rev if any(U.boxes_overlap(sp[s]['box'], b) for b in pics)]
                if bn not in names:
                    notes.append(f'bookmark trigger {bn} not a bookmark of the narration')
                elif not over:
                    notes.append(f'bookmark {bn}: annotation not over a picture')
                else:
                    used.add(over[0])
                    good.add((i, bn))
        if len(good) >= 3:
            return P(f'{len(good)} bookmark-triggered native annotations over figures (timed screen capture not run)')
        return F(f'{len(good)} valid bookmark triggers; ' + '; '.join(notes[:6]))
    _safe(R, 'D05', d05)

    # ---- D07 / D07b charts
    chs = deck.charts()

    def d07():
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
            if nums:
                ok.append(c['slide'])
            else:
                notes.append(f'slide {c["slide"]}: empty data area')
        if len(ok) >= 2:
            return P(f'{len(ok)} native charts with non-empty embedded workbooks (slides {ok}); COM Activate not run')
        return F(f'{len(chs)} chart(s), {len(ok)} with data; ' + '; '.join(notes[:6]))
    _safe(R, 'D07', d07)

    def d07b():
        mat = L.material(inp)
        bad, ok = [], []
        for c in chs:
            if c['wb'] is None:
                bad.append(f'slide {c["slide"]}: no workbook ({c["err"]})')
                continue
            try:
                book = L.workbook_cells(c['wb'])
            except Exception as e:
                bad.append(f'slide {c["slide"]}: workbook unreadable {e}')
                continue
            strs = ' '.join(str(v) for cells in book.values() for v, f in cells.values() if isinstance(v, str))
            why = []
            if not U.PAGE_RE.search(strs):
                why.append('no source/page reference')
            if not L.UNIT_STRICT.search(strs):
                why.append('no unit')
            pasted = []
            for sh, cells in book.items():
                hdr = {re.sub(r'\d', '', ref): str(v) for ref, (v, f) in cells.items() if re.sub(r'\D', '', ref) == '1' and isinstance(v, str)}
                for ref, (v, f) in cells.items():
                    if not isinstance(v, float) or f:
                        continue
                    if re.search(r'page|\bpg\b|\bp\.|ref|source|year|\bid\b|#|\bno\b', hdr.get(re.sub(r'\d', '', ref), ''), re.I):
                        continue
                    if not (mat.find(v) or mat.find_rounded(v)):
                        pasted.append(f'{sh}!{ref}={L.fmt(v)}')
            if pasted:
                why.append('derived values pasted, not live formulas: ' + ', '.join(pasted[:4]))
            (bad.append(f'slide {c["slide"]}: ' + '; '.join(why)) if why else ok.append(c['slide']))
        if not chs:
            bad.append('no charts')
        return F('; '.join(bad[:6])) if bad else P(f'embedded workbooks of slides {ok} list source pages and units; every value not printed '
                                                   'in the material is a live formula')
    _safe(R, 'D07b', d07b)

    # ---- D08 (fail-only) plotted values printed in the material (print rounding allowed) / answer key / live formula
    def d08():
        iss, nv, nc = L.plotted_value_issues(pp, L.material(inp), L.number_set(json.dumps(ctx.get('answer') or {}, ensure_ascii=False)),
                                             print_rounding=True)
        if not nc:
            return F('no native charts')
        return F('; '.join(iss[:6])) if iss else None
    _safe(R, 'D08', d08)

    # ---- D09 (fail-only) causal diagram: >=6 nodes + connectors
    def d09():
        best = (0, 0, None)
        for i in range(n):
            sp = deck.shape_boxes(i)
            nodes = [k for k, v in sp.items() if v['kind'] == 'sp' and v['text'] and v['ph'] is None]
            cx = len(deck.connectors(i))
            if (cx, len(nodes)) > best[:2]:
                best = (cx, len(nodes), i + 1)
            if cx >= 1 and len(nodes) >= 6:
                return None  # structure present; layers & correctness by reviewer
        return F(f'no slide with >=6 native text nodes and connector lines; best (connectors, nodes, slide)={best}')
    _safe(R, 'D09', d09)

    # ---- D10 (fail-only) >=3 pictures
    def d10():
        pics = sum(len(deck.pictures(i)) for i in range(n))
        return F(f'only {pics} raster picture(s) in deck') if pics < 3 else None
    _safe(R, 'D10', d10)

    # ---- D11 evidence-index page sampling (numbers in claim must appear on cited PDF page)
    def d11():
        h, rows = U.read_csv(out / 'evidence-index.csv')
        cf = U.find_col(h, ('source', 'file'), ('file',), ('source',))
        cp = U.find_col(h, ('pdf', 'page'), ('pdf',))
        cc = U.find_col(h, ('claim',), ('fact',))
        ctr = U.find_col(h, ('transform',))
        if None in (cf, cp, cc):
            return F(f'evidence-index.csv lacks source/pdf page/claim columns: {h}')
        cache = {}
        elig = []
        for r in rows:
            if max(cf, cp, cc) >= len(r):
                continue
            if ctr is not None and ctr < len(r) and re.search(r'recalc|convers|comput|calc|derived|sum|arithm', r[ctr], re.I):
                continue
            nums = {x.replace(',', '') for x in re.findall(r'\d[\d,]*(?:\.\d+)?', r[cc]) if len(x.replace(',', '')) >= 2}
            pg = re.findall(r'\d+', r[cp])
            if nums and pg:
                elig.append((r, nums, int(pg[0])))
        if len(elig) < 5:
            return F(f'only {len(elig)} evidence-index rows carry a quoted number with a PDF page (need >=5 to sample)')
        rnd = random.Random(20261024)
        sample = rnd.sample(elig, min(10, len(elig)))
        okc, notes = 0, []
        names = [x.name for x in inp.iterdir() if x.is_file()] if inp.is_dir() else []
        for r, nums, pg in sample:
            fn = L.resolve_input_file(r[cf], names) or Path(r[cf].strip().replace('input/', '')).name
            src = inp / fn
            if not src.exists():
                notes.append(f'{r[cf][:40]}: not an input file')
                continue
            if fn not in cache:
                if src.suffix.lower() == '.pdf':
                    cache[fn] = U.pdf_pages_text(src) or []
                else:
                    cache[fn] = [re.sub(r'<[^>]+>', ' ', src.read_text(encoding='utf-8', errors='replace'))]
            pages = cache[fn]
            text = pages[pg - 1] if src.suffix.lower() == '.pdf' and 1 <= pg <= len(pages) else (pages[0] if pages and src.suffix.lower() != '.pdf' else '')
            text = text.replace(',', '')
            hit = sum(1 for x in nums if x in text)
            if hit >= max(1, (len(nums) + 1) // 2):
                okc += 1
            else:
                notes.append(f'{fn} p{pg}: {sorted(nums)[:4]} not found')
        need = 9 if len(sample) == 10 else int(0.9 * len(sample) + 0.999)
        d = f'{okc}/{len(sample)} sampled numeric rows verified on cited PDF page; ' + '; '.join(notes[:4])
        return P(d) if okc >= need else F(d)
    _safe(R, 'D11', d11)

    # ---- D06 (fail-only): events.csv sentences vs script.md and the narration audio
    def d06():
        h, rows = U.read_csv(out / 'events.csv')
        ct, cs = U.find_col(h, ('time',)), U.find_col(h, ('sentence',), ('spoken',), ('text',))
        if ct is None or cs is None or not rows:
            return F(f'events.csv lacks time/sentence columns or rows: {h}')
        wtok = lambda t: re.findall(r"[a-z0-9]+", t.lower())
        sw = wtok(U.clean_spoken(stext))
        sj = ' ' + ' '.join(sw) + ' '
        dur = max([d for _, _, d in narr if d] or [0])
        env = _speech_env()
        bad, pos, prev_t = [], [], -1.0
        for r in rows:
            try:
                t = float(re.findall(r'-?\d+(?:\.\d+)?', r[ct])[0])
            except Exception:
                bad.append(f'unparsable time {r[ct] if ct < len(r) else ""}')
                continue
            sent = ' '.join(wtok(r[cs] if cs < len(r) else ''))
            k = sj.find(' ' + sent + ' ') if sent else -1
            if k < 0:
                bad.append(f'sentence not verbatim in script.md: "{(r[cs] if cs < len(r) else "")[:50]}"')
            else:
                pos.append((t, k))
            if t <= prev_t:
                bad.append(f'bookmark times not increasing at {t}')
            prev_t = t
            if dur and not 0 <= t <= dur:
                bad.append(f'time {t}s outside narration (0-{dur:.1f}s)')
            elif env is not None and not env(t - 0.5, t + 1.0):
                bad.append(f'no speech in the narration audio within {t - 0.5:.2f}-{t + 1.0:.2f}s')
        if [k for _, k in sorted(pos)] != sorted(k for _, k in pos):
            bad.append('sentence order in script.md differs from bookmark time order')
        return F('; '.join(bad[:6])) if bad else None

    def _speech_env():
        """-> fn(t0, t1) True if the narration has speech energy in [t0, t1] (frame RMS within 30 dB of the peak)."""
        import numpy as np
        for i, m, d in narr:
            if m['linked'] or not m['target'] or m['target'] not in deck.names:
                continue
            f = tmp / ('narr_' + m['target'].replace('/', '_'))
            f.write_bytes(deck.z.read(m['target']))
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(f), '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                                 capture_output=True, timeout=120).stdout
            x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            if not len(x):
                return None
            fr = 800  # 50 ms
            nfr = len(x) // fr
            if not nfr:
                return None
            rms = np.sqrt(np.mean(x[:nfr * fr].reshape(nfr, fr) ** 2, axis=1) + 1e-12)
            db = 20 * np.log10(rms)
            voiced = db > max(db.max() - 30, -50)
            return lambda t0, t1: bool(voiced[max(0, int(t0 / 0.05)):max(0, int(t1 / 0.05)) + 1].any())
        return None
    _safe(R, 'D06', d06)

    # ---- F01-F06: sampled slides = the 6 slides with most numbers (slide text + notes), fixed here; fail-only trace
    def fid():
        cnt = [(len(L.slide_numbers(L.slide_text(lpkg, i) + '\n' + L.notes_text(lpkg, i))), i + 1) for i in range(n)]
        rank = [s_ for c_, s_ in sorted(cnt, key=lambda x: (-x[0], x[1]))]
        groups = {f'F0{k}': [rank[k - 1]] if k <= len(rank) else [] for k in range(1, 7)}
        for iid, sl in groups.items():
            it = next((x for x in ctx.get('items') or [] if x['id'] == iid), None)
            if it is not None and sl:
                it['verify'] = (it.get('verify') or '') + f' [sampled slide fixed by checks.py: slide {sl[0]}]'
        return L.fidelity(ctx, pp, groups, out / 'evidence-index.csv')
    try:
        R.update(fid())
    except Exception as e:
        for k in range(1, 7):
            R[f'F0{k}'] = F(f'check error: {type(e).__name__}: {e}')
    return R


def postprocess(res, ctx):
    items = ctx['items']
    if STATE.get('missing') or STATE.get('deck') is None:
        why = f"GATE-W: missing {STATE.get('missing')} / pptx parse error {STATE.get('parse_error')}"
        for i in items:
            res[i['id']] = {'verdict': 'fail', 'detail': why, 'source': 'gate'}
        res['_gate'] = {'verdict': 'fail', 'detail': why}
        return res
    iss = STATE.get('integrity') or []
    if iss:
        why = 'GATE-P (static package integrity, approximates PowerPoint repair prompt): ' + '; '.join(iss[:6])
        for i in items:
            if i['group'] == 'G6':
                res[i['id']] = {'verdict': 'fail', 'detail': why, 'source': 'gate'}
        res['_gate_p'] = {'verdict': 'fail', 'detail': why}
    return res
