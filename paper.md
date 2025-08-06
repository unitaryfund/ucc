---
abstract: |
  We introduce Unitary Compiler Collection (UCC), an open-source Python
  package for front-end-agnostic, high-performance compilation of
  quantum circuits. UCC's goal is to gather the best of open-source
  compilation to make quantum programming simpler, faster, and more
  scalable. As quantum hardware advances, so does the complexity of
  programming it: increasing qubit counts, diverse gate operations, and
  varied architectures all present new challenges for quantum
  compilation. Two major challenges that we see are (1) compiler
  improvements are often isolated in separate libraries or unmaintained
  repositories without integration into existing tools, and (2) there
  are high switching costs between quantum computing frameworks and
  hardware platforms for both compiler developers and users. To address
  these, Unitary Foundation has developed UCC with an architecture and
  contribution framework to foster collaboration and enable the most
  performant tools of quantum and classical compilation to work
  together.
author:
- 
bibliography:
- refs.bib
title: "Unitary Compiler Collection: A Community-Driven, Interoperable,
  Open-Source Quantum Compiler"
---

# Motivation & Goals

In developing the Unitary Compiler Collection (UCC)[^1], we have looked
to the *GNU* Compiler Collection (GCC). GCC's 1987 release broke vendor
lock-in by unifying multiple targets behind a modular, free compiler.
Quantum compilation is at a similar crossroads today, where even
open-source (OS) compilers are frequently restricted to working only on
a restricted quantum hardware modality -- if such compiler are
open-source at all. Even with the best intentions to generalize,
compilers are often developed with a specific hardware modality in mind.
There is correspondingly a distinct lack of agreement on interoperable
intermediate representations (IRs) which could translate across
different quantum architectures.

We see a gap in the ecosystem for an open-source quantum compiler that
is

1.  performant for currently available Noisy Intermediate-Scale Quantum
    (NISQ) hardware [@nisq_2018]

2.  responsive to the needs of the early Fault Tolerant Quantum
    Computing (FTQC) era [@early_ft_2024],

3.  compatible with multiple quantum program representations and
    user-friendly -- both to quantum algorithm developers and compiler
    engineers,

4.  genuinely driven by the needs of the quantum hardware and software
    community as a whole, not limited to a single hardware modality or
    software stack.

In this submission, we present the Unitary Compiler Collection as an
attempt to address (G1)-(G4). In particular, we focus on the design,
supporting infrastructure, and community-building aspects of UCC, along
with our bootstrapping strategy of building on and combining existing
open-source libraries. We also present some preliminary results from our
benchmarking and integration efforts, which demonstrate that even at
this early stage in its development, UCC has competitive performance to
other quantum compilers, and is in a good starting position to expand
and differentiate its capabilities.

# Alternatives

