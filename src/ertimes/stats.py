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

<<<<<<< juliette
    required_cols = [county_col, visits_col, stations_col, bed_col]
=======
    # Ensure required columns exist before processing
    required_cols = [
        "county_name",
        "total_ed_visits",
        "ed_stations",
        "licensed_bed_size",
    ]
    # Ensure dataset has all required fields before analysis
>>>>>>> main
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
        Ranked DataFrame sorted by burden (highest first).

    Raises
    ------
    ValueError
        If the visits per station column is missing.
    """

    if visits_col not in summary.columns:
        raise ValueError(f"summary must include '{visits_col}' column")

    ranked = summary.copy()

    # Sort counties by burden (highest first)
    ranked = ranked.sort_values(
        by=visits_col,
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)

    return ranked


def rank_hospitals_by_visits_per_station(
    df: pd.DataFrame,
    facility_col: str = "facility_name",
    visits_col: str = "visits_per_station",
    agg: str = "median",
    top_n: int | None = None,
) -> pd.DataFrame:
    """
    Rank hospitals (facilities) by visits per station.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe containing facility identifier and visits per station.
    facility_col : str
        Column name for facility identifier. Default 'facility_name'.
    visits_col : str
        Column name containing visits-per-station values. Default 'visits_per_station'.
    agg : str
        Aggregation to use when there are multiple rows per facility. One of
        'median' or 'mean'. Default 'median'.
    top_n : int | None
        If provided, return only the top_n facilities.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns [facility_col, 'visits_per_station', 'rank'] sorted
        by 'visits_per_station' descending.
    """

    if facility_col not in df.columns or visits_col not in df.columns:
        missing = [c for c in (facility_col, visits_col) if c not in df.columns]
        raise ValueError(f"Missing required columns: {missing}")

    if agg not in ("median", "mean"):
        raise ValueError("agg must be 'median' or 'mean'")

    working = df[[facility_col, visits_col]].copy()
    working[visits_col] = pd.to_numeric(working[visits_col], errors="coerce")

    # Aggregate per facility
    if agg == "median":
        grouped = working.groupby(facility_col, dropna=False)[visits_col].median()
    else:
        grouped = working.groupby(facility_col, dropna=False)[visits_col].mean()

    result = grouped.reset_index().rename(columns={visits_col: "visits_per_station"})

    # Sort with NaNs last
    result = result.sort_values(by="visits_per_station", ascending=False, na_position="last").reset_index(drop=True)

    # Add rank (1-based). Ties receive the same rank using dense ranking
    result["rank"] = result["visits_per_station"].rank(method="dense", ascending=False).astype(int)

    if top_n is not None:
        result = result.head(top_n).reset_index(drop=True)

    return result


<<<<<<< juliette
def generate_county_report(
    summary: pd.DataFrame,
    county_name: str,
    county_col: str = "county_name",
    visits_col: str = "tot_ed_visits",
    stations_col: str = "ed_stations",
    beds_col: str = "licensed_bed_size",
    visits_per_station_col: str = "visits_per_station",
) -> pd.DataFrame:
=======
def generate_county_report(summary: pd.DataFrame, county_name: str) -> pd.DataFrame:
    """
    Return a one-row county report from a county summary DataFrame.

    Parameters
    ----------
    summary : pd.DataFrame
        DataFrame containing county-level metrics, such as the output of
        county_capacity_summary().
    county_name : str
        Name of the county to report.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns [facility_col, 'visits_per_station', 'rank'] sorted
        by 'visits_per_station' descending.
    """

    if facility_col not in df.columns or visits_col not in df.columns:
        missing = [c for c in (facility_col, visits_col) if c not in df.columns]
        raise ValueError(f"Missing required columns: {missing}")

    if agg not in ("median", "mean"):
        raise ValueError("agg must be 'median' or 'mean'")

    working = df[[facility_col, visits_col]].copy()
    working[visits_col] = pd.to_numeric(working[visits_col], errors="coerce")

    # Aggregate per facility
    if agg == "median":
        grouped = working.groupby(facility_col, dropna=False)[visits_col].median()
    else:
        grouped = working.groupby(facility_col, dropna=False)[visits_col].mean()

    result = grouped.reset_index().rename(columns={visits_col: "visits_per_station"})

    # Sort with NaNs last
    result = result.sort_values(by="visits_per_station", ascending=False, na_position="last").reset_index(drop=True)

    # Add rank (1-based). Ties receive the same rank using dense ranking
    result["rank"] = result["visits_per_station"].rank(method="dense", ascending=False).astype(int)

    if top_n is not None:
        result = result.head(top_n).reset_index(drop=True)

    return result


def generate_county_report(summary: pd.DataFrame, county_name: str) -> pd.DataFrame:
>>>>>>> main
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
<<<<<<< juliette
    required_cols = [county_col, visits_col, stations_col, beds_col, visits_per_station_col]
    missing = [col for col in required_cols if col not in summary.columns]
    if missing:
        raise ValueError(f"summary is missing required columns: {missing}")

    report = summary[summary[county_col] == county_name].copy()

=======
    required_cols = [
        "county_name",
        "total_visits",
        "total_stations",
        "total_beds",
        "visits_per_station",
    ]
    # Ensure the summary has all required metrics before filtering
    missing = [col for col in required_cols if col not in summary.columns]
    if missing:
        raise ValueError(f"summary is missing required columns: {missing}")
    # Filter dataset to the requested county
    report = summary[summary["county_name"] == county_name].copy()
    # Validate that the county exists in the dataset
>>>>>>> main
    if report.empty:
        raise ValueError(f"No county found with name '{county_name}'")

    # Return clean one-row result with reset index for consistency
    return report.reset_index(drop=True)


def _bed_size_to_numeric(value: object) -> float:
    """
    Convert a hospital bed size value into a numeric value.

    This function standardizes bed size values that may appear
    in different formats in the dataset. Supported formats include:

    - Missing values (returns np.nan)
    - Values ending with "+" (e.g., "200+")
    - Ranges (e.g., "50-99"), converted to the midpoint

    Parameters
    ----------
    value : object
        Bed size value from the dataset.

    Returns
    -------
    float
        Numeric representation of the bed size,
        or np.nan if conversion is not possible.
    """
    # Return NaN if the value is missing
    if pd.isna(value):
        return np.nan

    # Convert value to string and remove whitespace
    text = str(value).strip()

    # Handle values ending with "+" (e.g., "200+")
    if text.endswith("+"):
        number = text[:-1] # Remove "+"
        if number.isdigit():
            return float(number)
        
        # If remaining text is not numeric, return NaN
        return np.nan

    # Handle ranges like "50-99"
    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", text)
    if match:
        low = float(match.group(1))
        high = float(match.group(2))

        # Return midpoint of the range
        return (low + high) / 2.0

    # Return NaN if format is not recognized
    return np.nan


def find_capacity_volume_mismatch(
    df: pd.DataFrame,
    *,
    visit_col: str = "total_ed_visits",
    stations_col: str = "ed_stations",
    bed_col: str = "licensed_bed_size",
    facility_col: str = "facility_name",
    county_col: str = "county_name",
    year_col: str = "year",
    column_map: dict[str, str] | None = None,
    high_visit_quantile: float = 0.75,
    low_capacity_quantile: float = 0.25,
    min_visits: int | None = None,
) -> pd.DataFrame:
    """
    Identify facilities where visit volume appears high relative to capacity.

    This function calculates percentile rankings for visit volume,
    number of ED stations, and licensed bed size. It combines the
    station and bed percentiles into a capacity percentile and
    compares this to visit demand to calculate a mismatch score.
    Facilities with high visit demand and low capacity are flagged.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing facility-level emergency department data.

    visit_col : str, default="total_ed_visits"
        Column containing total ED visit counts.

    stations_col : str, default="ed_stations"
        Column containing number of ED stations.

    bed_col : str, default="licensed_bed_size"
        Column containing licensed bed size values.

    facility_col : str, default="facility_name"
        Column identifying facility names.

    county_col : str, default="county_name"
        Column identifying county names.

    year_col : str, default="year"
        Column identifying year values.

    high_visit_quantile : float, default=0.75
        Percentile threshold used to define high visit volume.

    low_capacity_quantile : float, default=0.25
        Percentile threshold used to define low capacity.

    min_visits : int or None, default=None
        Optional minimum visit filter.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing facilities flagged as potential
        capacity-volume mismatches, sorted by mismatch score.
    """

    # Clean dataset before processing
    df = clean_data(df)

    # Verify required columns exist
    required_cols = [visit_col, stations_col, bed_col, facility_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Validate percentile inputs
    if not 0 < high_visit_quantile < 1:
        raise ValueError("high_visit_quantile must be between 0 and 1")

    if not 0 < low_capacity_quantile < 1:
        raise ValueError("low_capacity_quantile must be between 0 and 1")

    working = df.copy()

    # Convert relevant columns to numeric format
    working["bed_size_numeric"] = working[bed_col].apply(_bed_size_to_numeric)
    working[visit_col] = pd.to_numeric(working[visit_col], errors="coerce")
    working[stations_col] = pd.to_numeric(working[stations_col], errors="coerce")

    # Remove rows with missing required numeric values
    working = working.dropna(
        subset=[visit_col, stations_col, "bed_size_numeric"]
    ).copy()

    # Optionally filter out low-volume facilities
    if min_visits is not None:
        working = working[working[visit_col] >= min_visits].copy()

    # Return early if no data remains
    if working.empty:
        return working

    # Calculate percentile rankings for visits and capacity metrics
    working["visit_percentile"] = working[visit_col].rank(
        pct=True, method="average"
    )
    working["station_percentile"] = working[stations_col].rank(
        pct=True, method="average"
    )
    working["bed_percentile"] = working["bed_size_numeric"].rank(
        pct=True, method="average"
    )

    # Combine station and bed percentiles into overall capacity measure
    working["capacity_percentile"] = (
        working["station_percentile"] + working["bed_percentile"]
    ) / 2.0

    # Calculate mismatch score (higher means more demand than capacity)
    working["mismatch_score"] = (
        working["visit_percentile"] - working["capacity_percentile"]
    )

    # Flag facilities with high demand and low capacity
    flagged = working[
        (working["visit_percentile"] >= high_visit_quantile)
        & (working["capacity_percentile"] <= low_capacity_quantile)
    ].copy()

    # Select output columns dynamically
    output_cols = [
        facility_col,
        county_col if county_col in flagged.columns else None,
        year_col if year_col in flagged.columns else None,
        visit_col,
        stations_col,
        bed_col,
        "bed_size_numeric",
        "visit_percentile",
        "station_percentile",
        "bed_percentile",
        "capacity_percentile",
        "mismatch_score",
    ]
    output_cols = [col for col in output_cols if col is not None]

    # Return sorted results
    return flagged[output_cols].sort_values(
        by="mismatch_score", ascending=False
    ).reset_index(drop=True)


def compute_capacity_pressure_score(
    df: pd.DataFrame,
    *,
    column_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Computes a capacity pressure score (1–10) per facility.

    Parameters:
        df: DataFrame containing the hospital ED data
        column_map: Optional mapping from generic column keys to actual columns.

    Returns:
        DataFrame with facility identifier and their capacity_pressure_score.
    """
    df = clean_data(df)

    bed_size_order = {
        '1-49':    1,
        '50-99':   2,
        '100-149': 3,
        '150-199': 4,
        '200-299': 5,
        '300-499': 6,
        '500+':    7
    }

    df = df.copy()
    df['bed_size_rank'] = df['licensed_bed_size'].map(bed_size_order)

    def safe_mode(series):
        mode = series.mode()
        return mode.iloc[0] if not mode.empty else np.nan

    grouped = df.groupby('facility_name').agg(
        visits_per_station   = ('visits_per_station',      'median'),
        primary_care_shortage = ('primary_care_shortage_area', safe_mode),
        mental_health_shortage = ('mental_health_shortage_area', safe_mode),
        bed_size_rank        = ('bed_size_rank',            'median')
    ).reset_index()

    vps_min = grouped['visits_per_station'].min()
    vps_max = grouped['visits_per_station'].max()
    grouped['vps_norm'] = (grouped['visits_per_station'] - vps_min) / (vps_max - vps_min + 1e-9)

    grouped['pc_pressure']  = (grouped['primary_care_shortage']  == 'Yes').astype(float)
    grouped['mh_pressure']  = (grouped['mental_health_shortage'] == 'Yes').astype(float)

    bed_min = grouped['bed_size_rank'].min()
    bed_max = grouped['bed_size_rank'].max()
    grouped['bed_pressure'] = 1 - (grouped['bed_size_rank'] - bed_min) / (bed_max - bed_min + 1e-9)

    weights = {
        'vps_norm':    0.50,   
        'pc_pressure': 0.20,   
        'mh_pressure': 0.15,   
        'bed_pressure': 0.15   
    }

    grouped['raw_score'] = (
        grouped['vps_norm']    * weights['vps_norm']    +
        grouped['pc_pressure'] * weights['pc_pressure'] +
        grouped['mh_pressure'] * weights['mh_pressure'] +
        grouped['bed_pressure'] * weights['bed_pressure']
    )

    grouped['capacity_pressure_score'] = (grouped['raw_score'] * 9 + 1).round(2)

    return grouped[['facility_name', 'capacity_pressure_score']].sort_values(
        'capacity_pressure_score', ascending=False
    ).reset_index(drop=True)


