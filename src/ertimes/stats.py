"""
Compatibility module that re-exports functions from the new stats submodules.

This module provides a unified namespace for backward compatibility.
Functions are distributed across:
- stats_ranking: ranking functions
- stats_analysis: analysis and scoring functions
- stats_visualization: plotting and mapping functions
- stats_reports: report generation functions
"""

# Import all ranking functions
from .stats_ranking import (
    rank_counties_by_burden,
    rank_hospitals_by_visits_per_station,
)

# Import all analysis functions
from .stats_analysis import (
    _resolve_columns,
    county_capacity_summary,
    _bed_size_to_numeric,
    find_capacity_volume_mismatch,
    compute_capacity_pressure_score,
    mental_health_shortage_analysis,
    clean_growth,
    calculate_growth,
    spike_frequency_pivot,
    county_facility_counts,
)

# Import all visualization functions
from .stats_visualization import (
    plot_facility_trend,
    plot_urban_rural_map,
    plot_category_visits,
    create_ed_map,
)

# Import all reporting functions
from .stats_reports import (
    generate_county_report,
    per_category_burden_report,
    summarize_by_ownership,
    find_duplicates,
)

# Import io functions for convenience
from .io import download_emergency_data

__all__ = [
    # ranking
    "rank_counties_by_burden",
    "rank_hospitals_by_visits_per_station",
    # analysis
    "_resolve_columns",
    "county_capacity_summary",
    "_bed_size_to_numeric",
    "find_capacity_volume_mismatch",
    "compute_capacity_pressure_score",
    "mental_health_shortage_analysis",
    "clean_growth",
    "calculate_growth",
    "spike_frequency_pivot",
    "county_facility_counts",
    # visualization
    "plot_facility_trend",
    "plot_urban_rural_map",
    "plot_category_visits",
    "create_ed_map",
    # reporting
    "generate_county_report",
    "per_category_burden_report",
    "summarize_by_ownership",
    "find_duplicates",
    # io
    "download_emergency_data",
]
