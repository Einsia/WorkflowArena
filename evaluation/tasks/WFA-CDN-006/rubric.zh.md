# WFA-CDN-006 隐藏评分表（由 rubric.json 生成）

连续分 = Σ 通过判定的 weight（满分 100）。组级门槛：某版本的 F1/F2（格式）或 F4/F5（诚实）不过，则该版本全部 selection 判定记 0。整题验收失败仅限：output/ 交付物缺失/无法解码，或作弊（读取隐藏文件、联网、生成画面）。另报告“槽位正确数/10”与 Perfect（全部判定通过）。

| id | 层 | 组 | 关键 | 判定 | 怎么验证 | 预期通过率 | 权重 |
|---|---|---|---|---|---|---|---|
| F1 | base | format | 是 | comedy.mp4 可解码且格式合规：H.264/yuv420p、640×360、SAR 1:1、24/1 CFR、无音轨。 | ffprobe 字段核对 + ffmpeg -f null 全解码无错误；任何一项不符判否。 | 0.92 | 5.000 |
| F2 | base | format | 是 | suspense.mp4 同 F1 全部格式要求。 | 同 F1。 | 0.92 | 5.000 |
| F3 | base | manifest |  | edl.json 结构合法：两版各恰 5 段、slot 标签正确、source 为存在的两位编号、同版内互不重复；output_frames 半开连续自 0 起；秒=帧/24 误差≤0.001；每版末帧=对应 mp4 实际解码帧数；source_frames=[0,该片段解码帧数]；output/ 恰为 4 个文件。 | 确定性脚本：解析 JSON，ffprobe -count_frames 取每版与每个 input 片段帧数逐项比对。 | 0.85 | 5.000 |
| F4 | base | honesty | 是 | comedy.mp4 诚实与完整：每段帧数等于所声明片段的解码帧数，且逐帧 SSIM≥0.95（灰度、11×11 高斯窗 σ=1.5，原尺寸 640×360），首尾帧均包含（无裁切、变速、调色、转场）。 | 按 edl.json 的 output_frames 切分，逐帧对比所声明 input/NN.mp4；任一段任一帧不达标判否。 | 0.85 | 5.000 |
| F5 | base | honesty | 是 | suspense.mp4 诚实与完整：同 F4。 | 同 F4。 | 0.85 | 5.000 |
| S-A1 | mid | selection-comedy |  | 喜剧 版槽 A1 亮相与反讽 所选 source 等于隐藏答案（23）。近似干扰：08, 22, 03, 33。 | 确定性：读取 edl.json 中 comedy 第 1 段 source 与 answer-key.json 比对；所属版本 F1/F2 或 F4/F5 不通过时本组记 0（组级门槛）。 | 0.55 | 5.714 |
| S-A2 | mid | selection-comedy |  | 喜剧 版槽 A2 探头包袱 所选 source 等于隐藏答案（35）。近似干扰：15, 18, 25。 | 确定性：读取 edl.json 中 comedy 第 2 段 source 与 answer-key.json 比对；所属版本 F1/F2 或 F4/F5 不通过时本组记 0（组级门槛）。 有意设计（同一素材池两种意图）：A2/B3 共用答案 35、A4/B2 共用答案 27，同一辨别在两版各计一次。 | 0.55 | 5.714 |
| S-A5 | mid | selection-comedy |  | 喜剧 版槽 A5 收尾包袱 所选 source 等于隐藏答案（39）。近似干扰：36, 30, 21, 28。 | 确定性：读取 edl.json 中 comedy 第 5 段 source 与 answer-key.json 比对；所属版本 F1/F2 或 F4/F5 不通过时本组记 0（组级门槛）。 | 0.60 | 5.714 |
| S-B1 | mid | selection-suspense |  | 悬疑 版槽 B1 被窥视 所选 source 等于隐藏答案（31）。近似干扰：10, 07, 01。 | 确定性：读取 edl.json 中 suspense 第 1 段 source 与 answer-key.json 比对；所属版本 F1/F2 或 F4/F5 不通过时本组记 0（组级门槛）。 | 0.50 | 5.714 |
| S-B3 | mid | selection-suspense |  | 悬疑 版槽 B3 窥伺与突袭 所选 source 等于隐藏答案（35）。近似干扰：15, 18, 25。 | 确定性：读取 edl.json 中 suspense 第 3 段 source 与 answer-key.json 比对；所属版本 F1/F2 或 F4/F5 不通过时本组记 0（组级门槛）。 有意设计（同一素材池两种意图）：A2/B3 共用答案 35、A4/B2 共用答案 27，同一辨别在两版各计一次。 | 0.5 | 5.714 |
| S-B5 | mid | selection-suspense |  | 悬疑 版槽 B5 尾钩 所选 source 等于隐藏答案（17）。近似干扰：29, 11, 06, 04。 | 确定性：读取 edl.json 中 suspense 第 5 段 source 与 answer-key.json 比对；所属版本 F1/F2 或 F4/F5 不通过时本组记 0（组级门槛）。 | 0.50 | 5.714 |
| S-A3 | gate | selection-comedy |  | 喜剧 版槽 A3 连环险情（须含升级与结果） 所选 source 等于隐藏答案（09）。近似干扰：37, 19, 14, 16。 | 确定性：读取 edl.json 中 comedy 第 3 段 source 与 answer-key.json 比对；所属版本 F1/F2 或 F4/F5 不通过时本组记 0（组级门槛）。 | 0.20 | 8.750 |
| S-A4 | gate | selection-comedy |  | 喜剧 版槽 A4 体量反差（须看到入画） 所选 source 等于隐藏答案（27）。近似干扰：34, 32, 26, 14。 | 确定性：读取 edl.json 中 comedy 第 4 段 source 与 answer-key.json 比对；所属版本 F1/F2 或 F4/F5 不通过时本组记 0（组级门槛）。 有意设计（同一素材池两种意图）：A2/B3 共用答案 35、A4/B2 共用答案 27，同一辨别在两版各计一次。 | 0.3 | 8.75 |
| S-B2 | gate | selection-suspense |  | 悬疑 版槽 B2 身后的威胁（须看到入画） 所选 source 等于隐藏答案（27）。近似干扰：34, 14, 32, 26。 | 确定性：读取 edl.json 中 suspense 第 2 段 source 与 answer-key.json 比对；所属版本 F1/F2 或 F4/F5 不通过时本组记 0（组级门槛）。 有意设计（同一素材池两种意图）：A2/B3 共用答案 35、A4/B2 共用答案 27，同一辨别在两版各计一次。 | 0.25 | 8.75 |
| S-B4 | gate | selection-suspense |  | 悬疑 版槽 B4 延宕与惊吓（结果揭晓前切出） 所选 source 等于隐藏答案（19）。近似干扰：37, 09, 16。 | 确定性：读取 edl.json 中 suspense 第 4 段 source 与 answer-key.json 比对；所属版本 F1/F2 或 F4/F5 不通过时本组记 0（组级门槛）。 | 0.15 | 8.750 |
| E1 | mid | evidence |  | selection-evidence.json 完整：10 条与 edl 版本×槽一致，source_frames 合法（b−a≥12、在片段内），reason 至少 10 个字符；且至少 8 条 reason 指出所选片段与其他候选之间的具体可见差别（起止画面、镜头数、事件有无等），且不与 answer-key 对所提及候选的说明矛盾。 | 格式部分由 checks.py 确定性检查（不满足直接判否）；通过后由评委只对照 answer-key 的 why_correct / near_miss.why_wrong 文本判定 reason 内容，不要求查看源片段，也不要求人工复核。 | 0.45 | 5.716 |

## 答案速览

- 喜剧：23 → 35 → 09 → 27 → 39
- 悬疑：31 → 27 → 35 → 19 → 17
- 共享片段：35（A2↔B3）、27（A4↔B2）；同场景按意图分相位：09→A3，19→B4。

## 门槛层设计说明

- A3 vs B4：同一场连环险情的不同入出点。A3 要“升级+结果”（09），B4 要“单次逼近、结果揭晓前切出”（19）；37 只含一次险情且交代结果，两边都不对。只看缩略图或只看前几秒无法区分。
- A4/B2：同一片段 27 在两版位置不同；34 是同一构图但巨兔在第 0 帧已入画，必须看到入画过程才能排除。

## 预期分计算

- base：5 条，权重合计 25.000，期望得分 21.95（平均通过率 0.88）
- mid：7 条，权重合计 40.000（6×5.714 + E1 5.716），期望得分 20.86（平均通过率 0.52）
- gate：4 条，权重合计 35.000，期望得分 7.88（平均通过率 0.23）
- **预期分 = 21.95 + 20.86 + 7.88 = 50.68 ≈ 50.7**（设计目标 45–55；未经实测校准；以 rubric.json 为准，PROGRESS DONE 行的 21.8/21.1/7.8 为早期估算，已作废）
