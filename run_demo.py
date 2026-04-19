from pathlib import Path

from ertimes.health_conditions_bar import plot_category_visits
from ertimes.io import download_emergency_data, load_emergency_data
from ertimes.stats import find_capacity_volume_mismatch, plot_hospital_load_distribution, plot_urban_rural_map
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


demo_plot_category_visits_downloaded()