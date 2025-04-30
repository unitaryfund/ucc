using Pkg
Pkg.activate(".")

gadget=ARGS[1]
d=parse(Int,ARGS[2])

using QuantumSE
using Z3

ctx = Context()

#bitvec2bool(x) = extract(x, 0, 0) == bv_val(ctx, 1, 1)

function _xadj(d, idx)
    ai = (idx-1)÷d
    bi = (idx-1)%d

    [d*d+ai*d+bi, ai*d+(bi+d-1)%d, ai*d+bi, d*d+((ai+d-1)%d)*d+bi] .+ 1
end

function _zadj(d, idx)
    ai = (idx-1)÷d
    bi = (idx-1)%d

    [((ai+1)%d)*d+bi, d*d+ai*d+bi, d*d+ai*d+(bi+1)%d, ai*d+bi] .+ 1
end

function mwpm(d::Integer, s, s_type)

    # assertion
    phi1 = bool_val(ctx, true)
    adj = s_type == "X" ? _xadj : _zadj
    r_bv = alloc_symb(ctx, "assert_recovery_$(s_type)", len = 2*d*d)
    r = [extract(r_bv, j-1, j-1) for j in 1:2*d*d]
    for j in 1:d*d-1
        phi1 = phi1 & (s[j] == reduce(⊻, r[[adj(d, j)...]]))
    end
    phi2 = (sum( (x -> zeroext(ctx, x, _range2b(2*d*d))).(r) ) <= bv_val(ctx, (d-1)÷2, _range2b(2*d*d)))
    phi = not(forall(r_bv, not(phi1 & phi2)))

    # claim
    ϕ₁ = bool_val(ctx, true)
    adj = s_type == "X" ? _xadj : _zadj
    r = [alloc_symb(ctx, "recovery_$(s_type)_$(j)") for j in 1:2*d*d]
    for j in 1:d*d-1
        ϕ₁ = ϕ₁ & (s[j] == reduce(⊻, r[[adj(d, j)...]]))
    end
    ϕ₂ = (sum( (x -> zeroext(ctx, x, _range2b(2*d*d))).(r) ) <= bv_val(ctx, (d-1)÷2, _range2b(2*d*d)))

    (r, (simplify(not(phi)) | (ϕ₁ & ϕ₂)), bool_val(ctx, true), bool_val(ctx, true))
end

@qprog prepare_cat (cat_qubits, verify_qubit, d) begin

    @repeat begin

        INITP(cat_qubits[1])
        for i in 2:length(cat_qubits)
            INIT2CNOT12(cat_qubits[1], cat_qubits[i])
        end

        #for i in 2:length(cat_qubits)
        #    CNOT(cat_qubits[1], cat_qubits[i])
        #end

        verify = generate_cat_verification(d, length(cat_qubits))
        res = Vector{Z3.Expr}(undef, length(verify)+1)
        res[1] = bv_val(ctx, 0, 1)
        for i in 1:length(verify)
            #INIT(verify_qubit)
            #CNOT(cat_qubits[verify[i][1]], verify_qubit)
            INIT2CNOT12(cat_qubits[verify[i][1]], verify_qubit)
            #CNOT(cat_qubits[verify[i][2]], verify_qubit)
            #res[i+1] = DestructiveM(verify_qubit)
            res[i+1] = CNOT12DestructiveM2(cat_qubits[verify[i][2]], verify_qubit)
        end

    end :until (reduce(|, res) == bv_val(ctx, 0, 1))

end


function toric_x_s(d::Integer, idx::Integer)
	s = zeros(Bool, 4*d*d)

	for j in _xadj(d, idx)
		s[j] = true
	end

	s
end

@qprog toric_x_m (d, idx) begin
    b = _xadj(d, idx)

    cat_qubits = [d*d*2+1, d*d*2+2, d*d*2+3, d*d*2+4]
    verify_qubit = d*d*2+5
    #prepare_cat(cat_qubits, verify_qubit, d)
    CatPreparationMod(cat_qubits)
    res = Vector{Z3.Expr}(undef, 4)
    for i in 1:4
        CNOT(cat_qubits[i], b[i])
    end

    for i in 1:4
        res[i] = MX(cat_qubits[i])
    end

    res = reduce(⊻, res)

    res
