#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C2 paper - step 6: generate the evidence table at ../核验/引用核验表.md

The table is derived entirely from the artefacts produced by steps 01 and 03.
Nothing in it is typed by hand -- for the same reason references.bib is not:
a hand-maintained evidence table drifts away from the evidence.

Usage
-----
  python 06_make_evidence_tables.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
C2 = HERE.parent
REPORTS = HERE / "reports"
OUT = C2 / "核验" / "引用核验表.md"


def main() -> int:
    ver = json.loads((REPORTS / "citation_verification.json").read_text(encoding="utf-8"))
    corr = json.loads((HERE / "refs_corrections.json").read_text(encoding="utf-8"))
    audit = json.loads((REPORTS / "corpus_audit.json").read_text(encoding="utf-8"))
    adj = json.loads((HERE / "artifact_adjudication.json")
                     .read_text(encoding="utf-8"))["adjudication"]

    L: list[str] = []
    A = L.append

    A("# C2 论文 · 引用核验表")
    A("")
    A("> 本表由 `pipeline/06_make_evidence_tables.py` 从核验记录自动生成，**不是手写的**。")
    A("> 重新生成：见本文件第七节。")
    A(f"> 核验生成时间：{ver['generated_at']}　｜　工具：{ver['tool']}")
    A("")
    A("## 一、核验规则")
    A("")
    A("每条候选引用必须同时通过三项独立检查，全部通过才写入 `references.bib`：")
    A("")
    A("| # | 检查项 | 阈值 | 为什么是这个阈值 |")
    A("|---|---|---|---|")
    A("| 1 | 标题归一化相似度 | >= 0.90 | 归一化后比较，容忍大小写/标点/破折号差异，但不容忍换词 |")
    A("| 2 | 第一作者姓氏 | 必须一致 | 姓氏互为子串即算命中，容忍 `Romera-Paredes` 这类连字符差异 |")
    A("| 3 | 年份 | 相差 <= 1 年 | **显式放宽**：预印本与正式出版跨年是常态（LeanDojo：arXiv 2023 / NeurIPS 2023） |")
    A("")
    A("三个独立来源：**OpenAlex**（主，覆盖 arXiv 预印本）、**Crossref**（副，DOI 注册机构）、")
    A("**arXiv abs 页**（旁证，直接检验编号本身）。")
    A("")
    A("> 年份放宽规则必须显式，不能藏在代码里。它记录在机器可读输出的 "
      "`policy.year_tolerance` 字段中。")
    A("")
    A("## 二、核验结果总览")
    A("")
    c = Counter(r["verdict"]["status"] for r in ver["results"])
    n_bib = sum(1 for _ in (C2 / "references.bib").read_text(encoding="utf-8").splitlines()
                if _.startswith("@"))
    A(f"- 候选总数（v2，已修正）：**{ver['count']}**")
    A(f"- 全部通过（VERIFIED）：**{c.get('VERIFIED', 0)}**")
    A(f"- 实际写入 `references.bib`：**{n_bib} 条**")
    A("")
    A("## 三、逐条核验记录")
    A("")
    A("命中出处 = OpenAlex 记录的出版渠道；`via` = 哪一路证据给出的最佳匹配。")
    A("")
    A("| # | key | 状态 | 标题相似度 | 作者 | 年份 | 命中标题 | 出处 | 年份 | DOI | 确认来源 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(ver["results"], 1):
        b = r["verdict"]["best"] or {}
        t = b.get("found_title") or "—"
        t = t[:62] + ("…" if len(t) > 62 else "")
        v = b.get("found_venue") or "—"
        v = v[:24] + ("…" if len(v) > 24 else "")
        A(f"| {i} | `{r['key']}` | {r['verdict']['status']} | {b.get('title_sim', '—')} | "
          f"{'Y' if b.get('author_ok') else 'N'} | {'Y' if b.get('year_ok') else 'N'} | "
          f"{t} | {v} | {b.get('found_year', '—')} | "
          f"`{b.get('found_doi') or '—'}` | {b.get('via', '—')} |")
    A("")
    A("## 四、生成过程中发现并修正的真实错误")
    A("")
    A("以下是 v1（AI 凭记忆写出）→ v2（核验修正）的**真实引用错误**。")
    A("完整修正记录见 [`pipeline/refs_corrections.json`](../pipeline/refs_corrections.json)。")
    A("")
    for e in audit["study_a"]["errors"]:
        A(f"### {e['severity']} · `{e['key']}` · {e['type']}")
        A("")
        A(f"- **v1（错误）**：{e['v1']}")
        A(f"- **v2（正确）**：{e['v2']}")
        d = next((x for x in corr["corrections"] if x["key"] == e["key"]), {})
        if d.get("how_found"):
            A(f"- **怎么发现的**：{d['how_found']}")
        if d.get("diagnosis"):
            A(f"- **诊断**：{d['diagnosis']}")
        A("")
    A("## 五、非错误、但需要说明的裁定")
    A("")
    for x in corr["corrections"]:
        if x["severity"] in ("LOW", "INFO"):
            A(f"- **`{x['key']}`**（{x['type']}）：{x.get('diagnosis', '')}")
    A("")
    A("## 六、Study B：工件可得性的人工裁定")
    A("")
    A("自动检索只负责**提名**，是否算「该论文的官方工件」由人工判定，逐条留证据：")
    A("`official` = 作者本人/本机构的仓库且指向该论文；`third_party` = 社区复现；")
    A("`family` = 同系列的**别的**论文的仓库；`none` = 未找到。")
    A("")
    A("| key | tier | 仓库 | 证据 |")
    A("|---|---|---|---|")
    order = {"official": 0, "third_party": 1, "family": 2, "none": 3}
    for k, v in sorted(adj.items(), key=lambda kv: (order.get(kv[1]["tier"], 9), kv[0])):
        repo = f"`{v['repo']}`" if v["repo"] else "—"
        A(f"| `{k}` | **{v['tier']}** | {repo} | {v['evidence'][:92]} |")
    A("")
    A("## 七、复跑方式")
    A("")
    A("```bash")
    A("python pipeline/01_verify_refs.py          # 三源核验，约 2 分钟")
    A("python pipeline/02_build_bib.py            # 由核验结果生成 references.bib")
    A("python pipeline/03_corpus_audit.py         # 重算论文第 5 节全部数字")
    A("python pipeline/06_make_evidence_tables.py # 重新生成本表")
    A("```")
    A("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"written {OUT} ({len(L)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
