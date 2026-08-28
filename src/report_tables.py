from __future__ import annotations

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.mapping import theme_from_bundle_id


PERSONA_ORDER = ["Ouders", "Jongeren", "Hulpverleners", "Aanmeldteam"]
THEME_ORDER = {
    "Experience": 1,
    "Overview/Insight": 2,
    #"Accessibility": 3,
    "Information exchange": 3,
    "Control": 4,
    "Effort": 5,
    #"Other": 99,
}

STANDOUT_MIN_N_VALID = 10
STANDOUT_MAX_PCT_NVT = 30.0


# -----------------------------
# Loading
# -----------------------------
def load_bridges(bridge_xlsx: str) -> pd.DataFrame:
    b = pd.read_excel(bridge_xlsx, sheet_name="Bridges").fillna("")
    b["bridge_row_order"] = np.arange(len(b))
    return b


def load_bundle_short_labels(bundle_xlsx: str) -> dict[str, str]:
    from src.labels import load_label_overrides
    df = pd.read_excel(bundle_xlsx, sheet_name="BundleMap").fillna("")
    ov = load_label_overrides()
    out: dict[str, str] = {}
    for _, r in df.iterrows():
        bid = str(r.get("bundle_id", "")).strip()
        lab = str(r.get("short_label_en", "")).strip()
        if bid and lab:
            out[bid] = ov.get(bid, lab)
    return out


def load_bundle_map(bundle_xlsx: str) -> pd.DataFrame:
    from src.labels import load_label_overrides
    bm = pd.read_excel(bundle_xlsx, sheet_name="BundleMap").fillna("")
    keep = ["bundle_id", "short_label_en", "reporting_label_en", "quant_in_main_table", "quant_in_appendix", "polarity"]
    keep = [c for c in keep if c in bm.columns]
    out = bm[keep].drop_duplicates().copy()
    ov = load_label_overrides()
    if "short_label_en" in out.columns:
        out["short_label_en"] = out.apply(
            lambda r: ov.get(str(r["bundle_id"]).strip(), r["short_label_en"]), axis=1)
    return out


# -----------------------------
# Shared helpers
# -----------------------------
def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def add_theme_cols(df: pd.DataFrame, bundle_col: str = "bundle_id") -> pd.DataFrame:
    out = df.copy()
    out["theme_label_en"] = out[bundle_col].apply(theme_from_bundle_id)
    out["theme_order"] = out["theme_label_en"].map(THEME_ORDER).fillna(99).astype(int)
    return out


def get_bridged_bundle_ids(bridges: pd.DataFrame) -> set[str]:
    fam = set(bridges["family_bundle_id"].astype(str).str.strip())
    pro = set(bridges["professional_bundle_id"].astype(str).str.strip())
    return fam | pro


def pool_orgs(likert_persona: pd.DataFrame) -> pd.DataFrame:
    s = likert_persona.copy()
    gcols = ["bundle_id", "persona", "group"]
    pooled = (
        s.groupby(gcols, dropna=False)
         .agg(
            n_total=("n_total", "sum"),
            n_valid=("n_valid", "sum"),
            n_nvt=("n_nvt", "sum"),
            n_dk=("n_dk", "sum"),
            top2_n=("top2_n", "sum"),
         )
         .reset_index()
    )
    pooled["pct_nvt"] = np.where(pooled["n_total"] > 0, pooled["n_nvt"] / pooled["n_total"] * 100, np.nan)
    pooled["pct_dk"] = np.where(pooled["n_total"] > 0, pooled["n_dk"] / pooled["n_total"] * 100, np.nan)
    pooled["pct_top2_valid"] = np.where(pooled["n_valid"] > 0, pooled["top2_n"] / pooled["n_valid"] * 100, np.nan)
    pooled["organization"] = "Pooled"
    return pooled


