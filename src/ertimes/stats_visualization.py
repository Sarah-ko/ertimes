from pathlib import Path

import folium
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns
from ertimes import stats_analysis

def plot_hospital_load_distribution(
    df: pd.DataFrame,
    visits_col: str = "Tot_ED_NmbVsts",
    stations_col: str = "EDStations",
    save_path: str | None = None,
) -> plt.Figure:
    """
    Plot the distribution of hospital load, measured as visits per station.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing hospital data.
    visits_col : str
        Column name for total ED visits.
    stations_col : str
        Column name for ED stations.
    save_path : str | None
        Optional path to save the plot.

    Returns
    -------
    plt.Figure
        The matplotlib figure object.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    required_cols = [visits_col, stations_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[visits_col] = pd.to_numeric(work[visits_col], errors="coerce")
    work[stations_col] = pd.to_numeric(work[stations_col], errors="coerce")
    work["visits_per_station"] = work[visits_col] / work[stations_col]
    work["visits_per_station"] = work["visits_per_station"].replace(
        [float("inf"), float("-inf")],
        pd.NA,
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(work["visits_per_station"].dropna(), bins=30, ax=ax)
    ax.set_xlabel("Visits per Station")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Hospital Load")

    if save_path:
        fig.savefig(save_path)

    return fig


def year_range(csv_file: str) -> tuple[int, int]:
    """
    Get the minimum and maximum year from a CSV file.
    """
    df = pd.read_csv(csv_file)

    if "year" not in df.columns:
        raise ValueError("CSV file must contain a 'year' column")

    years = pd.to_numeric(df["year"], errors="coerce").dropna()

    if years.empty:
        raise ValueError("CSV file does not contain any valid year values")

    return int(years.min()), int(years.max())


def plot_facility_trend(
    df: pd.DataFrame,
    facility_name: str,
    facility_col: str = "FacilityName2",
    year_col: str = "year",
    visits_col: str = "Tot_ED_NmbVsts",
) -> plt.Figure:
    """
    Plot total ED visits over time for a specific facility.

    Returns a matplotlib Figure object so tests can verify the plot without
    opening an interactive window.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    required_cols = [facility_col, year_col, visits_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    facility_df = df[df[facility_col] == facility_name].copy()

    if facility_df.empty:
        raise ValueError(f"Facility '{facility_name}' not found in data")

    facility_df[year_col] = pd.to_numeric(facility_df[year_col], errors="coerce")
    facility_df[visits_col] = pd.to_numeric(facility_df[visits_col], errors="coerce")
    facility_df = facility_df.sort_values(year_col)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(facility_df[year_col], facility_df[visits_col], marker="o")
    ax.set_xlabel("Year")
    ax.set_ylabel("Total ED Visits")
    ax.set_title(f"ED Visits Trend for {facility_name}")

    return fig


def plot_urban_rural_map(
    state: str,
    save: bool = False,
    latitude_col: str = "LATITUDE",
    longitude_col: str = "LONGITUDE",
    designation_col: str = "UrbanRuralDesi",
    facility_col: str = "FacilityName2",
) -> folium.Map:
    """
    Download emergency data for a state and map hospital locations.

    Duplicate coordinates are merged to avoid overlapping markers.
    """

    df = stats_analysis.download_emergency_data(state).copy()

    required_cols = [latitude_col, longitude_col, designation_col, facility_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(
            f"Downloaded dataset is missing required columns for mapping: {missing}"
        )

    df[latitude_col] = pd.to_numeric(df[latitude_col], errors="coerce")
    df[longitude_col] = pd.to_numeric(df[longitude_col], errors="coerce")
    df = df.dropna(subset=[latitude_col, longitude_col])

    if df.empty:
        raise ValueError("No valid latitude/longitude rows available for mapping")

    center_lat = df[latitude_col].mean()
    center_lon = df[longitude_col].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)

    grouped = (
        df.groupby([latitude_col, longitude_col], dropna=False)
        .agg(
            {
                facility_col: lambda x: ", ".join(
                    sorted({str(value) for value in x.dropna()})
                ),
                designation_col: "first",
            }
        )
        .reset_index()
    )

    for _, row in grouped.iterrows():
        designation = str(row[designation_col])
        color = "blue" if designation.lower() == "urban" else "green"

        folium.Marker(
            location=[row[latitude_col], row[longitude_col]],
            popup=f"{row[facility_col]} ({row[designation_col]})",
            icon=folium.Icon(color=color),
        ).add_to(m)

    if save:
        m.save("urban_rural_map.html")

    return m


def create_ed_map(df: pd.DataFrame, year: int):
    """
    Create an interactive Plotly map of emergency departments for a given year.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    required_cols = [
        "year",
        "latitude",
        "longitude",
        "total_ed_visits",
        "primary_care_shortage",
        "mental_health_shortage",
        "county",
        "ed_name",
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df_year = df[df["year"] == year].copy()

    color_map = {"Yes": "red", "No": "green"}

    fig = px.scatter_map(
        df_year,
        lat="latitude",
        lon="longitude",
        size="total_ed_visits",
        color="primary_care_shortage",
        color_discrete_map=color_map,
        hover_name="ed_name",
        hover_data={
            "total_ed_visits": True,
            "county": True,
            "primary_care_shortage": True,
            "mental_health_shortage": True,
            "latitude": False,
            "longitude": False,
        },
        zoom=7,
        height=600,
    )

    fig.update_layout(
        mapbox_style="open-street-map",
        title=f"Emergency Department Visits in {year}",
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
    )

    return fig


def _category_visits_summary(
    df: pd.DataFrame,
    category_col: str = "category",
    burden_col: str = "ed_burden",
) -> pd.DataFrame:
    """
    Build the category visits summary used by plotting functions.
    """
    required_cols = [category_col, burden_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[burden_col] = pd.to_numeric(work[burden_col], errors="coerce")
    work = work.dropna(subset=[burden_col])
    work = work[work[category_col] != "All ED Visits"]

    visits_summary = (
        work.groupby(category_col)[burden_col]
        .sum()
        .reset_index()
        .sort_values(by=burden_col, ascending=False, kind="mergesort")
        .reset_index(drop=True)
    )

    return visits_summary


def plot_category_visits_by_facility(
    df: pd.DataFrame,
    facility_name: str,
    save: bool = False,
):
    """
    Plot category-specific ED visits for a specific facility.

    Excludes the aggregate 'All ED Visits' category.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    required_cols = ["facility_name", "category", "ed_burden"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    facility_df = df[df["facility_name"] == facility_name].copy()

    visits_summary = _category_visits_summary(facility_df)

    print(visits_summary)

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.barh(visits_summary["category"], visits_summary["ed_burden"])
    ax.invert_yaxis()
    ax.ticklabel_format(style="plain", axis="x")
    ax.set_xlabel("Total ED Visits (Category-Specific)")
    ax.set_ylabel("Health Condition Category")
    ax.set_title(
        f"Total ED Visits by Condition Category in {facility_name} "
        "(Excluding 'All ED Visits')"
    )
    fig.tight_layout()

    if save:
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)
        fig.savefig(output_dir / f"{facility_name}_category_visits.png")

    plt.show()
    return fig


def plot_category_visits(df: pd.DataFrame, save: bool = False):
    """
    Plot total category-specific ED visits across all facilities.

    Excludes the aggregate 'All ED Visits' category.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    visits_summary = _category_visits_summary(df)

    # Tests parse this exact printed DataFrame, so keep the print.
    print(visits_summary)

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.barh(visits_summary["category"], visits_summary["ed_burden"])
    ax.invert_yaxis()
    ax.ticklabel_format(style="plain", axis="x")
    ax.set_xlabel("Total ED Visits (Category-Specific)")
    ax.set_ylabel("Health Condition Category")
    ax.set_title("Total ED Visits by Condition Category (Excluding 'All ED Visits')")
    fig.tight_layout()

    if save:
        output_dir = Path("data")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "category_visits_plot.png"
        fig.savefig(output_path)
        print(f"Plot saved to {output_path}")

    plt.show()
    return fig