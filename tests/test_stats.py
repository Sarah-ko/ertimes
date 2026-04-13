import numpy as np
import pandas as pd
import pytest

from ertimes import stats

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
    assert stats._bed_size_to_numeric("1-49") == 25.0
    assert stats._bed_size_to_numeric("50-99") == 74.5
    assert stats._bed_size_to_numeric("500+") == 500.0
    assert np.isnan(stats._bed_size_to_numeric(None))
    assert np.isnan(stats._bed_size_to_numeric("unknown"))

def test_rank_counties_by_burden():
    summary = pd.DataFrame(
        {
            "CountyName": ["A", "B", "C"],
            "visits_per_station": [10, 30, 20],
        }
    )

    ranked = stats.rank_counties_by_burden(summary)

    assert list(ranked["CountyName"]) == ["B", "C", "A"]


def test_county_capacity_summary(monkeypatch):
    fake_df = pd.DataFrame(
        {
            "CountyName": ["Alameda", "Alameda", "Fresno"],
            "Tot_ED_NmbVsts": [100, 200, 90],
            "EDStations": [10, 20, 0],
            "LICENSED_BED_SIZE": ["1-49", "50-99", "100-199"],
        }
    )

    def fake_download(state):
        return fake_df

    monkeypatch.setattr(stats, "download_emergency_data", fake_download)

    result = stats.county_capacity_summary("California")

    alameda = result[result["CountyName"] == "Alameda"].iloc[0]
    fresno = result[result["CountyName"] == "Fresno"].iloc[0]

    assert alameda["total_visits"] == 300
    assert alameda["total_stations"] == 30
    assert alameda["total_beds"] == 25.0 + 74.5
    assert alameda["visits_per_station"] == 10

    assert fresno["total_visits"] == 90
    assert fresno["total_stations"] == 0
    assert np.isnan(fresno["visits_per_station"])


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


def test_find_duplicates_basic():
    df = pd.DataFrame({
        "A": [1, 2, 2],
        "B": ["x", "y", "y"]
    })

    result = stats.find_duplicates(df)

    assert len(result) == 2


def test_find_duplicates_subset():
    df = pd.DataFrame({
        "A": [1, 2, 2, 2],
        "B": ["x", "y", "z", "y"]
    })

    result = stats.find_duplicates(df, subset=["A"])

    assert len(result) == 3


def test_find_duplicates_no_duplicates():
    df = pd.DataFrame({
        "A": [1, 2, 3]
    })

    result = stats.find_duplicates(df)

    assert result.empty


def test_find_duplicates_bad_subset():
    df = pd.DataFrame({
        "A": [1, 2]
    })

    with pytest.raises(ValueError):
        stats.find_duplicates(df, subset=["Z"])


def test_find_duplicates_bad_input_type():
    with pytest.raises(TypeError):
        stats.find_duplicates([1, 2, 3])

def test_plot_facility_trend_returns_figure():
    df = pd.DataFrame({
        'FacilityName2': ['A', 'A'],
        'year': [2020, 2021],
        'Tot_ED_NmbVsts': [100, 120]
    })

    fig = stats.plot_facility_trend(df, 'A')
    assert fig is not None
    assert hasattr(fig, "savefig")


def test_invalid_facility():
    df = pd.DataFrame({
        'FacilityName2': ['A'],
        'year': [2020],
        'Tot_ED_NmbVsts': [100]
    })

    with pytest.raises(ValueError):
        stats.plot_facility_trend(df, 'B')


def test_missing_columns():
    df = pd.DataFrame({
        'FacilityName2': ['A'],
        'year': [2020]
    })

    with pytest.raises(ValueError):
        stats.plot_facility_trend(df, 'A')

import pandas as pd
from ertimes.stats import mental_health_shortage_analysis

def test_mental_health_shortage_analysis():
    data = {
        'Tot_ED_NmbVsts': [1000, 2000],
        'EDStations': [10, 20],
        'MentalHealthShortageArea': ['Yes', 'No']
    }

    df = pd.DataFrame(data)
    result = mental_health_shortage_analysis(df)

    assert 'burden_score' in result.columns
    assert 'high_risk' in result.columns
    assert result['burden_score'].iloc[0] == 100       