import glob
import pandas as pd
import matplotlib.pyplot as plt
import os
import re

# Get the directory of the current script
directory_of_this_file = os.path.dirname(os.path.abspath(__file__))

# Construct the correct path to the results folder
results_folder = os.path.join(directory_of_this_file, "../results")

# Use glob to find all CSV files in the results folder
csv_files = glob.glob(os.path.join(results_folder, "gates*.csv"))

dataframes = []

# Extract compiler versions from the header using regex
def extract_compiler_versions(header):
    pattern = r"(\w+)=([\d\.]+)"
    return dict(re.findall(pattern, header))

print("Loading data files...", )
# Loop through each CSV file and read it into a DataFrame
for file in csv_files:
    print(file)
    
    with open(file, 'r') as f:
        # Read the first header line which contains compiler versions
        header_line = f.readline().strip()
        # Extract compiler versions from the header line
        compiler_versions = extract_compiler_versions(header_line)
        print(f"Compiler versions found: {compiler_versions}")
    
    # Note, this will combine results from the same date
    date_label = str(file).split('_')[1].split('.')[0]
    df = pd.read_csv(file, header=1)  # Load the CSV file into a DataFrame
    df['date'] = date_label
    df['reduction_factor'] = df['raw_multiq_gates'] / df['compiled_multiq_gates']
    df['gate_reduction_per_s'] = df['reduction_factor'] / df['compile_time']
    df['compiled_ratio'] = df['compiled_multiq_gates'] / df['raw_multiq_gates']
    
    # Add the extracted compiler versions to the DataFrame (store versions for each compiler)
    for compiler, version in compiler_versions.items():
        df[f'{compiler}_version'] = version  # Store each compiler version as a column
    
    dataframes.append(df)   # Append the DataFrame to the list

# Concatenate all DataFrames into a single DataFrame
df_dates = pd.concat(dataframes, ignore_index=True)

# Calculate averages for plotting
avg_compiled_ratio = df_dates.groupby(["compiler", "date"])["compiled_ratio"].mean().reset_index().sort_values("date")
avg_compile_time = df_dates.groupby(["compiler", "date"])["compile_time"].mean().reset_index().sort_values("date")

# Set global DPI
plt.rcParams['figure.dpi'] = 150  # Adjust DPI as needed

# Create a colormap for unique compilers
unique_compilers = sorted(df_dates["compiler"].unique())
colormap = plt.get_cmap("tab10", len(unique_compilers))
color_map = {compiler: colormap(i) for i, compiler in enumerate(unique_compilers)}

# Create subplots
fig, ax = plt.subplots(2, 1, figsize=(8, 8), sharex=True)

# Initialize a dictionary to store the last version seen for each compiler
last_version_seen = {compiler: None for compiler in unique_compilers}

# Plot avg_compiled_ratio for each compiler
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

    # Annotate version changes for each compiler
    for index, row in compiler_data.iterrows():
        # Get the version for this date and compiler from the original df_dates DataFrame
        current_version = df_dates[(df_dates["compiler"] == compiler) & (df_dates["date"] == row["date"])][f'{compiler}_version'].values[0]
        
        if current_version != last_version_seen[compiler]:
            # Alternating the vertical position to prevent overlap
            vertical_position = 'top' if index % 2 == 0 else 'bottom'
            
            # Annotate with an arrow pointing to the data point
            ax[0].annotate(
                f"{compiler}={current_version}",  # Annotate with the version
                (row["date"], row["compiled_ratio"]),
                textcoords="offset points",
                xytext=(0, 30 if vertical_position == 'top' else -30),  # Adjusting the offset vertically
                ha='center',
                fontsize=8,
                color=color_map[compiler],
                verticalalignment=vertical_position,
                arrowprops=dict(facecolor=color_map[compiler], shrink=0.05),
                bbox=dict(boxstyle="round,pad=0.3", edgecolor=color_map[compiler], facecolor="white", alpha=0.7)  # Add semi-transparent box
            )
            # Update the last version seen for this compiler
            last_version_seen[compiler] = current_version

ax[0].set_title("Average Compiled Ratio over Time")
ax[0].set_ylabel("Compiled Ratio")
ax[0].legend(title="Compiler")

# Plot avg_compile_time for each compiler
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

    # Annotate version changes for each compiler
    for index, row in compiler_data.iterrows():
        # Get the version for this date and compiler from the original df_dates DataFrame
        current_version = df_dates[(df_dates["compiler"] == compiler) & (df_dates["date"] == row["date"])][f'{compiler}_version'].values[0]
        
        if current_version != last_version_seen[compiler]:
            # Alternating the vertical position to prevent overlap
            vertical_position = 'top' if index % 2 == 0 else 'bottom'
            
            # Annotate with an arrow pointing to the data point
            ax[1].annotate(
                f"{compiler}={current_version}",  # Annotate with the version
                (row["date"], row["compile_time"]),
                textcoords="offset points",
                xytext=(0, 10 if vertical_position == 'top' else -10),  # Adjusting the offset vertically
                ha='center',
                fontsize=8,
                color=color_map[compiler],
                verticalalignment=vertical_position,
                arrowprops=dict(facecolor=color_map[compiler], shrink=0.05),
                bbox=dict(boxstyle="round,pad=0.3", edgecolor=color_map[compiler], facecolor="white", alpha=0.7)  # Add semi-transparent box
            )
            # Update the last version seen for this compiler
            last_version_seen[compiler] = current_version

ax[1].set_title("Average Compile Time over Time")
ax[1].set_ylabel("Compile Time")
ax[1].set_xlabel("Date")
ax[1].set_yscale("log")

plt.xticks(rotation=45)

# Adjust layout and save the figure
plt.tight_layout()
filename = os.path.join(directory_of_this_file, "../avg_compiler_benchmarks_over_time_with_versions_and_arrows.png")
print(f"\n Saving plot to {filename}")
fig.savefig(filename)

# Show the plot (optional)
# plt.show()
# Function to check for overlapping annotations
def check_overlap(annotation, annotations):
    for ann in annotations:
        if annotation.xy[0] == ann.xy[0] and abs(annotation.xy[1] - ann.xy[1]) < 0.05:
            return True
    return False

# Adjust annotation positions to avoid overlap
def adjust_annotations(ax):
    annotations = []
    for annotation in ax.texts:
        max_iterations = 100
        iterations = 0
        while check_overlap(annotation, annotations) and iterations < max_iterations:
            iterations += 1
            x, y = annotation.xy
            y += 0.05  # Adjust the y position to avoid overlap
            annotation.set_position((x, y))
        annotations.append(annotation)

# Adjust annotations for both subplots
adjust_annotations(ax[0])
adjust_annotations(ax[1])