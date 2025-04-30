using Z3
using LinearAlgebra: I, nullspace, rank
using SimpleGF2: rref
using InvertedIndices

#include("config")
#export NERRS

@inline _mod(j) = (j - 1) >> 6 + 1
@inline _rem(j) = UInt64(0x1) << ((j - 1) & (0x3f))

_len2(j) = Int(ceil(log2(j))) + 1
_range2b(j) = Int(ceil(log2(j+1)))

@inline _bv_val(ctx, v::Integer) = bv_val(ctx, v, 1)
@inline _bv_const(ctx, s::String) = bv_const(ctx, s, 1)

_sum(ctx, e, num_qubits) = sum((x -> concat(bv_val(ctx, 0, _len2(num_qubits)), x)).(e))


function zeroext(ctx, x, n)
    @assert n >= 1
    if n == 1
        return x
    else
        return concat(bv_val(ctx, 0, n - 1), x)
    end
end

function addzeros(ctx, x, n)
    @assert n >= 0
    if n == 0
        return x
    else
        return concat(bv_val(ctx, 0, n), x)
    end
end

function _Pauli_weight(ctx::Z3.Context, Pauli_vec::Vector{Z3.Expr}; num_blocks::Integer = 1)

    @assert length(Pauli_vec) % 2 == 0
    num_qubits = length(Pauli_vec) ÷ 2
    @assert num_qubits % num_blocks == 0
    num_qubits_block = num_qubits ÷ num_blocks

    weight = Vector{Z3.Expr}(undef, num_blocks)
    for j in 1:num_blocks
        weight[j] = simplify(sum([zeroext(ctx, (Pauli_vec[(j-1)*num_qubits_block + i] | Pauli_vec[(j-1)*num_qubits_block + i + num_qubits]), _range2b(num_qubits_block)) for i = 1:num_qubits_block]))
    end

    return weight
end

struct SymStabilizerState <: AbstractSymQuantumState
    num_qubits::UInt32

    xzs::Matrix{UInt64}

    phases::Vector{Z3.Expr}

    ctx::Z3.Context

    num_ancilla::UInt32

    SymStabilizerState(num_qubits::Integer, Tableau::Matrix{Bool}, phases::Vector{Z3.Expr}, ctx::Z3.Context, num_ancilla::Integer) = begin
        @assert num_qubits > num_ancilla
        @assert size(Tableau) == (2 * num_qubits, 2 * num_qubits)
        @assert length(phases) == 2 * num_qubits

        len = num_qubits >> 6 + 1
        xzs = zeros(UInt64, 2 * len, 2 * num_qubits + 1)

        @simd for i in 1:2*num_qubits
            for j in 1:num_qubits
                j6 = _mod(j)
                pw = _rem(j)
                if ~iszero(Tableau[i, j])
                    xzs[j6, i] |= pw
                end
                if ~iszero(Tableau[i, j+num_qubits])
                    xzs[j6+len, i] |= pw
                end
            end
        end

        new(num_qubits, xzs, vcat(phases, _bv_val(ctx, 0)), ctx, num_ancilla)
    end

    SymStabilizerState(num_qubits::Integer, Tableau::Matrix{Bool}, Phases::Vector{Bool}, ctx::Z3.Context, num_ancilla::Integer) = begin
        phases = Vector{Z3.Expr}(undef, 2 * num_qubits)
        for j in 1:2*num_qubits
            phases[j] = _bv_val(ctx, 1 * Phases[j])
        end

        SymStabilizerState(num_qubits, Tableau, phases, ctx, num_ancilla)
    end

    #=SymStabilizerState(num_qubits::Integer, ctx::Z3.Context) = begin
        Tableau = Matrix{Bool}(I, 2*num_qubits, 2*num_qubits)
        Phases = zeros(Bool, 2*num_qubits)

        SymStabilizerState(num_qubits, Tableau, Phases, ctx)
    end=#

    SymStabilizerState(q::SymStabilizerState) = begin
        new(q.num_qubits, copy(q.xzs), copy(q.phases), q.ctx, q.num_ancilla)
    end

    SymStabilizerState(num_qubits::Integer, ctx::Z3.Context, num_ancilla::Integer) = begin
        Tableau = Matrix{Bool}(I, 2 * num_qubits, 2 * num_qubits)
        phases = [_bv_val(ctx, 0) for j in 1:2*num_qubits]
        SymStabilizerState(num_qubits, Tableau, phases, ctx, num_ancilla)
    end
end

Base.copy(q::SymStabilizerState) = SymStabilizerState(q)

function update!(q::SymStabilizerState, q0::SymStabilizerState)
    q.xzs[:] = q0.xzs
    q.phases[:] = q0.phases
end

@inline function rowset!(q::SymStabilizerState, i, b)
    len = size(q.xzs, 1) ÷ 2

    @inbounds @simd for j in 1:size(q.xzs, 1)
        q.xzs[j, i] = 0
    end
    q.phases[i] = _bv_val(q.ctx, 0)

    if b <= q.num_qubits
        q.xzs[_mod(b), i] = _rem(b)
    else
        q.xzs[len+_mod(b - q.num_qubits), i] = _rem(b - q.num_qubits)
    end

    nothing
end

@inline function rowcopy!(q::SymStabilizerState, i, j)
    (i == j) && return
    q.phases[i] = q.phases[j]
    @inbounds @simd for k in 1:size(q.xzs, 1)
        q.xzs[k, i] = q.xzs[k, j]
    end

    nothing
end

@inline function rowswap!(q::SymStabilizerState, i, j)
    (i == j) && return
    q.phases[i], q.phases[j] = q.phases[j], q.phases[i]
    @inbounds @simd for k in 1:size(q.xzs, 1)
        q.xzs[k, i], q.xzs[k, j] = q.xzs[k, j], q.xzs[k, i]
    end

    nothing
