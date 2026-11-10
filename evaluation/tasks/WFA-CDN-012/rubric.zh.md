# WFA-CDN-012 隐藏评分细则（REVIEWER-ONLY，由 rubric.json 生成）

每项只判是/否，部分满足即判否。得分 = Σ（权重 × 通过）/ Σ 权重（不计 na 项），满分 100；各组权重见下。“验证”以 checks.py 开头的项由 tests/checks.py 确定性判定（注明 fail-only 的仅能判否），其余交给 LLM 评委（仅依据 output/ 证据与 answer-key.json）；求解者自述的 playback-check.md 不能单独作为证据。“关键”标记仅为设计注记，评分脚本不单独处理。参考数值与页码见 answer-key.json。

## 门槛

- **GATE0**（整题）output/ 中 presentation.pptx、slides.pdf、script.md、scenario-data.xlsx、evidence-index.csv、playback-check.md 六件齐全，且 pptx 能被 python-pptx 读出幻灯片。 — 不过 ⇒ 全部判定记否，验收失败。
- **GATE1**（G6 组级）PowerPoint 无修复打开的结构代理（Linux 评测无法运行 PowerPoint）：pptx 为完整 zip，[Content_Types] 覆盖全部部件，所有内部关系目标存在，XML 良构，python-pptx 可打开，且无任何外部关系（超链接除外）。 — 不过 ⇒ G6 全部判否（checks.postprocess）。
- **GATE2**（整题）作弊/违规：访问评测隐藏文件、联网取材、用材料包以外来源的数据替换材料数据。 — 不过 ⇒ 整题 0，验收失败。

## 分组

### G1 叙事与结构（9 分，6 项）

- **N01** [base · 预期 0.92] 9–11 页、16:9，含标题页与结束页，无空分隔页。  
  验证：python-pptx: slide count, slide size ratio 16:9; every non-title slide has ≥1 fact-bearing element besides its title.
- **N02** [base · 预期 0.80] 每页标题都是完整论断（含谓语的判断句），不是话题标签。  
  验证：Reviewer reads all titles; any noun-phrase title ⇒ NO.
- **N03** [base · 预期 0.82] script.md 每页给时长，合计 11–13 分钟；每页演讲者备注与讲稿该页文字一致（归一化后相似度 ≥ 0.9）。  
  验证：Parse script.md timings; difflib ratio between notes and script per slide.
- **N04** [mid · 预期 0.55] 结束页直接回答开场问题：给出需求、发电结构、价格三方面 2050 区间的结论，并至少写出一条“该区间不能告诉规划者什么”。  
  验证：Reviewer: all three dimensions + ≥1 limit present on the closing slide (not only in notes).
- **N05** [mid · 预期 0.50] 术语按听众解释：至少对“情景/案例”“quad（千万亿 Btu）”“不变美元 vs 名义美元”“Henry Hub”在首次出现时给出一句话解释。  
  验证：Reviewer checks slides+notes; any of the four used without explanation ⇒ NO.
- **N06** [mid · 预期 0.50] 页面顺序形成论证链：每页论断都被后续页面或结论使用，无两页重复同一论断。  
  验证：Reviewer maps title claims to the closing answer; any orphan/duplicate ⇒ NO.

### G2 视觉设计与可读性（9 分，7 项）

- **V01** [base · 预期 0.75] 正文 ≥ 20 pt，图注/出处行与表格单元格文字 ≥ 12 pt。  
  验证：checks.py (deterministic): effective run size = explicit size, else shape list style, layout/master placeholder, master text styles or presentation default (18 pt), times normAutofit fontScale. Body text = body/content placeholders and text boxes with >=15 words or >=2 paragraphs averaging >=5 words; source/caption lines (starting 'Source', 'Note', ... or all runs <16 pt) and short labels are not body. Any body run <20 pt, any other run <12 pt, or an explicit table-cell size <12 pt => NO.
- **V02** [base · 预期 0.88] 每页 ≤ 6 条要点。  
  验证：checks.py (deterministic): per slide, the non-empty paragraphs of all body text frames (plus multi-paragraph labels) are summed; titles, source/caption lines and single-line callouts are not bullets; any slide with >6 => NO.
- **V03** [gate · 预期 0.30] 没有任何形状或原生表格超出页面范围，渲染页面中无明显的文字溢出、重叠或裁切。  
  验证：checks.py (fail-only): every top-level shape, incl. a table frame taken as the sum of its row heights, must lie inside slide width/height (1 pt tolerance); otherwise the judge inspects the rendered page tiles (LibreOffice render) for overflow, overlap and clipping.
