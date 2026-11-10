# WFA-CDN-013 隐藏评分细则（reviewer-only，由 make_rubric.py 生成）

每条二元、相互独立，部分满足即判否。组级门槛：B01 失败 → G2 记 0。整题门槛：交付物缺失/打不开、作弊。

页码记法：p.N = 印刷页；PDF N = PDF 页序。TN 2252：PDF = 印刷 + 38；TN 2135：PDF = 印刷 + 30。

- **G1** 交付与合同 / Deliverables & contract
- **G2** 原生对象与地图（组级硬门槛：B01 失败则本组记 0）/ Native objects & maps (group gate: B01)
- **G3** 覆盖与忠实 / Coverage & fidelity
- **G4** 跨报告隐藏考点 / Cross-report hidden points
- **G5** 反事实边界推理 / Counterfactual-boundary reasoning
- **G6** 叙事与视觉 / Narrative & visual

## 基础层（base，25 分，11 条）

| ID | 组 | 关键 | 判定 | 验证 | 预期通过率 | 分值 |
|---|---|---|---|---|---|---|
| B01 | G1 | 是 | presentation.pptx 存在，且通过包完整性检查（zip 完整、内容类型、关系目标存在、XML 良构、python-pptx 可打开、无外链），作为 Windows 桌面版 PowerPoint 16.0 无修复提示打开的代理；失败则 G2 整组记 0。 | checks.py b01(): dlib.pptx_integrity() + external-link scan (structural proxy; no PowerPoint on the Linux grader). | 0.90 | 2.27 |
| B02 | G1 |  | 恰好 12 页，16:9。 | python-pptx: len(slides)==12 and slide_width/slide_height within 1% of 16/9. | 0.92 | 2.27 |
| B03 | G1 |  | slides.pdf 为 12 页，顺序与标题与 PPTX 一致。 | pdfinfo pages==12; pdftotext first line of each page vs pptx title placeholder text (fuzzy ≥0.8). | 0.90 | 2.27 |
| B04 | G1 |  | script.md 逐页给出逐字稿与时长，合计 12–15 分钟，标注点击事件；PPTX 演讲者备注与讲稿逐页一致（≥11/12 页词重合 ≥80%）。 | Parse script.md durations; python-pptx notes_slide text vs script per slide (token Jaccard). | 0.80 | 2.27 |
| B05 | G1 |  | evidence-index.csv 含规定 8 列，且每个承载事实的页面至少有一行。 | checks.py: header has the 8 columns; every fact-bearing slide (a digit in slide text or notes, or a chart/table/picture) is covered by >=1 row. | 0.85 | 2.27 |
| B06 | G1 |  | calculations.xlsx 中每个推导量都有实时公式（非粘贴值）以及源值、单位、报告与页码。 | openpyxl (data_only=False): result cells start with '='; required columns non-empty. Cross-check that intervals shown on slides appear here. | 0.75 | 2.27 |
| B07 | G1 |  | playback-check.md 写明软件与版本、实际验证项（含具体结果）与未验证项；除非写明版本并给出具体观察结果，否则不声称在 Windows PowerPoint 中测试过。 | Judge reads playback-check.md. Self-reports are not evidence for other items. | 0.85 | 2.27 |
| B08 | G6 |  | 标明 AI 制作，源报告单独署名，未暗示发布机构审阅或背书。 | Text scan of slides+notes for disclosure/credit; reviewer reads for endorsement implication. | 0.90 | 2.27 |
| B09 | G6 |  | 正文 ≥20 pt、图注/出处 ≥12 pt、每页 ≤6 条要点。 | checks.py: run sizes resolved through run/paragraph/shape lstStyle/layout+master placeholder/txStyles/defaultTextStyle with normAutofit fontScale; body = body/object placeholders or the slide's main text box (>=20 words, not a source/caption line) must be >=20 pt; all other text >=12 pt; bullet paragraphs summed over all non-title text frames of a slide <=6. | 0.70 | 2.27 |
| B10 | G1 |  | 六节按规定顺序出现，无空分隔页。 | Reviewer maps each slide to a section; any slide without evidence content fails. | 0.90 | 2.27 |
| B11 | G3 |  | 两份报告均被实质使用：evidence-index 中两份报告各 ≥5 行。 | Count rows by report column (TN 2252 / TN 2135 or equivalent naming). | 0.90 | 2.27 |

## 中间层（mid，40 分，18 条）

