# WFA-3D-016 隐藏评分标准（REVIEWER ONLY）

每条判定二元（部分满足即否），连续分 = Σ(通过判定 weight)/Σweight(=28，每条 1.0)×100；组级门槛只让该组相关判定记 0；整题门槛只作验收标记（aux._task_gate），连续分照报。checks.py 返回的判定为确定性测量结果；未被 checks.py 返回的判定（M11、G09、G10，以及工程条款通过后的 G08 视觉条款）由 LLM 评委依据证据（缩略图、文本、探测数据）判 pass/fail，含 critical 项；无人工盲审环节。逐帧容差类条款（“相差 ≤x%”）指采样帧中至少 90% 满足。Perfect=全部通过。测量口径：链节 = CHAIN（或 CHAIN.*）依赖图求值后的实例，或 CHAIN 的全部后代网格对象，或名为 CHAIN 的集合内网格对象（三者取数量最多者；QUICK_LINK* 另计 1 节）；S6 若用链接副本，CHAINRING/CRANK/车轮/BIKE 取同名前缀（如 CHAINRING.001）中在 S6 内位移最大者；头/手腕/指骨按骨名关键词自动识别（head、hand/wrist、finger/thumb/index/middle/ring/pinky 或 Rigify f_* 名，优先变形骨，不区分大小写，.L/.R/Left/Right 定侧，无法定侧时按骨架局部 +X 为左），指尖 = 指骨链末端骨的 tail；腕骨 = 指链根骨的第一个非手掌/非手指祖先骨；髋骨 = hips/pelvis/torso/root 名骨，否则无父骨的根骨。

帧表（基础版）：S1 0–149，S2 150–269，S3 270–449，S4 450–539，S5 540–659，S6 660–899；修订版 S3 270–458，S4 459–539。

判定 28 条：base 7 / mid 11 / gate 10；critical 17。

