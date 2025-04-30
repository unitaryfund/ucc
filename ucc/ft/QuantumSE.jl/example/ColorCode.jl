using Pkg
Pkg.activate(".")

gadget=ARGS[1]
d=parse(Int,ARGS[2])

using QuantumSE
using Z3
using LinearAlgebra
using SimpleGF2

ctx = Context()

#bitvec2bool(x) = extract(x, 0, 0) == bv_val(ctx, 1, 1)

function _zadj(d, idx)
    @assert d==3 || d==5
    if d==3
        res = [[1,2,3,4],[2,3,5,6],[3,4,5,7]]
        return res[idx]
    else
        res = [[1,2,3,4],[1,3,5,6],[5,6,7,8],[7,8,9,10],[3,4,6,7,9,11,12,14],[12,14,15,17],[11,12,13,15],[13,15,16,17]]
        return res[idx]
    end
end

function _xadj(d, idx)
    return _zadj(d, idx)
end

function mwpm(d::Integer, s, s_type)

    @assert d==3 || d==5
    n = d==3 ? 7 : 17

    # assertion
    phi1 = bool_val(ctx, true)
    adj = s_type == "X" ? _xadj : _zadj
    r_bv = alloc_symb(ctx, "assert_recovery_$(s_type)", len = n)
    r = [extract(r_bv, j-1, j-1) for j in 1:n]
    for j in 1:(n-1)÷2
        phi1 = phi1 & (s[j] == reduce(⊻, r[[adj(d, j)...]]))
    end
    phi2 = (sum( (x -> zeroext(ctx, x, _range2b(n))).(r) ) <= bv_val(ctx, (d-1)÷2, _range2b(n)))
    phi = not(forall(r_bv, not(phi1 & phi2)))

    # claim
    ϕ₁ = bool_val(ctx, true)
    adj = s_type == "X" ? _xadj : _zadj
    r = [alloc_symb(ctx, "recovery_$(s_type)_$(j)") for j in 1:n]
    for j in 1:(n-1)÷2
        ϕ₁ = ϕ₁ & (s[j] == reduce(⊻, r[[adj(d, j)...]]))
    end
    ϕ₂ = (sum( (x -> zeroext(ctx, x, _range2b(n))).(r) ) <= bv_val(ctx, (d-1)÷2, _range2b(n)))

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


function color_x_s(d::Integer, idx::Integer)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17

	s = zeros(Bool, 2*n)

	for j in _xadj(d, idx)
		s[j] = true
	end

	s
end

@qprog color_x_m (n, d, idx) begin
    b = _xadj(d, idx)

    len_b = length(b)
    cat_qubits = [n+i for i in 1:len_b]
    verify_qubit = n+len_b+1
    #prepare_cat(cat_qubits, verify_qubit, d)
    CatPreparationMod(cat_qubits)
    res = Vector{Z3.Expr}(undef, len_b)
    for i in 1:len_b
        CNOT(cat_qubits[i], b[i])
    end

    for i in 1:len_b
        res[i] = MX(cat_qubits[i])
    end

    res = reduce(⊻, res)

    res
end

function color_z_s(d::Integer, idx::Integer)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17

	s = zeros(Bool, 2*n)

	for j in (_zadj(d, idx) .+ n)
		s[j] = true
	end

	s
end

@qprog color_z_m (n, d, idx) begin
    b = _zadj(d, idx)

    len_b = length(b)
    cat_qubits = [n+i for i in 1:len_b]
    verify_qubit = n+len_b+1
    #prepare_cat(cat_qubits, verify_qubit, d)
    CatPreparationMod(cat_qubits)
    res = Vector{Z3.Expr}(undef, len_b)
    for i in 1:len_b
        CZ(cat_qubits[i], b[i])
    end

    for i in 1:len_b
        res[i] = MX(cat_qubits[i])
    end

    res = reduce(⊻, res)

    res
end

function _color_lx(d::Integer)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17
    lx = d==3 ? [1,2,6] : [2,4,11,13,16]

    lx
end

function _color_lz(d::Integer)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17
    lz = d==3 ? [1,2,6] : [2,4,11,13,16]

	lz
end



