import pandas as pd
import numpy as np
from clean import clean_data  



df = pd.read_csv("data/Emergency Department Volume and Capacity - Catalog - ED_COMBINE_AL.csv")

df = clean_data(df) 

"""
This function highlights facilities that experience both an above-average burden (namely, a higher-than-normal demand relative to available resources) and a shortage of mental health resources, identifying them at high-risk.
"""

def mental_health_shortage_analysis(df):
    """Analyzes the emergency department data to identify facilities that are 
    at high risk due to a combination of high burden and mental health 
    resource shortages.
    The function calculates a burden score for each facility, 
    determines the average burden, and flags facilities"""

    
    # Creates a copy to prevent modifying original dataframe
    df = df.copy()

    # Converts to numeric using the cleaned column names
    df['tot_ed_nmb_vsts'] = pd.to_numeric(df['tot_ed_nmb_vsts'], errors='coerce')
    df['ed_stations'] = pd.to_numeric(df['ed_stations'], errors='coerce').replace(0, 0.0001)

    # Calculates burden (# of visits/# of ED stations) + finds the burden average
    df['burden_score'] = df['tot_ed_nmb_vsts'] / df['ed_stations']
    avg_burden = df['burden_score'].mean()

    # Identifies + filters high-risk areas, where high risk is defined as a facility being classified as a "mental health shortage area" and the burden score being above-average (namely, higher than the mean burden score for the data set)
    df['high_risk'] = (
        (df['mental_health_shortage_area'] == 'Yes') & 
        (df['burden_score'] > avg_burden)
    )
    
    # Returns the facilities that are high risk
    return df[df['high_risk'] == True]

result = mental_health_shortage_analysis(df)
print(result)

"""
Identifies high-risk facilities based on emergency department (ED) burden 
and mental health resource shortages.

A facility is classified as "high risk" if:
1. It is located in a mental health shortage area, AND
2. Its burden score (visits per station) exceeds the average burden 
   within its group (which in this instance is set to year).

Parameters:
    df (pd.DataFrame): Input dataset
    visit_col (str): Column name for total ED visits
    station_col (str): Column name for number of ED stations
    shortage_col (str): Column indicating shortage status
    shortage_value (str): Value indicating a shortage (e.g., "Yes")
    group_col (str): Column used to compute group averages (e.g., year)

Returns:
    pd.DataFrame: Subset of the original DataFrame containing only 
    high-risk facilities, with additional columns:
        - burden_score
        - avg_burden
        - high_risk (boolean)
"""

def mental_health_shortage_analysis(
    df,
    visit_col="tot_ed_nmb_vsts",
    station_col="ed_stations",
    shortage_col="mental_health_shortage_area",
    shortage_value="Yes",
    group_col="year"
):

    # CALCULATION PREP (1): Convert key columns to numeric
    # Ensures calculations work properly and prevents errors
    df[visit_col] = pd.to_numeric(df[visit_col], errors="raise")
    df[station_col] = pd.to_numeric(df[station_col], errors="raise")

    # CALCULATION PREP (2): Prevent division by zero
    # Replace 0 stations with NaN
    df[station_col] = df[station_col].replace(0, np.nan)

    # TYPE CHECKING: Ensure columns are numeric
    if not np.issubdtype(df[visit_col].dtype, np.number):
        raise TypeError(f"{visit_col} must be numeric")
    if not np.issubdtype(df[station_col].dtype, np.number):
        raise TypeError(f"{station_col} must be numeric")

    # BURDEN SCORE: ED visits per station
    df["burden_score"] = df[visit_col] / df[station_col]

    # GROUP BENCHMARK: Average burden within group (e.g., year)
    df["avg_burden"] = df.groupby(group_col)["burden_score"].transform("mean")

    # HIGH-RISK FLAG:
    # 1. In mental health shortage area
    # 2. Burden above group average
    df["high_risk"] = (
        (df[shortage_col] == shortage_value) &
        (df["burden_score"] > df["avg_burden"])
    )
    
    # Returns the facilities that are high risk
    return df[df['high_risk'] == True]