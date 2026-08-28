"""
make_figures.py: Figures 1-5 for the manuscript, built from the final results tables
(Additional file 3), so figure values reproduce them after whole-number rounding.

Fig 1-3: pooled Families vs Professionals (Experience, Overview/Insight, Information exchange), from results table A.
Fig 4-5: Parents vs Child respondents (Control, Effort), from results table B.

Diverging 5-category Likert in a common positive direction: reverse-scored items are shown
so that "agree" (green, right) is the positive pole and are marked "(R)". Percentages are
among valid responses; N/A is shown at the right (% of eligible). Bar labels are whole
numbers; exact values are in Additional file 3.

The figures are drawn at their printed size, the BMC full-page width of 170 mm, so the font
sizes below are the sizes on the page. They carry no title: per the BMC submission
guidelines, figure titles and legends go in the manuscript, while the colour key stays in
the image. A layout check stops the build if any text is clipped or overlaps.
"""
from __future__ import annotations
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch
from matplotlib.textpath import TextPath
import pandas as pd

ROOT = Path(__file__).resolve().parent
FIGDIR = ROOT / "outputs" / "figures"
# Categories in administered-scale order (positions 1-5): Disagree, Somewhat disagree,
# Neutral, Somewhat agree, Agree. For reverse-scored items the position is the directional
# (positive) one, so agreement (green, right) is always the positive pole.
CATS = ["disagree", "somewhat_disagree", "neutral", "somewhat_agree", "agree"]
COLOR = {"disagree": "#d62728", "somewhat_disagree": "#ff9896", "neutral": "#7f7f7f",
         "somewhat_agree": "#98df8a", "agree": "#2ca02c"}
LEGEND = [Patch(facecolor=COLOR[c], edgecolor="white",
                label=c.replace("_", " ").capitalize()) for c in CATS]

# Print geometry (inches unless stated). RATE is identical in every figure, so bar thickness
# and the gaps between items are the same across Figures 1-5.
FIG_W_IN = 170 / 25.4      # BMC full-page width
FS = 6.5                   # item labels, persona names, axis text, colour key
FS_SMALL = 6.0             # numbers inside the bars and the N/A column
RATE = 0.28                # inches per y-unit
PAD_U = 0.6                # y-units above the first and below the last bar
TOP_IN, BOT_IN = 0.06, 0.62
EDGE_IN = 0.05             # outer margin
# The text columns are made as narrow as these line limits allow, so the bars get all the
# remaining width. Questions in Figures 4-5 sit beside two bars and have room for three lines.
LABEL_LINES = 2            # Figures 1-3: item labels
QUESTION_LINES = 3         # Figures 4-5: questions
GAP_IN = 0.08              # gap between the question column and the persona names
NA_OFFSET_PT = 3           # gap between the plot frame and the N/A column
TICK_IN = (plt.rcParams["ytick.major.size"] + plt.rcParams["ytick.major.pad"]) / 72
_FONT = FontProperties()


@lru_cache(maxsize=None)
def _advance(ch: str) -> float:
    """Advance width of one character at 1 pt (kerning ignored, hence the margin in _wrap)."""
    pair = TextPath((0, 0), "x" + ch + "x", size=100, prop=_FONT).get_extents().width
    base = TextPath((0, 0), "xx", size=100, prop=_FONT).get_extents().width
    return (pair - base) / 100


def _text_in(text: str, size: float) -> float:
    return 1.03 * size * sum(_advance(c) for c in text) / 72


