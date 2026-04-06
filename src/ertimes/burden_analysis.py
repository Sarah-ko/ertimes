import pandas as pd

def per_category_burden(
    df: pd.DataFrame,
    facility_col: str = "FacilityName2",
    category_col: str = "Category"
) -> pd.DataFrame:
    """
    Calculate the number of visits per facility per category.

    Returns:
        DataFrame with facilities as rows and categories as columns.
    """

    # Validate columns
    required_cols = [facility_col, category_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Drop missing values
    clean_df = df.dropna(subset=required_cols).copy()

    # Count visits per facility per category
    burden_table = (
        clean_df
        .groupby([facility_col, category_col])
        .size()
        .unstack(fill_value=0)
    )

    return burden_table