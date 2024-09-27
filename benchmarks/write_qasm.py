
from qbraid.transpiler import transpile as translate
from qbraid.programs.alias_manager import get_program_type_alias
from qiskit import transpile as qiskit_transpile

def write_qasm(circuit, filename, version='2', basis_gates=False):
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
    with open(f"./circuits/qasm{version}/ucc/{filename}.qasm", "w") as file:
        file.write(qasm_string)

