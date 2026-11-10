# Execution environment

The workspace is `/workspace`. Read `contract.json`, `submission.template.json` and `prompt.md`. Submit `/workspace/output/submission.json`; save the requested memo at `/workspace/output/memo.md`. Only the JSON answers are scored. The machine contract supersedes the legacy free-form delivery and narrative grading clauses. The agent timeout is 14400 seconds. Use the frozen local inputs and tools provided by the evaluation environment; do not access the network or call external model services.

# 提交格式：finance-machine-v3.1

必须先阅读contract.json和submission.template.json。原研究题面中的金融分析任务仍需完成，但交付格式以公开contract.json为准，替代原题允许等价自由字段的约定。output/submission.json需包含contract_version、task_id、profile_id和answers；按每个question id填写数值、布尔、枚举、符号式、集合、证书树及来源完整行。所有比率使用小数，注意公开合同的符号名、参数域、精度预算和证书结构。output/memo.md按原题要求撰写。只使用本工作区inputs/公开材料；不读取其他题、金标、评分实现、历史答案、其他session或聊天。可自主使用评测环境提供的工具；不得联网或调用外部模型服务。单题运行超时为 14400 秒（4 小时）。

# 软件：预收款、资本化成本与现金利润

比较NET、HUBS、U、BL、AKAM、PEGA、QLYS、TENB、VRNS、WK、BSY、FIVN的收入质量和现金创造。要求同时审阅合同负债、合同取得成本、资本化开发与股份支付，并解释增长指标和现金指标可能为何给出不同结论。

## 材料与交付边界

只使用本题`inputs/`中的12份冻结财报，覆盖下列12家公司：NET、HUBS、U、BL、AKAM、PEGA、QLYS、TENB、VRNS、WK、BSY、FIVN。`inputs/companies.json`列明完整覆盖范围；不得只选择披露齐全或指标较高的公司作答。不要求联网核实外部真实性。分析当前报告覆盖的2026年6月末附近半年及其2025年同期，季度利润可由半年减当季得到；财季实际日期、主体和币种必须保留。资料没有逐季现金流时不得补造。源表间不一致须指出版本、范围或尚未解释的残差。

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

1. 建立当前半年及同期收入、集团净利润、OCF、SBC费用、现金PPE及现金资本化软件/云计算成本的表；企业收购和非现金资本化单列，避免把已在PPE现金或OCF的成本重复扣。

2. 对合同负债将期初/期末current与noncurrent、从期初余额确认的收入、其他已披露增减分开。不能将RPO当已签收款，也不能用期末减期初加期初确认收入直接命名现金billings。列出能识别的桥及未披露残差。

3. 建立递延佣金/合同取得成本及软件资本化→摊销/减值→余额的可用桥。区分现金开发成本与资本化SBC，费用SBC与权益表SBC，以及本期付款与累计资本化余额。

4. 定义C为毛现金PPE及尚未含在其中的现金软件/云成本，B为现金流表合同负债变动区段中可明确识别的有符号贡献。对共同λ,μ∈[0,1]计算Q_i(λ,μ)=[OCF_i−C_i−λSBC_i−μB_i]/V_i，V为半年收入。μ剔除的是列报贡献，不能改称准确移除了预收现金；B不单列时保留具体未知，不用资产负债余额差替代。

5. 给共同二维参数域内的全部次序边界和前二集合，提供内部区域证书；另按已披露RPO的可取消性、确认期限及定义给可比性限制。不得把RPO/收入作为现金覆盖率。

6. 检验重复扣佣金、把RPO当现金、用权益表SBC代费用、漏掉独立资本化开发现金四种错误。每项至少说明对来源桥和最终比较的方向及可复算金额/公式。

## 委员会待审议命题

- 递延收入本期增加额就是预收现金净增加额。
- RPO足以覆盖一年收入，所以现金已提前收到。
- 合同佣金既已资本化，就应在OCF之外再扣其余额增加。


本版澄清：contract.json 的 representation_rules 和 certificate_schema 明确可接受的等价格式及完整证书结构。未知 answer ID 仍整份拒收。不得以仅前二名替代完整排名，不得省略 leave_one_out.robust_pairs。原权重与 root 全部检查通过才得分规则不变。
