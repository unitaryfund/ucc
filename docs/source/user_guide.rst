Unitary Compiler Collection User Guide
######################################

The Unitary Compiler Collection (UCC) is a Python library for frontend-agnostic, high performance compilation\* of quantum circuits.
It can be used with multiple quantum computing frameworks, including `Qiskit <https://github.com/Qiskit/qiskit>`_, `Cirq <https://github.com/quantumlib/Cirq>`_, and `PyTKET <https://github.com/CQCL/tket>`_ via OpenQASM2.

Installation
*************

To install ``ucc`` run:

:code:`pip install ucc`


UCC requires Python version :math:`\ge` 3.12. 

Basic usage
***********

To use UCC, one must first specify a circuit in a supported format.
For basic usage, the circuit of interest is simply input into the function ``ucc.compile()``.
The output of ``ucc.compile()`` is a transpiled circuit that is logically equivalent to the input circuit but with reduced gate counts (and by default returned in the same format) as the input circuit.
For example, we can define a random circuit in Qiskit and optimize it using the default settings of ``ucc.compile()``, as shown in the following example.

.. code:: python

   from qiskit.circuit.random import random_clifford_circuit
   import ucc
   from ucc.benchmarks.utils import count_multi_qubit_gates_qiskit


   gates = ["cx", "cz", "cy", "swap", "x", "y", "z", "s", "sdg", "h"]
   num_qubits = 10
   raw_circuit = random_clifford_circuit(
       num_qubits, gates=gates, num_gates=10 * num_qubits * num_qubits
   )
   compiled_circuit = ucc.compile(raw_circuit)
   print(f"Number of multi-qubit gates in original circuit: {count_multi_qubit_gates_qiskit(raw_circuit)}")
   print(f"Number of multi-qubit gates in compiled circuit: {count_multi_qubit_gates_qiskit(compiled_circuit)}")


Key modules
***********

UCC includes the following modules:

- ``quantum_translator`` for translating one circuit representation into another, e.g. Qiskit into Cirq
- ``transpilers`` containing the UCC default transpiler pass sequence and execution flow. UCC default passes, i.e. passes included in ``UCC_Default1`` are:
   - ``BasisTranslator``
   - ``Optimize1qGatesDecomposition``
   - ``CommutativeCancellation``
   - ``Collect2qBlocks``
   - ``ConsolidateBlocks``
   - ``UnitarySynthesis``
   - ``Optimize1qGatesDecomposition``
   - ``CollectCliffords``
- ``circuit_passes`` containing functions for checking commutation relations
- ``transpiler_passes`` consisting of submodules, each designed to perform a different optimization pass on the circuit.

These include the passes listed in ``UCC_Default1``, along with others for specialized use.
The full list of transpiler passes available in UCC can be found in the :doc:`api`.


Customization
*************

UCC offers different levels of customization, from settings accepted by the "default" pass ``UCCDefault1`` to the ability to add custom transpiler passes. 

Transpilation settings
======================
UCC settings can be adjusted using the keyword arguments of the ``ucc.compile()`` function, as shown. 

.. code:: python

   ucc.compile(
       circuit,
       return_format="original",
       mode="ucc",
       target_device=None,
       get_gate_counts=False,
   )


- ``return_format`` is the format in which the input circuit will be returned, e.g. "TKET" or "OpenQASM2". Check ``ucc.supported_circuit_formats()`` for supported circuit formats. Default is the format of input circuit. 
- ``mode`` specifies transpiler mode to use; currently ``ucc`` and ``qiskit`` are supported.
- ``target_device`` can be specified as a Qiskit backend or coupling map, or a list of connections between qubits. If None, all-to-all connectivity is assumed. If a Qiskit backend or coupling map is specified, only the coupling list extracted from the backend is used.
- ``get_gate_counts`` - if ``True``, gate counts of the compiled circuit are returned along with the compiled circuit. Default is ``False``.

Writing a custom pass
=====================
UCC reuses part of the Qiskit transpiler framework for creation of custom transpiler passes, specifically the ``TransformationPass`` type of pass and the ``PassManager`` object for running custom passes and sequences of passes.
In the following example, we demonstrate how to create a custom pass, where the Directed Acycylic Graph (DAG) representation of the circuit is the object manipulated by the pass.

.. code:: python

   from qiskit.transpiler.basepasses import TransformationPass
   from qiskit.dagcircuit import DAGCircuit

   class MyCustomPass(TransformationPass):

       def __init__(self):
           super().__init__()


       def run(self, dag: DAGCircuit) -> DAGCircuit:
           #  Your code here
           return dag


Applying a non-default pass in the transpilation sequence
=========================================================

UCC's built-in pass manager ``UCCDefault1().pass_manager`` can be used to apply a non-default or a custom pass in the sequence of transpilation passes.
In the following example we show how to add passes for merging single qubit rotations interrupted by a commuting 2 qubit gate.

.. code:: python
   
   from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel
   from qiskit.transpiler.passes import Optimize1qGatesSimpleCommutation

   from ucc import UCCDefault1
   from ucc.transpiler_passes import BasisTranslator


   single_q_basis = ['rz', 'rx', 'ry', 'h']
   target_basis = single_q_basis.append('cx')
   ucc_compiler = UCCDefault1()

   ucc_compiler.pass_manager.append(Optimize1qGatesSimpleCommutation(basis=single_q_basis))
   ucc_compiler.pass_manager.append(BasisTranslator(sel, target_basis=target_basis)) 

   custom_compiled_circuit = ucc_compiler.run(circuit_to_compile)


Alternatively, we can add a custom pass in the sequence, as shown in the following example.

.. code:: python

   from ucc import UCCDefault1
   ucc_compiler = UCCDefault1()

   ucc_compiler.pass_manager.append(MyCustomPass())

   custom_compiled_circuit = ucc_compiler.run(circuit_to_compile)


A note on terminology
*********************

\* There is some disagreement in the quantum computing community on the proper usage of the terms "transpilation" and "compilation."
For instance, Qiskit refers to optimization of the Directed Acyclic Graph (DAG) of a circuit as "transpilation," whereas in qBraid, the 1:1 translation of one circuit representation into another without optimization (e.g. a Cirq circuit to a Qiskit circuit; OpenQASM 2 into PyTKET) is called "transpilation." 
In addition, Cirq uses the term "transformer" and PyTKET uses :code:`CompilationUnit` to refer to what Qiskit calls a transpiler pass.
