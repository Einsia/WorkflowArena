# WFA-3D-008 评分表（reviewer-only）

版本 w08-v1 (2026-10-24)。每条判定二元，部分满足即否。连续分=Σweight×pass/Σweight（0–100）。G13 由 LLM 评委看渲染图判定，其余 31 条由 checks.py 确定性判定。组级门槛：B02 集合合同整体缺失（命中 <16 个单元集合）→ contract 与全部 zone_* / integration / change_order 组记 0；B03 中心线合同缺失超过一半→ integration、change_order、animation 组记 0。scene.blend 缺失或打不开时全部场景条目判否。容差：尺寸 ±3% 或 ±0.10 m 取大者，角度 ±2°，计数精确（各条另有规定者从之）。expected_pass 为设计估计，未实测。

## 分区

| 区 | 名称 | 单元 |
|---|---|---|
| A | 枢纽站场 / Hub yard | D01、D02、D03、T01、T02、P01、P02、S01、X01、X02 |
| B | 东环爬坡 / East climb | T03、T04、X03 |
| C | 北线与涧桥 / North line & creek bridge | T05、T06、T07、B01 |
| D | 西环下坡 / West descent | T08、T09、X04 |
| E | 支线与隧道 / Branch & tunnel | T10、T11、G01、G02 |
| F | 河桥与终点站 / River bridge & terminus | T12、B02、P03、S02、X05 |
| R | 列车 / Trains | R1、R2、R3 |

## 基础层（8 条，合计 25 分）

| ID | 组 | 判定 | 验证方法 | 权重 | P(single) | P(workflow) |
|---|---|---|---|---|---|---|
| B01 ★ | delivery | output/scene.blend 存在，能在 Blender 4.3 后台打开；场景单位为公制、单位比例 1.0。 | checks.py：blender -b output/scene.blend 后台导出；scene.unit_settings.system=='METRIC' 且 scale_length==1.0。scene.blend 缺失或打不开时本条及全部场景条目判否。 | 3.125 | 0.95 | 0.98 |
| B02 ★ | contract | 32 个单元集合（T01–T12、D01–D03、P01–P03、S01–S02、G01–G02、B01–B02、X01–X05、R1–R3）与 SITE 集合齐全，名称完全一致，每个集合至少含 1 个网格或曲线对象。 | checks.py：bpy.data.collections 名称精确匹配（区分大小写）；递归 all_objects 中 type in {MESH,CURVE} 计数 ≥1。缺任一→本条否；命中 <16 个单元集合→ contract、全部 zone_*、integration、change_order 组记 0（门槛）。 | 3.125 | 0.85 | 0.97 |
| B03 | contract | 中心线合同：T01–T12 各有 <ID>_AXIS 曲线，D01–D03 各有 _AXIS_MAIN 与 _AXIS_DIV 曲线，共 18 条，均位于对应集合内。 | checks.py：按名称查对象，type 为 CURVE（或仅含边的 MESH）、位于对应集合 all_objects 中且能得到折线（Bezier/Poly 样条直接采样，NURBS 用 evaluated to_mesh 边链）。 | 3.125 | 0.80 | 0.95 |
| B04 | contract | 构件命名合同：题面对象表中每类单元的必需对象（MAST/SLEEPERS/MACHINE/DECK/COL/BENCH/BODY/ROOF/OPENING/LAMP/PORTAL/VOUSSOIR/WING/PIER/DIAG 或 ARCH/V01…/AXLE）在所有已建单元中都存在（图纸无对应构件者除外，如无雨棚站台无 COL、无钟楼无 TOWER）。 | 对每单元按前缀 glob 查找；无设计构件的跳过（answer-key: canopy=none、clock_tower=false、ladder=false、masts>0 均有）。任一单元缺任一必需前缀→否。 | 3.125 | 0.65 | 0.90 |
| B05 | delivery | 动画时间线：scene.render.fps=24（fps_base=1），frame_start=1，frame_end=1440。 | 读 scene.render.fps/fps_base、scene.frame_start/frame_end。 | 3.125 | 0.90 | 0.97 |
| B06 | delivery | 渲染：overview.png 1920×1080，hub.png 与 terminus.png 1280×720，均为可解码 PNG 且非空白（灰度标准差 >5）。 | PIL 打开读尺寸；转灰度计算 std>5。 | 3.125 | 0.80 | 0.95 |
| B07 | delivery | manifest.json 为合法 JSON 数组，恰含 32 项，id 与单元编号一一对应，每项含 id/collection/built/params，params 含题面规定的该类型全部字段名。 | json.load；集合比较 ids；按类型检查字段名集合。 | 3.125 | 0.75 | 0.93 |
| B08 | site | SITE 集合内有地形网格，以及东河与北涧水体：东河水体网格在 y∈[-260,-200] 区间内覆盖 x=464.1±10 的位置，北涧水体在 T06 正下方（x∈[-10,50]、y≈140）且顶面低于 5.0；丘陵网格覆盖 G01–G02 之间线路的正上方。 | checks.py：SITE 中有 evaluated 包围盒 ≥300×200 m 的网格（地形）；射线测试：自 (454.1/464.1/474.1, −245, 60)、(464.1, −215, 60)、(464.1, −255, 60) 向下，首个命中须为 SITE 水体对象（对象名或材质名含 water/river/creek/stream/lake/brook/水/河/涧）；自 (30,150,4.5) 与 (30,130,4.5) 向下命中 SITE 水体且 z<5.0；自 T11 里程 60 处中线上方 30 m 向下先命中 SITE 网格且命中点高于轨面 3 m 以上。 | 3.125 | 0.75 | 0.90 |

