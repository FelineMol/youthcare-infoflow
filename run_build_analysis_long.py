import pandas as pd

from src.config import ProjectPaths
from src.io_load import discover_exports, read_forms_export
from src.mapping import load_bundle_mapping_table, build_header_lookup
from src.transform import build_analysis_long_for_export
from src.qc import summarize_likert, summarize_time, summarize_open

def main():
    paths = ProjectPaths.from_here()
    paths.outputs.mkdir(parents=True, exist_ok=True)

    # inputs
    inputs = discover_exports(paths.data_raw)

    # mapping
    mapping_path = paths.data_mapping / "intermediate_bundle_mapping_table_v6.xlsx"
    mapping_df = load_bundle_mapping_table(mapping_path)
    header_lookup = build_header_lookup(mapping_df)

    # Build analysis_long per file (checkpointable)
    all_parts = []
    for f in sorted(inputs, key=lambda x: (x.organization, x.persona, str(x.path))):
        df = read_forms_export(f.path)
        part = build_analysis_long_for_export(
            df=df,
            organization=f.organization,
            persona=f.persona,
            bundle_specs=mapping_df[["bundle_id", "scale_type", "polarity"]],
            header_lookup=header_lookup,
        )
        print(f"Built: {f.organization} {f.persona} -> rows={len(part)}")
        all_parts.append(part)

    analysis_long = pd.concat(all_parts, ignore_index=True)

    # QC: basic sanity
    print("\n=== QC ===")
    print("rows:", len(analysis_long))
    print("respondents:", analysis_long["respondent_id"].nunique())
    print("bundle_ids:", analysis_long["bundle_id"].nunique())
    print("open_rows:", (analysis_long["scale_type"] == "Open").sum())


    # Likert summaries
    likert_by_persona = summarize_likert(
        analysis_long,
        by=["bundle_id", "organization", "persona", "group"]
    )
    likert_by_group = summarize_likert(
        analysis_long,
        by=["bundle_id", "organization", "group"]
    )

    # Time summaries (keep org separate)
    time_counts = summarize_time(
        analysis_long,
        by=["bundle_id", "organization", "persona", "group"]
    )

    # Open summary (counts only)
    open_counts = summarize_open(
        analysis_long,
        by=["bundle_id", "organization", "persona", "group"]
    )

    # percentages rounded to 2 dp for display; counts (integers) preserve exactness
    likert_by_persona.round(2).to_csv(paths.outputs / "likert_summary_by_persona.csv", index=False)
    likert_by_group.round(2).to_csv(paths.outputs / "likert_summary_by_group.csv", index=False)
    time_counts.to_csv(paths.outputs / "time_counts_by_org_persona.csv", index=False)
    open_counts.to_csv(paths.outputs / "open_counts.csv", index=False)



    # Save
    out_csv = paths.outputs / "analysis_long.csv"
    out_xlsx = paths.outputs / "analysis_long.xlsx"
    analysis_long.to_csv(out_csv, index=False)
    analysis_long.to_excel(out_xlsx, index=False)
    print(f"\nSaved:\n- {out_csv}\n- {out_xlsx}")

if __name__ == "__main__":
    main()
