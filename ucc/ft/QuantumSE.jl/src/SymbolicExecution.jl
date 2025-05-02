using Z3
using MacroTools: postwalk, @capture

const CState = Dict{Symbol,Any}

const SymProbs = Dict{Z3.Expr,Z3.Expr}

#NERRS = 6
#include("config")
#export NERRS

mutable struct SymConfig
    S::QProg
    σ::CState
    const ρ::AbstractSymQuantumState
    P::SymProbs
    # path condition, assertion, claim
    ϕ::Tuple{Z3.Expr,Z3.Expr, Z3.Expr}

    const ctx::Z3.Context

    NERRS::Integer

    nerrs::Z3.Expr

    SymConfig(num_qubits::Integer, NERRS::Integer) = begin
        ctx = Z3.Context()
        new(QEmpty, CState(), SymStabilizerState(num_qubits, ctx), SymProbs(), (bool_val(ctx, true), bool_val(ρ.ctx, true), bool_val(ρ.ctx, true)), ctx, NERRS, bv_val(ctx, 0, NERRS))
    end

    SymConfig(S::QProg, σ::CState, ρ::AbstractSymQuantumState, P::SymProbs, ϕ::Tuple{Z3.Expr,Z3.Expr,Z3.Expr}, ctx::Z3.Context, NERRS::Integer, nerrs::Z3.Expr) = new(copy(S), copy(σ), copy(ρ), copy(P), (ϕ[1], ϕ[2], ϕ[3]), ctx, NERRS, nerrs)

    SymConfig(S::QProg, σ::CState, ρ::AbstractSymQuantumState, NERRS::Integer) = SymConfig(S, σ, ρ, SymProbs(), (bool_val(ρ.ctx, true), bool_val(ρ.ctx, true), bool_val(ρ.ctx, true)), ρ.ctx, NERRS, bv_val(ρ.ctx, 0, NERRS))

    SymConfig(cfg::SymConfig) = SymConfig(cfg.S, cfg.σ, cfg.ρ, cfg.P, (cfg.ϕ[1], cfg.ϕ[2], cfg.ϕ[3]), cfg.ctx, cfg.NERRS, cfg.nerrs)
end

Base.copy(cfg::SymConfig) = SymConfig(cfg)

CEval(σ::CState, e) = eval(postwalk(x -> x isa Symbol ? x in keys(σ) ? σ[x] : x : x, e))

function CAssign(σ, lvalue, rvalue)
    if lvalue isa Expr
        if lvalue.head == :ref
            index = CartesianIndex([CEval(σ, i) for i in lvalue.args[2:end]]...)
            σ[lvalue.args[1]][index] = CEval(σ, rvalue)
        end
    else
        σ[lvalue] = CEval(σ, rvalue)
    end
end

__error_count = 0
function errcnt()
    return __error_count
end

function adderrcnt()
    global __error_count
    __error_count += 1
    return __error_count
end

function clearerrcnt()
    global __error_count
    __error_count = 0
end

