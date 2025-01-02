
from qbraid.transpiler import transpile as translate
from qiskit import transpile as qiskit_transpile
from os.path import join 


def write_qasm(circuit, circuit_name, version='2', basis_gates=[], folder="../qasm_circuits"):
    qiskit_circuit = translate(circuit, 'qiskit')
    if basis_gates:
        decomp_circuit = qiskit_transpile(
            qiskit_circuit, 
            basis_gates=basis_gates, 
            optimization_level=0)
    else:
        decomp_circuit = qiskit_circuit

    # Generate QASM string
    qasm_string = translate(decomp_circuit, 'qasm' + version)

    # Write the string to a .qasm file

    filename = join(folder, f"/qasm{version}/ucc/{circuit_name}")
    if basis_gates:
        filename += f"_basis_{'_'.join(basis_gates)}"
        
    with open(filename + ".qasm", "w") as file:
        file.write(qasm_string)

