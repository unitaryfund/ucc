Unitary Compiler Collection User Guide
######################################

The Unitary Compiler Collection (UCC) is a Python library for frontend-agnostic, high performance compilation\* of quantum circuits.
It can be used with multiple quantum computing frameworks, including `Qiskit <https://github.com/Qiskit/qiskit>`_, `Cirq <https://github.com/quantumlib/Cirq>`_, and `PyTKET <https://github.com/CQCL/tket>`_ via OpenQASM2.

Installation
*************

To install ``ucc`` run

.. code:: bash

   pip install ucc

UCC requires Python version ≥ 3.12.

Basic usage
***********

To use UCC, one must first specify a circuit in a supported format.
For basic usage, the circuit of interest is simply input into the function ``ucc.compile()``.
The output of ``ucc.compile()`` is a transpiled circuit that is logically equivalent to the input circuit but with reduced gate counts (and by default returned in the same format as the input circuit).
For example, we can define a random circuit in Qiskit and optimize it using the default settings of ``ucc.compile()``, as shown in the following example.

..
   This comment is around the testcode/testoutput block below. These leverage
   doctest extension of sphinx to test this code actually runs and any output
   matches. The ELLIPSIS directive (and the use of ... in the expected output) of
   the testoutput block avoids us needing to explicitly have the gate count, which
   is subject to change as ucc changes over time.

.. testcode::

   from qiskit.circuit.random import random_clifford_circuit
   import ucc


   gates = ["cx", "cz", "cy", "swap", "x", "y", "z", "s", "sdg", "h"]
   num_qubits = 10
   raw_circuit = random_clifford_circuit(
      num_qubits, gates=gates, num_gates=10 * num_qubits * num_qubits
   )
   compiled_circuit = ucc.compile(raw_circuit)
   print(f"Number of multi-qubit gates in original circuit: {raw_circuit.num_nonlocal_gates()}")
   print(f"Number of multi-qubit gates in compiled circuit: {compiled_circuit.num_nonlocal_gates()}")

.. testoutput::
   :hide:
   :options: +ELLIPSIS, +NORMALIZE_WHITESPACE

   Number of multi-qubit gates in original circuit: ...
   Number of multi-qubit gates in compiled circuit: ...


Default Compilation Passes
**************************

When compiling, UCC uses a set of pre-defined qiskit passes set of compilation passes specified in ``ucc.ucc_defaults.UCCDefault1``.
These were chosen based on their good default performance on a set of input circuits. The vision for UCC is
to iterate and improve on these defaults, following the process in :doc:`contributing`.

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
       target_gateset=None,
       target_device=None,
       custom_passes=None
   )


- ``return_format`` is the format in which the input circuit will be returned, e.g. "TKET" or "OpenQASM2". Check ``ucc.supported_circuit_formats`` for supported circuit formats. Default is the format of input circuit.
- ``target_gateset`` is the gateset to compile the circuit to, e.g. {"cx", "rx",...}. Defaults to the gateset of the target device. If none is provided, defaults to `{"cx", "rz", "rx", "ry", "h"}`.
- ``target_device`` can be specified as a Qiskit backend. If None, all-to-all connectivity is assumed. If a `target_device` is specified, `target_device.operation_names` supercedes the `target_gateset`.
- ``custom_passes`` can be a list of Qiskit ``TransformationPass`` objects to run after the default set of passes in ``UCCDefault1``.

Writing a custom pass
=====================
UCC reuses part of the Qiskit transpiler framework for creation of custom transpiler passes, specifically the ``TransformationPass`` type of pass and the ``PassManager`` object for running custom passes and sequences of passes.
In the following example, we demonstrate how to create a custom pass, where the Directed Acycylic Graph (DAG) representation of the circuit is the object manipulated by the pass.

..
   This testsetup is associated with subsequent blocks that also have the custom_pass group.
   This setup is run, followed by all the blocks with this group in order and
   ensures the "circuit_to_compile" variable is defined.

.. testsetup:: custom_pass

   from qiskit import QuantumCircuit as QiskitCircuit
   circuit_to_compile = QiskitCircuit(2)
   circuit_to_compile.h(0)
   circuit_to_compile.cx(0, 1)

.. testcode:: custom_pass

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

The ``compile`` method accepts an optional list of custom passes to run after the default suite defined in the  built-in pass manager ``UCCDefault1().pass_manager``.
In the following example we show how to add pre-defined Qiskit passes for merging single qubit rotations interrupted by a commuting 2 qubit gate.

.. testcode:: custom_pass

   from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel
   from qiskit.transpiler.passes import (
      BasisTranslator,
      Optimize1qGatesSimpleCommutation,
   )
   from ucc import compile


   single_q_basis = ["rz", "rx", "ry", "h"]
   target_basis = single_q_basis.append("cx")

   custom_passes = [
      Optimize1qGatesSimpleCommutation(basis=single_q_basis),
      BasisTranslator(sel, target_basis=target_basis),
   ]

   custom_compiled_circuit = compile(
      circuit_to_compile, custom_passes=custom_passes
   )

Alternatively, we can add our custom pass, as shown in the following example.

.. testcode:: custom_pass

   from ucc import compile
   custom_compiled_circuit = compile(
      circuit_to_compile, custom_passes=[MyCustomPass()]
   )

An Example of a Custom Pass: BQSKitTransformationPass
=====================================================

