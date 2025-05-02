from .julia import jl
from stim import PauliString, Tableau
import numpy as np
import math
import openqasm3
import openqasm3.ast as ast
from openqasm3.printer import Printer, PrinterState
from typing import List, Sequence, Any
import io
from dataclasses import dataclass


class QProgVisitor(Printer):
    """
    Visitor that converts the QASM3 program to an @qprog statement
    that works with QuantumSE.jl in Julia. This is very basic and makes
    specific assumptions about the QASM3 program, raising an error if
    there are any issues.

    For now, we assume the QASM3 program defines a single subroutine, that takes
    two qubit registers as arugments:

      def func(qubit[size] state, qubit ancilla) { BODY }

    The first argument is the state register and corresponds to the physical qubits
    that encode a logical qubit. The ancilla is additional qubits that are used to
    implement the application.

    TODO: Support multiple logical input qubits; larger sized ancilla etc.

    """

    def __init__(self, stream: io.TextIOBase):
        super().__init__(stream)
        self.func_name = None
        self.global_decls = set()

    def visit_Include(self, node: ast.Include, context: PrinterState) -> None:
        # Ignore the include statement when converting to Julia
        pass

    def visit_Program(self, node: ast.Program, context: PrinterState) -> None:
        for statement in node.statements:
            self.visit(statement, context)

    def _visit_statement_list(
        self,
        nodes: List[ast.Statement],
        context: PrinterState,
        prefix: str = "",
    ) -> None:
        # Same as as the base class, but doesn't print '{' and '}' which are not
        # supported in Julia.
        self.stream.write(prefix)
        self._end_line(context)
        with context.increase_scope():
            for statement in nodes:
                self.visit(statement, context)
        self._start_line(context)

    def visit_IntType(self, node: ast.IntType, context: PrinterState) -> None:
        # Julia capitalizes the first letter of the type
        self.stream.write("Int")
        if node.size is not None:
            # This won't work for arbitrary sizes; but can handle later if needed
            self.visit(node.size, context)

    def visit_UintType(
        self, node: ast.UintType, context: PrinterState
    ) -> None:
        # Julia capitalizes the first letter of the type
        self.stream.write("UInt")
        if node.size is not None:
            # This won't work for arbitrary sizes; but can handle later if needed
            self.visit(node.size, context)

    def visit_BoolType(
        self, node: ast.BoolType, context: PrinterState
    ) -> None:
        # Julia capitalizes the first letter of the type
        self.stream.write("Bool")

    def visit_BitType(self, node: ast.BitType, context: PrinterState) -> None:
        # treat bits directly as Bool's
        self.stream.write("Bool")
        if node.size is not None:
            raise ValueError("Bit type does not support size")

    def _visit_bit_init(
        self, node: ast.Expression, context: PrinterState
    ) -> None:
        # Convert bit initialization expressions to Z3 bitvector expressions for us
        # in symbolic execution of @qprog
        if isinstance(node, ast.IntegerLiteral):
            self.stream.write(f"bv_val(ctx, {node.value}, 1)")
        elif isinstance(node, ast.QuantumMeasurement):
            self.visit(node)
        else:
            raise ValueError(
                f"Unsupported bit initialization expression type: {type(node)}"
            )

    def visit_ClassicalDeclaration(
        self, node: ast.ClassicalDeclaration, context: PrinterState
    ) -> None:
        self._start_line(context)
        self.visit(node.identifier, context)
        # No type for Julia
        # self.stream.write("::")
        # self.visit(node.type)
        if node.init_expression is not None:
            self.stream.write(" = ")
            # For bit types, inject the Z3 bittype
            if isinstance(node.type, ast.BitType):
                self._visit_bit_init(node.init_expression, context)
            else:
                self.visit(node.init_expression, context)

        self._end_statement(context)

    def visit_ConstantDeclaration(
        self, node: ast.ConstantDeclaration, context: PrinterState
    ) -> None:
        self._start_line(context)
        self.stream.write("const ")
        self.visit(node.identifier, context)
        # No type for Julia
        # self.stream.write("::")
        # self.visit(node.type)
        self.stream.write(" = ")
        # For bit types, inject the Z3 bittype
        if isinstance(node.type, ast.BitType):
            self._visit_bit_init(node.init_expression, context)
        else:
            self.visit(node.init_expression, context)
        self._end_statement(context)

        # store global constant declarations
        if context.current_indent == 0:
            self.global_decls.add(node.identifier.name)

    def _visit_sequence_and_add_one(
        self,
        nodes: Sequence[ast.QASMNode],
        context: PrinterState,
        *,
        start: str = "",
        end: str = "",
        separator: str,
    ) -> None:
        if start:
            self.stream.write(start)
        for node in nodes[:-1]:
            self.stream.write("( ")
            self.visit(node, context)
            self.stream.write(" ) + 1 ")
            self.stream.write(separator)
        if nodes:
            self.stream.write("( ")
            self.visit(nodes[-1], context)
            self.stream.write(" ) + 1 ")
        if end:
            self.stream.write(end)

    def visit_IndexedIdentifier(
        self, node: ast.IndexedIdentifier, context: PrinterState
    ) -> None:
        # Julia uses 1-based indexing, but QASM is 0-based.
        # We need to convert the index to 1-based for Julia.

        self.visit(node.name, context)
        for index in node.indices:
            self.stream.write("[")
            if isinstance(index, ast.DiscreteSet):
                raise ValueError("DiscreteSet indexing not supported in Julia")
            else:
                self._visit_sequence_and_add_one(
                    index, context, separator=", "
                )
            self.stream.write("]")

    def visit_QuantumReset(
        self, node: ast.QuantumReset, context: PrinterState
    ) -> None:
        self._start_line(context)
        self.stream.write("INIT(")
        self.visit(node.qubits, context)
        self.stream.write(")")
        self._end_statement(context)

    def visit_QuantumGate(
        self, node: ast.QuantumGate, context: PrinterState
    ) -> None:
        self._start_line(context)
        self._visit_gate_identifier(node.name, context)
        if node.arguments:
            ## This may not work for all gates; can revist later if needed
            self._visit_sequence(
                node.arguments, context, start="(", end=")", separator=", "
            )
        self._visit_sequence(
            node.qubits, context, start="(", end=")", separator=", "
        )
        self._end_statement(context)

    def _visit_gate_identifier(
        self, node: ast.Identifier, context: PrinterState
    ) -> None:
        # Add gates as needed to map to the types in QuantumSE.jl/SymbolicStabilizer.jl
        translation = {"h": "H", "cx": "CNOT"}
        if node.name in translation:
            self.stream.write(translation[node.name])
        else:
            raise ValueError(f"Unknown gate identifier: {node.name}")

    def visit_RangeDefinition(
        self, node: ast.RangeDefinition, context: PrinterState
    ) -> None:
        # Add parens around each range element
        if node.start is not None:
            self.stream.write("(")
            self.visit(node.start, context)
            self.stream.write(")")
        self.stream.write(":")
        if node.step is not None:
            self.stream.write("(")
            self.visit(node.step, context)
            self.stream.write(")")
            self.stream.write(":")
        if node.end is not None:
            self.stream.write("(")
            self.visit(node.end, context)
            self.stream.write(")")

    def visit_ForInLoop(
        self, node: ast.ForInLoop, context: PrinterState
    ) -> None:
        self._start_line(context)
        self.stream.write("for ")
        # no type for julia
        # self.visit(node.type)
        # self.stream.write(" ")
        self.visit(node.identifier, context)
        self.stream.write(" in ")
        if isinstance(node.set_declaration, ast.RangeDefinition):
            self.visit(node.set_declaration, context)
        else:
            self.visit(node.set_declaration, context)
        self._visit_statement_list(node.block, context, prefix=" ")
        self.stream.write("end")
        self._end_line(context)

    def visit_QuantumMeasurement(
        self, node: ast.QuantumMeasurement, context: PrinterState
    ) -> None:
        self.stream.write("DestructiveM(")
        self.visit(node.qubit, context)
        self.stream.write(")")

    def visit_SubroutineDefinition(
        self, node: ast.SubroutineDefinition, context: PrinterState
    ) -> None:
        # Here is where we are heavily restricting the QASM3 program format
        # This subroutine is meant to be the main circuit we are checking FT on.
        # We assume it has a specific format:
        #  def func(qubit[size] state, qubit ancilla) { BODY }
        # where state is the logical qubit register and ancilla is any ancilla
        # needed for measurements or other operations.
        if len(node.arguments) != 2:
            raise ValueError("Subroutine must have exactly two arguments")
        if not isinstance(node.arguments[0], ast.QuantumArgument):
            raise ValueError("First argument must be a quantum argument")
        if not isinstance(node.arguments[1], ast.QuantumArgument):
            raise ValueError("Second argument must be a quantum argument")
        if node.arguments[0].name.name != "state":
            raise ValueError("First argument must be named 'state'")
        if node.arguments[1].name.name != "ancilla":
            raise ValueError("Second argument must be named 'ancilla'")

        self.func_name = node.name.name
        self._start_line(context)
        self.stream.write("@qprog ")

        self.visit(node.name, context)
        self.stream.write(" () begin")
        self._end_line(context)

        ## Declare the arrays for state and ancilla
        ## The qprog code has arrays of integer indices for the qubits here
        self.stream.write(
            f"  state = [i for i in 1:{node.arguments[0].size.name}]"
        )
        self._end_line(context)
        self.stream.write("  ancilla = length(state) + 1")
        self._end_line(context)

        self._visit_statement_list(node.body, context)
        self.stream.write("end")
        self._end_line(context)

    def visit_WhileLoop(
        self, node: ast.WhileLoop, context: PrinterState
    ) -> None:
        # converts a QASM while loop to a @qprog repeat-until loop
        # this requries inverting the while loop condition

        self._start_line(context)
        self.stream.write("@repeat begin")
        self._visit_statement_list(node.block, context, prefix=" ")

        self.stream.write("end :until ")

        # Going from while(a) { BODY } to repeat { BODY } until !a
        # Restrict the while loop condition to be a binary expression
        # with LHS an identifier, RHS a literal and operator == or !=

        # Aside (it would be nice to just put ! in front of the entire expression but the
        # overloaded Z3 binary vectors don't seem to support that)

        if not isinstance(node.while_condition, ast.BinaryExpression):
            raise ValueError("While condition must be a unary expression")
        if not isinstance(node.while_condition.lhs, ast.Identifier):
            raise ValueError("While condition LHS must be a variable")
        if not isinstance(node.while_condition.rhs, ast.IntegerLiteral):
            raise ValueError("While condition RHS must be a literal")

        def to_e(x):
            return getattr(ast.BinaryOperator, x)

        op_map = {to_e("=="): to_e("!="), to_e("!="): to_e("==")}

        if node.while_condition.op not in op_map:
            raise ValueError(
                "While condition must be a binary expression with == or !="
            )

        target_op = op_map[node.while_condition.op]
        literal = node.while_condition.rhs.value
        self.stream.write(
            f"({node.while_condition.lhs.name} {target_op.name} bv_val(ctx,{literal},1))"
        )
        self._end_line(context)