end

function toric_z_s(d::Integer, idx::Integer)
	s = zeros(Bool, 4*d*d)

	for j in (_zadj(d, idx) .+ 2*d*d)
		s[j] = true
	end

	s
end

@qprog toric_z_m (d, idx) begin
    b = _zadj(d, idx)

    cat_qubits = [d*d*2+1, d*d*2+2, d*d*2+3, d*d*2+4]
    verify_qubit = d*d*2+5
    #prepare_cat(cat_qubits, verify_qubit, d)
    CatPreparationMod(cat_qubits)
    res = Vector{Z3.Expr}(undef, 4)
    for i in 1:4
        CZ(cat_qubits[i], b[i])
    end

    for i in 1:4
        res[i] = MX(cat_qubits[i])
    end

    res = reduce(⊻, res)

    res
end

function toric_lx1(d::Integer)
	s = zeros(Bool, 4*d*d)

	@inbounds @simd for i in 1:d
		s[d*d+i] = true
	end

	s
end

function toric_lx2(d::Integer)
	s = zeros(Bool, 4*d*d)

	@inbounds @simd for i in 1:d
		s[i*d] = true
	end

	s
end


function toric_lz1(d::Integer)
	s = zeros(Bool, 4*d*d)

	@inbounds @simd for i in 1:d
		s[3*d*d+i*d] = true
	end

	s
end

function toric_lz2(d::Integer)
	s = zeros(Bool, 4*d*d)

	@inbounds @simd for i in 1:d
		s[2*d*d+i] = true
	end

	s
end

@qprog _toric_decoder (d) begin

    t = Int(floor((d-1)/2))
    #t = t - 1

    @repeat begin

        s_x = Matrix{Z3.Expr}(undef, d*d-1, t+1)
        s_z = Matrix{Z3.Expr}(undef, d*d-1, t+1)


        for i in 1:t+1
            for j in 1:d*d-1
                #s_x[j,i] = toric_x_m(d, j)
                #s_z[j,i] = toric_z_m(d, j)
                b = _xadj(d, j)
                s_x[j,i] = MultiPauliMeasurement(b, ['X' for kk in 1:length(b)])
                b = _zadj(d, j)
                s_z[j,i] = MultiPauliMeasurement(b, ['Z' for kk in 1:length(b)])
            end
        end

        check_eq_x = Vector{Z3.Expr}(undef, t)
        check_eq_z = Vector{Z3.Expr}(undef, t)

        for i in 1:t
            check_eq_x[i] = reduce(|, [(s_x[j,i] ⊻ s_x[j,i+1]) for j in 1:d*d-1])
            check_eq_z[i] = reduce(|, [(s_z[j,i] ⊻ s_z[j,i+1]) for j in 1:d*d-1])
        end

        check_eq = (reduce(|, check_eq_x) | reduce(|, check_eq_z))

    end :until (check_eq == bv_val(ctx, 0, 1))

    r_x = mwpm(d, s_x[:, t+1], "X")
    r_z = mwpm(d, s_z[:, t+1], "Z")

    for j in 1:2*d*d
        #sZ(j, r_x[j])
        #sX(j, r_z[j])
        sPauli(j, r_z[j], r_x[j])
    end

end

@qprog toric_decoder (d) begin

    _toric_decoder(d)

    ancilla = [2*d*d+1, 2*d*d+2, 2*d*d+3, 2*d*d+4, 2*d*d+5]
    for i in 1:5
        INIT(ancilla[i])
    end

end

@qprog toric_identity (d) begin

    for i in 1:2*d*d
        Identity(i)
    end

end

@qprog toric_CNOT (d) begin

    for i in 1:2*d*d
        CNOT(i,2*d*d+i)
    end

end


