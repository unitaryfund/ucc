Changelog
=========

[0.4.2] - 2025-01-17
--------------------

Version 0.4.2 marks the first formal release to [PyPI](https://pypi.org/project/ucc/) of the Unitary Compiler Collection (UCC), a Python library for frontend-agnostic, high performance compilation of quantum circuits.

This release contains the default UCC compilation workflow, including circuit translation and optimization passes, pass management, and the user interface.
It also encompasses benchmarking scripts and utilities, tests, documentation, and basic infrastructure.

### Added
- PyPI release #165 [@Misty-W]
- Add RTD for online documentation #164 [@natestemen]
- Create contribution guide #157 [@natestemen]
- Plot compiler versions over time on graph #145 [@jordandsullivan]
- Add platform info to header #144 [@jordandsullivan]
- Speed up Github benchmarks #140 [@]
- Test GitHub actions for benchmarking pipeline #129 [@jordandsullivan]
- Save compiler versions with data #123 [@]
- Generate plot via GitHub actions pipeline #114 [@jordandsullivan]
- Clean up unnecessary files #101 [@jordandsullivan]
- Reorganize results files #97 [@jordandsullivan]
- Set up AWS workflow for benchmarking #93 [@jordandsullivan]
- Expand logical equivalence test #91 [@Misty-W]
- Add synthesis sequence that preserves natural gateset #89 [@Misty-W]
- Improve routing algorithm #85 [@Misty-W]
- Add benchmark for qubit mapping #83 [@Misty-W]
- Test to check that output circuits from ucc benchmarking are in the natural gate set #82 [@Misty-W]
- Reorganize code structure #70 [@Misty-W]
- Add expectation value benchmark #66 [@natestemen]
- benchmark script #64 [@jordandsullivan]
- Add Qiskit Optimization pass(es) that improve UCC gate reduction #60 [@Misty-W] 
- Run first hardware benchmarks #58 [@jordandsullivan]
- Create contribution guide for new transpiler passes #56 [@jordandsullivan]
- Create user guide #54 [@Misty-W]
- Display most recent benchmarks #53 [@jordandsullivan]
- Add CI/CD for tests #52 [@natestemen]
- Expand README with examples #51 [@jordandsullivan]
- Generate API guide with Sphinx #50 [@natestemen]
- Version release and changelog #47 [@natestemen]
- Separate qasm benchmark files from code to generate them #45 [@jordandsullivan]
- Profile code and triage speedups #44 [@jordandsullivan]
- Add tests to check logical equivalence of small circuits #35 [@natestemen]
- confirm licensing requirements #20 [@nathanshammah, @jordandsullivan]
- Non-quantum things to improve the robustness of our package, e.g. CI/CD #20 [@nathanshammah]
- Handle parameterized 1Q gates #19 [@sonikaj]
- Add qubit mapping pass #18 [@sonikaj]
- Docstrings for modified transpiler passes [@sonikaj]
- replace QuantumTranslator with qBraid.transpile #15 In unitaryfund/ucc [@jordandsullivan]
- Add a README #7 [@nathanshammah, @jordandsullivan]
- Add custom UCC transpiler code to ucc/ucc module #6 [@sonikaj]
- Add benchmarks #2 [@jordandsullivan]
- Choose a license #1 [@jordandsullivan]


### Fixed
- Install error due to openqasm versioning #154 [@Misty-W]
- fix small_test.sh CLI command to deal with spaces in paths #152 [@willzeng]
- Mismatched headers in datafiles #148 [@jordandsullivan]
- run-benchmarks action is failing on PRs #138 [@jordandsullivan]
- Fix cirq transformers import #126 [@jordandsullivan]
- RebaseTket function not compatible #118 [@jordandsullivan]
- qiskit blocks_to_matrix no longer imports #111 [@Misty-W]
- Shell script crashes computer #99 [@jordandsullivan]
- Compiled output circuit doesn't dump to OpenQASM 2.0 or 3.0 #80 [@Misty-W]
- Other qcs/quil install errors #75 [@willzeng]
- Hidden rust dependency on install #74 [@Misty-W]


### Removed
- Remove innaccurate data for multi-q gates #86 [@jordandsullivan]
- Remove QuantumTranslator references #23 [@jordandsullivan]