- **V04** [mid · 预期 0.45] 以一致的视觉编码（颜色/标签/图例）区分“模型预测结果”“机构陈述”“演讲者推断”，并在页面上给出图例。  
  验证：Reviewer: coding present on every content slide that carries such claims; key visible.
- **V05** [mid · 预期 0.50] 每个图表的系列均有名称（无空名或“Series N”等默认名），数值轴标题（无数值轴的图表为图表标题）写明单位；货币类图表同时在该处写明价格口径（如 2025 美元、实际、名义）。  
  验证：checks.py (deterministic): python-pptx series names, value-axis and chart titles; unit tokens (kWh/TWh/quad/Btu/¢/$/%/...); money detected from price/¢/$/cost words in chart title, axis titles or series names; basis tokens 2025/real/nominal/constant.
- **V06** [gate · 预期 0.20] 同一情景在出现它的所有图表中颜色相同，且不同情景不共用颜色；图表中情景的排列顺序与名称与原生表格一致。  
  验证：checks.py (deterministic): series fill/line colour (or per-point c:dPt colour for single-series case-category charts; automatic colours by series index) per case across charts; chart case order must follow table row order; case labels compared after normalisation (text in parentheses ignored). No case-coded chart => judge.
- **V07** [mid · 预期 0.55] 至少 1 幅报告原图被干净裁切并保留图例，叠加 ≥ 2 个原生可编辑标注，指向与该页论断相关的具体元素。  
  验证：python-pptx picture + overlapping autoshapes; reviewer checks crop and relevance.

### G3 材料覆盖与隐藏考点（21 分，11 项）

- **C00** [base · 预期 0.85] 覆盖题面要求的全部主题：各情景需求、发电结构、电价、天然气价格，以及“用电在能源总量中的位置”，每项至少一页承载数据。  
  验证：Reviewer maps slides to topics.
- **C01** [base · 预期 0.85] 原生表格列出全部 11 个情景，名称与材料一致（基线情景用材料中的现名；若用旧称须注明改名）。  
  验证：checks.py: native-table row labels vs the 11 case names and their short forms (Combination row is not counted as AltElec/AltTrnp; cases as rows or columns). Baseline found only as 'Reference' => judge checks for the rename note.
- **C02** [mid · 预期 0.60 · 关键] 总用电（Total Electricity Use）数值正确：2025 ≈ 4,298 十亿kWh；2050 最低 AltTrnp ≈ 5,439、最高 HighElDmd ≈ 6,470、基线 ≈ 5,995（舍入误差内）。若改用售电量，须标明且数值对应表 8 售电行。  
  验证：Compare deck/table values with answer-key K02 (tolerance: displayed rounding ±0.5%).
- **C03** [mid · 预期 0.55] 基线 2050 发电结构份额正确（天然气 ≈ 41%、可再生 ≈ 46%、核电 ≈ 13%、煤 < 1%，±1 个百分点），或逐字引用报告 p16 的近似值并注页码。  
  验证：answer-key K09; Table 8 Total Net Electricity Generation by Fuel / total.
- **C04** [mid · 预期 0.55] 煤电：保留 2024 电厂 CO2 规则的情景 2050 煤电份额 < 1%，去掉该规则（AltElec/Combination）约 5%；并指明是该规则假设拉开差距。  
  验证：answer-key K08 (report p16 PDF p19; Table 8).
- **C05** [mid · 预期 0.50 · 关键] 价格区间正确（2025 美元）：2050 全部门平均终端电价 HighOGS ≈ 13.1 至 LowOGS ≈ 16.6 ¢/kWh、基线 ≈ 14.0；Henry Hub 2050 ≈ 2.7 至 13.7 $/MMBtu、基线 ≈ 4.6。  
  验证：answer-key K04 (Table 8 'All Sectors Average' 2025-cents row; Table 1 Henry Hub 2025-dollars row).
- **C06** [gate · 预期 0.25] 隐藏考点：明确说明基线情景不是预测、不是“最可能”情景（报告 p4，PDF p7，脚注 3），且全稿没有把任何情景或其结果描述为预测、最可能或预期结果（“模型预测为/该情景下”等中性表述不算）。  
  验证：Judge searches slides+notes+script for 'forecast|predict|most likely|expected outcome|base case' and decides whether a case is being characterised as the likely future.
