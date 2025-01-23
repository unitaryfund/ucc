import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Directory containing the CSV files
directory = "../results"

# Initialize a DataFrame to store combined data
data = []

# Process each CSV file
for filename in os.listdir(directory):
    if filename.startswith("expval_") and filename.endswith(".csv"):
        # Extract the date from the filename
        date_str = filename.split("_")[1]  # Assuming the date is the second component
        date = datetime.strptime(date_str, "%Y-%m-%d")

        # Read the CSV file and add the date
        filepath = os.path.join(directory, filename)
        df = pd.read_csv(filepath, comment="#")
        df["date"] = date
        data.append(df)

# Combine all data into a single DataFrame
data = pd.concat(data)

# Filter for the latest date
latest_date = data["date"].max()
data_latest = data[data["date"] == latest_date]

# Create a color map for compilers
unique_compilers = sorted(data_latest["compiler"].unique())
colormap = plt.get_cmap("tab10", len(unique_compilers))
color_map = {compiler: colormap(i) for i, compiler in enumerate(unique_compilers)}

# Plot the data using violin plots
fig = plt.figure(figsize=(12, 8))
sns.violinplot(
    data=data_latest,
    x="compiler",
    y="absoluate_error",
    palette=color_map,
    density_norm="width"
)

# Customize the plot
plt.title(f"Distribution of Absolute Error by Compiler on {latest_date.strftime('%Y-%m-%d')}")
plt.xlabel("Compiler")
plt.ylabel("Average Absolute Error")
plt.grid(True, axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()

# Save the plot
directory_of_this_file = os.path.dirname(os.path.abspath(__file__))
filename = os.path.join(directory_of_this_file, "../latest_expval_benchmark_by_compiler.png")
print(f"\n Saving plot to {filename}")
fig.savefig(filename)
