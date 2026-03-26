from ertimes.stats import county_capacity_summary

summary = county_capacity_summary("california")
print(summary.head())