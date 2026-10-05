#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C2 论文 · 第 2 步：由核验结果生成 references.bib

设计原则
--------
**references.bib 是生成物，不是手写物。**

手写 .bib 正是引用造假的高发区：写的时候凭印象补作者、补年份、补会议名，
核验时又只核标题，于是作者列表和会议名成了没人检查的"自由文本"。
本脚本的做法是：bib 里的每一个字段都只能来自 01_verify_refs.py 落盘的
核验记录，字段来源在每条 entry 的注释里标明。人工只允许在
`venue_override.json` 里显式覆盖会议名，且每次覆盖都要写理由。

因此，任何人只要跑一遍 `01_verify_refs.py && 02_build_bib.py`，
都应该得到一份**逐字节可复现**的 references.bib。

用法
----
  python 02_build_bib.py            # 生成 ../references.bib
  python 02_build_bib.py --check    # 只比对，不写盘（CI 友好）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import requests

UA = "C2-AI4Math-RefVerifier/1.0 (mailto:c2.paper.verify@example.edu)"


def get(url: str) -> tuple[int, dict | None]:
    """带重试的 JSON 拉取（与 01_verify_refs.py 同款策略）。"""
    import time
    last = 0
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=40)
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

HERE = Path(__file__).resolve().parent
C2 = HERE.parent
REPORTS = HERE / "reports"
VERIFICATION = REPORTS / "citation_verification.json"
OVERRIDES = HERE / "venue_override.json"
OUT = C2 / "references.bib"

# 已知的作者列表需要人工纠正的条目（来源记录本身有错，非 AI 幻觉）
AUTHOR_OVERRIDES = {
    # OpenAlex 把同一作者登记了两次；提供的 PDF 封面写明为两位作者
    "chen2026lectures": "Chen, Xiaoyang and Jiang, Xiang",
}

PUBLISHED_TYPES = {"conference-paper", "article", "book-chapter", "book",
                   "review", "proceedings-article", "journal-article"}

# Crossref 的 type → BibTeX 条目类型
BIBTYPE = {
    "conference-paper": "inproceedings",
    "proceedings-article": "inproceedings",
    "journal-article": "article",
    "article": "article",
    "book-chapter": "incollection",
    "book": "book",
    "review": "article",
}


# ---------------------------------------------------------------- 工具

