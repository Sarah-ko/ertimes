"""
Script to download California median household income data from Census Bureau API
and save it as CSV for use in the Median_income module.

Requirements:
- Census API key (get one free at https://api.census.gov/data/key_signup.html)
- requests library
"""

import requests
import pandas as pd
import json
import os
from pathlib import Path

# Census API configuration
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY', 'YOUR_API_KEY_HERE')
ACS_YEAR = 2024
TABLE_ID = 'S1903'  # Median Income in the Past 12 Months

# Census API endpoints
BASE_URL = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"

def get_census_data_for_zipcode():
    """
    Fetch California median household income data by zip code from Census Bureau API.
    
    Returns:
    -------
    pd.DataFrame
        DataFrame with zip_code, median_income, county, city columns
    """
    
    if CENSUS_API_KEY == 'YOUR_API_KEY_HERE':
        print("Error: Census API key not set!")
        print("Get a free API key at: https://api.census.gov/data/key_signup.html")
        print("Then set it with: export CENSUS_API_KEY='your_key_here'")
        return None
    
    # Variables to retrieve for Table S1903
    # S1903_C03_001E = Median income
    variables = 'S1903_C03_001E,NAME'
    
    # Get all zip codes in California
    # Census treats ZCTA (Zip Code Tabulation Area) as geography
    params = {
        'get': variables,
        'for': 'zip code tabulation area:*',
        'in': 'state:06',  # 06 is California's FIPS code
        'key': CENSUS_API_KEY
    }
    
    print("Fetching California median income data from Census Bureau...")
    
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if len(data) < 2:
            print("No data returned from Census Bureau API")
            return None
        
        # Convert to DataFrame
        headers = data[0]
        rows = data[1:]
        
        df = pd.DataFrame(rows, columns=headers)
        
        # Clean up the data
        df = df.rename(columns={
            'S1903_C03_001E': 'median_income',
            'NAME': 'name',
            'zip code tabulation area': 'zip_code'
        })
        
        # Convert median_income to numeric, handling missing values
        df['median_income'] = pd.to_numeric(df['median_income'], errors='coerce')
        
        # Filter out rows with missing median income
        df = df[df['median_income'].notna()].copy()
        
        # Extract county and city from NAME field if available
        df['county'] = df['name'].str.extract(r',\s*([A-Za-z\s]+)\s+County,\s+California', expand=False)
        df['city'] = df['name'].str.extract(r'^(.*?),', expand=False)
        
        # Select and reorder columns
        df = df[['zip_code', 'median_income', 'county', 'city']].copy()
        
        # Convert median_income to integer
        df['median_income'] = df['median_income'].astype(int)
        
        print(f"Successfully retrieved {len(df)} zip codes with income data")
        
        return df
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Census API: {e}")
        return None
    except Exception as e:
        print(f"Error processing Census data: {e}")
        return None


def save_to_csv(df, output_path='data/california_median_income_by_zipcode.csv'):
    """
    Save the census data to CSV file.
    
    Parameters:
    -----------
    df : pd.DataFrame
        The income data to save
    output_path : str
        Path where to save the CSV file
    """
    
    # Create data directory if it doesn't exist
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(output_path, index=False)
    print(f"Data saved to {output_path}")
    print(f"\nData preview:")
    print(df.head(10))
    print(f"\nTotal records: {len(df)}")


def display_statistics(df):
    """Display basic statistics about the income data."""
    
    print("\n" + "="*70)
    print("CALIFORNIA MEDIAN INCOME STATISTICS")
    print("="*70)
    print(f"Total zip codes: {len(df)}")
    print(f"Mean median income: ${df['median_income'].mean():,.2f}")
    print(f"Median income: ${df['median_income'].median():,.2f}")
    print(f"Min income: ${df['median_income'].min():,}")
    print(f"Max income: ${df['median_income'].max():,}")
    print(f"Counties: {df['county'].nunique()}")
    print(f"\nCounties represented:")
    print(df['county'].value_counts())
    print("="*70 + "\n")


if __name__ == "__main__":
    # Fetch data from Census Bureau
    df = get_census_data_for_zipcode()
    
    if df is not None:
        # Display statistics
        display_statistics(df)
        
        # Save to CSV
        save_to_csv(df)
        
        print("\nYou can now use this data with the Median_income module:")
        print("from ertimes.Median_income import load_california_income_data")
        print("df = load_california_income_data('data/california_median_income_by_zipcode.csv')")
    else:
        print("\nFailed to fetch Census data. Please:")
        print("1. Get a Census API key: https://api.census.gov/data/key_signup.html")
        print("2. Set it: export CENSUS_API_KEY='your_key_here'")
        print("3. Run this script again")
