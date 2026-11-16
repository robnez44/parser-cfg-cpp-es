from typing import NoReturn

from minicpp.errors import SyntacticError
from minicpp.node import EPSILON, Node
from minicpp.tokens import Token

# ---------- Token groups used to choose between alternatives ----------
# Each group comes from a FIRST set of grammars/cpp.gram.

LITERALS = ("INT_LITERAL", "FLOAT_LITERAL", "STRING_LITERAL", "CHAR_LITERAL", "TRUE", "FALSE")  # FIRST(Literal)
PRIMARY_START = ("ID", *LITERALS, "LPAREN")                                 # FIRST(Primary)
ASSIGN_OPS = ("ASSIGN", "PLUS_ASSIGN", "MINUS_ASSIGN", "STAR_ASSIGN", "SLASH_ASSIGN", "PERCENT_ASSIGN")  # FIRST(AssignOp)
EQUALITY_OPS = ("EQUAL", "NOT_EQUAL")                                       # FIRST(EqualityOp)
RELATIONAL_OPS = ("LESS", "GREATER", "LESS_EQUAL", "GREATER_EQUAL")         # FIRST(RelationalOp)
ADDITIVE_OPS = ("PLUS", "MINUS")                                            # FIRST(AdditiveOp)
MULT_OPS = ("STAR", "SLASH", "PERCENT")                                     # FIRST(MultOp)
UNARY_OPS = ("NOT", "MINUS", "PLUS", "INCREMENT", "DECREMENT")              # FIRST(UnaryOp)
INCREMENT_OPS = ("INCREMENT", "DECREMENT")                                  # ++ and --


