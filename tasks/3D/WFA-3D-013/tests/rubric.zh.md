# WFA-3D-013 Attic Storm 隐藏评分标准（REVIEWER ONLY）

> 2026-10-25 清理后由 tests/rubric.json 自动生成；以 rubric.json 为准。

每条判定二元（0/1），部分满足即0。reward = Σ(权重×通过)/Σ(权重)（权重合计100）。除 G01 与 G11 的画面部分由评委看成片联系表判定外（且仅在其机测部分通过时），其余全部由 checks.py 机测（ffprobe/ffmpeg 解码、numpy 音频分析、Blender 后台逐帧导出与低采样重渲）。按 events.csv 声明帧测量；片中第 f 帧对应场景第 frame_start+f 帧。Blender 导出超时/脚本错误时相关条目各自判否并写明原因。

| id | 层 | 组 | 关键 | 权重 | 判定 | 怎么验证 | 预期通过率 |
|---|---|---|---|---|---|---|---|
| B01 | base | delivery | ★ | 3.125 | 基础版成片编码契约：H.264、yuv420p、1280×536、SAR 1:1、恒定 24 fps、解码恰好 672 帧。 | ffprobe 流参数 + 逐帧解码计数；r_frame_rate=avg_frame_rate=24/1。 | 0.88 |
| B02 | base | delivery |  | 3.125 | 音频契约：AAC 立体声 48 kHz，时长覆盖全部画面（差值 ≤ 1 帧）。 | ffprobe 音频流；音视频时长差 ≤ 41.7 ms。 | 0.9 |
| B03 | base | delivery |  | 3.125 | 母带：两版综合响度 −23 ±1 LUFS，真峰值 ≤ −1 dBTP，无连续 ≥3 个满幅采样。 | ffmpeg ebur128=peak=true 两版；解码 PCM 查削波。 | 0.75 |
| B04 | base | delivery |  | 3.125 | 修订版编码契约同基础版（672 帧、1280×536、24 fps CFR），且有 revision/timeline.json。 | 同 B01 对 revision/output.mp4；文件存在且 JSON 可解析。 | 0.85 |
| B05 | base | delivery |  | 3.125 | 三条分轨齐全（48 kHz PCM、28.0 s ±1 帧），按声明母带增益相加后与解码混音一致：1/3 倍频程带能量（100 ms 帧，50 Hz–14 kHz，仅计该帧最强带以下 40 dB 内的带）逐点差绝对值中位数 ≤ 0.75 dB、95 分位 ≤ 3 dB。 | 解码 AAC 至 48k；对齐（允许 ≤2048 样本编码延迟）后比带能量。不用波形相减：AAC 对高频噪声（雨）用 PNS 等感知编码，正确混音的波形残差也可达 −5 dB。 | 0.75 |
| B06 | base | delivery |  | 3.125 | events.csv 表头准确，11 个必需事件齐全，帧号为 0 起算的成片帧（frame=round(t×24)）0–671 整数，且时序合理：line_start<line_end；window_burst 在 S2 [144,264)；flash_peak 在 258–270；thunder_1>flash_peak；lamp_swing_start≥window_burst；curtain_grab<window_shut≤latch_click；thunder_far 在 S5（S5 自叠化起点第 540 帧起算，即 540–671）。 | checks.py：CSV 解析 + 上述规则表。 | 0.85 |
| B07 | base | delivery | ★ | 3.125 | project/scene.blend 可在 Blender 4.3 后台打开；全部必需对象名存在且类型正确（MARA_RIG 为 ARMATURE、LAMP_LIGHT/LIGHTNING 为 LIGHT、CAM_S1–S5 为 CAMERA）；场景存在自定义属性 dissolve_frames。 | checks.py：blender -b -y scene.blend 静态导出（_cdc_blend.rich_dump，只求值第 0 帧，超时 600 s）对象表与场景属性。逐帧导出的超时/错误不影响本条（相关条目各自判否）。 | 0.8 |
| B08 | base | delivery |  | 3.125 | credits.md 与 qa.md 存在（qa.md 非空）；credits.md 说明台词制作方式（如 espeak-ng/TTS/合成/录制）；交付文本文件与 scene.blend 媒体路径中无凭据、无联网 TTS/付费服务调用痕迹（服务端点、API key）、无 URL 媒体引用。仅提及服务名（如“未使用 ElevenLabs”）不算痕迹。 | checks.py：文件存在性 + 制作方式关键词 + 凭据/服务端点/URL 媒体正则；scene.blend 的 images/sounds/movieclips/libraries 路径不含 "://"。 | 0.9 |
| M01 | mid | edit | ★ | 3.3333 | 镜头结构：恰好五个镜头 S1→S5；T12 在 144±1、T34 在 408±1 为硬切且无混合帧（相邻帧差 < 切点帧差的35%）；其他位置无硬切（141–147、405–411、闪电窗 250–285、叠化 534–570 之外）；T45 叠化在 539–565 内有 ≥16 个混合帧（该帧在4倍降采样模糊亮度上可由第 538、566 帧线性组合拟合，R²≥0.85，混合比例5–95%）；无定格（全分辨率解码后连续 ≥6 帧且每帧与前一帧 PSNR ≥60 dB，即除编码噪声外完全相同；带渲染噪声或任何运动的固定机位不算）；若工程用时间线标记绑定相机，则第 72/200/330/480/620 帧的活动相机须依次为 CAM_S1…CAM_S5（未绑定时由 G10 按 CAM_Sn 重渲验证）。（片中第 f 帧 = 场景第 frame_start+f 帧） | checks.py：320 px 灰度帧差硬切检测 + 混合帧线性拟合 + 全分辨率逐帧流式 PSNR 定格检测 + Blender 标记/相机绑定。 | 0.6 |
| M02 | mid | sound_edit | ★ | 3.3333 | 对白 L-cut：dialogue 分轨中台词在 S1 内起音，并在 6.50 ±0.084 s（±2 帧）结束（之后 ≤ −50 dBFS，至 S2 结束）；全片仅此一句台词。 | checks.py：dialogue 分轨 20 ms RMS 包络，−40 dBFS 门限定起止（停顿 <0.4 s 合并）；首段之后至 11 s ≤ −50 dBFS 且无第二段。 | 0.55 |
| M03 | mid | sound_edit |  | 3.3333 | 台词声明准确：dialogue 分轨实测起止（20 ms RMS、−40 dBFS 门限，同 M02）与 events.csv 的 line_start/line_end 相差均 ≤4 帧。（可懂度不计分：评分镜像无 ASR 模型。） | checks.py：M02 的实测起止 vs 声明帧/24。 | 0.6 |
| M04 | mid | character |  | 3.3333 | 口型同步：在台词区间（实测起点前6帧至终点后6帧）内，MARA 至少一条口部通道（MARA_RIG 上 jaw/chin/mouth/lip/teeth 姿态骨的旋转角或位移，或受 MARA_RIG 驱动网格上的 jaw/mouth/viseme 形态键）与 dialogue 分轨 24 fps RMS 包络在 ±2 帧（≤83 ms）滞后内相关系数 r ≥0.4。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 逐帧导出口部骨骼 matrix_basis 旋转角/位移与形态键值；checks.py 求各滞后皮尔逊相关取最大。 | 0.4 |
| M05 | mid | camera | ★ | 3.3333 | 基于工程数据的镜头语法（宽松；等效焦距=lens×36/传感器宽，竖向适配时 lens×24/传感器高）：S1（CAM_S1，0–143）平视（每帧相机高度在 MARA 眼高 ±0.4 m 内、/俯仰/≤10°），推近 ≥0.05 m（沿初始视轴或朝 MARA），等效焦距 35–60 mm 且不变；S2（CAM_S2，144–263）手持：相对15帧滑动平均的最大位置偏离 2–60 mm（或视向抖动 ≥0.15° 且位置抖动 ≤60 mm），且非纯正弦（抖动频谱最强相邻3个频点能量占比 <80%）；S3（CAM_S3，264–407）相机高度中位数低于 MARA 眼高，每帧仰角 ≥5°，等效焦距 ≤32 mm，位移 <1 cm；S4（CAM_S4，408–539）位移 <1 cm，每帧景深开启且 f≤5.6；S5（CAM_S5，540–671）每帧俯角 ≥10°，后拉 ≥0.15 m（沿初始视轴或远离 MARA），焦距不变。MARA 眼高=MARA_RIG 头部骨中点（无则 MARA 网格包围盒顶端下 0.1 m）。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 逐帧导出 CAM_S* matrix_world、lens、传感器、dof/fstop 与 MARA_RIG 骨骼；checks.py 逐镜头判定。 | 0.45 |
| M06 | mid | cloth | ★ | 3.3333 | 布料模拟：CURTAIN 带 Cloth 修改器，缓存已烘焙进 scene.blend 或以 .bphys/blendcache 文件随 project/ 交付；网格 ≥400 顶点；顶边顶点（布料钉固顶点组中权重≥0.5者；无则第0帧最高2%高度带）每隔4帧采样距 CURTAIN_ROD 几何表面 ≤5 cm（允许挂环与沿杆滑动）。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 物理/缓存信息 + 逐帧求值网格；顶边顶点到杆 BVH 最近距离。 | 0.55 |
| M07 | mid | cloth |  | 3.3333 | 窗帘对风的响应：声明 window_burst 后 0.5 s 内 CURTAIN 顶点平均位移速率 ≥ 之前 0.5 s 的 3 倍；声明 window_shut 之后至片尾的最后 1 s 平均速率 ≤ S3 平均的 40%。 | rich_dump 逐帧求值 CURTAIN 顶点（≤1500 个均匀子集）平均位移速率。M06 不通过则本项记 0（组级门槛）。（片中第 f 帧 = 场景第 frame_start+f 帧） | 0.45 |
| M08 | mid | action | ★ | 3.3333 | 窗扇与窗闩动作和声音一致：WINDOW_SASH 在声明 window_burst ±3 帧开始转动（相对第0帧 >1°），向内打开（最大开角时其中心朝室内即 DESK 方向移动 ≥1 cm）且最大开角 ≥25°；自 window_shut 起至片尾与初始朝向相差 ≤3°；latch_click 之后 WINDOW_LATCH 世界矩阵不变；foley 分轨在声明 latch_click ±2 帧有瞬态（5 ms RMS 峰值高于前 200 ms 内 5 ms RMS 中位数 ≥10 dB）。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 逐帧世界矩阵 + 窗扇包围盒中心 + foley 包络瞬态检测。 | 0.5 |
| M09 | mid | action |  | 3.3333 | 手物接触：MARA_RIG 手部/手指骨段在声明 curtain_grab ±2 帧内距 CURTAIN（求值后布料顶点）≤5 cm，在 window_shut ±2 帧内距 WINDOW_SASH（表面采样点）≤5 cm；S4 中在 CAM_S4 画面内可见的每只手（手/手指骨点投影在画面内）有 ≥4 条手指链（每链 ≥3 骨，按手指名或手骨下拓扑）在 S4（408–551）有关键帧动画；S4 内（每2帧）及 window_shut ±2 帧任一手指骨点（头/中/尾）进入 WINDOW_SASH 内部深度均 ≤2 cm。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 骨骼世界坐标、fcurve 关键帧、相机投影；Blender 内 BVH 最近点+法线判穿透深度。 | 0.45 |
| M10 | mid | sound_design |  | 3.3333 | 雷光先后与声明：storm 分轨（<200 Hz、50 ms RMS 包络）上，thunder_1 低频起点（thunder_1 ±0.5 s 内首个比 [thunder_1−1.5 s, thunder_1−0.5 s] 中位数高 ≥6 dB 且距 thunder_1 后 3 s 内峰值不超过 20 dB 的窗）在 thunder_1 ±3 帧内，且 thunder_1 后 3 s 内峰值比该中位数高 ≥10 dB；thunder_1 晚于 flash_peak 0.15–10 s；thunder_far 在 S5 内（第 540–671 帧）、低频为主（Welch 谱 1/3 倍频程带上，相对其前 2.5 s 的能量增量中 300 Hz 以下各带占 ≥70%，持续的雨声不计入）且峰值低于 thunder_1 ≥6 dB；两次雷声均非恒定增益噪声（声明帧后 3 s / 2.5 s 内 <200 Hz 50 ms 包络动态范围 ≥10 dB；对 input 噪声做滤波+包络塑形属正当加工）。 | checks.py：storm 分轨 FFT 低通包络；thunder_far 段与其前 2.5 s 的 Welch 1/3 倍频程带能量差。 | 0.55 |
| M11 | mid | revision | ★ | 3.3333 | 叠化修订：修订版在第 526 帧前与 578 帧后与基础版画面一致（320 px 亮度 PSNR ≥35 dB）；修订版叠化在 527–576 内有 ≥40 个混合帧（由修订版第 526、577 帧线性组合拟合，同 M01），且叠化中心（混合比例 0.1–0.9、R²≥0.7 的帧上对混合比例作线性拟合，其等于 0.5 的帧）为 552±2；叠化把手为真实运动（528–575 内全分辨率相邻帧 PSNR <50 dB 的比例 ≥80%）；音频与基础版零差（≤ −50 dB；独立编码时改用带能量中位差 ≤0.25 dB）；场景属性 dissolve_frames 为 24 或 48，且若序列编辑器有交叉/伽马交叉/擦除转场条带，其长度等于 dissolve_frames（±1）。 | checks.py：逐帧 PSNR、混合帧拟合、全分辨率把手运动、音频相减；Blender 导出场景属性与序列条带。 | 0.45 |
| M12 | mid | evidence |  | 3.3333 | 证据一致：两份 timeline.json 中含实测镜头边界 T12/T23/T34（M01/G07 检测到的硬切；名义 144/264/408）及各自叠化范围（基础版 540–563、修订版 528–575；终点含或不含均可），以帧号或秒表示，误差 ≤1 帧；修订版母带增益与基础版在 B05 中重建混音的增益一致（±0.5 dB）。 | checks.py：遍历 timeline.json 全部数值（帧或秒×24）匹配；增益用 B05 的定位与拟合。 | 0.55 |
| G01 | gate | realism | ★ | 3.1818 | 写实观感（组级门槛）。机测：平涂块指数（亮度均值 24–235 的 8×8 块中，块内方差 <1.0 且均值与上下左右4个相邻块相差 <0.5 的比例；每镜头 3 帧非闪电帧全分辨率取中位数）在 5 个镜头中至少 3 个 ≤0.35；MARA、CURTAIN、DESK、PENDANT_LAMP、WINDOW_SASH 网格使用节点式 BSDF 材质；≥3 个物体有表面变化（图像/程序纹理或连接到 Principled 的输入）；Cycles 渲染开启降噪。画面（评委看联系表）：无镜头呈平面着色/卡通/无光照/白模。 | checks.py 先测机测部分，不合格直接判否（触发组级门槛）；合格时交评委看联系表判画面观感（评委判否不触发门槛）。 | 0.2 |
| G02 | gate | light | ★ | 3.1818 | 无偷光：除 LAMP_LIGHT 与 LIGHTNING 外，任一采样帧（每2帧）均不存在位于室内或距窗平面 5 cm 以内、可渲染且能量 >0 的 LIGHT 对象（窗平面=第0帧关闭的 WINDOW_SASH；室内=朝 DESK 一侧）；LAMP_LIGHT 从不隐藏且能量从不低于其最大值的 25%（无逐镜头开关）；其他室内灯无可见性/能量动画。允许世界背景照明。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 逐帧导出所有 LIGHT 的能量、hide_render、世界位置与 fcurve。 | 0.2 |
| G03 | gate | light | ★ | 3.1818 | 灯随灯动：LAMP_LIGHT 每帧距 PENDANT_LAMP 求值包围盒中心 ≤5 cm（或位于其包围盒 ±2 cm 内）；摆角（悬点→灯中心向量相对 lamp_swing_start 之前静止方向中位数的夹角，故允许恒定的非竖直静止偏角）在 lamp_swing_start 之前 <2°、之后峰值 ≥8°；悬点（求值后 LAMP_CORD 最高点，网格或曲线均可）全片漂移 ≤2 cm（相对其自身首帧）。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 逐帧导出灯罩求值包围盒、LAMP_CORD 求值网格最高点、LAMP_LIGHT 世界位置。 | 0.3 |
| G04 | gate | light | ★ | 3.1818 | 影随灯动（成片可测）：S3（第 max(280, lamp_swing_start)–407 帧）与 S5（570–665 帧）中，LAMP_LIGHT 投影到 CAM_S3/CAM_S5 画面的位置序列与解码成片亮度加权质心序列（均去线性趋势）在 ±3 帧滞后内 /r/ ≥0.5（取投影灯泡移动 ≥画面 0.5% 的轴）。S5 中投影移动 <0.5%（摆动已衰减）则跳过；S3 必须有该移动。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 逐帧相机矩阵/内参 + LAMP_LIGHT 位置，与 bpy_extras.world_to_camera_view 一致的投影；320 px 灰度成片质心。 | 0.15 |
| G05 | gate | light |  | 3.1818 | 单摆可信：s(t)=灯中心相对悬点的水平位移（扣除静止值）在主摆动轴上的投影；周期 T=window_shut 之后相邻上行过零点间隔的中位数（需 ≥3 个过零点，否则用第 264–671 帧）；T/(2π√(L/g)) 在 0.67–1.5 之间，L 取悬点到灯中心或悬点到 LAMP_LIGHT 的距离（取对求解者有利者）；window_shut 之后各半周期 /s/ 峰值在摆动两侧分别非增（后者 ≤ 同侧前一峰值×1.05；首尾不完整半周期不计）；S5 末摆幅（最后 24 帧 /s/ 最大值）< S3 峰值（264–407 帧 /s/ 最大值）。（片中第 f 帧 = 场景第 frame_start+f 帧） | checks.py：G03 的逐帧灯中心/悬点序列，SVD 主轴、过零点、峰值序列。 | 0.22 |
| G06 | gate | light | ★ | 3.1818 | 闪电来自窗外且偏冷：LIGHTNING（点/聚/面光）在 flash_peak ±6 帧内均位于窗平面外侧 ≥0.3 m（窗平面=第0帧关闭的 WINDOW_SASH，外侧=远离 DESK 一侧）；SUN 类型则光线方向自窗外射入（与室内窗法线夹角 <80°）；230–299 帧内无其他灯能量变化；S2（255–263 内最亮帧对第 234 帧）与 S3（264–275 内最亮帧对第 330 帧）中，增亮最多的像素（亮度增量前 10%）的 CIE b* 中位数比参考帧吊灯照亮像素（未削顶的亮度前 20%）低 ≥5。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 逐帧灯光位置/能量 + 窗扇几何；成片 RGB 解码（640 px）转 CIE Lab（D65）。 | 0.2 |
| G07 | gate | edit | ★ | 3.1818 | 闪白隐藏剪辑真实成立：T23 在 264±1（250–280 内首个零均值归一化亮度与第 280 帧相关高于与第 250 帧相关的帧）；262–266 帧平均亮度 ≥ 第 234–257 帧均值的 2.5 倍；255–274 帧中无一帧为均匀白场（全分辨率 ≥99% 像素 ≥250 且亮度标准差 <2；保留画面结构的过曝白闪允许）；LIGHTNING 能量有动画且逐帧最大值落在第 258–270 帧（场景内闪电照明，非后期叠白）。（片中第 f 帧 = 场景第 frame_start+f 帧） | checks.py：320 px / 全分辨率亮度统计 + rich_dump 逐帧 LIGHTNING 能量。 | 0.2 |
| G08 | gate | light |  | 3.1818 | 跨镜头曝光与色温连续（成片可测）：在非闪电帧 S1 24/72/120、S3 300/340/380、S4 430/470/510、S5 590/630/660 中，未削顶像素中最亮 20% 的 CIE b* 中位数在每个镜头（取该镜头各帧中位数）均 ≥8（暖色钨丝灯），且这些镜头之间该区域线性亮度中位数两两相差 ≤1.0 EV。 | checks.py：成片 RGB 解码（640 px）转 CIE Lab（D65）与线性亮度。 | 0.25 |
| G09 | gate | cloth | ★ | 3.1818 | 布料不穿模：每 4 帧采样，CURTAIN 任一顶点（≤1500 个均匀子集）都未位于 WINDOW_SASH 或窗所在墙体网格（包围盒包含关闭窗扇中心的网格）表面背面 2 cm 以上（正面取最近面法线一侧；若某网格离 DESK 最近的面使 DESK 位于其背面，即法线背向室内，则正反互换）。（片中第 f 帧 = 场景第 frame_start+f 帧） | Blender 内 BVH 最近点 + 法线判穿透深度。M06 不通过则本项记 0。 | 0.2 |
| G10 | gate | evidence | ★ | 3.1818 | 工程即真实来源：评分方从 scene.blend 重渲第 72/200/330/480/620 帧（480×201、8 spp、降噪；用标记绑定相机，无则依次 CAM_S1…CAM_S5；求解者渲染器无输出时改用 Cycles），与成片 480×201 SSIM 均 ≥0.75。重渲失败/超时判否。（片中第 f 帧 = 场景第 frame_start+f 帧） | checks.py：blender -b -y 渲染单帧 + numpy SSIM。 | 0.3 |
| G11 | gate | narrative | ★ | 3.1818 | 无字卡叙事。机测：storm+foley 在 23.5–28 s 的 RMS 比 6–23 s 低 ≥4 dB（结尾归于平静）。画面（评委看两版联系表）：按顺序可见窗被吹开且窗帘鼓入、大全景中吊灯摇晃的光影、双手拉窗帘/窗扇、结尾窗已关闭窗帘下垂；无字幕、片名/说明字卡或叠加图形。 | checks.py 先测 RMS 下降，不合格直接判否；合格时交评委看联系表判画面部分。 | 0.25 |

## 组级门槛

- GG-realism：G01 机测部分不通过（平涂块指数、材质/降噪）→ G02–G06、G08 记0。评委对画面部分的判否、或 Blender 检查失败不触发本门槛。
- GG-cloth：M06 不通过 → M07、G09 记0。

## 汇总

```
{
 "weight_total": 99.9994,
 "tier_share": {
  "base": 0.25,
  "mid": 0.4,
  "gate": 0.35
 },
 "judge_weight_complete_submission": "G01 + G11 visual parts only (6.36 of 100), and only when their measured parts pass",
 "expected_score": 49.1
}
```
