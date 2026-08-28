# Analytical and reporting decisions

Choices that are not obvious from the code, kept here so the results stay traceable.

## Qualitative quotes: redaction sign-off

The illustrative quotes were reviewed, redacted, and approved by the study author
(private working file `data/qualitative/S6_quote_review_PRIVATE.xlsx`).
The quote table holds 68 quotes across 30 subthemes (5 themes),
each with its interpretative phrase ("Core idea"); 14 are also cited in the manuscript
body (`cited_in_paper_text`). Quotes are English-only, attributed at persona level (no
organisation), and redacted for indirect identifiers. Dutch originals, the full open-text
corpus, and the coded workbook stay private. `build_s6_supplement.py` rebuilds the table
from the redacted review; it is not part of `run_all`'s core stages.

The quote table is not published. Redaction removes direct identifiers, but free-text answers from
small persona subgroups can still be indirectly identifying, and the participants were
children, parents and their care providers. The table is therefore written to
`outputs/S6_qualitative_patterns_PRIVATE.csv` (git-ignored) for the authors' own use and
is kept out of `supplement/`, so it cannot travel with the published supplement. Quotes
cited in the manuscript body appear in the article text itself; the qualitative methods
and the subtheme framework remain described in the paper.

## Table display: 2-decimal percentages, explicit column labels

Percentages in the published tables and the intermediate summaries are rounded to 2
decimals. Exact values stay recoverable from the integer counts (`…_n`, `valid_n`,
`eligible_n`). The 5-category columns in results tables A and B use full names (`disagree`,
`somewhat_disagree`, `neutral`, `somewhat_agree`, `agree`) rather than abbreviations. This
replaces the earlier "exact, not rounded" note; exactness is retained via the counts.

## Response-scale anchors: labelled as administered

The 5-point agreement scale was administered as "Mee oneens" (1), "Enigszins mee oneens"
(2), "Neutraal" (3), "Enigszins mee eens" (4), "Mee eens" (5). The published category
labels follow these anchors: Disagree, Somewhat disagree, Neutral, Somewhat agree, Agree.
An earlier draft labelled the endpoints "Completely disagree/agree"; there is no "Helemaal"
(completely) endpoint in the instrument, so that was corrected across the questionnaires, the results tables, the figures,
and this file. Counts and percentages are unchanged; only the category names change. Top-2
is positions 4+5, i.e. "Somewhat agree + Agree".

## Reverse-scored item labels shown in the positive direction

The 11 negatively-worded items are relabelled to match the directional coding, e.g.
"Finds repeating the child's story burdensome" becomes "Does not find repeating the
child's story burdensome". This is done in `metadata/label_overrides_en.csv` (the mapping
workbook is not edited). Figures keep an "(R)" marker and the results tables `original_direction` and `reverse_scored`
columns, so it stays visible which items were reverse-scored. Labels only; no numbers change.

## Open-text coding: non-substantive responses excluded

Of 153 extracted open-text responses, 132 were assigned a subtheme. The other 21 were
non-substantive (e.g. "idem", "zie eerder antwoord") and are excluded from the qualitative
coding and codebook counts.

## Effort family items (FAM-INSP): Levvel child display correction

The Levvel child Effort (FAM-INSP-a/b/c) questions had corrupted response labels in
Microsoft Forms. Corrected per the Forms design: "Beet je mee oneens" is position 2
(Enigszins mee oneens), "1 tot 3 maanden" is position 4 (Enigszins mee eens), and
"Meer dan 3 maanden" is position 5 (Mee eens). The correction is applied to Likert items
only; the same duration strings also occur in the professional time items, which are Time-
scale, out of publication scope, and never Likert-coded. All Levvel child Effort responses
are therefore valid Likert; N=You and Levvel parents used the standard 5-point scale.
Pooled-Families positive Top-2: FAM-INSP-a 22.9%, FAM-INSP-b 20.5%, FAM-INSP-c 10.3%.
The valid denominator is defined consistently across all outputs (not NVT, not DK, not
blank, coded 1-5).

## Small cells: include all (no suppression)

All subgroup cells are reported regardless of size; no suppression threshold is applied.
The smallest cells are the intake-coordinator (`Aanmeldteam`) subgroups (N=You n=2, Levvel
n=14) and the family personas (children/parents n=5-22). Denominators are always shown
next to percentages (`valid_n` and `eligible_n` in the results tables; `n_valid` and `n_total` in the
intermediate summaries). Percentages from very small cells (notably
N=You intake coordinators, n=2) are unstable and should be read as illustrative only, not
as estimates: this is an exploratory cross-sectional study with no claim of
representativeness or inference.

## Top-2 box direction: directional (reverse-coded)

Top-2 box and the 5-category distributions use `response_num_directional`:
negatively-worded items are reverse-coded (6 - x) so higher means more positive;
positively-worded items are unchanged. The 11 affected bundles (polarity `-`) are
FAM-BEV-c, FAM-UITW-a/b/c, FAM-INSP-a/b/c, PRO-BEV-d, PRO-INFO-a/b, PRO-OVZ-AMT-e. Results
tables A and B carry `original_direction` and `reverse_scored` columns; figures suffix
reverse-coded items with "(R)".

## NVT / DK / valid denominator

