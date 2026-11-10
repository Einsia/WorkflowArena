# WFA-CDN-014 隐藏评分细则（REVIEWER-ONLY，由 rubric.json 生成）

每项只判是/否，部分满足即判否。组得分 = 组权重 ×（通过项数 / 该组项数），总分为各组之和（满分 100）。求解者自述的 playback-check.md 不能单独作为证据。由 checks.py 机测的条目见 tests/checks.py 文件头，其余由 LLM 评审依据 rubric_score.py 收集的证据判定（v2026-10-25）。

## 门槛

- **GATE0**（整题）output/ 中 presentation.pptx、slides.pdf、script.md、calculations.xlsx、event-clip.mp4、evidence-index.csv、playback-check.md 七件齐全，且 pptx 能被 python-pptx 读出幻灯片。 — 不过 ⇒ 全部判定记否，验收失败。
- **GATE1**（G6 组级）包结构完整性代理（Linux 评测无 PowerPoint）：zip 完整、内容类型齐全、内部关系目标存在、XML 良构、python-pptx 可打开，且无非超链接外部关系。 — 不过 ⇒ G6 记 0；V07 记否；验收失败（连续分照常报告）。
- **GATE2**（整题）作弊/违规：访问评测隐藏文件、联网取材、以材料以外来源的数据或影像替换材料内容。（自动评测未实现，仅供人工审查） — 不过 ⇒ 整题 0，验收失败。

## 分组

### G1 叙事与结构（10 分，7 项）

- **N01** [base · 预期 0.92] 9–11 页、16:9，含标题页与结束页，无空分隔页。  
  验证：python-pptx: slide count, slide size ratio; every slide has >=1 fact-bearing element besides title.
- **N02** [base · 预期 0.80] 每页标题都是完整论断（含谓语的判断句），不是话题标签。  
  验证：Reviewer reads titles; any noun-phrase title => NO.
- **N03** [mid · 预期 0.55] 叙事顺序为：事件与后果 → 设计阶段错误 → 物理失效机理 → 现场损伤被观察与解读的过程 → 可中断环节评估 → 回答与边界；不缺环节、不跳回、不重复。  
  验证：Judge maps each slide to a stage; any stage missing, out of order or repeated => NO.
- **N04** [mid · 预期 0.45 · 关键] 结束页用一句话直接回答问题，并列出至少两条证据不支持的结论（须有材料依据，不得新增材料外事实）。  
  验证：Reviewer; both 'not supported' items must be backed by the report.
- **N05** [mid · 预期 0.50] script.md 按 130–150 词/分钟加声明停顿与短片时长计算的时长区间与 11–13 分钟有交集；逐页声明时长之和落在该区间 ±10% 内；每页备注文字与讲稿该页一致。  
  验证：checks.py n05(): word count of script sections (markup stripped), ffprobe clip duration, 'pause N s' marks; per-slide 'Duration' parse; notes vs script token overlap >=0.9 per slide.
- **N06** [mid · 预期 0.45] 为非专家听众解释以下全部术语：节点/界面剪力（冷缝处的水平剪力传递）、需求/容量比（D/C）、后张拉杆的张拉与卸张、冗余（单一传力路径）、probable cause 与 contributing 的区别。  
  验证：Reviewer; any one unexplained => NO.
- **N07** [gate · 预期 0.20 · 关键] 全篇以一致视觉编码区分“调查机构确立的事实 / 机构分析判断 / 制作者推断”，且无任何一处把制作者推断或当事方说法标为机构结论。  
  验证：Reviewer audits every coded element against report wording.

### G2 视觉设计与可读性（10 分，8 项）

- **V01** [base · 预期 0.75] 所有正文 ≥20 pt（按继承字号与自动缩放后的实际字号计；图注/出处行除外）。  
  验证：checks.py: run size resolved run -> paragraph -> shape lstStyle -> layout/master placeholder -> master txStyles -> presentation defaultTextStyle, times normAutofit fontScale; body = body/object placeholders + each slide's main text box (>=20 words, not a source/caption line).
- **V02** [base · 预期 0.85] 图注、出处行及其他所有文字 ≥12 pt（按继承字号与自动缩放后的实际字号计）。  
  验证：checks.py: same size resolution as V01, every text run of every text shape.
