#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C2 论文 · 第 1 步：引用核验

目的
----
本挑战的红线是「引用造假 → 研究严谨性 0 分」。因此 references.bib 中的每一条
都必须能在一个**独立的第三方权威索引**里被独立复现，而不是"AI 说有就有"。

做法
----
对候选清单中的每一条，分别向三个互相独立的来源发起查询：

  1. OpenAlex      https://api.openalex.org/works        （主：覆盖面广，含 arXiv 预印本）
  2. Crossref      https://api.crossref.org/works        （副：DOI 注册机构，出版方权威）
  3. arXiv abs 页   https://arxiv.org/abs/<id>            （旁证：仅对带 arXiv 号的条目）

然后做三项独立比对：标题、第一作者姓氏、年份。三项全过才算 VERIFIED。
本脚本**不修改任何原始返回**，全部落盘，供人工复核与复算。

输出
----
  reports/citation_verification.json   完整原始记录（含 API 返回关键字段）
  reports/citation_verification.csv    机器可读汇总表
  reports/citation_verification.md     人读版核验报告（含证据链）

用法
----
  python 01_verify_refs.py                 # 全量核验
  python 01_verify_refs.py --only yang2023leandojo
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import requests

# ---------------------------------------------------------------- 路径与常量

HERE = Path(__file__).resolve().parent
CANDIDATES = HERE / "refs_candidates.json"
REPORTS = HERE / "reports"
REPORTS.mkdir(exist_ok=True)

MAILTO = "c2.paper.verify@example.edu"          # 礼貌标识，换取更宽松的限流
UA = f"C2-AI4Math-RefVerifier/1.0 (mailto:{MAILTO})"
HTTP_TIMEOUT = 40
RETRIES = 3

TITLE_STRONG = 0.90        # 标题相似度：强匹配阈值
TITLE_WEAK = 0.70          # 标题相似度：弱匹配阈值


# ---------------------------------------------------------------- 工具函数