There is already a diverse ecosystem of quantum compilers, yet none
simultaneously satisfy the four requirements outlined above. Many
popular packages such as IBM's Qiskit [@qiskit2024], Google's
Cirq [@Cirq_Developers_Cirq_2025], and Quantinuum's tket [@pytket_2020]
are widely adopted with active communities [@uf_survey], but are often
tied closely to the hardware modality and roadmap of their respective
hardware platforms. As a result, other vendors in e.g. the neutral atom
space have developed their own compiler tools (QuEra's
bloqade [@quera_2025], Infleqtion's Superstaq [@superstaq]). Other
compiler packages focus on specific approaches: BQSKit [@bqskit_2021]
focuses on gate-level synthesis via optimal-control solvers,
PyZX [@kissinger2020Pyzx] offers ZX-calculus--based rewrite rules to
simplify circuits. The Munich Quantum Toolkit (MQT) [@mqt_2024] is a
comprehensive suite of compiler components and very similar in spirit to
UCC, but doesn't have the same focus on user-friendliness and
community-driven development. Taken together, this is an extensive set
of compiler tools that span many needs across the quantum compilation
stack, but creates an adoption challenge for users that want to benefit
from the strengths of each. As a result, none directly provide a single,
open-source, front-end-agnostic, multi-hardware modality quantum
compiler that is performant, user-friendly, and community-driven.

# Key design decisions {#design}

## Uniform interface

Our central, user-first goal is to lower the barrier to entry for both
algorithm developers and compiler engineers, which informed our
technical strategy of building on familiar, existing open-source
libraries. For algorithm developers, UCC offers a uniform `compile`
function that works across popular frameworks, returning a compiled
circuit in its original format:

::: minted
python from ucc import compile

from pytket import Circuit as TketCircuit from cirq import Circuit as
CirqCircuit from qiskit import QuantumCircuit as QiskitCircuit from cirq
import H, CNOT, LineQubit

def test_tket_compile(): circuit = TketCircuit(2) circuit.H(0)
circuit.CX(0, 1) compile(circuit)

def test_qiskit_compile(): circuit = QiskitCircuit(2) circuit.h(0)
circuit.cx(0, 1) compile(circuit)

def test_cirq_compile(): qubits = LineQubit.range(2) circuit =
CirqCircuit( H(qubits\[0\]), CNOT(qubits\[0\], qubits\[1\]))
compile(circuit)
:::

Likewise, for compiler developers, UCC exposes an intuitive interface
for adding custom passes, building directly on the familiar structure of
Qiskit's pass manager, which is already widely used in the quantum
community. This allows developers to focus on their specific compilation
logic without needing to learn a new framework or API.

::: minted
python from qiskit.transpiler.basepasses import TransformationPass from
qiskit.dagcircuit import DAGCircuit

class MyCustomPass(TransformationPass): def \_\_init\_\_(self):
super().\_\_init\_\_()

def run(self, dag: DAGCircuit) -\> DAGCircuit: \# Your code here return
dag custom_compiled_circuit = compile( circuit_to_compile,
custom_passes=\[MyCustomPass()\] )
:::

## Leveraging the broader ecosystem {#bootstrapping}

As hinted above, in order to accelerate development and focus on our
core goals of interoperability and user experience, we made the
strategic decision to build upon best-in-class open-source libraries
rather than reinventing core compiler functionalities. For its core
compiler capabilities, UCC adopts Qiskit's transpiler architecture
[@qiskit2024] given it's strong benchmark peformance in both circuit
reduction and runtime [@benchpress_2025] and a Python-level pass manager
backed by a fast Rust core. UCC uses a customized performance-tuned
sequence of Qiskit passes as its default compilation pipeline (see
[5](#results){reference-type="ref" reference="results"} for results).

The bootstrapping strategy was further validated in our approach to
interoperability. We initially planned to build a circuit translation
module from scratch. However, through our engagement with the Unitary
Foundation open-source community, we discovered the qBraid library
[@qbraid2025]. By adopting qBraid, UCC immediately gained support for
circuit translations between Qiskit, Cirq, PyQuil, Braket, and more,
seamlessly to the end-user. This decision not only saved significant
development time but also proved the power of our community-integrated
model: by actively participating in the ecosystem, we can identify and
integrate the best tools available.

## Infrastructure & benchmarking-assisted development {#infra_bench}

To support this community-driven approach and ensure sustainable,
high-quality contributions, we have built robust infrastructure for
development, testing, and performance validation. Our continuous
integration (CI) pipeline---powered by GitHub Actions---enforces unit
tests, linting, and code formatting on every pull request and commit.
Crucially, each CI run also executes our benchmark suite to verify that
new passes and optimizations maintain or improve key metrics such as
gate count, compile time, and circuit fidelity under noise.

![Example of UCC benchmark result, automatically run on a pending pull
request to preview the impact on
performance.](ucc_bench_comment.png){#fig:ucc_bench}

The benchmarking framework automates metric collection and comparison.
Benchmark results are published regularly to a dedicated GitHub
repository [@ucc-bench_2025], with plots of performance embedded in the
UCC README, providing transparent performance dashboards for
contributors and users. Figure [1](#fig:ucc_bench){reference-type="ref"
reference="fig:ucc_bench"} shows a benchmarking preview feature, where
the performance impact of any pending pull request is automatically
benchmarked and reported directly within the GitHub code review before
being merged. The benchmarking code's modular design makes it
straightforward to add new benchmarks---e.g., support for dynamic
circuits or novel instruction sets---ensuring extensibility as UCC and
the broader quantum-software ecosystem evolve.

# Building a Community of Contributors  {#community}

UCC's development follows a genuine open-source model, with all project
management happening publicly on GitHub, distinguishing it from
'develop-in-public' approaches or one-off code releases. Additionally,
UCC fosters a sustainable ecosystem of contributors through structured
community-building initiatives: in particular, the Unitary Foundation
microgrant program [@uf_grants] and UnitaryHACK hackathon
[@unitary_hack].

UnitaryHACK incentivizes high-quality contributions through financial
compensation and dedicated mentorship, effectively onboarding and
retaining new developers. In 2025, UnitaryHACK brought multiple new
compiler passes and features to UCC from external contributors who
continue to be active in the community. For larger projects, the Unitary
Foundation microgrant program provides \$4,000 in funding. This
initiative has already awarded over 100 grants across more than 30
countries, leading to a significant number of research publications, new
software libraries, and active contributors.

By leveraging our broad view of the ecosystem, we encourage grant
applicants to contribute to existing toolkits like UCC rather than
starting from scratch. These efforts, combined with a collaborative
Discord community of over 5,000 members, firmly embed UCC within a
thriving global quantum open-source community that values equitable
recognition and long-term project stewardship..

# Results

We demonstrate progress toward our primary goals by showcasing UCC's
competitive performance (G1) against established compilers and its early
demonstrations as an interoperable and community-extensible compilation
hub (G3, G4). While our work towards early FTQC-specific capabilities
(G2) and cross-hardware support is ongoing , these results establish a
strong foundation for future development.

## Competitive Performance

A core requirement (G1) for UCC is that its focus on user-friendliness
and interoperability must not come at the cost of performance. To
validate this, we benchmarked UCC's default compilation pipeline against
other leading open-source compilers using the `ucc-bench` suite
introduced previously.

![Benchmark comparison of top compiler performance on six representative
circuits (QAOA, QV, QFT, square-Heisenberg, Prep-Select, and QCNN). (a)
Log--log scatter of wall-clock compile time. Circuit names are annotated
near the UCC points, where other compile results for that circuit are at
the same x-coordinate. (b) Scatter of compiled-ratio, which is the ratio
of two-qubit gates in the compiled circuit over the original circuit. In
both plots, points above the diagonal are worse performance than UCC and
points below are
better.](latest_compiler_benchmarks_comparative_ucc.pdf){#fig:performance
width="\\textwidth"}

Benchmark circuits were chosen as a small suite of common quantum
algorithms: quantum approximate optimization algorithm (QAOA), quantum
fourier transform (QFT), quantum volume (QV), a quantum convolutional
neural network (QCNN), and a Heisenberg spin model on a square lattice.
These are circuits are over 100 qubits and drawn from other benhmarking
libraries [@Sawaya2024hamliblibraryof; @benchpress_2025; @qasmbench] or
built within the ucc-bench codebase. For these circuits, we track the
compilation time and the compiled ratio, which is the ratio of two-qubit
gates in the compiled circuit over the original circuit. Lower values
indicate better performance. This metric was chosen to capture the NISQ
era focus on reducing the use of the most error-prone/longer running
gates. All compilers target a basis gateset of $R_x$, $R_y$, $R_Z$, $H$
and $CNOT$ gates to ensure we have an apples-to-apples comparison of
circuit properties post compilation. UCC follows the documentation of
the respective compilers to set up the default configurations. This is
consistent with UCC's design philosophy is to make compiling easy and
painless for people running quantum algorithms, and not require the user
to have in-depth knowledge of compilation to get solid performance. This
means `pytket-peep` is tket with full peephole optimization,
`qiskit-default` is Qiskit's default transpilation with optimization
level 3, `cirq` uses a custom target gateset adaptor to ensure
consitency with other compilers. `pyqpanda3` is a performant but
closed-source compiler included for reference.

Figure [2](#fig:performance){reference-type="ref"
reference="fig:performance"} shows the compile time (left) and the
compiled ratio (right) from the benchmarks. The x-axis of each point is
the respective metric for UCC and the y-axis is the metric for the other
compiler. Points above (below) the diagonal are worse (better)
performance than UCC. We see UCC has strong performance in both metrics
amongst open-source compilers. For compile times, UCC and Qiskit are
similar, but UCC has substantially better performance for the
long-running compilation of a quantum volume (QV) circuit. The compiled
ratio of most circuits is similar, but UCC stands out as best on the
most differentiated circuit QFT. As discussed earlier, UCC's default
compilation pipeline is a customized set of Qiskit passes, hence the
difference in performance between the tools even though UCC is built on
top of Qiskit.

## Community-Driven Contributions

Given UCC's initial bootstrapping appropach, one initial capability of
UCC lies in its role as a "meta-compiler"---a hub that integrates
diverse, specialized compilation techniques from across the ecosystem.
This capability directly addresses our goals of being user-friendly and
compatible (G3) and genuinely community-driven (G4).

A clear example of this is the integration of BQSKit [@bqskit_2021], a
powerful synthesis-based compiler, as a custom UCC pass. This
contribution, originating from an external community member during our
UnitaryHACK 2025 event, highlights the success of our model. As shown in
the snippet below, a user can invoke BQSKit's advanced synthesis
algorithms with a single line, without needing to learn the full BQSKit
API or handle complex circuit conversions.

::: minted
python from ucc.transpilers.ucc_bqskit import BQSKitTransformationPass
result = compile(circuit_to_compile,
custom_passes=\[BQSKitTransformationPass()\])
:::

An additional integration is with `mitiq`, a popular library for quantum
error mitigation [@mitiq] developed by the Unitary Foundation. A circuit
compiled with UCC can then be composed with error mitigation techniques
like zero noise extrapolation [@zne_2019]:

::: minted
python import ucc, mitiq

circuit = \... \# Your quantum circuit here

\# compilation compiled_circuit = ucc.compile(circuit,
target_device=\"ibmq_mumbai\")

\# Method that takes a circuit and returns \# a (noisy) expectation
value, e.g. via \# a Qiskit or Cirq simulation wrapper my_executor =
\...

\# Execute the compiled circuit with ZNE mitigated_result =
mitiq.zne.execute( compiled_circuit, executor=my_executor,
scale_noise=mitiq.zne.scaling.fold_gates_at_random )
:::

![The impact of ZNE on pre- and post-compiled circuits which simulate
the Heisenberg model on a square lattice. The circuit acts on 8 qubits,
and contains 241 layers with 144 two-qubit gates. The error model used
is depolarizing noise impacting two-qubit gates with a noise rate of
1%.](ucc_mitiq.pdf){#fig:ucc_mitiq width="50%"}

Fig. [3](#fig:ucc_mitiq){reference-type="ref" reference="fig:ucc_mitiq"}
shows the result of running code like the above on a specific 9-qubit
circuit simulating the square Heisenberg Hamiltonian. Noise is simulated
as a depolarizing channel with $p=0.01$ after any two-qubit gate, given
that is the dominant source of noise on most hardware today. The graph
compares the expectation value of the all $0$ state for uncompiled vs
compiled circuits, and with and without zero noise extrapolation. The
noise-free expectation is the dashed line at 1. You can see the compiled
circuit is more robust to noise, as UCC was able to reduce the number of
two-qubit gates from 144 to 36. This combination of strong compilation
and error mitigation techniques is a powerful demonstration of UCC and
Mitiq's capabilities, and how they can be used to improve the
performance of quantum circuits on noisy hardware.

# Discussion & Outlook

This work has introduced UCC, outlined its architecture, collaborative
development framework, distinctive capabilities, and design philosophy.
The result in Section [5](#results){reference-type="ref"
reference="results"} underscore our core thesis: an open,
community-driven approach yields a high-performance, interoperable
compiler.

Looking forward, our research trajectory focuses on three strategic
thrusts to continue to improve in these areas alongside growing
capabilities in (G2). First, building upon our established
community-engagement initiatives, we plan to institute a rolling bounty
funding model for new compiler pass contributions to UCC, filling an
existing gap between short-term issues during events such as UnitaryHACK
and longer-term microgrant projects. Second, we will spur on strategic
collaboration with the broader quantum ecosystem to develop and expand
*intermediate representations* (IRs) that capture critical physical and
logical abstractions across the compilation stack. Such IRs should
enable efficient handling of hardware-specific quantum classical and
control, as well as resource optimization across abstraction layers.
Third, we will expand our benchmarking circuit library to incorporate
*realistic workloads for early Fault-Tolerant Quantum Computing* (FTQC)
architectures, including explicit modeling of logical qubit operations,
syndrome extraction cycles, and hardware connectivity constraints. This
expansion will enable more meaningful evaluation of compilation
strategies under practical FTQC conditions, and allow us to test
compilation schemes which combine quantum error mitigation [@qem] with
quantum error correction, such as in [@Wahl_2023], and evaluate the
fault tolerance of transformed circuits, as in our experimental ucc-ft
library [@ucc-ft_2025].

We will continue our model of co-development, expanding UCC to include
hardware-targeted compiler passes, ensuring that the Unitary Compiler
Collection remains responsive to emerging hardware paradigms,
compilation techniques, and QEC codes, while keeping user-friendliness
and ease of contribution as central tenets. These coordinated advances
will position UCC as both a robust and performant compilation framework
and a collaborative research testbed for next-generation quantum
software ecosystems.

# Acknowledgments

This work is supported by the U.S. Department of Energy, Office of
Science, Office of Advanced Scientific Computing Research, Accelerated
Research in Quantum Computing under Award Numbers DE-SC0025336 and
DE-SC0020266 and National Science Foundation POSE Phase II under Award
Number 2303643.

We thank the Unitary Foundation team for their input, feedback, and
support.

[^1]: See [ucc github](https://github.com/unitaryfoundation/ucc) for
    source and documentation
