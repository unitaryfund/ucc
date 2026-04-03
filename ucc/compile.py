from qbraid.programs.alias_manager import get_program_type_alias
from qbraid.transpiler import ConversionGraph
from qbraid.transpiler import transpile as translate
from qiskit import transpile as qiskit_transpile
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import CommutativeInverseCancellation
from .transpilers.ucc_defaults import UCCDefault1

import sys
import warnings

# Specify the supported Python version range
REQUIRED_MAJOR = 3
MINOR_VERSION_MIN = 12
MINOR_VERSION_MAX = 13

current_major = sys.version_info.major
current_minor = sys.version_info.minor

if current_major != REQUIRED_MAJOR or not (
    MINOR_VERSION_MIN <= current_minor <= MINOR_VERSION_MAX
):
    warnings.warn(
        f"Warning: This package is designed for Python {REQUIRED_MAJOR}.{MINOR_VERSION_MIN}-{REQUIRED_MAJOR}.{MINOR_VERSION_MAX}. "
        f"You are using Python {current_major}.{current_minor}."
    )
supported_circuit_formats = ConversionGraph().nodes()
_MAX_STRUCTURAL_BLOCK_SIZE = 256
_MIN_REPEATED_BLOCK_REPEATS = 4
_MAX_GLOBAL_STRUCTURAL_SCAN_SIZE = 50000


def _build_circuit_from_instructions(template_circuit, instructions):
    """Build a new circuit with the same registers from a list of instructions."""

    rebuilt_circuit = template_circuit.copy_empty_like()
    rebuilt_circuit.global_phase = template_circuit.global_phase
    for instruction in instructions:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )
    return rebuilt_circuit


def _normalize_param(param):
    """Return a hashable representation for instruction parameters."""

    if isinstance(param, (int, float)):
        return round(float(param), 12)
    return str(param)


def _instruction_signature(circuit, instruction):
    """Compute a stable signature for repeated-block detection."""

    return (
        instruction.operation.name,
        tuple(
            _normalize_param(param) for param in instruction.operation.params
        ),
        tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits),
        tuple(circuit.find_bit(clbit).index for clbit in instruction.clbits),
    )


def _inverse_instruction_signature(circuit, instruction):
    """Compute the signature of an instruction's inverse when available."""

    try:
        inverse_operation = instruction.operation.inverse()
    except Exception:
        return None

    return (
        inverse_operation.name,
        tuple(_normalize_param(param) for param in inverse_operation.params),
        tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits),
        tuple(circuit.find_bit(clbit).index for clbit in instruction.clbits),
    )


def _run_commutative_inverse_cancellation(circuit):
    """Run Qiskit's commutative inverse cancellation when supported."""

    try:
        return PassManager([CommutativeInverseCancellation()]).run(circuit)
    except Exception:
        return circuit


def _find_repeated_run(
    circuit,
    max_block_size=_MAX_STRUCTURAL_BLOCK_SIZE,
    min_repeats=_MIN_REPEATED_BLOCK_REPEATS,
):
    """Detect the largest repeated exact block anywhere in a circuit."""

    instruction_count = len(circuit.data)
    max_candidate_size = min(max_block_size, instruction_count // min_repeats)
    if max_candidate_size < 1:
        return None

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]
    best_match = None
    best_coverage = 0

    for block_size in range(1, max_candidate_size + 1):
        start_index = 0
        while start_index + min_repeats * block_size <= instruction_count:
            block = signatures[start_index : start_index + block_size]
            repeat_count = 1
            while (
                start_index + (repeat_count + 1) * block_size
                <= instruction_count
            ):
                candidate_start = start_index + repeat_count * block_size
                candidate_end = candidate_start + block_size
                if signatures[candidate_start:candidate_end] != block:
                    break
                repeat_count += 1

            coverage = repeat_count * block_size
            if repeat_count >= min_repeats and coverage > best_coverage:
                best_match = (start_index, block_size, repeat_count)
                best_coverage = coverage

            start_index += coverage if repeat_count > 1 else 1

    return best_match


