import pandas as pd
from src.ertimes.map_viz import create_ed_map

data = {
    "ed_id": [1,2,3,4],
    "ed_name": ["UVA Hospital", "Sentara Martha Jefferson", "Augusta Health", "Carilion Roanoke"],
    "latitude": [38.03, 38.03, 38.08, 37.27],
    "longitude": [-78.50, -78.48, -78.99, -79.94],
    "year": [2021, 2022, 2022, 2023],
    "total_ed_visits": [70000, 35000, 25000, 60000],
    "county": ["Charlottesville", "Charlottesville", "Augusta", "Roanoke"],
    "primary_care_shortage": ["Yes", "No", "Yes", "No"],
    "mental_health_shortage": ["Yes", "Yes", "No", "Yes"]
}

df = pd.DataFrame(data)

df.to_csv("ed_volume_dataset.csv", index=False)

# Testing this function on my mini dataset:

# df = pd.read_csv("ed_volume_dataset.csv")
# create_ed_map(df, 2022).show()
# the above code would work if I ran it directly in my map_viz file, but because
# this is a test file, I have to use other packages to be able to have the map
# open in a browser tab

import webbrowser
import os

# Create the map
fig = create_ed_map(df, 2022)

# Save to a temporary file
filename = "temp_map.html"
fig.write_html(filename)

# Open the file in a new tab
webbrowser.open('file://' + os.path.realpath(filename))
