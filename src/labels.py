"""Publication label overrides (metadata/label_overrides_en.csv), kept separate from the
mapping workbook. The override layer sets the exact English label shown in figures/tables:
reverse-scored items are stated in the positive direction, and other items carry small
editorial corrections (wording, punctuation, British spelling). See ANALYSIS_DECISIONS.md.
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
_OVERRIDES = _ROOT / "metadata" / "label_overrides_en.csv"


def load_label_overrides() -> dict[str, str]:
    """Return {bundle_id: publication_label_en}. Empty if the file is absent."""
    if not _OVERRIDES.exists():
        return {}
    df = pd.read_csv(_OVERRIDES).fillna("")
    return {
        str(r["bundle_id"]).strip(): str(r["publication_label_en"]).strip()
        for _, r in df.iterrows()
        if str(r.get("bundle_id", "")).strip() and str(r.get("publication_label_en", "")).strip()
    }


def publication_label(bundle_id: str, fallback: str, overrides: dict[str, str] | None = None) -> str:
    """The label to display for an item: override if present, else the fallback."""
    ov = load_label_overrides() if overrides is None else overrides
    return ov.get(str(bundle_id).strip(), fallback)
