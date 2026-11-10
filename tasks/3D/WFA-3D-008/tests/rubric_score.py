# -*- coding: utf-8 -*-
"""WorkflowArena CDC 扩题通用评分器（Harbor verifier）。

流程：
1. 读 /tests/rubric.json 中的判定列表（键名 criteria/judgments/items/decisions 任一）。
2. 若 /tests/checks.py 存在，调用 run(ctx) -> {item_id: {"verdict": "pass"|"fail"|"na", "detail": str}}，
   这些判定为确定性测量结果，不再交给评审模型。
3. 其余判定连同证据（产物清单、文本内容、媒体探测、抽帧/页面缩略图、.blend 场景摘要）
   分批交给多模态评审模型逐条判 pass/fail/na。
4. reward = Σ(weight × pass) / Σ(weight，排除 na)。可选 checks.postprocess(results, ctx) 处理组级门槛。

环境变量（便于本地冒烟测试）：WS_OUT / WS_TESTS / WS_LOG / WS_INSTR 覆盖默认路径；
JUDGE_OFFLINE=1 时不调用模型，未被 checks 覆盖的判定记为 ungraded（按未通过计）。
"""
import glob, json, os, pathlib, re, shutil, subprocess, sys, tempfile, traceback

OUT = pathlib.Path(os.environ.get('WS_OUT', '/workspace/output'))
TEST = pathlib.Path(os.environ.get('WS_TESTS', '/tests'))
LOG = pathlib.Path(os.environ.get('WS_LOG', '/logs/verifier'))
INSTR = pathlib.Path(os.environ.get('WS_INSTR', '/workspace/instruction.md'))
INPUT = pathlib.Path(os.environ.get('WS_INPUT', '/workspace/input'))
OFFLINE = os.environ.get('JUDGE_OFFLINE') == '1'
LOG.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(TEST))
TMP = pathlib.Path(tempfile.mkdtemp(prefix='wsv_'))
TEXT_EXT = {'.json', '.csv', '.tsv', '.md', '.txt', '.srt', '.vtt', '.edl', '.xml', '.otio', '.py', '.yaml', '.yml', '.html'}
VID_EXT = {'.mp4', '.mov', '.mkv', '.webm', '.avi'}
AUD_EXT = {'.wav', '.flac', '.mp3', '.m4a', '.aac'}
BATCH = int(os.environ.get('JUDGE_BATCH', '10'))
EVID_CAP = 300000  # v0.2: was 90000 (later files such as script.md / qa.md were cut)
TEXT_CAP = 40000
ANSWER_CAP = 120000  # v0.2: was 20000 (cdc-d-x05 key is 72k)


def result(x):
    (LOG / 'reward.json').write_text(json.dumps(x, ensure_ascii=False, indent=2), encoding='utf-8')
    (LOG / 'reward.txt').write_text(str(x.get('reward', 0)))
    print(json.dumps({k: x[k] for k in x if k != 'items'}, ensure_ascii=False))


def sh(cmd, timeout=300):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception as e:
        return f'<error {e}>'


def load_items():
    r = json.loads((TEST / 'rubric.json').read_text(encoding='utf-8'))
    for k in ('items', 'criteria', 'judgments', 'decisions'):
        v = r.get(k)
        if isinstance(v, list) and v and isinstance(v[0], dict) and 'criterion_zh' in v[0]:
            return r, k, v
    cands = [(len(v), k, v) for k, v in r.items()
             if isinstance(v, list) and v and isinstance(v[0], dict) and 'criterion_zh' in v[0] and 'tier' in v[0]]
    if cands:
        _, k, v = max(cands, key=lambda x: x[0])
        return r, k, v
    raise ValueError('rubric.json: no criteria list')


