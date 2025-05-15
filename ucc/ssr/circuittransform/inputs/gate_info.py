# -*- coding: utf-8 -*-
"""
Created on Sat Oct  8 17:06:03 2022

@author: zhoux

Store the parameters and basic methods of quantum gates.
"""

# SWAP is composed by 3 CXs
gate_depth_cx = {
    "cx": 1,
    "h": 1,
    "t": 1,
    "x": 1,
    "y": 1,
    "z": 1,
    "s": 1,
    "rx": 1,
    "ry": 1,
    "rz": 1,
    "u3": 1,
    "tdg": 1,
    "swap": 3,
    "p": 1,
    "u2": 1,
    "u1": 1,
    "u": 1,
    "cz": 1,
    "sx": 1,
}
# SWAP is composed by 3 CZs and 4 Hs
## Note that for CZ-implemented SWAPs, we always assume they will take all
## 7 time slots, i.e., ignoring the two positions that may be saved by vacaent
## single-qubit gates.
gate_depth_cz = {
    "cx": 1,
    "h": 1,
    "t": 1,
    "x": 1,
    "y": 1,
    "z": 1,
    "s": 1,
    "rx": 1,
    "ry": 1,
    "rz": 1,
    "u3": 1,
    "tdg": 1,
    "swap": 7,
    "p": 1,
    "u2": 1,
    "u1": 1,
    "u": 1,
    "cz": 1,
    "sx": 1,
}


def gen_swap_via_cx(q0, q1):
    return [("cx", (q0, q1), []), ("cx", (q1, q0), []), ("cx", (q0, q1), [])]


# swap(q0, q1) = h[q0], cz[q0, q1], h[0], h[q1], cz[q0, q1], h[1], h[q0], cz[q0, q1], h[0]
def gen_swap_via_cz(q0, q1):
    return [
        ("h", (q0,), []),
        ("cz", (q0, q1), []),
        ("h", (q0,), []),
        ("h", (q1,), []),
        ("cz", (q0, q1), []),
        ("h", (q1,), []),
        ("h", (q0,), []),
        ("cz", (q0, q1), []),
        ("h", (q0,), []),
    ]


"""
gate is a tuple (gate_name, (qubits), (parameters))
supported gate_name:
    cx
    u3
    ...
"""
# {gate_name: (num_qubits, num_parameters)}
supported_gate_names = {
    "cx": (2, 0),
    "h": (1, 0),
    "t": (1, 0),
    "x": (1, 0),
    "y": (1, 0),
    "z": (1, 0),
    "s": (1, 0),
    "rx": (1, 1),
    "ry": (1, 1),
    "rz": (1, 1),
    "u3": (1, 3),
    "tdg": (1, 0),
    "p": (1, 1),
    "u2": (1, 2),
    "u1": (1, 1),
    "swap": (2, 0),
    "u": (1, 3),
    "id": (1, 1),
    "cz": (2, 0),
    "sx": (1, 0),
}
