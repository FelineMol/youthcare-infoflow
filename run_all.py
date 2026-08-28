"""One-command runner for the canonical pipeline.

Runs the verified stages in dependency order, then tidies outputs (consolidates figures,
groups intermediate summaries under outputs/summaries/, moves non-canonical files to
outputs/_legacy/) and assembles supplement/.
Usage: python run_all.py  (non-zero exit if a stage fails).
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
PY = sys.executable

# The paper's Additional files 1-5, as uploaded to the journal (BMC names them "Additional
# file 1" and so on). Each maps to its file in supplement/; run_all also copies them, under
# exactly those names, to outputs/journal_upload/ (local only, not committed).
UPLOAD = {
    "Additional file 1.csv": "Additional_file_1_questionnaire_items.csv",
    "Additional file 2.csv": "Additional_file_2_bridge_matrix.csv",
    "Additional file 3.xlsx": "Additional_file_3_results.xlsx",
    "Additional file 4.pdf": "Additional_file_4_Top2_dotplots.pdf",
    "Additional file 5.csv": "Additional_file_5_codebook.csv",
}
# Additional file 3 bundles the results tables, one sheet each (CSV copies stay in supplement/).
RESULTS_SHEETS = [
    ("A pooled groups", "Additional_file_3A_pooled_group_results.csv"),
    ("B persona-specific", "Additional_file_3B_persona_specific_results.csv"),
    ("C persona divergence", "Additional_file_3C_persona_divergence.csv"),
    ("Column dictionary", "Additional_file_3_column_dictionary.csv"),
]

STAGES = [
    "run_build_analysis_long.py",          # analysis_long (private) + core summaries
    "run_build_likert_5cat_summary.py",    # 5-category summary (provenance)
    "export_publication_artifacts.py",     # metadata, bridges, results tables, dictionary, codebook
    "export_s1_questionnaires.py",         # Additional file 1: the four questionnaires (csv + md)
    "make_figures.py",                     # Figures 1-5 (from the final results tables)
    "make_s4_dotplots.py",                 # Additional file 4: Top-2 dot-plots (one PDF)
    "run_build_open_question_tables.py",   # open-text exports (PRIVATE)
]

# Intermediate verified summaries -> outputs/summaries/ (provenance, not paper tables)
SUMMARIES = [
    "likert_summary_by_persona.csv",
    "likert_5cat_summary_by_persona.csv",
    "likert_5cat_summary_by_persona_pooled.csv",
    "open_counts.csv",
]
# Non-canonical side-effects / superseded / orphaned -> outputs/_legacy/
TO_LEGACY = [
    "likert_summary_by_group.csv",
    "time_counts_by_org_persona.csv",
    "dotplot_bridges_Levvel.png",
    "dotplot_bridges_N=YOU.png",
    "dotplot_bridges_Pooled.png",
    "mapping_diagnostics.csv",             # orphaned: not produced by the current pipeline
]


def run_stage(stage: str) -> None:
    print(f"\n{'=' * 60}\n=== {stage}\n{'=' * 60}", flush=True)
    result = subprocess.run([PY, stage], cwd=str(ROOT), env={**os.environ, "MPLBACKEND": "Agg"})
    if result.returncode != 0:
        print(f"\n!! STAGE FAILED: {stage} (exit {result.returncode})")
        sys.exit(result.returncode)


def _move(src: Path, dst_dir: Path) -> None:
    if not src.exists():
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    shutil.move(str(src), str(dst))


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(str(src), str(dst))


def tidy() -> None:
    legacy = OUT / "_legacy"
    themes = OUT / "themes"

    # 1) sweep side-effect / superseded / orphaned files to _legacy
    for name in TO_LEGACY:
        _move(OUT / name, legacy)
    _move(themes / "theme_tables", legacy / "themes")   # Top-2 tables superseded by the results tables

    # 2) figures. Figures 1-5 (make_figures.py) are the article figures in outputs/figures/.
    #    Keep the Additional file 4 dot-plots; retire the superseded 5-/3-category theme plots
    #    and any old article_5cat copies to _legacy.
    for p in themes.glob("dotplot_theme_*_Pooled.png"):
        _move(p, OUT / "figures" / "S4_pooled_dotplots")
    for p in list(themes.glob("dotplot_theme_*_5cat.png")) + list(themes.glob("dotplot_theme_*_3cat.png")):
        _move(p, legacy / "superseded_theme_plots")
    if (OUT / "figures" / "article_5cat").exists():
        _move(OUT / "figures" / "article_5cat", legacy)

    # 3) group intermediate summaries under outputs/summaries/
    for name in SUMMARIES:
        _move(OUT / name, OUT / "summaries")

    # 4) assemble the published supplement
    assemble_supplement()


def _write_results_workbook(sup: Path) -> None:
    """Additional file 3: the results tables as one Excel workbook, one sheet per table."""
    import pandas as pd
    out = sup / "Additional_file_3_results.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        for sheet, name in RESULTS_SHEETS:
            pd.read_csv(sup / name).to_excel(xw, sheet_name=sheet, index=False)
            xw.sheets[sheet].freeze_panes = "A2"
    _fix_zip_timestamps(out)


def _fix_zip_timestamps(path: Path) -> None:
    """An .xlsx is a zip that records the time it was written. Pin those timestamps so that
    rebuilding an unchanged workbook gives an identical file (and a clean git status)."""
    import re
    import zipfile
    with zipfile.ZipFile(path) as z:
        parts = [(i.filename, z.read(i.filename)) for i in z.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts:
            if name == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*",
                              rb"\g<1>2026-01-01T00:00:00Z", data)
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)


def assemble_supplement() -> None:
    sup = ROOT / "supplement"
    meta = ROOT / "metadata"
    sup.mkdir(exist_ok=True)
    # Additional file 1, the column dictionary and the codebook are written straight to
    # supplement/ by their scripts. metadata/item_dictionary.csv stays an internal source.
    _copy(meta / "bridge_matrix.csv", sup / "Additional_file_2_bridge_matrix.csv")
    _copy(OUT / "aggregate_item_results.csv", sup / "Additional_file_3A_pooled_group_results.csv")
    _copy(OUT / "persona_specific_results.csv", sup / "Additional_file_3B_persona_specific_results.csv")
    _copy(OUT / "persona_divergence.csv", sup / "Additional_file_3C_persona_divergence.csv")
    _write_results_workbook(sup)
    _copy(OUT / "figures" / "S4_pooled_dotplots" / "Top2_dotplots.pdf",
          sup / "Additional_file_4_Top2_dotplots.pdf")
    upload = OUT / "journal_upload"
    if upload.exists():
        shutil.rmtree(upload)
    for name, src in UPLOAD.items():
        _copy(sup / src, upload / name)
    # S6 (qualitative patterns + redacted quotes) is built from the PRIVATE, author-
    # reviewed review sheet, only when it exists. Never auto-created as a placeholder.
    # S6 is NOT part of the published supplement: it holds participant quotes, so
    # build_s6_supplement writes it to outputs/ (private, git-ignored), not supplement/.
    if (ROOT / "data" / "qualitative" / "S6_quote_review_PRIVATE.xlsx").exists():
        try:
            import build_s6_supplement
            build_s6_supplement.main()
        except Exception as e:  # keep the pipeline green even if S6 inputs are absent/incomplete
            print(f"  [S6] not built ({e})")


def main() -> None:
    for stage in STAGES:
        run_stage(stage)
    tidy()
    # Release gate: seven assertions over the assembled supplement -> VALIDATION_REPORT.md.
    print(f"\n{'=' * 60}\n=== validate_release.py\n{'=' * 60}", flush=True)
    rc = subprocess.run([PY, "validate_release.py"], cwd=str(ROOT)).returncode
    if rc != 0:
        print("\n!! RELEASE VALIDATION FAILED — see VALIDATION_REPORT.md")
        sys.exit(rc)
    print(
        "\nPipeline complete.\n"
        "  Paper/supplement artifacts : outputs/figures/, metadata/, supplement/\n"
        "  Journal upload (5 files)   : outputs/journal_upload/\n"
        "  Provenance (intermediates) : outputs/summaries/\n"
        "  Non-canonical (retained)   : outputs/_legacy/\n"
        "  Private (not published)    : data/raw/, data/qualitative/, outputs/analysis_long.*, "
        "outputs/themes/open_questions/"
    )


if __name__ == "__main__":
    main()