function color_lx(d::Integer)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17

    lx=_color_lx(d)

    s = zeros(Bool, 2*n)

	@inbounds @simd for i in lx
		s[i] = true
	end

	s
end

function color_lz(d::Integer)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17

    lz=_color_lz(d)

   	s = zeros(Bool, 2*n)

	@inbounds @simd for i in lz
		s[n+i] = true
	end

	s
end

@qprog _color_decoder (n, d) begin

    t = Int(floor((d-1)/2))
    #t = t - 1

    @repeat begin

        s_x = Matrix{Z3.Expr}(undef, (n-1)÷2, t+1)
        s_z = Matrix{Z3.Expr}(undef, (n-1)÷2, t+1)


        for i in 1:t+1
            for j in 1:(n-1)÷2
                #s_x[j,i] = color_x_m(d, j)
                #s_z[j,i] = color_z_m(d, j)
                b = _xadj(d, j)
                s_x[j,i] = MultiPauliMeasurement(b, ['X' for kk in 1:length(b)])
                b = _zadj(d, j)
                s_z[j,i] = MultiPauliMeasurement(b, ['Z' for kk in 1:length(b)])
            end
        end

        check_eq_x = Vector{Z3.Expr}(undef, t)
        check_eq_z = Vector{Z3.Expr}(undef, t)

        for i in 1:t
            check_eq_x[i] = reduce(|, [(s_x[j,i] ⊻ s_x[j,i+1]) for j in 1:(n-1)÷2])
            check_eq_z[i] = reduce(|, [(s_z[j,i] ⊻ s_z[j,i+1]) for j in 1:(n-1)÷2])
        end

        check_eq = (reduce(|, check_eq_x) | reduce(|, check_eq_z))

    end :until (check_eq == bv_val(ctx, 0, 1))

    r_x = mwpm(d, s_x[:, t+1], "X")
    r_z = mwpm(d, s_z[:, t+1], "Z")

    for j in 1:n
        #sZ(j, r_x[j])
        #sX(j, r_z[j])
        sPauli(j, r_z[j], r_x[j])
    end

end

@qprog color_decoder (n,d) begin

    _color_decoder(n,d)

    ancilla = [n+1, n+2, n+3, n+4, n+5]
    for i in 1:5
        INIT(ancilla[i])
    end

end

@qprog color_identity (n,d) begin

    for i in 1:n
        Identity(i)
    end

end

@qprog color_CNOT (n,d) begin

    for i in 1:n
        CNOT(i, i+n)
    end

end

@qprog color_lx_m (n,d) begin
    b = _color_lx(d)

    cat_qubits = [n+i for i in 1:d]
    verify_qubit = n+d+1
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

@qprog color_lz_m (n,d) begin
    b = _color_lz(d)

    cat_qubits = [n+i for i in 1:d]
    verify_qubit = n+d+1
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
#    @assert d==3 || d==5
#    n = d==3 ? 7 : 17
#
#    # claim
#    ϕ₁ = bool_val(ctx, true)
#    adj = s_type == "X" ? _xadj : _zadj
#    r = [alloc_symb(ctx, "recovery_$(s_type)_$(j)") for j in 1:n]
#    for j in 1:(n-1)÷2
#        ϕ₁ = ϕ₁ & (s[j] == reduce(⊻, r[[adj(d, j)...]]))
#    end
#    for j in 1:length(ml)
#        ϕ₁ = ϕ₁ & (ml[j] == reduce(⊻, r[[ml_adj[j]...]]))
#    end
#
#    (r, ϕ₁, bool_val(ctx, true), bool_val(ctx, true))
#end

function mwpm_full(d::Integer, s, s_type, ml, ml_adj)

    @assert d==3 || d==5
    n = d==3 ? 7 : 17

    num_qubits = n
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


