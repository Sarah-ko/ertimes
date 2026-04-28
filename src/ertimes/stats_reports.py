import pandas as pd

def _resolve_columns(column_map: dict[str, str] | None, columns: list[str]) -> dict[str, str]:
    """
    Resolve column names using a mapping dictionary.

    If column_map is provided, maps each expected column name to its mapped value
    if present. Otherwise, the original expected column name is used.
    """
    if column_map is None:
        return {col: col for col in columns}

    return {col: column_map.get(col, col) for col in columns}


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
    """
    if not isinstance(summary, pd.DataFrame):
        raise TypeError("summary must be a pandas DataFrame")

    required_cols = [
        county_col,
        visits_col,
        stations_col,
        beds_col,
        visits_per_station_col,
    ]
    missing = [col for col in required_cols if col not in summary.columns]
    if missing:
        raise ValueError(f"summary is missing required columns: {missing}")

    county_data = summary[summary[county_col] == county_name]

    if county_data.empty:
        raise ValueError(f"No county found with name '{county_name}'")

    return county_data.reset_index(drop=True)


def per_category_burden_report(
    df: pd.DataFrame,
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
        Dictionary mapping each category to a list of top facility names.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    if top_n < 0:
        raise ValueError("top_n must be nonnegative")

    required_cols = [facility_col, category_col, visits_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[visits_col] = pd.to_numeric(work[visits_col], errors="coerce")

    result: dict[str, list[str]] = {}

    for category, group in work.groupby(category_col, sort=True):
        top_facilities = (
            group.sort_values(visits_col, ascending=False, kind="mergesort")
            .head(top_n)[facility_col]
            .tolist()
        )
        result[category] = top_facilities

    return result


def find_duplicates(
    df: pd.DataFrame,
    subset: list[str] | None = None,
    keep: str | bool = False,
) -> pd.DataFrame:
    """
    Find duplicate rows in a DataFrame.

    By default, keep=False returns every row that belongs to a duplicate group.
    This matches tests that expect both the first duplicate and later duplicate
    rows to be included.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame")

    if subset is not None:
        missing = [col for col in subset if col not in df.columns]
        if missing:
            raise ValueError(f"Missing subset columns: {missing}")

    return df[df.duplicated(subset=subset, keep=keep)]


def summarize_by_ownership(
    df: pd.DataFrame,
    column_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Summarize hospital data by ownership type.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing hospital data.
    column_map : dict[str, str] | None
        Optional mapping from standard column names to actual DataFrame column names.

    Returns
    -------
    pd.DataFrame
        Summary DataFrame grouped by ownership type.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    cols = _resolve_columns(
        column_map,
        [
            "hospital_ownership",
            "tot_ed_visits",
            "ed_stations",
            "visits_per_station",
        ],
    )

    ownership_type = cols["hospital_ownership"]
    total_visits = cols["tot_ed_visits"]
    stations = cols["ed_stations"]
    visits_per_station = cols["visits_per_station"]

    required = [ownership_type, total_visits, stations, visits_per_station]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[total_visits] = pd.to_numeric(work[total_visits], errors="coerce")
    work[stations] = pd.to_numeric(work[stations], errors="coerce")
    work[visits_per_station] = pd.to_numeric(work[visits_per_station], errors="coerce")

    work = work.dropna(subset=[ownership_type])

    summary = (
        work.groupby(ownership_type)
        .agg(
            Tot_ED_NmbVsts_mean=(total_visits, "mean"),
            Tot_ED_NmbVsts_sum=(total_visits, "sum"),
            EDStations_mean=(stations, "mean"),
            EDStations_sum=(stations, "sum"),
            Visits_Per_Station_mean=(visits_per_station, "mean"),
            Visits_Per_Station_median=(visits_per_station, "median"),
            Visits_Per_Station_std=(visits_per_station, "std"),
        )
        .reset_index()
    )

    summary = summary.sort_values(
        "Visits_Per_Station_mean",
        ascending=False,
        kind="mergesort",
    ).reset_index(drop=True)

    return summary