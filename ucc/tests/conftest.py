from pytest import fixture
from qiskit.transpiler import CouplingMap


@fixture
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


@fixture
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


@fixture
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
