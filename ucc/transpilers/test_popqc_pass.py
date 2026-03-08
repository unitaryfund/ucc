"""
Unit tests for PopQCPass

These tests verify the PopQCPass transpiler functionality:
1. Initialization with various parameters
2. Config file generation
3. Error handling when PopQC is not available
4. DAG transformation workflow
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from popqc_pass import PopQCPass
from qiskit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit


class TestPopQCPassInit(unittest.TestCase):
    """Test PopQCPass initialization."""
    
    def test_default_initialization(self):
        """Test default parameters are set correctly."""
        with patch('popqc_pass.PopQCPass._find_popqc', return_value='/fake/path/soam'):
            pass_ = PopQCPass()
            self.assertEqual(pass_.threads, 4)
            self.assertEqual(pass_.gateset, "Nam")
            self.assertEqual(pass_.omega, 200)
            self.assertEqual(pass_.timeout, 300)
    
    def test_custom_parameters(self):
        """Test custom parameters are set correctly."""
        with patch('popqc_pass.PopQCPass._find_popqc', return_value='/fake/path/soam'):
            pass_ = PopQCPass(threads=8, gateset="Clifford_T", omega=500, timeout=600)
            self.assertEqual(pass_.threads, 8)
            self.assertEqual(pass_.gateset, "Clifford_T")
            self.assertEqual(pass_.omega, 500)
            self.assertEqual(pass_.timeout, 600)


class TestPopQCPassConfig(unittest.TestCase):
    """Test PopQC config file generation."""
    
    def test_config_generation(self):
        """Test that config file is generated correctly."""
        with patch('popqc_pass.PopQCPass._find_popqc', return_value='/fake/soam'):
            pass_ = PopQCPass(threads=4, gateset="Nam", omega=200)
            config = pass_._create_config('/input.qasm', '/output.qasm')
            
            self.assertIn('omega = [200]', config)
            self.assertIn('gateset = ["Nam"]', config)
            self.assertIn('n_threads = [4]', config)
    
    def test_config_clifford_gateset(self):
        """Test config with Clifford_T gateset."""
        with patch('popqc_pass.PopQCPass._find_popqc', return_value='/fake/soam'):
            pass_ = PopQCPass(gateset="Clifford_T")
            config = pass_._create_config('/in.qasm', '/out.qasm')
            self.assertIn('gateset = ["Clifford_T"]', config)


class TestPopQCPassRun(unittest.TestCase):
    """Test PopQCPass.run() method."""
    
    def create_simple_dag(self):
        """Create a simple DAG for testing."""
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        return qc.to_dag()
    
    @patch('popqc_pass.subprocess.run')
    @patch('popqc_pass.tempfile.NamedTemporaryFile')
    @patch('popqc_pass.qasm2')
    @patch('popqc_pass.os.path.exists')
    def test_run_returns_dag_on_success(self, mock_exists, mock_qasm2, mock_tempfile, mock_run):
        """Test run returns DAG when PopQC succeeds."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        mock_file = MagicMock()
        mock_file.name = '/tmp/test.qasm'
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        mock_qasm2.dumps.return_value = "OPENQASM 2.0;"
        
        # Mock os.path.exists to return True for all files during test
        def exists_side_effect(path):
            return True
        mock_exists.side_effect = exists_side_effect
        
        with patch('popqc_pass.os.remove'):
            mock_qc = MagicMock()
            mock_qc.to_dag.return_value = self.create_simple_dag()
            mock_qasm2.loads.return_value = mock_qc
            
            with patch('popqc_pass.PopQCPass._find_popqc', return_value='/fake/soam'):
                pass_ = PopQCPass()
                result = pass_.run(self.create_simple_dag())
                self.assertIsInstance(result, DAGCircuit)
    
    @patch('popqc_pass.PopQCPass._find_popqc', return_value='/fake/soam')
    @patch('popqc_pass.subprocess.run')
    @patch('popqc_pass.tempfile.NamedTemporaryFile')
    @patch('popqc_pass.qasm2')
    def test_run_returns_original_on_error(self, mock_qasm2, mock_tempfile, mock_run, mock_find):
        """Test that original DAG is returned on PopQC error."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")
        
        mock_file = MagicMock()
        mock_file.name = '/tmp/test.qasm'
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        mock_qasm2.dumps.return_value = "OPENQASM 2.0;"
        
        with patch('popqc_pass.os.remove'):
            pass_ = PopQCPass()
            original_dag = self.create_simple_dag()
            result = pass_.run(original_dag)
            
            # Should return original DAG on error
            self.assertEqual(result, original_dag)


if __name__ == "__main__":
    unittest.main()
