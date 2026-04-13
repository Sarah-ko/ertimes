#as a function
import pandas as pd
import matplotlib.pyplot as plt

def plot_category_visits(df):
    """
    Plots total category-specific ED visits (EDDXCount) as a horizontal bar chart.
    Excludes the 'All ED Visits' category.
    """

    # Drop missing category-specific counts
    df = df.dropna(subset=["EDDXCount"])

    # Exclude the total aggregate category
    df = df[df["Category"] != "All ED Visits"]

    # Group by category and sum
    visits_summary = (
        df.groupby("Category")["EDDXCount"]
          .sum()
          .reset_index()
          .sort_values(by="EDDXCount", ascending=False)
    )

    print(visits_summary)

    # Plot
    plt.figure(figsize=(12, 8))
    plt.barh(visits_summary["Category"], visits_summary["EDDXCount"])

    # Largest to smallest
    plt.gca().invert_yaxis()

    # No scientific notation 
    plt.ticklabel_format(style='plain', axis='x')

    # Labels and title
    plt.xlabel("Total ED Visits (Category-Specific)")
    plt.ylabel("Health Condition Category")
    plt.title("Total ED Visits by Condition Category (Excluding 'All ED Visits')")

    plt.tight_layout()
    plt.show()

#load and call the function for this file specifically
if __name__ == "__main__": #this part is new
    ed = pd.read_excel("data/emergency-department-volume-and-capacity-2021-2023.xlsx")
    plot_category_visits(ed)