def xlsx_summary(p):
    """不依赖 openpyxl：从 xlsx zip 读工作表名、公式数与前若干公式。"""
    import zipfile
    out = {}
    try:
        z = zipfile.ZipFile(str(p))
        wb = z.read('xl/workbook.xml').decode('utf-8', 'replace') if 'xl/workbook.xml' in z.namelist() else ''
        out['sheets'] = re.findall(r'<sheet [^>]*name="([^"]+)"', wb)
        fs = []
        for n in sorted(x for x in z.namelist() if x.startswith('xl/worksheets/sheet') and x.endswith('.xml')):
            x = z.read(n).decode('utf-8', 'replace')
            for cell, f in re.findall(r'<c r="([A-Z]+\d+)"[^>]*>\s*<f[^>]*>([^<]*)</f>', x):
                fs.append(f'{n.rsplit("/", 1)[-1]}!{cell}: ={f}')
        out['formula_cells'] = len(fs)
        out['formulas_sample'] = fs[:60]
        # v0.2: cached cell values (shared strings resolved), first 400 cells per sheet
        ss = []
        if 'xl/sharedStrings.xml' in z.namelist():
            sx = z.read('xl/sharedStrings.xml').decode('utf-8', 'replace')
            ss = [re.sub(r'<[^>]+>', '', si) for si in re.findall(r'<si>(.*?)</si>', sx, re.S)]
        vals = {}
        for n in sorted(x for x in z.namelist() if x.startswith('xl/worksheets/sheet') and x.endswith('.xml')):
            x = z.read(n).decode('utf-8', 'replace')
            cells = []
            for attrs, body in re.findall(r'<c ([^>]*)>(.*?)</c>', x, re.S):
                ref = re.search(r'r="([A-Z]+\d+)"', attrs)
                v = re.search(r'<v>([^<]*)</v>', body)
                if not ref:
                    continue
                if 't="s"' in attrs and v:
                    val = ss[int(v.group(1))] if v.group(1).isdigit() and int(v.group(1)) < len(ss) else v.group(1)
                elif 't="inlineStr"' in attrs:
                    val = re.sub(r'<[^>]+>', '', body)
                else:
                    val = v.group(1) if v else None
                if val not in (None, ''):
                    cells.append(f'{ref.group(1)}={val}')
                if len(cells) >= 400:
                    break
            vals[n.rsplit('/', 1)[-1]] = cells
        out['cell_values'] = vals
    except Exception as e:
        out['error'] = str(e)
    return out


def pptx_xml_summary(p):
    """原生图表内嵌工作簿、动画/计时、切换、媒体与书签的结构摘要（解析 XML）。"""
    import zipfile
    out = {'slides': []}
    try:
        z = zipfile.ZipFile(str(p))
        names = z.namelist()
        out['embedded_workbooks'] = [n for n in names if n.startswith('ppt/embeddings/') and n.endswith(('.xlsx', '.xls'))]
        out['charts'] = [n for n in names if re.match(r'ppt/charts/chart\d+\.xml$', n)]
        out['media'] = [n for n in names if n.startswith('ppt/media/') and n.lower().endswith(('.mp4', '.mov', '.m4a', '.mp3', '.wav'))]
        pres = z.read('ppt/presentation.xml').decode('utf-8', 'replace')
        out['show_loop_or_kiosk'] = bool(re.search(r'<p:showPr[^>]*loop="1"|<p:kiosk', z.read('ppt/presProps.xml').decode('utf-8', 'replace'))) if 'ppt/presProps.xml' in names else None
        for n in sorted((x for x in names if re.match(r'ppt/slides/slide\d+\.xml$', x)), key=lambda s: int(re.findall(r'\d+', s)[-1])):
            x = z.read(n).decode('utf-8', 'replace')
            out['slides'].append({'slide': int(re.findall(r'\d+', n)[-1]),
                                  'transition': (re.search(r'<p:transition[^>]*>', x) or [None])[0],
                                  'advAfter_ms': (re.findall(r'advTm="(\d+)"', x) or [None])[0],
                                  'morph': 'morph' in x.lower(),
                                  'anim_effects': len(re.findall(r'<p:par>', x)),
                                  'triggers': len(re.findall(r'<p:tgtEl>|evt="onClick"', x)),
                                  'bookmarks': len(re.findall(r'bmk|<p14:bmk', x)),
                                  'media_trim': re.findall(r'<p14:trim[^>]*/>', x),
                                  'video_or_audio': len(re.findall(r'<a:videoFile|<a:audioFile|<p14:media', x))})
        for wbn in out['embedded_workbooks'][:12]:
            tmp = TMP / ('emb_' + wbn.rsplit('/', 1)[-1])
            tmp.write_bytes(z.read(wbn))
            out.setdefault('embedded_workbook_summary', {})[wbn] = xlsx_summary(tmp)
    except Exception as e:
        out['error'] = str(e)
    return out


