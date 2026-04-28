from pathlib import Path

from ertimes.stats_visualization import plot_category_visits, plot_hospital_load_distribution, plot_urban_rural_map
from ertimes.io import download_emergency_data, load_emergency_data
from ertimes.stats_analysis import find_capacity_volume_mismatch, county_capacity_summary, rank_counties_by_burden
from ertimes.stats_ranking import rank_hospitals_by_visits_per_station
from ertimes.stats_reports import summarize_by_ownership
import pandas as pd


df = download_emergency_data("california")

#raises error
result = find_capacity_volume_mismatch(
    df,
    high_visit_quantile=0.65,
    low_capacity_quantile=0.35,
)

print(result.head(10))
print(f"Rows returned: {len(result)}")


print("Downloading data for test...")
df = download_emergency_data("california")

print("Generating plot...")
plot_hospital_load_distribution(df, group_col='hospital_ownership', save=True)

print("Generating urban-rural map...")
plot_urban_rural_map("california", save=True)

print("Check your 'data/' folder for the new files!")

#test for health conditions bar plot
def demo_plot_category_visits_downloaded() -> None:
    """Download emergency data for California and render the category visits plot."""
    print("Downloading emergency data for California...")
    df = download_emergency_data("california")

    print("Generating category visits plot from downloaded data...")
    plot_category_visits(df, save=True)


def demo_county_capacity_summary():
    """Demo county capacity summary."""
    print("Generating county capacity summary...")
    summary = county_capacity_summary("california")
    print(summary.head())
    return summary

def demo_rank_counties():
    """Demo ranking counties by burden."""
    print("Ranking counties by burden...")
    summary = demo_county_capacity_summary()
    ranked = rank_counties_by_burden(summary)
    print(ranked.head())
    return ranked

def demo_rank_hospitals():
    """Demo ranking hospitals by visits per station."""
    print("Ranking hospitals by visits per station...")
    df = download_emergency_data("california")
    ranked = rank_hospitals_by_visits_per_station(df, top_n=5)
    print(ranked)
    return ranked

def demo_summarize_by_ownership():
    """Demo summarizing by ownership."""
    print("Summarizing by ownership...")
    df = download_emergency_data("california")
    summary = summarize_by_ownership(df)
    print(summary)
    return summary

demo_plot_category_visits_downloaded()

# Run demos
if __name__ == "__main__":
    demo_county_capacity_summary()
    demo_rank_counties()
    demo_rank_hospitals()
    demo_summarize_by_ownership()