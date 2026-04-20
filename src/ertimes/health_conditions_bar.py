#as a function
import pandas as pd
import matplotlib.pyplot as plt

def plot_category_visits(df, save: bool = False):
    """
    Plots total category-specific ED visits (ed_burden) as a horizontal bar chart.
    Excludes the 'All ED Visits' category.
    """

    # Drop missing category-specific counts
    df = df.dropna(subset=["ed_burden"])

    # Exclude the total aggregate category
    df = df[df["category"] != "All ED Visits"]

    # Group by category and sum
    visits_summary = (
        df.groupby("category")["ed_burden"]
          .sum()
          .reset_index()
          .sort_values(by="ed_burden", ascending=False)
    )

    print(visits_summary)

    # Plot
    plt.figure(figsize=(12, 8))
    plt.barh(visits_summary["category"], visits_summary["ed_burden"])

    # Largest to smallest
    plt.gca().invert_yaxis()

    # No scientific notation 
    plt.ticklabel_format(style='plain', axis='x')

    # Labels and title
    plt.xlabel("Total ED Visits (Category-Specific)")
    plt.ylabel("Health Condition Category")
    plt.title("Total ED Visits by Condition Category (Excluding 'All ED Visits')")

    plt.tight_layout()
    
    if save:
        from pathlib import Path
        output_dir = Path("data")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "category_visits_plot.png"
        plt.savefig(output_path)
        plt.close()
        print(f"\nSuccess: Category visits plot saved to {output_path}")
    else:
        plt.close()

#load and call the function for this file specifically
if __name__ == "__main__": #this part is new
    ed = pd.read_excel("data/emergency-department-volume-and-capacity-2021-2023.xlsx")
    plot_category_visits(ed)