# ---------------- evidence ----------------
def probe(p):
    o = sh(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(p)], 60)
    try:
        j = json.loads(o)
    except Exception:
        return {'error': o[:300]}
    s = [{k: st.get(k) for k in ('codec_type', 'codec_name', 'width', 'height', 'sample_aspect_ratio', 'pix_fmt',
                                  'r_frame_rate', 'nb_frames', 'sample_rate', 'channels', 'duration')} for st in j.get('streams', [])]
    return {'streams': s, 'duration': j.get('format', {}).get('duration')}


def contact_sheet(video, n=12, name='v'):
    """n 帧均匀抽样拼成 4 列缩略图，左上角带时间戳。"""
    try:
        d = float(json.loads(sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(video)]))['format']['duration'])
    except Exception:
        return None
    out = TMP / f'{name}_sheet.jpg'
    fps = n / max(d, 0.1)
    sh(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-vf',
        f"fps={fps:.5f},scale=320:-2,drawtext=text='%{{pts\\:hms}}':x=4:y=4:fontcolor=yellow:fontsize=14:box=1:boxcolor=black@0.6,tile=4x{(n + 3)//4}",
        '-frames:v', '1', '-q:v', '4', str(out)], 240)
    if not out.exists():  # drawtext 不可用时退化
        sh(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-vf', f'fps={fps:.5f},scale=320:-2,tile=4x{(n + 3)//4}',
            '-frames:v', '1', '-q:v', '4', str(out)], 240)
    return str(out) if out.exists() else None


def loudness(p):
    o = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(p), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True, timeout=300).stderr
    m = re.search(r'Integrated loudness:\s+I:\s+(-?[\d.]+) LUFS', o)
    pk = re.search(r'True peak:\s+Peak:\s+(-?[\d.]+) dBFS', o)
    return {'integrated_LUFS': m and float(m.group(1)), 'true_peak_dBFS': pk and float(pk.group(1))}


def pdf_pages(pdf, name):
    txt = sh(['pdftotext', '-layout', str(pdf), '-'], 120)
    pages = txt.split('\f')
    imgs = []
    npg = len([p for p in pages if p.strip()]) or 1
    stem = TMP / f'{name}_pg'
    sh(['pdftoppm', '-r', '30', '-png', str(pdf), str(stem)], 240)
    pngs = sorted(glob.glob(str(stem) + '-*.png'))
    # 每 9 页拼一张
    for i in range(0, len(pngs), 9):
        out = TMP / f'{name}_pages_{i//9}.jpg'
        lst = TMP / f'{name}_{i}.txt'
        lst.write_text('\n'.join(f"file '{p}'" for p in pngs[i:i + 9]))
        sh(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-vf',
            'scale=420:240:force_original_aspect_ratio=decrease,pad=420:240:(ow-iw)/2:(oh-ih)/2:white,tile=3x3', '-frames:v', '1', str(out)])
        if out.exists():
            imgs.append(str(out))
    return pages, imgs


