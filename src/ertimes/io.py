import pandas as pd
import requests
from io import BytesIO
from .clean import clean_data

# State-specific data URLs
STATE_URLS = {
    "california": "https://data.chhs.ca.gov/dataset/7fb6eb5e-0f39-4d52-a0c5-8d638b550c24/resource/929362c5-513b-4e89-8a9e-b34834a3004d/download/emergency-department-volume-and-capacity-2021-2023.xlsx",
    # add more states here
}

def download_emergency_data(state: str) -> pd.DataFrame:
    
    state_lower = state.lower()
    
    if state_lower not in STATE_URLS:
        raise ValueError(f"State '{state}' is not supported")
    
    url = STATE_URLS[state_lower]
    
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    df = pd.read_excel(BytesIO(response.content), engine="openpyxl")
    df = clean_data(df)
    
    return df


def load_emergency_data(filepath: str) -> pd.DataFrame:
    """Load and clean emergency department data from a CSV file."""
    df = pd.read_csv(filepath)
    df = clean_data(df)
    return df
