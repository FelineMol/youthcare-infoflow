"""Build the publication files from the verified summaries + mapping (no recomputation
from raw, so numbers reconcile with the pipeline): metadata/item_dictionary.csv,
metadata/bridge_matrix.csv (Additional file 2), outputs/aggregate_item_results.csv and
outputs/persona_specific_results.csv (Additional file 3, sheets A and B),
supplement/Additional_file_3_column_dictionary.csv and supplement/Additional_file_5_codebook.csv.
Percentages are
rounded to 2 dp; exact values stay in the integer count columns. Conventions: see
ANALYSIS_DECISIONS.md.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

from src.config import ProjectPaths
from src.mapping import theme_from_bundle_id

# Internal Dutch persona keys -> publication-facing English labels
PERSONA_DISPLAY = {
    "Ouders": "Parents",
    "Jongeren": "Child respondents",
    "Hulpverleners": "Care providers",
    "Aanmeldteam": "Intake coordinators",
}
GROUP_DISPLAY = {"Family": "Families", "Professionals": "Professionals"}

BRIDGE_INTERPRETATION_NOTE = (
    "Items address conceptually related information practices from different "
    "stakeholder positions. They were not necessarily worded identically and "
    "should not be interpreted as direct mirror items."
)


def _load_bundle_map(paths: ProjectPaths) -> pd.DataFrame:
    from src.labels import load_label_overrides
    p = paths.data_mapping / "intermediate_bundle_mapping_table_v6.xlsx"
    df = pd.read_excel(p, sheet_name="BundleMap").fillna("")
    ov = load_label_overrides()
    if "short_label_en" in df.columns:
        df["short_label_en"] = df.apply(
            lambda r: ov.get(str(r["bundle_id"]).strip(), r["short_label_en"]), axis=1)
    return df


def _reverse_coded(polarity: str) -> str:
    return "Yes" if str(polarity).strip() == "-" else "No"


def _personas_display(personas_in_bundle: str) -> str:
    parts = [p.strip() for p in str(personas_in_bundle).split(",") if p.strip()]
    return ", ".join(PERSONA_DISPLAY.get(p, p) for p in parts)


# ---------------------------------------------------------------------------
# metadata/item_dictionary.csv  (item backbone + data dictionary)
# ---------------------------------------------------------------------------
def build_item_dictionary(paths: ProjectPaths) -> pd.DataFrame:
    bm = _load_bundle_map(paths)
    rows = []
    for _, r in bm.iterrows():
        bid = str(r["bundle_id"]).strip()
        if not bid:
            continue
        rows.append({
            "item_id": bid,
            "scale_type": str(r.get("scale_type", "")).strip(),
            "theme": theme_from_bundle_id(bid),
            "polarity": str(r.get("polarity", "")).strip(),
            "reverse_coded": _reverse_coded(r.get("polarity", "")),
            "personas": _personas_display(r.get("personas_in_bundle", "")),
            "short_label_en": str(r.get("short_label_en", "")).strip(),
            "wording_nl_parents": str(r.get("Ouders_header_nl", "")).strip(),
            "wording_nl_children": str(r.get("Jongeren_header_nl", "")).strip(),
            "wording_nl_care_providers": str(r.get("Hulpverleners_header_nl", "")).strip(),
            "wording_nl_intake_coordinators": str(r.get("Aanmeldteam_header_nl", "")).strip(),
        })
    dict_df = pd.DataFrame(rows)

    # Open-text items (prompts) from analysis_long (the OPEN:: bundle_ids are the prompts)
    al_path = paths.outputs / "analysis_long.csv"
    if al_path.exists():
        al = pd.read_csv(al_path)
        op = al[al["scale_type"] == "Open"].copy()
        if not op.empty:
            from run_build_open_question_tables import map_theme_from_open_bundle
            op["prompt"] = op["bundle_id"].str.replace("OPEN::", "", regex=False)
            grp = (op.groupby("prompt")["persona"]
                     .apply(lambda s: ", ".join(PERSONA_DISPLAY.get(x, x)
                                                for x in sorted(s.unique())))
                     .reset_index())
            open_rows = [{
                "item_id": f"OPEN::{r['prompt']}",
                "scale_type": "Open",
                "theme": map_theme_from_open_bundle(r["prompt"]),
                "polarity": "",
                "reverse_coded": "No",
                "personas": r["persona"],
                "short_label_en": "",
                "wording_nl_parents": "",
                "wording_nl_children": "",
                "wording_nl_care_providers": "",
                "wording_nl_intake_coordinators": "",
                "open_prompt_nl": r["prompt"],
            } for _, r in grp.iterrows()]
            dict_df = pd.concat([dict_df, pd.DataFrame(open_rows)], ignore_index=True)
    if "open_prompt_nl" not in dict_df.columns:
        dict_df["open_prompt_nl"] = ""
    return dict_df


# ---------------------------------------------------------------------------
# metadata/bridge_matrix.csv  (Additional file 2)
# ---------------------------------------------------------------------------
def build_bridge_matrix(paths: ProjectPaths) -> pd.DataFrame:
    bridges = pd.read_excel(
        paths.data_mapping / "bridge_map_with_workload_links_v08.xlsx",
        sheet_name="Bridges",
    ).fillna("")
    bm = _load_bundle_map(paths)
    personas = {str(r["bundle_id"]).strip(): str(r.get("personas_in_bundle", "")).strip()
                for _, r in bm.iterrows()}
    labels = {str(r["bundle_id"]).strip(): str(r.get("short_label_en", "")).strip()
              for _, r in bm.iterrows()}

    rows = []
    for _, b in bridges.iterrows():
        fam = str(b["family_bundle_id"]).strip()
        pro = str(b["professional_bundle_id"]).strip()
        fam_theme = theme_from_bundle_id(fam)
        pro_theme = theme_from_bundle_id(pro)
        cross = fam_theme != pro_theme
        rows.append({
            "theme": fam_theme,
            "bridge_id": str(b["bridge_id"]).strip(),
            "confidence": str(b.get("confidence", "")).strip(),
            "family_item_id": fam,
            "family_theme": fam_theme,
            "family_personas": _personas_display(personas.get(fam, "")),
            "family_item_short_en": labels.get(fam, fam),
            "family_reverse_coded": _reverse_coded(b.get("family_polarity", "")),
            "professional_item_id": pro,
            "professional_theme": pro_theme,
            "professional_personas": _personas_display(personas.get(pro, "")),
            "professional_item_short_en": labels.get(pro, pro),
            "professional_reverse_coded": _reverse_coded(b.get("professional_polarity", "")),
            "relationship": "Conceptually bridged",
            "cross_theme": "Yes" if cross else "No",
            "cross_theme_note": (f"Family item classified under {fam_theme}; professional item under {pro_theme}."
                                 if cross else ""),
            "applicable_reporting": "Pooled descriptive and/or persona-specific",
            "interpretation_note": BRIDGE_INTERPRETATION_NOTE,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Results tables A / B  descriptive Likert results (computed directly from analysis_long, so
# eligible = valid + N/A + DK + missing + non-Likert reconciles exactly).
# Categories keep the directional (reverse-scored) coding; Top-2 is positively oriented.
# ---------------------------------------------------------------------------
# Category names match the administered anchors: 1 "Mee oneens" (Disagree), 2 "Enigszins
# mee oneens" (Somewhat disagree), 3 "Neutraal" (Neutral), 4 "Enigszins mee eens" (Somewhat
# agree), 5 "Mee eens" (Agree). Directional coding applies, so for reverse-scored items the
# label reflects the positive-direction position, not the raw text.
_CAT = {1: "disagree", 2: "somewhat_disagree", 3: "neutral", 4: "somewhat_agree", 5: "agree"}
_PCT_DP = 2


def _analysis_long_likert(paths: ProjectPaths) -> pd.DataFrame:
    al = pd.read_csv(paths.outputs / "analysis_long.csv")
    al = al[al["scale_type"].astype(str).str.strip().str.lower() == "likert"].copy()
    al["rn"] = pd.to_numeric(al["response_num_directional"], errors="coerce")
    al["rawnum"] = pd.to_numeric(al["response_num"], errors="coerce")  # original (administered) direction
    al["raw"] = al["response_raw"].fillna("").astype(str).str.strip()
    al["nvt"] = al["flag_nvt"].astype(str).str.strip().str.lower().eq("true")
    al["dk"] = al["flag_dk"].astype(str).str.strip().str.lower().eq("true")
    return al


def _accounting(g: pd.DataFrame) -> dict:
    valid = g["rn"].notna()
    blank = g["raw"].eq("") & ~g["nvt"] & ~g["dk"]
    non_likert = ~valid & ~g["nvt"] & ~g["dk"] & ~blank   # e.g. Levvel-child duration answers
    present = [o for o in ("N=YOU", "Levvel") if (g["organization"] == o).any()]
    d = {"orgs_included": " + ".join({"N=YOU": "N=You", "Levvel": "Levvel"}[o] for o in present),
         "eligible_n": len(g), "valid_n": int(valid.sum()),
         "nvt_n": int(g["nvt"].sum()), "dk_n": int(g["dk"].sum()),
         "missing_n": int(blank.sum()), "non_likert_excluded_n": int(non_likert.sum())}
    for k, name in _CAT.items():
        d[f"{name}_n"] = int((g["rn"] == k).sum())
    d["top2_n"] = d["somewhat_agree_n"] + d["agree_n"]           # positively-oriented Top-2 (positions 4+5)
    d["agree_original_direction_n"] = int(g["rawnum"].isin([4, 5]).sum())  # agree in administered direction
    return d


def _aggregate(al: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for kv, g in al.groupby(keys, dropna=False):
        rec = dict(zip(keys, kv if isinstance(kv, tuple) else (kv,)))
        rec.update(_accounting(g))
        rows.append(rec)
    return pd.DataFrame(rows)


def _meta_lookups(paths: ProjectPaths):
    bm = _load_bundle_map(paths)  # short_label_en is already override-applied (publication label)
    lab = {str(r["bundle_id"]).strip(): str(r.get("short_label_en", "")).strip() for _, r in bm.iterrows()}
    pol = {str(r["bundle_id"]).strip(): str(r.get("polarity", "")).strip() for _, r in bm.iterrows()}
    per = {str(r["bundle_id"]).strip(): _personas_display(r.get("personas_in_bundle", "")) for _, r in bm.iterrows()}
    return lab, pol, per


def _decorate(g: pd.DataFrame, lab, pol, per) -> pd.DataFrame:
    g = g.copy()
    g["item_id"] = g["bundle_id"]
    g["theme"] = g["bundle_id"].apply(theme_from_bundle_id)
    g["publication_label"] = g["bundle_id"].map(lab)
    g["original_direction"] = g["bundle_id"].map(pol)
    g["reverse_scored"] = g["original_direction"].apply(lambda p: "Yes" if str(p).strip() == "-" else "No")
    g["applicable_personas"] = g["bundle_id"].map(per)
    for name in _CAT.values():
        g[f"{name}_pct"] = np.where(g["valid_n"] > 0, g[f"{name}_n"] / g["valid_n"] * 100, np.nan).round(_PCT_DP)
    g["top2_pct"] = np.where(g["valid_n"] > 0, g["top2_n"] / g["valid_n"] * 100, np.nan).round(_PCT_DP)
    g["agree_original_direction_pct"] = np.where(
        g["valid_n"] > 0, g["agree_original_direction_n"] / g["valid_n"] * 100, np.nan).round(_PCT_DP)
    g["nvt_pct"] = np.where(g["eligible_n"] > 0, g["nvt_n"] / g["eligible_n"] * 100, np.nan).round(_PCT_DP)
    return g


_OUT_COLS = ["theme", "item_id", "publication_label", "original_direction", "reverse_scored",
             "applicable_personas", "reporting_unit", "orgs_included", "reporting_unit_n",
             "eligible_n", "valid_n", "nvt_n", "nvt_pct", "dk_n", "missing_n", "non_likert_excluded_n",
             "disagree_n", "disagree_pct", "somewhat_disagree_n", "somewhat_disagree_pct",
             "neutral_n", "neutral_pct", "somewhat_agree_n", "somewhat_agree_pct",
             "agree_n", "agree_pct",
             "top2_n", "top2_pct",
             "agree_original_direction_n", "agree_original_direction_pct", "cross_org_note"]

# Items whose two organisations used materially different wording; matched and pooled after a
# manual wording check (see ANALYSIS_DECISIONS, "Questionnaire differences between the two
# organisations").
_HARMONISED = {"FAM-REG-c", "FAM-REG-d", "PRO-OVZ-a"}
_HARMONISED_NOTE = "minor wording variation harmonised across organisations for pooling"


def _reporting_unit_n(paths: ProjectPaths) -> dict:
    """Total analysed respondents per persona and per group (the full denominator)."""
    al = pd.read_csv(paths.outputs / "analysis_long.csv")
    resp = al.drop_duplicates(["organization", "persona", "respondent_id"])
    n = {PERSONA_DISPLAY.get(p, p): int(c) for p, c in resp.groupby("persona")["respondent_id"].size().items()}
    n.update({GROUP_DISPLAY.get(g, g): int(c) for g, c in resp.groupby("group")["respondent_id"].size().items()})
    return n


def _add_org_context(df: pd.DataFrame, unit_n: dict) -> None:
    df["reporting_unit_n"] = df["reporting_unit"].astype(str).map(unit_n)
    df["cross_org_note"] = df["item_id"].astype(str).apply(
        lambda i: _HARMONISED_NOTE if i in _HARMONISED else "")


_S3_DICT = {
    "theme": "Theme the item belongs to.",
    "item_id": "Stable item identifier, shared with Additional files 1 and 2.",
    "publication_label": "Item statement in the positive (agreement) direction; reverse-scored items are relabelled and marked (R).",
    "original_direction": "Polarity as administered: + positive, - negative (reverse-scored).",
    "reverse_scored": "Yes if the item was worded negatively and recoded so that higher means more positive.",
    "applicable_personas": "Personas the item was put to.",
    "reporting_unit": "The persona or pooled group this row summarises.",
    "orgs_included": "Which organisations contributed rows for this reporting_unit (N=You + Levvel, N=You, or Levvel).",
    "reporting_unit_n": "Total analysed respondents in this persona or group (the full denominator).",
    "eligible_n": "Respondents in this reporting_unit who were asked the item; below reporting_unit_n when only one organisation asked it.",
    "valid_n": "Eligible respondents who gave a Likert rating 1-5 (the denominator for the percentages).",
    "nvt_n": "Chose 'not applicable'.", "nvt_pct": "'Not applicable' as % of eligible.",
    "dk_n": "Chose 'don't know'.", "missing_n": "Left the item blank.",
    "non_likert_excluded_n": "Gave a non-Likert answer excluded from valid (e.g. a duration option).",
    "disagree_n": "Count in 'disagree' (position 1, positive direction).", "disagree_pct": "As % of valid_n.",
    "somewhat_disagree_n": "Count in 'somewhat disagree' (2).", "somewhat_disagree_pct": "As % of valid_n.",
    "neutral_n": "Count in 'neutral' (3).", "neutral_pct": "As % of valid_n.",
    "somewhat_agree_n": "Count in 'somewhat agree' (4).", "somewhat_agree_pct": "As % of valid_n.",
    "agree_n": "Count in 'agree' (5).", "agree_pct": "As % of valid_n.",
    "top2_n": "Count in the top two agreement categories (somewhat agree + agree).",
    "top2_pct": "Top-2 as % of valid_n (the headline statistic).",
    "agree_original_direction_n": "Agreement in the administered direction; differs from Top-2 for reverse-scored items.",
    "agree_original_direction_pct": "As % of valid_n.",
    "cross_org_note": "Note for items whose two organisations' wording was harmonised for descriptive pooling.",
}


def build_s3_dictionary() -> pd.DataFrame:
    rows = [{"column": c, "description": _S3_DICT.get(c, "")} for c in _OUT_COLS]
    rows.append({"column": "(reconciliation)",
                 "description": "eligible_n = valid_n + nvt_n + dk_n + missing_n + non_likert_excluded_n."})
    return pd.DataFrame(rows)


def build_s3(paths: ProjectPaths):
    al = _analysis_long_likert(paths)
    lab, pol, per = _meta_lookups(paths)
    unit_n = _reporting_unit_n(paths)

    a = _decorate(_aggregate(al, ["bundle_id", "group"]), lab, pol, per)
    a["reporting_unit"] = a["group"].map(GROUP_DISPLAY)
    _add_org_context(a, unit_n)
    s3a = a[_OUT_COLS].sort_values(["theme", "item_id", "reporting_unit"], kind="stable").reset_index(drop=True)

    b = _decorate(_aggregate(al, ["bundle_id", "persona", "group"]), lab, pol, per)
    b["reporting_unit"] = b["persona"].map(PERSONA_DISPLAY)
    _add_org_context(b, unit_n)
    order = ["Parents", "Child respondents", "Care providers", "Intake coordinators"]
    b["reporting_unit"] = pd.Categorical(b["reporting_unit"], categories=order, ordered=True)
    s3b = b[_OUT_COLS].sort_values(["theme", "item_id", "reporting_unit"], kind="stable").reset_index(drop=True)

    for name, df in [("results A", s3a), ("results B", s3b)]:
        recon = df["valid_n"] + df["nvt_n"] + df["dk_n"] + df["missing_n"] + df["non_likert_excluded_n"]
        bad = df[recon != df["eligible_n"]]
        if len(bad):
            raise ValueError(f"{name}: eligible_n does not reconcile for {sorted(bad['item_id'].unique())}")
    return s3a, s3b


# ---------------------------------------------------------------------------
# Results table C, persona divergence: for each item, how far the two personas in a group sit apart.
# Compared on positively-oriented Top-2 (%) and on the directional 1-5 mean (higher = more
# positive). Items are flagged when both summaries move together and cells are not tiny, i.e.
# |Top-2 difference| >= 30 pp AND |mean difference| >= 0.5 AND both valid n >= 10. This is a
# descriptive screen for the results text, not a statistical test. Requiring both summaries
# avoids flagging top-box/shape differences that leave the group mean unchanged.
# ---------------------------------------------------------------------------
_DIV_PAIRS = (("Parents", "Child respondents"), ("Care providers", "Intake coordinators"))
_TOP2_MIN, _MEAN_MIN, _N_MIN = 30.0, 0.5, 10


def _row_mean(r) -> float:
    if r["valid_n"] <= 0:
        return float("nan")
    return sum((k + 1) * r[f"{name}_n"] for k, name in enumerate(_CAT.values())) / r["valid_n"]


def build_persona_divergence(s3b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for iid, g in s3b.groupby("item_id", sort=False):
        by_unit = {str(r["reporting_unit"]): r for _, r in g.iterrows()}
        grp = "Families" if ("Parents" in by_unit or "Child respondents" in by_unit) else "Professionals"
        ua, ub = _DIV_PAIRS[0] if grp == "Families" else _DIV_PAIRS[1]
        if ua not in by_unit or ub not in by_unit:      # subgroup-only item: no comparison
            continue
        ra, rb = by_unit[ua], by_unit[ub]
        ma, mb = _row_mean(ra), _row_mean(rb)
        d_top2 = abs(float(ra["top2_pct"]) - float(rb["top2_pct"]))
        d_mean = abs(ma - mb)
        min_n = min(int(ra["valid_n"]), int(rb["valid_n"]))
        rows.append({
            "theme": g["theme"].iloc[0], "item_id": iid,
            "publication_label": g["publication_label"].iloc[0], "reporting_group": grp,
            "persona_a": ua, "valid_n_a": int(ra["valid_n"]),
            "top2_pct_a": round(float(ra["top2_pct"]), 2), "mean_a": round(ma, 2),
            "persona_b": ub, "valid_n_b": int(rb["valid_n"]),
            "top2_pct_b": round(float(rb["top2_pct"]), 2), "mean_b": round(mb, 2),
            "top2_delta_pp": round(d_top2, 2), "mean_delta": round(d_mean, 2), "min_valid_n": min_n,
            "highlighted": "Yes" if (d_top2 >= _TOP2_MIN and d_mean >= _MEAN_MIN and min_n >= _N_MIN) else "No",
        })
    out = pd.DataFrame(rows)
    return out.sort_values(["highlighted", "top2_delta_pp"], ascending=[False, False],
                           kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------------------
# supplement/Additional_file_5_codebook.csv  (framework + aggregate counts; from the PRIVATE workbook)
# Definitions and illustrative quotes stay in the private workbook (redaction gate).
# ---------------------------------------------------------------------------
def build_codebook(paths: ProjectPaths) -> pd.DataFrame | None:
    wb = paths.root / "data" / "qualitative" / "open_questions_all_themes_coded.xlsx"
    if not wb.exists():
        wb = paths.outputs / "themes" / "open_questions_all_themes_coded.xlsx"
    if not wb.exists():
        print("  [codebook] coded workbook not found — skipping (run after moving it to data/qualitative/)")
        return None
    coding = pd.read_excel(wb, sheet_name="Coding")
    coding["theme_label_en"] = (coding["theme_label_en"].astype(str).str.strip()
                                .replace({"Overview / Insight": "Overview/Insight"}))
    coding["Subtheme"] = coding["Subtheme"].astype(str).str.strip()
    # Exclude responses that were extracted but not assigned a subtheme — they are
    # not part of the coding framework and would otherwise show as blank "codes".
    n_all = len(coding)
    coding = coding[~coding["Subtheme"].str.lower().isin(["", "nan", "none"])].copy()
    n_uncoded = n_all - len(coding)
    if n_uncoded:
        print(f"  [codebook] {n_uncoded} coded-sheet responses had no subtheme — excluded")
    tot = coding.groupby(["theme_label_en", "Subtheme"]).size().rename("n_total").reset_index()
    fam = (coding[coding["group"] == "Family"].groupby(["theme_label_en", "Subtheme"])
           .size().rename("n_families").reset_index())
    pro = (coding[coding["group"] == "Professionals"].groupby(["theme_label_en", "Subtheme"])
           .size().rename("n_professionals").reset_index())
    cb = (tot.merge(fam, how="left", on=["theme_label_en", "Subtheme"])
             .merge(pro, how="left", on=["theme_label_en", "Subtheme"]))
    for c in ["n_families", "n_professionals"]:
        cb[c] = cb[c].fillna(0).astype(int)
    cb = cb.rename(columns={"theme_label_en": "theme", "Subtheme": "subtheme"})
    return cb.sort_values(["theme", "n_total"], ascending=[True, False], kind="stable").reset_index(drop=True)


def main():
    paths = ProjectPaths.from_here()
    meta = paths.root / "metadata"
    meta.mkdir(exist_ok=True)

    build_item_dictionary(paths).to_csv(meta / "item_dictionary.csv", index=False)
    print(f"Saved {meta / 'item_dictionary.csv'}")
    build_bridge_matrix(paths).to_csv(meta / "bridge_matrix.csv", index=False)
    print(f"Saved {meta / 'bridge_matrix.csv'}")

    s3a, s3b = build_s3(paths)
    s3a.to_csv(paths.outputs / "aggregate_item_results.csv", index=False)
    print(f"Saved {paths.outputs / 'aggregate_item_results.csv'}  (results A, {len(s3a)} rows)")
    s3b.to_csv(paths.outputs / "persona_specific_results.csv", index=False)
    print(f"Saved {paths.outputs / 'persona_specific_results.csv'}  (results B, {len(s3b)} rows)")

    div = build_persona_divergence(s3b)
    div.to_csv(paths.outputs / "persona_divergence.csv", index=False)
    print(f"Saved {paths.outputs / 'persona_divergence.csv'}  (results C, {len(div)} rows, "
          f"{int((div['highlighted'] == 'Yes').sum())} highlighted)")

    # The column dictionary and the codebook are supplement-only, so they go straight there.
    sup = paths.root / "supplement"
    sup.mkdir(exist_ok=True)
    build_s3_dictionary().to_csv(sup / "Additional_file_3_column_dictionary.csv", index=False)
    print(f"Saved {sup / 'Additional_file_3_column_dictionary.csv'}")

    cb = build_codebook(paths)
    if cb is not None:
        cb.to_csv(sup / "Additional_file_5_codebook.csv", index=False)
        print(f"Saved {sup / 'Additional_file_5_codebook.csv'}  (framework + counts, {len(cb)} subthemes)")


if __name__ == "__main__":
    main()