| ID | 组 | 关键 | 判定 | 验证 | 预期通过率 | 分值 |
|---|---|---|---|---|---|---|
| M01 | G2 | 是 | ≥3 个原生图表，每个在 PowerPoint 中“编辑数据”可打开嵌入工作簿。 | pptx zip: ppt/charts/chart*.xml with c:externalData -> ppt/embeddings/*.xlsx; PowerPoint: right-click > Edit Data on each. | 0.75 | 2.22 |
| M02 | G2 |  | 图表嵌入工作簿列出源值、单位、报告与页码，推导值用公式。 | checks.py fails workbooks without page/report labels; judge reads the embedded workbook cell values and formulas (structure.embedded_workbook_summary) for units and formula use. | 0.45 | 2.22 |
| M03 | G3 | 是 | 分区“通知—火到达间隔”图：数据与 TN 2252 表 11（p.56/PDF 94）一致——抽查 ≥8 个分区，分钟精确；页面写明时间基准（IC 请求或 CodeRED）与正负号约定。 | checks.py m03(): chart whose categories (or series) are Table 11 zones; every plotted value of a key zone must equal first-fire minus/plus a request/CodeRED time, or one of those clock times, within 1 min (minutes, hours or Excel day fractions); >=8 zones; slide text/chart/axis titles must name the time basis (request/CodeRED) and a sign convention. | 0.50 | 2.22 |
| M04 | G3 |  | 呈现的 11 月 8 日早晨 burnover 编号、地点、时刻与 TN 2252 表 30（p.125/PDF 163）一致，无一错误。 | Judge compares slide text (incl. grouped shapes and table cells) and notes with the answer-key burnovers list. | 0.60 | 2.22 |
| M05 | G2 | 是 | ≥3 幅图片裁切各与报告某页匹配（与 evidence-index.csv 中该页所引 PDF 页（±1）或已知地图页做图像模板匹配），两份报告各 ≥1 幅；均非整页截图；每幅匹配的裁切上至少放有一个原生可编辑形状（解释未烧录进图片）。 | checks.py m05(): pdftoppm 40 dpi grey page renders, OpenCV multi-scale normalised cross-correlation >=0.6; matched area <85% of the page; >=1 non-picture shape intersecting the picture bbox. Legend/scale retention and legibility are not scored (not measurable from the evidence). | 0.50 | 2.22 |
| M06 | G2 | 是 | 某地图页用 ≥4 个可分别编辑的原生点击进入动画，每步显示的标签可识别一处 11 月 8 日上午的 burnover（表 30 编号“#N”或道路名），且各步按时间先后排列（标签有时刻则按标签，否则按表 30 时刻）。 | checks.py m06(): p:timing main-sequence clickEffect/entr on distinct shapes of a slide with a picture; revealed text mapped to answer-key Table 30 rows with time <=12:00 Nov 8; non-decreasing order. | 0.45 | 2.22 |
| M07 | G2 |  | 原生形状绘制的可编辑边界示意图，对 (a)(b)(c) 三种做法都区分观测记录/推断/不被支持的说法。 | pptx: diagram composed of p:sp shapes (not a picture); reviewer checks three alternatives × three categories. | 0.60 | 2.22 |
| M08 | G3 |  | 所用总体数字正确：约 40 000 人疏散、85 人死亡、>18 000 栋建筑损毁、31 个 TRA/>1200 平民、198 起 EA/R/≥1000 平民（TN 2252 摘要 p.iii）。任何一处错误即否。 | Text scan of slides/notes against answer-key headline values. | 0.80 | 2.22 |
| M09 | G3 | 是 | 逐页忠实：任何一页（含备注）都没有与 answer-key 相矛盾、或未列入 evidence-index.csv 的数字、时刻、计数或归属。 | Judge compares slides/notes with the answer key and evidence-index.csv. | 0.30 | 2.22 |
| M10 | G3 |  | evidence-index 页码准确：以固定种子抽 10 行，≥9 行的 PDF 页与印刷页一致（TN 2252：PDF = 印刷 + 38，罗马页 + 2；TN 2135：PDF = 印刷 + 30），且该 PDF 页上能找到该行论断中的数字（≥3 字符）或 ≥60% 的实义词。 | checks.py m10(): pdftotext of the cited PDF page of input/main-report.pdf or input/companion-report.pdf. | 0.40 | 2.22 |
| M11 | G4 |  | 区分 IC 请求时刻与 CodeRED 送达启动时刻，不混为一谈（如 Zones 3/8/14/Lower Pentz：疏散令请求 07:46，CodeRED 07:57）。 | Slides/notes/chart workbook; TN 2252 Table 11 and p.58. | 0.50 | 2.22 |
| M12 | G5 |  | (b) 通行能力论证正确使用 OHU/疏散车道比（表 4 p.28：Paradise 927、Magalia 1264、Concow 164 等所用值），并说明该比值不是显式通行能力指标。 | Compare values used; look for the caveat (TN 2252 p.28). | 0.55 | 2.22 |
| M13 | G6 |  | 每页标题都是该页能支持的论断。 | Reviewer reads 12 titles against slide content. | 0.60 | 2.22 |
| M14 | G6 |  | 全片一致的视觉编码区分观测/推断/不被支持（反事实）说法。 | Reviewer checks legend/style use on every slide carrying such claims. | 0.55 | 2.22 |
| M15 | G6 |  | 所有形状位于页面内；渲染页中无文字溢出；点击序列显示的形状不遮挡其所标注的地图要素或其他常显文字。 | checks.py fails shapes beyond the slide bounds; judge checks overflow/occlusion on the rendered pages. | 0.55 | 2.22 |
| M16 | G3 |  | 核心数值在页面、备注、图表工作簿、calculations.xlsx、讲稿、PDF 间一致（抽 6 个核心值）。 | Judge checks 6 sampled core values in slide text, notes, chart_data and embedded workbook cell values, calculations.xlsx CSV, script and PDF text. | 0.45 | 2.22 |
| M17 | G5 |  | 每条建议都对应到已呈现证据（标明页），且没有一条依赖不被支持的反事实。 | Reviewer reads recommendation slide(s) vs earlier slides. | 0.55 | 2.22 |
| M18 | G3 |  | 不把技术访谈中的个人评论（如 TN 2135 附录 TD 引语）或非报告结论当作报告发现呈现；引用须标为受访者陈述。 | Search slides/notes for quotes; check attribution (answer-key trap T01). | 0.80 | 2.22 |

## 门槛层（gate，35 分，14 条）

| ID | 组 | 关键 | 判定 | 验证 | 预期通过率 | 分值 |
|---|---|---|---|---|---|---|
| H01 | G4 | 是 | burnover 总数跨报告对齐：TN 2135 记 19 起，TN 2252 记 23 起，#20–23 为 TN 2252 第二轮（救援数据分析）新增；两数及原因均呈现，不把 19 当总数。 | answer-key H01 (TN 2252 p.7/PDF 45, p.123/PDF 161; TN 2135 p.117/PDF 147). | 0.30 | 2.69 |
| H02 | G4 | 是 | 严重度分类按表计数：23 起 = 14 起 Category 1 + 9 起 Category 2（TN 2252 表 30）；不得沿用正文“seven Category 2”；未呈现分类计数也判否。 | answer-key H02 (TN 2252 p.123 text vs Table 30; TN 2135 p.117 text '11+7' vs Table 33 11+8). | 0.15 | 2.69 |
| H03 | G4 |  | 条件项：凡给出 11 月 8 日 10:00 前（或“上午”）burnover 计数，须为 11 起（9 Cat 1 + 2 Cat 2，表 30），或与正文“nine (7/2)”并列并指出差异；单独使用“nine”判否；未给出该计数不判否（若点击序列/页面所列上午 burnover 少于表 30 而又称完整，按 M04 处理）。 | answer-key H03 (TN 2252 p.123/PDF 161 text; Table 30 PDF 163). | 0.40 | 2.69 |
| H04 | G4 |  | 高紧迫度 TRA 平民数：261 为不重复个人，352 为人×暴露次数（表 39）；若加总各 TRA 最小值，须标为人次，不得称为人数。 | answer-key H04 (TN 2252 p.158/PDF 196). | 0.20 | 2.69 |
| H05 | G4 |  | 区分 8 个高紧迫度 TRA 与其中 6 个高峰值危险 TRA；不得据 TF-TRA 7 措辞称“8 个 TRA 经历高峰值危险”。 | answer-key H05 (TN 2252 p.xxxiii/PDF 35 vs p.137/PDF 175, p.158/PDF 196, Table 31). | 0.20 | 2.69 |
| H06 | G4 |  | 08:01 预警时已着火的分区为 Zone 6（表 11：07:57），而非正文 p.61 所称 Zone 4（表 11：08:41）；图表数据与任何相关陈述均按表或明示差异。 | answer-key H06 (TN 2252 p.56/PDF 94 vs p.61/PDF 99). | 0.35 | 2.69 |
| H07 | G4 |  | 条件项：若简报给出 Concow 消防员/一线人员首次直接见火时刻，须呈现 TN 2252 内部差异（p.60/PDF 98 写 07:32，p.63/PDF 101 写 07:20，p.57/PDF 95 写 07:20–07:30 之间），或用 07:20 并引 TN 2252 p.63 或 TN 2135（p.59/PDF 89：07:20 经 Rim Road 的消防车遭遇迅速扩大的飞火；p.122/PDF 152）；悄悄用 07:32 判否。未给出该时刻视为通过。 | answer-key H07; TN 2135 p.59/PDF 89 and p.122/PDF 152. | 0.35 | 2.69 |
| H08 | G4 | 是 | Zones 3/8 定量对齐：疏散令请求 07:46 比首个火数据点（07:50/07:49）早 3–4 分钟，但 CodeRED 07:57 比首火晚 7–8 分钟；需在页面/图表上呈现。 | answer-key H08; values in calculations.xlsx with formulas. | 0.20 | 2.69 |
| H09 | G5 | 是 | (a) 更早疏散令的边界：引用表 30 中主干道 burnover 在火到前已拥堵/受阻（#4、6、7、8、22 中 ≥3 个）及 TN 2252 p.59“延迟通知的影响超出研究范围且难以量化”；不声称更早下令可避免 burnover 或死亡，不给出“可挽救人数”。 | answer-key H09. | 0.15 | 2.69 |
| H10 | G5 |  | (b) 通行能力边界：至少使用表 5 或表 6 的一个 OHU/车道值（如 Zones 3/8/14 为 316，Paradise 以南 2950 或 2529）并注页码，且指出表 4–6 未计入火/障碍造成的车道损失（p.32/PDF 70）；不得把 OHU 比值当作实际通行量或“多一条车道即可救人”的证据。 | answer-key H10 (TN 2252 p.32–33/PDF 70–71). | 0.30 | 2.69 |
| H11 | G5 | 是 | (c) 燃料处理边界引自 TN 2135：初始高火星通量区深入 Paradise 1 km、显著飞火达 3.4 km，需数百米宽的处理带且环境/财务影响巨大、效果评估超出范围；不声称周边燃料带可阻止 Paradise 起火。 | answer-key H11 (TN 2135 p.140/PDF 170; p.136/PDF 166). | 0.20 | 2.69 |
| H12 | G4 |  | 首次观察时刻标注：#5 Windermere、#20 Camelot（及若出现的 #14）的时刻为首次观察、burnover 条件更早已存在；相关间隔标为界限值而非精确值。 | answer-key H12 (Table 30 footnote e; Table 12 footnote a). | 0.15 | 2.69 |
| H13 | G2 |  | （仅供人工复核，不计分）地图标注落在报告地图（TN 2252 图 24 / TN 2135 图 47 或所用图）对应道路/地点上。 | Not graded automatically (the judge has neither the source maps nor legible renders). | 0.20 | 0.00 |
| H14 | G4 |  | 火势时程跨报告对齐：“火有多快”一节引用 TN 2135（如 08:30 主火线抵达 Paradise，Apple View Way–Merrill Rd 约 1 km；约 70 分钟后 2.8 km 正面；08:00 前 Pentz Rd 以东飞火）且与 TN 2252 表 11 首火数据点（Zone 8 07:49、Zone 3 07:50）一致、无矛盾。 | answer-key H14 (TN 2135 p.122/PDF 152; TN 2252 p.56). | 0.30 | 2.69 |

## 预期分计算（设计估计，未校准）

| 层 | 条数 | 分值 | 平均预期通过率 | 期望得分 |
|---|---|---|---|---|
| base | 11 | 25 | 0.852 | 21.3 |
| mid | 18 | 40 | 0.550 | 22.0 |
| gate | 14 | 35 | 0.250 | 8.8 |
| 合计 | 43 | 100 | | **52.0** |

v2026-10-25 清理：critical 字段仅为设计标记，rubric_score.py 不读取，关键项与其他项同样计分；权重 0 的条目仅供参考、不送评审模型。由 checks.py 机测的条目见 tests/checks.py 文件头；其余条目由 LLM 评审依据 rubric_score.py 收集的证据判定。
