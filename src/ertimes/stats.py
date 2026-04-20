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


def county_capacity_summary(state: str) -> pd.DataFrame:
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

    Returns
    -------
    pd.DataFrame
        DataFrame with one row per county containing summary metrics.

    Raises
    ------
    ValueError
        If required columns are missing from the dataset.
    """
    df = download_emergency_data(state).copy()

    # Ensure required columns exist before processing
    required_cols = [
        "county_name",
        "total_ed_visits",
        "ed_stations",
        "licensed_bed_size",
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Convert key columns to numeric to avoid aggregation errors
    df["total_ed_visits"] = pd.to_numeric(df["total_ed_visits"], errors="coerce")
    df["ed_stations"] = pd.to_numeric(df["ed_stations"], errors="coerce")

    # Convert bed size categories (e.g., "50-99", "500+") to numeric values
    df["bed_size_numeric"] = df["licensed_bed_size"].apply(_bed_size_to_numeric)

    # Aggregate metrics at the county level
    summary = (
        df.groupby("county_name", dropna=False)
        .agg(
            total_visits=("total_ed_visits", "sum"),
            total_stations=("ed_stations", "sum"),
            total_beds=("bed_size_numeric", "sum"),
        )
        .reset_index()
    )

    # Calculate visits per station safely (avoid division by zero)
    summary["visits_per_station"] = np.where(
        summary["total_stations"] > 0,
        summary["total_visits"] / summary["total_stations"],
        np.nan,
    )

    return summary


def rank_counties_by_burden(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Rank counties by emergency department burden.

    Counties are sorted in descending order of visits per station,
    where higher values indicate greater strain on ED capacity.

    Parameters
    ----------
    summary : pd.DataFrame
        DataFrame produced by county_capacity_summary, containing
        'visits_per_station'.

    Returns
    -------
    pd.DataFrame
        Ranked DataFrame sorted by burden (highest first).

    Raises
    ------
    ValueError
        If 'visits_per_station' column is missing.
    """

    # Ensure required column exists
    if "visits_per_station" not in summary.columns:
        raise ValueError("summary must include 'visits_per_station' column")

    ranked = summary.copy()

    # Sort counties by burden (highest first)
    ranked = ranked.sort_values(
        by="visits_per_station",
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
>>>>>>> 07a3c5930e7d0dc865cad0b62c2931803661d5c6

    Returns
    -------
    pd.DataFrame
<<<<<<< HEAD
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
        One-row DataFrame containing the selected county's summary metrics.

    Raises
    ------
    ValueError
        If required columns are missing or the county is not found.
    """
    required_cols = [
        "county_name",
        "total_visits",
        "total_stations",
        "total_beds",
        "visits_per_station",
    ]
    missing = [col for col in required_cols if col not in summary.columns]
    if missing:
        raise ValueError(f"summary is missing required columns: {missing}")

    report = summary[summary["county_name"] == county_name].copy()

    if report.empty:
        raise ValueError(f"No county found with name '{county_name}'")

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
    high_visit_quantile: float = 0.75,
    low_capacity_quantile: float = 0.25,
    min_visits: int | None = None,
) -> pd.DataFrame:
    df = clean_data(df)
    required_cols = [visit_col, stations_col, bed_col, facility_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if not 0 < high_visit_quantile < 1:
        raise ValueError("high_visit_quantile must be between 0 and 1")

    if not 0 < low_capacity_quantile < 1:
        raise ValueError("low_capacity_quantile must be between 0 and 1")

    working = df.copy()

    working["bed_size_numeric"] = working[bed_col].apply(_bed_size_to_numeric)
    working[visit_col] = pd.to_numeric(working[visit_col], errors="coerce")
    working[stations_col] = pd.to_numeric(working[stations_col], errors="coerce")

    working = working.dropna(
        subset=[visit_col, stations_col, "bed_size_numeric"]
    ).copy()

    if min_visits is not None:
        working = working[working[visit_col] >= min_visits].copy()

    if working.empty:
        return working

    working["visit_percentile"] = working[visit_col].rank(
        pct=True, method="average"
    )
    working["station_percentile"] = working[stations_col].rank(
        pct=True, method="average"
    )
    working["bed_percentile"] = working["bed_size_numeric"].rank(
        pct=True, method="average"
    )

    working["capacity_percentile"] = (
        working["station_percentile"] + working["bed_percentile"]
    ) / 2.0

    working["mismatch_score"] = (
        working["visit_percentile"] - working["capacity_percentile"]
    )

    flagged = working[
        (working["visit_percentile"] >= high_visit_quantile)
        & (working["capacity_percentile"] <= low_capacity_quantile)
    ].copy()

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

    return flagged[output_cols].sort_values(
        by="mismatch_score", ascending=False
    ).reset_index(drop=True)


def compute_capacity_pressure_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes a capacity pressure score (1–10) per facility, grouped by FacilityName2.

    Score interpretation:
        1  = Severely underutilized — low visits/station, adequate primary care,
             mental health, and large bed size
        10 = Severely overutilized — high visits/station, shortage areas for
             primary care and mental health, small bed size

    Parameters:
        df: DataFrame containing the hospital ED data

    Returns:
        DataFrame with FacilityName2 and their capacity_pressure_score (1–10)
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

def plot_hospital_load_distribution(df: pd.DataFrame, group_col: str = 'hospital_ownership', output_dir: str = 'data', save: bool = False):
    """
    Generates a statistical distribution plot of ED visits per station.

    This function cleans the input data by removing records with missing values 
    in the analysis columns, calculates the mean visits per station for the 
    specified grouping, and produces a boxplot to visualize data spread and outliers.

    Args:
        df (pd.DataFrame): The Emergency Department dataset containing 
            'visits_per_station' and the specified grouping column.
        group_col (str, optional): The categorical column used to group the 
            hospitals. Defaults to 'hospital_ownership'.
        output_dir (str, optional): Directory to save output files. Defaults to 'data'.

    Returns:
        tuple: A tuple containing:
            - clean_df (pd.DataFrame): The filtered DataFrame used for the plot.
            - avg_load (pd.Series): The calculated mean values sorted descending.
            
    Raises:
        KeyError: If 'visits_per_station' or group_col are missing from the DataFrame.
    Prepares and cleans emergency department data for load distribution analysis.
    """
    # 1. Data Cleaning: Remove rows where essential metrics or grouping labels are missing.
    # Using .copy() ensures we don't accidentally modify the original source DataFrame.
    clean_df = df.dropna(subset=['visits_per_station', group_col]).copy()
    
    # 2. Validation: Check if the resulting dataset is empty. 
    # This prevents the program from crashing during plotting if no valid data exists.
    if clean_df.empty:
        print(f"Warning: No valid data available for {group_col}.")
        return None
    
    # 3. Numerical Computing: Aggregate data to find the average visit burden per category.
    # Sorting descending provides an immediate insight into which categories have the highest load.
    avg_load = clean_df.groupby(group_col)['visits_per_station'].mean().sort_values(ascending=False)
    
    print(f"\n--- Statistical Summary: Mean Visits per Station by {group_col} ---")
    print(avg_load.head())
    
    # 4. Visualization: Initialize a figure and generate a Seaborn boxplot.
    # Boxplots are chosen over simple bar charts because they visualize the full distribution,
    # including the median, quartiles, and outliers within each hospital category.
    fig = plt.figure(figsize=(12, 6))
    sns.boxplot(data=clean_df, x=group_col, y='visits_per_station', palette="viridis")
    
    # 5. Aesthetic Polishing: Set titles, labels, and rotate x-axis text for readability.
    # Tight_layout is used to ensure labels do not get cut off when the image is saved.
    plt.title(f'Distribution of ED Visits per Station by {group_col}')
    plt.xticks(rotation=45)
    plt.ylabel('Visits per Station')
    plt.tight_layout()
    
    if save:
        # 6. File I/O & Error Handling: Construct path and save the image safely.
        # Using Path objects handles slashes correctly across different operating systems.
        output_path = Path(output_dir) / f"load_distribution_{group_col}.png"
        try:
            # Ensure the target directory exists (mkdir) before attempting to write the file.
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path)
            plt.close(fig)  # Explicitly close the figure to free up system memory after the file is saved.
            print(f"\nSuccess: Distribution plot saved to {output_path}")
        except PermissionError as e:
            # Handle cases where the data folder is locked or read-only.
            print(f"Error: Permission denied when creating directory or saving file: {e}")
            plt.close(fig)
            raise
        except Exception as e:
            # Catch-all for other I/O issues (e.g., disk full) to provide a clear error message.
            print(f"Error: Failed to save plot: {e}")
            plt.close(fig)
            raise
    else:
        plt.close(fig)

def year_range(csv_file:str)->tuple[int,int]:
    df=pd.read_csv(csv_file)
    if "year" not in df.columns:
        raise ValueError("CSV must contain a 'year' column")
    df["year"]=pd.to_numeric(df["year"],errors="coerce")
    return int(df["year"].min()),int(df["year"].max())

def plot_facility_trend(df: pd.DataFrame, facility_id: str):
    """
    Plots a time series of ED visits over time for a single facility.
    """

    required_cols = ['FacilityName2', 'year', 'Tot_ED_NmbVsts']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    facility_df = df[df['FacilityName2'] == facility_id].copy()

    if facility_df.empty:
        raise ValueError(f"No data found for facility '{facility_id}'")

    facility_df['year'] = pd.to_numeric(facility_df['year'], errors='coerce')
    facility_df['Tot_ED_NmbVsts'] = pd.to_numeric(
        facility_df['Tot_ED_NmbVsts'], errors='coerce')

    facility_df = facility_df.dropna(subset=['year', 'Tot_ED_NmbVsts'])

    if facility_df.empty:
        raise ValueError(f"No valid numeric data for facility '{facility_id}'")

    facility_df = facility_df.sort_values('year')

    plt.figure(figsize=(10, 6))
    sns.lineplot(
        data=facility_df,
        x='year',
        y='Tot_ED_NmbVsts',
        marker='o'
    )

    plt.title(f"ED Visits Trend for {facility_id}")
    plt.xlabel("Year")
    plt.ylabel("Total ED Visits")
    plt.tight_layout()

    return plt.gcf()

import pandas as pd

def per_category_burden_report(df, top_n=3):
    """
    Generates a per-category burden report for facilities.

    Parameters:
        df (pd.DataFrame): Dataset containing at least 'FacilityName2', 'Category', 'Visits_Per_Station'
        top_n (int): Number of top facilities to report per category (default 3)

    Returns:
        dict: Dictionary with categories as keys and a list of top facility names as values
    """
    # Ensure required columns exist
    required_cols = ["FacilityName2", "Category", "Visits_Per_Station"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns: {missing_cols}")

    report = {}
    
    # Get unique categories
    categories = df["Category"].unique()
    
    for category in categories:
        # Filter data for this category
        cat_df = df[df["Category"] == category]
        
        # Sort by Visits_Per_Station descending
        cat_df = cat_df.sort_values(by="Visits_Per_Station", ascending=False)
        
        # Select top_n facilities
        top_facilities = cat_df["FacilityName2"].head(top_n).tolist()
        
        # Add to report
        report[category] = top_facilities
    
    return report


def run_er_analysis(df, hospital_name=None):
    """
    ER analysis:
    - Compute year-over-year (YoY) changes
    - Use visits per station as a proxy for utilization
    - Detect mismatches between demand and capacity
    - Generate simple visualizations
    """
    df = clean_data(df)

    # Sort for correct time-series operations
    df = df.sort_values(["facility_id", "year"]).copy()

    # Year-over-year visits change
    df["YoY_Visits"] = (
    df.groupby("facility_id")["total_ed_visits"]
    .transform(lambda x: x.ffill().pct_change())
)

    # Utilization proxy
    df["Utilization"] = df["visits_per_station"]

    # FIX: remove deprecated fill_method argument
    df["Utilization_change"] = (
    df.groupby("facility_id")["Utilization"]
    .transform(lambda x: x.ffill().pct_change())
)

    # Detect mismatch: demand ↑ but utilization not ↑
    df["Mismatch"] = (
        (df["YoY_Visits"] > 0) & (df["Utilization_change"] <= 0)
    )

    # --- Visualization 1: Capacity vs Demand ---
    fig1 = plt.figure()
    plt.scatter(df["visits_per_station"], df["total_ed_visits"])
    plt.xlabel("Capacity (Visits per Station)")
    plt.ylabel("Demand (Total Visits)")
    plt.title("Capacity vs Demand")
    plt.tight_layout()
    plt.show()
    plt.close(fig1)  # Close figure to prevent memory leak

    # --- Visualization 2: Specific hospital trend ---
    if hospital_name:
        data = df[df["facility_name"] == hospital_name]

        if not data.empty:
            fig2 = plt.figure()
            plt.plot(data["year"], data["total_ed_visits"], marker="o")
            plt.title(f"ER Visits Trend - {hospital_name}")
            plt.xlabel("Year")
            plt.ylabel("Visits")
            plt.tight_layout()
            plt.show()
            plt.close(fig2)  # Close figure to prevent memory leak
        else:
            print(f"[Warning] No data found for hospital: {hospital_name}")

    # --- Visualization 3: Average YoY trend ---
    yoy = df.groupby("year")["YoY_Visits"].mean()

    fig3 = plt.figure()
    yoy.plot(marker="o")
    plt.title("Average Year-over-Year Change in ER Visits")
    plt.xlabel("Year")
    plt.ylabel("YoY Change")
    plt.tight_layout()
    plt.show()
    plt.close(fig3)  # Close figure to prevent memory leak

    return df


import os
import folium
from folium.plugins import MarkerCluster
import pandas as pd

# Urban vs rural disparity dashboard
def plot_urban_rural_map(state: str, save: bool = False) -> folium.Map:
    """Downloads emergency data for a given state and displays hospital

    locations on an interactive map.

    Duplicate coordinates are merged to prevent overlapping issues on the map.
    """
    # Download the dataset
    print(f"Loading/Downloading dataset for state: {state}...")
    df = download_emergency_data(state)

    # Check if required columns exist in the downloaded dataset
    required_cols = ["latitude", "longitude", "urban_rural_designation", "facility_name"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(
            f"Downloaded dataset is missing required columns for mapping: {missing}"
        )

    # Drop rows where coordinates are missing
    map_data = df.dropna(subset=["latitude", "longitude"]).copy()

    # Convert coordinates to numeric, handling errors
    map_data["latitude"] = pd.to_numeric(map_data["latitude"], errors="coerce")
    map_data["longitude"] = pd.to_numeric(
        map_data["longitude"], errors="coerce"
    )
    map_data = map_data.dropna(subset=["latitude", "longitude"])

    print(f"Total raw hospital records: {len(map_data)}")
    
    # Group by coordinates and combine hospital names and area types
    map_data = (
        map_data.groupby(["latitude", "longitude"])
        .agg(
            {
                "facility_name": lambda x: "<br>".join(
                    x.dropna().astype(str).unique()
                ),
                "urban_rural_designation": "first",
            }
        )
        .reset_index()
    )

    total_unique_locations = len(map_data)
    print(
        f"Data processing complete. Found {total_unique_locations} unique hospital locations."
    )

    if total_unique_locations == 0:
        print("Warning: No valid hospital coordinates found to plot.")
        return None

    # Initialize map at the mean center of all hospitals
    center_lat = map_data["latitude"].mean()
    center_lon = map_data["longitude"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=7)

    marker_cluster = MarkerCluster(
        spiderfyOnMaxZoom=False,
        showCoverageOnHover=False,
        disableClusteringAtZoom=9,  
    ).add_to(m)

     # Iterate through each unique location and add colored markers
    for _, row in map_data.iterrows():
        hospital_names = row["facility_name"]
        area_type = str(row["urban_rural_designation"]).strip().lower()
        
        # Assign colors and icons based on Urban/Rural status

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
            location=[row["latitude"], row["longitude"]],
            popup=f"<b>Hospital(s):</b><br>{hospital_names}<br><b>Type:</b> {row['urban_rural_designation']}",
            icon=folium.Icon(color=marker_color, icon=marker_icon),
        ).add_to(marker_cluster)
    
    if save:
        # Save the map to an HTML file
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


def mental_health_shortage_analysis(df):
    df = df.copy()

    df['Tot_ED_NmbVsts'] = pd.to_numeric(df['Tot_ED_NmbVsts'], errors='coerce')
    df['EDStations'] = pd.to_numeric(df['EDStations'], errors='coerce')

    df['EDStations'] = df['EDStations'].replace(0, 0.0001)

    df['burden_score'] = df['Tot_ED_NmbVsts'] / df['EDStations']

    avg_burden = df['burden_score'].mean()

    df['high_risk'] = (
        (df['MentalHealthShortageArea'] == 'Yes') &
        (df['burden_score'] > avg_burden)
    )

    return df


def summarize_by_ownership(df,
    ownership_type="HospitalOwnership",
    total_visits="Tot_ED_NmbVsts",
    stations="EDStations",
    visits_perstation="Visits_Per_Station"):
    """
    group hospitals by ownership type and compute summary statistics for burden, volume, & capacity insight
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


def county_facility_counts(
    df: pd.DataFrame,
    county_col: str = "CountyName",
    facility_col: str = "FacilityName2"
) -> pd.DataFrame:
    required = [county_col, facility_col]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    df = df.dropna(subset=[county_col, facility_col])

    counts = (
        df.groupby(county_col)[facility_col]
        .nunique()
        .reset_index()
        .rename(columns={facility_col: "facility_count"})
    )

    return counts.sort_values(
        by="facility_count",
        ascending=False
    ).reset_index(drop=True)


def spike_frequency_pivot(
    df: pd.DataFrame,
    threshold_pct: float = 20.0,
    facility_col: str = 'FacilityName2',
    category_col: str = 'Category',
    visits_col: str = 'Visits_Per_Station'
) -> pd.DataFrame:

    df = df.copy()

    df['yoy_pct_change'] = (
        df.sort_values('year')
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