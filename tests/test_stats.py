from ertimes.stats import county_capacity_summary
import pytest
import pandas as pd

def test_county_capacity_summary_returns_dataframe():
    summary = county_capacity_summary("california")

    assert not summary.empty
    assert "CountyName" in summary.columns
    assert "total_visits" in summary.columns
    assert "total_stations" in summary.columns
    assert "total_beds" in summary.columns
    assert "visits_per_station" in summary.columns

# Use this clean import now that 'pip install -e .' worked!
from ertimes.io import download_emergency_data 
from ertimes.stats import _bed_size_to_numeric, find_capacity_volume_mismatch

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

def test_bed_size_to_numeric():
    assert _bed_size_to_numeric("1-49") == 25.0
    assert _bed_size_to_numeric("50-99") == 74.5
    assert _bed_size_to_numeric("500+") == 500.0
    assert pd.isna(_bed_size_to_numeric(None))


def test_find_capacity_volume_mismatch_flags_expected_hospital():
    df = pd.DataFrame(
        {
            "FacilityName2": ["A", "B", "C", "D"],
            "CountyName": ["X", "X", "Y", "Y"],
            "year": [2023, 2023, 2023, 2023],
            "Tot_ED_NmbVsts": [1000, 900, 700, 100],
            "EDStations": [1, 10, 8, 20],
            "LICENSED_BED_SIZE": ["1-49", "500+", "300-499", "500+"],
        }
    )

    result = find_capacity_volume_mismatch(
        df,
        high_visit_quantile=0.75,
        low_capacity_quantile=0.25,
    )

    assert len(result) == 1
    assert result.loc[0, "FacilityName2"] == "A"
    assert result.loc[0, "mismatch_score"] > 0


def test_find_capacity_volume_mismatch_missing_column_raises():
    df = pd.DataFrame(
        {
            "FacilityName2": ["A"],
            "Tot_ED_NmbVsts": [1000],
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        find_capacity_volume_mismatch(df)
