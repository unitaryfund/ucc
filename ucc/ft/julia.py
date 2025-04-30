import juliapkg
import juliacall as jc  # noqa

juliapkg.resolve()

from juliacall import Main as jl  # noqa


def cat_run():
    jl.seval('include("./ucc/ft/QuantumSE.jl/example/CatPreparation.jl")')
