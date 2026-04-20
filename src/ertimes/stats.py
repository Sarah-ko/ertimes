import re
import numpy as np
import pandas as pd
from ertimes.io import download_emergency_data
import matplotlib.pyplot as plt
import seaborn as sns
import folium
import os
from pathlib import Path
from folium.plugins import MarkerCluster

DEFAULT_COLUMN_MAP = {
    "facility_id": "oshpd_id",
    "facility_name": "FacilityName2",
    "county_name": "CountyName",
    "hospital_system": "system",
    "licensed_bed_size": "LICENSED_BED_SIZE",
    "tot_ed_visits": "Tot_ED_NmbVsts",
    "ed_stations": "EDStations",
    "ed_burden": "EDDXCount",
    "hospital_ownership": "HospitalOwnership",
    "urban_rural_designation": "UrbanRuralDesi",
    "teaching_designation": "TeachingDesignation",
    "primary_care_shortage_area": "PrimaryCareShortageArea",
    "mental_health_shortage_area": "MentalHealthShortageArea",
    "category": "Category",
    "latitude": "LATITUDE",
    "longitude": "LONGITUDE",
    "visits_per_station": "Visits_Per_Station",
    "year": "year",
}


def _resolve_columns(
    column_map: dict[str, str] | None,
    required_keys: list[str],
) -> dict[str, str]:
    mapping = DEFAULT_COLUMN_MAP.copy()
    if column_map is not None:
        if not isinstance(column_map, dict):
            raise TypeError("column_map must be a dict[str, str] or None")
        mapping.update(column_map)

    missing = [key for key in required_keys if key not in mapping]
    if missing:
        raise KeyError(f"Missing required column keys: {missing}")

    return {key: mapping[key] for key in required_keys}


