# WFA-CDN-009 隐藏评分细则（REVIEWER-ONLY，由 rubric.json 生成）

每项只判是/否，部分满足即判否。组得分 = 组权重 ×（通过项数 / 该组适用项数），总分为各组之和（满分 100）。标“条件项”的判定先判是否适用：不适用记 N/A，从该组分子分母中同时剔除（其余项按组权重重新均分）。评委须与求解模型不同家族；求解者自述的 playback-check.md 不能单独作为证据。关键质量项须有工程检查（python-pptx / PowerPoint COM）或人工核对，不得只靠 LLM 评委。

## 门槛

- **GATE0**（整题）output/ 中 presentation.pptx、slides.pdf、script.md、evidence-index.csv、playback-check.md 五件齐全，且 pptx 能被 python-pptx 读出幻灯片。 — 不过 ⇒ 全部判定记否，验收失败。
- **GATE1**（G6 组级）Windows 桌面版 PowerPoint 16.x 通过 COM Presentations.Open（ReadOnly 与 ReadWrite 各一次）打开，无错误、无修复提示（不得使用 OpenAndRepair）；将 pptx 单独复制到新文件夹、断网后再次打开同样无修复。 — 不过 ⇒ G6 记 0；V07 记否；验收失败（连续分照常报告）。
- **GATE2**（整题）作弊/违规：访问评测隐藏文件、联网取材、以材料包以外来源的数据替换材料数据。 — 不过 ⇒ 整题 0，验收失败。

## 分组

### G1 叙事与结构（13 分，7 项）

- **N01** [base · 预期 0.92] 8–10 页、16:9，含标题页与结束页，无空分隔页。  
  验证：python-pptx: slide count 8–10, slide size ratio 16:9 (±1%); first slide = title slide (exempt from content check), last slide = closing; every other slide has ≥1 content element besides its title (no empty divider).
- **N02** [base · 预期 0.80] 每页标题都是完整论断（含谓语的判断句），不是话题标签。  
  验证：Reviewer reads titles; any noun-phrase title ⇒ NO.
- **N03** [mid · 预期 0.60] 叙事顺序为：飞行中事件 → 物理直接原因 → 制造环节源头 → 组织/监管层面 → 防线评估 → 回答与边界；不跳回、不重复。  
  验证：Reviewer maps each slide to a stage; any stage missing or out of order ⇒ NO.
- **N04** [mid · 预期 0.45 · 关键] 结束页用一句话直接回答问题，并列出至少两条证据不支持的结论（与 G3/G5 隐藏项一致，不得新增材料外事实）。  
  验证：Reviewer; both 'not supported' items must be backed by the material.
- **N05** [mid · 预期 0.50] script.md 在 130–150 词/分钟内某一语速下（加讲稿声明的停顿）总时长落在 11–13 分钟，即讲稿词数 + 停顿折算须在 130×11 至 150×13 词当量（1430–1950）之间；逐页声明时长之和与 11–13 分钟总时长相符（±10%）；每页备注文字与讲稿该页一致。  
  验证：Deterministic word count + python-pptx notes diff (normalised whitespace, ≥90% token overlap per slide).
- **N06** [mid · 预期 0.55] 为非结构工程听众解释以下全部术语：门塞（plug 与可用出口门的区别）、快速失压、事故调查机构的 probable cause / contributing to 用语。  
  验证：Reviewer; any of the three unexplained ⇒ NO.
- **N07** [gate · 预期 0.20 · 关键] 全篇区分“调查机构已确立的事实 / 机构的分析判断 / 制作者自己的推断”，用一致的视觉编码，且没有任何一处把制作者推断标为机构结论。  
  验证：Reviewer audits every coded element against the report wording.

### G2 视觉设计与可读性（13 分，8 项）

- **V01** [base · 预期 0.75] 所有正文 ≥20 pt（PowerPoint 渲染为准，含自动缩放后）。  
  验证：COM: TextFrame2.TextRange.Font.Size per run, excluding captions/source lines.
- **V02** [base · 预期 0.85] 图注与出处行 ≥12 pt。  
  验证：COM font sizes.
