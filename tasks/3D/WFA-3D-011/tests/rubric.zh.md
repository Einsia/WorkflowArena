# WFA-3D-011 隐藏评分标准（REVIEWER ONLY）

> 2026-10-25 清理后由 tests/rubric.json 自动生成；以 rubric.json 为准。

每条判定二元（0/1），部分满足即0。reward = Σ(权重×通过)/Σ(权重)，权重为0的条目（M04）只作信息、不计分。M04 撤权后其权重按比例分给 mid 层其余16条（各 17/16），各层权重占比不变。除 B09、G11、G14 的画面部分由评委看联系表判定外，其余全部由 checks.py 机测（ffprobe/ffmpeg、numpy 音频分析、Blender 后台逐帧导出）。按 events.csv 声明帧测量；片中第 f 帧对应场景第 frame_start+f 帧。

| id | 层 | 组 | 关键 | 权重 | 判定 | 怎么验证 | 预期通过率 |
|---|---|---|---|---|---|---|---|
| B01 | base | delivery | ★ | 1 | 基础版成片编码契约：恰好900帧；H.264、yuv420p、1280×720、方形像素、恒定30fps；AAC立体声48kHz且音频覆盖整段画面。 | ffprobe -count_frames；检查 codec/pix_fmt/size/SAR/r_frame_rate=avg_frame_rate=30/1；音频时长≥画面时长-1帧。 | 0.92 |
| B02 | base | delivery |  | 1 | 修订版成片编码契约：恰好891帧，其余规格同 B01。 | 同 B01，帧数 891。 | 0.85 |
| B03 | base | delivery |  | 1 | 两版母带：综合响度 −18±2 LUFS；解码采样峰值 ≤ −1 dBFS；无削波样本。 | ffmpeg ebur128 / astats；削波=连续≥3样本/x/≥0.999。 | 0.85 |
| B04 | base | delivery |  | 1 | 分轨格式：两版均有 stems/speech、kitchen、hall 三条，48kHz PCM，时长分别为30.0 s与29.7 s（±1帧）。 | soundfile.info 逐条核对。 | 0.88 |
| B05 | base | delivery |  | 1 | events.csv 表头恰为 event_id,frame,description；14个必需 id 全部存在且各出现一次；帧号为0–899的整数。 | csv 解析。 | 0.9 |
| B06 | base | delivery |  | 1 | 两版 timeline.json 均可解析，且包含：shot/clip/range 键下的镜头范围，其数值含各镜头起点（基础版 180/390/540/720，修订版 180/381/531/711）和终点（900/899 或 891/890），帧或秒均可；4个转场（"transitions" 列表/字典含4项，或 T12/T23/T34/T45 四个 id）；speech、kitchen、hall 各有数值型 in/out（start/end/region/offset）；以及母带增益（与分轨名同处、键名含 "gain" 的数值）。 | checks.py：json 解析后遍历键路径与数值做上述匹配（键名不限于示例，按子串识别）。 | 0.85 |
| B07 | base | project | ★ | 1 | 工程可用：scene.blend 在 Blender 4.3 后台可打开；README 含一条同时出现 `blender` 与 `-b`/`--background`（顺序不限）的导出命令行；MEI/LIN（网格）、MEI_RIG/LIN_RIG（骨架）、POT/POT_LID/LADLE/BOWL/DOOR/STOVE、至少1个 SOUP_DOMAIN* 与 STEAM_DOMAIN* 对象、CAM_S1–CAM_S5（摄影机）全部存在且类型正确；场景自定义属性 revision_trim_frames 存在。 | blender -b -y scene.blend --python（_cdc_blend.rich_dump）导出对象表；README 逐行正则。打不开 → GG1；导出超时/脚本错误 → 本条失败（写明原因），不触发 GG1。 | 0.85 |
| B08 | base | delivery |  | 1 | credits.md 存在，写明 Blender 并说明台词制作方式（如 espeak-ng/sox/TTS/合成/录制人声）；qa.md 存在且非空；交付中所有文本文件无凭据、无指向网络媒体的 URL。 | checks.py：文件存在性 + 关键词正则 + 凭据/URL 媒体正则扫描。 | 0.9 |
| B09 | base | look |  | 1 | 无字幕、字卡、叠加图形或配乐：（机测）两版 kitchen、hall 分轨中不存在这样的 3 s 窗：≥80% 的 100 ms 帧为调性帧（80–4000 Hz 最强谱峰比其 ±1/3 倍频程内频点中位数高 ≥15 dB）且有 ≥3 个主导音级各占 ≥10% 帧（旋律/和声；稳定嗡声、哨声或带限噪声不算）；（画面，评委）两版成片联系表中无字幕、片名/说明字卡或叠加图形（场景道具上的文字不计）。 | checks.py 先做音乐检测，不合格直接判否；合格时交评委看联系表判画面叠加。 | 0.9 |
| M01 | mid | edit | ★ | 1.0625 | 剪辑结构：恰好4处剪切，分别位于第180、390、540、720帧（±1帧），均为无混合帧的硬切；无其他剪切；剪辑点附近无叠化；无定格（解码后连续≥6帧除编码舍入外完全相同，即全分辨率亮度无像素变化超过2级；固定机位镜头须有可见运动或渲染噪声）。 | 320×180 灰度逐帧差+直方图距离检测硬切；切点两侧混合帧检验；预期切点 ±6 帧内查持续中等差分（叠化）；全分辨率逐帧流式比较查定格（容差2级）。 | 0.65 |
| M02 | mid | sound | ★ | 1.0625 | J-cut 精度：hall 分轨起音（首个高于 −50 dBFS 的 10 ms 窗）在 12.00±0.05 s，11.95 s 前低于 −60 dBFS。 | hall.wav 10 ms RMS 包络定起音；起音前段 10 ms 窗最大电平。 | 0.55 |
| M03 | mid | speech |  | 1.0625 | 画外起句：声明的 line_door_start 在第360–389帧（剪辑前、门厅声音进入后），实测起点与声明相差≤6帧；line_door_end 落在 S3（390–539）。 | speech.wav VAD（webrtcvad 模式2）分句，与 events.csv 对照。 | 0.5 |
| M04 | mid | speech | ★ | 0 | （信息项，权重0——评分镜像中无 ASR 模型。）台词可懂：离线 whisper small.en 对 speech 分轨逐句识别，文本归一化（小写、去标点、展开缩写）后，三句合并 WER ≤0.20（12词中≤2词错），且每句≤1词错。 | 不评分；不交评委（weight 0 → na）。 | 0.65 |
| M05 | mid | speech |  | 1.0625 | 台词与声明一致：line_warn 与 line_thanks 实测起止与声明相差≤6帧，line_warn 全部落在 S4、line_thanks 全部落在 S5。 | 同 M03。 | 0.55 |
| M06 | mid | speech |  | 1.0625 | 两个声音可区分且不单调、语速合规：每句（取与声明窗口重叠的能量 VAD 段）自相关基频（70–400 Hz）浊音帧标准差≥1.5半音；梅一句与林两句的中位基频相差≥2半音；每句语速2.0–4.5词/秒（词数按 transcript.en.txt 书写计：3、3、4；句长=VAD 首个起点到末个终点）。 | checks.py：numpy 自相关 F0（40 ms 帧/10 ms 步长，归一化峰>0.5 为浊音）+ 能量 VAD。 | 0.58 |
| M07 | mid | speech | ★ | 1.0625 | 口型同步：S3（第390–539帧）中 LIN、S4（第540–719帧）中 MEI，各自至少一条口部通道（其骨架上 jaw/chin/mouth/lip 姿态骨的旋转角或位移，或其网格上 jaw/mouth/viseme 形态键）与 speech 分轨 30 fps RMS 包络在 ±2帧（≤80 ms）滞后内相关系数 r≥0.4。 | rich_dump 逐帧导出口部骨骼 matrix_basis 旋转角/位移与形态键值；checks.py 求各滞后皮尔逊相关取最大。（片中第 f 帧 = 场景第 frame_start+f 帧） | 0.4 |
| M08 | mid | camera | ★ | 1.0625 | 镜头参数（从工程逐帧导出，宽松阈值）：S1 平视（CAM_S1 平均高度1.1–1.9 m、俯仰±10°内）、位移<1 cm、焦距不变、景深关闭或 f≥5.6；S2 全程俯仰≤−30°（下俯）、位移<1 cm、景深开启且 f≤4；S3 平视（同 S1）、焦距不变、手持抖动（相对15帧滑动平均的最大偏离）位置1–60 mm 或视向≥0.1°（位置抖动仍须≤60 mm）；S4 LIN 评估后网格包围盒投影到 CAM_S4 占画面5–45%（镜头内中位数）且中心位于画面左或右40%区域，相机到 MEI_RIG 距离在镜头内缩短≥0.08 m，焦距不变，景深开启；S5 位置变化<2 cm、俯仰角单调上抬（容差0.05°）≥3°、景深开启。五镜头须全部满足。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 逐帧导出 CAM_S* matrix_world、lens、传感器、shift、dof/fstop，LIN 评估包围盒；投影公式与 bpy_extras.world_to_camera_view 一致。 | 0.4 |
| M09 | mid | sound |  | 1.0625 | 关门同步：DOOR 旋转在声明 door_close ±2帧内停止，hall 分轨在该处±2帧有关门瞬态（峰值高于前500 ms 底噪≥12 dB）。 | 工程导出 DOOR 角速度；hall.wav 瞬态检测。 | 0.45 |
| M10 | mid | sound |  | 1.0625 | 厨房声学连续：kitchen 分轨在13.0、18.0、24.0 s（修订版12.7、17.7、23.7 s）三处均无断口（跨点±500 ms 内无 >20 ms 低于 −70 dBFS 的段）；同室的24.0 s（23.7 s）处底噪电平跳变<3 dB；跨房间的13.0、18.0 s（12.7、17.7 s）处允许视角衰减/恢复，底噪电平跳变≤20 dB。底噪电平=跨点前/后各500 ms 内 20 ms RMS 的第10百分位。 | kitchen.wav 20 ms RMS 第10百分位跨点比较 + 静音段检测。 | 0.65 |
| M11 | mid | delivery |  | 1.0625 | 分轨一致：两版 stems 与解码混音对齐后在 ≤4 kHz 低通带内最小二乘残差 ≤ −25 dB（相对同带混音 RMS）；timeline.json 中声明的母带增益（键名含 db 按 dB，否则线性或 dB 取相符者）与拟合增益相差≤1 dB。找不到声明增益判否。 | 解码 AAC 后互相关对齐、4 kHz 低通、最小二乘拟合增益（AAC 192k 宽带残差约 −16 dB、4 kHz 以下约 −32 dB，故只比低频带）。 | 0.65 |
| M12 | mid | revision | ★ | 1.0625 | 修订画面传播：修订版第0–380帧与基础版同帧 PSNR≥30 dB；修订版第381–890帧与基础版第390–899帧 PSNR≥30 dB；修订版剪辑点为381、531、711帧（±1）。 | 逐帧 PSNR（下采样到 640×360）。 | 0.5 |
| M13 | mid | revision | ★ | 1.0625 | 修订声音传播与同源：修订版 hall 起音 11.70±0.05 s 且 11.65 s 前低于 −60 dBFS；11.65 s 前混音与基础版一致（≤4 kHz 带内残差≤ −25 dB）；11.7 s 之后 speech 相对基础版整体提前0.300±0.010 s；评分方以 revision_trim_frames=9 从同一 .blend 重渲修订版第400帧（480×270、8 spp；求解者渲染器无输出时改用 Cycles），与修订成片 480×270 SSIM≥0.75。重渲失败/超时判否。 | 互相关求偏移；blender -b -y 设置属性后渲染单帧。（片中第 f 帧 = 场景第 frame_start+f 帧） | 0.4 |
| M14 | mid | project | ★ | 1.0625 | 工程即真实来源：评分方从 scene.blend 重渲基础版第90、270、465、630、810帧（480×270、8 spp；无绑定相机的标记时依次用 CAM_S1–S5；求解者渲染器无输出时改用 Cycles），与成片 480×270 SSIM 均≥0.75。渲染失败/超时判否（不触发 GG2）。 | blender -b -y 低采样重渲 + SSIM。（片中第 f 帧 = 场景第 frame_start+f 帧） | 0.45 |
| M15 | mid | project | ★ | 1.0625 | 人物绑定：MEI/LIN 网格各由对应骨架驱动（骨架修改器或骨架父级）；每个骨架两只手各有≥4条手指链、每链≥3根带关键帧的骨（按 thumb/index/middle/ring/pinky+左右侧名称分组，或手骨下的骨链），且每只手至少2根手指的关键帧曲线不同（独立动画）；每个角色有带关键帧的 jaw/chin/mouth/lip 骨或有动画的 jaw/mouth/viseme 形态键；两人网格为立体（世界包围盒三轴均≥0.1 m）。 | rich_dump：armature 修改器/父子关系、骨表、动作 fcurve（含 NLA）、形态键动作、评估包围盒。 | 0.5 |
| M16 | mid | sound |  | 1.0625 | 掀盖声音语义：kitchen 分轨在声明 lid_lift ±3帧内有锅盖接触/离锅瞬态；lid_lift 后1 s 内沸腾声（1–6 kHz 带）比前1 s 升高≥3 dB。 | kitchen.wav 带通能量 + 瞬态检测。 | 0.4 |
| M17 | mid | delivery |  | 1.0625 | 事件声明合理：lid_grip<lid_lift<180；ladle_in<pour_start<pour_end 均在180–389；door_close 在390–539；line_warn 在540–719；lin_touch<mei_release，mei_release 在720–899；line_thanks 在720–899；同一句起<止。 | 纯 csv 逻辑检查；与实测无关。 | 0.6 |
| G01 | gate | contact | ★ | 1 | 握盖接触：声明 lid_grip 帧 MEI 任一手/手指骨（骨段 head–tail）到 POT_LID 把手（锅盖顶部中心 3 cm 内的表面采样点）距离≤1.5 cm；lid_grip 之前 POT_LID 原点移动<2 mm；lid_grip 之后直到锅盖离开 CAM_S2 画框（或第389帧），每帧手到把手距离≤2 cm。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 逐帧导出 MEI_RIG 手部骨世界坐标与 POT_LID 变换、表面采样；checks.py 求骨段到点集最近距离；CAM_S2 投影判出画。 | 0.2 |
| G02 | gate | contact | ★ | 1 | 离锅与热气因果：POT_LID 最低表面点与 POT 最高表面点的间隙相对第0帧首次增加>5 mm 的帧落在声明 lid_lift ±2帧内；第175–185帧锅盖逐帧上升（z 增加）；STEAM_DOMAIN* 气体密度总和（Blender 读取烘焙缓存）在 lid_lift 后15帧内的峰值≥其前15帧均值的3倍。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump：表面采样+逐帧变换；Fluid domain_settings.density_grid 求和。 | 0.2 |
| G03 | gate | edit | ★ | 1 | T12 动作匹配：剪辑前（178→179）与剪辑后（180→181）POT_LID 速度方向夹角≤45°、速率比0.5–2；179→180 额外位置跳变（扣除两速度均值）<3 cm；锅盖中心在 CAM_S1（178→179）与 CAM_S2（180→181）投影中均向画面上方运动；第180帧锅盖至少部分位于 CAM_S2 画框内。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 变换 + 相机投影。 | 0.25 |
| G04 | gate | contact | ★ | 1 | 舀汤接触：声明 ladle_in 到 pour_end 每帧 MEI 右手骨（未区分左右时取任一手骨）到 LADLE 表面≤2 cm；声明 ladle_in 帧勺头中心位于液体内（SOUP_DOMAIN* 评估网格之并）；ladle_in 到 pour_start 之间≥50%采样帧勺头（LADLE 长轴较宽一端的球域）内液体≥1 mL。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump extra：逐帧评估 SOUP_DOMAIN* 网格建 BVH，最近点法向判内外，网格采样估体积。 | 0.15 |
| G05 | gate | sim | ★ | 1 | 倒汤：声明 pour_start 到 pour_end 之间≥70%帧液体连接勺头与碗（勺头→碗沿中心线段 20–80% 处各点在液体内或距液面≤1.5 cm）；BOWL 内（BOWL 局部包围盒内切圆柱，网格采样）液体体积从不比其累计最大值低5%以上且5 mL 以上，pour_end 时≥30 mL 且≥pour_start 时勺头液体体积的50%。（片中第 f 帧 = 场景第 frame_start+f 帧） | 同 G04（逐帧 BVH 采样）。 | 0.15 |
| G06 | gate | contact | ★ | 1 | 碗始终有支撑：声明 pour_end 到第899帧每一帧 BOWL 与 MEI 或 LIN 至少一根手/手指骨距离≤2 cm，或 BOWL 最低点正下方表面≤5 mm（场景射线检测）。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump：骨段到 BOWL 表面采样距离；extra 中 scene.ray_cast。 | 0.15 |
| G07 | gate | contact | ★ | 1 | 交接重叠：实测 lin_touch（LIN 手/手指骨首次距 BOWL 表面≤1.5 cm）与 mei_release（MEI 手/手指骨最后一次≤1.5 cm）分别与声明值相差≤3帧；两人同时≤1.5 cm 的帧≥4；实测 mei_release 落在 S5（720–899）。（片中第 f 帧 = 场景第 frame_start+f 帧） | 同 G06 的逐帧距离表。 | 0.12 |
| G08 | gate | edit | ★ | 1 | T45 动作匹配与轴线：BOWL 在 719→720 的额外跳变（扣除 718→719 与 720→721 速度均值）<3 cm，剪辑处速度≥1 cm/s；CAM_S4@719 与 CAM_S5@720 投影中 MEI 手部与 LIN 手部（各骨架手骨均值）横坐标差的符号相同（不越轴）。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 变换 + 骨骼 + 投影。 | 0.2 |
| G09 | gate | sim | ★ | 1 | 热气模拟：有 STEAM_DOMAIN* 对象为 Mantaflow 气体域，其缓存目录位于 project/ 内且含覆盖 S2 与 S5 ≥80% 帧的文件；采样帧（Blender 读取）密度场在 S2、S5 每个采样帧非零，4×4×4 粗分布在相邻采样间变化（≥80% 的相邻对；非静止/冻结场），密度加权竖直速度向上（中位数>0）。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump：domain_settings（cache_directory、density_grid、velocity_grid、domain_resolution）；缓存文件名中的帧号覆盖率。 | 0.15 |
| G10 | gate | sim | ★ | 1 | 汤液模拟：有 SOUP_DOMAIN* 对象为 Mantaflow 液体域，其缓存目录位于 project/ 内且含覆盖 S2 ≥80% 帧的文件；液体几何（SOUP_DOMAIN* 评估网格）在≥90%的 S2 采样帧存在且顶点数在 S2 内有变化（模拟液面，非刚体道具）。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump：fluid 设置 + 缓存文件 + 逐帧评估网格。 | 0.15 |
| G11 | gate | look | ★ | 1 | 写实渲染：（机测）主体对象 MEI、LIN、POT、POT_LID、BOWL、LADLE、STOVE 使用基于节点的 BSDF 材质，其中≥3个有纹理或 BSDF 输入接有节点（表面变化）；至少一个柔光（面光、灯光尺寸/半径>2 cm、日光角>0.3°）或环境/天空世界光；Cycles 渲染开启降噪；5个镜头中至少3个平涂块指数≤0.35（平涂块=方差<1.0且与上下左右4块均值差均<0.5的8×8亮度块，排除均值<24或>235的块；每15帧抽样、每镜头取中位数）；（画面，评委）联系表呈现写实材质、光照与阴影，无平面着色/卡通/未贴图白模外观。（组级门槛 GG3。） | checks.py 先测材质/灯光/降噪/平涂块指数，任一不合格直接判否；全部合格时交评委看联系表。 | 0.25 |
| G12 | gate | contact |  | 1 | 手指包裹：声明 lid_grip 帧（POT_LID 把手，MEI）、ladle_in–pour_end 中点（LADLE，MEI 右手）、lin_touch–mei_release 中点（BOWL，MEI 与 LIN 各自）一只手至少3根不同手指（按名称与左右侧分组的手指骨）有骨段距所握物体≤2 cm。（片中第 f 帧 = 场景第 frame_start+f 帧） | rich_dump 骨段 + 物体表面采样距离。 | 0.15 |
| G13 | gate | sim |  | 1 | 碗中汤随碗运动：声明 pour_end 到片尾每个采样帧碗内液体≥pour_end 时体积的50%，且其质心与碗轴水平距离≤3 cm；声明 lin_touch 到 mei_release 之间至少一帧碗内液面（7×7 网格向下射线命中点）高差≥2 mm（非刚性液面）。（片中第 f 帧 = 场景第 frame_start+f 帧） | 同 G04（逐帧 BVH 采样与射线）。 | 0.15 |
| G14 | gate | narrative | ★ | 1 | 叙事可读（画面）：仅凭联系表即可读出“奶奶在厨房盛汤—孙子穿冬衣从门口进来—热汤从她手中递到他手里”；画面无解释性文字。（先闻其声、房间声学与无音乐由 M02、M03、M10、B09 机测。） | 评委看两版成片联系表（视觉判断）。 | 0.3 |