def norm_title(s: str) -> str:
    """标题归一化：去重音、去标点、压空白、转小写。

    目的：让 'Let\'s Verify Step by Step' 与 'Let’s verify step by step'
    这类排版差异不干扰比对。
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"<[^>]+>", " ", s)          # 去掉 arXiv 页面里混进来的标签
    s = re.sub(r"^title:\s*", "", s, flags=re.I)
    s = re.sub(r"[^0-9a-zA-Z一-鿿]+", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()


def surname(name: str) -> str:
    """从 'Kaiyu Yang' / 'Yang, Kaiyu' / 'Romera-Paredes, M.' 里取姓氏。"""
    if not name:
        return ""
    name = name.strip()
    if "," in name:
        name = name.split(",")[0]
    else:
        name = name.split()[-1] if name.split() else ""
    return re.sub(r"[^a-z]", "", name.lower())


def get_json(url: str, params: dict | None = None) -> tuple[int, dict | None]:
    """带重试的 JSON 拉取。失败不抛异常，返回 (状态码, None) 让上游记录。"""
    last = 0
    for attempt in range(RETRIES):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA},
                             timeout=HTTP_TIMEOUT)
            last = r.status_code
            if r.status_code == 200:
                return 200, r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            return r.status_code, None
        except requests.RequestException:
            time.sleep(2 ** attempt)
    return last, None


def get_text(url: str) -> tuple[int, str]:
    for attempt in range(RETRIES):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=HTTP_TIMEOUT)
            if r.status_code == 200:
                return 200, r.text
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            return r.status_code, ""
        except requests.RequestException:
            time.sleep(2 ** attempt)
    return 0, ""


# ---------------------------------------------------------------- 三个来源

def query_openalex(title: str) -> dict:
    """OpenAlex：主索引。"""
    url = "https://api.openalex.org/works"
    code, data = get_json(url, {
        "search": title,
        "per-page": 5,
        "mailto": MAILTO,
    })
    rec = {"source": "OpenAlex", "url": url, "http": code, "candidates": []}
    if code != 200 or not data:
        return rec
    for w in data.get("results", [])[:5]:
        src = (w.get("primary_location") or {}).get("source") or {}
        rec["candidates"].append({
            "title": w.get("title") or "",
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "year": w.get("publication_year"),
            "venue": src.get("display_name") or "",
            "type": w.get("type") or "",
            "authors": [a["author"]["display_name"]
                        for a in (w.get("authorships") or [])],
            "openalex_id": (w.get("id") or "").rsplit("/", 1)[-1],
            "cited_by_count": w.get("cited_by_count"),
        })
    return rec


def query_crossref(title: str) -> dict:
    """Crossref：DOI 注册机构，出版方口径。"""
    url = "https://api.crossref.org/works"
    code, data = get_json(url, {
        "query.bibliographic": title,
        "rows": 5,
        "mailto": MAILTO,
    })
    rec = {"source": "Crossref", "url": url, "http": code, "candidates": []}
    if code != 200 or not data:
        return rec
    for it in (data.get("message", {}).get("items") or [])[:5]:
        issued = (it.get("issued", {}) or {}).get("date-parts", [[None]])[0]
        rec["candidates"].append({
            "title": (it.get("title") or [""])[0],
            "doi": it.get("DOI") or "",
            "year": issued[0] if issued else None,
            "venue": (it.get("container-title") or [""])[0],
            "type": it.get("type") or "",
            "authors": [f"{a.get('given','')} {a.get('family','')}".strip()
                        for a in (it.get("author") or [])],
            # 结构化作者（given/family），供生成 BibTeX 时构造 "Family, Given"
            "authors_struct": [{"given": a.get("given", ""),
                                "family": a.get("family", "")}
                               for a in (it.get("author") or [])],
            "publisher": it.get("publisher") or "",
        })
    return rec


def query_arxiv(arxiv_id: str) -> dict:
    """arXiv abs 页：直接确认编号对应的论文确实存在、且标题一致。

    注意（v1 → v2 修正）：v1 版本没有解析 arXiv 页上的投稿日期，
    导致 arXiv 这条证据永远 year_ok=False，把所有只在 arXiv 上的条目
    误判为 PARTIAL（如 yue2024mammoth 标题相似度 1.0 却被降级）。
    这里补上 `[Submitted on 23 May 2024]` 的解析。
    """
    url = f"https://arxiv.org/abs/{arxiv_id}"
    code, html = get_text(url)
    rec = {"source": "arXiv", "url": url, "http": code, "candidates": []}
    if code != 200 or not html:
        return rec
    m = re.search(r'<h1 class="title mathjax">(.*?)</h1>', html, re.S)
    title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
    # arXiv 的 <h1> 里带一个 "Title:" 前缀。归一化比对时会去掉它，
    # 但如果这条证据被选为最佳命中，存下来的 title 会带着前缀，
    # 一路带进 references.bib（本次就是这样漏了两条，编译后才发现）。
    title = re.sub(r"^Title:\s*", "", title, flags=re.I).strip()
    ma = re.search(r'<div class="authors">(.*?)</div>', html, re.S)
    authors = []
    if ma:
        authors = [re.sub(r"<[^>]+>", "", a).strip()
                   for a in re.findall(r"<a[^>]*>(.*?)</a>", ma.group(1))]
    md = re.search(r'<div class="dateline">.*?Submitted on\s+(\d{1,2})\s+(\w+)\s+(\d{4})',
                   html, re.S)
    year = int(md.group(3)) if md else None
    rec["candidates"].append({"title": title, "authors": authors,
                              "arxiv_id": arxiv_id, "year": year})
    return rec


# ---------------------------------------------------------------- 判定

def judge(cand: dict, sources: list[dict]) -> dict:
    """三源交叉判定。

    规则（三条独立证据，缺一不可视为 VERIFIED）：
      A. 标题：至少一个来源里存在相似度 ≥ TITLE_STRONG 的条目
      B. 作者：该条目第一作者姓氏与候选条目的 first_author 一致
      C. 年份：该条目年份与候选年份相差 ≤ 1

    备注：年份放宽 ±1 是有意的 —— 预印本与正式出版年常常跨年
    （如 LeanDojo：arXiv 2023 / NeurIPS 2023，DeepSeek-Prover 亦然）。
    这一放宽被显式记录在报告里，不做隐式处理。
    """
    exp_title = cand["title"]
    exp_author = surname(cand.get("first_author", ""))
    exp_year = cand.get("year")

    best = None
    for src in sources:
        for c in src.get("candidates", []):
            t = sim(exp_title, c.get("title", ""))
            a = surname(c.get("authors", [""])[0]) if c.get("authors") else ""
            y = c.get("year")
            # 姓氏互为子串即算命中，容忍 "Romera-Paredes" / "RomeraParedes"
            # 这类连字符与缩写差异
            author_ok = bool(exp_author and a) and (exp_author in a or a in exp_author)
            year_ok = (y is not None and exp_year is not None
                       and abs(int(y) - int(exp_year)) <= 1)
            score = t + (0.5 if author_ok else 0) + (0.3 if year_ok else 0)
            if best is None or score > best["score"]:
                best = {
                    "score": round(score, 4),
                    "title_sim": round(t, 4),
                    "author_ok": author_ok,
                    "year_ok": year_ok,
                    "found_title": c.get("title", ""),
                    "found_authors": c.get("authors", []),          # 全量，不截断
                    "found_authors_struct": c.get("authors_struct", []),
                    "found_year": y,
                    "found_venue": c.get("venue", ""),
                    "found_doi": c.get("doi", ""),
                    "found_type": c.get("type", ""),
                    "via": src["source"],
                    "via_url": src["url"],
                }

    if best is None:
        status = "NOT_FOUND"
    elif (best["title_sim"] >= TITLE_STRONG and best["author_ok"]
          and best["year_ok"]):
        status = "VERIFIED"
    elif best["title_sim"] >= TITLE_WEAK:
        status = "PARTIAL"
    else:
        status = "NOT_FOUND"

    return {"status": status, "best": best}


# ---------------------------------------------------------------- 主流程

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="只核验某个 key")
    ap.add_argument("--out-suffix", default="")
    args = ap.parse_args()

    cands = json.loads(CANDIDATES.read_text(encoding="utf-8"))["candidates"]
    if args.only:
        cands = [c for c in cands if c["key"] == args.only]
        if not cands:
            print(f"[FATAL] 没有找到 key={args.only}", file=sys.stderr)
            return 2

    results = []
    for i, cand in enumerate(cands, 1):
        print(f"[{i}/{len(cands)}] {cand['key']:<26} {cand['title'][:58]}")
        sources = [query_openalex(cand["title"]),
                   query_crossref(cand["title"])]
        if cand.get("arxiv"):
            sources.append(query_arxiv(cand["arxiv"]))
        verdict = judge(cand, sources)
        results.append({
            "key": cand["key"],
            "expected": {
                "title": cand["title"],
                "first_author": cand.get("first_author"),
                "year": cand.get("year"),
                "arxiv": cand.get("arxiv"),
                "doi": cand.get("doi"),
                "role": cand.get("role"),
                "why": cand.get("why"),
            },
            "verdict": verdict,
            "sources": sources,
        })
        print(f"        -> {verdict['status']}"
              f"  title_sim={verdict['best']['title_sim'] if verdict['best'] else 'n/a'}"
              f"  via={verdict['best']['via'] if verdict['best'] else '-'}")
        time.sleep(0.6)          # 对公共 API 保持克制

    # 落盘 JSON
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    payload = {"generated_at": stamp, "tool": "01_verify_refs.py",
               "policy": {"title_strong": TITLE_STRONG, "title_weak": TITLE_WEAK,
                          "year_tolerance": 1,
                          "sources": ["OpenAlex", "Crossref", "arXiv abs"]},
               "count": len(results), "results": results}
    (REPORTS / f"citation_verification{args.out_suffix}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 落盘 CSV
    with open(REPORTS / f"citation_verification{args.out_suffix}.csv", "w",
              newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["key", "status", "title_sim", "author_ok", "year_ok",
                    "expected_title", "found_title", "found_year",
                    "found_venue", "found_doi", "via", "role"])
        for r in results:
            b = r["verdict"]["best"] or {}
            w.writerow([r["key"], r["verdict"]["status"], b.get("title_sim", ""),
                        b.get("author_ok", ""), b.get("year_ok", ""),
                        r["expected"]["title"], b.get("found_title", ""),
                        b.get("found_year", ""), b.get("found_venue", ""),
                        b.get("found_doi", ""), b.get("via", ""),
                        r["expected"]["role"]])

    # 人读版报告
    tally = {}
    for r in results:
        tally[r["verdict"]["status"]] = tally.get(r["verdict"]["status"], 0) + 1
    lines = [
        "# C2 论文 · 引用核验报告",
        "",
        f"- 生成时间：{stamp}",
        f"- 核验工具：`pipeline/01_verify_refs.py`（可复跑）",
        f"- 独立来源：OpenAlex（主）/ Crossref（副）/ arXiv abs 页（旁证）",
        f"- 判定阈值：标题相似度 ≥ {TITLE_STRONG} 且第一作者姓氏一致 且年份相差 ≤ 1 年",
        f"- 候选总数：**{len(results)}**",
        "",
        "## 汇总",
        "",
        "| 状态 | 条数 | 含义 |",
        "|---|---|---|",
        f"| VERIFIED | {tally.get('VERIFIED',0)} | 三项证据齐备，可进入 references.bib |",
        f"| PARTIAL | {tally.get('PARTIAL',0)} | 标题大致命中但作者/年份有出入，需人工裁定 |",
        f"| NOT_FOUND | {tally.get('NOT_FOUND',0)} | 三个来源都查不到，**一律不得引用** |",
        "",
        "## 逐条证据",
        "",
        "| # | key | 状态 | 标题相似度 | 作者 | 年份 | 命中标题 | 命中出处 | 年份 | DOI | 来源 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(results, 1):
        b = r["verdict"]["best"] or {}
        lines.append(
            f"| {i} | `{r['key']}` | **{r['verdict']['status']}** | "
            f"{b.get('title_sim','—')} | "
            f"{'✓' if b.get('author_ok') else '✗'} | "
            f"{'✓' if b.get('year_ok') else '✗'} | "
            f"{(b.get('found_title') or '—')[:70]} | "
            f"{(b.get('found_venue') or '—')[:34]} | "
            f"{b.get('found_year','—')} | "
            f"`{b.get('found_doi','—')}` | {b.get('via','—')} |")
    lines += [
        "",
        "## 判定口径说明（可复核）",
        "",
        "1. **为什么用三个来源**：单一数据库都有盲区。Crossref 不收部分 arXiv 预印本，",
        "   OpenAlex 的会议/期刊归属偶有滞后，arXiv abs 页只能覆盖预印本。",
        "   三源交叉后，任何一条引用至少能被其中一到两个来源独立复现。",
        "2. **为什么年份放宽 ±1**：预印本与正式出版年份跨年是常态",
        "   （LeanDojo：arXiv 2023 → NeurIPS 2023；FunSearch：arXiv 2023 → Nature 2024）。",
        "   本条放宽是**显式**的，写入 `policy.year_tolerance`，不是隐藏规则。",
        "3. **NOT_FOUND 的处置**：直接删除，不写入 `references.bib`，并在 AI 日志与 AAR 中",
        "   记为一次真实的 AI 幻觉案例。",
        "",
        "## 复跑方式",
        "",
        "```bash",
        "python pipeline/01_verify_refs.py",
        "```",
        "",
    ]
    (REPORTS / f"citation_verification{args.out_suffix}.md").write_text(
        "\n".join(lines), encoding="utf-8")

    print(f"\n完成：{tally}")
    print(f"报告已写入 {REPORTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