def to_julia_tableau_fmt(
    tableau: Tableau,
) -> np.ndarray:
    """
    Converts a Stim stabilizer Tableau to the specified Julia boolean matrix format
    expected by the QuantumSE.jl package.

    The Julia format represents stabilizers as a boolean matrix where rows are
    generators and columns are [X_part | Z_part].

    The Stim format returned by tableau.to_numpy() follows the Aaronson-Gottesman
    format in https://arxiv.org/pdf/quant-ph/0406196.

    """
    _x2x, _x2z, z2x, z2z, _x_signs, _z_signs = tableau.to_numpy()

    num_qubits = z2x.shape[0]

    julia_stabilizer = np.zeros((num_qubits, 2 * num_qubits), dtype=bool)
    # We only care how the stabilizer generators for Z (versus entire Tableu)
    julia_stabilizer[:, 0:num_qubits] = z2x
    julia_stabilizer[:, num_qubits : 2 * num_qubits] = z2z

    return julia_stabilizer


@dataclass
class QProgAndContext:
    src: str
    qprog: Any
    global_decls: dict[str, Any]


def to_qprog(circuit):
    """Convert the circuit to a qprog object, evaluating and returning a handle to
    the julia function object.
    """

    res = openqasm3.parse(circuit)
    buff = io.StringIO()
    visitor = QProgVisitor(buff)
    visitor.visit(res)
    jl.seval(buff.getvalue())

    return QProgAndContext(
        src=buff.getvalue(),
        qprog=getattr(jl, visitor.func_name),
        global_decls={s: getattr(jl, s) for s in visitor.global_decls},
    )


