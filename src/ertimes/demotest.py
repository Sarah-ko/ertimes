import pandas as pd
from ertimes.demodata import download_data


def test_data_reading(dataset: str) -> bool:
    try:
        print(f"Attempting to read data for {dataset}...")
        df = download_data(dataset)

        if isinstance(df, pd.DataFrame):
            print("Success: Data is a valid Pandas DataFrame.")
            print(f"Success: Found {len(df)} rows of data.")
            print(f"Success: Found {len(df.columns)} columns.")
            print("\nColumns:")
            print(df.columns.tolist())
            print("\nFirst 5 rows:")
            print(df.head())

            if "county" in df.columns:
                print("\nSuccess: 'county' column detected.")
            else:
                print("\nWarning: 'county' column not found.")

            return True

    except Exception as e:
        print(f"Failed to read data: {e}")
        return False


if __name__ == "__main__":
    test_data_reading("calidemodata")
