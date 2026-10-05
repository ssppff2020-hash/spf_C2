# pipeline/ · 流水线使用说明

> **先读这个。** 七个脚本，从「没有 LaTeX」到「论文编译通过、数字可复算」。
> 每一步都可以单独跑，也可以按顺序跑完。

---

## 一、这条流水线解决什么问题

一篇 AI 辅助写的论文，最容易出问题的三处是：

| 问题 | 后果 | 本流水线的对策 |
|---|---|---|
| 引用是编的 | 红线的第一条：研究严谨性 0 分 | `01` 三源交叉核验，不通过就不进 bib |
| 数字是编的 | 论证不成立，且无法被复核 | `03` 全部数字由脚本从落盘数据算出 |
| 环境搭不起来 | 红线第二条：不可编译 ≤ 5 分 | `00` 把环境搭建也脚本化 |

---

## 二、七个步骤

```
00_setup_texlive.py   ← 环境：装 TeX Live，并把 8 个已知故障的对策固化
01_verify_refs.py     ← 引用：三源交叉核验候选清单
02_build_bib.py       ← 生成：由核验记录生成 references.bib
03_corpus_audit.py    ← 实证：论文第 5 节的两个研究
04_make_figures.py    ← 出图：三张矢量图（零硬编码数据）
05_build.sh           ← 编译：pdflatex → bibtex → pdflatex ×2 ＋ 五类健全性检查
06_make_evidence_tables.py ← 证据：由核验记录生成 核验/引用核验表.md
```

**全量复跑（约 10 分钟，含网络请求）：**

```bash
cd C2
python pipeline/00_setup_texlive.py doctor      # 先确认环境在
python pipeline/01_verify_refs.py               # 核验引用（约 2 分钟）
python pipeline/02_build_bib.py                 # 生成 references.bib
python pipeline/03_corpus_audit.py              # 重算全部数字（约 5 分钟）
python pipeline/04_make_figures.py              # 重新出图
bash   pipeline/05_build.sh                     # 编译论文
python pipeline/06_make_evidence_tables.py      # 重新生成引用核验表
```

---

## 三、每个脚本在干什么

### `00_setup_texlive.py` —— 环境

本机原本没有任何 TeX 发行版。这个脚本把安装与修复都固化了。

```bash
python 00_setup_texlive.py doctor     # 检查引擎/格式文件是否齐全
python 00_setup_texlive.py install <包名> [<包名>...]
python 00_setup_texlive.py refresh    # 打补丁 + 裁剪 language.dat + 建格式 + 建字体映射
python 00_setup_texlive.py patch      # 单独修 TeX Live 脚本的 PATH 分隔符 bug
```

它绕开不了的那些坑，都在
[`拿来说明/04`](../拿来说明/04-从零装TeXLive-八个故障与根因.md) 里写了根因。

> **注意**：`patch` 会**就地修改** TeX Live 自带的三个 Perl 脚本
> （`updmap.pl` / `fmtutil.pl` / `tlmgr.pl`），修的是它们把 PATH 分隔符写死成 `:` 的 bug。
> 原行保留为注释。这是修改第三方工具，所以在此声明。

### `01_verify_refs.py` —— 引用核验

对每条候选查询三个独立索引：**OpenAlex**（主）／**Crossref**（副）／**arXiv abs 页**（旁证）。

判定规则（三项全过才 VERIFIED）：

1. 标题归一化相似度 ≥ **0.90**
2. 第一作者姓氏一致
3. 年份相差 ≤ **1** 年（**显式放宽**，记录在输出的 `policy.year_tolerance` 里）

产出：

| 文件 | 内容 |
|---|---|
| `reports/citation_verification.json` | 全部原始记录（每条 3 个来源 × top-5 候选） |
| `reports/citation_verification.csv` | 机器可读汇总 |
| `reports/citation_verification.md` | 人读版报告 |

```bash
python 01_verify_refs.py                    # 全量
python 01_verify_refs.py --only yang2023leandojo   # 单条排查
```

### `02_build_bib.py` —— 生成 bib

**`references.bib` 是生成物，不是手写物。**

每个字段只能来自 `01` 的落盘记录；人工只能通过 `venue_override.json` 显式覆盖，且要写理由。

有 DOI 的条目会**回 Crossref 按 DOI 反查**权威会议名与类型——
**不从 OpenAlex 的会议字段照抄**，因为那是按标题召回的
（本流水线第一版就因此让两条不同论文共享了同一个 DOI，见
[`拿来说明/01`](../拿来说明/01-为什么-references.bib-必须由脚本生成.md)）。

```bash
python 02_build_bib.py            # 生成 ../references.bib
python 02_build_bib.py --check    # 只比对不写盘（CI 友好，不一致则退出码 1）
```

### `03_corpus_audit.py` —— 实证研究

产出论文第 5 节的**全部数字**。

- **Study A**：把 v1（凭记忆写的 31 条）与 v2（核验后的 30 条）对账，
  算幻觉率与失败模式分布。**不联网**，只读两份存档。
