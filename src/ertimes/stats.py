import re
import numpy as np
import pandas as pd
from ertimes.io import download_emergency_data
import matplotlib.pyplot as plt
import seaborn as sns


def county_capacity_summary(state: str) -> pd.DataFrame:
    df = download_emergency_data(state).copy()

    required_cols = [
        "CountyName",
        "Tot_ED_NmbVsts",
        "EDStations",
        "LICENSED_BED_SIZE",
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["Tot_ED_NmbVsts"] = pd.to_numeric(df["Tot_ED_NmbVsts"], errors="coerce")
    df["EDStations"] = pd.to_numeric(df["EDStations"], errors="coerce")
    df["bed_size_numeric"] = df["LICENSED_BED_SIZE"].apply(_bed_size_to_numeric)

    summary = (
        df.groupby("CountyName", dropna=False)
        .agg(
            total_visits=("Tot_ED_NmbVsts", "sum"),
            total_stations=("EDStations", "sum"),
            total_beds=("bed_size_numeric", "sum"),
        )
        .reset_index()
    )

    summary["visits_per_station"] = np.where(
        summary["total_stations"] > 0,
        summary["total_visits"] / summary["total_stations"],
        np.nan,
    )

    return summary

def rank_counties_by_burden(summary: pd.DataFrame) -> pd.DataFrame:
    if "visits_per_station" not in summary.columns:
        raise ValueError("summary must include 'visits_per_station' column")

    ranked = summary.copy()
    ranked = ranked.sort_values(
        by="visits_per_station",
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)

    return ranked

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
    high_visit_quantile: float = 0.75,
    low_capacity_quantile: float = 0.25,
    min_visits: int | None = None,
) -> pd.DataFrame:
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

    # --- 1. Bed size ordinal mapping (larger = more capacity = less pressure) ---
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
    df['bed_size_rank'] = df['LICENSED_BED_SIZE'].map(bed_size_order)

    # --- 2. Aggregate by facility (median for numeric, mode for categorical) ---
    def safe_mode(series):
        mode = series.mode()
        return mode.iloc[0] if not mode.empty else np.nan

    grouped = df.groupby('FacilityName2').agg(
        visits_per_station   = ('Visits_Per_Station',      'median'),
        primary_care_shortage = ('PrimaryCareShortageArea', safe_mode),
        mental_health_shortage = ('MentalHealthShortageArea', safe_mode),
        bed_size_rank        = ('bed_size_rank',            'median')
    ).reset_index()

    # --- 3. Normalize Visits_Per_Station to 0–1 ---
    vps_min = grouped['visits_per_station'].min()
    vps_max = grouped['visits_per_station'].max()
    grouped['vps_norm'] = (grouped['visits_per_station'] - vps_min) / (vps_max - vps_min + 1e-9)

    # --- 4. Shortage area penalty: Yes = 1 (adds pressure), No = 0 ---
    grouped['pc_pressure']  = (grouped['primary_care_shortage']  == 'Yes').astype(float)
    grouped['mh_pressure']  = (grouped['mental_health_shortage'] == 'Yes').astype(float)

    # --- 5. Normalize bed size rank inversely (smaller beds = more pressure) ---
    bed_min = grouped['bed_size_rank'].min()
    bed_max = grouped['bed_size_rank'].max()
    grouped['bed_pressure'] = 1 - (grouped['bed_size_rank'] - bed_min) / (bed_max - bed_min + 1e-9)

    # --- 6. Weighted composite score (weights sum to 1.0) ---
    weights = {
        'vps_norm':    0.50,   # Utilization is the primary driver
        'pc_pressure': 0.20,   # Primary care shortage adds pressure
        'mh_pressure': 0.15,   # Mental health shortage adds pressure
        'bed_pressure': 0.15   # Smaller bed size adds pressure
    }

    grouped['raw_score'] = (
        grouped['vps_norm']    * weights['vps_norm']    +
        grouped['pc_pressure'] * weights['pc_pressure'] +
        grouped['mh_pressure'] * weights['mh_pressure'] +
        grouped['bed_pressure'] * weights['bed_pressure']
    )

    # --- 7. Scale raw score (0–1) to final score (1–10) ---
    grouped['capacity_pressure_score'] = (grouped['raw_score'] * 9 + 1).round(2)

    return grouped[['FacilityName2', 'capacity_pressure_score']].sort_values(
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

def plot_hospital_load_distribution(df: pd.DataFrame, group_col: str = 'HospitalOwnership'):
    """
    Prepares and cleans emergency department data for load distribution analysis.
    """
    clean_df = df.dropna(subset=['Visits_Per_Station', group_col]).copy()
    
    if clean_df.empty:
        print(f"Warning: No valid data available for {group_col}.")
        return None
    
    avg_load = clean_df.groupby(group_col)['Visits_Per_Station'].mean().sort_values(ascending=False)
    
    print(f"\n--- Statistical Summary: Mean Visits per Station by {group_col} ---")
    print(avg_load.head())
    
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=clean_df, x=group_col, y='Visits_Per_Station', palette="viridis")
    
    plt.title(f'Distribution of ED Visits per Station by {group_col}')
    plt.xticks(rotation=45)
    plt.ylabel('Visits per Station')
    plt.tight_layout()
    
    output_path = f"data/load_distribution_{group_col}.png"
    plt.savefig(output_path)
    print(f"\nSuccess: Distribution plot saved to {output_path}")

    #julianne year range function
def year_range(csv_file):
   df=pd.read_csv(csv_file)
   earliest_year = df['year'].min()
   latest_year=df['year'].max()
   print(year_range('data/Emergency Department Volume and Capacity - Catalog - ED_COMBINE_AL.csv'))
   return "earliest year: " + str(earliest_year), "latest year: " + str(latest_year)

