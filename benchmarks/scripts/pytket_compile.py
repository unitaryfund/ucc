# pytket_compile.py

from common import qasm_files, log_performance
from pytket.circuit import OpType
from pytket.predicates import CompilationUnit
from pytket.passes import SequencePass, DecomposeBoxes, auto_rebase_pass, SimplifyInitial, RemoveRedundancies
from pytket.transform import Transform
from qbraid.transpiler import transpile as translate

def pytket_compile(pytket_circuit):
    compilation_unit = CompilationUnit(pytket_circuit)
    seqpass = SequencePass([
        SimplifyInitial(),
        DecomposeBoxes(),
        RemoveRedundancies(),
        auto_rebase_pass({OpType.Rx, OpType.Ry, OpType.Rz, OpType.CX, OpType.H})
    ])
    seqpass.apply(compilation_unit)
    return compilation_unit.circuit

results_log = []

for filename in qasm_files:
    with open(filename, "r") as file:
        print(f"Compiling {filename} with PyTKET")
        qasm_string = file.read()
        native_circuit = translate(qasm_string, 'pytket')
        log_entry = log_performance(pytket_compile, native_circuit, "pytket")
        log_entry['circuit_name'] = filename.split('/')[-1].split('_N')[0]
        results_log.append(log_entry)

# Save results
import pandas as pd
from datetime import datetime
df = pd.DataFrame(results_log)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
df.to_csv(f"pytket_results_{timestamp}.csv", index=False)
