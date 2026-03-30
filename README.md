# ertimes
**ertimes (Emergency Response Times)** is a Python package designed to simplify the analysis of emergency department (ER) volume and capacity datasets. It provides tools for data cleaning, summarization, and visualization to help researchers and analysts better understand patterns in emergency healthcare demand.

---

# 🚀 Quick Start (How to Run)

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

# 📦 Installation

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

# 🌎 Dataset

This package was originally built using a dataset from **data.gov** containing:

> Emergency Department Volume and Capacity data from the state of California

The goal is to **generalize this package to support datasets from other states and regions**.

---

# 🏗️ Project Structure

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

Run tests using:

```bash
pytest
```

---