@qprog toric_lx1_m (d) begin
    b = [d*d+i for i in 1:d]

    cat_qubits = [d*d*2+i for i in 1:d]
    verify_qubit = d*d*2+d+1
    #prepare_cat(cat_qubits, verify_qubit, d)
    CatPreparationMod(cat_qubits)
    res = Vector{Z3.Expr}(undef, d)
    for i in 1:d
        CNOT(cat_qubits[i], b[i])
    end

    for i in 1:d
        res[i] = MX(cat_qubits[i])
    end

    res = reduce(⊻, res)

    res
end

@qprog toric_lx2_m (d) begin
    b = [i*d for i in 1:d]

    cat_qubits = [d*d*2+i for i in 1:d]
    verify_qubit = d*d*2+d+1
    #prepare_cat(cat_qubits, verify_qubit, d)
    CatPreparationMod(cat_qubits)
    res = Vector{Z3.Expr}(undef, d)
    for i in 1:d
        CNOT(cat_qubits[i], b[i])
    end

    for i in 1:d
        res[i] = MX(cat_qubits[i])
    end

    res = reduce(⊻, res)

    res
end

@qprog toric_lz1_m (d) begin
    b = [d*d+i*d for i in 1:d]

    cat_qubits = [d*d*2+i for i in 1:d]
    verify_qubit = d*d*2+d+1
    #prepare_cat(cat_qubits, verify_qubit, d)
    CatPreparationMod(cat_qubits)
    res = Vector{Z3.Expr}(undef, d)
    for i in 1:d
        CZ(cat_qubits[i], b[i])
    end

    for i in 1:d
        res[i] = MX(cat_qubits[i])
    end

    res = reduce(⊻, res)

    res
end

@qprog toric_lz2_m (d) begin
    b = [i for i in 1:d]

    cat_qubits = [d*d*2+i for i in 1:d]
    verify_qubit = d*d*2+d+1
    #prepare_cat(cat_qubits, verify_qubit, d)
    CatPreparationMod(cat_qubits)
    res = Vector{Z3.Expr}(undef, d)
    for i in 1:d
        CZ(cat_qubits[i], b[i])
    end

    for i in 1:d
        res[i] = MX(cat_qubits[i])
    end

    res = reduce(⊻, res)

    res
end

#function mwpm_full(d::Integer, s, s_type, ml, ml_adj)
#
#    # claim
#    ϕ₁ = bool_val(ctx, true)
#    adj = s_type == "X" ? _xadj : _zadj
#    r = [alloc_symb(ctx, "recovery_$(s_type)_$(j)") for j in 1:2*d*d]
#    for j in 1:d*d-1
#        ϕ₁ = ϕ₁ & (s[j] == reduce(⊻, r[[adj(d, j)...]]))
#    end
#    for j in 1:length(ml)
#        ϕ₁ = ϕ₁ & (ml[j] == reduce(⊻, r[[ml_adj[j]...]]))
#    end
#
#    (r, ϕ₁, bool_val(ctx, true), bool_val(ctx, true))
#end

function mwpm_full(d::Integer, s, s_type, ml, ml_adj)

    num_qubits = 2*d*d
    num_stabilizers = length(s)
    num_logical = length(ml)

    adj = s_type == "X" ? _xadj : _zadj

    mat=zeros(Bool, num_stabilizers+num_logical, num_qubits)
    for j in 1:num_stabilizers
        for k in adj(d, j)
            mat[j, k] = 1
        end
    end
    for j in 1:num_logical
        for k in ml_adj[j]
            mat[num_stabilizers+j, k] = 1
        end
    end

    mat = _extend_rows(mat)
    mat_GF2 = GF2.(mat)
    inv_mat = Matrix{UInt64}(inv(mat_GF2))

    s = vcat(s,ml)

    part_solution = Vector{Z3.Expr}(undef, num_qubits)
    for j in 1 : num_qubits
        part_solution[j] = simplify(reduce(⊻, [inv_mat[j, jj] & s[jj] for jj in 1:num_stabilizers+num_logical]))
    end

    (part_solution, bool_val(ctx, true), bool_val(ctx, true), bool_val(ctx, true))