| id | 层 | 组 | ★ | 判定 | 怎么验证 | 预期通过率 |
|---|---|---|---|---|---|---|
| B01 | base | DELIV | ★ | 基础版 output.mp4：H.264、yuv420p、1280×720 方形像素、恒定 30 fps、解码恰好 900 帧；AAC 立体声 48 kHz，音频覆盖全片。 | ffprobe 流参数 + ffmpeg 计数解码帧；音频时长 ≥ 画面时长 − 1 帧（29.967 s）。 | 0.92 |
| B02 | base | DELIV |  | 修订版 output.mp4 满足与 B01 相同的编码契约，且为 900 帧。 | 同 B01。 | 0.85 |
| B03 | base | DELIV |  | 两版混音综合响度 −18±2 LUFS，采样峰值 ≤ −1 dBFS，无连续 ≥3 个满幅采样。 | ffmpeg ebur128 / numpy 解码 PCM。 | 0.78 |
| B04 | base | DELIV |  | 基础版 stems/foley,shop,street.wav 均为 48 kHz PCM、30.0±0.05 s；按 timeline.json 声明增益相加后与解码混音一致：对齐（允许 ≤2048 样本编码延迟）后 1/3 倍频程带能量（100 ms 帧，50 Hz–14 kHz，仅计该帧最强带以下 40 dB 内的带）逐点差绝对值中位数 ≤ 0.75 dB、95 分位 ≤ 3 dB；声明增益与实测最优拟合增益相差 ≤1 dB。 | 解码 AAC 至 48k 单声道；互相关对齐后比带能量；≤4 kHz 低通最小二乘拟合各分轨增益并与声明值比较。不用波形相减：AAC 感知编码下正确混音的波形残差也达不到 −30 dB。 | 0.72 |
| B05 | base | DELIV |  | events.csv 表头逐字为 event_id,frame,description；11 个必需事件 id 全部存在、帧为 0–899 整数且各在其所属镜头内（old_chain_off∈S1，watch_check∈S2，chain_hand_contact/link_join_start/link_click∈S3，courier_turn∈S4，crank_grab/crank_turn_start/chain_engage/crank_release∈S5，pedal_start∈S6），并满足顺序 chain_hand_contact<link_join_start<link_click、crank_grab≤crank_turn_start≤chain_engage<crank_release。 | 解析 CSV；镜头归属按名义帧表。 | 0.85 |
| B06 | base | DELIV | ★ | project/scene.blend 可在 Blender 4.3 后台打开且以 Blender 4.3 保存（文件版本 4.3.x）；题面列出的全部对象名（2 人物、2 骨架、14 道具、CAM_S1–S6）存在，MECHANIC_RIG、COURIER_RIG 为骨架对象；场景自定义属性 roll_T34_frames 存在；README 含 blender -b 导出命令。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定；读 bpy.data.version 与对象类型。评分镜像无 Blender 时本项与全部 .blend 判定记 error（不出分）。 | 0.82 |
| B07 | base | DELIV |  | 两版 timeline.json 均可解析；M01/M09 实测检出的每个剪辑帧都在 timeline.json 的数值中以“剪辑帧”或“上一镜末帧”形式声明（±1 帧）；修订版声明 T34 为 459（或 S3 末帧 458）。 | checks.py：递归收集 timeline.json 中全部整数值，与 M01（基础版）/M09（修订版）检出的剪辑帧比对；检测未运行时按名义剪辑帧比对。 | 0.80 |
| M01 | mid | EDIT | ★ | 基础版恰为六个镜头：在第 150/270/450/540/660 帧（各 ±1）检出硬切，每处无混合帧（剪辑两侧相邻帧不存在线性混合解释）；其余位置无剪辑、无定格（连续 ≥6 帧逐像素相同即判定格，S1/S3/S5 固定机位处允许静止背景但须有前景运动）。 | 320×180 灰度帧差 + 直方图检测剪辑并做混合帧检查；定格 = 原生 1280×720 灰度下连续 ≥5 对相邻帧（≥6 帧）中变化 >3 灰阶的像素占比 ≤0.01%（前景有运动则不判定格）。 | 0.72 |
| M02 | mid | EDIT |  | 摄影机数据（评分方从 .blend 逐帧导出）：S1 机高 1.2–1.9 m、俯仰 |θ|≤8°、固定（位置变化 <1 cm、焦距不变、朝向变化 ≤0.5°）；S2 仰拍（俯仰均值 ≥+3°）、手持抖动 2–60 mm、无变焦；S3 固定、焦距 ≥50 mm 或对焦距离 ≤0.6 m、景深开启且 f≤4；S4 朝 COURIER 推轨 ≥0.08 m、焦距不变、景深开启；S5 固定、CHAINRING 中心投影在画面中部 40% 区域内（x、y ∈ [0.3, 0.7]）；S6 摄影机平移 ≥3 m 且与 COURIER 距离增大 ≥1.5 倍（或焦距缩短 ≥1.5 倍）。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：CAM_S1–S6 每帧 matrix_world、lens、DOF；手持抖动 = 位置相对 ±7 帧滑动平均的最大偏离；S4 推轨 = 首末帧到 COURIER 原点距离之差；任一镜头不符即否。 | 0.42 |
| M03 | mid | SOUND | ★ | 交叉剪辑声音：shop 分轨只在店内镜头（S1/S3/S5）有声、street 分轨只在街景镜头（S2/S4/S6）有声；每个剪辑点 ±2 帧内完成切换，非所属段电平 ≤ −50 dBFS；每段内无断续（不存在 ≥100 ms、电平比该段中位电平低 ≥20 dB 的空洞；车辆经过等自然起伏不判否）；两种环境声长时谱质心相差 ≥30% 或 1/3 倍频程谱距离 ≥6 dB。 | 分轨 50 ms RMS 包络 + 谱质心/1/3 oct 谱。 | 0.58 |
| M04 | mid | PROJ | ★ | 工程即真实来源：评分方以 roll_T34_frames=0、各帧所属镜头的 CAM_Sk 从 scene.blend 重渲第 75/210/360/495/600/780 帧，与成片对应帧在 640×360 灰度下 SSIM 均 ≥0.70；重渲失败即否。 | checks.py：blender -b x06_blend_dump.py render 模式，Cycles CPU、采样 ≤16、降噪、640×360（场景非 Cycles 时先试场景引擎）；SSIM 用 7×7 均值窗、灰度；总时限 1500 s。 | 0.50 |
| M05 | mid | CHAR | ★ | MECHANIC_RIG、COURIER_RIG 各自通过 Armature 修改器驱动对应网格；技师每只手 ≥4 条手指骨链、每链 ≥2 骨，且在 S1/S3/S5 内各链至少有一处不同于其他手指的关键帧旋转；无图片平面手或脸。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：网格对象 Armature 修改器目标；技师指骨链按骨名识别（链 = 指骨根骨沿子骨的最长链）；每链曲线 = 链内各骨相对静止姿态的旋转角之和（S1+S3+S5 采样帧）；每链转幅 ≥5° 且与同手至少一条其他链的相关 |r|<0.95；手指网格 = 主权重 ≥0.5 属指骨的顶点数 ≥ 4×指骨数（否则视为图片平面手）。 | 0.52 |
| M06 | mid | MECH |  | CHAIN 由离散链节构成（≥100 个独立对象或实例，非单一连续网格/纹理条），链节数与 scene.json 106 节相符（±2，快扣计 1 节），相邻链节销中心距 12.7 mm ±5%（按场景单位），S5 内链节全程闭合成环无断开。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：链节取依赖图实例/后代/集合（见计分口径）；节距 = 最近邻距离中位数（含 QUICK_LINK 原点）；闭环 = S5 每个采样帧中以 ≤1.5×节距为边的邻接图连通且每节度数 ≥2。 | 0.45 |
| M07 | mid | CHAR |  | 快递员动作按声明发生：watch_check 与 courier_turn 距其镜头边界均 ≥6 帧；watch_check ±6 帧内左手腕骨最高点比 S2 中此前最低点高 ≥0.15 m，且 WATCH 在左手腕（距左腕骨 ≤12 cm 且比右腕近）、其原点投影在 CAM_S2 画框内；courier_turn ±6 帧内头部骨偏航变化 ≥30°；若有眼骨，转后视线方向与指向 WINDOW 的夹角须减小（朝向店面）。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：COURIER_RIG 腕/头/眼骨世界坐标与轴向；WATCH 原点；CAM_S2 投影。 | 0.45 |
| M08 | mid | WORLD |  | 同一连续世界：S1 采样帧（每 3 帧）中至少 60% 帧，从 CAM_S1 向 COURIER 网格包围盒内采样点的射线（穿过 WINDOW* 对象）首先命中 COURIER/HELMET/WATCH，且该点投影在 WINDOW 投影包围框内；COURIER 髋/根骨在 S1 末帧与 S2 首帧的世界位置差 ≤0.6 m；COURIER、MECHANIC、两骨架、WINDOW、BIKE、CAM_S1、CAM_S2 同在一个场景（同一世界坐标系）。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：scene.ray_cast 可见性 + world_to_camera_view 投影；髋/根骨世界坐标。 | 0.38 |
| M09 | mid | REV | ★ | 修订画面：修订版第 0–449 帧与第 459–899 帧逐帧与基础版一致（320×180 灰度 PSNR ≥32 dB）；第 450–458 帧为 S3 的延续（每帧与基础版第 449 帧的平均绝对差小于与第 450 帧，且其中至少 4 对相邻帧有变化，非定格）；T34 硬切在第 459 帧 ±1 且第 450 帧附近无剪辑；由同一 .blend 以 roll_T34_frames=9、CAM_S3 重渲第 454 帧与修订版第 454 帧 SSIM ≥0.70。 | checks.py：逐帧 PSNR/帧差 + 剪辑检测；重渲同 M04（roll_T34_frames=9）。 | 0.45 |
| M10 | mid | REV |  | 修订声音：修订版 shop 分轨在 15.00–15.30 s 有声并于 15.30 s ±2 帧切出，street 分轨于 15.30 s ±2 帧切入；其余时段三条分轨（无损 wav）与基础版波形差异 ≤ −40 dB；AAC 混音在非修订时段（0–14.9 s、15.4 s–结尾）与基础版混音对齐（允许 ≤2048 样本）后 1/3 倍频程带能量（100 ms 帧，50 Hz–14 kHz，仅计该帧最强带以下 40 dB 内的带）逐点差绝对值中位数 ≤ 0.75 dB、95 分位 ≤ 3 dB。 | 分轨差分能量 + 包络切换点；AAC 混音用与 B04 相同的频带能量比较，不用波形相减（两次独立 AAC 编码的波形残差达不到 −30 dB）。 | 0.42 |
| M11 | mid | DOC |  | credits.md 列出全部资产、工具与声音制作方式且无联网/付费服务痕迹；qa.md 存在，所列帧号/采样位置与 events.csv、timeline.json 及探测数据一致；产物中无凭据或外部 URL 媒体引用。 | LLM 评委读 credits.md、qa.md、events.csv、timeline.json 与探测数据判定。 | 0.60 |
| G01 | gate | CONTACT | ★ | 合扣接触：link_click − link_join_start ∈ [3, 90] 帧；在 link_click 帧，技师两只手各至少一个指尖（指链末端骨 tail）距 QUICK_LINK 或其相邻两节链节表面 ≤2.5 cm；QUICK_LINK 各部件（QUICK_LINK*、其子对象）与相邻两节链节之间的距离在 link_join_start 时与最终值相差 >2 mm（分离），自就位帧起至 S3 末恒定（≤0.5 mm），就位帧与 link_click 相差 ≤3 帧；foley 分轨在 link_click ±2 帧内有一个瞬态：5 ms RMS 包络峰值比此前 150 ms 的 20 分位电平高 ≥12 dB、峰值 −10 dB 以上持续 <60 ms；S3 内距其 >0.2 s 的其他同类起音峰值须至少低 1 dB。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：指尖 tail 到 QUICK_LINK 网格（BVH）与相邻链节网格的最近距离；QUICK_LINK 部件—链节距离；foley 分轨 numpy 包络。 | 0.18 |
| G02 | gate | CONTACT | ★ | 穿链接触：在 chain_hand_contact 帧至少一个指尖距 CHAIN 链节表面 ≤2 cm；距该指尖最近的 5 节链节在此前 10 帧内位移 ≤2 mm（静止），此后 15 帧内随手移动（链节平均位移与指尖位移夹角余弦 ≥0.5、长度比 0.5–2、各 ≥5 mm）；S3 每 3 帧抽样，链节/REAR_COG/CHAINRING 顶点侵入手指（以指骨为轴、半径取该骨主权重顶点到骨轴距离中位数的胶囊体）的深度 ≤6 mm；S3 首帧 CHAIN 未同时挂在两齿盘上、S3 末帧在 REAR_COG 与 CHAINRING 节圆上各有 ≥4 节（径向 ±6 mm、轴向 ±8 mm）。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：链节网格 BVH 最近距离、链节位移场、指骨胶囊体侵入深度、节圆啮合计数。 | 0.14 |
| G03 | gate | MECH | ★ | 链条啮合无打滑：驱动段（chain_engage+2 至 crank_release−2）中至少 90% 的帧，链节（BIKE 坐标系内）速度中位数与 CHAINRING 节圆线速度 ω·r（r = 12.7 mm/(2·sin(π/44)) = 88.99 mm）相差 ≤12%；驱动段中间帧在链盘节圆 ±6 mm、盘面 ±8 mm 内的链节 ≥8 节，其中 ≥80% 的销中心距节圆 ≤4 mm（落在齿间而非浮空或穿齿）。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：链节逐帧位置、CHAINRING 相对 BIKE 的旋转；节圆中心/轴取 CHAINRING 求值网格包围盒中心与最薄轴。 | 0.14 |
| G04 | gate | MECH | ★ | 传动比与啮合时刻：chain_engage − crank_turn_start ≤15 帧；驱动段至少 90% 的帧 REAR_COG 角速度 / CHAINRING 角速度（相对 BIKE、同一轴向取号）= 44/16（2.75）±10%（含同旋向），REAR_WHEEL / REAR_COG = 1 ±5%；后轮首次 |ω| ≥0.3 rad/s 的帧在 chain_engage ±2 内，chain_engage−3 之前 |ω| <0.3 rad/s。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：相对 BIKE 的逐帧旋转增量求角速度。 | 0.20 |
| G05 | gate | MECH | ★ | 飞轮空转语义：crank_release 之后 S5 至少剩 15 帧；后轮 |ω|>0.3 rad/s 持续 ≥15 帧且逐帧单调衰减（后一帧 ≤ 前一帧×1.03+0.05 rad/s，单帧降幅 ≤ 松手时的 25%）；空转末帧曲柄归一化转速低于后轮归一化转速且后轮/曲柄转速比 >2.75×1.1（曲柄未被带转），松手时曲柄 |ω| ≥0.5 rad/s；空转期间（crank_release+3 帧起）每个 0.25 s 窗内 foley 分轨（>1 kHz 包络自相关峰 ≥0.3）有周期咔哒，“咔哒重复率 ÷ 后轮转速（转/秒）”各窗均在 18–72 内且变异系数 ≤25%；驱动段内（foley 高于 −60 dBFS 的窗）无自相关峰 ≥0.5 且比值在 18–72 内的同类周期咔哒。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：后轮/曲柄相对 BIKE 角速度；foley 分轨 numpy 包络自相关逐 0.25 s 窗求重复率。 | 0.10 |
| G06 | gate | MATCH | ★ | 图形与运动匹配剪辑：第 659 帧（CAM_S5，CHAINRING）与第 660 帧（CAM_S6，S6 链盘）中链盘中心投影位置相差 ≤8% 画宽，投影直径比 0.67–1.5；658→659 与 660→661 的屏幕旋转同向（每帧 ≥0.3°），屏幕角速度比 0.5–2.0；第 660 帧链盘投影直径 ≥30% 画高。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：链盘包围盒中心与 16 个轮缘点经 world_to_camera_view 投影。 | 0.20 |
| G07 | gate | MATCH | ★ | 同车与骑行运动学：S6 中骑行的是 BIKE（或网格数据相同的链接副本），链盘位于后轮平面的骑行右侧 >1 cm（驱动侧）；pedal_start+3 帧后车速 >0.3 m/s 的采样帧中至少 90%：CRANK 转速（转/秒）× 2.75 × 0.68π 与 BIKE 地速相差 ≤20%，前后轮滚动（ω×0.34 m，方向为前滚）与地速相差 ≤15%；S6 末采样帧 COURIER 包围盒中心投影在 CAM_S6 画右之外（x>1）且此前在画内。 | checks.py 调用 blender -b scene.blend --python x06_blend_dump.py 逐帧导出（胶片帧 i = 场景帧 frame_start+i；镜头 Sk 一律经 CAM_Sk 测量；roll_T34_frames 置 0），x06_blend_checks.py 用 numpy 判定：BIKE 地速、CRANK/车轮相对 BIKE 与世界角速度、链盘横向偏置；CAM_S6 投影。 | 0.15 |
| G08 | gate | QUAL | ★ | 写实渲染（组门槛：本项不过则 G09、G10 记 0）。工程条款（checks.py 测量，任一不符即否）：场景网格所用材质 ≥90% 含 BSDF（非纯自发光/平涂），≥4 个材质的颜色/粗糙度/法线/置换由纹理或程序节点驱动；有面光、软阴影灯（日光角 >0.5°、点/聚光半径 ≥5 cm）或天空/HDRI 世界；Cycles 时开启降噪。视觉条款（评委看缩略图）：无任何镜头呈平面着色、卡通、白模或无阴影。 | checks.py 读 x06_blend_dump.py 导出的材质节点、灯光、世界与渲染设置；工程条款不符直接记否，否则由 LLM 评委按缩略图判视觉条款。 | 0.22 |
| G09 | gate | QUAL | ★ | 接触可读性：缩略图中 S3 可见技师手指在链条/快扣上操作，S5 可见手握曲柄且链盘/后轮在动作中，无可见的手指破损、消失或穿模。 | LLM 评委依缩略图判定。 | 0.18 |
| G10 | gate | QUAL | ★ | 叙事与剪辑意图：仅凭缩略图（不依赖文字说明）可读出“修车与等待交叉并行 → 链条修好 → 同一辆车骑走”，店内与街景交替出现，S5 末与 S6 首的链盘构成可辨认的匹配剪辑；画面无字幕、标题卡或叠加图形。 | LLM 评委依缩略图判定（声音可信度由 M03 测量覆盖）。 | 0.30 |

