# # This file has been modified from the original version in Qiskit.

# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


"""Test the VF2Layout pass"""

import rustworkx



from qiskit import QuantumRegister, QuantumCircuit
from qiskit.circuit import ControlFlowOp
from qiskit.circuit.library import CXGate, XGate
from qiskit.transpiler import CouplingMap, Layout, TranspilerError
from qiskit.transpiler.passes.layout.vf2_post_layout import VF2PostLayoutStopReason
from qiskit.converters import circuit_to_dag
from qiskit.providers.fake_provider import Fake5QV1, GenericBackendV2
from qiskit.circuit import Qubit
from qiskit.transpiler.target import Target, InstructionProperties

from ucc import compile
from ucc.transpiler_passes import VF2PostLayout


seed = 42

# 5 qubits bidirectional legacy coupling maps
BOGOTA_CMAP = [[0, 1], [1, 0], [1, 2], [2, 1], [2, 3], [3, 2], [3, 4], [4, 3]]
LIMA_CMAP = [[0, 1], [1, 0], [1, 2], [1, 3], [2, 1], [3, 1], [3, 4], [4, 3]]
YORKTOWN_CMAP = [
    [0, 1],
    [0, 2],
    [1, 0],
    [1, 2],
    [2, 0],
    [2, 1],
    [2, 3],
    [2, 4],
    [3, 2],
    [3, 4],
    [4, 2],
    [4, 3],
]

def assertLayoutV2(dag, target, property_set):
        """Checks if the circuit in dag was a perfect layout in property_set for the given
        coupling_map"""

        layout = property_set["post_layout"]

        def run(dag, wire_map):
            for gate in dag.two_qubit_ops():
                physical_q0 = wire_map[gate.qargs[0]]
                physical_q1 = wire_map[gate.qargs[1]]
                qargs = (physical_q0, physical_q1)
                assert target.instruction_supported(gate.name, qargs)
            for node in dag.op_nodes(ControlFlowOp):
                for block in node.op.blocks:
                    inner_wire_map = {
                        inner: wire_map[outer] for outer, inner in zip(node.qargs, block.qubits)
                    }
                    run(circuit_to_dag(block), inner_wire_map)

        run(dag, {bit: layout[bit] for bit in dag.qubits if bit in layout})


def test_2q_circuit_5q_backend_v2():
    """A simple example, without considering the direction
        0 - 1
    qr1 - qr0
    """
    backend = GenericBackendV2(
        num_qubits=5,
        basis_gates=["cx", "id", "rz", "sx", "x"],
        coupling_map=YORKTOWN_CMAP,
        seed=seed,
    )

    qr = QuantumRegister(2, "qr")
    circuit = QuantumCircuit(qr)
    circuit.cx(qr[1], qr[0])  # qr1 -> qr0
    tqc = compile(circuit)
    initial_layout = tqc._layout
    dag = circuit_to_dag(tqc)
    pass_ = VF2PostLayout(target=backend.target, seed=seed, strict_direction=False)
    pass_.run(dag)
    assertLayoutV2(dag, backend.target, pass_.property_set)
    assert pass_.property_set["post_layout"] != initial_layout
