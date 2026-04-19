import pandas as pd
import plotly.express as px

def create_ed_map(df, year):
    """
    Create an interactive map of EDs for a given year.
    
    Parameters:
        df (pd.DataFrame): DataFrame with ED info
        year (int): Year to filter the dataset
    Returns:
        fig (plotly.graph_objects.Figure): Interactive map figure
    """
    # Filter for the selected year
    df_year = df[df["year"] == year]
    
    # Map primary care shortage to colors
    color_map = {"Yes": "red", "No": "green"}
    
    # Create the scatter mapbox
    fig = px.scatter_map(
        df_year,
        lat="latitude",
        lon="longitude",
        size="total_ed_visits",
        color="primary_care_shortage",
        color_discrete_map=color_map,
        hover_name="ed_name",
        hover_data={
            "total_ed_visits": True,
            "county": True,
            "primary_care_shortage": True,
            "mental_health_shortage": True,
            "latitude": False,
            "longitude": False
        },
        zoom=7,
        height=600
    )
    
    fig.update_layout(
        mapbox_style="open-street-map",
        title=f"Emergency Department Visits in {year}",
        margin={"r":0,"t":40,"l":0,"b":0}
    )
    
    return fig






