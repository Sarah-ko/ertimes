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

def rank_counties_by_burden(summary: pd.DataFrame, visits_col: str = "visits_per_station") -> pd.DataFrame:
    """
    Rank counties by emergency department burden.

    Counties are sorted in descending order of visits per station,
    where higher values indicate greater strain on ED capacity.

    Parameters
    ----------
    summary : pd.DataFrame
        DataFrame produced by county_capacity_summary, containing visits-per-station values.
    visits_col : str
        Column name for visits per station. Defaults to the summary output.

    Returns
    -------
    pd.DataFrame
        DataFrame with counties ranked by burden, including burden score.
    """
    if visits_col not in summary.columns:
        raise ValueError(f"Column '{visits_col}' not found in summary DataFrame")

    # Sort by visits per station descending
    ranked = summary.sort_values(visits_col, ascending=False).reset_index(drop=True)

    return ranked


def rank_hospitals_by_visits_per_station(
    df,
    agg: str = "median",
    top_n: int | None = None,
    facility_col: str = "facility_name",
    visits_col: str = "visits_per_station",
) -> pd.DataFrame:
    """
    Rank hospitals by visits per station, aggregated by facility.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing hospital data.
    agg : str
        Aggregation method: 'mean' or 'median'. Defaults to 'median'.
    top_n : int | None
        Number of top hospitals to return. If None, return all.
    facility_col : str
        Column name for facility identifier.
    visits_col : str
        Column name for visits per station.

    Returns
    -------
    pd.DataFrame
        Ranked DataFrame with facility_name and aggregated visits_per_station.
    """
    required_cols = [facility_col, visits_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Aggregate by facility
    if agg == "mean":
        aggregated = df.groupby(facility_col)[visits_col].mean().reset_index()
    elif agg == "median":
        aggregated = df.groupby(facility_col)[visits_col].median().reset_index()
    else:
        raise ValueError("agg must be 'mean' or 'median'")

    # Sort descending
    aggregated = aggregated.sort_values(visits_col, ascending=False).reset_index(drop=True)

    # Limit to top_n if specified
    if top_n is not None:
        aggregated = aggregated.head(top_n)

    return aggregated