# WFA-3D-003 评分表（reviewer-only，由 rubric.json 生成）

每条判定二元（部分满足即否），连续分=Σweight×pass（0–100）。组级门槛：B02 失败（场景可测时）→zone_*、integration、change 组全部记 0。scene.blend 缺失/无法打开（B01）时全部场景项判否，B06–B08 照常评分。评分只以 .blend 实测为准；manifest 仅用于 B08 格式与 M12 一致性。仅 G14 由评审模型看渲染图判定（权重 2.5/100）。expected_pass 为设计估计，未经实测。

测量口径：通用：bpy 打开 output/scene.blend；depsgraph=evaluated；单元 U 的局部系 = 答案键 units[U].origin_world/axes_world；ROOT=bpy.data.objects[f'{U}_ROOT']；所有静态量在第 1 帧取（scene.frame_set(1)），V2 在声明帧取。

## 分区

| 区 | 名称 | 单元 |
|---|---|---|
| A | 中央枢纽与尾段 / Core hub & aft | N1, K1, T1, N3, L5, L4, V3 |
| B | 前向轴线 / Forward spine | L1, A1, N2, V1, V2 |
| C | 前向侧舱 / Forward lateral modules | L2, L3, E1, A2 |
| D | 右舷桁架 / Starboard truss | T2, S1, T3, S2, R1, R3 |
| E | 左舷桁架 / Port truss | T4, S3, T5, S4, R2, R4 |

## 基础层（8 条，共 25 分）

| ID | 组 | 判定 | verify | 单 | WF | 权重 |
|---|---|---|---|---|---|---|
| B01 | delivery | output/scene.blend 存在，Blender 4.3 后台可打开；unit_settings.system=METRIC 且 scale_length=1。 | blender -b output/scene.blend 读取 scene.unit_settings；无法打开/无法测量→全部场景项判否（B06–B08 只看文件，照常评分）。 | 0.95 | 0.97 | 3.125 |
| B02 | contract | 28 个单元集合名逐一精确存在，另有 SITE 集合（组级门槛：失败则 zone/integration/change 组全 0）。 | 场景集合树（scene.collection 递归）中存在 28 个单元编号集合与 SITE；大小写、空格严格。B02 失败且场景可测时，zone_*/integration/change 组全部判否（postprocess gate）。 | 0.85 | 0.95 | 3.125 |
| B03 | contract | 每个单元集合内都有 `<ID>_ROOT` 空物体，且有非空网格 `<ID>_BODY`（顶点数>0），BODY 以 ROOT 为祖先。 | 逐单元：ROOT 在单元集合内且 type=='EMPTY'；BODY 在单元集合内、type=='MESH'，evaluated 顶点数>0（修改器/几何节点生效后，含 GN/集合实例几何）；沿 parent 链能到 ROOT。28/28 才通过。 | 0.80 | 0.93 | 3.125 |
| B04 | contract | SITE 中有日光灯 SUN（type=SUN）与相机 CAM_OVERVIEW、CAM_STBD、CAM_FWD。 | SITE.all_objects 名称与类型检查。 | 0.85 | 0.95 | 3.125 |
| B05 | animation | 场景帧范围 1–240，fps=24（fps_base=1）。 | scene.frame_start==1, frame_end==240, render.fps==24, fps_base==1.0。 | 0.90 | 0.95 | 3.125 |
| B06 | render | renders/overview.png 为 1920×1080 PNG 且非空白。 | PIL 读尺寸；灰度标准差>8 且非单色像素占比>2%。 | 0.85 | 0.95 | 3.125 |
| B07 | render | renders/stbd_truss.png 与 forward.png 均为 1920×1080 PNG 且非空白。 | 同 B06，两张都过才通过。 | 0.70 | 0.90 | 3.125 |
| B08 | manifest | manifest.json 可解析，units 恰 28 项，每项含 id/collection/built/params，params 字段名与题面类型表一致。 | json.load；按 id 首字母查字段集合完全相等（多/少字段均否）。 | 0.80 | 0.93 | 3.125 |

## 中间层（15 条，共 40 分）