@qprog _color_prepare_0 (n,d) begin

    t = Int(floor((d-1)/2))
    #t = t - 1

    for i in 1:n
        INIT(i)
    end

    @repeat begin

        s_x = Matrix{Z3.Expr}(undef, (n-1)÷2, t+1)
        s_z = Matrix{Z3.Expr}(undef, (n+1)÷2, t+1)


        for i in 1:t+1
            for j in 1:(n-1)÷2
                #s_x[j,i] = color_x_m(d, j)
                #s_z[j,i] = color_z_m(d, j)
                b = _xadj(d, j)
                s_x[j,i] = MultiPauliMeasurement(b, ['X' for kk in 1:length(b)])
                b = _zadj(d, j)
                s_z[j,i] = MultiPauliMeasurement(b, ['Z' for kk in 1:length(b)])
            end
            #s_z[(n+1)÷2,i] = color_lz_m(d)
            b = _color_lz(d)
            s_z[(n+1)÷2,i] = MultiPauliMeasurement(b, ['Z' for kk in 1:length(b)])
        end

        check_eq_x = Vector{Z3.Expr}(undef, t)
        check_eq_z = Vector{Z3.Expr}(undef, t)

        for i in 1:t
            check_eq_x[i] = reduce(|, [(s_x[j,i] ⊻ s_x[j,i+1]) for j in 1:(n-1)÷2])
            check_eq_z[i] = reduce(|, [(s_z[j,i] ⊻ s_z[j,i+1]) for j in 1:(n+1)÷2])
        end

        check_eq = (reduce(|, check_eq_x) | reduce(|, check_eq_z))

    end :until (check_eq == bv_val(ctx, 0, 1))

    lz_adj = [_color_lz(d)]
    r_x = mwpm_full(d, s_x[1:(n-1)÷2, t+1], "X", [], [])
    r_z = mwpm_full(d, s_z[1:(n-1)÷2, t+1], "Z", s_z[(n+1)÷2:(n+1)÷2, t+1], lz_adj)

    for j in 1:n
        #sZ(j, r_x[j])
        #sX(j, r_z[j])
        sPauli(j, r_z[j], r_x[j])
    end

end

@qprog color_prepare_0 (n,d) begin

    _color_prepare_0(n,d)

    ancilla = [n+i for i in 1:max(5,d+1)]
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

@qprog color_measurement (n,d) begin

    t = Int(floor((d-1)/2))

    m_lz = Vector{Z3.Expr}(undef, 2*t+1)

    for i in 1:2*t+1
        #m_lz[i] = color_lz_m(d)
        b = _color_lz(d)
        m_lz[i] = MultiPauliMeasurement(b, ['Z' for kk in 1:length(b)])
        _color_decoder(n,d)
    end

    final_res = majority(m_lz)

end


