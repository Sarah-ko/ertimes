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