end

@qprog _toric_prepare_00 (d) begin

    t = Int(floor((d-1)/2))
    #t = t - 1

    for i in 1:2*d*d
        INIT(i)
    end

    @repeat begin

        s_x = Matrix{Z3.Expr}(undef, d*d-1, t+1)
        s_z = Matrix{Z3.Expr}(undef, d*d+1, t+1)

        for i in 1:t+1
            for j in 1:d*d-1
                #s_x[j,i] = toric_x_m(d, j)
                #s_z[j,i] = toric_z_m(d, j)
                b = _xadj(d, j)
                s_x[j,i] = MultiPauliMeasurement(b, ['X' for kk in 1:length(b)])
                b = _zadj(d, j)
                s_z[j,i] = MultiPauliMeasurement(b, ['Z' for kk in 1:length(b)])
            end
            #s_z[d*d,i] = toric_lz1_m(d)
            #s_z[d*d+1,i] = toric_lz2_m(d)
            b = [d*d+ii*d for ii in 1:d]
            s_z[d*d,i] = MultiPauliMeasurement(b, ['Z' for kk in 1:length(b)])
            b = [ii for ii in 1:d]
            s_z[d*d+1,i] = MultiPauliMeasurement(b, ['Z' for kk in 1:length(b)])
        end

        check_eq_x = Vector{Z3.Expr}(undef, t)
        check_eq_z = Vector{Z3.Expr}(undef, t)

        for i in 1:t
            check_eq_x[i] = reduce(|, [(s_x[j,i] ⊻ s_x[j,i+1]) for j in 1:d*d-1])
            check_eq_z[i] = reduce(|, [(s_z[j,i] ⊻ s_z[j,i+1]) for j in 1:d*d+1])
        end

        check_eq = (reduce(|, check_eq_x) | reduce(|, check_eq_z))

    end :until (check_eq == bv_val(ctx, 0, 1))

    lz_adj = [[d*d+i*d for i in 1:d], [i for i in 1:d]]
    r_x = mwpm_full(d, s_x[1:d*d-1, t+1], "X", [], [])
    r_z = mwpm_full(d, s_z[1:d*d-1, t+1], "Z", s_z[d*d:d*d+1, t+1], lz_adj)

    for j in 1:2*d*d
        #sZ(j, r_x[j])
        #sX(j, r_z[j])
        sPauli(j, r_z[j], r_x[j])
    end

end

@qprog toric_prepare_00 (d) begin

    _toric_prepare_00(d)

    ancilla = [2*d*d+i for i in 1:max(5,d+1)]
    for i in 1:length(ancilla)
        INIT(ancilla[i])
    end

end

function majority(s)

    # assert length(s) % 2 == 1
    len_s = length(s)

    half = bv_val(ctx, len_s ÷ 2, _range2b(len_s))

    r = alloc_symb(ctx, "majority")

    phi1 = ((sum([zeroext(ctx, s[i], _range2b(len_s)) for i in 1:len_s]) <= half) == (r == _bv_val(ctx, 0)))

    (r, phi1, bool_val(ctx, true), bool_val(ctx, true))

end

@qprog toric_measurement (d) begin

    t = Int(floor((d-1)/2))

    m_lz = Vector{Z3.Expr}(undef, 2*t+1)

    for i in 1:2*t+1
        #m_lz[i] = toric_lz1_m(d)
        b = [d*d+ii*d for ii in 1:d]
        m_lz[i] = MultiPauliMeasurement(b, ['Z' for kk in 1:length(b)])
        _toric_decoder(d)
    end

    final_res = majority(m_lz)

end

