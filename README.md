## `ucc`: Unitary Compiler Collection
<a href="https://github.com/unitaryfoundation/ucc"><img src="https://raw.githubusercontent.com/unitaryfoundation/ucc/main/docs/source/img/UCC-logo.png" alt="light orange oval with a hissing black cat in the center with UCC written across the bottom" width="350"/></a>

[![Repository](https://img.shields.io/badge/GitHub-5C5C5C.svg?logo=github)](https://github.com/unitaryfoundation/ucc)
[![PyPI version](https://badge.fury.io/py/ucc.svg)](https://badge.fury.io/py/ucc)
[![Downloads](https://static.pepy.tech/personalized-badge/ucc?period=total&units=international_system&left_color=black&right_color=green&left_text=Downloads)](https://www.pepy.tech/projects/ucc)
[![License](https://img.shields.io/github/license/unitaryfoundation/ucc)](https://github.com/unitaryfoundation/ucc/blob/main/LICENSE)
[![Unitary Foundation](https://img.shields.io/badge/Supported%20By-Unitary%20Foundation-FFFF00.svg)](https://unitary.foundation)
[![Documentation Status](https://readthedocs.org/projects/ucc/badge/?version=latest)](https://ucc.readthedocs.io/en/latest/?badge=latest)
[![Discord Chat](https://img.shields.io/badge/dynamic/json?color=blue&label=Discord&query=approximate_presence_count&suffix=%20online.&url=https%3A%2F%2Fdiscord.com%2Fapi%2Finvites%2FJqVGmpkP96%3Fwith_counts%3Dtrue)](http://discord.unitary.foundation)

<!-- start-changelog-link-to-remove-for-docs -->
**[See the changelog](./CHANGELOG.md)**
<!-- end-changelog-link-to-remove-for-docs -->

The **Unitary Compiler Collection (UCC)** is a Python library for frontend-agnostic, high performance compilation of quantum circuits. UCC's goal is to gather together the best of open source compilation to make quantum programming simpler, faster, and more scalable.

By leveraging [qBraid](https://github.com/qBraid/qBraid), UCC interfaces automatically with multiple quantum computing frameworks, including [Qiskit](https://github.com/Qiskit/qiskit), [Cirq](https://github.com/quantumlib/Cirq), and [PyTKET](https://github.com/CQCL/tket) and supports programs in OpenQASM 2 and [OpenQASM 3](https://openqasm.com/). For a full list of the latest supported interfaces, just call `ucc.supported_circuit_formats`.


**Want to know more?**
- Check out our [documentation](https://ucc.readthedocs.io/en/latest/), which you can build locally after installation by running `make html` in `ucc/docs/source`.
- Watch our [introductory video](https://www.youtube.com/watch?v=11uQynyOUI8) about UCC presented at [FOSDEM 2025](https://fosdem.org/2025/) by [@natestamen](https://github.com/natestemen/).
- Read the [launch announcement](https://unitary.foundation/posts/2025_ucc_launch_blog) to learn more on the current state of UCC, its capabilities and future direction.
- For code, repo, or theory questions, especially those requiring more detailed responses, submit a [Discussion](https://github.com/unitaryfoundation/ucc/discussions).
- For casual or time sensitive questions, chat with us on [Discord](http://discord.unitary.foundation).

## Quickstart

### Installation

**Note**: UCC requires Python version ≥ 3.12.

For normal users of `UCC`, you can install via `pip` as
```bash
pip install ucc
```

If developing, including if building custom transpiler passes, please install [uv](https://docs.astral.sh/uv/getting-started/installation/), which is used to managed dependencies and ensure a reproducible development enviroment. Once uv is installed, setup your development environment via

```bash
git clone https://github.com/unitaryfoundation/ucc.git
cd ucc
uv sync --all-extras --all-groups
```

This `uv sync` command ensures the optional developer and documentation dependences are installed. For development with uv, we assume you either prefix each command with ``uv run``, or
you first activate the [uv managed virtual environment](https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment) by running ``source .venv/bin/activate`` in your shell.

For more details on using uv, refer to its [documentation](https://docs.astral.sh/uv/) or [this tutorial](https://realpython.com/python-uv/).


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
    compile(circuit)

def test_qiskit_compile():
    circuit = QiskitCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    compile(circuit)

def test_cirq_compile():
    qubits = LineQubit.range(2)
    circuit = CirqCircuit(
        H(qubits[0]),
        CNOT(qubits[0], qubits[1]))
    compile(circuit)
```
<!-- start-how-does-ucc-stack-up -->
<!-- comment used to strip this section from being added to the docs build-->
## How does UCC stack up?

UCC seeks to provide an end-to-end compiler that works well for the majority of the users out of the box. Today, this is achieved by running a particular subset of [Qiskit](https://github.com/Qiskit/qiskit) transpiler passes.
To ensure we continue to improve performance and meet user needs, we regularly run benchmarks comparing UCC against the latest versions of leading quantum compiler frameworks across a range of circuits. Here’s the latest:
![alt text](https://github.com/unitaryfoundation/ucc-bench/blob/main/results/ucc-benchmarks-8-core-U22.04/latest_compiler_benchmarks_by_circuit.png?raw=true)

And here you can see progress over time, with new package versions labeled for each compiler:
![alt text](https://github.com/unitaryfoundation/ucc-bench/blob/main/results/ucc-benchmarks-8-core-U22.04/avg_compiler_benchmarks_over_time.png?raw=true)
where pytket-peep indicates the `FullPeepHoleOptimize` function of PyTKET.

The benchmark code, configurations and raw results from running on specific hardware are maintined in the companion repository of [`ucc-bench`](https://github.com/unitaryfoundation/ucc-bench).

To learn more about running these benchmarks, the overall benchmark philosophy, or how to contribute to improving the benchmarking methodology, check out the [benchmarking section](https://ucc.readthedocs.io/en/latest/benchmarking.html) in the docs or the `README.md` in [`ucc-bench`](https://github.com/unitaryfoundation/ucc-bench).
<!-- end-how-does-ucc-stack-up -->

## Contributing

We’re building UCC as a community-driven project.
Your contributions help improve the tool for everyone!
There are many ways you can contribute, such as

- **Create a Custom Compiler Pass**: Learn how in the [User Guide](https://ucc.readthedocs.io/en/latest/user_guide.html)
- **Submit a bug report or feature request**: Submit a bug report or feature request [on GitHub](https://github.com/unitaryfoundation/ucc/issues/new/choose).
- **Contribute Code**: Follow the [Contribution Guide](https://ucc.readthedocs.io/en/latest/contributing.html) to submit new passes and improvements.

If you have questions about contributing please ask on the [Unitary Foundation Discord](http://discord.unitary.foundation).

## License

UCC is distributed under [GNU Affero General Public License version 3.0](https://www.gnu.org/licenses/agpl-3.0.en.html)(AGPLv3).
Parts of ucc contain code or modified code that is part of [Qiskit](https://github.com/Qiskit/qiskit) or [Qiskit Benchpress](https://github.com/Qiskit/benchpress), which are distributed under the Apache 2.0 license.
