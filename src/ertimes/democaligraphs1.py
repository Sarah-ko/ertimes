import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def load_merged_data(filepath: str) -> pd.DataFrame:
    """
    This function loads the merged hospital/demographic data dataset from a CSV file.

    Parameters
    ----------
    filepath : str
        This is the path to the merged CSV file.

    Returns
    -------
    pd.DataFrame
        This is a cleaned dataframe with standardized county names.
    """
    df = pd.read_csv(filepath)

    # Standardize county names so grouping works even if capitalization/spaces differ.
    df["county"] = (
        df["county"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" county", "", regex=False)
    )

    return df


def clean_numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
    """
    This function converts each column to numeric values, removing commas if needed.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    column : str
        Column name to clean.

    Returns
    -------
    pd.Series
        Numeric version of the column.
    """
    return pd.to_numeric(
        df[column].astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    )


def summarize_by_county(df: pd.DataFrame) -> pd.DataFrame:
    """
    This function create sone row per county.

    Demographic variables are averaged or taken as first values because they are
    county-level values repeated across hospital rows. Hospital variables are
    averaged across hospitals/years within each county.
    """

    # Columns that should be numeric before aggregation.
    numeric_cols = [
        "cfambelowpovperc",
        "cpersbelowpovperc",
        "aperclessHS",
        "apercbachplus",
        "bmedianfamincome",
        "bmedianHHincome",
        "dpercnonenglish",
        "epop>65perc",
        "fhispperc",
        "fblackperc",
        "fwhiteperc",
        "fforbornperc",
        "tot_ed_nmbvsts",
        "visits_per_station",
        "edstations",
    ]

    # Make a copy so the original dataframe is not changed unexpectedly.
    df = df.copy()

    # Clean all selected numeric columns.
    for col in numeric_cols:
        if col in df.columns:
            df[col] = clean_numeric_column(df, col)

    # Group by county to create county-level data.
    county_df = df.groupby("county", as_index=False).agg({
        # Demographic variables
        "cfambelowpovperc": "first",
        "cpersbelowpovperc": "first",
        "aperclessHS": "first",
        "apercbachplus": "first",
        "bmedianfamincome": "first",
        "bmedianHHincome": "first",
        "dpercnonenglish": "first",
        "epop>65perc": "first",
        "fhispperc": "first",
        "fblackperc": "first",
        "fwhiteperc": "first",
        "fforbornperc": "first",

        # Hospital shortage area categories
        "mentalhealthshortagearea": "first",
        "primarycareshortagearea": "first",

        # Hospital/ED variables
        "tot_ed_nmbvsts": "mean",
        "visits_per_station": "mean",
        "edstations": "mean",
    })

    return county_df


def graph_boxplot_by_category(
    county_df: pd.DataFrame,
    numeric_col: str,
    category_col: str,
    x_label: str,
    y_label: str,
    title: str
) -> None:
    """
    This makes a boxplot comparing a numeric demographic variable across a categorical
    hospital shortage-area variable.
    """

    # Keep only needed columns and remove missing values.
    plot_df = county_df[[numeric_col, category_col]].dropna().copy()

    # Converts the numeric column safely.
    plot_df[numeric_col] = pd.to_numeric(plot_df[numeric_col], errors="coerce")
    plot_df = plot_df.dropna()

    groups = []
    labels = []

    # Creates one boxplot group for each shortage-area category.
    for category in sorted(plot_df[category_col].unique()):
        group = plot_df.loc[plot_df[category_col] == category, numeric_col]
        if len(group) > 0:
            groups.append(group)
            labels.append(str(category))

    plt.figure(figsize=(8, 6))
    plt.boxplot(groups, tick_labels=labels)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.tight_layout()
    plt.show()


def graph_scatter(
    county_df: pd.DataFrame,
    x_col: str,
    y_col: str,
    x_label: str,
    y_label: str,
    title: str
) -> None:
    """
    This makes a scatterplot comparing one demographic variable to one hospital variable.

    A simple trendline is added when there are at least two valid points.
    """

    # Keep only the columns needed for the graph.
    plot_df = county_df[[x_col, y_col]].dropna().copy()

    # Convert both columns to numeric values.
    plot_df[x_col] = pd.to_numeric(plot_df[x_col], errors="coerce")
    plot_df[y_col] = pd.to_numeric(plot_df[y_col], errors="coerce")
    plot_df = plot_df.dropna()

    plt.figure(figsize=(8, 6))
    plt.scatter(plot_df[x_col], plot_df[y_col])

    # Add a linear trendline to make the overall relationship easier to see.
    if len(plot_df) >= 2:
        slope, intercept = np.polyfit(plot_df[x_col], plot_df[y_col], 1)
        x_vals = np.linspace(plot_df[x_col].min(), plot_df[x_col].max(), 100)
        y_vals = slope * x_vals + intercept
        plt.plot(x_vals, y_vals)

    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.tight_layout()
    plt.show()