def collapse_within_group(df: pd.DataFrame, group_name: str) -> pd.DataFrame:
    sub = df[df["group"] == group_name].copy()
    if sub.empty:
        return sub

    pooled = (
        sub.groupby(["bundle_id", "group"], dropna=False)
           .agg(
               n_total=("n_total", "sum"),
               n_valid=("n_valid", "sum"),
               n_nvt=("n_nvt", "sum"),
               n_dk=("n_dk", "sum"),
               top2_n=("top2_n", "sum"),
           )
           .reset_index()
    )
    pooled["pct_nvt"] = np.where(pooled["n_total"] > 0, pooled["n_nvt"] / pooled["n_total"] * 100, np.nan)
    pooled["pct_dk"] = np.where(pooled["n_total"] > 0, pooled["n_dk"] / pooled["n_total"] * 100, np.nan)
    pooled["pct_top2_valid"] = np.where(pooled["n_valid"] > 0, pooled["top2_n"] / pooled["n_valid"] * 100, np.nan)
    pooled["persona"] = "Pooled"
    pooled["organization"] = "Pooled"
    return pooled


# -----------------------------
# Bridged tables
# -----------------------------
def make_bridge_appendix_table(
    bridges: pd.DataFrame,
    likert_by_persona: pd.DataFrame,
    short_lookup: dict[str, str],
) -> pd.DataFrame:
    pooled = pool_orgs(likert_by_persona)
    rows = []

    for _, b in bridges.iterrows():
        bridge_id = str(b["bridge_id"]).strip()
        fam_bid = str(b["family_bundle_id"]).strip()
        pro_bid = str(b["professional_bundle_id"]).strip()
        bridge_row_order = b.get("bridge_row_order", np.nan)

        theme_label_en = theme_from_bundle_id(fam_bid)
        theme_order = THEME_ORDER.get(theme_label_en, 99)

        fam_lab = short_lookup.get(fam_bid, fam_bid)
        pro_lab = short_lookup.get(pro_bid, pro_bid)

        for persona in ["Ouders", "Jongeren"]:
            sub = pooled[(pooled["bundle_id"] == fam_bid) & (pooled["persona"] == persona)]
            if sub.empty:
                continue
            r = sub.iloc[0]
            rows.append({
                "theme_order": theme_order,
                "theme_label_en": theme_label_en,
                "bridge_row_order": bridge_row_order,
                "bridge_id": bridge_id,
                "side": "Family",
                "persona": persona,
                "bundle_id": fam_bid,
                "short_label_en": fam_lab,
                "pct_top2_valid": r["pct_top2_valid"],
                "n_valid": r["n_valid"],
                "pct_nvt": r["pct_nvt"],
            })

        for persona in ["Hulpverleners", "Aanmeldteam"]:
            sub = pooled[(pooled["bundle_id"] == pro_bid) & (pooled["persona"] == persona)]
            if sub.empty:
                continue
            r = sub.iloc[0]
            rows.append({
                "theme_order": theme_order,
                "theme_label_en": theme_label_en,
                "bridge_row_order": bridge_row_order,
                "bridge_id": bridge_id,
                "side": "Professionals",
                "persona": persona,
                "bundle_id": pro_bid,
                "short_label_en": pro_lab,
                "pct_top2_valid": r["pct_top2_valid"],
                "n_valid": r["n_valid"],
                "pct_nvt": r["pct_nvt"],
            })

    out = pd.DataFrame(rows)
    out["persona"] = pd.Categorical(out["persona"], categories=PERSONA_ORDER, ordered=True)
    out = out.sort_values(
        ["theme_order", "bridge_row_order", "bridge_id", "side", "persona"],
        kind="stable"
    ).reset_index(drop=True)
    return out


