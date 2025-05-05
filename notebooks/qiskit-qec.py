from qiskit import (
    QuantumCircuit,
    QuantumRegister,
    ClassicalRegister,
)
import ucc
from qbraid import transpile as translate
import pyqasm

# This is a simple example of a quantum error correction circuit implementing a 3 qubit repetition code using Qiskit. The circuit encodes a single qubit into three qubits, measures the syndrome, and applies corrections if necessary.
# Adapted from https://learning.quantum.ibm.com/tutorial/build-repetition-codes
# License Apache-2.0

num_qubits = 5
# Create quantum and classical registers
# We will use 3 qubits to encode the data and 2 ancilla qubits to measure the syndrome
# TODO: generalize this register initialization to any number of qubits
qreg_data = QuantumRegister(3)
qreg_measure = QuantumRegister(2)
creg_data = ClassicalRegister(3, name="data")
creg_syndrome = ClassicalRegister(2, name="syndrome")
state_data = qreg_data[0]
ancillas_data = qreg_data[1:]


def build_qc():
    """Build a typical error correction circuit"""
    return QuantumCircuit(qreg_data, qreg_measure, creg_data, creg_syndrome)


def initialize_qubits(circuit: QuantumCircuit):
    """Initialize qubit to |1>"""
    circuit.x(qreg_data[0])
    circuit.barrier(qreg_data)
    return circuit


def encode_bit_flip(circuit, state, ancillas) -> QuantumCircuit:
    """Encode bit-flip. This is done by simply adding a cx"""
    for ancilla in ancillas:
        circuit.cx(state, ancilla)
    circuit.barrier(state, *ancillas)
    return circuit


def measure_syndrome_bit(circuit, qreg_data, qreg_measure, creg_measure):
    """
    Measure the syndrome by measuring the parity.
    We reset our ancilla qubits after measuring the stabilizer
    so we can reuse them for repeated stabilizer measurements.
    Because we have already observed the state of the qubit,
    we can write the conditional reset protocol directly to
    avoid another round of qubit measurement if we used
    the `reset` instruction.
    """
    # TODO: generalize this to any number of qubits, try unrollable for loop with pyqasm.unroll()
    circuit.cx(qreg_data[0], qreg_measure[0])
    circuit.cx(qreg_data[1], qreg_measure[0])
    circuit.cx(qreg_data[0], qreg_measure[1])
    circuit.cx(qreg_data[2], qreg_measure[1])
    circuit.barrier(*qreg_data, *qreg_measure)
    circuit.measure(qreg_measure, creg_measure)
    with circuit.if_test((creg_syndrome[0], 1)):
        circuit.x(qreg_measure[0])
    with circuit.if_test((creg_syndrome[1], 1)):
        circuit.x(qreg_measure[1])
    circuit.barrier(*qreg_data, *qreg_measure)
    return circuit


def apply_correction_bit(circuit, qreg_data, creg_syndrome):
    """We can detect where an error occurred and correct our state"""
    with circuit.if_test((creg_syndrome, 3)):
        circuit.x(qreg_data[0])
    with circuit.if_test((creg_syndrome, 1)):
        circuit.x(qreg_data[1])
    with circuit.if_test((creg_syndrome, 2)):
        circuit.x(qreg_data[2])
    circuit.barrier(qreg_data)
    return circuit


def apply_final_readout(circuit, qreg_data, creg_data):
    """Read out the final measurements"""
    circuit.barrier(qreg_data)
    circuit.measure(qreg_data, creg_data)
    return circuit


def build_error_correction_sequence(apply_correction: bool) -> QuantumCircuit:
    circuit = build_qc()
    circuit = initialize_qubits(circuit)
    circuit = encode_bit_flip(circuit, state_data, ancillas_data)
    circuit = measure_syndrome_bit(
        circuit, qreg_data, qreg_measure, creg_syndrome
    )

    if apply_correction:
        circuit = apply_correction_bit(circuit, qreg_data, creg_syndrome)

    circuit = apply_final_readout(circuit, qreg_data, creg_data)
    return circuit

    circuit = build_error_correction_sequence(apply_correction=True)
    circuit.draw(output="mpl", style="iqp")


def main():
    # Build the quantum error correction circuit
    circuit = build_error_correction_sequence(apply_correction=True)

    # Convert the circuit to OpenQASM
    # If you try to submit the qiskit code with if-else statements, the qbraid transpiler will throw an error when ucc calls it
    # TODO: add the OpenQASM export
    qasm_code = translate(circuit, target="qasm3")

    # TODO: Unroll loops with pyqasm
    module = pyqasm.loads(qasm_code)
    module.unroll()
    # circuit = qasm_code

    # Compile with ucc
    compiled_circuit = ucc.compile(circuit)
    # compiled_circuit = transpile(circuit, optimization_level=3)
    # Print the circuit
    print(compiled_circuit)


if __name__ == "__main__":
    main()
