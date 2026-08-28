"""Denominators, Top-2, count-weighted pooling, time-scale separation, category sums."""
import numpy as np
import pandas as pd
import pytest

from src.qc import summarize_likert, summarize_time
from src.report_tables import pool_orgs


def _likert_row(bundle, num, direc, raw, org="O", per="Ouders", grp="Family", nvt=False, dk=False):
    return dict(scale_type="Likert", bundle_id=bundle, organization=org, persona=per, group=grp,
                response_raw=raw, response_num=num, response_num_directional=direc,
                flag_nvt=nvt, flag_dk=dk)


def test_top2_uses_directional_not_raw():
    # Negative item: raw "Mee eens"(5) -> directional 1 (NOT top-2); raw "Mee oneens"(1) -> directional 5 (top-2).
    df = pd.DataFrame([
        _likert_row("X", 5, 1, "Mee eens"),
        _likert_row("X", 1, 5, "Mee oneens"),
    ])
    out = summarize_likert(df, by=["bundle_id"]).iloc[0]
    assert out["n_valid"] == 2 and out["top2_n"] == 1
    assert out["pct_top2_valid"] == 50.0


def test_valid_denominator_excludes_non_likert_answers():
    # A duration answer (num/directional NaN, not NVT/DK) must be in n_total but NOT n_valid.
    df = pd.DataFrame([
        _likert_row("X", 4, 4, "Enigszins mee eens"),
        _likert_row("X", np.nan, np.nan, "1 tot 3 maanden"),
    ])
    out = summarize_likert(df, by=["bundle_id"]).iloc[0]
    assert out["n_total"] == 2 and out["n_valid"] == 1


def test_nvt_dk_counted_separately_and_excluded_from_valid():
    df = pd.DataFrame([
        _likert_row("X", 5, 5, "Mee eens"),
        _likert_row("X", np.nan, np.nan, "Niet van toepassing", nvt=True),
        _likert_row("X", np.nan, np.nan, "Weet ik niet", dk=True),
    ])
    out = summarize_likert(df, by=["bundle_id"]).iloc[0]
    assert out["n_valid"] == 1 and out["n_nvt"] == 1 and out["n_dk"] == 1


def test_zero_valid_responses_yield_nan_not_crash():
    df = pd.DataFrame([
        _likert_row("X", np.nan, np.nan, "Niet van toepassing", nvt=True),
        _likert_row("X", np.nan, np.nan, "Weet ik niet", dk=True),
    ])
    out = summarize_likert(df, by=["bundle_id"]).iloc[0]
    assert out["n_valid"] == 0 and np.isnan(out["pct_top2_valid"])


def test_pooling_is_count_weighted_not_mean_of_percentages():
    # org1: 5/10 = 50%; org2: 9/90 = 10%. Mean would be 30%; count-weighted is 14/100 = 14%.
    df = pd.DataFrame([
        dict(bundle_id="X", persona="Ouders", group="Family", organization="N=YOU",
             n_total=10, n_valid=10, n_nvt=0, n_dk=0, top2_n=5),
        dict(bundle_id="X", persona="Ouders", group="Family", organization="Levvel",
             n_total=90, n_valid=90, n_nvt=0, n_dk=0, top2_n=9),
    ])
    pooled = pool_orgs(df)
    assert len(pooled) == 1
    # count-weighted 14%, NOT the unweighted mean of 50% and 10% (= 30%)
    assert pooled.iloc[0]["pct_top2_valid"] == pytest.approx(14.0)
    assert pooled.iloc[0]["pct_top2_valid"] != pytest.approx(30.0)


def test_time_items_kept_separate_by_organisation():
    df = pd.DataFrame([
        dict(scale_type="Time", bundle_id="PRO-TIME-a", organization="N=YOU", persona="Hulpverleners",
             group="Professionals", response_raw="1 tot 3 maanden"),
        dict(scale_type="Time", bundle_id="PRO-TIME-a", organization="Levvel", persona="Hulpverleners",
             group="Professionals", response_raw="minuten"),
    ])
    out = summarize_time(df, by=["bundle_id", "organization", "persona", "group"])
    orgs = set(out["organization"])
    assert orgs == {"N=YOU", "Levvel"}          # both organisations present, separately
    assert len(out) == 2                          # never merged into one pooled row


def _write_long(tmp_path, rows):
    p = tmp_path / "analysis_long.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return str(p)


def test_5cat_percentages_sum_to_100(tmp_path):
    from run_build_likert_5cat_summary import build_likert_5cat_summary
    rows = [
        _likert_row("X", 1, 1, "Mee oneens"),
        _likert_row("X", 4, 4, "Enigszins mee eens"),
        _likert_row("X", 5, 5, "Mee eens"),
        _likert_row("X", np.nan, np.nan, "Weet ik niet", dk=True),
    ]
    out = build_likert_5cat_summary(_write_long(tmp_path, rows), str(tmp_path / "out.csv"))
    r = out[out["n_valid"] > 0].iloc[0]
    assert r["n_valid"] == 3
    s = sum(r[f"pct_{i}_valid"] for i in range(1, 6))
    assert abs(s - 100.0) < 1e-9
