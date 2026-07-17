from ucc._version import __version__ as __version__

__all__ = [
    "compile",
    "supported_circuit_formats",
    "UCCDefault1",
    "__version__",
]


def __getattr__(name):
    if name in {"compile", "supported_circuit_formats"}:
        from .compile import (
            compile as _compile,
            supported_circuit_formats as _supported_circuit_formats,
        )

        if name == "compile":
            return _compile
        return _supported_circuit_formats

    if name == "UCCDefault1":
        from .transpilers.ucc_defaults import UCCDefault1 as _UCCDefault1

        return _UCCDefault1

    raise AttributeError(f"module 'ucc' has no attribute '{name}'")
