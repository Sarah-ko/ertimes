import pandas as pd

# a set of functions that check 
# always used inside the other functions 
# change the columns in the dataframe
# no function 

# Mapping of abbreviated column names to readable names
COLUMN_RENAME_MAP = {
    'oshpd_id': 'facility_id',
    'facilityname2': 'facility_name',
    'countyname': 'county_name',
    'system': 'hospital_system',
    'licensed_bed_size': 'licensed_bed_size',
    'tot_ed_nmbvsts': 'total_ed_visits',
    'edstations': 'ed_stations',
    'eddxcount': 'ed_burden',
    'hospitalownership': 'hospital_ownership',
    'urbanruraldesi': 'urban_rural_designation',
    'teachingdesignation': 'teaching_designation',
    'primarycareshortagearea': 'primary_care_shortage_area',
    'mentalhealthshortagearea': 'mental_health_shortage_area',
    'category': 'category',
    'latitude': 'latitude',
    'longitude': 'longitude',
    'visits_per_station': 'visits_per_station',
    'year': 'year'}


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names to lowercase with underscores."""
    def clean_name(col):
        col = col.strip().lower()                          # Strip spaces and lowercase
        col = col.replace(' ', '_')                        # Replace spaces with underscores
        col = ''.join(c for c in col if c.isalnum() or c == '_')  # Keep only alphanumeric and _
        return col
    
    df.columns = [clean_name(col) for col in df.columns]
    return df


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename abbreviated columns to readable names."""
    # Only rename columns that are in the mapping
    rename_dict = {k: v for k, v in COLUMN_RENAME_MAP.items() if k in df.columns}
    return df.rename(columns=rename_dict)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all cleaning operations to the dataframe."""
    df = clean_column_names(df)
    df = rename_columns(df)
    return df

def clean_yes_no_columns(df: pd.DataFrame, columns: list, fill_missing: str = 'Unknown', convert_to_bool: bool = False) -> pd.DataFrame:
    """
    Clean Yes/No qualitative columns by standardizing values, handling missing data, and optionally converting to boolean.
    
    Parameters:
    - df: The DataFrame to clean.
    - columns: List of column names to clean (e.g., ['primary_care_shortage_area', 'mental_health_shortage_area']).
    - fill_missing: Value to fill missing entries ('Unknown' by default; use 'No' if assuming absence).
    - convert_to_bool: If True, convert 'Yes' to True, 'No' to False, and 'Unknown' to None (for analysis).
    
    Returns:
    - The cleaned DataFrame.
    """
    for col in columns:
        if col in df.columns:
            # Convert to string and standardize
            df[col] = df[col].astype(str).str.strip().str.lower()
            
            # Map variations to standard 'yes'/'no'
            mapping = {
                'yes': 'Yes',
                'y': 'Yes',
                'true': 'Yes',
                '1': 'Yes',
                'no': 'No',
                'n': 'No',
                'false': 'No',
                '0': 'No',
                'nan': fill_missing,  # Handle NaN strings
                '': fill_missing
            }
            df[col] = df[col].map(mapping).fillna(fill_missing)
            
            # Fill any remaining NaN (from original data)
            df[col] = df[col].fillna(fill_missing)
            
            # Optional boolean conversion for analysis
            if convert_to_bool:
                bool_mapping = {'Yes': True, 'No': False, 'Unknown': None}
                df[col] = df[col].map(bool_mapping)
    
    return df