def find_duplicates(
    df: pd.DataFrame,
    subset: list[str] | None = None,
) -> pd.DataFrame:
    """
    Return all duplicate rows in a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame to check for duplicate rows.

    subset : list[str] | None
        Columns to check duplicates on.
        If None, all columns are used.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing all rows that are duplicates
        of another row in the input DataFrame.

    Raises
    ------
    TypeError
        If df is not a pandas DataFrame.

    ValueError
        If any column in subset does not exist in df.

    Examples
    --------
    >>> df = pd.DataFrame({
    ...     "A": [1, 2, 2],
    ...     "B": [3, 4, 4]
    ... })
    >>> find_duplicates(df)
       A  B
    1  2  4
    2  2  4

    >>> find_duplicates(df, subset=["A"])
       A  B
    1  2  4
    2  2  4
    """

    if not isinstance(df, pd.DataFrame):
        # Ensure input is a pandas DataFrame
        raise TypeError("df must be a pandas DataFrame")

    if subset is not None:
        # Check that all requested columns exist
        missing = [col for col in subset if col not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

    duplicates = df[df.duplicated(subset=subset, keep=False)].copy()

    return duplicates

def plot_hospital_load_distribution(
    df: pd.DataFrame,
    group_col: str = "HospitalOwnership",
    visits_col: str = "Visits_Per_Station",
    output_dir: str = "data",
    save: bool = False,
):
    """
    Generates a statistical distribution plot of ED visits per station.

    This function cleans the input data by removing records with missing values
    in the analysis columns, calculates the mean visits per station for the
    specified grouping, and produces a boxplot to visualize data spread and outliers.

    Args:
        df (pd.DataFrame): The Emergency Department dataset containing
            visits per station and the specified grouping column.
        group_col (str, optional): The categorical column used to group the
            hospitals. Defaults to the raw dataset hospital ownership column.
        visits_col (str, optional): The column for visits per station.
            Defaults to the raw dataset visits-per-station column.
        output_dir (str, optional): Directory to save output files. Defaults to 'data'.
        save (bool, optional): Whether to save the plot. Defaults to False.

    Returns:
        tuple: A tuple containing:
            - clean_df (pd.DataFrame): The filtered DataFrame used for the plot.
            - avg_load (pd.Series): The calculated mean values sorted descending.

    Raises:
        ValueError: If visits_col or group_col are missing from the DataFrame.
    """
    if group_col not in df.columns or visits_col not in df.columns:
        missing = [col for col in (group_col, visits_col) if col not in df.columns]
        raise ValueError(f"Missing required columns: {missing}")

    # 1. Data Cleaning: Remove rows where essential metrics or grouping labels are missing.
    clean_df = df.dropna(subset=[visits_col, group_col]).copy()

    if clean_df.empty:
        print(f"Warning: No valid data available for {group_col}.")
        return None, None

    avg_load = clean_df.groupby(group_col)[visits_col].mean().sort_values(ascending=False)

    print(f"\n--- Statistical Summary: Mean {visits_col} by {group_col} ---")
    print(avg_load.head())

    fig = plt.figure(figsize=(12, 6))
    sns.boxplot(data=clean_df, x=group_col, y=visits_col, palette="viridis")

    plt.title(f'Distribution of {visits_col} by {group_col}')
    plt.xticks(rotation=45)
    plt.ylabel(visits_col.replace('_', ' ').title())
    plt.tight_layout()

    if save:
        output_path = Path(output_dir) / f"load_distribution_{group_col}.png"
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path)
            plt.close(fig)
            print(f"\nSuccess: Distribution plot saved to {output_path}")
        except PermissionError as e:
            print(f"Error: Permission denied when creating directory or saving file: {e}")
            plt.close(fig)
            raise
        except Exception as e:
            print(f"Error: Failed to save plot: {e}")
            plt.close(fig)
            raise
    else:
        plt.close(fig)

    return clean_df, avg_load

