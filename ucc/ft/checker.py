from .julia import jl
from stim import PauliString, Tableau
import numpy as np
import math


def to_julia_tableau_fmt(
    tableau: Tableau,
) -> np.ndarray:
    """
    Converts a Stim stabilizer Tableau to the specified Julia boolean matrix format
    expected by the QuantumSE.jl package.

    The Julia format represents stabilizers as a boolean matrix where rows are
    generators and columns are [X_part | Z_part].

    The Stim format returned by tableau.to_numpy() follows the Aaronson-Gottesman
    format in https://arxiv.org/pdf/quant-ph/0406196.

    """
    _x2x, _x2z, z2x, z2z, _x_signs, _z_signs = tableau.to_numpy()

    num_qubits = z2x.shape[0]

    julia_stabilizer = np.zeros((num_qubits, 2 * num_qubits), dtype=bool)
    # We only care how the stabilizer generators for Z (versus entire Tableu)
    julia_stabilizer[:, 0:num_qubits] = z2x
    julia_stabilizer[:, num_qubits : 2 * num_qubits] = z2z

    return julia_stabilizer


def to_qprog(circuit):
    """Convert the circuit to a qprog object.

    This is a placeholder function. The actual implementation will depend on
    the specific details of the circuit and the qprog format.
    """

    jl.seval("""
    @qprog prepare_cat (num_cat_qubits, d) begin

        cat_qubits = [i for i in 1:num_cat_qubits]
        verify_qubit = num_cat_qubits + 1

        @repeat begin

            INIT(cat_qubits[1])
            H(cat_qubits[1])
            #for i in 2:length(cat_qubits)
            #    INIT2CNOT12(cat_qubits[1], cat_qubits[i])
            #end

            for i in 2:length(cat_qubits)
                INIT(cat_qubits[i])
                CNOT(cat_qubits[1], cat_qubits[i])
            end

            verify = generate_cat_verification(d, length(cat_qubits))
            res = Vector{Z3.Expr}(undef, length(verify)+1)
            res[1] = bv_val(ctx, 0, 1)
            for i in 1:length(verify)
                INIT(verify_qubit)
                CNOT(cat_qubits[verify[i][1]], verify_qubit)
                #INIT2CNOT12(cat_qubits[verify[i][1]], verify_qubit)
                CNOT(cat_qubits[verify[i][2]], verify_qubit)
                res[i+1] = DestructiveM(verify_qubit)
                #res[i+1] = CNOT12DestructiveM2(cat_qubits[verify[i][2]], verify_qubit)
            end

        end :until (reduce(|, res) == bv_val(ctx, 0, 1))

    end""")

    return jl.prepare_cat


def _bits_needed(j):
    return int(math.ceil(math.log2(j + 1)))


def ft_check(stabilizers: list[PauliString], circuit, max_faults) -> bool:
    """Check if the given circuit over the given stabilizers is fault tolerent
    up to max_faults.
    """

    # Directly translating CatPreparation.jl
    jl.seval("using QuantumSE;")
    jl.seval("using Z3;")

    d = max_faults * 2 + 1  #
    NERRS = 6  # Can this be inferred?
    tableau = to_julia_tableau_fmt(Tableau.from_stabilizers(stabilizers))
    num_main_qubits = tableau.shape[0]
    num_ancilla = 1  # infer from circuit?

    # create the julia Z3 context
    ctx = jl.Context()

    # create target cat state symbolic stabilizer state
    # TODO: For cat state phases are all 0 the function below doesn't do anything
    # special. For general codes, we will need a way to setup the symbolic phases
    rho_target = jl.from_stabilizer_py(
        num_main_qubits, tableau, ctx, num_ancilla
    )

    # create initial state
    # TODO: For cat state, its not a QECC we are checking, but that starting
    # from computationl basis, we succesfully prepare the cat state
    # For other codes, what is this? (need to lock at examples still)

    tableau_in = to_julia_tableau_fmt(
        Tableau.from_stabilizers(
            [PauliString(f"Z{i}") for i in range(num_main_qubits)]
        )
    )
    rho_init = jl.from_stabilizer_py(
        num_main_qubits, tableau_in, ctx, num_ancilla
    )

    # Translate the circuit to qprog
    prepare_cat_func = to_qprog(circuit)

    # Create CState object for looking up the classical variables
    cstate = jl.make_cstate({"ctx": ctx})

    num_errors = (d - 1) // 2
    b_num_main_qubits = _bits_needed(num_main_qubits)
    nerrs_input = jl.bv_val(ctx, 0, b_num_main_qubits)
    cfg1 = jl.SymConfig(
        prepare_cat_func(num_main_qubits, d), cstate, rho_init, NERRS
    )

    # Generate configurations and check_FT
    res = True
    cfgs1 = jl.QuantSymEx(cfg1)
    for cfg in cfgs1:
        if not jl.check_FT_py(
            cfg, rho_target, num_errors, nerrs_input, "prepare"
        ):
            res = False
            break
    return res
