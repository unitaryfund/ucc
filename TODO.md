# UCC Repository TODO List

This document tracks issues and improvements identified during the comprehensive QA review. Each item is formatted as a GitHub Issue template for easy copy-paste into GitHub Issues.

---

## 🚨 Critical Priority Issues

### Issue #1: Critical Syntax Error in compile.py

**Title:** Fix syntax error in Python version warning message

**Labels:** `bug`, `critical`, `high-priority`

**Description:**
There's a syntax error in `/ucc/compile.py` at line 23 that causes the Python version warning message to be malformed.

**Current code:**
```python
f"You are using Python) {current_major}.{current_minor}."
#                     ^ Extra closing parenthesis
```

**Expected behavior:**
The warning message should display correctly without syntax errors.

**Steps to reproduce:**
1. Import the ucc module with a Python version outside 3.12-3.13
2. Observe the malformed warning message

**Proposed solution:**
Remove the extra closing parenthesis:
```python
f"You are using Python {current_major}.{current_minor}."
```

**Files affected:**
- `ucc/compile.py` (line 23)

---

### Issue #2: Incomplete property implementation in UCCDefault1

**Title:** Complete the default_passes property implementation

**Labels:** `bug`, `critical`, `enhancement`

**Description:**
The `default_passes` property in `UCCDefault1` class is incomplete and always returns `None`, which may cause issues for users expecting pass information.

**Current code:**
```python
@property
def default_passes(self):
    return  # This returns None implicitly
```

**Expected behavior:**
The property should return meaningful information about the default passes or be removed if not needed.

**Proposed solution:**
Either implement the property to return the actual default passes or remove it if it's not needed:
```python
@property
def default_passes(self):
    return [
        Optimize1qGatesDecomposition,
        CommutativeCancellation,
        Collect2qBlocks,
        # ... other default passes
    ]
```

**Files affected:**
- `ucc/transpilers/ucc_defaults.py` (lines 59-60)

---

## 🔧 High Priority Issues

### Issue #3: Add comprehensive type hints throughout codebase

**Title:** Add type hints to improve code maintainability and IDE support

**Labels:** `enhancement`, `code-quality`, `high-priority`

**Description:**
The codebase lacks comprehensive type annotations, making it harder to maintain and reducing IDE support quality.

**Current state:**
- Main `compile()` function lacks parameter and return type hints
- `UCCDefault1` class methods are missing type annotations
- Test files have no type hints

**Expected behavior:**
All public functions and methods should have proper type hints for parameters and return values.

**Proposed solution:**
Add type hints systematically:
```python
from typing import Optional, Set, List, Any, Union
from qiskit import QuantumCircuit
from qiskit.transpiler import Target

def compile(
    circuit: Any,
    return_format: str = "original",
    target_gateset: Optional[Set[str]] = None,
    target_device: Optional[Target] = None,
    custom_passes: Optional[List] = None,
) -> Any:
    # ... implementation
```

**Files affected:**
- `ucc/compile.py`
- `ucc/transpilers/ucc_defaults.py`
- `ucc/transpilers/ucc_bqskit.py`
- Test files

---

### Issue #X: Fix complex-to-float fidelity comparisons

**Title:** Use absolute value for complex fidelity comparisons

**Labels:** `bug`, `high-priority`

**Description:**
`np.vdot(...)` returns a complex number but is compared directly to a float threshold, which can raise or behave unexpectedly.

**Files affected:**
- `ucc/transpilers/aqc/__init__.py`
- `ucc/transpilers/aqc/mps_sequential.py`

**Proposed solution:**
Wrap comparisons and logs with `np.abs(...)`.

---

### Issue #X: Use computed target basis during pre-translation

**Title:** Use `UCCDefault1.target_basis` for basis translation

**Labels:** `bug`, `high-priority`

**Description:**
`ucc/compile.py` uses `target_gateset` instead of the computed `target_basis`, ignoring defaults.

**Files affected:**
- `ucc/compile.py`

**Proposed solution:**
`basis_gates=ucc_default1.target_basis`.

---

### Issue #X: Fix nested tests not discovered by PyTest

**Title:** Unindent nested tests to module level

**Labels:** `testing`, `bug`, `high-priority`

**Description:**
Two tests are defined inside another test function and won’t be collected.

