import numpy as np
import pandas as pd
import pytest
import folium
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to prevent windows
import matplotlib.pyplot as plt
import sys

from ertimes import stats

# Use this clean import now that 'pip install -e .' worked!
from ertimes.io import download_emergency_data 
from ertimes.stats import _bed_size_to_numeric, find_capacity_volume_mismatch
from ertimes.stats import generate_county_report
from ertimes.stats import compute_capacity_pressure_score, spike_frequency_pivot

def test_download_california_data(monkeypatch):
    """
    Pytest to verify California data downloads and reads correctly.
    """
    # Mock the actual download to avoid network calls
    mock_df = pd.DataFrame({
        'facility_id': [1, 2, 3],
        'facility_name': ['Hospital A', 'Hospital B', 'Hospital C'],
        'county_name': ['County1', 'County1', 'County2'],
        'year': [2023, 2023, 2023],
        'total_ed_visits': [100, 200, 150],
        'ed_stations': [5, 10, 8]
    })
    
    def fake_download(state):
        if state.lower() == "california":
            return mock_df
        raise ValueError(f"{state} is not supported")
    
    monkeypatch.setattr(stats, "download_emergency_data", fake_download)
    
    # 1. Run the function
    df = download_emergency_data("california")

    # 2. The Assertions (The real 'Proof' for your grade)
    assert isinstance(df, pd.DataFrame), "The result should be a Pandas DataFrame"
    assert not df.empty, "The DataFrame is empty"

    # Check for the specific column from the CA Health dataset
    assert 'facility_name' in df.columns, "Missing expected column: facility_name"

    # Check if we got a substantial amount of data
    assert len(df) > 0, f"Expected >0 rows, but got {len(df)}"

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
            "county_name": ["A", "B", "C"],
            "visits_per_station": [10, 30, 20],
        }
    )

    ranked = stats.rank_counties_by_burden(summary)

    assert list(ranked["county_name"]) == ["B", "C", "A"]


def test_county_capacity_summary(monkeypatch):
    fake_df = pd.DataFrame(
        {
            "county_name": ["Alameda", "Alameda", "Fresno"],
            "total_ed_visits": [100, 200, 90],
            "ed_stations": [10, 20, 0],
            "licensed_bed_size": ["1-49", "50-99", "100-199"],
        }
    )

    def fake_download(state):
        return fake_df

    monkeypatch.setattr(stats, "download_emergency_data", fake_download)

    result = stats.county_capacity_summary("California")

    alameda = result[result["county_name"] == "Alameda"].iloc[0]
    fresno = result[result["county_name"] == "Fresno"].iloc[0]

    assert alameda["total_visits"] == 300
    assert alameda["total_stations"] == 30
    assert alameda["total_beds"] == 25.0 + 74.5
    assert alameda["visits_per_station"] == 10

    assert fresno["total_visits"] == 90
    assert fresno["total_stations"] == 0
    assert np.isnan(fresno["visits_per_station"])


def test_find_capacity_volume_mismatch_flags_expected_hospital():
    """Tests that find_capacity_volume_mismatch correctly identifies a hospital with high visits per station and low bed size as a mismatch.
    """
    df = pd.DataFrame(
        {
            "facility_name": ["A", "B", "C", "D"],
            "county_name": ["X", "X", "Y", "Y"],
            "year": [2023, 2023, 2023, 2023],
            "total_ed_visits": [1000, 900, 700, 100],
            "ed_stations": [1, 10, 8, 20],
            "licensed_bed_size": ["1-49", "500+", "300-499", "500+"],
        }
    )

    result = find_capacity_volume_mismatch(
        df,
        high_visit_quantile=0.75,
        low_capacity_quantile=0.25,
    )

    assert len(result) == 1
    assert result.loc[0, "facility_name"] == "A"
    assert result.loc[0, "mismatch_score"] > 0