def _find_repeated_prefix(circuit, max_block_size=256, min_repeats=4):
    """Detect the largest repeated exact prefix block in a circuit."""

    instruction_count = len(circuit.data)
    max_candidate_size = min(max_block_size, instruction_count // min_repeats)
    if max_candidate_size < 1:
        return None

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]
    best_match = None
    best_coverage = 0

    for block_size in range(1, max_candidate_size + 1):
        prefix = signatures[:block_size]
        repeat_count = 1
        while (repeat_count + 1) * block_size <= instruction_count:
            start_index = repeat_count * block_size
            end_index = start_index + block_size
            if signatures[start_index:end_index] != prefix:
                break
            repeat_count += 1

        coverage = repeat_count * block_size
        if repeat_count >= min_repeats and coverage > best_coverage:
            best_match = (block_size, repeat_count)
            best_coverage = coverage

    return best_match


def _simplify_repeated_prefix(circuit):
    """Simplify a repeated leading block once and reuse the result."""

    repeated_prefix = _find_repeated_prefix(circuit)
    if repeated_prefix is None:
        return circuit

    block_size, repeat_count = repeated_prefix
    run_end = block_size * repeat_count
    block_instructions = list(circuit.data[:block_size])
    block_circuit = _build_circuit_from_instructions(
        circuit, block_instructions
    )
    simplified_block = _run_commutative_inverse_cancellation(block_circuit)

    if len(simplified_block.data) >= block_size:
        return circuit

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    for _ in range(repeat_count):
        for instruction in simplified_block.data:
            rebuilt_circuit.append(
                instruction.operation,
                instruction.qubits,
                instruction.clbits,
            )

    for instruction in circuit.data[run_end:]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    if len(rebuilt_circuit.data) >= len(circuit.data):
        return circuit

    return rebuilt_circuit


def _find_adjacent_inverse_blocks(
    circuit, max_block_size=_MAX_STRUCTURAL_BLOCK_SIZE
):
    """Detect the largest adjacent exact block followed by its inverse."""

    instruction_count = len(circuit.data)
    max_candidate_size = min(max_block_size, instruction_count // 2)
    if max_candidate_size < 1:
        return None

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]
    inverse_signatures = [
        _inverse_instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]
    best_match = None
    best_coverage = 0

    for block_size in range(1, max_candidate_size + 1):
        for start_index in range(0, instruction_count - 2 * block_size + 1):
            block = signatures[start_index : start_index + block_size]
            inverse_block = list(
                reversed(
                    inverse_signatures[
                        start_index + block_size : start_index + 2 * block_size
                    ]
                )
            )
            if any(signature is None for signature in inverse_block):
                continue
            if block != inverse_block:
                continue

            coverage = 2 * block_size
            if coverage > best_coverage:
                best_match = (start_index, block_size)
                best_coverage = coverage

    return best_match


def _simplify_repeated_run(circuit):
    """Simplify a repeated block once and reuse the result."""

    repeated_run = _find_repeated_run(circuit)
    if repeated_run is None:
        return circuit

    start_index, block_size, repeat_count = repeated_run
    run_end = start_index + block_size * repeat_count
    block_instructions = list(
        circuit.data[start_index : start_index + block_size]
    )
    block_circuit = _build_circuit_from_instructions(
        circuit, block_instructions
    )
    simplified_block = _run_commutative_inverse_cancellation(block_circuit)

    if len(simplified_block.data) >= block_size:
        return circuit

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    for instruction in circuit.data[:start_index]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    for _ in range(repeat_count):
        for instruction in simplified_block.data:
            rebuilt_circuit.append(
                instruction.operation,
                instruction.qubits,
                instruction.clbits,
            )

    for instruction in circuit.data[run_end:]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    if len(rebuilt_circuit.data) >= len(circuit.data):
        return circuit

    return rebuilt_circuit


