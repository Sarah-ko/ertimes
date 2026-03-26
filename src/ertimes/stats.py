import re
import numpy as np
import pandas as pd
from ertimes.io import download_emergency_data


def county_capacity_summary(state: str) -> pd.DataFrame:
    """
    Return a county-level summary of emergency department capacity data.

    Parameters
    ----------
    state : str
        Name of the state to download data for.

    Returns
    -------
    pd.DataFrame
        DataFrame with one row per county containing total visits,
        total ED stations, total licensed beds, and visits per station.
    """
    df = download_emergency_data(state)

    summary = (
        df.groupby("CountyName")
        .agg(
            total_visits=("Tot_ED_NmbVsts", "sum"),
            total_stations=("EDStations", "sum"),
            total_beds=("LICENSED_BED_SIZE", "sum"),
        )
        .reset_index()
    )

    summary["visits_per_station"] = (
        summary["total_visits"] / summary["total_stations"]
    )

    return summary


def _bed_size_to_numeric(value: object) -> float:
    """
    Convert a LICENSED_BED_SIZE category into an approximate numeric value.

    Examples
    --------
    '1-49' -> 25.0
    '50-99' -> 74.5
    '500+' -> 500.0
    """
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
    """
    Find hospitals with relatively high visit volume but relatively low capacity.

    Capacity is based on:
      - EDStations
      - LICENSED_BED_SIZE (converted from category to approximate numeric size)

    A hospital is flagged when:
      - its visit percentile is >= high_visit_quantile
      - its capacity percentile is <= low_capacity_quantile

    Returns a DataFrame sorted by mismatch_score descending.

    Parameters
    ----------
    df : pd.DataFrame
        Input hospital data.
    visit_col, stations_col, bed_col, facility_col, county_col, year_col : str
        Column names in df.
    high_visit_quantile : float
        Percentile threshold for "high visits".
    low_capacity_quantile : float
        Percentile threshold for "low capacity".
    min_visits : int | None
        Optional minimum visits threshold before a hospital is considered.

    Returns
    -------
    pd.DataFrame
        Subset of hospitals flagged for capacity-volume mismatch, with helper columns.
    """
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


def year_range(data: pd.DataFrame) -> tuple[str, str]:
    earliest_year = data["year"].min()
    latest_year = data["year"].max()
    return (
        "earliest year: " + str(earliest_year),
        "latest year: " + str(latest_year),
    )