end

function rowmult!(q::SymStabilizerState, i, j)
    len = size(q.xzs, 1) ÷ 2
    r = q.xzs[:, i]
    l = q.xzs[:, j]

    cnt1 = zero(q.xzs[1, 1])
    cnt2 = zero(q.xzs[1, 1])

    @inbounds @simd for k in 1:len
        x1, x2, z1, z2 = l[k], r[k], l[k+len], r[k+len]
        q.xzs[k, i] = newx1 = x1 ⊻ x2
        q.xzs[k+len, i] = newz1 = z1 ⊻ z2
        x1z2 = x1 & z2
        anti_comm = (x2 & z1) ⊻ x1z2
        cnt2 ⊻= (cnt1 ⊻ newx1 ⊻ newz1 ⊻ x1z2) & anti_comm
        cnt1 ⊻= anti_comm
    end

    extra_phase = ((count_ones(cnt1) ⊻ (count_ones(cnt2) << 1)) & 0x3)

    q.phases[i] = simplify(_bv_val(q.ctx, extra_phase ÷ 2) ⊻ q.phases[i] ⊻ q.phases[j])

    nothing
end

function _canonicalize_mat(mat)
    num_qubits = size(mat, 2) ÷ 2
    num_rows = size(mat, 1)

    rest_j = UInt32[]

    mat = vcat(zeros(typeof(mat[1,1]), num_qubits*2-num_rows, num_qubits*2), mat)

    i = 2 * num_qubits - num_rows + 1
    for j in 1 : 2 * num_qubits
        k = findfirst(ii -> mat[ii, j] != 0, i:2*num_qubits)
        if k !== nothing
            k = k + i - 1
            tmp = mat[k, :]
            mat[k, :] = mat[i, :]
            mat[i, :] = tmp
            for k2 in vcat(2*num_qubits-num_rows+1:i-1, i+1:2*num_qubits)
                if ~iszero(mat[k2, j])
                    mat[k2, :] = mat[k2, :] .⊻ mat[i, :]
                end
            end
            i += 1
        else
            push!(rest_j, j)
        end
    end

    i = 1
    for j in rest_j
        mat[i, j] = 1
        i += 1
    end

    return mat
end

function _extend_rows(mat)
    num_columns = size(mat, 2)
    num_rows = size(mat, 1)
    @assert num_columns >= num_rows

    mat_original = mat

    rest_j = UInt32[]

    mat = vcat(mat, zeros(typeof(mat[1,1]), num_columns-num_rows, num_columns))

    i = 1
    for j in 1 : num_columns
        k = findfirst(ii -> mat[ii, j] != 0, i:num_rows)
        if k !== nothing
            k = k + i - 1
            tmp = mat[k, :]
            mat[k, :] = mat[i, :]
            mat[i, :] = tmp
            for k2 in vcat(1:i-1, i+1:num_rows)
                if ~iszero(mat[k2, j])
                    mat[k2, :] = mat[k2, :] .⊻ mat[i, :]
                end
            end
            i += 1
        else
            push!(rest_j, j)
        end
    end

    i = num_rows + 1
    for j in rest_j
        mat[i, j] = 1
        i += 1
    end

    return vcat(mat_original[1:num_rows,:], mat[num_rows+1:num_columns,:])
end



function _canonicalize_gott!(q::SymStabilizerState)
    len = size(q.xzs, 1) ÷ 2
    rest_j = UInt32[]
    perms = Tuple{UInt32,UInt32}[]

    @inbounds @simd for i in 1:q.num_qubits
        for j in 1:len
            q.xzs[j, i] = 0
            q.xzs[j+len, i] = 0
        end
        q.phases[i] = _bv_val(q.ctx, 0)
    end

    i = q.num_qubits + 1
    for j in 1:q.num_qubits
        j6 = _mod(j)
        pwj = _rem(j)
        k = findfirst(ii -> q.xzs[j6, ii] & pwj != 0, i:2*q.num_qubits)
        if k !== nothing
            k = k + i - 1
            rowswap!(q, k, i)
            push!(perms, (k, i))
            for k2 in vcat(q.num_qubits+1:i-1, i+1:2*q.num_qubits)
                if ~iszero(q.xzs[j6, k2] & pwj)
                    rowmult!(q, k2, i)
                end
            end
            q.xzs[j6+len, i-q.num_qubits] ⊻= pwj
            i += 1
        else
            push!(rest_j, j)
        end
    end

    for j in rest_j
        j6 = _mod(j)
        pwj = _rem(j)
        k = findfirst(ii -> q.xzs[j6+len, ii] & pwj != 0, i:2*q.num_qubits)
        if k !== nothing
            k = k + i - 1
            rowswap!(q, k, i)
            push!(perms, (k, i))
            for k2 in vcat(q.num_qubits+1:i-1, i+1:2*q.num_qubits)
                if ~iszero(q.xzs[j6+len, k2] & pwj)
                    rowmult!(q, k2, i)
                end
            end
            q.xzs[j6, i-q.num_qubits] ⊻= pwj
            i += 1
        end
    end

    #for (k, i) in reverse(perms)
    #    rowswap!(q, k, i)
    #    rowswap!(q, k - q.num_qubits, i - q.num_qubits)
    #end

    nothing
end

