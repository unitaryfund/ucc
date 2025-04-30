using StaticArrays

abstract type AbstractGroup end

abstract type AbstraLinearGroup <: AbstractGroup end

det(x::AbstraLinearGroup) = mod.(x.M[1,1]*x.M[2,2] - x.M[1,2]*x.M[2,1], x.p)

Base.:*(x::AbstraLinearGroup, y::AbstraLinearGroup) = typeof(x)(x.p, x.M * y.M)
Base.inv(x::AbstraLinearGroup) = typeof(x)(x.p, det(x)^(x.p-2) * SA[x.M[2,2] -x.M[1,2];-x.M[2,1] x.M[1,1]] )

struct L2 <: AbstraLinearGroup
    p::Int
    M::SMatrix{2,2,Int}

    L2(p, M) = new(p, mod.(M, p))
end

struct PL2 <: AbstraLinearGroup
    p::Int
    M::SMatrix{2,2,Int}

    PL2(p, M) = new(p, mod.(M, p))
end

function Proj(M::SMatrix{2,2,Int}, p)
    M = mod.(M, p)
    if M[1,1] > p>>1 || (M[1,1] == 0 && M[1,2] > p>>1)
        return M * SA[p-1 0; 0 p-1]
    end
    return M
end

Base.:*(x::PL2, y::PL2) = PL2(x.p, Proj(x.M * y.M, x.p))

Base.inv(x::PL2) = PL2(x.p, Proj(det(x)^(x.p-2) * SA[x.M[2,2] -x.M[1,2];-x.M[2,1] x.M[1,1]], x.p))

pgl2(p) = filter(
    x-> det(x) != 0,
    [
        [PL2(p, [a b;c d]) for a in 1:p>>1 for b in 0:p-1 for c in 0:p-1 for d in 0:p-1];
        [PL2(p, [0 b;c d]) for b in 1:p>>1 for c in 0:p-1 for d in 0:p-1]
    ]
)

psl2(p) = filter(
    x-> det(x) == 1,
    [
        [PL2(p, [a b;c d]) for a in 1:p>>1 for b in 0:p-1 for c in 0:p-1 for d in 0:p-1];
        [PL2(p, [0 b;c d]) for b in 1:p>>1 for c in 0:p-1 for d in 0:p-1]
    ]
)

function jacobi4squares(p, q)
	mod(p, 4) == 1 || @error "$(p) mod 4 != 1"

    res = Vector{PL2}(undef, p+1)
    i = mod(2^(q>>2), q)
    j = 0
	for a0 in 1:2:isqrt(p)
        h_a1 = isqrt(p-a0^2)
		for a1 in [0:2:h_a1;-2:-2:-h_a1]
            h_a2 = isqrt(p-a0^2-a1^2)
			for a2 in [0:2:h_a2;-2:-2:-h_a2]
                h_a3 = isqrt(p-a0^2-a1^2-a2^2)
				for a3 in [0:2:h_a3;-2:-2:-h_a3]
					if (a0^2+a1^2+a2^2+a3^2) == p
                        j+=1
                        res[j] = PL2(q, Proj(SA[a0+i*a1 a2+i*a3; -a2+i*a3 a0-i*a1], q))
					end
				end
			end
		end
	end
    res
end