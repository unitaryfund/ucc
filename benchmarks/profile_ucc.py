import cProfile
from graphviz import Source
import os
import subprocess

from qbraid.transpiler import transpile as translate
from ucc import compile as ucc_compile

# Step 1: Define the circuit 
qasm_file = "./circuits/qasm2/ucc/qcnn_N100_7layers.qasm"

with open(qasm_file, "r") as file:
    qasm_string = file.read()
circuit = translate(qasm_string, 'qiskit')

# Step 2: Profile the function using cProfile
profiler = cProfile.Profile()
profiler.enable()
ucc_compile(circuit)
profiler.disable()

# Step 3: Save the profiling data in the current directory
current_dir = os.getcwd()  # Get the current working directory
temp_stats_file = os.path.join(current_dir, "profile_data.pstats")
profiler.dump_stats(temp_stats_file)

# Step 4: Convert the profiling data to a dot format using gprof2dot
dot_file_name = os.path.join(current_dir, "profile_graph.dot")  # Save as a DOT file in the current directory
subprocess.run(['gprof2dot', '-f', 'pstats', temp_stats_file, '-o', dot_file_name])

# Step 5: Render and save the graph using Graphviz in PDF format
output_pdf = os.path.join(current_dir, "profile_graph.pdf")  # Save the graph as PDF in current directory
s = Source.from_file(dot_file_name, format="pdf")  # Generate a high-res PDF
s.render(filename=output_pdf, view=True)

# Display a message confirming the file has been saved in the current directory
print(f"Graph saved as PDF: {output_pdf}")