function add_ancilla(stabilizer::Matrix{Bool}, phases::Vector{Z3.Expr}, num_ancilla::Integer, ctx::Z3.Context)

    num_r, num_c = size(stabilizer)
    @assert num_r * 2 == num_c
    @assert length(phases) == num_r

    stabilizer_ancilla = hcat(hcat(stabilizer[:, 1:num_r], zeros(Bool, num_r, num_ancilla)), hcat(stabilizer[:, num_r+1:2*num_r], zeros(Bool, num_r, num_ancilla)))
    stabilizer_ancilla = vcat(stabilizer_ancilla, zeros(Bool, num_ancilla, num_c + 2 * num_ancilla))
    for j in 1:num_ancilla
        stabilizer_ancilla[num_r+j, 2*num_r+num_ancilla+j] = 1
    end

    phases_ancilla = Vector{Z3.Expr}(undef, num_ancilla)
    for j in 1:num_ancilla
        phases_ancilla[j] = _bv_val(ctx, 0)
    end
    phases_ancilla = vcat(phases, phases_ancilla)

    return stabilizer_ancilla, phases_ancilla

end

function from_stabilizer(num_main_qubits::Integer, Stabilizer::Matrix{Bool}, phases1::Vector{Z3.Expr}, ctx::Z3.Context, num_ancilla::Integer=0)

    Stabilizer, phases1 = add_ancilla(Stabilizer, phases1, num_ancilla, ctx)
    num_qubits = num_main_qubits + num_ancilla

    Tableau = vcat(zeros(Bool, num_qubits, 2 * num_qubits), Stabilizer)
    phases0 = Vector{Z3.Expr}(undef, num_qubits)
    for j in 1:num_qubits
        phases0[j] = _bv_val(ctx, 0)
    end
    phases = vcat(phases0, phases1)

    result = SymStabilizerState(num_qubits, Tableau, phases, ctx, num_ancilla)

    _canonicalize_gott!(result)

    result
end

function logical_operators(H1, H2)
    n = size(H1, 2)
    X = rref(H1)
    nx = rank(X)
    X_idxs = [findfirst(!iszero, X[j, :]) for j in 1:nx]
    Z = rref(H2[:, Not(X_idxs)])
    nz = rank(Z)
    Z_idxs = [[1:n...][Not(X_idxs)][findfirst(!iszero, Z[j, :])] for j in 1:nz]
    nl = n - nx - nz
    L = zeros(GF2, nl, n)
    L[1:nl, X_idxs] = X[1:nx, Not([X_idxs; Z_idxs])]'
    L[1:nl, Not([X_idxs; Z_idxs])] += I

    L
end

function from_css_code(HX, HZ, ctx::Z3.Context;num_ancilla=0)
    n = size(HX, 2)

    X = rref(HX)
    nx = rank(X)
    X = X[1:nx, :]

    Z = rref(HZ)
    nz = rank(Z)
    Z = Z[1:nz, :]

    LZ = logical_operators(X, Z)
    LX = logical_operators(Z, X)
    nl = size(LZ, 1)
    dx = minimum([length(findall(!iszero, LX[j, :])) for j in 1:nl])
    dz = minimum([length(findall(!iszero, LZ[j, :])) for j in 1:nl])
    println("[[n, k, dx, dz]] = [[$(n), $(nl), dx<$(dx), dz<$(dz)]]")

    stabilizer1 = Matrix{Bool}([[X; LX] zeros(GF2, nx + nl, n); zeros(GF2, nz, n) Z])
    phases1 = [_bv_val(ctx, 0) for j in 1:n]
    for j in 1:nl
        phases1[nx+j] = _bv_const(ctx, "lx$(j)")
    end
    ρ1 = from_stabilizer(n, stabilizer1, phases1, ctx, num_ancilla)

    stabilizer2 = Matrix{Bool}([X zeros(GF2, nx, n); zeros(GF2, nz + nl, n) [Z; LZ]])
    phases2 = [_bv_val(ctx, 0) for j in 1:n]
    for j in 1:nl
        phases2[nx+nz+j] = _bv_const(ctx, "lz$(j)")
    end
    ρ2 = from_stabilizer(n, stabilizer2, phases2, ctx, num_ancilla)

    ρ1, ρ2, dx, dz
end

function print_full_tableau(q::SymStabilizerState)
    len = size(q.xzs, 1) ÷ 2

    for i in 1:2*q.num_qubits
        for j in 1:q.num_qubits
            j6 = _mod(j)
            pwj = _rem(j)
            print((q.xzs[j6, i] & pwj) >> ((j - 1) & (0x3f)))
        end
        for j in 1:q.num_qubits
            j6 = _mod(j)
            pwj = _rem(j)
            print((q.xzs[j6+len, i] & pwj) >> ((j - 1) & (0x3f)))
        end
        println(" | ", simplify(q.phases[i]))
        if i == q.num_qubits
            print("\n")
        end
    end
    nothing
end

function output_stabilizer_tableau(q::SymStabilizerState)
    len = size(q.xzs, 1) ÷ 2

    stabilizer_tableau = zeros(UInt64, q.num_qubits, 2 * q.num_qubits)
    for i in q.num_qubits+1:2*q.num_qubits
        for j in 1:q.num_qubits
            j6 = _mod(j)
            pwj = _rem(j)
            stabilizer_tableau[i-q.num_qubits, j] = (q.xzs[j6, i] & pwj) >> ((j - 1) & (0x3f))
        end
        for j in 1:q.num_qubits
            j6 = _mod(j)
            pwj = _rem(j)
            stabilizer_tableau[i-q.num_qubits, j+q.num_qubits] = (q.xzs[j6+len, i] & pwj) >> ((j - 1) & (0x3f))
        end
    end
    return stabilizer_tableau
end

