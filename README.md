# Connectivity-Aware Spectral Quantum Compiler

> A topology- and calibration-aware compiler that maps quantum-circuit interaction structure onto suitable regions of real quantum hardware before Qiskit performs its final routing, translation, and optimization.

---

## Core idea

Both the logical circuit and the physical hardware are represented as weighted graphs. The compiler constructs comparable geometric representations of each using the graph Laplacian and space-filling curves, then uses those representations as a global locality prior during placement and routing.

### Logical interaction graph

```
vertices     = logical qubits
edges        = pairs of logical qubits that interact
edge weights = two-qubit gate count or estimated execution cost
```

### Hardware graph

```
vertices     = physical qubits
edges        = available two-qubit couplers
edge weights = calibration-aware routing cost (hop + error + duration)
```

---

## Hardware geometry pipeline

```
coupling graph
    → calibration-aware edge costs  [hop_weight × hop + error_weight × -log(1-e) + duration_weight × t/t₀]
    → all-pairs shortest-path distances
    → affinity matrix               [exp(-cost / sigma)]
    → normalized graph Laplacian    [L = D - W]
    → spectral coordinates          [first k non-trivial eigenvectors]
    → integer grid normalization
    → Hilbert (2-D) or Morton (n-D) curve order
```

---

## Compilation modes

| Mode | Pipeline |
|---|---|
| Baseline | Qiskit optimization level 3 |
| Hybrid | Spectral layout → SABRE routing → Qiskit level 3 |
| Custom | Spectral layout → custom routing → Qiskit translation + level 3 |

---

## Routing priority

```
1. actual hardware connectivity
2. reduction in shortest-path distance
3. calibration-aware path quality
4. upcoming (lookahead) interactions
5. spectral or curve locality
```

---

## Development plan

| Phase | Scope | Status |
|---|---|---|
| 1 | Hardware graph construction and calibration-aware edge costs | ✅ Done |
| 2 | Shortest-path distances, spectral embedding, curve ordering, hardware metric | 🔄 In progress |
| 3 | Logical interaction graph, initial placement, Qiskit layout pass | ⬜ Planned |
| 4 | Routing state, SWAP scoring, router, Qiskit routing pass | ⬜ Planned |
| 5 | Full pipeline integration, equivalence checks, benchmarks | ⬜ Planned |

---

## Software layout

```
ucc/custom_passes/spectral/
├── graph.py                   ✅ undirected adjacency from coupling map
├── calibration.py             ✅ calibration-aware edge costs
│
├── hardware/
│   ├── distances.py           all-pairs hop and weighted distances
│   ├── embedding.py           Laplacian, affinity, spectral coordinates
│   ├── curves.py              Hilbert and Morton curve ordering
│   └── hardware_metric.py     HardwareMetric composite object
│
├── layout/
│   ├── logical_graph.py       weighted interaction graph from circuit
│   ├── placement.py           curve-rank pairing and layout scoring
│   └── layout_pass.py         Qiskit AnalysisPass wrapper
│
├── routing/
│   ├── routing_state.py       logical-to-physical mapping and front layer
│   ├── swap_scoring.py        SWAP candidate scoring
│   ├── router.py              interaction-sequence router
│   └── routing_pass.py        Qiskit TransformationPass wrapper
│
└── pipeline/
    └── passes.py              PassManager builders for all three modes
```

---

## Benchmark circuit families

- **Local lattice**: Ising, Heisenberg, nearest-neighbor random
- **Optimization**: QAOA, MaxCut, HUBO/QUBO
- **Chemistry**: hardware-efficient ansätze, UCC circuits
- **Fourier/arithmetic**: QFT, phase estimation, adders
- **Random controls**: Clifford, quantum-volume-style

---

## Evaluation metrics

- native two-qubit gate count
- SWAP count (pre-basis-translation)
- circuit depth
- estimated accumulated hardware error
- compilation time
- layout objective value
- stability across transpiler seeds

---

## Research questions

1. Does spectral placement reduce routing cost across circuit families?
2. Which circuit structures benefit most?
3. Does calibration-aware geometry improve estimated execution fidelity?
4. Is the primary benefit from layout or routing?
5. Does Hilbert ordering outperform Morton for typical hardware topologies?
6. How sensitive is the method to calibration changes?
7. When does the method complement or outperform Qiskit level 3?
