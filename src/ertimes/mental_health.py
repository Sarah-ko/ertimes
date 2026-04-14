import pandas as pd
import numpy as np
from clean import clean_data  



df = pd.read_csv("data/Emergency Department Volume and Capacity - Catalog - ED_COMBINE_AL.csv")

df = clean_data(df) 

"""
This function highlights facilities that experience both an above-average burden (namely, a higher-than-normal demand relative to available resources) and a shortage of mental health resources, identifying them at high-risk.
"""

def mental_health_shortage_analysis(df):

    
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