function check_toric_measurement(d::Integer, NERRS::Integer, slv_backend_cmd::Cmd)

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = d*d*2
        num_ancilla = max(5, d+1)
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)
	    lz1 = _bv_const(ctx, "lz1")
	    lz2 = _bv_const(ctx, "lz2")

	    @simd for i in 1:d*d-1
	    	stabilizer[i,:] = toric_x_s(d, i)
	    	stabilizer[i+d*d,:] = toric_z_s(d, i)
	    	phases[i] = _bv_val(ctx, 0)
	    	phases[i+d*d] = _bv_val(ctx, 0)
	    end

	    stabilizer[d*d,:] = toric_lz1(d)
	    phases[d*d] = lz1
	    stabilizer[2*d*d,:] = toric_lz2(d)
	    phases[2*d*d] = lz2

        ρ01 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ1 = copy(ρ01)

        σ = CState([(:d, d),
            (:toric_measurement, toric_measurement),
            (:_toric_decoder, _toric_decoder),
            (:toric_z_m, toric_z_m),
            (:toric_x_m, toric_x_m),
            (:toric_lz1_m, toric_lz1_m),
            (:toric_lz2_m, toric_lz2_m),
            (:majority, majority),
            (:_xadj, _xadj),
            (:_zadj, _zadj),
            (:prepare_cat, prepare_cat),
            (:generate_cat_verification, generate_cat_verification),
            (:ctx, ctx),
            (:mwpm, mwpm)
        ])

        num_errors = Int(floor((d-1)÷2))


        b_num_main_qubits = _range2b(num_main_qubits)
        nerrs_input = bv_val(ctx, 0, b_num_main_qubits)
        for j in 1:num_main_qubits
            nerrs_input += zeroext(ctx, inject_symbolic_error(ρ1, j), b_num_main_qubits)
        end

        cfg1 = SymConfig(toric_measurement(d), σ, ρ1, NERRS)

        res = true
        cfgs1 = QuantSymEx(cfg1)
        for cfg in cfgs1
            if !check_FT(cfg.ρ, ρ01, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "measurement", slv_backend_cmd, meas_result=cfg.σ[:final_res], meas_gt=lz1, use_z3=false)
                res = false
                break
            end
        end

    end

    t1 = time()

    res, t1-t0
end


function check_toric_prepare(d::Integer, NERRS::Integer, slv_backend_cmd::Cmd)

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = d*d*2
        num_ancilla = max(5, d+1)
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)

	    @simd for i in 1:d*d-1
	    	stabilizer[i,:] = toric_x_s(d, i)
	    	stabilizer[i+d*d,:] = toric_z_s(d, i)
	    	phases[i] = _bv_val(ctx, 0)
	    	phases[i+d*d] = _bv_val(ctx, 0)
	    end

	    stabilizer[d*d,:] = toric_lz1(d)
	    phases[d*d] = _bv_val(ctx, 0)
	    stabilizer[2*d*d,:] = toric_lz2(d)
	    phases[2*d*d] = _bv_val(ctx, 0)

        ρ0 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)

        @simd for i in 1:2*d*d
	    	stabilizer[i,:] = [0 for j in 1:4*d*d]
            stabilizer[i,2*d*d+i] = 1
	    	phases[i] = _bv_val(ctx, 0)
	    end

        ρ1 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)

        σ = CState([(:d, d),
            (:_toric_prepare_00, _toric_prepare_00),
            (:toric_prepare_00, toric_prepare_00),
            (:toric_z_m, toric_z_m),
            (:toric_x_m, toric_x_m),
            (:toric_lz1_m, toric_lz1_m),
            (:toric_lz2_m, toric_lz2_m),
            (:_xadj, _xadj),
            (:_zadj, _zadj),
            (:prepare_cat, prepare_cat),
            (:generate_cat_verification, generate_cat_verification),
            (:ctx, ctx),
            (:mwpm_full, mwpm_full)
        ])

        num_errors = Int(floor((d-1)÷2))

        b_num_main_qubits = _range2b(num_main_qubits)
        nerrs_input = bv_val(ctx, 0, b_num_main_qubits)
        #for j in 1:num_main_qubits
        #    nerrs_input += zeroext(ctx, inject_symbolic_Xerror(ρ1, j), b_num_main_qubits)
        #end

        cfg1 = SymConfig(toric_prepare_00(d), σ, ρ1, NERRS)

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



