"""
export_s1_questionnaires.py: builds Additional file 1, the four persona questionnaires as administered.

Reads the authored, version-controlled source table metadata/questionnaire_items_source.csv
(one row per questionnaire x item, with the administered Dutch wording and its English
translation) and renders two deliverables:

  supplement/Additional_file_1_questionnaire_items.csv   one row per questionnaire x item
                                                         (the file uploaded to the journal)
  supplement/Additional_file_1_questionnaires.md         the same content as a readable document

The questionnaire is a fixed historical record of what respondents saw, so the source table
is authored data (not recomputed from the response files). Likert item IDs are stable across
Additional files 1, 2 (bridges) and 3 (results); a test checks this. Professional time-estimate items are
out of publication scope and are not included. Open-text prompts are shown; responses are not.
"""
from __future__ import annotations
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "metadata" / "questionnaire_items_source.csv"
SUP = ROOT / "supplement"

QUESTIONNAIRES = ["Parents", "Child respondents", "Care providers", "Intake coordinators"]
QUESTIONNAIRE_NL = {"Parents": "Ouders", "Child respondents": "Jongeren",
                    "Care providers": "Hulpverleners", "Intake coordinators": "Aanmeldteam"}
THEME_ORDER = ["Experience", "Overview/Insight", "Information exchange", "Control", "Effort"]

LIKERT_OPTIONS = ("5-point agreement: Mee oneens (1) / Enigszins mee oneens (2) / Neutraal (3) / "
                  "Enigszins mee eens (4) / Mee eens (5) = Disagree / Somewhat disagree / "
                  "Neutral / Somewhat agree / Agree")
OPEN_OPTIONS = "Free text (optional)"

PREAMBLE = f"""# Additional file 1. Survey questionnaires (as administered)

This file reproduces the four respondent questionnaires of an exploratory,
cross-sectional survey on information flow in youth care, fielded in Microsoft Forms at two
organisations (N=You and Levvel). Four respondent personas were surveyed: parents and
child respondents (young people aged 12-18), grouped as Families, and care providers and
intake coordinators, grouped as Professionals. Each questionnaire is shown in the
language administered (Dutch) with an English translation.

**Consent and eligibility.** Participants were informed about the study and gave consent
before starting; the full consent text is not reproduced here. Young people first answered an
eligibility screening question ("Ben jij een jongere...?" / "Are you a young person...?");
those who answered "Nee" (No) did not continue to the substantive items. One N=You young
person answered "No" and was excluded, giving an analysed sample of N=72.

**Response scale.** Likert items used a 5-point agreement scale, administered in Dutch as
*Mee oneens* (1), *Enigszins mee oneens* (2), *Neutraal* (3), *Enigszins mee eens* (4) and
*Mee eens* (5). In English these read as Disagree, Somewhat disagree, Neutral, Somewhat agree
and Agree. Where offered, respondents could also choose *Niet van toepassing* (Not applicable)
or *Weet ik niet* (Don't know); these are not counted in the valid Likert denominators (see Additional file 3).

**Mandatory vs optional.** Likert items were mandatory. Open-text prompts were optional; their
prompts are shown here, but individual responses are not reproduced.

**Reverse-scored items.** Some items were worded negatively (marked *reverse-scored* below).
This file shows them exactly as administered. In Additional file 3 and the figures these items
are relabelled to a common positive direction and marked "(R)"; the item IDs are stable across
Additional files 1, 2 and 3, so
each administered item can be traced to its results.

**Scope.** Professional time-estimate items are out of the publication scope and are not
included here or in Additional files 2 and 3.

Item IDs (e.g. FAM-BEV-a, PRO-INFO-c) are the stable identifiers used throughout the
additional files. The leading letter in each Dutch item (a., b., ...) is the order in which items
appeared within that section of the form.
"""


def _load() -> pd.DataFrame:
    df = pd.read_csv(SRC)
    df["item_id"] = df["item_id"].astype(str).str.strip()
    for c in ("dutch_wording_levvel", "english_levvel"):   # organisation-specific variants (few items)
        df[c] = df[c].fillna("").astype(str) if c in df.columns else ""
    if df["english_full"].isna().any() or (df["english_full"].astype(str).str.strip() == "").any():
        missing = df[df["english_full"].isna() | (df["english_full"].astype(str).str.strip() == "")]
        raise SystemExit(f"[questionnaires] {len(missing)} rows missing english_full, e.g. {missing['item_id'].tolist()[:5]}")
    # Some administered wording was truncated at the Microsoft Forms export ("..."); flag it.
    df["source_truncated"] = df["dutch_wording"].astype(str).str.rstrip().str.endswith("...")
    # Collapse open prompts that differ only by trailing punctuation/whitespace (the same
    # prompt administered at both organisations); keep the longer (colon-terminated) form.
    def _norm(s: str) -> str:
        return re.sub(r"[\s:]+$", "", re.sub(r"\s+", " ", str(s).strip())).lower()
    op = df["scale_type"].eq("Open")
    df["_k"] = ""
    df.loc[op, "_k"] = df.loc[op, "questionnaire"] + "||" + df.loc[op, "dutch_wording"].map(_norm)
    df["_len"] = df["dutch_wording"].str.len()
    keep = df[op].sort_values("_len", ascending=False).drop_duplicates("_k").index
    df = df[(~op) | df.index.isin(keep)].drop(columns=["_k", "_len"]).reset_index(drop=True)
    return df


