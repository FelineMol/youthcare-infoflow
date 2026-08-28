"""Shared fixtures and fully-synthetic helpers for the test suite.

Nothing here is derived from real respondents. All strings are invented; the
open-text values are obviously artificial placeholders. Tests never read
data/raw/ or the private qualitative workbook.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# A few synthetic bundles spanning the relevant scale types / polarities / themes.
BUNDLE_SPECS = pd.DataFrame([
    {"bundle_id": "FAM-BEV-a", "scale_type": "Likert", "polarity": "+"},   # Experience, positive
    {"bundle_id": "FAM-INSP-a", "scale_type": "Likert", "polarity": "-"},  # Effort, negative (reverse-coded)
    {"bundle_id": "FAM-REG-a", "scale_type": "Likert", "polarity": "+"},   # Control
    {"bundle_id": "PRO-INFO-c", "scale_type": "Likert", "polarity": "+"},  # Information exchange
])

HEADERS = {
    "FAM-BEV-a": "a. Overzicht houden voelt makkelijk",
    "FAM-INSP-a": "a. Het kostte me veel tijd en moeite",
    "FAM-REG-a": "a. Ik weet wie welke informatie kan zien",
    "PRO-INFO-c": "c. Ik kan makkelijk informatie opvragen bij anderen",
}
OPEN_HEADER = "ik wil graag nog iets toevoegen"
SCREENER_HEADER = "Ben jij een jongere?"


@pytest.fixture
def bundle_specs():
    return BUNDLE_SPECS.copy()


def make_export(likert_by_bundle, ids=None, open_texts=None, screener=None):
    """Construct a synthetic Microsoft-Forms-style export DataFrame.

    likert_by_bundle: {bundle_id: [response strings, one per respondent]}
    """
    n = len(next(iter(likert_by_bundle.values())))
    data = {"ID": ids if ids is not None else list(range(1, n + 1))}
    for bundle, responses in likert_by_bundle.items():
        data[HEADERS[bundle]] = responses
    if open_texts is not None:
        data[OPEN_HEADER] = open_texts
    if screener is not None:
        data[SCREENER_HEADER] = screener
    return pd.DataFrame(data)


def header_lookup(org, persona, bundles):
    return {(org, persona, b): HEADERS[b] for b in bundles}