function check_toric_decoder(d::Integer, NERRS::Integer, slv_backend_cmd::Cmd)

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = d*d*2
        num_ancilla = 5
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)
	    lz1 = _bv_const(ctx, "lz1")
	    lz2 = _bv_const(ctx, "lz2")

	    @simd for i in 1:d*d-1
	    	stabilizer[i,:] = toric_x_s(d, i)
	    	stabilizer[i+d*d,:] = toric_z_s(d, i)
	    	phases[i] = _bv_val(ctx, 0)
	    	phases[i+d*d] = _bv_val(ctx, 0)
	    end

	    stabilizer[d*d,:] = toric_lz1(d)
	    phases[d*d] = lz1
	    stabilizer[2*d*d,:] = toric_lz2(d)
	    phases[2*d*d] = lz2

        ρ01 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ1 = copy(ρ01)

        stabilizer[d*d,:] = toric_lx1(d)
	    phases[d*d] = _bv_val(ctx, 0)
	    stabilizer[2*d*d,:] = toric_lx2(d)
	    phases[2*d*d] = _bv_val(ctx, 0)

        ρ02 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ2 = copy(ρ02)

        σ = CState([(:d, d),
            (:_toric_decoder, _toric_decoder),
            (:toric_decoder, toric_decoder),
            (:toric_z_m, toric_z_m),
            (:toric_x_m, toric_x_m),
            (:_xadj, _xadj),
            (:_zadj, _zadj),
            (:prepare_cat, prepare_cat),
            (:generate_cat_verification, generate_cat_verification),
            (:ctx, ctx),
            (:mwpm, mwpm)
        ])

        num_errors = Int(floor((d-1)÷2))


        b_num_main_qubits = _range2b(num_main_qubits)
        nerrs_input = bv_val(ctx, 0, b_num_main_qubits)
        for j in 1:num_main_qubits
            nerrs_input += zeroext(ctx, inject_symbolic_error(ρ1, j), b_num_main_qubits)
        end

        cfg1 = SymConfig(toric_decoder(d), σ, ρ1, NERRS)

        res = true
        cfgs1 = QuantSymEx(cfg1)
        for cfg in cfgs1
            if !check_FT(cfg.ρ, ρ01, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "decoder", slv_backend_cmd, use_z3=false)
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

            cfg2 = SymConfig(toric_decoder(d), σ, ρ2, NERRS)


            cfgs2 = QuantSymEx(cfg2)
            for cfg in cfgs2
                if !check_FT(cfg.ρ, ρ02, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "decoder", slv_backend_cmd, use_z3=false)
                    res = false
                    break
                end
            end
        end

    end

    t1 = time()

    res, t1-t0
end


function check_toric_identity(d::Integer, NERRS::Integer, slv_backend_cmd::Cmd)

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = d*d*2
        num_ancilla = 0
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)
	    lz1 = _bv_const(ctx, "lz1")
	    lz2 = _bv_const(ctx, "lz2")

	    @simd for i in 1:d*d-1
	    	stabilizer[i,:] = toric_x_s(d, i)
	    	stabilizer[i+d*d,:] = toric_z_s(d, i)
	    	phases[i] = _bv_val(ctx, 0)
	    	phases[i+d*d] = _bv_val(ctx, 0)
	    end

	    stabilizer[d*d,:] = toric_lz1(d)
	    phases[d*d] = lz1
	    stabilizer[2*d*d,:] = toric_lz2(d)
	    phases[2*d*d] = lz2

        ρ01 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ1 = copy(ρ01)

        stabilizer[d*d,:] = toric_lx1(d)
	    phases[d*d] = _bv_val(ctx, 0)
	    stabilizer[2*d*d,:] = toric_lx2(d)
	    phases[2*d*d] = _bv_val(ctx, 0)

        ρ02 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ2 = copy(ρ02)

        σ = CState([(:d, d),
            (:toric_identity, toric_identity),
            (:ctx, ctx)
        ])

        num_errors = Int(floor((d-1)÷2))


        b_num_main_qubits = _range2b(num_main_qubits)
        nerrs_input = bv_val(ctx, 0, b_num_main_qubits)
        for j in 1:num_main_qubits
            nerrs_input += zeroext(ctx, inject_symbolic_error(ρ1, j), b_num_main_qubits)
        end

        cfg1 = SymConfig(toric_identity(d), σ, ρ1, NERRS)

        res = true
        cfgs1 = QuantSymEx(cfg1)
        for cfg in cfgs1
            if !check_FT(cfg.ρ, ρ01, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "gate", slv_backend_cmd, use_z3=false)
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

            cfg2 = SymConfig(toric_identity(d), σ, ρ2, NERRS)


            cfgs2 = QuantSymEx(cfg2)
            for cfg in cfgs2
                if !check_FT(cfg.ρ, ρ02, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "gate", slv_backend_cmd, use_z3=false)
                    res = false
                    break
                end
            end
        end

    end

    t1 = time()

    res, t1-t0
