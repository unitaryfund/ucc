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
    qubit[size] cat_qubits;
    qubit verify_qubit;

    bool success = false;

    while( !success ) {

    reset qubits;
    bit res = 0;

    h cat_qubits[1];
    for int i in [1:size] {
        cx cat_qubits[1], cat_qubits[i];
    }

    // verify
    for int i in [1:size] {
        reset verify_qubit;
        cx cat_qubits[i-1], verify_qubit;
        cx cat_qubits[i], verify_qubit;
        bit tmp = measure verify_qubit;
        res = res | tmp;
    }

    sucess = res == 0;

    }
    """.replace("__NUM_QUBITS__", str(num_qubits))

    # Check if the circuit is fault tolerant
    result = ft_check(stabilizers, circuit, max_faults)
    assert result == expected_result
