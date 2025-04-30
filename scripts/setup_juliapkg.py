# This script is used to setup the Julia packages needed inside the ucc.ft module.abs
# This is meant to be run by ucc developers if the dependences in those packages change

import juliapkg as jp
from pathlib import Path
import tomllib as toml

ucc_path = Path(__file__).parent.parent / "ucc"
target = ucc_path / "juliapkg.json"

# Infer from the QuantumSE.jl package dependencies
project_toml = toml.load(
    open(ucc_path / "ft" / "QuantumSE.jl" / "Project.toml", "rb")
)


jp.require_julia(project_toml["compat"]["julia"], target=target)
for pkg, uuid in project_toml["deps"].items():
    # Z3 requires a specific pre-release version
    if pkg == "Z3":
        jp.add(
            pkg,
            uuid,
            target=target,
            url="https://github.com/acasta-yhliu/Z3.jl",
            rev="quantumse",
        )
    else:
        jp.add(pkg, uuid, target=target)

# add local QuantumSE.jl
jp.add(
    "QuantumSE",
    "f27a11fe-df42-48ab-baf7-2c7df1fe28fa",
    target=target,
    path="./ft/QuantumSE.jl",
    dev=True,
)
