# <a href="https://github.com/unitaryfund/ucc">
[![Repository](https://img.shields.io/badge/GitHub-5C5C5C.svg?logo=github)](https://github.com/unitaryfund/ucc)
[![Unitary Fund](https://img.shields.io/badge/Supported%20By-Unitary%20Fund-FFFF00.svg)](https://unitary.fund)
[![Discord Chat](https://img.shields.io/badge/dynamic/json?color=blue&label=Discord&query=approximate_presence_count&suffix=%20online.&url=https%3A%2F%2Fdiscord.com%2Fapi%2Finvites%2FJqVGmpkP96%3Fwith_counts%3Dtrue)](http://discord.unitary.fund)

The **Unitary Compiler Collection (UCC)** is a Python library for frontend-agnostic, high performance compilation of quantum circuits. It interfaces with multiple quantum computing frameworks, including [Qiskit](https://github.com/Qiskit/qiskit), [Cirq](https://github.com/quantumlib/Cirq), and [PyTKET](https://github.com/CQCL/tket) via OpenQASM2. 


## Quickstart

### Installation

<<<<<<< HEAD
=======

>>>>>>> 9d08e6b6097bbc6ae37e423b880becd56a428eb2
```bash
git clone https://github.com/unitaryfund/ucc.git
cd ucc
pip install -e . # Editable mode
```

### Example with Qiskit, Cirq, and PyTKET

Define a circuit with your preferred quantum SDK and compile it!

```python
from ucc import compile

from pytket import Circuit as TketCircuit
from cirq import Circuit as CirqCircuit
from qiskit import QuantumCircuit as QiskitCircuit
from cirq import H, CNOT, LineQubit

def test_tket_compile():
    circuit = TketCircuit(2)
    circuit.H(0)
    circuit.CX(0, 1)
<<<<<<< HEAD
    compile(circuit, qasm_version='2', return_format='original')
=======
    compile(circuit, return_format='original')
>>>>>>> 9d08e6b6097bbc6ae37e423b880becd56a428eb2

def test_qiskit_compile():
    circuit = QiskitCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
<<<<<<< HEAD
    compile(circuit, qasm_version='2', return_format='original')
=======
    compile(circuit, return_format='original')
>>>>>>> 9d08e6b6097bbc6ae37e423b880becd56a428eb2

def test_cirq_compile():
    qubits = LineQubit.range(2)
    circuit = CirqCircuit(H(qubits[0]), CNOT(qubits[0], qubits[1]))
<<<<<<< HEAD
    compile(circuit, qasm_version='2', return_format='original')
=======
    compile(circuit, return_format='original')
>>>>>>> 9d08e6b6097bbc6ae37e423b880becd56a428eb2
```

## License
UCC is distributed under [GNU Affero General Public License version 3.0](https://www.gnu.org/licenses/agpl-3.0.en.html)(AGPLv3). 
Parts of ucc contain code or modified code that is part of Qiskit, which is distributed under Apache 2.0 license.