def _bits_needed(j):
    return int(math.ceil(math.log2(j + 1)))


def ft_check(stabilizers: list[PauliString], circuit, max_faults) -> bool:
    """Check if the given circuit over the given stabilizers is fault tolerent
    up to max_faults.
    """

    # Directly translating CatPreparation.jl
    jl.seval("using QuantumSE;")
    jl.seval("using Z3;")

    d = max_faults * 2 + 1
    NERRS = 12  # TODO: Can this be inferred -- basically log2 number of maximum labeled errors (so how many bits to track it all))
    tableau = to_julia_tableau_fmt(Tableau.from_stabilizers(stabilizers))
    num_main_qubits = tableau.shape[
        0
    ]  # TODO: validate this matches what is specified in circuit?
    num_ancilla = 1  # TODO: infer from circuit?

    # create the julia Z3 context
    ctx = jl.Context()

    # create target cat state symbolic stabilizer state
    # TODO: For cat state phases are all 0 the function below doesn't do anything
    # special. For general codes, we will need a way to setup the symbolic phases
    rho_target = jl.from_stabilizer_py(
        num_main_qubits, tableau, ctx, num_ancilla
    )

    # create initial state
    # TODO: For cat state, its not a QECC we are checking, but that starting
    # from computationl basis, we succesfully prepare the cat state
    # For other codes, will be expected results, e.g. initial state for prep
    # logical gate result state of logical op, etc.

    tableau_in = to_julia_tableau_fmt(
        Tableau.from_stabilizers(
            [PauliString(f"Z{i}") for i in range(num_main_qubits)]
        )
    )
    rho_init = jl.from_stabilizer_py(
        num_main_qubits, tableau_in, ctx, num_ancilla
    )

    # Translate the circuit to qprog
    func_and_context = to_qprog(circuit)

    # Create CState object for looking up the classical variables
    # include any global constants declared in the QASM file
    cstate = jl.make_cstate({"ctx": ctx} | func_and_context.global_decls)

    num_errors = (d - 1) // 2
    b_num_main_qubits = _bits_needed(num_main_qubits)
    nerrs_input = jl.bv_val(ctx, 0, b_num_main_qubits)
    cfg1 = jl.SymConfig(func_and_context.qprog(), cstate, rho_init, NERRS)

    # Generate configurations and check_FT
    res = True
    cfgs1 = jl.QuantSymEx(cfg1)
    for cfg in cfgs1:
        if not jl.check_FT_py(
            cfg, rho_target, num_errors, nerrs_input, "prepare"
        ):
            res = False
            break
    return res
