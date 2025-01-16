from adjustText import adjust_text
import glob
import pandas as pd
import matplotlib.pyplot as plt
import os
import re

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
    print(file)
    with open(file, 'r') as f:
        header_line = f.readline().strip()
        compiler_versions = extract_compiler_versions(header_line)
    date_label = str(file).split('_')[1].split('.')[0]
    df = pd.read_csv(file, header=1)
    df['date'] = date_label
    df['reduction_factor'] = df['raw_multiq_gates'] / df['compiled_multiq_gates']
    df['gate_reduction_per_s'] = df['reduction_factor'] / df['compile_time']
    df['compiled_ratio'] = df['compiled_multiq_gates'] / df['raw_multiq_gates']
    for compiler, version in compiler_versions.items():
        df[f'{compiler}_version'] = version
    dataframes.append(df)

df_dates = pd.concat(dataframes, ignore_index=True)
avg_compiled_ratio = df_dates.groupby(["compiler", "date"])["compiled_ratio"].mean().reset_index().sort_values("date")
avg_compile_time = df_dates.groupby(["compiler", "date"])["compile_time"].mean().reset_index().sort_values("date")

plt.rcParams['figure.dpi'] = 150
unique_compilers = sorted(df_dates["compiler"].unique())
colormap = plt.get_cmap("tab10", len(unique_compilers))
color_map = {compiler: colormap(i) for i, compiler in enumerate(unique_compilers)}

fig, ax = plt.subplots(2, 1, figsize=(8, 8), sharex=False)
# Rotate x labels on axes 0
plt.setp(ax[0].xaxis.get_majorticklabels(), rotation=45)

last_version_seen = {compiler: None for compiler in unique_compilers}
all_texts = []

from adjustText import adjust_text

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

    # Store annotations for adjust_text
    annotations = []
    for index, row in compiler_data.iterrows():
        # Get the version for this date and compiler from the original DataFrame
        current_version = df_dates[(df_dates["compiler"] == compiler) & (df_dates["date"] == row["date"])][f'{compiler}_version'].values[0]
        
        if current_version != last_version_seen[compiler]:
            annotation = ax[0].annotate(
                f"{compiler}={current_version}",
                (row["date"], row["compiled_ratio"]),
                textcoords="offset points",
                xytext=(10, 15),  # Default offset
                ha='center',
                fontsize=8,
                color=color_map[compiler],
                arrowprops=dict(
                    arrowstyle="->",
                    color=color_map[compiler],
                    lw=0.5,
                    shrinkA=5,  # Shrink arrow length to avoid overlap
                    shrinkB=5
                ),
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    edgecolor=color_map[compiler],
                    facecolor="white",
                    alpha=0.8
                )
            )
            annotations.append(annotation)
            last_version_seen[compiler] = current_version
    
    # # Adjust the text to avoid overlap
    # adjust_text(
    #     annotations,
    #     ax=ax[0],
    #     only_move={'points': 'y', 'texts': 'y'},  # Constrain movement to vertical axis
    #     autoalign='y',
    #     force_text=0.5,
    #     force_points=0.1
    # )

ax[0].set_title("Average Compiled Ratio over Time")
ax[0].set_ylabel("Compiled Ratio")
ax[0].legend(title="Compiler")
# Expand axes to be slightly larger than data range
ax[0].set_ylim(0.74, 0.96)

# Plot only compiler runtime data after we created GitHub Actions pipeline for standardization
avg_compile_time = avg_compile_time[avg_compile_time["date"] >= "2024-12-16"]

# Repeat for avg_compile_time
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
    print('Compiler: ', compiler)
    # Store annotations for adjust_text
    annotations = []
    for index, row in compiler_data.iterrows():
        # Get the version for this date and compiler
        current_version = df_dates[(df_dates["compiler"] == compiler) & (df_dates["date"] == row["date"])][f'{compiler}_version'].values[0]
        print('Current version: ', current_version)
        if current_version != last_version_seen[compiler]:
            print('New version: ', current_version)
            # Create annotation with textcoords="data" for better alignment
            annotation = ax[1].annotate(
                f"{compiler}={current_version}",
                (row["date"], row["compile_time"]),  # Attach to the exact data point
                textcoords="offset points",
                xytext=(10, 15),  # Default offset
                ha='center',
                fontsize=8,
                color=color_map[compiler],
                arrowprops=dict(
                    arrowstyle="->",
                    color=color_map[compiler],
                    lw=0.5,
                    shrinkA=5,  # Shrink arrow length to avoid overlap
                    shrinkB=5
                ),
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    edgecolor=color_map[compiler],
                    facecolor="white",
                    alpha=0.8
                )
            )
            annotations.append(annotation)
            last_version_seen[compiler] = current_version

    # # # Adjust the text to avoid overlap
    # adjust_text(
    #     annotations,
    #     ax=ax[1],
    #     only_move={'points': 'y', 'texts': 'y'},  # Restrict movement to vertical axis
    #     autoalign='y',  # Prefer vertical alignment
    #     force_text=0.001,  # Increase text repulsion
    #     force_points=0.01,  # Increase repulsion from points
    #     expand_text=(1.2, 1.4),  # Slightly expand spacing for clarity,
    #     expand_points=(1.01, 1.01),  # Limit how far annotations move from data points
    #     lim=100  # Limit iterations to avoid excessive adjustment time
    # )

ax[1].set_title("Average Compile Time over Time")
ax[1].set_ylabel("Compile Time")
ax[1].set_xlabel("Date")
ax[1].set_yscale("log")
ax[1].legend(title="Compiler")

plt.xticks(rotation=45)
plt.tight_layout()
filename = os.path.join(directory_of_this_file, "../avg_compiler_benchmarks_over_time_with_versions_and_arrows.png")
print(f"\nSaving plot to {filename}")
fig.savefig(filename)
