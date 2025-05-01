module QuantumSE

abstract type AbstractSymQuantumState end

include("QuantumProgram.jl")
export @qprog, QProg, QEmpty, @repeat

include("GF2.jl")
export GF2

include("SymbolicStabilizer.jl")
export M, X, Y, Z, sX, sY, sZ, S, H, CNOT, INIT, Identity, CZ, INITP, MX, sPauli, DestructiveM, DestructiveMX, INIT1CNOT12, CNOT12DestructiveM2, CZ12DestructiveMX1, CatPreparationMod, MultiPauliMeasurement,
    SymStabilizerState, from_stabilizer, print_full_tableau, update!, inject_errors, inject_symbolic_error, inject_symbolic_Xerror, inject_symbolic_Zerror, from_css_code,
    _bv_val, _bv_const, _len2, _range2b, check_FT, _sum, varid, zeroext, addzeros, alloc_symb, generate_cat_verification, _canonicalize_mat, _Pauli_weight, _extend_rows

include("SymbolicExecution.jl")
export CState, SymConfig, QuantSymEx, CEval, errcnt, adderrcnt, clearerrcnt

include("LinearGroup.jl")
export AbstractGroup, AbstraLinearGroup, L2, PL2, pgl2, psl2, jacobi4squares

include("Sampler.jl")
export Sampler, parse_stim

include("PythonTranslate.jl")
export from_stabilizer_py, make_cstate, check_FT_py

using PrecompileTools
using Z3

#@setup_workload begin
    # Putting some things in `@setup_workload` instead of `@compile_workload` can reduce the size of the
    # precompile file and potentially make loading faster.
#    _ctx = Z3.Context()
#    @qprog id_circuit (n) begin
#        s = [j for j in 1:n]
#        for j in 1:n
#            H(j)
#        end
#        for j in 1:n
#            X(j)
#        end
#        for j in 1:n
#            X(j)
#        end
#        for j in 1:n
#            H(j)
#        end
#    end
#    n = 4
#    @compile_workload begin
        # all calls in this block will be precompiled, regardless of whether
        # they belong to your package or not (on Julia 1.8 and higher)
#        stabilizer = zeros(Bool, n, 2 * n)
#        phases = Vector{Z3.Expr}(undef, n)

#        for j in 1:n
#            stabilizer[j, j+n] = true
#            phases[j] = _bv_const(_ctx, "z_$(j)")
#        end

#        ρ0 = from_stabilizer(n, stabilizer, phases, _ctx, 0)
#        ρ = copy(ρ0)

#        σ = CState([(:n, n),
#            (:id_circuit, id_circuit),
#            (:ctx, _ctx),
#        ])

#        cfg = SymConfig(id_circuit(n), σ, ρ, _len2(n * 4) + 1)

#        cfgs = QuantSymEx(cfg)

#        res = true
#        for cfg in cfgs
#            if !check_FT(
#                cfg.ρ, ρ0, (cfg.ϕ[1], cfg.ϕ[2], cfg.ϕ[3]), cfg.nerrs, cfg.NERRS, 1;
#            )
#                res = false
#                break
#            end
#        end
#    end
#end

end # module QSE
