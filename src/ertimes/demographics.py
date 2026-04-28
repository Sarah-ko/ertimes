
from functools import reduce
from pathlib import Path

import pandas as pd


DATA_URLS = {
    "calidemodata": (
        "https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vThWsHWEJm2Kr_HFyesdrkKOcQIkoNqQXBI_wHjeTbrcbXvr4ak3IaDZJkHTzfalTdYbIf0T0mGIMbz/"
        "pub?output=csv"
    )
}


COUNTY_COLUMNS = {
    "a": "acounty9grade",
    "b": "bcountymedfamincome",
    "c": "ccountyfambelowpov",
    "d": "dcountylang",
    "e": "ecountypop<18",
    "f": "fcountyamerind",
}


def standardize_county_names(series: pd.Series) -> pd.Series:
    """
    Standardize county names for consistent merging.

    This strips whitespace, converts values to lowercase, and removes the
    trailing " county" suffix when present.

    Parameters
    ----------
    series : pd.Series
        Series containing county names.

    Returns
    -------
    pd.Series
        Standardized county-name values.
    """
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" county", "", regex=False)
    )


def standardize_county(series: pd.Series) -> pd.Series:
    """
    Alias for standardize_county_names.

    Kept for compatibility with the original demomerge.py helper.
    """
    return standardize_county_names(series)