function output_destabilizer_tableau(q::SymStabilizerState)
    len = size(q.xzs, 1) ÷ 2

    destabilizer_tableau = zeros(Bool, 2 * q.num_qubits, 2 * q.num_qubits)
    for i in 1:q.num_qubits
        for j in 1:q.num_qubits
            j6 = _mod(j)
            pwj = _rem(j)
            destabilizer_tableau[i, j] = (q.xzs[j6, i] & pwj) >> ((j - 1) & (0x3f))
        end
        for j in 1:q.num_qubits
            j6 = _mod(j)
            pwj = _rem(j)
            destabilizer_tableau[i, j+q.num_qubits] = (q.xzs[j6+len, i] & pwj) >> ((j - 1) & (0x3f))
        end
    end
    for i in q.num_qubits+1:2*q.num_qubits
        for j in 1:q.num_qubits
            j6 = _mod(j)
            pwj = _rem(j)
            destabilizer_tableau[i, j] = (q.xzs[j6, i] & pwj) >> ((j - 1) & (0x3f))
        end
        for j in 1:q.num_qubits
            j6 = _mod(j)
            pwj = _rem(j)
            destabilizer_tableau[i, j+q.num_qubits] = (q.xzs[j6+len, i] & pwj) >> ((j - 1) & (0x3f))
        end
    end

    return destabilizer_tableau
end



function CNOT!(q::SymStabilizerState, b, c)
    len = size(q.xzs, 1) ÷ 2
    b6 = _mod(b)
    c6 = _mod(c)
    pwb = _rem(b)
    pwc = _rem(c)

    @inbounds @simd for j in 1:2*q.num_qubits
        x1, z1, x2, z2 = q.xzs[b6, j] & pwb != 0, q.xzs[b6+len, j] & pwb != 0, q.xzs[c6, j] & pwc != 0, q.xzs[c6+len, j] & pwc != 0
        if x1
            q.xzs[c6, j] ⊻= pwc
        end
        if z2
            q.xzs[b6+len, j] ⊻= pwb
        end
        if (x1 && z1 && x2 && z2) || (x1 && z2 && ~(z1 || x2))
            q.phases[j] = q.phases[j] ⊻ _bv_val(q.ctx, 1)
            q.phases[j] = simplify(q.phases[j])
        end
    end

    nothing
end

function H!(q::SymStabilizerState, b)
    len = size(q.xzs, 1) ÷ 2
    b6 = _mod(b)
    pw = _rem(b)

    @inbounds @simd for j in 1:2*q.num_qubits
        x, z = q.xzs[b6, j] & pw, q.xzs[b6+len, j] & pw
        q.xzs[b6, j] ⊻= x ⊻ z
        q.xzs[b6+len, j] ⊻= x ⊻ z
        if x != 0 && z != 0
            q.phases[j] = q.phases[j] ⊻ _bv_val(q.ctx, 1)
            q.phases[j] = simplify(q.phases[j])
        end
    end

    nothing
end

function CZ!(q::SymStabilizerState, b, c)
    H!(q, c)
    CNOT!(q, b, c)
    H!(q, c)

    nothing
end


function S!(q::SymStabilizerState, b)
    len = size(q.xzs, 1) ÷ 2
    b6 = _mod(b)
    pw = _rem(b)

    @inbounds @simd for j in 1:2*q.num_qubits
        x, z = q.xzs[b6, j] & pw, q.xzs[b6+len, j] & pw
        q.xzs[b6+len, j] ⊻= x
        if x != 0 && z != 0
            q.phases[j] = q.phases[j] ⊻ _bv_val(q.ctx, 1)
            q.phases[j] = simplify(q.phases[j])
        end
    end

    nothing
end

function Identity!(q::SymStabilizerState, b)
    len = size(q.xzs, 1)
    nothing
end

function X!(q::SymStabilizerState, b)
    len = size(q.xzs, 1) ÷ 2
    b6 = _mod(b)
    pw = _rem(b)

    @inbounds @simd for j in 1:2*q.num_qubits
        x, z = q.xzs[b6, j] & pw, q.xzs[b6+len, j] & pw
        if ~iszero(z)
            q.phases[j] = q.phases[j] ⊻ _bv_val(q.ctx, 1)
            q.phases[j] = simplify(q.phases[j])
        end
    end

    nothing
end

function Z!(q::SymStabilizerState, b)
    len = size(q.xzs, 1) ÷ 2
    b6 = _mod(b)
    pw = _rem(b)

    @inbounds @simd for j in 1:2*q.num_qubits
        x, z = q.xzs[b6, j] & pw, q.xzs[b6+len, j] & pw
        if ~iszero(x)
            q.phases[j] = q.phases[j] ⊻ _bv_val(q.ctx, 1)
            q.phases[j] = simplify(q.phases[j])
        end
    end

    nothing
end

function Y!(q::SymStabilizerState, b)
    len = size(q.xzs, 1) ÷ 2
    b6 = _mod(b)
    pw = _rem(b)

    @inbounds @simd for j in 1:2*q.num_qubits
        x, z = q.xzs[b6, j] & pw, q.xzs[b6+len, j] & pw
        if ~iszero(x ⊻ z)
            q.phases[j] = q.phases[j] ⊻ _bv_val(q.ctx, 1)
            q.phases[j] = simplify(q.phases[j])
        end
    end

    nothing
end

function sX!(q::SymStabilizerState, b, s)
    len = size(q.xzs, 1) ÷ 2
    b6 = _mod(b)
    pw = _rem(b)

    @inbounds @simd for j in 1:2*q.num_qubits
        x, z = q.xzs[b6, j] & pw, q.xzs[b6+len, j] & pw
        if ~iszero(z)
            q.phases[j] = q.phases[j] ⊻ s
            q.phases[j] = simplify(q.phases[j])
        end
    end

    nothing
end

