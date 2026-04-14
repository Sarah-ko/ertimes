import pandas as pd

"""
This function cleans the raw dataset. It renames columns to snake_case, removes whitespace from string columns, and handles basic formatting to ensure the data is clean, consistent, and ready to be used for analysis without running into formatting issues later on!
"""

def clean_data(df):

    # Creates a copy to avoid modifying original dataset
    df = df.copy()

    # Converts all column names to "snake_case"
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r'[^a-z0-9]+', '_', regex=True)
        .str.strip('_')
)

    # Manual renames for certain, tricky columns
    rename_dict = {
        'facilityname2': 'facility_name',
        'tot_ed_nmbvsts': 'tot_ed_nmb_vsts',
        'edstations': 'ed_stations',
        'mentalhealthshortagearea': 'mental_health_shortage_area',
        'primarycareshortageare': 'primary_care_shortage_area'
}

    df = df.rename(columns=rename_dict)

    # Cleans up string data - removes extra spaces in 'Yes'/'No' columns
    string_cols = df.select_dtypes(include=['object']).columns
    for col in string_cols:
        df[col] = df[col].astype(str).str.strip()

    return df