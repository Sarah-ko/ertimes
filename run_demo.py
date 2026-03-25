from ertimes.io import download_emergency_data
from ertimes.stats import find_capacity_volume_mismatch

df = download_emergency_data("california")

result = find_capacity_volume_mismatch(
    df,
    high_visit_quantile=0.65,
    low_capacity_quantile=0.35,
)

print(result.head(10))
print(f"Rows returned: {len(result)}")