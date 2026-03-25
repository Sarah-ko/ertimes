from ertimes.stats import county_capacity_summary


def test_county_capacity_summary_returns_dataframe():
    summary = county_capacity_summary("california")

    assert not summary.empty
    assert "CountyName" in summary.columns
    assert "total_visits" in summary.columns
    assert "total_stations" in summary.columns
    assert "total_beds" in summary.columns
    assert "visits_per_station" in summary.columns