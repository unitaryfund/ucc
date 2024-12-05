from setuptools import setup, find_packages

# Read the contents of your README file
with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="ucc",  # Package name
    version="0.1.1",  
    author="Jordan Sullivan",
    author_email="jordan@unitary.fund",
    description="Unitary Compiler Collection: A quantum circuit interface and compiler for multiple quantum frameworks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/unitaryfund/ucc",  # Repository URL
    packages=find_packages(),  # Automatically find and include all packages in the project
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",  # Python version required
    install_requires=[
        "qiskit>=0.41.0",
        "cirq-core>=1.4.0",
        "pytket>=1.3.0",
        "pyqrack>=1.33.0",
        "qbraid>=0.7.3",
        "ply",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",  # Testing framework
            "pytest-cov>=2.10",  # Coverage plugin for pytest
        ],
        "doc": ["sphinx==8.1.3"],
    },
    entry_points={
        "console_scripts": [
            "ucc=ucc.__main__:main",  # Command-line entry point
        ],
    },
)
