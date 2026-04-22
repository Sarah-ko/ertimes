import pandas as pd
import matplotlib.pyplot as plt


def load_merged_data(filepath: str) -> pd.DataFrame:
    """Loads the merged dataset from a CSV file and standardizes 
    county names."""
    
    df = pd.read_csv(filepath)

    # standardize county names just in case
    df["county"] = (
        df["county"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" county", "", regex=False)
    )

    return df


def summarize_by_county(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create one row per county.
    Adjust aggregation methods depending on the variable.
    """
    county_df = df.groupby("county", as_index=False).agg({
        "cfambelowpovperc": "first",
        "mentalhealthshortagearea": "first",
        "tot_ed_nmbvsts": "mean",
        "visits_per_station": "mean",
        "edstations": "mean"
    })

    return county_df


def graph_poverty_vs_mentalhealth(county_df: pd.DataFrame):
    """
    Boxplot of family-below-poverty percent by mental health shortage area category.
    """
    plot_df = county_df[["cfambelowpovperc", "mentalhealthshortagearea"]].dropna()

    # convert to numeric if needed
    plot_df["cfambelowpovperc"] = pd.to_numeric(plot_df["cfambelowpovperc"], errors="coerce")
    plot_df = plot_df.dropna()

    groups = []
    labels = []

    for category in sorted(plot_df["mentalhealthshortagearea"].unique()):
        group = plot_df.loc[
            plot_df["mentalhealthshortagearea"] == category,
            "cfambelowpovperc"
        ]
        if len(group) > 0:
            groups.append(group)
            labels.append(str(category))

    plt.figure(figsize=(8, 6))
    plt.boxplot(groups, tick_labels=labels)
    plt.xlabel("Mental Health Shortage Area")
    plt.ylabel("Family Below Poverty (%)")
    plt.title("County Poverty vs. Mental Health Shortage Area")
    plt.tight_layout()
    plt.show()


def graph_poverty_vs_visits(county_df: pd.DataFrame):
    """
    Scatterplot of family-below-poverty percent vs average visits per station.
    """
    plot_df = county_df[["cfambelowpovperc", "visits_per_station"]].dropna()

    plot_df["cfambelowpovperc"] = pd.to_numeric(plot_df["cfambelowpovperc"], errors="coerce")
    plot_df["visits_per_station"] = pd.to_numeric(plot_df["visits_per_station"], errors="coerce")
    plot_df = plot_df.dropna()

    
    plt.figure(figsize=(8, 6))
    plt.scatter(plot_df["cfambelowpovperc"], plot_df["visits_per_station"])
    plt.xlabel("Family Below Poverty (%)")
    plt.ylabel("Average Visits per Station")
    plt.title("County Poverty vs. Average Visits per Station")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    df = load_merged_data("merged_output.csv")
    county_df = summarize_by_county(df)

    print(county_df.head())
    print("\nCounty-level shape:", county_df.shape)

    graph_poverty_vs_mentalhealth(county_df)
    graph_poverty_vs_visits(county_df)