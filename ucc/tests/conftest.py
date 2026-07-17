import pytest
from qiskit.transpiler import CouplingMap


@pytest.fixture
def line4():
    return CouplingMap(
        [
            [0, 1],
            [1, 0],
            [1, 2],
            [2, 1],
            [2, 3],
            [3, 2],
        ]
    )


@pytest.fixture
def square4():
    return CouplingMap(
        [
            [0, 1],
            [1, 0],
            [1, 2],
            [2, 1],
            [2, 3],
            [3, 2],
            [3, 0],
            [0, 3],
        ]
    )


@pytest.fixture
def star4():
    return CouplingMap(
        [
            [0, 1],
            [1, 0],
            [0, 2],
            [2, 0],
            [0, 3],
            [3, 0],
        ]
    )
