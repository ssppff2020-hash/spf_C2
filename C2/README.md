# C2 · AI for Math 论文 —— 交付包

> 挑战：`ch-20260717031343-8ot0ji` ｜ 完成日期：2026-10-05
> 交付物：**一篇可编译、可投稿的 LaTeX 论文** ＋ **一条可复跑的核验流水线** ＋ **全过程的证据链**

---

## 一、这是什么

一篇围绕 **AI4Math 可靠性框架** 的学术论文，题目是

> **Reliability in AI for Mathematics: An Assurance-Chain Framework and a Corpus Audit**

以及支撑它的全部脚本、核验记录与日志。

论文主张：把「非形式命题 → 形式对象 → 判定」看成一条**四段保证链**，
学界现有的三条技术路线（搜索＋验证、形式化、可复现评估）各自只守住链条的一部分，
并且各自留下**性质不同**的残余风险。因此「哪条路线最好」是个**提法有问题**的问题；
有用的问题是「这次部署能容忍哪一种残余风险」。

然后论文**把这条框架用在自己的文献综述上**：先让模型凭记忆写出 31 条候选引用，
再逐条核验——**31 条里有 3 条是真错（9.7%）**，其中一条给了一个语法合法、
能正常解析、但指向完全不相干论文的 arXiv 编号。

**一句话**：论文的核心论点是「没有验证层的生成会以可测量的方式出错」，
而这篇论文自己的引文生成层就是这样一个例子，所以把它的错误率当成数据报出来。

---

## 二、交付物清单（对照任务卡）

任务卡要求：`paper.tex, references.bib, *AI日志*, *AAR*`

| 任务卡要求 | 本包位置 | 状态 |
|---|---|---|
| `paper.tex` | [`paper.tex`](paper.tex) —— 可独立编译（`pdflatex` 或 `xelatex`） | ✅ 15 页，0 未解析引用 |
| `references.bib` | [`references.bib`](references.bib) —— **30 条，全部经三源核验** | ✅ 生成物，含 SHA-256 |
| `*AI日志*` | [`AI日志/`](AI日志/) —— 5 篇，含真实 prompt、报错原文、返工记录 | ✅ |
| `*AAR*` | [`AAR/C2-七维复盘AAR.md`](AAR/C2-七维复盘AAR.md) —— 七维，含 8 条失败清单 | ✅ |
| （额外）编译产物 | [`build/paper.pdf`](build/paper.pdf) ＋ [`build/build.log`](build/build.log) | ✅ |
| （额外）可复跑流水线 | [`pipeline/`](pipeline/) —— 7 个脚本，从环境搭建到出图出表 | ✅ |
| （额外）核验证据 | [`核验/`](核验/) —— 引文核验表、论据对照表、任务书逐句对照表、编译验证记录 | ✅ |
| （额外）关键决策说明 | [`拿来说明/`](拿来说明/) —— 4 篇 | ✅ |

---

## 三、目录结构

```
C2/
├── README.md                     ← 本文件
├── paper.tex                     ← 【核心交付物】论文主文件
├── references.bib                ← 【核心交付物】30 条已核验文献（生成物，勿手改）
├── 编译说明.md                    ← 怎么把 paper.tex 编成 PDF
│
├── build/                        ← 编译产物
│   ├── paper.pdf                 ← 编译好的论文（15 页）
│   └── build.log                 ← 完整编译日志（含每一趟 pdflatex/bibtex）
│
├── figures/                      ← 论文插图（由脚本生成，矢量 PDF）
│   ├── fig1_assurance_chain.pdf
│   ├── fig2_study_a.pdf
│   └── fig3_study_b.pdf
│
├── pipeline/                     ← 【可复跑】七步流水线
│   ├── README.md                 ← 换一个题目怎么用（先读这个）
│   ├── 00_setup_texlive.py       ← TeX Live 环境搭建与修复
│   ├── 01_verify_refs.py         ← 三源交叉核验引用
│   ├── 02_build_bib.py           ← 由核验结果生成 references.bib
│   ├── 03_corpus_audit.py        ← 论文第 5 节的两个实证研究
│   ├── 04_make_figures.py        ← 生成插图
│   ├── 05_build.sh               ← 编译论文并做健全性检查
│   ├── 06_make_evidence_tables.py← 生成核验/引用核验表.md
│   ├── refs_candidates.json      ← 候选引用清单（v2，已修正）
│   ├── refs_corrections.json     ← v1→v2 每一条修正的证据
│   ├── artifact_adjudication.json← Study B 的人工裁定表
│   └── reports/                  ← 全部机器可读的核验与审计输出
│
├── 核验/                         ← 【重点】证据链
│   ├── 引用核验表.md              ← 30 条文献逐条证据（含命中的 DOI 与来源）
│   ├── 论据对照表.md              ← 论文每个论断 → 出处/数据
│   ├── 任务书逐句对照表.md         ← 任务书每一句 → 交付物（C1 教训 F6 的对策）
│   └── 编译验证记录.md            ← 编译环境、命令、日志、SHA-256
│
├── AI日志/                       ← 每日 AI 协作日志（5 篇）
├── AAR/                          ← 七维复盘
└── 拿来说明/                      ← 4 个关键决策的完整推导（含原文/指令/产出/对比）
```

