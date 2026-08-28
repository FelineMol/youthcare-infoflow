"""Theme detection, header matching, header-column detection, bundle specs."""
import pandas as pd
import pytest

from src.mapping import (
    theme_from_bundle_id,
    match_expected_header_to_export_columns,
    detect_header_column,
    get_bundle_specs,
)


@pytest.mark.parametrize("bid,theme", [
    ("FAM-BEV-a", "Experience"),
    ("FAM-OVZ-c", "Overview/Insight"),
    ("FAM-TOEG-c", "Information exchange"),
    ("FAM-UITW-a", "Information exchange"),
    ("PRO-INFO-c", "Information exchange"),
    ("FAM-REG-a", "Control"),
    ("FAM-INSP-a", "Effort"),
    ("PRO-TIME-a", "Other"),   # time items must NOT land in Effort
])
def test_theme_from_bundle_id(bid, theme):
    assert theme_from_bundle_id(bid) == theme


def test_header_match_exact():
    mr = match_expected_header_to_export_columns("a. Vraag een", ["a. Vraag een", "b. Vraag twee"])
    assert mr.match_type == "exact" and mr.found_column == "a. Vraag een"


def test_header_match_normalized_whitespace():
    mr = match_expected_header_to_export_columns("a.  Vraag   een", ["a. Vraag een"])
    assert mr.match_type == "normalized" and mr.found_column == "a. Vraag een"


def test_header_match_prefix_when_truncated():
    expected = "a. " + "lange vraag tekst " * 6  # > 60 chars
    export_col = expected[:70] + " (afgekapt in export)"
    mr = match_expected_header_to_export_columns(expected, [export_col])
    assert mr.match_type == "prefix" and mr.found_column == export_col


def test_header_match_missing():
    mr = match_expected_header_to_export_columns("a. Vraag een", ["z. Iets heel anders"])
    assert mr.match_type == "missing" and mr.found_column is None


def test_detect_header_column_exact_then_legacy():
    df_exact = pd.DataFrame(columns=["N=YOU_Ouders_header_nl", "other"])
    assert detect_header_column(df_exact, "N=YOU", "Ouders") == "N=YOU_Ouders_header_nl"
    df_legacy = pd.DataFrame(columns=["Ouders_header_nl", "other"])
    assert detect_header_column(df_legacy, "N=YOU", "Ouders") == "Ouders_header_nl"


def test_detect_header_column_prefers_header_nl_when_ambiguous():
    df = pd.DataFrame(columns=["Levvel_Ouders_header_nl", "Levvel_Ouders_header_extra"])
    assert detect_header_column(df, "Levvel", "Ouders") == "Levvel_Ouders_header_nl"


def test_get_bundle_specs_first_occurrence_wins():
    df = pd.DataFrame([
        {"bundle_id": "B1", "scale_type": "Likert", "polarity": "+"},
        {"bundle_id": "B1", "scale_type": "Time", "polarity": "-"},  # duplicate ignored
        {"bundle_id": "B2", "scale_type": "Likert", "polarity": "-"},
    ])
    specs = get_bundle_specs(df)
    assert specs["B1"].scale_type == "Likert" and specs["B1"].polarity == "+"
    assert specs["B2"].polarity == "-"