- **V03** [base · 预期 0.90] 任一页要点 ≤6 条。  
  验证：checks.py: bullet paragraphs (buChar/buAutoNum or body-placeholder default) summed over all non-title text frames of each slide.
- **V04** [mid · 预期 0.50] 每个原生图表坐标轴有标题与单位（kips、比值等），多系列有图例，数据标签与坐标轴刻度标签字号 ≥12 pt（PowerPoint 渲染为准）。  
  验证：checks.py v04(): chart XML: every non-deleted axis has title text, value-axis title has a unit token; multi-series charts have a legend; tick and shown data-label sizes from axis/dLbls txPr, else chartSpace txPr, else 10 pt (PowerPoint default) must be >=12 pt.
- **V05** [mid · 预期 0.50] 报告原图裁切到相关图块并保留图例/图号，原生标注准确指向所述部位（如 11/12 节点、裂缝位置）。  
  验证：Reviewer compares crop with source page.
- **V06** [mid · 预期 0.45] 静态渲染中无文字溢出或裁切，无对象超出页面，常显对象之间无重叠；带进入动画或触发效果的形状不参与重叠判定。  
  验证：checks.py fails shapes beyond the slide and overlapping always-visible text shapes (fail-only); judge checks text overflow/clipping on the rendered pages.
- **V07** [gate · 预期 0.18] 任何触发说明框、机理形状或标注显示时，不遮挡时间线条目（触发形状）、连接线、图表/表格框、视频或常显文字；不同触发器的说明框可共用同一位置。  
  验证：checks.py v07(): bbox of every animated target vs trigger shapes, chart/table frames, video, always-visible text shapes (overlap >0.1 in) and connector paths not glued to the target.
- **V08** [base · 预期 0.80] 全篇英文语法、拼写、单位与时间写法正确一致（kips、in²、ft、a.m./p.m. 或 24 小时制统一）。  
  验证：Reviewer + spell check.

### G3 材料覆盖与隐藏考点（26 分，11 项）

- **A01** [base · 预期 0.80] 交代事件基本事实：日期与约时刻、地点（道路）、主跨长度与下落高度、被压车辆数，均与报告一致。  
  验证：answer-key K-BASIC.
- **A02** [base · 预期 0.70] 伤亡计数按表 1 分人群、分严重程度给出且与摘要一致（死亡 6 = 工人 1 + 车内 5），不把送医人数当作受伤人数。  
  验证：answer-key K-INJ.
- **A03** [mid · 预期 0.45 · 关键] 按报告原文区分 probable cause、contributing 与 contributing to the severity（封路/停工），不改写成追责措辞、不把严重度因素说成坍塌原因。  
  验证：answer-key K-PC.
- **A04** [base · 预期 0.75] 至少引用两条安全建议，写明编号与对象机构，且至少一条与所述可中断环节对应。  
  验证：answer-key K-REC.
- **A05** [mid · 预期 0.50] 时间线关键节点日期/时刻全部正确：2/24 开裂声与 11/12 处裂缝、3/10 落位后卸张、3/13“非安全问题”回复与再张拉建议、3/15 上午会议、坍塌。  
  验证：answer-key K-TIMELINE; any wrong date/time => NO.
- **A06** [mid · 预期 0.40] 说明报告排除的因素：混凝土与钢材材料不是因素、千斤顶工作正常（Findings 2、3）。  
  验证：answer-key K-MAT.
- **H01** [gate · 预期 0.50 · 关键] [隐藏·条件项] 若简报给出节点 1/2 界面剪力需求低估的百分比：要么给出正文的 49% 并注明出自报告正文（p.78/PDF 97），要么给出按表 6 模型 1（2,481）与表 F-1（1,368 kips）算得的约 45%（模型 1–4 为 44.7–46.3%）并注明这些出处；两者并列并指出不一致亦通过。把 49% 说成可由表 6/F-1 复现、或给出百分比而无出处判否。未给出该百分比视为通过。  
  验证：answer-key H01-49pct; deck text/notes/calculations.xlsx. The instruction only requires page traceability, not detection of the internal discrepancy.
- **H02** [gate · 预期 0.15 · 关键] [隐藏] 用表 F-3/F-4 或 p.72 的口径量化 11/12 节点容量高估（约 20–22%）；若出现“约 25%”，指明其为 Pc 中 1.25 荷载系数的效应而非容量比；不把两数当同一量。  
  验证：answer-key H02-20vs25.
