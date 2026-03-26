import re
import numpy as np
import pandas as pd
from ertimes.io import download_emergency_data


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


def year_range(data: pd.DataFrame) -> tuple[str, str]:
    earliest_year = data["year"].min()
    latest_year = data["year"].max()
    return (
        "earliest year: " + str(earliest_year),
        "latest year: " + str(latest_year),
    )