function QuantSymEx(cfg::SymConfig)

    NERRS = cfg.NERRS

    length(cfg.S.args) != 0 || return [cfg]

    inst = cfg.S.args[1]

    if ~isa(inst, Expr)
        cfg.σ[:__res__] = CEval(cfg.σ, inst)
        cfg.S.args = cfg.S.args[2:end]
        return QuantSymEx(cfg)
    end

    if inst.head == :call
        if inst.args[1] in [:H, :S, :X, :Y, :Z, :CNOT, :Identity, :CZ] # Clifford gates
            if length(inst.args) == 2
                # 1-q Clifford
                let target_qubit = CEval(cfg.σ, inst.args[2])
                    eval(inst.args[1])(cfg.ρ, target_qubit)
                    counter = inject_symbolic_error(cfg.ρ, target_qubit)
                    cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                    println(adderrcnt())
                    println(">>> $(varid()) $(inst)")
                end
            elseif length(inst.args) == 3
                # CNOT, CZ
                let target_qubit1 = CEval(cfg.σ, inst.args[2]), target_qubit2 = CEval(cfg.σ, inst.args[3])
                    eval(inst.args[1])(cfg.ρ, target_qubit1, target_qubit2)
                    counter1 = inject_symbolic_error(cfg.ρ, target_qubit1)
                    counter2 = inject_symbolic_error(cfg.ρ, target_qubit2)
                    counter = counter1 | counter2
                    cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                    println(adderrcnt())
                    println(">>> $(varid()) $(inst)")
                end
            end
        elseif inst.args[1] in [:sX, :sY, :sZ] # Symbolic X, Y, Z gates
            let target_qubit = CEval(cfg.σ, inst.args[2]), control_sym=CEval(cfg.σ, inst.args[3])
                eval(inst.args[1])(cfg.ρ, target_qubit, control_sym)
                counter = inject_symbolic_error(cfg.ρ, target_qubit)
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :sPauli # Symbolic Pauli gate
            let target_qubit = CEval(cfg.σ, inst.args[2]), control_sym1=CEval(cfg.σ, inst.args[3]), control_sym2=CEval(cfg.σ, inst.args[4])
                eval(inst.args[1])(cfg.ρ, target_qubit, control_sym1, control_sym2)
                counter = inject_symbolic_error(cfg.ρ, target_qubit)
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :M # Measurement Z basis
            let target_qubit = CEval(cfg.σ, inst.args[2]), sym_name=eval(CEval(cfg.σ, inst.args[3]))
                counter1 = inject_symbolic_Xerror(cfg.ρ, target_qubit)
                cfg.σ[:__res__] = eval(inst.args[1])(cfg.ρ, target_qubit, sym_name)
                counter2 = inject_symbolic_Xerror(cfg.ρ, target_qubit)
                counter = counter1 | counter2
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :MX # Measurement X basis
            let target_qubit = CEval(cfg.σ, inst.args[2]), sym_name=eval(CEval(cfg.σ, inst.args[3]))
                counter1 = inject_symbolic_Zerror(cfg.ρ, target_qubit)
                cfg.σ[:__res__] = eval(inst.args[1])(cfg.ρ, target_qubit, sym_name)
                counter2 = inject_symbolic_Zerror(cfg.ρ, target_qubit)
                counter = counter1 | counter2
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :DestructiveM # Destructive Measurement Z basis
            let target_qubit = CEval(cfg.σ, inst.args[2]), sym_name=eval(CEval(cfg.σ, inst.args[3]))
                counter1 = inject_symbolic_Xerror(cfg.ρ, target_qubit)
                cfg.σ[:__res__] = eval(inst.args[1])(cfg.ρ, target_qubit, sym_name)
                #counter2 = inject_symbolic_Xerror(cfg.ρ, target_qubit)
                counter = counter1 #| counter2
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :DestructiveMX # Destructive Measurement X basis
            let target_qubit = CEval(cfg.σ, inst.args[2]), sym_name=eval(CEval(cfg.σ, inst.args[3]))
                counter1 = inject_symbolic_Zerror(cfg.ρ, target_qubit)
                cfg.σ[:__res__] = eval(inst.args[1])(cfg.ρ, target_qubit, sym_name)
                #counter2 = inject_symbolic_Zerror(cfg.ρ, target_qubit)
                counter = counter1 #| counter2
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :INIT # INIT |0>
            let target_qubit = CEval(cfg.σ, inst.args[2])
                eval(inst.args[1])(cfg.ρ, target_qubit, "INIT")
                counter = inject_symbolic_Xerror(cfg.ρ, target_qubit)
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :INITP # INIT |+>
            let target_qubit = CEval(cfg.σ, inst.args[2])
                eval(inst.args[1])(cfg.ρ, target_qubit, "INITP")
                counter = inject_symbolic_Zerror(cfg.ρ, target_qubit)
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :INIT2CNOT12 # INIT |0> on qubit 2, CNOT on qubits 1, 2
            let target_qubit1 = CEval(cfg.σ, inst.args[2]), target_qubit2 = CEval(cfg.σ, inst.args[3])
                eval(inst.args[1])(cfg.ρ, target_qubit1, target_qubit2, "INIT2CNOT12")
                counter1 = inject_symbolic_error(cfg.ρ, target_qubit1)
                counter2 = inject_symbolic_Xerror(cfg.ρ, target_qubit2)
                counter = counter1 | counter2
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :CNOT12DestructiveM2 #CNOT on qubits 1, 2, DestructiveM on qubit 2
            let target_qubit1 = CEval(cfg.σ, inst.args[2]), target_qubit2 = CEval(cfg.σ, inst.args[3]), sym_name=eval(CEval(cfg.σ, inst.args[4]))
                counter1 = inject_symbolic_error(cfg.ρ, target_qubit1)
                counter2 = inject_symbolic_Xerror(cfg.ρ, target_qubit2)
                cfg.σ[:__res__] = eval(inst.args[1])(cfg.ρ, target_qubit1, target_qubit2, sym_name)
                counter = counter1 | counter2
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :CNOT12DestructiveMX1 #CNOT on qubits 1, 2, DestructiveMX on qubit 1
            let target_qubit1 = CEval(cfg.σ, inst.args[2]), target_qubit2 = CEval(cfg.σ, inst.args[3]), sym_name=eval(CEval(cfg.σ, inst.args[4]))
                counter1 = inject_symbolic_Zerror(cfg.ρ, target_qubit1)
                counter2 = inject_symbolic_error(cfg.ρ, target_qubit2)
                cfg.σ[:__res__] = eval(inst.args[1])(cfg.ρ, target_qubit1, target_qubit2, sym_name)
                counter = counter1 | counter2
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :CZ12DestructiveMX1 #CZ on qubits 1, 2, DestructiveMX on qubit 1
            let target_qubit1 = CEval(cfg.σ, inst.args[2]), target_qubit2 = CEval(cfg.σ, inst.args[3]), sym_name=eval(CEval(cfg.σ, inst.args[4]))
                counter1 = inject_symbolic_Zerror(cfg.ρ, target_qubit1)
                counter2 = inject_symbolic_error(cfg.ρ, target_qubit2)
                cfg.σ[:__res__] = eval(inst.args[1])(cfg.ρ, target_qubit1, target_qubit2, sym_name)
                counter = counter1 | counter2
                cfg.nerrs += zeroext(cfg.ctx, counter, NERRS)
                println(adderrcnt())
                println(">>> $(varid()) $(inst)")
            end
        elseif inst.args[1] == :CatPreparationMod # Cat Preparation Module
            let target_qubits = CEval(cfg.σ, inst.args[2])
                cfg.σ[:__res__] = eval(inst.args[1])(cfg.ρ, target_qubits)
                b_num_target_qubits = _range2b(length(target_qubits))
                counter1 = zeroext(cfg.ctx, inject_symbolic_Zerror(cfg.ρ, target_qubits[1]), b_num_target_qubits)   #a single Z error suffices
                counter2 = bv_val(cfg.ctx, 0, b_num_target_qubits)
                for jj in 1:length(target_qubits)
                    tmp_counter = inject_symbolic_Xerror(cfg.ρ, target_qubits[jj])
                    counter2 += zeroext(cfg.ctx, tmp_counter, b_num_target_qubits)
                    println(adderrcnt())
                end
                counter = alloc_symb(cfg.ctx, "cat_error", len = b_num_target_qubits)
                phi = (not(counter1 <= counter2) | (counter == counter2)) & ((counter1 <= counter2) | (counter == counter1))
                cfg.nerrs += addzeros(cfg.ctx, counter, NERRS-b_num_target_qubits)
                cfg.ϕ = (cfg.ϕ[1] & phi, cfg.ϕ[2], cfg.ϕ[3])
                println(">>> $(varid()) $(inst)")
            end
         elseif inst.args[1] == :MultiPauliMeasurement #Multi-qubits Pauli Measurement
            let target_qubits = CEval(cfg.σ, inst.args[2]), Paulis = CEval(cfg.σ, inst.args[3]), sym_name=eval(CEval(cfg.σ, inst.args[4]))
                meas_result = eval(inst.args[1])(cfg.ρ, target_qubits, Paulis, sym_name)
                bit_error = alloc_symb(cfg.ctx, sym_name*"_bit_error")
                cfg.σ[:__res__] = (meas_result ⊻ bit_error)
                b_num_target_qubits = _range2b(length(target_qubits))
                counter1 = zeroext(cfg.ctx, bit_error, b_num_target_qubits)   #a single bit-flip error suffices
                counter2 = bv_val(cfg.ctx, 0, b_num_target_qubits)
                for jj in 1:length(target_qubits)
                    tmp_counter = inject_symbolic_error(cfg.ρ, target_qubits[jj])
                    counter2 += zeroext(cfg.ctx, tmp_counter, b_num_target_qubits)
                    println(adderrcnt())
                end
                counter = alloc_symb(cfg.ctx, "MultiPauliMeasurement_error", len = b_num_target_qubits)
                phi = (not(counter1 <= counter2) | (counter == counter2)) & ((counter1 <= counter2) | (counter == counter1))
                cfg.nerrs += addzeros(cfg.ctx, counter, NERRS-b_num_target_qubits)
                cfg.ϕ = (cfg.ϕ[1] & phi, cfg.ϕ[2], cfg.ϕ[3])
                println(">>> $(varid()) $(inst)")
             end

            # if haskey(cfg.σ, :__init_list__)
            #     push!(cfg.σ[:__init_list__], symb)
            # else
            #     cfg.σ[:__init_list__] = [symb]
            # end
        else
            S = copy(cfg.S)
            res = CEval(cfg.σ, inst)
            if res isa Expr
                # println("what is this case? $(inst)")
                σ = copy(cfg.σ)
                cfg.S.args = CEval(cfg.σ, inst).args
                cfg = QuantSymEx(cfg)[1]
                σ[:__res__] = cfg.σ[:__res__]
                cfg.σ = σ
            elseif res isa Tuple
                cfg.σ[:__res__] = res[1]
                cfg.ϕ = (cfg.ϕ[1] & res[2], cfg.ϕ[2] & res[3], cfg.ϕ[3] & res[4])
            else
                cfg.σ[:__res__] = res
            end
            cfg.S.args = S.args[2:end]
            return QuantSymEx(cfg)
        end

        cfg.S.args = cfg.S.args[2:end]
        return QuantSymEx(cfg)

    elseif inst.head == :(=)

        if ~isa(inst.args[2], Expr)
            CAssign(cfg.σ, inst.args[1], inst.args[2])
            cfg.S.args = cfg.S.args[2:end]
            return QuantSymEx(cfg)
        end


        if inst.args[2].head == :comprehension # assume that comprehension doesn't contain conditionals
            inst.args[2].args[1].args[1] = postwalk(
                x -> x isa Symbol ? x == inst.args[2].args[1].args[2].args[1] ? Expr(:$, :($x)) : x : x,
                inst.args[2].args[1].args[1]
            )
            inst.args[2].args[1].args[1] = Expr(:block, Expr(:quote, inst.args[2].args[1].args[1]))
            qprogs = CEval(cfg.σ, inst.args[2])
            n_qprog = length(qprogs)
            temp = Vector{Union{Z3.Expr,Int}}(undef, n_qprog)
            S = copy(cfg.S)
            for j in 1:n_qprog
                cfg.S.args = [qprogs[j]]
                cfg = QuantSymEx(cfg)[1]
                # UCC edit -- Handle if we got a UInt instead of an Int
                # For source QASM, qubit registers are sized from compile time unit constants
                # That size is used in some looping constructs/comprehensions (like here)
                # and Z3/Julia need it to be an Int
                ttmp = cfg.σ[:__res__]
                temp[j] = ttmp isa UInt ? Int(ttmp) : ttmp
            end
            cfg.S.args = S.args[2:end]
            CAssign(cfg.σ, inst.args[1], temp)
            return QuantSymEx(cfg)
        elseif inst.args[2].head == :call # assume that subroutine doesn't contain conditionals
            S = copy(cfg.S)
            cfg.S.args = [inst.args[2]]
            cfg = QuantSymEx(cfg)[1]
            CAssign(cfg.σ, inst.args[1], cfg.σ[:__res__])
            cfg.S.args = S.args[2:end]
            return QuantSymEx(cfg)
        else
            CAssign(cfg.σ, inst.args[1], inst.args[2])
            cfg.S.args = cfg.S.args[2:end]
            return QuantSymEx(cfg)
        end

    elseif inst.head == :if
        ϕ = CEval(cfg.σ, inst.args[1])
        S1 = copy(cfg.S)
        S1.args = [inst.args[2].args; cfg.S.args[2:end]]
        S2 = copy(cfg.S)
        if length(inst.args) == 3
            S2.args = [inst.args[3].args; cfg.S.args[2:end]]
        else
            S2.args = cfg.S.args[2:end]
        end
        if ϕ isa Bool
            if ϕ
                cfg1 = SymConfig(S1, cfg.σ, cfg.ρ, cfg.P, cfg.ϕ, cfg.ctx, cfg.NERRS, cfg.nerrs)
                return QuantSymEx(cfg1)
            else
                cfg2 = SymConfig(S2, cfg.σ, cfg.ρ, cfg.P, cfg.ϕ, cfg.ctx, cfg.NERRS, cfg.nerrs)
                return QuantSymEx(cfg2)
            end
        end
        cfg1 = SymConfig(S1, cfg.σ, cfg.ρ, cfg.P, (cfg.ϕ[1] & ϕ, cfg.ϕ[2], cfg.ϕ[3]), cfg.ctx, cfg.NERRS, cfg.nerrs)
        cfg2 = SymConfig(S2, cfg.σ, cfg.ρ, cfg.P, (cfg.ϕ[1] & not(ϕ), cfg.ϕ[2], cfg.ϕ[3]), cfg.ctx, cfg.NERRS, cfg.nerrs)
        return vcat(QuantSymEx(cfg1)..., QuantSymEx(cfg2)...)
    elseif inst.head == :for
        inst.args[2] = postwalk(
            x -> x isa Symbol ? x == inst.args[1].args[1] ? Expr(:$, :($x)) : x : x,
            inst.args[2]
        )
        new_S = Expr(:block, Expr(:quote, inst.args[2]))
        qprogs = [CEval(CState(Dict([(inst.args[1].args[1], j)])), new_S) for j in CEval(cfg.σ, inst.args[1])]
        #qprogs = CEval(cfg.σ, Expr(:comprehension, new_S, inst.args[1]))
        n_qprog = length(qprogs)
        S = copy(cfg.S)
        for j in 1:n_qprog
            cfg.S.args = qprogs[j].args
            cfg = QuantSymEx(cfg)[1]
        end
        #S = copy(cfg.S)
        #cfg.S.args = [vcat([s.args for s in qprogs]...);cfg.S.args[2:end]]
        #@time QuantSymEx(cfg)
        cfg.S.args = S.args[2:end]
        return QuantSymEx(cfg)
    elseif inst.head == :repeat_until
        # repeat until, args[1] = condition, args[2] = body

        # execute once with the body
        rest_S = cfg.S.args[2:end]

        cfg.S.args = inst.args[2].args

        # return QuantSymEx(cfg)
        newcfgs = QuantSymEx(cfg)

        # add path condition for each config
        execute_config(c) = begin
            ϕ = CEval(c.σ, inst.args[1])
            # println("path condition is $(ϕ)")
            c.S.args = rest_S
            return SymConfig(c.S, c.σ, c.ρ, c.P, (c.ϕ[1] & ϕ, c.ϕ[2], c.ϕ[3]), c.ctx, c.NERRS, c.nerrs)
            # return c
        end
        final = map(execute_config, newcfgs)

        # println(final[1].S)

        #return final
        return vcat([QuantSymEx(final[ii]) for ii in 1:length(final)]...)
    else
        cfg.σ[:__res__] = CEval(cfg.σ, inst)
        cfg.S.args = cfg.S.args[2:end]
        return QuantSymEx(cfg)
    end

end
