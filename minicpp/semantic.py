"""Semantic analyzer: checks rules S1 to S9 of CONTRATO.md (section 9) on the parse tree.

It collects every SemanticError instead of stopping at the first one. The file has
four fixed sections, one per owner, so each person edits only theirs and Git merges
the changes without conflicts.
"""

import re

from minicpp.errors import SemanticError
from minicpp.node import Node
from minicpp.symbols import Symbol, SymbolTable
from minicpp.tokens import Token

LOOPS = {"WhileStmt", "DoWhileStmt", "ForStmt"}


def _snake_case(label: str) -> str:
    """``LocalDecl`` -> ``local_decl``.

    Only meant for nonterminal labels (CamelCase). A token type such as ``ID``
    would become ``i_d``, so there are no visit methods for tokens.
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", label).lower()


class SemanticAnalyzer:
    """Walks the parse tree once and collects the semantic errors.

    The state (errors and symbol table) is created in check(), so each call
    starts clean even if the same analyzer is reused.
    """

    def check(self, tree: Node) -> list[SemanticError]:
        """Run the semantic rules over the parse tree and return the errors, sorted by position."""
        self.errors: list[SemanticError] = []
        self.symbols = SymbolTable()
        self.loop_depth = 0        # loops that enclose the current node (rule S8)
        self.switch_depth = 0      # switches that enclose the current node (rule S8)
        self.visit(tree)
        self.errors.sort(key=lambda e: (e.line, e.column))
        return self.errors

    # ==================================================================
    # Section 1 (P1): general traversal
    # ==================================================================

    def visit(self, node: Node) -> None:
        """Call visit_<label in snake_case> if it exists, otherwise visit the children in order.

        It also counts the loops and switches that enclose the current node (rule S8).
        The count lives here and not in visit_for_stmt or visit_switch_stmt, because
        those methods belong to section 2 (scopes).
        """
        if node.label in LOOPS:
            self.loop_depth += 1
        elif node.label == "SwitchStmt":
            self.switch_depth += 1

        method = getattr(self, "visit_" + _snake_case(node.label), None)
        if method is None:
            self.generic_visit(node)
        else:
            method(node)

        if node.label in LOOPS:
            self.loop_depth -= 1
        elif node.label == "SwitchStmt":
            self.switch_depth -= 1

    def generic_visit(self, node: Node) -> None:
        """Visit the children from left to right (used when there is no visit_<label>)."""
        for child in node.children:
            self.visit(child)

    def error(self, token: Token, detail: str) -> None:
        """Record an error at the position of a token. The analyzer keeps going."""
        self.errors.append(SemanticError(token.line, token.column, detail))

    # ==================================================================
    # Section 2 (P4): declarations and scopes (rules S1, S2 and S5)
    # ==================================================================

    def declare(self, symbol: Symbol) -> None:
        """Declare a symbol in the current scope and report S2 if the name is already there."""
        previous = self.symbols.declare(symbol)
        if previous is not None:
            self.errors.append(
                SemanticError(
                    symbol.line,
                    symbol.column,
                    f"'{symbol.name}' ya fue declarada en este ámbito (línea {previous.line})",
                )
            )

    def declare_declarators(self, type_name: str, first_id: Node, tail: Node) -> None:
        """Declare `Type ID VarDeclTail`: the first name and the ones of the DeclaratorList.

        VarDeclTail -> Initializer DeclaratorList
        Each initializer is checked before its name is declared, so `int x = x;` is an S1 error.
        """
        initializer, declarator_list = tail.children
        ids = [(first_id, initializer)]
        while not declarator_list.children[0].is_epsilon():   # DeclaratorList -> COMMA ID Initializer DeclaratorList | ε
            _, id_node, init, declarator_list = declarator_list.children
            ids.append((id_node, init))
        for id_node, init in ids:
            self.visit(init)
            self.check_initializer(type_name, init)     # S3 (section 3)
            token = id_node.token
            self.declare(Symbol(token.lexeme, "variable", type_name, token.line, token.column))

    def param_list(self, params: Node) -> list[tuple[str, Token]]:
        """Collect (type, name token) of each parameter.

        Params -> Param ParamsTail | ε       Param -> Type ID       ParamsTail -> COMMA Param ParamsTail | ε
        """
        found = []
        while params.children and params.children[0].label != "ε":
            param = params.children[0] if params.label == "Params" else params.children[1]
            type_node, id_node = param.children
            found.append((type_node.children[0].token.lexeme, id_node.token))
            params = params.children[1] if params.label == "Params" else params.children[2]
        return found

    def declare_function(self, type_name: str, id_node: Node, params: Node, body: Node) -> None:
        """Declare a function in the current (global) scope, then check its body in a new scope.

        The name goes in before the body is checked, so a function can call itself.
        Parameters and the main block of the body share one scope, as in C++.
        """
        token = id_node.token
        parameters = self.param_list(params)
        function = Symbol(token.lexeme, "function", type_name, token.line, token.column,
                          [type_ for type_, _ in parameters])
        self.declare(function)
        self.symbols.enter_scope()
        for param_type, param_token in parameters:
            self.declare(Symbol(param_token.lexeme, "parameter", param_type,
                                param_token.line, param_token.column))
        self.enter_function(function)               # S7, section 4
        self.generic_visit(body.children[1])        # Block -> LBRACE StmtList RBRACE: no extra scope
        self.exit_function()                        # S7, section 4
        self.symbols.exit_scope()

    def visit_global_decl(self, node: Node) -> None:
        """GlobalDecl -> Type ID GlobalDeclTail | VOID ID LPAREN Params RPAREN Block"""
        first = node.children[0]
        if first.label == "VOID":
            _, id_node, _, params, _, body = node.children
            self.declare_function("void", id_node, params, body)
            return
        type_node, id_node, tail = node.children
        type_name = type_node.children[0].token.lexeme
        choice = tail.children[0]
        if choice.label == "LPAREN":                # GlobalDeclTail -> LPAREN Params RPAREN Block
            _, params, _, body = tail.children
            self.declare_function(type_name, id_node, params, body)
        else:                                       # GlobalDeclTail -> VarDeclTail SEMICOLON
            self.declare_declarators(type_name, id_node, choice)

    def visit_local_decl(self, node: Node) -> None:
        """LocalDecl -> Type ID VarDeclTail SEMICOLON"""
        type_node, id_node, tail, _ = node.children
        self.declare_declarators(type_node.children[0].token.lexeme, id_node, tail)

    def visit_block(self, node: Node) -> None:
        """Block -> LBRACE StmtList RBRACE  (a block inside the body opens its own scope)"""
        self.symbols.enter_scope()
        self.generic_visit(node)
        self.symbols.exit_scope()

    def visit_for_stmt(self, node: Node) -> None:
        """ForStmt -> FOR LPAREN ForInit OptExpr SEMICOLON OptExpr RPAREN Stmt

        The scope opens before the initialization, so `int i` does not exist after the loop.
        """
        self.symbols.enter_scope()
        self.generic_visit(node)
        self.check_condition(node.children[3], "for")   # S9 (section 3), while `int i` still exists
        self.symbols.exit_scope()

    def visit_switch_stmt(self, node: Node) -> None:
        """SwitchStmt -> SWITCH LPAREN Expr RPAREN LBRACE CaseList RBRACE

        The braces of the switch are one block: all the cases share its scope. The condition is outside it.
        """
        _, _, condition, _, _, cases, _ = node.children
        self.visit(condition)
        self.symbols.enter_scope()
        self.visit(cases)
        self.symbols.exit_scope()

    def visit_primary(self, node: Node) -> None:
        """Primary -> ID IdTail | Literal | LPAREN Expr RPAREN   (S1 for variables and function calls)"""
        first = node.children[0]
        if first.label == "ID":
            token = first.token
            is_call = node.children[1].children[0].label == "LPAREN"   # IdTail -> LPAREN Args RPAREN | ε
            symbol = self.symbols.lookup(token.lexeme)
            if symbol is None:
                what = "la función" if is_call else "la variable"
                self.error(token, f"{what} '{token.lexeme}' no está declarada")
            elif is_call:
                self.check_call(symbol, token, node.children[1])   # S6, section 4
            elif symbol.kind == "function":                    # S6: a function used as a value
                self.error(token, f"'{token.lexeme}' es una función, no una variable")
        self.generic_visit(node)                    # the arguments of a call are expressions too

    def visit_cin_stmt(self, node: Node) -> None:
        """CinStmt -> CIN SHIFT_RIGHT ID CinTail SEMICOLON   (S1 for each variable read)"""
        self.check_cin_names(node)

    def check_cin_names(self, node: Node) -> None:
        for child in node.children:
            if child.label == "ID":
                if self.symbols.lookup(child.token.lexeme) is None:
                    self.error(child.token, f"la variable '{child.token.lexeme}' no está declarada")
            else:
                self.check_cin_names(child)    

    # ==================================================================
    # Section 3 (P5): types of expressions (rules S3, S4 and S9)
    # ==================================================================

    # Numeric group, from lowest to highest rank. C++ converts among them on its own.
    NUMERIC_RANK = {"bool": 0, "char": 1, "int": 2, "float": 3, "double": 4}
    INTEGER_TYPES = {"bool", "char", "int"}                   # the ones % accepts
    INCREMENTABLE = {"char", "int", "float", "double"}        # ++ and -- (not bool, not string)
    LITERAL_TYPES = {
        "INT_LITERAL": "int",
        "FLOAT_LITERAL": "double",          # 3.14 is double in C++ (float needs the suffix f)
        "STRING_LITERAL": "string",
        "CHAR_LITERAL": "char",
        "TRUE": "bool",
        "FALSE": "bool",
    }
    # Expression levels with the scheme X -> Y XTail. Their type is computed the same way.
    BINARY_LEVELS = {"OrExpr", "AndExpr", "EqualityExpr", "RelationalExpr", "AdditiveExpr", "MultExpr"}
    LOGICAL_OPS = {"&&", "||"}
    COMPARISON_OPS = {"==", "!=", "<", ">", "<=", ">="}
    ARITHMETIC_OPS = {"+", "-", "*", "/"}

    @classmethod
    def is_numeric(cls, type_name: str) -> bool:
        return type_name in cls.NUMERIC_RANK

    @classmethod
    def is_integer(cls, type_name: str) -> bool:
        return type_name in cls.INTEGER_TYPES

    @classmethod
    def promote(cls, left: str, right: str) -> str:
        """Type of an arithmetic result: the higher rank, and at least int (`char + char` is int)."""
        return max(left, right, "int", key=cls.NUMERIC_RANK.__getitem__)

    def visit_program(self, node: Node) -> None:
        """Program -> Header GlobalList   (the root: starts the cache of types for this tree)"""
        self.types: dict[int, str | None] = {}
        self.generic_visit(node)

    def visit_expr(self, node: Node) -> None:
        """Expr -> AssignExpr

        First the children are visited, so section 2 checks S1 on the names. Then the
        type is computed, which reports S3 and S4. A nested Expr (parentheses or
        arguments) was already computed and saved, so its errors are not repeated.
        """
        self.generic_visit(node)
        self.type_of(node)

    def visit_cout_item(self, node: Node) -> None:
        """CoutItem -> ENDL | AdditiveExpr   (cout shows any type except void)"""
        self.generic_visit(node)
        item = node.children[0]
        if item.label == "AdditiveExpr" and self.type_of(item) == "void":
            self.error(item.leaves()[0], "cout no puede mostrar un valor de tipo void")

    def visit_if_stmt(self, node: Node) -> None:
        """IfStmt -> IF LPAREN Expr RPAREN Stmt ElsePart"""
        self.generic_visit(node)
        self.check_condition(node.children[2], "if")

    def visit_while_stmt(self, node: Node) -> None:
        """WhileStmt -> WHILE LPAREN Expr RPAREN Stmt"""
        self.generic_visit(node)
        self.check_condition(node.children[2], "while")

    def visit_do_while_stmt(self, node: Node) -> None:
        """DoWhileStmt -> DO Stmt WHILE LPAREN Expr RPAREN SEMICOLON"""
        self.generic_visit(node)
        self.check_condition(node.children[4], "do-while")

    def check_condition(self, node: Node, statement: str) -> None:
        """S9: the condition can not be string nor void. Receives an Expr or an OptExpr.

        The for calls it from section 2 with its OptExpr, which may be ε (`for (;;)`).
        """
        if node.label == "OptExpr":
            node = node.children[0]
            if node.is_epsilon():
                return
        type_name = self.type_of(node)
        if type_name in ("string", "void"):
            self.error(node.leaves()[0], f"la condición del {statement} no puede ser de tipo {type_name}")

    def check_initializer(self, type_name: str, init: Node) -> None:
        """S3 in a declaration: `int x = "hola";`. Called from section 2.

        Initializer -> ASSIGN Expr | ε
        """
        if init.children[0].is_epsilon():
            return
        self.check_assignment(init.children[0].token, type_name, self.type_of(init.children[1]))

    def type_of(self, node: Node) -> str | None:
        """Return the type of an expression node, or None if it is unknown because of an error.

        Each node is computed only once: the result is saved by the id of the node,
        so asking again (a condition, a return) does not report the same error twice.
        """
        key = id(node)
        if key not in self.types:
            self.types[key] = self.compute_type(node)
        return self.types[key]

    def compute_type(self, node: Node) -> str | None:
        """Compute the type according to the production of the node."""
        label = node.label
        children = node.children

        if label == "Expr":                         # Expr -> AssignExpr
            return self.type_of(children[0])

        if label == "AssignExpr":                   # AssignExpr -> OrExpr AssignTail
            target, tail = children
            target_type = self.type_of(target)
            if tail.children[0].is_epsilon():       # no assignment: just the OrExpr
                return target_type
            op_node, value = tail.children          # AssignTail -> AssignOp AssignExpr
            return self.check_assignment(op_node.children[0].token, target_type, self.type_of(value))

        if label in self.BINARY_LEVELS:             # X -> Y XTail
            first, tail = children
            return self.binary_chain(self.type_of(first), tail)

        if label == "UnaryExpr":                    # UnaryExpr -> UnaryOp UnaryExpr | PostfixExpr
            if children[0].label == "UnaryOp":
                return self.unary_type(children[0].children[0].token, self.type_of(children[1]))
            return self.type_of(children[0])

        if label == "PostfixExpr":                  # PostfixExpr -> Primary PostfixOpt
            primary, postfix = children
            primary_type = self.type_of(primary)
            if postfix.children[0].is_epsilon():
                return primary_type
            return self.unary_type(postfix.children[0].token, primary_type)

        if label == "Primary":                      # Primary -> ID IdTail | Literal | LPAREN Expr RPAREN
            first = children[0]
            if first.label == "ID":
                return self.name_type(first.token, children[1])
            if first.label == "Literal":            # Literal -> INT_LITERAL | FLOAT_LITERAL | ...
                return self.LITERAL_TYPES[first.children[0].label]
            return self.type_of(children[1])

        return None

    def name_type(self, token: Token, id_tail: Node) -> str | None:
        """Type of `ID IdTail`: a variable, or the return type of a function call.

        If the name is not declared, S1 was already reported in section 2: the type is unknown.
        A call to something that is not a function is S6 (section 4): unknown here too.
        """
        symbol = self.symbols.lookup(token.lexeme)
        if symbol is None:
            return None
        is_call = id_tail.children[0].label == "LPAREN"        # IdTail -> LPAREN Args RPAREN | ε
        if is_call:
            return symbol.type if symbol.kind == "function" else None
        return symbol.type if symbol.kind != "function" else None

    def binary_chain(self, left: str | None, tail: Node) -> str | None:
        """Walk an XTail from left to right: XTail -> op Y XTail | ε

        This is how the left associativity of `a - b - c` = `(a - b) - c` is respected:
        the type accumulated so far is the left operand of the next operator.
        """
        while not tail.children[0].is_epsilon():
            op_node, operand, tail = tail.children
            op = op_node.leaves()[0]                # OR and AND are tokens; the rest are XOp nodes
            left = self.binary_type(op, left, self.type_of(operand))
        return left

    def binary_type(self, op: Token, left: str | None, right: str | None) -> str | None:
        """S4 for binary operators. Returns the type of the result, or None after an error."""
        if left is None or right is None:           # an earlier error: do not report again
            return None
        symbol = op.lexeme
        both_numeric = self.is_numeric(left) and self.is_numeric(right)
        both_string = left == right == "string"

        if symbol in self.LOGICAL_OPS and both_numeric:
            return "bool"
        if symbol in self.COMPARISON_OPS and (both_numeric or both_string):
            return "bool"
        if symbol in self.ARITHMETIC_OPS and both_numeric:
            return self.promote(left, right)
        if symbol == "+" and both_string:
            return "string"
        if symbol == "%":
            if self.is_integer(left) and self.is_integer(right):
                return "int"
            wrong = left if not self.is_integer(left) else right
            self.error(op, f"el operador % necesita operandos enteros y recibió {wrong}")
            return None

        self.error(op, f"el operador {symbol} no se puede aplicar a {left} y {right}")
        return None

    def unary_type(self, op: Token, operand: str | None) -> str | None:
        """S4 for !, unary - and +, and prefix or postfix ++ and --."""
        if operand is None:
            return None
        symbol = op.lexeme
        if symbol == "!" and self.is_numeric(operand):
            return "bool"
        if symbol in ("-", "+") and self.is_numeric(operand):
            return self.promote(operand, operand)
        if symbol in ("++", "--") and operand in self.INCREMENTABLE:
            return operand
        self.error(op, f"el operador {symbol} no se puede aplicar a {operand}")
        return None

    def check_assignment(self, op: Token, target: str | None, value: str | None) -> str | None:
        """S3 for =, +=, -=, *=, /=, %= and for initializers. Returns the type of the target.

        `=` needs both numeric or both string. `+=` too. `-=`, `*=`, `/=` only numbers,
        and `%=` only integers. Mixing string with a number is S3; an operator that
        does not accept the types (like `s -= t` with strings) is S4.
        """
        if target is None or value is None:
            return None
        symbol = op.lexeme
        both_numeric = self.is_numeric(target) and self.is_numeric(value)
        both_string = target == value == "string"

        if not (both_numeric or both_string):
            self.error(op, f"no se puede asignar {value} a {target}")
            return None
        if symbol in ("=", "+=") or (both_numeric and symbol in ("-=", "*=", "/=")):
            return target
        if symbol == "%=" and self.is_integer(target) and self.is_integer(value):
            return target
        if symbol == "%=" and both_numeric:
            wrong = target if not self.is_integer(target) else value
            self.error(op, f"el operador %= necesita operandos enteros y recibió {wrong}")
            return None
        self.error(op, f"el operador {symbol} no se puede aplicar a {target} y {value}")
        return None

    # ==================================================================
    # Section 4 (P1): functions, return, break and continue
    # ==================================================================

    def visit_break_stmt(self, node: Node) -> None:
        """BreakStmt -> BREAK SEMICOLON   (S8: only inside a loop or a switch)"""
        if self.loop_depth == 0 and self.switch_depth == 0:
            self.error(node.children[0].token,
                       "break solo puede ir dentro de un ciclo o de un switch")

    def visit_continue_stmt(self, node: Node) -> None:
        """ContinueStmt -> CONTINUE SEMICOLON   (S8: only inside a loop)"""
        if self.loop_depth == 0:
            self.error(node.children[0].token, "continue solo puede ir dentro de un ciclo")

    def call_arguments(self, args: Node) -> list[Node]:
        """Return the Expr node of each argument, from left to right.

        Args -> Expr ArgsTail | ε       ArgsTail -> COMMA Expr ArgsTail | ε
        """
        if args.children[0].is_epsilon():
            return []
        found = [args.children[0]]
        tail = args.children[1]
        while not tail.children[0].is_epsilon():
            _, expr, tail = tail.children
            found.append(expr)
        return found

    def check_call(self, symbol: Symbol, token: Token, id_tail: Node) -> None:
        """S6: the called name is a function, gets as many arguments as it has parameters,
        and each argument is compatible with its parameter.

        IdTail -> LPAREN Args RPAREN
        The types are only compared when the count matches, so one mistake gives one error.
        """
        name = token.lexeme
        if symbol.kind != "function":
            self.error(token, f"'{name}' no es una función")
            return
        arguments = self.call_arguments(id_tail.children[1])
        expected, received = len(symbol.params), len(arguments)
        if expected != received:
            word = "argumento" if expected == 1 else "argumentos"
            self.error(token, f"'{name}' espera {expected} {word} y recibió {received}")
            return
        for position, (param_type, argument) in enumerate(zip(symbol.params, arguments), 1):
            argument_type = self.type_of(argument)
            if argument_type is not None and not self.compatible(param_type, argument_type):
                detail = (f"el argumento {position} de '{name}' "
                          f"debe ser {param_type} y recibió {argument_type}")
                self.error(argument.leaves()[0], detail)

    def enter_function(self, function: Symbol) -> None:
        """Remember the function whose body is being checked (rule S7)."""
        self.current_function = function
        self.return_count = 0

    def exit_function(self) -> None:
        """S7: a function with a type has at least one return. main may end without one.

        It does not check that every path returns: `if (x) return 1;` alone is accepted.
        The error points at the name of the function, as in every rule (CONTRATO.md, section 9).
        """
        function = self.current_function
        if function.type == "void" or function.name == "main" or self.return_count > 0:
            return
        self.errors.append(SemanticError(function.line, function.column,
                                         self.missing_value(function)))

    def visit_return_stmt(self, node: Node) -> None:
        """ReturnStmt -> RETURN OptExpr SEMICOLON   (S7: the value matches the function type)

        OptExpr -> Expr | ε. The value must be compatible with the return type, as in `=`.
        """
        self.return_count += 1
        function = self.current_function
        has_value = not node.children[1].children[0].is_epsilon()
        token = node.children[0].token
        if function.type == "void" and has_value:
            self.error(token,
                       f"la función '{function.name}' es void y no puede devolver un valor")
        elif function.type != "void" and not has_value:
            self.error(token, self.missing_value(function))
        elif has_value:
            value = node.children[1].children[0]            # OptExpr -> Expr
            value_type = self.type_of(value)
            if value_type is not None and not self.compatible(function.type, value_type):
                detail = (f"la función '{function.name}' "
                          f"debe devolver {function.type} y recibió {value_type}")
                self.error(value.leaves()[0], detail)
        self.generic_visit(node)                    # the returned expression may use names (S1)

    @staticmethod
    def missing_value(function: Symbol) -> str:
        return f"la función '{function.name}' debe devolver un valor de tipo {function.type}"

    def compatible(self, target: str, value: str) -> bool:
        """The rule of `=` (CONTRATO.md, section 9): both numeric, or both string."""
        return (self.is_numeric(target) and self.is_numeric(value)) or target == value == "string"
