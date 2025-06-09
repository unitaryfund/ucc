"""
# This file is part of the Universal Circuit Compiler (UCC).
"""

import pytest
from qiskit import QuantumCircuit
from qiskit_ibm_runtime.fake_provider import FakeVigoV2

from ucc import compile as ucc_compile


def test_pass_raises_error_without_device():
    """Tests that the pass correctly raises an error if no device is provided."""
    qc = QuantumCircuit(2)
    with pytest.raises(
        ValueError, match="Noise-aware routing requires a `target_device`"
    ):
        ucc_compile(qc, noise_aware_routing=True, target_device=None)


def test_pass_adds_swaps_for_disconnected_qubits():
    """
    Tests that routing is performed for an incompatible circuit.

    The correct outcome of routing is not the literal presence of a 'swap' gate
    in the final output (as it gets decomposed), but an increase in the number
    of hardware-native 2-qubit gates (cx).
    """
    target_device = FakeVigoV2()

    # This circuit has 1 CX gate that cannot run on Vigo's topology.
    qc = QuantumCircuit(4)
    qc.cx(0, 3)
    original_cx_count = qc.num_nonlocal_gates()
    assert original_cx_count == 1

    # Compile with our noise-aware pass
    compiled_qc = ucc_compile(
        qc, noise_aware_routing=True, target_device=target_device
    )

    # The final circuit should have more CX gates than the original,
    # because the SWAP gate was decomposed into 3 CXs.
    # Expected final count = 1 (original) + 3 (from SWAP) = 4.
    final_cx_count = compiled_qc.count_ops().get("cx", 0)
    assert final_cx_count > original_cx_count


def test_pass_on_compatible_circuit():
    """
    Tests that no SWAPs are added for a circuit that is already
    compatible with the device topology, meaning the cx count doesn't change.
    """
    target_device = FakeVigoV2()

    # This circuit has 1 CX gate that is compatible with Vigo's topology.
    qc = QuantumCircuit(2)
    qc.cx(0, 1)
    original_cx_count = qc.num_nonlocal_gates()
    assert original_cx_count == 1

    compiled_qc = ucc_compile(
        qc, noise_aware_routing=True, target_device=target_device
    )

    # Since no routing was needed, the final CX count should be the same as the original.
    # (Minor changes from 1q optimizations are possible but cx should be stable).
    final_cx_count = compiled_qc.count_ops().get("cx", 0)
    assert final_cx_count == original_cx_count
