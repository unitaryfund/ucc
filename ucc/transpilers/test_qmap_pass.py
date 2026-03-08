"""
Unit tests for QMAPRoutingPass

Tests verify:
1. Initialization parameters
2. Method selection (exact vs heuristic)
3. Teleportation flag
4. QMAP compilation workflow
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ucc.transpilers.qmap_pass import QMAPRoutingPass, QMAP_AVAILABLE
from qiskit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit


@unittest.skipUnless(QMAP_AVAILABLE, "MQT QMAP not installed")
class TestQMAPRoutingPassInit(unittest.TestCase):
    """Test QMAPRoutingPass initialization."""
    
    def test_default_params(self):
        """Test default initialization."""
        pass_ = QMAPRoutingPass()
        self.assertEqual(pass_.method, "heuristic")
        self.assertEqual(pass_.use_teleportation, False)
        self.assertEqual(pass_.verbose, False)
    
    def test_exact_method(self):
        """Test initialization with exact method."""
        pass_ = QMAPRoutingPass(method="exact")
        self.assertEqual(pass_.method, "exact")
    
    def test_heuristic_method(self):
        """Test initialization with heuristic method."""
        pass_ = QMAPRoutingPass(method="heuristic")
        self.assertEqual(pass_.method, "heuristic")
    
    def test_teleportation_enabled(self):
        """Test teleportation flag."""
        pass_ = QMAPRoutingPass(use_teleportation=True)
        self.assertEqual(pass_.use_teleportation, True)
    
    def test_verbose_enabled(self):
        """Test verbose flag."""
        pass_ = QMAPRoutingPass(verbose=True)
        self.assertEqual(pass_.verbose, True)


@unittest.skipUnless(QMAP_AVAILABLE, "MQT QMAP not installed")
class TestQMAPRoutingPassRun(unittest.TestCase):
    """Test QMAPRoutingPass.run() method."""
    
    def create_simple_dag(self):
        """Create a simple DAG for testing."""
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(1, 2)
        return qc.to_dag()
    
    def test_run_returns_dag(self):
        """Test that run returns a DAG."""
        pass_ = QMAPRoutingPass(method="heuristic")
        dag = self.create_simple_dag()
        result = pass_.run(dag)
        self.assertIsInstance(result, DAGCircuit)


class TestQMAPAvailability(unittest.TestCase):
    """Test QMAP availability check."""
    
    def test_qmap_available_flag(self):
        """Verify QMAP availability flag is set correctly."""
        # Should be True if mqt.qmap is installed
        self.assertIsInstance(QMAP_AVAILABLE, bool)


if __name__ == "__main__":
    unittest.main()
