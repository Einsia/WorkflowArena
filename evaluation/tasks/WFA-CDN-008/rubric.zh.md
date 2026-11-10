# WFA-CDN-008 隐藏评分表（审核专用）

由 rubric.json 生成。共 14 个独立二元判定；部分满足即判否。

整题门槛（只两种）：交付物缺失/无法解码；作弊（访问审核材料、联网、生成式替代）。组级门槛：某段诚实检查失败 → 该段 G 项记 0。另报告“槽位正确数/7”。

| ID | 层 | 组 | 判定 | 怎么验证 | 预期通过率 | 权重 |
|---|---|---|---|---|---|---|
| B1 | base | deliverable | 交付物与编码：output/ 恰为 solution.mp4、solution.json、selection-evidence.json 三个文件；视频可完整解码，H.264/yuv420p、1280×720、SAR 1:1、30/1 CFR、无音轨。 | ffprobe 流参数 + 全量解码计帧；ls output/。 | 0.90 | 9 |
| B2 | base | manifest | 清单一致：7 段；source 为 01–46 中合法且互不相同的 ID；thread/beat 字段齐全；整数半开帧区间自 0 连续无缝；秒=帧/30（≤0.001 s）；最后结束帧=解码帧数；source_frames=[0,该片段帧数]。 | 解析 JSON，对照 provenance.json 中各片段帧数确定性检查。 | 0.85 | 8 |
| B3 | base | honesty | 诚实与完整（7 段全部）：每段输出帧数等于所称片段解码帧数，且逐帧 SSIM≥0.95（灰度、最长边 360 px、11×11 高斯窗 σ=1.5），首尾帧均包含。 | 逐段逐帧 SSIM（所称片段 vs 输出对应帧）。某段不过则该段对应的 G 项同时记 0（组级门槛）。 | 0.85 | 8 |
| M1 | mid | content-A | 线索 A 内容判读：A1–A4 四段的 source 都落在各自的“正确内容族”（正确片段、同节选的合成变体、同一原始镜头的相邻窗口，见 answer-key content_family）。 | 查表，确定性。 | 0.55 | 10 |
| M2 | mid | content-B | 线索 B 内容判读：B1–B3 三段的 source 都落在各自的正确内容族（定义同 M1；B2 的内容族另含紧接其后的同一礁檐镜头 27、44，见 answer-key content_family）。 | 查表，确定性。 | 0.6 | 10 |
| M3 | mid | intercut | 交叉组接结构：输出顺序的 beat 标注恰为 A1,B1,A2,B2,A3,B3,A4，且每段 thread 与 beat 前缀一致。 | JSON 字段确定性检查。 | 0.7 | 10 |
| M4 | mid | evidence | 选择证据：模式合法（7 条、beat 互不相同、source 与 solution.json 中该 beat 的 source 一致、source_frames 在片段内且 b−a ≥ 12、reason 非空），且 7 条中至少 6 条 reason 指出所选片段与一个具名其他候选之间的具体可见差别，并与 answer-key 对该候选的说明不矛盾。 | 模式部分由 checks.py 确定性检查（不满足直接判否）；通过后由评委只对照 answer-key beats.*.why 文本判定 reason 内容，不要求查看源帧，也不要求人工复核。 | 0.45 | 10 |
| G1 | gate | select-A1 | A1 精确选择：所选 ID 等于隐藏答案（13）。近似干扰：25、37、34。前提：该段 B3 诚实检查通过。 | 查表，确定性。干扰说明：25: SAME excerpt time-reversed (camera retreats, mound shrinks); 37: same shot later — slides past the mound flank, mound leaves frame right, sand revealed; 34: deeper darker mound, no surface visible, drifting | 0.30 | 5 |
| G2 | gate | select-B1 | B1 精确选择：所选 ID 等于隐藏答案（01）。近似干扰：06、26、14、15。前提：该段 B3 诚实检查通过。 | 查表，确定性。干扰说明：06: SAME excerpt + synthetic progressive digital push-in 1.00→1.30 (fails handheld hover); 26: same shot earlier — ~3 s sustained lateral sweep at the start, no dark fish; 14: tang school arriving over a dark mound while camera pushes forward; 15: reef flat with scattered fish, sideways drift, no dense school | 0.25 | 5 |
| G3 | gate | select-A2 | A2 精确选择：所选 ID 等于隐藏答案（19）。近似干扰：24、43、16。前提：该段 B3 诚实检查通过。 | 查表，确定性。干扰说明：24: SAME excerpt time-reversed (descends back behind the table edge, ends close on branches); 43: same shot earlier — approaches table-coral tree from below, never clears the top; 16: same shot later — starts over sand, lateral drift to another table coral | 0.30 | 5 |
| G4 | gate | select-B2 | B2 精确选择：所选 ID 等于隐藏答案（39）。近似干扰：02、27、44。前提：该段 B3 诚实检查通过。 | 查表，确定性。干扰说明：02: SAME excerpt time-reversed (pulls away from the overhang, fish recede into shadow); 27/44: next shot — already under the overhang, lit, hovering, fish visible from frame 0 | 0.30 | 5 |
| G5 | gate | select-A3 | A3 精确选择：所选 ID 等于隐藏答案（46）。近似干扰：07、36、41。前提：该段 B3 诚实检查通过。 | 查表，确定性。干扰说明：07: earlier window + synthetic digital zoom 1.0→1.6 toward the urchin (urchin grows but no parallax: near seabed and reef lip scale together, softer pixels); 36: SAME excerpt time-reversed (retreats, urchin shrinks); 41: same shot earlier — hollow/ledge dominant, urchin stays small, lateral component | 0.15 | 5 |
| G6 | gate | select-B3 | B3 精确选择：所选 ID 等于隐藏答案（42）。近似干扰：45、09、20。前提：该段 B3 诚实检查通过。 | 查表，确定性。干扰说明：45: SAME excerpt mirrored (background streams right→left, camera follows to frame-right); 09: reef slope, camera drifts while a shark crosses briefly, no follow; 20: same shot later — sharks leave frame, camera continues over rubble | 0.20 | 5 |
| G7 | gate | select-A4 | A4 精确选择：所选 ID 等于隐藏答案（33）。近似干扰：22、04、40、32。前提：该段 B3 诚实检查通过。 | 查表，确定性。干扰说明：22: SAME excerpt + synthetic slow digital push-in 1.00→1.25; 04: SAME excerpt + synthetic lateral crop pan (82% window); 40: same shot later — slow real forward push, butterflyfish pass early; 32: other table reef in lighter cyan water with damselfish school, swaying hover, no butterflyfish entry | 0.15 | 5 |