function check_color_measurement(d::Integer, NERRS::Integer, slv_backend_cmd::Cmd)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = n
        num_ancilla = max(5, d+1)
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)
	    lz = _bv_const(ctx, "lz")

	    @simd for i in 1:(n-1)÷2
	    	stabilizer[i,:] = color_x_s(d, i)
	    	stabilizer[i+(n-1)÷2,:] = color_z_s(d, i)
	    	phases[i] = _bv_val(ctx, 0)
	    	phases[i+(n-1)÷2] = _bv_val(ctx, 0)
	    end

	    stabilizer[n,:] = color_lz(d)
	    phases[n] = lz

        ρ01 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ1 = copy(ρ01)

        σ = CState([(:d, d),
            (:color_measurement, color_measurement),
            (:_color_decoder, _color_decoder),
            (:color_z_m, color_z_m),
            (:color_x_m, color_x_m),
            (:color_lz_m, color_lz_m),
            (:_color_lz, _color_lz),
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

        cfg1 = SymConfig(color_measurement(n,d), σ, ρ1, NERRS)

        res = true
        cfgs1 = QuantSymEx(cfg1)
        for cfg in cfgs1
            if !check_FT(cfg.ρ, ρ01, cfg.ϕ, cfg.nerrs, cfg.NERRS, num_errors, nerrs_input, "measurement", slv_backend_cmd, meas_result=cfg.σ[:final_res], meas_gt=lz, use_z3=false)
                res = false
                break
            end
        end

    end

    t1 = time()

    res, t1-t0
end


function check_color_prepare(d::Integer, NERRS::Integer, slv_backend_cmd::Cmd)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = n
        num_ancilla = max(5, d+1)
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)

	    @simd for i in 1:(n-1)÷2
	    	stabilizer[i,:] = color_x_s(d, i)
	    	stabilizer[i+(n-1)÷2,:] = color_z_s(d, i)
	    	phases[i] = _bv_val(ctx, 0)
	    	phases[i+(n-1)÷2] = _bv_val(ctx, 0)
	    end

	    stabilizer[n,:] = color_lz(d)
	    phases[n] = _bv_val(ctx, 0)

        ρ0 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)

        @simd for i in 1:n
	    	stabilizer[i,:] = [0 for j in 1:2*n]
            stabilizer[i,n+i] = 1
	    	phases[i] = _bv_val(ctx, 0)
	    end

        ρ1 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)

        σ = CState([(:d, d),
            (:_color_prepare_0, _color_prepare_0),
            (:color_prepare_0, color_prepare_0),
            (:color_z_m, color_z_m),
            (:color_x_m, color_x_m),
            (:_color_lz, _color_lz),
            (:color_lz_m, color_lz_m),
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

        cfg1 = SymConfig(color_prepare_0(n,d), σ, ρ1, NERRS)

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



function check_color_decoder(d::Integer, NERRS::Integer, slv_backend_cmd::Cmd)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = n
        num_ancilla = 5
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)
	    lz = _bv_const(ctx, "lz")

	    @simd for i in 1:(n-1)÷2
	    	stabilizer[i,:] = color_x_s(d, i)
	    	stabilizer[i+(n-1)÷2,:] = color_z_s(d, i)
	    	phases[i] = _bv_val(ctx, 0)
	    	phases[i+(n-1)÷2] = _bv_val(ctx, 0)
	    end

	    stabilizer[n,:] = color_lz(d)
	    phases[n] = lz

        ρ01 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ1 = copy(ρ01)

        stabilizer[n,:] = color_lx(d)
	    phases[n] = _bv_val(ctx, 0)

        ρ02 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ2 = copy(ρ02)

        σ = CState([(:d, d),
            (:_color_decoder, _color_decoder),
            (:color_decoder, color_decoder),
            (:color_z_m, color_z_m),
            (:color_x_m, color_x_m),
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

        cfg1 = SymConfig(color_decoder(n,d), σ, ρ1, NERRS)

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

            cfg2 = SymConfig(color_decoder(n,d), σ, ρ2, NERRS)


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


function check_color_identity(d::Integer, NERRS::Integer, slv_backend_cmd::Cmd)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = n
        num_ancilla = 0
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)
	    lz = _bv_const(ctx, "lz")

	    @simd for i in 1:(n-1)÷2
	    	stabilizer[i,:] = color_x_s(d, i)
	    	stabilizer[i+(n-1)÷2,:] = color_z_s(d, i)
	    	phases[i] = _bv_val(ctx, 0)
	    	phases[i+(n-1)÷2] = _bv_val(ctx, 0)
	    end

	    stabilizer[n,:] = color_lz(d)
	    phases[n] = lz

        ρ01 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ1 = copy(ρ01)

        stabilizer[n,:] = color_lx(d)
	    phases[n] = _bv_val(ctx, 0)

        ρ02 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ2 = copy(ρ02)

        σ = CState([(:d, d),
            (:color_identity, color_identity),
            (:ctx, ctx)
        ])

        num_errors = Int(floor((d-1)÷2))


        b_num_main_qubits = _range2b(num_main_qubits)
        nerrs_input = bv_val(ctx, 0, b_num_main_qubits)
        for j in 1:num_main_qubits
            nerrs_input += zeroext(ctx, inject_symbolic_error(ρ1, j), b_num_main_qubits)
        end

        cfg1 = SymConfig(color_identity(n,d), σ, ρ1, NERRS)

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

            cfg2 = SymConfig(color_identity(n,d), σ, ρ2, NERRS)


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

function check_color_CNOT(d::Integer, NERRS::Integer, slv_backend_cmd::Cmd)
    @assert d==3 || d==5
    n = d==3 ? 7 : 17

    @info "Initailization Stage"
    t0 = time()
    begin

        num_main_qubits = 2*n
        num_ancilla = 0
        num_qubits = num_main_qubits + num_ancilla

        stabilizer = Matrix{Bool}(undef, num_main_qubits, 2*num_main_qubits)
	    phases = Vector{Z3.Expr}(undef, num_main_qubits)
	    lz1 = _bv_const(ctx, "lz1")
        lz2 = _bv_const(ctx, "lz2")

	    @simd for i in 1:(n-1)÷2
            x_s=color_x_s(d, i)
            z_s=color_z_s(d, i)
	        stabilizer[i,:] = vcat(vcat(x_s[1:n], zeros(Bool, n)), vcat(x_s[n+1:2*n], zeros(Bool, n)))
	    	stabilizer[i+(n-1)÷2,:] = vcat(vcat(z_s[1:n], zeros(Bool, n)), vcat(z_s[n+1:2*n], zeros(Bool, n)))
            stabilizer[i+n,:] = vcat(vcat(zeros(Bool, n), x_s[1:n]), vcat(zeros(Bool, n), x_s[n+1:2*n]))
            stabilizer[i+(3*n-1)÷2, :] = vcat(vcat(zeros(Bool, n), z_s[1:n]), vcat(zeros(Bool, n), z_s[n+1:2*n]))
	    	phases[i] = _bv_val(ctx, 0)
	    	phases[i+(n-1)÷2] = _bv_val(ctx, 0)
            phases[i+n] = _bv_val(ctx, 0)
            phases[i+(3*n-1)÷2] = _bv_val(ctx, 0)
	    end

        lz_s=color_lz(d)
	    stabilizer[n,:] = vcat(vcat(lz_s[1:n], zeros(Bool, n)), vcat(lz_s[n+1:2*n], zeros(Bool, n)))
	    phases[n] = lz1
        stabilizer[2*n,:] = vcat(vcat(zeros(Bool, n), lz_s[1:n]), vcat(zeros(Bool, n), lz_s[n+1:2*n]))
        phases[2*n] = lz2

        ρ01 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ1 = copy(ρ01)

        for i in 1:n
            CNOT(ρ01, i, i+n)
        end

        lx_s=color_lx(d)
        stabilizer[n,:] = vcat(vcat(lx_s[1:n], zeros(Bool, n)), vcat(lx_s[n+1:2*n], zeros(Bool, n)))
	    phases[n] = _bv_val(ctx, 0)
        stabilizer[2*n,:] = vcat(vcat(zeros(Bool, n), lx_s[1:n]), vcat(zeros(Bool, n), lx_s[n+1:2*n]))
        phases[2*n] = _bv_val(ctx, 0)

        ρ02 = from_stabilizer(num_main_qubits, stabilizer, phases, ctx, num_ancilla)
        ρ2 = copy(ρ02)

        for i in 1:n
            CNOT(ρ02, i, i+n)
        end

        σ = CState([(:d, d),
            (:color_CNOT, color_CNOT),
            (:ctx, ctx)
        ])

        num_errors = Int(floor((d-1)÷2))


        b_num_main_qubits = _range2b(num_main_qubits)
        nerrs_input = bv_val(ctx, 0, b_num_main_qubits)
        for j in 1:num_main_qubits
            nerrs_input += zeroext(ctx, inject_symbolic_error(ρ1, j), b_num_main_qubits)
        end

        cfg1 = SymConfig(color_CNOT(n,d), σ, ρ1, NERRS)

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

            cfg2 = SymConfig(color_CNOT(n,d), σ, ρ2, NERRS)


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



#d=5
@assert d==3 || d==5
@assert gadget in ["ec","prep","cnot","meas"]
n = d==3 ? 7 : 17
NERRS=11
#open("color_code.dat", "w") do io
  #println(io, "nq all")
println("nq all")

if gadget == "ec"
  res, all = check_color_decoder(d,NERRS,`bitwuzla -rwl 1`)
elseif gadget == "prep"
  res, all = check_color_prepare(d,NERRS,`bitwuzla -rwl 1`)
elseif gadget == "cnot"
  res, all = check_color_CNOT(d,NERRS,`bitwuzla -rwl 1`)
elseif gadget == "meas"
  res, all = check_color_measurement(d,NERRS,`bitwuzla -rwl 1`)
end

  #println("$(n+5) $(all)")
  #println(io, "$(n+5) $(all)")
println("Color Code, $(gadget), [n,k,d]=[$(n),1,$(d)], time=$(all)")
  #println(io, "Color Code, [n,k,d]=[$(n),1,$(d)], time=$(all)")
#end