**Files affected:**
- `ucc/tests/test_compile.py`

**Proposed solution:**
Move `test_compile_target_device_opset` and `test_compile_target_device_coupling_map` to top-level.

---

### Issue #X: Fix backend option validation logic

**Title:** Correct option validation in `Mybackend.run`

**Labels:** `bug`, `high-priority`

**Description:**
Uses `hasattr(kwarg, self.options)` which is inverted and incorrect.

**Files affected:**
- `ucc/tests/mock_backends.py`

**Proposed solution:**
Use `if kwarg not in self.options:` or `if not hasattr(self.options, kwarg):`.

---

### Issue #4: Add input validation to compile function

**Title:** Add robust input validation and error handling to compile function

**Labels:** `enhancement`, `robustness`, `high-priority`

**Description:**
The main `compile()` function lacks input validation, which could lead to cryptic errors when users pass invalid arguments.

**Current state:**
- No validation for circuit input type
- No validation for target_gateset format
- No graceful handling of qBraid translation failures

**Expected behavior:**
- Clear error messages for invalid inputs
- Type checking for parameters
- Graceful error handling with helpful messages

**Proposed solution:**
```python
def compile(circuit, return_format="original", target_gateset=None, target_device=None, custom_passes=None):
    # Validate circuit input
    if circuit is None:
        raise ValueError("Circuit cannot be None")
    
    # Validate target_gateset
    if target_gateset is not None and not isinstance(target_gateset, (set, list)):
        raise TypeError("target_gateset must be a set or list of gate names")
    
    # Validate return_format
    valid_formats = supported_circuit_formats + ["original"]
    if return_format not in valid_formats:
        raise ValueError(f"return_format must be one of {valid_formats}")
    
    # ... rest of implementation with try-catch blocks
```

**Files affected:**
- `ucc/compile.py`

---

### Issue #5: Add comprehensive error handling for edge cases

**Title:** Improve error handling throughout the codebase

**Labels:** `enhancement`, `robustness`, `high-priority`

**Description:**
Several functions lack proper error handling, which can lead to cryptic error messages and poor user experience.

**Areas needing improvement:**
1. qBraid translation failures
2. Qiskit transpilation errors  
3. BQSKit compilation failures
4. Memory allocation issues in AQC

**Expected behavior:**
- Clear, actionable error messages
- Graceful degradation where possible
- Proper exception types

**Proposed solution:**
Add try-catch blocks with meaningful error messages:
```python
try:
    qiskit_circuit = translate(circuit, "qiskit")
except Exception as e:
    raise RuntimeError(f"Failed to translate circuit to Qiskit format: {str(e)}") from e
```

**Files affected:**
- `ucc/compile.py`
- `ucc/transpilers/ucc_bqskit.py`
- `ucc/transpilers/aqc/__init__.py`

---

## 🔐 Medium Priority Security Issues

### Issue #6: Improve error message handling to prevent information disclosure

**Title:** Sanitize error messages to prevent information disclosure

**Labels:** `security`, `medium-priority`

**Description:**
Verbose error messages in AQC compilation expose internal system information like memory calculations that could be used for fingerprinting.

**Current issue:**
```python
f"Required_memory: {required_memory} GB \n"
f"Available memory to allocate to storing statevector IR: {available_memory} GB \n\n"
```

**Security concern:**
Exposing detailed memory information could help attackers understand system capabilities.

**Proposed solution:**
Provide less detailed error messages by default, with verbose mode as an option:
```python
if verbose:
    # Show detailed memory info
else:
    warnings.warn("Insufficient memory for statevector simulation")
```

**Files affected:**
- `ucc/transpilers/aqc/__init__.py`

---

### Issue #X: Declare missing dependency `psutil`

**Title:** Add `psutil` to runtime dependencies or guard import

**Labels:** `bug`, `packaging`, `medium-priority`

**Description:**
`psutil` is used for memory checks but isn’t declared.

**Files affected:**
- `pyproject.toml`
- `ucc/transpilers/aqc/mps_utils.py`

**Proposed solution:**
Add to `[project].dependencies` or make AQC memory check optional with guarded import.

---

### Issue #X: Guard optional `quick.circuit.QiskitCircuit` import

