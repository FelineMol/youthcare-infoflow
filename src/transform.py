from __future__ import annotations

from dataclasses import dataclass
import re
import pandas as pd
import numpy as np


LIKERT_MAP = {
    "Mee oneens": 1,
    "Enigszins mee oneens": 2,
    "Neutraal": 3,
    "Enigszins mee eens": 4,
    "Mee eens": 5,
    # Forms-configuration issue in the Levvel child Effort (FAM-INSP) items only:
    # "Beet je mee oneens" is a corrupted "Enigszins mee oneens" -> 2.
    "Beet je mee oneens": 2,
}

# Same Levvel child Effort corruption: duration labels were shown in place of
# agreement positions 4 and 5 (confirmed from the Forms design). Applied to LIKERT
# items only (these strings also occur in the professional time items, which are Time-
# scale and out of publication scope, and must not be Likert-coded).
DURATION_DISPLAY_FIX = {"1 tot 3 maanden": 4, "meer dan 3 maanden": 5}

META_COLS = {
    # English exports
    "ID", "Start time", "Completion time", "Email", "Name", "Last modified time",
    # Dutch exports
    "Begintijd", "Tijd van voltooien", "E-mail", "Naam", "Laatste wijzigingstijd",
}

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()

def classify_response(val) -> dict:
    """
    Returns raw + numeric coding for Likert when possible.
    NVT/DK are flagged and numeric is NaN.
    """
    if pd.isna(val):
        return {"raw": "", "num": np.nan, "nvt": False, "dk": False}

    raw = str(val).strip()
    if raw == "":
        return {"raw": "", "num": np.nan, "nvt": False, "dk": False}

    lo = raw.lower()

    if "niet van toepassing" in lo or "doe ik niet" in lo or lo in {"nvt", "n.v.t."}:
        return {"raw": raw, "num": np.nan, "nvt": True, "dk": False}

    if "weet ik niet" in lo or "weet ik niet meer" in lo:
        return {"raw": raw, "num": np.nan, "nvt": False, "dk": True}

    if raw in LIKERT_MAP:
        return {"raw": raw, "num": LIKERT_MAP[raw], "nvt": False, "dk": False}

    # time / other categories stay raw only
    return {"raw": raw, "num": np.nan, "nvt": False, "dk": False}

def reverse_code_1to5(x: float) -> float:
    if pd.isna(x):
        return np.nan
    return 6 - x

def detect_jongeren_screener_col(columns: list[str]) -> str | None:
    for c in columns:
        if "ben jij een jongere" in str(c).lower():
            return c
    return None

def is_open_text_header(h: str) -> bool:
    """
    Treat feedback columns (starting with "ik wil graag" or "feedback")as open text columns.
    """
    s = str(h).strip().lower()
    return s.startswith("ik wil graag") or s.startswith("feedback:")

def build_analysis_long_for_export(
    df: pd.DataFrame,
    organization: str,
    persona: str,
    bundle_specs: pd.DataFrame,
    header_lookup: dict[tuple[str, str, str], str],
) -> pd.DataFrame:
    """
    Converts a single export df into long format for:
      - mapped bundle_id items (Likert/Time)
      - open-text columns as scale_type="Open" (bundle_id = OPEN::<header>)
    """
    if "ID" not in df.columns:
        raise ValueError(f"Export missing ID column for {organization} {persona}")

    # Exclude jongeren screener "Nee"
    if persona == "Jongeren":
        sc = detect_jongeren_screener_col(list(df.columns))
        if sc is not None:
            mask_no = df[sc].astype(str).str.strip().str.lower().str.startswith("nee")
            df = df.loc[~mask_no].copy()

    out_rows = []
    group = "Family" if persona in ["Ouders", "Jongeren"] else "Professionals"

    # ---------- 1) mapped bundle items ----------
    # make quick column lookup for normalized matching
    export_cols = list(df.columns)
    export_cols_norm = {norm_ws(c): c for c in export_cols}

    for _, r in bundle_specs.iterrows():
        bundle_id = str(r["bundle_id"]).strip()
        scale_type = str(r["scale_type"]).strip()
        polarity = str(r["polarity"]).strip()

        expected = header_lookup.get((organization, persona, bundle_id), "")
        if not expected:
            continue  # not available for this org/persona

        expected_norm = norm_ws(expected)

        # match
        col = None
        if expected in export_cols:
            col = expected
        elif expected_norm in export_cols_norm:
            col = export_cols_norm[expected_norm]
        else:
            key = expected_norm[:60]
            candidates = [c for c in export_cols if norm_ws(c).startswith(key)]
            if len(candidates) == 1:
                col = candidates[0]

        if col is None:
            raise ValueError(f"Unmatched column during build: {organization} {persona} {bundle_id}")

        for _, row in df[["ID", col]].iterrows():
            respondent_id = f"{organization}_{persona}_{row['ID']}"
            parsed = classify_response(row[col])

            num = parsed["num"]
            # Likert-only display-corruption fix (Levvel child Effort duration labels -> positions 4/5)
            if scale_type.lower().startswith("lik") and pd.isna(num):
                num = DURATION_DISPLAY_FIX.get(parsed["raw"].lower(), num)
            num_dir = np.nan
            if scale_type.lower().startswith("lik") and not pd.isna(num):
                num_dir = reverse_code_1to5(num) if polarity == "-" else num

            out_rows.append({
                "organization": organization,
                "persona": persona,
                "group": group,
                "respondent_id": respondent_id,
                "source_id": row["ID"],
                "bundle_id": bundle_id,
                "scale_type": scale_type,
                "polarity": polarity,
                "response_raw": parsed["raw"],
                "response_num": num,
                "response_num_directional": num_dir,
                "flag_nvt": parsed["nvt"],
                "flag_dk": parsed["dk"],
            })

    # ---------- 2) Open text columns ----------
    # Exclude obvious metadata + consent text columns
    candidate_open_cols = [
        c for c in df.columns
        if c not in META_COLS and is_open_text_header(c)
    ]

    for col in candidate_open_cols:
        for _, row in df[["ID", col]].iterrows():
            txt = "" if pd.isna(row[col]) else str(row[col]).strip()
            if txt == "":
                continue
            respondent_id = f"{organization}_{persona}_{row['ID']}"
            out_rows.append({
                "organization": organization,
                "persona": persona,
                "group": group,
                "respondent_id": respondent_id,
                "source_id": row["ID"],
                "bundle_id": f"OPEN::{col}",
                "scale_type": "Open",
                "polarity": "",
                "response_raw": txt,
                "response_num": np.nan,
                "response_num_directional": np.nan,
                "flag_nvt": False,
                "flag_dk": False,
            })

    return pd.DataFrame(out_rows)