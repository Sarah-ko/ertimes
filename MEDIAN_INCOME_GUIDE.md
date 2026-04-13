# California Median Income Analysis by Zip Code

This module provides tools to analyze California household median income data organized by zip code. It includes functions for data loading, filtering, and statistical analysis.

## Features

- **Load income data** - Load California median household income data by zip code
- **Lookup by zip code** - Get detailed income information for a specific zip code
- **Filter by county** - Extract all zip codes within a specific county
- **Statistical analysis** - Calculate income statistics grouped by county or city
- **Income range filtering** - Find zip codes within specific income thresholds
- **Summary reports** - Generate formatted income summaries

## Installation

The module is part of the `ertimes` package. To use it:

```bash
pip install -e .
```

## Usage

### Basic Usage

```python
from ertimes.Median_income import load_california_income_data, display_income_summary

# Load the data
df = load_california_income_data()

# Display a summary
display_income_summary(df)
```

### Look Up Specific Zip Code

```python
from ertimes.Median_income import load_california_income_data, get_income_by_zip

df = load_california_income_data()
info = get_income_by_zip(df, '90001')

if info:
    print(f"Zip Code: {info['zip_code']}")
    print(f"City: {info['city']}")
    print(f"County: {info['county']}")
    print(f"Median Income: ${info['median_income']:,}")
```

### Get All Zip Codes in a County

```python
from ertimes.Median_income import load_california_income_data, get_income_by_county

df = load_california_income_data()
sf_data = get_income_by_county(df, 'San Francisco')
print(sf_data[['zip_code', 'city', 'median_income']])
```

### Calculate Statistics by County

```python
from ertimes.Median_income import load_california_income_data, get_income_statistics

df = load_california_income_data()
stats = get_income_statistics(df, group_by='county')
print(stats)
```

### Filter by Income Range

```python
from ertimes.Median_income import load_california_income_data, filter_by_income_range

df = load_california_income_data()
# Find zip codes with median income between $60k and $100k
filtered = filter_by_income_range(df, 60000, 100000)
print(filtered[['zip_code', 'city', 'median_income']])
```

### Find Highest and Lowest Income Areas

```python
from ertimes.Median_income import load_california_income_data

df = load_california_income_data()

# Top 5 highest income zip codes
top_5 = df.nlargest(5, 'median_income')
print("Highest Income Zip Codes:")
print(top_5[['zip_code', 'city', 'median_income']])

# Top 5 lowest income zip codes
bottom_5 = df.nsmallest(5, 'median_income')
print("Lowest Income Zip Codes:")
print(bottom_5[['zip_code', 'city', 'median_income']])
```

## API Reference

### `load_california_income_data(filepath=None)`
Load California median household income data by zip code.

**Parameters:**
- `filepath` (str, optional): Path to a CSV file with income data. If None, uses sample data.

**Returns:**
- `pd.DataFrame`: DataFrame with columns: zip_code, median_income, county, city

### `get_income_by_zip(df, zip_code)`
Get median income information for a specific zip code.

**Parameters:**
- `df` (pd.DataFrame): Income data frame
- `zip_code` (str): The zip code to look up

**Returns:**
- `dict`: Dictionary with zip code details or None if not found

### `get_income_by_county(df, county)`
Get median income data for all zip codes in a county.

**Parameters:**
- `df` (pd.DataFrame): Income data frame
- `county` (str): The county name

**Returns:**
- `pd.DataFrame`: Filtered data for the specified county

### `get_income_statistics(df, group_by=None)`
Calculate median income statistics.

**Parameters:**
- `df` (pd.DataFrame): Income data frame
- `group_by` (str, optional): Column to group by ('county' or 'city'). If None, returns overall stats.

**Returns:**
- `pd.DataFrame`: Statistics with mean, median, min, max income

### `filter_by_income_range(df, min_income, max_income)`
Filter zip codes by median income range.

**Parameters:**
- `df` (pd.DataFrame): Income data frame
- `min_income` (float): Minimum median income threshold
- `max_income` (float): Maximum median income threshold

**Returns:**
- `pd.DataFrame`: Filtered DataFrame with zip codes in the income range

### `display_income_summary(df)`
Print a formatted summary of income data.

**Parameters:**
- `df` (pd.DataFrame): Income data frame

## Running the Demo

To see examples of all features in action:

```bash
python median_income_demo.py
```

This will show:
1. Overall income summary
2. Lookup of specific zip codes
3. County-level analysis
4. Statistics by county
5. Filtering by income range
6. Top 5 highest and lowest income areas

## Data Format

The expected DataFrame structure has the following columns:

| Column | Type | Description |
|--------|------|-------------|
| zip_code | str | 5-digit zip code |
| median_income | float | Median household income in dollars |
| county | str | County name |
| city | str | City name |

## Using Your Own Data

To use your own California income data:

```python
from ertimes.Median_income import load_california_income_data

# Load your custom CSV file
df = load_california_income_data('path/to/your/income_data.csv')

# Your CSV should have columns: zip_code, median_income, county, city
```

## Example Output

```
======================================================================
CALIFORNIA MEDIAN HOUSEHOLD INCOME BY ZIP CODE - SUMMARY
======================================================================

Total zip codes: 25
Mean median income: $73,920.00
Median income: $68,000.00
Income range: $35,000 - $145,000

----------------------------------------------------------------------
BY COUNTY:
----------------------------------------------------------------------
               mean_income  median_income  min_income  max_income  count
county                                                                  
Kern               47400.0        48000.0       42000       52000      5
Los Angeles        45600.0        42000.0       35000       65000      5
San Diego          67000.0        68000.0       58000       75000      5
San Francisco     128600.0       128000.0      110000      145000      5
Sonoma             81000.0        82000.0       72000       88000      5
```

## Notes

- This module currently uses sample data for demonstration purposes
- To integrate real California income data, provide a CSV file in the format specified above
- All functions handle missing data gracefully and return appropriate warnings

## Requirements

- pandas >= 2.2
- numpy >= 2.0
