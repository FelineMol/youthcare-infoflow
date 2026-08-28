"""Likert coding, directional reversal, and analysis_long construction."""
import numpy as np
import pandas as pd
import pytest

from conftest import BUNDLE_SPECS, make_export, header_lookup
from src.transform import classify_response, reverse_code_1to5, build_analysis_long_for_export


# ---- Likert coding: 1..5, NVT, DK, blank, unmapped, the Levvel-child typo ----
@pytest.mark.parametrize("raw,num", [
    ("Mee oneens", 1),
    ("Enigszins mee oneens", 2),
    ("Neutraal", 3),
    ("Enigszins mee eens", 4),
    ("Mee eens", 5),
    ("Beet je mee oneens", 2),  # decision (c): Levvel-child Forms typo -> "Enigszins mee oneens"
])
def test_likert_coding(raw, num):
    r = classify_response(raw)
    assert r["num"] == num and not r["nvt"] and not r["dk"]


def test_nvt_dk_missing_are_distinct_states():
    nvt = classify_response("Niet van toepassing")
    dk = classify_response("Weet ik niet")
    blank = classify_response("")
    missing = classify_response(np.nan)
    assert nvt["nvt"] and not nvt["dk"] and np.isnan(nvt["num"])
    assert dk["dk"] and not dk["nvt"] and np.isnan(dk["num"])
    assert not blank["nvt"] and not blank["dk"] and np.isnan(blank["num"])
    assert not missing["nvt"] and not missing["dk"] and np.isnan(missing["num"])


def test_duration_answer_is_unmapped_not_flagged():
    # A non-Likert duration answer must not be coded and must not be NVT/DK.
    r = classify_response("1 tot 3 maanden")
    assert np.isnan(r["num"]) and not r["nvt"] and not r["dk"]


def test_reverse_code():
    assert reverse_code_1to5(1) == 5
    assert reverse_code_1to5(5) == 1
    assert reverse_code_1to5(3) == 3
    assert np.isnan(reverse_code_1to5(np.nan))


# ---- build_analysis_long_for_export ----
def test_directional_reversal_for_negative_item():
    # FAM-INSP-a is polarity '-': raw "Mee eens" (5) -> directional 1; "Mee oneens" (1) -> directional 5.
    df = make_export({"FAM-INSP-a": ["Mee eens", "Mee oneens"]})
    long = build_analysis_long_for_export(
        df, "ORG", "Ouders", BUNDLE_SPECS, header_lookup("ORG", "Ouders", ["FAM-INSP-a"]))
    long = long.sort_values("source_id")
    assert list(long["response_num"]) == [5, 1]
    assert list(long["response_num_directional"]) == [1, 5]


def test_positive_item_directional_equals_raw():
    df = make_export({"FAM-BEV-a": ["Mee eens", "Mee oneens"]})
    long = build_analysis_long_for_export(
        df, "ORG", "Ouders", BUNDLE_SPECS, header_lookup("ORG", "Ouders", ["FAM-BEV-a"]))
    assert (long["response_num"] == long["response_num_directional"]).all()


def test_group_assignment_and_open_text_rows():
    df = make_export({"FAM-BEV-a": ["Mee eens", "Neutraal", "Mee oneens"]},
                     open_texts=["synthetic note one", "", "synthetic note two"])
    long = build_analysis_long_for_export(
        df, "ORG", "Ouders", BUNDLE_SPECS, header_lookup("ORG", "Ouders", ["FAM-BEV-a"]))
    assert (long["group"] == "Family").all()
    opens = long[long["scale_type"] == "Open"]
    assert len(opens) == 2  # only the two non-empty notes


def test_professional_group():
    df = make_export({"PRO-INFO-c": ["Mee eens", "Mee oneens"]})
    long = build_analysis_long_for_export(
        df, "ORG", "Hulpverleners", BUNDLE_SPECS, header_lookup("ORG", "Hulpverleners", ["PRO-INFO-c"]))
    assert (long["group"] == "Professionals").all()


def test_unmapped_required_header_raises():
    # header_lookup points FAM-REG-a at a header that is not present in the export.
    df = make_export({"FAM-BEV-a": ["Mee eens"]})
    hl = {("ORG", "Ouders", "FAM-REG-a"): "a. Ik weet wie welke informatie kan zien"}
    with pytest.raises(ValueError):
        build_analysis_long_for_export(df, "ORG", "Ouders", BUNDLE_SPECS, hl)


def test_jongeren_screener_excludes_nee():
    df = make_export({"FAM-BEV-a": ["Mee eens", "Mee oneens"]}, screener=["Ja", "Nee, bedankt"])
    long = build_analysis_long_for_export(
        df, "ORG", "Jongeren", BUNDLE_SPECS, header_lookup("ORG", "Jongeren", ["FAM-BEV-a"]))
    assert long["source_id"].nunique() == 1  # the "Nee" respondent is dropped
