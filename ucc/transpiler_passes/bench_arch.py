import numpy as np
import math
import networkx as nx
from qiskit import QuantumCircuit
from qiskit.circuit import Barrier, Measure
from qiskit.circuit.library.standard_gates import HGate

class BenchArch(object):
    """Base class for generating device coupling graph, circuit dag graph"""
    def __init__(self, qasm, lattice_xy=None, coupling_map=None):
        """
        Args:
            qasm: circuit in OpenQASM format
            lattice_xy: (x,y) if coupling_map is not given and the topology is grid
            coupling_map: connectivity between qubits such as 
            [(0,1), (1,2), (2,3), (3,4), (4,5), (5,6), (6,7), (0,7), (0,8), (1,9), (0,10)]
        """
        # Transform OpenQASM to qiskit circuit
        self.benchmark = QuantumCircuit.from_qasm_str(qasm)
        self.b_qbts = len(self.benchmark.qubits)
        # Generate the topology graph (2d grid) and the distance matrix
        if coupling_map:
            self.coupling_map = coupling_map
        else:
            self.lattice_x, self.lattice_y = lattice_xy
            self.coupling_map = self.grid_coupling()

        # n_qbits is the number of qubits in the given topology
        self.topology, self.distmat, self.n_qbits = self.topology_graph()
        self.G_circ, self.pairs, self.instrs, self.q1_instrs = self.circuit_graph()
        adjmat_csr = nx.adjacency_matrix(self.G_circ)
        self.adjmat = adjmat_csr.todense() 

    def zz_tuple(self, qbits):
        """
        Representation for two-qubit gate
        """
        if isinstance(qbits[0], int):
            physical_q_0 = qbits[0]
            physical_q_1 = qbits[1]
        else:
            physical_q_0 = qbits[0]._index
            physical_q_1 = qbits[1]._index
        r_0 = min(physical_q_0, physical_q_1)
        r_1 = max(physical_q_0, physical_q_1)
        return (r_0, r_1)

    def circuit_graph(self):
        # Generate the interaction graph of the input circuit and the interaction matrix
        qpairs = []
        all_qs = []
        instrs2q = {}
        instrs1q = {0: [], 1:[]}
        for instr, qbits, cbits in self.benchmark.data:
            if len(qbits) == 2:
                qpairs.append((qbits[0]._index, qbits[1]._index))
                instrs2q[self.zz_tuple(qbits)] = instr
            elif len(qbits) == 1:
                if isinstance(instr, Barrier):
                    continue
                elif isinstance(instr, Measure):
                    continue
                elif isinstance(instr, HGate):
                    instrs1q[0].append((instr, qbits[0]._index))
                else:
                    instrs1q[1].append((instr, qbits[0]._index))
            for q in qbits:
                if q not in all_qs:
                    all_qs.append(q)
        G_circ = nx.Graph()
        G_circ.add_nodes_from(np.arange(self.n_qbits))
        G_circ.add_edges_from(qpairs)
        return G_circ, qpairs, instrs2q, instrs1q

    def instruction_graph(self, qpairs):
        qbits = []
        for qpair in qpairs:
            for q in qpair:
                if q not in qbits:
                    qbits.append(q)

        G = nx.Graph()
        G.add_nodes_from(qbits)
        G.add_edges_from(qpairs)
        return G

    def grid_coupling(self):
        # Generate the 2d grid coupling map
        pnodes = [(x, y) for y in range(0, self.lattice_y) for x in range(0, self.lattice_x)]
        locs_pqbits = {}
        for node in pnodes:
            locs_pqbits[node] = node[1]*self.lattice_x+node[0]
        topology_edges = []
        for i in range(len(pnodes)):
            node = pnodes[i]
            for j in range(i+1,len(pnodes)):
                if abs(pnodes[j][0]-node[0]) + abs(pnodes[j][1]-node[1]) == 1:
                    topology_edges.append((locs_pqbits[node], locs_pqbits[pnodes[j]]))
        return topology_edges

    def topology_graph(self):
        # Generate the topology graph and the distance matrix
        all_qbts = []
        for qpair in self.coupling_map:
            for q in qpair:
                if q not in all_qbts:
                    all_qbts.append(q)
        n_qbits = len(all_qbts)
        topology = nx.Graph()
        topology.add_nodes_from(np.arange(n_qbits))
        topology.add_edges_from(self.coupling_map)

        distmat = np.zeros((n_qbits, n_qbits))
        for i in range(n_qbits-1):
            for j in range(i+1, n_qbits):
                distmat[i,j] = nx.shortest_path_length(topology, source=i, target=j)
                distmat[j,i] = distmat[i,j]
        return topology, distmat, n_qbits