- **V03** [base · 预期 0.90] 任一页要点 ≤6 条。  
  验证：python-pptx paragraph count per body placeholder/text box.
- **V04** [mid · 预期 0.50] 每个原生图表坐标轴有标题与单位，多系列有图例，数据标签在投影尺寸下可读。  
  验证：COM: Chart.HasAxis/HasTitle; reviewer at 1920x1080 export.
- **V05** [mid · 预期 0.50] 报告原图裁切到相关图块并保留图例/比例尺/图号，原生标注准确指向所述部位。  
  验证：Reviewer compares crop with source page.
- **V06** [mid · 预期 0.45] PowerPoint 静态渲染中任一页都没有文字溢出、裁切或对象重叠。  
  验证：COM export PNG per slide + shape bbox overlap check + reviewer.
- **V07** [gate · 预期 0.20] 所有动画状态下均无遮挡：因果链页每一步点击后、反事实页每个触发器单独触发及全部触发后（任意顺序）。  
  验证：COM slideshow: step through clicks; fire triggers in order and reverse order; screenshot each state.
- **V08** [base · 预期 0.80] 全篇英文语法、拼写、单位与时间写法正确一致（ft、psi、PST/UTC、24 小时制）。  
  验证：Reviewer + spell check.

### G3 材料覆盖与隐藏考点（20 分，16 项）

- **A01** [base · 预期 0.88] 交代事件基本事实：2024-01-05、该航班、737-9 及注册号、自 PDX 起飞前往 ONT、返航 PDX 落地，均与材料一致。  
  验证：answer-key K-BASIC (F10, P1).
- **A02** [mid · 预期 0.55] 飞行时间线与 FDR 一致：1712:33 客舱压力骤降（约 14,830 ft）、1713:41 最高 16,320 ft 后下降、1726:46 落地（约 14 分钟后）。  
  验证：answer-key K-TL (F16, F17, F20).
- **A03** [mid · 预期 0.55] 伤情：1 名乘务员与 7 名乘客轻伤，无人送医；机长、副驾驶、3 名乘务员、164 名乘客未受伤（共 177 人）。不把另 2 名自行就医者计入伤者。  
  验证：answer-key K-INJ (F10, F20 fn14).
- **A04** [mid · 预期 0.45 · 关键] 物证链：四颗螺栓孔无接触损伤/变形→螺栓在门塞上移前已缺失；垫圈淡痕→硬件曾经装过；密封区多条平行污线→前几次飞行中逐步上移。  
  验证：answer-key K-PHYS (F99–F100).
- **A05** [mid · 预期 0.45 · 关键] 制造源头：五颗受损铆钉返工需打开门塞；门塞至迟 2023-09-18 10:53 已打开、至少到 09-19 17:09 仍开；09-19 第二班关闭，当时无门组人员在岗；无拆卸记录，故无质检；约 18:39 的照片显示可见三处无螺栓。  
  验证：answer-key K-ORIGIN (F62–F65, F105–F106).
- **A06** [mid · 预期 0.45 · 关键] 按终报原文区分 probable cause（波音未提供足够培训、指导与监督以确保拆卸流程被遵守）与 contributing（FAA 合规执法监督与审计计划无效），不改写为追责/罚责措辞。  
  验证：answer-key K-PC (F136).
- **A07** [mid · 预期 0.55] 交代至少两项系统性因素并与终报结论对应：拆卸 BPI 缺乏清晰易用且有至少 10 年合规问题史；在岗培训无结构无记录；劳动力经验下降未做变更管理评估。  
  验证：answer-key K-SYS (F133–F134 findings 15,16,20,21).
- **A08** [mid · 预期 0.45] 建议数量正确（新建议：FAA 11 条、波音 8 条；重申：FAA 4 条、A4A/NACA/RAA 1 条），并具体引用至少一条与门塞直接相关的建议。  
  验证：answer-key K-REC (F1, F106).
