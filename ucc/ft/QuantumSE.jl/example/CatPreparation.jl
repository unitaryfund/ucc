#using Pkg
#Pkg.activate(".")

fault_t=2#parse(Int,ARGS[1])

using Z3
using QuantumSE


ctx = Context()

#bitvec2bool(x) = extract(x, 0, 0) == bv_val(ctx, 1, 1)


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

end


function check_cat_prepare(d::Integer, num_cat_qubits::Integer, NERRS::Integer, slv_backend_cmd::Cmd)

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = num_cat_qubits
        num_ancilla = 1
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)

	    @simd for i in 1:num_main_qubits-1
	    	stabilizer[i,:] = [0 for j in 1:2*num_main_qubits]
            stabilizer[i,num_main_qubits+i] = 1
            stabilizer[i,num_main_qubits+i+1] = 1
	    	phases[i] = _bv_val(ctx, 0)
	    end
        println("stabilizer=", stabilizer)


	    stabilizer[num_main_qubits,:] = vcat([1 for j in 1:num_main_qubits], [0 for j in 1:num_main_qubits])
	    phases[num_main_qubits] = _bv_val(ctx, 0)

        ρ0 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)

        @simd for i in 1:num_main_qubits
	    	stabilizer[i,:] = [0 for j in 1:2*num_main_qubits]
            stabilizer[i,num_main_qubits+i] = 1
	    	phases[i] = _bv_val(ctx, 0)
	    end

        ρ1 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)

        σ = CState([(:d, d),
            (:prepare_cat, prepare_cat),
            (:generate_cat_verification, generate_cat_verification),
            (:ctx, ctx)
       ])

        num_errors = Int(floor((d-1)÷2))


        b_num_main_qubits = _range2b(num_main_qubits)
        nerrs_input = bv_val(ctx, 0, b_num_main_qubits)
        #for j in 1:num_main_qubits
        #    nerrs_input += zeroext(ctx, inject_symbolic_Xerror(ρ1, j), b_num_main_qubits)
        #end

        cfg1 = SymConfig(prepare_cat(num_main_qubits, d), σ, ρ1, NERRS)

        res = true
        cfgs1 = QuantSymEx(cfg1)
        for cfg in cfgs1
            if !check_FT(cfg.ρ, ρ0, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "prepare", slv_backend_cmd, use_z3=false)
                res = false
                break
            end
        end

    end

    t1 = time()

    res, t1-t0
end


#d=7
#@assert d%2==1
d=fault_t*2+1
num_cat_qubits=8
NERRS=12
#open("cat_preparation.dat", "w") do io
  #println(io, "nq all")
println("nq all")
res, all = check_cat_prepare(d,num_cat_qubits,NERRS,`bitwuzla -rwl 1`)
println("Cat State Preparation, num_faults=$(fault_t), time=$(all)")
  #println(io, "$(d*d+5) $(all)")
#end
