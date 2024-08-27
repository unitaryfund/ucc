from setuptools import setup, find_packages

setup(
    name='quantum_translator',
    version='0.1.0',
    description='A library for translating Qiskit, Cirq, and TKET circuits into OpenQASM.',
    author='Jordan Sullivan',
    author_email='jordan@unitary.fund',
    packages=find_packages(),
    install_requires=[
        'qiskit',
        'cirq',
        'pytket',
        'openqasm3',
    ],
)