## 中间层（11 条，合计 40 分）

| ID | 组 | 判定 | 验证方法 | 权重 | P(single) | P(workflow) |
|---|---|---|---|---|---|---|
| M01 | zone_A | A 区（枢纽站场）就位与尺寸：D01–D03 三条道岔的岔尖与两端、T01/T02 起终点平面误差 ≤0.10 m；P01/P02 站台平面中点 ≤0.30 m，长宽 ±3%，站台面高程 ±0.05 m；S01 平面中点 ≤0.50 m，长、进深 ±3%；X01/X02 立柱 ≤0.30 m。 | checks.py：轴线端点与 answer-key units.<ID>.geom 的 start/end（道岔 toe/main_end/div_end）比较；DECK、S01_BODY 为 evaluated 网格水平 PCA 有向包围盒的中心/长宽/顶面 z；X 立柱位置 = <ID>_MAST 最低 0.3 m 内顶点的平面质心。全部单元满足才通过。 | 3.636 | 0.50 | 0.80 |
| M02 | zone_B | B 区（东环爬坡）：T03、T04 起终点平面误差 ≤0.15 m、轨面高程 ±0.05 m；X03 立柱 ≤0.30 m。 | axis 端点：对 <ID>_AXIS（或 D 的 _AXIS_MAIN/_AXIS_DIV）取 evaluated 曲线（to_mesh 后世界坐标折线）两端点，与 answer-key units.<ID>.geom 的 start/end（道岔 toe/main_end/div_end）比较。 | 3.636 | 0.55 | 0.85 |
| M03 | zone_C | C 区（北线与涧桥）：T05–T07 起终点 ≤0.15 m、高程 ±0.05 m；B01 桥长中点 ≤0.30 m，桥长 40.0、桥宽 6.0 ±3%，桁高（桥面顶至斜杆顶）6.0±0.30 m。 | checks.py：axis 端点与 answer-key units.<ID>.geom 的 start/end 比较；B01_DECK evaluated 网格水平 PCA 有向包围盒的中心/长/宽；桁高 = B01_DIAG* 世界包围盒顶 z − B01_DECK 顶 z。 | 3.636 | 0.50 | 0.85 |
| M04 | zone_D | D 区（西环下坡）：T08、T09 起终点 ≤0.15 m、高程 ±0.05 m；X04 立柱 ≤0.30 m。 | axis 端点：对 <ID>_AXIS（或 D 的 _AXIS_MAIN/_AXIS_DIV）取 evaluated 曲线（to_mesh 后世界坐标折线）两端点，与 answer-key units.<ID>.geom 的 start/end（道岔 toe/main_end/div_end）比较。主环闭合误差在此只计端点到键值的距离。 | 3.636 | 0.50 | 0.85 |
| M05 | zone_E | E 区（支线与隧道）：T10、T11 起终点 ≤0.15 m、高程 ±0.05 m；G01、G02 洞口中心 ≤0.30 m；净洞口（由端墙与拱石共同围成）洞高 ±3%，洞宽 ±3%（洞宽取最大宽或轨面处宽；马蹄形 G02 另接受图纸轮廓最大宽 1.12×6.00=6.72）；端墙宽 ±3%；端墙高 ±3%，压顶计入 PORTAL 时允许超出至 +0.7 m。容差均为 ±3% 或 ±0.10 m 取大者。 | checks.py：<ID>_PORTAL 与 <ID>_VOUSSOIR* 的 evaluated 网格合并建 BVH，在端墙平面内按 0.1 m 网格沿端墙法向（PORTAL 竖直面主方位）射线扫描；轨面 +1 m 处离中心最近的封闭未命中区间为洞口，向上追踪至首个命中得洞高、各行最大未命中宽得洞宽（或取轨面 +0.2 m 处宽度，二者任一在容差内即可）；端墙宽 = 半高处命中范围；端墙高 = 最高命中行 − 轨面（T11 AXIS 在洞门处的 z）。 | 3.636 | 0.45 | 0.82 |
| M06 | zone_F | F 区（河桥与终点站）构件尺寸（与位置无关）：B02 桥长 48.0、桥宽 6.5 ±3%；P03 长宽 ±3%、站台面高出轨面 0.55±0.05 m；S02 长、进深 ±3%，檐高 ±0.20 m；X05 高度 ±0.20 m。 | 各对象沿自身主轴的有向包围盒；P03 高度 = DECK 顶 z − 其中点处 T12 轨面 z。 | 3.636 | 0.40 | 0.82 |
| M07 | zone_R | R 区（列车）编组尺寸：三列车车辆数正确，各车长 ±3% 或 ±0.10 m，车体主色与图纸色值各通道差 ≤0.08（Base Color 按线性转 sRGB 后比较，或按原值直接比较，任一满足即可）。 | checks.py：<ID>_V## 对象（含子对象）evaluated 网格在车辆局部 X 方向的范围；主色 = 面积最大材质的 Principled Base Color（Base Color 接 RGB 节点时取该节点颜色），按线性→sRGB 与按原值两种读法，任一读法各通道差 ≤0.08 即通过。 | 3.636 | 0.45 | 0.85 |
| M08 | manifest | manifest 与实测一致：所有 built=true 单元中，离散字段（masts、mast_side、sleeper、hand、frog、machine_side、canopy、canopy_columns、benches、floors、bays、roof、clock_tower、aspects、colors、ladder、shape、voussoirs、wing_walls、type、spans、panels_per_span、piers、n_vehicles、loco_axles）与 .blend 实测全部相同，且没有 built=true 而集合为空的单元。 | 用 G01–G07 的同一测量函数得到实测值，与 manifest 逐字段比较（不与答案键比较）。 | 3.636 | 0.45 | 0.75 |
| M09 | animation | 在轨运行：第 1 帧起每 12 帧采样一次（共 120 帧），三列车每辆车原点到最近的 AXIS 折线平面距离 ≤0.30 m、高程差 ≤0.10 m，车辆局部 +X 与该处线路切线夹角 ≤3°（或 177°–180°）。 | checks.py：第 1 帧起每 12 帧取 matrix_world；轴线折线为全部 <ID>_AXIS/_AXIS_MAIN/_AXIS_DIV 的世界坐标折线（Bezier 每段 33 点采样、Poly 控制点、NURBS 用 evaluated 边链），取最近线段。 | 3.636 | 0.45 | 0.75 |
| M10 | animation | R1 时刻（变更单未改动部分）：R1 在第 1–48、720–816、1392–1440 帧停于 P01——列车全长中点与 P01 中点在 T01 中心线上的投影点（answer-key P01.geom.axis_point）平面距离 ≤2.0 m，且区间内各车位移 ≤0.05 m；第 384 帧与第 1104 帧 R1 中点距该投影点 >50 m。 | checks.py：列车中点 = 各车两端点（车辆原点 ± 本车局部 X 包围范围，沿 matrix_world 第 1 列）中相距最远两点的中点；参考点 = units.P01.geom.axis_point；区间首末帧与每 6 帧采样，静止 = 各车原点相对区间首帧位移 ≤0.05 m。 | 3.636 | 0.50 | 0.82 |
| M11 | geometry | 纵断面：T01–T12 的 AXIS 在区段起点、终点及中点处的轨面高程与键值相差 ≤0.05 m（中点按线性坡度计算）。 | AXIS 折线按弧长取 0、L/2、L 三点的 z。 | 3.636 | 0.45 | 0.80 |