The ``BQSKitTransformationPass`` is a custom pass provided in ``ucc.transpilers.ucc_bqskit``. It uses `BQSKit <https://github.com/BQSKit/bqskit>`_ to optimize the circuit. BQSKit is slower than Qiskit, but can find optimizations where Qiskit cannot, especially in circuits with lots of small-angle single-qubit gates interspersed among multi-qubit gates such that optimization techniques that apply a fixed set of known identities will not perform well.

In general, if you wouldn't mind a slower runtime in exchange for finding a shorter circuit, you may find it helpful to include the ``BQSKitTransformationPass`` in your workflow.


Before you can use ``BQSKitTransformationPass``, you must install BQSKit:

.. code:: bash

   pip install bqskit

Here is an example of how to use the ``BQSKitTransformationPass``:

..
   This testsetup is associated with subsequent blocks that also have the bqskit group.
   This setup is run, followed by all the blocks with this group in order and
   ensures the "circuit_to_compile" variable is defined.

.. testsetup:: bqskit

   from qiskit import QuantumCircuit as QiskitCircuit
   from ucc import compile
   qasm = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[3];
        h q[0];
        cp(1.5707963267948966) q[1], q[0];
        h q[1];
        cp(0.7853981633974483) q[2], q[0];
        cp(1.5707963267948966) q[2], q[1];
        h q[2];
        swap q[0], q[2];
        """
   circuit_to_compile = QiskitCircuit.from_qasm_str(qasm)

.. testcode:: bqskit

   from ucc.transpilers.ucc_bqskit import BQSKitTransformationPass
   result = compile(circuit_to_compile, custom_passes=[BQSKitTransformationPass()])

Instead of relying on the provided default set of BQSKit passes, you can specify your own BQSKit workflow.

.. testcode:: bqskit

   from ucc.transpilers.ucc_bqskit import BQSKitTransformationPass
   from bqskit.passes import QuickPartitioner, ForEachBlockPass, LEAPSynthesisPass, TreeScanningGateRemovalPass, UnfoldPass
   bqskit_pass_list = [
       QuickPartitioner(3),
       ForEachBlockPass([
           LEAPSynthesisPass(),
           TreeScanningGateRemovalPass(),
           ], replace_filter="less-than-multi"),
       UnfoldPass(),
       ]
   bqskit_pass = BQSKitTransformationPass(bqskit_passes=bqskit_pass_list)
   result = compile(circuit_to_compile, custom_passes=[bqskit_pass])



The ``BQSKitTransformationPass`` is just one example of the extensibility of UCC. If you would like to port a compile pass from another framework, please create a `proposal <https://github.com/unitaryfoundation/ucc/discussions/new?category=new-compiler-pass>`_ and be ready to benchmark its performance relative to ``UCCDefault1``.


An example of a custom pass: Approximate Quantum Compilation via MPS encoding
=============================================================================
The ``MPSEncoder`` is a custom pass provided in ``ucc.aqc``. Users can opt for `qmprs <https://github.com/Qualition/qmprs>`_ for a more advanced implementation of the same pass.
You can install it with ``pip install git+https://github.com/Qualition/qmprs.git``.

This pass leverages Matrix Product State (MPS) representation of a state to approximately compile the state to a quantum circuit using multiple layers of one and two qubit gates in O(N) depth.
The automatic parameter definition takes the entanglement structure of the input state into account, and tries to come up with the optimal parameters to maximize fidelity and minimize circuit depth. Users can also override ``optimal_params`` static method to define their own rule for generating the optimal parameters.

Most quantum circuit libraries are written assuming the initial state is all zeros in the computational basis. This pass's optimization may rely on that assumption. If you intend to run your post-compiled circuit on other input states, or in sequence with other circuits, be aware that this pass might not be equivalent in those cases.

Here is an example of how to use the ``MPSEncoder``:

..
   This testsetup is associated with subsequent blocks that also have the mps group.
   This setup is run, followed by all the blocks with this group in order and
   ensures the "circuit_to_compile" variable is defined.
.. testsetup:: mps

   from qiskit import QuantumCircuit as QiskitCircuit
   from ucc import compile
   qasm = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[3];
        h q[0];
        crx(1.5707963267948966) q[1], q[0];
        x q[1];
        cry(0.7853981633974483) q[2], q[0];
        crz(1.5707963267948966) q[2], q[1];
        y q[2];
        swap q[0], q[2];
        """
   circuit_to_compile = QiskitCircuit.from_qasm_str(qasm)

.. testcode:: mps

   from ucc.transpilers.aqc.mps_pass import MPSPass
   result = compile(circuit_to_compile, custom_passes=[MPSPass()])

The ``MPSEncoder`` is just one example of the extensibility of UCC. If you would like to port a compile pass from another framework, please create a `proposal <https://github.com/unitaryfoundation/ucc/discussions/new?category=new-compiler-pass>`_ and be ready to benchmark its performance relative to ``UCCDefault1``.

A note on terminology
*********************

.. important::
   There is some disagreement in the quantum computing community on the proper usage of the terms "transpilation" and "compilation."
   For instance, Qiskit refers to optimization of the Directed Acyclic Graph (DAG) of a circuit as "transpilation," whereas in qBraid, the 1:1 translation of one circuit representation into another without optimization (e.g. a Cirq circuit to a Qiskit circuit; OpenQASM 2 into PyTKET) is called "transpilation."
   In addition, Cirq uses the term "transformer" and PyTKET uses :code:`CompilationUnit` to refer to what Qiskit calls a transpiler pass.
