import os
import warnings
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import requests

from ertimes.io import download_emergency_data

def _resolve_columns(column_map: dict[str, str] | None, columns: list[str]) -> dict[str, str]:
    """
    Resolve column names using a mapping dictionary.

    If column_map is provided, maps each expected column name to its mapped value
    if present. Otherwise, the original expected column name is used.
    """
    if column_map is None:
        return {col: col for col in columns}

    return {col: column_map.get(col, col) for col in columns}


def _safe_minmax(series: pd.Series, default: float = 0.0) -> pd.Series:
    """
    Safely min-max normalize a numeric Series.

    If the series has all equal values, all missing values, or an invalid range,
    return a constant default-valued Series instead of producing NaNs.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    min_val = numeric.min()
    max_val = numeric.max()

    if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
        return pd.Series(default, index=series.index, dtype=float)

    return (numeric - min_val) / (max_val - min_val)


def _yes_flag(series: pd.Series) -> pd.Series:
    """
    Convert Yes/No-like values into 1/0 indicators.
    """
    return series.astype(str).str.strip().str.lower().eq("yes").astype(int)


def county_capacity_summary(
    state: str,
    county_col: str = "CountyName",
    visits_col: str = "Tot_ED_NmbVsts",
    stations_col: str = "EDStations",
    bed_col: str = "LICENSED_BED_SIZE",
) -> pd.DataFrame:
    """
    Aggregate emergency department capacity metrics at the county level.

    Computes total ED visits, total ED stations, total licensed bed size, and
    visits per station for each county.
    """
    df = download_emergency_data(state).copy()

    required_cols = [county_col, visits_col, stations_col, bed_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df[visits_col] = pd.to_numeric(df[visits_col], errors="coerce")
    df[stations_col] = pd.to_numeric(df[stations_col], errors="coerce")
    df["bed_size_numeric"] = df[bed_col].apply(_bed_size_to_numeric)

    summary = (
        df.groupby(county_col, dropna=False)
        .agg(
            tot_ed_visits=(visits_col, "sum"),
            ed_stations=(stations_col, "sum"),
            licensed_bed_size=("bed_size_numeric", "sum"),
        )
        .reset_index()
    )

    summary["visits_per_station"] = summary["tot_ed_visits"] / summary["ed_stations"]
    summary["visits_per_station"] = summary["visits_per_station"].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    return summary


def _bed_size_to_numeric(value: object) -> float:
    """
    Convert bed size categories to numeric midpoint-style values.
    """
    if pd.isna(value):
        return np.nan

    value_str = str(value).strip()

    if value_str == "1-49":
        return 25.0
    if value_str == "50-99":
        return 74.5
    if value_str == "100-199":
        return 149.5
    if value_str == "200-299":
        return 249.5
    if value_str == "300-499":
        return 399.5
    if value_str == "500+":
        return 500.0

    return np.nan

def find_capacity_volume_mismatch(
    df: pd.DataFrame,
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
    Identify hospitals with high visits per station and low bed capacity.
    """
    required_cols = [facility_col, county_col, year_col, visits_col, stations_col, bed_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[visits_col] = pd.to_numeric(work[visits_col], errors="coerce")
    work[stations_col] = pd.to_numeric(work[stations_col], errors="coerce")
    work["bed_numeric"] = work[bed_col].apply(_bed_size_to_numeric)

    work["visits_per_station"] = work[visits_col] / work[stations_col]
    work["visits_per_station"] = work["visits_per_station"].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    high_visit_threshold = work["visits_per_station"].quantile(high_visit_quantile)
    low_capacity_threshold = work["bed_numeric"].quantile(low_capacity_quantile)

    mismatches = work[
        (work["visits_per_station"] >= high_visit_threshold)
        & (work["bed_numeric"] <= low_capacity_threshold)
    ].copy()

    if mismatches.empty:
        return mismatches[
            [facility_col, county_col, year_col, "visits_per_station", "bed_numeric"]
        ].assign(mismatch_score=pd.Series(dtype=float))

    if high_visit_threshold == 0 or low_capacity_threshold == 0:
        mismatches["mismatch_score"] = 0.0
    else:
        mismatches["mismatch_score"] = (
            (mismatches["visits_per_station"] - high_visit_threshold)
            / high_visit_threshold
        ) * (
            (low_capacity_threshold - mismatches["bed_numeric"])
            / low_capacity_threshold
        )

    return mismatches[
        [facility_col, county_col, year_col, "visits_per_station", "bed_numeric", "mismatch_score"]
    ]


def compute_capacity_pressure_score(
    df: pd.DataFrame,
    facility_col: str = "facility_name",
    visits_col: str = "visits_per_station",
    bed_col: str = "licensed_bed_size",
    primary_shortage_col: str = "primary_care_shortage_area",
    mental_shortage_col: str = "mental_health_shortage_area",
) -> pd.DataFrame:
    """
    Compute a 1-10 capacity pressure score for hospitals.

    The score combines:
    - utilization from visits per station,
    - inverse bed capacity,
    - primary care and mental health shortage indicators.

    This implementation avoids NaN scores when all facilities have the same
    utilization or bed-size values.
    """
    required_cols = [
        facility_col,
        visits_col,
        bed_col,
        primary_shortage_col,
        mental_shortage_col,
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()

    work[visits_col] = pd.to_numeric(work[visits_col], errors="coerce")
    work["bed_numeric"] = work[bed_col].apply(_bed_size_to_numeric)

    work["util_norm"] = _safe_minmax(work[visits_col], default=0.0)
    work["bed_norm"] = 1 - _safe_minmax(work["bed_numeric"], default=0.0)

    work["shortage_flag"] = (
        _yes_flag(work[primary_shortage_col])
        + _yes_flag(work[mental_shortage_col])
    )

    work["capacity_pressure_score"] = (
        0.5 * work["util_norm"]
        + 0.3 * work["bed_norm"]
        + 0.2 * (work["shortage_flag"] / 2)
    ) * 10

    work["capacity_pressure_score"] = (
        work["capacity_pressure_score"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
        .clip(1, 10)
    )

    result = (
        work.groupby(facility_col, sort=True)["capacity_pressure_score"]
        .max()
        .reset_index()
        .sort_values("capacity_pressure_score", ascending=False, kind="mergesort")
        .reset_index(drop=True)
    )

    return result

def mental_health_shortage_analysis(
    df: pd.DataFrame,
    percentile_threshold: float = 80,
    visits_col: str = "tot_ed_nmb_vsts",
    stations_col: str = "ed_stations",
    shortage_col: str = "mental_health_shortage_area",
    year_col: str = "year",
) -> pd.DataFrame:
    """
    Analyze hospitals in mental health shortage areas with high utilization.
    """
    required_cols = [visits_col, stations_col, shortage_col, year_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[visits_col] = pd.to_numeric(work[visits_col], errors="coerce")
    work[stations_col] = pd.to_numeric(work[stations_col], errors="coerce")

    work["burden_score"] = work[visits_col] / work[stations_col]
    work["burden_score"] = work["burden_score"].replace([np.inf, -np.inf], np.nan)

    threshold = work["burden_score"].quantile(percentile_threshold / 100)

    result = work[
        _yes_flag(work[shortage_col]).eq(1)
        & (work["burden_score"] >= threshold)
    ].copy()

    return result

def clean_growth(df: pd.DataFrame, column_map: dict[str, str] | None = None) -> pd.DataFrame:
    """
    Clean and prepare data for growth calculations.
    """
    cols = _resolve_columns(column_map, ["oshpd_id", "year", "tot_ed_nmb_vsts"])
    oshpd_id = cols["oshpd_id"]
    year = cols["year"]
    tot_ed_nmb_vsts = cols["tot_ed_nmb_vsts"]

    required = [oshpd_id, year, tot_ed_nmb_vsts]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[tot_ed_nmb_vsts] = pd.to_numeric(work[tot_ed_nmb_vsts], errors="coerce")
    work[year] = pd.to_numeric(work[year], errors="coerce")
    work = work.dropna(subset=[oshpd_id])

    return work

def calculate_growth(
    df: pd.DataFrame,
    value_col: str | None = None,
    group_cols: list[str] | None = None,
    time_col: str | None = None,
    pct: bool = True,
    column_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Calculate year-over-year growth rates or absolute changes.
    """
    cols = _resolve_columns(column_map, ["oshpd_id", "year", "tot_ed_nmb_vsts"])
    oshpd_id = cols["oshpd_id"]
    year = cols["year"]
    tot_ed_nmb_vsts = cols["tot_ed_nmb_vsts"]

    if value_col is None:
        value_col = tot_ed_nmb_vsts
    if group_cols is None:
        group_cols = [oshpd_id]
    if time_col is None:
        time_col = year

    required = group_cols + [time_col, value_col]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work[time_col] = pd.to_numeric(work[time_col], errors="coerce")

    work = work.sort_values(by=group_cols + [time_col])

    if pct:
        work["growth"] = work.groupby(group_cols)[value_col].pct_change() * 100
    else:
        work["growth"] = work.groupby(group_cols)[value_col].diff()

    return work


def run_er_analysis(
    df: pd.DataFrame,
    hospital_name: str | None = None,
    facility_col: str = "facility_name",
    year_col: str = "year",
    visits_col: str = "total_ed_visits",
    visits_per_station_col: str = "visits_per_station",
) -> pd.DataFrame:
    """
    Run a simple emergency-room utilization analysis.

    Computes YoY visit changes, stores utilization, and flags high-utilization /
    high-volume mismatch rows.
    """
    required_cols = [facility_col, year_col, visits_col, visits_per_station_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[visits_col] = pd.to_numeric(work[visits_col], errors="coerce")
    work[visits_per_station_col] = pd.to_numeric(
        work[visits_per_station_col],
        errors="coerce",
    )
    work[year_col] = pd.to_numeric(work[year_col], errors="coerce")

    work = work.sort_values([facility_col, year_col])

    work["YoY_Visits"] = work.groupby(facility_col)[visits_col].pct_change() * 100
    work["Utilization"] = work[visits_per_station_col]

    util_threshold = work["Utilization"].quantile(0.75)
    visit_threshold = work[visits_col].quantile(0.75)
    work["Mismatch"] = (
        (work["Utilization"] > util_threshold)
        & (work[visits_col] > visit_threshold)
    )

    if hospital_name is not None:
        work = work[work[facility_col] == hospital_name].copy()

    return work


def county_facility_counts(
    df: pd.DataFrame,
    county_col: str = "CountyName",
    facility_col: str = "FacilityName2",
) -> pd.DataFrame:
    """
    Count unique facilities per county.
    """
    required_cols = [county_col, facility_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    result = (
        df.groupby(county_col)[facility_col]
        .nunique()
        .reset_index()
        .rename(columns={facility_col: "facility_count"})
    )

    result = result.sort_values("facility_count", ascending=False).reset_index(drop=True)
    return result


def spike_frequency_pivot(
    df: pd.DataFrame,
    threshold_pct: float = 20.0,
    facility_col: str = "facility_name",
    category_col: str = "category",
    year_col: str = "year",
    visits_col: str = "visits_per_station",
) -> pd.DataFrame:
    """
    Create a pivot table of spike frequencies by category.
    """
    required_cols = [facility_col, category_col, year_col, visits_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[visits_col] = pd.to_numeric(work[visits_col], errors="coerce")
    work[year_col] = pd.to_numeric(work[year_col], errors="coerce")

    work = work.sort_values([facility_col, category_col, year_col])
    work["yoy_growth"] = work.groupby([facility_col, category_col])[visits_col].pct_change() * 100
    work["spike"] = work["yoy_growth"] > threshold_pct

    pivot = (
        work.pivot_table(
            index=category_col,
            values="spike",
            aggfunc="sum",
            fill_value=0,
        )
        .rename(columns={"spike": "spike_count"})
        .sort_values("spike_count", ascending=False)
    )

    return pivot


def load_california_income_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Load California median household income data by zip code.
    """
    if filepath:
        try:
            return pd.read_csv(filepath)
        except FileNotFoundError:
            warnings.warn(f"File {filepath} not found. Returning sample data.")
            return _get_sample_california_income_data()

    return _get_sample_california_income_data()


def _get_sample_california_income_data() -> pd.DataFrame:
    """
    Return sample California median household income data by zip code.
    """
    sample_data = {
        "zip_code": [
            "90001", "90002", "90003", "90004", "90005",
            "94102", "94103", "94104", "94105", "94106",
            "92101", "92102", "92103", "92104", "92105",
            "93501", "93502", "93503", "93504", "93505",
            "95401", "95402", "95403", "95404", "95405",
        ],
        "county": [
            "Los Angeles", "Los Angeles", "Los Angeles", "Los Angeles", "Los Angeles",
            "San Francisco", "San Francisco", "San Francisco", "San Francisco", "San Francisco",
            "San Diego", "San Diego", "San Diego", "San Diego", "San Diego",
            "Kern", "Kern", "Kern", "Kern", "Kern",
            "Sonoma", "Sonoma", "Sonoma", "Sonoma", "Sonoma",
        ],
        "city": [
            "Los Angeles", "Los Angeles", "Los Angeles", "Los Angeles", "Los Angeles",
            "San Francisco", "San Francisco", "San Francisco", "San Francisco", "San Francisco",
            "San Diego", "San Diego", "San Diego", "San Diego", "San Diego",
            "Bakersfield", "Bakersfield", "Bakersfield", "Bakersfield", "Bakersfield",
            "Santa Rosa", "Santa Rosa", "Santa Rosa", "Santa Rosa", "Santa Rosa",
        ],
        "median_income": [
            35000, 38000, 42000, 65000, 48000,
            125000, 135000, 128000, 145000, 110000,
            58000, 62000, 68000, 75000, 72000,
            42000, 45000, 48000, 50000, 52000,
            72000, 78000, 82000, 85000, 88000,
        ],
    }
    return pd.DataFrame(sample_data)


def get_income_by_zip(df: pd.DataFrame, zip_code: str) -> Optional[Dict]:
    """
    Get median income information for a specific zip code.
    """
    result = df[df["zip_code"] == zip_code]
    if result.empty:
        return None

    row = result.iloc[0]
    return {
        "zip_code": row["zip_code"],
        "median_income": row["median_income"],
        "county": row["county"],
        "city": row["city"],
    }


def get_income_by_county(df: pd.DataFrame, county: str) -> pd.DataFrame:
    """
    Get median income data for all zip codes in a county.
    """
    return df[df["county"].str.lower() == county.lower()].copy()