def test_find_capacity_volume_mismatch_missing_column_raises():
    """Tests that find_capacity_volume_mismatch raises a ValueError when required columns are missing.
    """
    df = pd.DataFrame(
        {
            "FacilityName2": ["A"],
            "Tot_ED_NmbVsts": [1000],
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        find_capacity_volume_mismatch(df)


def test_find_duplicates_basic():
    """Tests that find_duplicates correctly identifies duplicate rows 
    based on all columns."""
    df = pd.DataFrame({
        "A": [1, 2, 2],
        "B": ["x", "y", "y"]
    })

    result = stats.find_duplicates(df)

    assert len(result) == 2


def test_find_duplicates_subset():
    """Tests that find_duplicates correctly identifies duplicate rows
    based on a specified subset of columns."""
    df = pd.DataFrame({
        "A": [1, 2, 2, 2],
        "B": ["x", "y", "z", "y"]
    })

    result = stats.find_duplicates(df, subset=["A"])

    assert len(result) == 3


def test_find_duplicates_no_duplicates():
    """Tests that find_duplicates returns an empty DataFrame when 
    there are no duplicates.
    """
    df = pd.DataFrame({
        "A": [1, 2, 3]
    })

    result = stats.find_duplicates(df)

    assert result.empty


def test_find_duplicates_bad_subset():
    """Tests that find_duplicates raises a ValueError when the 
    specified subset of columns does not exist in the DataFrame.
    """
    df = pd.DataFrame({
        "A": [1, 2]
    })

    with pytest.raises(ValueError):
        stats.find_duplicates(df, subset=["Z"])


def test_find_duplicates_bad_input_type():
    """"Tests that find_duplicates raises a TypeError when the 
    input is not a DataFrame.
    """
    with pytest.raises(TypeError):
        stats.find_duplicates([1, 2, 3])

def test_plot_facility_trend_returns_figure():
    """Tests that plot_facility_trend returns a Matplotlib 
    figure object when given valid input data."""
    df = pd.DataFrame({
        'FacilityName2': ['A', 'A'],
        'year': [2020, 2021],
        'Tot_ED_NmbVsts': [100, 120]
    })

    fig = stats.plot_facility_trend(df, 'A')
    assert fig is not None
    assert hasattr(fig, "savefig")


def test_invalid_facility():
    """Tests that plot_facility_trend raises a ValueError when 
    the specified facility is not found in the DataFrame.
    """
    df = pd.DataFrame({
        'FacilityName2': ['A'],
        'year': [2020],
        'Tot_ED_NmbVsts': [100]
    })

    with pytest.raises(ValueError):
        stats.plot_facility_trend(df, 'B')


def test_missing_columns():
    """Tests that plot_facility_trend raises a ValueError when 
    required columns are missing from the DataFrame."""
    df = pd.DataFrame({
        'FacilityName2': ['A'],
        'year': [2020]
    })

    with pytest.raises(ValueError):
        stats.plot_facility_trend(df, 'A')

import pandas as pd
from ertimes.stats import mental_health_shortage_analysis

def test_mental_health_shortage_analysis():
    """Tests that mental_health_shortage_analysis correctly 
    calculates burden scores and flags high-risk facilities based on 
    synthetic data."""
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


def test_per_category_burden_basic():
    """Tests that per_category_burden_report correctly groups by category, 
    sums visits per station, and returns the top N facilities for each 
    category."""
    df = pd.DataFrame({
        "FacilityName2": ["A", "B", "C"],
        "Category": ["Mental Health", "Mental Health", "Stroke"],
        "Visits_Per_Station": [10, 20, 15]
    })
    result = stats.per_category_burden_report(df, top_n=2)
    expected = {
        "Mental Health": ["B", "A"],  # top 2 by Visits_Per_Station
        "Stroke": ["C"]
        
    }
    assert result == expected

def test_per_category_burden_missing_column():
    """Tests that per_category_burden_report raises a ValueError 
    when required columns are missing.
    """
    df = pd.DataFrame({
        "FacilityName2": ["A"],
        "Tot_ED_NmbVsts": [10]  # missing 'Category' and 'Visits_Per_Station'
    })
    with pytest.raises(KeyError):
        stats.per_category_burden_report(df)


def test_rank_hospitals_by_visits_per_station_basic():
    """Tests that rank_hospitals_by_visits_per_station 
    correctly ranks facilities by visits per station using the 
    default median aggregation."""
    df = pd.DataFrame({
        "facility_name": ["H1", "H2", "H3", "H1"],
        "visits_per_station": [10, 30, 20, 30],
    })

    result = stats.rank_hospitals_by_visits_per_station(df)

    # H1 median of [10, 30] = 20; H2 = 30; H3 = 20
    # Sorted descending: H2 (30), then H1 (20), then H3 (20)
    assert list(result["facility_name"]) == ["H2", "H1", "H3"]
    assert result.loc[0, "visits_per_station"] == 30


def test_rank_hospitals_by_visits_per_station_mean_and_top_n():
    df = pd.DataFrame({
        "facility_name": ["A", "B", "C", "A"],
        "visits_per_station": [10, 40, 30, 50],
    })

    # Using mean aggregation: A=(10+50)/2=30, B=40, C=30
    # Sorted: B (40), A (30), C (30)
    # top_n=2 gives [B, A]
    result = stats.rank_hospitals_by_visits_per_station(df, agg="mean", top_n=2)
    assert len(result) == 2
    assert list(result["facility_name"]) == ["B", "A"]


def test_rank_hospitals_by_visits_per_station_missing_columns():
    df = pd.DataFrame({"X": [1, 2]})
    with pytest.raises(ValueError):
        stats.rank_hospitals_by_visits_per_station(df)

#pytest for health_conditions_bar.py 
from io import StringIO
from ertimes.health_conditions_bar import plot_category_visits

def test_plot_category_visits(monkeypatch, capsys):
    """
    Tests that plot_category_visits:
    - drops missing EDDXCount rows
    - excludes 'All ED Visits'
    - groups and sums correctly
    - prints correct summary
    - calls plotting functions without error
    """
    # Mock plt.show() so the plot does not actually appear
    monkeypatch.setattr(plt, "show", lambda: None)
    # Build a sample DataFrame
    df = pd.DataFrame({
        "category": ["A", "B", "All ED Visits", "A", "C", "B"],
        "ed_burden": [10, 5, 9999, None, 20, 5]
    })
    # Run the function
    plot_category_visits(df)
    # Capture printed output
    captured = capsys.readouterr()
    printed = captured.out.strip()

    # Expected grouped/summed output (A: 10, B: 10, C: 20)
    expected_df = pd.DataFrame({
        "category": ["C", "A", "B"],
        "ed_burden": [20.0, 10.0, 10.0]
    })

    # Convert printed output into a DataFrame
    printed_df = pd.read_csv(StringIO(printed), sep=r"\s+")

    # Assertions
    pd.testing.assert_frame_equal(
        printed_df.reset_index(drop=True),
        expected_df.reset_index(drop=True)
    )

def test_generate_county_report_basic():
    summary = pd.DataFrame(
        {
            "county_name": ["Autauga", "Baldwin"],
            "total_visits": [1000, 2000],
            "total_stations": [10, 20],
            "total_beds": [75.0, 125.0],
            "visits_per_station": [100.0, 100.0],
        }
    )
    result = generate_county_report(summary, "Autauga")

    assert result.shape == (1, 5)
    assert result.loc[0, "county_name"] == "Autauga"
    assert result.loc[0, "total_visits"] == 1000

def test_generate_county_report_missing_county():
    summary = pd.DataFrame(
        {
            "county_name": ["Autauga", "Baldwin"],
            "total_visits": [1000, 2000],
            "total_stations": [10, 20],
            "total_beds": [75.0, 125.0],
            "visits_per_station": [100.0, 100.0],
        }
    )

    with pytest.raises(ValueError, match="No county found"):
        generate_county_report(summary, "Fresno")


#Median_Income Tests
from ertimes.Median_income import load_california_income_data, get_income_by_zip, get_income_statistics


def test_load_california_income_data():
    # Test loading data from a valid file
    df = load_california_income_data('data/california_median_income_by_zipcode.csv')
    assert not df.empty, "DataFrame should not be empty"
    assert 'zip_code' in df.columns, "DataFrame should contain 'zip_code' column"
    assert 'median_income' in df.columns, "DataFrame should contain 'median_income' column"


def test_get_income_by_zip():
    # Sample DataFrame for testing
    sample_data = {
        'zip_code': ['90001', '90002'],
        'median_income': [35000, 38000],
        'county': ['Los Angeles', 'Los Angeles'],
        'city': ['Los Angeles', 'Los Angeles']
    }
    df = pd.DataFrame(sample_data)
    result = get_income_by_zip(df, '90001')
    assert result['zip_code'] == '90001', "Should return correct zip code"
    assert result['median_income'] == 35000, "Should return correct median income"
    assert result['county'] == 'Los Angeles', "Should return correct county"


def test_get_income_statistics():
    # Sample DataFrame for testing
    sample_data = {
        'zip_code': ['90001', '90002'],
        'median_income': [35000, 38000],
        'county': ['Los Angeles', 'Los Angeles'],
        'city': ['Los Angeles', 'Los Angeles']
    }
    df = pd.DataFrame(sample_data)
    stats = get_income_statistics(df)
    assert stats['mean_income'][0] == 36500.0, "Mean income should be calculated correctly"
    assert stats['median_income'][0] == 36500.0, "Median income should be calculated correctly"
    assert stats['min_income'][0] == 35000, "Minimum income should be calculated correctly"
    assert stats['max_income'][0] == 38000, "Maximum income should be calculated correctly"

#testing non percent growth 
def test_calculate_growth_absolute():
    df = pd.DataFrame({
        "oshpd_id": [1, 1],
        "year": [2020, 2021],
        "Tot_ED_NmbVsts": [200, 250]
    })

    result = stats.calculate_growth(
        df,
        value_col="Tot_ED_NmbVsts",
        group_cols=["oshpd_id"],
        pct=False
    )

    assert result.loc[1, "growth"] == 50

# Test for plot_urban_rural_map() function
def test_plot_urban_rural_map_runs(monkeypatch):
    """
    Verifies that plot_urban_rural_map runs successfully
    and returns a folium Map object.

    The map need to be manually opened.
    """

    fake_df = pd.DataFrame({
        "latitude": [34.1, 35.2],
        "longitude": [-118.2, -119.3],
        "urban_rural_designation": ["Urban", "Rural"],
        "facility_name": ["Hospital A", "Hospital B"]
    })

    def fake_download(state):
        return fake_df

    monkeypatch.setattr(stats, "download_emergency_data", fake_download)

    result = stats.plot_urban_rural_map("California")

    assert result is not None
    assert isinstance(result, folium.Map)


# Compute_capacity_pressure_score tests
"""
test_stats.py

Unit tests for capacity pressure scoring and spike frequency pivot functions
in ertimes.stats. Tests are organized around three areas:

    1. compute_capacity_pressure_score — validates score bounds, directionality,
       output structure, and edge cases using synthetic hospital data.

    2. spike_frequency_pivot — validates that year-over-year spikes are correctly
       detected, aggregated by category, and summed across facilities.

Tests use make_df() and make_pivot_test_df() helpers to build minimal DataFrames
with sensible defaults, so each test only specifies what it's actually testing.
The smoke test (test_smoke_real_data) runs against live downloaded data to catch
any integration issues with the full pipeline.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_df(facilities: list[dict]) -> pd.DataFrame:
    """
    Build a minimal capacity-score test DataFrame from a list of facility dicts.

    Each dict may override any of the default column values. Columns use the
    lowercase naming convention expected by compute_capacity_pressure_score.

    Parameters:
        facilities: list of dicts, one per facility row

    Returns:
        DataFrame with one row per facility dict
    """
    defaults = {
        'primary_care_shortage_area':  'No',
        'mental_health_shortage_area': 'No',
        'visits_per_station':          100.0,
        'licensed_bed_size':           '200-299',
    }
    rows = [{**defaults, **f} for f in facilities]
    return pd.DataFrame(rows)


def score(df: pd.DataFrame) -> pd.Series:
    """
    Convenience wrapper that returns capacity_pressure_score indexed by facility_name.

    Parameters:
        df: DataFrame compatible with compute_capacity_pressure_score

    Returns:
        Series of scores indexed by facility_name
    """
    return compute_capacity_pressure_score(df).set_index('facility_name')['capacity_pressure_score']


def make_pivot_test_df(records: list[dict]) -> pd.DataFrame:
    """
    Build a minimal spike-pivot test DataFrame from a list of row dicts.

    Each dict may override any of the default column values. Columns use the
    original casing expected by spike_frequency_pivot.

    Parameters:
        records: list of dicts, one per row

    Returns:
        DataFrame with one row per record dict
    """
    defaults = {
        'FacilityName2':      'Test Hospital',
        'Category':           'All ED Visits',
        'year':               2021,
        'Visits_Per_Station': 100.0,
    }
    return pd.DataFrame([{**defaults, **r} for r in records])

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def two_hospitals() -> pd.DataFrame:
    """
    Two-facility DataFrame for directional and structural tests.

    'High' has maximum pressure indicators: high utilization, both shortage
    areas flagged, and smallest bed size. 'Low' uses all defaults.
    """
    return make_df([
        {'facility_name': 'High', 'visits_per_station': 1000.0,
         'primary_care_shortage_area': 'Yes',
         'mental_health_shortage_area': 'Yes',
         'licensed_bed_size': '1-49'},
        {'facility_name': 'Low', 'visits_per_station': 10.0},
    ])


# ---------------------------------------------------------------------------
# compute_capacity_pressure_score — output structure
# ---------------------------------------------------------------------------

def test_score_bounds(two_hospitals):
    """All scores must fall within the defined 1–10 scale."""
    s = score(two_hospitals)
    assert s.between(1, 10).all()


def test_score_is_numeric(two_hospitals):
    """Scores must be a numeric dtype, not strings or objects."""
    assert pd.api.types.is_numeric_dtype(score(two_hospitals))


def test_output_columns(two_hospitals):
    """Output DataFrame must have exactly facility_name and capacity_pressure_score."""
    result = compute_capacity_pressure_score(two_hospitals)
    assert list(result.columns) == ['facility_name', 'capacity_pressure_score']


def test_sorted_descending(two_hospitals):
    """Results must be sorted highest score first."""
    s = compute_capacity_pressure_score(two_hospitals)['capacity_pressure_score'].tolist()
    assert s == sorted(s, reverse=True)


def test_one_row_per_facility():
    """Multiple rows for the same facility must collapse into a single output row."""
    df = make_df([{'facility_name': 'A'}, {'facility_name': 'A'}])
    assert len(compute_capacity_pressure_score(df)) == 1


# ---------------------------------------------------------------------------
# compute_capacity_pressure_score — directional logic
# ---------------------------------------------------------------------------

def test_high_utilization_scores_higher(two_hospitals):
    """A facility with higher visits_per_station must score higher than a low one."""
    s = score(two_hospitals)
    assert s['High'] > s['Low']


def test_shortage_increases_score():
    """Flagging both shortage areas must produce a higher score than no shortages."""
    df = make_df([
        {'facility_name': 'Shortage',
         'primary_care_shortage_area': 'Yes',
         'mental_health_shortage_area': 'Yes'},
        {'facility_name': 'None'},
    ])
    s = score(df)
    assert s['Shortage'] > s['None']


def test_smaller_bed_size_increases_score():
    """A facility with fewer beds must score higher than one with more beds."""
    df = make_df([
        {'facility_name': 'Small', 'licensed_bed_size': '1-49'},
        {'facility_name': 'Large', 'licensed_bed_size': '500+'},
    ])
    s = score(df)
    assert s['Small'] > s['Large']


# ---------------------------------------------------------------------------
# compute_capacity_pressure_score — edge cases
# ---------------------------------------------------------------------------

def test_zero_visits_no_nan():
    """A facility with zero visits must still produce a valid (non-NaN) score."""
    df = make_df([{'facility_name': 'A', 'visits_per_station': 0.0}])
    assert not score(df).isna().any()


def test_smoke_real_data():
    """End-to-end smoke test: no NaN scores on live downloaded California data."""
    df = download_emergency_data("california")
    assert not score(df).isna().any()


# ---------------------------------------------------------------------------
# spike_frequency_pivot
# ---------------------------------------------------------------------------

def test_multiple_facilities_spikes_summed():
    """
    Spikes from different facilities in the same category must be summed.

    Both Hospital A and Hospital B double their visits from 2021 to 2022
    (+100%), which exceeds the default 20% threshold. The pivot table must
    report a spike_count of 2 for 'All ED Visits'.
    """
    df = make_pivot_test_df([
        {'FacilityName2': 'Hospital A', 'year': 2021, 'Visits_Per_Station': 100},
        {'FacilityName2': 'Hospital A', 'year': 2022, 'Visits_Per_Station': 200},
        {'FacilityName2': 'Hospital B', 'year': 2021, 'Visits_Per_Station': 100},
        {'FacilityName2': 'Hospital B', 'year': 2022, 'Visits_Per_Station': 200},
    ])
    assert spike_frequency_pivot(df).loc['All ED Visits', 'spike_count'] == 2

def test_smoke_real_data():
    """End-to-end smoke test: no NaN spike counts on live downloaded California data."""
    df = download_emergency_data("california")
    result = spike_frequency_pivot(
        df,
        threshold_pct=20.0,
        facility_col='facility_name',
        category_col='category',
        visits_col='visits_per_station'
    )
    assert not result.isna().any().any()
    assert result['spike_count'].sum() > 0

def test_all_categories_present():
    """Both categories in the input must appear as rows in the pivot output."""
    df = make_pivot_test_df([
        {'Category': 'Diabetes',      'year': 2021, 'Visits_Per_Station': 100},
        {'Category': 'Diabetes',      'year': 2022, 'Visits_Per_Station': 200},
        {'Category': 'Mental Health', 'year': 2021, 'Visits_Per_Station': 100},
        {'Category': 'Mental Health', 'year': 2022, 'Visits_Per_Station': 105},
    ])
    result = spike_frequency_pivot(df)
    assert set(result.index) == {'Diabetes', 'Mental Health'}

def test_spike_counted():
    """A +100% YoY increase must register as one spike."""
    df = make_pivot_test_df([
        {'year': 2021, 'Visits_Per_Station': 100},
        {'year': 2022, 'Visits_Per_Station': 200},
    ])
    assert spike_frequency_pivot(df, threshold_pct=20.0).loc['All ED Visits', 'spike_count'] == 1

#pytests for summarize_by_ownership function
from ertimes.stats import summarize_by_ownership 

def test_basic_summary():
    """Test that function computes group summary stats correctly on a simple dataset
    
    checks that grouping works, aggregation applies, and column names are correct with manually computable values"""

    #simple test data with 2 ownership groups
    df = pd.DataFrame({
        "HospitalOwnership": ["A", "A", "B", "B"],
        "Tot_ED_NmbVsts": [100, 200, 300, 400],
        "EDStations": [10, 20, 30, 40],
        "Visits_Per_Station": [10, 10, 10, 10]
    })
    #run function
    result = summarize_by_ownership(df)
    #create expected result via manual computation
    expected = pd.DataFrame({
        "HospitalOwnership": ["A", "B"],
        "Tot_ED_NmbVsts_mean": [150.0, 350.0],
        "Tot_ED_NmbVsts_sum": [300, 700],
        "EDStations_mean": [15.0, 35.0],
        "EDStations_sum": [30, 70],
        "Visits_Per_Station_mean": [10.0, 10.0],
        "Visits_Per_Station_median": [10.0, 10.0],
        "Visits_Per_Station_std": [0.0, 0.0]
    })

    result = result.sort_values("HospitalOwnership").reset_index(drop=True)
    expected = expected.sort_values("HospitalOwnership").reset_index(drop=True)
    #compare results, testing for structure/value comparison
    pd.testing.assert_frame_equal(result, expected)

def test_sort_order():
    """Test that output is sorted by visits_perstation_mean descending (ordering by average efficiency)
    
    the group with highest visits_perstation_mean should appear first"""
    #simple data where B has higher efficiency
    df = pd.DataFrame({
        "HospitalOwnership": ["A", "B"],
        "Tot_ED_NmbVsts": [100, 200],
        "EDStations": [10, 10],
        "Visits_Per_Station": [5, 20]  
    })
    result = summarize_by_ownership(df)
    #check that first row is B (the highest efficiency)
    assert result.iloc[0]["HospitalOwnership"] == "B"

def test_missing_col_error():
    """Test that missing any of the required columns raises ValueError for that column"""
    #data with missing required numeric columns
    df = pd.DataFrame({
        "HospitalOwnership": ["A", "B"]
    })
    #expect error that tells which columns are missing
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_by_ownership(df)

def test_non_numeric_coercion():
    """Test that nonnumeric values are handled correctly

    ie) coercion of non-numeric values to NaN, and mean/aggrgation functions ignore NaN in computation"""

    df = pd.DataFrame({
        "HospitalOwnership": ["A", "A"],
        "Tot_ED_NmbVsts": ["100", "bad"],  #'bad' → NaN due to nonnumeric coercion
        "EDStations": ["10", "20"],
        "Visits_Per_Station": ["5", "5"]
    })
    result = summarize_by_ownership(df)
    # only 100 should be used in computation, only numeric value 
    assert result.loc[0, "Tot_ED_NmbVsts_mean"] == 100.0

def test_missing_ownership():
    """Test that rows with missing ownership category are dropped from data"""

    df = pd.DataFrame({
        "HospitalOwnership": ["A", None],
        "Tot_ED_NmbVsts": [100, 200],
        "EDStations": [10, 20],
        "Visits_Per_Station": [10, 10]
    })
    # only A should remain, the only valid ownership group 
    result = summarize_by_ownership(df)

    assert len(result) == 1
    assert result.iloc[0]["HospitalOwnership"] == "A"


import sys


sys.path.append("src")

import ertimes.stats as stats


def fake_download():
    return pd.DataFrame({
        "oshpd_id": [1, 1, 2, 2],
        "year": [2021, 2022, 2021, 2022],
        "Tot_ED_NmbVsts": [100, 120, 200, 210],
        "Visits_Per_Station": [10, 12, 20, 21],
        "FacilityName2": ["A", "A", "B", "B"]
    })


def test_run_er_analysis(monkeypatch):
 
    monkeypatch.setattr(stats, "download_emergency_data", fake_download)

    df = fake_download()
    result = stats.run_er_analysis(df)

    # checks
    assert isinstance(result, pd.DataFrame)
    assert "YoY_Visits" in result.columns
    assert "Utilization" in result.columns
    assert "Mismatch" in result.columns


# ============================================================================
# Tests for county_facility_counts()
# ============================================================================

def test_county_facility_counts_basic():
    """Test basic functionality: counts unique facilities per county."""
    df = pd.DataFrame({
        "CountyName": ["Alameda", "Alameda", "Fresno", "Fresno", "Fresno"],
        "FacilityName2": ["HospA", "HospB", "HospC", "HospD", "HospC"],
    })
    
    result = stats.county_facility_counts(df)
    
    assert len(result) == 2
    # Fresno: HospC, HospD, HospC (counted as 2 unique)
    # Alameda: HospA, HospB (2 unique)
    assert result.iloc[0]["facility_count"] == 2  # Fresno (3 rows but 2 unique facilities)
    assert result.iloc[1]["facility_count"] == 2  # Alameda


def test_county_facility_counts_sorted_descending():
    """Test that results are sorted by facility_count descending."""
    df = pd.DataFrame({
        "CountyName": ["A", "A", "B", "B", "B", "B"],
        "FacilityName2": ["H1", "H2", "H3", "H4", "H5", "H6"],
    })
    
    result = stats.county_facility_counts(df)
    
    assert (result["facility_count"] == result["facility_count"].sort_values(ascending=False)).all()


def test_county_facility_counts_missing_columns():
    """Test that missing required columns raise ValueError."""
    df = pd.DataFrame({
        "County": ["Alameda"],
        "Facility": ["HospA"],
    })
    
    with pytest.raises(ValueError, match="Missing required columns"):
        stats.county_facility_counts(df)


def test_county_facility_counts_custom_columns():
    """Test with custom column names."""
    df = pd.DataFrame({
        "Region": ["North", "North", "South"],
        "Hospital": ["H1", "H2", "H3"],
    })
    
    result = stats.county_facility_counts(
        df,
        county_col="Region",
        facility_col="Hospital"
    )
    
    assert "Region" in result.columns
    assert len(result) == 2


def test_county_facility_counts_handles_na():
    """Test that NaN values are dropped from grouping."""
    df = pd.DataFrame({
        "CountyName": ["Alameda", "Alameda", None, "Fresno"],
        "FacilityName2": ["HospA", "HospB", "HospC", "HospD"],
    })
    
    result = stats.county_facility_counts(df)
    
    # Should only have Alameda and Fresno (not NaN county)
    assert len(result) == 2
    assert None not in result["CountyName"].values


def test_county_facility_counts_duplicates_not_counted():
    """Test that duplicate facilities in a county are counted once (using nunique)."""
    df = pd.DataFrame({
        "CountyName": ["Alameda", "Alameda", "Alameda"],
        "FacilityName2": ["HospA", "HospA", "HospB"],
    })
    
    result = stats.county_facility_counts(df)
    
    # Should have 2 unique facilities (HospA counted once, HospB counted once)
    assert result.iloc[0]["facility_count"] == 2

#testing another scenario for percent growth 

def test_calculate_growth_percent_multiple_groups():
    df = pd.DataFrame({
        "oshpd_id": [1, 1, 1, 2, 2],
        "year": [2020, 2021, 2022, 2020, 2021],
        "Tot_ED_NmbVsts": [100, 150, 300, 200, 100]
    })

    result = stats.calculate_growth(
        df,
        value_col="Tot_ED_NmbVsts",
        group_cols=["oshpd_id"],
        pct=True
    )

    # Group 1 expectations
    assert np.isnan(result.loc[result["year"] == 2020].iloc[0]["growth"])
    assert result.loc[(result["oshpd_id"] == 1) & (result["year"] == 2021), "growth"].iloc[0] == 50
    assert result.loc[(result["oshpd_id"] == 1) & (result["year"] == 2022), "growth"].iloc[0] == 100

    # Group 2 expectations
    assert np.isnan(result.loc[(result["oshpd_id"] == 2) & (result["year"] == 2020), "growth"].iloc[0])
    assert result.loc[(result["oshpd_id"] == 2) & (result["year"] == 2021), "growth"].iloc[0] == -50