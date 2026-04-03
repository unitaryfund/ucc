import argparse

from . import __version__, supported_circuit_formats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ucc",
        description="Minimal CLI for the Unitary Compiler Collection.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the installed UCC version and exit.",
    )
    parser.add_argument(
        "--supported-circuit-formats",
        action="store_true",
        help="Print the circuit formats supported by qBraid/UCC and exit.",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.supported_circuit_formats:
        for format_name in sorted(supported_circuit_formats):
            print(format_name)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
