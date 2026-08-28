from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import pandas as pd

PERSONAS = ["Ouders", "Jongeren", "Hulpverleners", "Aanmeldteam"]
ORGS = ["N=YOU", "Levvel"]

def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()

def _norm_for_match(s: str) -> str:
    """
    Normalization used for matching headers between mapping table and export:
    - collapse whitespace
    - keep punctuation (Forms headers can include dots/colons)
    """
    return _norm_ws(s)

@dataclass(frozen=True)
class BundleSpec:
    bundle_id: str
    scale_type: str        # Likert / Time / Open (we'll add Open later)
    polarity: str          # + or -
    pool_across_orgs: str  # yes/no (string to preserve Excel)
    reporting_label_en: str | None = None

@dataclass(frozen=True)
class HeaderSpec:
    organization: str
    persona: str
    bundle_id: str
    expected_header: str

def load_bundle_mapping_table(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path).fillna("")
    required = {"bundle_id", "scale_type", "polarity"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Mapping table missing required columns: {sorted(missing)}")
    return df

def detect_header_column(df: pd.DataFrame, organization: str, persona: str) -> str | None:
    """
    Finds the column name in the mapping table that stores the (Dutch) header text
    for a given organization+persona.
    """
    target = f"{organization}_{persona}_header_nl"
    if target in df.columns:
        return target

    org_l = organization.lower()
    per_l = persona.lower()
    candidates = [
        c for c in df.columns
        if org_l in c.lower() and per_l in c.lower() and "header" in c.lower()
    ]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        # choose the most specific
        for c in candidates:
            if c.lower().endswith("_header_nl"):
                return c
        return candidates[0]

    legacy = f"{persona}_header_nl"
    if legacy in df.columns:
        return legacy

    return None

def theme_from_bundle_id(bundle_id: str) -> str:
    """Scalable theme detection: checks substrings anywhere in the ID."""
    bid = str(bundle_id).upper()
    if "BEV" in bid: return "Experience"
    if "OVZ" in bid: return "Overview/Insight"
    if "TOEG" in bid: return "Information exchange"
    if "UITW" in bid: return "Information exchange"
    if "INFO" in bid: return "Information exchange"
    if "REG" in bid: return "Control"
    if "INSP" in bid: return "Effort"
    return "Other"

#def theme_from_bundle_id_coarse(bundle_id: str) -> str:
#    """
#    Coarse theme mapping for reporting.
#    Collapses sub-themes into fewer buckets.
#    """
#    fine = theme_from_bundle_id(bundle_id)

#    if fine in {"Accessibility", "Information exchange", "Other"}:
#        return "Information exchange"
#    return fine

def build_header_lookup(mapping_df: pd.DataFrame) -> dict[tuple[str, str, str], str]:
    """
    Returns {(org, persona, bundle_id): expected_header}
    Only includes rows where expected_header is non-empty.
    """
    lookup: dict[tuple[str, str, str], str] = {}

    for org in ORGS:
        for persona in PERSONAS:
            col = detect_header_column(mapping_df, org, persona)
            if col is None:
                continue
            for _, row in mapping_df.iterrows():
                bid = str(row["bundle_id"]).strip()
                header = str(row[col]).strip()
                if bid and header:
                    lookup[(org, persona, bid)] = header

    return lookup

def get_bundle_specs(mapping_df: pd.DataFrame) -> dict[str, BundleSpec]:
    """
    Returns {bundle_id: BundleSpec} using the first occurrence of each bundle_id.
    """
    specs: dict[str, BundleSpec] = {}
    for _, row in mapping_df.iterrows():
        bid = str(row["bundle_id"]).strip()
        if not bid or bid in specs:
            continue
        specs[bid] = BundleSpec(
            bundle_id=bid,
            scale_type=str(row.get("scale_type", "")).strip(),
            polarity=str(row.get("polarity", "")).strip(),
            pool_across_orgs=str(row.get("pool_across_orgs", "")).strip() if "pool_across_orgs" in mapping_df.columns else "",
            reporting_label_en=str(row.get("reporting_label_en", "")).strip() if "reporting_label_en" in mapping_df.columns else None,
        )
    return specs

# ---------- Matching diagnostics ----------

@dataclass(frozen=True)
class MatchResult:
    bundle_id: str
    expected_header: str
    found_column: str | None
    match_type: str  # exact / normalized / prefix / missing
    n_candidates: int

def match_expected_header_to_export_columns(expected_header: str, export_columns: list[str]) -> MatchResult:
    """
    Matches one expected header to actual export columns.
    Matching strategy:
      1) exact
      2) normalized whitespace exact
      3) prefix match on first 60 chars (handles truncated "...") if unique
    """
    exp = str(expected_header)
    exp_norm = _norm_for_match(exp)

    # 1) exact
    if exp in export_columns:
        return MatchResult(bundle_id="", expected_header=exp, found_column=exp, match_type="exact", n_candidates=1)

    # 2) normalized exact
    norm_map = {_norm_for_match(c): c for c in export_columns}
    if exp_norm in norm_map:
        return MatchResult(bundle_id="", expected_header=exp, found_column=norm_map[exp_norm], match_type="normalized", n_candidates=1)

    # 3) prefix unique
    key = exp_norm[:60]
    candidates = []
    for c in export_columns:
        if _norm_for_match(c).startswith(key):
            candidates.append(c)
    if len(candidates) == 1:
        return MatchResult(bundle_id="", expected_header=exp, found_column=candidates[0], match_type="prefix", n_candidates=1)

    return MatchResult(bundle_id="", expected_header=exp, found_column=None, match_type="missing", n_candidates=len(candidates))

def build_mapping_diagnostics(
    mapping_df: pd.DataFrame,
    header_lookup: dict[tuple[str, str, str], str],
    exports: list[tuple[str, str, pd.DataFrame]],
) -> pd.DataFrame:
    """
    exports: list of (org, persona, df_export)
    Returns a diagnostics table with one row per (org, persona, bundle_id) that was expected.
    """
    rows = []
    for org, persona, df_export in exports:
        cols = list(df_export.columns)
        # for each bundle expected for this org/persona
        for (o, p, bid), expected in header_lookup.items():
            if o != org or p != persona:
                continue
            mr = match_expected_header_to_export_columns(expected, cols)
            rows.append({
                "organization": org,
                "persona": persona,
                "bundle_id": bid,
                "expected_header": expected,
                "found_column": mr.found_column or "",
                "match_type": mr.match_type,
                "n_candidates_prefix": mr.n_candidates if mr.match_type == "missing" else 1,
            })
    return pd.DataFrame(rows)