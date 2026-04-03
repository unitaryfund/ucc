# UCC 100k-Gate Structured Circuit Optimization Report

## 1. Project Goal
`ucc` (Unitary Compiler Collection) is intended to provide a unified compilation interface across different quantum circuit frontends and target backends.

In practice, the project is not trying to build a completely new low-level compiler stack from scratch. Instead, it wraps:
- qBraid-based cross-framework circuit conversion,
- Qiskit-based compilation and transpilation,
- target backend / target gateset constraints,
- and custom pass extensibility,

into a single compilation interface.

In short, the project aims to provide:
- a unified compilation entry point,
- a default optimization pipeline,
- multi-frontend compatibility,
- backend / gateset targeting,
- and pluggable optimization passes.

## 2. Initially Observed Problem
The main issue discovered in the project was not simple breakage, but an algorithmic weakness in the default compilation strategy for large structured circuits.

The core problems were:
- basis lowering happened too early, destroying higher-level structure;
- the default flow relied mostly on local rewrite / synthesis behavior, with limited structural awareness.

As a result, the compiler often failed to detect global cancellation opportunities such as:
- `U` followed by `U†`,
- repeated structured blocks,
- commuting inverse chains.

Instead of simplifying structured circuits, the compiler often expanded them dramatically.

This was most obvious on `QFT + inverse-QFT`, but the same issue also affected large ring-style layered circuits.

## 3. Initial 100k-Gate Results
Three structured circuits of exactly `100,000` gates were used as benchmarks.

| Circuit | Input Gates | Output Gates | Input Depth | Output Depth | Input 2Q Gates | Output 2Q Gates | Compile Time |
|---|---:|---:|---:|---:|---:|---:|---:|
| QFT + inverse-QFT | 100,000 | 1,049,611 | 33,324 | 239,924 | 83,300 | 146,612 | 6.78 s |
| QAOA-like Ring | 100,000 | 290,092 | 62,000 | 170,189 | 40,000 | 39,940 | 1.75 s |
| Basis-Friendly Ring | 100,000 | 290,321 | 62,000 | 170,425 | 40,000 | 39,940 | 1.68 s |

### Interpretation of the Initial Results
- `QFT + inverse-QFT` showed catastrophic regression: a highly cancellable circuit expanded to more than `1.0M` gates.
- Both ring circuits also regressed badly: total gate count and depth increased sharply, while the 2-qubit gate count barely improved.
- This showed that the original default pipeline behaved more like a local rewrite system than a large-circuit optimizer.

## 4. Optimization Process
The fix was not based on simply adding a heavier optimizer. Instead, the compiler was improved in stages using structure-aware logic.

### Stage 1: Anti-regression guard
A conservative structural cost model was introduced to compare candidate outputs and reject obviously worse results.

This solved one immediate issue:
- the compiler should at least avoid returning a circuit that is clearly worse.

However, this alone did not add structural understanding. It only blocked catastrophic regressions.

### Stage 2: Structural pre-simplification
A pre-simplification step was added before basis lowering, so that high-level cancellations could be exploited before the circuit was aggressively decomposed.

The first effective rule was:
- `CommutativeInverseCancellation`

This was important because many cancellation opportunities become much harder to recover after decomposition.

### Stage 3: Repeated-block optimization
Next, repeated-block reuse was introduced:
- detect repeated prefix blocks,
- optimize a single instance of the block,
- reuse the optimized result across all repetitions.

This significantly reduced redundant work on repeated structured circuits.

### Stage 4: More general block matching
Finally, more general structural rules were added:
- repeated block run detection at arbitrary positions,
- whole-block removal for adjacent inverse blocks.

To avoid turning preprocessing into a bottleneck, the implementation was split into fast and general paths:
- very large circuits prefer the prefix fast path,
- more expensive general block scans are only enabled for moderate-size circuits.

## 5. Final 100k-Gate Results
After the structural optimization layers were added, the same `100,000`-gate benchmarks were rerun.

| Circuit | Input Gates | Output Gates | Input Depth | Output Depth | Input 2Q Gates | Output 2Q Gates | Compile Time |
|---|---:|---:|---:|---:|---:|---:|---:|
| QFT + inverse-QFT | 100,000 | 0 | 33,324 | 0 | 83,300 | 0 | 0.45 s |
| QAOA-like Ring | 100,000 | 99,858 | 62,000 | 61,933 | 40,000 | 39,940 | 5.21 s |
| Basis-Friendly Ring | 100,000 | 79,960 | 62,000 | 60,940 | 40,000 | 39,940 | 5.51 s |

## 6. Result Comparison
Compared with the initial version, the current compiler has fixed the major algorithmic regression on structured `100k`-gate workloads.

The key differences are:

### QFT + inverse-QFT
- Initial: `100,000 -> 1,049,611`
- Final: `100,000 -> 0`
- Compile time also dropped from `6.78s` to `0.45s`

This means the compiler no longer destroys this structure. It now recognizes and cancels it directly.

### QAOA-like Ring
- Initial: expanded to `290,092` gates
- Final: reduced to `99,858` gates

So the default pipeline no longer damages this type of structured layered circuit. The output remains close to the original scale.

### Basis-Friendly Ring
- Initial: expanded to `290,321` gates
- Final: reduced to `79,960` gates

This shows that the current optimizer not only avoids regression, but can also deliver real compression when the circuit is already closer to the target basis.

## 7. Validation
After the optimization work, the full test suite was rerun.

- Final test result: `118 passed, 10 warnings`

The warnings are mainly due to optional dependencies not being installed (such as `qmprs`, `kahypar`, and `optuna/cmaes/nevergrad`), not functional failures.

## 8. Conclusion
The original problem in this project was not that it could not process large circuits, but that its default optimization strategy was structurally naive and therefore prone to severe expansion on structured workloads.

By adding:
- structural pre-simplification,
- repeated-block reuse,
- inverse-block cancellation,
- and a split between fast-path and general structural scans,

the current version has transformed the default pipeline from a regression-prone local rewrite flow into a much more reasonable optimizer for large structured circuits.
