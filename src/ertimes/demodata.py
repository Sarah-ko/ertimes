import pandas as pd
from ertimes.democlean import clean_data

DATA_URLS = {
    "calidemodata": "https://docs.google.com/spreadsheets/d/e/2PACX-1vThWsHWEJm2Kr_HFyesdrkKOcQIkoNqQXBI_wHjeTbrcbXvr4ak3IaDZJkHTzfalTdYbIf0T0mGIMbz/pub?output=csv"
}


def download_data(dataset: str) -> pd.DataFrame:
    dataset_lower = dataset.lower()

    if dataset_lower not in DATA_URLS:
        raise ValueError(f"Dataset '{dataset}' is not supported")

    url = DATA_URLS[dataset_lower]
    df = pd.read_csv(url)
    df = clean_data(df)

    return df


def load_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df = clean_data(df)
    return df