def year_range(csv_file:str)->tuple[int,int]:
    # Load the dataset from the provided CSV file path
    df=pd.read_csv(csv_file)
    # Ensure the dataset contains a 'year' column needed for analysis
    if "year" not in df.columns:
        raise ValueError("CSV must contain a 'year' column")
    # Convert year values to numeric, forcing invalid entries to NaN
    df["year"]=pd.to_numeric(df["year"],errors="coerce")
    # Return the minimum and maximum year values as integers
    return int(df["year"].min()),int(df["year"].max())

def plot_facility_trend(
    df: pd.DataFrame,
    facility_id: str,
    facility_col: str = "FacilityName2",
    year_col: str = "year",
    visits_col: str = "Tot_ED_NmbVsts",
):
    """
    Plots a time series of ED visits over time for a single facility.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing at least the facility, year, and visit count columns.
    facility_id : str
        Name of the facility to plot.
    facility_col : str
        Column name identifying facilities. Defaults to the raw dataset facility name.
    year_col : str
        Column name for year values. Defaults to 'year'.
    visits_col : str
        Column name for ED visit totals. Defaults to the raw dataset visits column.

    Returns
    -------
    matplotlib.figure.Figure
        A matplotlib Figure object containing the facility trend plot.

    Raises
    ------
    ValueError
        If required columns are missing, the facility is not found,
        or no valid numeric data is available.
    """
    required_cols = [facility_col, year_col, visits_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    facility_df = df[df[facility_col] == facility_id].copy()
    if facility_df.empty:
        raise ValueError(f"No data found for facility '{facility_id}'")

    facility_df[year_col] = pd.to_numeric(facility_df[year_col], errors='coerce')
    facility_df[visits_col] = pd.to_numeric(facility_df[visits_col], errors='coerce')

    facility_df = facility_df.dropna(subset=[year_col, visits_col])
    if facility_df.empty:
        raise ValueError(f"No valid numeric data for facility '{facility_id}'")

    facility_df = facility_df.sort_values(year_col)

    plt.figure(figsize=(10, 6))
    sns.lineplot(
        data=facility_df,
        x=year_col,
        y=visits_col,
        marker='o'
    )

    plt.title(f"ED Visits Trend for {facility_id}")
    plt.xlabel("Year")
    plt.ylabel("Total ED Visits")
    plt.tight_layout()

    return plt.gcf()


def per_category_burden_report(
    df: pd.DataFrame,
    top_n: int = 3,
    facility_col: str = "FacilityName2",
    category_col: str = "Category",
    visits_col: str = "Visits_Per_Station",
):
    """
    Generates a per-category burden report for facilities.

    Parameters:
        df (pd.DataFrame): Dataset containing at least facility name, category, and visits-per-station columns.
        top_n (int): Number of top facilities to report per category.
        facility_col (str): Column name for facility identifier.
        category_col (str): Column name for facility category.
        visits_col (str): Column name for visits per station.

    Returns:
        dict: Dictionary with categories as keys and a list of top facility names as values.
    """
    required_cols = [facility_col, category_col, visits_col]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns: {missing_cols}")

    report = {}
    categories = df[category_col].unique()

    for category in categories:
        cat_df = df[df[category_col] == category]
        cat_df = cat_df.sort_values(by=visits_col, ascending=False)
        top_facilities = cat_df[facility_col].head(top_n).tolist()
        report[category] = top_facilities

    return report


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
<<<<<<< juliette
    required_cols = [facility_col, year_col, visits_col, visits_per_station_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = clean_data(df)
    df = df.sort_values([facility_col, year_col]).copy()

    df[visits_col] = pd.to_numeric(df[visits_col], errors="coerce")
    df[visits_per_station_col] = pd.to_numeric(df[visits_per_station_col], errors="coerce")

    df["YoY_Visits"] = (
        df.groupby(facility_col)[visits_col]
        .transform(lambda x: x.ffill().pct_change())
    )

    df["Utilization"] = df[visits_per_station_col]
    df["Utilization_change"] = (
        df.groupby(facility_col)["Utilization"]
        .transform(lambda x: x.ffill().pct_change())
    )
=======
   

    df = df.sort_values(["oshpd_id", "year"]).copy()

    df["YoY_Visits"] = df.groupby("oshpd_id")["Tot_ED_NmbVsts"].pct_change()

    df["Utilization"] = df["Visits_Per_Station"]

    df["Utilization_change"] = df.groupby("oshpd_id")["Utilization"].pct_change(fill_method=None)
>>>>>>> main

    df["Mismatch"] = (
        (df["YoY_Visits"] > 0) & (df["Utilization_change"] <= 0)
    )

    fig1 = plt.figure()
    plt.scatter(df[visits_per_station_col], df[visits_col])
    plt.xlabel("Capacity (Visits per Station)")
    plt.ylabel("Demand (Total Visits)")
    plt.title("Capacity vs Demand")
    plt.tight_layout()
    plt.show()
    plt.close(fig1)

    if hospital_name:
        data = df[df[facility_col] == hospital_name]
        if not data.empty:
            fig2 = plt.figure()
            plt.plot(data[year_col], data[visits_col], marker="o")
            plt.title(f"ER Visits Trend - {hospital_name}")
            plt.xlabel("Year")
            plt.ylabel("Visits")
            plt.tight_layout()
            plt.show()
            plt.close(fig2)
        else:
            print(f"[Warning] No data found for hospital: {hospital_name}")

    yoy = df.groupby(year_col)["YoY_Visits"].mean()
    fig3 = plt.figure()
    yoy.plot(marker="o")
    plt.title("Average Year-over-Year Change in ER Visits")
    plt.xlabel("Year")
    plt.ylabel("YoY Change")
    plt.tight_layout()
    plt.show()
    plt.close(fig3)

    return df


import os
import folium
from folium.plugins import MarkerCluster
import pandas as pd

# Urban vs rural disparity dashboard
def plot_urban_rural_map(
    state: str,
    save: bool = False,
    latitude_col: str = "LATITUDE",
    longitude_col: str = "LONGITUDE",
    designation_col: str = "UrbanRuralDesi",
    facility_col: str = "FacilityName2",
) -> folium.Map:
    """Downloads emergency data for a given state and displays hospital

    locations on an interactive map.

    Duplicate coordinates are merged to prevent overlapping issues on the map.
    """
    print(f"Loading/Downloading dataset for state: {state}...")
    df = download_emergency_data(state)

    required_cols = [latitude_col, longitude_col, designation_col, facility_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(
            f"Downloaded dataset is missing required columns for mapping: {missing}"
        )

    map_data = df.dropna(subset=[latitude_col, longitude_col]).copy()
    map_data[latitude_col] = pd.to_numeric(map_data[latitude_col], errors="coerce")
    map_data[longitude_col] = pd.to_numeric(map_data[longitude_col], errors="coerce")
    map_data = map_data.dropna(subset=[latitude_col, longitude_col])

    print(f"Total raw hospital records: {len(map_data)}")

    map_data = (
        map_data.groupby([latitude_col, longitude_col])
        .agg(
            {
                facility_col: lambda x: "<br>".join(x.dropna().astype(str).unique()),
                designation_col: "first",
            }
        )
        .reset_index()
    )

    total_unique_locations = len(map_data)
    print(f"Data processing complete. Found {total_unique_locations} unique hospital locations.")

    if total_unique_locations == 0:
        print("Warning: No valid hospital coordinates found to plot.")
        return None

    center_lat = map_data[latitude_col].mean()
    center_lon = map_data[longitude_col].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=7)

    marker_cluster = MarkerCluster(
        spiderfyOnMaxZoom=False,
        showCoverageOnHover=False,
        disableClusteringAtZoom=9,
    ).add_to(m)

    for _, row in map_data.iterrows():
        hospital_names = row[facility_col]
        area_type = str(row[designation_col]).strip().lower()

        if "urban" in area_type:
            marker_color = "blue"
            marker_icon = "cloud"
        elif "rural" in area_type:
            marker_color = "red"
            marker_icon = "leaf"
        else:
            marker_color = "gray"
            marker_icon = "info-sign"

        folium.Marker(
            location=[row[latitude_col], row[longitude_col]],
            popup=(
                f"<b>Hospital(s):</b><br>{hospital_names}"
                f"<br><b>Type:</b> {row[designation_col]}"
            ),
            icon=folium.Icon(color=marker_color, icon=marker_icon),
        ).add_to(marker_cluster)

    if save:
        output_dir = Path("data")
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"urban_rural_map_{state}.html"
            m.save(str(output_path))
            print(f"\nSuccess: Map saved to {output_path}")
        except PermissionError as e:
            print(f"Error: Permission denied when creating directory or saving file: {e}")
            raise
        except Exception as e:
            print(f"Error: Failed to save map: {e}")
            raise

    return m


<<<<<<< juliette
def mental_health_shortage_analysis(
    df,
    visits_col: str = "Tot_ED_NmbVsts",
    stations_col: str = "EDStations",
    mental_health_col: str = "MentalHealthShortageArea",
):
    df = df.copy()

    required_cols = [visits_col, stations_col, mental_health_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df[visits_col] = pd.to_numeric(df[visits_col], errors="coerce")
    df[stations_col] = pd.to_numeric(df[stations_col], errors="coerce")

    df[stations_col] = df[stations_col].replace(0, 0.0001)
    df["burden_score"] = df[visits_col] / df[stations_col]

    avg_burden = df["burden_score"].mean()
    df["high_risk"] = (
        (df[mental_health_col] == "Yes") &
        (df["burden_score"] > avg_burden)
    )

    return df


def summarize_by_ownership(df, column_map: dict[str, str] | None = None):
=======
def summarize_by_ownership(df,
    ownership_type="HospitalOwnership",
    total_visits="Tot_ED_NmbVsts",
    stations="EDStations",
    visits_perstation="Visits_Per_Station"):
>>>>>>> main
    """
    group hospitals by ownership type and compute summary statistics for burden, volume, & capacity insight
    group hospitals by ownership type and compute summary statistics for burden, volume, & capacity insights
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
   
    #group by different types of ownership, compute summary statistics 
    summary = (df.groupby(ownership_type).agg(**{
            f"{total_visits}_mean": (total_visits, "mean"),
            f"{total_visits}_sum": (total_visits, "sum"),
            f"{stations}_mean": (stations, "mean"),
            f"{stations}_sum": (stations, "sum"),
            f"{visits_perstation}_mean": (visits_perstation, "mean"),
            f"{visits_perstation}_median": (visits_perstation, "median"),
            f"{visits_perstation}_std": (visits_perstation, "std"),}
            ).reset_index())

    #return columns sorted by average efficiency in descending order
    summary = summary.sort_values(by=f"{visits_perstation}_mean", ascending=False)
    
    #output final summary
    return summary



def clean_growth(df, column_map: dict[str, str] | None = None):
    cols = _resolve_columns(column_map, ['tot_ed_visits', 'year', 'facility_name'])
    
    df = df.copy()

    # clear NAs
    df = df.dropna(subset=[cols['tot_ed_visits'], cols['year']])

    # types
    df[cols['year']] = df[cols['year']].astype(int)
    df[cols['tot_ed_visits']] = pd.to_numeric(df[cols['tot_ed_visits']], errors="coerce")

    df = df.sort_values(by=[cols['facility_name'], cols['year']])

    return df



def calculate_growth(df, value_col=None, group_cols=None, time_col=None, pct=True, column_map: dict[str, str] | None = None):
   """
   Parameters:
   - df: Data Frame
   - value_col: column to calculate growth on ('Tot_ED_NmbVsts')
   - group_cols: list of columns to group by ('oshpd_id')
   - time_col: time ('year')
   - pct: if True, returns percent growth; else raw difference
   - column_map: optional mapping for column names
   """
   cols = _resolve_columns(column_map, ['tot_ed_visits', 'facility_name', 'year'])
   
   if value_col is None:
       value_col = cols['tot_ed_visits']
   if group_cols is None:
       group_cols = [cols['facility_name']]
   if time_col is None:
       time_col = cols['year']

   df = df.copy()

   # Sort
   df = df.sort_values(by=group_cols + [time_col])

   # Calculate previous value
   df["prev_value"] = df.groupby(group_cols)[value_col].shift(1)

   # Growth calculation
   if pct:
       df["growth"] = (df[value_col] - df["prev_value"]) / df["prev_value"] * 100
   else:
       df["growth"] = df[value_col] - df["prev_value"]

   return df


def county_facility_counts(
    df: pd.DataFrame,
    county_col: str = None,
    facility_col: str = None,
    column_map: dict[str, str] | None = None
) -> pd.DataFrame:
<<<<<<< juliette
    cols = _resolve_columns(column_map, ['county_name', 'facility_name'])
    
    if county_col is None:
        county_col = cols['county_name']
    if facility_col is None:
        facility_col = cols['facility_name']
    
=======
    # Ensure required columns exist before processing
>>>>>>> main
    required = [county_col, facility_col]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    # Work on a copy to avoid modifying original data
    df = df.copy()
    # Remove rows with missing county or facility information
    df = df.dropna(subset=[county_col, facility_col])
    # Count unique facilities per county
    counts = (
        df.groupby(county_col)[facility_col]
        .nunique()
        .reset_index()
        .rename(columns={facility_col: "facility_count"})
    )
    # Sort counties by number of facilities (highest first)
    return counts.sort_values(
        by="facility_count",
        ascending=False
    ).reset_index(drop=True)


def spike_frequency_pivot(
    df: pd.DataFrame,
    threshold_pct: float = 20.0,
    facility_col: str = None,
    category_col: str = None,
    visits_col: str = None,
    column_map: dict[str, str] | None = None
) -> pd.DataFrame:
    """
    Build a pivot table of spike frequency aggregated by visit category.

    A spike is defined as a year-over-year increase in visits per station
    that meets or exceeds threshold_pct for a given facility and category.
    Spike counts are summed across all facilities, so the result reflects
    how often each category experiences high-growth periods across the
    entire dataset.
    """
    cols = _resolve_columns(column_map, ['facility_name', 'category', 'visits_per_station', 'year'])
    
    if facility_col is None:
        facility_col = cols['facility_name']
    if category_col is None:
        category_col = cols['category']
    if visits_col is None:
        visits_col = cols['visits_per_station']
    year_col = cols['year']
        
    df = df.copy()

    df['yoy_pct_change'] = (
        df.sort_values(year_col)
          .groupby([facility_col, category_col])[visits_col]
          .pct_change(fill_method=None) * 100
    )

    df['is_spike'] = (df['yoy_pct_change'] >= threshold_pct).astype(int)

    pivot = df.pivot_table(
        index=category_col,
        values='is_spike',
        aggfunc='sum'
    ).rename(columns={'is_spike': 'spike_count'})

    return pivot.sort_values('spike_count', ascending=False)


def mental_health_shortage_analysis(
    df,
    visit_col="tot_ed_nmb_vsts",
    station_col="ed_stations",
    shortage_col="mental_health_shortage_area",
    shortage_value="Yes",
    group_col="year",
    percentile_threshold=75,
    top_n=None
):

    """
    Identifies high-risk facilities based on ED burden and mental health shortages
    using a percentile-based definition of high burden.

    A facility is considered "high risk" if:
    - It is in a mental health shortage area, AND
    - Its ED burden (visits per station) is above the specified percentile
      within its group (e.g., year)

    Parameters:
        df (pd.DataFrame): Input dataset
        visit_col (str): Column for ED visits
        station_col (str): Column for ED stations
        shortage_col (str): Column indicating shortage status
        shortage_value (str): Value indicating shortage (e.g., "Yes")
        group_col (str or list): Column(s) for grouping (e.g., year)
        percentile_threshold (int): Percentile cutoff (default = 75)
        top_n (int, optional): Return top N highest-risk facilities

    Returns:
        pd.DataFrame: High-risk facilities
    
    Flow:
        1. Input data set is copied & cleaned
        2. Burden score is created for each facility
        3. Within each group, a percentile score is computed for the burden score (default = 75th percentile)
        4. Facilities are flagged as "high burden" if the exceed the percentile, and flagged as "mental health shortage areas" depending on the data
        5. Risk score is computed (percentile rank (burden) + composite risk (shortage))
        6. Facilities are sorted by risk
        7. A summary of high-risk facility counts is printed by group

    """

    # Convert to numeric: ensures columns are numbers and not "strings"
    df[visit_col] = pd.to_numeric(df[visit_col], errors="coerce")
    df[station_col] = pd.to_numeric(df[station_col], errors="coerce")

    # Handle bad data: removes rows w/ missing values + replaces "0" stations with NaN (to avoid division by 0)
    df = df.dropna(subset=[visit_col, station_col])
    df[station_col] = df[station_col].replace(0, np.nan)
    df = df.dropna(subset=[station_col])

    # Burden score calculation: # of visits/# of available stations (essentially, tells us how overloaded each facility is)
    df["burden_score"] = df[visit_col] / df[station_col]

    # Percentile threshold for each group: calculates the cutoff for the top 75th percentile of facilities for high burden, with regards to the group
    df["burden_percentile_thresh"] = df.groupby(group_col)["burden_score"].transform(
    lambda x: np.percentile(x, percentile_threshold)
    )

    # High burden flag: tells us if hospitals are in the top 75th percentile of burden
    df["high_burden"] = df["burden_score"] > df["burden_percentile_thresh"]

    # Shortage flag: converts "Yes" into "True/False", making it easier to use logic
    df["is_shortage"] = df[shortage_col] == shortage_value

    # Defining high-risk facilities: tells us high burden AND shortage area
    df["high_risk"] = df["is_shortage"] & df["high_burden"]

    # Percentile rank: converts a burden into a relative position (0 to 1)
    df["burden_percentile_rank"] = df.groupby(group_col)["burden_score"].rank(pct=True)

    #Risk score: higher burden -> higher percentile rank; shortage -> +1 point
    df["risk_score"] = (
        df["burden_percentile_rank"] +
        df["is_shortage"].astype(int)
    )

    # Sorting: puts the most at-risk facilities at the top
    df = df.sort_values("risk_score", ascending=False)

    # Selects output type: top_n returns all high-risk hospitals; setting it equal to a number would return that number of facilities
    if top_n is not None:
        result = df.head(top_n)
    else:
        result = df[df["high_risk"]]

    # Summary output: counts the number of high-risk hospitals per group ("year" here)
    summary = result.groupby(group_col).size()
    print("\nHigh-risk facilities per group:")
    print(summary)

    return result


def summarize_by_ownership(df,
    ownership_type="HospitalOwnership",
    total_visits="Tot_ED_NmbVsts",
    stations="EDStations",
    visits_perstation="Visits_Per_Station"):
    """
    group hospitals by ownership type and compute summary statistics for burden, volume, & capacity insights
   
    parameters needed:
    ownership_type: column name representing ownership categories (e.g. nonprofit, government, private, etc)
    total_visits: column name representing total number of emergency department encounters for the facility
    stations: column name representing the number of emergency department treatment stations
    visits_perstation: column name representing number of visits per station in a facility
      """
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
    #group by different types of ownership, compute summary statistics 
    summary = df.groupby(ownership_type).agg({
    total_visits: ["mean", "sum"], #volume metric
    stations: ["mean", "sum"], #capacity metric
    visits_perstation: ["mean", "median", "std"]}) #burden metric
    #flattens column names & resets to have ownership type column 
    summary.columns = ["_".join(col) for col in summary.columns]
    summary = summary.reset_index()
    #return columns sorted by average efficiency in descending order
    summary = summary.sort_values(by=f"{visits_perstation}_mean", ascending=False)
    
    #output final summary
    return summary



def clean_growth(df):
   df = df.copy()


   # clear NAs
   df = df.dropna(subset=["Tot_ED_NmbVsts", "year"])


   # types
   df["year"] = df["year"].astype(int)
   df["Tot_ED_NmbVsts"] = pd.to_numeric(df["Tot_ED_NmbVsts"], errors="coerce")


   df = df.sort_values(by=["FacilityName2", "year"])


   return df



def calculate_growth(df, value_col, group_cols, time_col="year", pct=True):
   
   """
   Parameters:
   - df: Data Frame
   - value_col: column to calculate growth on ('Tot_ED_NmbVsts')
   - group_cols: list of columns to group by ('oshpd_id')
   - time_col: time ('year')
   - pct: if True, returns percent growth; else raw difference
   """


   df = df.copy()


   # Sort
   df = df.sort_values(by=group_cols + [time_col])


   # Calculate previous value
   df["prev_value"] = df.groupby(group_cols)[value_col].shift(1)


   # Growth calculation
   if pct:
       df["growth"] = (df[value_col] - df["prev_value"]) / df["prev_value"] * 100
   else:
       df["growth"] = df[value_col] - df["prev_value"]


   return df


def county_facility_counts(df,county_col="CountyName",facility_col="FacilityName2"):
    required=[county_col,facility_col]
    missing=[col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df=df.copy()
    df=df.dropna(subset=[county_col,facility_col])
    counts=df.groupby(county_col)[facility_col].nunique().reset_index()
    counts=counts.rename(columns={facility_col:"facility_count"})
    return counts.sort_values(by="facility_count",ascending=False).reset_index(drop=True)


    # RETURN: Only high-risk facilities
    return df[df["high_risk"]]