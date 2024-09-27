
from qbraid.transpiler import transpile
from qbraid.programs.alias_manager import get_program_type_alias

def write_qasm(circuit, filename, version='2'):
    original_format = get_program_type_alias(circuit)

    # Generate QASM string
    qasm_string = transpile(circuit, 'qasm' + version)
    # Sanity check
    # assert circuit == transpile(qasm_string, original_format)

    # Write the string to a .qasm file
    with open(f"./circuits/qasm{version}/ucc/{filename}.qasm", "w") as file:
        file.write(qasm_string)