class Parser:
    """Recursive descent parser for the C++ subset defined in grammars/cpp.gram.

    Each nonterminal of the grammar has one method with the same name in
    snake_case. The first line of each method's docstring is the production
    it implements. The parser never backtracks: it chooses every production
    by looking only at the current token (one token of lookahead).
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens   # always ends with an EOF token
        self.pos = 0           # index of the current token

    # Helpers 

    def current(self) -> Token:
        """Return the lookahead token without consuming it."""
        return self.tokens[self.pos]

    def check(self, *token_types: str) -> bool:
        """Return True if the current token is one of the given types."""
        return self.current().type in token_types

    def consume(self, token_type: str) -> Node:
        """Consume the current token if it has the expected type.

        Returns a terminal leaf for the parse tree, or raises SyntacticError.
        """
        token = self.current()
        if token.type != token_type:
            self.error([token_type])
        self.pos += 1
        return Node(token_type, token=token)

    def consume_one_of(self, token_types: tuple[str, ...]) -> Node:
        """Consume the current token if it is any of the given types."""
        if not self.check(*token_types):
            self.error(list(token_types))

        return self.consume(self.current().type)

    def epsilon(self) -> Node:
        """Return an ε leaf, used when a production derives the empty string."""
        return Node(EPSILON)

    def error(self, expected: list[str]) -> NoReturn:
        """Raise a SyntacticError at the current token."""
        token = self.current()
        raise SyntacticError(token.line, token.column, expected, token)

    def require_variable(self, target: Node) -> None:
        """Check that the target of an assignment, ++ or -- is a plain variable.

        The grammar cannot express this rule and stay LL(1), so it is checked
        here (CONTRATO.md, section 2). The error points at the first token
        that breaks the rule: the target itself if it does not start with an
        identifier, or the token right after the identifier otherwise.
        """
        tokens = target.leaves()
        if len(tokens) == 1 and tokens[0].type == "ID":
            return
        offending = tokens[1] if tokens[0].type == "ID" else tokens[0]
        raise SyntacticError(offending.line, offending.column, ["ID"], offending)

    # Expressions

    def expr(self) -> Node:
        """Expr -> AssignExpr"""
        return Node("Expr", [self.assign_expr()])

    def assign_expr(self) -> Node:
        """AssignExpr -> OrExpr AssignTail"""
        left = self.or_expr()
        if self.check(*ASSIGN_OPS):
            self.require_variable(left)
        return Node("AssignExpr", [left, self.assign_tail()])

    def assign_tail(self) -> Node:
        """AssignTail -> AssignOp AssignExpr | ε"""
        if self.check(*ASSIGN_OPS):
            return Node("AssignTail", [self.assign_op(), self.assign_expr()])
        return Node("AssignTail", [self.epsilon()])

    def assign_op(self) -> Node:
        """AssignOp -> ASSIGN | PLUS_ASSIGN | MINUS_ASSIGN | STAR_ASSIGN | SLASH_ASSIGN | PERCENT_ASSIGN"""
        return Node("AssignOp", [self.consume_one_of(ASSIGN_OPS)])

    def or_expr(self) -> Node:
        """OrExpr -> AndExpr OrExprTail"""
        return Node("OrExpr", [self.and_expr(), self.or_expr_tail()])

    def or_expr_tail(self) -> Node:
        """OrExprTail -> OR AndExpr OrExprTail | ε"""
        if self.check("OR"):
            return Node("OrExprTail", [self.consume("OR"), self.and_expr(), self.or_expr_tail()])
        return Node("OrExprTail", [self.epsilon()])

    def and_expr(self) -> Node:
        """AndExpr -> EqualityExpr AndExprTail"""
        return Node("AndExpr", [self.equality_expr(), self.and_expr_tail()])

    def and_expr_tail(self) -> Node:
        """AndExprTail -> AND EqualityExpr AndExprTail | ε"""
        if self.check("AND"):
            return Node("AndExprTail", [self.consume("AND"), self.equality_expr(), self.and_expr_tail()])
        return Node("AndExprTail", [self.epsilon()])

    def equality_expr(self) -> Node:
        """EqualityExpr -> RelationalExpr EqualityExprTail"""
        return Node("EqualityExpr", [self.relational_expr(), self.equality_expr_tail()])

    def equality_expr_tail(self) -> Node:
        """EqualityExprTail -> EqualityOp RelationalExpr EqualityExprTail | ε"""
        if self.check(*EQUALITY_OPS):
            return Node("EqualityExprTail", [self.equality_op(), self.relational_expr(), self.equality_expr_tail()])
        return Node("EqualityExprTail", [self.epsilon()])

    def equality_op(self) -> Node:
        """EqualityOp -> EQUAL | NOT_EQUAL"""
        return Node("EqualityOp", [self.consume_one_of(EQUALITY_OPS)])

    def relational_expr(self) -> Node:
        """RelationalExpr -> AdditiveExpr RelationalExprTail"""
        return Node("RelationalExpr", [self.additive_expr(), self.relational_expr_tail()])

    def relational_expr_tail(self) -> Node:
        """RelationalExprTail -> RelationalOp AdditiveExpr RelationalExprTail | ε"""
        if self.check(*RELATIONAL_OPS):
            return Node("RelationalExprTail", [self.relational_op(), self.additive_expr(), self.relational_expr_tail()])
        return Node("RelationalExprTail", [self.epsilon()])

    def relational_op(self) -> Node:
        """RelationalOp -> LESS | GREATER | LESS_EQUAL | GREATER_EQUAL"""
        return Node("RelationalOp", [self.consume_one_of(RELATIONAL_OPS)])

    def additive_expr(self) -> Node:
        """AdditiveExpr -> MultExpr AdditiveExprTail"""
        return Node("AdditiveExpr", [self.mult_expr(), self.additive_expr_tail()])

    def additive_expr_tail(self) -> Node:
        """AdditiveExprTail -> AdditiveOp MultExpr AdditiveExprTail | ε"""
        if self.check(*ADDITIVE_OPS):
            return Node("AdditiveExprTail", [self.additive_op(), self.mult_expr(), self.additive_expr_tail()])
        return Node("AdditiveExprTail", [self.epsilon()])

    def additive_op(self) -> Node:
        """AdditiveOp -> PLUS | MINUS"""
        return Node("AdditiveOp", [self.consume_one_of(ADDITIVE_OPS)])

    def mult_expr(self) -> Node:
        """MultExpr -> UnaryExpr MultExprTail"""
        return Node("MultExpr", [self.unary_expr(), self.mult_expr_tail()])

    def mult_expr_tail(self) -> Node:
        """MultExprTail -> MultOp UnaryExpr MultExprTail | ε"""
        if self.check(*MULT_OPS):
            return Node("MultExprTail", [self.mult_op(), self.unary_expr(), self.mult_expr_tail()])
        return Node("MultExprTail", [self.epsilon()])

    def mult_op(self) -> Node:
        """MultOp -> STAR | SLASH | PERCENT"""
        return Node("MultOp", [self.consume_one_of(MULT_OPS)])

    def unary_expr(self) -> Node:
        """UnaryExpr -> UnaryOp UnaryExpr | PostfixExpr"""
        if self.check(*UNARY_OPS):
            op = self.unary_op()
            operand = self.unary_expr()
            if op.children[0].label in INCREMENT_OPS:
                self.require_variable(operand)
            return Node("UnaryExpr", [op, operand])
        return Node("UnaryExpr", [self.postfix_expr()])

    def unary_op(self) -> Node:
        """UnaryOp -> NOT | MINUS | PLUS | INCREMENT | DECREMENT"""
        return Node("UnaryOp", [self.consume_one_of(UNARY_OPS)])

    def postfix_expr(self) -> Node:
        """PostfixExpr -> Primary PostfixOpt"""
        primary = self.primary()
        if self.check(*INCREMENT_OPS):
            self.require_variable(primary)
        return Node("PostfixExpr", [primary, self.postfix_opt()])

    def postfix_opt(self) -> Node:
        """PostfixOpt -> INCREMENT | DECREMENT | ε"""
        if self.check(*INCREMENT_OPS):
            return Node("PostfixOpt", [self.consume_one_of(INCREMENT_OPS)])
        return Node("PostfixOpt", [self.epsilon()])

    def primary(self) -> Node:
        """Primary -> ID IdTail | Literal | LPAREN Expr RPAREN"""
        if self.check("ID"):
            return Node("Primary", [self.consume("ID"), self.id_tail()])
        if self.check(*LITERALS):
            return Node("Primary", [self.literal()])
        if self.check("LPAREN"):
            return Node("Primary", [self.consume("LPAREN"), self.expr(), self.consume("RPAREN")])
        self.error(list(PRIMARY_START))

    def id_tail(self) -> Node:
        """IdTail -> LPAREN Args RPAREN | ε"""
        if self.check("LPAREN"):
            return Node("IdTail", [self.consume("LPAREN"), self.args(), self.consume("RPAREN")])
        return Node("IdTail", [self.epsilon()])

    def args(self) -> Node:
        """Args -> Expr ArgsTail | ε"""
        if self.check("RPAREN"):
            return Node("Args", [self.epsilon()])
        return Node("Args", [self.expr(), self.args_tail()])

    def args_tail(self) -> Node:
        """ArgsTail -> COMMA Expr ArgsTail | ε"""
        if self.check("COMMA"):
            return Node("ArgsTail", [self.consume("COMMA"), self.expr(), self.args_tail()])
        return Node("ArgsTail", [self.epsilon()])

    def literal(self) -> Node:
        """Literal -> INT_LITERAL | FLOAT_LITERAL | STRING_LITERAL | CHAR_LITERAL | TRUE | FALSE"""
        return Node("Literal", [self.consume_one_of(LITERALS)])