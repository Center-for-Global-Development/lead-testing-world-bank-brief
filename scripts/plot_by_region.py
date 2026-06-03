#!/usr/bin/env python3
"""
Horizontal bar chart of active WB water supply / sanitation projects by
world region, with each region's $ commitment stacked by financing type
(IBRD loans / IDA credits / grants).

Inputs:  outputs/audit/portfolio_audit_with_region.csv
Outputs: outputs/audit/projects_by_region.png / .svg
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "outputs" / "audit" / "portfolio_audit_with_region.csv"
PNG = ROOT / "outputs" / "audit" / "projects_by_region.png"
SVG = ROOT / "outputs" / "audit" / "projects_by_region.svg"

SHORT = {
    "Eastern and Southern Africa": "East/Southern Africa",
    "Western and Central Africa":  "West/Central Africa",
    "Latin America and Caribbean": "Latin America & Caribbean",
    # WB's "MENAAP" region — Afghanistan and Pakistan were moved here from
    # South Asia in 2023. Shortened to "Middle East & N. Africa" for the
    # chart axis; the AFG/PAK detail is mentioned in the blog text.
    "Middle East, North Africa, Afghanistan, and Pakistan": "Middle East & N. Africa",
    "Europe and Central Asia":     "Europe & Central Asia",
    "South Asia":                  "South Asia",
    "East Asia and Pacific":       "East Asia & Pacific",
}

# CGD Data Visualization Style Guide v03 (4.4.23) — categorical palette.
# Standard order is Light Teal → Gold → Blue. Mapping by category size:
#   IBRD  (largest, default)            → Light Teal  #006970
#   IDA   (middle)                      → Blue        #2D99B5
#   Grant (smallest, draws attention)   → Gold        #FFB52C
COLORS = {"IBRD": "#006970", "IDA": "#2D99B5", "Grant": "#FFB52C"}

# Other guide-approved colors used for axes / text
TEAL_BLACK = "#1A272A"   # axis lines
TEAL       = "#0B4C5B"   # title and axis labels
LIGHT_GRAY = "#DFE0E2"   # neutrals if needed


def safe_float(x: str) -> float:
    try:
        return float(x or 0)
    except ValueError:
        return 0.0


def main() -> int:
    rows = [r for r in csv.DictReader(SRC.open()) if r["region"] != "Unknown"]

    # The chart shows the WATER-ATTRIBUTABLE share of each project's
    # financing mix, not the full project value. Multi-sector projects
    # have water as one component of a larger budget — only the water
    # share is relevant for a piece about lead in drinking water.
    #
    # For each project we scale the IBRD / IDA / grant amounts by the
    # ratio of weighted_commitment_usd (water-attributable) to
    # commitment_usd (full). The bars then sum to the same total as
    # the audit's weighted headline figure.
    by_region = defaultdict(lambda: {"IBRD": 0.0, "IDA": 0.0, "Grant": 0.0,
                                     "n": 0, "audit_total": 0.0})
    for r in rows:
        reg = r["region"]
        full = safe_float(r.get("commitment_usd"))
        weighted = safe_float(r.get("weighted_commitment_usd"))
        share = (weighted / full) if full > 0 else 0.0
        by_region[reg]["IBRD"]  += safe_float(r.get("ibrd_amount"))  * share
        by_region[reg]["IDA"]   += safe_float(r.get("ida_amount"))   * share
        by_region[reg]["Grant"] += safe_float(r.get("grant_amount")) * share
        by_region[reg]["n"]     += 1
        by_region[reg]["audit_total"] += weighted

    # Sort regions by total commitment (sum of stacks), descending
    regions = sorted(by_region,
                     key=lambda r: by_region[r]["IBRD"] + by_region[r]["IDA"]
                                   + by_region[r]["Grant"],
                     reverse=True)
    labels = [SHORT.get(r, r) for r in regions]

    fig, ax = plt.subplots(figsize=(8.0, 4.6))

    bottoms = [0.0] * len(regions)
    # Legend labels: IBRD/IDA carry a parenthetical because the acronyms aren't
    # self-explanatory; Grant stands on its own.
    LEGEND = {"IBRD": "IBRD (loan)", "IDA": "IDA (credit)", "Grant": "Grant"}
    for kind in ["IBRD", "IDA", "Grant"]:
        heights = [by_region[r][kind] / 1e9 for r in regions]
        ax.barh(labels, heights, left=bottoms, color=COLORS[kind],
                label=LEGEND[kind],
                edgecolor="white", linewidth=0.6)
        bottoms = [b + h for b, h in zip(bottoms, heights)]

    ax.invert_yaxis()
    ax.set_xlabel("Water-attributable commitment, $ billion",
                  color=TEAL, fontsize=11)
    # x-axis label already says "$ billion" — keep tick labels as plain numbers
    ax.xaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f"))
    # Per CGD guide: remove tick marks; keep tick labels (they identify the
    # data) but strip the small marks themselves to reduce non-data ink.
    ax.tick_params(axis="both", length=0, colors=TEAL_BLACK)
    # Per CGD guide: avoid grids unless needed for clarity.
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(TEAL_BLACK)
    ax.spines["left"].set_color(TEAL_BLACK)

    # End-of-bar totals
    max_total = max(bottoms)
    for i, r in enumerate(regions):
        total = bottoms[i]
        n = by_region[r]["n"]
        ax.text(total + max_total * 0.012, i,
                f"${total:.1f}B  ({n} projects)",
                va="center", ha="left", fontsize=9)

    # Extend x-axis a bit so labels fit
    ax.set_xlim(0, max_total * 1.13)

    # Horizontal legend above the chart (between title and bars), mirroring
    # the stacking order of the bars (left-to-right reads the same as the
    # colour ordering inside each bar).
    leg = ax.legend(title="Financing type",
                    loc="lower center", bbox_to_anchor=(0.5, 1.02),
                    ncol=3, frameon=False, fontsize=9,
                    columnspacing=2.0, handletextpad=0.5)
    leg.get_title().set_color(TEAL)

    # Title aligned with the figure's left edge (i.e. with the region labels),
    # not with the axes' left edge (where the bars start). Anchored just above
    # the axes via a small pad so the gap stays tight.
    ax.text(0.0, 1.0,
            "World Bank Active Water-Supply Portfolio:\n"
            "Share by region and financing type",
            transform=fig.transFigure, ha="left", va="top",
            fontsize=13, fontweight="bold", color=TEAL)
    # No footnote — the descriptive caption is added downstream of the figure.
    fig.tight_layout(rect=(0, 0.0, 1, 0.92))
    # Pull the axes up but leave room above for the horizontal legend that
    # sits between title and chart.
    pos = ax.get_position()
    ax.set_position([pos.x0, pos.y0, pos.width, 0.80 - pos.y0])

    fig.savefig(PNG, dpi=200, bbox_inches="tight")
    fig.savefig(SVG, bbox_inches="tight")
    print(f"Wrote {PNG}")
    print(f"Wrote {SVG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