- **H03** [gate · 预期 0.20 · 关键] [隐藏] 表述坍塌发生在再张拉进行过程中（并引千斤顶活塞伸出/正在张拉等物证）；若引用 p.38“紧随其后”的说法须指出与他处不一致；任何地方不说再张拉已完成。  
  验证：answer-key H03-timing.
- **H04** [gate · 预期 0.20] [隐藏] 卸张后裂缝变化的两种表述分别归属：设计方内部邮件“略有增长” vs 调查人员“明显发展”；不把“略有增长”当作已确立事实。  
  验证：answer-key H04-crack-growth.
- **H05** [gate · 预期 0.15 · 关键] [隐藏] 解释为何 D/C 最高的是节点 1/2（2.15）而失效发生在 11/12（1.62）：至少给出报告所列两条原因（24 vs 42 英寸隔板、四根竖向套管/空洞、杆件 11 比杆件 2 浅）。  
  验证：answer-key H05-why-11-12.

### G4 逐页忠实度（8 分，8 项）

- **F01** [base · 预期 0.85] 第 1 页（标题页，含备注）没有任何与 answer-key 及 evidence-index.csv 所列页码不符或无出处的内容；出现一处即判否。  
  验证：Judge checks slide text, table cells, chart data and notes against the answer key and evidence-index.csv (the judge has no copy of the report).
- **F02** [mid · 预期 0.50] 第 2 页（文字、图表数据、标注、触发面板与备注）没有任何与 answer-key 相矛盾、或在 evidence-index.csv 中无出处的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Judge checks slide text, table cells, chart data and notes against the answer key and evidence-index.csv (the judge has no copy of the report).
- **F03** [mid · 预期 0.50] 第 3 页（文字、图表数据、标注、触发面板与备注）没有任何与 answer-key 相矛盾、或在 evidence-index.csv 中无出处的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Judge checks slide text, table cells, chart data and notes against the answer key and evidence-index.csv (the judge has no copy of the report).
- **F04** [mid · 预期 0.50] 第 4 页（文字、图表数据、标注、触发面板与备注）没有任何与 answer-key 相矛盾、或在 evidence-index.csv 中无出处的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Judge checks slide text, table cells, chart data and notes against the answer key and evidence-index.csv (the judge has no copy of the report).
- **F05** [mid · 预期 0.50] 第 5 页（文字、图表数据、标注、触发面板与备注）没有任何与 answer-key 相矛盾、或在 evidence-index.csv 中无出处的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Judge checks slide text, table cells, chart data and notes against the answer key and evidence-index.csv (the judge has no copy of the report).
- **F06** [mid · 预期 0.50] 第 6 页（文字、图表数据、标注、触发面板与备注）没有任何与 answer-key 相矛盾、或在 evidence-index.csv 中无出处的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Judge checks slide text, table cells, chart data and notes against the answer key and evidence-index.csv (the judge has no copy of the report).
- **F07** [mid · 预期 0.50] 第 7 页（文字、图表数据、标注、触发面板与备注）没有任何与 answer-key 相矛盾、或在 evidence-index.csv 中无出处的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Judge checks slide text, table cells, chart data and notes against the answer key and evidence-index.csv (the judge has no copy of the report).
- **F08** [mid · 预期 0.40] 第 8 页至最后一页（文字、图表数据、标注与备注）没有任何与 answer-key 及 evidence-index.csv 所列页码不符或无出处的内容；出现一处即判否。  
  验证：Judge checks slide text, table cells, chart data and notes against the answer key and evidence-index.csv (the judge has no copy of the report).

### G5 失效机理推理与计算（26 分，8 项）

- **R01** [gate · 预期 0.30 · 关键] 失效机理链环节齐全且顺序正确：需求低估 → 容量高估 → 11/12 界面配筋不足与空洞 → 拆模起开裂并持续发展 → 卸张加剧损伤 → 再张拉 → 节点界面剪切失效 → 单一传力路径丧失、整跨坍塌；每环按“机构事实/机构分析/制作者推断”编码，无材料外环节。  
  验证：Judge vs answer-key K-MECH.
- **R02** [gate · 预期 0.30 · 关键] 不把再张拉（或千斤顶操作）说成 probable cause 或“没有再张拉就不会坍塌”；按报告将其定位为未经同行评审的设计变更/荷载操作（Finding 21），根因为设计计算错误。  
  验证：Reviewer vs K-PC/K-MAT/K-MECH.