def _cancel_adjacent_inverse_blocks(circuit):
    """Remove an adjacent block and its exact inverse."""

    inverse_block = _find_adjacent_inverse_blocks(circuit)
    if inverse_block is None:
        return circuit

    start_index, block_size = inverse_block
    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase

    for instruction in circuit.data[:start_index]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    for instruction in circuit.data[start_index + 2 * block_size :]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    return rebuilt_circuit


def _structural_pre_simplify(circuit):
    """Apply cheap structure-aware simplifications before basis lowering.

    Layer 1 uses commutative inverse cancellation directly on the whole
    circuit. Layer 2 simplifies large repeated exact blocks anywhere in the
    circuit. Layer 3 removes adjacent exact inverse blocks as whole units.
    """

    simplified_circuit = circuit
    for _ in range(3):
        previous_instruction_count = len(simplified_circuit.data)
        prefix_simplified_circuit = _simplify_repeated_prefix(
            simplified_circuit
        )
        if len(prefix_simplified_circuit.data) < len(simplified_circuit.data):
            simplified_circuit = prefix_simplified_circuit
        elif len(simplified_circuit.data) <= _MAX_GLOBAL_STRUCTURAL_SCAN_SIZE:
            simplified_circuit = _simplify_repeated_run(simplified_circuit)
            simplified_circuit = _cancel_adjacent_inverse_blocks(
                simplified_circuit
            )
        simplified_circuit = _run_commutative_inverse_cancellation(
            simplified_circuit
        )
        if len(simplified_circuit.data) >= previous_instruction_count:
            break
    return simplified_circuit


def _circuit_metrics(circuit):
    """Compute coarse structural metrics for anti-regression checks."""

    total_gates = 0
    multi_qubit_gates = 0
    for instruction in circuit.data:
        operation = instruction.operation
        if operation.name == "barrier":
            continue
        total_gates += 1
        if operation.num_qubits > 1 and operation.name != "measure":
            multi_qubit_gates += 1

    return {
        "total_gates": total_gates,
        "depth": circuit.depth(),
        "multi_qubit_gates": multi_qubit_gates,
    }


def _circuit_cost(circuit):
    """Score a circuit for conservative default-pipeline comparisons.

    The default compiler should not significantly inflate total size or depth
    in exchange for tiny multi-qubit improvements. This weighted score keeps
    two-qubit reductions valuable while still rejecting obvious blow-ups.
    """

    metrics = _circuit_metrics(circuit)
    return (
        metrics["total_gates"]
        + metrics["depth"]
        + 10 * metrics["multi_qubit_gates"]
    )


def _should_compare_against_preset(
    original_circuit, baseline_circuit, candidate_circuit
):
    """Return True when the default path shows a clear regression signal.

    Two cases justify the extra preset comparison:
    1. The UCC default flow is already worse than a simple basis translation.
    2. Basis lowering alone inflated the circuit enough that a more global
       optimizer may recover higher-level structure before decomposition.
    """

    baseline_cost = _circuit_cost(baseline_circuit)
    return _circuit_cost(
        candidate_circuit
    ) > baseline_cost or baseline_cost > 1.5 * _circuit_cost(original_circuit)


def _compile_preset_reference(circuit, compiler):
    """Compile a reference candidate with Qiskit's preset optimizer.

    This is only used as a fallback/reference for the default UCC pipeline, so
    it intentionally does not forward the user callback.
    """

    if compiler.target_backend is not None:
        return qiskit_transpile(
            circuit,
            backend=compiler.target_backend,
            optimization_level=3,
        )

    return qiskit_transpile(
        circuit,
        basis_gates=list(compiler.target_gateset),
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )


def _select_lowest_cost_circuit(circuits):
    """Return the circuit with the lowest conservative structural cost."""

    return min(circuits, key=_circuit_cost)


