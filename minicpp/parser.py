from typing import NoReturn

from minicpp.errors import SyntacticError
from minicpp.node import EPSILON, Node
from minicpp.tokens import Token

# ---------- Token groups used to choose between alternatives ----------
# Each group comes from a FIRST set of grammars/cpp.gram.

LITERALS = ("INT_LITERAL", "FLOAT_LITERAL", "STRING_LITERAL", "CHAR_LITERAL", "TRUE", "FALSE")  # FIRST(Literal)
MULT_OPS = ("STAR", "SLASH", "PERCENT")                                    # FIRST(MultOp)
UNARY_OPS = ("NOT", "MINUS", "PLUS", "INCREMENT", "DECREMENT")             # FIRST(UnaryOp)
INCREMENT_OPS = ("INCREMENT", "DECREMENT")                                 # ++ and --

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

    def require_variable(self, operand: Node) -> None:
        """Check that an operand of ++ or -- is a plain variable.

        The grammar cannot express this rule and stay LL(1), so it is checked
        here (CONTRATO.md, section 2). The error points at the operand.
        """
        tokens = operand.leaves()
        if len(tokens) != 1 or tokens[0].type != "ID":
            first = tokens[0]
            raise SyntacticError(first.line, first.column, ["ID"], first)

    # Expressions

    def expr(self) -> Node:
        """Temporary until step 4: only parses up to the multiplicative level."""
        return self.mult_expr()

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
        
        self.error(["ID", *LITERALS, "LPAREN"])

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