def county_capacity_summary(state: str, column_map: dict[str, str] | None = None) -> pd.DataFrame:
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
    column_map : dict[str, str] | None
        Optional mapping from generic column keys to actual DataFrame columns.

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
    cols = _resolve_columns(
        column_map,
        [
            "county_name",
            "tot_ed_visits",
            "ed_stations",
            "licensed_bed_size",
        ],
    )

    # Convert key columns to numeric to avoid aggregation errors
    df[cols["ed_stations"]] = pd.to_numeric(df[cols["ed_stations"]], errors="coerce")
    df[cols["tot_ed_visits"]] = pd.to_numeric(df[cols["tot_ed_visits"]], errors="coerce")

    # Convert bed size categories (e.g., "50-99", "500+") to numeric values
    df["bed_size_numeric"] = df[cols["licensed_bed_size"]].apply(_bed_size_to_numeric)

    # Aggregate metrics at the county level
    summary = (
        df.groupby(cols["county_name"], dropna=False)
        .agg(
            total_visits=(cols["tot_ed_visits"], "sum"),
            total_stations=(cols["ed_stations"], "sum"),
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
        "CountyName",
        "total_visits",
        "total_stations",
        "total_beds",
        "visits_per_station",
    ]
    missing = [col for col in required_cols if col not in summary.columns]
    if missing:
        raise ValueError(f"summary is missing required columns: {missing}")

    report = summary[summary["CountyName"] == county_name].copy()

    if report.empty:
        raise ValueError(f"No county found with name '{county_name}'")

    return report.reset_index(drop=True)

def _bed_size_to_numeric(value: object) -> float:
    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    if text.endswith("+"):
        number = text[:-1]
        if number.isdigit():
            return float(number)
        return np.nan

    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", text)
    if match:
        low = float(match.group(1))
        high = float(match.group(2))
        return (low + high) / 2.0

    return np.nan


def find_capacity_volume_mismatch(
    df: pd.DataFrame,
    *,
    visit_col: str = "Tot_ED_NmbVsts",
    stations_col: str = "EDStations",
    bed_col: str = "LICENSED_BED_SIZE",
    facility_col: str = "FacilityName2",
    county_col: str = "CountyName",
    year_col: str = "year",
    column_map: dict[str, str] | None = None,
    high_visit_quantile: float = 0.75,
    low_capacity_quantile: float = 0.25,
    min_visits: int | None = None,
) -> pd.DataFrame:
    if column_map is not None:
        cols = _resolve_columns(
            column_map,
            [
                "tot_ed_visits",
                "ed_stations",
                "licensed_bed_size",
                "facility_name",
                "county_name",
                "year",
            ],
        )
        visit_col = cols["tot_ed_visits"]
        stations_col = cols["ed_stations"]
        bed_col = cols["licensed_bed_size"]
        facility_col = cols["facility_name"]
        county_col = cols["county_name"]
        year_col = cols["year"]

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

    cols = _resolve_columns(
        column_map,
        [
            "facility_name",
            "licensed_bed_size",
            "visits_per_station",
            "primary_care_shortage_area",
            "mental_health_shortage_area",
        ],
    )

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
    df['bed_size_rank'] = df[cols['licensed_bed_size']].map(bed_size_order)

    def safe_mode(series):
        mode = series.mode()
        return mode.iloc[0] if not mode.empty else np.nan

    grouped = df.groupby(cols['facility_name']).agg(
        visits_per_station   = (cols['visits_per_station'],      'median'),
        primary_care_shortage = (cols['primary_care_shortage_area'], safe_mode),
        mental_health_shortage = (cols['mental_health_shortage_area'], safe_mode),
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

    return grouped[[cols['facility_name'], 'capacity_pressure_score']].sort_values(
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
        Input DataFrame.
    subset : list[str] | None
        Columns to check duplicates on.

    Returns
    -------
    pd.DataFrame
        Duplicate rows.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    if subset is not None:
        missing = [col for col in subset if col not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

    duplicates = df[df.duplicated(subset=subset, keep=False)].copy()

    return duplicates

def plot_hospital_load_distribution(
    df: pd.DataFrame,
    group_col: str = 'hospital_ownership',
    column_map: dict[str, str] | None = None,
    output_dir: str = 'data',
):
    """
    Generates a statistical distribution plot of ED visits per station.

    This function cleans the input data by removing records with missing values
    in the analysis columns, calculates the mean visits per station for the
    specified grouping, and produces a boxplot to visualize data spread and outliers.

    Args:
        df (pd.DataFrame): The Emergency Department dataset.
        group_col (str, optional): The grouping column key or actual column name.
            Defaults to the generic 'hospital_ownership' key.
        column_map (dict[str, str] | None): Optional mapping from generic keys to
            actual DataFrame column names.
        output_dir (str, optional): Directory to save output files. Defaults to 'data'.

    Returns:
        tuple: A tuple containing:
            - clean_df (pd.DataFrame): The filtered DataFrame used for the plot.
            - avg_load (pd.Series): The calculated mean values sorted descending.

    Raises:
        KeyError: If required columns are missing from the DataFrame.
    """
    if column_map is not None and group_col in DEFAULT_COLUMN_MAP:
        group_col = _resolve_columns(column_map, [group_col])[group_col]
    visits_col_name = _resolve_columns(column_map, ['visits_per_station'])['visits_per_station'] if column_map is not None else 'Visits_Per_Station'

    # 1. Data Cleaning: Remove rows where essential metrics or grouping labels are missing.
    # Using .copy() ensures we don't accidentally modify the original source DataFrame.
    clean_df = df.dropna(subset=[visits_col_name, group_col]).copy()
    
    # 2. Validation: Check if the resulting dataset is empty. 
    # This prevents the program from crashing during plotting if no valid data exists.
    if clean_df.empty:
        print(f"Warning: No valid data available for {group_col}.")
        return None
    
    # 3. Numerical Computing: Aggregate data to find the average visit burden per category.
    # Sorting descending provides an immediate insight into which categories have the highest load.
    avg_load = clean_df.groupby(group_col)[visits_col_name].mean().sort_values(ascending=False)
    
    print(f"\n--- Statistical Summary: Mean Visits per Station by {group_col} ---")
    print(avg_load.head())
    
    # 4. Visualization: Initialize a figure and generate a Seaborn boxplot.
    # Boxplots are chosen over simple bar charts because they visualize the full distribution,
    # including the median, quartiles, and outliers within each hospital category.
    fig = plt.figure(figsize=(12, 6))
    sns.boxplot(data=clean_df, x=group_col, y=visits_col_name, palette="viridis")
    
    # 5. Aesthetic Polishing: Set titles, labels, and rotate x-axis text for readability.
    # Tight_layout is used to ensure labels do not get cut off when the image is saved.
    plt.title(f'Distribution of ED Visits per Station by {group_col}')
    plt.xticks(rotation=45)
    plt.ylabel('Visits per Station')
    plt.tight_layout()
    
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

def year_range(csv_file:str)->tuple[int,int]:
    df=pd.read_csv(csv_file)
    if "year" not in df.columns:
        raise ValueError("CSV must contain a 'year' column")
    df["year"]=pd.to_numeric(df["year"],errors="coerce")
    return int(df["year"].min()),int(df["year"].max())

def plot_facility_trend(
    df: pd.DataFrame,
    facility_id: str,
    column_map: dict[str, str] | None = None,
):
    """
    Plots a time series of ED visits over time for a single facility.

    Parameters:
        df: Input DataFrame.
        facility_id: Facility identifier used to filter the data.
        column_map: Optional mapping from generic keys to actual column names.
    """

    cols = _resolve_columns(
        column_map,
        ["facility_name", "year", "tot_ed_visits"],
    )

    required_cols = [cols["facility_name"], cols["year"], cols["tot_ed_visits"]]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    facility_df = df[df[cols["facility_name"]] == facility_id].copy()

    if facility_df.empty:
        raise ValueError(f"No data found for facility '{facility_id}'")

    facility_df[cols['year']] = pd.to_numeric(facility_df[cols['year']], errors='coerce')
    facility_df[cols['tot_ed_visits']] = pd.to_numeric(
        facility_df[cols['tot_ed_visits']], errors='coerce')

    facility_df = facility_df.dropna(subset=[cols['year'], cols['tot_ed_visits']])

    if facility_df.empty:
        raise ValueError(f"No valid numeric data for facility '{facility_id}'")

    facility_df = facility_df.sort_values(cols['year'])

    plt.figure(figsize=(10, 6))
    sns.lineplot(
        data=facility_df,
        x=cols['year'],
        y=cols['tot_ed_visits'],
        marker='o'
    )

    plt.title(f"ED Visits Trend for {facility_id}")
    plt.xlabel("Year")
    plt.ylabel("Total ED Visits")
    plt.tight_layout()

    return plt.gcf()

import pandas as pd

def per_category_burden_report(
    df,
    top_n=3,
    column_map: dict[str, str] | None = None,
):
    """
    Generates a per-category burden report for facilities.

    Parameters:
        df (pd.DataFrame): Dataset containing at least facility name, category, and visits-per-station columns.
        top_n (int): Number of top facilities to report per category (default 3)
        column_map (dict[str, str] | None): Optional mapping from generic keys to actual column names.

    Returns:
        dict: Dictionary with categories as keys and a list of top facility names as values
    """
    cols = _resolve_columns(
        column_map,
        ["facility_name", "category", "visits_per_station"],
    )

    # Ensure required columns exist
    required_cols = [cols["facility_name"], cols["category"], cols["visits_per_station"]]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns: {missing_cols}")

    report = {}
    
    # Get unique categories
    categories = df[cols["category"]].unique()
    
    for category in categories:
        # Filter data for this category
        cat_df = df[df[cols["category"]] == category]
        
        # Sort by Visits_Per_Station descending
        cat_df = cat_df.sort_values(by=cols["visits_per_station"], ascending=False)
        
        # Select top_n facilities
        top_facilities = cat_df[cols["facility_name"]].head(top_n).tolist()
        
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

    # Sort for correct time-series operations
    df = df.sort_values(["oshpd_id", "year"]).copy()

    # Year-over-year visits change
    df["YoY_Visits"] = (
    df.groupby("oshpd_id")["Tot_ED_NmbVsts"]
    .transform(lambda x: x.ffill().pct_change())
)

    # Utilization proxy
    df["Utilization"] = df["Visits_Per_Station"]

    # FIX: remove deprecated fill_method argument
    df["Utilization_change"] = (
    df.groupby("oshpd_id")["Utilization"]
    .transform(lambda x: x.ffill().pct_change())
)

    # Detect mismatch: demand ↑ but utilization not ↑
    df["Mismatch"] = (
        (df["YoY_Visits"] > 0) & (df["Utilization_change"] <= 0)
    )

    # --- Visualization 1: Capacity vs Demand ---
    fig1 = plt.figure()
    plt.scatter(df["Visits_Per_Station"], df["Tot_ED_NmbVsts"])
    plt.xlabel("Capacity (Visits per Station)")
    plt.ylabel("Demand (Total Visits)")
    plt.title("Capacity vs Demand")
    plt.tight_layout()
    plt.show()
    plt.close(fig1)  # Close figure to prevent memory leak

    # --- Visualization 2: Specific hospital trend ---
    if hospital_name:
        data = df[df["FacilityName2"] == hospital_name]

        if not data.empty:
            fig2 = plt.figure()
            plt.plot(data["year"], data["Tot_ED_NmbVsts"], marker="o")
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
def plot_urban_rural_map(state: str) -> folium.Map:
    """Downloads emergency data for a given state and displays hospital

    locations on an interactive map.

    Duplicate coordinates are merged to prevent overlapping issues on the map.
    """
    # Download the dataset
    print(f"Loading/Downloading dataset for state: {state}...")
    df = download_emergency_data(state)

    # Check if required columns exist in the downloaded dataset
    required_cols = ["LATITUDE", "LONGITUDE", "UrbanRuralDesi", "FacilityName2"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(
            f"Downloaded dataset is missing required columns for mapping: {missing}"
        )

    # Drop rows where coordinates are missing
    map_data = df.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()

    # Convert coordinates to numeric, handling errors
    map_data["LATITUDE"] = pd.to_numeric(map_data["LATITUDE"], errors="coerce")
    map_data["LONGITUDE"] = pd.to_numeric(
        map_data["LONGITUDE"], errors="coerce"
    )
    map_data = map_data.dropna(subset=["LATITUDE", "LONGITUDE"])

    print(f"Total raw hospital records: {len(map_data)}")
    
    # Group by coordinates and combine hospital names and area types
    map_data = (
        map_data.groupby(["LATITUDE", "LONGITUDE"])
        .agg(
            {
                "FacilityName2": lambda x: "<br>".join(
                    x.dropna().astype(str).unique()
                ),
                "UrbanRuralDesi": "first",
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
    center_lat = map_data["LATITUDE"].mean()
    center_lon = map_data["LONGITUDE"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=7)

    marker_cluster = MarkerCluster(
        spiderfyOnMaxZoom=False,
        showCoverageOnHover=False,
        disableClusteringAtZoom=9,  
    ).add_to(m)

     # Iterate through each unique location and add colored markers
    for _, row in map_data.iterrows():
        hospital_names = row["FacilityName2"]
        area_type = str(row["UrbanRuralDesi"]).strip().lower()
        
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
            location=[row["LATITUDE"], row["LONGITUDE"]],
            popup=f"<b>Hospital(s):</b><br>{hospital_names}<br><b>Type:</b> {row['UrbanRuralDesi']}",
            icon=folium.Icon(color=marker_color, icon=marker_icon),
        ).add_to(marker_cluster)
    
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
    ""


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


def spike_frequency_pivot(
    df: pd.DataFrame,
    threshold_pct: float = 20.0
) -> pd.DataFrame:
    """
    Builds a pivot table of spike frequency aggregated by category.

    A spike is a year-over-year increase in Visits_Per_Station that
    meets or exceeds threshold_pct for a given facility + category.

    Parameters:
        df            : Raw hospital DataFrame
        threshold_pct : Minimum % YoY increase to count as a spike

    Returns:
        Pivot table with Category as index and 'spike_count' as column,
        sorted by spike frequency descending.
    """

    # --- 1. Compute year-over-year % change per facility + category ---
    df = df.copy()

    df['yoy_pct_change'] = (
        df.sort_values('year')
          .groupby(['FacilityName2', 'Category'])['Visits_Per_Station']
          .pct_change() * 100
    )

    # --- 2. Flag spikes ---
    df['is_spike'] = (df['yoy_pct_change'] >= threshold_pct).astype(int)

    # --- 3. Pivot: rows = Category, value = total spike count ---
    pivot = df.pivot_table(
        index='Category',
        values='is_spike',
        aggfunc='sum'
    ).rename(columns={'is_spike': 'spike_count'})

    return pivot.sort_values('spike_count', ascending=False)

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
    ""


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

# check important columns exist, a function that takes in the columns, check the type of column, 
def summarize_by_geography_year_condition(df,
   geography="UrbanRuralDesi",
    total_visits="Tot_ED_NmbVsts",
    stations="EDStations",
    visits_perstation="Visits_Per_Station",
    year="year",
    condition_visit="Category",
    condition_count="EDDXCount"):
    required = [geography, total_visits, stations, visits_perstation, year, condition_count]  # Removed condition_visit from required since it's string
    missing = [col for col in required if col not in df.columns]
    if any(missing):
        raise ValueError(f"Missing required columns: {missing}")
    df = df.copy()
    df[total_visits] = pd.to_numeric(df[total_visits], errors="coerce")
    df[stations] = pd.to_numeric(df[stations], errors="coerce")
    df[visits_perstation] = pd.to_numeric(df[visits_perstation], errors="coerce")
    df[year] = pd.to_numeric(df[year], errors="coerce")
    # Removed to_numeric for condition_visit since it's string (Category)
    df[condition_count] = pd.to_numeric(df[condition_count], errors="coerce")
    df[condition_visit] = pd.to_numeric(df[condition_visit], errors="coerce")

    df = df.dropna(subset=[geography, year])
    summary = df.groupby([geography, year]).agg({
    total_visits: ["mean", "sum"], #volume metric
    stations: ["mean", "sum"], #capacity metric
    visits_perstation: ["mean", "median", "std"], #burden metric
    # Removed condition_visit agg since it's string
    condition_count: ["mean", "sum"]}) #condition count metric
    summary.columns = ["_".join(col) for col in summary.columns]
    summary = summary.reset_index()
    return summary.sort_values(by=[geography, year])  # Removed condition_visit from sort





    