- **C07** [gate · 预期 0.12 · 关键] 隐藏考点（附条件）：若简报给出任何数据中心服务器用电数值，须使用报告/图数据（2050 基线 ≈446、HighElDmd ≈819 十亿kWh）或情景说明表 3（800 / 1,440 TWh/yr）之值，并明确指出两份文件不一致（TWh 即十亿kWh，并非单位差异）；只悄悄引用其一或以单位不同解释掉判否。全稿没有服务器用电数值时判通过（计为通过，而非不适用）。  
  验证：checks.py: no 'data centre/center' or 'server' wording anywhere in slides, tables, charts, notes or script => pass; otherwise the judge searches for 1,440/1440/800/818/819/446 and checks the flag against answer-key K05.
- **C08** [mid · 预期 0.45] 高电力需求与高经济增长两情景用电年均增速相近（报告 p14 写 1.6% 与 1.5%/yr；表 8 计算约 1.65% 与 1.57%，任一口径均可），但驱动不同：前者按设计仅商业建筑（数据中心与制冷）增量，后者为全经济增长（报告 p14）。  
  验证：answer-key K11.
- **C09** [gate · 预期 0.15] 负荷形态与成本：AltTrnp 需求更低但配电在电价中的占比更高、HighElDmd 发电成本更高，且用表 8 分项电价（2025 美元）支持：AltTrnp 配电 ≈ 5.04 vs 基线 ≈ 4.92 ¢/kWh；HighElDmd 发电 ≈ 6.62 vs 6.41 ¢/kWh。  
  验证：answer-key K14; both directions with numbers ⇒ YES.
- **C10** [mid · 预期 0.45] 把用电放到能源总量背景中：基线 2050 购电 ≈ 19.0 quads，对应交付能源 ≈ 76.5 quads（≈ 25%）或总消费 ≈ 93.2 quads（含电力相关损失 ≈ 16.2 quads），并说明所用分母口径。  
  验证：answer-key K06; Table 2 rows.

### G4 逐页忠实度（10 分，8 项）

- **F00** [base · 预期 0.80] 每张含数字的页面都有可见出处行（文件 + 页或表/工作表）。  
  验证：python-pptx text search per slide; reviewer.
- **F01** [gate · 预期 0.25 · 关键] 原生表格中每个 2050/2025 数值都与源表一致（显示舍入内）；任一格错误即否。  
  验证：checks.py (deterministic): best native table (cases as rows or columns); each numeric column is fitted to ONE source quantity of input/tables/<case>_table<N>.xlsx (2025 or 2050 value, average annual change, growth, CAGR, change vs baseline, share of generation / delivered / total energy; unit scales x1, x1000, x1/1000, x100, x1/100, BkWh->quads) and every case cell must reproduce it within its displayed rounding; a 2025 reference row must equal the baseline 2025 value of the same row. Any cell off its column's source => NO; a column that cannot be tied to any source row => judge.
- **F02** [mid · 预期 0.45 · 关键] 每个图表系列的绘制数值（须同时存在于该图嵌入工作簿中）在其存储精度内与源表（或 figure-data.xlsx）一致；任一数据点错误或编造即否。  
  验证：checks.py (deterministic): series mapped to cases (series or categories named as cases) are fitted to one source row of input/tables (per point year); unmapped series must equal baseline rows or lie in one row/column of figure-data.xlsx (>=3 points); otherwise judge. Workbook containment is checked in D04.
- **F03** [mid · 预期 0.50] 需求页：所有数字与论断可追溯且正确。  
  验证：Reviewer vs evidence-index + answer-key.
- **F04** [mid · 预期 0.50] 发电结构/容量页：所有数字与论断可追溯且正确。  
  验证：Reviewer vs evidence-index + answer-key.
- **F05** [mid · 预期 0.45] 价格页：所有数字与论断可追溯且正确，且每个价格写明口径。  
  验证：Reviewer vs evidence-index + answer-key.
- **F06** [mid · 预期 0.55] 页面、备注与讲稿中没有任何未列入 evidence-index.csv 或与 answer-key 相矛盾的事实（如州级数据、其他机构数字、报告未载的政策细节）。  
  验证：Judge cross-reads slides/notes/script against evidence-index.csv and the answer key.
