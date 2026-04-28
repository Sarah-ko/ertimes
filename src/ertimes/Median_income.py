"""
Module for analyzing median household income in California by zip code.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
import warnings


def load_california_income_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Load California median household income data by zip code.
    
    Parameters
    ----------
    filepath : str, optional
        Path to a CSV file containing zip code and median income data.
        If None, returns a sample dataset for demonstration.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns: 'zip_code', 'median_income', 'county', 'city'
    """
    if filepath:
        try:
            df = pd.read_csv(filepath) # Load user-provided dataset
            return df
        except FileNotFoundError:
            warnings.warn(f"File {filepath} not found. Returning sample data.")
            return _get_sample_california_income_data()
    else:
        # Use built-in sample data when no file is provided
        return _get_sample_california_income_data()


def _get_sample_california_income_data() -> pd.DataFrame:
    """
    Return sample California median household income data by zip code.
    
    Returns
    -------
    pd.DataFrame
        Sample data with California zip codes and median income values.
    """
    sample_data = {
        'zip_code': [
            '90001', '90002', '90003', '90004', '90005',
            '94102', '94103', '94104', '94105', '94106',
            '92101', '92102', '92103', '92104', '92105',
            '93501', '93502', '93503', '93504', '93505',
            '95401', '95402', '95403', '95404', '95405'
        ],
        'county': [
            'Los Angeles', 'Los Angeles', 'Los Angeles', 'Los Angeles', 'Los Angeles',
            'San Francisco', 'San Francisco', 'San Francisco', 'San Francisco', 'San Francisco',
            'San Diego', 'San Diego', 'San Diego', 'San Diego', 'San Diego',
            'Kern', 'Kern', 'Kern', 'Kern', 'Kern',
            'Sonoma', 'Sonoma', 'Sonoma', 'Sonoma', 'Sonoma'
        ],
        'city': [
            'Los Angeles', 'Los Angeles', 'Los Angeles', 'Los Angeles', 'Los Angeles',
            'San Francisco', 'San Francisco', 'San Francisco', 'San Francisco', 'San Francisco',
            'San Diego', 'San Diego', 'San Diego', 'San Diego', 'San Diego',
            'Bakersfield', 'Bakersfield', 'Bakersfield', 'Bakersfield', 'Bakersfield',
            'Santa Rosa', 'Santa Rosa', 'Santa Rosa', 'Santa Rosa', 'Santa Rosa'
        ],
        'median_income': [
            35000, 38000, 42000, 65000, 48000,
            125000, 135000, 128000, 145000, 110000,
            58000, 62000, 68000, 75000, 72000,
            42000, 45000, 48000, 50000, 52000,
            72000, 78000, 82000, 85000, 88000
        ]
    }
    return pd.DataFrame(sample_data)


def get_income_by_zip(df: pd.DataFrame, zip_code: str) -> Optional[Dict]:
    """
    Get median income information for a specific zip code.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing zip code and income data
    zip_code : str
        The zip code to look up
    
    Returns
    -------
    dict or None
        Dictionary with zip code details if found, None otherwise
    """
    result = df[df['zip_code'] == zip_code] # Filter for matching zip code
    if result.empty:
        return None # Return None if zip code not found
    
    row = result.iloc[0] #Extract the first matching row
    
    #Return relevant fields as a dictionary
    return {
        'zip_code': row['zip_code'],
        'median_income': row['median_income'],
        'county': row['county'],
        'city': row['city']
    }


def get_income_by_county(df: pd.DataFrame, county: str) -> pd.DataFrame:
    """
    Get median income data for all zip codes in a county.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing zip code and income data
    county : str
        The county name
    
    Returns
    -------
    pd.DataFrame
        Filtered DataFrame for the specified county
    """
    # Case-insensitive match on county name
    return df[df['county'].str.lower() == county.lower()].copy()


def get_income_statistics(df: pd.DataFrame, 
                         group_by: Optional[str] = None) -> pd.DataFrame:
    """
    Calculate median income statistics by county or city.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing zip code and income data
    group_by : str, optional
        Column to group by ('county' or 'city'). If None, returns overall stats.
    
    Returns
    -------
    pd.DataFrame
        Statistics table with mean, median, min, max income
    """
    if group_by:
        # Group by specified column and compute summary statistics
        stats = df.groupby(group_by)['median_income'].agg([
            ('mean_income', 'mean'),
            ('median_income', 'median'),
            ('min_income', 'min'),
            ('max_income', 'max'),
            ('count', 'count')
        ]).round(2)
    else:
        # Compute overall statistics without grouping
        stats = pd.DataFrame({
            'mean_income': [df['median_income'].mean()],
            'median_income': [df['median_income'].median()],
            'min_income': [df['median_income'].min()],
            'max_income': [df['median_income'].max()],
            'count': [len(df)]
        }).round(2)
    
    return stats


def filter_by_income_range(df: pd.DataFrame, 
                          min_income: float, 
                          max_income: float) -> pd.DataFrame:
    """
    Filter zip codes by median income range.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing zip code and income data
    min_income : float
        Minimum median income threshold
    max_income : float
        Maximum median income threshold
    
    Returns
    -------
    pd.DataFrame
        Filtered DataFrame with zip codes in the income range
    """
    #Filter rows where income falls within the specified range (inclusive)
    return df[(df['median_income'] >= min_income) & 
              (df['median_income'] <= max_income)].copy()


def display_income_summary(df: pd.DataFrame) -> None:
    # Print formatted summary statistics for quick inspection
    """
    Print a formatted summary of income data.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing zip code and income data
    """
    print("\n" + "="*70)
    print("CALIFORNIA MEDIAN HOUSEHOLD INCOME BY ZIP CODE - SUMMARY")
    print("="*70)
    print(f"\nTotal zip codes: {len(df)}")
    print(f"Mean median income: ${df['median_income'].mean():,.2f}")
    print(f"Median income: ${df['median_income'].median():,.2f}")
    print(f"Income range: ${df['median_income'].min():,.0f} - ${df['median_income'].max():,.0f}")
    print("\n" + "-"*70)
    print("BY COUNTY:")
    print("-"*70)
     # Reuse stats function to compute county-level summaries
    county_stats = get_income_statistics(df, group_by='county')
    print(county_stats.to_string())
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    # Example usage
    df = load_california_income_data()
    
    # Display overall summary
    display_income_summary(df)
    
    # Look up specific zip code
    print("EXAMPLE: Lookup specific zip code (90001):")
    result = get_income_by_zip(df, '90001')
    if result:
        print(f"  Zip Code: {result['zip_code']}")
        print(f"  City: {result['city']}")
        print(f"  County: {result['county']}")
        print(f"  Median Income: ${result['median_income']:,}\n")
    
    # Filter by income range
    print("EXAMPLE: Zip codes with median income between $60,000 - $100,000:")
    filtered = filter_by_income_range(df, 60000, 100000)
    print(filtered[['zip_code', 'city', 'county', 'median_income']].to_string(index=False))
    print()
