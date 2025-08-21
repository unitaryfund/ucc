from qiskit_ionq import IonQProvider

ionq_provider = IonQProvider()
ionq_backend = ionq_provider.get_backend("ionq_qpu", gateset="native")
print("Coupling map", dir(ionq_backend))
# v2_ionq_backend = BackendV2Converter(ionq_backend)

# circuit = QiskitCircuit(2)
# circuit.h(0)
# circuit.cx(0, 1)
# compile(circuit, target_device=v2_ionq_backend.target)