- Valid Likert responses are 1-5. NVT ("niet van toepassing") and DK ("weet ik niet") are
  excluded from the valid denominator (`valid_n` in the results tables, `n_valid` in the intermediate
  summaries).
- The not-applicable share counts NVT only (DK is not included): `nvt_pct` = `nvt_n /
  eligible_n` in the results tables, and `pct_nvt` = `n_nvt / n_total` in the intermediate summaries.
- DK is kept as a distinct count (`dk_n` in the results tables, `n_dk` in `likert_summary_by_persona.csv`);
  it is not shown in the figures.
- Missing, NVT, and DK stay three distinct states throughout.

## Publication-facing labels

- "Intake coordinators" for the intake team (internal persona key `Aanmeldteam` unchanged).
- "N=You" in figure titles and table headers; the internal identifier stays `N=YOU` (CSV
  values, filenames, raw-data folder).
- "Care providers"; "families" = parents + children aged 12-18; "professionals" = care
  providers + intake coordinators, per manuscript terminology.

## Figure format for BMC Health Services Research

Figures 1-5 are drawn at the journal's full-page width (170 mm) and saved at about 300 dpi at
that size, so the 6.5-pt text prints at 6.5 pt. Each figure's text column is as narrow as the
line limits allow (item labels in Figures 1-3 on at most two lines; questions in Figures 4-5,
which sit beside two bars, on at most three), with each label split into lines of even length.
The bars get the remaining width, so bar width differs slightly between figures.
Following the BMC submission guidelines, the figures carry no title: titles and legends are in
the manuscript, and the colour key stays in the image. `make_figures.py` stops with an error if
any text comes within 1 mm of the image edge, overlaps other text, or if a bar number is wider
than its segment.

## Persona divergence screen (results table C)

For each item the two personas in a reporting group (parents vs child respondents; care
providers vs intake coordinators) are compared on positively-oriented Top-2 (%) and on a
directional 1-5 mean (1 = Disagree ... 5 = Agree; higher = more positive). An item is
highlighted in the results only when both summaries move together and neither cell is tiny:
absolute Top-2 difference at least 30 percentage points, absolute mean difference at least
0.5, and both valid n at least 10. This is a descriptive screen, not a statistical test.
Requiring the mean to corroborate the Top-2 gap avoids flagging top-box or shape differences
that leave the group mean unchanged (for example a bimodal group like PRO-INFO-c, where
Top-2 differs by 33 points but the means are 2.67 vs 2.73). The directional mean is used only
for this screen and is not reported elsewhere. Six items meet the rule (PRO-OVZ-c, PRO-OVZ-a,
PRO-INFO-f, FAM-TOEG-b, FAM-OVZ-e, PRO-OVZ-b); all per-item values and the flag are in
Additional file 3, sheet C (`supplement/Additional_file_3C_persona_divergence.csv`).

## Questionnaire differences between the two organisations

N=You and Levvel did not use identical questionnaires. Levvel reworded some items and left a
few out. To pool the two organisations, items were matched across them; the matching is kept
in the BundleMap (a Dutch header per organisation and persona, plus availability flags), and
`src.mapping.build_header_lookup` treats any filled-in header as a mapped item.

An audit (2026-07-30) showed the automatic matching had been too strict and dropped three
items that Levvel did ask, only with different words. We read the raw wording, confirmed the
questions were the same, and added them to the mapping so both organisations count:

- FAM-REG-c, Levvel children: "Ik wil zelf bepalen wie er welke informatie over mij mag lezen"
- FAM-REG-d, Levvel parents: "Ik wil graag alles weten wat er in de dossiers van mijn kind staat"
- PRO-OVZ-a, Levvel care providers: "Ik heb goed overzicht van welke organisaties of hulpverleners eerder bij het kind betrokken zijn geweest"

Three items really were asked in one organisation only, and stay that way:

- FAM-BEV-d and FAM-BEV-e are in Levvel's child form but not its parent form (N=You has both).
- PRO-OVZ-HULPV-f was asked only at N=You. Levvel asked care providers a different question
  ("Ik moet vaak extra informatie opvragen omdat de informatie niet compleet is"), which has
  no N=You counterpart, so it is left unmapped rather than pooled.

To keep this visible, results tables A and B carry an `orgs_included` column: "N=You + Levvel" for most
items, and "N=You" (or "Levvel") for the three single-organisation rows, where the eligible N
is therefore below the full persona. After the fix, PRO-OVZ-a care providers went from 7 to 15
and it became a highlighted persona difference; FAM-REG-c and FAM-REG-d reached the full
family denominators but their persona differences stayed small. A copy of the pre-audit
mapping workbook was kept as a local backup; it is not part of this repository.

## Standing conventions

- Pooling is count-weighted: pooled percentages come from summed counts, never a mean of
  subgroup percentages. Persona denominators are retained.
- Professional time items (`PRO-TIME-*`) use different scales per organisation and are
  never pooled across organisations; they live in `time_counts_by_org_persona.csv` and are
  not reported for the Effort theme in the article.
- Control and Effort are family-only themes; no Family/Professional comparison is built for
  them.
- Sample: N=72 analysed respondents (Families 41, Professionals 31). That is 73 raw
  submissions minus one N=You Jongeren who answered the screener "Nee" and is excluded.