**Title:** Ensure `qmprs` path dependencies are present

**Labels:** `bug`, `packaging`, `medium-priority`

**Description:**
`qmprs_compiler.py` imports `quick.circuit.QiskitCircuit` which may not be present unless provided by `qmprs`.

**Files affected:**
- `ucc/transpilers/aqc/qmprs_compiler.py`

**Proposed solution:**
Confirm it’s part of `qmprs` or add an optional extra; otherwise guard import and raise helpful error.

---

### Issue #7: Add explicit user consent for fallback behavior

**Title:** Require explicit consent for AQC fallback to vanilla implementation

**Labels:** `security`, `enhancement`, `medium-priority`

**Description:**
The AQC compilation silently falls back to vanilla implementation when `qmprs` is not available, which could be unexpected behavior.

**Current behavior:**
Automatic fallback with only a warning message.

**Security/UX concern:**
Users might not realize they're getting different behavior than expected.

**Proposed solution:**
Add a parameter to control fallback behavior:
```python
def approx_compile(circuit: QuantumCircuit, allow_fallback: bool = False) -> QuantumCircuit:
    if not qmprs_available:
        if not allow_fallback:
            raise ImportError("qmprs not available and fallback not allowed")
        warnings.warn("Falling back to vanilla sequential encoding")
```

**Files affected:**
- `ucc/transpilers/aqc/__init__.py`
- `ucc/transpilers/aqc/mps_pass.py`

---

## 🧪 Medium Priority Testing Issues

### Issue #8: Add comprehensive error condition tests

**Title:** Add test cases for error conditions and edge cases

**Labels:** `testing`, `enhancement`, `medium-priority`

**Description:**
The test suite lacks coverage for error conditions, which could hide bugs in error handling code.

**Missing test cases:**
- Invalid circuit inputs to `compile()`
- Network failures during qBraid operations
- Memory allocation failures
- Invalid target_gateset values
- BQSKit compilation failures

**Proposed solution:**
Add a new test file `test_error_conditions.py`:
```python
def test_compile_with_none_circuit():
    with pytest.raises(ValueError, match="Circuit cannot be None"):
        compile(None)

def test_compile_with_invalid_target_gateset():
    circuit = QuantumCircuit(2)
    with pytest.raises(TypeError, match="target_gateset must be"):
        compile(circuit, target_gateset="invalid")
```

**Files to create:**
- `ucc/tests/test_error_conditions.py`

**Files to modify:**
- Existing test files to add error condition coverage

---

### Issue #9: Fix potential import error in test_compile.py

**Title:** Fix conditional import of MPSPass in tests

**Labels:** `testing`, `bug`, `medium-priority`

**Description:**
The test file imports `MPSPass` unconditionally, which could fail if AQC dependencies are not available.

**Current code:**
```python
from ucc.transpilers.aqc.mps_pass import MPSPass
```

**Issue:**
This import could fail in environments where AQC dependencies are not installed.

**Proposed solution:**
Make the import conditional and skip tests if not available:
```python
try:
    from ucc.transpilers.aqc.mps_pass import MPSPass
    mps_available = True
except ImportError:
    mps_available = False

@pytest.mark.skipif(not mps_available, reason="MPS pass not available")
def test_compile_with_mps_pass(N):
    # ... test implementation
```

**Files affected:**
- `ucc/tests/test_compile.py`

---

## 🔧 Low Priority Code Quality Issues

### Issue #10: Convert magic numbers to named constants

**Title:** Replace magic numbers with named constants

**Labels:** `code-quality`, `enhancement`, `low-priority`

**Description:**
The codebase contains several magic numbers that should be named constants for better maintainability.

**Examples:**
- `0.8` - fidelity threshold in AQC compilation
- `4` - max_iterations in SabreLayout
- `20` - default trial counts
- `1` - local_iterations default

**Proposed solution:**
Create a constants file:
```python
# ucc/constants.py
DEFAULT_AQC_FIDELITY_THRESHOLD = 0.8
DEFAULT_SABRE_MAX_ITERATIONS = 4
DEFAULT_SABRE_TRIALS = 20
DEFAULT_LOCAL_ITERATIONS = 1
DEFAULT_GATESET = {"cx", "rz", "rx", "ry", "h"}
```

**Files to create:**
- `ucc/constants.py`

