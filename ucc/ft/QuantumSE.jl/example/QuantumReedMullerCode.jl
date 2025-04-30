using Pkg
Pkg.activate(".")

using QuantumSE
using Z3

ctx = Context()

#bitvec2bool(x) = extract(x, 0, 0) == bv_val(ctx, 1, 1)

const Z_check=[[1,6,7,13],
               [1,5,7,12],
               [1,5,6,11],
               [2,7,8,12],
               [2,7,10,13],
               [2,8,10,14],
               [3,5,8,12],
               [3,5,9,11],
               [4,6,9,11],
               [9,11,14,15]]

const X_check=[[1,5,6,7,11,12,13,15],
               [2,7,8,10,12,13,14,15],
               [3,5,8,9,11,12,14,15],
               [4,6,9,10,11,13,14,15]]

const Z_l=[1,2,7]

const X_l=[1,2,3,5,7,8,12]

const d=3

function _zadj(idx)

    return Z_check[idx]

end

function _xadj(idx)

    return X_check[idx]

end

function mwpm(s, s_type)

    # assertion
    phi1 = bool_val(ctx, true)
    adj = s_type == "X" ? _xadj : _zadj
    num_s = s_type == "X" ? 4 : 10
    r_bv = alloc_symb(ctx, "assert_recovery_$(s_type)", len = 15)
    r = [extract(r_bv, j-1, j-1) for j in 1:15]
    for j in 1:num_s
        phi1 = phi1 & (s[j] == reduce(⊻, r[[adj(j)...]]))
    end
    phi2 = (sum( (x -> zeroext(ctx, x, _range2b(15))).(r) ) <= bv_val(ctx, 1, _range2b(15)))
    phi = not(forall(r_bv, not(phi1 & phi2)))

    # claim
    ϕ₁ = bool_val(ctx, true)
    adj = s_type == "X" ? _xadj : _zadj
    num_s = s_type == "X" ? 4 : 10
    r = [alloc_symb(ctx, "recovery_$(s_type)_$(j)") for j in 1:15]
    for j in 1:num_s
        ϕ₁ = ϕ₁ & (s[j] == reduce(⊻, r[[adj(j)...]]))
    end
    ϕ₂ = (sum( (x -> zeroext(ctx, x, _range2b(15))).(r) ) <= bv_val(ctx, 1, _range2b(15)))

    (r, (simplify(not(phi)) | (ϕ₁ & ϕ₂)), bool_val(ctx, true), bool_val(ctx, true))
end

@qprog prepare_cat (cat_qubits, verify_qubit) begin

    @repeat begin

        INITP(cat_qubits[1])
        for i in 2:length(cat_qubits)
            INIT(cat_qubits[i])
        end

        for i in 2:length(cat_qubits)
            CNOT(cat_qubits[1], cat_qubits[i])
        end

        #non-FT example for length(cat_qubits)==4:
        #res = Vector{Z3.Expr}(undef, 2)
        #INIT(verify_qubit)
        #CNOT(cat_qubits[1], verify_qubit)
        #CNOT(cat_qubits[4], verify_qubit)
        #res[1] = DestructiveM(verify_qubit)
        #INIT(verify_qubit)
        #CNOT(cat_qubits[2], verify_qubit)
        #CNOT(cat_qubits[3], verify_qubit)
        #res[2] = DestructiveM(verify_qubit)

        verify = generate_cat_verification(d, length(cat_qubits))
        res = Vector{Z3.Expr}(undef, length(verify)+1)
        res[1] = bv_val(ctx, 0, 1)
        for i in 1:length(verify)
            INIT(verify_qubit)
            CNOT(cat_qubits[verify[i][1]], verify_qubit)
            CNOT(cat_qubits[verify[i][2]], verify_qubit)
            res[i+1] = DestructiveM(verify_qubit)
        end

    end :until (reduce(|, res) == bv_val(ctx, 0, 1))

end

function QuantumReedMuller_x_s(idx::Integer)
	s = zeros(Bool, 15*2)

	for j in _xadj(idx)
		s[j] = true
	end

	s
end

@qprog QuantumReedMuller_x_m (idx) begin
    b = _xadj(idx)

    len_b = length(b)
    cat_qubits = [15+i for i in 1:len_b]
    verify_qubit = 15+len_b+1
    #prepare_cat(cat_qubits, verify_qubit)
    CatPreparationMod(cat_qubits)
    for i in 1:len_b
        CNOT(cat_qubits[i], b[i])
    end

    res = Vector{Z3.Expr}(undef, len_b)
    for i in 1:len_b
        res[i] = DestructiveMX(cat_qubits[i])
    end

    res = reduce(⊻, res)

    res
end

function QuantumReedMuller_z_s(idx::Integer)
	s = zeros(Bool, 15*2)

	for j in (_zadj(idx) .+ 15)
		s[j] = true
	end

	s
end

@qprog QuantumReedMuller_z_m (idx) begin
    b = _zadj(idx)

    len_b = length(b)
    cat_qubits = [15+i for i in 1:len_b]
    verify_qubit = 15+len_b+1
    #prepare_cat(cat_qubits, verify_qubit)
    CatPreparationMod(cat_qubits)
    for i in 1:len_b
        CZ(cat_qubits[i], b[i])
    end

    res = Vector{Z3.Expr}(undef, len_b)
    for i in 1:len_b
        res[i] = DestructiveMX(cat_qubits[i])
    end

    res = reduce(⊻, res)

    res