---

## 四、怎么用

**只想要论文** → 读 [`build/paper.pdf`](build/paper.pdf)。
想自己编译 → 见 [`编译说明.md`](编译说明.md)，一条命令：`bash pipeline/05_build.sh`。

**想验证文献是真的** → 读 [`核验/引用核验表.md`](核验/引用核验表.md)，
里面每条都有标题相似度、命中的 DOI、以及是哪个索引确认的。
想自己重跑核验 → `python pipeline/01_verify_refs.py`（约 2 分钟，30 次三源查询）。

**想验证论文里的数字** → 全部来自 `pipeline/reports/corpus_audit.json`，
由 `python pipeline/03_corpus_audit.py` 重新生成。论文里**没有一个数字是手写的**。

**想复用这条流程** → 读 [`pipeline/README.md`](pipeline/README.md)。

**想知道哪里做得不好** → 直接看 [`AAR/C2-七维复盘AAR.md`](AAR/C2-七维复盘AAR.md)
维度五的失败清单（8 条，含 1 条最高优先级的方法论缺陷）。

---

## 五、论文的核心数据（全部可复算）

| 指标 | 数值 | 来源 |
|---|---|---|
| 凭记忆生成的候选引用 | 31 条 | `pipeline/refs_candidates.json` v1 存档 |
| 自动核验标记 | 5 条 | `reports/citation_verification_v1_from_memory.json` |
| **真实引用错误** | **3 条（9.7%）** | `reports/corpus_audit.json` → `study_a` |
| 语料规模（已核验） | 30 条 | `references.bib` |
| Study B 测量范围 | 26 条（有 arXiv 号者） | `reports/corpus_audit.json` → `study_b` |
| 有公开官方工件 | 13 条（50.0%） | `artifact_adjudication.json` |
| 自动筛选查准 / 查全 | 80.0% / 61.5% | `study_b2.auto_vs_adjudicated` |

三条真实的引用错误（论文表 3 有完整对照）：

1. **DeepSeek-Prover** —— 标题错，且给了一个 **语法合法、能解析、但指向无关论文** 的 arXiv 编号 `2308.08381`（真实编号是 `2405.14333`）。这是最危险的一类：任何「编号能打开就算过」的弱校验都拦不住。
2. **LiveBench** —— 把作者的 `Contamination-Limited` 写成了更强势的 `Contamination-Free`。
3. **Goedel-Prover** —— 把 `Theorem Proving` 写成了 `Program Verification`。

---

## 六、方法说明（如实交代）

**引用核验。** `references.bib` 是**生成物**，不是手写的。核验对每条候选查询三个互相独立的索引
（OpenAlex 主、Crossref 副、arXiv abs 页旁证），要求标题相似度 ≥ 0.90、第一作者姓氏一致、
年份相差 ≤ 1 年，三项全过才写入。核验不通过的条目一律不进入 bib。
DOI 一律回到 Crossref 反查权威出版信息，**不从 OpenAlex 的会议字段照抄**——
后者是按标题召回的，本次就出现过两条不同条目共享同一个 ACL DOI 的情况。

**数字。** 论文第 5 节的每一个数字都由 `03_corpus_audit.py` 从落盘的 API 响应用脚本算出；
插图从同一份 JSON 读数，所以图与表不可能不一致。

**未被验证的部分。** 论文的**论证文字没有经过人工逐句审读**。核验覆盖的是事实层
（引文、数据、图），不是论证层。论文第 7.3 节把这一点写在了正文里。

---

## 七、已知限制（不掩饰）

1. **Study A 的样本很小**：31 条、单一领域、单次会话、一个模型。9.7% 只能当作
   「这类错误确实存在且量级如此」的存在性证据，不能当作领域估计。
2. **Study B 只测「有没有公开的官方工件」**，不测它能不能跑、对不对得上论文、
   有没有维护。而且 4 条无 arXiv 号的条目（3 篇 Nature ＋ 1 篇 LNCS）被排除在外，
   这批恰好偏向期刊论文，可能系统性不同于预印本。
3. **Study B 的语料是人工策展的文献综述，不是随机抽样**，其构成是为了支撑框架而非检验框架。
   50% 这个数字不应被当作领域性质引用。
4. 论文作者栏已于提交前填写为 `Songpengfei`（原占位符 `Author Name` / `Affiliation` / `author@example.org` 与 `TODO(author)` 注释均已移除）。
5. **框架不是唯一的建模方式**：也可以把 $L_2$ 拆成解析与定型，或把资源约束单列为一段。
   论文只主张这个分解「有用」，不主张它「唯一」。

---

## 八、许可与致谢

- 论文为本次挑战原创作品。
- 引用的 30 篇文献版权归各自作者与出版方所有，本包仅在 `references.bib` 中记录题录信息，
  每个条目的 DOI / arXiv 链接可回溯原文。
- 挑战方随附的 `materials/Lectures on AI for Mathematics.pdf`（Xiaoyang Chen，arXiv:2604.11504）
  是本文问题框架的直接来源，已在论文第 2 节显式致谢并界定差异。
