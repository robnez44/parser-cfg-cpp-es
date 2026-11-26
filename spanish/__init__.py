"""Spanish analyzer: lexer and parser (CONTRATO_FASE2.md, section 6)."""

from minicpp.node import Node
from spanish.lexer import tokenize
from spanish.parser import SpanishParser


def analyze(sentence: str) -> Node:
    """Run the lexer and the parser and return the parse tree.

    A lexical or syntactic error is raised. There is no semantic analyzer in
    phase 2, because agreement is checked by the grammar (decision 3).
    """
    tokens = tokenize(sentence)
    return SpanishParser(tokens).parse()
