using MacroTools: postwalk, prewalk, rmlines, @capture

const QProg = Expr

QEmpty = rmlines(quote end)

M_counts = [0]

all_symbols(x::Symbol) = [x]
all_symbols(e::Expr) = e.head == :tuple ? length(e.args) == 0 ? Symbol[] : vcat(map(all_symbols, e.args)...) : nothing

macro qprog(name, args, e::Expr)
    args = all_symbols(args)
    e = macroexpand(Main, e)
    e = postwalk(
        x -> @capture(x, M(b_)) ? :(M($(b), Expr(:string, $("M_$(name)_"), $(b), $("_$(M_counts[1]+=1)")))) : x,
        e
    )
    e = postwalk(
        x -> @capture(x, MX(b_)) ? :(MX($(b), Expr(:string, $("MX_$(name)_"), $(b), $("_$(M_counts[1]+=1)")))) : x,
        e
    )
    e = postwalk(
        x -> @capture(x, DestructiveM(b_)) ? :(DestructiveM($(b), Expr(:string, $("DestructiveM_$(name)_"), $(b), $("_$(M_counts[1]+=1)")))) : x,
        e
    )
    e = postwalk(
        x -> @capture(x, DestructiveMX(b_)) ? :(DestructiveMX($(b), Expr(:string, $("DestructiveMX_$(name)_"), $(b), $("_$(M_counts[1]+=1)")))) : x,
        e
    )
    e = postwalk(
        x -> @capture(x, CNOT12DestructiveM2(b_, c_)) ? :(CNOT12DestructiveM2($(b), $(c), Expr(:string, $("CNOT12DestructiveM2_$(name)_"), $(b), $("_"), $(c), $("_$(M_counts[1]+=1)")))) : x,
        e
    )
    e = postwalk(
        x -> @capture(x, CNOT12DestructiveMX1(b_, c_)) ? :(CNOT12DestructiveMX1($(b), $(c), Expr(:string, $("CNOT12DestructiveMX1_$(name)_"), $(b), $("_"), $(c), $("_$(M_counts[1]+=1)")))) : x,
        e
    )
    e = postwalk(
        x -> @capture(x, CZ12DestructiveMX1(b_, c_)) ? :(CZ12DestructiveMX1($(b), $(c), Expr(:string, $("CZ12DestructiveMX1_$(name)_"), $(b), $("_"), $(c), $("_$(M_counts[1]+=1)")))) : x,
        e
    )
    e = postwalk(
        x -> @capture(x, MultiPauliMeasurement(b_, c_)) ? :(MultiPauliMeasurement($(b), $(c), Expr(:string, $("MultiPauliMeasurement_$(name)_"), $(b), $("_"), $(c), $("_$(M_counts[1]+=1)")))) : x,
        e
    )
    body = Expr(:quote, postwalk(x -> x in args ? Expr(:$, x) : x, e))
    fn = quote
        function $(esc(name))($(args...))
            $body
        end
    end
    fn = prewalk(rmlines, fn)
    return fn
end

macro repeat(body::Expr, symb, condition)
    if symb != :(:until)
        error("expecting :until symbol, but got $(symb)")
    else
        return Expr(:repeat_until, esc(condition), esc(body))
    end
end