def _wrap(text: str, width_in: float, size: float) -> str:
    """Greedy word wrap so that each line fits width_in at the given font size."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and _text_in(trial, size) > width_in:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return "\n".join(lines + [cur])


def _fit_column(texts, size, max_lines):
    """Narrowest column (inches) in which every text wraps to at most max_lines lines.
    Returns the column width and the wrapped texts."""
    lo, hi = 0.3, FIG_W_IN
    for _ in range(30):
        mid = (lo + hi) / 2
        if max(_wrap(t, mid, size).count("\n") + 1 for t in texts) <= max_lines:
            hi = mid
        else:
            lo = mid
    wrapped = [_balance(t, _wrap(t, hi, size).count("\n") + 1, size) for t in texts]
    return max(_text_in(line, size) for w in wrapped for line in w.split("\n")), wrapped


def _balance(text, n_lines, size):
    """Split text into n_lines lines of as even a width as possible (no lone last word)."""
    words = text.split()
    if n_lines <= 1 or len(words) <= 1:
        return text
    best, best_w = None, float("inf")
    for cuts in combinations(range(1, len(words)), n_lines - 1):
        bounds = (0, *cuts, len(words))
        lines = [" ".join(words[i:j]) for i, j in zip(bounds, bounds[1:])]
        w = max(_text_in(line, size) for line in lines)
        if w < best_w:
            best, best_w = lines, w
    return "\n".join(best)

# figure number, theme, mode, table, ordered reporting units
FIGSPEC = [
    (1, "Experience", "group", "S3A", ["Families", "Professionals"]),
    (2, "Overview/Insight", "group", "S3A", ["Families", "Professionals"]),
    (3, "Information exchange", "group", "S3A", ["Families", "Professionals"]),
    (4, "Control", "persona", "S3B", ["Child respondents", "Parents"]),
    (5, "Effort", "persona", "S3B", ["Child respondents", "Parents"]),
]
UNIT_SHORT = {"Families": "Fam", "Professionals": "Prof",
              "Care providers": "Care providers", "Intake coordinators": "Intake coordinators"}


def _item_label(row) -> str:
    lab = str(row["publication_label"]).strip()
    return f"{lab} (R)" if str(row["reverse_scored"]).strip() == "Yes" else lab


def _prof_unit(row) -> str:
    # subgroup-only professional items must not be labelled as all professionals
    ap = str(row["applicable_personas"]).strip()
    return ap if ap in ("Care providers", "Intake coordinators") else "Professionals"


def _draw_rail(ax, y, row, bar_h=0.72, label_min=6.0):  # label every segment >= 6%
    """Draw one diverging bar; return [(text, x0, x1)] for the labelled segments."""
    p1, p2, neu, p4, p5 = (float(row[f"{c}_pct"]) for c in CATS)  # positions 1-5
    half = neu / 2.0
    labelled = []
    segs = [(-half, half, COLOR[CATS[2]], neu),                        # neutral straddles 0
            (-half - p2, -half, COLOR[CATS[1]], p2),                   # somewhat disagree
            (-half - p2 - p1, -half - p2, COLOR[CATS[0]], p1),         # disagree (most negative)
            (half, half + p4, COLOR[CATS[3]], p4),                     # somewhat agree
            (half + p4, half + p4 + p5, COLOR[CATS[4]], p5)]           # agree (most positive)
    for x0, x1, col, val in segs:
        if x1 - x0 == 0:
            continue
        ax.barh(y, x1 - x0, left=x0, height=bar_h, color=col, edgecolor="white", linewidth=0.5)
        if val >= label_min:
            txt = ax.text((x0 + x1) / 2, y, f"{val:.0f}", ha="center", va="center",
                          fontsize=FS_SMALL, color="white")
            labelled.append((txt, x0, x1))
    na = row["nvt_pct"]
    if pd.notna(na):
        ax.annotate(f"N/A={float(na):.0f}%", xy=(1, y), xycoords=ax.get_yaxis_transform(),
                    xytext=(NA_OFFSET_PT, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=FS_SMALL)
    return labelled


def _check_layout(fig, ax, leg, questions, segments, name):
    """Stop the build if text comes within 1 mm of the image edge, overlaps other text, or a
    bar number is wider than its segment."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    m = fig.dpi / 25.4                                     # 1 mm in pixels
    box = lambda a: a.get_window_extent(r)
    ylabels = [t for t in ax.get_yticklabels() if t.get_text()]
    edge = [*ylabels, *questions, *ax.texts, ax.xaxis.label, leg]
    problems = [f"clipped: {a.get_text()[:40] if hasattr(a, 'get_text') else 'colour key'!r}"
                for a in edge if box(a).x0 < m or box(a).x1 > fig.bbox.width - m
                or box(a).y0 < m or box(a).y1 > fig.bbox.height - m]
    def clash(group, label):
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if box(a).overlaps(box(b)):
                    problems.append(f"{label}: {a.get_text()[:30]!r} / {b.get_text()[:30]!r}")
    clash(ylabels, "labels overlap")
    clash(questions + ylabels, "question overlaps persona name")
    for a in (ax.xaxis.label, *ax.get_xticklabels()):
        if box(leg).overlaps(box(a)):
            problems.append(f"colour key overlaps {a.get_text()!r}")
    for txt, x0, x1 in segments:
        seg_px = ax.transData.transform((x1, 0))[0] - ax.transData.transform((x0, 0))[0]
        if box(txt).width > seg_px:
            problems.append(f"number {txt.get_text()!r} wider than its segment")
    if problems:
        raise ValueError(f"{name} layout problems:\n  " + "\n  ".join(problems))


