"""Validation of the real (public) mapping workbooks. Skipped if absent.

Uses only the public mapping — never data/raw/ or the private qualitative workbook.
"""
from pathlib import Path

import pandas as pd
import pytest

from src.mapping import theme_from_bundle_id

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "data" / "mapping" / "intermediate_bundle_mapping_table_v6.xlsx"
BRIDGE = ROOT / "data" / "mapping" / "bridge_map_with_workload_links_v08.xlsx"

pytestmark = pytest.mark.skipif(
    not (MAP.exists() and BRIDGE.exists()),
    reason="mapping workbooks not present (public data not checked out)",
)


def _bundlemap():
    return pd.read_excel(MAP, sheet_name="BundleMap").fillna("")


def _bridges():
    return pd.read_excel(BRIDGE, sheet_name="Bridges").fillna("")


def test_bridge_ids_unique_and_sides_exist_in_bundlemap():
    br = _bridges()
    ids = br["bridge_id"].astype(str).str.strip()
    assert ids.is_unique, "bridge_id values must be unique"
    valid = set(_bundlemap()["bundle_id"].astype(str).str.strip())
    for side in ["family_bundle_id", "professional_bundle_id"]:
        for b in br[side].astype(str).str.strip():
            if b:
                assert b in valid, f"{side} {b!r} not found in BundleMap"


def test_no_control_or_effort_bridges():
    # Control and Effort are family-only: no bridge may imply a Family-Professional comparison.
    br = _bridges()
    for b in br["family_bundle_id"].astype(str).str.strip():
        assert theme_from_bundle_id(b) not in {"Control", "Effort"}


def test_control_effort_have_no_professional_likert_items():
    bm = _bundlemap()
    for _, r in bm.iterrows():
        bid = str(r["bundle_id"]).strip()
        is_likert = str(r["scale_type"]).strip().lower().startswith("lik")
        if is_likert and bid.startswith("PRO-"):
            assert theme_from_bundle_id(bid) not in {"Control", "Effort"}


def test_time_bundles_not_pooled_across_orgs():
    bm = _bundlemap()
    time = bm[bm["scale_type"].astype(str).str.strip().str.lower() == "time"]
    assert len(time) > 0
    assert (time["pool_across_orgs"].astype(str).str.strip().str.lower() == "no").all()
