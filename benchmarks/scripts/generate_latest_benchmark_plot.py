import glob
import pandas as pd
import matplotlib.pyplot as plt
import os

# Get the directory of the current script
directory_of_this_file = os.path.dirname(os.path.abspath(__file__))

# Construct the correct path to the results folder
results_folder = os.path.join(directory_of_this_file, "../results")

# Use glob to find all CSV files in the results folder
csv_files = glob.glob(os.path.join(results_folder, "gates*.csv"))

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

# Calculate averages for plotting
avg_compiled_ratio = df_dates.groupby(["compiler", "date"])["compiled_ratio"].mean().reset_index().sort_values("date")
avg_compile_time = df_dates.groupby(["compiler", "date"])["compile_time"].mean().reset_index().sort_values("date")

# Set global DPI
plt.rcParams['figure.dpi'] = 150  # Adjust DPI as needed

# Create a colormap for unique compilers
unique_compilers = df_dates["compiler"].unique()
colormap = plt.get_cmap("tab10", len(unique_compilers))
color_map = {compiler: colormap(i) for i, compiler in enumerate(unique_compilers)}

# Create subplots
fig, ax = plt.subplots(2, 1, figsize=(8, 8), sharex=True)

# Plot avg_compiled_ratio
for compiler in unique_compilers:
    compiler_data = avg_compiled_ratio[avg_compiled_ratio["compiler"] == compiler]
    ax[0].plot(
        compiler_data["date"],
        compiler_data["compiled_ratio"],
        label=compiler,
        marker="o",
        linestyle="-",
        color=color_map[compiler]
    )
ax[0].set_title("Average Compiled Ratio over Time")
ax[0].set_ylabel("Compiled Ratio")
ax[0].legend(title="Compiler")

# Plot avg_compile_time
for compiler in unique_compilers:
    compiler_data = avg_compile_time[avg_compile_time["compiler"] == compiler]
    ax[1].plot(
        compiler_data["date"],
        compiler_data["compile_time"],
        label=compiler,
        marker="o",
        linestyle="-",
        color=color_map[compiler]
    )
ax[1].set_title("Average Compile Time over Time")
ax[1].set_ylabel("Compile Time")
ax[1].set_xlabel("Date")
ax[1].set_yscale("log")

# Adjust layout and save the figure
plt.tight_layout()
fig.savefig("../compiler_benchmarks_over_time.png")

# Show the plot (optional)
# plt.show()
