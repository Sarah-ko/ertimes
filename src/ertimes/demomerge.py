from pathlib import Path
import pandas as pd
from demodata import download_data

def load_hospital_data(filepath: str | Path) -> pd.DataFrame:
    df = pd.read_csv(filepath)


    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^\w]", "", regex=True)
    )

    return df
 
    """This function loads hospital data from our .csv data file."""


def standardize_county(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" county", "", regex=False)
    )
    """This function standardizes county names by gettind rid of whitespace, 
    making names lowercase, and removing the word 'county' from each."""

def merge_datasets(hospital_filepath: str | Path) -> pd.DataFrame:
    hospital_df = load_hospital_data(hospital_filepath)
    demo_df = download_data("calidemodata")

    possible_cols = ["county", "county_name", "countyname"]

    county_col = None
    for col in possible_cols:
        if col in hospital_df.columns:
            county_col = col # looks for county columns
            break

    if county_col is None:
        raise ValueError("No county column found in hospital dataset.") # adds an option if there is no county column

    hospital_df = hospital_df.rename(columns={county_col: "county"}) # renames county
    hospital_df["county"] = standardize_county(hospital_df["county"])
    demo_df["county"] = standardize_county(demo_df["county"])

    merged_df = pd.merge(hospital_df, demo_df, on="county", how="left") # uses county as key and does a left merge
    return merged_df
"""This function loads both datasets, standardizes them, and merges the hospital and demographic datasets using county as the key."""

def test_merge(filepath: str | Path) -> bool:
    try:
        print("Merging datasets...")
        df = merge_datasets(filepath)

        print("Success.")
        print(df.head())
        print("\nShape:", df.shape)
        print("\nColumns:", df.columns.tolist())

        missing = df["apercless9grade"].isna().sum()
        print(f"\nRows missing demographic data: {missing}")

        df.to_csv("merged_output.csv", index=False)
        print("\nSaved merged data to merged_output.csv")

        return True

    except Exception as e:
        print("Failed:", e) # prints "Failed" so the user can see if it goes wrong.
        return False
    """This function runs the dataset merge, prints summary information, 
and saves the merged output to a CSV file, also giving a print statement 
when it runs correctly."""

if __name__ == "__main__":
    file_path = Path(__file__).resolve().parent / "data" / "Emergency Department Volume and Capacity - Catalog - ED_COMBINE_AL.csv"
    test_merge(file_path) # checks file path for correct hospital data file
