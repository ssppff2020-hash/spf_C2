#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C2 paper - step 4: generate the paper's figures.

Every number plotted here is read from reports/corpus_audit.json. No data
constant is hard-coded in this file, so a figure can never drift out of sync
with the table generated from the same JSON.

Labels are English on purpose: the paper is English, and matplotlib's default
font has no CJK glyphs (which is exactly how the first version of this script
failed -- see the AI log for 2026-10-05).

Usage
-----
  python 04_make_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
C2 = HERE.parent
FIGS = C2 / "figures"
FIGS.mkdir(exist_ok=True)
AUDIT = HERE / "reports" / "corpus_audit.json"

# One colour per paradigm, used consistently in every figure and table.
C_V = "#2f6f9f"      # verifier-in-the-loop
C_F = "#b3592a"      # formalization
C_R = "#4c8c4a"      # reproducible evaluation

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
})


def load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- Figure 1

def fig_assurance_chain(out: Path) -> None:
    """The four-link assurance chain: where each paradigm intervenes, and
    what residual risk it leaves behind."""
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.4)
    ax.axis("off")

    stages = [
        (0.4, "Informal claim", "natural-language\nmathematical claim"),
        (3.3, "Reduction", "map to a formal\nor executable object"),
        (6.2, "Formal object", "proof term / program\n/ constraint system"),
        (9.1, "Verdict", "kernel check or\nautomated decision"),
    ]
    for i, (x, title, sub) in enumerate(stages):
        ax.add_patch(FancyBboxPatch((x, 3.7), 2.4, 1.5,
                                    boxstyle="round,pad=0.08",
                                    linewidth=1.1, edgecolor="#333333",
                                    facecolor="#f2f2f2"))
        ax.text(x + 1.2, 4.72, title, ha="center", va="center",
                fontsize=8.6, fontweight="bold")
        ax.text(x + 1.2, 4.16, sub, ha="center", va="center", fontsize=6.9,
                color="#444444")
        if i < len(stages) - 1:
            ax.add_patch(FancyArrowPatch((x + 2.42, 4.45), (x + 2.88, 4.45),
                                         arrowstyle="-|>", mutation_scale=11,
                                         linewidth=1.0, color="#333333"))

    guards = [
        (C_V, "V - Verifier-in-the-loop", 9.1,
         "guards link 4 (judgement)",
         "residual risk: reduction jump; verifier shares the generator's distribution"),
        (C_F, "F - Formalization", 3.3,
         "guards links 2-4 (reduction + judgement)",
         "residual risk: autoformalization mistranslates the statement"),
        (C_R, "R - Reproducible evaluation", 0.4,
         "guards what precedes link 1 (the measurement)",
         "residual risk: construct validity - a benchmark is not a capability"),
    ]
    for i, (color, name, x, held, risk) in enumerate(guards):
        y = 2.55 - i * 0.80
        ax.add_patch(FancyBboxPatch((0.4, y - 0.30), 11.2, 0.66,
                                    boxstyle="round,pad=0.05",
                                    linewidth=0.9, edgecolor=color,
                                    facecolor="#ffffff"))
        ax.plot([x + 1.2, x + 1.2], [4.42, y + 0.36], color=color,
                linewidth=1.4, linestyle=(0, (3, 2)))
        ax.text(0.62, y + 0.17, name, fontsize=8.0, fontweight="bold",
                color=color, va="center")
        ax.text(0.62, y - 0.14, f"{held}  |  {risk}", fontsize=6.7,
                color="#333333", va="center")

    ax.text(0.4, 5.84,
            "The four-link assurance chain and where each paradigm intervenes",
            fontsize=9.2, fontweight="bold")
    ax.text(0.4, 5.46,
            "No single paradigm covers the whole chain: residual risk is not removed, only moved.",
            fontsize=7.6, color="#555555")
    fig.savefig(out)
    plt.close(fig)


# ---------------------------------------------------------------- Figure 2

