# C2 论文 · 引用核验报告

- 生成时间：2026-10-05T18:14:33+0800
- 核验工具：`pipeline/01_verify_refs.py`（可复跑）
- 独立来源：OpenAlex（主）/ Crossref（副）/ arXiv abs 页（旁证）
- 判定阈值：标题相似度 ≥ 0.9 且第一作者姓氏一致 且年份相差 ≤ 1 年
- 候选总数：**31**

## 汇总

| 状态 | 条数 | 含义 |
|---|---|---|
| VERIFIED | 26 | 三项证据齐备，可进入 references.bib |
| PARTIAL | 3 | 标题大致命中但作者/年份有出入，需人工裁定 |
| NOT_FOUND | 2 | 三个来源都查不到，**一律不得引用** |

## 逐条证据

| # | key | 状态 | 标题相似度 | 作者 | 年份 | 命中标题 | 命中出处 | 年份 | DOI | 来源 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `polu2020gptf` | **VERIFIED** | 1.0 | ✓ | ✓ | Generative Language Modeling for Automated Theorem Proving | arXiv (Cornell University) | 2020 | `10.48550/arxiv.2009.03393` | OpenAlex |
| 2 | `han2022pact` | **VERIFIED** | 1.0 | ✓ | ✓ | Proof Artifact Co-training for Theorem Proving with Language Models | arXiv (Cornell University) | 2021 | `10.48550/arxiv.2102.06203` | OpenAlex |
| 3 | `wu2022autoformalization` | **VERIFIED** | 1.0 | ✓ | ✓ | Autoformalization with Large Language Models | arXiv (Cornell University) | 2022 | `10.48550/arxiv.2205.12615` | OpenAlex |
| 4 | `jiang2023dsp` | **VERIFIED** | 1.0 | ✓ | ✓ | Draft, Sketch, and Prove: Guiding Formal Theorem Provers with Informal | arXiv (Cornell University) | 2022 | `10.48550/arxiv.2210.12283` | OpenAlex |
| 5 | `yang2023leandojo` | **VERIFIED** | 1.0 | ✓ | ✓ | LeanDojo: Theorem Proving with Retrieval-Augmented Language Models | arXiv (Cornell University) | 2023 | `10.48550/arxiv.2306.15626` | OpenAlex |
| 6 | `xin2023deepseekprover` | **NOT_FOUND** | 0.4058 | ✗ | ✓ | SubgoalXL: Subgoal-based Expert Learning for Theorem Proving | arXiv (Cornell University) | 2024 | `10.48550/arxiv.2408.11172` | OpenAlex |
| 7 | `trinh2024alphageometry` | **VERIFIED** | 1.0 | ✓ | ✓ | Solving olympiad geometry without human demonstrations | Nature | 2024 | `10.1038/s41586-023-06747-5` | OpenAlex |
| 8 | `romera2024funsearch` | **VERIFIED** | 1.0 | ✓ | ✓ | Mathematical discoveries from program search with large language model | Nature | 2023 | `10.1038/s41586-023-06924-6` | OpenAlex |
| 9 | `demoura2021lean4` | **VERIFIED** | 1.0 | ✓ | ✓ | The Lean 4 Theorem Prover and Programming Language | Lecture notes in computer science | 2021 | `10.1007/978-3-030-79876-5_37` | OpenAlex |
| 10 | `cobbe2021gsm8k` | **VERIFIED** | 1.0 | ✓ | ✓ | Training Verifiers to Solve Math Word Problems | arXiv (Cornell University) | 2021 | `10.48550/arxiv.2110.14168` | OpenAlex |
| 11 | `lightman2024verify` | **VERIFIED** | 1.0 | ✓ | ✓ | Let's Verify Step by Step | arXiv (Cornell University) | 2023 | `10.48550/arxiv.2305.20050` | OpenAlex |
| 12 | `huang2024selfcorrect` | **VERIFIED** | 1.0 | ✓ | ✓ | Large Language Models Cannot Self-Correct Reasoning Yet | arXiv (Cornell University) | 2023 | `10.48550/arxiv.2310.01798` | OpenAlex |
| 13 | `stechly2024selfverification` | **VERIFIED** | 1.0 | ✓ | ✓ | On the Self-Verification Limitations of Large Language Models on Reaso | arXiv (Cornell University) | 2024 | `10.48550/arxiv.2402.08115` | OpenAlex |
| 14 | `kambhampati2024llmmodulo` | **VERIFIED** | 1.0 | ✓ | ✓ | LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks | arXiv (Cornell University) | 2024 | `10.48550/arxiv.2402.01817` | OpenAlex |
| 15 | `valmeekam2023planning` | **VERIFIED** | 1.0 | ✓ | ✓ | On the Planning Abilities of Large Language Models : A Critical Invest | arXiv (Cornell University) | 2023 | `10.48550/arxiv.2305.15771` | OpenAlex |
| 16 | `gao2023pal` | **VERIFIED** | 1.0 | ✓ | ✓ | PAL: Program-aided Language Models | arXiv (Cornell University) | 2022 | `10.48550/arxiv.2211.10435` | OpenAlex |
| 17 | `chen2023pot` | **VERIFIED** | 1.0 | ✓ | ✓ | Program of Thoughts Prompting: Disentangling Computation from Reasonin | arXiv (Cornell University) | 2022 | `10.48550/arxiv.2211.12588` | OpenAlex |
| 18 | `schick2023toolformer` | **VERIFIED** | 1.0 | ✓ | ✓ | Toolformer: Language Models Can Teach Themselves to Use Tools | arXiv (Cornell University) | 2023 | `10.48550/arxiv.2302.04761` | OpenAlex |
| 19 | `hendrycks2021math` | **VERIFIED** | 1.0 | ✓ | ✓ | Measuring Mathematical Problem Solving With the MATH Dataset | arXiv (Cornell University) | 2021 | `10.48550/arxiv.2103.03874` | OpenAlex |
| 20 | `yue2024mammoth` | **PARTIAL** | 1.0 | ✓ | ✗ | Title:MAmmoTH: Building Math Generalist Models through Hybrid Instruct | — | None | `` | arXiv |
| 21 | `zhou2023cheater` | **VERIFIED** | 1.0 | ✓ | ✓ | Don't Make Your LLM an Evaluation Benchmark Cheater | arXiv (Cornell University) | 2023 | `10.48550/arxiv.2311.01964` | OpenAlex |
| 22 | `sainz2023contamination` | **VERIFIED** | 1.0 | ✓ | ✓ | NLP Evaluation in trouble: On the Need to Measure LLM Data Contaminati | — | 2023 | `10.18653/v1/2023.findings-emnlp.722` | OpenAlex |
| 23 | `white2024livebench` | **PARTIAL** | 0.9217 | ✓ | ✗ | Title:LiveBench: A Challenging, Contamination-Limited LLM Benchmark | — | None | `` | arXiv |
| 24 | `rein2023gpqa` | **VERIFIED** | 1.0 | ✓ | ✓ | GPQA: A Graduate-Level Google-Proof Q&A Benchmark | arXiv (Cornell University) | 2023 | `10.48550/arxiv.2311.12022` | OpenAlex |
| 25 | `wang2023scientific` | **VERIFIED** | 1.0 | ✓ | ✓ | Scientific discovery in the age of artificial intelligence | Nature | 2023 | `10.1038/s41586-023-06221-2` | OpenAlex |
| 26 | `lu2024aiscientist` | **VERIFIED** | 1.0 | ✓ | ✓ | The AI Scientist: Towards Fully Automated Open-Ended Scientific Discov | arXiv (Cornell University) | 2024 | `10.48550/arxiv.2408.06292` | OpenAlex |
| 27 | `welleck2022naturalprover` | **VERIFIED** | 1.0 | ✓ | ✓ | NaturalProver: Grounded Mathematical Proof Generation with Language Mo | arXiv (Cornell University) | 2022 | `10.48550/arxiv.2205.12910` | OpenAlex |
| 28 | `lin2025goedelprover` | **PARTIAL** | 0.8188 | ✓ | ✓ | Goedel-Prover: A Frontier Model for Open-Source Automated Theorem Prov | arXiv (Cornell University) | 2025 | `10.48550/arxiv.2502.07640` | OpenAlex |
| 29 | `ren2025deepseekproverv2` | **VERIFIED** | 1.0 | ✓ | ✓ | DeepSeek-Prover-V2: Advancing Formal Mathematical Reasoning via Reinfo | arXiv (Cornell University) | 2025 | `10.48550/arxiv.2504.21801` | OpenAlex |
| 30 | `chen2026lectures` | **VERIFIED** | 1.0 | ✓ | ✓ | Lectures on AI for Mathematics | arXiv (Cornell University) | 2026 | `10.48550/arxiv.2604.11504` | OpenAlex |
| 31 | `outline2026ai4math` | **NOT_FOUND** | 0.3178 | ✗ | ✓ | Is This LLM Library Learning? Evaluation Must Account For Compute and  | — | 2026 | `10.18653/v1/2026.eacl-long.163` | OpenAlex |

## 判定口径说明（可复核）

1. **为什么用三个来源**：单一数据库都有盲区。Crossref 不收部分 arXiv 预印本，
   OpenAlex 的会议/期刊归属偶有滞后，arXiv abs 页只能覆盖预印本。
   三源交叉后，任何一条引用至少能被其中一到两个来源独立复现。
2. **为什么年份放宽 ±1**：预印本与正式出版年份跨年是常态
   （LeanDojo：arXiv 2023 → NeurIPS 2023；FunSearch：arXiv 2023 → Nature 2024）。
   本条放宽是**显式**的，写入 `policy.year_tolerance`，不是隐藏规则。
3. **NOT_FOUND 的处置**：直接删除，不写入 `references.bib`，并在 AI 日志与 AAR 中
   记为一次真实的 AI 幻觉案例。

## 复跑方式

```bash
python pipeline/01_verify_refs.py
```