- **F07** [mid · 预期 0.45] evidence-index.csv 按固定随机种子抽 10 行（不足 10 行则全部），全部能在所列文件/页或单元格找到对应值或原文。  
  验证：checks.py (deterministic): PDF rows - the cited page (read as PDF page and as printed page + 3 / + 4 for case-descriptions) must contain a number of the claim or a 5-word phrase (or >=75% of the long words) of it; rows marked recalculation/conversion only need an existing cited page. xlsx rows - the cited sheet/cell(s) (A1 refs or 'row N col X') must hold a claim number (recalculated rows: a numeric cell). 10/10 => YES.

### G5 情景比较推理与口径归一（33 分，10 项）

- **R01** [gate · 预期 0.25 · 关键] 跨情景价格比较全部使用同一年份的不变美元（2025 美元）；任何页面/图/表未用名义价格比较或排序情景（名义下 LowEcon 2050 均价 ≈ 31.9¢ 会被误排为最贵，实际为 ≈ 13.6¢）。  
  验证：Check plotted/table price values against Table 8/Table 1 2025-dollar rows; any nominal-row value in a cross-case comparison ⇒ NO. answer-key K03.
- **R02** [gate · 预期 0.25 · 关键] 价格随时间变化以实际口径表述且正确：基线全部门均价 2025→2050 ≈ +3.8%（≈ +0.15%/yr，2025 美元）；若同时给名义值（≈ 23.2¢，+2.2%/yr）须标明名义且不作“涨价”结论依据。  
  验证：answer-key K15.
- **R03** [gate · 预期 0.20 · 关键] 电量换算正确：任何以 quads/Btu 表示的电量使用 3,412 Btu/kWh（结果与表 2 购电行差 ≤ 1%），并标明是交付口径还是含发电/输配损失的一次能源口径；不得把两种口径混比。  
  验证：answer-key K06; recompute deck numbers.
- **R04** [mid · 预期 0.55] 需求增长计算正确：2025–2050 总用电增长区间下端落在 25%–27%、上端落在 50%–51%（表 8 算得 +26.5% 与 +50.5%）；年均增速下端落在 0.9%–1.0%、上端落在 1.6%–1.7%（表 8 算得 0.95% 与 1.65%）。直接引用报告 p14/p15 的 25%–50%、0.9%–1.6% 也通过。  
  验证：answer-key K02; CAGR = (v2050/v2025)^(1/25)−1.
- **R05** [gate · 预期 0.15] AltTrnp 与基线 2050 年电量差须量化并写明所指量：售电量 −10.0% 或总用电 −9.3%（表 8）。若引用报告 p12（PDF p15）“售电少 9%”，须并列表 8 数值并指出差异。未量化即否。  
  验证：answer-key K07.
- **R06** [mid · 预期 0.50 · 关键] 每个差距归因到被改变的单一假设：需求低端←取消 MY2027+ 车辆尾气标准（AltTrnp/Combination）；需求高端←数据中心服务器假设（HighElDmd）/经济增长；价格区间←油气资源与技术假设（High/Low OGS）；煤电份额←2024 电厂 CO2 规则。四项全对才过。  
  验证：answer-key K10; case-descriptions pp4–8.
- **R07** [gate · 预期 0.30] 情景差以“情景 − 基线、同年同单位”表述；Combination 被说明为 AltElec 与 AltTrnp 假设的组合，而不是独立的第五种驱动。  
  验证：Reviewer; answer-key K10 (Combination Δuse −8.6% ≈ AltTrnp −9.3% + AltElec +0.6%).
- **R08** [gate · 预期 0.20] 气价—电价联动论证口径正确：展示 HighOGS/基线/LowOGS 的 2050 Henry Hub（2025 $/MMBtu）与均价（2025 ¢/kWh）同向变化；不得未换算就把 $/MMBtu 与 ¢/kWh 直接相减/相除（1 MMBtu = 293.07 kWh）。  
  验证：answer-key K04; reviewer checks any combined arithmetic.
- **R09** [mid · 预期 0.45] 附条件：若出现 GDP 或能源强度数值，须标明为 2012 年链式美元，且未与 2025 美元数值混用；若给出宏观增速假设，须与情景说明表 2 一致（实际 GDP 1.2%/1.7%/2.2%/年）。全稿未出现 GDP、能源强度或宏观增速数值时判通过。  
  验证：answer-key K12; judge checks every GDP/intensity/growth-assumption value in slides, notes and script.
- **R10** [mid · 预期 0.50] “区间不能告诉什么”至少两条有材料依据：情景不是概率、区间不是置信区间；全国口径非州级；政策截至 2025 年 12 月；模型不评估实验性技术（报告 p28）等。且全稿无概率化表述。  
  验证：Reviewer.

