"""Assemble the S6 qualitative patterns table from the private, author-redacted review
sheet (data/qualitative/S6_quote_review_PRIVATE.xlsx) plus the Subthemes "Core idea"
column. A cited_in_paper_text flag marks quotes used in the manuscript. Depends on the
private redaction review, so it is not part of run_all's core stages.

S6 is NOT published: it holds participant quotes, which can be indirectly identifying
even after redaction. The table is written to outputs/ (private, git-ignored) for the
authors' own use, never to supplement/.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / "data" / "qualitative" / "S6_quote_review_PRIVATE.xlsx"
CODED = ROOT / "data" / "qualitative" / "open_questions_all_themes_coded.xlsx"
OUT = ROOT / "outputs" / "S6_qualitative_patterns_PRIVATE.csv"   # private: never published

THEME_ORDER = ["Experience", "Overview/Insight", "Information exchange", "Control", "Effort"]
PERSONA_ORDER = ["Parent", "Child respondent", "Care provider", "Intake coordinator"]


def _subtheme_framework() -> pd.DataFrame:
    """Subthemes sheet -> theme, subtheme, interpretative_phrase (Core idea), in sheet order."""
    raw = pd.read_excel(CODED, sheet_name="Subthemes", header=None).dropna(how="all").reset_index(drop=True)
    hdr = None
    for i in range(min(6, len(raw))):
        if any(str(v).strip().lower() == "subtheme" for v in raw.iloc[i]):
            hdr = i
            break
    header = [str(v).strip() for v in raw.iloc[hdr].tolist()]
    body = raw.iloc[hdr + 1:].copy()
    body.columns = header
    body = body.loc[:, [c for c in body.columns if c and c.lower() != "nan"]]
    body["Theme"] = body["Theme"].ffill()
    body = body[body["Subtheme"].notna()].copy()
    out = pd.DataFrame({
        "theme": body["Theme"].astype(str).str.strip().replace({"Overview / Insight": "Overview/Insight",
                                                                 "Overview/insight": "Overview/Insight"}),
        "subtheme": body["Subtheme"].astype(str).str.strip(),
        "interpretative_phrase": body["Core idea"].astype(str).str.strip(),
    })
    out["_order"] = range(len(out))
    return out


def build() -> pd.DataFrame:
    r = pd.read_excel(REVIEW, sheet_name="Review")
    r.columns = [str(c).strip() for c in r.columns]
    r["subtheme"] = r["subtheme"].astype(str).str.strip()
    r["cited_in_paper_text"] = (
        r["Used in paper text"].astype(str).str.strip().str.lower().eq("yes").map({True: "yes", False: "no"})
    )
    quotes = r[["subtheme", "persona", "english_quote_FINAL", "cited_in_paper_text"]].rename(
        columns={"english_quote_FINAL": "quote"})
    quotes["quote"] = quotes["quote"].astype(str).str.strip()

    fw = _subtheme_framework()
    # sanity: every reviewed subtheme must exist in the framework
    missing = sorted(set(quotes["subtheme"]) - set(fw["subtheme"]))
    if missing:
        raise ValueError(f"Subthemes in review not found in Subthemes sheet: {missing}")

    merged = fw.merge(quotes, on="subtheme", how="left")
    merged["theme"] = pd.Categorical(merged["theme"], categories=THEME_ORDER, ordered=True)
    merged["persona"] = pd.Categorical(merged["persona"], categories=PERSONA_ORDER, ordered=True)
    merged["_cited"] = merged["cited_in_paper_text"].eq("yes").map({True: 0, False: 1})  # cited first
    merged = merged.sort_values(["theme", "_order", "_cited", "persona"], kind="stable")
    merged["cited_in_paper_text"] = merged["cited_in_paper_text"].fillna("")  # subthemes with no quote
    return merged[["theme", "subtheme", "interpretative_phrase", "persona", "quote", "cited_in_paper_text"]]


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    s6 = build()
    s6.to_csv(OUT, index=False)
    n_q = int(s6["quote"].astype(str).str.strip().replace("nan", "").ne("").sum())
    n_cited = int(s6["cited_in_paper_text"].eq("yes").sum())
    print(f"Saved {OUT.relative_to(ROOT)}")
    print(f"  subthemes: {s6['subtheme'].nunique()} | quote rows: {n_q} | cited in paper text: {n_cited}")


if __name__ == "__main__":
    main()
