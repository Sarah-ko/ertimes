import pandas as pd
from functools import reduce

COUNTY_COLUMNS = {
    "a": "acounty9grade",
    "b": "bcountymedfamincome",
    "c": "ccountyfambelowpov",
    "d": "dcountylang",
    "e": "ecountypop<18",
    "f": "fcountyamerind",
}


def standardize_county_names(series: pd.Series) -> pd.Series:
    """
    Standardizes county names by stripping whitespace, converting to lowercase,
    and removing " county" suffix.
    """
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" county", "", regex=False)
    )


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans the dataset by extracting and standardizing county names from multiple columns,
    then merging the relevant data into a single DataFrame with one row per county."""
    df = df.copy()
    blocks = []

    for prefix, main_county_col in COUNTY_COLUMNS.items():
        cols = [col for col in df.columns if col.startswith(prefix)]
        block = df[cols].copy()

        block = block.rename(columns={main_county_col: "county"})

        extra_county_cols = [
            col for col in block.columns
            if col != "county" and col.startswith(prefix + "county")
        ]
        block = block.drop(columns=extra_county_cols)

        block["county"] = standardize_county_names(block["county"])

        block = block[block["county"].notna()]
        block = block[block["county"] != ""]
        block = block[block["county"] != "nan"]

        block = block.drop_duplicates(subset="county")

        blocks.append(block)

    if not blocks:
        raise ValueError("No county-based blocks were found in the dataset.")

    merged = reduce(
        lambda left, right: pd.merge(left, right, on="county", how="outer"),
        blocks
    )

    return merged