### G6 原生对象与交付（18 分，13 项）

- **D00** [base · 预期 0.70] 原生表格每个指标列的表头写明单位，货币列写明价格口径（年份美元或名义）。  
  验证：python-pptx table header cells.
- **D01** [base · 预期 0.92] 六件交付齐全；pptx 可解析。  
  验证：File check.
- **D02** [base · 预期 0.85] 存在原生表格（a:tbl graphicFrame，非图片/OLE），含 11 情景 × ≥ 5 个 2050 指标，并给出 2025 参照值。  
  验证：checks.py (deterministic): python-pptx has_table (a:tbl); cases as rows or columns; >=11 case rows + header and >=6 columns; a 2025 reference column/row/value is required ('2025' used only as a price-basis label such as '2025 ¢/kWh' or '2025 $' does not count).
- **D03** [base · 预期 0.85] ≥ 3 个原生图表（c:chart），各带嵌入工作簿。  
  验证：python-pptx has_chart; chart part has embedded xlsx.
- **D04** [gate · 预期 0.35] 每个图表的嵌入工作簿包含所绘数值，并另有写明单位、价格口径（货币类图表）与出处位置（文件 + 工作表/单元格或页码）的文字单元格。  
  验证：checks.py (deterministic): unzip each embedded workbook; every plotted cache value must be a workbook number; strings must contain a unit token (kWh|TWh|quad|Btu|¢|cents|$|%|unit), a location token (table N|.xlsx|.pdf|sheet|cell|row N|A1 ref|page|p.N|figure-data) and, for money charts, a basis token (2025|nominal|real|constant). 'Edit Data opens in PowerPoint' is covered by the GATE1 structural proxy.
- **D05** [gate · 预期 0.20 · 关键] 表–图一致：同时出现在原生表格与图表中的每个数值显示完全一致（数字、单位、口径、舍入），且都与源表一致。  
  验证：checks.py (deterministic): native-table columns and chart series are each fitted to a source quantity (see F01/F02); wherever both show the same quantity for the same case and year, the chart value formatted with its number format (General format: raw value within the table's rounding) must equal the table cell and use the same unit scale, otherwise NO. No shared value => YES. Table columns that cannot be fitted => judge.
- **D06** [mid · 预期 0.60] 电价图：≥ 4 个情景的表 8 全部门平均电价，覆盖 2025–2050（数据点取自源表年份、首末为 2025 与 2050，或各情景 2025–2050 年均值），无编造插值。  
  验证：checks.py (deterministic): a chart whose series or categories map to >=4 cases; year categories must start at 2025 and end at 2050 and every point must equal Table 8 'All Sectors Average' (2025 cents, or nominal if the chart says nominal; also accepted in $/kWh) within stored precision; year-less bars must equal the 26-year mean.
- **D07** [base · 预期 0.90] 每页都有演讲者备注。  
  验证：python-pptx notes_slide text non-empty.
- **D08** [mid · 预期 0.50] scenario-data.xlsx：≥ 80% 的派生数值为引用源值单元格的实时公式，且每行写明源文件与位置。  
  验证：openpyxl formulas vs values.
- **D09** [base · 预期 0.80] evidence-index.csv 字段齐全（页号、元素、论断、源文件、页/单元格、变换），每个承载事实的元素至少一行。  
  验证：CSV schema + count vs slide elements.
- **D10** [mid · 预期 0.60] slides.pdf 与 pptx 页数相同，且每页含对应幻灯片标题（顺序一致）。  
  验证：checks.py: pypdf page count vs slide count; >=80% of each slide title's words on the same pdftotext page.
- **D11** [mid · 预期 0.45] playback-check.md 写明软件与版本、实际做过的检查及结果，并列出未能验证项；无无法证实的声明。  
  验证：Judge reads playback-check.md against the delivered files.
- **D12** [base · 预期 0.88] 标明 AI 辅助制作、对源文件署名、未暗示机构背书。  
  验证：Reviewer.

## 预期分计算

- 判定数：55（base 15 / mid 26 / gate 14）
- 分值占比：base 21.8 / mid 46.1 / gate 32.1（满分 100）
- 预期分 = Σ（单项权重 × 预期通过率）
- **预期分 ≈ 48.9**（设计估计，未经实测校准）
  - G1：6.1 / 9
  - G2：4.7 / 9
  - G3：10.2 / 21
  - G4：4.9 / 10
  - G5：11.1 / 33
  - G6：11.9 / 18
