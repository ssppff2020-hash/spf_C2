#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C2 论文 · 第 3 步：语料审计（论文的实证部分）

本脚本产出论文第 5 节（Evaluation）里的全部数字。两个子研究：

  Study A —— 引用可靠性审计
      把「AI 凭记忆写出的 31 条候选引用」与「三源核验后人工裁定的 30 条」
      逐条对齐，统计幻觉率、按失败模式分类。
      这是本文最核心的实证结果：**文献综述这一层，本身就是一次未经验证的生成**。

  Study B —— 语料工件可得性
      对语料中所有 arXiv 条目抓 abs 页摘要，用正则检测作者是否声明了公开工件
      （代码仓库 / 形式化证明库 / 数据集）。衡量「可复现评估」这一范式在
      被调研语料里的实际落地程度。

两个子研究的原始输出全部落盘（reports/），论文里的每个数字都能追溯到具体行。

用法
----
  python 03_corpus_audit.py            # 跑全部
  python 03_corpus_audit.py --study-a  # 只跑 Study A（不联网）
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"
REPORTS.mkdir(exist_ok=True)

UA = "C2-AI4Math-CorpusAudit/1.0 (mailto:c2.paper.verify@example.edu)"

def norm(s: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", (s or "").lower())


def _sim(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


V1 = REPORTS / "citation_verification_v1_from_memory.json"
V2 = REPORTS / "citation_verification.json"
CORRECTIONS = HERE / "refs_corrections.json"
CAND_V2 = HERE / "refs_candidates.json"


# ================================================================ Study A

def study_a() -> dict:
    """引用可靠性审计：v1（凭记忆）→ v2（核验修正）。"""
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    v2 = json.loads(V2.read_text(encoding="utf-8"))
    corr = json.loads(CORRECTIONS.read_text(encoding="utf-8"))

    v1_keys = {r["key"] for r in v1["results"]}
    v2_keys = {r["key"] for r in v2["results"]}

    # 自动核验在 v1 阶段直接拦下的条目（未进入人工裁定）
    auto_flagged = [r for r in v1["results"]
                    if r["verdict"]["status"] != "VERIFIED"]

    severity = Counter(c["severity"] for c in corr["corrections"])
    ctype = Counter(c["type"] for c in corr["corrections"])

    real_errors = [c for c in corr["corrections"]
                   if c["severity"] in ("HIGH", "MEDIUM")]

    result = {
        "candidates_written_from_memory": len(v1_keys),
        "candidates_after_adjudication": len(v2_keys),
        "auto_flagged_by_pipeline": len(auto_flagged),
        "auto_flagged_detail": [
            {"key": r["key"], "status": r["verdict"]["status"],
             "title_sim": (r["verdict"]["best"] or {}).get("title_sim")}
            for r in auto_flagged],
        "human_adjudicated_entries": len(corr["corrections"]),
        "genuine_reference_errors": len(real_errors),
        "hallucination_rate_pct": round(
            100.0 * len(real_errors) / len(v1_keys), 2),
        "severity_breakdown": dict(severity),
        "failure_mode_breakdown": dict(ctype),
        "errors": [
            {"key": c["key"], "severity": c["severity"], "type": c["type"],
             "v1": c.get("v1_title") or c.get("v1"),
             "v2": c.get("v2_title") or c.get("v2") or c.get("v2_action")}
            for c in real_errors],
    }
    return result


# ================================================================ Study B

# 工件声明的检测模式。刻意保守：只认明确的"这里有东西可跑"的表述，
# 不认泛泛的 "we use X"。宁可低估，不可高估。
ARTIFACT_PATTERNS = [
    (r"github\.com/[\w.\-]+/[\w.\-]+", "repo_url"),
    (r"code (?:is |are )?(?:publicly )?available", "code_available"),
    (r"open[- ]sourc\w+", "open_source"),
    (r"our code", "our_code"),
    (r"we release (?:our )?(?:code|data|model)", "we_release"),
    (r"(?:dataset|benchmark) (?:is |are )?(?:publicly )?available", "data_available"),
    (r"huggingface\.co/[\w.\-]+", "hf_url"),
    (r"zenodo\.org", "zenodo"),
]


def fetch_abstract(arxiv_id: str) -> str:
    """抓 arXiv abs 页的摘要原文。"""
    url = f"https://arxiv.org/abs/{arxiv_id}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=40)
            if r.status_code == 200:
                m = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>',
                              r.text, re.S)
                if m:
                    txt = re.sub(r"<[^>]+>", " ", m.group(1))
                    txt = (txt.replace("&amp;", "&").replace("&lt;", "<")
                              .replace("&gt;", ">").replace("&#39;", "'"))
                    return re.sub(r"\s+", " ", txt).strip()
                return ""
            time.sleep(2 ** attempt)
        except requests.RequestException:
            time.sleep(2 ** attempt)
    return ""


def study_b() -> dict:
    """工件可得性：检索语料中 arXiv 条目是否声明白盒可复现的工件。"""
    cands = json.loads(CAND_V2.read_text(encoding="utf-8"))["candidates"]
    rows = []
    for c in cands:
        aid = c.get("arxiv")
        if not aid:
            rows.append({"key": c["key"], "role": c.get("role"), "title": c["title"],
                         "arxiv": "", "has_artifact": None,
                         "signals": "", "note": "非 arXiv 条目，未纳入本次测量"})
            continue
        abs_txt = fetch_abstract(aid)
        hits = []
        for pat, label in ARTIFACT_PATTERNS:
            m = re.search(pat, abs_txt, re.I)
            if m:
                hits.append(f"{label}:{m.group(0)[:48]}")
        rows.append({
            "key": c["key"], "role": c.get("role"), "title": c["title"], "arxiv": aid,
            "has_artifact": bool(hits),
            "signals": " | ".join(hits),
            "note": "" if abs_txt else "摘要抓取失败",
            "abstract_chars": len(abs_txt),
        })
        time.sleep(0.5)

    measured = [r for r in rows if r["has_artifact"] is not None]
    with_art = [r for r in measured if r["has_artifact"]]
    by_role = defaultdict(lambda: [0, 0])
    for r in measured:
        by_role[r["role"]][0] += 1
        if r["has_artifact"]:
            by_role[r["role"]][1] += 1

    return {
        "corpus_size": len(rows),
        "measured_arxiv_entries": len(measured),
        "entries_declaring_artifact": len(with_art),
        "artifact_rate_pct": round(100.0 * len(with_art) / max(len(measured), 1), 1),
        "by_role": {k: {"measured": v[0], "with_artifact": v[1],
                        "rate_pct": round(100.0 * v[1] / max(v[0], 1), 1)}
                    for k, v in sorted(by_role.items())},
        "rows": rows,
    }


# ================================================================ Study B2

def project_name(title: str) -> tuple[str, str]:
    """拆出 (检索词, 项目名)。

    检索词用标题的第一个短语；项目名只取冒号前的部分 ——
    没有冒号就用整个标题（并因此很难命中，属**故意保守**）。
    v1 版本在无冒号时退回"取第一个单词"，结果 'Training Verifiers...'
    被拿去和 GitHub 上的 'training' 对上，产生了假阳性。
    """
    head = re.split(r"[:：]", title)[0].strip()
    query = head if len(head.split()) <= 4 else " ".join(head.split()[:3])
    return query, head


def study_b2(rows: list[dict]) -> dict:
    """用一个独立的第二信号：GitHub 上能否检索到与论文同名的公开仓库。

    为什么要第二个信号：摘要没提代码，不代表没代码 —— 很多论文把仓库链接
    写在正文或页脚。GitHub 检索能捕捉这部分。两个信号都在，
    结论才站得住；两者不一致的地方，本脚本如实并列，不做取舍。
    """
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    out_rows = []
    for r in rows:
        key = r["key"]
        if not r.get("arxiv"):
            continue
        title = r.get("title") or ""
        q, proj = project_name(title)
        url = "https://api.github.com/search/repositories"
        rec = {"key": key, "role": r.get("role"), "query": q,
               "found": False, "repo": "", "stars": None, "pushed_at": "",
               "description": "", "name_in_title": False, "http": None,
               "name_sim": None, "desc_sim": None, "html_url": ""}
        for attempt in range(4):
            try:
                resp = requests.get(url, headers=headers, timeout=40,
                                    params={"q": q, "per_page": 3})
                rec["http"] = resp.status_code
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    if items:
                        it = items[0]
                        rec.update({
                            "found": True,
                            "repo": it.get("full_name", ""),
                            "stars": it.get("stargazers_count"),
                            "pushed_at": (it.get("pushed_at") or "")[:10],
                            "description": (it.get("description") or "")[:160],
                            "html_url": it.get("html_url", ""),
                        })
                        # 判定：仓库名≈项目名，或仓库描述≈论文标题。
                        # 两者都用归一化后的相似度，阈值取得偏严（宁漏勿错）。
                        name_sim = _sim(proj, it.get("name", ""))
                        desc_sim = _sim(title, it.get("description") or "")
                        rec["name_sim"] = round(name_sim, 3)
                        rec["desc_sim"] = round(desc_sim, 3)
                        rec["name_in_title"] = (name_sim >= 0.90
                                                or desc_sim >= 0.70)
                    break
                if resp.status_code in (403, 429):
                    time.sleep(8)          # 未认证时搜索接口限流很紧
                    continue
                break
            except requests.RequestException:
                time.sleep(4)
        out_rows.append(rec)
        time.sleep(7 if not token else 1)  # 未认证：10 次/分钟

    found = [r for r in out_rows if r["found"] and r["name_in_title"]]
    return {
        "queries": len(out_rows),
        "repo_found_name_matching": len(found),
        "repo_found_any": sum(1 for r in out_rows if r["found"]),
        "rate_pct": round(100.0 * len(found) / max(len(out_rows), 1), 1),
        "rows": out_rows,
    }


# ================================================================ 裁定合并

def merge_adjudication(b2: dict, b_rows: list[dict]) -> dict:
    """把人工裁定表合并进自动检索结果，产出论文最终用的数字。

    这里额外算一件论文需要、但两个子研究单独都算不出来的事：
    **自动筛选相对人工裁定的查准率与查全率。**
    "自动"取两个信号的并集（摘要声明 或 GitHub 提名）。tier=official 才算
    真阳性；自动命中但 tier 不是 official 的算假阳性。
    这组数字是论文"自动化需要一个验证层"这个论点的直接证据，
    所以必须由脚本算，不能手写。
    """
    path = HERE / "artifact_adjudication.json"
    if not path.exists():
        b2["adjudication"] = None
        return b2
    adj = json.loads(path.read_text(encoding="utf-8"))["adjudication"]
    role_of = {r["key"]: r.get("role") for r in b_rows}
    sig_abs = {r["key"]: bool(r["has_artifact"]) for r in b_rows}

    rows = []
    for r in b2["rows"]:
        a = adj.get(r["key"], {})
        rows.append({**r, "tier": a.get("tier", "unadjudicated"),
                     "tier_repo": a.get("repo", ""),
                     "tier_evidence": a.get("evidence", ""),
                     "auto_flag": bool(r.get("name_in_title"))
                                  or sig_abs.get(r["key"], False)})
    b2["rows"] = rows

    tier = Counter(r["tier"] for r in rows)
    official = [r for r in rows if r["tier"] == "official"]

    # ---- 自动筛选 vs 人工裁定 -------------------------------------------
    tp = [r for r in rows if r["auto_flag"] and r["tier"] == "official"]
    fp = [r for r in rows if r["auto_flag"] and r["tier"] != "official"]
    fn = [r for r in rows if not r["auto_flag"] and r["tier"] == "official"]
    b2["auto_vs_adjudicated"] = {
        "auto_flagged": sum(1 for r in rows if r["auto_flag"]),
        "true_positive": len(tp), "false_positive": len(fp),
        "false_negative": len(fn),
        "precision_pct": round(100.0 * len(tp) / max(len(tp) + len(fp), 1), 1),
        "recall_pct": round(100.0 * len(tp) / max(len(tp) + len(fn), 1), 1),
        "false_positive_keys": [r["key"] for r in fp],
        "false_negative_keys": [r["key"] for r in fn],
    }

    # ---- 按范式汇总 ------------------------------------------------------
    by_role = defaultdict(lambda: [0, 0, 0])     # measured, auto, official
    for r in rows:
        role = role_of.get(r["key"]) or "unknown"
        by_role[role][0] += 1
        if r["tier"] == "official":
            by_role[role][2] += 1
            if r["auto_flag"]:
                by_role[role][1] += 1

    b2["tier_breakdown"] = dict(tier)
    b2["official_count"] = len(official)
    b2["official_rate_pct"] = round(100.0 * len(official) / max(len(rows), 1), 1)
    b2["official_by_role"] = {
        k: {"measured": v[0], "official": v[2],
            "rate_pct": round(100.0 * v[2] / max(v[0], 1), 1),
            "auto": v[1], "missed": v[2] - v[1]}
        for k, v in sorted(by_role.items())}
    b2["official_repos"] = [
        {"key": r["key"], "repo": r["tier_repo"], "stars": r["stars"],
         "last_push": r["pushed_at"]} for r in official]
    return b2


# ================================================================ 主流程

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study-a", action="store_true", help="只跑 Study A")
    args = ap.parse_args()

    out = {}

    print("=== Study A: 引用可靠性审计 ===")
    out["study_a"] = study_a()
    a = out["study_a"]
    print(f"  凭记忆写出候选   : {a['candidates_written_from_memory']}")
    print(f"  自动核验拦下     : {a['auto_flagged_by_pipeline']}")
    print(f"  人工裁定         : {a['human_adjudicated_entries']}")
    print(f"  真实引用错误     : {a['genuine_reference_errors']}"
          f"  (幻觉率 {a['hallucination_rate_pct']}%)")
    print(f"  严重度分布       : {a['severity_breakdown']}")

    if not args.study_a:
        print("=== Study B: 语料工件可得性 ===")
        out["study_b"] = study_b()
        b = out["study_b"]
        print(f"  纳入测量 (arXiv) : {b['measured_arxiv_entries']}/{b['corpus_size']}")
        print(f"  声明白盒工件     : {b['entries_declaring_artifact']}"
              f"  ({b['artifact_rate_pct']}%)")
        for role, v in b["by_role"].items():
            print(f"    {role:<14} {v['with_artifact']}/{v['measured']} = {v['rate_pct']}%")

        print("=== Study B2: GitHub 公开仓库检索 ===")
        out["study_b2"] = merge_adjudication(study_b2(b["rows"]), b["rows"])
        b2 = out["study_b2"]
        print(f"  检索条数         : {b2['queries']}")
        print(f"  同名仓库命中     : {b2['repo_found_name_matching']} ({b2['rate_pct']}%)")
        print(f"  人工裁定 tier    : {b2.get('tier_breakdown')}")
        print(f"  官方工件         : {b2.get('official_count')} "
              f"({b2.get('official_rate_pct')}%)")
        for role, v in b2.get("official_by_role", {}).items():
            print(f"    {role:<14} {v['official']}/{v['measured']} = {v['rate_pct']}%"
                  f"  (auto {v['auto']}, missed {v['missed']})")
        av = b2.get("auto_vs_adjudicated", {})
        print(f"  自动 vs 人工裁定 : P={av.get('precision_pct')}% "
              f"R={av.get('recall_pct')}%  "
              f"(TP={av.get('true_positive')} FP={av.get('false_positive')} "
              f"FN={av.get('false_negative')})")

    (REPORTS / "corpus_audit.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # 论文用的 CSV
    if "study_b" in out:
        with open(REPORTS / "artifact_availability.csv", "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["key", "role", "arxiv", "has_artifact", "signals", "note"])
            for r in out["study_b"]["rows"]:
                w.writerow([r["key"], r["role"], r["arxiv"],
                            r["has_artifact"], r["signals"], r["note"]])

    print(f"\n已写入 {REPORTS/'corpus_audit.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
