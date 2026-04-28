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

def generate_county_report(
    summary: pd.DataFrame,
    county_name: str,
    county_col: str = "county_name",
    visits_col: str = "tot_ed_visits",
    stations_col: str = "ed_stations",
    beds_col: str = "licensed_bed_size",
    visits_per_station_col: str = "visits_per_station",
) -> pd.DataFrame:
    """
    Return a one-row county report from a county summary DataFrame.

    Parameters
    ----------
    summary : pd.DataFrame
        DataFrame containing county-level summary metrics.
    county_name : str
        Name of the county to report.
    county_col : str
        Column name for county identifier in the summary table.
    visits_col : str
        Column name for total visits in the summary table.
    stations_col : str
        Column name for total stations in the summary table.
    beds_col : str
        Column name for licensed bed size total in the summary table.
    visits_per_station_col : str
        Column name for visits per station in the summary table.

    Returns
    -------
    pd.DataFrame
        One-row DataFrame containing the selected county's summary metrics.

    Raises
    ------
    ValueError
        If required columns are missing or the county is not found.
    """
    required_cols = [county_col, visits_col, stations_col, beds_col, visits_per_station_col]
    missing = [col for col in required_cols if col not in summary.columns]
    if missing:
        raise ValueError(f"summary is missing required columns: {missing}")

    # Filter to county
    county_data = summary[summary[county_col] == county_name]

    if county_data.empty:
        raise ValueError(f"No county found with name '{county_name}'")

    return county_data.reset_index(drop=True)

def per_category_burden_report(
    df,
    top_n: int = 10,
    facility_col: str = "FacilityName2",
    category_col: str = "Category",
    visits_col: str = "Visits_Per_Station",
) -> dict[str, list[str]]:
    """
    Generate a report of top burdened facilities per category.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing facility data.
    top_n : int
        Number of top facilities per category.
    facility_col : str
        Column name for facility identifier.
    category_col : str
        Column name for category.
    visits_col : str
        Column name for visits per station.

    Returns
    -------
    dict[str, list[str]]
        Dictionary mapping category to list of top facility names.
    """
    required_cols = [facility_col, category_col, visits_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Group by category and get top facilities
    result = {}
    for category, group in df.groupby(category_col):
        top_facilities = (
            group.nlargest(top_n, visits_col)[facility_col]
            .tolist()
        )
        result[category] = top_facilities

    return result

def find_duplicates(
    df,
    subset: list[str] | None = None,
    keep: str = "first",
) -> pd.DataFrame:
    """
    Find duplicate rows in a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to check for duplicates.
    subset : list[str] | None
        Columns to consider for duplicates. If None, use all columns.
    keep : str
        Which duplicates to keep: 'first', 'last', or False.

    Returns
    -------
    pd.DataFrame
        DataFrame containing duplicate rows.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame")

    duplicates = df[df.duplicated(subset=subset, keep=keep)]

    return duplicates

def summarize_by_ownership(df, column_map: dict[str, str] | None = None):
    """
    Summarize hospital data by ownership type.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing hospital data.
    column_map : dict[str, str] | None
        Column mapping.

    Returns
    -------
    pd.DataFrame
        Summary DataFrame grouped by ownership.
    """
    cols = _resolve_columns(column_map, ['hospital_ownership', 'tot_ed_visits', 'ed_stations', 'visits_per_station'])
    
    ownership_type = cols['hospital_ownership']
    total_visits = cols['tot_ed_visits']
    stations = cols['ed_stations']
    visits_perstation = cols['visits_per_station']
    
    #ensure all required columns exist, raise column specific error if not
    required = [ownership_type, total_visits, stations, visits_perstation]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
   
    # create a copy of the original data frame to avoid overwriting/modifying
    df = df.copy()
    
    #ensure columns are read as numeric for numeric analysis
    df[total_visits] = pd.to_numeric(df[total_visits], errors="coerce")
    df[stations] = pd.to_numeric(df[stations], errors="coerce")
    df[visits_perstation] = pd.to_numeric(df[visits_perstation], errors="coerce")
    
    #drop observations that are missing ownership type (our parameter of interest for grouping)
    df = df.dropna(subset=[ownership_type])
    
    # Group by ownership and calculate summary statistics
    summary = df.groupby(ownership_type).agg(
        Tot_ED_NmbVsts_mean=(total_visits, 'mean'),
        Tot_ED_NmbVsts_sum=(total_visits, 'sum'),
        EDStations_mean=(stations, 'mean'),
        EDStations_sum=(stations, 'sum'),
        Visits_Per_Station_mean=(visits_perstation, 'mean'),
        Visits_Per_Station_median=(visits_perstation, 'median'),
        Visits_Per_Station_std=(visits_perstation, 'std')
    ).reset_index()
    
    # Sort by mean visits per station descending
    summary = summary.sort_values('Visits_Per_Station_mean', ascending=False).reset_index(drop=True)
    
    return summary

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