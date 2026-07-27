# Connectivity-Aware Spectral Quantum Compiler

> A topology- and calibration-aware compiler that maps quantum-circuit interaction structure onto suitable regions of real quantum hardware before Qiskit performs its final routing, translation, and optimization.

---

## Core idea

Both the logical circuit and the physical hardware are represented as weighted graphs (logical qubit interactions and calibration-aware coupler costs, respectively). The compiler embeds each graph into a comparable geometric space using the graph Laplacian and space-filling curves (Hilbert/Morton), then uses that shared geometry as a global locality prior during placement and routing — prioritizing hardware connectivity and calibration quality first, with spectral/curve locality as a tie-breaker.

## Compilation modes

| Mode | Pipeline |
|---|---|
| Baseline | Qiskit optimization level 3 |
| Hybrid | Spectral layout → SABRE routing → Qiskit level 3 |
| Custom | Spectral layout → custom routing → Qiskit translation + level 3 |

---

## Development plan

| Phase | Scope | Status |
|---|---|---|
| 1 | Hardware graph construction and calibration-aware edge costs | ✅ Done |
| 2 | Shortest-path distances, spectral embedding, curve ordering, hardware metric | ✅ Done |
| 3 | Logical interaction graph, initial placement, Qiskit layout pass | ✅ Done |
| 4 | Routing state, SWAP scoring, router, Qiskit routing pass | ✅ Done |
| 5 | Full pipeline integration, equivalence checks, benchmarks | 🔄 In progress |

---

## Benchmarks

Circuit families: local lattice (Ising, Heisenberg, nearest-neighbor random), optimization (QAOA, MaxCut, HUBO/QUBO), chemistry (hardware-efficient ansätze, UCC), Fourier/arithmetic (QFT, phase estimation, adders), and random controls (Clifford, quantum-volume-style).

Metrics: native two-qubit gate count, SWAP count, circuit depth, estimated accumulated hardware error, compilation time, layout objective value, and stability across transpiler seeds.

---

## Latest results

**Source:** IBM Runtime
**Backend:** `ibm_fez`
**Qubits:** 156

| Case | Baseline depth | Spectral depth | Baseline 2Q | Spectral 2Q |
| --- | ---: | ---: | ---: | ---: |
| random-3q | 5 | 5 | 0 | 0 |
| random-5q | 66 | 120 | 27 | 49 |
| qft-3q | 32 | 94 | 9 | 25 |
| qft-5q | 99 | 173 | 30 | 70 |
| efficient-su2-3q | 30 | 90 | 6 | 25 |
| real-amplitudes-3q | 29 | 85 | 6 | 25 |
| qaoa-ring-3q | 31 | 94 | 7 | 27 |
| draper-adder-2q | 41 | 79 | 11 | 26 |

Full report: [`ucc/benchmark_results/2026-07-23T224629-ibm_fez.md`](ucc/benchmark_results/2026-07-23T224629-ibm_fez.md)

---

## Research questions

Does spectral placement reduce routing cost across circuit families, and which structures benefit most? Does calibration-aware geometry improve estimated execution fidelity? Is the benefit driven by layout or routing? Does Hilbert ordering outperform Morton for typical topologies? How sensitive is the method to calibration changes, and when does it complement or outperform Qiskit level 3?
