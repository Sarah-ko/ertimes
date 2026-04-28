from ertimes.map_viz import create_ed_map
import pandas as pd

def test_create_ed_map_filters_year():
    """Tests that the create_ed_map function correctly filters data by year."""
    df = pd.DataFrame({
        "year": [2022, 2022, 2023],
        "latitude": [1, 2, 3],
        "longitude": [1, 2, 3],
        "total_ed_visits": [100, 200, 300],
        "primary_care_shortage": ["Yes", "No", "Yes"],
        "mental_health_shortage": ["Yes", "Yes", "No"],
        "ed_name": ["A", "B", "C"],
        "county": ["X", "Y", "Z"]
    })

    fig = create_ed_map(df, 2022)

    total_points = sum(len(trace.lat) for trace in fig.data)
    assert total_points == 2