def _enforce_target_constraints(circuit, compiler):
    """Re-translate a circuit into the requested backend or basis.

    Custom passes run after the default pipeline and may introduce operations
    outside the requested target. Run a final, non-optimizing translation so
    the public ``compile()`` contract still holds for the returned circuit.
    """

    if compiler.target_backend is not None:
        return qiskit_transpile(
            circuit,
            backend=compiler.target_backend,
            optimization_level=0,
        )

    return qiskit_transpile(
        circuit,
        basis_gates=list(compiler.target_gateset),
        optimization_level=0,
    )


def compile(
    circuit,
    return_format="original",
    target_gateset=None,
    target_backend=None,
    custom_passes=None,
    callback=None,
):
    """Compiles the provided quantum `circuit` by translating it to a Qiskit
    circuit, transpiling it, and returning the optimized circuit in the
    specified `return_format`.

    Args:
        circuit (object): The quantum circuit to be compiled.
        return_format (str): The format in which your circuit will be returned.
            e.g., "TKET", "OpenQASM2". Check ``ucc.supported_circuit_formats``.
            Defaults to the format of the input circuit.
        target_gateset (set[str]): (optional) The gateset to compile the circuit to.
            e.g. {"cx", "rx",...}. Defaults to the gate set of the target device if available. If no `target_gateset` or ` target_backend` is provided, defaults to {"cx", "rz", "rx", "ry", "h"}.
        target_backend (qiskit.providers.backend): (optional)
            The target device  to compile the circuit for. Can be specified as a Qiskit backend. If None, all-to-all connectivity is assumed. If a `target_backend` is specified, `target_backend.operation_names` supercedes the `target_gateset`.
        custom_passes (list[qiskit.transpiler.TransformationPass]): (optional)
            A list of custom passes to apply after the default set
            of passes. Defaults to None.
        callback: A callback function that will be called after each pass execution. The
                function will be called with 5 keyword arguments::

                    pass_ (Pass): the pass being run
                    dag (DAGCircuit): the dag output of the pass
                    time (float): the time to execute the pass
                    property_set (PropertySet): the property set
                    count (int): the index for the pass execution

    Returns:
        object: The compiled circuit in the specified format.
    """
    if return_format == "original":
        return_format = get_program_type_alias(circuit)

    # Translate to Qiskit Circuit object
    qiskit_circuit = _structural_pre_simplify(translate(circuit, "qiskit"))

    # Initialize the UCCDefault1 compiler with the target device and gateset
    ucc_default1 = UCCDefault1(
        target_backend=target_backend, target_gateset=target_gateset
    )

    # Translate into the target device gateset first; no optimization
    basis_translated_circuit = qiskit_transpile(
        qiskit_circuit,
        basis_gates=ucc_default1.target_gateset,
        optimization_level=0,
    )
    if target_backend is None:
        baseline_circuit = basis_translated_circuit
    else:
        baseline_circuit = _enforce_target_constraints(
            qiskit_circuit, ucc_default1
        )

    # Compile the circuit using the UCCDefault1 pass manager
    compiled_circuit = ucc_default1.run(
        basis_translated_circuit, callback=callback
    )

    has_custom_passes = bool(custom_passes)
    if has_custom_passes:
        custom_pass_manager = PassManager()
        custom_pass_manager.append(custom_passes)
        compiled_circuit = custom_pass_manager.run(
            compiled_circuit, callback=callback
        )

    compiled_circuit = _enforce_target_constraints(
        compiled_circuit, ucc_default1
    )
    if not has_custom_passes:
        candidate_circuits = [baseline_circuit, compiled_circuit]
        if _should_compare_against_preset(
            qiskit_circuit, baseline_circuit, compiled_circuit
        ):
            candidate_circuits.append(
                _compile_preset_reference(qiskit_circuit, ucc_default1)
            )
        compiled_circuit = _select_lowest_cost_circuit(candidate_circuits)

    # Translate the compiled circuit to the desired format
    final_result = translate(compiled_circuit, return_format)
    return final_result
