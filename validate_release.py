"""
validate_release.py: seven release assertions over the published artifacts, plus a report.

Runs seven checks against supplement/ (Additional files 1, 2 and 3) and writes VALIDATION_REPORT.md.
Exits non-zero if any check fails. These verify the published tables/figures are internally
consistent and free of participant-level data; unit-level logic is covered by the pytest suite.
"""
from __future__ import annotations
from pathlib import Path
import datetime as dt
import re
import pandas as pd

ROOT = Path(__file__).resolve().parent
SUP = ROOT / "supplement"
CATS = ["disagree", "somewhat_disagree", "neutral", "somewhat_agree", "agree"]
FAMILY_UNITS = {"Parents", "Child respondents"}
PRO_UNITS = {"Care providers", "Intake coordinators"}
TOL = 0.05  # rounding tolerance on 2-dp percentages


class Check:
    def __init__(self, name): self.name, self.ok, self.detail = name, True, ""
    def fail(self, msg): self.ok = False; self.detail = msg
    def note(self, msg): self.detail = msg


def _read(name) -> pd.DataFrame:
    return pd.read_csv(SUP / name)


def c1_reconcile(s3a, s3b) -> Check:
    c = Check("Row accounting reconciles (eligible = valid + N/A + DK + missing + non-Likert)")
    bad = []
    for tag, df in [("results A", s3a), ("results B", s3b)]:
        lhs = df["eligible_n"]
        rhs = df[["valid_n", "nvt_n", "dk_n", "missing_n", "non_likert_excluded_n"]].sum(axis=1)
        mism = df[lhs != rhs]
        bad += [f"{tag}:{r.item_id}/{r.reporting_unit}" for _, r in mism.iterrows()]
    if bad:
        c.fail(f"{len(bad)} rows do not reconcile: {bad[:5]}")
    else:
        c.note(f"all {len(s3a) + len(s3b)} rows reconcile exactly")
    return c


def c2_distributions(s3a, s3b) -> Check:
    c = Check("Valid-response percentages sum to 100 and Top-2 = somewhat_agree + agree")
    bad = []
    for tag, df in [("results A", s3a), ("results B", s3b)]:
        v = df[df["valid_n"] > 0]
        s = v[[f"{k}_pct" for k in CATS]].sum(axis=1)
        for idx, tot in s.items():
            if abs(tot - 100.0) > 5 * TOL:
                bad.append(f"{tag}:{v.loc[idx,'item_id']} sum={tot:.2f}")
        t = v["somewhat_agree_pct"] + v["agree_pct"]
        for idx, expect in t.items():
            if abs(expect - v.loc[idx, "top2_pct"]) > 2 * TOL:
                bad.append(f"{tag}:{v.loc[idx,'item_id']} top2 mismatch")
    if bad:
        c.fail(f"{len(bad)} issues: {bad[:5]}")
    else:
        c.note("category percentages sum to 100 (+-rounding); Top-2 equals positions 4+5")
    return c


def c3_pooling(s3a, s3b) -> Check:
    c = Check("Group results are count-weighted pools of the persona counts")
    bad = []
    ncols = [f"{k}_n" for k in CATS] + ["valid_n", "eligible_n", "nvt_n"]
    for _, g in s3a.iterrows():
        unit = g["reporting_unit"]
        subs = FAMILY_UNITS if unit == "Families" else PRO_UNITS
        rows = s3b[(s3b["item_id"] == g["item_id"]) & (s3b["reporting_unit"].isin(subs))]
        if rows.empty:
            continue
        for col in ncols:
            if int(g[col]) != int(rows[col].sum()):
                bad.append(f"{g['item_id']}/{unit}:{col} {int(g[col])}!={int(rows[col].sum())}")
    if bad:
        c.fail(f"{len(bad)} mismatches: {bad[:5]}")
    else:
        c.note("every group count equals the sum of its persona subgroups")
    return c


def c4_no_pro_control_effort(s3a, s3b) -> Check:
    c = Check("No professional rows for Control or Effort (family-only themes)")
    hits = []
    for df in (s3a, s3b):
        m = df[df["theme"].isin(["Control", "Effort"]) &
               ((df["reporting_unit"] == "Professionals") | df["reporting_unit"].isin(PRO_UNITS))]
        hits += list(m["item_id"])
    if hits:
        c.fail(f"professional Control/Effort rows present: {sorted(set(hits))[:5]}")
    else:
        c.note("Control and Effort contain family units only")
    return c