function sZ!(q::SymStabilizerState, b, s)
    len = size(q.xzs, 1) ÷ 2
    b6 = _mod(b)
    pw = _rem(b)

    @inbounds @simd for j in 1:2*q.num_qubits
        x, z = q.xzs[b6, j] & pw, q.xzs[b6+len, j] & pw
        if ~iszero(x)
            q.phases[j] = q.phases[j] ⊻ s
            q.phases[j] = simplify(q.phases[j])
        end
    end

    nothing
end

function sY!(q::SymStabilizerState, b, s)
    len = size(q.xzs, 1) ÷ 2
    b6 = _mod(b)
    pw = _rem(b)

    @inbounds @simd for j in 1:2*q.num_qubits
        x, z = q.xzs[b6, j] & pw, q.xzs[b6+len, j] & pw
        if ~iszero(x ⊻ z)
            q.phases[j] = q.phases[j] ⊻ s
            q.phases[j] = simplify(q.phases[j])
        end
    end

    nothing
end

function sPauli!(q::SymStabilizerState, b, s_x, s_z)

    sX!(q, b, s_x)
    sZ!(q, b, s_z)

    nothing
end



function M!(q::SymStabilizerState, b, sym_name::String)
    b6 = _mod(b)
    pw = _rem(b)
    p = findfirst(ii -> q.xzs[b6, ii+q.num_qubits] & pw != 0, 1:q.num_qubits)
    if p !== nothing
        rowcopy!(q, p, p + q.num_qubits)
        rowset!(q, p + q.num_qubits, b + q.num_qubits)

        res = alloc_symb(q.ctx, sym_name)

        q.phases[p+q.num_qubits] = res

        @inbounds @simd for j in vcat(1:p-1, p+1:2*q.num_qubits)
            if ~iszero(q.xzs[b6, j] & pw)
                rowmult!(q, j, p)
            end
        end

        return res
    else
        m = findfirst(ii -> q.xzs[b6, ii] & pw != 0, 1:q.num_qubits)
        rowcopy!(q, 2 * q.num_qubits + 1, m + q.num_qubits)

        @inbounds for j in m+1:q.num_qubits
            if ~iszero(q.xzs[b6, j] & pw)
                rowmult!(q, 2 * q.num_qubits + 1, j + q.num_qubits)
            end
        end

        return q.phases[2*q.num_qubits+1]
    end
end

function INIT!(q::SymStabilizerState, b, tmp_s)
    tmp_phase = M!(q, b, tmp_s)
    sX!(q, b, tmp_phase)

    nothing
    # return tmp_phase
end

function INITP!(q::SymStabilizerState, b, tmp_s)
    INIT!(q, b, tmp_s)
    H!(q, b)

    nothing
end

function MX!(q::SymStabilizerState, b, sym_name::String)
    H!(q, b)
    res = M!(q, b, sym_name)
    H!(q, b)

    return res
end

function MY!(q::SymStabilizerState, b, sym_name::String)
    Z!(q, b)
    S!(q, b)
    H!(q, b)
    res = M!(q, b, sym_name)
    H!(q, b)
    S!(q, b)

    return res
end

function DestructiveM!(q::SymStabilizerState, b, sym_name::String)
    res = M!(q, b, sym_name)

    return res
end

function DestructiveMX!(q::SymStabilizerState, b, sym_name::String)
    res = MX!(q, b, sym_name)

    return res
end

########

function INIT2CNOT12!(q::SymStabilizerState, b1, b2, tmp_s)

    INIT!(q, b2, tmp_s)
    CNOT!(q, b1, b2)

    nothing

end

function CNOT12DestructiveM2!(q::SymStabilizerState, b1, b2, sym_name::String)

    CNOT!(q, b1, b2)
    res = M!(q, b2, sym_name)

    return res
end

function CNOT12DestructiveMX1!(q::SymStabilizerState, b1, b2, sym_name::String)

    CNOT!(q, b1, b2)
    res = MX!(q, b1, sym_name)

    return res
end

function CZ12DestructiveMX1!(q::SymStabilizerState, b1, b2, sym_name::String)

    CZ!(q, b1, b2)
    res = MX!(q, b1, sym_name)

    return res
end

########

#################

function generate_cat_verification(d, num_cat_qubits)

    println("dddddddd")
    println(d)

    if num_cat_qubits < 4
        return []
    elseif num_cat_qubits == 4
        #non-FT
        #return [[1, 4],[2, 3]]

        #FT
        return [[3, 4]]
    else
        return [[i, i+1] for i in 1:num_cat_qubits-1]
    end

end

function CatPreparationMod!(q::SymStabilizerState, cat_qubits) #Ideal Cat Preparation, FT version is in example/FT_CatPreparation.jl

    INITP!(q, cat_qubits[1], "CatPreparation_1")
    for i in 2:length(cat_qubits)
        INIT2CNOT12!(q, cat_qubits[1], cat_qubits[i], "CatPreparation_$(i)")
    end

    nothing

end

