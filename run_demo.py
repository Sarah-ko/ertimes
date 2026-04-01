from ertimes.io import download_emergency_data
from ertimes.stats import find_capacity_volume_mismatch
import pandas as pd
from ertimes.stats import plot_hospital_load_distribution

df = download_emergency_data("california")

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