- **H01** [gate · 预期 0.20 · 关键] [隐藏] 分离高度：以 FDR 约 14,830 ft（1712:33）为准；若出现初报中的“约 16,000 ft”（机组回忆）或“约 14,850 ft”（1 秒后主警告时刻），须标明其来源与含义，不得把 16,000 ft 当作分离高度，也不得把三者悄悄统一。  
  验证：answer-key K-ALT (P3, P4, F16).
- **H02** [gate · 预期 0.08 · 关键] [隐藏] 发现初报自相矛盾：首页与末页伤情栏印“177 None / Total Injuries: 177 None”，而同一份初报正文写 7 名乘客与 1 名乘务员轻伤；简报保留原文并标出不一致，以终报为准，不悄悄改正。  
  验证：answer-key K-INJ177 (P1, P19 vs P1 narrative, F10).
- **H03** [gate · 预期 0.12 · 关键] [隐藏] 增压 AUTO FAIL 历史：初报/维修日志为 3 次（12-07、01-03、01-04），终报 CPC 记忆为 4 次飞行（另含 2023-11-10，投入运营前一天）；故障特征指向 CPC 的 UART 芯片间歇故障，且终报认定与门塞上移无关。计数须注明来源，结论不得写成“相关/预警”。  
  验证：answer-key K-AUTOFAIL (P8, F25, F48 fn43, F49, F132 #5).
- **H04** [gate · 预期 0.20] [隐藏] 指出门塞旁 26A、26B 当时空座（已值机的两人迟到改签），并据此说明伤情轻微带有偶然性，不能据“仅轻伤”推断风险低。  
  验证：answer-key K-SEATS (F18 fn12, F39 fn35).
- **H05** [gate · 预期 0.20 · 关键] [隐藏] 说明调查未能确定是谁打开、谁最终关闭门塞；不把“move crew”或 Spirit 人员写成关闭/打开者（波音高管曾在媒体会上称 move crew 关闭，后同意访谈并未确认；NTSB 因此限制波音获取调查信息）。  
  验证：answer-key K-WHO (F60, F66 fn60, F133 #13, F105).
- **H06** [gate · 预期 0.20 · 条件项，适用概率 0.30，无条件通过率 0.06] [隐藏·条件项] 仅当简报（页面、备注或讲稿）引用“最有经验的门组成员在门塞开启当天休假”这一事实时计分：须写日期 2023-09-18/19，并注明终报原文脚注（印刷 p55）误印为 2024 的不一致；照抄 2024 或悄悄改为 2023 不加说明均判否。未引用该事实时本项记 N/A，不计入 G3 分母。  
  验证：answer-key K-TYPO (F69 vs F62–F63). Reviewer first decides applicable (fact cited anywhere in slides/notes/script) or N/A.
- **H07** [gate · 预期 0.20 · 关键] [隐藏] 说明终报未能评估波音安全文化及生产线是否存在不良（生产）压力（样本小、罢工阻碍问卷）；简报不得把“赶产压力导致”作为已确立原因。  
  验证：answer-key K-CULTURE (F135 #27).
- **H08** [gate · 预期 0.25] [隐藏] 门塞设计改进（二次止动装置、螺栓挂绳）按报告时状态描述：截至 2025 年 5 月仍在取证，新机预计 2026 年起安装，在役机靠服务通告/AD 改装；不得说已装机或已强制。  
  验证：answer-key K-DESIGN (F106).

### G4 逐页忠实度（14 分，8 项）

- **F01** [base · 预期 0.85] 第 1 页（标题页，含备注）没有任何无出处或与材料不符的内容；出现一处即判否。  
  验证：Reviewer.
- **F02** [mid · 预期 0.50] 第 2 页（文字、图表数据、标注与备注）没有任何无出处或与材料不符的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Reviewer checks every fact against evidence-index.csv rows and the PDFs.
- **F03** [mid · 预期 0.50] 第 3 页（文字、图表数据、标注与备注）没有任何无出处或与材料不符的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Reviewer checks every fact against evidence-index.csv rows and the PDFs.
- **F04** [mid · 预期 0.50] 第 4 页（文字、图表数据、标注与备注）没有任何无出处或与材料不符的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Reviewer checks every fact against evidence-index.csv rows and the PDFs.
- **F05** [mid · 预期 0.50] 第 5 页（文字、图表数据、标注与备注）没有任何无出处或与材料不符的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Reviewer checks every fact against evidence-index.csv rows and the PDFs.
- **F06** [mid · 预期 0.50] 第 6 页（文字、图表数据、标注与备注）没有任何无出处或与材料不符的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Reviewer checks every fact against evidence-index.csv rows and the PDFs.
- **F07** [mid · 预期 0.50] 第 7 页（文字、图表数据、标注与备注）没有任何无出处或与材料不符的数字、时刻、日期、计数、单位或论断；出现一处即判否。  
  验证：Reviewer checks every fact against evidence-index.csv rows and the PDFs.
- **F08** [mid · 预期 0.40] 第 8 页至最后一页（文字、图表数据、标注与备注）均没有任何无出处或与材料不符的内容；出现一处即判否。  
  验证：Same as F01.

### G5 因果推理、反事实与计算（20 分，10 项）

- **R01** [mid · 预期 0.45 · 关键] 因果链各环节顺序正确且无材料外环节，每个箭头标出支持它的证据类型（FDR、物证、制造记录/照片/短信、访谈）。  
  验证：Reviewer vs answer-key chain.
- **R02** [mid · 预期 0.50] 日期/时长算术至少两项正确并注明口径：开启(09-18)→事故 109 天；交付(10-31)→事故 66 天；投运(11-11)→事故 55 天；分离→落地约 14 分 13 秒；510 小时/154 循环为原文值。  
  验证：answer-key K-ARITH.
- **R03** [gate · 预期 0.15 · 关键] 反事实：说明按波音工程评估，只要一颗下部垂直止动螺栓、或两颗上导轨螺栓在位，门塞就不会上移脱出——事故需要四颗全部缺失；据此论证“复装任何一部分硬件”都是有效防线。  
  验证：answer-key K-REDUND (F47, F98).
- **R04** [gate · 预期 0.15 · 关键] 反事实措辞分寸：短戳流程若正确使用“可能提供发现机会”（may），不得写成“必然阻止”；拆卸记录被写为规定的主防线（触发复装步骤与质检）。  
  验证：answer-key K-SHORTSTAMP (F134 #22, F133 #14, F134 #18).
- **R05** [gate · 预期 0.12 · 关键] 把两条“看似防线”判为不能阻止：例行航前绕机检查无法察觉此前的上移（终报结论 4）；因 AUTO FAIL 停飞/排故与门塞无关（结论 5）。两条都须出现且判定正确。  
  验证：answer-key K-PREFLIGHT, K-AUTOFAIL.
- **R06** [mid · 预期 0.40] 监管防线：用 2022-10 至 2023-09 FAA 在 Renton 的审计记录 68 项“被指控不合规”无一涉及拆卸 BPI、而 2018–2023 有 16 项与该 BPI 相关的合规问题（波音自报 9、FAA 发现 7），论证 FAA 为何是“促成因素”；保留 alleged 的限定。  
  验证：answer-key K-FAA (F81–F82).
- **R07** [gate · 预期 0.20 · 关键] 口径：门塞开启历史为 2018 年以来 62 次（28 架），Renton 24 次（15 架）、外场 38 次（13 架）；Renton 2021/2022/2023 的 1/2/4 是“受影响飞机架数”而非次数。图表/文字不得把次数与架数混画或互换。  
  验证：answer-key K-PLUGHIST (F69 fn62).
- **R08** [mid · 预期 0.35] 解释“为何飞了 154 个循环才脱落”：静态需 >150 lb 才能推动（右侧门塞样件），但动态载荷可使有效重量降到约 25 lb（0.40–0.45 g，估计误差约 ±0.15 g，标称 63 lb），导致逐步上移；不夸大为精确测量。  
  验证：answer-key K-LOADS (F45–F47, F99).
- **R09** [gate · 预期 0.25 · 关键] 回答区分系统性原因（培训、指导、监督、监管）与个人差错，不指认个人，也不把结论推广为材料未支持的“机队/全行业普遍缺陷”。  
  验证：Reviewer.
- **R10** [gate · 预期 0.25 · 关键] 结束页“证据不支持的结论”中至少一条对应 H03、H05 或 H07 且表述忠实。  
  验证：Reviewer.

### G6 原生对象、动画与交付（20 分，11 项）

- **D01** [base · 预期 0.88] slides.pdf 与 pptx 页数相同，内容对应。  
  验证：Page count + title text match.
- **D02** [base · 预期 0.85] evidence-index.csv 列齐全（页号、元素、论断、源文件、印刷页、PDF 页、图表/章节号、变换），且每页至少一行。  
  验证：csv parse.
- **D03** [base · 预期 0.85] 演讲者备注非空且每页都有；标明 AI 协助制作与源文件署名，无背书暗示。  
  验证：python-pptx notes + text search.
- **D04** [base · 预期 0.80 · 关键] ≥2 个原生图表（GraphicFrame/chart part，非图片），COM ChartData.Activate() 均成功，嵌入工作簿首表含所绘数值、单位与出处页。  
  验证：COM ChartData.Activate + openpyxl on embedded xlsx.
- **D05** [gate · 预期 0.25 · 关键] 图表所绘每个数值均与材料一致（含阶段/口径），无编造的中间点；工作簿数值与 PPT 可见标签一致。  
  验证：Reviewer compares workbook cells with answer-key pages.
- **D06** [base · 预期 0.80] ≥2 幅报告真实原图（从 PDF 提取/裁切，非重绘）并配原生可编辑标注。  
  验证：Image hash/visual match to PDF page render; callouts are autoshapes/text boxes.
- **D07** [mid · 预期 0.50 · 关键] 因果链页：链条由原生形状与连接线（cxnSp 连接到形状）组成，≥5 个单击进入效果按顺序揭示独立形状，在 PowerPoint 放映中逐次执行。  
  验证：COM: TimeLine.MainSequence count/trigger type msoAnimTriggerOnPageClick; slideshow stepping screenshots.
- **D08** [gate · 预期 0.15 · 关键] 反事实页：≥3 个防线形状各自是交互触发器（COM TimeLine.InteractiveSequences，TriggerType = msoAnimTriggerOnShapeClick，TriggerShape 为该防线形状），单击后揭示独立可编辑说明；放映中逐个点击确实触发，且不是超链接/跳页/主序列点击。  
  验证：COM InteractiveSequences enumeration + slideshow click via SlideShowWindow coordinates; screenshot before/after each.
- **D09** [gate · 预期 0.30] 单独复制 pptx 到新文件夹断网放映，图表、图片、动画与触发器均正常（无外链、无缺失图片红叉）。  
  验证：COM LinkFormat scan + slideshow run in copy folder.
- **D10** [mid · 预期 0.35] 核心数值与结论在页面、备注、图表工作簿、讲稿、PDF 与证据索引间一致（以 answer-key.json 各 checkpoint 的 answer 字段关键量为准，全部一致才通过）。  
  验证：Scripted string match of key values across artefacts + reviewer.
- **D11** [mid · 预期 0.45] playback-check.md 给出实际验证的软件与版本、具体步骤与结果、未能验证的内容；与审阅者实测不矛盾（如声称已在 PowerPoint 中验证而实测失败即否）。  
  验证：Reviewer compares claims with COM results.

## 预期分计算

- 判定数：60（base 13 / mid 28 / gate 19）
- 分值占比：base 22.3 / mid 46.8 / gate 30.9（满分 100）
- 预期分 = Σ_组 E[组权重 × 通过项数 / 适用项数]；非条件项按预期通过率计，条件项（H06）按“适用概率 q × 适用时通过率 p”枚举两种情形：适用时组内 n 项、不适用时 n−1 项（G3：q=0.3、p=0.2，对应无条件通过率 0.06）
- **预期分 ≈ 47.2**（设计估计，未经实测校准）
  - G1：7.5 / 13
  - G2：8.0 / 13
  - G3：7.4 / 20
  - G4：7.4 / 14
  - G5：5.6 / 20
  - G6：11.2 / 20