def _theme_sort_key(df: pd.DataFrame) -> pd.Series:
    order = {t: i for i, t in enumerate(THEME_ORDER)}
    return df["theme"].map(lambda t: order.get(t, 99))


def build_csv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["response_options"] = out["scale_type"].map(
        lambda s: LIKERT_OPTIONS if s == "Likert" else OPEN_OPTIONS)
    out = out.rename(columns={"dutch_wording": "wording_nl", "english_full": "wording_en",
                              "dutch_wording_levvel": "wording_nl_levvel", "english_levvel": "wording_en_levvel"})
    cols = ["questionnaire", "item_id", "theme", "scale_type", "mandatory", "reverse_scored",
            "response_options", "wording_nl", "wording_en",
            "wording_nl_levvel", "wording_en_levvel", "source_truncated"]
    out["_q"] = out["questionnaire"].map({q: i for i, q in enumerate(QUESTIONNAIRES)})
    out["_o"] = (out["scale_type"] == "Open").astype(int)
    out["_t"] = _theme_sort_key(out)
    out = out.sort_values(["_q", "_o", "_t", "item_id"], kind="stable")[cols].reset_index(drop=True)
    return out


def _mark(item_id: str, truncated: bool) -> str:
    return f"{item_id} †" if truncated else item_id


def _cells(r):
    """Dutch and English cells; if the two organisations worded the item differently, show both."""
    nl = str(r["dutch_wording"]).replace("|", "\\|")
    en = str(r["english_full"]).replace("|", "\\|")
    lv_nl = str(r.get("dutch_wording_levvel", "")).strip()
    if lv_nl and lv_nl.lower() != "nan":
        lv_en = str(r.get("english_levvel", "")).strip().replace("|", "\\|")
        nl = f"**N=You:** {nl}<br>**Levvel:** {lv_nl.replace('|', chr(92) + '|')}"
        en = f"**N=You:** {en}<br>**Levvel:** {lv_en}"
    return nl, en


def build_md(df: pd.DataFrame) -> str:
    parts = [PREAMBLE]
    trunc = df[df["source_truncated"]]
    if not trunc.empty:
        ids = ", ".join(sorted(set(trunc["item_id"])))
        parts.append(
            "\n> **† Source-truncated wording.** The administered text of the following items "
            f"was cut off (\"...\") in the Microsoft Forms export and could not be recovered "
            f"from the available files: {ids}. The wording is shown as far as it was "
            "exported; the full text should be restored from the original Forms design before "
            "final publication.\n")
    varied = df[df["dutch_wording_levvel"].astype(str).str.strip().replace("nan", "") != ""]
    if not varied.empty:
        ids = ", ".join(sorted(set(varied["item_id"])))
        parts.append(
            "\n> **Organisation-specific wording.** For a few items the two organisations worded "
            f"the question differently: {ids}. Both administered versions are shown in the "
            "cell, labelled N=You and Levvel. Responses were pooled across organisations after a "
            "manual check that the wordings ask the same thing.\n")
    for q in QUESTIONNAIRES:
        sub = df[df["questionnaire"] == q]
        if sub.empty:
            continue
        n_lik = int((sub["scale_type"] == "Likert").sum())
        n_open = int((sub["scale_type"] == "Open").sum())
        parts.append(f"\n---\n\n## Questionnaire: {q}  ({QUESTIONNAIRE_NL[q]})\n")
        parts.append(f"*{n_lik} mandatory Likert items; {n_open} optional open-text prompts.*\n")

        lik = sub[sub["scale_type"] == "Likert"].copy()
        lik = lik.assign(_t=_theme_sort_key(lik)).sort_values(["_t", "item_id"], kind="stable")
        for theme in [t for t in THEME_ORDER if t in set(lik["theme"])]:
            parts.append(f"\n### {theme} (Likert, mandatory)\n")
            parts.append("| ID | Reverse-scored | Dutch (as administered) | English translation |")
            parts.append("|---|---|---|---|")
            for _, r in lik[lik["theme"] == theme].iterrows():
                nl, en = _cells(r)
                parts.append(f"| {_mark(r['item_id'], r['source_truncated'])} | {r['reverse_scored']} | {nl} | {en} |")

        op = sub[sub["scale_type"] == "Open"].copy()
        if not op.empty:
            op = op.assign(_t=_theme_sort_key(op)).sort_values(["_t", "item_id"], kind="stable")
            parts.append("\n### Open-text prompts (optional; responses not reproduced)\n")
            parts.append("| ID | Theme | Dutch prompt (as administered) | English translation |")
            parts.append("|---|---|---|---|")
            for _, r in op.iterrows():
                nl = str(r["dutch_wording"]).replace("|", "\\|")
                en = str(r["english_full"]).replace("|", "\\|")
                parts.append(f"| {_mark(r['item_id'], r['source_truncated'])} | {r['theme']} | {nl} | {en} |")
    return "\n".join(parts) + "\n"


def main() -> None:
    SUP.mkdir(exist_ok=True)
    df = _load()
    build_csv(df).to_csv(SUP / "Additional_file_1_questionnaire_items.csv", index=False)
    (SUP / "Additional_file_1_questionnaires.md").write_text(build_md(df), encoding="utf-8")
    n = len(df)
    print(f"Saved {SUP / 'Additional_file_1_questionnaire_items.csv'}  ({n} rows)")
    print(f"Saved {SUP / 'Additional_file_1_questionnaires.md'}")


if __name__ == "__main__":
    main()