end

function check_toric_CNOT(d::Integer, NERRS::Integer, slv_backend_cmd::Cmd)

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = 4*d*d
        num_ancilla = 0
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)
	    lz1_1 = _bv_const(ctx, "lz1_1")
        lz2_1 = _bv_const(ctx, "lz2_1")
        lz1_2 = _bv_const(ctx, "lz1_2")
        lz2_2 = _bv_const(ctx, "lz2_2")

	    @simd for i in 1:d*d-1
            x_s=toric_x_s(d, i)
            z_s=toric_z_s(d, i)
	        stabilizer[i,:] = vcat(vcat(x_s[1:2*d*d], zeros(Bool, 2*d*d)), vcat(x_s[2*d*d+1:4*d*d], zeros(Bool, 2*d*d)))
	    	stabilizer[i+(d*d-1),:] = vcat(vcat(z_s[1:2*d*d], zeros(Bool, 2*d*d)), vcat(z_s[2*d*d+1:4*d*d], zeros(Bool, 2*d*d)))
            stabilizer[i+d*d*2,:] = vcat(vcat(zeros(Bool, 2*d*d), x_s[1:2*d*d]), vcat(zeros(Bool, 2*d*d), x_s[2*d*d+1:4*d*d]))
            stabilizer[i+(3*d*d-1), :] = vcat(vcat(zeros(Bool, 2*d*d), z_s[1:2*d*d]), vcat(zeros(Bool, 2*d*d), z_s[2*d*d+1:4*d*d]))
	    	phases[i] = _bv_val(ctx, 0)
	    	phases[i+(d*d-1)] = _bv_val(ctx, 0)
            phases[i+d*d*2] = _bv_val(ctx, 0)
            phases[i+(3*d*d-1)] = _bv_val(ctx, 0)
	    end

        lz1_s=toric_lz1(d)
        lz2_s=toric_lz2(d)

	    stabilizer[2*d*d-1,:] = vcat(vcat(lz1_s[1:2*d*d], zeros(Bool, 2*d*d)), vcat(lz1_s[2*d*d+1:4*d*d], zeros(Bool, 2*d*d)))
	    phases[2*d*d-1] = lz1_1
        stabilizer[2*d*d,:] = vcat(vcat(lz2_s[1:2*d*d], zeros(Bool, 2*d*d)), vcat(lz2_s[2*d*d+1:4*d*d], zeros(Bool, 2*d*d)))
	    phases[2*d*d] = lz2_1

        stabilizer[4*d*d-1,:] = vcat(vcat(zeros(Bool, 2*d*d), lz1_s[1:2*d*d]), vcat(zeros(Bool, 2*d*d), lz1_s[2*d*d+1:4*d*d]))
        phases[4*d*d-1] = lz1_2
        stabilizer[4*d*d,:] = vcat(vcat(zeros(Bool, 2*d*d), lz2_s[1:2*d*d]), vcat(zeros(Bool, 2*d*d), lz2_s[2*d*d+1:4*d*d]))
        phases[4*d*d] = lz2_2

        ρ01 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ1 = copy(ρ01)

        for i in 1:2*d*d
            CNOT(ρ01, i, i+2*d*d)
        end

        lx1_s=toric_lx1(d)
        lx2_s=toric_lx2(d)

        stabilizer[2*d*d-1,:] = vcat(vcat(lx1_s[1:2*d*d], zeros(Bool, 2*d*d)), vcat(lx1_s[2*d*d+1:4*d*d], zeros(Bool, 2*d*d)))
	    phases[2*d*d-1] = _bv_val(ctx, 0)
        stabilizer[2*d*d,:] = vcat(vcat(lx2_s[1:2*d*d], zeros(Bool, 2*d*d)), vcat(lx2_s[2*d*d+1:4*d*d], zeros(Bool, 2*d*d)))
	    phases[2*d*d] = _bv_val(ctx, 0)

        stabilizer[4*d*d-1,:] = vcat(vcat(zeros(Bool, 2*d*d), lx1_s[1:2*d*d]), vcat(zeros(Bool, 2*d*d), lx1_s[2*d*d+1:4*d*d]))
        phases[4*d*d-1] = _bv_val(ctx, 0)
        stabilizer[4*d*d,:] = vcat(vcat(zeros(Bool, 2*d*d), lx2_s[1:2*d*d]), vcat(zeros(Bool, 2*d*d), lx2_s[2*d*d+1:4*d*d]))
        phases[4*d*d] = _bv_val(ctx, 0)

        ρ02 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ2 = copy(ρ02)

        for i in 1:2*d*d
            CNOT(ρ02, i, i+2*d*d)
        end

        σ = CState([(:d, d),
            (:toric_CNOT, toric_CNOT),
            (:ctx, ctx)
        ])

        num_errors = Int(floor((d-1)÷2))


        b_num_main_qubits = _range2b(num_main_qubits)
        nerrs_input = bv_val(ctx, 0, b_num_main_qubits)
        for j in 1:num_main_qubits
            nerrs_input += zeroext(ctx, inject_symbolic_error(ρ1, j), b_num_main_qubits)
        end

        cfg1 = SymConfig(toric_CNOT(d), σ, ρ1, NERRS)

        res = true
        cfgs1 = QuantSymEx(cfg1)
        for cfg in cfgs1
            if !check_FT(cfg.ρ, ρ01, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "gate", slv_backend_cmd, num_blocks=2, use_z3=false)
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

            cfg2 = SymConfig(toric_CNOT(d), σ, ρ2, NERRS)


            cfgs2 = QuantSymEx(cfg2)
            for cfg in cfgs2
                if !check_FT(cfg.ρ, ρ02, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "gate", slv_backend_cmd, num_blocks=2, use_z3=false)
                    res = false
                    break
                end
            end
        end

    end

    t1 = time()

    res, t1-t0
end


#d=3
@assert d%2==1
@assert gadget in ["ec","prep","cnot","meas"]
NERRS=11
#open("toric_code.dat", "w") do io
  #println(io, "nq all")
println("nq all")

if gadget == "ec"
  res, all = check_toric_decoder(d,NERRS,`bitwuzla -rwl 1`)
elseif gadget == "prep"
  res, all = check_toric_prepare(d,NERRS,`bitwuzla -rwl 1`)
elseif gadget == "cnot"
  res, all = check_toric_CNOT(d,NERRS,`bitwuzla -rwl 1`)
elseif gadget == "meas"
  res, all = check_toric_measurement(d,NERRS,`bitwuzla -rwl 1`)
end

  #println("$(d*d*2+5) $(all)")
  #println(io, "$(d*d*2+5) $(all)")
println("Toric Code, $(gadget), [n,k,d]=[$(d*d*2),2,$(d)], time=$(all)")
  #println(io, "Toric Code, [n,k,d]=[$(d*d*2),2,$(d)], time=$(all)")
#end