def build_figure(fignum, theme, mode, table, units, s3a, s3b, bridges):
    df = (s3a if table == "S3A" else s3b)
    df = df[df["theme"] == theme].copy()
    rails, yticks, ylabels, y = [], [], [], 0.0

    if mode == "group":
        # Bridged items are shown as adjacent Family/Professional pairs, in bridge order,
        # with a gap between bridges; standalones follow. Cross-theme bridges (partner in
        # another theme) fall through to standalones in this theme's figure.
        by_item = {r["item_id"]: r for _, r in df.iterrows()}
        used = set()
        seq = []  # ("pair", fam, pro) then ("solo", item, None)
        for _, b in bridges.iterrows():
            fam, pro = str(b["family_item_id"]).strip(), str(b["professional_item_id"]).strip()
            if fam in by_item and pro in by_item:
                seq.append(("pair", fam, pro))
                used |= {fam, pro}
        for i in sorted(x for x in by_item if x not in used and x.startswith("FAM-")):
            seq.append(("solo", i, None))
        for i in sorted(x for x in by_item if x not in used and x.startswith("PRO-")):
            seq.append(("solo", i, None))

        # Tight rail step within a pair; a small extra gap separates bridges/standalones.
        WITHIN, BETWEEN = 0.9, 0.45

        def add_rail(item_id, is_prof):
            nonlocal y
            row = by_item[item_id]
            u = _prof_unit(row) if is_prof else "Families"
            rails.append((y, row))
            yticks.append(y)
            ylabels.append(f"{UNIT_SHORT.get(u, u)}: {_item_label(row)}")
            y -= WITHIN

        first_solo = True
        for kind, a, c in seq:
            if kind == "pair":
                add_rail(a, False)            # Family item
                add_rail(c, True)             # bridged Professional item, adjacent
                y -= BETWEEN                  # small gap after the pair
            else:
                if first_solo:
                    y -= BETWEEN              # gap before the standalone block
                    first_solo = False
                add_rail(a, a.startswith("PRO-"))
    else:  # persona mode: per family item, one rail per persona, shared item label
        # Item order matches the earlier theme figures: family-only themes have no bridges,
        # so items are ordered by publication label. Persona rails within an item sit close
        # together; a wider gap separates items so each Parent/Child pair reads as one group.
        WITHIN, BETWEEN = 0.9, 0.45  # identical to the group figures' pair/gap spacing
        order = df.drop_duplicates("item_id").sort_values("publication_label")["item_id"].tolist()
        shared = []
        for it in order:
            ys = []
            for unit in units:
                row = df[(df["item_id"] == it) & (df["reporting_unit"] == unit)]
                if row.empty:
                    continue
                row = row.iloc[0]
                rails.append((y, row))
                yticks.append(y)
                ylabels.append(unit)
                ys.append(y)
                y -= WITHIN
            if ys:
                shared.append((sum(ys) / len(ys), _item_label(df[df["item_id"] == it].iloc[0])))
            y -= BETWEEN

    span = (yticks[0] - yticks[-1]) if yticks else 1.0
    fig_h = RATE * (span + 2 * PAD_U) + TOP_IN + BOT_IN
    if mode == "group":
        label_in, labels = _fit_column(ylabels, FS, LABEL_LINES)
        left_in = EDGE_IN + label_in + TICK_IN
    else:  # persona names on the axis, the shared question in a column to their left
        labels = [_balance(u, 2, FS) for u in ylabels]   # "Child respondents" on two lines
        name_in = max(_text_in(line, FS) for u in labels for line in u.split("\n"))
        question_in, questions_wrapped = _fit_column([lab for _, lab in shared], FS, QUESTION_LINES)
        left_in = EDGE_IN + question_in + GAP_IN + name_in + TICK_IN
    na_in = max((_text_in(f"N/A={float(r['nvt_pct']):.0f}%", FS_SMALL)
                 for _, r in rails if pd.notna(r["nvt_pct"])), default=0.0)
    right_in = NA_OFFSET_PT / 72 + na_in + EDGE_IN
    fig, ax = plt.subplots(figsize=(FIG_W_IN, fig_h))
    fig.subplots_adjust(left=left_in / FIG_W_IN, right=1 - right_in / FIG_W_IN,
                        top=1 - TOP_IN / fig_h, bottom=BOT_IN / fig_h)
    segments = []
    for yy, row in rails:
        segments += _draw_rail(ax, yy, row)
    ax.axvline(0, color="grey", lw=1, alpha=0.5, zorder=0)
    ax.set_yticks(yticks)
    ax.set_yticklabels(labels, fontsize=FS)
    ax.set_ylim(yticks[-1] - PAD_U, yticks[0] + PAD_U)
    ax.set_xlim(-101, 101)
    ax.set_xlabel("Valid-response distribution (%)", fontsize=FS)
    ax.tick_params(axis="both", labelsize=FS)
    ax.grid(True, axis="x", linestyle="--", alpha=0.3)
    questions = []
    if mode == "persona":
        ax_w_in = FIG_W_IN - left_in - right_in
        x = -(TICK_IN + name_in + GAP_IN) / ax_w_in          # right edge of the question column
        for (ymid, _), text in zip(shared, questions_wrapped):
            questions.append(ax.text(x, ymid, text,
                                     transform=ax.get_yaxis_transform(),
                                     ha="right", va="center", fontsize=FS, clip_on=False))
    # Colour key a fixed distance above the bottom edge, centred under the bars where it fits.
    leg = ax.legend(handles=LEGEND, frameon=False, loc="lower center", ncol=5, fontsize=FS,
                    handlelength=1.4, handletextpad=0.5, columnspacing=1.2,
                    bbox_to_anchor=(0.5, 0.06 / fig_h), bbox_transform=fig.transFigure)
    fig.canvas.draw()
    half = leg.get_window_extent().width / fig.dpi / 2
    centre = (left_in + FIG_W_IN - right_in) / 2
    centre = min(max(centre, EDGE_IN + half), FIG_W_IN - EDGE_IN - half)
    leg.set_bbox_to_anchor((centre / FIG_W_IN, 0.06 / fig_h), transform=fig.transFigure)
    out = FIGDIR / f"Figure_{fignum}_{theme.replace('/', '-').replace(' ', '_')}.png"
    _check_layout(fig, ax, leg, questions, segments, out.name)
    fig.savefig(out, dpi=300)  # ~300 dpi at the printed size, as BMC asks
    plt.close(fig)
    return out


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    s3a = pd.read_csv(ROOT / "outputs" / "aggregate_item_results.csv")
    s3b = pd.read_csv(ROOT / "outputs" / "persona_specific_results.csv")
    bridges = pd.read_csv(ROOT / "metadata" / "bridge_matrix.csv")
    for fignum, theme, mode, table, units in FIGSPEC:
        out = build_figure(fignum, theme, mode, table, units, s3a, s3b, bridges)
        print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