def clean_demographic_data(
    df: pd.DataFrame,
    county_columns: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Clean the demographic dataset into one row per county.

    The source demographic spreadsheet stores related county-level variables in
    separate prefixed column blocks. This function extracts each block,
    standardizes the county column, removes duplicate county columns, and merges
    the blocks into one county-level DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Raw demographic DataFrame.
    county_columns : dict[str, str] | None
        Mapping from prefix to the primary county column for that block.
        Defaults to COUNTY_COLUMNS.

    Returns
    -------
    pd.DataFrame
        Cleaned county-level demographic DataFrame.

    Raises
    ------
    TypeError
        If df is not a pandas DataFrame.
    ValueError
        If no valid county-based blocks are found.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    if county_columns is None:
        county_columns = COUNTY_COLUMNS

    work = df.copy()
    blocks: list[pd.DataFrame] = []

    for prefix, main_county_col in county_columns.items():
        cols = [col for col in work.columns if str(col).startswith(prefix)]

        if not cols or main_county_col not in cols:
            continue

        block = work[cols].copy()
        block = block.rename(columns={main_county_col: "county"})

        extra_county_cols = [
            col
            for col in block.columns
            if col != "county" and str(col).startswith(prefix + "county")
        ]
        if extra_county_cols:
            block = block.drop(columns=extra_county_cols)

        block["county"] = standardize_county_names(block["county"])

        block = block[block["county"].notna()]
        block = block[block["county"] != ""]
        block = block[block["county"] != "nan"]

        block = block.drop_duplicates(subset="county")

        blocks.append(block)

    if not blocks:
        raise ValueError("No county-based blocks were found in the dataset.")

    merged = reduce(
        lambda left, right: pd.merge(left, right, on="county", how="outer"),
        blocks,
    )

    return merged


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compatibility wrapper for the original democlean.clean_data function.

    Prefer clean_demographic_data in new code.
    """
    return clean_demographic_data(df)


def download_demographic_data(dataset: str = "calidemodata") -> pd.DataFrame:
    """
    Download a supported demographic dataset and return a cleaned DataFrame.

    Parameters
    ----------
    dataset : str
        Dataset key. Currently supports "calidemodata".

    Returns
    -------
    pd.DataFrame
        Cleaned demographic DataFrame.

    Raises
    ------
    ValueError
        If the dataset key is not supported.
    """
    dataset_lower = dataset.lower()

    if dataset_lower not in DATA_URLS:
        raise ValueError(f"Dataset '{dataset}' is not supported")

    raw_df = pd.read_csv(DATA_URLS[dataset_lower])
    return clean_demographic_data(raw_df)


def download_data(dataset: str) -> pd.DataFrame:
    """
    Compatibility wrapper for the original demodata.download_data function.

    Prefer download_demographic_data in new code.
    """
    return download_demographic_data(dataset)


def load_demographic_data(filepath: str | Path) -> pd.DataFrame:
    """
    Load a local demographic CSV file and return a cleaned DataFrame.

    Parameters
    ----------
    filepath : str | Path
        Path to a demographic CSV file.

    Returns
    -------
    pd.DataFrame
        Cleaned demographic DataFrame.
    """
    raw_df = pd.read_csv(filepath)
    return clean_demographic_data(raw_df)


def load_data(filepath: str | Path) -> pd.DataFrame:
    """
    Compatibility wrapper for the original demodata.load_data function.

    Prefer load_demographic_data in new code.
    """
    return load_demographic_data(filepath)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of df with standardized lowercase snake-style column names.

    This mirrors the behavior originally used for hospital data in demomerge.py.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    work = df.copy()
    work.columns = (
        work.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^\\w]", "", regex=True)
    )

    return work


def load_hospital_data(filepath: str | Path) -> pd.DataFrame:
    """
    Load hospital/emergency-response data from a CSV and normalize column names.

    Parameters
    ----------
    filepath : str | Path
        Path to a hospital/emergency-response CSV file.

    Returns
    -------
    pd.DataFrame
        Loaded DataFrame with normalized column names.
    """
    df = pd.read_csv(filepath)
    return normalize_column_names(df)


def find_county_column(
    df: pd.DataFrame,
    possible_cols: list[str] | None = None,
) -> str:
    """
    Find a likely county column in a hospital/emergency-response DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to inspect.
    possible_cols : list[str] | None
        Candidate county column names. Defaults to common normalized names.

    Returns
    -------
    str
        Name of the detected county column.

    Raises
    ------
    ValueError
        If no county column is found.
    """
    if possible_cols is None:
        possible_cols = ["county", "county_name", "countyname"]

    for col in possible_cols:
        if col in df.columns:
            return col

    raise ValueError("No county column found in hospital dataset.")


def merge_with_demographics(
    hospital_data: pd.DataFrame | str | Path,
    demographic_data: pd.DataFrame | str | Path | None = None,
    dataset: str = "calidemodata",
    county_col: str | None = None,
    how: str = "left",
) -> pd.DataFrame:
    """
    Merge hospital/emergency-response data with county-level demographic data.

    Parameters
    ----------
    hospital_data : pd.DataFrame | str | Path
        Hospital data as a DataFrame or path to a CSV file.
    demographic_data : pd.DataFrame | str | Path | None
        Optional demographic data as a DataFrame or path to a CSV file.
        If None, the supported demographic dataset is downloaded.
    dataset : str
        Dataset key used when demographic_data is None.
    county_col : str | None
        County column in hospital_data. If None, common names are detected.
    how : str
        Merge method passed to pandas.merge. Defaults to "left".

    Returns
    -------
    pd.DataFrame
        Hospital data merged with demographic columns by standardized county.

    Raises
    ------
    ValueError
        If no county column is found in the hospital data.
    """
    if isinstance(hospital_data, (str, Path)):
        hospital_df = load_hospital_data(hospital_data)
    elif isinstance(hospital_data, pd.DataFrame):
        hospital_df = normalize_column_names(hospital_data)
    else:
        raise TypeError("hospital_data must be a DataFrame, string path, or Path")

    if demographic_data is None:
        demo_df = download_demographic_data(dataset)
    elif isinstance(demographic_data, (str, Path)):
        demo_df = load_demographic_data(demographic_data)
    elif isinstance(demographic_data, pd.DataFrame):
        demo_df = clean_demographic_data(demographic_data)
    else:
        raise TypeError("demographic_data must be None, a DataFrame, string path, or Path")

    if county_col is None:
        county_col = find_county_column(hospital_df)

    if county_col not in hospital_df.columns:
        raise ValueError(f"County column '{county_col}' not found in hospital dataset")

    if "county" not in demo_df.columns:
        raise ValueError("Demographic dataset must contain a 'county' column after cleaning")

    hospital_df = hospital_df.rename(columns={county_col: "county"}).copy()

    hospital_df["county"] = standardize_county_names(hospital_df["county"])
    demo_df = demo_df.copy()
    demo_df["county"] = standardize_county_names(demo_df["county"])

    merged_df = pd.merge(hospital_df, demo_df, on="county", how=how)
    return merged_df


def merge_datasets(hospital_filepath: str | Path) -> pd.DataFrame:
    """
    Compatibility wrapper for the original demomerge.merge_datasets function.

    Prefer merge_with_demographics in new code.
    """
    return merge_with_demographics(hospital_filepath)