## 组级门槛

- GG1：scene.blend 缺失或无法在 Blender 4.3 后台打开 → project、camera、contact、sim 组全部记0（导出超时/脚本错误不触发本门槛，相关条目各自记失败并写明原因）。
- GG2：M14 重渲 SSIM 实测 <0.75 → contact 组记0（重渲失败/超时只使 M14 失败，不触发本门槛）。
- GG3：G11 失败（机测部分不合格，或评委判定为平面着色/卡通/白模）→ look、sim 组其余条目记0。
- GG4：events.csv 缺失或无法解析 → 所有按声明帧测量的条目（M03、M05、M09、M16、M17、G01、G02、G04–G07、G13）记0。

## 汇总

```
{
 "n": 40,
 "by_tier": {
  "base": 9,
  "mid": 17,
  "gate": 14
 },
 "tier_share": {
  "base": 0.225,
  "mid": 0.425,
  "gate": 0.35
 },
 "tier_mean_pass": {
  "base": 0.878,
  "mid": 0.514,
  "gate": 0.184
 },
 "critical": 23,
 "expected_score": 48.0,
 "n_scored": 39,
 "weight_total": 40.0,
 "tier_weight": {
  "base": 9,
  "mid": 17.0,
  "gate": 14
 },
 "judge_items": [
  "B09 (visual part, after the measured music test passes)",
  "G11 (visual part, after the measured parts pass)",
  "G14"
 ],
 "note": "expected_score = 100*Σ(w·expected_pass)/Σw over items with expected_pass (2026-10-25 weights)."
}
```
