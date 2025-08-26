# Changelog
<!-- Release notes generated using configuration in .github/release.yml at main -->

## [0.4.9] - 2025-08-26
[PyPI](https://pypi.org/project/ucc/0.4.9/) | [GitHub](https://github.com/unitaryfoundation/ucc/releases/tag/v0.4.9)
In version 0.4.9, we optimized the logic for target gateset selection, made infrastructure and documentation updates and upgraded dependencies.

### ✨ Key Features
* Fix links to research references in docs by @jordandsullivan in https://github.com/unitaryfoundation/ucc/pull/455
* Add codecov reporting by @bachase in https://github.com/unitaryfoundation/ucc/pull/465
* add codecov badge to readme by @jordandsullivan in https://github.com/unitaryfoundation/ucc/pull/467
* Test for Merit systems automation by @jordandsullivan in https://github.com/unitaryfoundation/ucc/pull/470
* Simplified and optimized logic for target gateset selection.  by @jordandsullivan in https://github.com/unitaryfoundation/ucc/pull/492
### 🔄 Dependencies
By @dependabot  
* pytket (2.7.0 → 2.9.1) via [#456](https://github.com/unitaryfoundation/ucc/pull/456) + [#458](https://github.com/unitaryfoundation/ucc/pull/458)  
* qbraid (0.9.7 → 0.9.8) via [#459](https://github.com/unitaryfoundation/ucc/pull/459)  
* cirq-core (1.5.0 → 1.6.1) via [#457](https://github.com/unitaryfoundation/ucc/pull/457) + [#487](https://github.com/unitaryfoundation/ucc/pull/487)  
* sphinxcontrib-bibtex (2.6.3 → 2.6.5) via [#472](https://github.com/unitaryfoundation/ucc/pull/472)  
* pytest (8.3.5 → 8.4.1) via [#473](https://github.com/unitaryfoundation/ucc/pull/473)  
* pytest-cov (6.1.1 → 6.2.1) via [#474](https://github.com/unitaryfoundation/ucc/pull/474)  
* quimb (1.11.1 → 1.11.2) via [#475](https://github.com/unitaryfoundation/ucc/pull/475)  
* ruff (0.11.7 → 0.12.10) via [#476](https://github.com/unitaryfoundation/ucc/pull/476) + [#483](https://github.com/unitaryfoundation/ucc/pull/483) + [#486](https://github.com/unitaryfoundation/ucc/pull/486) + [#494](https://github.com/unitaryfoundation/ucc/pull/494)  
* actions/checkout (4 → 5) via [#481](https://github.com/unitaryfoundation/ucc/pull/481)  
* actions/download-artifact (4 → 5) via [#482](https://github.com/unitaryfoundation/ucc/pull/482)  
* pre-commit (4.2.0 → 4.3.0) via [#484](https://github.com/unitaryfoundation/ucc/pull/484)  
* qiskit (2.1.1 → 2.1.2) via [#493](https://github.com/unitaryfoundation/ucc/pull/493)  


**Full Changelog**: https://github.com/unitaryfoundation/ucc/compare/v0.4.8...0.4.9

## [0.4.8] - 2025-07-17
[PyPI](https://pypi.org/project/ucc/0.4.8/) | [GitHub](https://github.com/unitaryfoundation/ucc/releases/tag/v0.4.8)

In v0.4.8, we've made documentation and workflow improvements based on feedback from [UnitaryHACK](https://unitaryhack.dev/) 2025.
### 📚 Documentation & Workflow Improvements
* Add intro video about UCC by @WingCode in https://github.com/unitaryfoundation/ucc/pull/431
* Add license badge to README by @jordandsullivan in https://github.com/unitaryfoundation/ucc/pull/438
* Add ucc logo by @jordandsullivan in https://github.com/unitaryfoundation/ucc/pull/439
* Ensure all pre-commit hook are validated in CI by @bachase in https://github.com/unitaryfoundation/ucc/pull/442
* README updates by @bachase in https://github.com/unitaryfoundation/ucc/pull/443
* Update release instructions to use automated Release tagging by @jordandsullivan in https://github.com/unitaryfoundation/ucc/pull/447
### 🔄  Dependencies
By @dependabot
* quimb (1.11.0 → 1.11.1) via  https://github.com/unitaryfoundation/ucc/pull/441
* qiskit (2.0.2 → 2.1.1) via https://github.com/unitaryfoundation/ucc/pull/440 + https://github.com/unitaryfoundation/ucc/pull/450
* pytket (2.6.0 → 2.7.0) via https://github.com/unitaryfoundation/ucc/pull/449

**Full Changelog**: https://github.com/unitaryfoundation/ucc/compare/v0.4.7...v0.4.8


## [0.4.7] - 2025-06-17
[PyPI](https://pypi.org/project/ucc/0.4.7/) | [GitHub](https://github.com/unitaryfoundation/ucc/releases/tag/v0.4.7)

In v0.4.7, we are celebrating a triumphant [UnitaryHACK](https://unitaryhack.dev/) 2025, with exciting new contributions from lovely new contributors -- and a whole slew of updates and improvements by the maintainers to support their work!

### ✨ Key Features
First external compiler pass port by new contributor @WolfLink 🔮: Integrated a gate-reducing pass from [BQSKit](https://github.com/BQSKit/bqskit) (#412).
New approximate compilation module by new contributor @ACE07-Sev 🎯 : Added MPS encoding support for circuit optimization (#421).

### 📚 Documentation & Workflow Improvements
Enhanced compiler customization docs (#391 by @Misty-W)
Added call-outs for reasearch using UCC (#405 @bachase)
Simplified New Compiler Pass proposal issue template (#373 by @jordandsullivan)
Migrated in-depth Compiler Pass proposal to Discussions (#372 + #378 by @jordandsullivan)
Added support for benchmarking automation on fork PRs (#402 by @bachase)
Added CHANGELOG to docs (#389 by @bachase)
Update `ucc.compile` docstring (#399 by @Misty-W)

### 🔄 Dependency Updates
By @dependabot...
qiskit (2.0.0 → 2.0.2) via [#363](https://github.com/unitaryfoundation/ucc/pull/363) + [#397](https://github.com/unitaryfoundation/ucc/pull/397)
pytket (2.4.1 → 2.6.0) via [#398](https://github.com/unitaryfoundation/ucc/pull/398) + [#409](https://github.com/unitaryfoundation/ucc/pull/409)
qiskit-qasm3-import (0.5.1 → 0.6.0) in [#424](https://github.com/unitaryfoundation/ucc/pull/424)
quimb (1.10.0 → 1.11.0) in [#425](https://github.com/unitaryfoundation/ucc/pull/425)
qbraid (0.9.5 → 0.9.7) in [#426](https://github.com/unitaryfoundation/ucc/pull/426)


### 👏 Community Spotlight
Huge thanks to all Unitary Hack 2025 participants and our new contributors!
* @ACE07-Sev made their first contribution in [#421](https://github.com/unitaryfoundation/ucc/pull/421)
* @WolfLink made their first contribution in [#412](https://github.com/unitaryfoundation/ucc/pull/412)
* @WingCode investigated methods of logical equivalence verification on large circuits in [#62](https://github.com/unitaryfoundation/ucc/issues/62)


Full changelog [here](https://github.com/unitaryfoundation/ucc/compare/v0.4.6...v0.4.7).


## [0.4.6] - 2025-04-16
[PyPI](https://pypi.org/project/ucc/0.4.6/) | [GitHub](https://github.com/unitaryfoundation/ucc/releases/tag/v0.4.6)

In version 0.4.6, we refactored the UCC benchmarking workflows and migrated them to a
standalone repository [ucc-bench](https://github.com/unitaryfoundation/ucc-bench). We updated the corresponding [documention](https://ucc.readthedocs.io/en/latest/benchmarking.html), adding details on the benchmarked circuits and compiler configurations. As part of this migration, benchmarks can be run on pending PRs to understand the performance implications of a change before merging. The results are posted as comments to the PR (see [here](https://github.com/unitaryfoundation/ucc/pull/359#issuecomment-2876701484) for an example). Going forward, changes related to benchmarking infrastructure will be primarily tracked in the [ucc-bench](https://github.com/unitaryfoundation/ucc-bench) repository.

In preparation for supporting compilation of dynamic circuits, we removed a previously default target gateset compiler pass, and instead added support for users to specify a target gateset to apply post-compilation.

We also started work on a fault tolerance checker based on [this](https://github.com/unitaryfoundation/ucc/discussions/344) discussion. We are developing the prototype in a separate [ucc-ft](https://github.com/unitaryfoundation/ucc-ft), and will track progress there until we reach a point to consider merging the functionality back into ucc.

We also migrated to [uv](https://docs.astral.sh/uv/) for package management, and enable Dependabot for upgrading dependencies.

## What's Changed
### Added
* Add workflow to trigger ucc-bench run by @bachase in https://github.com/unitaryfoundation/ucc/pull/327

### Changed
* Migrate to ucc-bench by @bachase in https://github.com/unitaryfoundation/ucc/pull/335
* Migrate to uv for package/project management by @bachase in https://github.com/unitaryfoundation/ucc/pull/347
* 338 dynamic circuits qec by @jordandsullivan in https://github.com/unitaryfoundation/ucc/pull/355
* 342 target gateset by @jordandsullivan in https://github.com/unitaryfoundation/ucc/pull/354
* Separate dependency updates in auto-generated release notes by @bachase in https://github.com/unitaryfoundation/ucc/pull/361

### Dependencies
* Bump astral-sh/setup-uv from 5 to 6 by @dependabot in https://github.com/unitaryfoundation/ucc/pull/351
* Bump actions/create-github-app-token from 1 to 2 by @dependabot in https://github.com/unitaryfoundation/ucc/pull/349
* Bump pytket from 2.3.1 to 2.4.1 by @dependabot in https://github.com/unitaryfoundation/ucc/pull/359

## [0.4.5] - 2025-04-15
[PyPI](https://pypi.org/project/ucc/0.4.5/) | [GitHub](https://github.com/unitaryfoundation/ucc/releases/tag/v0.4.5)

In version 0.4.5, we enabled plotting of relative errors on the simulated benchmarks and continued refinement of the expectation value benchmarking flow,
including the addition of a custom observable for QCNN circuits and adjustments in the applied gate error rates to reflect capabilities of current devices.

We also automated the pypi publishing workflow upon release, added support for Qiskit 2.0 along with other dependency upgrades,
and updated our infrastructure to reflect the GitHub rebranding of UCC's home organization, [Unitary Foundation](https://github.com/unitaryfoundation)

Thanks to our first external contributor @Shivansh20128 for improving UCC code and documentation!

### Added

- Add section on pypi publishing to dev docs #323. [@Misty-W]
- Re-enable expval benchmarks. #322 [@natestemen]
- Adding pypi version and download stats to readme. #318 [@Shivansh20128]
- Add manual trigger to PyPI publishing. #311 [@jordandsullivan]
- Add custom qcnn observable. #310 [@Misty-W]
- Create first draft of python-publish.yml. #309 [@jordandsullivan]

### Fixed

- Fix pytket version ranges. #331 [@bachase]
- Fix expval benchmark plotting script name. #324 [@natestemen]

### Changed

- Update dependencies (including to qiskit 2.0.0). #325 [@bachase]
- Use normalized relative error for expectation value benchmarking. #321 [@natestemen]
- Update GitHub organization name from unitaryfund to unitaryfoundation. #320 [@bachase]
- Using argparse to parse arguments. #319 [@Shivansh20128]
- Upgrade dependencies. #317 [@bachase]
- Use error rates reflecting current quantum devices #315 [@natestemen]


## [0.4.4] - 2025-03-13
[PyPI](https://pypi.org/project/ucc/0.4.4/) | [GitHub](https://github.com/unitaryfoundation/ucc/releases/tag/v0.4.4)

In version 0.4.4, we updated and expanded our documentation and streamlined benchmark data visualization. We also implemented more custom observables for our expectation value benchmarks, improved the user experience for adding custom transpiler passes, and switched to using the `FullPeepHoleOptimize` function to benchmark PyTKET based on feedback from the community!

### Added

- Enable repeat use of `UCCDefault1` and update documentation. #268 [@bachase]
- Support custom passes in `ucc.compile`. #301 [@bachase]
- Add note defining `pytket-peep` in README. #284 [@jordandsullivan]
- Add `dependabot` for automated dependency updates. #297 [@bachase]

### Fixed

- Improve reproducibility and consistency of benchmarking workflow. #253 [@bachase]
- Ensure `target_device` is used when specified, not just connectivity, when compiling. #290 [@bachase]

### Changed

- Change QAOA observable to use the problem Hamiltonian. #260 [@Misty-W]
- Switch PyTKET to use `FullPeepHoleOptimize`. #266 [@jordandsullivan]
- Adjust plotting scripts to change resolution to per release in time series plots. #254 [@Misty-W]
- Update Poetry lock file, Qiskit, and PyTKET versions. #294 [@jordandsullivan]
- Relabel Qiskit data in plots. #300 [@jordandsullivan]

### Removed

- Remove violin plots from benchmark visualizations. #282 [@jordandsullivan]
- Remove outdated README reference to custom transpiler passes. #274 [@jordandsullivan]
- Remove specific dated data from plots. #283 [@jordandsullivan]

## [0.4.3] - 2025-02-26
[PyPI](https://pypi.org/project/ucc/0.4.3/) | [GitHub](https://github.com/unitaryfoundation/ucc/releases/tag/v0.4.3)

In version 0.4.3, we enhanced UCC infrastructure, benchmarking, and documentation.
Release highlights include the introduction of
[Poetry](https://github.com/python-poetry/install.python-poetry.org) for dependency management,
the automated display of results from benchmarks run on the `main` branch,
and plotting of expectation value benchmark results.
In the case of quantum volume circuits, we changed the expectation value metric from the default
ZZZZZZZZZZZ observable to the heavy output probability.


### Added

- Mention benchpress explicitly in License section. #241 [@jordandsullivan]
- Add target gate set for cirq benchmarking #224 [@bachase]
- Add ruff for linting and formating #216 [@bachase]
- Added warnings to top level compile function for trying to import non-supported python versions #185 [@jordandsullivan]
- Add explicit Sphinx config in .readthedocs.yaml file #180 [@Misty-W]


### Fixed

- Ensure benchmarking runs don't add gitignored files #247 [@bachase]
- Pull latest compatible version of libraries when generating benchmark docker #244 [@bachase]
- Fix broken links in docs #240 [@bachase]
- Fix spelling mistake #237 [@natestemen]
- Fix relative path bug in expval benchmarking script #231 [@natestemen]
- Fix typo in readme for supported formats #230 [@bachase]
- Fix benchmark script to work with poetry #214 [@bachase]
- Combine recent data files w/ incomplete benchmarks #207 [@Misty-W]


### Changed

- Run pytest before ruff linter checks #267 [@jordandsullivan]
- Clarify poetry usage #265 [@bachase]
- Update Install Poetry link to instructions for installation #257 [@jordandsullivan]
- Upgrade dependencies #250 [@bachase]
- Change QV error rates back to global variables #248 [@Misty-W]
- Update documentation to expand on design goals: #245 [@bachase]
- Change expectation value metric to HOP for QV circuits #223 [@Misty-W]
- Switch to poetry for dependency management #208 [@bachase]
- Test run benchmarks with simple wording change #205 [@Misty-W]
- Wording #198 [@jordandsullivan]
- Test deploy key push access #197 [@jordandsullivan]
- Plot adjustments #183 by jordandsullivan
- Minor docs updates #181 by Misty-W
- Update README.md #178 by willzeng


### Removed

- Remove custom transpilation passes #256 [@bachase]


## [0.4.2] - 2025-01-17
[PyPI](https://pypi.org/project/ucc/0.4.2/) | [GitHub](https://github.com/unitaryfoundation/ucc/releases/tag/v0.4.2)

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