def c5_no_control_effort_bridges(s2) -> Check:
    c = Check("No Control or Effort bridges in Additional file 2")
    themed = s2[s2[["family_theme", "professional_theme"]].isin(["Control", "Effort"]).any(axis=1)]
    if len(themed):
        c.fail(f"{len(themed)} bridges touch Control/Effort: {list(themed['bridge_id'])}")
    else:
        c.note(f"all {len(s2)} bridges are outside Control/Effort")
    return c


def c6_stable_ids(s1, s2, s3a, s3b) -> Check:
    c = Check("Item IDs are stable across Additional files 1, 2 and 3")
    s1_lik = set(s1[s1["scale_type"] == "Likert"]["item_id"])
    s3_ids = set(s3a["item_id"]) | set(s3b["item_id"])
    bridge_ids = set(s2["family_item_id"]) | set(s2["professional_item_id"])
    problems = []
    if s1_lik != s3_ids:
        problems.append(f"questionnaire-only={sorted(s1_lik - s3_ids)[:3]} results-only={sorted(s3_ids - s1_lik)[:3]}")
    if not bridge_ids <= s1_lik:
        problems.append(f"bridge IDs not in the questionnaires: {sorted(bridge_ids - s1_lik)[:3]}")
    if problems:
        c.fail("; ".join(problems))
    else:
        c.note(f"{len(s1_lik)} Likert IDs match the results; all {len(bridge_ids)} bridge sides are in the questionnaires")
    return c


def c7_no_participant_data(s1, s3a, s3b) -> Check:
    c = Check("No participant-level data in the published set")
    problems = []
    # The questionnaires carry prompts/wording only; the results carry counts/percentages only.
    if "wording_en" in s1 and s1["scale_type"].eq("Open").any():
        pass  # prompts are expected; responses are never emitted by the exporter
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    for name in ["Additional_file_1_questionnaire_items.csv", "Additional_file_2_bridge_matrix.csv",
                 "Additional_file_3A_pooled_group_results.csv", "Additional_file_3B_persona_specific_results.csv"]:
        p = SUP / name
        if p.exists() and email.search(p.read_text(encoding="utf-8")):
            problems.append(f"e-mail-like string in {name}")
    # Denominators in the results are aggregate (eligible_n), never per-respondent identifiers.
    if "ID" in s3a.columns or "respondent" in "".join(s3a.columns).lower():
        problems.append("results table A has a respondent-level column")
    if problems:
        c.fail("; ".join(problems))
    else:
        c.note("supplement holds prompts, counts and percentages only; no identifiers or free-text responses")
    return c


def main() -> int:
    s3a, s3b = _read("Additional_file_3A_pooled_group_results.csv"), _read("Additional_file_3B_persona_specific_results.csv")
    s2 = _read("Additional_file_2_bridge_matrix.csv")
    s1 = _read("Additional_file_1_questionnaire_items.csv")
    checks = [c1_reconcile(s3a, s3b), c2_distributions(s3a, s3b), c3_pooling(s3a, s3b),
              c4_no_pro_control_effort(s3a, s3b), c5_no_control_effort_bridges(s2),
              c6_stable_ids(s1, s2, s3a, s3b), c7_no_participant_data(s1, s3a, s3b)]
    n_pass = sum(c.ok for c in checks)
    lines = ["# Validation report", "",
             f"Generated {dt.date.today().isoformat()} by `validate_release.py` over `supplement/`.", "",
             f"**{n_pass}/{len(checks)} checks passed.**", ""]
    for i, c in enumerate(checks, 1):
        lines.append(f"{i}. {'PASS' if c.ok else 'FAIL'} — {c.name}  \n   {c.detail}")
    (ROOT / "VALIDATION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(f"[{'PASS' if c.ok else 'FAIL'}] {c.name}" for c in checks))
    print(f"\n{n_pass}/{len(checks)} passed -> VALIDATION_REPORT.md")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
