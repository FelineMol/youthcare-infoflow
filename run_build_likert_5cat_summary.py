import os
import numpy as np
import pandas as pd

from src.mapping import theme_from_bundle_id


def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _norm_str(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip()


def build_likert_5cat_summary(
    analysis_long_csv: str,
    out_csv: str,
) -> pd.DataFrame:
    """
    Creates a 5-category Likert summary from analysis_long:
      1..5 (no collapsing)

    NVT is excluded from the valid denominator for 1..5,
    but %NVT is reported vs n_total.

    Required columns in analysis_long:
      - bundle_id
      - persona
      - group
      - organization
      - scale_type  (must be 'Likert' for rows to include)
      - response_num (1..5 for likert, NaN otherwise)
      - flag_nvt (string "True" if flagged)
    """
    df = pd.read_csv(analysis_long_csv)

    # Normalize key string columns (prevents silent drops)
    for c in ["bundle_id", "persona", "group", "organization", "scale_type"]:
        if c in df.columns:
            df[c] = _norm_str(df[c])

    # Keep Likert rows only
    df = df[df["scale_type"].str.lower() == "likert"].copy()

    # If missing, default to not-flagged
    if "flag_nvt" not in df.columns:
        df["flag_nvt"] = ""

    # Coerce flags: True iff cell equals "True" (case-insensitive)
    df["flag_nvt"] = df["flag_nvt"].astype(str).str.strip().str.lower().eq("true")

    # Use the DIRECTIONAL numeric response: negatively-worded items are
    # reverse-coded (6 - x) so that higher = more positive. Positively-worded
    # items are identical to response_num.
    df["response_num"] = pd.to_numeric(df["response_num_directional"], errors="coerce")

    # Totals per (org, persona, group, bundle)
    gcols = ["organization", "persona", "group", "bundle_id"]

    # n_total = all responses including NVT/DK
    base = df.groupby(gcols, dropna=False).size().rename("n_total").reset_index()

    # counts
    n_nvt = df[df["flag_nvt"]].groupby(gcols, dropna=False).size().rename("n_nvt").reset_index()

    # valid = not NVT and has a 1..5 number
    valid = df[(~df["flag_nvt"]) & (df["response_num"].notna())].copy()
    n_valid = valid.groupby(gcols, dropna=False).size().rename("n_valid").reset_index()

    # 1..5 counts
    counts_1 = valid[valid["response_num"] == 1].groupby(gcols, dropna=False).size().rename("n_1").reset_index()
    counts_2 = valid[valid["response_num"] == 2].groupby(gcols, dropna=False).size().rename("n_2").reset_index()
    counts_3 = valid[valid["response_num"] == 3].groupby(gcols, dropna=False).size().rename("n_3").reset_index()
    counts_4 = valid[valid["response_num"] == 4].groupby(gcols, dropna=False).size().rename("n_4").reset_index()
    counts_5 = valid[valid["response_num"] == 5].groupby(gcols, dropna=False).size().rename("n_5").reset_index()

    # merge all counts
    out = (
        base.merge(n_valid, on=gcols, how="left")
            .merge(counts_1, on=gcols, how="left")
            .merge(counts_2, on=gcols, how="left")
            .merge(counts_3, on=gcols, how="left")
            .merge(counts_4, on=gcols, how="left")
            .merge(counts_5, on=gcols, how="left")
            .merge(n_nvt, on=gcols, how="left")
    )

    for c in ["n_valid", "n_1", "n_2", "n_3", "n_4", "n_5", "n_nvt"]:
        out[c] = out[c].fillna(0).astype(int)

    # percents
    out["pct_nvt"] = np.where(out["n_total"] > 0, out["n_nvt"] / out["n_total"] * 100, np.nan)

    out["pct_1_valid"] = np.where(out["n_valid"] > 0, out["n_1"] / out["n_valid"] * 100, np.nan)
    out["pct_2_valid"] = np.where(out["n_valid"] > 0, out["n_2"] / out["n_valid"] * 100, np.nan)
    out["pct_3_valid"] = np.where(out["n_valid"] > 0, out["n_3"] / out["n_valid"] * 100, np.nan)
    out["pct_4_valid"] = np.where(out["n_valid"] > 0, out["n_4"] / out["n_valid"] * 100, np.nan)
    out["pct_5_valid"] = np.where(out["n_valid"] > 0, out["n_5"] / out["n_valid"] * 100, np.nan)

    # theme label for downstream plotting
    out["theme_label_en"] = out["bundle_id"].apply(theme_from_bundle_id)

    out.round(2).to_csv(out_csv, index=False)  # percentages to 2 dp; counts unaffected
    print(f"Saved {out_csv}")
    return out


def pool_orgs_5cat(summary_by_persona: pd.DataFrame) -> pd.DataFrame:
    """
    Pools across organizations by summing counts; recomputes percents.
    """
    s = summary_by_persona.copy()
    gcols = ["bundle_id", "persona", "group"]

    pooled = (
        s.groupby(gcols, dropna=False)
         .agg(
            n_total=("n_total", "sum"),
            n_valid=("n_valid", "sum"),
            n_1=("n_1", "sum"),
            n_2=("n_2", "sum"),
            n_3=("n_3", "sum"),
            n_4=("n_4", "sum"),
            n_5=("n_5", "sum"),
            n_nvt=("n_nvt", "sum"),
            #n_dk=("n_dk", "sum"),
         )
         .reset_index()
    )

    pooled["pct_nvt"] = np.where(pooled["n_total"] > 0, pooled["n_nvt"] / pooled["n_total"] * 100, np.nan)
    #pooled["pct_dk"]  = np.where(pooled["n_total"] > 0, pooled["n_dk"]  / pooled["n_total"] * 100, np.nan)

    pooled["pct_1_valid"] = np.where(pooled["n_valid"] > 0, pooled["n_1"] / pooled["n_valid"] * 100, np.nan)
    pooled["pct_2_valid"] = np.where(pooled["n_valid"] > 0, pooled["n_2"] / pooled["n_valid"] * 100, np.nan)
    pooled["pct_3_valid"] = np.where(pooled["n_valid"] > 0, pooled["n_3"] / pooled["n_valid"] * 100, np.nan)
    pooled["pct_4_valid"] = np.where(pooled["n_valid"] > 0, pooled["n_4"] / pooled["n_valid"] * 100, np.nan)
    pooled["pct_5_valid"] = np.where(pooled["n_valid"] > 0, pooled["n_5"] / pooled["n_valid"] * 100, np.nan)

    pooled["organization"] = "Pooled"
    pooled["theme_label_en"] = pooled["bundle_id"].apply(theme_from_bundle_id)
    return pooled


def main():
    ensure_dir("outputs")

    analysis_long_csv = "outputs/analysis_long.csv"
    out_csv = "outputs/likert_5cat_summary_by_persona.csv"

    s = build_likert_5cat_summary(analysis_long_csv, out_csv)

    pooled = pool_orgs_5cat(s)
    pooled.round(2).to_csv("outputs/likert_5cat_summary_by_persona_pooled.csv", index=False)
    print("Saved outputs/likert_5cat_summary_by_persona_pooled.csv")


if __name__ == "__main__":
    main()