BLEND_PY = r'''
import bpy, json, sys
sc = bpy.context.scene
d = {"scene": sc.name, "frame_start": sc.frame_start, "frame_end": sc.frame_end, "fps": sc.render.fps,
     "resolution": [sc.render.resolution_x, sc.render.resolution_y], "engine": sc.render.engine,
     "camera": sc.camera.name if sc.camera else None,
     "markers": [[m.name, m.frame, m.camera.name if m.camera else None] for m in sc.timeline_markers],
     "objects": [], "collections": [c.name for c in bpy.data.collections],
     "sequencer": []}
for o in bpy.data.objects:
    e = {"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None,
         "loc": [round(x, 3) for x in o.matrix_world.translation], "animated": bool(o.animation_data and o.animation_data.action)}
    if o.type == "CAMERA": e["lens"] = round(o.data.lens, 2)
    if o.type == "LIGHT": e["light"] = [o.data.type, round(o.data.energy, 2), [round(c, 3) for c in o.data.color]]
    if o.type == "ARMATURE": e["bones"] = [b.name for b in o.data.bones][:60]
    if o.material_slots: e["materials"] = [s.material.name for s in o.material_slots if s.material]
    d["objects"].append(e)
if sc.sequence_editor:
    for s in sc.sequence_editor.sequences_all:
        d["sequencer"].append([s.name, s.type, s.channel, s.frame_final_start, s.frame_final_end])
print("BLENDJSON" + json.dumps(d))
'''


def blend_summary(p):
    if not shutil.which('blender'):
        return {'note': 'blender not available in verifier image'}
    f = TMP / 'blend_dump.py'
    f.write_text(BLEND_PY)
    o = sh(['blender', '-b', str(p), '--python', str(f)], 600)
    m = re.search(r'BLENDJSON(\{.*\})', o)
    return json.loads(m.group(1)) if m else {'error': o[-800:]}