| ID | 组 | 判定 | verify | 单 | WF | 权重 |
|---|---|---|---|---|---|---|
| M01 | zone_A | A 区（中央枢纽与尾段：N1,K1,T1,N3,L5,L4,V3）全部单元 ROOT 位姿正确（原点 ±0.10 m，三根轴方向各 ≤2°）。 | 通用：bpy 打开 output/scene.blend；depsgraph=evaluated；单元 U 的局部系 = 答案键 units[U].origin_world/axes_world；ROOT=bpy.data.objects[f'{U}_ROOT']；所有静态量在第 1 帧取（scene.frame_set(1)），V2 在声明帧取。 对区内每个 U：ROOT.matrix_world 平移 vs origin_world ≤0.10 m；ROOT 局部 X/Y/Z 轴 vs axes_world 夹角 ≤2°；scale 各分量 1±0.01。V2 在第 180 帧测。全部单元通过才通过。 | 0.55 | 0.85 | 2.667 |
| M02 | zone_B | B 区（前向轴线：L1,A1,N2,V1,V2）全部单元 ROOT 位姿正确（原点 ±0.10 m，三根轴方向各 ≤2°）。 | 通用：bpy 打开 output/scene.blend；depsgraph=evaluated；单元 U 的局部系 = 答案键 units[U].origin_world/axes_world；ROOT=bpy.data.objects[f'{U}_ROOT']；所有静态量在第 1 帧取（scene.frame_set(1)），V2 在声明帧取。 对区内每个 U：ROOT.matrix_world 平移 vs origin_world ≤0.10 m；ROOT 局部 X/Y/Z 轴 vs axes_world 夹角 ≤2°；scale 各分量 1±0.01。V2 在第 180 帧测。全部单元通过才通过。 | 0.45 | 0.80 | 2.667 |
| M03 | zone_C | C 区（前向侧舱：L2,L3,E1,A2）全部单元 ROOT 位姿正确（原点 ±0.10 m，三根轴方向各 ≤2°）。 | 通用：bpy 打开 output/scene.blend；depsgraph=evaluated；单元 U 的局部系 = 答案键 units[U].origin_world/axes_world；ROOT=bpy.data.objects[f'{U}_ROOT']；所有静态量在第 1 帧取（scene.frame_set(1)），V2 在声明帧取。 对区内每个 U：ROOT.matrix_world 平移 vs origin_world ≤0.10 m；ROOT 局部 X/Y/Z 轴 vs axes_world 夹角 ≤2°；scale 各分量 1±0.01。V2 在第 180 帧测。全部单元通过才通过。 | 0.45 | 0.80 | 2.667 |
| M04 | zone_D | D 区（右舷桁架：T2,S1,T3,S2,R1,R3）全部单元 ROOT 位姿正确（原点 ±0.10 m，三根轴方向各 ≤2°）。 | 通用：bpy 打开 output/scene.blend；depsgraph=evaluated；单元 U 的局部系 = 答案键 units[U].origin_world/axes_world；ROOT=bpy.data.objects[f'{U}_ROOT']；所有静态量在第 1 帧取（scene.frame_set(1)），V2 在声明帧取。 对区内每个 U：ROOT.matrix_world 平移 vs origin_world ≤0.10 m；ROOT 局部 X/Y/Z 轴 vs axes_world 夹角 ≤2°；scale 各分量 1±0.01。V2 在第 180 帧测。全部单元通过才通过。 | 0.50 | 0.85 | 2.667 |
| M05 | zone_E | E 区（左舷桁架：T4,S3,T5,S4,R2,R4）全部单元 ROOT 位姿正确（原点 ±0.10 m，三根轴方向各 ≤2°）。 | 通用：bpy 打开 output/scene.blend；depsgraph=evaluated；单元 U 的局部系 = 答案键 units[U].origin_world/axes_world；ROOT=bpy.data.objects[f'{U}_ROOT']；所有静态量在第 1 帧取（scene.frame_set(1)），V2 在声明帧取。 对区内每个 U：ROOT.matrix_world 平移 vs origin_world ≤0.10 m；ROOT 局部 X/Y/Z 轴 vs axes_world 夹角 ≤2°；scale 各分量 1±0.01。V2 在第 180 帧测。全部单元通过才通过。 | 0.40 | 0.80 | 2.667 |
| M06 | zone_A | A 区全部单元主结构尺寸正确（±3% 或 ±0.10 m 取大）。主结构 <U>_BODY 仅含舱体/桁架框/基座/转接杆/平台/底座本体，不含端口法兰环、对接机构、喷管等附件（附件为独立对象）。 | 把 <U>_BODY evaluated 顶点（含其 GN/集合实例几何）变换到 ROOT 局部系取包围盒：N/L/V 取 x 向长度=L、y/z 向=D；K 取 x 向=L、最大径向=D；T 取 L、W、H；S 取基座 L；R 取转接杆 x 向长度=mast；E 取 L、W、H；A 取基座顶面高度=h0。答案键 units[U].body / extra（已含变更单）。全部单元通过才通过。 | 0.55 | 0.85 | 2.667 |
| M07 | zone_B | B 区全部单元主结构尺寸正确（±3% 或 ±0.10 m 取大）。主结构 <U>_BODY 仅含舱体/桁架框/基座/转接杆/平台/底座本体，不含端口法兰环、对接机构、喷管等附件（附件为独立对象）。 | 把 <U>_BODY evaluated 顶点（含其 GN/集合实例几何）变换到 ROOT 局部系取包围盒：N/L/V 取 x 向长度=L、y/z 向=D；K 取 x 向=L、最大径向=D；T 取 L、W、H；S 取基座 L；R 取转接杆 x 向长度=mast；E 取 L、W、H；A 取基座顶面高度=h0。答案键 units[U].body / extra（已含变更单）。全部单元通过才通过。 | 0.50 | 0.85 | 2.667 |
| M08 | zone_C | C 区全部单元主结构尺寸正确（±3% 或 ±0.10 m 取大）。主结构 <U>_BODY 仅含舱体/桁架框/基座/转接杆/平台/底座本体，不含端口法兰环、对接机构、喷管等附件（附件为独立对象）。 | 把 <U>_BODY evaluated 顶点（含其 GN/集合实例几何）变换到 ROOT 局部系取包围盒：N/L/V 取 x 向长度=L、y/z 向=D；K 取 x 向=L、最大径向=D；T 取 L、W、H；S 取基座 L；R 取转接杆 x 向长度=mast；E 取 L、W、H；A 取基座顶面高度=h0。答案键 units[U].body / extra（已含变更单）。全部单元通过才通过。 | 0.50 | 0.85 | 2.667 |
| M09 | zone_D | D 区全部单元主结构尺寸正确（±3% 或 ±0.10 m 取大）。主结构 <U>_BODY 仅含舱体/桁架框/基座/转接杆/平台/底座本体，不含端口法兰环、对接机构、喷管等附件（附件为独立对象）。 | 把 <U>_BODY evaluated 顶点（含其 GN/集合实例几何）变换到 ROOT 局部系取包围盒：N/L/V 取 x 向长度=L、y/z 向=D；K 取 x 向=L、最大径向=D；T 取 L、W、H；S 取基座 L；R 取转接杆 x 向长度=mast；E 取 L、W、H；A 取基座顶面高度=h0。答案键 units[U].body / extra（已含变更单）。全部单元通过才通过。 | 0.55 | 0.85 | 2.667 |
| M10 | zone_E | E 区全部单元主结构尺寸正确（±3% 或 ±0.10 m 取大）。主结构 <U>_BODY 仅含舱体/桁架框/基座/转接杆/平台/底座本体，不含端口法兰环、对接机构、喷管等附件（附件为独立对象）。 | 把 <U>_BODY evaluated 顶点（含其 GN/集合实例几何）变换到 ROOT 局部系取包围盒：N/L/V 取 x 向长度=L、y/z 向=D；K 取 x 向=L、最大径向=D；T 取 L、W、H；S 取基座 L；R 取转接杆 x 向长度=mast；E 取 L、W、H；A 取基座顶面高度=h0。答案键 units[U].body / extra（已含变更单）。全部单元通过才通过。 | 0.50 | 0.85 | 2.667 |
| M11 | contract | 每个单元的端口空物体集合与答案键端口集合完全一致（含未连接端口；N2 为 Mk-B 的 5 个端口）。 | names = {o.name for o in coll.all_objects if re.fullmatch(rf'{U}_P\d+', o.name)}；== {U}_P* from answer-key ports_world。 | 0.45 | 0.80 | 2.667 |
| M12 | manifest | manifest 声明与 .blend 实测一致：计数字段等于对应代号对象数，尺寸字段与 BODY 实测相符（±3%），built 与实际一致。 | 对每个 built:true 单元：port_count=端口空物体数；ring_count=RING 数；window_count=WIN；payload_sites=SITE；tank_count=TANK；bay_count=BAY；blanket_count=BLANKET；segments_per_blanket=每块 BLANKET 子级 SEG 数（各块相等）；panel_count=PANEL；dof=JNT；solar_wings=WING；rcs_quads=RCS；slots_occupied=PL；length_m 与 BODY 实测 x 向长度、diameter_m 与 BODY 实测 max(y,z) 向尺寸（K 取 2·最大径向）相差 ≤3%；built 必须等于“BODY 存在且非空”。slots_total、blanket_length_m、panel_length_m 与字符串字段（bracing/gimbal/end_effector）不比较。全部一致才通过（不看对错，只看一致）。 | 0.30 | 0.70 | 2.667 |
| M13 | animation | SUN 灯光每个检查帧的局部 +Z 与 S(f) 夹角 ≤2°。 | 帧 1/60/120/180/240：SUN.matrix_world 第 3 列 vs answer-key sun.check_frames。 | 0.60 | 0.85 | 2.667 |
| M14 | animation | V2 运动形式：帧 1→180 为匀速直线（帧 60、120 的位置与首末连线按时间比例插值偏差 ≤0.3 m），首末距离 40±0.5 m，全程姿态不变（≤1°），帧 180–240 静止（≤0.02 m）。 | 取 V2_ROOT 世界矩阵于帧 1/60/120/180/200/240 比较（不检查泊位是否正确，泊位见 G07）。 | 0.55 | 0.85 | 2.667 |
| M15 | arms | A1、A2 的 `<ID>_EE` 世界位置与答案键 ee_world 偏差均 ≤0.15 m。 | bpy.data.objects['A1_EE'].matrix_world.translation vs units.A1.ee_world；A2 同。 | 0.35 | 0.75 | 2.667 |

