# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Optimize chains of single-qubit gates using Euler 1q decomposer"""

import logging
import math

from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.passes.utils import control_flow
from qiskit.synthesis.one_qubit import one_qubit_decompose
from qiskit._accelerate import euler_one_qubit_decomposer
from qiskit.circuit.library.standard_gates import (
    UGate,
    PhaseGate,
    U3Gate,
    U2Gate,
    U1Gate,
    RXGate,
    RYGate,
    RZGate,
    RGate,
    SXGate,
    XGate,
)
from qiskit.circuit import Qubit
from qiskit.circuit.quantumcircuitdata import CircuitInstruction
from qiskit.dagcircuit.dagcircuit import DAGCircuit
from qiskit.dagcircuit.dagnode import DAGOpNode


logger = logging.getLogger(__name__)

# When expanding the list of supported gates this needs to updated in
# lockstep with the VALID_BASES constant in src/euler_one_qubit_decomposer.rs
# and the global variables in one_qubit_decompose.py
NAME_MAP = {
    "u": UGate,
    "u1": U1Gate,
    "u2": U2Gate,
    "u3": U3Gate,
    "p": PhaseGate,
    "rx": RXGate,
    "ry": RYGate,
    "rz": RZGate,
    "r": RGate,
    "sx": SXGate,
    "x": XGate,
}


class Optimize1qGatesDecomposition(TransformationPass):
    """Optimize chains of single-qubit gates by combining them into a single gate.

    The decision to replace the original chain with a new re-synthesis depends on:
     - whether the original chain was out of basis: replace
     - whether the original chain amounts to identity: replace with null

    """

    def __init__(self, basis=None):
        """Optimize1qGatesDecomposition initializer.

        Args:
            basis (list[str]): Basis gates to consider, e.g. `['u3', 'cx']`. For the effects
                of this pass, the basis is the set intersection between the `basis` parameter
                and the Euler basis.
        """
        super().__init__()

        self._basis_gates = basis
        self._global_decomposers = []
        self._local_decomposers_cache = {}

        if basis:
            self._global_decomposers = _possible_decomposers(set(basis))

    def _resynthesize_run(self, matrix, qubit=None):
        """
        Re-synthesizes one 2x2 `matrix`, typically extracted via `dag.collect_1q_runs`.

        Returns the newly synthesized circuit in the indicated basis, or None
        if no synthesis routine applied.

        """

        best_synth_circuit = euler_one_qubit_decomposer.unitary_to_gate_sequence(
            matrix,
            self._global_decomposers,
            qubit,
        )
        return best_synth_circuit

    @control_flow.trivial_recurse
    def run(self, dag):
        """Run the Optimize1qGatesDecomposition pass on `dag`.

        Args:
            dag (DAGCircuit): the DAG to be optimized.

        Returns:
            DAGCircuit: the optimized DAG.
        """
        runs = []
        qubits = []
        bases = []
        for run in dag.collect_1q_runs():
            qubit = dag.find_bit(run[0].qargs[0]).index
            runs.append(run)
            qubits.append(qubit)
            bases.append(self._global_decomposers)
        best_sequences = euler_one_qubit_decomposer.optimize_1q_gates_decomposition(
            runs, qubits, bases, simplify=True
        )
        for index, best_circuit_sequence in enumerate(best_sequences):
            run = runs[index]
            qubit = qubits[index]
            if best_circuit_sequence is not None:
                (_, _, best_circuit_sequence) = best_circuit_sequence

                first_node_id = run[0]._node_id
                qubit = run[0].qargs
                for gate, angles in best_circuit_sequence:
                    op = CircuitInstruction.from_standard(gate, qubit, angles)
                    node = DAGOpNode.from_instruction(op, dag=dag)
                    node._node_id = dag._multi_graph.add_node(node)
                    dag._increment_op(gate.name)
                    dag._multi_graph.insert_node_on_in_edges(node._node_id, first_node_id)
                dag.global_phase += best_circuit_sequence.global_phase
                # Delete the other nodes in the run
                for current_node in run:
                    dag.remove_op_node(current_node)

        return dag

def _possible_decomposers(basis_set):
    decomposers = []
    if basis_set is None:
        decomposers = list(one_qubit_decompose.ONE_QUBIT_EULER_BASIS_GATES)
    else:
        euler_basis_gates = one_qubit_decompose.ONE_QUBIT_EULER_BASIS_GATES
        for euler_basis_name, gates in euler_basis_gates.items():
            if set(gates).issubset(basis_set):
                decomposers.append(euler_basis_name)
        # If both U3 and U321 are in decomposer list only run U321 because
        # in worst case it will produce the same U3 output, but in the general
        # case it will use U2 and U1 which will be more efficient.
        if "U3" in decomposers and "U321" in decomposers:
            decomposers.remove("U3")
        # If both ZSX and ZSXX are in decomposer list only run ZSXX because
        # in the worst case it will produce the same output, but in the general
        # case it will simplify X rotations to use X gate instead of multiple
        # SX gates and be more efficient. Running multiple decomposers in this
        # case will just waste time.
        if "ZSX" in decomposers and "ZSXX" in decomposers:
            decomposers.remove("ZSX")
    return decomposers