- **R03** [mid · 预期 0.35] calculations.xlsx 正确算出 11/12 节点 D/C：调查方核算约 1.62（1,835/1,130，与图 31 一致）与设计方自身数值约 0.71（978/1,369），注明各自来源，均为实时公式。  
  验证：openpyxl formulas + answer-key K-DC-calc (±0.02).
- **R04** [base · 预期 0.70] 三帧时间戳间隔计算正确（0.165 s、0.264 s，共 0.429 s），并记入 calculations.xlsx。  
  验证：openpyxl + K-DASHCAM.
- **R05** [gate · 预期 0.15 · 关键] 可中断环节判定与材料一致：至少一个被材料支持为可能防止坍塌的环节（如独立同行评审核查全部节点力，Finding 18），封路/停工被正确表述为降低后果严重度而非防止结构失效，且至少一个看似防线被正确否定（如冷缝打毛也不足以提供足够容量，Finding 5）。  
  验证：Reviewer vs K-BARRIERS.
- **R06** [gate · 预期 0.25 · 关键] 不越界：不指认个人罪责，不把结论推广到材料未支持的“所有混凝土桁架桥”式普遍断言，不对报告未判定的事项（如若未卸张是否仍会坍塌）给出确定结论。  
  验证：Reviewer.
- **R07** [mid · 预期 0.30] 配筋量表述正确：设计提供 8 根 7 号筋（4.8 in²），调查方核算应另加约 13 in²，并保留报告“仅示数量级”的限定。  
  验证：answer-key K-REBAR.
- **R08** [mid · 预期 0.40] 关于坍塌历时的表述与报告一致：0.429 s 只表述为三张静图之间的间隔，不说成测得的完整坍塌历时（报告称整个事件录像不足 2 秒）。  
  验证：Reviewer vs K-DASHCAM.

### G6 原生对象、动画、媒体与交付（20 分，15 项）

- **D01** [base · 预期 0.88] slides.pdf 与 pptx 页数相同，内容对应。  
  验证：Page count + title text match.
- **D02** [base · 预期 0.85] evidence-index.csv 列齐全（页号、元素、论断、印刷页、PDF 页、图表/章节号、变换），且每页至少一行。  
  验证：csv parse.
- **D03** [base · 预期 0.85] 演讲者备注每页非空；标明 AI 协助制作与来源署名，无背书暗示。  
  验证：python-pptx notes + text search.
