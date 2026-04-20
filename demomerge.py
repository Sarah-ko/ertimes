import pandas as pd
from demodata import download_data


def load_hospital_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)

    # standardize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^\w]", "", regex=True)
    )

    return df


def standardize_county(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" county", "", regex=False)
    )


def merge_datasets(hospital_filepath: str) -> pd.DataFrame:
    # Load datasets
    hospital_df = load_hospital_data(hospital_filepath)
    demo_df = download_data("calidemodata")

    # --- Identify county column in hospital data ---
    # Adjust this if needed after you print columns
    possible_cols = ["county", "county_name", "countyname"]

    county_col = None
    for col in possible_cols:
        if col in hospital_df.columns:
            county_col = col
            break

    if county_col is None:
        raise ValueError("No county column found in hospital dataset.")

    # Rename to match demographic dataset
    hospital_df = hospital_df.rename(columns={county_col: "county"})

    # Standardize county names in both datasets
    hospital_df["county"] = standardize_county(hospital_df["county"])
    demo_df["county"] = standardize_county(demo_df["county"])

    # --- Merge ---
    merged_df = pd.merge(
        hospital_df,
        demo_df,
        on="county",
        how="left"  # keep all hospital rows (important)
    )

    return merged_df


def test_merge(filepath: str):
    try:
        print("Merging datasets...")
        df = merge_datasets(filepath)

        print("Success.")
        print(df.head())
        print("\nShape:", df.shape)
        print("\nColumns:", df.columns.tolist())

        # check for missing demographic merges
        missing = df["apercless9grade"].isna().sum()
        print(f"\nRows missing demographic data: {missing}")

        df.to_csv("merged_output.csv", index=False)
        print("\nSaved merged data to merged_output.csv")

        return True

    except Exception as e:
        print("Failed:", e)
        return False

# The demographic dataset contains county-level averages from 2019–2023. 
# These values were merged with yearly hospital data and treated as constant 
# across years. This allows analysis of how stable population characteristics 
# relate to variation in emergency department utilization over time.

if __name__ == "__main__":
    test_merge("ertimes/data/Emergency Department Volume and Capacity - Catalog - ED_COMBINE_AL.csv")
