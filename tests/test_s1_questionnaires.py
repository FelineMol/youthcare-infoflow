"""Questionnaire (Additional file 1) consistency against Additional files 2 and 3.

These read the committed supplement/ files (skipped if a release has not been assembled).
They guard the stable-ID contract and the family-only theme rule at the questionnaire level.
"""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SUP = ROOT / "supplement"
FAMILY_THEMES_ONLY = {"Control", "Effort"}


def _read(name):
    p = SUP / name
    if not p.exists():
        pytest.skip(f"{name} not assembled; run run_all.py")
    return pd.read_csv(p)


@pytest.fixture(scope="module")
def s1():
    return _read("Additional_file_1_questionnaire_items.csv")


def test_s1_likert_ids_match_s3(s1):
    s3 = pd.concat([_read("Additional_file_3A_pooled_group_results.csv"),
                    _read("Additional_file_3B_persona_specific_results.csv")], ignore_index=True)
    s1_likert = set(s1[s1["scale_type"] == "Likert"]["item_id"])
    assert s1_likert == set(s3["item_id"])


def test_s2_bridge_sides_exist_in_s1(s1):
    s2 = _read("Additional_file_2_bridge_matrix.csv")
    s1_likert = set(s1[s1["scale_type"] == "Likert"]["item_id"])
    sides = set(s2["family_item_id"]) | set(s2["professional_item_id"])
    assert sides <= s1_likert


def test_no_time_items_in_s1(s1):
    assert not s1["item_id"].str.contains("TIME").any()


def test_mandatory_optional_matches_scale(s1):
    assert (s1.loc[s1["scale_type"] == "Likert", "mandatory"] == "Mandatory").all()
    assert (s1.loc[s1["scale_type"] == "Open", "mandatory"] == "Optional").all()


def test_every_item_has_both_languages(s1):
    for col in ("wording_nl", "wording_en"):
        assert s1[col].notna().all()
        assert (s1[col].astype(str).str.strip() != "").all()


def test_professional_questionnaires_have_no_control_or_effort_likert(s1):
    # The family-only rule is a quantitative one: no professional Likert items for Control or
    # Effort. Professionals could still answer open-text prompts tagged to those themes.
    prof_likert = s1[s1["questionnaire"].isin(["Care providers", "Intake coordinators"]) &
                     (s1["scale_type"] == "Likert")]
    assert not prof_likert["theme"].isin(FAMILY_THEMES_ONLY).any()
