from importlib.util import find_spec

if find_spec("juliacall") is None:
    raise ImportError(
        "The `ucc.ft` module requires optional julia extensions be present. Please install it via `pip install ucc[ft]`."
    )
