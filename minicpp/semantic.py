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
        self.declare(Symbol(token.lexeme, "function", type_name, token.line, token.column,
                            [type_ for type_, _ in parameters]))
        self.symbols.enter_scope()
        for param_type, param_token in parameters:
            self.declare(Symbol(param_token.lexeme, "parameter", param_type,
                                param_token.line, param_token.column))
        self.generic_visit(body.children[1])        # Block -> LBRACE StmtList RBRACE: no extra scope
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
            if self.symbols.lookup(token.lexeme) is None:
                what = "la función" if is_call else "la variable"
                self.error(token, f"{what} '{token.lexeme}' no está declarada")
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
    # Section 3 (P5): types of expressions
    # ==================================================================

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
