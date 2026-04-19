from pathlib import Path

from ertimes.health_conditions_bar import plot_category_visits
from ertimes.io import download_emergency_data, load_emergency_data
from ertimes.stats import find_capacity_volume_mismatch, plot_hospital_load_distribution
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
plot_hospital_load_distribution(df, group_col='HospitalOwnership')

print("Check your 'data/' folder for the new .png file!")

#test for health conditions bar plot
def demo_plot_category_visits_local() -> None:
    """Load local raw CSV emergency data and render the category visits plot."""
    local_data_path = Path("data") / "Emergency Department Volume and Capacity - Catalog - ED_COMBINE_AL.csv"
    if not local_data_path.exists() and "__file__" in globals():
        local_data_path = Path(__file__).resolve().parent / "data" / "Emergency Department Volume and Capacity - Catalog - ED_COMBINE_AL.csv"

    print(f"Loading local emergency data from: {local_data_path}")
    df = pd.read_csv(local_data_path)

    print("Generating category visits plot from local data...")
    plot_category_visits(df)


demo_plot_category_visits_local()