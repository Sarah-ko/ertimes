import re
import numpy as np
import pandas as pd
from ertimes.io import download_emergency_data
from ertimes.clean import clean_data
import matplotlib.pyplot as plt
import seaborn as sns
import folium
import os
from pathlib import Path
from folium.plugins import MarkerCluster
import requests
import json
from typing import Optional, Dict, List
import warnings

def _resolve_columns(column_map: dict[str, str] | None, columns: list[str]) -> dict[str, str]:
    """
    Resolve column names using a mapping dictionary.
    
    If column_map is provided, maps each column name to its mapped value if present,
    otherwise uses the original column name.
    
    Parameters
    ----------
    column_map : dict[str, str] | None
        Dictionary mapping column names to their actual names in the DataFrame.
    columns : list[str]
        List of column names to resolve.
    
    Returns
    -------
    dict[str, str]
        Dictionary mapping each input column name to its resolved name.
    """
    if column_map is None:
        return {col: col for col in columns}
    else:
        return {col: column_map.get(col, col) for col in columns}

def county_capacity_summary(
    state: str,
    county_col: str = "CountyName",
    visits_col: str = "Tot_ED_NmbVsts",
    stations_col: str = "EDStations",
    bed_col: str = "LICENSED_BED_SIZE",
) -> pd.DataFrame:
    """
    Aggregate emergency department capacity metrics at the county level.

    This function downloads ED data for a given state and computes:
    - total ED visits per county
    - total ED stations per county
    - total beds per county (converted to numeric)
    - visits per station (measure of capacity burden)

    Parameters
    ----------
    state : str
        State name used to download emergency department data.
    county_col : str
        Column name for county identifier. Defaults to the raw dataset column.
    visits_col : str
        Column name for total ED visits. Defaults to the raw dataset column.
    stations_col : str
        Column name for ED stations. Defaults to the raw dataset column.
    bed_col : str
        Column name for licensed bed size. Defaults to the raw dataset column.

    Returns
    -------
    pd.DataFrame
        DataFrame with one row per county containing summary metrics.

    Raises
    ------
    ValueError
        If required columns are missing from the dataset.
    """
    df = download_emergency_data(state).copy() # Load and isolate dataset for safe mutation

    required_cols = [county_col, visits_col, stations_col, bed_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Convert key columns to numeric to avoid aggregation errors
    df[visits_col] = pd.to_numeric(df[visits_col], errors="coerce")
    df[stations_col] = pd.to_numeric(df[stations_col], errors="coerce")

    # Convert bed size categories (e.g., "50-99", "500+") to numeric values
    df["bed_size_numeric"] = df[bed_col].apply(_bed_size_to_numeric)

    # Aggregate metrics at the county level
    summary = (
        df.groupby(county_col, dropna=False)
        .agg(
            tot_ed_visits=(visits_col, "sum"),
            ed_stations=(stations_col, "sum"),
            licensed_bed_size=("bed_size_numeric", "sum"),
        )
        .reset_index()
    )

    # Calculate visits per station as a measure of capacity burden
    summary["visits_per_station"] = summary["tot_ed_visits"] / summary["ed_stations"]
    summary["visits_per_station"] = summary["visits_per_station"].replace([np.inf, -np.inf], np.nan)

    return summary

def _bed_size_to_numeric(value: object) -> float:
    """
    Convert bed size categories to numeric values.

    Parameters
    ----------
    value : object
        Bed size category (e.g., "1-49", "50-99", "500+").

    Returns
    -------
    float
        Numeric representation of bed size.
    """
    if pd.isna(value):
        return np.nan
    value_str = str(value).strip()
    if value_str == "1-49":
        return 25.0
    elif value_str == "50-99":
        return 74.5
    elif value_str == "100-199":
        return 149.5
    elif value_str == "200-299":
        return 249.5
    elif value_str == "300-499":
        return 399.5
    elif value_str == "500+":
        return 500.0
    else:
        return np.nan

def find_capacity_volume_mismatch(
    df,
    high_visit_quantile: float = 0.75,
    low_capacity_quantile: float = 0.25,
    facility_col: str = "facility_name",
    county_col: str = "county_name",
    year_col: str = "year",
    visits_col: str = "total_ed_visits",
    stations_col: str = "ed_stations",
    bed_col: str = "licensed_bed_size",
) -> pd.DataFrame:
    """
    Identify hospitals with capacity-volume mismatches.

    A mismatch occurs when a hospital has high visits per station (high burden)
    but low bed capacity.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing hospital data.
    high_visit_quantile : float
        Quantile threshold for high visits per station.
    low_capacity_quantile : float
        Quantile threshold for low bed capacity.
    facility_col : str
        Column name for facility identifier.
    county_col : str
        Column name for county identifier.
    year_col : str
        Column name for year.
    visits_col : str
        Column name for total ED visits.
    stations_col : str
        Column name for ED stations.
    bed_col : str
        Column name for licensed bed size.

    Returns
    -------
    pd.DataFrame
        DataFrame with mismatched hospitals and mismatch scores.
    """
    required_cols = [facility_col, county_col, year_col, visits_col, stations_col, bed_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Copy to avoid modifying original
    df = df.copy()

    # Convert to numeric
    df[visits_col] = pd.to_numeric(df[visits_col], errors="coerce")
    df[stations_col] = pd.to_numeric(df[stations_col], errors="coerce")
    df["bed_numeric"] = df[bed_col].apply(_bed_size_to_numeric)

    # Calculate visits per station
    df["visits_per_station"] = df[visits_col] / df[stations_col]

    # Calculate quantiles
    high_visit_threshold = df["visits_per_station"].quantile(high_visit_quantile)
    low_capacity_threshold = df["bed_numeric"].quantile(low_capacity_quantile)

    # Identify mismatches
    mismatches = df[
        (df["visits_per_station"] >= high_visit_threshold) &
        (df["bed_numeric"] <= low_capacity_threshold)
    ].copy()

    # Calculate mismatch score (higher is worse)
    mismatches["mismatch_score"] = (
        (mismatches["visits_per_station"] - high_visit_threshold) /
        high_visit_threshold
    ) * (
        (low_capacity_threshold - mismatches["bed_numeric"]) /
        low_capacity_threshold
    )

    return mismatches[[facility_col, county_col, year_col, "visits_per_station", "bed_numeric", "mismatch_score"]]

def compute_capacity_pressure_score(
    df,
    facility_col: str = "facility_name",
    visits_col: str = "visits_per_station",
    bed_col: str = "licensed_bed_size",
    primary_shortage_col: str = "primary_care_shortage_area",
    mental_shortage_col: str = "mental_health_shortage_area",
) -> pd.DataFrame:
    """
    Compute a capacity pressure score for hospitals.

    The score combines utilization, bed capacity, and shortage areas.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing hospital data.
    facility_col : str
        Column name for facility identifier.
    visits_col : str
        Column name for visits per station.
    bed_col : str
        Column name for licensed bed size.
    primary_shortage_col : str
        Column name for primary care shortage area.
    mental_shortage_col : str
        Column name for mental health shortage area.

    Returns
    -------
    pd.DataFrame
        DataFrame with facility_name and capacity_pressure_score.
    """
    required_cols = [facility_col, visits_col, bed_col, primary_shortage_col, mental_shortage_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Copy to avoid modifying original
    df = df.copy()

    # Convert bed size to numeric
    df["bed_numeric"] = df[bed_col].apply(_bed_size_to_numeric)

    # Normalize utilization (visits per station)
    util_min = df[visits_col].min()
    util_max = df[visits_col].max()
    df["util_norm"] = (df[visits_col] - util_min) / (util_max - util_min)

    # Normalize bed capacity (inverse, higher beds = lower pressure)
    bed_min = df["bed_numeric"].min()
    bed_max = df["bed_numeric"].max()
    df["bed_norm"] = 1 - (df["bed_numeric"] - bed_min) / (bed_max - bed_min)

    # Shortage flags
    df["shortage_flag"] = (
        (df[primary_shortage_col] == "Yes").astype(int) +
        (df[mental_shortage_col] == "Yes").astype(int)
    )

    # Calculate score (weighted combination)
    df["capacity_pressure_score"] = (
        0.5 * df["util_norm"] +
        0.3 * df["bed_norm"] +
        0.2 * (df["shortage_flag"] / 2)
    ) * 10  # Scale to 1-10

    # Clamp to 1-10
    df["capacity_pressure_score"] = df["capacity_pressure_score"].clip(1, 10)

    # Group by facility (take max score if multiple rows)
    result = df.groupby(facility_col)["capacity_pressure_score"].max().reset_index()

    # Sort descending
    result = result.sort_values("capacity_pressure_score", ascending=False).reset_index(drop=True)

    return result

def mental_health_shortage_analysis(
    df,
    percentile_threshold: float = 80,
    visits_col: str = "tot_ed_nmb_vsts",
    stations_col: str = "ed_stations",
    shortage_col: str = "mental_health_shortage_area",
    year_col: str = "year",
) -> pd.DataFrame:
    """
    Analyze hospitals in mental health shortage areas with high utilization.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing hospital data.
    percentile_threshold : float
        Percentile threshold for high utilization.
    visits_col : str
        Column name for total ED visits.
    stations_col : str
        Column name for ED stations.
    shortage_col : str
        Column name for mental health shortage area.
    year_col : str
        Column name for year.

    Returns
    -------
    pd.DataFrame
        DataFrame with high-risk hospitals.
    """
    required_cols = [visits_col, stations_col, shortage_col, year_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Copy to avoid modifying original
    df = df.copy()

    # Convert to numeric
    df[visits_col] = pd.to_numeric(df[visits_col], errors="coerce")
    df[stations_col] = pd.to_numeric(df[stations_col], errors="coerce")

    # Calculate burden score
    df["burden_score"] = df[visits_col] / df[stations_col]

    # Calculate threshold
    threshold = df["burden_score"].quantile(percentile_threshold / 100)

    # Filter for shortage areas and high burden
    result = df[
        (df[shortage_col] == "Yes") &
        (df["burden_score"] >= threshold)
    ].copy()

    return result

def clean_growth(df, column_map: dict[str, str] | None = None):
    """
    Clean and prepare data for growth calculations.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to clean.
    column_map : dict[str, str] | None
        Column mapping.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame.
    """
    cols = _resolve_columns(column_map, ['oshpd_id', 'year', 'tot_ed_nmb_vsts'])
    oshpd_id = cols['oshpd_id']
    year = cols['year']
    tot_ed_nmb_vsts = cols['tot_ed_nmb_vsts']
    
    # Ensure all required columns exist
    required = [oshpd_id, year, tot_ed_nmb_vsts]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Create a copy of the original data frame to avoid overwriting/modifying
    df = df.copy()
    
    # Ensure columns are read as numeric for numeric analysis
    df[tot_ed_nmb_vsts] = pd.to_numeric(df[tot_ed_nmb_vsts], errors="coerce")
    
    # Drop observations that are missing oshpd_id (our parameter of interest for grouping)
    df = df.dropna(subset=[oshpd_id])
    
    return df

def calculate_growth(df, value_col=None, group_cols=None, time_col=None, pct=True, column_map: dict[str, str] | None = None):
    """
    Calculate year-over-year growth rates.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing time series data.
    value_col : str
        Column name for the value to calculate growth on.
    group_cols : list[str]
        Columns to group by.
    time_col : str
        Column name for time.
    pct : bool
        Whether to calculate percentage growth.
    column_map : dict[str, str] | None
        Column mapping.

    Returns
    -------
    pd.DataFrame
        DataFrame with growth calculations.
    """
    cols = _resolve_columns(column_map, ['oshpd_id', 'year', 'tot_ed_nmb_vsts'])
    oshpd_id = cols['oshpd_id']
    year = cols['year']
    tot_ed_nmb_vsts = cols['tot_ed_nmb_vsts']
    
    if value_col is None:
        value_col = tot_ed_nmb_vsts
    if group_cols is None:
        group_cols = [oshpd_id]
    if time_col is None:
        time_col = year
    
    # Ensure all required columns exist
    required = group_cols + [time_col, value_col]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Create a copy of the original data frame to avoid overwriting/modifying
    df = df.copy()
    
    # Ensure columns are read as numeric for numeric analysis
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
    
    # Sort by group and time
    df = df.sort_values(by=group_cols + [time_col])
    
    # Calculate growth
    if pct:
        df['growth'] = df.groupby(group_cols)[value_col].pct_change() * 100
    else:
        df['growth'] = df.groupby(group_cols)[value_col].diff()
    
    return df

def run_er_analysis(
    df,
    hospital_name=None,
    facility_col: str = "facility_name",
    year_col: str = "year",
    visits_col: str = "total_ed_visits",
    visits_per_station_col: str = "visits_per_station",
):
    """
    ER analysis:
    - Compute year-over-year (YoY) changes
    - Use visits per station as a proxy for utilization
    - Detect mismatches between demand and capacity
    - Generate simple visualizations
    """
    required_cols = [facility_col, year_col, visits_col, visits_per_station_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Copy to avoid modifying original
    df = df.copy()

    # Convert to numeric
    df[visits_col] = pd.to_numeric(df[visits_col], errors="coerce")
    df[visits_per_station_col] = pd.to_numeric(df[visits_per_station_col], errors="coerce")
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")

    # Sort by facility and year
    df = df.sort_values([facility_col, year_col])

    # Calculate YoY changes
    df["YoY_Visits"] = df.groupby(facility_col)[visits_col].pct_change() * 100
    df["Utilization"] = df[visits_per_station_col]

    # Detect mismatches (simple threshold)
    df["Mismatch"] = (df["Utilization"] > df["Utilization"].quantile(0.75)) & (df[visits_col] > df[visits_col].quantile(0.75))

    # Filter to specific hospital if requested
    if hospital_name:
        df = df[df[facility_col] == hospital_name]

    return df

def county_facility_counts(
    df,
    county_col: str = "CountyName",
    facility_col: str = "FacilityName2",
) -> pd.DataFrame:
    """
    Count unique facilities per county.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing facility data.
    county_col : str
        Column name for county.
    facility_col : str
        Column name for facility.

    Returns
    -------
    pd.DataFrame
        DataFrame with county and facility count.
    """
    required_cols = [county_col, facility_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Group by county and count unique facilities
    result = (
        df.groupby(county_col)[facility_col]
        .nunique()
        .reset_index()
        .rename(columns={facility_col: "facility_count"})
    )

    # Sort descending by count
    result = result.sort_values("facility_count", ascending=False).reset_index(drop=True)

    return result

def spike_frequency_pivot(
    df,
    threshold_pct: float = 20.0,
    facility_col: str = "facility_name",
    category_col: str = "category",
    year_col: str = "year",
    visits_col: str = "visits_per_station",
) -> pd.DataFrame:
    """
    Create a pivot table of spike frequencies by category.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing time series data.
    threshold_pct : float
        Percentage threshold for spike detection.
    facility_col : str
        Column name for facility.
    category_col : str
        Column name for category.
    year_col : str
        Column name for year.
    visits_col : str
        Column name for visits per station.

    Returns
    -------
    pd.DataFrame
        Pivot table with spike counts.
    """
    required_cols = [facility_col, category_col, year_col, visits_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Copy to avoid modifying original
    df = df.copy()

    # Convert to numeric
    df[visits_col] = pd.to_numeric(df[visits_col], errors="coerce")
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")

    # Sort by facility, category, year
    df = df.sort_values([facility_col, category_col, year_col])

    # Calculate YoY growth
    df["yoy_growth"] = df.groupby([facility_col, category_col])[visits_col].pct_change() * 100

    # Detect spikes
    df["spike"] = df["yoy_growth"] > threshold_pct

    # Pivot to count spikes per category
    pivot = df.pivot_table(
        index=category_col,
        values="spike",
        aggfunc="sum",
        fill_value=0
    ).rename(columns={"spike": "spike_count"})

    # Sort descending
    pivot = pivot.sort_values("spike_count", ascending=False)

    return pivot

# Census data functions
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY', 'YOUR_API_KEY_HERE')
ACS_YEAR = 2024
TABLE_ID = 'S1903'  # Median Income in the Past 12 Months
BASE_URL = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"

def get_census_data_for_zipcode():
    """
    Fetch California median household income data by zip code from Census Bureau API.
    
    Returns:
    -------
    pd.DataFrame
        DataFrame with zip_code, median_income, county, city columns
    """
    
    if CENSUS_API_KEY == 'YOUR_API_KEY_HERE':
        print("Error: Census API key not set!")
        print("Get a free API key at: https://api.census.gov/data/key_signup.html")
        print("Then set it with: export CENSUS_API_KEY='your_key_here'")
        return None
    
    # Variables to retrieve for Table S1903
    # S1903_C03_001E = Median income
    variables = 'S1903_C03_001E,NAME'
    
    # Get all zip codes in California
    # Census treats ZCTA (Zip Code Tabulation Area) as geography
    params = {
        'get': variables,
        'for': 'zip code tabulation area:*',
        'in': 'state:06',  # 06 is California's FIPS code
        'key': CENSUS_API_KEY
    }
    
    print("Fetching California median income data from Census Bureau...")
    
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if len(data) < 2:
            print("No data returned from Census Bureau API")
            return None
        
        # Convert to DataFrame
        headers = data[0]
        rows = data[1:]
        
        df = pd.DataFrame(rows, columns=headers)
        
        # Clean up the data
        df = df.rename(columns={
            'S1903_C03_001E': 'median_income',
            'NAME': 'name',
            'zip code tabulation area': 'zip_code'
        })
        
        # Convert median_income to numeric, handling missing values
        df['median_income'] = pd.to_numeric(df['median_income'], errors='coerce')
        
        # Filter out rows with missing median income
        df = df[df['median_income'].notna()].copy()
        
        # Extract county and city from NAME field if available
        df['county'] = df['name'].str.extract(r',\s*([A-Za-z\s]+)\s+County,\s+California', expand=False)
        df['city'] = df['name'].str.extract(r'^(.*?),', expand=False)
        
        # Select and reorder columns
        df = df[['zip_code', 'median_income', 'county', 'city']].copy()
        
        # Convert median_income to integer
        df['median_income'] = df['median_income'].astype(int)
        
        print(f"Successfully retrieved {len(df)} zip codes with income data")
        
        return df
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Census API: {e}")
        return None
    except Exception as e:
        print(f"Error processing Census data: {e}")
        return None

def save_to_csv(df, output_path='data/california_median_income_by_zipcode.csv'):
    """
    Save the census data to CSV file.
    
    Parameters:
    -----------
    df : pd.DataFrame
        The income data to save
    output_path : str
        Path where to save the CSV file
    """
    
    # Create data directory if it doesn't exist
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(output_path, index=False)
    print(f"Data saved to {output_path}")
    print(f"\nData preview:")
    print(df.head(10))
    print(f"\nTotal records: {len(df)}")

def display_statistics(df):
    """Display basic statistics about the income data."""
    
    print("\n" + "="*70)
    print("CALIFORNIA MEDIAN INCOME STATISTICS")
    print("="*70)
    print(f"Total zip codes: {len(df)}")
    print(f"Mean median income: ${df['median_income'].mean():,.2f}")
    print(f"Median income: ${df['median_income'].median():,.2f}")
    print(f"Min income: ${df['median_income'].min():,}")
    print(f"Max income: ${df['median_income'].max():,}")
    print(f"Counties: {df['county'].nunique()}")
    print(f"\nCounties represented:")
    print(df['county'].value_counts())
    print("="*70 + "\n")

# Median income functions
def load_california_income_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Load California median household income data by zip code.
    
    Parameters
    ----------
    filepath : str, optional
        Path to a CSV file containing zip code and median income data.
        If None, returns a sample dataset for demonstration.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns: 'zip_code', 'median_income', 'county', 'city'
    """
    if filepath:
        try:
            df = pd.read_csv(filepath) # Load user-provided dataset
            return df
        except FileNotFoundError:
            warnings.warn(f"File {filepath} not found. Returning sample data.")
            return _get_sample_california_income_data()
    else:
        # Use built-in sample data when no file is provided
        return _get_sample_california_income_data()

def _get_sample_california_income_data() -> pd.DataFrame:
    """
    Return sample California median household income data by zip code.
    
    Returns
    -------
    pd.DataFrame
        Sample data with California zip codes and median income values.
    """
    sample_data = {
        'zip_code': [
            '90001', '90002', '90003', '90004', '90005',
            '94102', '94103', '94104', '94105', '94106',
            '92101', '92102', '92103', '92104', '92105',
            '93501', '93502', '93503', '93504', '93505',
            '95401', '95402', '95403', '95404', '95405'
        ],
        'county': [
            'Los Angeles', 'Los Angeles', 'Los Angeles', 'Los Angeles', 'Los Angeles',
            'San Francisco', 'San Francisco', 'San Francisco', 'San Francisco', 'San Francisco',
            'San Diego', 'San Diego', 'San Diego', 'San Diego', 'San Diego',
            'Kern', 'Kern', 'Kern', 'Kern', 'Kern',
            'Sonoma', 'Sonoma', 'Sonoma', 'Sonoma', 'Sonoma'
        ],
        'city': [
            'Los Angeles', 'Los Angeles', 'Los Angeles', 'Los Angeles', 'Los Angeles',
            'San Francisco', 'San Francisco', 'San Francisco', 'San Francisco', 'San Francisco',
            'San Diego', 'San Diego', 'San Diego', 'San Diego', 'San Diego',
            'Bakersfield', 'Bakersfield', 'Bakersfield', 'Bakersfield', 'Bakersfield',
            'Santa Rosa', 'Santa Rosa', 'Santa Rosa', 'Santa Rosa', 'Santa Rosa'
        ],
        'median_income': [
            35000, 38000, 42000, 65000, 48000,
            125000, 135000, 128000, 145000, 110000,
            58000, 62000, 68000, 75000, 72000,
            42000, 45000, 48000, 50000, 52000,
            72000, 78000, 82000, 85000, 88000
        ]
    }
    return pd.DataFrame(sample_data)

def get_income_by_zip(df: pd.DataFrame, zip_code: str) -> Optional[Dict]:
    """
    Get median income information for a specific zip code.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing zip code and income data
    zip_code : str
        The zip code to look up
    
    Returns
    -------
    dict or None
        Dictionary with zip code details if found, None otherwise
    """
    result = df[df['zip_code'] == zip_code] # Filter for matching zip code
    if result.empty:
        return None # Return None if zip code not found
    
    row = result.iloc[0] #Extract the first matching row
    
    #Return relevant fields as a dictionary
    return {
        'zip_code': row['zip_code'],
        'median_income': row['median_income'],
        'county': row['county'],
        'city': row['city']
    }

def get_income_by_county(df: pd.DataFrame, county: str) -> pd.DataFrame:
    """
    Get median income data for all zip codes in a county.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing zip code and income data
    county : str
        The county name
    
    Returns
    -------
    pd.DataFrame
        Filtered DataFrame for the specified county
    """
    # Case-insensitive match on county name
    return df[df['county'].str.lower() == county.lower()].copy()

def get_income_statistics(df: pd.DataFrame, 
                         group_by: Optional[str] = None) -> pd.DataFrame:
    """
    Calculate median income statistics by county or city.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing zip code and income data
    group_by : str, optional
        Column to group by ('county' or 'city'). If None, returns overall stats.
    
    Returns
    -------
    pd.DataFrame
        Statistics table with mean, median, min, max income
    """
    if group_by:
        # Group by specified column and compute summary statistics
        stats = df.groupby(group_by)['median_income'].agg([
            ('mean_income', 'mean'),
            ('median_income', 'median'),
            ('min_income', 'min'),
            ('max_income', 'max'),
            ('count', 'count')
        ]).round(2)
    else:
        # Compute overall statistics without grouping
        stats = pd.DataFrame({
            'mean_income': [df['median_income'].mean()],
            'median_income': [df['median_income'].median()],
            'min_income': [df['median_income'].min()],
            'max_income': [df['median_income'].max()],
            'count': [len(df)]
        }).round(2)
    
    return stats

def filter_by_income_range(df: pd.DataFrame, 
                          min_income: float, 
                          max_income: float) -> pd.DataFrame:
    """
    Filter zip codes by median income range.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing zip code and income data
    min_income : float
        Minimum median income threshold
    max_income : float
        Maximum median income threshold
    
    Returns
    -------
    pd.DataFrame
        Filtered DataFrame with zip codes in the income range
    """
    #Filter rows where income falls within the specified range (inclusive)
    return df[(df['median_income'] >= min_income) & 
              (df['median_income'] <= max_income)].copy()

def display_income_summary(df: pd.DataFrame) -> None:
    # Print formatted summary statistics for quick inspection
    """
    Print a formatted summary of income data.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing income data
    """
    print("\n" + "="*60)
    print("CALIFORNIA MEDIAN INCOME SUMMARY")
    print("="*60)
    print(f"Total zip codes: {len(df)}")
    print(f"Mean income: ${df['median_income'].mean():,.2f}")
    print(f"Median income: ${df['median_income'].median():,.2f}")
    print(f"Min income: ${df['median_income'].min():,}")
    print(f"Max income: ${df['median_income'].max():,}")
    print(f"Counties: {df['county'].nunique()}")
    print("="*60 + "\n")