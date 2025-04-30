using LoopVectorization
using LinearAlgebra: Adjoint, Transpose
using SimpleGF2 # https://github.com/scheinerman/SimpleGF2.jl

#import SimpleGF2: +, -, * 

#@inline +(x::GF2, y::GF2) = GF2(x.val != y.val)
#@inline -(x::GF2) = x
#@inline -(x::GF2, y::GF2) = x + y

#@inline *(x::GF2, y::GF2) = GF2(x.val & y.val)

@inline Base.UInt8(x::GF2) = x.val
@inline Base.conj(x::GF2) = x

@inline function Base.:(*)(A::Union{Adjoint{GF2, Matrix{GF2}}, Transpose{Matrix{GF2}}, Matrix{GF2}}, B::Union{Adjoint{GF2, Matrix{GF2}}, Transpose{Matrix{GF2}}, Matrix{GF2}})
    m, n = size(A)
    p, q = size(B)
    @assert n == p "matrix dimensions must agree"
    A = UInt8.(A)
    B = UInt8.(B)
    C = Matrix{UInt8}(undef, m, q)
    A_mul_B!(C, A, B)
    GF2.(C)
end

function A_mul_B!(C, A, B)
    @tturbo for n ∈ indices((C,B), 2), m ∈ indices((C,A), 1)
        Cmn = zero(eltype(C))
        for k ∈ indices((A,B), (2,1))
            Cmn += A[m,k] * B[k,n]
        end
        C[m,n] = Cmn
    end
end