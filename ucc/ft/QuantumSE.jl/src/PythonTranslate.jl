using Z3

# Layer for converting between python and Julia
# mostly deals with type conversions


function from_stabilizer_py(num_main_qubits::Integer, Stabilizer::AbstractArray, ctx::Z3.Context, num_ancilla::Integer=0)
    phases = Vector{Z3.Expr}(undef, num_main_qubits)
    for i in 1:num_main_qubits
        phases[i] = _bv_val(ctx, 0)
    end

    from_stabilizer(num_main_qubits, convert(Matrix{Bool},Stabilizer), phases, ctx, num_ancilla)
end

function make_cstate(d::AbstractDict{Any, Any})
    CState(Symbol(k) => v for (k, v) in d)
end

function check_FT_py(cfg::SymConfig, ρ0::SymStabilizerState, num_errors::Int64, nerrs_input::Z3.Expr, FT_type::String)
    check_FT(cfg.ρ, ρ0, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "prepare", `bitwuzla -rwl 1`, use_z3=false)
end

