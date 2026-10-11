# ai-collision-check · 撞车检测

> 在研究一个方向**之前**，做一次可复现的撞车检查。
>
> **核心设计原则：不输出「撞车 / 没撞车」的二值结论。**

[English](#english) · [为什么需要这个](#为什么需要这个) · [安装](#安装) · [用法](#用法)

---

## 为什么需要这个

一个研究者想做某个方向，用 AI 查了一遍文献，看到几篇今年的论文标题很像，于是说了一句"算了"，换方向。

**这个过程里丢了至少四样东西：**

| 混在一起的四件事 | 发生了什么 |
|---|---|
| **领域膨胀** | arXiv 2026 年 9 月收到 **40,363** 篇投稿，两年前的同期是 20,569，十年前是 9,869。**池子翻倍，撞车概率就翻倍**，不需要任何新理论 |
| **检测灵敏度** | AI 让"找到撞车"从几小时变成几分钟。同样的撞车率，你今天能看见的比三年前多得多 |
| **真实收敛** | 可能真的在趋同（已有研究：[Doshi & Hauser 2024](https://www.science.org/doi/full/10.1126/sciadv.adn5290)，生成式 AI 提升个体创造力但降低集体多样性） |
| **误杀** | **被判"撞车"而放弃的想法，不留任何痕迹。** 没人知道有多少本来能做的研究死在这一步 |

这个工具针对的是**第四样**。

它来自一次真实的经历：作者做完方案后做撞车检查，发现两篇相隔一天发布的论文（10 月 1 日、10 月 2 日），判断"完全撞车"，说了句"算了"。后来逐字读完正文才发现——**不是同一个东西，差异有三处实质性区别。那次"算了"，是一次误杀。**

---

## 设计原则：为什么禁止二值结论

工具里有一条硬性规则：

> **任何"有人做过"的结论，都必须附带"他们做了什么"和"他们没做什么"。**

因为二值结论是误杀的唯一来源。而"他们没做什么"，正是你的差异化空间。

判定分三栏，而不是两栏：

| 判定 | 含义 |
|---|---|
| **已被占据** | 同一个问题、同一类方法，有人做过了 |
| **部分重叠** | 主题相关，但场景 / 数据 / 约束 / 代价 / 评测方式不同 |
| **空白** | 检索结果里没有实质相关的工作 |

另外还有一条给使用者的纪律（写在配套模板里）：

> **"真撞车"（读了对方方法部分确认一致）和"看起来像"（只看了标题摘要）必须分开记录。**
> 分清这两者的困难程度，本身就是研究结果。

---

## 安装

### 方式一：作为 skill 使用（推荐）

把 `skill/` 整个目录复制到你的 skills 目录：

```bash
# DSH / Claude skills 目录
cp -r skill/ ~/.dsh/skills/collision-check/
# 或
cp -r skill/ ~/.claude/skills/collision-check/
```

之后当你提到「要做某个方向」「这个想法有没有人做过」「查一下撞车」时，skill 会自动触发。

### 方式二：直接当命令行脚本

**零依赖**，只用 Python 标准库（Python 3.9+ 均可）：

```bash
python skill/scripts/collision_agent.py --idea "你的研究方向"
```

---

## 用法

```bash
# 1. 最简用法（需要 LLM 做判定）
export OPENAI_API_KEY=sk-xxxx
python collision_agent.py --idea "把一次提问的用户反馈遮蔽掉，比较 agent 动作分布是否改变"

# 2. 从文件读方向描述
python collision_agent.py --file direction.md

# 3. 只看近三年的文献
python collision_agent.py --idea "..." --since 2023

# 4. 只检索、不判定（不需要 API key）
python collision_agent.py --idea "..." --query "abandoned research ideas novelty check" --no-llm

# 5. 手写英文检索式（强烈建议在 --no-llm 模式下使用）
python collision_agent.py --idea "..." \
  --query "clarification question redundancy metric" \
  --query "over-clarification agent benchmark"
```

报告输出到 `reports/CC-YYYYMMDD-HHMM.md`，末尾附一行可直接粘贴进想法日志的表格行。

### 配置

兼容任何 OpenAI 协议的端点：

```bash
export OPENAI_API_KEY=...                                    # 必填，否则退化为只检索
export OPENAI_BASE_URL=https://api.deepseek.com/v1           # 可选
export COLLISION_MODEL=deepseek-chat                         # 可选
export OPENALEX_MAILTO=you@example.com                       # 可选，进 OpenAlex polite pool
```

常见端点：

| 服务 | `OPENAI_BASE_URL` | `COLLISION_MODEL` 示例 |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| 智谱 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-plus` |

---

## 它怎么工作：四步

```
① 拆主张      把研究方向拆成 3-5 条「可独立检索」的主张
              （整段方向描述直接拿去检索，效果很差）
                    ↓
② 多路检索    arXiv API / OpenAlex / Semantic Scholar
              任一源失败不影响其他源
                    ↓
③ 三栏判定    已被占据 / 部分重叠 / 空白
              每条都必须写清「他们做了什么」和「他们没做什么」
                    ↓
④ 差异化假设  强制产出「我的差异点落在哪一行」，必须对应到具体证据
```

---

## 目录结构

```
ai-collision-check/
├── README.md
├── LICENSE
├── skill/                          # 可直接安装的 skill
│   ├── SKILL.md                    # 触发条件 + 流程规范
│   ├── scripts/
│   │   └── collision_agent.py      # 零依赖实现
│   └── references/
│       └── criteria.md             # 三栏判定的详细判据
├── templates/
│   └── idea-log.md                 # 想法日志模板（误杀率的数据采集工具）
├── tests/
│   └── test_offline.py             # 离线端到端测试（不联网、不需要 key）
└── docs/                           # 背景文档（工作笔记性质）
    ├── literature-map.md           # 20+ 篇已验证文献的领域地图
    ├── research-routes.md          # 三条可执行研究路线 + 撞车分析
    ├── meta-research-idea-collision.md  # 「想法撞车」元研究方案
    ├── mechanisms-timestamp-privacy.md  # 时间戳 / 防御性发表 / 隐私匹配机制
    └── product-design.md           # 如果把这件事做成产品，设计要点
```

---

## 测试

```bash
python tests/test_offline.py
```

离线端到端测试：把 LLM 和检索都 mock 掉，跑通完整的四步流程，然后对生成的报告做 13 项断言——包括三栏判定是否齐全、`evidence_ids` 下标越界是否被安全忽略、标题里的方括号是否会破坏 markdown 链接、回访日期是否正确算成 +90 天。

**不联网、不需要 API key。** 改完代码先跑它。

---

## 已知限制

诚实列出，这些是实测出来的：

1. **arXiv / OpenAlex 对中文检索式几乎无效。** 两个源都以英文为主，必须提供英文检索式——要么让 LLM 生成（默认行为），要么用 `--query` 手写。
2. **Semantic Scholar 免费额度会返回 429。** 已做优雅降级，不影响其他源。
3. **不接 LLM 时检索质量很差。** 纯关键词搜索的噪声极大；**LLM 的"拆解主张 + 三栏判定"是必需步骤，不是可选优化**。
4. **判定依赖 LLM，因此不完全可复现。** 检索部分是确定性的（可记录、可复现），判定部分有随机性。建议对关键结论人工复核。
5. **它不能替代读论文。** 工具能告诉你去读哪几篇，不能替你判断"是不是同一个东西"——作者本人的那次误杀，恰恰发生在这里。

---

## 背景

这个工具是一份更长的工作的一部分：一个研究者试图研究"AI 为什么总是把确认推给别人"，结果在撞车检查里撞得粉碎，然后发现**"撞车"这件事本身没人测量过**。

`docs/` 里的文献地图涵盖 20+ 篇已逐条核实的论文，包括：

- 模型"该不该问"的判断准确率只有 **36.5%**
- Claude Code 用户**批准了 93% 的权限提示**，Anthropic 自己称之为"审批疲劳"
- 在一个信息完全完备的任务上，不同 agent 的"多余提问率"从 **5.00%** 到 **32.50%**（[CONTRA, arXiv:2610.01769](https://arxiv.org/abs/2610.01769)）
- 300 个未脚本化会话中，**52% 存在过度提问**（[arXiv:2605.07937](https://arxiv.org/abs/2605.07937)）

---

## 贡献

欢迎提交：

- **新的检索源**（PubMed、DBLP、中国知网等）
- **判定判据的改进**（`skill/references/criteria.md`）
- **你自己的误杀案例**——如果你有"判了撞车、放弃了、后来发现没人做"的经历，开个 issue 讲讲

---

## License

[MIT](LICENSE)

---

<a name="english"></a>
## English

**ai-collision-check** — a reproducibility-first novelty check to run *before* you commit to a research direction.

**Core design rule: never output a binary "scooped / not scooped" verdict.** Every "someone has done this" claim must be accompanied by *what they did* and *what they did not do* — because the latter is your differentiation space.

It runs a four-step pipeline: decompose the direction into searchable claims → multi-source retrieval (arXiv / OpenAlex / Semantic Scholar) → three-way classification (occupied / partially overlapping / open) → forced differentiation hypothesis.

Zero dependencies (Python stdlib only). Works with any OpenAI-compatible endpoint, or without an LLM at all in retrieval-only mode.

The tool targets one specific failure mode: **ideas killed by a false-positive collision check leave no trace.** Nobody can measure how many viable research directions die that way, because abandoned ideas are never recorded.
