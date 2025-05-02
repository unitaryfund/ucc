import pytest
import numpy as np


pytest.importorskip("juliacall")
pytest.importorskip("stim")


def test_to_julia_tableau_fmt():
    from stim import PauliString, Tableau
    from ucc.ft.checker import to_julia_tableau_fmt

    # 3-qubit bit flip example
    t = Tableau.from_stabilizers(
        [PauliString("ZZI"), PauliString("IZZ"), PauliString("XXX")]
    )
    res = to_julia_tableau_fmt(t)
    expected = np.array(
        [
            [
                False,
                False,
                False,
                True,
                True,
                False,
            ],
            [False, False, False, False, True, True],
            [True, True, True, False, False, False],
        ],
        dtype=bool,
    )
    assert np.array_equal(res, expected)


@pytest.mark.parametrize(
    "max_faults, expected_result",
    [
        (2, True),
        (3, False),
    ],
)
def test_check_ft_cat_state_with_different_faults(max_faults, expected_result):
    """Test the fault tolerance of the cat state circuit with varying max_faults."""

    from stim import PauliString
    from ucc.ft.checker import ft_check

    num_qubits = 8

    stabilizers = [
        PauliString(f"Z{i}*Z{j}")
        for (i, j) in zip(range(num_qubits), range(1, num_qubits))
    ]
    stabilizers.append(PauliString("X" * num_qubits))

    circuit = """
    OPENQASM 3.0;
    include "stdgates.inc";

    const uint size = __NUM_QUBITS__;

    def cat_prep(qubit[size] state, qubit ancilla) {

        bit res = 1;
        while(res != 0) {
            reset state[0];
            res = 0;
            h state[0];

            // QASM ranges are inclusive for both start and end
            for int i in [1:(size-1)] {
                reset state[i];
                cx state[0], state[i];
            }

            // Parity check
            for int i in [1:(size-1)] {
                reset ancilla;
                cx state[i-1], ancilla;
                cx state[i], ancilla;
                bit tmp = measure ancilla;
                res = res | tmp;
            }
        }
    }
    """.replace("__NUM_QUBITS__", str(num_qubits))

    # Check if the circuit is fault tolerant
    result = ft_check(stabilizers, circuit, max_faults)
    assert result == expected_result