def make_bridge_main_table_family_vs_prof(
    bridges: pd.DataFrame,
    likert_by_persona: pd.DataFrame,
    short_lookup: dict[str, str],
) -> pd.DataFrame:
    pooled = pool_orgs(likert_by_persona)
    rows = []

    def collapse(sub: pd.DataFrame) -> dict:
        if sub.empty:
            return dict(pct=np.nan, n=np.nan, pct_nvt=np.nan)
        n_total = sub["n_total"].sum()
        n_valid = sub["n_valid"].sum()
        n_nvt = sub["n_nvt"].sum()
        top2_n = sub["top2_n"].sum()
        pct = (top2_n / n_valid * 100) if n_valid > 0 else np.nan
        pct_nvt = (n_nvt / n_total * 100) if n_total > 0 else np.nan
        return dict(pct=pct, n=n_valid, pct_nvt=pct_nvt)

    for _, b in bridges.iterrows():
        bridge_id = str(b["bridge_id"]).strip()
        fam_bid = str(b["family_bundle_id"]).strip()
        pro_bid = str(b["professional_bundle_id"]).strip()
        bridge_row_order = b.get("bridge_row_order", np.nan)

        theme_label_en = theme_from_bundle_id(fam_bid)
        theme_order = THEME_ORDER.get(theme_label_en, 99)

        fam_lab = short_lookup.get(fam_bid, fam_bid)
        pro_lab = short_lookup.get(pro_bid, pro_bid)

        fam_sub = pooled[(pooled["bundle_id"] == fam_bid) & (pooled["group"] == "Family")]
        pro_sub = pooled[(pooled["bundle_id"] == pro_bid) & (pooled["group"] == "Professionals")]

        fam = collapse(fam_sub)
        pro = collapse(pro_sub)

        rows.append({
            "theme_order": theme_order,
            "theme_label_en": theme_label_en,
            "bridge_row_order": bridge_row_order,
            "bridge_id": bridge_id,
            "family_item_short_en": fam_lab,
            "professional_item_short_en": pro_lab,
            "family_pct_top2_valid": fam["pct"],
            "family_n_valid": fam["n"],
            "family_pct_nvt": fam["pct_nvt"],
            "professional_pct_top2_valid": pro["pct"],
            "professional_n_valid": pro["n"],
            "professional_pct_nvt": pro["pct_nvt"],
        })

    out = pd.DataFrame(rows)
    out = out.sort_values(["theme_order", "bridge_row_order", "bridge_id"], kind="stable").reset_index(drop=True)
    return out


# -----------------------------
# Standalone theme outputs (non-bridged)
# -----------------------------
def filter_theme_nonbridged_persona(
    bridges: pd.DataFrame,
    likert_by_persona: pd.DataFrame,
    theme_label_en: str,
) -> pd.DataFrame:
    bridged = get_bridged_bundle_ids(bridges)
    df = pool_orgs(likert_by_persona)
    df = add_theme_cols(df, "bundle_id")
    df = df[(df["theme_label_en"] == theme_label_en) & (~df["bundle_id"].astype(str).str.strip().isin(bridged))]
    return df


def make_theme_side_table(
    theme_persona_df: pd.DataFrame,
    bundle_map: pd.DataFrame,
    group_name: str,
    personas: list[str],
) -> pd.DataFrame:
    bm = bundle_map[["bundle_id", "short_label_en", "polarity"]].drop_duplicates()
    df = theme_persona_df.merge(bm, on="bundle_id", how="left")
    df = df[(df["group"] == group_name) & (df["persona"].isin(personas))].copy()

    pooled_side = collapse_within_group(theme_persona_df, group_name).merge(bm, on="bundle_id", how="left")
    out = pd.concat([df, pooled_side], ignore_index=True)

    persona_order = personas + ["Pooled"]
    out["persona"] = pd.Categorical(out["persona"], categories=persona_order, ordered=True)

    pooled_rows = out[out["persona"] == "Pooled"].copy()
    if not pooled_rows.empty:
        order = pooled_rows.sort_values("pct_top2_valid", ascending=True, kind="stable")["bundle_id"].tolist()
    else:
        order = out["bundle_id"].astype(str).unique().tolist()

    out["bundle_id"] = pd.Categorical(out["bundle_id"], categories=order, ordered=True)
    out = out.sort_values(["bundle_id", "persona"], kind="stable").reset_index(drop=True)
    return out


def make_theme_standouts_standalone(
    family_table: pd.DataFrame,
    prof_table: pd.DataFrame,
    theme_label_en: str,
    top_k: int = 3,
) -> pd.DataFrame:
    rows: list[dict] = []

    def pick(df: pd.DataFrame, side: str) -> None:
        pooled = df[df["persona"] == "Pooled"].copy()
        if pooled.empty:
            return
        pooled = pooled[
            (pooled["n_valid"].fillna(0) >= STANDOUT_MIN_N_VALID) &
            (pooled["pct_nvt"].fillna(0) <= STANDOUT_MAX_PCT_NVT)
        ].copy()
        if pooled.empty:
            return

        low = pooled.sort_values("pct_top2_valid", ascending=True).head(top_k)
        high = pooled.sort_values("pct_top2_valid", ascending=False).head(top_k)

        for _, r in low.iterrows():
            rows.append({
                "theme_label_en": theme_label_en,
                "side": side,
                "rule": "Lowest pooled Top-2",
                "bundle_id": r["bundle_id"],
                "short_label_en": r.get("short_label_en", ""),
                "pct_top2_valid": r["pct_top2_valid"],
                "n_valid": r["n_valid"],
                "pct_nvt": r["pct_nvt"],
            })

        for _, r in high.iterrows():
            rows.append({
                "theme_label_en": theme_label_en,
                "side": side,
                "rule": "Highest pooled Top-2",
                "bundle_id": r["bundle_id"],
                "short_label_en": r.get("short_label_en", ""),
                "pct_top2_valid": r["pct_top2_valid"],
                "n_valid": r["n_valid"],
                "pct_nvt": r["pct_nvt"],
            })

    pick(family_table, "Family")
    pick(prof_table, "Professionals")

    return pd.DataFrame(rows)


