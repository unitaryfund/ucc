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

# Convert the 'date' column to datetime
df_all['date'] = pd.to_datetime(df_all['date'])

# Step 6: Group by date and compiler, and calculate the average absolute error
summary = df_all.groupby(['date', 'compiler']).agg(
    avg_absolute_error=('absoluate_error', 'mean')
).reset_index()

# Step 7: Set up the figure
fig, ax = plt.subplots(figsize=(12, 6))

# Set color map for different compilers
unique_compilers = sorted(summary['compiler'].unique())
colormap = plt.get_cmap("tab10", len(unique_compilers))
color_map = {compiler: colormap(i) for i, compiler in enumerate(unique_compilers)}

# Step 8: Plot average absolute error over time
for compiler in unique_compilers:
    compiler_data = summary[summary['compiler'] == compiler]
    
    ax.plot(
        compiler_data['date'], 
        compiler_data['avg_absolute_error'], 
        label=compiler, 
        color=color_map[compiler], 
        marker='o'
    )

# Step 9: Customize plot
ax.set_title("Average Absolute Error Over Time")
ax.set_xlabel("Date")
ax.set_ylabel("Average Absolute Error")
ax.grid(True)
ax.legend(title="Compiler")

# Adjust layout and save the figure
plt.tight_layout()
filename = os.path.join(directory_of_this_file, "../average_absolute_error_over_time.png")
print(f"\n Saving plot to {filename}")
fig.savefig(filename)