end

function QuantumReedMuller_lx()
	s = zeros(Bool, 2*15)

	@inbounds @simd for i in 1:7
		s[X_l[i]] = true
	end

	s
end

function QuantumReedMuller_lz()
	s = zeros(Bool, 2*15)

	@inbounds @simd for i in 1:3
		s[15 + Z_l[i]] = true
	end

	s
end

@qprog _QuantumReedMuller_decoder () begin

    t = 1
    #t = t - 1

    @repeat begin

        s_x = Matrix{Z3.Expr}(undef, 4, t+1)
        s_z = Matrix{Z3.Expr}(undef, 10, t+1)


        for i in 1:t+1
            for j in 1:4
                s_x[j,i] = QuantumReedMuller_x_m(j)
            end
            for j in 1:10
                s_z[j,i] = QuantumReedMuller_z_m(j)
            end
        end

        check_eq_x = Vector{Z3.Expr}(undef, t)
        check_eq_z = Vector{Z3.Expr}(undef, t)

        for i in 1:t
            check_eq_x[i] = reduce(|, [(s_x[j,i] ⊻ s_x[j,i+1]) for j in 1:4])
            check_eq_z[i] = reduce(|, [(s_z[j,i] ⊻ s_z[j,i+1]) for j in 1:10])
        end

        check_eq = (reduce(|, check_eq_x) | reduce(|, check_eq_z))

    end :until (check_eq == bv_val(ctx, 0, 1))

    r_x = mwpm(s_x[:, t+1], "X")
    r_z = mwpm(s_z[:, t+1], "Z")

    for j in 1:15
        #sZ(j, r_x[j])
        #sX(j, r_z[j])
        sPauli(j, r_z[j], r_x[j])
    end

end

@qprog QuantumReedMuller_decoder () begin

    _QuantumReedMuller_decoder()

    for i in 1:9
        INIT(15+i)
    end

end


function check_QuantumReedMuller_decoder(NERRS::Integer, slv_backend_cmd::Cmd)

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = 15
        num_ancilla = 9
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)
	    lz = _bv_const(ctx, "lz")

	    for i in 1:4
	    	stabilizer[i,:] = QuantumReedMuller_x_s(i)
            phases[i] = _bv_val(ctx, 0)
	    end
        for i in 1:10
	    	stabilizer[i+4,:] = QuantumReedMuller_z_s(i)
	    	phases[i+4] = _bv_val(ctx, 0)
	    end

	    stabilizer[15,:] = QuantumReedMuller_lz()
	    phases[15] = lz

        ρ01 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ1 = copy(ρ01)

        stabilizer[15,:] = QuantumReedMuller_lx()
	    phases[15] = _bv_val(ctx, 0)

        ρ02 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ2 = copy(ρ02)

        σ = CState([(:d, 3),
            (:_QuantumReedMuller_decoder, _QuantumReedMuller_decoder),
            (:QuantumReedMuller_decoder, QuantumReedMuller_decoder),
            (:QuantumReedMuller_z_m, QuantumReedMuller_z_m),
            (:QuantumReedMuller_x_m, QuantumReedMuller_x_m),
            (:_xadj, _xadj),
            (:_zadj, _zadj),
            (:prepare_cat, prepare_cat),
            (:generate_cat_verification, generate_cat_verification),
            (:ctx, ctx),
            (:mwpm, mwpm)
        ])

        num_errors = 1


        b_num_main_qubits = _range2b(num_main_qubits)
        nerrs_input = bv_val(ctx, 0, b_num_main_qubits)
        for j in 1:num_main_qubits
            nerrs_input += zeroext(ctx, inject_symbolic_error(ρ1, j), b_num_main_qubits)
        end

        cfg1 = SymConfig(QuantumReedMuller_decoder(), σ, ρ1, NERRS)

        res = true
        cfgs1 = QuantSymEx(cfg1)
        for cfg in cfgs1
            if !check_FT(cfg.ρ, ρ01, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "decoder", slv_backend_cmd, use_z3=false, non_FT=true)
                res = false
                break
            end
        end

        if res
            clearerrcnt()
            nerrs_input = bv_val(ctx, 0, b_num_main_qubits)
            for j in 1:num_main_qubits
                nerrs_input += zeroext(ctx, inject_symbolic_error(ρ2, j), b_num_main_qubits)
            end

            cfg2 = SymConfig(QuantumReedMuller_decoder(), σ, ρ2, NERRS)


            cfgs2 = QuantSymEx(cfg2)
            for cfg in cfgs2
                if !check_FT(cfg.ρ, ρ02, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "decoder", slv_backend_cmd, use_z3=false, non_FT=true)
                    res = false
                    break
                end
            end
        end

    end

    t1 = time()

    res, t1-t0
end


NERRS=11
#open("QuantumReedMuller_code.dat", "w") do io
  #println(io, "nq all")
println("nq all")
res, all = check_QuantumReedMuller_decoder(NERRS, `bitwuzla -rwl 1`)
  #println("$(d*d+5) $(all)")
  #println(io, "$(d*d+5) $(all)")
println("Quantum Reed-Muller Code, ec, [n,k,d]=[15,1,3], time=$(all)")
  #println(io, "Quantum Reed-Muller Code, [n,k,d]=[15,1,3], time=$(all)")
#end
