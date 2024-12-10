#!/usr/bin/env python
# coding: utf-8

import glob
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Use glob to find all CSV files in the current directory
csv_files = glob.glob("../results/gates*.csv")

# List to hold DataFrames
dataframes = []

# Loop through each CSV file and read it into a DataFrame
for file in csv_files:
    print(file)
    # Note, this will combine results from the same date
    date_label = str(file).split('_')[1]
    df = pd.read_csv(file)  # Load the CSV file into a DataFrame
    df['date'] = date_label
    df['reduction_factor'] = df['raw_multiq_gates'] / df['compiled_multiq_gates'] 
    df['gate_reduction_per_s'] = df['reduction_factor'] / df['compile_time']
    df['compiled_ratio'] = df['compiled_multiq_gates'] / df['raw_multiq_gates']
    
    
    dataframes.append(df)   # Append the DataFrame to the list

# Concatenate all DataFrames into a single DataFrame
df_dates = pd.concat(dataframes, ignore_index=True)


# Assuming avg_compiled_ratio and avg_compile_time are generated like this:
avg_compiled_ratio = df_dates.groupby(["compiler", "date"])["compiled_ratio"].mean().reset_index().sort_values("date")
avg_compile_time = df_dates.groupby(["compiler", "date"])["compile_time"].mean().reset_index().sort_values("date")


# Set global DPI
plt.rcParams['figure.dpi'] = 150  # Adjust DPI as needed

fig, ax = plt.subplots(2, 1, figsize=(8, 8), sharex=True)

unique_compilers = df_dates["compiler"].unique()
colormap = plt.get_cmap("tab10", len(unique_compilers))
color_map = {compiler: colormap(i) for i, compiler in enumerate(unique_compilers)}

# Plot avg_compiled_ratio
sns.lineplot(
    data=avg_compiled_ratio, 
    x="date", 
    y="compiled_ratio", 
    hue="compiler", 
    style="compiler", 
    markers=True, 
    dashes=False, 
    palette=color_map, 
    ax=ax[0]
)
ax[0].set_title("Average Compiled Ratio over Time")
ax[0].set_ylabel("Compiled Ratio")

# Plot avg_compile_time
sns.lineplot(
    data=avg_compile_time, 
    x="date", 
    y="compile_time", 
    hue="compiler", 
    style="compiler", 
    markers=True, 
    dashes=False, 
    palette=color_map, 
    ax=ax[1]
)
ax[1].set_title("Average Compile Time over Time")
ax[1].set_ylabel("Compile Time")
ax[1].set_xlabel("Date")
ax[1].set_yscale("log")
#plt.tight_layout()
# plt.show()

# Save the plot to a file
fig.savefig("../compiler_benchmarks_over_time.png")