- **D04** [base · 预期 0.80 · 关键] ≥2 个原生图表（chart part，非图片），各有内嵌（非链接）工作簿，含所绘数值、单位表头或单位单元格及页码。  
  验证：checks.py d04(): c:externalData -> ppt/embeddings/*.xlsx; numbers present; a string cell matching page/p./PDF; a unit header/cell ('Unit', 'kips', '(kips)', 'ratio', 'D/C', 's', '%' ...).
- **D05** [gate · 预期 0.25 · 关键] 图表所绘每个数值均为报告数值（报告正文或图 31 印出的数据标签）或 calculations.xlsx 的计算结果；绘制表 6 需求值的图表须声明所用模型或统计方式；各图表嵌入工作簿包含所绘数值。  
  验证：checks.py d05(): chart caches vs numbers in pdftotext(input/report.pdf) + answer-key K-FIG31 + calculations.xlsx formula results (tolerance: 0.006 below 1.2, else min(1, 0.5%)); cache values must be present in the embedded workbook; Table 6 match requires model/maximum/envelope wording on the slide or chart title.
- **D06** [base · 预期 0.80] ≥2 幅图片为报告真实原图（从 PDF 提取或裁切，非重绘），且每幅上至少放有一个原生可编辑标注。  
  验证：checks.py d06(): pdfimages of input/report.pdf; OpenCV multi-scale normalised cross-correlation >=0.65 between each deck picture and a report image (either direction); >=1 sp/cxnSp/grpSp overlapping the picture.
- **D07** [mid · 预期 0.50 · 关键] 机理链页：原生形状 + 连到形状的连接线（cxnSp），≥6 个单击进入效果按机理顺序揭示独立形状。  
  验证：checks.py d07(): p:timing main-sequence clickEffect/entr on distinct shapes, glued connectors present; each step's text mapped to K-MECH stages (demand, capacity, interface/voids, cracking, detensioning, restressing, failure) by first-mentioned keyword; >=6 mapped steps, >=5 distinct stages, non-decreasing order. Slideshow execution is inferred from the XML (no PowerPoint on the grader).
- **D08** [gate · 预期 0.15 · 关键] 时间线页：≥5 个带日期条目各自是交互触发器（InteractiveSequences，TriggerType=OnShapeClick，TriggerShape 为该条目），揭示独立可编辑说明框；放映中逐个点击确实触发，非超链接/跳页/主序列。  
  验证：checks.py d08(): p:timing interactiveSeq with onClick trigger spid on >=5 shapes whose text has a date, each revealing (entr) a separate panel shape. Slideshow behaviour is inferred from the XML.
- **D09** [mid · 预期 0.30] 至少一个原生图表在放映中按系列或按类别逐步构建（图表动画的 ChartUnit/BuildLevel 为按系列/类别，非整体出现、非叠放图片）。  
  验证：checks.py d09(): p:bldGraphic/a:bldChart bld=series|category AND a timing effect whose spTgt targets that chart with p:graphicEl/a:chart (series/category steps).
- **D10** [mid · 预期 0.40 · 关键] event-clip.mp4 为 H.264、4–12 s、1280×720 或 1920×1080；同一媒体嵌入 pptx（ppt/media 内，非链接），并由单击启动（单击触发器、主序列单击或默认的单击播放媒体节点；不得自动播放）。  
  验证：checks.py d10(): ffprobe; zip listing + byte/duration identity; play/playFrom/togglePause command targeting the video inside an onClick interactiveSeq or a main-sequence click group without onBegin, or a p:video media node with no auto-start command.
- **D11** [gate · 预期 0.15 · 关键] 短片内容：只用报告坍塌过程静图（图 9–11），按时间顺序，画面时刻标签与报告时间戳一致，画面注明为静图序列，节奏为 1:1 或注明放慢倍数且相对误差 ≤10%。  
  验证：checks.py d11() (fail-only): ffmpeg frame differences split the clip into held stills; each matched (OpenCV NCC >=0.55) against the report's embedded Fig 9/10/11 images; order must be exactly Fig 9 -> 10 -> 11; holds must keep 0.165 : 0.264 s within 10% and equal 1:1 or a slow-down factor stated in slide text/notes/script (+-10%). When it reaches the judge these parts have passed; the judge checks the on-frame time labels and the 'sequence of stills' disclosure on the contact sheet.
- **D12** [gate · 预期 0.30] 包内无任何外部关系（媒体、图片、图表数据、字体），且所有被引用部件均存在。  
  验证：checks.py d12(): dlib.pptx_integrity() + external non-hyperlink relationship scan.
- **D13** [mid · 预期 0.35] 核心数值与结论在页面、备注、图表工作簿、calculations.xlsx、讲稿、PDF 与证据索引间一致（以 answer-key 关键量为准，全部一致才通过）。  
  验证：Judge checks the answer-key key quantities in slide text, notes, chart_data, embedded workbook cell values, calculations.xlsx CSV, script, PDF text and evidence-index.csv.
- **D14** [mid · 预期 0.45] playback-check.md 写明实际使用的软件与版本、步骤与结果、未能验证的内容；其声明不与评测脚本的实测结果矛盾。  
  验证：checks.py postprocess fails D14 when a line claims a trigger/chart-build/video/mechanism/offline/workbook property as verified and the corresponding check (D08/D09/D10/D07/D12/D04) failed; otherwise judge reads playback-check.md.
- **D15** [base · 预期 0.70] calculations.xlsx 中每个派生量都是实时公式并引用源值单元格，列有单位与页码。  
  验证：openpyxl data_only=False formula check.

## 预期分计算

- 判定数：57（base 17 / mid 25 / gate 15）
- 分值占比：base 27.2 / mid 40.0 / gate 32.8（满分 100）
- 预期分 = Σ（单项权重 × 预期通过率）
- **预期分 ≈ 46.5**（设计估计，未经实测校准）
  - G1：5.5 / 10
  - G2：6.2 / 10
  - G3：11.3 / 26
  - G4：4.2 / 8
  - G5：8.9 / 26
  - G6：10.3 / 20

critical 字段仅为设计标记，rubric_score.py 不读取，关键项与其他项同样计分。