## 组级门槛

- PROJ/CHAR/MECH/WORLD/CONTACT/MATCH：B06 不通过（scene.blend 无法打开或缺必需对象）→ 这些组中依赖 .blend 的判定全部记 0
- QUAL：G08 写实门槛不通过 → G09、G10 记 0
- REV：修订版缺失或 B02 不通过 → M09、M10 记 0
- CONTACT/MECH/MATCH：events.csv 缺失或 B05 不通过 → 依赖声明帧的判定（M07、G01、G02、G03、G04、G05、G07）记 0

## 整题门槛（只作验收标记）

- base/output.mp4 缺失、无法解码或不满足 B01 → aux._task_gate=fail（验收标记，不改连续分）

## 声明帧合理性规则（已写入相应判定）

- 声明事件须落在所属镜头内且满足 B05 中的顺序；同一 id 多行取第一行。
- chain_engage − crank_turn_start ≤ 15 帧（写入 G04，仅影响 G04）。
- crank_release 之后至 S5 结束至少剩 15 帧（写入 G05，仅影响 G05）。
- link_click − link_join_start ∈ [3, 90] 帧（写入 G01）；watch_check 与 courier_turn 至少距镜头边界 6 帧（写入 M07）。
- 声明帧被评分方实测反驳（如声明 link_click 但该帧快扣未就位）时，相关判定记否，不做就近搜索。

## 评审方式

无人工盲审。checks.py 测量 B01–B07、M01–M10、G01–G07 与 G08 工程条款；LLM 评委只判 M11、G09、G10 与 G08 视觉条款（依据缩略图、文本与探测数据）。

## 预期分计算

| 层 | 条数 | 权重占比 | 平均预期通过率 | 贡献 |
|---|---|---|---|---|
| base | 7 | 25% | 0.82 | 20.5 |
| mid | 11 | 39% | 0.50 | 19.6 |
| gate | 10 | 36% | 0.18 | 6.5 |

预期分 = Σ(weight×expected_pass)/Σweight×100 = **46.6**（设计目标 45–55；组级门槛的相关性会让实际均值略低，未实测）。