def collect():
    ev, imgs = {'files': []}, []
    for p in sorted(OUT.rglob('*')):
        if not p.is_file():
            continue
        rel = str(p.relative_to(OUT))
        ext = p.suffix.lower()
        info = {'path': rel, 'bytes': p.stat().st_size}
        try:
            if ext in TEXT_EXT:
                t = p.read_text(encoding='utf-8', errors='replace')
                info['content'] = t[:TEXT_CAP] + ('…[truncated]' if len(t) > TEXT_CAP else '')
            elif ext in VID_EXT:
                info['probe'] = probe(p)
                if any(s.get('codec_type') == 'audio' for s in info['probe'].get('streams', [])):
                    info['loudness'] = loudness(p)
                if len([i for i in imgs if '_sheet' in i]) < 4:
                    c = contact_sheet(p, 12, re.sub(r'\W', '_', rel))
                    if c:
                        imgs.append(c)
            elif ext in AUD_EXT:
                info['probe'] = probe(p)
                info['loudness'] = loudness(p)
            elif ext == '.pptx':
                pdf = TMP / (p.stem + '_conv.pdf')
                sh(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', str(TMP), str(p)], 300)
                cand = TMP / (p.stem + '.pdf')
                if cand.exists():
                    cand.rename(pdf)
                try:
                    from pptx import Presentation
                    deck = Presentation(str(p))
                    sl = []
                    def _walk(shs):
                        for sp in shs:
                            yield sp
                            if getattr(sp, 'shape_type', None) is not None and 'GROUP' in str(sp.shape_type):
                                yield from _walk(sp.shapes)

                    def _chart(sp):
                        try:
                            ch = sp.chart
                            d = {'type': str(ch.chart_type), 'title': ch.chart_title.text_frame.text if ch.has_title else None,
                                 'series': []}
                            try:
                                d['categories'] = [str(c) for c in ch.plots[0].categories][:60]
                            except Exception:
                                pass
                            for pl in ch.plots:
                                for se in pl.series:
                                    d['series'].append({'name': se.name, 'values': list(se.values)[:60]})
                            for ax in ('category_axis', 'value_axis'):
                                try:
                                    a = getattr(ch, ax)
                                    d[ax + '_title'] = a.axis_title.text_frame.text if a.has_title else None
                                except Exception:
                                    pass
                            return d
                        except Exception as e:
                            return {'error': str(e)}

                    for i, s in enumerate(deck.slides, 1):
                        allsh = list(_walk(s.shapes))
                        shapes = [(sp.shape_type and str(sp.shape_type)) for sp in allsh]
                        txt = ' | '.join(sp.text_frame.text for sp in allsh if sp.has_text_frame and sp.text_frame.text)
                        tables = [[[c.text for c in r.cells] for r in sp.table.rows] for sp in allsh
                                  if getattr(sp, 'has_table', False)]
                        charts = [_chart(sp) for sp in allsh if getattr(sp, 'has_chart', False)]
                        notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ''
                        sl.append({'slide': i, 'charts': len(charts), 'tables': len(tables),
                                   'table_cells': tables, 'chart_data': charts,
                                   'pictures': shapes.count('PICTURE (13)'), 'media': sum(1 for x in shapes if x and 'MEDIA' in x),
                                   'text': txt[:3000], 'notes': notes[:2400]})
                    info['slides'] = sl
                    info['slide_size_in'] = [deck.slide_width / 914400, deck.slide_height / 914400]
                except Exception as e:
                    info['pptx_parse_error'] = str(e)
                info['structure'] = pptx_xml_summary(p)
                if pdf.exists():
                    _, im = pdf_pages(pdf, 'pptx_' + p.stem)
                    imgs.extend(im[:4])
            elif ext == '.pdf':
                pages, im = pdf_pages(p, 'pdf_' + p.stem)
                info['pages'] = len([x for x in pages if x.strip()])
                info['text'] = '\f'.join(pages)[:15000]
                if not any('pptx_' in i for i in imgs):
                    imgs.extend(im[:4])
            elif ext in ('.xlsx', '.xls', '.ods'):
                sh(['soffice', '--headless', '--convert-to', 'csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,-1',
                    '--outdir', str(TMP), str(p)], 300)
                info['sheets_csv'] = {c.name: c.read_text(errors='replace')[:6000] for c in TMP.glob(p.stem + '*.csv')}
                if ext == '.xlsx':
                    info['workbook'] = xlsx_summary(p)
            elif ext == '.blend':
                info['blend'] = blend_summary(p)
            elif ext in ('.png', '.jpg', '.jpeg') and len(imgs) < 8:
                imgs.append(str(p))
        except Exception as e:
            info['error'] = str(e)
        ev['files'].append(info)
    return ev, imgs[:8]


# ---------------- judge ----------------
def judge_batch(items, instruction, evidence, answer, imgs):
    from judge import judge
    spec = [{'id': i['id'], 'tier': i.get('tier'), 'criterion_en': i.get('criterion_en', ''), 'criterion_zh': i.get('criterion_zh', ''),
             'verify': i.get('verify', ''), 'conditional_na_allowed': bool(re.search(r'条件项|N/A|不计入|未.{0,8}视为通过|if (it is )?(cited|given|mentioned)', json.dumps(i, ensure_ascii=False), re.I))}
            for i in items]
    ev = json.dumps(evidence, ensure_ascii=False)
    if len(ev) > EVID_CAP:
        ev = ev[:EVID_CAP] + '…[evidence truncated]'
    prompt = ('You are a strict, fair grader for a hard creative-production benchmark task. Judge EACH rubric item below '
              'independently as "pass", "fail", or "na" ("na" ONLY if the item is explicitly conditional and its condition did not occur). '
              'Use only the evidence (extracted text, probes, scene dumps, attached contact sheets/page renders). If an item needs a '
              'measurement that the evidence does not support, decide from the closest available evidence and say so; never pass '
              'something because the solver merely claims it. Hidden reference answers are provided for you only.\n'
              'Return ONLY JSON: {"<id>": {"verdict": "pass|fail|na", "reason": "<=30 words"}, ...}\n\n'
              f'TASK INSTRUCTION:\n{instruction}\n\nHIDDEN REFERENCE (answer key):\n{json.dumps(answer, ensure_ascii=False)[:ANSWER_CAP]}\n\n'
              f'RUBRIC ITEMS:\n{json.dumps(spec, ensure_ascii=False)}\n\nEVIDENCE FROM /workspace/output:\n{ev}')
    return judge(prompt, imgs)


def main():
    rub, key, items = load_items()
    produced = [p for p in OUT.rglob('*') if p.is_file()] if OUT.exists() else []
    if not produced:
        return result({'reward': 0, 'resolved': False, 'failure': 'no files in output/'})
    ctx = {'out': OUT, 'tests': TEST, 'input': INPUT, 'tmp': TMP, 'rubric': rub, 'items': items}
    ak = TEST / 'answer-key.json'
    answer = json.loads(ak.read_text(encoding='utf-8')) if ak.exists() else {}
    ctx['answer'] = answer
    res = {}
    checks = None
    if (TEST / 'checks.py').exists():
        import importlib
        checks = importlib.import_module('checks')
        try:
            for k, v in (checks.run(ctx) or {}).items():
                res[k] = dict(v, source='checks')
        except Exception:
            res['_checks_error'] = {'verdict': 'error', 'detail': traceback.format_exc()[-1500:]}
    if '_checks_error' in res:
        # v0.2: a crashing checks.py must not silently hand deterministic items to the judge; mark them as grading
        # errors so that test.sh refuses to write a reward
        for i in items:
            res.setdefault(i['id'], {'verdict': 'error', 'source': 'checks', 'reason': 'checks.py crashed'})
    for i in items:
        # v0.2: weight-0 (informational) items are never sent to the judge
        if i['id'] not in res and not float(i.get('weight', 1) or 0):
            res[i['id']] = {'verdict': 'na', 'source': 'rubric', 'reason': 'informational item (weight 0)'}
    todo = [i for i in items if i['id'] not in res]
    evidence, imgs = ({}, [])
    if todo:
        evidence, imgs = collect()
        if OFFLINE:
            for i in todo:
                res[i['id']] = {'verdict': 'ungraded', 'source': 'offline'}
        else:
            instruction = INSTR.read_text(encoding='utf-8') if INSTR.exists() else ''
            for s in range(0, len(todo), BATCH):
                chunk = todo[s:s + BATCH]
                try:
                    out = judge_batch(chunk, instruction, evidence, answer, imgs)
                except Exception as e:
                    out = {i['id']: {'verdict': 'ungraded', 'reason': f'judge error: {e}'} for i in chunk}
                for i in chunk:
                    v = out.get(i['id']) or {'verdict': 'ungraded', 'reason': 'missing in judge output'}
                    v['verdict'] = str(v.get('verdict', 'ungraded')).lower()
                    res[i['id']] = dict(v, source='judge')
    if checks is not None and hasattr(checks, 'postprocess'):
        try:
            res = checks.postprocess(res, ctx) or res
        except Exception:
            res['_postprocess_error'] = {'verdict': 'error', 'detail': traceback.format_exc()[-1500:]}
    num = den = 0.0
    per = []
    for i in items:
        w = float(i.get('weight', 1) or 0)
        v = res.get(i['id'], {}).get('verdict', 'ungraded')
        if v == 'na':
            per.append(dict(id=i['id'], tier=i.get('tier'), weight=w, **res.get(i['id'], {})))
            continue
        den += w
        if v == 'pass':
            num += w
        per.append(dict(id=i['id'], tier=i.get('tier'), weight=w, **res.get(i['id'], {'verdict': v})))
    reward = round(num / den, 4) if den else 0.0
    tiers = {}
    for p in per:
        t = tiers.setdefault(p['tier'], [0, 0])
        if p.get('verdict') != 'na':
            t[1] += p['weight']
            t[0] += p['weight'] if p.get('verdict') == 'pass' else 0
    ung = sum(1 for p in per if p.get('verdict') not in ('pass', 'fail', 'na'))
    ung += int('_postprocess_error' in res)  # v0.2: a crashed postprocess (group gates) is incomplete grading
    from acceptance import evaluate_acceptance
    acceptance = evaluate_acceptance(rub, res, num, den, ung)
    result({'reward': reward, 'score_100': round(reward * 100, 2), **acceptance,
            'tier_pass_weight': {k: [round(a, 3), round(b, 3)] for k, (a, b) in tiers.items()},
            'n_items': len(items), 'n_checks': sum(1 for p in per if p.get('source') == 'checks'),
            'n_ungraded': ung, 'items': per, 'aux': {k: v for k, v in res.items() if k.startswith('_')}})


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        result({'reward': 0, 'resolved': False, 'grader_error': str(e), 'trace': traceback.format_exc()[-2000:]})
        raise
