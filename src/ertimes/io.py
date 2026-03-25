import pandas as pd
import requests
from io import BytesIO

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
    
    return df


def test_data_reading(state: str):
    """
    Tests if the data from the URL is correctly read into a DataFrame.
    """
    try:
        print(f"Attempting to read data for {state}...")
        df = download_emergency_data(state)
        
        # Check 1: Is it actually a DataFrame?
        if isinstance(df, pd.DataFrame):
            print("✓ Success: Data is a valid Pandas DataFrame.")
            
            # Check 2: Does it have rows?
            print(f"✓ Success: Found {len(df)} rows of data.")
            
            # Check 3: Does it have expected columns like 'Facility Name'?
            if 'Facility Name' in df.columns:
                print("✓ Success: 'Facility Name' column detected.")
                
            # Check 4: Show a tiny preview
            print("\nFirst 3 rows of data:")
            print(df.head(3))
            
            return True
    except Exception as e:
        print(f"✗ Failed to read data: {e}")
        return False
if __name__ == "__main__":
    # This runs your new reading test!
    test_data_reading("california")
if __name__ == "__main__":
    # This runs your new reading test!
    test_data_reading("california")