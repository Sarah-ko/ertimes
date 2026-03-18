import pandas as pd

def get_er_data():
  """
  Download ER volume dataset from website.
  Returns a pandas DataFrame.
  """
  
  url = "https://example.com/er_volume_data.csv"
  data = pd.read_csv(url)
  return = data
