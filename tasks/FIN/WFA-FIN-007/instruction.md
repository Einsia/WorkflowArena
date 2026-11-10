# Execution environment

The workspace is `/workspace`. Read `contract.json`, `submission.template.json` and `prompt.md`. Submit `/workspace/output/submission.json`; save the requested memo at `/workspace/output/memo.md`. Only the JSON answers are scored. The machine contract supersedes the legacy free-form delivery and narrative grading clauses. The agent timeout is 14400 seconds. Use the frozen local inputs and tools provided by the evaluation environment; do not access the network or call external model services.

# 提交格式：finance-machine-v3.1

必须先阅读contract.json和submission.template.json。原研究题面中的金融分析任务仍需完成，但交付格式以公开contract.json为准，替代原题允许等价自由字段的约定。output/submission.json需包含contract_version、task_id、profile_id和answers；按每个question id填写数值、布尔、枚举、符号式、集合、证书树及来源完整行。所有比率使用小数，注意公开合同的符号名、参数域、精度预算和证书结构。output/memo.md按原题要求撰写。只使用本工作区inputs/公开材料；不读取其他题、金标、评分实现、历史答案、其他session或聊天。可自主使用评测环境提供的工具；不得联网或调用外部模型服务。单题运行超时为 14400 秒（4 小时）。

# 油气：弃置义务、套保与投资现金

比较EOG、DVN、FANG、MTDR、PR、RRC、CRK、KOS、TALO、GPOR当前半年的经营现金与全口径投资压力。需将油气开发、并购、弃置义务和套保现金衔接到同一资金桥，不把会计计量变化当付款。

## 材料与交付边界

只使用本题`inputs/`中的10份冻结财报，覆盖下列10家公司：EOG、DVN、FANG、MTDR、PR、RRC、CRK、KOS、TALO、GPOR。`inputs/companies.json`列明完整覆盖范围；不得只选择披露齐全或指标较高的公司作答。不要求联网核实外部真实性。分析当前报告覆盖的2026年6月末附近半年及其2025年同期，季度利润可由半年减当季得到；财季实际日期、主体和币种必须保留。资料没有逐季现金流时不得补造。源表间不一致须指出版本、范围或尚未解释的残差。

输出`output/submission.json`及最多1200字中文`output/memo.md`；可另存`work/`。所有实质结论及计算必须已经写入可读文件，评分不执行提交程序。每个重要原数/判断给证据id，定位文件、表/段、行列、期间、单位及短逐字原文，允许规范空白。提交须使用 contract.json 与 submission.template.json 规定的字段和 question id。

金额统一USD百万，费用/流量符号按题目及来源明确。表内千美元要换算；不得把不同期间、集团/分部、持续/终止或普通股归属混用。允许查资料、编程和标准依赖。不读取其他题、金标、历史答卷或聊天。

## 比较与验收规则

所有公司使用同一政策参数。参数是委员会指定的分析口径，不是GAAP、公司正式非GAAP、真实价值或买卖建议。财报事实、分析政策、假设、推断和无法识别必须分别标注。

交付一张覆盖矩阵：逐公司列明所需指标及事件的已识别/部分识别/未发现/不适用状态和检索依据。行业内经营模式、合并范围或保险/资产组合差异须进入可比性解释，不能为得到完整排名而把异质公司强行改成同一口径。对公司缺失关键输入的情况仍须保留该公司，给其可得部分与未定集合。

除全样本前二外，再给每家公司移除后的稳健关系及前二集合变化。这个leave-one-out检验只解释结论对覆盖范围的依赖，不将公司数、排名翻转数量或重复计算当作难度证明。不同参数取值下都不改变结论的公司也应保留并解释原因。

金额容差为max(0.002百万,参与原数各半个披露单位之和)，同源表达式允许代数抵消；百分比误差据此传播，至少0.02个百分点。排名差被精度覆盖时给不确定边界。不要按任意小数位强判。

除明确“越低越好”的指标外，指标越高越靠前；名次为1+严格优于该公司的公司数，前二包含第二名边界所有并列。稳健优势要求全政策域均不差且至少一处严格更好。始终前二与可能前二分别是对全部/存在一个共同政策点成立。未知输入必须传播至端点、交点和集合，并区分确定与未定；无来源支持的余额上界、零值或极端现金情景都不可强加。

一维指标检查所有内部翻转点和相邻区间；二维指标检查边界及内部区域，四个角不足以证明始终前二。不同评价轴分别给证书，不凭空设综合权重。有据的部分排序、参数不等式或not_identifiable是有效答案；必须指出真正缺少的分解和追加取得哪项披露会改变结论。笼统“资料不足”不能代替检索。

请对下面的审议命题逐条判定supported/refuted/partly_supported/not_identifiable，以原文和计算解释。命题是待审查观点，不是正确答案提示。任何重大额外解释也属于内容评价。

评分以重大判断为单位：期间/范围10、资金/行业分类30、来源支持的桥25、政策汇合20、反事实10、证据5，共100。同一根因的季度/指标/排名传播合并扣分，不按格子放大或稀释；合理等价口径、正确未知及源材料缺陷可以得分。时间本身不计分，完成即可提交。

## 需要完成的研究工作

1. 逐公司重建ARO期初→新增/并购→修订/汇率→折现增值→结算/处置→期末及current/noncurrent。逐项判断settled是否与divested合并、是否足以识别现金；不能把该行一律当已付现金。

2. 从现金流表及衍生品附注同时区分P&L中的重估、非现金回转、已实现损益与结算现金；明确OCF中已包含哪笔结算，不能扣掉会计损益后再次扣现金。

3. 重建开发/钻完井/其他PPE、现金财产收购、企业收购、收购带入现金/债务、租赁本金及合伙方融资。考虑investing working-capital转列；同一笔现金一次且仅一次。

4. 定义F_i,p=OCF_i−K_i−L_i−pA_i，p∈{0,1}；K为毛现金自建开发/PPE，L为尚未含K的融资租赁本金，A为单列净现金收购支出（负数保留，股权对价不计现金）。令H为已含OCF的有符号衍生品结算净收款，Q_i,p(λ)=[F_i,p−λH_i]/V_i，λ∈[0,1]共同，V为半年集团收入。

5. 给两种投资政策的端点、全部交点、稳健关系及前二证书。对于经营中已支付的弃置现金，仅做单独归因或显式撤销情景，基础F不得再次扣除；无法识别的支付保留未知。

6. 反事实至少覆盖ARO增值当现金、结算及处置混同、套保损益与结算重复调整、股票并购对价当现金，以及实际范围变化对可比性的影响。

## 委员会待审议命题

- ARO余额增长额就是本期弃置现金支出。
- 衍生品会计收益应直接从OCF再扣一次。
- 股票并购的总对价都应该计入当前现金capex。


本版澄清：contract.json 的 representation_rules 和 certificate_schema 明确可接受的等价格式及完整证书结构。未知 answer ID 仍整份拒收。不得以仅前二名替代完整排名，不得省略 leave_one_out.robust_pairs。原权重与 root 全部检查通过才得分规则不变。