## 门槛层（14 条，共 35 分）

| ID | 组 | 判定 | verify | 单 | WF | 权重 |
|---|---|---|---|---|---|---|
| G01 | zone_A | A 区（中央枢纽与尾段）全部单元图上离散特征全对（计数精确、形制正确，已应用变更单）。 | 按代号对象计数与答案键 units[U].params 精确比较；逐类型：K: tank_count(TANK)；L: window_count(WIN)、payload_sites(SITE)，且 SITE 质心位于 ROOT 局部 +Z 侧、WIN 质心位于 −Z 侧；N: port_count(端口空物体数)、ring_count(RING)；T: bay_count(BAY)、bracing（每个 BAY 在 ROOT 局部 +Y 侧面两条对角线 25%/75% 处采样点到网格最近距离 ≤0.15 m：X=两条都有，warren=恰一条）；V: solar_wings(WING)、rcs_quads(RCS)。全部单元全部特征对才通过。 | 0.15 | 0.60 | 2.500 |
| G02 | zone_B | B 区（前向轴线）全部单元图上离散特征全对（计数精确、形制正确，已应用变更单）。 | 按代号对象计数与答案键 units[U].params 精确比较；逐类型：A: dof(JNT)、end_effector（几何 = <ID>_EFFECTOR 及其全部子级网格，含实例几何；末端轴线 = 答案键 ee_world − 倒数第二关节，位置取场景 <ID>_EE；gripper：≥2 个松散部件伸出 EE 平面 ≥0.2 m；snare：恰 1 个松散部件，EE 前后 ±0.5 m 内轴线射线不击中网格，且该段轴线 0.1 m 半径内无顶点）；L: window_count(WIN)、payload_sites(SITE)，且 SITE 质心位于 ROOT 局部 +Z 侧、WIN 质心位于 −Z 侧；N: port_count(端口空物体数)、ring_count(RING)；V: solar_wings(WING)、rcs_quads(RCS)。全部单元全部特征对才通过。 | 0.12 | 0.55 | 2.500 |
| G03 | zone_C | C 区（前向侧舱）全部单元图上离散特征全对（计数精确、形制正确，已应用变更单）。 | 按代号对象计数与答案键 units[U].params 精确比较；逐类型：A: dof(JNT)、end_effector（几何 = <ID>_EFFECTOR 及其全部子级网格，含实例几何；末端轴线 = 答案键 ee_world − 倒数第二关节，位置取场景 <ID>_EE；gripper：≥2 个松散部件伸出 EE 平面 ≥0.2 m；snare：恰 1 个松散部件，EE 前后 ±0.5 m 内轴线射线不击中网格，且该段轴线 0.1 m 半径内无顶点）；E: slots_occupied(PL)；L: window_count(WIN)、payload_sites(SITE)，且 SITE 质心位于 ROOT 局部 +Z 侧、WIN 质心位于 −Z 侧。全部单元全部特征对才通过。 | 0.15 | 0.60 | 2.500 |
| G04 | zone_D | D 区（右舷桁架）全部单元图上离散特征全对（计数精确、形制正确，已应用变更单）。 | 按代号对象计数与答案键 units[U].params 精确比较；逐类型：R: panel_count(PANEL)；S: blanket_count(BLANKET)、segments_per_blanket(每块 SEG 子级数)；T: bay_count(BAY)、bracing（每个 BAY 在 ROOT 局部 +Y 侧面两条对角线 25%/75% 处采样点到网格最近距离 ≤0.15 m：X=两条都有，warren=恰一条）。全部单元全部特征对才通过。 | 0.15 | 0.60 | 2.500 |
| G05 | zone_E | E 区（左舷桁架）全部单元图上离散特征全对（计数精确、形制正确，已应用变更单）。 | 按代号对象计数与答案键 units[U].params 精确比较；逐类型：R: panel_count(PANEL)；S: blanket_count(BLANKET)、segments_per_blanket(每块 SEG 子级数)；T: bay_count(BAY)、bracing（每个 BAY 在 ROOT 局部 +Y 侧面两条对角线 25%/75% 处采样点到网格最近距离 ≤0.15 m：X=两条都有，warren=恰一条）。全部单元全部特征对才通过。 | 0.12 | 0.55 | 2.500 |
| G06 | change | CO-01 C1 落实：N2 为 Mk-B（BODY 长度、RING 数、5 个端口按附图位置），且 L1.P2–N2.P1、N2.P4–V1.P1、N2.P2–L2.P1、N2.P3–L3.P1 四对端口同轴对接。 | N2 BODY 尺寸/RING 计数/端口空物体世界位姿 vs 答案键；四对端口按 G10 口径判定。 | 0.30 | 0.75 | 2.500 |
| G07 | change | CO-01 C2 落实：V2 泊于 N2.P5——第 180 帧 V2_P1 与 N2_P5 同轴对接（位置 ≤0.10 m、法向反向 ≤2°、键向 ≤2°），第 1 帧 V2_P1 位于 N2_P5 外法向 40±0.5 m；N3_P3 空置。 | 帧 180、1 取端口空物体世界矩阵（答案键 units.V2.v2_port_world_track）；N3_P3 空置：帧 1/180/240 逐帧检查，N3 以外任何空物体原点、网格（含无面的线框网格、曲线及实例几何，按顶点/边距离）不得落在 N3_P3 0.5 m 内；三帧都须测到才可通过。 | 0.25 | 0.70 | 2.500 |
| G08 | change | CO-01 C3 及牵连落实：T4 长度/节间数按变更单，且 S3、T5、S4、R2、R4 的 ROOT 原点均在答案键位置 ±0.10 m（按原图纸会偏 1.2–2.4 m）。 | T4 BODY x 向长度、BAY 数；五个牵连单元 ROOT 平移 vs origin_world（pre_CO_shift_m 记录了忽略变更的偏移量）。 | 0.20 | 0.70 | 2.500 |
| G09 | change | CO-01 C4 落实：S4 为双轴——各检查帧 S4 全部 BLANKET 局部 +Z 与 S(f) 夹角 ≤3°。 | 帧 1/60/120/180/240；目标 units.S4.blanket_normal_target。 | 0.30 | 0.75 | 2.500 |
| G10 | integration | 全部 27 条连接（变更后拓扑）的端口对同轴对接：位置 ≤0.10 m、法向反向 ≤2°、键向同向 ≤2°（V2 在第 180 帧测）。 | 对 answer-key.links 每条 (a,pa,b,pb)：两个端口空物体世界矩阵比较；此外要求端口空物体相对本单元 ROOT 的局部位姿与图纸端口表一致（≤0.05 m、≤2°），防止只移空物体不移几何。 | 0.10 | 0.55 | 2.500 |
| G11 | integration | 太阳翼对日跟踪：S1、S2、S3 的全部 BLANKET 在各检查帧电池面法向与目标夹角 ≤3°（S1/S3 单轴取 S 在 α 轴法平面上的投影，S2 双轴取 S）。 | 帧 1/60/120/180/240：BLANKET.matrix_world 第 3 列 vs units.Sx.blanket_normal_target；另查单轴毯的转轴不漂移（毯局部系中 α 轴方向变化 ≤2°）。 | 0.25 | 0.70 | 2.500 |
| G12 | integration | 散热器侧对太阳：R1–R4 全部 PANEL 在各检查帧 |n·S(f)| ≤ sin3°，且板组绕各自转轴转动（PANEL 局部 +Z 始终 ⟂ 转轴 ±2°）。 | 帧 1/60/120/180/240：PANEL 第 3 列与 sun.check_frames 点积；转轴=units.Rx.rotary_axis_world。 | 0.30 | 0.75 | 2.500 |
| G13 | integration | 无穿插：检查帧 1/120/240 中，任意两个不同单元集合的 evaluated 网格（含 GN/集合实例几何）不相交；对接界面的接触除外——交对中任一三角形有顶点/质心落在已连接端口中心 1.0 m 内，或两三角形都有顶点位于该端口面平面 ±0.15 m 内且距端口中心 ≤2.5 m。28 个单元在三帧都必须有带面几何（否则判否，防止空几何空过）。 | 每单元合并 evaluated 多边形（含实例几何）建 BVHTree；两两 bvh.overlap()（最多 20000 对/单元对）；按上述端口界面规则剔除；扫描总时长上限 900 s，超时判否。端口位姿：场景端口空物体（每帧）+ 答案键静态端口。 | 0.20 | 0.55 | 2.500 |
| G14 | visual | 视觉审查：overview/stbd_truss/forward 三图中站体完整、可辨认各类单元、太阳翼深蓝毯面与白色散热板可辨、无明显破面或悬空件。 | 评审模型看三张渲染图按 4 项清单逐项判，任一项否即否。 | 0.40 | 0.65 | 2.500 |

## 预期分计算（设计估计，未实测）

| 层 | 条数 | 权重 | 单 agent 期望 | Workflow 期望 |
|---|---|---|---|---|
| base | 8 | 25 | 20.94 | 23.53 |
| mid | 15 | 40 | 19.2 | 32.8 |
| gate | 14 | 35 | 7.47 | 22.5 |
| 合计 | 37 | 100 | **47.6** | **78.8** |

单 agent 失分主因：28 单元×约 4.5 分钟≈2 小时以上读图施工，3600 s 内做不完全部区；批量模板导致计数/形制错（门槛层 G01–G05）；漏读 CO-01（N2 重编号、V2 改泊、T4 加长牵连、S4 双轴）；端口链式位姿与跟踪约束未在拼装后实测验收（G10–G13）。
