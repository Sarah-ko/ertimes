# ertimes
**ertimes (Emergency Response Times)** is a Python package designed to simplify the analysis of emergency department (ER) volume and capacity datasets. It provides tools for data cleaning, summarization, and visualization to help researchers and analysts better understand patterns in emergency healthcare demand.

# About
`ertimes` (Emergency Response Times) is a Python package we built to make it easier to work with and analyze emergency department (ED) volume and capacity data.

Emergency healthcare datasets are often messy and inconsistent, which makes it hard to compare hospitals or understand broader system trends. This package helps turn that raw data into a cleaner, more usable format so it’s easier to explore questions about **demand, capacity, and hospital burden**.

In particular, `ertimes` is designed to help answer questions like:

* Which counties or hospitals are experiencing the highest ER demand?
* Where is patient volume exceeding available capacity?
* How do utilization patterns vary across facilities and over time?
* Which areas might be under-resourced relative to demand?

To support this, the package includes a full workflow for:

* **Data cleaning and standardization**, so county and facility names are consistent
* **Aggregation tools** for summarizing data at the hospital and county level
* **Capacity analysis**, including metrics like visits per station and mismatch scoring
* **Ranking functions** to identify high-burden facilities and regions
* **Visualization tools** to help explore trends and distributions more clearly

The main goal is to make it easier to go from raw emergency department data to meaningful insights without needing a lot of manual preprocessing or repeated analysis code.

This project was originally developed using California emergency department data from data.gov, but it is structured so it can be extended to other states or similar datasets with minimal changes.

Overall, `ertimes` is meant to be a practical toolkit for exploring real-world healthcare capacity issues in a more organized and reproducible way.


---

# Quick Start (How to Run)

The easiest way to use this package is through the demo script:

```bash
python run_demo.py
```

This script demonstrates the core functionality of the package, including:
- Loading and preprocessing the dataset
- Performing analysis on ER visits and capacity
- Generating summary outputs and/or visualizations

### Requirements
Make sure you have Python installed (recommended: Python 3.10+), then install dependencies:

```bash
pip install -e ".[dev]"
```

If you encounter version issues, ensure your Python version matches the requirement specified in `pyproject.toml`.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/Sarah-ko/ertimes.git
cd ertimes
```

Install the package in editable mode:

```bash
pip install -e .
```

(Optional for development)
```bash
pip install -e ".[dev]"
```

---

# What This Package Does

`ertimes` is built to work with datasets that describe **emergency department utilization**, including:

- ER visit volume
- Capacity constraints
- Hospital-level trends over time

The package provides functionality for:

### Data Cleaning
- Handling missing values  
- Standardizing formats  
- Preparing datasets for analysis  

### Analysis
- Comparing ER visits vs capacity  
- Identifying utilization patterns  
- Detecting mismatches between demand and resources  

### Visualization
- Time series trends  
- Capacity vs volume comparisons  
- Summary charts for hospital performance  

---

# Dataset

This package was originally built using a dataset from **data.gov** containing:

> Emergency Department Volume and Capacity data from the state of California

The goal is to **generalize this package to support datasets from other states and regions**.

---

# Project Structure

```
ertimes/
├── ertimes/           # Core package code
├── tests/             # Unit tests
├── run_demo.py        # Demo script (main entry point)
├── pyproject.toml     # Package configuration
└── README.md
```

---

# Testing

![Coverage](coverage-badge.svg)

Run tests with coverage using:

```bash
python -m pytest tests/ -v --cov=ertimes --cov-report=term-missing --cov-report=xml
```

Run tests without coverage using:

```bash
python -m pytest tests/ -v
```

---
