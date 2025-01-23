from qbraid.transpiler import transpile
from qiskit import transpile as qiskit_transpile
import os

def write_qasm(circuit, circuit_name, version='2', basis_gates=[], folder="../qasm_circuits"):
    qiskit_circuit = transpile(circuit, 'qiskit')
    if basis_gates:
        decomp_circuit = qiskit_transpile(
            qiskit_circuit, 
            basis_gates=basis_gates, 
            optimization_level=0)
    else:
        decomp_circuit = qiskit_circuit

    # Generate QASM string
    qasm_string = transpile(decomp_circuit, 'qasm' + version)

    # Get the absolute path of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create the absolute path for the folder where QASM files will be saved
    abs_folder = os.path.abspath(os.path.join(script_dir, folder))
    
    # Construct the filename with the given circuit name and version
    filename = os.path.join(abs_folder, f"qasm{version}/ucc/{circuit_name}")
    
    # Append basis gates to the filename if they are provided
    if basis_gates:
        filename += f"_basis_{'_'.join(basis_gates)}"
        
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename + ".qasm", "w") as file:
        file.write(qasm_string)
