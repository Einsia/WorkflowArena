# WFA-3D-015 隐藏评分标准（REVIEWER ONLY）

版本 x05-rubric-v2 (2026-10-25 cleanup)。判定 27 条（其中 X04 权重 0），关键 19 条，总权重 100。

> 由 rubric.json 渲染（2026-10-25 清理，脚本 /tmp/rubfix/cdc-c-x05/rub/patch_rubric.py）；review/render_rubric.py 为旧版生成器，已不再同步。

## 评分规则

- **verdicts**：每条判定独立二元；部分满足即判否。连续分 = Σ(通过判定权重) / Σ(非 na 判定权重) × 100（总权重 100；X04 权重 0 不计）。
- **group_gates**：S 组门槛 = B03；P 组门槛 = B06；R 组门槛 = B01(rev1/rev2 部分)
- **group_gate_rule**：组门槛判定失败，则该组其余判定全部记 0（门槛判定本身仍按自身结果计）；不影响其他组。
- **task_gates**：整题门槛：base/output.mp4 缺失或不满足 B01 编码契约时，postprocess 在报告 aux 中记 _task_gate = fail（“验收失败”），连续分照常报告。作弊（联网、读隐藏文件等）不在评分程序内检测。
- **acceptance**：全部判定通过才算 Perfect。
- **judge**：只有 M12（文本部分）、X07（外观部分）与 X09 交由 LLM 评委按证据判 pass/fail；其余判定由 checks.py 确定性给出。无人工盲审环节；评分镜像缺 blender 时工程相关判定记 error，不发奖励。
- **measure_on_declared**：动作与台词时刻一律按 events.csv 声明帧测量，配合 B05 的合理性规则；剪辑点、J-cut 提前量、修订帧数为公开规格。
- **bone_identification**：骨名不作规定，checks.py 按名称关键词识别：头骨 = 名为 head（单词）或 spine.006 的骨（优先变形骨）；下颌/口型 = 名含 jaw/mouth/lip/chin/teeth/tongue 的骨、名含 jaw/mouth/viseme/lip/open 等的形态键、名含 jaw/mouth 的角色子物体；手部骨链 = 名含 hand/palm/finger/thumb/index/middle/ring/pinky/f_ 的骨（优先变形骨）；左右侧按 .L/.R、_l/_r、left/right。
- **project_measurement**：工程测量：评分方用 blender -b 只读打开 project/scene.blend，将 rev1_hold_frames、rev2_trim_frames 设为 0（base 状态），逐帧（影片第 i 帧 = frame_start + i）导出对象/骨骼/形态键/材质发射/摄影机数据；第 k 镜头用 CAM_Sk。

## 判定

