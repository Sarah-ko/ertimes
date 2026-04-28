import pandas as pd

def rank_counties_by_burden(
    summary: pd.DataFrame,
    visits_col: str = "visits_per_station",
) -> pd.DataFrame:
    """
    Rank counties by emergency department burden.

    Counties are sorted in descending order of visits per station, where higher
    values indicate greater strain on emergency department capacity.

    Parameters
    ----------
    summary : pd.DataFrame
        DataFrame produced by county_capacity_summary, containing visits-per-station values.
    visits_col : str
        Column name for visits per station.

    Returns
    -------
    pd.DataFrame
        DataFrame sorted by visits per station in descending order.
    """
    if not isinstance(summary, pd.DataFrame):
        raise TypeError("summary must be a pandas DataFrame")

    if visits_col not in summary.columns:
        raise ValueError(f"Column '{visits_col}' not found in summary DataFrame")

    ranked = summary.sort_values(visits_col, ascending=False).reset_index(drop=True)
    return ranked


def rank_hospitals_by_visits_per_station(
    df: pd.DataFrame,
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
        Aggregation method. Must be either "mean" or "median".
    top_n : int | None
        Number of top hospitals to return. If None, returns all hospitals.
    facility_col : str
        Column name for facility identifier.
    visits_col : str
        Column name for visits per station.

    Returns
    -------
    pd.DataFrame
        Ranked DataFrame with facility name and aggregated visits per station.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    required_cols = [facility_col, visits_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if agg not in {"mean", "median"}:
        raise ValueError("agg must be 'mean' or 'median'")

    work = df.copy()
    work[visits_col] = pd.to_numeric(work[visits_col], errors="coerce")

    if agg == "mean":
        aggregated = work.groupby(facility_col, sort=True)[visits_col].mean().reset_index()
    else:
        aggregated = work.groupby(facility_col, sort=True)[visits_col].median().reset_index()

    # Use mergesort so ties preserve the deterministic groupby order.
    aggregated = aggregated.sort_values(
        visits_col,
        ascending=False,
        kind="mergesort",
    ).reset_index(drop=True)

    if top_n is not None:
        if top_n < 0:
            raise ValueError("top_n must be nonnegative or None")
        aggregated = aggregated.head(top_n)

    return aggregated