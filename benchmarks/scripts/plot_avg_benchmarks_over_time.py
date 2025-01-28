from common import annotate_and_adjust, adjust_axes_to_fit_labels

import glob
import pandas as pd
import matplotlib.pyplot as plt
import os
import re


### Load data
# Get the directory of the current script
directory_of_this_file = os.path.dirname(os.path.abspath(__file__))
results_folder = os.path.join(directory_of_this_file, "../results")
csv_files = glob.glob(os.path.join(results_folder, "gates*.csv"))

dataframes = []

def extract_compiler_versions(header):
    pattern = r"(\w+)=([\d\.]+)"
    return dict(re.findall(pattern, header))

print("Loading data files...")
for file in csv_files:
    with open(file, 'r') as f:
        header_line = f.readline().strip()
        compiler_versions = extract_compiler_versions(header_line)
    date_label = str(file).split('_')[1].split('.')[0]
    df = pd.read_csv(file, header=1)
    df['date'] = date_label
    df['compiled_ratio'] = df['compiled_multiq_gates'] / df['raw_multiq_gates']
    df['compiler_version'] = df['compiler'].map(compiler_versions)
 
    dataframes.append(df)

df_dates = pd.concat(dataframes, ignore_index=True)

# Find the average compiled ratio for each compiler on each date
avg_compiled_ratio = df_dates.groupby(["compiler", "date", "compiler_version"])["compiled_ratio"].mean().reset_index().sort_values("date")

# Find the average compile time for each compiler on each date
avg_compile_time = df_dates.groupby(["compiler", "date", "compiler_version"])["compile_time"].mean().reset_index().sort_values("date")


###### Plotting
# Ensure colors are consistently assigned to each compiler
unique_compilers = sorted(df_dates["compiler"].unique())
colormap = plt.get_cmap("tab10", len(unique_compilers))
color_map = {compiler: colormap(i) for i, compiler in enumerate(unique_compilers)}

fig, ax = plt.subplots(2, 1, figsize=(8, 8), sharex=False, dpi=150)
# Rotate x labels on axes 0
plt.setp(ax[0].xaxis.get_majorticklabels(), rotation=45)


#### Plot Compiled ratio
print("Plotting compiled ratio...")
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

# Keep track of last compiler version seen over time to track version changes
last_version_seen = {compiler: None for compiler in unique_compilers}

previous_bboxes = []
# Now iterate over each compiler entry and annotate if it's a new version, if so label it
for date in avg_compiled_ratio["date"].unique():
    date_data = avg_compiled_ratio[avg_compiled_ratio["date"] == date]
    # Sort date_data in order of compiled_ratio
    date_data = date_data.sort_values("compiled_ratio")
    # print('Date data for \n', date, date_data, '\n')
    # Now iterate over each compiler entry and annotate if it's a new version
    for _, row in date_data.iterrows():
        # Get the version for this date 
        current_version = row["compiler_version"]
        compiler = row["compiler"]
        compiled_ratio = row["compiled_ratio"]
        
        # Check if the version has changed
        if current_version != last_version_seen[compiler]:
            text = f"{compiler}={current_version}"
            xy = (row["date"], compiled_ratio)
            color = color_map[compiler]

            # Add the annotation and adjust for overlap
            annotate_and_adjust(
                ax=ax[0],
                text=text,
                xy=xy,
                color=color,
                previous_bboxes=previous_bboxes,
                offset=(0, 15),  # Initial offset
                increment=2,  # Vertical adjustment step
                max_attempts=20,
                rotation=30
            )
            plt.pause(0.1)
            # Update the last seen version for this compiler
            last_version_seen[compiler] = current_version
               
adjust_axes_to_fit_labels(ax[0], x_scale=1.01, y_scale=1.075)
# Set y axis range to be slightly larger than data range

ax[0].set_title("Average Compiled Ratio over Time")
ax[0].set_ylabel("Compiled Ratio")
# ax[0].set_ylim(0.745, 0.96)
# Expand axes to be slightly larger than data range
ax[0].legend(title="Compiler")


#### Plot Compile time
# Get runtime data only after we created GitHub Actions pipeline for standardization
avg_compile_time = avg_compile_time[avg_compile_time["date"] >= "2024-12-16"]

previous_annotations = []
last_version_seen = {compiler: None for compiler in unique_compilers}

print("Plotting compile time...")
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

# Add annotations for version changes
for date in avg_compile_time["date"].unique():
    date_data = avg_compile_time[avg_compile_time["date"] == date]
    # Sort date_data in order of compiled_ratio
    date_data = date_data.sort_values("compile_time")
    for _, row in date_data.iterrows():
        # print(row, '\n')
        # Get the version for this date 
        current_version = row["compiler_version"]
        compiler = row["compiler"]
        compile_time = row["compile_time"]
        
        # Check if the version has changed
        if current_version != last_version_seen[compiler]:
            text = f"{compiler}={current_version}"
            xy = (row["date"], compile_time)
            color = color_map[compiler]

            # Add the annotation and adjust for overlap
            annotate_and_adjust(
                ax=ax[1],
                text=text,
                xy=xy,
                color=color,
                previous_bboxes=previous_bboxes,
                offset=(0, 15),  # Initial offset
                increment=2,  # Vertical adjustment step
                max_attempts=10,
                rotation=15
            )
            # plt.pause(0.1)
            # Update the last seen version for this compiler
            last_version_seen[compiler] = current_version

ax[1].set_title("Average Compile Time over Time")
ax[1].set_ylabel("Compile Time (s)")
ax[1].set_xlabel("Date")
ax[1].set_yscale("log")
ax[1].legend(title="Compiler")
adjust_axes_to_fit_labels(ax[1], x_scale=1.01, y_scale=1.75, y_log=True)

plt.xticks(rotation=45)
plt.tight_layout()
filename = os.path.join(directory_of_this_file, "../avg_compiler_benchmarks_over_time.png")
print(f"\nSaving plot to {filename}")
fig.savefig(filename)
