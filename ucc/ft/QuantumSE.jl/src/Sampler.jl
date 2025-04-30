using LoopVectorization
using SparseArrays
using Random: bitrand, rand!
using Z3

function bits_mul_s_uint8s!(C::Matrix{UInt64}, A::Matrix{UInt64}, B::AbstractSparseMatrix{UInt8, Int})
    rv = rowvals(B)
    M, N = size(C)
    @inbounds for n ∈ 1:N
        temp = zero(UInt64)
        @turbo for m in 1:M
            C[m, n] = temp
        end
        for k in nzrange(B, n)
            rvk = rv[k]
            @turbo for m in 1:M
                C[m, n] ⊻= A[m, rvk]
            end
        end
    end
end

function biased_bitrand(M, N, p)
    T = UInt16(floor(0xffff*p))
    C16 = Matrix{UInt16}(undef, M, N)
    rand!(C16)
    C = Matrix{UInt8}(undef, M, N)
    @tturbo for n in 1:N
        for m in 1:M
            C[m, n] = C16[m, n] > T ? false : true
        end
    end
    C
end

function Sampler(bv_expressions, p)
    bv_strings = String.(string.(bv_expressions))
    ns = length(bv_strings)
    errors = Vector{Vector{String}}(undef, ns)
    measures = Vector{Vector{String}}(undef, ns)
    b = Vector{UInt8}(undef, ns)
    @inbounds for j in 1:ns
        if match(r"#b1", bv_strings[j]) === nothing
            b[j] = UInt8(0)
        else
            b[j] = UInt8(1)
        end
        errors[j] = [m.match for m in collect(eachmatch(r"error_(\d+)", bv_strings[j]))]
        measures[j] = [m.match for m in collect(eachmatch(r"measure_(\d+)", bv_strings[j]))]
    end
    error_strings = unique(vcat(errors...))
    measure_strings = unique(vcat(measures...))
    n_errors = length(error_strings)
    n_measures = length(measure_strings)
    error_dicts = Dict([(error_strings[j], j) for j in 1:n_errors])
    measure_dicts = Dict([(measure_strings[j], j) for j in 1:n_measures])

    IH = [vcat([[error_dicts[s] for s in e] for e in errors]...);vcat([[n_errors+measure_dicts[s] for s in m] for m in measures]...);[n_errors+n_measures+1 for j in 1:ns]]
    JH = [vcat([[k for j in 1:length(errors[k])] for k in 1:ns]...);vcat([[k for j in 1:length(measures[k])] for k in 1:ns]...);[j for j in 1:ns]]
    nn = length(IH)
    VH = ones(UInt8, nn)
    VH[nn-ns+1:nn] = b

    ### n_errors = 0
    H = sparse(IH, JH, VH, n_errors+n_measures+1, ns)

    sampler = shots -> _Sampler(shots, H, n_measures, ns)
    precompile(sampler, (Int,))

    sampler
end

function _Sampler(shots, H, n_measures, ns)
    xz = rand(UInt64, (shots-1)>>6+1, n_measures+1)
    @inbounds @simd for j in axes(xz, 1)
        xz[j,n_measures+1] = typemax(UInt64)
    end
    samples = Matrix{UInt64}(undef, (shots-1)>>6+1, ns)
    bits_mul_s_uint8s!(samples, xz, H)
    samples
end

function parse_stim(stim_file_name::String, ctx)
    stim_file = readlines(stim_file_name)
    cmds = Vector{Tuple{Int64, String, Vector{Int64}}}(undef,length(stim_file))
    n_cmds = 0
    n_lines = length(stim_file)
    num_qubits = 0
    num_measures = 0
    for i in 1:n_lines
        tokens = split(stim_file[i], " ")
        n_tokens = length(tokens)
        j = 1
        while j <= n_tokens && tokens[j] == ""
            j += 1
        end
        if j > n_tokens
            continue
        elseif tokens[j][1] == '#'
            continue
        elseif tokens[j] in ["H", "S", "M", "CX"]
            n_cmds += 1
            k_l = j+1
            k_u = k_l
            while k_u <= n_tokens && tokens[k_u][1] != '#'
                k_u += 1
            end
            inds = [parse(Int, tokens[k]) for k in k_l:k_u-1]
            if tokens[j] == "M"
                num_measures += length(inds)
            end
            num_qubits = max(num_qubits, maximum(inds))
            cmds[n_cmds] = (i, tokens[j], inds)
        end
    end

    qs = SymStabilizerState(num_qubits, ctx)
    m_expressions = Vector{Z3.Expr}(undef, num_measures)
    j = j

    for k in 1:n_cmds
        cmd = cmds[k]
        if cmd[2] == "H"
            for b in cmd[3]
                H(qs, b)
            end
        elseif cmd[2] == "S"
            for b in cmd[3]
                S(qs, b)
            end
        elseif cmd[2] == "CX"
            for k in 1:2:length(cmd[3])
                CNOT(qs, cmd[3][k], cmd[3][k+1])
            end
        elseif cmd[2] == "M"
            for b in cmd[3]
                m_expressions[j] = M(qs, b, "measure_$(num_qubits*cmd[1]+b)")
                j += 1
            end
        end
    end

    m_expressions
end

