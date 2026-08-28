"""
make_s4_dotplots.py: Additional file 4, one Top-2 dot-plot per theme, collected in one PDF
(one theme per page).

Built straight from the final results tables (Additional file 3), so every dot is the Top-2
percentage there exactly. Persona values are pooled across organisations from the underlying
counts (never a mean of organisation percentages); that pooling already happened in the
results tables. This is a descriptive picture only. No difference tests, p-values or
inferential comparisons are shown, and the exact counts and denominators stay in
Additional file 3.

Series per item: the applicable personas (Parents, Child respondents; or Care providers,
Intake coordinators) plus the pooled group (Families or Professionals). Reverse-scored items
use the same positive-direction labels and "(R)" marker as Figures 1-5.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUTDIR = ROOT / "outputs" / "figures" / "S4_pooled_dotplots"
PDF = OUTDIR / "Top2_dotplots.pdf"          # copied to supplement/ as Additional file 4
THEME_ORDER = ["Experience", "Overview/Insight", "Information exchange", "Control", "Effort"]

# reporting_unit in the results tables  ->  (legend label, marker, colour). Pooled Families and Pooled
# Professionals deliberately use different markers (X vs P).
SERIES = [
    ("Parents",             "Parents",               "o", "#1f77b4"),
    ("Child respondents",   "Child respondents",     "^", "#2ca02c"),
    ("Care providers",      "Care providers",        "s", "#ff7f0e"),
    ("Intake coordinators", "Intake coordinators",   "D", "#d62728"),
    ("Families",            "Families, pooled",      "X", "#4d4d4d"),
    ("Professionals",       "Professionals, pooled", "P", "#000000"),
]
FAM_PERSONAS = ["Parents", "Child respondents"]
PRO_PERSONAS = ["Care providers", "Intake coordinators"]
UNIT_SHORT = {"Families": "Fam", "Professionals": "Prof",
              "Care providers": "Care providers", "Intake coordinators": "Intake coordinators"}
# Themes that pool families vs professionals (Figures 1-3, bridge-paired order). Control and
# Effort are family-only (Figures 4-5, ordered by label).
GROUP_THEMES = {"Experience", "Overview/Insight", "Information exchange"}


def _label(row) -> str:
    lab = str(row["publication_label"]).strip()
    if str(row["reverse_scored"]).strip() == "Yes":
        lab = f"{lab} (R)"
    if str(row["item_id"]).startswith("FAM-"):
        u = "Families"
    else:
        ap = str(row["applicable_personas"]).strip()
        u = ap if ap in ("Care providers", "Intake coordinators") else "Professionals"
    return f"{UNIT_SHORT.get(u, u)}: {lab}"


def _theme_order(theme, ids, bridges):
    """Same item order as the main figures: bridge pairs adjacent (Family then Professional),
    then unbridged items; family-only themes are ordered by label."""
    if theme not in GROUP_THEMES:
        return ids  # already sorted by label in build_theme for the persona themes
    idset, used, order = set(ids), set(), []
    for _, b in bridges.iterrows():
        fam, pro = str(b["family_item_id"]).strip(), str(b["professional_item_id"]).strip()
        if fam in idset and pro in idset:
            order += [fam, pro]
            used |= {fam, pro}
    order += sorted(i for i in idset if i not in used and str(i).startswith("FAM-"))
    order += sorted(i for i in idset if i not in used and str(i).startswith("PRO-"))
    return order


def build_theme(theme, s3a, s3b, bridges):
    """Return [(label, {reporting_unit: top2_pct})] for every item in the theme, in figure order."""
    a = s3a[s3a["theme"] == theme].sort_values("publication_label", kind="stable")
    by_item = {r["item_id"]: r for _, r in a.iterrows()}
    rows = []
    for iid in _theme_order(theme, list(a["item_id"]), bridges):
        r = by_item[iid]
        grp = r["reporting_unit"]                         # Families or Professionals
        vals = {}
        for p in (FAM_PERSONAS if grp == "Families" else PRO_PERSONAS):
            pr = s3b[(s3b["item_id"] == iid) & (s3b["reporting_unit"] == p)]
            if not pr.empty:
                vals[p] = float(pr.iloc[0]["top2_pct"])
        vals[grp] = float(r["top2_pct"])                  # pooled group
        rows.append((_label(r), vals))
    return rows


def plot_theme(theme, rows, out, pdf):
    n = len(rows)
    LEFT, RIGHT = 0.42, 0.98                              # wide plot; labels fit on <=2 lines
    RATE, TOP_IN, BOT_IN = 0.45, 0.7, 1.7                 # constant scale; bottom holds x-label + legend + note
    fig_h = RATE * n + TOP_IN + BOT_IN
    fig, ax = plt.subplots(figsize=(15, fig_h))
    ys = list(range(n))[::-1]                             # first item at the top
    present = set()
    for y, (_, vals) in zip(ys, rows):
        for key, _disp, marker, colour in SERIES:
            if key in vals:
                ax.scatter(vals[key], y, marker=marker, s=95, color=colour,
                           edgecolor="white", linewidth=0.6, zorder=3)
                present.add(key)
    ax.set_yticks(ys)
    ax.set_yticklabels([textwrap.fill(r[0], 80) for r in rows], fontsize=10)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_xlim(-3, 103)                                  # a point at 0% or 100% is not clipped
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(axis="x", labelsize=10)
    ax.set_xlabel("% in the top two agreement categories (Top-2), among valid responses", fontsize=11)
    ax.set_title(f"{theme} — Top-2 agreement by persona and pooled group", fontsize=13)
    ax.grid(True, axis="x", linestyle="--", alpha=0.35)
    fig.subplots_adjust(left=LEFT, right=RIGHT, top=1 - TOP_IN / fig_h, bottom=BOT_IN / fig_h)
    # legend below the x-axis label (fixed inches from the bottom), centred, two rows if needed
    handles = [Line2D([0], [0], marker=m, linestyle="none", markerfacecolor=c,
                      markeredgecolor="white", markersize=11, label=disp)
               for key, disp, m, c in SERIES if key in present]
    ax.legend(handles=handles, frameon=False, loc="lower center",
              bbox_to_anchor=(0.5, 0.55 / fig_h), bbox_transform=fig.transFigure,
              ncol=min(3, len(handles)), fontsize=10, columnspacing=2.2, handletextpad=0.4)
    fig.text(0.5, 0.16 / fig_h,
             "Descriptive summary; each point is the Top-2 percentage among valid responses, "
             "pooled across organisations from the underlying counts. Exact counts and denominators are in Additional file 3.",
             ha="center", fontsize=8, style="italic")
    fig.savefig(out, dpi=300)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    if OUTDIR.exists():
        shutil.rmtree(OUTDIR)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    s3a = pd.read_csv(ROOT / "outputs" / "aggregate_item_results.csv")
    s3b = pd.read_csv(ROOT / "outputs" / "persona_specific_results.csv")
    bridges = pd.read_csv(ROOT / "metadata" / "bridge_matrix.csv")
    # CreationDate is left out so that rebuilding gives an identical file.
    with PdfPages(PDF, metadata={"CreationDate": None}) as pdf:
        for theme in THEME_ORDER:
            rows = build_theme(theme, s3a, s3b, bridges)
            if not rows:
                continue
            out = OUTDIR / f"S4_{theme.replace('/', '-').replace(' ', '_')}_Top2_dotplot.png"
            plot_theme(theme, rows, out, pdf)
            print(f"Saved {out.relative_to(ROOT)}")
    print(f"Saved {PDF.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