**Files to modify:**
- `ucc/transpilers/aqc/__init__.py`
- `ucc/transpilers/ucc_defaults.py`

---

### Issue #X: Remove unused `default_passes` property

**Title:** Remove or implement `UCCDefault1.default_passes`

**Labels:** `cleanup`, `low-priority`

**Description:**
Property returns `None` and is unused; creates confusion.

**Files affected:**
- `ucc/transpilers/ucc_defaults.py`

**Proposed solution:**
Remove the property or return a meaningful list.

---

### Issue #X: Align comment with memory check behavior

**Title:** Fix comment/code mismatch in AQC memory check

**Labels:** `documentation`, `low-priority`

**Description:**
Comment says “Use half of the memory available,” but code doesn’t halve available memory.

**Files affected:**
- `ucc/transpilers/aqc/mps_utils.py`

**Proposed solution:**
Either halve the available memory in code or update the comment.

---

### Issue #11: Clean up unused imports

**Title:** Remove unused imports throughout codebase

**Labels:** `code-quality`, `cleanup`, `low-priority`

**Description:**
Several files contain unused imports that should be removed for cleaner code.

**How to identify:**
Use `ruff` or similar tools to identify unused imports:
```bash
ruff check --select F401
```

**Expected outcome:**
All imports should be used or removed.

**Files likely affected:**
- Most Python files in the project

---

### Issue #12: Improve docstring coverage and consistency

**Title:** Add comprehensive docstrings to all public functions

**Labels:** `documentation`, `enhancement`, `low-priority`

**Description:**
Many functions lack docstrings or have inconsistent documentation format.

**Current state:**
- Some functions have good docstrings
- Others have minimal or no documentation
- Inconsistent format across files

**Proposed solution:**
Use consistent Google-style docstrings:
```python
def example_function(param1: int, param2: str) -> bool:
    """Brief description of the function.

    Longer description if needed.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is negative.
    """
```

**Files affected:**
- All Python files with public functions

---

## 📊 Infrastructure Improvements

### Issue #13: Add dependency security scanning

**Title:** Add automated dependency vulnerability scanning

**Labels:** `security`, `infrastructure`, `enhancement`

**Description:**
Add automated scanning for known vulnerabilities in dependencies.

**Proposed solution:**
Add a GitHub Action for dependency scanning:
```yaml
- name: Run safety check
  run: uv run safety check

- name: Run bandit security linter
  run: uv run bandit -r ucc/
```

**Files to create:**
- `.github/workflows/security.yml`

**Dependencies to add:**
- `safety`
- `bandit`

---

### Issue #14: Improve CI/CD pipeline with additional checks

**Title:** Enhance CI pipeline with more quality checks

**Labels:** `infrastructure`, `enhancement`, `low-priority`

**Description:**
Add additional quality checks to the CI pipeline.

**Proposed additions:**
- Type checking with `mypy`
- Import sorting with `isort`
- Complexity analysis
- Documentation building tests

**Files to modify:**
- `.github/workflows/test.yml`

---

## 📝 Documentation Improvements

### Issue #15: Add API reference documentation

**Title:** Generate comprehensive API documentation

**Labels:** `documentation`, `enhancement`, `low-priority`

**Description:**
Create comprehensive API documentation using Sphinx autodoc.

**Proposed solution:**
- Set up Sphinx autodoc properly
- Add docstrings to all public APIs
- Generate HTML documentation
- Add examples for each major function

**Files to create/modify:**
- `docs/source/api.rst`
- Various documentation files

---

## Usage Instructions

1. **Copy individual issues** from this document to create GitHub Issues
2. **Assign appropriate labels** as suggested
3. **Set milestones** based on priority levels
4. **Create branches** for each issue following naming convention: `issue-{number}-brief-description`
5. **Make focused PRs** that address single issues
6. **Update this document** as issues are resolved

## Priority Guidelines

- **🚨 Critical**: Fix immediately, these break functionality
- **🔧 High Priority**: Address in next release cycle
- **🔐 Security**: Address based on risk assessment
- **🧪 Testing**: Important for long-term stability
- **📊 Infrastructure**: Improve development workflow
- **📝 Documentation**: Enhance user experience

---

*Generated from QA review on 2025-08-29*
