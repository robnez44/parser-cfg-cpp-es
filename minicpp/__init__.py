"""Mini C++ analyzer: lexer, parser and semantic analyzer (CONTRATO.md, section 7)."""

from minicpp.errors import SemanticError
from minicpp.lexer import tokenize
from minicpp.node import Node
from minicpp.parser import Parser
from minicpp.semantic import SemanticAnalyzer


def analyze(code: str) -> tuple[Node, list[SemanticError]]:
    """Run the three stages in order and return the parse tree and the semantic errors.

    A lexical or syntactic error is raised and stops the analysis (decision 14),
    so the semantic analyzer only runs on a complete tree.
    """
    tokens = tokenize(code)
    tree = Parser(tokens).parse()
    errors = SemanticAnalyzer().check(tree)
    return tree, errors
