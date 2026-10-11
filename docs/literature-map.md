# AI 为什么老在"问别人"：确认行为、社交成本与研究地图

> 整理日期：2026-10-10。
> 引用规则：文献均经实际抓取核实过标题、作者、发表处与链接；**逐字引文标注了核实者与核实方式**；存在版本冲突或未能核实的地方明确标出。
> **本版含对上一版的更正，见第 10 节"更正记录"。**

---

## 0. 一句话结论

**"AI 不懂社交成本"只对了一半。** 准确的说法是三层叠加：

1. **社交成本没有进入训练目标**（reward 里"打扰你"这一项根本不存在）；
2. **厂商策略文档其实把成本写清楚了**（"别问废话""权衡问的不便"），但模型**执行不了那个条件判断**——在"该不该问"这个二值决策上，基线模型准确率只有 **36.5%（3B）/ 36.7%（7B）**（[Structured Uncertainty guided Clarification, arXiv:2511.08798](https://arxiv.org/abs/2511.08798)）；
3. **工程上用硬规则兜底**（"不确定就问""危险操作前必须确认"），于是模型表现得更保守。

所以它表现出的不是人情上的迟钝，而是**阈值没有被校准**。另一篇 2026 年的研究把这类行为定性为"模型特有属性"：模型"行动 vs. 升级给人"的隐含阈值**因模型而异、无法由架构或规模预测，且模型的自我估计存在系统性失准**（[Act or Escalate?, arXiv:2604.08588](https://arxiv.org/abs/2604.08588)）。如果是"不懂社交"，它应该一致地不懂；实际是每个模型一把不同的、随机的尺子。

---

## 1. 先把"AI 问别人"拆成三类，因为成本结构完全不同

| 类型 | 具体表现 | 真正的成本 |
|---|---|---|
| A. 问使用者 | 反复让你确认、让你补信息、把选择权退回给你 | 你的注意力、上下文重建、决策疲劳 |
| B. 问同伴（多智能体/团队） | agent 之间反复对需求、反复请求确认、任务来回甩 | token/延迟/金钱，以及**你仍要读这些来回** |
| C. 问审批人（human-in-the-loop） | 危险操作前停下等你点"同意" | 审批带宽是**有限且会疲劳**的资源 |

把三类混在一起谈，就会出现"它到底懂不懂社交成本"的假问题——**A 的成本是社交性的，B 的成本是经济性的，C 的成本是安全工程性的。**

---

## 2. 七条机制（为什么会这样）

### 机制 1：文本世界里"提问"的边际成本是 0
训练语料里问一句"请问您是指 A 还是 B？"没有任何代价——没有等待、没有被打断的人。**模型学到的是"提问在语言上是合理且礼貌的动作"，而从未学过"提问要花掉对方 3 分钟"。**（推断）

### 机制 2：偏好数据会奖励"谨慎的样子"
Anthropic 的研究证明，人类偏好数据与偏好模型会系统性偏好**读起来更令人满意**的回答，部分场景下甚至牺牲真实性（"Towards Understanding Sycophancy in Language Models", [arXiv:2310.13548](https://arxiv.org/abs/2310.13548)）。安全训练则被实测出会引发**夸张的安全行为**（XSTest, [arXiv:2308.01263](https://arxiv.org/abs/2308.01263)）。"问一下更保险"正是这类被奖励的表面特征之一。（前半为文献结论，最后一句为推断）

### 机制 3：损失不对称，而其中一侧的损失是"看不见的"
猜错的代价（幻觉、越权、误删文件）在训练与评测里都被重罚；打扰你的代价**在 reward 里根本不存在**。这正是 ACL 2026 那篇论文的出发点：现有做法"依赖脆弱的置信度阈值，且不考虑不同决策的不同风险"（"Value of Information: A Framework for Human–Agent Communication", [ACL 2026](https://aclanthology.org/2026.acl-long.1987/)）。

### 机制 4：没有人在算"问"这个动作的期望效用
决策论意义上"该不该问"早就是可算的，而且**Horvitz 1999 的原始模型里"发起对话"就是与"行动/不行动"并列的第三个选项**：

- 四个结果效用 u(A,G)、u(A,¬G)、u(¬A,G)、u(¬A,¬G)；行动与不行动各有期望效用，解出概率阈值 **p\***，p(G|E) > p\* 才行动。
- **引入"对话"（Dialog）后出现两个阈值**：p\*_{A,D}（不行动 vs. 提问）与 p\*_{D,A}（提问 vs. 行动）。
- 原文明确给出了不对称的方向：`"the utility of engaging in a dialog with a user when the user does not have the goal in question is typically greater than the utility of performing an action when the goal is not desired"`，而 `"the utility of asking a user before performing a desired action is typically smaller than the utility of simply performing a desired action"`。
- **打断成本如何进入模型**：u(A,¬G)（不需要却被打扰）`"can be significantly influenced by the status of a user's attention … can diminish significantly with increases in the depth of a user's focus on another task. Such a reduction in the value of action leads to a higher probability threshold."`
（Horvitz, E. 1999, *Principles of Mixed-Initiative User Interfaces*, CHI'99, pp. 159–166, [DOI 10.1145/302979.303030](https://doi.org/10.1145/302979.303030)；引文与公式取自作者官方 PDF 全文 [chi99horvitz.pdf](http://erichorvitz.com/chi99horvitz.pdf)）

⚠️ **术语更正**：CHI'99 这篇里**没有**出现 "expected value of computation (EVC)" 或 "cost of interruption (COI)"（对作者官方 PDF 做字符串计数，两者均为 0 命中）。EVC 的正式定义在其更早的 IJCAI-89 论文 *Reflection and Action Under Scarce Resources*（[ij89.pdf](http://erichorvitz.com/ij89.pdf)）；"cost of interruption" 作为专名见 Horvitz, Apacible & Koch, *BusyBody*, CSCW 2004（[DOI 10.1145/1031607.1031690](https://doi.org/10.1145/1031607.1031690)）。**不要把 EVC/COI 记在 CHI'99 名下。**

同一谱系的"净价值"表述见 Horvitz, Kadie, Paek & Hovel 2003（CACM 46(3), 52–59, [PDF](http://erichorvitz.com/cacm-attention.pdf)）：`"the attention-sensitive costs of disruption are subtracted from estimates of the value of alerting, yielding a net value of alerting a user for each channel and alerting modality."`

而直到 2026 年，主流 agent 仍在用 prompt + 置信度阈值近似它。最新的做法直接改用 **EVPI（完美信息期望价值）+ 分面成本建模**，效果是把澄清提问**减少 1.5–2.7 倍**的同时覆盖率还提高 7–39%（[arXiv:2511.08798](https://arxiv.org/abs/2511.08798)）。

### 机制 5：多轮信用分配很难，"该问却没问"和"不该问却问了"都拿不到正确梯度
多轮 GRPO 类方法用轨迹级奖励，无法定位"哪一轮交互真正带来了信息"。InfoPO 的做法是构造"遮蔽反馈"的反事实，只奖励那些**真正改变了后续动作分布**的交互轮（[arXiv:2603.00656](https://arxiv.org/abs/2603.00656)）。这解释了为什么"何时问"长期学不好。

### 机制 6：厂商并非不懂成本——文档里写得很清楚，但模型执行不了那个条件

**这是本次核实里最有意思的发现：把"过度确认很烦"明确写进策略文档的，恰恰是厂商自己。**

- **Claude's Constitution** 在"会让资深 Anthropic 员工不满的行为"清单里点名：`"Checks in or asks clarifying questions more than necessary for simple agentic tasks."`，紧接着写 `"This behavior makes Claude more annoying and less useful, and reflects poorly on Anthropic."` 同一份文档也规定了反向边界：`"Claude should ask for clarification in cases of genuine ambiguity."`（[Claude's Constitution](https://www.anthropic.com/constitution)）
- **OpenAI Model Spec** 把这件事写成了显式的成本权衡：`"It must therefore balance the risk of acting with incomplete information against the cost of asking for clarification."`、`"the assistant should weigh the cost of incorrect assumptions against the inconvenience of asking the user"`、`"Trivial questions may waste the user's time and cognitive resources"`，并要求 `"prevent unnecessary user interactions"`（[Model Spec](https://model-spec.openai.com/2026-08-18.html)、[源文](https://github.com/openai/model_spec/blob/main/model_spec.md)）。
- **生产环境的数字（我独立抓取全文核实）**：Anthropic 工程博客原文——`"Claude Code users approve 93% of permission prompts."`、`"Over time that leads to approval fatigue, where people stop paying close attention to what they're approving."`（[How we built Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode)，2026-03-25）。同文记录了他们内部事故日志里的真实案例：用户说"cancel my job"，agent **没有问**，而是按名字相似度挑了一个最接近的作业去删——这正是机制 7 的"该问不问"。该文还给出了生产环境里的**打扰配额**：每会话 3 次连续拒绝或累计 20 次即停止并升级到人。

> **结论修正**：不是"厂商把成本当 0"，而是**文档层面写对了成本，执行层面算不出那个条件**。条件句（"只在真正歧义时问"）要求模型判断"歧义是否真实"，而这正是它做不好的判断。

### 机制 7：正经文献记录更多的其实是"该问不问"

- 语言模型**很少**请用户澄清歧义，而是直接给错答案（CLAM, [arXiv:2212.07769](https://arxiv.org/abs/2212.07769)）。
- 由于下一词预测目标，模型会**凭空补出缺失参数**，这是提出 Ask-when-Needed 与 NoisyToolBench 的动机（[EMNLP 2025, arXiv:2409.00557](https://arxiv.org/abs/2409.00557)）。
- 多智能体失败分类 MAST 把 **FM-2.2 "Fail to Ask for Clarification"** 列为正式失败模式，定义原文：`"Inability to request additional information when faced with unclear or incomplete data, potentially resulting in incorrect actions."`，正文写作 `"proceeding with wrong assumptions instead of seeking clarification (FM-2.2, 6.80%)"`。
- **分类体系本身是不对称的**：MAST 的 14 个失败模式里**只有"该问不问"，没有任何一个"过度澄清"模式**。也就说，现有的失败编目与评测基础设施只惩罚一侧。

> **合起来看**：AI 不是单向"爱问"，而是**两个方向都会错**——该问不问时你在为幻觉买单，不该问乱问时你在为注意力买单。这正是"校准问题"而非"情商问题"的定义。

---

## 3. 一个更锋利的对照：人类不是算得准，而是反向偏

人类同样算不准社交成本，但偏的方向相反：**人是问得太少。**

- 求助被经典地建模为**对自尊的威胁**——求助意味着承认自己无能（Tessler & Schwartz 1972, *Help seeking, self-esteem, and achievement motivation*, JPSP 21(3), 318–326, [DOI 10.1037/h0032321](https://doi.org/10.1037/h0032321)）。
- 在组织情境中，求助与权力动机相互作用：**高权力动机者对求助的形象代价更敏感，更不愿开口**（Lee, F. 1997, *When the Going Gets Tough, Do the Tough Ask for Help?*, **OBHDP 72(3), 336–363**, [DOI 10.1006/obhd.1997.2746](https://doi.org/10.1006/obhd.1997.2746)）。
- 组织内信息搜寻不是免费的：是否向某人求助取决于四个关系维度——**知道对方懂什么（awareness）、能否及时接触（access）、关系是否安全到可以暴露无知（safety）、对方是否愿意共同解题（engagement）**（Borgatti & Cross 2003, *A Relational View of Information Seeking and Learning in Social Networks*, Management Science 49(4), 432–445, [DOI 10.1287/mnsc.49.4.432.14428](https://doi.org/10.1287/mnsc.49.4.432.14428)；作者公开工作论文版 [The Ties that Share](http://www.analytictech.com/borgatti/papers/tiesthatshare.pdf)）。⚠️ 该工作论文版中 safety 维度在定量模型里**未独立显著**（被解释为该公司存在"提问可接受"的强文化规范、safety 方差极小）；**正式写作若要给系数或显著性，须先取得出版版原文，只引用"四维度框架"是安全的。**

**AI 没有自我形象成本、没有同伴压力、不会因为问了显得笨。** 所以它天然偏离人类基线，偏向"问"。这也说明：把人类的社交直觉当作 AI 的目标行为，本身就不成立——需要的是**显式的成本项**，不是更像人的性格。

---

## 4. 打断别人的成本有多贵（AI 侧的"社交成本"应该按什么计价）

- **被打断时人会用"加快速度"补偿，代价是更高的压力与挫败感，而不是更差的任务质量**（Mark, Gudith & Klocke 2008, *The Cost of Interrupted Work: More Speed and Stress*, CHI'08, pp. 107–110, [DOI 10.1145/1357054.1357072](https://dl.acm.org/doi/10.1145/1357054.1357072)）。
- **实测的恢复代价**：现场研究中，用户响应 alert 后平均要再花近 10 分钟才回到被打断任务，另有 10–15 分钟才恢复聚焦；**27% 的任务挂起后超过 2 小时才被恢复**；立即响应邮件 alert 的恢复阶段平均 16 分 33 秒（Iqbal & Horvitz 2007, *Disruption and Recovery of Computing Tasks*, CHI'07, pp. 677–686, [DOI 10.1145/1240624.1240730](https://doi.org/10.1145/1240624.1240730)；[作者全文 PDF](http://erichorvitz.com/CHI_2007_Iqbal_Horvitz.pdf)）。
- **对打断代价做显式权衡与延迟策略的实验**：Horvitz, Apacible & Subramani 2005, *Balancing Awareness and Interruption: Investigation of Notification Deferral Policies*, UM 2005, [DOI 10.1007/11527886_59](https://doi.org/10.1007/11527886_59)，[PDF](http://erichorvitz.com/bdef_studies.pdf)。
- **智能通知管理确实能降低打断代价、提升任务表现**：Iqbal & Bailey 2008, CHI'08, pp. 93–102, [DOI 10.1145/1357054.1357070](https://doi.org/10.1145/1357054.1357070)。
- **恢复延迟的认知机制**：Altmann & Trafton 2002, *Memory for goals: an activation-based model*, Cognitive Science 26(1), 39–83, [DOI 10.1207/s15516709cog2601_2](https://doi.org/10.1207/s15516709cog2601_2)。
- **把审批人当作会疲劳的内生资源建模后，会出现倒 U 型关系：升级率越高，实际安全性反而可能越低**，安全最优策略是**低于满额升级**（"Oversight Has a Capacity", [arXiv:2606.08919](https://arxiv.org/abs/2606.08919)）。该文指出人类评审对"什么算危险"只有中等一致性（Fleiss' κ = 0.52）。
- **多专家延迟决策（learning to defer）研究已开始显式建模专家的工作量约束**（[arXiv:2403.06906](https://arxiv.org/abs/2403.06906)；经典工作见 [Predict Responsibly](https://papers.NeurIPS.cc/paper_files/paper/2018/hash/09d37c08f7b129e96277388757530c72-Abstract.html), NeurIPS 2018）。

⚠️ **不要使用"被打断后需 23 分钟 15 秒才能回到任务"**：该数字不在 Mark et al. 2008 全文中，原始出处（Mark, Gonzalez & Harris 2005, CHI'05）为付费墙未能核对，且存在公开质疑。**改用上面 Iqbal & Horvitz 2007 的实测数字。**

---

## 5. 提问本身的用户成本：有直接测量，而且比直觉更贵

- **用户实际愿意答多少问？** 实测：用户平均**实际回答了 11.4 个问题（中位数 7）**，而 **50% 用户自述只愿答 6–10 个**；平均每题耗时 **7.1 秒**（中位数 4.98 秒）；在系统被噪声答案带偏时，停止原因中"疲劳"占 **34%**、"问题不相关"占 22%（对照条件下为 14%、7%）。结论句：`"current research should drop the assumption that users are happy to answer as many questions as the system generates"`（Zou, Kanoulas & Liu 2020, *An Empirical Study on Clarifying Question-Based Systems*, CIKM'20, pp. 2361–2364, [DOI 10.1145/3340531.3412094](https://doi.org/10.1145/3340531.3412094)；[开放全文](https://ar5iv.labs.arxiv.org/html/2008.00279)）。
- **低质量提问是负收益**：`"posing CQs to users causes higher interaction costs (in terms of time spent), yet, it does not always ensure better returns. Therefore, CQs introduce a high risk of user dissatisfaction and frustration"`；命中数的增长率在后期**大幅下降（diminishing return of gain）**；而且**先出现低质量问题会拉低后续高质量问题的点击率**（CTR 从 74.4% 降到 50%）（Zou, Aliannejadi, Kanoulas, Pera & Liu 2023, *Users Meet Clarifying Questions*, TOIS, [DOI 10.1145/3524110](https://doi.org/10.1145/3524110)；[开放全文](https://pure.uva.nl/ws/files/169537246/Users_Meet_Clarifying_Questions.pdf)）。
- **收益侧基线**：只问一个好的澄清问题，P@1 可提升 **170% 以上**（Aliannejadi et al. 2019, SIGIR'19, pp. 475–484, [DOI 10.1145/3331184.3331265](https://doi.org/10.1145/3331184.3331265)；Qulac：198 topics / 762 facets / 10,277 QA 对）。
- **提问质量决定它是帮助还是干扰**：具体的问题优于泛泛的问题；问题的主观性与情绪色彩有影响；越短、越模糊的查询从澄清中获益越大；而表述糟糕的问题会导致用户挫败与困惑（Rahmani et al., EACL 2024, [arXiv:2402.01934](https://arxiv.org/abs/2402.01934)）。
- 检索场景中直接研究了"澄清问题让用户受益还是被打扰"（Zamani et al., *Asking Clarifying Questions: To benefit or to disturb users in Web search?*, [IP&M 2023](https://www.sciencedirect.com/science/article/pii/S0306457322002771)）。
- 澄清时机也有专门研究：2026 年 C&C 的一项研究比较了"先问"与"后问"，发现**在总体用户体验上没有显著差异**（[C&C 2026](https://dl.acm.org/doi/10.1145/3803784.3816856)）——即"何时问"的影响没有直觉上那么大，"问得值不值"才是关键。
- 机器人求助研究显示求助请求会影响**协作与信任**（[ACM 2026](https://dl.acm.org/doi/10.1145/3776734.3794472)）。

---

## 6. 警报/审批疲劳：学术证据在"alert fatigue"，不在"approval fatigue"

- **警报疲劳的纵向实证**：178 名医生随机接受 EHR 临床试验提醒，响应率随时间显著下降，**每个时间段下降 2.7%**（Embi & Leonard 2012, JAMIA 19(e1), e145–e148, [DOI 10.1136/amiajnl-2011-000743](https://doi.org/10.1136/amiajnl-2011-000743)）。
- **工作量与重复警报都会压低接受率**：**每多一条提醒，接受可能性降 30%**；重复提醒占比每升 5 个百分点，降 10%（112 名门诊医生，3.5 年数据）（Ancker et al. 2017, BMC Med Inform Decis Mak 17(1), 36, [DOI 10.1186/s12911-017-0430-8](https://doi.org/10.1186/s12911-017-0430-8)）。
- **自动化偏差的权威综述**：过度依赖（misuse）、因频繁误报而弃用（disuse）、设计者/管理者造成的滥用（abuse）（Parasuraman & Riley 1997, Human Factors 39(2), 230–253, [DOI 10.1518/001872097778543886](https://doi.org/10.1518/001872097778543886)）。原始实验证据见 Mosier et al. 1998, [DOI 10.1207/s15327108ijap0801_3](https://doi.org/10.1207/s15327108ijap0801_3)。
- 通知的注意力代价：真实场景中约每 4–5 分钟收到一条通知，相当比例到达于不方便的时刻（Pielot, Church & de Oliveira 2014, MobileHCI'14, [DOI 10.1145/2628363.2628364](https://doi.org/10.1145/2628363.2628364)）。

⚠️ **"approval fatigue" 未能核实到任何可靠的学术来源，不要引用为学术概念**——它是 Anthropic 工程博客里的产品用语（有 93% 这个真实数据支撑）。学术侧对应的是 alert fatigue 与自动化偏差。

---

## 7. 相关研究地图（按问题分层）

**A. 何时该问：决策论与延迟决策**
- Horvitz 1999, *Principles of Mixed-Initiative User Interfaces*（行动/不行动/对话三选项与两个阈值，[DOI](https://doi.org/10.1145/302979.303030)）
- Horvitz & Paek 2001, *Harnessing Models of Users' Goals to Mediate Clarification Dialog in Spoken Language Systems*, UM 2001（[全文](http://erichorvitz.com/umdl.htm)）
- Dong et al., ACL 2026, *Value of Information: A Framework for Human–Agent Communication*（[链接](https://aclanthology.org/2026.acl-long.1987/)）——显式把"施加给用户的认知成本"写进效用
- Madras et al., NeurIPS 2018, *Predict Responsibly: Learning to Defer*（[链接](https://papers.NeurIPS.cc/paper_files/paper/2018/hash/09d37c08f7b129e96277388757530c72-Abstract.html)）
- *Cost-Sensitive Learning to Defer to Multiple Experts with Workload Constraints*（[arXiv:2403.06906](https://arxiv.org/abs/2403.06906)）

**B. 澄清问题的生成与"选择性提问"**
- Aliannejadi et al., SIGIR 2019, Qulac（[DOI](https://doi.org/10.1145/3331184.3331265)）
- Kuhn, Gal & Farquhar, *CLAM: Selective Clarification for Ambiguous Questions*（[arXiv:2212.07769](https://arxiv.org/abs/2212.07769)）
- Wang et al., EMNLP 2025, *Learning to Ask: When LLM Agents Meet Unclear Instruction*（Ask-when-Needed / NoisyToolBench / ToolEvaluator，用**准确率 + 交互效率**双指标，[arXiv:2409.00557](https://arxiv.org/abs/2409.00557)）
- Suri et al., *Structured Uncertainty guided Clarification*（EVPI + 成本建模 + ClarifyBench，[arXiv:2511.08798](https://arxiv.org/abs/2511.08798)）

**C. 训练与优化：把"该不该问"变成可学信号**
- *InfoPO: Information-Driven Policy Optimization for User-Centric Agents*（[arXiv:2603.00656](https://arxiv.org/abs/2603.00656)）
- *Act or Escalate? Evaluating Escalation Behavior in Automation with Language Models*（[arXiv:2604.08588](https://arxiv.org/abs/2604.08588)）

**D. 该问不问：文献里更常见的那一侧**
- CLAM（同上）；Ask-when-Needed（同上）
- MAST（NeurIPS 2025, [arXiv:2503.13657](https://arxiv.org/abs/2503.13657)）：3 大类 14 个模式，其中 **FM-2.2 "Fail to Ask for Clarification"** 属于 FC2 Inter-Agent Misalignment。占比：**v3（1642 traces）6.80%**，v1 为 **11.65%**。
  ⚠️ **版本敏感**：v3 Figure 1：FC1 44.2% / FC2 32.3% / FC3 23.5%；v1：41.77% / 36.94% / 21.30%；且 v3 内部 FM-1.1 疑似有正文 11.8% 与图 15.7% 的不一致。**引用必须指定版本号。**
- **该分类里没有任何"过度澄清"模式**——失败编目本身只惩罚一侧。

**E. 过度保守与弃答**
- Röttger et al., NAACL 2024, XSTest（[arXiv:2308.01263](https://arxiv.org/abs/2308.01263)）
- Wen et al., TACL 2024, *Know Your Limits: A Survey of Abstention in LLMs*（[arXiv:2407.18418](https://arxiv.org/abs/2407.18418)）
- Osika et al., ICLR 2024, MINT（多轮交互预算下的评测，[arXiv:2309.10691](https://arxiv.org/abs/2309.10691)）

**F. 交互成本、打断与人类监督容量** —— 见第 4、5、6 节，此处不重复。

**G. 多智能体之间的"问"也是成本**
- *Cost-Effective Communication: An Auction-based Method for Language Agent Interaction*（用拍卖机制给 agent 间消息定价，[AAAI 2026](https://ojs.aaai.org/index.php/AAAI/article/view/40182) / [arXiv:2511.13193](https://arxiv.org/abs/2511.13193)）

**H. 人类为什么问得少（对照组）** —— 见第 3 节。

**I. 心智理论（ToM）——为什么这不是主因**
- Kosinski 2023 报告 LLM 在经典 ToM 任务上达到人类水平（[arXiv:2302.02083](https://arxiv.org/abs/2302.02083)），Ullman 2023 指出**对任务做微小改动即失效**（[arXiv:2302.08399](https://arxiv.org/abs/2302.08399)）。
- **判断**：ToM 关心"对方知道什么"，而"该不该问"关心"对方的注意力值多少钱"。后者是效用函数缺失，不是心智推断失败。

**J. 厂商策略与产品文档（一手材料）**
- [Claude's Constitution](https://www.anthropic.com/constitution)：点名"多余确认"是让资深员工不满的行为
- [OpenAI Model Spec](https://model-spec.openai.com/2026-08-18.html)：要求"权衡错误假设的成本与询问用户的不便"
- [How we built Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode)：93% 批准率 → 审批疲劳；分类器替代人工批准；**每会话 3 次连续拒绝或累计 20 次即升级到人**（生产环境里的"打扰配额"）
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)：`"Agents can then pause for human feedback at checkpoints or when encountering blockers."`——只在检查点或遇阻时回到人类（该文没有独立的"不要过度询问"原则句，勿外推）

---

## 8. 可以用来判断和改进的判据

**判断"是规则问题还是校准问题"：**
1. 换到成本可忽略的场景，它还问吗？还问 → 是硬规则/系统提示在驱动。
2. 你把"打断成本"明确写进指令后，它是否变得会算了？不会 → 是校准问题（注意：厂商文档已经写了，仍然不生效，说明这一条最可能是主因）。
3. 同一个问题问 3 次，答案分布是否稳定？不稳定 → 阈值本质是随机的。

**工程侧可行的改法（已有生产先例）：**
- 给 agent 一个**显式的决策规则**而不是"不确定就问"：按 Horvitz 的三选项框架，把"发起对话"当成独立动作，用两个阈值卡住它。
- 评测时用**双指标**（任务正确率 + 交互轮数/用户操作数），否则"多问"永远免费；失败分类法也要补上"过度澄清"这一类。参考已有的用户侧实测：**平均只愿答 6–10 个问题**，这就是预算量级。
- 给 harness 设**打扰配额**：Anthropic 的做法是"3 次连续拒绝或累计 20 次即停止并升级到人"。
- 让升级/交接**带成本标签**：同事的确认、用户的确认、审批人的确认，计价不同。
- 注意**提问顺序本身有溢出效应**：先问低质量问题会拉低后续高质量问题的点击率（74.4% → 50%），所以宁可少问、问准。

---

## 9. 参考链接汇总

- VoI 框架（ACL 2026）：https://aclanthology.org/2026.acl-long.1987/
- Act or Escalate（2026）：https://arxiv.org/abs/2604.08588
- Oversight Has a Capacity（2026）：https://arxiv.org/abs/2606.08919
- Structured Uncertainty / ClarifyBench（2026）：https://arxiv.org/abs/2511.08798
- InfoPO（2026）：https://arxiv.org/abs/2603.00656
- MAST（NeurIPS 2025）：https://arxiv.org/abs/2503.13657
- Ask-when-Needed / NoisyToolBench（EMNLP 2025）：https://arxiv.org/abs/2409.00557
- CLAM：https://arxiv.org/abs/2212.07769
- Qulac（SIGIR 2019）：https://doi.org/10.1145/3331184.3331265
- 用户愿意答多少问（CIKM 2020）：https://doi.org/10.1145/3340531.3412094
- 澄清问题的成本与递减收益（TOIS 2023）：https://doi.org/10.1145/3524110
- Clarification usefulness & user satisfaction（EACL 2024）：https://arxiv.org/abs/2402.01934
- Ask Before or After?（C&C 2026）：https://dl.acm.org/doi/10.1145/3803784.3816856
- Zamani et al., IP&M 2023：https://www.sciencedirect.com/science/article/pii/S0306457322002771
- Sycophancy（Anthropic）：https://arxiv.org/abs/2310.13548
- XSTest：https://arxiv.org/abs/2308.01263
- Abstention 综述（TACL 2024）：https://arxiv.org/abs/2407.18418
- MINT（ICLR 2024）：https://arxiv.org/abs/2309.10691
- 打断成本（CHI'08）：https://doi.org/10.1145/1357054.1357072
- 打断后的恢复实测（CHI'07）：https://doi.org/10.1145/1240624.1240730
- Horvitz 1999（CHI'99）：https://doi.org/10.1145/302979.303030
- BusyBody / cost of interruption（CSCW 2004）：https://doi.org/10.1145/1031607.1031690
- Learning to Defer（NeurIPS 2018）：https://papers.NeurIPS.cc/paper_files/paper/2018/hash/09d37c08f7b129e96277388757530c72-Abstract.html
- Deferral with workload constraints：https://arxiv.org/abs/2403.06906
- 警报疲劳（JAMIA 2012）：https://doi.org/10.1136/amiajnl-2011-000743
- 警报疲劳与工作量（BMC MIDM 2017）：https://doi.org/10.1186/s12911-017-0430-8
- 自动化偏差综述（Human Factors 1997）：https://doi.org/10.1518/001872097778543886
- Moral Crumple Zones：https://estsjournal.org/index.php/ests/article/view/260
- Agent 通信拍卖（AAAI 2026）：https://ojs.aaai.org/index.php/AAAI/article/view/40182
- 求助的自尊威胁（JPSP 1972）：https://doi.org/10.1037/h0032321
- 求助的形象成本（Lee 1997, OBHDP）：https://doi.org/10.1006/obhd.1997.2746
- 信息搜寻的关系成本（Borgatti & Cross 2003）：https://doi.org/10.1287/mnsc.49.4.432.14428
- ToM 争议：https://arxiv.org/abs/2302.02083 ・ https://arxiv.org/abs/2302.08399
- Claude's Constitution：https://www.anthropic.com/constitution
- OpenAI Model Spec：https://model-spec.openai.com/2026-08-18.html
- Claude Code auto mode（93% / 审批疲劳 / 打扰配额）：https://www.anthropic.com/engineering/claude-code-auto-mode
- Building effective agents：https://www.anthropic.com/engineering/building-effective-agents

---

## 10. 更正记录（相对上一版）

| # | 上一版的说法 | 更正后 | 依据 |
|---|---|---|---|
| 1 | "Horvitz 1999 把 expected value of computation / cost of interruption 写进了混合主动式交互" | **术语归因错误。** CHI'99 全文 0 次出现 EVC/COI/interrupt；该文用的是"行动 vs. 不行动 vs. 对话"的期望效用与两个阈值。EVC 属 IJCAI-89 *Reflection and Action Under Scarce Resources*；COI 属 BusyBody（CSCW 2004） | 对作者官方 PDF 做全文字符串计数 |
| 2 | 打断成本一节只引了 Mark et al. 2008 | 补充 Iqbal & Horvitz 2007 的实测恢复数据；并明确**不要用"23 分钟"那个数字** | 全文核对 + 原始出处付费墙未取到 |
| 3 | 未区分"alert fatigue"与"approval fatigue" | 学术证据在 alert fatigue（响应率每时段降 2.7%；每多一条提醒接受率降 30%）；**"approval fatigue" 无学术来源，是厂商产品用语，不可当学术概念引用** | Europe PMC 摘要核对 + 多轮检索无果 |
| 4 | 提问的 UX 成本只有"质量决定帮助还是干扰" | 补入直接测量的用户预算：**平均答 11.4 问、中位数 7，50% 自述只愿答 6–10 个，每题 7.1 秒，停止原因中疲劳占 34%**；以及递减收益与提问顺序的溢出效应（74.4%→50%） | CIKM 2020 / TOIS 2023 开放全文 |
| 5 | Lee 1997 只给了 PsycNET 记录 | 补全为 **OBHDP 72(3), 336–363, DOI 10.1006/obhd.1997.2746**（不是 JPSP） | Crossref 元数据 |
| 6 | Borgatti & Cross 2003 仅引用"四维度框架" | 保留该引用，并标注：**工作论文版中 safety 维度未独立显著**，正式写作给系数前须取得出版版 | 作者公开工作论文版 |

### 残留不确定性

| 内容 | 核实方式 | 状态 |
|---|---|---|
| 全部学术论文的标题/作者/发表处 | 逐条抓取 arXiv abs、ACL Anthology、Crossref API、NeurIPS 页面 | 已核实 |
| Claude Code auto mode 的 93% 与审批疲劳引文 | **我本人抓取全文** | 已核实（逐字一致） |
| Claude's Constitution 与 Model Spec 的逐字引文 | 子代理抓取 anthropic.com 页面与 jsdelivr 镜像（本环境 raw.githubusercontent 被 TLS 阻断） | 已核实但**未经我二次复核**，引用前建议回原文确认措辞 |
| MAST 的 FM-2.2 定义原文与占比 | 子代理下载 v3 PDF 全文提取 | 已提取，**版本敏感**，引用须标版本 |
| Horvitz 系列公式与措辞 | 子代理对作者官方 PDF 做字符串检索（含"0 命中"的反向验证） | 已核实；EVC 的 28 次命中在 IJCAI-89 |
| GitHub Copilot / OpenAI Codex 承认"过度询问损害体验" | 检索无官方表述 | **未能核实**，正文未引用 |