| id | 层 | 组 | 关键 | 权重 | 预期通过率 | 判定 | 怎么验证 |
|---|---|---|---|---|---|---|---|
| B01 | base | A 交付合同 | ★ | 5 | 0.88 | 三版成片编码契约：base 900 帧、rev1 912 帧、rev2 903 帧；H.264 yuv420p 1280×720 方形像素、恒定 30 fps；AAC 立体声 48 kHz，音频覆盖全部画面。 | ffprobe -count_frames 解码计数；codec/pix_fmt/SAR/r_frame_rate/avg_frame_rate；音频时长 ≥ 画面时长 −1 帧。 |
| B02 | base | A 交付合同 |  | 4 | 0.80 | 母带：三版综合响度均在 −22.0 至 −18.0 LUFS；真峰值 ≤ −0.9 dBTP；无连续 ≥3 个满幅采样。 | ffmpeg ebur128=peak=true；解码 PCM 统计 |x|≥0.999 连续段。 |
| B03 | base | A 交付合同 | ★ | 4 | 0.75 | 分轨契约（声音组门槛）：三版各有 stems/{studio,taxi,radio,phone}.wav，48 kHz PCM 立体声，长度与成片相差 ≤1 帧；按 timeline.json 声明增益相加后，与解码混音的 1/3 倍频程带能量（100 ms 帧）逐点差中位数 ≤ 0.75 dB、95 分位 ≤ 3 dB，且每条分轨的声明增益与最小二乘拟合增益（≤4 kHz）相差 ≤ 1 dB。 | checks.py：ffprobe 检查格式与长度；timeline.json 中名含 gain 的数值按 统一/master 线性|dB/逐轨 线性|dB 各种解读取最优；对齐 ≤2048 样本后比较 1/3 倍频程带能量；≤4 kHz 低通后最小二乘拟合各轨增益。（AAC 有损编码使波形残差不可达，故不用波形残差。） |
| B04 | base | A 交付合同 | ★ | 4 | 0.85 | 镜头结构：base 在第 180/360/540/720 帧（±1）各有一处硬切，切点两侧无混合帧；其余位置无剪辑；无 ≥15 帧的定格：相邻帧 PSNR ≥ 55 dB 连续 ≥15 帧，且工程中该段所属镜头的 CAM_Sk（矩阵/焦距）与画内角色骨架（骨骼运动或口型通道）在该段内都没有变化。 | checks.py：320×180 灰度逐帧，平均绝对差尖峰 + 32 档直方图变化检测剪辑，相邻帧差判断混合帧；PSNR 连续段作为定格候选，再用工程逐帧导出核对摄影机与画内角色是否有动画（工程测量：评分方以 rev1_hold_frames = rev2_trim_frames = 0 只读打开 project/scene.blend，影片第 i 帧 = 场景 frame_start + i，第 k 镜头用 CAM_Sk）。 |
| B05 | base | A 交付合同 |  | 4 | 0.80 | events.csv：表头恰为 event_id,frame,description；16 个必需 id 齐全、帧为 0–899 整数；位置与顺序合理：line1 在 S1；line2_start 在 S1 且 line2_end 在 S2；knob_down_* 与 phone_at_ear 在 S2 且 knob_down_end < phone_at_ear ≤ line3_start；line3_start = 342±2；line3_end 在 S4 且 < caller_fader_down < line4_start（均在 S4）；line4_end、phone_hang_up、knob_up_*、light_green 在 S5 且 phone_hang_up < knob_up_start。 | csv 解析 + 规则表核对。 |
| B06 | base | A 交付合同 | ★ | 4 | 0.85 | 工程契约（场景组门槛）：project/scene.blend 由 Blender 4.3 保存（文件版本 4.3.x）且可后台打开；3 个人物、3 个骨架（*_RIG 均为 Armature）、10 个道具、CAM_S1–CAM_S5 全部按名存在；场景属性 rev1_hold_frames、rev2_trim_frames 存在；README 含 blender -b 导出命令；credits.md、qa.md 存在。 | checks.py：blender -b scene.blend --python（只读）导出对象名/类型、场景属性与 bpy.data.version；评分镜像缺 blender 时记 error（不发奖励）。 |
| M01 | mid | S 声音视点与剪辑 | ★ | 4 | 0.50 | 台词时刻：四条分轨相加后，在 300–3400 Hz 语音频带包络（20 ms 窗、10 ms 步）上，每句实测起止与 events.csv 声明的 line*_start/line*_end 相差 ≤ 6 帧：声明起点 ±0.2 s 内有语音活动，且（前一句未紧邻时）起点前 0.2–0.45 s 无活动；终点同理。活动阈值 = max(全片 10 分位底噪 + 15 dB, 该句峰值 − 35 dB)。（可懂度不再单独评分。） | checks.py 确定性测量；不再用 ASR（评分镜像无 ASR 模型）。 |
| M02 | mid | S 声音视点与剪辑 |  | 3 | 0.60 | T23 J-cut：taxi 分轨上司机语音起点（300–3400 Hz 包络持续 ≥50 ms 超过阈值 max(底噪+15 dB, 峰值−35 dB)）= 11.40 ± 0.05 s，11.00–11.35 s 无此类语音活动；342–359 帧中 DRIVER 嘴部在每帧要么不可见（头骨中点投影在 CAM_S2 画外，或头部前向与“头→摄影机”水平方向夹角 > 100°），要么 DRIVER 口型通道与 taxi 分轨逐帧包络相关 r ≥ 0.5（滞后 ≤ 2 帧）。 | checks.py：分轨包络 + 工程逐帧导出（工程测量：评分方以 rev1_hold_frames = rev2_trim_frames = 0 只读打开 project/scene.blend，影片第 i 帧 = 场景 frame_start + i，第 k 镜头用 CAM_Sk）；头部前向取下颌骨（头→下巴）水平方向，无下颌骨时取面部骨（eye/nose/lip…）重心方向。 |
| M03 | mid | S 声音视点与剪辑 | ★ | 4 | 0.50 | T12 视点切换：L2 在 studio 分轨上不晚于 6.05 s 结束、在 radio 分轨上不早于 5.95 s 开始（源分轨最后一个、目标分轨第一个“高于各自峰值 −30 dB”的 10 ms 帧，300–3400 Hz），二者间隙 ≤ 0.40 s、重叠 ≤ 0.05 s；6.10–12.00 s studio 分轨 ≤ −55 dBFS（10 ms RMS）；剪辑点处无爆音：四轨相加信号在 6.00 s ±10 ms 内的 24 阶线性预测残差峰值不超过 ±60 ms 邻域残差峰值 12 dB。（跳字/重复词无 ASR，不单独测量，由间隙上限约束。） | checks.py 确定性测量（分轨包络、电平、线性预测残差）。 |
| M04 | mid | S 声音视点与剪辑 | ★ | 3 | 0.50 | T45 视点切换：与 M03 同口径，L4 在 24.00 s 处 studio → radio：studio 不晚于 24.05 s 结束、radio 不早于 23.95 s 开始，间隙 ≤ 0.40 s、重叠 ≤ 0.05 s；24.10–30.00 s studio 分轨 ≤ −55 dBFS；24.00 s 处无爆音（同 M03 判据）。 | 同 M03。 |
| M05 | mid | S 声音视点与剪辑 | ★ | 4 | 0.55 | T34 L-cut 转电话：L3 在 taxi 分轨上不晚于 18.05 s 结束、在 phone 分轨上不早于 17.95 s 开始（M03 口径），间隙 ≤ 0.40 s、重叠 ≤ 0.05 s；18.20–24.00 s taxi 分轨 ≤ −55 dBFS；phone 分轨 0–17.95 s ≤ −50 dBFS；phone 分轨上 L3 的最后活动不早于声明 line3_end − 0.2 s；18.00 s 处无爆音（M03 判据）。 | 同 M03。 |
| M06 | mid | P 场景、动作与工程 |  | 3 | 0.45 | 收音机旋钮因果：RADIO_KNOB 相对 RADIO 的旋转在 knob_down_start–knob_down_end 与 knob_up_start–knob_up_end 内各单调（容差 0.5°）转过 ≥ 30°，其余时段（窗口外 ±2 帧以外）转动 ≤ 3°；两次转动开始（±2 帧）时 DRIVER 手部骨链（名含 hand/palm/finger/thumb/index/middle/ring/pinky/f_ 的骨段）距旋钮原点 ≤ 6 cm；radio 分轨短时响度（K 加权 400 ms 窗的最大值）：结束点后 0.5–1.0 s 比开始前 0.5 s 至开始前 3 帧，调低时低 ≥ 6 LU、调高时高 ≥ 6 LU。 | checks.py：工程逐帧导出（工程测量：评分方以 rev1_hold_frames = rev2_trim_frames = 0 只读打开 project/scene.blend，影片第 i 帧 = 场景 frame_start + i，第 k 镜头用 CAM_Sk） + 分轨短时响度。 |
| M07 | mid | P 场景、动作与工程 |  | 3 | 0.45 | 电话与推子：phone_at_ear 至 min(line3_end, 539) 每帧 PHONE 原点距 DRIVER 头骨骨段 ≤ 12 cm、距 DRIVER 手部骨链 ≤ 6 cm；CALLER_FADER 在 caller_fader_down −3 与 +3 帧之间平移 ≥ 1 cm，且 caller_fader_down −3 帧至该帧内 HOST_B 手部骨链距其 ≤ 5 cm；phone 分轨自 caller_fader_down +3 帧起 ≤ −60 dBFS。 | checks.py：工程逐帧导出（工程测量：评分方以 rev1_hold_frames = rev2_trim_frames = 0 只读打开 project/scene.blend，影片第 i 帧 = 场景 frame_start + i，第 k 镜头用 CAM_Sk） + 分轨电平。 |
| M08 | mid | P 场景、动作与工程 | ★ | 4 | 0.45 | 镜头参数（工程逐帧）：S1 俯仰 ±10° 内、位移 < 1 cm、焦距 28–70 mm 不变；S2/S5 焦距在 24–70 mm，且有手持抖动：去除 15 帧滑动平均后的位置残差峰值 1–60 mm（或位置残差 < 1 mm 时朝向残差 0.05–3°），且非周期（残差自相关在首次过零后 60 帧内回升不到 0.6）；S3 位移 < 1 cm、焦距不变、景深开启且 f ≤ 4；S4 摄影机到 HOST_B 头骨的距离从第 540 帧到第 719 帧缩短 ≥ 0.08 m、焦距不变、景深开启且 f ≤ 4。 | checks.py：工程逐帧导出 CAM_S* 矩阵、lens、dof（工程测量：评分方以 rev1_hold_frames = rev2_trim_frames = 0 只读打开 project/scene.blend，影片第 i 帧 = 场景 frame_start + i，第 k 镜头用 CAM_Sk）。 |
| M09 | mid | R 两轮修订 | ★ | 4 | 0.55 | rev1：912 帧；0–341 帧与 base 一致（每 19 帧抽样 PSNR ≥ 30）；rev1 第 372/462/642/822 帧与 base 第 360/450/630/810 帧 PSNR ≥ 30；T23 在第 372±1 帧硬切；四条分轨 0–11.38 s 与 base 相关 ≥ 0.99（两者皆静音则免）；12.4 s 起每条非静音分轨（200–4000 Hz）与 base 的互相关最大值所在滞后 = +0.400 ± 0.010 s 且相关 ≥ 0.5；rev1 taxi 分轨 L3 起点（M02 口径）= 11.80 ± 0.05 s。（同一 .blend 出三版，工程属性取值不在此核对，属性存在由 B06 检查。） | checks.py：PSNR 抽样、剪辑检测、分轨相关与 FFT 互相关、起点检测。 |
| M10 | mid | P 场景、动作与工程 | ★ | 3 | 0.45 | 工程即真实来源：评分方以 base 属性（0/0）、Cycles CPU、16 采样（OIDN 降噪）、320×180、第 k 镜头用 CAM_Sk 重渲第 90/270/450/630/810 帧，与 base 成片对应帧在 320×180 灰度、3×3 平滑后的 SSIM ≥ 0.75 的帧数 ≥ 4/5。 | checks.py：blender -b 重渲（限时）+ numpy SSIM；渲染失败记 fail 并附日志。 |
| M11 | mid | P 场景、动作与工程 |  | 3 | 0.55 | 同一性与道具状态：HOST_B_RIG 髋/根骨位置在 S1 与 S4 全部帧内偏移 ≤ 0.15 m；ON_AIR_LAMP 在 S1 ≥ 90% 帧投影于 CAM_S1 画内，且其（含子物体）材质发射或灯光在 S1 ≥ 90% 帧非零；RADIO 在 S2、S5 各 ≥ 75% 帧投影于 CAM_S2/CAM_S5 画内；TRAFFIC_LIGHT（含子物体）在第 720 帧至 light_green 前的 ≥ 90% 帧发红光、light_green+3 帧起 ≥ 90% 帧发绿光（按材质发射色/灯光色判断，判断不出时取成片中投影位置的像素红绿差）；TAXI 在 720 至 light_green 位移 ≤ 1 cm，且在 light_green 后 30 帧内开始移动（> 1 cm）。 | checks.py：工程逐帧导出（工程测量：评分方以 rev1_hold_frames = rev2_trim_frames = 0 只读打开 project/scene.blend，影片第 i 帧 = 场景 frame_start + i，第 k 镜头用 CAM_Sk）；必要时读取成片 S5 像素。 |
| M12 | mid | N 叙事与证据 |  | 2 | 0.60 | 证据一致：credits.md 写明每项资产与工具来源及台词制作方式（离线），未出现联网/付费服务/模仿真人声音；qa.md 列出真实问题及修正前后的帧号或采样位置，或明确写“未发现问题”；各版 timeline.json 含镜头帧范围、四个转场、各句起止、各分轨主要声音起止与母带增益，且与 events.csv 一致；产物中无凭据。 | checks.py 扫描文本文件中的凭据特征串（命中即 fail）；其余由评审模型依 credits.md、qa.md、timeline.json、events.csv 文本判定。 |
| X01 | gate | S 声音视点与剪辑 | ★ | 4.52 | 0.35 | 电话线路音色：phone 分轨 L3 段落的长时谱中，< 200 Hz 与 > 5 kHz 两个频带的能量各比 300–3400 Hz 低 ≥ 15 dB；且 radio 分轨语音段 3.4–8 kHz 的相对能量比 phone 分轨高 ≥ 6 dB（两种听点音色可测地不同）。 | Welch PSD（语音活动帧）求频带能量比。 |
| X02 | gate | S 声音视点与剪辑 | ★ | 5.65 | 0.20 | 画内收音机声像：在 S2、S5 中逐 0.5 s 窗，用 CAM_S2/CAM_S5 投影 RADIO 中心得画面横坐标 x；radio 分轨语音窗口的声道电平差（200–4000 Hz）在 |x−0.5| ≥ 0.10 时与 x−0.5 同号且绝对值 ≥ 1.5 dB，在 |x−0.5| < 0.10 时绝对值 ≤ 3 dB；≥ 80% 的窗口满足。 | checks.py：工程逐帧投影（工程测量：评分方以 rev1_hold_frames = rev2_trim_frames = 0 只读打开 project/scene.blend，影片第 i 帧 = 场景 frame_start + i，第 k 镜头用 CAM_Sk） + 分轨 ILD（R−L，200–4000 Hz，0.5 s 窗，低于分段峰值 30 dB 或 −70 dBFS 的窗不计）。 |
| X03 | gate | S 声音视点与剪辑 | ★ | 4.52 | 0.15 | 说话人声像（X02 规则，每段 ≥ 80% 窗口满足）：S1 中 L1 在 studio 分轨上的 ILD 与 HOST_A 头骨在 CAM_S1 的投影一致、L2（≤ 6 s 部分）与 HOST_B 一致；S3 中 L3（12.0 s 至 min(line3_end, 18.0 s)）在 taxi 分轨上与 DRIVER 头骨在 CAM_S3 的投影一致；S4 中 HOST_A 头骨在 line4_start–719 帧的 ≥ 90% 帧投影于画外，且 L4（≤ 24 s 部分）各窗 studio ILD 绝对值 ≥ 1.5 dB 并与 HOST_A 在 CAM_S4 相机坐标系中的左右侧同号（方位角在 ±10° 内则不要求同号），≥ 80% 窗口满足。 | checks.py：头骨中点投影/相机坐标（工程测量：评分方以 rev1_hold_frames = rev2_trim_frames = 0 只读打开 project/scene.blend，影片第 i 帧 = 场景 frame_start + i，第 k 镜头用 CAM_Sk） + 分轨 ILD。 |
| X04 | gate | S 声音视点与剪辑 | ★ | 0 | 0.20 | （信息项，权重 0，不评分）听点盲听：四段 2 s 片段（S1 L1、S2 L2 剪辑点后、S3 L3、S4 L3 剪辑点后）可分别听辨为直播间现场、车内现场、车载收音机、电话线路。 | 无自动化或人工听评环节，权重 0，仅作记录；可测的听点差异由 X01 评分。 |
| X05 | gate | S 声音视点与剪辑 |  | 2.26 | 0.15 | 嗓音变化与语速：四轨相加后每句在声明窗口内，浊音帧（40 ms 自相关峰 ≥ 0.5，60–400 Hz）的 f0 标准差 ≥ 1.5 半音（至少 20 个浊音帧）；发音语速 = transcript.en.txt 该句词数 ÷ 语音活动时长（M01 阈值，剔除 ≥ 0.20 s 的停顿）在 1.8–4.5 词/秒。 | checks.py 确定性测量；嗓音辨识与自然度无可靠自动测量，不评分。 |
| X06 | gate | P 场景、动作与工程 | ★ | 4.52 | 0.20 | 口型与倾听：说话者口型通道（名含 jaw/mouth/lip/chin/teeth/tongue 的骨骼相对静止姿态的旋转角或位移、名含 jaw/mouth/viseme/lip/open 等的形态键值、名含 jaw/mouth 的角色子物体）与对应分轨逐帧 RMS 包络（100–4000 Hz）的最大相关 r ≥ 0.5（滞后 ≤ 2 帧，约 67 ms）：HOST_A 于 S1 中 L1（studio）、HOST_B 于 S1 中 L2 的画内帧（studio，画内不足 10 帧则免）、DRIVER 于 S3 中 L3（taxi）；画内不说话者 HOST_B（S1 中 L1 期间对 studio；S4 全段对 studio+phone）所有口型通道 r < 0.3。 | checks.py：工程逐帧导出口型通道（工程测量：评分方以 rev1_hold_frames = rev2_trim_frames = 0 只读打开 project/scene.blend，影片第 i 帧 = 场景 frame_start + i，第 k 镜头用 CAM_Sk） + 分轨包络互相关。 |
| X07 | gate | P 场景、动作与工程 | ★ | 4.52 | 0.15 | 写实与人物：checks.py 核对三骨架均为 Armature 且各驱动至少一个网格（Armature 修改器），每只手 ≥ 4 条 ≥3 骨的手指链（.L/.R 等名称定侧），DRIVER 与 HOST_B 的手指骨在片中有 ≥ 5° 的姿态变化——任一不满足即 fail；满足时由评审模型看缩略图判定：各镜头为物理着色（材质有变化、可见夜间实用光源、柔和阴影），无平涂/卡通/白模/图片平面脸。 | checks.py（骨架/手指，fail-only）+ 评审模型（缩略图外观）。 |
| X08 | gate | R 两轮修订 | ★ | 4.52 | 0.20 | rev2 依赖修订：903 帧；T45 在第 723±1 帧；0–722 帧与 rev1 一致（每 37 帧抽样 PSNR ≥ 30）；rev2 第 723/780/840/900 帧与 rev1 第 732/789/849/909 帧 PSNR ≥ 30；四条分轨在 rev2 的 L4 起点（line4_start+3 帧）前与 rev1 相关 ≥ 0.99；此后每条非静音分轨（200–4000 Hz）比 rev1 提前 0.300 ± 0.010 s（互相关峰，r ≥ 0.5）；studio→radio 切换在 24.10 s（M03 口径：studio 不晚于 24.15 s 结束、radio 不早于 24.05 s 开始、间隙 ≤ 0.40 s、重叠 ≤ 0.05 s，24.20 s 后 studio ≤ −55 dBFS）；phone 分轨在 (caller_fader_down+15)/30 s 至 rev2 L4 起点 ≤ −60 dBFS，且 phone 上 L3 最后活动早于 studio 上 L4 起点。（属性取值不核对，见 M09。） | checks.py：PSNR 抽样、剪辑检测、分轨相关与互相关、包络。 |
| X09 | gate | N 叙事与证据 | ★ | 4.49 | 0.25 | 叙事可读性（依交付物）：缩略图中直播间（S1/S4）与出租车（S2/S3/S5）按规定顺序交替，可见收音机、电话与 ON AIR 灯；timeline.json/events.csv 所述“直播 → 车内收听 → 来电上播 → 主持人回应 → 开走”与画面一致。 | 评审模型依成片缩略图与文本判定（无人工盲审环节）。 |

## 预期分计算

| 层 | 判定数 | 权重 | 预期得分 |
|---|---|---|---|
| base | 6 | 25 | 20.6 |
| mid | 12 | 40 | 20.4 |
| gate | 9 | 35 | 7.3 |

- 不计组门槛：Σ权重×预期通过率 / Σ权重 = **48.3**。
- 计入组门槛（S 组门槛 B03 通过率 0.75、P 组 B06 0.85、R 组 0.90；假设门槛失败抹去该组约一半本会通过的分）：约 **45.8**。
- 设计估计，未经实测。
