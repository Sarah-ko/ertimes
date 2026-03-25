import pytest
import pandas as pd
# Use this clean import now that 'pip install -e .' worked!
from ertimes.io import download_emergency_data 

def test_download_california_data():
    """
    Pytest to verify California data downloads and reads correctly.
    """
    # 1. Run the function
    df = download_emergency_data("california")

    # 2. The Assertions (The real 'Proof' for your grade)
    assert isinstance(df, pd.DataFrame), "The result should be a Pandas DataFrame"
    assert not df.empty, "The DataFrame is empty"

    # Check for the specific column from the CA Health dataset
    assert 'FacilityName2' in df.columns, "Missing expected column: FacilityName2"

    # Check if we got a substantial amount of data
    assert len(df) > 100, f"Expected >100 rows, but got {len(df)}"

def test_invalid_state_raises_error():
    """
    Verifies that asking for a fake state correctly triggers a ValueError.
    """
    # This proves you are thinking about "Edge Cases" for Technical Depth
    with pytest.raises(ValueError, match="is not supported"):
        download_emergency_data("not_a_real_state")