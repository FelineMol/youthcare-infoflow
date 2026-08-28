"""
run_build_open_question_tables.py

Extracts all open-ended responses from analysis_long.csv,
maps them to themes based on validated Dutch question text,
and exports structured tables for qualitative analysis.

Outputs:
    outputs/themes/open_questions/open_questions_all_themes.csv
    outputs/themes/open_questions/open_questions_<theme>.csv
"""

import os
import pandas as pd

# Theme order consistent with the rest of the analysis pipeline
THEME_ORDER = [
    "Experience",
    "Overview/Insight",
    "Information exchange",
    "Control",
    "Effort",
]


def ensure_dir(path: str) -> None:
    """Create output directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def normalize_text(series: pd.Series) -> pd.Series:
    """Standardize string formatting."""
    return series.astype(str).str.strip()


def map_theme_from_open_bundle(bundle_id: str) -> str:
    """
    Map open-ended questions to themes based on validated Dutch question text.
    This avoids unreliable keyword-only matching.
    """
    text = str(bundle_id).lower().strip()

    # Control (Regie)
    if "regie" in text:
        return "Control"

    # Effort (Tijd, moeite, energie)
    if any(word in text for word in ["tijd", "moeite", "energie", "inspanning"]):
        return "Effort"

    # Information Exchange
    if any(phrase in text for phrase in [
        "informatie met elkaar delen",
        "informatie te delen",
        "informatie te vinden",
        "informatie te gebruiken",
        "informatie uitwisselen",
        "verhaal te vertellen en te delen",
        "gegevens te delen",
        "gegevens uitwisselen",
        "informatieoverdracht",
        "informatieoverdracht",
        "informatieoverdracht",
        "info te delen",
        "info te vinden",
        "info met elkaar delen"
    ]):
        return "Information exchange"

    # Overview / Insight (explicit combination)
    if "inzicht en overzicht" in text:
        return "Overview/Insight"

    # Experience (general experience obtaining insight/overview)
    if any(phrase in text for phrase in [
        "overzicht te krijgen",
        "inzicht te krijgen",
        "goed beeld te krijgen",
        "hoe het voor mij was",
        "hoe het voor ons was",
    ]):
        return "Experience"

    return "Other"


def build_open_question_tables(
    analysis_long_csv: str,
    output_dir: str = "outputs/themes/open_questions",
) -> pd.DataFrame:
    """
    Builds tables of open-text responses grouped by theme.
    """

    ensure_dir(output_dir)

    # Load data
    df = pd.read_csv(analysis_long_csv).fillna("")

    # Normalize text fields
    for col in ["bundle_id", "persona", "group", "organization", "scale_type"]:
        if col in df.columns:
            df[col] = normalize_text(df[col])

    # Identify open-ended responses
    open_mask = df["scale_type"].str.lower().isin(
        ["open", "text", "open_text", "qualitative"]
    ) | df["bundle_id"].str.contains("open", case=False, na=False)

    open_df = df[open_mask].copy()

    if open_df.empty:
        raise ValueError(
            "No open-ended responses found. Check the 'scale_type' column in analysis_long.csv."
        )

    # Map themes
    open_df["theme_label_en"] = open_df["bundle_id"].apply(
        map_theme_from_open_bundle
    )

    # Use the correct response column
    if "response_text" in open_df.columns:
        open_df["response_clean"] = normalize_text(open_df["response_text"])
    elif "response_raw" in open_df.columns:
        open_df["response_clean"] = normalize_text(open_df["response_raw"])
    else:
        raise ValueError(
            "No response text column found. Expected 'response_text' or 'response_raw'."
        )

    # Keep only non-empty responses
    open_df = open_df[open_df["response_clean"] != ""].copy()

    # Select relevant columns
    open_df = open_df[
        [
            "theme_label_en",
            "bundle_id",
            "persona",
            "group",
            "organization",
            "response_clean",
        ]
    ].rename(columns={"response_clean": "response_text"})

    # Order themes
    open_df["theme_label_en"] = pd.Categorical(
        open_df["theme_label_en"],
        categories=THEME_ORDER + ["Other"],
        ordered=True,
    )

    open_df = open_df.sort_values(
        ["theme_label_en", "bundle_id", "group", "persona"],
        kind="stable",
    ).reset_index(drop=True)

    # Save master file
    master_path = os.path.join(
        output_dir, "open_questions_all_themes.csv"
    )
    open_df.to_csv(master_path, index=False)
    print(f"Saved {master_path}")

    # Save per-theme files
    for theme in open_df["theme_label_en"].dropna().unique():
        subset = open_df[open_df["theme_label_en"] == theme]
        if subset.empty:
            continue

        safe_theme = (
            str(theme)
            .replace("/", "-")
            .replace(" ", "_")
            .lower()
        )

        theme_path = os.path.join(
            output_dir, f"open_questions_{safe_theme}.csv"
        )
        subset.to_csv(theme_path, index=False)
        print(f"Saved {theme_path}")

    return open_df


def main():
    build_open_question_tables(
        analysis_long_csv="outputs/analysis_long.csv",
        output_dir="outputs/themes/open_questions",
    )


if __name__ == "__main__":
    main()