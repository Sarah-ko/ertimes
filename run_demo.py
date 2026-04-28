from pathlib import Path

import pandas as pd

from ertimes.io import download_emergency_data, load_emergency_data

from ertimes.stats_analysis import (
    county_capacity_summary,
    find_capacity_volume_mismatch,
    compute_capacity_pressure_score,
    mental_health_shortage_analysis,
    calculate_growth,
    run_er_analysis,
    county_facility_counts,
    spike_frequency_pivot,
    load_california_income_data,
    get_income_by_zip,
    get_income_by_county,
)

from ertimes.stats_ranking import (
    rank_counties_by_burden,
    rank_hospitals_by_visits_per_station,
)

from ertimes.stats_reports import (
    generate_county_report,
    summarize_by_ownership,
    find_duplicates,
    per_category_burden_report,
)

from ertimes.stats_visualization import (
    plot_hospital_load_distribution,
    plot_facility_trend,
    plot_category_visits,
    plot_category_visits_by_facility,
    plot_urban_rural_map,
)

from ertimes.demographics import (
    get_income_statistics,
    filter_by_income_range,
)


OUTPUT_DIR = Path("demo_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


def print_section(title: str) -> None:
    """Print a clear section header for demo output."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def demo_download_emergency_data() -> pd.DataFrame:
    """Demo downloading and cleaning emergency department data."""
    print_section("1. Download Emergency Department Data")

    print("Downloading California emergency department data...")
    df = download_emergency_data("california")

    print("Download complete.")
    print(f"Shape: {df.shape}")
    print("\nColumns:")
    print(df.columns.tolist())

    print("\nFirst 5 rows:")
    print(df.head())

    return df


def demo_load_emergency_data_from_saved_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Demo saving then loading emergency data locally."""
    print_section("2. Save and Reload Emergency Data Locally")

    csv_path = OUTPUT_DIR / "california_emergency_data_sample.csv"
    df.head(100).to_csv(csv_path, index=False)

    print(f"Saved first 100 rows to: {csv_path}")

    loaded_df = load_emergency_data(csv_path)

    print("Reloaded local CSV successfully.")
    print(f"Reloaded shape: {loaded_df.shape}")
    print(loaded_df.head())

    return loaded_df


def demo_capacity_volume_mismatch(df: pd.DataFrame) -> pd.DataFrame:
    """Demo identifying hospitals with high demand and low capacity."""
    print_section("3. Capacity-Volume Mismatch Analysis")

    result = find_capacity_volume_mismatch(
        df,
        high_visit_quantile=0.65,
        low_capacity_quantile=0.35,
        facility_col="facility_name",
        county_col="county_name",
        year_col="year",
        visits_col="total_ed_visits",
        stations_col="ed_stations",
        bed_col="licensed_bed_size",
    )

    print("Hospitals with high visits per station and relatively low bed capacity:")
    print(result.head(10))
    print(f"\nRows returned: {len(result)}")

    return result


def demo_county_capacity_summary() -> pd.DataFrame:
    """Demo county-level capacity summary."""
    print_section("4. County Capacity Summary")

    summary = county_capacity_summary(
        "california",
        county_col="county_name",
        visits_col="total_ed_visits",
        stations_col="ed_stations",
        bed_col="licensed_bed_size",
    )

    print("County-level capacity summary:")
    print(summary.head(10))
    print(f"\nRows returned: {len(summary)}")

    return summary


def demo_rank_counties(summary: pd.DataFrame) -> pd.DataFrame:
    """Demo ranking counties by emergency department burden."""
    print_section("5. Rank Counties by Burden")

    ranked = rank_counties_by_burden(
        summary,
        visits_col="visits_per_station",
    )

    print("Top 10 counties by visits per station:")
    print(ranked.head(10))

    return ranked


def demo_generate_county_report(summary: pd.DataFrame) -> pd.DataFrame:
    """Demo generating a single-county report."""
    print_section("6. Generate Single County Report")

    if summary.empty:
        print("County summary is empty; skipping county report.")
        return pd.DataFrame()

    county_name = summary.iloc[0]["county_name"]

    report = generate_county_report(
        summary,
        county_name=county_name,
        county_col="county_name",
        visits_col="tot_ed_visits",
        stations_col="ed_stations",
        beds_col="licensed_bed_size",
        visits_per_station_col="visits_per_station",
    )

    print(f"Generated report for county: {county_name}")
    print(report)

    return report


def demo_rank_hospitals(df: pd.DataFrame) -> pd.DataFrame:
    """Demo ranking hospitals by visits per station."""
    print_section("7. Rank Hospitals by Visits per Station")

    ranked = rank_hospitals_by_visits_per_station(
        df,
        agg="median",
        top_n=10,
        facility_col="facility_name",
        visits_col="visits_per_station",
    )

    print("Top 10 hospitals by median visits per station:")
    print(ranked)

    return ranked


def demo_summarize_by_ownership(df: pd.DataFrame) -> pd.DataFrame:
    """Demo summarizing emergency data by hospital ownership type."""
    print_section("8. Summarize by Hospital Ownership")

    summary = summarize_by_ownership(
        df,
        column_map={
            "hospital_ownership": "hospital_ownership",
            "tot_ed_visits": "total_ed_visits",
            "ed_stations": "ed_stations",
            "visits_per_station": "visits_per_station",
        },
    )

    print("Ownership-level summary:")
    print(summary.head(10))

    return summary


def demo_find_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Demo duplicate detection."""
    print_section("9. Find Duplicate Rows")

    duplicate_rows = find_duplicates(
        df,
        subset=["facility_name", "county_name", "year", "category"],
    )

    print("Potential duplicate rows using facility, county, year, and category:")
    print(duplicate_rows.head(10))
    print(f"\nDuplicate rows found: {len(duplicate_rows)}")

    return duplicate_rows


def demo_per_category_burden_report(df: pd.DataFrame) -> dict[str, list[str]]:
    """Demo top burdened facilities by condition category."""
    print_section("10. Per-Category Burden Report")

    report = per_category_burden_report(
        df,
        top_n=3,
        facility_col="facility_name",
        category_col="category",
        visits_col="visits_per_station",
    )

    print("Top 3 facilities by visits per station for each category:")
    for category, facilities in list(report.items())[:10]:
        print(f"{category}: {facilities}")

    return report


def demo_capacity_pressure_score(df: pd.DataFrame) -> pd.DataFrame:
    """Demo composite capacity pressure score."""
    print_section("11. Capacity Pressure Score")

    scores = compute_capacity_pressure_score(
        df,
        facility_col="facility_name",
        visits_col="visits_per_station",
        bed_col="licensed_bed_size",
        primary_shortage_col="primary_care_shortage_area",
        mental_shortage_col="mental_health_shortage_area",
    )

    print("Top 10 facilities by capacity pressure score:")
    print(scores.head(10))

    return scores


def demo_mental_health_shortage_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Demo high-burden facilities in mental health shortage areas."""
    print_section("12. Mental Health Shortage Analysis")

    result = mental_health_shortage_analysis(
        df,
        percentile_threshold=80,
        visits_col="total_ed_visits",
        stations_col="ed_stations",
        shortage_col="mental_health_shortage_area",
        year_col="year",
    )

    print("Facilities in mental health shortage areas with high ED burden:")
    print(result.head(10))
    print(f"\nRows returned: {len(result)}")

    return result


def demo_growth_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Demo year-over-year growth calculations."""
    print_section("13. Year-over-Year Growth Analysis")

    result = calculate_growth(
        df,
        value_col="total_ed_visits",
        group_cols=["facility_name"],
        time_col="year",
        pct=True,
    )

    print("Growth analysis sample:")
    print(result[["facility_name", "year", "total_ed_visits", "growth"]].head(15))

    return result


def demo_run_er_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Demo general ER analysis helper."""
    print_section("14. General ER Analysis")

    result = run_er_analysis(
        df,
        facility_col="facility_name",
        year_col="year",
        visits_col="total_ed_visits",
        visits_per_station_col="visits_per_station",
    )

    print("ER analysis sample:")
    print(result[["facility_name", "year", "YoY_Visits", "Utilization", "Mismatch"]].head(15))

    print("\nMismatch counts:")
    print(result["Mismatch"].value_counts(dropna=False))

    return result


def demo_county_facility_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Demo counting unique facilities by county."""
    print_section("15. County Facility Counts")

    result = county_facility_counts(
        df,
        county_col="county_name",
        facility_col="facility_name",
    )

    print("Top 10 counties by number of unique facilities:")
    print(result.head(10))

    return result


def demo_spike_frequency_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """Demo detecting year-over-year burden spikes by category."""
    print_section("16. Spike Frequency Pivot")

    result = spike_frequency_pivot(
        df,
        threshold_pct=20.0,
        facility_col="facility_name",
        category_col="category",
        year_col="year",
        visits_col="visits_per_station",
    )

    print("Categories with the most year-over-year spikes:")
    print(result.head(10))

    return result


def demo_income_data() -> pd.DataFrame:
    """Demo California income data utilities."""
    print_section("17. California Income Data Utilities")

    income_path = Path("data/california_median_income_by_zipcode.csv")

    if income_path.exists():
        income_df = load_california_income_data(income_path)
        print(f"Loaded income data from: {income_path}")
    else:
        income_df = load_california_income_data()
        print("Income CSV not found. Loaded built-in sample income data.")

    print("\nIncome data sample:")
    print(income_df.head())

    print("\nIncome statistics:")
    print(get_income_statistics(income_df))

    print("\nIncome statistics by county:")
    print(get_income_statistics(income_df, group_by="county"))

    zip_code = str(income_df.iloc[0]["zip_code"])
    print(f"\nLookup for ZIP code {zip_code}:")
    print(get_income_by_zip(income_df, zip_code))

    county = str(income_df.iloc[0]["county"])
    print(f"\nFirst 5 ZIP codes in county: {county}")
    print(get_income_by_county(income_df, county).head())

    print("\nZIP codes with median income between $70,000 and $120,000:")
    print(filter_by_income_range(income_df, 70000, 120000).head(10))

    return income_df


def demo_visualizations(df: pd.DataFrame) -> None:
    """Demo visualization functions and save outputs."""
    print_section("18. Visualization Demos")

    load_plot_path = OUTPUT_DIR / "hospital_load_distribution.png"
    category_plot_path = OUTPUT_DIR / "category_visits_plot.png"
    facility_category_plot_path = OUTPUT_DIR / "facility_category_visits_plot.png"
    trend_plot_path = OUTPUT_DIR / "facility_trend.png"

    print("Generating hospital load distribution plot...")
    fig = plot_hospital_load_distribution(
        df,
        visits_col="total_ed_visits",
        stations_col="ed_stations",
        save_path=str(load_plot_path),
    )
    print(f"Saved: {load_plot_path}")

    print("\nGenerating category visits plot...")
    fig = plot_category_visits(df, save=False)
    fig.savefig(category_plot_path)
    print(f"Saved: {category_plot_path}")

    first_facility = df["facility_name"].dropna().iloc[0]

    print(f"\nGenerating facility trend plot for: {first_facility}")
    fig = plot_facility_trend(
        df,
        first_facility,
        facility_col="facility_name",
        year_col="year",
        visits_col="total_ed_visits",
    )
    fig.savefig(trend_plot_path)
    print(f"Saved: {trend_plot_path}")

    print(f"\nGenerating category visits plot for facility: {first_facility}")
    fig = plot_category_visits_by_facility(df, first_facility, save=False)
    fig.savefig(facility_category_plot_path)
    print(f"Saved: {facility_category_plot_path}")

    print("\nGenerating urban-rural map...")
    map_obj = plot_urban_rural_map(
        "california",
        save=False,
        latitude_col="latitude",
        longitude_col="longitude",
        designation_col="urban_rural_designation",
        facility_col="facility_name",
    )
    map_path = OUTPUT_DIR / "urban_rural_map.html"
    map_obj.save(map_path)
    print(f"Saved: {map_path}")


def main() -> None:
    """Run all demos."""
    print_section("ERTIMES PACKAGE DEMO")

    df = demo_download_emergency_data()

    demo_load_emergency_data_from_saved_csv(df)

    demo_capacity_volume_mismatch(df)

    county_summary = demo_county_capacity_summary()
    demo_rank_counties(county_summary)
    demo_generate_county_report(county_summary)

    demo_rank_hospitals(df)
    demo_summarize_by_ownership(df)
    demo_find_duplicates(df)
    demo_per_category_burden_report(df)
    demo_capacity_pressure_score(df)
    demo_mental_health_shortage_analysis(df)
    demo_growth_analysis(df)
    demo_run_er_analysis(df)
    demo_county_facility_counts(df)
    demo_spike_frequency_pivot(df)
    demo_income_data()
    demo_visualizations(df)

    print_section("DEMO COMPLETE")
    print(f"Check the '{OUTPUT_DIR}/' folder for saved CSVs, plots, and maps.")


if __name__ == "__main__":
    main()