def graph_correlation_heatmap(county_df: pd.DataFrame) -> None:
    """
    This makes a simple correlation heatmap for selected demographic and hospital variables.
    """

    selected_cols = [
        "cfambelowpovperc",
        "cpersbelowpovperc",
        "aperclessHS",
        "apercbachplus",
        "bmedianHHincome",
        "dpercnonenglish",
        "epop>65perc",
        "fforbornperc",
        "tot_ed_nmbvsts",
        "visits_per_station",
        "edstations",
    ]

    # Keep only columns that are actually present.
    selected_cols = [col for col in selected_cols if col in county_df.columns]

    # Create numeric-only correlation dataframe.
    corr_df = county_df[selected_cols].apply(pd.to_numeric, errors="coerce").corr()

    plt.figure(figsize=(10, 8))
    plt.imshow(corr_df)
    plt.colorbar(label="Correlation")
    plt.xticks(range(len(corr_df.columns)), corr_df.columns, rotation=90)
    plt.yticks(range(len(corr_df.columns)), corr_df.columns)
    plt.title("Correlation Heatmap: Demographics vs. Hospital Variables")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # Load the merged dataset.
    df = load_merged_data("merged_output.csv")

    # Summarize to one row per county so demographic data is not repeated by hospital row.
    county_df = summarize_by_county(df)

    # Print a quick preview to confirm the county-level dataset was created.
    print(county_df.head())
    print("\nCounty-level shape:", county_df.shape)

    # Graph: poverty vs mental health shortage area.
    graph_boxplot_by_category(
        county_df,
        numeric_col="cfambelowpovperc",
        category_col="mentalhealthshortagearea",
        x_label="Mental Health Shortage Area",
        y_label="Families Below Poverty (%)",
        title="County Family Poverty vs. Mental Health Shortage Area"
    )

    # Graph: poverty vs visits per station.
    graph_scatter(
        county_df,
        x_col="cfambelowpovperc",
        y_col="visits_per_station",
        x_label="Families Below Poverty (%)",
        y_label="Average Visits per Station",
        title="County Family Poverty vs. Average Visits per Station"
    )

    # Graph 1: household income vs visits per station.
    graph_scatter(
        county_df,
        x_col="bmedianHHincome",
        y_col="visits_per_station",
        x_label="Median Household Income ($)",
        y_label="Average Visits per Station",
        title="Median Household Income vs. Average Visits per Station"
    )

    # Graph 2: percent non-English-speaking households vs ED visits.
    graph_scatter(
        county_df,
        x_col="dpercnonenglish",
        y_col="tot_ed_nmbvsts",
        x_label="Non-English-Speaking Households (%)",
        y_label="Average Total ED Visits",
        title="Non-English-Speaking Households vs. Average ED Visits"
    )

    # Graph 3: percent with bachelor's degree or higher vs visits per station.
    graph_scatter(
        county_df,
        x_col="apercbachplus",
        y_col="visits_per_station",
        x_label="Bachelor's Degree or Higher (%)",
        y_label="Average Visits per Station",
        title="Education Level vs. Average Visits per Station"
    )

    # Graph 4: percent age 65+ vs ED stations.
    graph_scatter(
        county_df,
        x_col="epop>65perc",
        y_col="edstations",
        x_label="Population Age 65+ (%)",
        y_label="Average Number of ED Stations",
        title="Older Adult Population vs. ED Stations"
    )

    # Graph 5: percent foreign-born vs total ED visits.
    graph_scatter(
        county_df,
        x_col="fforbornperc",
        y_col="tot_ed_nmbvsts",
        x_label="Foreign-Born Population (%)",
        y_label="Average Total ED Visits",
        title="Foreign-Born Population vs. Average ED Visits"
    )

    # Graph 6: personal poverty vs primary care shortage area.
    graph_boxplot_by_category(
        county_df,
        numeric_col="cpersbelowpovperc",
        category_col="primarycareshortagearea",
        x_label="Primary Care Shortage Area",
        y_label="People Below Poverty (%)",
        title="County Poverty vs. Primary Care Shortage Area"
    )

    # Graph 7: correlation heatmap for selected demographic and hospital variables.
    graph_correlation_heatmap(county_df)