- **Study B**：测语料里有多少篇有公开的官方工件。
  两个信号（摘要声明 / GitHub 检索）＋ **26 条人工裁定**（读 `artifact_adjudication.json`）。
- **自动 vs 人工裁定**：算查准率与查全率——这是论文最有力的一个数字。

```bash
python 03_corpus_audit.py            # 全部
python 03_corpus_audit.py --study-a  # 只跑 Study A（不联网）
```

### `04_make_figures.py` —— 出图

**脚本里没有任何硬编码的数据常量**，三张图全部从 `reports/corpus_audit.json` 读数。
所以**图与表不可能不一致**。

> 图注一律用英文：论文是英文的，而且 matplotlib 默认字体没有中文字形。
> 第一版图注写了中文，渲染时报 `Glyph ... missing from font(s) DejaVu Sans`。

### `06_make_evidence_tables.py` —— 证据表

由 `01` 和 `03` 的落盘记录生成 [`核验/引用核验表.md`](../核验/引用核验表.md)。
**和 bib 同理：手维护的证据表会慢慢和证据脱节**，所以也做成生成物。

### `05_build.sh` —— 编译

```
pdflatex → bibtex → pdflatex → pdflatex
```

然后检查五类问题，**任何一类出现即以退出码 1 失败**：

未定义交叉引用 / 未定义引文 / 未定义控制序列 / Emergency stop / 找不到文件。

> 这个检查器**自己出过一次 bug**：`grep -c` 计数为 0 时退出码为 1，
> 导致变量变成 `"0\n0"`，所有检查被跳过，脚本却仍打印 "OK"。
> 已修复。**一个静默失效的检查器比没有检查器更危险。**

---

## 四、换一个题目怎么用

这条流水线的设计目标是**与课题解耦**。换题目的改动量：

| 脚本 | 要改什么 |
|---|---|
| `00_setup_texlive.py` | **不用改**。纯环境。 |
| `01_verify_refs.py` | **不用改**。改 `refs_candidates.json` 即可（换领域只需换候选清单）。 |
| `02_build_bib.py` | 基本不用改。若新领域有大量非英语文献，可能要调作者名处理。 |
| `03_corpus_audit.py` | **Study A 部分完全通用**（任何「AI 生成清单＋核验」都能套）。Study B 需要换判据。 |
| `04_make_figures.py` | 要重画图，但「数字只从 JSON 读」这个结构保留。 |
| `05_build.sh` | **不用改**。任何 LaTeX 项目都能用。 |

**最通用的两条，与领域完全无关：**

1. **「先让 AI 生成、原样落盘、再核验、报错误率」这个模式。**
   它把「AI 可靠吗」这个无法回答的问题，变成「AI 在这个任务上错多少」这个可以量的问题。
2. **「自动提名 ＋ 人工裁定 ＋ 两者都留证据」这个结构。**
   纯自动不可靠，纯人工不可复跑，两者结合才既可靠又可复跑。

---

## 五、文件清单

```
pipeline/
├── README.md                      ← 本文件
├── 00_setup_texlive.py            ← 环境搭建与修复
├── 01_verify_refs.py              ← 三源引用核验
├── 02_build_bib.py                ← 生成 references.bib
├── 03_corpus_audit.py             ← 两个实证研究
├── 04_make_figures.py             ← 三张插图
├── 05_build.sh                    ← 编译与健全性检查
├── 06_make_evidence_tables.py     ← 生成 核验/引用核验表.md
│
├── refs_candidates.json           ← 候选引用清单（v2，已修正）
├── refs_corrections.json          ← v1→v2 每一条修正的证据
├── venue_override.json            ← 会议名的人工覆盖（当前为空）
├── artifact_adjudication.json     ← Study B 的 26 条人工裁定
│
└── reports/                       ← 全部机器可读输出
    ├── citation_verification.json / .csv / .md
    ├── citation_verification_v1_from_memory.json / .csv / .md   ← v1 原始证据，未修改
    ├── references_bib_sha256.txt
    ├── corpus_audit.json
    └── artifact_availability.csv
```

---

## 六、已知限制

1. **`01_verify_refs.py` 每次跑都会重新查上游。** 几年后若索引改了记录，重跑结果可能与本文不同。
   所以 `reports/citation_verification.json` **是当时的证据快照，不是缓存**——以它为准。
2. **`--syncwithtrees` 会交互式提问。** `00_setup_texlive.py` 里用 `input="y\n"` 应答；
   如果在别的环境跑，注意这一点（第一遍回 `n` 会静默地什么都不做）。
3. **GitHub 搜索 API 未认证时限流很紧**（10 次/分钟）。
   `03_corpus_audit.py` 里为此加了 7 秒间隔；设 `GITHUB_TOKEN` 环境变量可显著加快。
4. **`02_build_bib.py` 的 `AUTHOR_OVERRIDES` 里有硬编码的作者修正**
   （目前只有 `chen2026lectures` 一条，因为 OpenAlex 把同一作者登记了两次）。
   这类硬编码是**有意的**，但每一条都应当有注释说明原因。
