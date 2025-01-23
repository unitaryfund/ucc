import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

# Step 1: Get the directory of the current script
directory_of_this_file = os.path.dirname(os.path.abspath(__file__))

# Step 2: Construct the correct path to the results folder
results_folder = os.path.join(directory_of_this_file, "../results")

# Step 3: Use glob to find all CSV files in the results folder
csv_files = glob.glob(os.path.join(results_folder, "expval_*.csv"))

# Step 4: Iterate through all CSV files and load them into dataframes with date column
dfs = []  # List to store dataframes
for file in csv_files:
    # Extract the date from the filename (assuming the date is after 'expval_' and before '.csv')
    date_label = str(file).split('_')[1].split('.')[0]

    # Load the CSV file into a DataFrame
    df = pd.read_csv(file, comment="#")

    # Add the extracted date as a new column in the dataframe
    df['date'] = date_label

    # Append the dataframe to the list
    dfs.append(df)

# Step 5: Concatenate all dataframes into one large dataframe
df_all = pd.concat(dfs, ignore_index=True)

# Find the most recent date in the 'date' column
latest_date = df_all['date'].max()
print("latest date is", latest_date)

# Filter the dataframe to only include rows from the most recent date
df_latest = df_all[df_all['date'] == latest_date]

# Step 6: Define the bar width and create x-axis positions for the circuits
bar_width = 0.2
circuit_names = df_latest['circuit_name'].unique()
x_positions = range(len(circuit_names))  # X positions for each circuit

# Create a dictionary to map circuit names to indices
circuit_name_to_index = {name: i for i, name in enumerate(circuit_names)}

# Step 7: Set up the figure and axes
fig, ax = plt.subplots(figsize=(10, 6))

# Set color map for different compilers
# Get unique compilers and sort them alphabetically
unique_compilers = sorted(df_latest['compiler'].unique())

# Set color map for different compilers
colormap = plt.get_cmap("tab10", len(unique_compilers))
color_map = {compiler: colormap(i) for i, compiler in enumerate(unique_compilers)}

# Step 8: Plot absolute error for each compiler
for i, (key, grp) in enumerate(df_latest.groupby("compiler")):
    # Get indices for each circuit in the current compiler group
    grp_indices = grp['circuit_name'].map(circuit_name_to_index)

    # Plot absolute error
    ax.bar(
        [grp_indices + i * bar_width for grp_indices in grp_indices],  # Shift bars for each compiler
        grp['absoluate_error'],  # Absolute error data
        width=bar_width,
        label=key,
        color=color_map[key]
    )

# Step 9: Customize plots
ax.set_title(f"Absolute Error by Compiler on Circuits (Date: {latest_date})")
ax.set_xlabel("Circuit Name")
ax.set_ylabel("Absolute Error")
ax.set_xticks(x_positions)
ax.set_xticklabels(circuit_names, rotation=75)
ax.set_yscale("log")

# Step 10: Add legend
ax.legend(title="Compiler")

# Adjust layout and save the figure
plt.tight_layout()
filename = os.path.join(directory_of_this_file, "../latest_absolute_errors_by_circuit.png")
print(f"\n Saving plot to {filename}")
fig.savefig(filename)