## 门槛层（13 条，合计 35 分）

| ID | 组 | 判定 | 验证方法 | 权重 | P(single) | P(workflow) |
|---|---|---|---|---|---|---|
| G01 | zone_A_discrete | A 区离散特征全对：D01 左开、D02 右开、D03 右开；D01/D02 为 1:6（侧股偏角 9.46°）、D03 为 1:9（6.34°）；三台转辙机侧别；P01 双排共 8 柱、5 座椅，P02 单排 6 柱、3 座椅；S01 两层 11 开间（正立面 22 洞口）、四坡顶、有钟楼；X01 三灯 G/Y/R 有爬梯，X02 两灯 G/R 无爬梯；T01/T02 支柱数、侧别、轨枕类别。 | 道岔：_AXIS_DIV 终点切线与 _AXIS_MAIN 方向夹角 ±0.5°、偏向侧；MACHINE 质心在直股左/右。站台：COL 连通块数与按横向偏移聚类的排数；BENCH 块数。S01：OPENING 块数、按 z 聚类层数；ROOF 面法线（nz>0.2）按水平方位聚类数 =4 为四坡、=2 为双坡；TOWER 存在。X：LAMP 按 z 降序的材质颜色（hue 归类 G/Y/R）、LADDER 存在性。T：MAST 块数、相对 AXIS 侧别（叉积符号）、SLEEPERS 材质颜色（sRGB；Base Color 按线性转 sRGB 与按原值两种读法取更接近图例者）：离图例木色 #5B3A1E 更近且 R≥B 判木，否则饱和度 <0.25 判混凝土。键值见 answer-key。 | 2.692 | 0.08 | 0.50 |
| G02 | zone_B_discrete | B 区离散特征全对：T03、T04 支柱数与侧别、轨枕类别、各圆曲线均为左转；X03 四灯自上而下 Y/G/R/Y 且有爬梯。 | 同 G01 测量函数；圆曲线转向 = AXIS 折线曲率符号。 | 2.692 | 0.30 | 0.65 |
| G03 | zone_C_discrete | C 区离散特征全对：T05–T07 支柱数、侧别与轨枕；B01 为下承式华伦桁架 2 孔、1 座中间桥墩、每孔 6 节间（斜杆连通块共 48）。 | B01_PIER 块数=1；B01_DIAG 块数=48（2 孔×6 节间×每节间 2 斜杆×2 片桁）；桁架片位于桥面两侧（下承式：桁架顶高于轨面 ≥4 m）。 | 2.692 | 0.12 | 0.55 |
| G04 | zone_D_discrete | D 区离散特征全对：T08、T09 支柱数、侧别、轨枕；X04 三灯 Y/G/R、无爬梯。 | 同 G01。 | 2.692 | 0.30 | 0.65 |
| G05 | zone_E_discrete | E 区离散特征全对：T10/T11 支柱数、侧别、轨枕；G01 半圆拱、13 块拱石、八字翼墙；G02 马蹄形拱、11 块拱石、一字翼墙。 | VOUSSOIR 块数；洞口形：起拱线以下洞宽在轨面处与最大洞宽之比 ≥0.98 为半圆拱、≤0.95 为马蹄形；翼墙：WING 主平面与端墙平面夹角 15°–75° 为八字、≤5° 为一字。 | 2.692 | 0.12 | 0.55 |
| G06 | zone_F_discrete | F 区离散特征全对：T12 支柱 4 根及侧别、轨枕；B02 上承式石拱 3 孔、2 墩；P03 无雨棚、4 座椅；S02 一层 5 开间、双坡顶、无钟楼；X05 两灯 Y/R、有爬梯。 | 同 G01；B02_ARCH 块数=3，B02_PIER 块数=2。 | 2.692 | 0.15 | 0.60 |
| G07 | zone_R_discrete | R 区离散特征全对：R1 内燃机车 V01 6 轴、R2 蒸汽机车 V01 4 轴且后挂煤水车 V02（长 7.0 m）、R3 动车头车 V01 4 轴；第 1 帧各列车车辆按 V01..Vn 依次相邻（相邻车辆原点间距 = 两车长均值 ±1.5 m）。 | checks.py：<ID>_V01_AXLE 计数（≥2 个对象数对象，单个对象数网格连通块）；R2_V02 存在且长 7.0（±3%）；第 1 帧相邻车辆原点间距。车体颜色只在 M07 判定。 | 2.692 | 0.20 | 0.65 |
| G08 | change_order | 变更单线形落实：T12 AXIS 终点平面误差 ≤0.15 m（改线后键值）、终点切线方位 −15°±1°、总长 254.72±0.5 m；场景中不存在旧线位（旧终点 (578.08,−207.46) 5 m 范围内无任何轨道 AXIS 或车挡）。 | axis 端点：对 <ID>_AXIS（或 D 的 _AXIS_MAIN/_AXIS_DIV）取 evaluated 曲线（to_mesh 后世界坐标折线）两端点，与 answer-key units.<ID>.geom 的 start/end（道岔 toe/main_end/div_end）比较；旧终点见 answer-key stale_before_co.T12_end。 | 2.692 | 0.30 | 0.80 |
| G09 | change_order | 变更单牵连单元：B02 桥长中点位于改线后 T12 与东河河道中线交点 ≤0.50 m、桥轴方位 −15°±2°；P03、S02、X05 均位于按改线后 T12 推算的位置（P03 ≤0.30 m，S02 ≤0.50 m，X05 ≤0.30 m）并与线路平行 ±2°。 | 与 answer-key units.<ID>.geom 比较；若与 stale_before_co 位置吻合则判否。 | 2.692 | 0.12 | 0.60 |
| G10 | timetable | 修订时刻表落实：R2 在 1–648、1236–1440 帧停于 P02；R3 在 1–96、888–1440 帧停于 P03，在 432–516 帧停于 P01——列车中点与站台中点在其线路中心线上的投影点（answer-key geom.axis_point）平面距离 ≤2.0 m，区间内各车位移 ≤0.05 m；且 R3 第 264 帧、R2 第 942 帧列车中点距所有站台的中点及其投影点均 >30 m。 | checks.py：同 M10 的中点与静止判定；参考点 = units.<站台>.geom.axis_point；按变更后键值 answer-key.timetable。 | 2.692 | 0.15 | 0.60 |
| G11 | integration | 线路集成：topology.csv 全部 16 个接头处，相邻两条 AXIS 端点平面距离 ≤0.05 m、切线方位差 ≤1°、轨面高程差 ≤0.03 m（主环含 T09→D01 闭合接头）。 | checks.py：answer-key.interfaces 的 16 个接头；端点切线 = 末段弦向 + 由末三点估计的曲率修正（对任意采样密度的圆弧精确）；道岔岔尖对岔尖接头 J05 同样要求外向切线相反（差 180°±1°）。 | 2.692 | 0.15 | 0.55 |
| G12 | integration | 结构接口：三座站台靠线路一侧边缘距中心线 1.75±0.05 m；B01、B02 桥面顶低于轨面 0.35±0.05 m；G01、G02 端墙法向与线路切线夹角 ≤2°、洞口中心距线路中线 ≤0.20 m；全部信号机立柱距中心线 2.50±0.15 m，全部接触网支柱距中心线 3.00±0.15 m。 | checks.py：站台边缘 = DECK 有向包围盒中心到所属 AXIS 的平面距离 − W/2；桥面：桥面中心处 AXIS z − DECK 顶 z；洞门：PORTAL 竖直面主方位（面积加权）与 T11 切线夹角、M05 扫描得到的洞口中心到 T11 中线距离；立柱：MAST 最低 0.3 m 顶点质心到所属 AXIS 的距离（信号机按 placement 区段，接触网按本区段）。 | 2.692 | 0.12 | 0.55 |
| G13 | visual | 视觉检查：渲染图（overview/hub/terminus）画面为完整连贯的铁路景观——有地形与水体、钢轨与道床可辨、列车在轨、无明显漂浮/穿插/缺面、非纯灰白模；任一不满足即否。 | LLM 评委根据 output/renders/*.png（至多 8 张）判定；不以 manifest 或求解者自述为依据。 | 2.692 | 0.45 | 0.70 |

## 预期分计算（设计估计，未实测）

| 层 | 条数 | 权重 | single 期望得分 | workflow 期望得分 |
|---|---|---|---|---|
| base | 8 | 25 | 20.16 | 23.59 |
| mid | 11 | 40 | 18.91 | 32.58 |
| gate | 13 | 35 | 6.89 | 21.4 |
| 合计 | 32 | 100 | **46.0** | **77.6** |

期望分 = Σ weight × expected_pass。single 失分主要来源：32 单元串行读图施工超出 3600 s，后段分区（E/F/R）常未建或粗建；同类单元模板化导致支柱数、灯色、拱石数、开间等离散特征错；漏看变更单的牵连（B02 随河交点移动、P03/S02/X05 随车挡移动）与修订时刻；不做拼装后接头与偏移验收。