function MultiPauliMeasurement!(q::SymStabilizerState, qubits, Pauli, sym_name)

    @assert length(qubits) == length(Pauli)

    if Pauli[1] == 'Z'
        nothing
    elseif Pauli[1] == 'X'
        H!(q, qubits[1])
    elseif Pauli[1] == 'Y'
        S!(q, qubits[1])
        Z!(q, qubits[1])
        H!(q, qubits[1])
    else
        @assert 1==0
    end

    for i in 2:length(qubits)
        if Pauli[i] == 'Z'
            CNOT!(q, qubits[i], qubits[1])
        elseif Pauli[i] == 'X'
            H!(q, qubits[i])
            CNOT!(q, qubits[i], qubits[1])
        elseif Pauli[i] == 'Y'
            S!(q, qubits[i])
            Z!(q, qubits[i])
            H!(q, qubits[i])
            CNOT!(q, qubits[i], qubits[1])
        else
            @assert 1==0
        end
    end

    res = M!(q, qubits[1], sym_name)

    for i in 2:length(qubits)
        if Pauli[i] == 'Z'
            CNOT!(q, qubits[i], qubits[1])
        elseif Pauli[i] == 'X'
            CNOT!(q, qubits[i], qubits[1])
            H!(q, qubits[i])
        elseif Pauli[i] == 'Y'
            CNOT!(q, qubits[i], qubits[1])
            H!(q, qubits[i])
            S!(q, qubits[i])
        else
            @assert 1==0
        end
    end

    if Pauli[1] == 'Z'
        nothing
    elseif Pauli[1] == 'X'
        H!(q, qubits[1])
    elseif Pauli[1] == 'Y'
        H!(q, qubits[1])
        S!(q, qubits[1])
    else
        @assert 1==0
    end

    return res

end

#################


CNOT, H, S, X, Y, Z, sX, sY, sZ, M, INIT, Identity, CZ, INITP, MX, sPauli, DestructiveM, DestructiveMX, CatPreparationMod, MultiPauliMeasurement = CNOT!, H!, S!, X!, Y!, Z!, sX!, sY!, sZ!, M!, INIT!, Identity!, CZ!, INITP!, MX!, sPauli!, DestructiveM!, DestructiveMX!, CatPreparationMod!, MultiPauliMeasurement!

INIT2CNOT12, CNOT12DestructiveM2, CNOT12DestructiveMX1, CZ12DestructiveMX1 = INIT2CNOT12!, CNOT12DestructiveM2!, CNOT12DestructiveMX1!, CZ12DestructiveMX1!

function inject_errors(q::SymStabilizerState, error_type::String)
    terms = Vector{Z3.Expr}(undef, q.num_qubits)
    sGate = error_type == "X" ? sX : sZ
    errors = [_bv_const(q.ctx, "$(error_type)_error_$(j)") for j in 1:q.num_qubits]
    for j in 1:q.num_qubits
        sGate(q, j, errors[j])
    end

    return errors
end

__allocvarid = 0
function alloc_symb(ctx::Z3.Context, prefix::String; len::Integer = 1)
    global __allocvarid
    __allocvarid += 1
    return bv_const(ctx, "$(prefix)_$(__allocvarid)", len)
end

function varid()
    return __allocvarid
end

function inject_symbolic_error(q::SymStabilizerState, target_qubit::Int)
    xerr_symb = alloc_symb(q.ctx, "symb_Xerror")
    zerr_symb = alloc_symb(q.ctx, "symb_Zerror")

    #sX!(q, target_qubit, xerr_symb & ~zerr_symb)
    #sY!(q, target_qubit, xerr_symb & zerr_symb)
    #sZ!(q, target_qubit, ~xerr_symb & zerr_symb)
    sX!(q, target_qubit, xerr_symb)
    sZ!(q, target_qubit, zerr_symb)

    return xerr_symb | zerr_symb
end

function inject_symbolic_Xerror(q::SymStabilizerState, target_qubit::Int)
    xerr_symb = alloc_symb(q.ctx, "symb_Xerror")
    #zerr_symb = alloc_symb(q, "symb_Zerror")

    #sX!(q, target_qubit, xerr_symb & ~zerr_symb)
    #sY!(q, target_qubit, xerr_symb & zerr_symb)
    #sZ!(q, target_qubit, ~xerr_symb & zerr_symb)
    sX!(q, target_qubit, xerr_symb)
    #sZ!(q, target_qubit, zerr_symb)

    return xerr_symb
end

function inject_symbolic_Zerror(q::SymStabilizerState, target_qubit::Int)
    #xerr_symb = alloc_symb(q, "symb_Xerror")
    zerr_symb = alloc_symb(q.ctx, "symb_Zerror")

    #sX!(q, target_qubit, xerr_symb & ~zerr_symb)
    #sY!(q, target_qubit, xerr_symb & zerr_symb)
    #sZ!(q, target_qubit, ~xerr_symb & zerr_symb)
    #sX!(q, target_qubit, xerr_symb)
    sZ!(q, target_qubit, zerr_symb)

    return zerr_symb
end



function inject_symbolic_error_SymPauli(q::SymStabilizerState, target_qubit::Int, control_sym::Z3.Expr)
    xerr_symb = alloc_symb(q.ctx, "symb_Xerror")
    zerr_symb = alloc_symb(q.ctx, "symb_Zerror")

    #sX!(q, target_qubit, xerr_symb & ~zerr_symb)
    #sY!(q, target_qubit, xerr_symb & zerr_symb)
    #sZ!(q, target_qubit, ~xerr_symb & zerr_symb)

    #sX!(q, target_qubit, xerr_symb & control_sym)
    #sZ!(q, target_qubit, zerr_symb & control_sym)

    #return (xerr_symb | zerr_symb) & control_sym

    sX!(q, target_qubit, xerr_symb)
    sZ!(q, target_qubit, zerr_symb)

    return xerr_symb | zerr_symb

end

@inline function _equal(a, b, ranges)
    e = true
    for j in ranges
        for i in axes(a, 1)
            e &= a[i, j] == b[i, j]
        end
    end
    e
end

"""return `true` if SAT"""
function smt_solve_z3(slv::Solver)
    #@info "z3 is used as smt solver"

    res = check(slv)

    #@info "z3 has solved the problem"

    if res == Z3.sat
        open("query.smt2", "w") do io
            println(io, to_smt2(slv, "sat"))
        end

        open("model.smt2", "w") do io
            println(io, get_model(slv))
        end

        return true
    else
        return false
    end
end

