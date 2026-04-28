#!/usr/bin/env python
"""
Demo script showing how to use the Median_income module
to analyze California household income by zip code.
"""

import sys
import importlib.util

from ertimes.stats_analysis import (
    load_california_income_data,
    get_income_by_zip,
    get_income_by_county,
    get_income_statistics,
    filter_by_income_range,
    display_income_summary,
)


def main():
    """Main function to run the California median income analysis demo.
    This function loads the dataset, performs various analyses, and prints the results.
    """
    print("\n" + "="*70)
    print("CALIFORNIA MEDIAN INCOME ANALYSIS DEMO - CENSUS DATA 2024")
    print("="*70 + "\n")
    
    # Load data from Census Bureau CSV
    df = load_california_income_data('data/california_median_income_by_zipcode.csv')
    
    # 1. Display overall summary
    print("1. OVERALL SUMMARY")
    print("-" * 70)
    display_income_summary(df)
    
    # 2. Get income for specific zip codes
    print("\n2. LOOKUP SPECIFIC ZIP CODES")
    print("-" * 70)
    zip_codes_to_check = ['90001', '94102', '92101', '95401']
    for zip_code in zip_codes_to_check:
        info = get_income_by_zip(df, zip_code)
        if info:
            print(f"  {info['zip_code']}: {info['city']}, {info['county']}")
            print(f"    Median Income: ${info['median_income']:,}\n")
    
    # 3. Get all zip codes in a county
    print("\n3. ZIP CODES BY COUNTY - Los Angeles County")
    print("-" * 70)
    la_data = get_income_by_county(df, 'Los Angeles')
    print(la_data[['zip_code', 'city', 'median_income']].to_string(index=False))
    
    # 4. Statistics by county
    print("\n\n4. INCOME STATISTICS BY COUNTY")
    print("-" * 70)
    county_stats = get_income_statistics(df, group_by='county')
    print(county_stats.to_string())
    
    # 5. Filter by income range
    print("\n\n5. ZIP CODES IN INCOME RANGE ($70,000 - $120,000)")
    print("-" * 70)
    filtered = filter_by_income_range(df, 70000, 120000)
    print(filtered[['zip_code', 'city', 'county', 'median_income']].sort_values(
        'median_income', ascending=False).to_string(index=False))
    
    # 6. Find highest and lowest income zip codes
    print("\n\n6. TOP 5 HIGHEST MEDIAN INCOME ZIP CODES")
    print("-" * 70)
    top_5 = df.nlargest(5, 'median_income')[['zip_code', 'city', 'county', 'median_income']]
    print(top_5.to_string(index=False))
    
    print("\n\n7. TOP 5 LOWEST MEDIAN INCOME ZIP CODES")
    print("-" * 70)
    bottom_5 = df.nsmallest(5, 'median_income')[['zip_code', 'city', 'county', 'median_income']]
    print(bottom_5.to_string(index=False))
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
