import pandas as pd
import numpy as np

def summarize_likert(df_long: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    d = df_long[df_long["scale_type"].str.lower().eq("likert")].copy()

    # Valid denominator = a real Likert response: not NVT/DK/blank AND coded to 1-5.
    # Requiring a numeric code also excludes non-Likert answers that leaked into some
    # items (e.g. the duration options in the Levvel child Effort items), keeping the
    # denominator consistent with the 3-/5-category summaries. See ANALYSIS_DECISIONS.md.
    d["is_blank"] = d["response_raw"].fillna("").astype(str).str.strip().eq("")
    d["is_valid"] = (
        (~d["flag_nvt"]) & (~d["flag_dk"]) & (~d["is_blank"])
        & d["response_num_directional"].notna()
    )

    # Top-2 box uses the DIRECTIONAL coding: negatively-worded items are
    # reverse-coded (6 - x) so that higher = more positive. Positively-worded
    # items are unchanged (response_num_directional == response_num).
    d["top2"] = d["response_num_directional"].isin([4, 5])

    g = d.groupby(by, dropna=False)
    out = g.agg(
        n_total=("bundle_id", "size"),
        n_valid=("is_valid", "sum"),
        n_nvt=("flag_nvt", "sum"),
        n_dk=("flag_dk", "sum"),
        top2_n=("top2", "sum"),
    ).reset_index()

    out["pct_nvt"] = np.where(out["n_total"] > 0, out["n_nvt"] / out["n_total"] * 100, np.nan)
    out["pct_dk"] = np.where(out["n_total"] > 0, out["n_dk"] / out["n_total"] * 100, np.nan)

    # Top2 among valid responses only
    out["pct_top2_valid"] = np.where(out["n_valid"] > 0, out["top2_n"] / out["n_valid"] * 100, np.nan)

    return out

def summarize_time(df_long: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    d = df_long[df_long["scale_type"].str.lower().eq("time")].copy()
    d["is_blank"] = d["response_raw"].fillna("").astype(str).str.strip().eq("")
    d = d[~d["is_blank"]].copy()

    # counts per category
    counts = (
        d.groupby(by + ["response_raw"], dropna=False)
         .size()
         .reset_index(name="n")
    )
    return counts

def summarize_open(df_long: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    d = df_long[df_long["scale_type"].str.lower().eq("open")].copy()
    d["is_blank"] = d["response_raw"].fillna("").astype(str).str.strip().eq("")
    d = d[~d["is_blank"]].copy()

    out = (
        d.groupby(by, dropna=False)
         .size()
         .reset_index(name="n_open_nonempty")
    )
    return out