"""return `true` if SAT"""
function smt_solve_external(slv::Solver, command::Cmd, postfix::String)
    @info "'$(command)' is used as smt solver for $(postfix) case"

    smt2_file_name = "_temp_check_$(postfix)_"

    open(smt2_file_name * ".smt2", "w") do io
        println(io, "(set-logic ALL)")
        println(io, "(set-option :produce-models true)")
        println(io, to_smt2(slv, "unknown")[3:end])
        #println(io, slv)
        println(io, "(get-model)")
        println(io, "(exit)")
    end

    #replace signed with unsigned
    run(pipeline(`sed -i '' 's/bvsle/bvule/g' $(smt2_file_name*".smt2")`))
    run(pipeline(`sed -i '' 's/bvslt/bvult/g' $(smt2_file_name*".smt2")`))
    run(pipeline(`sed -i '' 's/bvsge/bvuge/g' $(smt2_file_name*".smt2")`))
    run(pipeline(`sed -i '' 's/bvsgt/bvugt/g' $(smt2_file_name*".smt2")`))


    res_string = read(pipeline(`$(command) $(smt2_file_name*".smt2")`), String)


    @info "'$(command)' has solved the problem"

    # should be SAT, since UNSAT is not occurred
    if ~occursin("unsat", res_string)
        open(smt2_file_name * ".output", "w") do io
            println(io, res_string)
        end
        @info "The assignment that generates the bug has been written to ./$(smt2_file_name).output"
        return true
    end

    return false
end

