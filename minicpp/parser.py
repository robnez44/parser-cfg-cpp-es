from minicpp.errors import SyntacticError
from minicpp.node import EPSILON, Node
from minicpp.tokens import Token

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

    def epsilon(self) -> Node:
        """Return an ε leaf, used when a production derives the empty string."""
        return Node(EPSILON)

    def error(self, expected: list[str]):
        """Raise a SyntacticError at the current token."""
        token = self.current()
        raise SyntacticError(token.line, token.column, expected, token)