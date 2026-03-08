"""
PopQC Transpiler Pass for UCC
==============================

This module provides a UCC transpiler pass that integrates PopQC
(Parallel Quantum Circuit Optimizer) for parallel circuit optimization.

PopQC Paper: https://arxiv.org/abs/2506.13720v1
PopQC Repo: https://github.com/UmutAcarLab/popqc

Installation:
    1. Build PopQC: cargo build --release
    2. Install PopQC binary to PATH

Usage:
    from ucc import compile
    from popqc_pass import PopQCPass

    # Use PopQC with 8 threads
    compiled = compile(circuit, custom_passes=[PopQCPass(threads=8)])
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional, List

from qiskit.transpiler.basepasses import TransformationPass
from qiskit.dagcircuit import DAGCircuit
from qiskit import QuantumCircuit


class PopQCPass(TransformationPass):
    """
    A Qiskit transpiler pass that uses PopQC for parallel circuit optimization.

    PopQC achieves significant speedups by using multiple threads to optimize
    different regions of a quantum circuit simultaneously.

    Parameters:
        threads (int): Number of threads to use for parallel optimization.
                      Default: 4
        gateset (str): Target gateset. Options: "Nam", "Clifford_T".
                      Default: "Nam"
        omega (int): Optimization parameter. Higher = more optimization.
                    Default: 200
        timeout (int): Timeout in seconds. Default: 300
        popqc_path (str): Path to PopQC binary. If None, searches PATH.

    Example:
        >>> from qiskit import QuantumCircuit
        >>> from ucc import compile
        >>> from popqc_pass import PopQCPass
        >>>
        >>> circuit = QuantumCircuit(10)
        >>> # ... add gates ...
        >>> compiled = compile(circuit, custom_passes=[PopQCPass(threads=8)])
    """

    def __init__(
        self,
        threads: int = 4,
        gateset: str = "Nam",
        omega: int = 200,
        timeout: int = 300,
        popqc_path: Optional[str] = None
    ):
        super().__init__()
        self.threads = threads
        self.gateset = gateset
        self.omega = omega
        self.timeout = timeout
        self.popqc_path = popqc_path or self._find_popqc()

    def _find_popqc(self) -> str:
        """Find PopQC binary in PATH or common locations."""
        # Check PATH
        result = subprocess.run(
            ["which", "soam"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()

        # Check common locations
        common_paths = [
            Path.home() / ".cargo" / "bin" / "soam",
            Path("/usr/local/bin/soam"),
            Path("./popqc-repo/target/release/soam"),
        ]

        for path in common_paths:
            if path.exists():
                return str(path)

        raise FileNotFoundError(
            "PopQC binary 'soam' not found. "
            "Please build PopQC or specify popqc_path."
        )

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """
        Run PopQC optimization on the circuit.

        Args:
            dag: The DAG circuit to optimize.

        Returns:
            Optimized DAG circuit.
        """
        # Convert DAG to circuit
        circuit = dag.to_circuit()

        # Export to QASM
        qasm = qasm2.dumps(circuit)

        # Create temp files
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.qasm', delete=False
        ) as input_file:
            input_file.write(qasm)
            input_path = input_file.name

        output_path = input_path.replace('.qasm', '_optimized.qasm')
        config_path = input_path.replace('.qasm', '.toml')

        try:
            # Create config
            config = self._create_config(input_path, output_path)
            with open(config_path, 'w') as f:
                f.write(config)

            # Run PopQC
            result = subprocess.run(
                [self.popqc_path, config_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=Path(self.popqc_path).parent
            )

            if result.returncode != 0:
                print(f"PopQC warning: {result.stderr}")
                return dag

            # Read optimized circuit
            if os.path.exists(output_path):
                with open(output_path, 'r') as f:
                    optimized_qasm = f.read()

                optimized_circuit = QuantumCircuit.qasm2.loads(optimized_qasm)
                return optimized_circuit.to_dag()

            return dag

        except subprocess.TimeoutExpired:
            print(f"PopQC timeout after {self.timeout}s")
            return dag
        except Exception as e:
            print(f"PopQC error: {e}")
            return dag
        finally:
            # Cleanup
            for path in [input_path, output_path, config_path]:
                if os.path.exists(path):
                    os.remove(path)

    def _create_config(self, input_path: str, output_path: str) -> str:
        """Create PopQC configuration file."""
        return f'''circuit_path = ["{input_path}"]
use_soam = [true]
omega = [{self.omega}]
preprocess_config = ["None"]
cost = ["Gate"]
gateset = ["{self.gateset}"]
n_threads = [{self.threads}]
layout = ["One"]

[[oracle_name]]
[oracle_name.Qiskit]
'''


def benchmark_popqc(circuit: QuantumCircuit, threads_list: List[int] = [1, 2, 4, 8]):
    """
    Benchmark PopQC with different thread counts.

    Args:
        circuit: Quantum circuit to optimize.
        threads_list: List of thread counts to test.

    Returns:
        Dictionary with benchmark results.
    """
    import time

    results = {}

    for threads in threads_list:
        popqc = PopQCPass(threads=threads)
        dag = circuit.to_dag()

        start = time.time()
        optimized = popqc.run(dag)
        elapsed = time.time() - start

        results[threads] = {
            "time": elapsed,
            "original_gates": len(circuit),
            "optimized_gates": len(optimized.to_circuit()) if optimized else len(circuit)
        }

    return results


if __name__ == "__main__":
    # Demo
    from qiskit import QuantumCircuit

    print("PopQC Transpiler Pass Demo")
    print("=" * 40)

    # Create a test circuit
    circuit = QuantumCircuit(5)
    for i in range(5):
        circuit.h(i)
    for i in range(4):
        circuit.cx(i, i + 1)
    for i in range(5):
        circuit.h(i)

    print(f"Original circuit: {len(circuit)} gates")

    # Note: This requires PopQC to be built and in PATH
    try:
        popqc = PopQCPass(threads=4)
        print(f"PopQC binary found: {popqc.popqc_path}")
        print("Ready to optimize circuits!")
    except FileNotFoundError as e:
        print(f"Note: {e}")
        print("Build PopQC first: cargo build --release")