def plot_theme_standalone_two_panel(
    family_table: pd.DataFrame,
    prof_table: pd.DataFrame,
    theme_label_en: str,
    out_png: str,
    show_pooled: bool = True,
) -> None:
    def prep(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
        d = df.copy()
        order = d["bundle_id"].cat.categories.tolist() if hasattr(d["bundle_id"], "cat") else d["bundle_id"].tolist()
        y_map = {bid: i for i, bid in enumerate(order)}
        d["_y"] = d["bundle_id"].map(y_map)
        d["_label"] = d["short_label_en"].fillna(d["bundle_id"].astype(str))
        if "polarity" in d.columns:
            neg = d["polarity"].astype(str).str.strip() == "-"
            d.loc[neg, "_label"] = d.loc[neg, "_label"].astype(str) + " (R)"
        return d, order

    fam, fam_order = prep(family_table)
    pro, pro_order = prep(prof_table)

    fig_h = max(4.0, 0.35 * max(len(fam_order), len(pro_order)) + 1.8)
    fig, axes = plt.subplots(ncols=2, figsize=(14, fig_h), sharex=True)

    fam_personas = ["Ouders", "Jongeren"] + (["Pooled"] if show_pooled else [])
    pro_personas = ["Hulpverleners", "Aanmeldteam"] + (["Pooled"] if show_pooled else [])

    ax = axes[0]
    for persona in fam_personas:
        if persona not in fam["persona"].astype(str).unique():
            continue
        sub = fam[fam["persona"] == persona]
        ax.scatter(sub["pct_top2_valid"], sub["_y"], label=persona)
    ax.set_yticks(range(len(fam_order)))
    labels = []
    for bid in fam_order:
        sub = fam[(fam["bundle_id"] == bid) & (fam["persona"] == "Pooled")]
        if sub.empty:
            sub = fam[fam["bundle_id"] == bid].head(1)
        labels.append(sub["_label"].iloc[0] if not sub.empty else str(bid))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Top-2 box (%; directional)")
    ax.set_title(f"{theme_label_en} — Family")
    ax.legend(frameon=False, loc="lower right")

    ax = axes[1]
    for persona in pro_personas:
        if persona not in pro["persona"].astype(str).unique():
            continue
        sub = pro[pro["persona"] == persona]
        ax.scatter(sub["pct_top2_valid"], sub["_y"], label=persona)
    ax.set_yticks(range(len(pro_order)))
    labels = []
    for bid in pro_order:
        sub = pro[(pro["bundle_id"] == bid) & (pro["persona"] == "Pooled")]
        if sub.empty:
            sub = pro[pro["bundle_id"] == bid].head(1)
        labels.append(sub["_label"].iloc[0] if not sub.empty else str(bid))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Top-2 box (%; directional)")
    ax.set_title(f"{theme_label_en} — Professionals")
    handles, labels = ax.get_legend_handles_labels()
    if labels:
        ax.legend(frameon=False, loc="lower right")
    fig.suptitle(f"{theme_label_en}: Standalone items (non-bridged)", y=1.02)
    if any("(R)" in str(l) for l in (list(fam["_label"]) + list(pro["_label"]))):
        fig.text(0.01, 0.01,
                 "(R) = reverse-scored item (shown in the positive direction)",
                 fontsize=7, style="italic")
    fig.tight_layout()
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_theme_standalone_single_panel(
    side_table: pd.DataFrame,
    theme_label_en: str,
    side_title: str,
    out_png: str,
    show_pooled: bool = True,
) -> None:
    if side_table.empty:
        return

    d = side_table.copy()
    order = d["bundle_id"].cat.categories.tolist() if hasattr(d["bundle_id"], "cat") else d["bundle_id"].tolist()
    y_map = {bid: i for i, bid in enumerate(order)}
    d["_y"] = d["bundle_id"].map(y_map)
    d["_label"] = d["short_label_en"].fillna(d["bundle_id"].astype(str))
    if "polarity" in d.columns:
        neg = d["polarity"].astype(str).str.strip() == "-"
        d.loc[neg, "_label"] = d.loc[neg, "_label"].astype(str) + " (R)"

    fig_h = max(4.0, 0.35 * len(order) + 1.8)
    fig, ax = plt.subplots(figsize=(10, fig_h))

    if side_title == "Family":
        personas = ["Ouders", "Jongeren"] + (["Pooled"] if show_pooled else [])
    else:
        personas = ["Hulpverleners", "Aanmeldteam"] + (["Pooled"] if show_pooled else [])

    for persona in personas:
        if persona not in d["persona"].astype(str).unique():
            continue
        sub = d[d["persona"] == persona]
        ax.scatter(sub["pct_top2_valid"], sub["_y"], label=persona)

    ax.set_yticks(range(len(order)))
    labels = []
    for bid in order:
        sub = d[(d["bundle_id"] == bid) & (d["persona"] == "Pooled")]
        if sub.empty:
            sub = d[d["bundle_id"] == bid].head(1)
        labels.append(sub["_label"].iloc[0] if not sub.empty else str(bid))
    ax.set_yticklabels(labels)

    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Top-2 box (%; directional)")
    ax.set_title(f"{theme_label_en} — {side_title}")

    handles, labels = ax.get_legend_handles_labels()
    if labels:
        ax.legend(frameon=False, loc="lower right")

    if any("(R)" in str(l) for l in d["_label"]):
        fig.text(0.01, 0.01,
                 "(R) = reverse-scored item (shown in the positive direction)",
                 fontsize=7, style="italic")

    fig.tight_layout()
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def run_theme_outputs_standalones_two_panel(
    bridges: pd.DataFrame,
    likert_by_persona: pd.DataFrame,
    bundle_map: pd.DataFrame,
    out_root: str = "outputs/themes",
    top_k: int = 3,
    show_pooled: bool = True,
) -> None:
    ensure_dir(out_root)

    pooled = pool_orgs(likert_by_persona)
    pooled = add_theme_cols(pooled, "bundle_id")
    theme_labels = sorted([t for t in pooled["theme_label_en"].dropna().unique().tolist() if str(t).strip()])

    all_standouts = []

    for theme in theme_labels:
        theme_df = filter_theme_nonbridged_persona(bridges, likert_by_persona, theme)
        safe_theme = theme.replace("/", "-").replace(" ", "_")
        fam_tab = make_theme_side_table(
            theme_persona_df=theme_df,
            bundle_map=bundle_map,
            group_name="Family",
            personas=["Ouders", "Jongeren"],
        )
        pro_tab = make_theme_side_table(
            theme_persona_df=theme_df,
            bundle_map=bundle_map,
            group_name="Professionals",
            personas=["Hulpverleners", "Aanmeldteam"],
        )

        # Decide figure type based on availability
        if fam_tab.empty and not pro_tab.empty:
            plot_theme_standalone_single_panel(
                side_table=pro_tab,
                theme_label_en=theme,
                side_title="Professionals",
                out_png=f"{out_root}/theme_{safe_theme}_standalone_professionals.png",
                show_pooled=show_pooled,
            )
        elif pro_tab.empty and not fam_tab.empty:
            plot_theme_standalone_single_panel(
                side_table=fam_tab,
                theme_label_en=theme,
                side_title="Family",
                out_png=f"{out_root}/theme_{safe_theme}_standalone_family.png",
                show_pooled=show_pooled,
            )
        else:
            plot_theme_standalone_two_panel(
                family_table=fam_tab,
                prof_table=pro_tab,
                theme_label_en=theme,
                out_png=f"{out_root}/theme_{safe_theme}_standalone_panel.png",
                show_pooled=show_pooled,
            )
    
        safe_theme = theme.replace("/", "-").replace(" ", "_")

        fam_tab.to_csv(f"{out_root}/theme_{safe_theme}_family_table.csv", index=False)
        pro_tab.to_csv(f"{out_root}/theme_{safe_theme}_professionals_table.csv", index=False)

        stand = make_theme_standouts_standalone(fam_tab, pro_tab, theme_label_en=theme, top_k=top_k)
        stand.to_csv(f"{out_root}/theme_{safe_theme}_standouts.csv", index=False)
        all_standouts.append(stand)

        plot_theme_standalone_two_panel(
            family_table=fam_tab,
            prof_table=pro_tab,
            theme_label_en=theme,
            out_png=f"{out_root}/theme_{safe_theme}_standalone_panel.png",
            show_pooled=show_pooled,
        )

    if all_standouts:
        pd.concat(all_standouts, ignore_index=True).to_csv(f"{out_root}/theme_all_standouts.csv", index=False)

def build_bundle_to_bridge_id_map(bridges: pd.DataFrame) -> dict[str, str]:
    m = {}
    for _, b in bridges.iterrows():
        bid = str(b.get("bridge_id", "")).strip()
        fam = str(b.get("family_bundle_id", "")).strip()
        pro = str(b.get("professional_bundle_id", "")).strip()
        if bid:
            if fam:
                m[fam] = bid
            if pro:
                m[pro] = bid
    return m

def make_theme_pooled_persona_table(
    likert_by_persona: pd.DataFrame,
    bundle_map: pd.DataFrame,
    bridges: pd.DataFrame,
    theme_label_en: str,
) -> pd.DataFrame:
    """
    Returns persona-level pooled table for a single theme, with labels and theme ordering.
    Output columns:
    bundle_id,persona,group,n_total,n_valid,n_nvt,n_dk,top2_n,pct_nvt,pct_dk,pct_top2_valid,
    organization,theme_label_en,theme_order,short_label_en
    """
    # pool across orgs (keeps persona + group)
    pooled = pool_orgs(likert_by_persona)
    pooled = add_theme_cols(pooled, "bundle_id")  # adds theme_label_en + theme_order

    # filter to theme
    df = pooled[pooled["theme_label_en"] == theme_label_en].copy()

    # attach short labels
    bm = bundle_map[["bundle_id", "short_label_en"]].drop_duplicates()
    df = df.merge(bm, on="bundle_id", how="left")

    bundle_to_bridge = build_bundle_to_bridge_id_map(bridges)

    bridge_order_map = (
        bridges[["bridge_id", "bridge_row_order"]]
        .assign(bridge_id=lambda x: x["bridge_id"].astype(str).str.strip())
        .drop_duplicates()
        .set_index("bridge_id")["bridge_row_order"]
        .to_dict()
    )

    df["bridge_id"] = df["bundle_id"].astype(str).str.strip().map(bundle_to_bridge).fillna("")
    df["is_bridged"] = df["bridge_id"].astype(str).str.len() > 0
    df["bridge_row_order"] = df["bridge_id"].map(bridge_order_map).fillna(999999).astype(int)
    df["persona"] = pd.Categorical(df["persona"], categories=PERSONA_ORDER, ordered=True)

    df = df.sort_values(
        ["is_bridged", "bridge_row_order", "bundle_id", "group", "persona"],
        ascending=[False, True, True, True, True],
        kind="stable",
    ).reset_index(drop=True)
    
    # enforce column order
    cols = [
        "bridge_id",
        "bundle_id",
        "persona",
        "group",
        "n_total",
        "n_valid",
        "n_nvt",
        "n_dk",
        "top2_n",
        "pct_nvt",
        "pct_dk",
        "pct_top2_valid",
        "organization",
        "theme_label_en",
        "theme_order",
        "short_label_en",
        "is_bridged",
        "bridge_row_order",
    ]
    cols = [c for c in cols if c in df.columns]
    df = df[cols].copy()

    # sort 
#    if "persona" in df.columns:
#        df["persona"] = pd.Categorical(df["persona"], categories=PERSONA_ORDER, ordered=True)
#    df = df.sort_values(["theme_order", "bundle_id", "group", "persona"], kind="stable").reset_index(drop=True)

    return df