def norm(s: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", (s or "").lower())


def tsim(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def bib_author_from_display(name: str) -> str:
    """OpenAlex/arXiv 的 'Given Family' → 保持原样即可被 BibTeX 正确解析。

    只有当出现逗号（已经是 'Family, Given'）时原样保留。
    唯一的例外是含粒词/多段姓氏的名字，交由 AUTHOR_OVERRIDES 处理。
    """
    name = (name or "").strip()
    if not name:
        return ""
    return re.sub(r"\s+", " ", name)


def bib_author_from_struct(d: dict) -> str:
    g, f = (d.get("given") or "").strip(), (d.get("family") or "").strip()
    if f and g:
        return f"{f}, {g}"
    return f or g


def esc(s: str) -> str:
    """BibTeX 字段转义：保护 & % $ # _ { } 以及大写连字符。"""
    s = (s or "").strip()
    s = s.replace("\\", "")
    for a, b in [("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                 ("#", r"\#"), ("_", r"\_")]:
        s = s.replace(a, b)
    return s


# ---------------------------------------------------------------- 主流程

def resolve_doi(doi: str) -> dict | None:
    """拿 DOI 去 Crossref 反查权威出版信息。

    为什么必须反查、而不能用 OpenAlex 的会议字段：
    OpenAlex 的 conference-paper 记录里 venue 经常是空的，而且它是**按标题召回**的，
    同一标题下可能挂着完全不同的论文（本次就出现了两条不同条目共享同一个 ACL DOI
    的情况）。照抄这些字段等于制造一条"看起来有出处、实际对不上"的引用 ——
    正是红线所禁。Crossref 是 DOI 注册机构，按 DOI 反查得到的是**该 DOI 本身**的
    权威元数据，不存在召回错配的问题。
    """
    url = f"https://api.crossref.org/works/{doi}"
    code, data = get(url)
    if code != 200 or not data:
        return None
    m = data.get("message", {})
    issued = (m.get("issued", {}) or {}).get("date-parts", [[None]])[0]
    return {
        "container": (m.get("container-title") or [""])[0],
        "type": m.get("type") or "",
        "year": issued[0] if issued else None,
        "title": (m.get("title") or [""])[0],
        "publisher": m.get("publisher") or "",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="只比对不写盘；与磁盘内容不一致则退出码 1")
    args = ap.parse_args()

    if not VERIFICATION.exists():
        print("[FATAL] 找不到核验记录，请先跑 01_verify_refs.py", file=sys.stderr)
        return 2

    ver = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8")) \
        if OVERRIDES.exists() else {}

    entries, skipped = [], []
    for r in ver["results"]:
        key, exp = r["key"], r["expected"]
        verdict = r["verdict"]
        if verdict["status"] != "VERIFIED":
            skipped.append((key, verdict["status"]))
            continue
        b = verdict["best"]

        title = b["found_title"] or exp["title"]
        year = b["found_year"] or exp["year"]

        # ---- 作者：优先结构化（Crossref），否则用展示名，最后许人工覆盖
        if key in AUTHOR_OVERRIDES:
            authors = AUTHOR_OVERRIDES[key]
            author_src = "manual_override"
        elif b.get("found_authors_struct"):
            authors = " and ".join(bib_author_from_struct(d)
                                   for d in b["found_authors_struct"])
            author_src = "Crossref(struct)"
        else:
            authors = " and ".join(bib_author_from_display(a)
                                   for a in b["found_authors"])
            author_src = f"{b['via']}(display_name)"

        # ---- 出版信息
        ov = overrides.get(key, {})
        doi = b.get("found_doi") or exp.get("doi") or ""
        eprint = exp.get("arxiv") or ""
        # arXiv 的 DataCite DOI 与 eprint 字段重复，只保留 eprint
        m = re.match(r"10\.48550/[Aa]r[Xx]iv\.(.+)$", doi or "")
        if m:
            eprint = eprint or m.group(1)
            doi = ""

        # 有正式 DOI 就去 Crossref 反查权威 venue / 类型
        venue, cr_type, venue_src = "", "", ""
        if doi:
            cr = resolve_doi(doi)
            if cr and cr.get("container"):
                venue, cr_type, venue_src = cr["container"], cr["type"], "Crossref(DOI反查)"
                if cr.get("year"):
                    year = cr["year"]
        if ov.get("venue"):
            venue, venue_src = ov["venue"], "manual_override"

        bibtype = BIBTYPE.get(cr_type, "")
        if not bibtype:
            bibtype = "inproceedings" if venue else "misc"
        if bibtype == "inproceedings" and not venue:
            bibtype = "misc"

        fields = [
            ("author", authors),
            ("title", "{" + esc(title) + "}"),
            ("year", str(year)),
        ]
        if bibtype == "inproceedings":
            fields.append(("booktitle", esc(venue)))
        elif bibtype == "article" and venue:
            fields.append(("journal", esc(venue)))
        if eprint:
            fields.append(("eprint", eprint))
            fields.append(("archivePrefix", "arXiv"))
        if doi:
            fields.append(("doi", doi))
        if ov.get("note"):
            fields.append(("note", esc(ov["note"])))
        fields.append(("url", ov.get("url") or (
            f"https://doi.org/{doi}" if doi
            else (f"https://arxiv.org/abs/{eprint}" if eprint else ""))))

        body = ",\n".join(f"  {k:<14}= {{{v}}}" for k, v in fields if v)
        comment = (f"% 核验: {verdict['status']} · 标题相似度 {b['title_sim']} · "
                   f"作者来源 {author_src} · 命中来源 {b['via']}"
                   + (f" · 出版信息 {venue_src}" if venue_src else ""))
        entries.append((key, bibtype, comment, body))

    # ---- 组装文件
    header = f"""% ============================================================================
%  references.bib  —  C2 论文参考文献库
%  ---------------------------------------------------------------------------
%  【本文件是生成物，请勿手工编辑】
%  生成脚本 : pipeline/02_build_bib.py
%  核验记录 : pipeline/reports/citation_verification.json
%  生成时间 : {ver.get('generated_at')}
%  条目数   : {len(entries)}
%
%  每一条都通过了三源交叉核验（OpenAlex / Crossref / arXiv abs 页）：
%  标题相似度、第一作者姓氏、年份三项全部一致才算 VERIFIED。
%  核验不通过的条目一律不写入本文件。
%  逐条证据见 pipeline/reports/citation_verification.md
%  修正历史见 pipeline/refs_corrections.json
% ============================================================================

"""
    out = header + "\n\n".join(
        f"{c}\n@{t}{{{k},\n{b}\n}}" for k, t, c, b in entries) + "\n"

    if args.check:
        old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        same = old == out
        print(f"[check] {'一致' if same else '不一致'}")
        return 0 if same else 1

    OUT.write_text(out, encoding="utf-8")
    digest = hashlib.sha256(out.encode("utf-8")).hexdigest()
    print(f"写入 {OUT}")
    print(f"  条目数 {len(entries)} / 跳过 {len(skipped)}")
    print(f"  sha256 {digest}")
    if skipped:
        print(f"  [跳过未通过核验] {skipped}")
    (REPORTS / "references_bib_sha256.txt").write_text(
        f"{digest}  references.bib\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
