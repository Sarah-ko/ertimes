import pandas as pd
import requests
from io import BytesIO

STATE_URLS = {
    "california": "https://data.chhs.ca.gov/dataset/7fb6eb5e-0f39-4d52-a0c5-8d638b550c24/resource/929362c5-513b-4e89-8a9e-b34834a3004d/download/emergency-department-volume-and-capacity-2021-2023.xlsx",
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
    
    return df


def test_data_reading(state: str):
    """
    Tests if the data from the URL is correctly read into a DataFrame.
    """
    try:
        print(f"Attempting to read data for {state}...")
        df = download_emergency_data(state)
        
        if isinstance(df, pd.DataFrame):
            print("✓ Success: Data is a valid Pandas DataFrame.")
            
            print(f"✓ Success: Found {len(df)} rows of data.")
            
            if 'Facility Name' in df.columns:
                print("✓ Success: 'Facility Name' column detected.")
                
            print("\nFirst 3 rows of data:")
            print(df.head(3))
            
            return True
    except Exception as e:
        print(f"✗ Failed to read data: {e}")
        return False
if __name__ == "__main__":
    test_data_reading("california")
if __name__ == "__main__":
    test_data_reading("california")