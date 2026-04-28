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
import plotly.express as px

def plot_hospital_load_distribution(
    df,
    visits_col: str = "Tot_ED_NmbVsts",
    stations_col: str = "EDStations",
    save_path: str | None = None,
) -> plt.Figure:
    """
    Plot the distribution of hospital load (visits per station).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing hospital data.
    visits_col : str
        Column name for total ED visits.
    stations_col : str
        Column name for ED stations.
    save_path : str | None
        Path to save the plot.

    Returns
    -------
    plt.Figure
        The matplotlib figure.
    """
    required_cols = [visits_col, stations_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Copy to avoid modifying original
    df = df.copy()

    # Convert to numeric
    df[visits_col] = pd.to_numeric(df[visits_col], errors="coerce")
    df[stations_col] = pd.to_numeric(df[stations_col], errors="coerce")

    # Calculate visits per station
    df["visits_per_station"] = df[visits_col] / df[stations_col]

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(df["visits_per_station"].dropna(), bins=30, ax=ax)
    ax.set_xlabel("Visits per Station")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Hospital Load")

    if save_path:
        fig.savefig(save_path)

    return fig

def year_range(csv_file:str)->tuple[int,int]:
    """
    Get the year range from a CSV file.

    Parameters
    ----------
    csv_file : str
        Path to the CSV file.

    Returns
    -------
    tuple[int, int]
        Min and max year.
    """
    df = pd.read_csv(csv_file)
    years = pd.to_numeric(df['year'], errors='coerce').dropna()
    return int(years.min()), int(years.max())

def plot_facility_trend(
    df,
    facility_name: str,
    facility_col: str = "FacilityName2",
    year_col: str = "year",
    visits_col: str = "Tot_ED_NmbVsts",
) -> plt.Figure:
    """
    Plot the trend of visits for a specific facility over time.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing facility data.
    facility_name : str
        Name of the facility to plot.
    facility_col : str
        Column name for facility identifier.
    year_col : str
        Column name for year.
    visits_col : str
        Column name for total ED visits.

    Returns
    -------
    plt.Figure
        The matplotlib figure.
    """
    required_cols = [facility_col, year_col, visits_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Filter to facility
    facility_df = df[df[facility_col] == facility_name].copy()

    if facility_df.empty:
        raise ValueError(f"Facility '{facility_name}' not found in data")

    # Convert to numeric
    facility_df[year_col] = pd.to_numeric(facility_df[year_col], errors="coerce")
    facility_df[visits_col] = pd.to_numeric(facility_df[visits_col], errors="coerce")

    # Sort by year
    facility_df = facility_df.sort_values(year_col)

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(facility_df[year_col], facility_df[visits_col], marker='o')
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
    """Downloads emergency data for a given state and displays hospital

    locations on an interactive map.

    Duplicate coordinates are merged to prevent overlapping issues on the map.
    """
    print(f"Loading/Downloading dataset for state: {state}...")
    df = download_emergency_data(state)

    required_cols = [latitude_col, longitude_col, designation_col, facility_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(
            f"Downloaded dataset is missing required columns for mapping: {missing}"
        )

    # Convert latitude and longitude to numeric
    df[latitude_col] = pd.to_numeric(df[latitude_col], errors="coerce")
    df[longitude_col] = pd.to_numeric(df[longitude_col], errors="coerce")

    # Drop rows with missing coordinates
    df = df.dropna(subset=[latitude_col, longitude_col])

    # Create base map centered on California
    m = folium.Map(location=[36.7783, -119.4179], zoom_start=6)

    # Group by coordinates to handle duplicates
    grouped = df.groupby([latitude_col, longitude_col]).agg({
        facility_col: lambda x: ', '.join(x.unique()),
        designation_col: 'first'
    }).reset_index()

    # Add markers
    for _, row in grouped.iterrows():
        color = 'blue' if row[designation_col] == 'Urban' else 'green'
        folium.Marker(
            location=[row[latitude_col], row[longitude_col]],
            popup=f"{row[facility_col]} ({row[designation_col]})",
            icon=folium.Icon(color=color)
        ).add_to(m)

    if save:
        m.save("urban_rural_map.html")

    return m

def create_ed_map(df, year):
    """
    Create an interactive map of EDs for a given year.
    
    Parameters:
        df (pd.DataFrame): DataFrame with ED info
        year (int): Year to filter the dataset
    Returns:
        fig (plotly.graph_objects.Figure): Interactive map figure
    """
    # Filter for the selected year
    df_year = df[df["year"] == year]
    
    # Map primary care shortage to colors
    color_map = {"Yes": "red", "No": "green"}
    
    # Create the scatter mapbox
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
            "longitude": False
        },
        zoom=7,
        height=600
    )
    
    fig.update_layout(
        mapbox_style="open-street-map",
        title=f"Emergency Department Visits in {year}",
        margin={"r":0,"t":40,"l":0,"b":0}
    )
    
    return fig

def plot_category_visits_by_facility(df, facility_name, save: bool = False):
    """
    Plots total category-specific ED visits (ed_burden) as a horizontal bar chart
    for a specific facility. Excludes the 'All ED Visits' category.
    """

    # Keep only the specified facility
    df = df[df["facility_name"] == facility_name]

    # Drop missing category-specific counts
    df = df.dropna(subset=["ed_burden"])

    # Exclude the total aggregate category
    df = df[df["category"] != "All ED Visits"]

    # Group by category and sum
    visits_summary = (
        df.groupby("category")["ed_burden"]
          .sum()
          .reset_index()
          .sort_values(by="ed_burden", ascending=False)
    )

    print(visits_summary)

    # Plot
    plt.figure(figsize=(12, 8))
    plt.barh(visits_summary["category"], visits_summary["ed_burden"])

    # Largest to smallest
    plt.gca().invert_yaxis()

    # No scientific notation
    plt.ticklabel_format(style='plain', axis='x')

    # Labels and title
    plt.xlabel("Total ED Visits (Category-Specific)")
    plt.ylabel("Health Condition Category")
    plt.title(f"Total ED Visits by Condition Category in {facility_name} (Excluding 'All ED Visits')")

    plt.tight_layout()
    
    if save:
        from pathlib import Path
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)
        plt.savefig(output_dir / f"{facility_name}_category_visits.png")
    
    plt.show()

def plot_category_visits(df, save: bool = False):
    """
    Plots total category-specific ED visits (ed_burden) as a horizontal bar chart.
    Excludes the 'All ED Visits' category.
    """

    # Drop missing category-specific counts
    df = df.dropna(subset=["ed_burden"])

    # Exclude the total aggregate category
    df = df[df["category"] != "All ED Visits"]

    # Group by category and sum
    visits_summary = (
        df.groupby("category")["ed_burden"]
          .sum()
          .reset_index()
          .sort_values(by="ed_burden", ascending=False)
    )

    print(visits_summary)

    # Plot
    plt.figure(figsize=(12, 8))
    plt.barh(visits_summary["category"], visits_summary["ed_burden"])

    # Largest to smallest
    plt.gca().invert_yaxis()

    # No scientific notation 
    plt.ticklabel_format(style='plain', axis='x')

    # Labels and title
    plt.xlabel("Total ED Visits (Category-Specific)")
    plt.ylabel("Health Condition Category")
    plt.title("Total ED Visits by Condition Category (Excluding 'All ED Visits')")

    plt.tight_layout()
    
    if save:
        from pathlib import Path
        output_dir = Path("data")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "category_visits_plot.png"
        plt.savefig(output_path)
        print(f"Plot saved to {output_path}")
    
    plt.show()