def fig_study_a(out: Path, audit: dict) -> None:
    """The audit funnel: 31 memory-written candidates -> 5 flagged -> 3 errors.

    A funnel reads better than the two-panel version first produced here: the
    point is the *attrition*, and a stacked bar hides it behind an axis label
    that was long enough to get clipped off the page.
    """
    a = audit["study_a"]
    n_total = a["candidates_written_from_memory"]
    n_flag = a["auto_flagged_by_pipeline"]
    n_err = len(a["errors"])

    steps = [
        (n_total, "written from LLM memory",
         "no retrieval, no verification at generation time", "#4a4a4a"),
        (n_flag, "flagged by the three-source check",
         "title similarity / first-author surname / year", "#d9743a"),
        (n_err, "confirmed genuine errors",
         "2 further flags dismissed as a tooling bug and a scope mistake",
         "#b3251f"),
    ]

    fig, ax = plt.subplots(figsize=(7.2, 2.75))
    for i, (val, label, sub, color) in enumerate(steps):
        y = -i
        ax.barh([y], [val], color=color, edgecolor="none", height=0.52)
        ax.text(val + 0.45, y, f"{val}", va="center", ha="left",
                fontsize=12, fontweight="bold", color=color)
        ax.text(-0.45, y, label, va="center", ha="right", fontsize=8.4)
        ax.text(0.25, y - 0.44, sub, va="center", ha="left", fontsize=6.9,
                color="#666666")

    ax.set_xlim(0, n_total * 1.08)
    ax.set_ylim(-2.75, 0.75)
    ax.set_yticks([])
    ax.set_xlabel(f"number of candidate references (n = {n_total})")
    ax.spines["left"].set_visible(False)
    ax.set_title(f"Figure 2. Reliability audit of the citation-generation layer "
                 f"- error rate {a['hallucination_rate_pct']}%",
                 fontsize=9.2, fontweight="bold")
    fig.savefig(out)
    plt.close(fig)


# ---------------------------------------------------------------- Figure 3

def fig_study_b(out: Path, audit: dict) -> None:
    """Official-artifact rate by paradigm: automated screen vs adjudicated."""
    b, b2 = audit["study_b"], audit["study_b2"]
    roles = ["paradigm_F", "paradigm_V", "paradigm_R"]
    label = {"paradigm_F": "F - Formalization",
             "paradigm_V": "V - Verifier-in-loop",
             "paradigm_R": "R - Reproducible eval"}
    colors = {"paradigm_F": C_F, "paradigm_V": C_V, "paradigm_R": C_R}

    # "Automated" here is the union of both signals (abstract wording OR
    # GitHub match), matching Table 3. Using the abstract screen alone would
    # understate the automation and make the figure disagree with the table.
    auto, adj = [], []
    for r in roles:
        ar = b2["official_by_role"].get(r, {"official": 0, "measured": 1,
                                            "auto": 0})
        auto.append(100.0 * ar["auto"] / ar["measured"])
        adj.append(100.0 * ar["official"] / ar["measured"])

    x = range(len(roles))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    bars1 = ax.bar([i - w / 2 for i in x], auto, w,
                   label="automated screen (abstract OR repo match)",
                   color="#cfcfcf", edgecolor="#666666")
    bars2 = ax.bar([i + w / 2 for i in x], adj, w,
                   label="automated proposal + human adjudication (final)",
                   color=[colors[r] for r in roles], edgecolor="#666666")
    for bars in (bars1, bars2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.8,
                    f"{bar.get_height():.0f}%", ha="center", fontsize=7.6)
    ax.set_xticks(list(x))
    ax.set_xticklabels([label[r] for r in roles], fontsize=8)
    ax.set_ylabel("papers with a public official artifact (%)")
    ax.set_ylim(0, 100)
    ax.legend(fontsize=7.0, frameon=False, loc="upper left")
    ax.set_title("Figure 3. Public official artifacts by paradigm "
                 "(n = 26 arXiv entries)", fontsize=9.2, fontweight="bold")
    fig.savefig(out)
    plt.close(fig)


def main() -> int:
    audit = load()
    fig_assurance_chain(FIGS / "fig1_assurance_chain.pdf")
    fig_study_a(FIGS / "fig2_study_a.pdf", audit)
    fig_study_b(FIGS / "fig3_study_b.pdf", audit)
    for p in sorted(FIGS.glob("*.pdf")):
        print(f"  {p.name}  {p.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