## 答案键摘要

| 输出位 | 分镜 | 答案 | 运镜类别 | 内容族 | 近似干扰 |
|---|---|---|---|---|---|
| 1 | A1 | 13 | forward swim-in (real) | 13,25,37 | 25,37,34 |
| 2 | B1 | 01 | handheld hover | 01,06,26 | 06,26,14,15 |
| 3 | A2 | 19 | forward + rise over top (crane-like, ends high angle) | 16,19,24,43 | 24,43,16 |
| 4 | B2 | 39 | low slow push, settles | 02,27,39,44 | 02,27,44 |
| 5 | A3 | 46 | dolly-in with parallax (vs digital zoom) | 07,36,41,46 | 07,36,41 |
| 6 | B3 | 42 | lateral tracking, background L→R | 20,42,45 | 45,09,20 |
| 7 | A4 | 33 | locked-off hover | 04,22,33,40 | 22,04,40,32 |

## 预期分计算

分层权重：基础层 25、中间层 40、门槛层 35（合计 100）。

预期分 = Σ 权重 × 预期通过率 = 9×0.90 + 8×0.85 + 8×0.85 + 10×0.55 + 10×0.60 + 10×0.70 + 10×0.45 + 5×0.30 + 5×0.25 + 5×0.30 + 5×0.30 + 5×0.15 + 5×0.20 + 5×0.15 = **53.0**

- 基础层期望 21.7 / 25
- 中间层期望 23.0 / 40
- 门槛层期望 8.2 / 35

以上为设计目标，未经实测校准。Perfect（全部判定通过）预期 <5%。