function check_FT(q1::SymStabilizerState, q2::SymStabilizerState, assumptions::Tuple{Z3.Expr, Z3.Expr, Z3.Expr}, nerrs::Z3.Expr, NERRS::Integer, num_errors::Int64, nerrs_input::Z3.Expr, FT_type::String, slv_backend_cmd::Cmd=`bitwuzla -rwl 0`; meas_result=0, meas_gt=0, num_blocks=1, use_z3=false, non_FT=false)
    if q1.num_qubits != q2.num_qubits
        @info "The number of qubits does not match"
        return false
    end

    if _range2b(errcnt()) > NERRS
        println("NERRS should be >= $(_range2b(errcnt()))")
        @assert 1 == 0
    end

    num_main_qubits = q1.num_qubits - q1.num_ancilla

    slv = Solver(q1.ctx)

    b_num_errors = _range2b(num_errors)
    b_num_main_qubits = _range2b(num_main_qubits)
    nerrs_compact = bv_const(q1.ctx, "nerrs_compact", b_num_errors)
    nerrs_input_compact = bv_const(q1.ctx, "nerrs_input_compact", b_num_errors)
    nerrs_all_compact = bv_const(q1.ctx, "nerrs_all_compact", b_num_errors)
    assumption_nerrs_compact = (nerrs == addzeros(q1.ctx, nerrs_compact, NERRS - b_num_errors))
    assumption_nerrs_input_compact = (nerrs_input == addzeros(q1.ctx, nerrs_input_compact, b_num_main_qubits - b_num_errors))
    assumption_nerrs_all_compact = (addzeros(q1.ctx, nerrs_compact, 1) + addzeros(q1.ctx, nerrs_input_compact, 1) == addzeros(q1.ctx, nerrs_all_compact, 1))
    assumption_num_errors = assumption_nerrs_compact & assumption_nerrs_input_compact & assumption_nerrs_all_compact & (nerrs_all_compact <= bv_val(q1.ctx, num_errors, b_num_errors))
    if non_FT == true
        assumption_num_errors = assumption_num_errors & (nerrs_compact == bv_val(q1.ctx, 0, b_num_errors))
    end


    if FT_type == "measurement"
        @assert typeof(meas_result) == Z3.Expr
        @assert typeof(meas_gt) == Z3.Expr
        measurement_condition = (meas_result == meas_gt)
        conjecture = assumption_num_errors & assumptions[1] & assumptions[3] & not(measurement_condition)
    else
        _canonicalize_gott!(q1)
        _canonicalize_gott!(q2)

        if ~_equal(q1.xzs, q2.xzs, q1.num_qubits+1:2*q1.num_qubits) #q1.num_qubits+1-q1.num_ancilla:2*q1.num_qubits-q1.num_ancilla)#ranges)
            @info "The Stabilizer does not match, the program is wrong even without error insertion"
            return false
        end

        ######## Original
        #stabilizer_tableau = output_stabilizer_tableau(q1)
        #@assert iszero(stabilizer_tableau[num_main_qubits + 1 : q1.num_qubits, 1 : q1.num_qubits + num_main_qubits])
        #for j in num_main_qubits + 1 : q1.num_qubits
        #    for k in q1.num_qubits + num_main_qubits + 1 : 2 * q1.num_qubits
        #        @assert stabilizer_tableau[j, k] == (j + q1.num_qubits == k)
        #    end
        #end

        #stabilizer_tableau_main = zeros(UInt64, num_main_qubits, 2 * num_main_qubits)
        #stabilizer_tableau_main[1 : num_main_qubits, 1 : num_main_qubits] = stabilizer_tableau[1 : num_main_qubits, 1 : num_main_qubits]
        #stabilizer_tableau_main[1 : num_main_qubits, num_main_qubits + 1 : 2 * num_main_qubits] = stabilizer_tableau[1 : num_main_qubits, q1.num_qubits + 1 : q1.num_qubits + num_main_qubits]

        #q1_phases_main = q1.phases[q1.num_qubits + 1 : q1.num_qubits + num_main_qubits]
        #q2_phases_main = q2.phases[q2.num_qubits + 1 : q2.num_qubits + num_main_qubits]
        #
        #err_phases = Vector{Z3.Expr}(undef, num_main_qubits)
        #Pauli_err = bv_const(q1.ctx, "Pauli_err", 2 * num_main_qubits)

        #Pauli_err_vec = Vector{Z3.Expr}(undef, 2 * num_main_qubits)
        #for j in 1 : 2 * num_main_qubits
        #    Pauli_err_vec[j] = extract(Pauli_err, j - 1, j - 1)
        #end

        #for k in 1 : num_main_qubits
        #    err_phases[k] = reduce(⊻, [stabilizer_tableau_main[k, j] & Pauli_err_vec[j] for j in 1 : 2 * num_main_qubits])
        #end

        #error_condition = reduce(&, [q1_phases_main[j] ⊻ err_phases[j] == q2_phases_main[j] for j in 1 : num_main_qubits])
        #########

        ######## Destabilizer table
        destabilizer_tableau = output_destabilizer_tableau(q1)
        @assert iszero(destabilizer_tableau[num_main_qubits + 1 : q1.num_qubits, vcat(1 : num_main_qubits , q1.num_qubits + 1 : 2*q1.num_qubits)])
        for j in num_main_qubits + 1 : q1.num_qubits
            for k in num_main_qubits + 1 : q1.num_qubits
                @assert destabilizer_tableau[j, k] == (j == k)
            end
        end

        destabilizer_tableau_main = zeros(UInt64, 2 * num_main_qubits, 2 * num_main_qubits)
        destabilizer_tableau_main[1 : num_main_qubits, 1 : num_main_qubits] = destabilizer_tableau[1 : num_main_qubits, 1 : num_main_qubits]
        destabilizer_tableau_main[1 : num_main_qubits, num_main_qubits + 1 : 2 * num_main_qubits] = destabilizer_tableau[1 : num_main_qubits, q1.num_qubits + 1 : q1.num_qubits + num_main_qubits]
        destabilizer_tableau_main[num_main_qubits + 1 : 2 * num_main_qubits, 1 : num_main_qubits] = destabilizer_tableau[q1.num_qubits + 1 : q1.num_qubits + num_main_qubits, 1 : num_main_qubits]
        destabilizer_tableau_main[num_main_qubits + 1 : 2 * num_main_qubits, num_main_qubits + 1 : 2 * num_main_qubits] = destabilizer_tableau[q1.num_qubits + 1 : q1.num_qubits + num_main_qubits, q1.num_qubits + 1 : q1.num_qubits + num_main_qubits]
        destabilizer_tableau_main_GF2 = GF2.(destabilizer_tableau_main)
        inv_destab = Matrix{UInt64}(inv(destabilizer_tableau_main_GF2))
        null_space_destab = Matrix{UInt64}(nullspace(destabilizer_tableau_main_GF2[num_main_qubits + 1 : 2 * num_main_qubits, 1 : 2 * num_main_qubits]))

        q1_phases_main = q1.phases[vcat(1 : num_main_qubits, q1.num_qubits + 1 : q1.num_qubits + num_main_qubits)]
        q2_phases_main = q2.phases[vcat(1 : num_main_qubits, q2.num_qubits + 1 : q2.num_qubits + num_main_qubits)]

        part_solution = Vector{Z3.Expr}(undef, 2 * num_main_qubits)
        for j in 1 : 2 * num_main_qubits
            part_solution[j] = simplify(reduce(⊻, [inv_destab[j, k] & (q1_phases_main[k] ⊻ q2_phases_main[k]) for k in num_main_qubits + 1 : 2 * num_main_qubits]))
        end

        coefs = bv_const(q1.ctx, "coefs", num_main_qubits)
        coefs_vec = Vector{Z3.Expr}(undef, num_main_qubits)
        for j in 1 : num_main_qubits
            coefs_vec[j] = extract(coefs, j - 1, j - 1)
        end

        Pauli_err_vec = Vector{Z3.Expr}(undef, 2 * num_main_qubits)
        for k in 1 : 2 * num_main_qubits
            Pauli_err_vec[k] = simplify(part_solution[k] ⊻ reduce(⊻, [null_space_destab[k, j] & coefs_vec[j] for j in 1 : num_main_qubits]))
        end
        ########

        if FT_type == "decoder"
            weight_condition = _Pauli_weight(q1.ctx, Pauli_err_vec)[1] <= addzeros(q1.ctx, nerrs_compact, b_num_main_qubits - b_num_errors)
        elseif FT_type == "gate"
            @assert num_main_qubits % num_blocks == 0
            num_qubits_block = num_main_qubits ÷ num_blocks
            b_num_qubits_block = _range2b(num_qubits_block)
            weight_condition = bool_val(q1.ctx, true)
            for j in 1 : num_blocks
                weight_condition = weight_condition & (_Pauli_weight(q1.ctx, Pauli_err_vec, num_blocks=num_blocks)[j] <= addzeros(q1.ctx, nerrs_all_compact, b_num_qubits_block - b_num_errors))
            end
        elseif FT_type == "prepare"
            weight_condition = _Pauli_weight(q1.ctx, Pauli_err_vec)[1] <= addzeros(q1.ctx, nerrs_compact, b_num_main_qubits - b_num_errors)
        else
            @assert 1==0
        end
        #conjecture = assumption_num_errors & assumptions[1] & assumptions[3] & forall(Pauli_err, not(error_condition & weight_condition))
        conjecture = assumption_num_errors & assumptions[1] & assumptions[3] & forall(coefs, not(weight_condition))
    end

    add(slv, conjecture)

    is_sat = if use_z3
        smt_solve_z3(slv)
    else
        smt_solve_external(slv, slv_backend_cmd, "FT_condition")
    end

    if is_sat
        println(">>> Fail!")
        return false
    else
        println(">>> Pass!")
    end

    return true
end
