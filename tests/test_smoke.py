"""End-to-end smoke run on fully synthetic data (two orgs x family + professional)."""
import pandas as pd

from conftest import BUNDLE_SPECS, make_export, header_lookup
from src.transform import build_analysis_long_for_export
from src.qc import summarize_likert
from src.report_tables import pool_orgs

FAM_BUNDLES = ["FAM-BEV-a", "FAM-INSP-a", "FAM-REG-a"]
PRO_BUNDLES = ["PRO-INFO-c"]


def _build_org(org):
    fam = make_export({
        "FAM-BEV-a": ["Mee eens", "Neutraal", "Mee oneens"],
        "FAM-INSP-a": ["Mee oneens", "Mee eens", "Niet van toepassing"],
        "FAM-REG-a": ["Mee eens", "Enigszins mee eens", ""],
    }, open_texts=["synthetic remark", "", ""])
    pro = make_export({"PRO-INFO-c": ["Mee eens", "Mee oneens"]})
    long_fam = build_analysis_long_for_export(
        fam, org, "Ouders", BUNDLE_SPECS, header_lookup(org, "Ouders", FAM_BUNDLES))
    long_pro = build_analysis_long_for_export(
        pro, org, "Hulpverleners", BUNDLE_SPECS, header_lookup(org, "Hulpverleners", PRO_BUNDLES))
    return pd.concat([long_fam, long_pro], ignore_index=True)


def test_smoke_pipeline_runs_and_is_consistent():
    analysis_long = pd.concat([_build_org("N=YOU"), _build_org("Levvel")], ignore_index=True)

    # Structure
    assert set(analysis_long["group"].unique()) == {"Family", "Professionals"}
    assert (analysis_long["scale_type"] == "Open").sum() == 2  # one synthetic remark per org

    summ = summarize_likert(analysis_long, by=["bundle_id", "organization", "persona", "group"])

    # Control (FAM-REG-a) is family-only in this synthetic set: no Professionals rows.
    reg = summ[summ["bundle_id"] == "FAM-REG-a"]
    assert set(reg["group"].unique()) == {"Family"}

    # Directional reversal: FAM-INSP-a respondent who answered "Mee eens"(5) counts
    # against Top-2 (directional 1), while "Mee oneens"(1) counts for it (directional 5).
    insp = summ[summ["bundle_id"] == "FAM-INSP-a"]
    assert insp["top2_n"].sum() >= 1  # the "Mee oneens" responses

    # Pooling collapses the two orgs to a single row per (bundle, persona, group),
    # count-weighted; percentages stay within [0, 100].
    pooled = pool_orgs(summ)
    assert (pooled.groupby(["bundle_id", "persona", "group"]).size() == 1).all()
    valid_pct = pooled["pct_top2_valid"].dropna()
    assert ((valid_pct >= 0) & (valid_pct <= 100)).all()
