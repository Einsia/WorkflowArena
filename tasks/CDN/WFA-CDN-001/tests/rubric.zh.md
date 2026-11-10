# WFA-CDN-001 隐藏评分标准（由 rubric.json 生成）

判定 14 条，相互独立、二元；部分满足即判否。

| id | 层 | 组 | 权重 | 预期通过率 | 判定 | 怎么验证 |
|---|---|---|---|---|---|---|
| B1 | base | delivery | 6.25 | 0.92 | output/assembly.mp4 存在且可完整解码；H.264/yuv420p，1280×720，SAR 1:1，30/1 CFR，无音轨。 | ffprobe 字段核对 + 全解码无错误。缺失/不可解码 = 整题验收失败（连续分照常报告）。 |
| B2 | base | delivery | 6.25 | 0.85 | selection.json 结构有效：恰好 7 个对象按 slot 1–7 排序；source 为 01–40 中互不相同的两位字符串；source_frames、output_frames 为整数半开区间，b−a=d−c，source_frames 在片段帧数内；含 closest_alternative 与 reason 字段。 | 确定性 JSON 校验；片段帧数取自 provenance.json。selection.json 不可解析 = selection 组记 0。 |
| B3 | base | assembly | 6.25 | 0.85 | 总长合同：output_frames 从 0 起首尾相接，最后结束帧 = 1650 = assembly.mp4 实际解码帧数。 | 确定性：ffprobe -count_frames 与 JSON 比对，须全部等于 1650。 |
| B4 | base | delivery | 6.25 | 0.9 | output/ 中恰好只有 assembly.mp4 与 selection.json 两个文件。 | 确定性目录列举。 |
| M1 | mid | assembly | 8 | 0.72 | 素材诚实：7 段全部与各自声明的片段区间逐帧一致（1×、正向、无缩放裁切滤镜），段间为硬切（无转场帧、无黑场插入）。 | 确定性：每个输出帧与声明的源帧 SSIM≥0.95（灰度，长边 360px，11×11 高斯 σ=1.5）；任一帧不符即判否。 |
| M2 | mid | selection | 8 | 0.6 | 槽4 所选 ID 等于隐藏答案（35），且该段画面与所声称片段的声明区间逐帧一致。 | 确定性：selection.json slots[3].source == "35"；对应 output_frames 段逐帧 SSIM≥0.95（灰度，长边 360px）对所声称 source_frames。近似干扰：28 24 13。内容/首尾镜头可区分。 |
| M3 | mid | selection | 8 | 0.62 | 槽5 所选 ID 等于隐藏答案（05），且该段画面与所声称片段的声明区间逐帧一致。 | 确定性：selection.json slots[4].source == "05"；对应 output_frames 段逐帧 SSIM≥0.95（灰度，长边 360px）对所声称 source_frames。近似干扰：09 40 08。内容/首尾镜头可区分。 |
| M4 | mid | assembly | 8 | 0.55 | 裁剪合同：对所有选对的槽，所用区间完整覆盖该片段的隐藏必保区间（保留了描述中的全部镜头与运镜过程）；至少选对 2 槽才判定，否则判否。 | 确定性：answer-key.json 的 must_keep_source_frames ⊆ source_frames。必保区间按宽松口径设定（仅要求每个描述镜头/运镜阶段出现，首尾留余量）。 |
| M5 | mid | selection | 8 | 0.5 | 近似辨识：至少 4 个槽的 closest_alternative 属于该槽的隐藏近似干扰集合且 reason 非空；这些槽的 reason 指出所选片段与该候选之间的一个具体可见差别，并与 answer-key 中该干扰的 why 说明一致（不矛盾）。 | 集合成员与 reason 非空为确定性检查（checks.py，满足条件的槽 <4 直接判否）；≥4 时由评委只对照 answer-key near_miss.why 判断这些 reason 是否具体且不矛盾，不要求查看源片段。 |
| G1 | gate | selection | 7 | 0.25 | 槽1 所选 ID 等于隐藏答案（39），且该段画面与所声称片段的声明区间逐帧一致。 | 确定性：selection.json slots[0].source == "39"；对应 output_frames 段逐帧 SSIM≥0.95（灰度，长边 360px）对所声称 source_frames。近似干扰：37 31 23。运镜依赖槽：干扰含同窗合成运镜变体，首帧与答案近同。 |
| G2 | gate | selection | 7 | 0.15 | 槽2 所选 ID 等于隐藏答案（06），且该段画面与所声称片段的声明区间逐帧一致。 | 确定性：selection.json slots[1].source == "06"；对应 output_frames 段逐帧 SSIM≥0.95（灰度，长边 360px）对所声称 source_frames。近似干扰：14 22 32 25。运镜依赖槽：干扰含同窗合成运镜变体，首帧与答案近同。 |
| G3 | gate | selection | 7 | 0.25 | 槽3 所选 ID 等于隐藏答案（29），且该段画面与所声称片段的声明区间逐帧一致。 | 确定性：selection.json slots[2].source == "29"；对应 output_frames 段逐帧 SSIM≥0.95（灰度，长边 360px）对所声称 source_frames。近似干扰：30 04 33 11。运镜依赖槽：干扰含同窗合成运镜变体，首帧与答案近同。 |
| G4 | gate | selection | 7 | 0.2 | 槽6 所选 ID 等于隐藏答案（27），且该段画面与所声称片段的声明区间逐帧一致。 | 确定性：selection.json slots[5].source == "27"；对应 output_frames 段逐帧 SSIM≥0.95（灰度，长边 360px）对所声称 source_frames。近似干扰：16 18 26 07。运镜依赖槽：干扰含同窗合成运镜变体，首帧与答案近同。 |
| G5 | gate | selection | 7 | 0.3 | 槽7 所选 ID 等于隐藏答案（19），且该段画面与所声称片段的声明区间逐帧一致。 | 确定性：selection.json slots[6].source == "19"；对应 output_frames 段逐帧 SSIM≥0.95（灰度，长边 360px）对所声称 source_frames。近似干扰：12 17 21 15。运镜依赖槽：干扰含同窗合成运镜变体，首帧与答案近同。 |

## 门槛
- 整题验收失败：assembly.mp4 缺失或无法解码；作弊（读 reviewer-only、联网、生成替代画面）。连续分照常报告。
- 组级：selection.json 无法解析 → selection 组（B2、M2、M3、M5、G1–G5）记 0。
- 另报：选对槽数 / 7。

## 答案摘要
| 槽 | 答案 | 必保区间(源帧) | 运镜依赖 | 近似干扰 |
|---|---|---|---|---|
| 1 | 39 | [45, 210] | 是 | 37, 31, 23 |
| 2 | 06 | [60, 200] | 是 | 14, 22, 32, 25 |
| 3 | 29 | [45, 240] | 是 | 30, 04, 33, 11 |
| 4 | 35 | [6, 330] | 否 | 28, 24, 13 |
| 5 | 05 | [5, 225] | 否 | 09, 40, 08 |
| 6 | 27 | [10, 235] | 是 | 16, 18, 26, 07 |
| 7 | 19 | [60, 255] | 是 | 12, 17, 21, 15 |

可行性：必保区间合计 1464 帧 ≤ 1650 ≤ 正确片段全长合计 1920 帧。

## 预期分计算（设计目标，未实测）
- base：4 条，权重 25.0，期望得分 22.00（层内平均通过率 0.88）
- mid：5 条，权重 40，期望得分 23.92（层内平均通过率 0.60）
- gate：5 条，权重 35，期望得分 8.05（层内平均通过率 0.23）
- **预期分 = 53.97**（目标带 45–55）
