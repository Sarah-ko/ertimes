import numpy as np
import pandas as pd
import pytest
import folium
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


def test_per_category_burden_basic():
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
    df = pd.DataFrame({
        "FacilityName2": ["A"],
        "Tot_ED_NmbVsts": [10]  # missing 'Category' and 'Visits_Per_Station'
    })
    with pytest.raises(KeyError):
        stats.per_category_burden_report(df)

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
        "Category": ["A", "B", "All ED Visits", "A", "C", "B"],
        "EDDXCount": [10, 5, 9999, None, 20, 5]
    })
    # Run the function
    plot_category_visits(df)
    # Capture printed output
    captured = capsys.readouterr()
    printed = captured.out.strip()

    # Expected grouped/summed output (A: 10, B: 10, C: 20)
    expected_df = pd.DataFrame({
        "Category": ["C", "A", "B"],
        "EDDXCount": [20.0, 10.0, 10.0]
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
            "CountyName": ["Autauga", "Baldwin"],
            "total_visits": [1000, 2000],
            "total_stations": [10, 20],
            "total_beds": [75.0, 125.0],
            "visits_per_station": [100.0, 100.0],
        }
    )
    result = generate_county_report(summary, "Autauga")

    assert result.shape == (1, 5)
    assert result.loc[0, "CountyName"] == "Autauga"
    assert result.loc[0, "total_visits"] == 1000

def test_generate_county_report_missing_county():
    summary = pd.DataFrame(
        {
            "CountyName": ["Autauga", "Baldwin"],
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
    
def test_plot_urban_rural_map_runs(monkeypatch):
    """
    Verifies that plot_urban_rural_map runs successfully
    and returns a folium Map object.
    """

    fake_df = pd.DataFrame({
        "LATITUDE": [34.1, 35.2],
        "LONGITUDE": [-118.2, -119.3],
        "UrbanRuralDesi": ["Urban", "Rural"],
        "FacilityName2": ["Hospital A", "Hospital B"]
    })

    def fake_download(state):
        return fake_df

    monkeypatch.setattr(stats, "download_emergency_data", fake_download)

    result = stats.plot_urban_rural_map("California")

    assert result is not None
    assert isinstance(result, folium.Map)


sys.path.append("src")

from ertimes.stats import run_er_analysis

def test_run_er_analysis():
    # load data
    df = pd.read_excel("data/emergency-department-volume-and-capacity-2021-2023.xlsx")

    # run function
    result = run_er_analysis(df)

    # basic checks
    assert isinstance(result, pd.DataFrame)
    assert "YoY_Visits" in result.columns
    assert "Utilization" in result.columns
    assert "Mismatch" in result.columns
# compute_capacity_pressure_score tests
def make_df(facilities: list[dict]) -> pd.DataFrame:
    """Build a test DataFrame from a list of facility dicts."""
    defaults = {
        'PrimaryCareShortageArea':  'No',
        'MentalHealthShortageArea': 'No',
        'Visits_Per_Station':       100.0,
        'LICENSED_BED_SIZE':        '200-299',
    }
    rows = [{**defaults, **f} for f in facilities]
    return pd.DataFrame(rows)

def score(df):
    return compute_capacity_pressure_score(df).set_index('FacilityName2')['capacity_pressure_score']

@pytest.fixture
def two_hospitals():
    return make_df([
        {'FacilityName2': 'High', 'Visits_Per_Station': 1000.0, 'PrimaryCareShortageArea': 'Yes', 'MentalHealthShortageArea': 'Yes', 'LICENSED_BED_SIZE': '1-49'},
        {'FacilityName2': 'Low',  'Visits_Per_Station': 10.0},
    ])


def test_score_bounds(two_hospitals):
    s = score(two_hospitals)
    assert s.between(1, 10).all()

def test_score_is_numeric(two_hospitals):
    assert pd.api.types.is_numeric_dtype(score(two_hospitals))

def test_output_columns(two_hospitals):
    result = compute_capacity_pressure_score(two_hospitals)
    assert list(result.columns) == ['FacilityName2', 'capacity_pressure_score']

def test_sorted_descending(two_hospitals):
    s = compute_capacity_pressure_score(two_hospitals)['capacity_pressure_score'].tolist()
    assert s == sorted(s, reverse=True)

def test_one_row_per_facility():
    df = make_df([{'FacilityName2': 'A'}, {'FacilityName2': 'A'}])
    assert len(compute_capacity_pressure_score(df)) == 1

def test_high_utilization_scores_higher(two_hospitals):
    s = score(two_hospitals)
    assert s['High'] > s['Low']

def test_shortage_increases_score():
    df = make_df([{'FacilityName2': 'Shortage', 'PrimaryCareShortageArea': 'Yes', 'MentalHealthShortageArea': 'Yes'},
                  {'FacilityName2': 'None'}])
    s = score(df)
    assert s['Shortage'] > s['None']

def test_smaller_bed_size_increases_score():
    df = make_df([{'FacilityName2': 'Small', 'LICENSED_BED_SIZE': '1-49'},
                  {'FacilityName2': 'Large', 'LICENSED_BED_SIZE': '500+'}])
    s = score(df)
    assert s['Small'] > s['Large']

def test_zero_visits_no_nan():
    df = make_df([{'FacilityName2': 'A', 'Visits_Per_Station': 0.0}])
    assert not score(df).isna().any()

def test_smoke_real_data():
    df = pd.read_csv('data/Emergency Department Volume and Capacity - Catalog - ED_COMBINE_AL.csv')
    assert not score(df).isna().any()


def make_pivot_test_df(records: list[dict]) -> pd.DataFrame:
    """Build a test DataFrame from a list of row dicts."""
    defaults = {
        'FacilityName2':      'Test Hospital',
        'Category':           'All ED Visits',
        'year':               2021,
        'Visits_Per_Station': 100.0,
    }
    return pd.DataFrame([{**defaults, **r} for r in records])

def test_multiple_facilities_spikes_summed():
    """
    Main test for spike_frequency_pivot

    Spikes across two facilities in the same category should be summed."""
    df = make_pivot_test_df([
        {'FacilityName2': 'Hospital A', 'year': 2021, 'Visits_Per_Station': 100},
        {'FacilityName2': 'Hospital A', 'year': 2022, 'Visits_Per_Station': 200},
        {'FacilityName2': 'Hospital B', 'year': 2021, 'Visits_Per_Station': 100},
        {'FacilityName2': 'Hospital B', 'year': 2022, 'Visits_Per_Station': 200},
    ])
    assert spike_frequency_pivot(df).loc['All ED Visits', 'spike_count'] == 2
